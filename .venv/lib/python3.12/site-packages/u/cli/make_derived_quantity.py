import sys
from typing import Mapping

from u._utils import parse_symbol


def main() -> None:
    equation = "".join(sys.argv[1:])
    exponents = parse_symbol(equation)
    print(exponents)
