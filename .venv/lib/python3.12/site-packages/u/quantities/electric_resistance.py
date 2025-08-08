import typing as t

from .distance import DISTANCE, m
from .duration import DURATION, s
from .electric_current import ELECTRIC_CURRENT, A
from .mass import MASS, kg
from ..quantity import Quantity
from ..capital_quantities import MUL, DIV, SQUARE, CUBE
from ..unit import Unit


# fmt: off
__all__ = [
    "ELECTRIC_RESISTANCE", "ElectricResistance",
    "ohms", "ohm",
]
# fmt: on


ELECTRIC_RESISTANCE = t.Union[
    DIV[DIV[MUL[MASS, SQUARE[DISTANCE]], CUBE[DURATION]], SQUARE[ELECTRIC_CURRENT]],
]  # FIXME: Add missing formulas

ElectricResistance = Quantity[ELECTRIC_RESISTANCE]

ohms = ohm = Unit(kg * m**2 / s**3 / A**2, "Ω")
