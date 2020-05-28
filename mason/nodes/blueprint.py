"""Blueprint nodes."""

from typing import Any

import mason


@mason.nodify
@mason.slot
def return_(value: Any = None):
    """Raises the value as a return."""
    raise mason.exceptions.ReturnException(value)


@mason.nodify
@mason.slot
def exit_(code: int = 0):
    """Raises the exit exception."""
    raise mason.exceptions.ExitException(code)


class Input(mason.Node):
    """Defines a node to extract an input variable from a flow."""

    key: str
    default: Any
    value: mason.outport(Any)

    def __init__(self, **args):
        super().__init__(**args)

        self.ports['value'].getter = self.get_value

    async def get_value(self) -> Any:
        """Extracts the value for the given output port from the context."""
        key, default = await self.gather('key', 'default')
        if not key:
            key = self.name
        context = self.get_context()
        return context.args.get(key, default) if context else default


class TriggerEvent(mason.Node):
    """Emits a blueprint signal."""

    event: str

    @mason.slot
    async def trigger(self):
        """Emits the signal through the blueprint for this node."""
        ev = await self.get('event')
        self.blueprint.emit(ev)


class OnEvent(mason.Node):
    """Triggers when a blueprint signal is emitted."""

    event: str = 'triggered'
    triggered: mason.Signal

    async def setup(self):
        ev = await self.get('event')
        self.blueprint.connect(ev, self.run)

    async def run(self):
        """Triggers when the blueprints signal is emitted."""
        self.triggered.emit()

    async def teardown(self):
        ev = await self.get('event')
        self.blueprint.disconnect(ev, self.run)
