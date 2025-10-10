"""Base classes and interfaces for pipelines, tasks, and gates, etc."""

import abc
import importlib
import inspect
from enum import Enum
from typing import Any

from pydantic import BaseModel

from src.di import module

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE


class MissingRequiredKeyError(Exception):
    """Raised when a required key is missing in the pipeline definition."""


class Unit(Enum):
    """Unit of a time window."""

    FRAME = "frame"
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"


def _to_seconds(value: int, unit: Unit) -> float:
    match unit:
        case Unit.SECOND:
            return float(value * SECOND)
        case Unit.MINUTE:
            return float(value * MINUTE)
        case Unit.HOUR:
            return float(value * HOUR)
        case _:
            raise ValueError(f"Cannot convert {unit} to seconds")


class Frequency(BaseModel):
    """Execution frequency of a pipeline.

    For example, every 5 minutes, every 30 frames, etc.

    """

    every: int
    unit: Unit

    def to_seconds(self) -> float:
        """Return the frequency in seconds, if applicable."""
        return _to_seconds(self.every, self.unit)

    @staticmethod
    def build(every: int, unit: str) -> "Frequency":
        """Return a Frequency object from the given configuration."""
        return Frequency(every=every, unit=Unit(unit))


class Lookback(BaseModel):
    """Lookback window for a task or gate.

    For example, last 10 seconds, last 100 frames, etc.

    """

    last: int
    unit: Unit

    def to_seconds(self) -> float:
        """Return the lookback window in seconds, if applicable."""
        return _to_seconds(self.last, self.unit)

    @staticmethod
    def build(last: int | None, unit: str | None) -> "Lookback | None":
        """Return a Lookback object from the given configuration."""
        match last, unit:
            case None, None:
                return None
            case int(), str():
                return Lookback(last=last, unit=Unit(unit))
            case _:
                raise ValueError("Both 'last' and 'unit' must be provided or not at all")


class Gate(abc.ABC):
    """Abstract base class for gates that check whether a pipeline should run at a given time."""

    @abc.abstractmethod
    def evaluate(self, asof_seconds: float) -> bool:
        """Evaluate the gate at the given time."""

    @staticmethod
    @abc.abstractmethod
    def build(args: dict[str, Any]) -> "Gate":
        """Build a Gate object from the given configuration."""


class Task(abc.ABC):
    """Abstract base class for tasks that can be executed in a pipeline."""

    @abc.abstractmethod
    def execute(self, asof_seconds: float) -> None:
        """Execute the task at the given time."""

    @staticmethod
    @abc.abstractmethod
    def build(args: dict[str, Any]) -> "Task":
        """Build a Task object from the given configuration."""


class Pipeline:
    """A data processing pipeline consisting of tasks and gates.

    Gates are used to determine whether the pipeline should run at a given time,
    i.e., if all gates evaluate to True. Then all tasks in the pipeline will be executed.

    """

    def __init__(
        self,
        frequency: Frequency,
        gates: list[Gate],
        tasks: list[Task],
        allow_failure: bool = False,
    ) -> None:
        """Initialize the Pipeline.

        Args:
            frequency (Frequency): How often the pipeline should run.
            gates (list[Gate]): A list of gates to evaluate before running the pipeline.
            tasks (list[Task]): A list of tasks to execute in the pipeline.
            allow_failure (bool, optional): Whether to allow task failures. Defaults to False.
                The caller of the pipeline should handle failures accordingly.

        Raises:
            ValueError: If no tasks are provided.

        """
        if not tasks:
            raise ValueError("At least one task must be provided")

        self._frequency = frequency
        self._gates = gates
        self._tasks = tasks
        self._allow_failure = allow_failure

    @property
    def frequency(self) -> Frequency:
        """Return the frequency of the pipeline."""
        return self._frequency

    @property
    def allow_failure(self) -> bool:
        """Return whether task failures are allowed."""
        return self._allow_failure

    def run(self, asof_seconds: float) -> bool:
        """Run the pipeline at the given time. Return True if gates pass and tasks are executed."""
        if all(gate.evaluate(asof_seconds) for gate in self._gates) if self._gates else True:
            for task in self._tasks:
                task.execute(asof_seconds)
            return True
        return False

    @staticmethod
    def build(args: dict[str, Any]) -> "Pipeline":
        """Return a Pipeline object from the given configuration."""
        if "frequency" not in args:
            raise MissingRequiredKeyError("frequency")
        frequency = Frequency.build(args["frequency"]["every"], args["frequency"]["unit"])

        gates = [
            Pipeline._provide(gate_args["module"], gate_args.get("args", {}))
            for gate_args in args.get("gates", [])
        ]

        if "tasks" not in args:
            raise MissingRequiredKeyError("tasks")
        tasks = [
            Pipeline._provide(task_args["module"], task_args.get("args", {}))
            for task_args in args["tasks"]
        ]

        allow_failure = args.get(
            "allow_failure",
            inspect.signature(Pipeline.__init__).parameters["allow_failure"].default,
        )

        return Pipeline(frequency=frequency, gates=gates, tasks=tasks, allow_failure=allow_failure)

    @staticmethod
    def _provide(name: str, args: dict[str, Any]) -> object:
        importlib.import_module(name).register()
        return module.global_registry[name].build(args)
