from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit

__all__ = ["TEMPERATURE", "Temperature", "kelvins", "kelvin", "K"]


class TEMPERATURE(QUANTITY):
    pass


Temperature = Quantity[TEMPERATURE]


kelvins = kelvin = K = Unit(Temperature, "K", 1)

# TODO: Celsius and Fahrenheit aren't compatible with the current design, since 0 doesn't mean
# "nothing".

# celsius = C = Unit(Temperature, "°C", offset=273.15)
# fahrenheit = F = Unit(Temperature, "°F", formula=((BASE_UNIT - 273.15) * 1.8) + 32)
