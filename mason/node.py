"""Defines Node classes."""
import asyncio
import contextlib
import functools
import inspect
import uuid
from typing import Any, Callable, Dict, Optional, Set, Sequence, TypeVar, Union
from typing import Generator, Tuple, Type, TYPE_CHECKING

import attr

from mason import callbacks
from mason import exceptions
from mason import port
from mason import schema
from mason import utils

_library = utils.lazy_import('mason.library')
_middleware = utils.lazy_import('mason.middlware')
_events = utils.lazy_import('mason.events')

if TYPE_CHECKING:
    from mason import library
    from mason import middleware


@attr.s(auto_attribs=True)
class ExecutionContext:
    """Context information when running a flow."""

    args: Dict[str, Any] = None
    state: Dict[str, Any] = None
    results: Dict[str, Any] = None


class NodeMeta(type):
    """Metaclass for nodes to handle port creation and registration."""

    def __new__(mcs, clsname: str, supers: Tuple[Any], attributes: Any):
        """Generates new node type."""
        is_abstract = attributes.setdefault('__abstract__', False)
        if is_abstract:
            return type.__new__(mcs, clsname, supers, attributes)

        model = type.__new__(mcs, clsname, supers, attributes)
        model.__schema__ = schema.generate(model)
        return model


class Node(metaclass=NodeMeta):
    """Base class for defining nodes."""
    __abstract__ = True
    __schema__ = None

    def __init__(self,
                 *,
                 values: Dict[str, Any] = None,
                 library: Optional['library.Library'] = None,
                 nodes: Optional[Sequence['Node']] = None,
                 parent: Optional['Node'] = None,
                 label: str = '',
                 uid: str = '',
                 middleware: Optional['middleware.Middleware'] = None):
        if type(self).__abstract__:
            raise NotImplementedError(f'{type(self).__name__} is abstract.')

        self.uid = uid or str(uuid.uuid4())
        self.ports: Dict[str, port.Port] = {}
        self.signals: Dict[str, callbacks.Signal] = {}
        self.slots: Dict[str, callbacks.Slot] = {}

        self._middleware = middleware
        self._library = library
        self._label = label
        self._parent: Optional['Node'] = None
        self._nodes: Set['Node'] = set()
        self._execution_context: Optional[ExecutionContext] = None

        self._init_schema(type(self).__schema__, values or {})

        if parent:
            self.parent = parent

        if nodes:
            for node in nodes:
                node.parent = self

    def __enter__(self):
        self.resume()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type:
            self.dispatch(_events.NodeErrored(self))
        else:
            self.suspend()

    def resume(self):
        self.dispatch(_events.NodeEntered(self))

    def suspend(self):
        self.dispatch(_events.NodeExited(self))

    def __getitem__(self, key: str) -> Union['Node',
                                             port.Port,
                                             callbacks.Signal,
                                             Callable[..., Any]]:
        """Returns an item within the hierarchy."""
        parts = key.split('.')
        curr = self
        for part in parts[:-1]:
            if part == '__self__':
                continue
            curr = curr.find_child(part)
            if not curr:
                raise KeyError(key)
        prop = parts[-1]
        if prop in curr.ports:
            return curr.ports[prop]
        if prop in curr.signals:
            return curr.signals[prop]
        if prop in curr.slots:
            return curr.slots[prop]
        try:
            return curr.nodes[prop]
        except KeyError:
            raise KeyError(key)

    def _init_schema(self,
                     my_schema: Optional[schema.Schema],
                     values: Dict[str, Any]):
        """Initializes this node from its schema."""
        if my_schema:
            for port_name, schema_port in my_schema.ports.items():
                try:
                    overrides = {'value': values[port_name]}
                except KeyError:
                    overrides = {}
                self.ports[port_name] = schema_port.evolve(**overrides)

            for signal_name in my_schema.signals:
                self.signals[signal_name] = callbacks.Signal(sender=self)

            for slot_name in my_schema.slots:
                method = getattr(self, slot_name)
                self.slots[slot_name] = callbacks.Slot(method, receiver=self)

    def connect(self, source_path: str, target_path: str):
        """Convenience method to create a connection between the children."""
        source = self[source_path]
        target = self[target_path]
        source.connect(target)

    def create(self, node_type: Union[str, Type['Node']], **props) -> 'Node':
        """Creates a new child node for this node instance."""
        if isinstance(node_type, str):
            node_type = self.library.node_types[node_type]
        return node_type(parent=self, **props)

    def delete(self):
        """Deletes this node from the graph."""
        self.parent = None
        del self

    def disconnect(self, source_path: str, target_path: Optional[str] = None):
        """Disconnects the source from the target, or from all connections."""
        source = self[source_path]
        target = self[target_path] if target_path else None
        source.disconnect(target)

    def dispatch(self, event: 'events.Event'):
        """Dispatches an event through the middleware."""
        mid = self.middleware
        if mid:
            mid.dispatch(event)

    @contextlib.contextmanager
    def execution_context(self,
                          initial_state: Dict[str, Any],
                          args: Dict[str, Any]) -> ExecutionContext:
        """Creates a new execution context instance for this blueprint."""
        try:
            self._execution_context = ExecutionContext(args=args,
                                                       results={},
                                                       state=initial_state)
            yield self._execution_context
        finally:
            self._execution_context = None

    async def emit(self, signal_name: str, *args: Any) -> None:
        """Helper function to emit a signal by name."""
        await self.signals[signal_name].emit(*args)

    async def gather(self, *port_names: str) -> Sequence[Any]:
        """Gathers multiple port values."""
        tasks = (self.ports[port_name].get() for port_name in port_names)
        return await asyncio.gather(*tasks)

    async def get(self, port_name: str) -> Any:
        """Returns the port value for the given port name."""
        return await self.ports[port_name].get()

    def get_context(self) -> Optional[ExecutionContext]:
        """Returns the context for this node."""
        curr = self
        # pylint: disable=protected-access
        while curr:
            if curr._execution_context:
                return curr._execution_context
            curr = curr.parent
        # pylint: enable=protected-access
        return None

    def find_ancestor(self, node_type: Type['Node']) -> Optional['Node']:
        """Returns the ancestor whose type matches the given parameter."""
        curr = self.parent
        while curr and not isinstance(curr, node_type):
            curr = curr.parent
        return curr

    def find_child(
            self,
            uid: str,
            recursive: bool = False,
            node_type: Optional[Type['Node']] = None) -> Optional['Node']:
        """Returns a child by its id."""
        for child in self._nodes:
            if ((not node_type or isinstance(child, node_type)) and
                    child.uid == uid):
                return child
            if not recursive:
                continue
            found = child.find_child(uid, recursive=True, node_type=node_type)
            if found:
                return found
        return None

    @property
    @functools.lru_cache()
    def middleware(self) -> Optional['middleware.Middleware']:
        curr = self
        # pylint: disable=protected-access
        while curr:
            if curr._middleware:
                return curr._middleware
            curr = curr.parent
        # pylint: disable=protected-access
        return None

    @property
    @functools.lru_cache()
    def library(self) -> 'library.Library':
        """Traverse up the hierarchy to find the closest library."""
        curr = self
        # pylint: disable=protected-access
        while curr and not curr._library:
            if curr._library:
                return curr._library
            curr = curr.parent
        # pylint: disable=protected-access
        return _library.get_default_library()

    @property
    def blueprint(self) -> Optional['Blueprint']:
        """Returns the blueprint node in this hierarchy."""
        return self.find_ancestor(Blueprint)

    @property
    def root_node(self) -> 'Node':
        """Returns the root node in this hierarchy."""
        curr = self
        while curr.parent:
            curr = curr.parent
        return curr

    @property
    def parent(self) -> Optional['Node']:
        """Returns the parent for this node."""
        return self._parent

    @property
    def nodes(self) -> Dict[str, 'Node']:
        """Returns the children for this node."""
        return {n.uid: n for n in self._nodes}

    @parent.setter
    def parent(self, parent: Optional['Node']):
        """Sets the parent for this node."""
        if parent == self._parent:
            return
        if self._parent:
            self._parent._nodes.remove(self)  # pylint: disable=protected-access
        self._parent = parent
        if parent:
            parent._nodes.add(self)  # pylint: disable=protected-access

    async def setup(self):
        """Setup this node before execution."""

    @property
    def label(self) -> str:
        """Generates a label for this node."""
        return self._label or (
            self.uid
            .title()
            .replace('_', ' ')
            .replace('-', ' ')
        )

    def walk_nodes(self) -> Generator['Node', None, None]:
        """Traverses the hierarchy of this node."""
        for node in self._nodes:
            yield node
            yield from node.walk_nodes()

    async def teardown(self):
        """Teardown this node after execution."""


