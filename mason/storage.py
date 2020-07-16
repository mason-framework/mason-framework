"""Defines a storage system for loading and saving blueprint."""

import abc
import os
from typing import Any, Optional, Dict, Sequence, Tuple

import attr
from mason import node
from mason import library as _lib
from mason import exceptions
from mason import io


@attr.s(auto_attribs=True)
class StorageItem:
    """Storage item interface."""

    path: str
    name: str
    type: str

    def asdict(self) -> Dict[str, Any]:
        """Serializes this item as a dictionary."""
        return {
            'path': self.path,
            'name': self.name,
            'type': self.type,
        }


@attr.s(auto_attribs=True)
class StorageDriver(abc.ABC):
    """Abstract storage driver."""

    default_format: str = io.DEFAULT_FORMAT
    valid_formats: Sequence[str] = tuple(io.SERIALIZERS.keys())

    def make_fullpath(
            self,
            group: str,
            name: str,
            extra_name: str,
            data_format: Optional[str]) -> str:
        """Create fullpath for the parameters."""
        data_format = data_format or self.default_format
        if extra_name:
            filename = f'{name}.{extra_name}.{data_format}'
        else:
            filename = f'{name}.{data_format}'
        return os.path.join(group, filename)

    def parse_fullpath(self, fullpath: str) -> Tuple[str, str, str, str]:
        """Returns the group, name and data format for the blueprint."""
        group, name = os.path.split(fullpath)
        name, data_format = os.path.splitext(name)
        if not data_format:
            data_format = self.default_format
        else:
            data_format = data_format.strip('.')

        if '.' in name:
            name, extra_name = os.path.splitext(name)
            extra_name = extra_name.strip('.')
        else:
            extra_name = ''
        return group, name, extra_name, data_format

    @abc.abstractmethod
    async def ensure_exists(self, group: str):
        """Ensures that a group exists."""

    async def load_item(
            self,
            fullpath: str,
            extras: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """Loads the content from an item with any desired extra information."""
        data_names = ['']
        if extras:
            data_names.extend(extras)
        group, name, _, data_format = self.parse_fullpath(fullpath)
        data = {}
        for data_name in data_names:
            data_path = self.make_fullpath(group, name, data_name, data_format)
            try:
                data_content = await self.read(data_path)
            except exceptions.PathNotFoundError:
                if data_name:
                    continue
                raise
            else:
                data[data_name] = io.parse_data(data_content, data_format)
        return data

    @abc.abstractmethod
    async def read(self, fullpath: str) -> str:
        """Reads the content for a given path."""

    @abc.abstractmethod
    async def write(self, fullpath: str, content: str):
        """Writes the information to the storage."""

    @abc.abstractmethod
    async def list_items(self) -> Sequence[StorageItem]:
        """Walks tree of options."""

    async def save_item(self, fullpath: str, data: Dict[str, Any]):
        """Saves content to the path."""
        group, name, _, data_format = self.parse_fullpath(fullpath)
        await self.ensure_exists(group)

        for data_name, data_ in data.items():
            data_path = self.make_fullpath(group, name, data_name, data_format)
            data_content = io.dump_data(data_, data_format)
            await self.write(data_path, data_content)



class Storage:
    """Storage system."""

    def __init__(self, driver: StorageDriver):
        self.driver = driver

    async def load_item(
            self,
            fullpath: str,
            extras: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """Loads the contents for an item and its extras."""
        return await self.driver.load_item(fullpath, extras)

    async def load_blueprint(
            self,
            fullpath: str,
            library: Optional[_lib.Library] = None,
            **bp_options) -> node.Blueprint:
        """Loads a blueprint and extra information from the path."""
        data = await self.driver.load_item(fullpath)
        return io.parse_blueprint(data[''], library, **bp_options)

    async def list_items(self) -> Sequence[str]:
        """List all available blueprints."""
        return await self.driver.list_items()

    async def save_blueprint(
            self,
            fullpath: str,
            blueprint: node.Blueprint,
            extras: Optional[Dict[str, Any]] = None):
        """Saves a blueprint to the given path."""
        data = {'': io.dump_blueprint(blueprint)}
        if extras:
            data.update(extras)
        await self.save_item(fullpath, data)

    async def save_item(
            self,
            fullpath: str,
            data: Dict[str, Any]):
        """Saves an item to the given path."""
        await self.driver.save_item(fullpath, data)
