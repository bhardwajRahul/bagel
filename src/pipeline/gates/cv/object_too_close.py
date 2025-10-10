"""A gate that evaluates whether an object of certain labels is too close in images."""

import inspect
import logging
from typing import Any

import numpy as np
import torch
from transformers import (
    AutoImageProcessor,
    AutoModelForDepthEstimation,
    YolosForObjectDetection,
    YolosImageProcessor,
)

from src.di import module
from src.image.base import ImageDataset
from src.pipeline import base, images
from src.source.base import SourceFactory
from src.topic.base import TopicRegistry

YOLO_MODEL_ID = "hustvl/yolos-tiny"
DEPTH_MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"

yolo_processor = YolosImageProcessor.from_pretrained(YOLO_MODEL_ID)
yolo_model = YolosForObjectDetection.from_pretrained(YOLO_MODEL_ID)
depth_processor = AutoImageProcessor.from_pretrained(DEPTH_MODEL_ID)
depth_model = AutoModelForDepthEstimation.from_pretrained(DEPTH_MODEL_ID)


class Gate(base.Gate):
    """A gate that evaluates whether an object of certain labels is too close in images.

    It uses a pre-trained YOLO model for object detection and a depth estimation model to determine
    the closeness of detected objects.

    If any object in the lookback window matches the criteria, the gate evaluates to True.

    """

    def __init__(  # noqa: PLR0913
        self,
        factory: SourceFactory,
        registry: TopicRegistry,
        dataset: ImageDataset,
        topic: str,
        labels: list[str] | None = None,
        probability: float = 0.5,
        closeness: float | None = None,
        last: int | None = None,
        unit: str | None = None,
    ) -> None:
        """Initialize a gate for detecting if an object of certain labels is too close.

        Args:
            factory (SourceFactory): A data source factory.
            registry (TopicRegistry): A topic registry.
            dataset (ImageDataset): An image dataset.
            topic (str): The image topic to evaluate.
            labels (list[str] | None, optional): The YOLO labels to detect, e.g., ["person", "car"].
                If None, all available labels are used. Defaults to None.
            probability (float, optional): The minimum probability for a detection to be considered.
                Must be between 0 and 1. Defaults to 0.5.
            closeness (float | None, optional): The closeness threshold. Must be between 0 and 1.
                1 means very close, 0 means very far. If None, the median closeness of the depth map
                is used. Defaults to None.
            last (int | None, optional): Value of the lookback window. Defaults to None.
            unit (str | None, optional): The unit of the lookback window. Defaults to None.

        Raises:
            ValueError: If the labels is an empty list.
            ValueError: If any of the specified labels are not supported by the YOLO model.
            ValueError: If probability is not between 0 and 1.
            ValueError: If closeness is not between 0 and 1.

        """
        self._factory = factory
        self._registry = registry
        self._dataset = dataset
        self._topic = topic
        self._lookback = base.Lookback.build(last, unit)

        if labels is not None and not labels:
            raise ValueError("Labels list cannot be empty")
        self._yolo_labels = yolo_model.config.id2label
        available_labels = list(set(self._yolo_labels.values()))
        labels = labels or available_labels
        wrong_labels = [label for label in labels if label not in available_labels]
        if wrong_labels:
            raise ValueError(
                f"Labels not supported: {wrong_labels}. Available labels: {available_labels}"
            )
        self._labels = labels

        if not (0.0 <= probability <= 1.0):
            raise ValueError("Probability must be between 0 and 1")
        self._probability = probability

        if closeness is not None and not (0.0 <= closeness <= 1.0):
            raise ValueError("Closeness must be between 0 and 1")
        self._closeness = closeness

    def evaluate(self, asof_seconds: float) -> bool:
        """Evaluate if any object of the specified labels is too close at the given time."""
        for _, _, image in images.to_images(
            self._factory,
            self._registry,
            self._dataset,
            [self._topic],
            asof_seconds,
            self._lookback,
        ):
            # Object detection
            yolo_inputs = yolo_processor(images=image, return_tensors="pt")
            with torch.no_grad():
                yolo_outputs = yolo_model(**yolo_inputs)
            detections = yolo_processor.post_process_object_detection(
                yolo_outputs,
                target_sizes=torch.tensor([image.size[::-1]]),
                threshold=self._probability,
            )[0]

            # Depth estimation
            depth_inputs = depth_processor(images=image, return_tensors="pt")
            with torch.no_grad():
                depth_outputs = depth_model(**depth_inputs)
            depth_map = depth_outputs.predicted_depth.squeeze().cpu().numpy()
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
            closeness_threshold = self._closeness or np.median(depth_map)

            # Check if any object is too close
            for probability, label, bbox in zip(
                detections["scores"], detections["labels"], detections["boxes"], strict=True
            ):
                yolo_label = self._yolo_labels[label.item()]
                x0, y0, x1, y1 = map(int, bbox.tolist())
                region = depth_map[y0:y1, x0:x1]
                closeness = np.max(region) if region.size > 0 else None
                if (
                    yolo_label in self._labels
                    and closeness is not None
                    and closeness >= closeness_threshold
                ):
                    logging.info(
                        "Found '%s' object probability=%.4f closeness=%.4f",
                        yolo_label,
                        probability,
                        closeness,
                    )
                    return True

        return False

    @staticmethod
    def build(args: dict[str, Any]) -> "Gate":
        """Build a gate from configuration."""
        factory = module.provide(args["factory"]["module"], args["factory"].get("args", {}))
        registry = module.provide(args["registry"]["module"], args["registry"].get("args", {}))
        dataset = module.provide(args["dataset"]["module"], args["dataset"].get("args", {}))
        return Gate(
            factory=factory,
            registry=registry,
            dataset=dataset,
            topic=args["topic"],
            labels=args.get("labels"),
            probability=args.get(
                "probability",
                inspect.signature(Gate.__init__).parameters["probability"].default,
            ),
            closeness=args.get("closeness"),
            last=args.get("last"),
            unit=args.get("unit"),
        )


def register() -> None:
    """Register module for dependency injection."""
    module.global_registry[__name__] = Gate