class Blueprint(Node):
    """Defines a base blueprint node."""

    on_setup: callbacks.Signal
    on_run: callbacks.Signal
    on_teardown: callbacks.Signal

    def __enter__(self):
        return self

    def __exit__(self, *args):
        del args  # Unused.

    def resume(self):
        pass

    def suspend(self):
        pass

    async def __call__(self,
                       initial_state: Dict[str, Any] = None,
                       **args: Any) -> Any:
        """Executes the blueprint."""
        with self.execution_context(initial_state, args) as context:
            self.dispatch(_events.BlueprintStarted(self))
            await self.setup()
            try:
                return await self.run(context)
            finally:
                await self.teardown()
                self.dispatch(_events.BlueprintFinished(self))

    async def setup(self):
        """Sets up the nodes for this blueprint."""
        for node in self.walk_nodes():
            await node.setup()
        await self.emit('on_setup')

    async def run(self, context: ExecutionContext) -> Any:
        """Runs the body of the blueprint."""
        try:
            await self.emit('on_run')
        except exceptions.ReturnException as exc:
            return exc.value
        except exceptions.ExitException as exc:
            if exc.code != 0:
                raise
        return context.results if context.results else None

    async def teardown(self):
        await self.emit('on_teardown')
        for node in self.walk_nodes():
            await node.teardown()


