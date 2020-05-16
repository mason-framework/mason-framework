"""Defines logical nodes."""
import enum
from typing import Any

import mason

class Operator(enum.Enum):
    """Defines comparison operation options."""

    Equal = '=='
    NotEqual = '!='
    LessThan = '<'
    LessThanOrEqual = '<='
    GreaterThan = '>'
    GreaterThanOrEqual = '>='


@mason.nodify
def compare(a: Any, b: Any, op: Operator = Operator.Equal) -> bool:
    """Define a node that compares a to b given the operator."""
    if op == Operator.Equal:
        return a == b
    if op == Operator.NotEqual:
        return a != b
    if op == Operator.LessThan:
        return a < b
    if op == Operator.LessThanOrEqual:
        return a <= b
    if op == Operator.GreaterThan:
        return a > b
    if op == Operator.GreaterThanOrEqual:
        return a >= b
    raise RuntimeError(f'Ivalid operation: {op}')

compare.__node__.__schema__.ports['op'].choices = [
    op.value for op in Operator.__members__.values()]


@mason.nodify
def nonzero(a: Any) -> bool:
    """Returns whether or not the item is empty."""
    return bool(a)
