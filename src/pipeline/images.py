"""Helper functions for image processing in pipelines."""

from collections.abc import Iterator

from PIL import Image

from src.image.base import ImageDataset
from src.pipeline import base
from src.source.base import SourceFactory
from src.topic.base import TopicRegistry


def to_images(  # noqa: PLR0913
    factory: SourceFactory,
    registry: TopicRegistry,
    dataset: ImageDataset,
    topics: list[str],
    asof_seconds: float,
    lookback: base.Lookback | None = None,
) -> Iterator[tuple[str, float, Image.Image]]:
    """Yield images up to `asof_seconds`.

    Thin wrapper around `ImageDataset.images` to support lookback.

    """
    start_seconds = None
    if lookback and lookback.unit != base.Unit.FRAME and asof_seconds - lookback.to_seconds() >= 0:
        start_seconds = asof_seconds - lookback.to_seconds()

    images = dataset.images(
        factory=factory,
        registry=registry,
        topics=topics,
        start_seconds=start_seconds,
        end_seconds=asof_seconds,
    )

    if lookback and lookback.unit == base.Unit.FRAME:
        images = list(images)[-lookback.last :]

    yield from images
