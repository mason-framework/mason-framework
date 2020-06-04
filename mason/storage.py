"""Defines a storage system for loading and saving blueprint."""

import abc
from typing import Sequence, Tuple, List
from mason import node


class StorageDriver(abc.ABC):
    """Abstract storage driver."""

    @abc.abstractmethod
    async def load_blueprint(self, path: str) -> node.Blueprint:
        """Loads a blueprint from the given path."""

    @abc.abstractmethod
    async def save_blueprint(self, path: str, blueprint: node.Blueprint):
        """Saves a blueprint to the given path."""

    @abc.abstractmethod
    async def list_blueprints(self) -> Sequence[str]:
        """Walks tree of options."""



class Storage:
    """Storage system."""

    def __init__(self, driver: StorageDriver):
        self.driver = driver

    async def load_blueprint(self, path: str) -> node.Blueprint:
        """Loads a blueprint from the given path."""
        return await self.driver.load_blueprint(path)

    async def list_blueprints(self) -> Sequence[str]:
        """List all available blueprints."""
        return await self.driver.list_blueprints()

    async def save_blueprint(self, path: str, blueprint: node.Blueprint):
        """Saves a blueprint to the given path."""
        return await self.driver.save_blueprint(path, blueprint)
