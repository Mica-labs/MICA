# fmt: off
from ..prefixes import (
    kilo, mega, giga, tera, peta, exa, zetta, yotta,
    kibi, mebi, gibi, tebi, pebi, exbi, zebi, yobi,
)
# fmt: on
from ..quantity import Quantity
from ..capital_quantities import QUANTITY
from ..unit import Unit


# fmt: off
__all__ = [
    "DATA_VOLUME",
    "DataVolume",
    "bytes", "byte", "B",
    "megabytes", "megabyte", "MB",
    "gigabytes", "gigabyte", "GB",
    "terabytes", "terabyte", "TB",
    "petabytes", "petabyte", "PB",
    "exabytes", "exabyte", "EB",
    "zettabytes", "zettabyte", "ZB",
    "yottabytes", "yottabyte", "YB",
    "kibibytes", "kibibyte", "kiB",
    "mebibytes", "mebibyte", "MiB",
    "gibibytes", "gibibyte", "GiB",
    "tebibytes", "tebibyte", "TiB",
    "pebibytes", "pebibyte", "PiB",
    "exbibytes", "exbibyte", "EiB",
    "zebibytes", "zebibyte", "ZiB",
    "yobibytes", "yobibyte", "YiB",
]
# fmt: on


class DATA_VOLUME(QUANTITY):
    pass


DataVolume = Quantity[DATA_VOLUME]


# TODO: Bits don't really fit in here. I initially wanted to define a byte as 8 bits, but that's not
# true - 8 bits is an octet. Bytes don't have a fixed amount of bits.
# bits = bit = b = Unit(FileSize, 'b', 1)

bytes = byte = B = Unit(DataVolume, "B", 1)

kilobytes = kilobyte = kB = kilo(bytes)
megabytes = megabyte = MB = mega(bytes)
gigabytes = gigabyte = GB = giga(bytes)
terabytes = terabyte = TB = tera(bytes)
petabytes = petabyte = PB = peta(bytes)
exabytes = exabyte = EB = exa(bytes)
zettabytes = zettabyte = ZB = zetta(bytes)
yottabytes = yottabyte = YB = yotta(bytes)

kibibytes = kibibyte = kiB = kibi(bytes)
mebibytes = mebibyte = MiB = mebi(bytes)
gibibytes = gibibyte = GiB = gibi(bytes)
tebibytes = tebibyte = TiB = tebi(bytes)
pebibytes = pebibyte = PiB = pebi(bytes)
exbibytes = exbibyte = EiB = exbi(bytes)
zebibytes = zebibyte = ZiB = zebi(bytes)
yobibytes = yobibyte = YiB = yobi(bytes)
