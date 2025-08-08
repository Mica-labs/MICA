from __future__ import annotations

import collections
import math
import re
import types
import typing as t
import typing_extensions as te

import u

from ._utils import UNION_TYPES, ExponentDict, str_exponent
from .capital_quantities import QUANTITY, DIV, MUL, MUL_


__all__ = ["Quantity", "NullableQuantity"]


FrozenExponents = frozenset[tuple[type[QUANTITY], int]]

Q_co = t.TypeVar("Q_co", bound=QUANTITY, covariant=True)
Q2 = t.TypeVar("Q2", bound=QUANTITY)


NUMBER_WITH_UNIT_REGEX = re.compile(r"([+-]?[0-9._]+)(.*)")


QUANTITY_ALIASES_BY_EXPONENTS = dict[FrozenExponents, "QuantityAlias"]()


class QuantityAlias(types.GenericAlias):
    exponents: ExponentDict
    units: t.Sequence[u.Unit]
    prefixes: t.Sequence[u.Prefix]

    def __new__(cls, typ, subtype, exponents: ExponentDict):
        self = super().__new__(cls, typ, subtype)

        self.exponents = exponents
        self.units = []
        self.prefixes = u.STANDARD_SI_PREFIXES

        return self

    # GenericAlias is stupid and redirects all attribute access to the __origin__ class. Since we
    # want to implement an `exponents` property, we have to fix that idiotic behavior.
    def __getattribute__(self, name: str):
        if name in __class__.__annotations__:
            return vars(self)[name]

        if name in vars(__class__):
            return vars(__class__)[name].__get__(self)

        return super().__getattribute__(name)

    @property
    def base_unit(self) -> u.Unit:
        if self.units:
            return next(unit for unit in self.units if unit.multiplier == 1)

        unit = u.one
        for quantity, exponent in self.exponents.items():
            unit *= Quantity[quantity].base_unit ** exponent

        return unit

    def parse(self, *args, **kwargs):
        return Quantity.parse.__func__(self, *args, **kwargs)  # type: ignore

    def __call__(self, value: float, unit: u.Unit[Q_co] | None = None):
        if unit is None:
            assert value == 0
            unit = self.base_unit

        return super().__call__(value, unit)  # type: ignore (wtf?)

    def __hash__(self) -> int:
        return hash(self.exponents)

    def __eq__(self, other: object):
        if not isinstance(other, __class__):
            return NotImplemented

        return self.exponents == other.exponents

    def __repr__(self) -> str:
        exponents = self.exponents

        if not exponents:
            return "Quantity[ONE]"

        exponents = " ".join(
            f"{quantity.__name__}{str_exponent(exponents[quantity])}"
            for quantity in sorted(exponents, key=lambda q: q.__name__)
        )

        return f"Quantity[{exponents}]"


def get_exponents(quantity_caps: type[QUANTITY]) -> ExponentDict:
    exponents = collections.defaultdict(int)

    _add_exponents(quantity_caps, exponents)

    return ExponentDict(exponents)


def _add_exponents(quantity, exponents: collections.defaultdict[type[QUANTITY], int]) -> None:
    # `quantity` can be:
    #
    # 1. A parameterized MUL or DIV
    # 2. A subclass of `QUANTITY`
    # 3. A Union
    if isinstance(quantity, type):
        if quantity.__name__ != "ONE":
            exponents[quantity] += 1

        return

    origin = t.get_origin(quantity)
    args = t.get_args(quantity)

    if any(isinstance(arg, t.TypeVar) for arg in args):
        raise NotFullyParameterized

    if origin in UNION_TYPES:
        # If it's a Union, then the subtypes must all be equivalent. So we simply pick one and
        # recurse.
        quantity = args[0]
        _add_exponents(quantity, exponents)
    elif origin is MUL_:
        _add_exponents(args[0], exponents)
        _add_exponents(args[1], exponents)
    else:
        _add_exponents(args[0], exponents)

        exps = collections.defaultdict(int)
        _add_exponents(args[1], exps)

        for quant, exp in exps.items():
            exponents[quant] -= exp


