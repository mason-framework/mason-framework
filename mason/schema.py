"""Defines model schema files."""
import enum
import inspect
import typing
from typing import Dict, Set, Type, TYPE_CHECKING, Optional

import attr

from mason import callbacks
from mason import port

if TYPE_CHECKING:
    from mason import node



class NodeShape(enum.Enum):
    """Define the shape for this node."""

    Round = 'round'


@attr.s(auto_attribs=True, eq=False)
class Schema:
    """Define schema properties."""

    group: str
    name: str
    ports: Dict[str, 'port.Port']
    signals: Set[str]
    slots: Set[str]
    shape: Optional[str] = None
    default_label: Optional[str] = None

    @property
    def uid(self) -> str:
        """Returns the unique id for this schema."""
        return f'{self.group}.{self.name}'



def generate(model: Type['node.Node']) -> Schema:
    """Generates a new Schema instance from the type attributes."""
    group_name = inspect.getmodule(model).__name__.rsplit('.', 1)[-1]
    model_name = model.__name__
    ports = {}
    signals = set()
    slots = set()

    # extract signals and ports from annotations
    for name, annotation in typing.get_type_hints(model).items():
        if name.startswith('_'):
            continue

        if annotation is callbacks.Signal or isinstance(annotation,
                                                        callbacks.Signal):
            signals.add(name)
        elif isinstance(annotation, port.Port):
            annotation.name = name
            ports[name] = annotation
        else:
            default = getattr(model, name, None)
            ports[name] = port.Port(annotation, name=name, default=default)

    # extract slots from attributes
    for name, prop in inspect.getmembers(model):
        if getattr(prop, '__slot__', False):
            slots.add(name)

    schema = Schema(group=group_name,
                    name=model_name,
                    ports=ports,
                    signals=signals,
                    shape=getattr(model, '__shape__', None),
                    default_label=getattr(model, '__default_label__', None),
                    slots=slots)
    return schema
