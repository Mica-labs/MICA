import typing as t

from .distance import DISTANCE, m
from .duration import DURATION, s
from .mass import MASS, kg
from ..quantity import Quantity
from ..capital_quantities import DIV, MUL, SQUARE
from ..unit import Unit


# fmt: off
__all__ = [
    "FORCE",
    "Force",
    "newtons", "newton", "N",
]
# fmt: on

FORCE = t.Union[
    DIV[MUL[MASS, DISTANCE], SQUARE[DURATION]],
    DIV[DIV[MUL[MASS, DISTANCE], DURATION], DURATION],
    MUL[MASS, DIV[DISTANCE, SQUARE[DURATION]]],
    MUL[MASS, DIV[DIV[DISTANCE, DURATION], DURATION]],
    MUL[DISTANCE, DIV[MASS, SQUARE[DURATION]]],
    MUL[DISTANCE, DIV[DIV[MASS, DURATION], DURATION]],
    MUL[DIV[MASS, DURATION], DIV[DISTANCE, DURATION]],
]


Force = Quantity[FORCE]


newtons = newton = N = Unit(kg * m / s / s, "N")
