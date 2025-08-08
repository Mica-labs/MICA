from __future__ import annotations

import typing as t


__all__ = ["QUANTITY", "MUL", "DIV", "SQUARE", "CUBE", "TESSERACT"]


class QUANTITY:
    pass


Q = t.TypeVar("Q", bound=QUANTITY)
Q1 = t.TypeVar("Q1", bound=QUANTITY, covariant=True)
Q2 = t.TypeVar("Q2", bound=QUANTITY, covariant=True)


class MUL_(t.Generic[Q1, Q2], QUANTITY): ...


class DIV(t.Generic[Q1, Q2], QUANTITY): ...


MUL = t.Union[MUL_[Q1, Q2], MUL_[Q2, Q1]]
SQUARE = MUL_[Q, Q]
CUBE = MUL[Q, SQUARE[Q]]
TESSERACT = t.Union[MUL_[SQUARE[Q], SQUARE[Q]], MUL[MUL[SQUARE[Q], Q], Q]]
