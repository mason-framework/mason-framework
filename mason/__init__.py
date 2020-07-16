"""Expose public mason API."""

from mason import callbacks
from mason import exceptions
from mason import events
from mason import middleware
from mason import library
from mason import node
from mason import port
from mason import schema
from mason import storage

try:
    from importlib import metadata  # Python 3.8+
except ImportError:
    import importlib_metadata as metadata  # Python 3.7<

__version__ = metadata.version('mason-framework')

Blueprint = node.Blueprint
Library = library.Library
Event = events.Event
Dispatcher = middleware.Dispatcher
Middleware = middleware.Middleware
Node = node.Node
NodeShape = schema.NodeShape
Port = port.Port
PortDirection = port.PortDirection
PortVisibility = port.PortVisibility
Storage = storage.Storage
Signal = callbacks.Signal

getter = port.getter
get_default_library = library.get_default_library
inport = port.inport
nodify = node.nodify
outport = port.outport
slot = callbacks.slot
