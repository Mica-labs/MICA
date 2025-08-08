from __future__ import annotations

import typing as t

import u

from ._utils import cached

__all__ = [
    "Prefix",
    "STANDARD_SI_PREFIXES",
    "SI_PREFIXES",
    "BINARY_PREFIXES",
    "atto",
    "femto",
    "pico",
    "nano",
    "micro",
    "milli",
    "centi",
    "deci",
    "deka",
    "hecto",
    "kilo",
    "mega",
    "giga",
    "tera",
    "peta",
    "exa",
    "zetta",
    "yotta",
    "kibi",
    "mebi",
    "gibi",
    "tebi",
    "pebi",
    "exbi",
    "zebi",
    "yobi",
]


Q = t.TypeVar("Q", bound="u.QUANTITY")


prefix_by_symbol = dict[str, "Prefix"]()


class Prefix:
    def __init__(self, symbol: str, multiplier: float):
        self.symbol = symbol
        self.multiplier = multiplier

        prefix_by_symbol[symbol] = self

    @classmethod
    def from_symbol(cls, symbol: str) -> Prefix:
        try:
            return prefix_by_symbol[symbol]
        except KeyError:
            raise ValueError(f"The symbol {symbol!r} doesn't correspond to any Prefix")

    @cached
    def __call__(self, unit: u.Unit[Q]) -> u.Unit[Q]:
        if isinstance(unit, u.unit.UnregisteredUnit):
            raise ValueError("Prefixes cannot be applied to compound units") from None

        return u.unit.UnregisteredUnit(
            unit.quantity,
            self.symbol + unit.symbol,
            self.multiplier * unit.multiplier,
        )

    def __repr__(self) -> str:
        return f"<Prefix {self.symbol}>"


DUMMY_PREFIX = Prefix("", 1)


quecto = Prefix("q", 1e-30)
ronto = Prefix("r", 1e-27)
yocto = Prefix("y", 1e-24)
zepto = Prefix("z", 1e-21)
atto = Prefix("a", 1e-18)
femto = Prefix("f", 1e-15)
pico = Prefix("p", 1e-12)
nano = Prefix("n", 1e-9)
micro = Prefix("µ", 1e-6)
milli = Prefix("m", 1e-3)
centi = Prefix("c", 1e-2)
deci = Prefix("d", 1e-1)
deka = Prefix("da", 1e1)
hecto = Prefix("h", 1e2)
kilo = Prefix("k", 1e3)
mega = Prefix("M", 1e6)
giga = Prefix("G", 1e9)
tera = Prefix("T", 1e12)
peta = Prefix("P", 1e15)
exa = Prefix("E", 1e18)
zetta = Prefix("Z", 1e21)
yotta = Prefix("Y", 1e24)
ronna = Prefix("R", 1e27)
quetta = Prefix("Q", 1e30)


STANDARD_SI_PREFIXES = (
    quecto,
    ronto,
    yocto,
    zepto,
    atto,
    femto,
    pico,
    nano,
    micro,
    milli,
    kilo,
    mega,
    giga,
    tera,
    peta,
    exa,
    zetta,
    yotta,
    ronna,
    quetta,
)

SI_PREFIXES = (
    quecto,
    ronto,
    yocto,
    zepto,
    atto,
    femto,
    pico,
    nano,
    micro,
    milli,
    centi,
    deci,
    deka,
    hecto,
    kilo,
    mega,
    giga,
    tera,
    peta,
    exa,
    zetta,
    yotta,
    ronna,
    quetta,
)

kibi = Prefix("ki", 2**10)
mebi = Prefix("Mi", 2**20)
gibi = Prefix("Gi", 2**30)
tebi = Prefix("Ti", 2**40)
pebi = Prefix("Pi", 2**50)
exbi = Prefix("Ei", 2**60)
zebi = Prefix("Zi", 2**70)
yobi = Prefix("Yi", 2**80)

BINARY_PREFIXES = (kibi, mebi, gibi, tebi, pebi, exbi, zebi, yobi)
