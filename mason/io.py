"""Loaders for mason types."""
import enum
import json
from typing import Any, Dict, Optional

from google.protobuf import json_format
import yaml

from mason import library as _lib
from mason import node
from mason import port
from mason import schema
from mason.proto import blueprint_pb2
from mason.proto import library_pb2


def _read_content(filename: str) -> str:
    """Reads the content of a file."""
    with open(filename, 'r') as f:
        return f.read()


def _serialize(value: Any) -> Any:
    """Serializes the value for JSON."""
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)


def _create_node(config: blueprint_pb2.Node,
                 parent: node.Node) -> node.Node:
    """Return new node from config."""
    new_node = parent.create(config.type,
                             uid=config.uid,
                             name=config.name,
                             title=config.title)
    for node_config in config.nodes:
        _create_node(node_config, new_node)
    return new_node


def _create_blueprint(config: blueprint_pb2.Blueprint,
                      library: _lib.Library) -> node.Blueprint:
    """Return new blueprint from config."""
    bp_type = library.blueprint_types.get(config.type, node.Blueprint)
    bp = bp_type(name=config.name, library=library)
    for node_config in config.nodes:
        _create_node(node_config, bp)
    for connection in config.connections:
        bp.connect(connection.source, connection.target)
    return bp


def _dump_port_schema(port_schema: port.Port) -> Dict[str, Any]:
    """Dumps port schema to config."""
    if port_schema.default is not None:
        default = json.dumps(port_schema.default, default=_serialize)
    else:
        default = None
    port_config = library_pb2.Port(name=port_schema.name,
                                   type=port_schema.value_type,
                                   direction=port_schema.direction.value,
                                   sequence=port_schema.is_sequence,
                                   map=port_schema.is_map,
                                   choices=port_schema.choices,
                                   default=default)
    return json_format.MessageToDict(port_config)


def _dump_node_schema(node_schema: schema.Schema) -> Dict[str, Any]:
    """Dumps node schema to config."""
    ports = []
    for _, port_schema in sorted(node_schema.ports.items()):
        ports.append(_dump_port_schema(port_schema))
    node_config = library_pb2.Node(name=node_schema.name,
                                   group=node_schema.group,
                                   ports=ports,
                                   signals=list(sorted(node_schema.signals)),
                                   slots=list(sorted(node_schema.slots)))
    return json_format.MessageToDict(node_config)


def _dump_blueprint_schema(bp_schema: schema.Schema) -> Dict[str, Any]:
    """Dumps the blueprint to config."""
    bp_config = library_pb2.Blueprint(group=bp_schema.group,
                                      name=bp_schema.name,
                                      signals=list(sorted(bp_schema.signals)),
                                      slots=list(sorted(bp_schema.slots)))
    return json_format.MessageToDict(bp_config)


def dump_library(library: Optional[_lib.Library] = None) -> Dict[str, Any]:
    """Dumps library instance to configuration."""
    library = library or _lib.get_default_library()
    config = library_pb2.Library()
    nodes = [_dump_node_schema(node_type.__schema__)
             for _, node_type in sorted(library.node_types.items())]

    blueprints = [_dump_blueprint_schema(bp_type.__schema__)
                  for _, bp_type in sorted(library.blueprint_types.items())]
    config = library_pb2.Library(nodes=nodes, blueprints=blueprints)
    return json_format.MessageToDict(config)


def load_blueprint(
        filename: str,
        library: Optional[_lib.Library] = None) -> node.Blueprint:
    """Loads a blueprint file from disk."""
    content = _read_content(filename)
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        data = yaml.safe_load(content)
    elif filename.endswith('json'):
        data = json.loads(content)
    else:
        raise RuntimeError(f'Unknown file format: {filename}.')
    bp_config = json_format.ParseDict(data, blueprint_pb2.Blueprint())
    return _create_blueprint(bp_config, library or _lib.get_default_library())