class NotFullyParameterized(Exception):
    pass


# Regular properties can't be annotated to return Units that match the Quantity (for example, make
# `Speed.base_unit` return a `Unit[SPEED]`), so we have to use custom descriptors. They're designed
# to be used as decorators because that way the IDE preserves the docstring.
class UnitProperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance: type[Quantity[Q_co]], owner: t.Any = None) -> u.Unit[Q_co]:
        return self.func(instance)


class UnitSequenceProperty:
    def __init__(self, func):
        self.func = func

    def __get__(
        self, instance: type[Quantity[Q_co]], owner: t.Any = None
    ) -> t.Sequence[u.Unit[Q_co]]:
        return self.func(instance)


class QuantityMeta(type(t.Generic)):
    @property
    def exponents(cls) -> ExponentDict:
        """
        When used on a compound quantity, this returns a mapping of all the base quantities that
        make up the compound quantity along with their exponents. For example, `u.Speed.exponents`
        will return `{u.DISTANCE: 1, u.DURATION: -1}`.

        When used on a base quantity like `Duration`, it will simply return that quantity with an
        exponent of 1: `{u.DURATION: 1}`.
        """

        raise TypeError(f"Unparameterized {cls} has no exponents")

    @UnitSequenceProperty
    def units(cls):
        """
        A sequence of units associated with this quantity. Only units created by the `Unit`
        constructor are included, which means that this returns an empty sequence for compound
        quantities like `Speed` and `Area`. However, if a compound unit has dedicated units, like
        `Frequency` has `hertz`, then those will be included.

        The units are sorted by their `multiplier`, in ascending order.
        """
        raise TypeError(f"Unparameterized {cls} has no units")

    @UnitProperty
    def base_unit(cls):
        """
        Returns the base unit for this quantity, that is, the unit with a `multiplier` of 1.
        """
        raise TypeError(f"Unparameterized {cls} has no units")

    @property
    def prefixes(cls) -> t.Sequence[u.Prefix]:
        """
        Returns the prefixes that are conventionally used with this quantity. For most quantities,
        this is `u.STANDARD_SI_PREFIXES`. There are some exceptions though, for example,
        `u.Duration` only uses "small" prefixes like `u.milli` and `u.micro`.
        """
        raise TypeError(f"Unparameterized {cls} has no prefixes")

    @prefixes.setter
    def prefixes(cls, prefixes: t.Sequence[u.Prefix]) -> None:
        raise TypeError(f"Unparameterized {cls} cannot have prefixes")


