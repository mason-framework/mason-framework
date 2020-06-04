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

    @mason.getter('value')
    async def get_value(self) -> Any:
        """Extracts the value for the given output port from the context."""
        key, default = await self.gather('key', 'default')
        if key is None:
            key = self._label or self.uid
        context = self.get_context()
        return context.args.get(key, default) if context else default


class Output(mason.Node):
    """Defines a node to add output values to the context."""

    key: str
    value: Any

    assigned: mason.Signal

    @mason.slot
    async def assign(self):
        """Assigns the value for this node to the context."""
        key, value = await self.gather('key', 'value')
        if key is None:
            key = self._label or self.uid
        context = self.get_context()
        context.results[key] = value
        await self.emit('assigned')


class Emit(mason.Node):
    """Emits a blueprint signal."""

    event: str

    @mason.slot
    async def emit(self):
        """Emits the signal through the blueprint for this node."""
        ev = await self.get('event')
        await self.blueprint.emit(ev)


class On(mason.Node):
    """Triggers when a blueprint signal is emitted."""

    event: str = 'on_run'
    triggered: mason.Signal

    async def setup(self):
        ev = await self.get('event')
        self.blueprint.signals[ev].connect(self.run)

    async def run(self):
        """Triggers when the blueprints signal is emitted."""
        # Because this is not a slot, we'll want to use its own
        # context manually here.
        with self:
            await self.emit('triggered')

    async def teardown(self):
        ev = await self.get('event')
        self.blueprint.signals[ev].disconnect(self.run)
