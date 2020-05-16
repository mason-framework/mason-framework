"""Defines a library to utilize for generating nodes."""
import importlib
import functools
import types
from typing import Any, Dict, Type

from mason import node

_DEFAULT_MODULES = (
    'mason.nodes.data',
    'mason.nodes.flow',
    'mason.nodes.log',
    'mason.nodes.logic',
    'mason.nodes.math',
)


class Library:
    """Library to handle dynamic loading and creation of nodes."""

    def __init__(self, autoload_defaults: bool = False):
        self.blueprint_types: Dict[str, Type[node.Blueprint]] = {}
        self.node_types: Dict[str, Type[node.Node]] = {}
        if autoload_defaults:
            self.load_defaults()

    def load(self, package_name: str):
        """Loads a package of nodes into the library."""
        module = importlib.import_module(package_name)
        self.load_module(module)

    def load_items(self, items: Dict[str, Any]):
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

    def load_module(self, module: types.ModuleType):
        """Loads nodes and blueprints from a module."""
        self.load_items(vars(module))

    def load_defaults(self):
        """Load the default packages."""
        self.blueprint_types[node.Blueprint.__schema__.uid] = node.Blueprint
        for module_name in _DEFAULT_MODULES:
            self.load(module_name)

    def register(self, item_type: Type[node.Node]):
        """Register node or blueprint type to this library."""
        if issubclass(item_type, node.Blueprint):
            self.blueprint_types[item_type.__schema__.uid] = item_type
        elif issubclass(item_type, node.Node):
            self.node_types[item_type.__schema__.uid] = item_type
        else:
            raise TypeError(f'Invalid type to register: {item_type}.')


@functools.lru_cache()
def get_default_library() -> Library:
    """Return the default library."""
    return Library(autoload_defaults=True)
