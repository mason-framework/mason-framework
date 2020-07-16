"""Defines a library to utilize for generating nodes."""
import importlib
import functools
import types
from typing import Any, Dict, Sequence, Union, Type

from mason import node

DEFAULT_MODULES = (
    'mason.nodes.blueprint',
    'mason.nodes.flow',
    'mason.nodes.logic',
    'mason.nodes.math',
)


class Library:
    """Library to handle dynamic loading and creation of nodes."""

    def __init__(self,
                 version: int = 1,
                 modules: Sequence[str] = None):
        self.version = version
        self.blueprint_types: Dict[str, Type[node.Blueprint]] = {}
        self.node_types: Dict[str, Type[node.Node]] = {}
        if modules:
            for module in modules:
                self.load(module)

    def load(self, module: Union[str, types.ModuleType]):
        """Loads a package of nodes into the library."""
        if isinstance(module, str):
            module = importlib.import_module(module)
        self.load_scope(vars(module))

    def load_scope(self, items: Dict[str, Any]):
        """Loads nodes and blueprints from a dictionary."""
        for item in items.values():
            if hasattr(item, '__node__'):
                item = getattr(item, '__node__')

            try:
                is_blueprint = issubclass(item, node.Blueprint)
                is_node = issubclass(item, node.Node)
            except TypeError:
                is_blueprint = False
                is_node = False

            if is_blueprint:
                self.blueprint_types[item.__schema__.uid] = item
            elif is_node and not item.__abstract__:
                self.node_types[item.__schema__.uid] = item

    def register(self, item_type: Type[node.Node]):
        """Register node or blueprint type to this library."""
        if issubclass(item_type, node.Blueprint):
            self.blueprint_types[item_type.__schema__.uid] = item_type
        elif issubclass(item_type, node.Node):
            self.node_types[item_type.__schema__.uid] = item_type
        else:
            raise TypeError(f'Invalid type to register: {item_type}.')


DefaultLibrary = functools.partial(Library, modules=DEFAULT_MODULES)


@functools.lru_cache()
def get_default_library() -> Library:
    """Return the default library."""
    return DefaultLibrary()