class Quantity(t.Generic[Q_co], metaclass=QuantityMeta):
    @classmethod  # This is only here to shut up the type checker
    def __class_getitem(cls, quantity_caps) -> QuantityAlias:
        # Make sure that all equivalent quantities return the same QuantityAlias
        try:
            if isinstance(quantity_caps, t.TypeVar):
                raise NotFullyParameterized

            exponents = get_exponents(quantity_caps)
        except NotFullyParameterized:
            return super().__class_getitem__(quantity_caps)  # type: ignore (wtf?)

        frozen_exponents = frozenset(exponents.items())

        try:
            return QUANTITY_ALIASES_BY_EXPONENTS[frozen_exponents]
        except KeyError:
            pass

        alias = QuantityAlias(cls, quantity_caps, exponents)

        QUANTITY_ALIASES_BY_EXPONENTS[frozen_exponents] = alias
        return alias

    if not t.TYPE_CHECKING:
        __class_getitem__ = __class_getitem

    @t.overload
    def __init__(self, value: t.Literal[0]): ...

    @t.overload
    def __init__(self, value: float, unit: u.Unit[Q_co]): ...

    def __init__(self, value: float, unit: u.Unit[Q_co] | None = None):
        # We actually can't implement the case with the optional unit here because `self` is a
        # `Quantity` instance and not a `QuantityAlias`. So `QuantityAlias.__call__` is responsible
        # for giving us a unit.
        if unit is None:
            raise TypeError("Creating an unparameterized `Quantity` requires a `unit`.")

        self._value = value
        self.unit = unit

    @property
    def quantity(self) -> type[Quantity[Q_co]]:
        """
        Returns the quantity that is being measured. For example `u.minutes(3).quantity` will return
        `u.Duration`.
        """
        return self.unit.quantity

    def to_number(self, unit: u.Unit[Q_co]) -> float:
        """
        Converts this measurement to a number in the given unit. For example:

        ```python
        >>> u.minutes(1).to_number(u.seconds)
        60
        ```
        """
        return self._value * (self.unit.multiplier / unit.multiplier)

    @classmethod
    def parse(cls, text: str, /) -> Quantity[Q_co]:
        """
        Parses a string containing a number followed by a unit.

        When this method is used directly on the `Quantity` class, any kind of quantity can be
        parsed. For example:

        ```python
        >>> u.Quantity.parse('5min')
        5 min
        >>> u.Quantity.parse('5 km')
        5 km
        ```

        But when this method is used on a specific quantity, only that quantity can be parsed. For
        example:

        ```python
        >>> u.Duration.parse('5min')
        5 min
        >>> u.Duration.parse('5 km')
        ValueError: Cannot parse '5 km' as a Duration
        ```
        """

        match = NUMBER_WITH_UNIT_REGEX.match(text)
        if not match:
            raise ValueError(f"Cannot parse {text!r} as a Quantity")

        number_str, unit_str = match.groups()

        number = float(number_str)
        if number.is_integer():
            number = int(number)

        try:
            unit = u.Unit.parse(unit_str, cls)
        except ValueError:
            raise ValueError(f"Cannot parse {text!r} as a {cls!r}")

        return cls(number, unit)

    @classmethod
    def typecheck(cls, value: Quantity, /) -> te.TypeGuard[Quantity[Q_co]]:
        """
        Checks whether the given measurement is measuring this quantity. It also acts as a
        `TypeGuard`:

        ```python
        def example(value: u.Quantity):
            if u.Distance.typecheck(value):
                print("It's a distance!")

                distance: u.Distance = value  # Ok, type checker doesn't complain
            else:
                print("It's not a distance.")
        """

        return cls.exponents == type(value).exponents

    def is_compatible_with(self, other: Quantity) -> te.TypeGuard[Quantity[Q_co]]:
        """
        Checks whether two values are measuring the same quantity. It also acts as a
        `TypeGuard`:

        ```python
        def example(value1: u.Quantity, value2: u.Quantity):
            if value1.is_compatible_with(value2):
                print(
                    "Now the type checker understands that these two values"
                    " have the same type, allowing us to do things like this:"
                )

                print(value1.to_number(value2.unit))
        ```
        """
        return self.quantity == other.quantity

    def __bool__(self) -> bool:
        return bool(self._value)

    def __float__(self) -> float:
        return float(self._value * self.unit.multiplier)

    def __neg__(self) -> Quantity[Q_co]:
        return Quantity(-self._value, self.unit)

    def __eq__(self, quantity: object, /) -> bool:
        if quantity == 0:
            num = self._value * self.unit.multiplier
            expected = 0
        elif not isinstance(quantity, __class__):
            return NotImplemented
        elif not self.is_compatible_with(quantity):
            return False
        else:
            num = self.to_number(quantity.unit)
            expected = quantity._value

        return math.isclose(num, expected)

    def __lt__(self, quantity: NullableQuantity[Q_co], /) -> bool:
        if quantity == 0:
            num = self._value * self.unit.multiplier
            expected = 0
        elif not isinstance(quantity, __class__):
            return NotImplemented
        elif not self.is_compatible_with(quantity):
            return False
        else:
            num = self.to_number(quantity.unit)
            expected = quantity._value

        return num < expected and not math.isclose(num, expected)

    def __le__(self, quantity: object, /) -> bool:
        if quantity == 0:
            num = self._value * self.unit.multiplier
            expected = 0
        elif not isinstance(quantity, __class__):
            return NotImplemented
        elif not self.is_compatible_with(quantity):
            return False
        else:
            num = self.to_number(quantity.unit)
            expected = quantity._value

        return num < expected or math.isclose(num, expected)

    def __gt__(self, quantity: object, /) -> bool:
        if quantity == 0:
            num = self._value * self.unit.multiplier
            expected = 0
        elif not isinstance(quantity, __class__):
            return NotImplemented
        elif not self.is_compatible_with(quantity):
            return False
        else:
            num = self.to_number(quantity.unit)
            expected = quantity._value

        return num > expected and not math.isclose(num, expected)

    def __ge__(self, quantity: object, /) -> bool:
        if quantity == 0:
            num = self._value * self.unit.multiplier
            expected = 0
        elif not isinstance(quantity, __class__):
            return NotImplemented
        elif not self.is_compatible_with(quantity):
            return False
        else:
            num = self.to_number(quantity.unit)
            expected = quantity._value

        return num > expected or math.isclose(num, expected)

    def __add__(self, quantity: NullableQuantity[Q_co], /) -> Quantity[Q_co]:
        if quantity == 0:
            return self

        return Quantity(
            self._value + quantity.to_number(self.unit),
            self.unit,
        )

    __radd__ = __add__

    def __sub__(self, quantity: NullableQuantity[Q_co], /) -> Quantity[Q_co]:
        if quantity == 0:
            return self

        return Quantity(
            self._value - quantity.to_number(self.unit),
            self.unit,
        )

    def __rsub__(self, zero: t.Literal[0], /) -> Quantity[Q_co]:
        assert zero == 0
        return Quantity(-self._value, self.unit)

    @t.overload
    def __mul__(self, number: float, /) -> Quantity[Q_co]: ...

    @t.overload
    def __mul__(self, quantity: Quantity[Q2], /) -> Quantity[MUL[Q_co, Q2]]: ...

    def __mul__(self, other: float | Quantity[Q2]) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(
                self._value * other._value,
                self.unit * other.unit,
            )
        else:
            return Quantity(self._value * other, self.unit)

    @t.overload
    def __truediv__(self, number: float, /) -> Quantity[Q_co]: ...

    @t.overload
    def __truediv__(self, quantity: Quantity[Q2], /) -> Quantity[DIV[Q_co, Q2]]: ...

    def __truediv__(self, other: float | Quantity[Q2]) -> Quantity:
        if isinstance(other, Quantity):
            return Quantity(
                self._value / other._value,
                self.unit / other.unit,
            )
        else:
            return Quantity(self._value / other, self.unit)

    @t.overload
    def __rtruediv__(self, number: float, /) -> Quantity[DIV[u.ONE, Q_co]]: ...

    @t.overload
    def __rtruediv__(self, quantity: Quantity[Q2], /) -> Quantity[DIV[Q2, Q_co]]: ...

    def __rtruediv__(self, other: t.Union[float, Quantity[Q2]]) -> Quantity[DIV]:
        if isinstance(other, Quantity):
            return Quantity(
                other._value / self._value,
                other.unit / self.unit,
            )
        else:
            return Quantity(
                other / self._value,
                u.one / self.unit,
            )

    def __repr__(self) -> str:
        return f"{self._value} {self.unit.symbol}"

    def __str__(self) -> str:
        value, unit = self._find_unit_for_str()

        if isinstance(value, int) or value.is_integer():
            value_str = str(int(value))
        else:
            value_str = format(value, ".1f")

        return f"{value_str} {unit.symbol}"

    def _find_unit_for_str(self) -> tuple[float, u.Unit[Q_co]]:
        value = self._value * self.unit.multiplier

        # Special case: If the value is 0, use the base unit
        if math.isclose(value, 0):
            return 0, self.unit.quantity.base_unit

        # We want to find a suitable (i.e. human-readable) representation of this quantity, which
        # means we want to output a "short" number (with few digits). This is a non-trivial problem.
        # We won't bother looking for a better representation if the current unit works well enough.
        digits, _, decimal_digits = str(self._value).partition(".")
        if len(digits.lstrip("-")) < 4 and len(decimal_digits) < 4:
            return self._value, self.unit

        return _find_most_suitable_unit(value, self.unit.quantity)


