from .data_volume import DATA_VOLUME, bytes, kilobytes, megabytes, gigabytes, terabytes
from .duration import DURATION, second
from ..quantity import Quantity
from ..capital_quantities import DIV


# fmt: off
__all__ = [
    "DATA_TRANSFER_SPEED",
    "DataTransferSpeed",
    "bytes_per_second", "Bps",
    "kilobytes_per_second", "KBps",
    "megabytes_per_second", "MBps",
    "gigabytes_per_second", "GBps",
    "terabytes_per_second", "TBps",
]
# fmt: on


DATA_TRANSFER_SPEED = DIV[DATA_VOLUME, DURATION]

DataTransferSpeed = Quantity[DATA_TRANSFER_SPEED]

bytes_per_second = Bps = bytes / second
kilobytes_per_second = KBps = kilobytes / second
megabytes_per_second = MBps = megabytes / second
gigabytes_per_second = GBps = gigabytes / second
terabytes_per_second = TBps = terabytes / second
