import pathlib
import shutil
import tempfile

import pytest

from src.source import errors
from src.source.ros2 import mcap


def test_source_factory() -> None:
    # GIVEN
    factory = mcap.SourceFactory("data/sample/ros2/mcap/")

    # WHEN
    metadata = factory.metadata

    # THEN
    assert metadata["version"] == "7"
    assert metadata["storage_identifier"] == "mcap"
    assert metadata["compression_format"] == ""
    assert metadata["compression_mode"] == ""
    assert metadata["relative_file_paths"] == ["part_0.mcap"]
    assert metadata["file_information"] == [
        {
            "duration_seconds": 2.970267,
            "message_count": 15,
            "path": "part_0.mcap",
            "start_time_seconds": 1689969664.041739,
        }
    ]
    assert metadata["topic_information"] == [
        {
            "message_count": 7,
            "topic_metadata": {
                "name": "/fluid_pressure",
                "serialization_format": "cdr",
                "type": "sensor_msgs/msg/FluidPressure",
                "type_description_hash": "RIHS01_22dfb2b145a0bd5a31a1ac3882a1b32148b51d9b2f3bab250290d66f3595bc32",  # noqa: E501
            },
        },
        {
            "message_count": 1,
            "topic_metadata": {
                "name": "/parameter_events",
                "serialization_format": "cdr",
                "type": "rcl_interfaces/msg/ParameterEvent",
                "type_description_hash": "RIHS01_043e627780fcad87a22d225bc2a037361dba713fca6a6b9f4b869a5aa0393204",  # noqa: E501
            },
        },
        {
            "message_count": 0,
            "topic_metadata": {
                "name": "/events/write_split",
                "serialization_format": "cdr",
                "type": "rosbag2_interfaces/msg/WriteSplitEvent",
                "type_description_hash": "RIHS01_5ef58f7106a5cff8f5a794028c18117ee21015850ddcc567df449f41932960f8",  # noqa: E501
            },
        },
        {
            "message_count": 7,
            "topic_metadata": {
                "name": "/rosout",
                "serialization_format": "cdr",
                "type": "rcl_interfaces/msg/Log",
                "type_description_hash": "RIHS01_e28ce254ca8abc06abf92773b74602cdbf116ed34fbaf294fb9f81da9f318eac",  # noqa: E501
            },
        },
    ]


def test_validate_path_should_raise() -> None:
    # GIVEN
    path = pathlib.Path("data/sample/ros2/mcap/")

    # WHEN / THEN
    with tempfile.TemporaryDirectory() as tmpdir, pytest.raises(errors.MissingFilesError):
        shutil.copyfile(path / "metadata.yaml", pathlib.Path(tmpdir) / "metadata.yaml")
        mcap.SourceFactory(tmpdir).validate_path()
