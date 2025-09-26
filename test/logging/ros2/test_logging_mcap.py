from src.logging.ros2.mcap import LoggingDataset
from src.source.ros2.mcap import SourceFactory
from src.topic.ros2.mcap import TopicRegistry


def test_logging_dataset() -> None:
    # GIVEN
    factory = SourceFactory("data/sample/ros2/mcap_zstd")
    registry = TopicRegistry()
    dataset = LoggingDataset()

    # WHEN
    relation = dataset.to_duckdb(factory, registry)

    # THEN
    assert relation.to_df().shape == (11, 3)


def test_can_select_time_range() -> None:
    # GIVEN
    factory = SourceFactory("data/sample/ros2/mcap_zstd")
    registry = TopicRegistry()
    dataset = LoggingDataset()

    # WHEN
    relation = dataset.to_duckdb(
        factory, registry, start_seconds=1756947560.6797543, end_seconds=None
    )

    # THEN
    assert relation.to_df().shape == (2, 3)
