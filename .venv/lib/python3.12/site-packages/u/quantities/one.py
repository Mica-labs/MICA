from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit

__all__ = ["ONE", "One", "ones", "one"]


class ONE(QUANTITY):
    """
    Represents the absence of a quantity. Used to create "inverted" quantities like `FREQUENCY =
    DIV[ONE, DURATION]`.
    """


One = Quantity[ONE]


ones = one = Unit(One, "1", 1)
