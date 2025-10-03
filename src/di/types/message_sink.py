"""A list of supported message sink types and utilities to identify them."""

from enum import Enum


class TopicSink(Enum):
    """Supported message sink types."""

    ROS2_BRIDGE = "ros2.bridge"


def resolve(hint: str) -> TopicSink:
    """Resolve the message sink type from the given hint."""
    hint = hint.lower()
    if any(keyword in hint for keyword in ["ros2", "ros2bridge", "ros2 bridge"]):
        return TopicSink.ROS2_BRIDGE
    else:
        raise ValueError(f"Cannot resolve message sink type from hint: {hint}")
