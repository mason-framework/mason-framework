"""Define a generic callback system."""

import asyncio
import inspect
import types
from typing import Any, Callable, Optional, Set, Union, TypeVar
import weakref

CallbackType = Union[types.MethodType, Callable[..., Any]]
SlotType = TypeVar('SlotType')


class Signal:
    """Signal class type."""

    def __init__(self, *annotations):
        params = []
        for i, annotation in enumerate(annotations):
            params.append(
                inspect.Parameter(
                    f'arg_{i}',
                    inspect.Parameter.POSITIONAL_ONLY,
                    annotation=annotation
                )
            )
        self._annotations = annotations
        self._signature = inspect.Signature(params)
        self._slot_refs = set()

    def _cleanup_dead_refs(self) -> None:
        """Clean out dead references."""
        self._slot_refs = {ref for ref in self._slot_refs if ref()}

    def _get_active_slots(self) -> Set[CallbackType]:
        """Cleans out dead references and returns active callbacks."""
        self._cleanup_dead_refs()
        return {ref() for ref in self._slot_refs}

    def _validate_slot_signature(self, func: CallbackType) -> None:
        """Ensures that the signature of the slot function matches the signal.

        This method will iterate over the annotations for the Signal and compare
        them against the function signature for the callback slot.  If the type
        annotations do not match, a TypeError is raised.

        Args:
            func: Callable object with type annotations.

        Raises:
            TypeError if the signatures are not compatible.
        """
        signature = inspect.signature(func)
        if len(self._annotations) <= len(signature.parameters):
            for i, param in enumerate(signature.parameters.values()):
                actual = param.annotation
                try:
                    expected = self._annotations[i]
                except IndexError:
                    if (param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
                            and param.default == inspect.Parameter.empty):
                        break
                else:
                    # Check against the name to support type annotations of
                    # classes that are referenced before being defined.  See
                    # test case for example.
                    name = getattr(actual, '__name__', None)
                    if expected not in (actual, name):
                        break
            else:
                return

        raise TypeError('Failed to create connection.  Expected'
                        f'{self._annotations} but received {signature}.')

    def connect(self, *funcs: CallbackType) -> None:
        """Creates a connection by validating and adding the slot to the ref."""
        for func in funcs:
            self._validate_slot_signature(func)
            if getattr(func, 'is_slot', False) is True:
                func.__dict__.setdefault('connection_count', 0)
                func.__dict__['connection_count'] += 1
            if inspect.ismethod(func):
                ref = weakref.WeakMethod(func)
            else:
                ref = weakref.ref(func)
            self._slot_refs.add(ref)

    def disconnect(self, *funcs: Optional[CallbackType]) -> None:
        """Removes the slot (if provided) or all slot connections."""
        ignore = [None] + list(funcs)
        new_refs = set()
        for ref in self._slot_refs:
            func = ref()
            if func not in ignore:
                if getattr(func, 'is_slot', False) is True:
                    func.__dict__['connection_count'] -= 1
                continue
            new_refs.add(ref)
        self._slot_refs = new_refs

    async def emit(self, *args: Any) -> None:
        """Iterates over each active slot and calls them with the given values.

        Args:
            *args: Variable arguments to send to connected slot functions.

        Raises:
            TypeError if the provided arguments do not match the signature.
        """
        if self._signature.bind(*args):
            tasks = (func(*args) for func in self._get_active_slots())
            await asyncio.gather(*tasks)

    @property
    def is_empty(self) -> bool:
        """Cleans up dead references and returns if any active slots remain."""
        self._cleanup_dead_refs()
        return not self._slot_refs


def slot(func: SlotType) -> SlotType:
    """Decorate the function as a slot."""
    setattr(func, 'is_slot', True)
    setattr(func, 'connection_count', 0)
    return func
