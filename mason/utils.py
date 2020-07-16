"""Utility methods."""
import importlib
from typing import Any

_LAZY_MODULES = {}


class LazyModule:

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.module = None

    def __getattr__(self, name: str) -> Any:
        if self.module is None:
            self.module = importlib.import_module(self.module_name)
        return getattr(self.module, name)


def lazy_import(module_name: str) -> LazyModule:
    if module_name in _LAZY_MODULES:
        return _LAZY_MODULES[module_name]
    module = LazyModule(module_name)
    _LAZY_MODULES[module_name] = module
    return module
