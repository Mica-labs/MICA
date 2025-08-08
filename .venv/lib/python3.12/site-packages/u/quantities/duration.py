from ..prefixes import SI_PREFIXES, milli
from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


# fmt: off
__all__ = [
    "DURATION",
    "Duration",
    "seconds", "second", "sec", "s",
    "minutes", "minute", "min",
    "hours", "hour", "h",
    "days", "day", "d",
    "weeks", "week", "wk", "w",
    "years", "year", "yr", "y",
    "decades", "decade", "dec",
    "centuries", "century", "cent", "c",
    "millenia", "millenium", "mil", "ka", "ky",
]
# fmt: on


class DURATION(QUANTITY):
    pass


Duration = Quantity[DURATION]
Duration.prefixes = SI_PREFIXES[: SI_PREFIXES.index(milli) + 1]


seconds = second = sec = s = Unit(Duration, "s", 1)
minutes = minute = min = Unit(Duration, "min", 60)
hours = hour = h = Unit(Duration, "h", 3_600)
days = day = d = Unit(Duration, "d", 86_400)
weeks = week = wk = w = Unit(Duration, "wk", 86_400)
years = year = yr = y = Unit(Duration, "yr", 31_557_600)
decades = decade = dec = Unit(Duration, "dec", 315_576_000)
centuries = century = cent = c = Unit(Duration, "cent", 3_155_760_000)
millenia = millenium = mil = ka = ky = Unit(Duration, "mil", 31_557_600_000)