NullableQuantity = t.Union[Quantity[Q2], t.Literal[0]]


def _find_most_suitable_unit(value: float, quantity: type[Quantity]) -> tuple[float, u.Unit]:
    # Goal: Find the combination of units that results in the *shortest* (i.e. fewest digits)
    # number.
    #
    # This is essentially a knapsack problem, which doesn't really have an efficient algorithm.
    # Considering that this is only used for the `__str__` method, I don't want to burn too much
    # time on finding the optimal solution. A fast approximation will have to do.

    # TODO: Maybe we could pre-compute some kind of acceleration structure? Like "For values between
    # 0 and 999, use meters. Upwards of 1000, use kilometers". I'm afraid the structure might get
    # very large if multiple units and prefixes are involved, though.

    # We'll use a greedy algorithm. We'll assume that there's always a unit with a factor of 1, so
    # we don't need to plan ahead. We'll start with the largest exponent, pick the largest possible
    # unit, and if that's not enough, add a prefix as well. Then we'll move on to the next
    # dimension.

    # First, find out which units exist for this quantity. If there is a dedicated unit, like there
    # is Coloumbs for DURATION*ELECTRIC_CURRENT, we'll use that.
    if quantity.units:
        unit = _find_most_suitable_unit_and_prefix(value, quantity.units)
        value /= unit.multiplier
    else:
        unit = u.one

        for quantity_caps, exponent in sorted(
            quantity.exponents.items(), key=lambda pair: pair[1], reverse=True
        ):
            best_unit = _find_most_suitable_unit_and_prefix(
                value, Quantity[quantity_caps].units, exponent
            )

            value /= best_unit.multiplier
            unit *= best_unit

    return value, unit


