from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any


class InferenceFailureStage(StrEnum):
    INPUT_CONVERSION = "input_conversion"
    MODEL_EXECUTION = "model_execution"
    PREDICTION_CONVERSION = "prediction_conversion"
    LOADER = "loader"


@dataclass(frozen=True)
class InferenceFailure(Exception):
    stage: InferenceFailureStage
    error: Exception


@dataclass(frozen=True)
class InferenceBatchContext:
    batch: object | None
    loader: object
    model: object
    writer: object
    device: object
    source_path: Path
    source_num_rows: int
    config: dict[str, Any]
    output_dir: Path
    output_path: str | None
    write_timestamped: bool
    timestamp: str | None

    def with_batch(self, batch: object) -> "InferenceBatchContext":
        return replace(self, batch=batch)