def nodify(*args,
           type_name: str = '',
           result_name: str = 'result',
           node_type: Optional[Type[Node]] = None):
    """Decorator for generating a node type from a function."""
    T = TypeVar('T')
    def inner(func: T) -> T:
        sig = inspect.signature(func)
        args = []
        signals = []
        annotations = {}
        defaults = {}
        pass_context_as = ''
        for param_name, param in sig.parameters.items():
            try:
                is_context = issubclass(param.annotation, ExecutionContext)
            except TypeError:
                is_context = False

            if is_context:
                pass_context_as = param_name
            elif param.annotation is callbacks.Signal:
                signals.append(param_name)
                annotations[param_name] = param.annotation
            else:
                args.append(param_name)
                annotations[param_name] = param.annotation
                if param.default is not inspect.Parameter.empty:
                    defaults[param_name] = param.default

        def init(inst: Node, **props):
            Node.__init__(inst, **props)

            try:
                inst.ports[result_name].getter = getattr(inst, func.__name__)
            except KeyError:
                pass

        async def bound_func(inst: Node) -> Any:
            """Method to invoke the function."""
            kwargs = {}
            if pass_context_as:
                kwargs[pass_context_as] = inst.get_context()
            values = await inst.gather(*args)
            kwargs.update(zip(args, values))
            kwargs.update({sig_name: inst.signals[sig_name]
                           for sig_name in signals})
            result = func(**kwargs)
            if inspect.isawaitable(result):
                return await result
            return result

        if hasattr(func, '__slot__'):
            setattr(bound_func, '__slot__', func.__slot__)

        if sig.return_annotation is not inspect.Parameter.empty:
            annotations[result_name] = port.Port(
                sig.return_annotation,
                direction=port.PortDirection.Output)

        node_attrs = {
            '__annotations__': annotations,
            '__init__': init,
            func.__name__: bound_func,
            **defaults,
        }

        node_base = (node_type or Node,)
        node_group = inspect.getmodule(func).__name__.split('.')[-1]
        node_clsname = type_name or func.__name__.title().replace('_', '')
        node_class = type(node_clsname, node_base, node_attrs)
        node_class.__schema__.group = node_group
        func.__node__ = node_class
        return func
    if len(args) == 1:
        return inner(args[0])
    return inner
