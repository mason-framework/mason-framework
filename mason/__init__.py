"""Expose public mason API."""

from mason import callbacks
from mason import exceptions
from mason import library
from mason import io
from mason import node
from mason import port

try:
    from importlib import metadata  # Python 3.8+
except ImportError:
    import importlib_metadata as metadata  # Python 3.7<

__version__ = metadata.version('mason-framework')

Blueprint = node.Blueprint
Library = library.Library
Node = node.Node
Port = port.Port
PortDirection = port.PortDirection
Signal = callbacks.Signal

dump_library = io.dump_library
get_default_library = library.get_default_library
inport = port.inport
load_blueprint = io.load_blueprint
load_config = io.load_config
nodify = node.nodify
outport = port.outport
slot = callbacks.slot
