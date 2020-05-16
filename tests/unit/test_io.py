"""Tests the mason framework file io system."""
# pylint: disable=protected-access, missing-function-docstring

import enum
import mock

from mason import callbacks
from mason import io
from mason import library
from mason import node
from mason import port
from mason import schema


def test_io_serialize_enum_stores_value():
    class TempEnum(enum.Enum):
        """Temp enum."""

        A = 1
        B = 2

    assert io._serialize(10) == '10'
    assert io._serialize('test') == 'test'
    assert io._serialize(TempEnum.A) == '1'
    assert io._serialize(TempEnum.B) == '2'


def test_io_create_node():
    config = io.blueprint_pb2.Node(
        type='flow.Input',
        name='a',
        uid='123',
    )
    mock_parent = mock.create_autospec(node.Node)
    mock_node = mock.create_autospec(node.Node)
    mock_parent.create.return_value = mock_node
    actual = io._create_node(config, mock_parent)
    mock_parent.create.assert_called_once_with(
        'flow.Input',
        name='a',
        uid='123',
        title=''
    )
    assert mock_node is actual


def test_io_create_blueprint_with_empty_nodes():
    config = io.blueprint_pb2.Blueprint(
        name='test_blueprint',
        nodes=[],
        connections=[]
    )
    bp = io._create_blueprint(config, library.get_default_library())
    assert isinstance(bp, node.Blueprint)
    assert bp.name == 'test_blueprint'
    assert len(bp.nodes) == 0


def test_io_create_blueprint_with_nodes_and_connections():
    nodes = [
        io.blueprint_pb2.Node(type='flow.Input', name='a'),
        io.blueprint_pb2.Node(type='flow.Return', name='return')
    ]
    connections = [
        io.blueprint_pb2.Connection(source='a.value',
                                    target='return.value'),
        io.blueprint_pb2.Connection(source='triggered',
                                    target='return.return_')
    ]
    config = io.blueprint_pb2.Blueprint(
        name='test_blueprint',
        nodes=nodes,
        connections=connections
    )
    with mock.patch.object(node.Blueprint, 'connect') as mock_connect:
        with mock.patch.object(io, '_create_node') as mock_create_node:
            bp = io._create_blueprint(config, library.get_default_library())
            assert isinstance(bp, node.Blueprint)
            assert bp.name == 'test_blueprint'
            mock_create_node.assert_any_call(nodes[0], bp)
            mock_create_node.assert_any_call(nodes[1], bp)
            mock_connect.assert_any_call('a.value', 'return.value')
            mock_connect.assert_any_call('triggered', 'return.return_')


def test_io_dump_node_schema():
    node_schema = schema.Schema(
        group='test',
        name='Move',
        ports={'x': port.Port(int, name='x'), 'y': port.Port(int, name='y')},
        signals={'moved'},
        slots={'move'}
    )
    actual = io._dump_node_schema(node_schema)
    expected = {
        'group': 'test',
        'name': 'Move',
        'ports': [
            {'name': 'x', 'direction': 'input', 'type': 'int'},
            {'name': 'y', 'direction': 'input', 'type': 'int'}
        ],
        'signals': ['moved'],
        'slots': ['move']
    }
    assert actual == expected


def test_io_dump_blueprint_schema():
    bp_schema = schema.Schema(
        group='test',
        name='Blueprint',
        ports={},
        slots=set(),
        signals={'triggered'}
    )
    actual = io._dump_node_schema(bp_schema)
    expected = {
        'group': 'test',
        'name': 'Blueprint',
        'signals': ['triggered']
    }
    assert actual == expected


def test_io_dump_library():
    class Move(node.Node):
        """Example move node."""

        x: int
        y: int

        moved: callbacks.Signal

        @callbacks.slot
        def move(self):
            pass

    Move.__schema__.group = 'test'

    mock_library = library.Library(autoload_defaults=False)
    mock_library.blueprint_types['node.Blueprint'] = node.Blueprint
    mock_library.node_types['test.Move'] = Move
    actual = io.dump_library(mock_library)
    expected = {
        'blueprints': [{
            'group': 'node',
            'name': 'Blueprint',
            'signals': ['triggered']
        }],
        'nodes': [{
            'group': 'test',
            'name': 'Move',
            'ports': [
                {'direction': 'input', 'name': 'x', 'type': 'int'},
                {'direction': 'input', 'name': 'y', 'type': 'int'}
            ],
            'signals': ['moved'],
            'slots': ['move']
        }]
    }
    assert actual == expected
