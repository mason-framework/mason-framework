"""Tests the mason framework node system."""
# pylint: disable=protected-access, missing-function-docstring, redefined-outer-name

import mock
import pytest

from mason import callbacks
from mason import library
from mason import node
from mason import port
from mason import schema


def test_node_definition_with_no_properties_generates_schema():
    class TestNode(node.Node):
        """Test node."""

    assert TestNode.__abstract__ is False
    assert isinstance(TestNode.__schema__, schema.Schema)
    assert TestNode.__schema__.group == 'test_node'
    assert TestNode.__schema__.name == 'TestNode'
    assert len(TestNode.__schema__.ports) == 0
    assert len(TestNode.__schema__.signals) == 0
    assert len(TestNode.__schema__.slots) == 0


def test_node_definition_as_abstract_has_no_schema():
    class AbstractNode(node.Node):
        """Test abstract node."""
        __abstract__ = True

    assert AbstractNode.__abstract__ is True
    assert AbstractNode.__schema__ is None


class test_node_definition_inheritance_shares_schema():
    class Base(node.Node):
        """Abstract base node."""
        __abstract__ = True

        x: int
        y: int
        started: callbacks.Signal

        async def _do_something(self):
            raise NotImplementedError()

        @callbacks.slot
        async def do_something(self):
            self._do_something()

    class A(Base):
        """Test a node."""

        z: float

        async def _do_something(self):
            """Do something for a."""

    class B(Base):
        """Test b node."""

        z: int

        async def _do_something(self):
            """Do something for b."""

    a_schema = A.__schema__
    b_schema = B.__schema__

    assert a_schema != b_schema
    assert a_schema.name == 'A'
    assert b_schema.name == 'B'
    assert a_schema.ports.keys() == b_schema.ports.keys()
    assert a_schema.ports['x'].annotation == b_schema.ports['x'].annotation
    assert a_schema.ports['y'].annotation == b_schema.ports['y'].annotation
    assert a_schema.ports['z'].annotation != b_schema.ports['z'].annotation
    assert a_schema.signals == b_schema.signals == {'started'}
    assert a_schema.slots == b_schema.slots == {'do_something'}


def test_node_abstraction_raises_error():
    with pytest.raises(NotImplementedError):
        node.Node()


def test_node_library_is_default_library():
    class TestNode(node.Node):
        """Test node."""

    test_node = TestNode()
    assert test_node.library is library.get_default_library()


def test_node_library_overrides_default_library():
    lib = library.Library()

    class TestNode(node.Node):
        """Test node."""

    test_node = TestNode(library=lib)
    assert test_node.library is lib


def test_node_library_inheritance():
    lib = library.Library()

    class TestNode(node.Node):
        """Test node."""

    test_parent = TestNode(library=lib)
    test_node = TestNode(parent=test_parent)

    assert test_parent.library is lib
    assert test_node.library is lib


def test_node_automatically_generates_uid():
    class TestNode(node.Node):
        """Test node."""

    test_node = TestNode()
    assert bool(test_node.uid) is True


def test_node_setting_uid_overrides_generated():
    class TestNode(node.Node):
        """Test node."""

    test_node = TestNode(uid='unique-id')
    assert test_node.uid == 'unique-id'


def test_node_initializes_schema_on_init():
    class TestNode(node.Node):
        """Test node."""

        x: int
        y: int

    with mock.patch.object(TestNode, '_init_schema') as mock_init:
        TestNode(values=dict(x=1, y=2))
        mock_init.assert_called_once_with(TestNode.__schema__, {'x': 1, 'y': 2})


def test_node_initialize_with_children_reparents_them():
    class TestNode(node.Node):
        """Test node."""

    a = TestNode(name='a')
    b = TestNode(name='b')
    c = TestNode(nodes=[a, b])
    assert a.parent is c
    assert b.parent is c
    assert c.nodes == {'a': a, 'b': b}


def test_node_getitem_traverses_hierarchy():
    class TestNode(node.Node):
        """Test node."""

        x: int
        y: int

        moved: callbacks.Signal

        @callbacks.slot
        def move(self):
            pass

    a = TestNode(name='a')
    b = TestNode(name='b', parent=a)
    c = TestNode(name='c', parent=b)

    assert a['b'] is b
    assert a['b.c'] is c
    assert b['c'] is c
    assert a['b.c.x'] is c.ports['x']
    assert a['x'] is a.ports['x']
    assert a['b.moved'] is b.signals['moved']
    assert a['moved'] is a.signals['moved']
    assert a['b.c.move'] == c.move  # pylint: disable=comparison-with-callable
    assert a['__self__.moved'] == a.signals['moved']
    assert a['__self__.x'] == a['x'] == a.ports['x']


def test_node_initialization_with_values_overrides_defaults():
    class TestNode(node.Node):
        """Test node."""
        x: int = 0
        y: int = 0

    a = TestNode()
    b = TestNode(values=dict(x=1, y=2))
    assert a.ports['x'].local_value == 0
    assert a.ports['y'].local_value == 0
    assert b.ports['x'].local_value == 1
    assert b.ports['y'].local_value == 2


