"""Defines action middleware for the mason framework."""

import contextlib
from typing import List, Callable
from mason import events

Dispatcher = Callable[..., None]
DispatchHandler = Callable[[events.Event, Dispatcher], None]


class Middleware:
    """Middleware management."""

    def __init__(self, handlers: List[DispatchHandler] = None):
        self._handlers = handlers

    def add_handler(self, handler: DispatchHandler):
        """Adds a new handler to the middleware."""
        self._handlers.append(handler)

    def dispatch(self, event: events.Event):
        """Dispatches an event through the middleware."""
        iter_ = iter(self._handlers)
        def next_():
            try:
                handler = next(iter_)
            except StopIteration:
                pass
            else:
                handler(event, next_)
        next_()

    @contextlib.contextmanager
    def with_handler(self, handler: DispatchHandler):
        """Return middleware with a handler."""
        self._handlers.append(handler)
        yield self
        self._handlers.remove(self._handlers.index(handler))
