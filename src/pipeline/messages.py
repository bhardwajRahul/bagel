"""Helper functions for message processing in pipelines."""

import duckdb

from settings import settings
from src.message.base import MessageDataset
from src.pipeline import base
from src.source.base import SourceFactory
from src.topic.base import TopicRegistry


def to_duckdb(  # noqa: PLR0913
    factory: SourceFactory,
    registry: TopicRegistry,
    dataset: MessageDataset,
    topics: list[str],
    asof_seconds: float,
    lookback: base.Lookback | None = None,
    ffill: bool = False,
) -> duckdb.DuckDBPyRelation:
    """Return a DuckDB relation of topic messages up to `asof_seconds`.

    Thin wrapper around `MessageDataset.to_duckdb` to support lookback.

    """
    start_seconds = None
    if lookback and lookback.unit != base.Unit.FRAME and asof_seconds - lookback.to_seconds() >= 0:
        start_seconds = asof_seconds - lookback.to_seconds()

    relation = dataset.to_duckdb(
        factory=factory,
        registry=registry,
        topics=topics,
        start_seconds=start_seconds,
        end_seconds=asof_seconds,
        ffill=ffill,
        empty=False,
    )

    if lookback and lookback.unit == base.Unit.FRAME:
        relation = (
            relation.order(f"{settings.TIMESTAMP_SECONDS_COLUMN_NAME} DESC")
            .limit(lookback.last)
            .order(f"{settings.TIMESTAMP_SECONDS_COLUMN_NAME} ASC")
        )

    return relation
