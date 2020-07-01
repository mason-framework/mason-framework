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

    __shape__ = mason.NodeShape.Round

    default: mason.inport(Any, visibility=mason.PortVisibility.Editable)
    value: mason.outport(Any)

    @mason.getter('value')
    def get_value(self) -> Any:
        """Extracts the value for the given output port from the context."""
        key = self._label or self.uid
        default = self.get('default')
        context = self.get_context()
        return context.args.get(key, default) if context else default


class Output(mason.Node):
    """Defines a node to add output values to the context."""

    name: str
    value: Any

    assigned: mason.Signal

    @mason.slot
    async def assign(self):
        """Assigns the value for this node to the context."""
        name, value = self.get('key', 'value')
        context = self.get_context()
        context.results[name] = value
        await self.emit('assigned')


class Emit(mason.Node):
    """Emits a blueprint signal."""

    event: str

    @mason.slot
    async def emit(self):
        """Emits the signal through the blueprint for this node."""
        ev = self.get('event')
        await self.blueprint.emit(ev)


class On(mason.Node):
    """Triggers when a blueprint signal is emitted."""

    __shape__ = mason.NodeShape.Round

    event: mason.inport(
        str,
        default='on_run',
        visibility=mason.PortVisibility.Editable)
    triggered: mason.Signal

    async def setup(self):
        ev = self.get('event')
        self.blueprint.signals[ev].connect(self.run)

    async def run(self):
        """Triggers when the blueprints signal is emitted."""
        # Because this is not a slot, we'll want to use its own
        # context manually here.
        with self:
            await self.emit('triggered')

    async def teardown(self):
        ev = self.get('event')
        self.blueprint.signals[ev].disconnect(self.run)