def test_node_connection_is_shortcut_for_port_connection():
    class TestNode(node.Node):
        """Test node."""
        x: int = 0
        y: int = 0

    a = TestNode()

    with mock.patch.object(a.ports['x'], 'connect') as mock_connect:
        a.connect('x', 'y')
    mock_connect.assert_called_once_with(a.ports['y'])


def test_node_connection_is_shortcut_for_signal_connection():
    class TestNode(node.Node):
        """Test node."""

        triggered: callbacks.Signal

        @callbacks.slot
        def trigger(self):
            pass

    a = TestNode()
    with mock.patch.object(a.signals['triggered'], 'connect') as mock_connect:
        a.connect('triggered', 'trigger')
    mock_connect.assert_called_once_with(a.trigger)


def test_node_connection_is_shortcut_to_nested_connections():
    class TestNode(node.Node):
        """Test node."""
        x: int
        y: int
        value: port.Port(int, direction=port.PortDirection.Output)

        triggered: callbacks.Signal

        @callbacks.slot
        def trigger(self):
            pass

    a = TestNode(name='a')
    b = TestNode(name='b')
    c = TestNode(nodes=[a, b])

    with mock.patch.object(a.ports['value'], 'connect') as mock_connect_port:
        with mock.patch.object(a.signals['triggered'],
                               'connect') as mock_connect_signal:
            c.connect('a.value', 'b.x')
            c.connect('a.triggered', 'b.trigger')

    mock_connect_port.assert_called_once_with(b.ports['x'])
    mock_connect_signal.assert_called_once_with(b.trigger)


def test_node_create_with_type_and_name_uses_no_defaults():
    class TestNode(node.Node):
        """Test node."""

    a = TestNode(name='a')
    b = a.create(TestNode, name='b')
    assert a.nodes == {'b': b}
    assert b.parent == a


def test_node_create_with_type_generates_automatic_name():
    class TestNode(node.Node):
        """Test node."""

    a = TestNode(name='a')
    b = a.create(TestNode)
    c = a.create(TestNode)
    assert b.name == 'testnode-01'
    assert c.name == 'testnode-02'


def test_node_create_with_string_creates_from_library():
    class TestNode(node.Node):
        """Test node."""

    lib = library.Library()
    lib.register(TestNode)

    a = TestNode(name='a', library=lib)
    b = a.create('test_node.TestNode')
    c = a.create('test_node.TestNode')

    assert b.name == 'testnode-01'
    assert c.name == 'testnode-02'


def test_node_create_with_missing_type_raises_error():
    class TestNode(node.Node):
        """Test node."""

    lib = library.Library()

    a = TestNode(name='a', library=lib)
    with pytest.raises(KeyError):
        a.create('test_node.TestNode')


def test_node_delete_removes_from_hierarchy():
    class TestNode(node.Node):
        """Test node."""

    a = TestNode()
    b = TestNode(parent=a)

    assert len(a.nodes) == 1
    b.delete()
    assert len(a.nodes) == 0


def test_node_disconnection_is_shortcut_for_port_connection():
    class TestNode(node.Node):
        """Test node."""
        x: int = 0
        y: int = 0

    a = TestNode()

    with mock.patch.object(a.ports['x'], 'disconnect') as mock_disconnect:
        a.disconnect('x', 'y')
    mock_disconnect.assert_called_once_with(a.ports['y'])


def test_node_disconnection_is_shortcut_for_signal_connection():
    class TestNode(node.Node):
        """Test node."""

        triggered: callbacks.Signal

        @callbacks.slot
        def trigger(self):
            pass

    a = TestNode()
    with mock.patch.object(a.signals['triggered'],
                           'disconnect') as mock_disconnect:
        a.disconnect('triggered', 'trigger')
    mock_disconnect.assert_called_once_with(a.trigger)


def test_node_disconnection_is_shortcut_to_nested_connections():
    class TestNode(node.Node):
        """Test node."""
        x: int
        y: int
        value: port.Port(int, direction=port.PortDirection.Output)

        triggered: callbacks.Signal

        @callbacks.slot
        def trigger(self):
            pass

    a = TestNode(name='a')
    b = TestNode(name='b')
    c = TestNode(nodes=[a, b])

    with mock.patch.object(a.ports['value'],
                           'disconnect') as mock_disconnect_port:
        with mock.patch.object(a.signals['triggered'],
                               'disconnect') as mock_disconnect_signal:
            c.disconnect('a.value', 'b.x')
            c.disconnect('a.triggered', 'b.trigger')

    mock_disconnect_port.assert_called_once_with(b.ports['x'])
    mock_disconnect_signal.assert_called_once_with(b.trigger)


def test_node_disconnection_works_without_target():
    class TestNode(node.Node):
        """Test node."""
        x: int
        y: int

    a = TestNode()
    with mock.patch.object(a.ports['x'], 'disconnect') as mock_disconnect:
        a.disconnect('x')
    mock_disconnect.assert_called_once_with(None)
