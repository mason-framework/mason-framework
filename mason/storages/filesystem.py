"""Defines a filesystem storage driver."""


import os
from typing import Collection, Sequence

import attr
from mason import io
from mason import node
from mason import storage


@attr.s(auto_attribs=True)
class FilesystemDriver(storage.StorageDriver):
    """Implements filesystem storage."""

    rootpath: str
    default_ext: str = '.yaml'
    supported_types: Sequence[str] = ('.yaml', '.json')

    def _walk_blueprints(self) -> Collection[str]:
        for rootpath, _, files in os.walk(self.rootpath):
            basepath = os.path.relpath(rootpath, self.rootpath)
            if basepath == '.':
                basepath = ''

            for filename in files:
                basename, ext = os.path.splitext(filename)
                if ext in self.supported_types:
                    yield os.path.join(
                        basepath,
                        basename if ext == self.default_ext else filename)

    async def load_blueprint(self, path: str) -> node.Blueprint:
        filename = os.path.join(self.rootpath, path)
        if not os.path.isfile(filename):
            filename += self.default_ext
        return io.load_blueprint(filename)

    async def save_blueprint(self, path: str, blueprint: node.Blueprint):
        filename = os.path.join(self.rootpath, path)
        content = io.dump_blueprint(blueprint)
        with open(filename, 'w') as f:
            f.write(content)

    async def list_blueprints(self) -> Sequence[str]:
        return list(self._walk_blueprints())
