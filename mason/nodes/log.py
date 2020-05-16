"""Define logging nodes."""
import logging
from typing import Any, Optional

import mason


class Print(mason.Node):
    """Prints out a message."""

    message: Optional[Any] = None

    @mason.slot
    async def print_(self):
        """Prints current message."""
        print(await self.get('message'))


class Log(mason.Node):
    """Logs out to the base python logger."""

    name: str = 'root'
    level: str = 'INFO'
    message: Any = None

    @mason.slot
    async def log(self):
        """Logs to the logger."""
        name, level, message = await self.gather('name', 'level', 'message')
        log_level = getattr(logging, level)
        logger = logging.getLogger(name)
        logger.log(log_level, message)
