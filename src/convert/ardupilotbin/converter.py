"""MessageConverter implementation for ArduPilot Dataflash messages."""

from typing import Any

import pyarrow as pa
from pymavlink import DFReader

from src.convert import converter
from src.convert.ardupilotbin import cast


class MessageConverter(converter.MessageConverter):
    """Convert ArduPilot Dataflash messages to JSON-serializable dictionaries."""

    def __init__(self, type_name: str, yaml_string: str) -> None:
        """Initialize an ArduPilot Dataflash MessageConverter.

        Args:
            type_name (str): ArduPilot Dataflash message type name (e.g., 'ACC').
            yaml_string (str): Key-value pairs of field names and format strings in YAML format.

        """
        self._type_name = type_name
        self._raw_schema = yaml_string
        self._pa_struct = cast.to_pa_struct(yaml_string)

    @property
    def type_name(self) -> str:
        """Return the type name of the ArduPilot Dataflash message."""
        return self._type_name

    @property
    def raw_schema(self) -> str | bytes:
        """Return the ArduPilot Dataflash message definition string."""
        return self._raw_schema

    @property
    def pa_struct(self) -> pa.StructType:
        """Return the pyarrow StructType that represents the ArduPilot Dataflash message schema."""
        return self._pa_struct

    def to_dict(self, message: DFReader.DFMessage) -> dict[str, Any]:
        """Convert an ArduPilot Dataflash message to a JSON-serializable dictionary.

        The message should already be a dictionary with keys matching the schema.
        """
        return message.to_dict()
