"""Defines exception classes for the mason framework."""
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mason import port


class MasonError(Exception):
    """Base error for all Mason exceptions."""


class FlowException(Exception):
    """Base exception to signal the exit of a flow."""


class ExitException(FlowException):
    """Exception to exit a flow with a code."""

    def __init__(self, code: int, message: str = ''):
        self.code = code
        super().__init__(message)


class ReturnException(FlowException):
    """Exception to return a value from the flow."""

    def __init__(self, value: Any):
        self.value = value
        super().__init__()


class InvalidConnectionError(MasonError):
    """Raised when two ports cannot connect to one another."""

    def __init__(self, a: 'port.Port', b: 'port.Port'):
        super().__init__(f'Cannot connect {a.name} to {b.name}.')


class PathNotFoundError(MasonError):
    """Raised when unable to load a storage item."""

    def __init__(self, path: str):
        super().__init__(f'Cannot find path: {path}')


class UnknownFormatError(MasonError):
    """Raised when loading an unknown file format."""

    def __init__(self, ext: str):
        super().__init__(f'Uknown format: {ext}')
