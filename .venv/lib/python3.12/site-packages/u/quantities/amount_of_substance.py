from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


# fmt: off
__all__ = [
    "AMOUNT_OF_SUBSTANCE",
    "AmountOfSubstance",
    "moles", "mole", "mol",
]
# fmt: on


class AMOUNT_OF_SUBSTANCE(QUANTITY):
    pass


AmountOfSubstance = Quantity[AMOUNT_OF_SUBSTANCE]


moles = mole = mol = Unit(AmountOfSubstance, "mol", 1)
