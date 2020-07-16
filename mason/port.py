"""Defines a basic Port type."""

import enum
import functools
import weakref
from collections import abc
from typing import Any, Awaitable, Callable, Dict, Optional, Set
from typing import Sequence, TypeVar
from typing import Union, TYPE_CHECKING

from mason import exceptions

if TYPE_CHECKING:
    from mason import node

T = TypeVar('T')
_CHOICES_TYPE = Optional[Union[Dict[str, Any], Sequence[Any]]]
_GETTER_TYPE = Callable[[], Awaitable[Any]]

class PortDirection(enum.Enum):
    """Defines flow direction types."""

    Input = 'input'
    Output = 'output'


class PortVisibility(enum.Enum):
    """Defines visibility options for UI."""

    Visible = 'visible'
    Editable = 'editable'
    Connectable = 'connectable'
    Hidden = 'hidden'


class Port:
    """Defines a data storage class for nodes."""

    def __init__(self,
                 annotation: Any,
                 *,
                 choices: _CHOICES_TYPE = None,
                 default: Any = None,
                 direction: PortDirection = PortDirection.Input,
                 name: str = '',
                 title: str = '',
                 value: Any = None,
                 node: 'node.Node' = None,
                 visibility: PortVisibility = PortVisibility.Visible):
        self.annotation = annotation
        self.visibility = visibility
        self.name = name
        self.default = default
        self.direction = direction
        self.getter: Optional[_GETTER_TYPE] = None
        self.node = node

        origin = getattr(annotation, '__origin__', None)

        self._choices = choices
        self.is_map = origin is dict
        try:
            self.is_sequence = issubclass(origin, abc.Sequence)
        except TypeError:
            self.is_sequence = False

        try:
            self.is_enum = issubclass(annotation, enum.Enum)
        except TypeError:
            self.is_enum = False

        self._title = title
        self._connections: Set['Port'] = weakref.WeakSet()

        if isinstance(value, Port):
            self._local_value = default
            self.connect(value)
        else:
            self._local_value = value if value is not None else default

    def __del__(self):
        """Disconnects this port from others on deletion."""
        self.disconnect()

    def can_connect(self, other: 'Port') -> bool:
        """Tests to see whether or not this port can connect to the other."""
        if self.direction == other.direction:
            return False
        if self.direction == PortDirection.Output:
            return True
        return self.is_sequence or self.is_map or not self.is_connected

    @property
    def connections(self) -> Set['Port']:
        """Returns a set of ports this instance is connected to."""
        return set(self._connections)

    @property
    def choices(self) -> _CHOICES_TYPE:
        """Returns an optional sequence of strings for this port."""
        if self._choices:
            return self._choices
        if self.is_enum:
            return dict(self.annotation.__members__)
        return None

    @choices.setter
    def choices(self, value: _CHOICES_TYPE):
        """Sets the choices for this port."""
        self._choices = value

    def connect(self, *ports: 'Port') -> None:
        """Creates a connection between this port and another port."""
        for port in ports:
            if self.can_connect(port) and port.can_connect(self):
                self._connections.add(port)
                port._connections.add(self)  # pylint: disable=protected-access
            else:
                raise exceptions.InvalidConnectionError(self, port)

    def evolve(self, **overrides: Any) -> 'Port':
        """Generate a copy of this port information."""
        props = dict(
            annotation=self.annotation,
            choices=self._choices,
            name=self.name,
            default=self.default,
            direction=self.direction,
            value=self._local_value,
            title=self._title,
            node=self.node,
        )
        props.update(overrides)
        new_port = Port(**props)
        new_port.getter = self.getter
        return new_port

    def disconnect(self, *ports: 'Port') -> None:
        """Disconnects all ports, or the port specified as other."""
        if not ports:
            for port in self._connections:
                port._connections.remove(self)  # pylint: disable=protected-access
            self._connections.clear()
        else:
            for port in ports:
                port._connections.remove(self)  # pylint: disable=protected-access
                self._connections.remove(port)

    def get_value(self) -> Any:
        """Returns the current value of this port."""
        with self.node:
            is_input = self.direction == PortDirection.Input
            use_connection = is_input and self.is_connected

            if use_connection and self.is_sequence:
                return {other.get_value() for other in self._connections}
            if use_connection and self.is_map:
                return {other.name: other.get_value()
                        for other in self._connections}
            if use_connection:
                conn = next(iter(self._connections))
                return conn.get_value()
            if self.getter:
                return self.getter()
            return self.local_value

    @property
    def is_connected(self) -> bool:
        """Returns whether or not this port has connections."""
        return len(self._connections) > 0

    @property
    def local_value(self) -> Any:
        """Returns the local value of this port instance."""
        return self._local_value

    @local_value.setter
    def local_value(self, value: Any):
        """Sets the local value for this port instance."""
        if self.is_enum and not isinstance(value, self.annotation):
            if hasattr(self.annotation, value):
                value = getattr(self.annotation, value)
            else:
                value = self.annotation(value)

        self._local_value = value

    @property
    def title(self) -> str:
        """Returns the title of this port."""
        return self._title or self.name.title()

    @property
    def uid(self) -> str:
        """Returns the unique id of this port."""
        node_uid = self.node.uid if self.node else '<< unknown >>'
        return f'{node_uid}.{self.name}'

    @property
    def value_type(self) -> Any:
        """Returns the value type of this port."""
        args = getattr(self.annotation, '__args__', None)
        if args:
            vtype = args[-1]
        else:
            vtype = self.annotation
        return getattr(vtype, '__name__', str(vtype))


inport = functools.partial(Port, direction=PortDirection.Input)
outport = functools.partial(Port, direction=PortDirection.Output)


def getter(port_name: str) -> Callable[[T], T]:
    """Marks this function as a getter for a port."""
    def inner(func: T) -> T:
        func.__port_getter__ = port_name
        return func
    return inner
