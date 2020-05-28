"""Define logging nodes."""
import logging
from typing import Any

import mason


class Print(mason.Node):
    """Prints out a message."""

    message: Any

    @mason.slot
    async def print_(self):
        """Prints current message."""
        print(await self.get('message'))


class Log(mason.Node):
    """Logs out to the base python logger."""

    name: str = 'root'
    level: mason.inport(
        str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
    )
    message: Any = None

    @mason.slot
    async def log(self):
        """Logs to the logger."""
        name, level, message = await self.gather('name', 'level', 'message')
        log_level = getattr(logging, level)
        logger = logging.getLogger(name)
        logger.log(log_level, message)