def _find_most_suitable_unit_and_prefix(
    value: float, sorted_units: t.Sequence[u.Unit], exponent: int = 1
) -> u.Unit:
    # Because prefixes cannot be applied to compound units (like m²), we can't just find a suitable
    # unit and then apply a prefix to it. We have to apply the prefix first, and then the exponent.

    unit = _find_most_suitable_multiplier(
        value,
        sorted_units,
        # Ignore the polarity of the exponent. Negative exponents will be prefixed with a `/`
        # symbol, which effectively makes them positive.
        abs(exponent),
    )

    # There are a few situations where we'll try to add a prefix:
    # - The largest available unit was selected
    # - There is a huge gap between the selected unit and the next one, like meter and lightsecond.
    add_prefix = unit is sorted_units[-1]
    if not add_prefix:
        selected_index = sorted_units.index(unit)
        try:
            next_unit = sorted_units[selected_index + 1]
        except IndexError:
            pass
        else:
            add_prefix = next_unit.multiplier / unit.multiplier > 1000

    if add_prefix:
        prefixes = list(unit.quantity.prefixes)
        prefixes.append(u.prefixes.DUMMY_PREFIX)

        unit = _find_most_suitable_multiplier(
            value, [prefix(unit) for prefix in prefixes], exponent
        )

    return unit**exponent


T = t.TypeVar("T", "u.Unit", "u.Prefix")


def _find_most_suitable_multiplier(value: float, things: t.Iterable[T], exponent: int = 1) -> T:
    candidates = [thing for thing in things if thing.multiplier**exponent <= value]

    if candidates:
        return max(candidates, key=lambda thing: thing.multiplier)
    else:
        return min(things, key=lambda thing: thing.multiplier)
