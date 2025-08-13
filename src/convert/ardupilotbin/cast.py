"""Convert ArduPilot format strings to PyArrow DataTypes."""

import pyarrow as pa
import yaml


def cast(format_str: str) -> pa.DataType:  # noqa: C901, PLR0912
    """Cast an ArduPilot format string to a PyArrow DataType.

    The type mapping is based on the pymavlink DFReader's FORMAT_TO_STRUCT:
    https://github.com/ArduPilot/pymavlink/blob/master/DFReader.py#L36

    The original format strings are documented here:
    https://github.com/dronekit/ardupilot-releases/blob/master/libraries/DataFlash/DataFlash.h#L697
    """
    match format_str:
        case "a":
            pa_type = pa.string()
        case "b":
            pa_type = pa.int8()
        case "B":
            pa_type = pa.uint8()
        case "h":
            pa_type = pa.int16()
        case "H":
            pa_type = pa.uint16()
        case "i":
            pa_type = pa.int32()
        case "I":
            pa_type = pa.uint32()
        case "f":
            pa_type = pa.float32()
        case "d":
            pa_type = pa.float64()
        case "n" | "N":  # char[4], char[16]
            pa_type = pa.string()
        case "Z":  # char[64]
            pa_type = pa.binary()
        case "c" | "C":  # int16_t * 100, uint16_t * 100
            pa_type = pa.float64()
        case "e" | "E":  # int32_t * 100, uint32_t * 100
            pa_type = pa.float64()
        case "L":  # int32_t latitude/longitude
            pa_type = pa.float64()
        case "M":  # uint8_t flight mode
            pa_type = pa.uint8()
        case "q":  # Backward compat
            pa_type = pa.int64()
        case "Q":  # Backward compat
            pa_type = pa.uint64()
        case _:
            raise ValueError(f"Unsupported type: {format_str}")
    return pa_type


def to_pa_struct(yaml_string: str) -> pa.StructType:
    """Convert a YAML string representing an ArduPilot message schema to a PyArrow StructType.

    Args:
        yaml_string (str): Key-value pairs of field names and their format strings.

    Returns:
        pa.StructType: The corresponding PyArrow StructType.

    """
    schema = yaml.safe_load(yaml_string)
    fields = []
    for field_name, format_str in schema.items():
        fields.append(pa.field(field_name, cast(format_str), nullable=False))
    return pa.struct(fields)
