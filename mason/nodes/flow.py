"""Define flow control nodes."""

import asyncio
from typing import Any, Sequence

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



class For(mason.Node):
    """Defines a For Loop node."""

    start: int = 0
    stop: int = 10
    interval: int = 1

    index: mason.outport(int)

    index_changed: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)

        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Implement internal run function."""
        self._cancelled.clear()
        start, stop, interval = await self.gather('start', 'stop', 'interval')
        for i in range(start, stop, interval):
            self.ports['index'].local_value = i
            await self.emit('index_changed')
            if self._cancelled.is_set():
                await self.emit('cancelled')
                break
        else:
            await self.emit('finished')

    @mason.slot
    async def cancel(self):
        """Cancels the loop."""
        self._cancelled.set()


class Iterate(mason.Node):
    """Iterate over a set of items."""

    items: mason.inport(Sequence[Any])
    item: mason.outport(Any)

    item_changed: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)
        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Implement internal iteration logic."""
        self._cancelled.clear()
        items = await self.get('items')
        for item in items:
            self.ports['item'].local_value = item
            await self.emit('item_changed')
            if self._cancelled.is_set():
                await self.emit('cancelled')
                break
        else:
            await self.emit('finished')


class Enumerate(mason.Node):
    """Iterate over a set of items."""

    items: Sequence[Any]
    index: mason.outport(int)
    item: mason.outport(Any)

    item_changed: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)
        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Implement internal iteration logic."""
        self._cancelled.clear()
        items = await self.get('items')
        for index, item in enumerate(items):
            self.ports['index'].local_value = index
            self.ports['item'].local_value = item
            await self.emit('item_changed')
            if self._cancelled.is_set():
                await self.emit('cancelled')
                break
        else:
            await self.emit('finished')


class Merge(mason.Node):
    """Wait for all connections before continuing."""

    merged: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)
        self._counter = 0

    async def setup(self):
        """Initialize counter to 0."""
        self._counter = 0

    @mason.slot
    async def continue_(self):
        """Emits finished when all tasks are complete."""
        self._counter += 1
        if self._counter == getattr(self.continue_, 'connection_count', 0):
            await self.emit('merged')
            self._counter = 0


class While(mason.Node):
    """While loop node."""

    condition: Any

    triggered: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)

        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Perform while loop."""
        self._cancelled.clear()
        while await self.get('condition'):
            await self.emit('triggered')
            if self._cancelled.is_set():
                await self.emit('cancelled')
                break
        else:
            await self.emit('finished')

    @mason.slot
    async def cancel(self):
        """Cancels the while loop."""
        self._cancelled.set()


class If(mason.Node):
    """Control logic for if/else checks."""

    condition: Any

    passed: mason.Signal
    failed: mason.Signal

    @mason.slot
    async def check(self):
        """Checks whether or not the condition is true and emits signals."""
        if await self.get('condition'):
            await self.emit('passed')
        else:
            await self.emit('failed')


@mason.nodify
@mason.slot
async def sleep(seconds: float = 1, finished: mason.Signal = None):
    """Control node for sleeping."""
    await asyncio.sleep(seconds)
    if finished:
        await finished.emit()
