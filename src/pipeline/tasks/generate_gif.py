"""A task that generates GIF files from images in a topic over a lookback window."""

import logging
import pathlib
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from src.di import module
from src.image.base import ImageDataset
from src.pipeline import base, images
from src.source.base import SourceFactory
from src.topic.base import TopicRegistry


class Task(base.Task):
    """A task that generates GIF files from images in a topic over a lookback window."""

    def __init__(  # noqa: PLR0913
        self,
        factory: SourceFactory,
        registry: TopicRegistry,
        dataset: ImageDataset,
        topic: str,
        output_directory: str,
        last: int | None = None,
        unit: str | None = None,
    ) -> None:
        """Initialize the GIF generation task.

        Args:
            factory (SourceFactory): A data source factory.
            registry (TopicRegistry): A topic registry.
            dataset (ImageDataset): An image dataset.
            topic (str): The image topic to generate GIFs from.
            output_directory (str): The directory to save the generated GIFs.
            last (int | None, optional): Value of the lookback window. Defaults to None.
            unit (str | None, optional): The unit of the lookback window. Defaults to None.

        """
        self._factory = factory
        self._registry = registry
        self._dataset = dataset
        self._topic = topic
        self._lookback = base.Lookback.build(last, unit)
        self._output_directory = pathlib.Path(output_directory)

        # Styling options for the text box below each image
        self._strip_height = 40
        self._padding = 4
        self._font = ImageFont.load_default()
        self._fill_text = (255, 255, 255, 255)

    def execute(self, asof_seconds: float) -> None:
        """Generate GIF files and save to the output directory."""

        def _text_size(draw, text, font) -> tuple[int, int]:  # noqa: ANN001
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]

        frames = []
        first_timestamp_text, first_image = None, None

        for _, timestamp_seconds, image in images.to_images(
            self._factory,
            self._registry,
            self._dataset,
            [self._topic],
            asof_seconds,
            self._lookback,
        ):
            timestamp_text = f"{timestamp_seconds:.8f}"

            img = image.convert("RGBA")
            W, H = img.size  # noqa: N806

            annotated = Image.new("RGBA", (W, H + self._strip_height), (0, 0, 0, 255))
            annotated.paste(img, (0, 0))
            draw = ImageDraw.Draw(annotated)

            _, topic_h = _text_size(draw, self._topic, self._font)
            ts_w, _ = _text_size(draw, timestamp_text, self._font)

            y_text = H + (self._strip_height - topic_h) // 2
            draw.text(
                (self._padding, y_text),
                self._topic,
                font=self._font,
                fill=self._fill_text,
            )
            draw.text(
                (W - ts_w - self._padding, y_text),
                timestamp_text,
                font=self._font,
                fill=self._fill_text,
            )

            frames.append(annotated)
            if first_timestamp_text is None:
                first_timestamp_text = timestamp_text
                first_image = annotated

        if frames and first_timestamp_text and first_image:
            stems = [
                self._topic.lstrip("/").replace("/", "_"),
                f"at={first_timestamp_text}",
                f"n={len(frames)}",
            ]
            gif_file = self._output_directory / f"{'_'.join(stems)}.gif"
            gif_file.parent.mkdir(parents=True, exist_ok=True)
            first_image.save(
                gif_file,
                save_all=True,
                append_images=frames[1:],
                duration=100,
                loop=0,
            )
            logging.info("Generated %s from %d frames", self._output_directory, len(frames))

    @staticmethod
    def build(args: dict[str, Any]) -> "Task":
        """Build a task from configuration."""
        factory = module.provide(args["factory"]["module"], args["factory"].get("args", {}))
        registry = module.provide(args["registry"]["module"], args["registry"].get("args", {}))
        dataset = module.provide(args["dataset"]["module"], args["dataset"].get("args", {}))
        return Task(
            factory=factory,
            registry=registry,
            dataset=dataset,
            topic=args["topic"],
            output_directory=args["output_directory"],
            last=args.get("last"),
            unit=args.get("unit"),
        )


def register() -> None:
    """Register module for dependency injection."""
    module.global_registry[__name__] = Task
