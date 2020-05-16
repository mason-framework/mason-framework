"""Define dynamic math functions."""

import math
import functools
import mason

math_node = functools.partial(mason.nodify, result_name='value')

@math_node
def add(a: float, b: float) -> float:  # pylint: disable=C0103
    """Return the result of adding a and b."""
    return a + b

@math_node
def sub(a: float, b: float) -> float:  # pylint: disable=C0103
    """Return the result of subtracting b from a."""
    return a - b

@math_node
def mult(a: float, b: float) -> float:  # pylint: disable=C0103
    """Return the product of multiplication of a and b."""
    return a * b

@math_node
def div(dividend: float, divisor: float) -> float:
    """Return the result of division of the dividend by the divisor."""
    return dividend / divisor

@math_node
def neg(number: float) -> float:
    """Return the negative of number."""
    return number * -1

@math_node
def pow_(base: float, exponent: float = 2) -> float:  # pylint: disable=C0103
    """Return the exponentiation of base by exponent."""
    return base ** exponent

@math_node
def sqrt(number: float) -> float:
    """Return the square root of number."""
    return math.sqrt(number)
