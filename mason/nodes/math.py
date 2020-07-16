"""Define dynamic math functions."""

import math
import functools
from typing import Any

import mason

math_node = functools.partial(
    mason.nodify,
    result_name='value',
    shape=mason.NodeShape.Round,
)


@math_node(default_label='x')
def const(x: Any) -> Any:
    """Returns the constant value of x."""
    return x


@math_node(default_label='x+y')
def add(x: float, y: float) -> float:
    """Return the result of adding x and y."""
    return x + y

@math_node(default_label='x-y')
def sub(x: float, y: float) -> float:
    """Return the result of subtracting y from x."""
    return x - y

@math_node(default_label='x*y')
def mult(x: float, y: float) -> float:
    """Return the product of multiplication of x and y."""
    return x * y

@math_node(default_label='x/y')
def div(x: float, y: float) -> float:
    """Return the result of division of x by y."""
    return x / y

@math_node(default_label='-x')
def neg(x: float) -> float:
    """Return the negative of x."""
    return -x

@math_node(default_label='x^y')
def pow_(x: float, y: float = 2) -> float:
    """Return the exponentiation of x by y."""
    return x ** y

@math_node(default_label='√(x)')
def sqrt(x: float) -> float:
    """Return the square root of x."""
    return math.sqrt(x)
