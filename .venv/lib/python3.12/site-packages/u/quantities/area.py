from .distance import DISTANCE, meter, kilometer
from ..quantity import Quantity
from ..capital_quantities import MUL


# fmt: off
__all__ = [
    "AREA",
    "Area",
    "square_meters", "square_meter", "m2",
    "square_kilometers", "square_kilometer", "km2",
]
# fmt: on


AREA = MUL[DISTANCE, DISTANCE]

Area = Quantity[AREA]

square_meters = square_meter = m2 = meter**2
square_kilometers = square_kilometer = km2 = kilometer**2
