"""Define flow control nodes."""

import asyncio
import logging
from typing import Any, Sequence

import mason


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


class Get(mason.Node):
    """Gets a valu from the execution context state."""

    key: str
    default: Any

    value: mason.outport(Any)

    @mason.getter('value')
    async def get_value(self) -> Any:
        """Returns the value from the context."""
        key, default = await self.gather('key', 'default')
        context = self.get_context()
        if context:
            return context.state.get(key or self._label or self.uid, default)
        return default


class Set(mason.Node):
    """Sets a value in the execution context state."""

    key: str
    value: Any

    @mason.slot
    async def store(self):
        """Stores the value at the current time to the context state."""
        key, value = await self.gather('key', 'value')
        context = self.get_context()
        if context:
            context.state[key or self.label] = value


class Print(mason.Node):
    """Prints out a message."""

    message: Any
    printed: mason.Signal

    @mason.slot
    async def print_(self):
        """Prints current message."""
        print(await self.get('message'))
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
        logger_name, level, message = await self.gather(
            'logger', 'level', 'message')
        log_level = getattr(logging, level)
        logger = logging.getLogger(logger_name)
        logger.log(log_level, message)
        await self.emit('logged')
