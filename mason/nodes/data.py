"""Defines data nodes."""
from typing import Any, Optional


import mason


@mason.nodify
def const(default: Any) -> Any:
    """Returns the constant value."""
    return default


class Get(mason.Node):
    """Gets a valu from the execution context state."""

    key: Optional[str] = None
    default: Any = None

    value: mason.outport(Any)

    def __init__(self, **props):
        super().__init__(**props)
        self.ports['value'].getter = self.get_value

    async def get_value(self) -> Any:
        """Returns the value from the context."""
        key, default = await self.gather('key', 'default')
        context = self.get_context()
        if context:
            return context.state.get(key or self.name, default)
        return default


class Set(mason.Node):
    """Sets a value in the execution context state."""

    key: Optional[str] = None
    value: Any = None

    @mason.slot
    async def store(self):
        """Stores the value at the current time to the context state."""
        key, value = await self.gather('key', 'value')
        context = self.get_context()
        if context:
            context.state[key or self.name] = value
