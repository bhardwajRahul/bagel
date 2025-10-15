"""Write messages from specified topics to a file."""

import logging
import pathlib
from enum import Enum

from src.artifacts import short_digest
from src.di import module
from src.pipeline import base, messages


class OutputFormat(Enum):
    """Supported output file formats."""

    CSV = "csv"
    PARQUET = "parquet"
    ARROW = "arrow"


class WriteTopicsToFileTask(messages.TopicMessageMixin, base.Task):
    """Write messages from specified topics to a file."""

    def __init__(
        self,
        topics: list[str] | None,
        ffill: bool,
        output_directory: str,
        output_format: str,
    ) -> None:
        """Initialize the task.

        Args:
            topics (list[str] | None): A list of topics to write to a file. If None, all available
                topics will be written.
            ffill (bool): Whether to apply forward-fill to the topic messages.
            output_directory (str): The directory to write the output files to.
            output_format (str): The format of the output files (e.g., "csv", "parquet", "arrow").

        Raises:
            ValueError: If the topics list is empty when specified.

        """
        if topics is not None and len(topics) == 0:
            raise ValueError("If 'topics' is specified, it must contain at least one topic name.")
        self._topics = topics
        self._ffill = ffill
        self._output_directory = pathlib.Path(output_directory)
        self._output_format = OutputFormat(output_format)

    def execute(self, asof_seconds: float, lookback: base.Lookback | None) -> None:
        """Execute the task at the given time."""
        topics = self._topics or self.registry.available_topics(self.factory.build())
        relation = self.to_duckdb(
            topics=topics, asof_seconds=asof_seconds, lookback=lookback, ffill=self._ffill
        )

        digest = short_digest([*topics, str(lookback), str(self._ffill)])
        output_file = (
            self._output_directory
            / f"timestamp_seconds={asof_seconds}"
            / f"{digest}.{self._output_format.value}"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        match self._output_format:
            case OutputFormat.CSV:
                relation.to_csv(file_name=str(output_file))

            case OutputFormat.PARQUET:
                relation.to_parquet(file_name=str(output_file))

            case OutputFormat.ARROW:
                from pyarrow import ipc

                table = relation.to_arrow()
                with ipc.new_file(output_file, table.schema) as writer:
                    writer.write_table(table)

        logging.info(
            "Wrote topics %s to %s at %.4f seconds",
            topics,
            output_file,
            asof_seconds,
        )


def register() -> None:
    """Register module for dependency injection."""
    module.global_registry[__name__] = WriteTopicsToFileTask
