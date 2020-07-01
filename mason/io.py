"""Loaders for mason types."""
import enum
import os
import functools
import json
from typing import Any, Dict, Optional, Tuple, List

from google.protobuf import json_format
import yaml

from mason import callbacks
from mason import exceptions
from mason import library as _lib
from mason import node
from mason import port
from mason import schema
from mason.proto import blueprint_pb2
from mason.proto import config_pb2
from mason.proto import library_pb2


def _serialize(value: Any) -> str:
    """Serializes the value for JSON."""
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)

_load_yaml = functools.partial(yaml.safe_load)
_dump_yaml = functools.partial(yaml.safe_dump)
_load_json = functools.partial(json.loads)
_dump_json = functools.partial(json.dumps, default=_serialize)

DEFAULT_FORMAT = 'yaml'
SERIALIZERS = {
    'yaml': (_load_yaml, _dump_yaml),
    'json': (_load_json, _dump_json),
}

_JSON_EXTENSIONS = ('.json',)
_YAML_EXTENSIONS = ('.yaml', '.yml')


def _dump_node(node_inst: node.Node) -> Dict[str, Any]:
    """Converts a node instance to a protobuf."""
    nodes = {}
    for child_uid, child_node in node_inst.nodes.items():
        nodes[child_uid] = _convert_node_to_proto(child_node)

    values = {}
    connections = {}
    for port_ in node_inst.ports.values():
        if port_.direction == port.PortDirection.Input:
            if port_.local_value != port_.default:
                values[port_.name] = json.dumps(port_.local_value,
                                                default=_serialize)
            targets = [conn.uid for conn in port_.connections]
            if targets:
                conn = blueprint_pb2.Connection()
                json_format.ParseDict({'targets': targets}, conn)
                connections[port_.name] = conn.targets  # pylint: disable=no-member

    for signal_name, signal in node_inst.signals.items():
        targets = [
            slot.uid for slot in signal.slots
            if isinstance(slot, callbacks.Slot)
        ]
        if targets:
            conn = blueprint_pb2.Connection()
            json_format.ParseDict({'targets': targets}, conn)
            connections[signal_name] = conn.targets  # pylint: disable=no-member

    node_schema = node_inst.__schema__
    props = {}
    if nodes:
        props['nodes'] = nodes
    if node_inst._label:
        props['label'] = node_inst._label
    if values:
        props['set'] = values
    if connections:
        props['connect'] = connections
    return {f'{node_schema.group}.{node_schema.name}': props}


def _dump_blueprint(
        blueprint: node.Blueprint) -> Dict[str, Any]:
    """Converts a blueprint instance to a protobuf."""
    nodes = {}
    for node_uid, node_ in blueprint.nodes.items():
        nodes[node_uid] = _dump_node(node_)
    return nodes


def _convert_library_to_proto(library: _lib.Library) -> library_pb2.Library:
    """Converts a library instance to a protobuf."""
    nodes = [_convert_node_schema_to_proto(node_type.__schema__)
             for _, node_type in sorted(library.node_types.items())]
    blueprints = [_convert_bp_schema_to_proto(bp_type.__schema__)
                  for _, bp_type in sorted(library.blueprint_types.items())]
    return library_pb2.Library(nodes=nodes, blueprints=blueprints)


def _convert_bp_schema_to_proto(
        bp_schema: schema.Schema) -> library_pb2.BlueprintSchema:
    """Converts a blueprint schema to a protobuf."""
    return library_pb2.BlueprintSchema(
        name=bp_schema.name,
        group=bp_schema.group,
        signals=list(sorted(bp_schema.signals)),
        slots=list(sorted(bp_schema.slots))
    )


def _convert_node_schema_to_proto(
        node_schema: schema.Schema) -> library_pb2.NodeSchema:
    """Converts a node schema to a protobuf."""
    ports = [
        _convert_port_schema_to_proto(port_schema)
        for _, port_schema in sorted(node_schema.ports.items())
    ]
    return library_pb2.NodeSchema(
        name=node_schema.name,
        group=node_schema.group,
        ports=ports,
        shape=node_schema.shape.value if node_schema.shape else None,
        default_label=node_schema.default_label,
        signals=list(sorted(node_schema.signals)),
        slots=list(sorted(node_schema.slots)),
    )


def _convert_port_schema_to_proto(
        port_schema: port.Port) -> library_pb2.PortSchema:
    """Converts a port instance to a protobuf."""
    if port_schema.default is not None:
        default = json.dumps(port_schema.default, default=_serialize)
    else:
        default = None
    return library_pb2.PortSchema(
        name=port_schema.name,
        type=port_schema.value_type,
        direction=port_schema.direction.value,
        sequence=port_schema.is_sequence,
        map=port_schema.is_map,
        choices=port_schema.choices,
        default=default,
        visibility=port_schema.visibility.value,
    )


