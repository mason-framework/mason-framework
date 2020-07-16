"""Defines event classes for the system."""

import time

from mason import node as node_mod


class Event:
    """Base event type."""

    def __init__(self):
        self.occurred_at = time.time()

    def asdict(self):
        """Converts this event to a dictionary."""
        return {
            'event_type': type(self).__name__,
            'occurred_at': self.occurred_at,
        }


class NodeEvent(Event):
    """Base event type for all nodes."""

    def __init__(self, node: node_mod.Node):
        super().__init__()
        self.node = node

    def asdict(self):
        """Returns this event as a dictionary."""
        data = super().asdict()
        data['uid'] = self.node.uid
        return data


class NodeEntered(NodeEvent):
    """Event occurs when a node is entered."""


class NodeExited(NodeEvent):
    """Event occurs when a node is exited."""


class NodeErrored(NodeEvent):
    """Event occurs when an error is hit."""


class BlueprintStarted(NodeEvent):
    """Event occurs when a blueprint starts."""


class BlueprintFinished(NodeEvent):
    """Event occurs when a blueprint finishes."""
