from .distance import DISTANCE, meters, kilometers
from .duration import DURATION, seconds, hours
from ..quantity import Quantity
from ..capital_quantities import DIV


__all__ = ["SPEED", "Speed", "meters_per_second", "mps", "kilometers_per_hour", "kph"]


SPEED = DIV[DISTANCE, DURATION]

Speed = Quantity[SPEED]

meters_per_second = mps = meters / seconds
kilometers_per_hour = kph = kilometers / hours
