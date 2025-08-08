import typing as t

from ..quantity import Quantity
from ..capital_quantities import DIV, SQUARE
from .distance import DISTANCE, meters, kilometers
from .duration import DURATION, second, hour
from .speed import SPEED


# fmt: off
__all__ = [
    "ACCELERATION",
    "Acceleration",
    "meters_per_second_squared", "mps2",
    "kilometers_per_hour_squared", "kph2",
]
# fmt: on


ACCELERATION = t.Union[
    DIV[SPEED, DURATION],
    DIV[DISTANCE, SQUARE[DURATION]],
]

Acceleration = Quantity[ACCELERATION]

meters_per_second_squared = mps2 = meters / (second**2)
kilometers_per_hour_squared = kph2 = kilometers / (hour**2)
