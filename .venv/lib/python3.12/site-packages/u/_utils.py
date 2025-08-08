from __future__ import annotations

import collections.abc
import functools
import re
import sys
import types
import typing as t

import u


C = t.TypeVar("C", bound=t.Callable)


if sys.version_info >= (3, 10):
    UNION_TYPES = (t.Union, types.UnionType)
else:
    UNION_TYPES = (t.Union,)


def is_union(obj: object) -> bool:
    return t.get_origin(obj) in UNION_TYPES


def cached(func: C) -> C:
    cache = {}

    @functools.wraps(func)
    def wrapper(*args):
        try:
            return cache[args]
        except KeyError:
            pass

        result = cache[args] = func(*args)
        return result

    return wrapper  # type: ignore


SYMBOL_REGEX = re.compile(r"(^|[*/])([^*/]+?)([⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹]*)\s*(?=[*/]|$)")


def parse_symbol(symbol: str) -> t.Counter[str]:
    """
    Parses a symbol into a Counter of exponents.

    ```
    >>> parse_symbol('1/s²')
    Counter({'1': 1, 's': -2})
    ```
    """
    result = collections.Counter()

    for op, sym, power in SYMBOL_REGEX.findall(symbol):
        multiplier = -1 if op == "/" else 1
        result[sym.strip()] += multiplier * parse_exponent(power)

    return result


POW_TO_NUM = str.maketrans("⁻⁺⁰¹²³⁴⁵⁶⁷⁸⁹", "-+0123456789")
NUM_TO_POW = {value: key for key, value in POW_TO_NUM.items()}


def parse_exponent(exp: str) -> int:
    if not exp:
        return 1

    return int(exp.translate(POW_TO_NUM))


def str_exponent(exp: int) -> str:
    if exp == 1:
        return ""

    return str(exp).translate(NUM_TO_POW)


def join_symbols(symbol1: str, symbol2: str, operator: str) -> str:
    powers1 = parse_symbol(symbol1)

    powers2 = parse_symbol(symbol2)
    if operator == "/":
        powers2 = {symbol: -exponent for symbol, exponent in powers2.items()}

    powers1.update(powers2)
    powers1.pop("1", None)

    # Find the first symbol with a positive exponent
    segments = []

    for symbol, exponent in powers1.items():
        if exponent > 0:
            del powers1[symbol]
            segments.append(f"{symbol}{str_exponent(exponent)}")
            break
    else:
        segments.append("1")

    # Add the remaining symbols
    for symbol, exponent in powers1.items():
        segments += [
            "*" if exponent > 0 else "/",
            symbol,
            str_exponent(abs(exponent)),
        ]

    return "".join(segments)


class ExponentDict(collections.abc.Mapping[type["u.QUANTITY"], int]):
    def __init__(self, exponents: t.Mapping[type[u.QUANTITY], int]):
        # We're converting to a dict for 2 reasons:
        # 1. Makes implementing `__repr__` trivial
        # 2. If it's a defaultdict, we don't have to worry about accidentally mutating it
        self._exponents = dict(exponents)

    def __getitem__(self, quantity: type[u.QUANTITY]) -> int:
        return self._exponents.get(quantity, 0)

    def __iter__(self) -> t.Iterator[type[u.QUANTITY]]:
        return iter(self._exponents)

    def __len__(self) -> int:
        return len(self._exponents)

    def __hash__(self) -> int:
        return hash(tuple(self.items()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, __class__):
            return NotImplemented

        return self._exponents == other._exponents

    def __repr__(self) -> str:
        return repr(self._exponents)