def _parse_blueprint(
        data: Dict[str, Any],
        library: Optional[_lib.Library] = None,
        **bp_options) -> node.Blueprint:
    """Converts a protobuf blueprint to a blueprint instance."""
    library = library or _lib.get_default_library()
    bp_typename = data.pop('@@type', '')
    bp_type = library.blueprint_types.get(bp_typename, node.Blueprint)
    bp = bp_type(
        library=library,
        **bp_options)
    connections = []
    for uid, node_info in data.items():
        _, node_connections = _parse_node(uid, node_info, bp)
        connections.extend(node_connections)
    for source, targets in connections:
        for target in targets:
            bp.connect(source, target)
    return bp


def _parse_node(
        uid: str,
        node_info: Dict[str, Any],
        parent: node.Node) -> Tuple[node.Node, List[Tuple[str, str]]]:
    """Converts a protobuf node to a node instance."""
    for node_type in node_info:
        type_info = node_info[node_type] or {}
        new_node = parent.create(node_type,
                                 uid=uid,
                                 label=type_info.get('label'))
        node_connections = []

        for child_uid, child_info in type_info.get('nodes', {}).items():
            _, child_connections = _parse_node(child_uid, child_info, new_node)
            node_connections.extend(child_connections)

        for port_name, value_json in type_info.get('set', {}).items():
            try:
                value = json.loads(value_json)
            except json.JSONDecodeError:
                value = value_json
            new_node.ports[port_name].local_value = value

        for node_source, targets in type_info.get('connect', {}).items():
            node_connections.append((f'{uid}.{node_source}', targets))

        return new_node, node_connections


def dump_blueprint(blueprint: node.Blueprint) -> Dict[str, Any]:
    """Dumps a blueprint to data."""
    return _dump_blueprint(blueprint)


def dump_data(data: Any, data_format: str = DEFAULT_FORMAT) -> str:
    """Dumps the data to a given format."""
    try:
        _, dumper = SERIALIZERS[data_format]
    except KeyError:
        raise exceptions.UnknownFormatError(data_format)
    return dumper(data)


def dump_library(library: Optional[_lib.Library] = None) -> Dict[str, Any]:
    """Dumps library to data."""
    library = library or _lib.get_default_library()
    library_proto = _convert_library_to_proto(library)
    return json_format.MessageToDict(library_proto)


def load_blueprint(filename: str,
                   library: Optional[_lib.Library] = None,
                   **bp_options) -> node.Blueprint:
    """Loads a blueprint from the file."""
    data = read_data(filename)
    return parse_blueprint(data, library, **bp_options)


def load_config(filename: str):
    """Loads a configuration file for mason."""
    data = read_data(filename)
    config = config_pb2.Config()
    json_format.ParseDict(data, config)
    # pylint: disable=no-member
    library_modules = set(config.library.modules)
    library_use_default = config.library.extends_default
    library_version = config.library.version
    # pylint: enable=no-member
    if library_use_default:
        library_modules.update(_lib.DEFAULT_MODULES)
    _lib.DefaultLibrary = functools.partial(_lib.Library,
                                            version=library_version,
                                            modules=list(library_modules))


def parse_blueprint(data: Dict[str, Any],
                    library: Optional[_lib.Library] = None,
                    **bp_options) -> node.Blueprint:
    """Parses a blueprint from data."""
    return _parse_blueprint(data, library, **bp_options)


def parse_data(content: str, data_format: str = DEFAULT_FORMAT) -> Any:
    """Parses string content for the given format."""
    try:
        loader, _ = SERIALIZERS[data_format]
    except KeyError:
        raise exceptions.UnknownFormatError(data_format)
    return loader(content)


def read_data(filename: str) -> Dict[str, Any]:
    """Reads the content from the file."""
    _, ext = os.path.splitext(filename)
    if ext in _YAML_EXTENSIONS:
        with open(filename, 'r') as f:
            return yaml.safe_load(f)
    elif ext in _JSON_EXTENSIONS:
        with open(filename, 'r') as f:
            return json.load(f)
    raise exceptions.UnknownFormatError(ext)


def save_blueprint(filename: str, bp: node.Blueprint):
    """Saves a blueprint to the given file."""
    bp_data = dump_blueprint(bp)
    write_data(filename, bp_data)


def write_data(filename: str, data: Dict[str, Any]):
    """Saves data to the file."""
    _, ext = os.path.splitext(filename)
    if ext in _YAML_EXTENSIONS:
        with open(filename, 'w') as f:
            yaml.dump(data, f, indent=2)
    elif ext in _JSON_EXTENSIONS:
        with open(filename, 'w') as f:
            json.dump(data, f, default=_serialize)
    else:
        raise exceptions.UnknownFormatError(ext)
