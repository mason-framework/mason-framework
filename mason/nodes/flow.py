"""Define flow control nodes."""

import asyncio
import logging
from typing import Any, Sequence

import mason


class ForLoop(mason.Node):
    """Defines a For Loop node."""

    start: int = 0
    stop: int = 10
    interval: int = 1

    index: mason.outport(int)

    changed: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)

        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Implement internal run function."""
        self._cancelled.clear()
        start, stop, interval = self.get('start', 'stop', 'interval')
        for i in range(start, stop, interval):
            self.ports['index'].local_value = i
            await self.emit('changed')
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

    changed: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)
        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Implement internal iteration logic."""
        self._cancelled.clear()
        items = self.get('items')
        for item in items:
            self.ports['item'].local_value = item
            await self.emit('changed')
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

    changed: mason.Signal
    cancelled: mason.Signal
    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)
        self._cancelled = asyncio.Event()

    @mason.slot
    async def run(self):
        """Implement internal iteration logic."""
        self._cancelled.clear()
        items = self.get('items')
        for index, item in enumerate(items):
            self.ports['index'].local_value = index
            self.ports['item'].local_value = item
            await self.emit('changed')
            if self._cancelled.is_set():
                await self.emit('cancelled')
                break
        else:
            await self.emit('finished')


class WaitForAll(mason.Node):
    """Wait for all connections before continuing."""

    finished: mason.Signal

    def __init__(self, **props):
        super().__init__(**props)
        self._lock = asyncio.Lock()
        self._counter = 0
        self._total = 0

    async def setup(self):
        """Initialize counter to 0."""
        self._counter = 0
        self._total = self.slots['continue_'].connection_count

    @mason.slot
    async def continue_(self):
        """Emits finished when all tasks are complete."""
        is_finished = False
        async with self._lock:
            self._counter += 1
            is_finished = self._counter == self._total

            print('WaitForAll: counter:', self._counter, 'total:', self._total)
        if is_finished:
            await self.emit('finished')


class WhileLoop(mason.Node):
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
        while self.get('condition'):
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


class Branch(mason.Node):
    """Control logic for branching flows."""

    condition: Any

    on_true: mason.Signal
    on_false: mason.Signal

    @mason.slot
    async def check(self):
        """Checks whether or not the condition is true and emits signals."""
        if self.get('condition'):
            await self.emit('on_true')
        else:
            await self.emit('on_false')


@mason.nodify
@mason.slot
async def sleep(seconds: float = 1, finished: mason.Signal = None):
    """Control node for sleeping."""
    await asyncio.sleep(seconds)
    if finished:
        await finished.emit()


class Get(mason.Node):
    """Gets a valu from the execution context state."""

    key: str
    default: Any

    value: mason.outport(Any)

    @mason.getter('value')
    def get_value(self) -> Any:
        """Returns the value from the context."""
        key, default = self.get('key', 'default')
        context = self.get_context()
        if context:
            return context.state.get(key or self._label or self.uid, default)
        return default


class Set(mason.Node):
    """Sets a value in the execution context state."""

    key: str
    value: Any

    finished: mason.Signal

    @mason.slot
    async def store(self):
        """Stores the value at the current time to the context state."""
        key, value = self.get('key', 'value')
        context = self.get_context()
        if context:
            context.state[key or self.label] = value
        await self.emit('finished')


class Print(mason.Node):
    """Prints out a message."""

    message: Any
    printed: mason.Signal

    @mason.slot
    async def print_(self):
        """Prints current message."""
        print(self.get('message'))
        await self.emit('printed')


class Log(mason.Node):
    """Logs out to the base python logger."""

    logger: str = 'root'
    level: mason.inport(
        str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
    )
    message: Any = None
    logged: mason.Signal

    @mason.slot
    async def log(self):
        """Logs to the logger."""
        logger_name, level, message = self.get(
            'logger', 'level', 'message')
        log_level = getattr(logging, level)
        logger = logging.getLogger(logger_name)
        logger.log(log_level, message)
        await self.emit('logged')
