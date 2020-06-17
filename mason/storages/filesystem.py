"""Defines a filesystem storage driver."""


import os
from typing import Collection, Sequence

import attr
from mason import storage
from mason import exceptions


@attr.s(auto_attribs=True)
class FileSystem(storage.StorageDriver):
    """Implements filesystem storage."""

    rootpath: str = ''

    def _walk_items(self) -> Collection[storage.StorageItem]:
        """Traverses the filesystem for blueprints."""
        for rootpath, folders, files in os.walk(self.rootpath):
            basepath = os.path.relpath(rootpath, self.rootpath)
            if basepath == '.':
                basepath = ''

            for folder in folders:
                yield storage.StorageItem(
                    path=basepath,
                    name=folder,
                    type='group'
                )

            for filename in files:
                basename, ext = os.path.splitext(filename)
                data_format = ext.strip('.')
                name = (
                    basename
                    if data_format == self.default_format
                    else filename)
                if data_format in self.valid_formats and '.' not in basename:
                    yield storage.StorageItem(
                        path=basepath,
                        name=name,
                        type='blueprint'
                    )

    async def ensure_exists(self, group: str):
        """Ensures a directory path exists."""
        fullpath = os.path.join(self.rootpath, group)
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)

    async def read(self, fullpath: str) -> str:
        """Reads the content from storage."""
        fullpath = os.path.join(self.rootpath, fullpath)
        try:
            with open(fullpath, 'r') as f:
                return f.read()
        except FileNotFoundError:
            raise exceptions.PathNotFoundError(fullpath)

    async def write(self, fullpath: str, content: str):
        """Writes the information to the storage."""
        fullpath = os.path.join(self.rootpath, fullpath)
        try:
            with open(fullpath, 'w') as f:
                return f.write(content)
        except FileNotFoundError:
            raise exceptions.PathNotFoundError(fullpath)

    async def list_items(self) -> Sequence[storage.StorageItem]:
        return list(self._walk_items())
