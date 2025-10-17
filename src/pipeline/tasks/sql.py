"""Run a SQL query on topic messages at a given time and write the result to a file."""

import logging
import pathlib
from enum import Enum

import duckdb

from src.artifacts import short_digest
from src.di import module
from src.pipeline import base, messages


class OutputFormat(Enum):
    """Supported output file formats."""

    CSV = "csv"
    PARQUET = "parquet"
    ARROW = "arrow"


class SqlQueryTask(messages.TopicMessageMixin, base.Task):
    """Run a SQL query on topic messages at a given time and write the result to a file."""

    def __init__(
        self,
        topic: str,
        statement: str,
        output_directory: str,
        output_format: str,
    ) -> None:
        """Initialize the task.

        Args:
            topic (str): The topic to run the SQL query on.
            statement (str): The SQL query to execute. The `FROM` clause must refer to
                the topic name as a table.
            output_directory (str): The directory to write the output files to.
            output_format (str): The format of the output files (e.g., "csv", "parquet", "arrow").

        """
        self._topic = topic
        self._statement = statement
        self._output_directory = pathlib.Path(output_directory)
        self._output_format = OutputFormat(output_format)

    def execute(self, asof_seconds: float, lookback: base.Lookback | None) -> None:
        """Execute the task at the given time."""
        relation = self.to_duckdb(
            topics=[self._topic], asof_seconds=asof_seconds, lookback=lookback
        )
        duckdb.register(self._topic, relation)
        result = duckdb.sql(self._statement)

        digest = short_digest([self._topic, self._statement])
        output_file = (
            self._output_directory
            / f"timestamp_seconds={asof_seconds}"
            / f"{digest}.{self._output_format.value}"
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        match self._output_format:
            case OutputFormat.CSV:
                result.to_csv(file_name=str(output_file))

            case OutputFormat.PARQUET:
                result.to_parquet(file_name=str(output_file))

            case OutputFormat.ARROW:
                from pyarrow import ipc

                table = result.to_arrow()
                with ipc.new_file(output_file, table.schema) as writer:
                    writer.write_table(table)

        logging.info(
            "Wrote SQL query result for topic '%s' at %.4f seconds to file: %s",
            self._topic,
            asof_seconds,
            output_file,
        )


def register() -> None:
    """Register module for dependency injection."""
    module.global_registry[__name__] = SqlQueryTask
