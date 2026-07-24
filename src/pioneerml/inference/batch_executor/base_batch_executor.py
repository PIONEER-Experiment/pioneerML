from __future__ import annotations

from abc import ABC
from collections.abc import Mapping
from typing import Any

from pioneerml.data_writer.input_source import PredictionSet

from .context import InferenceBatchContext, InferenceFailure, InferenceFailureStage


class BaseInferenceBatchExecutor(ABC):
    """Execute one opaque inference batch; subclasses may override failure handling."""

    @classmethod
    def from_factory(cls, *, config: Mapping[str, Any] | None = None):
        return cls(config=dict(config or {}))

    def __init__(self, *, config: Mapping[str, Any] | None = None) -> None:
        self.config = dict(config or {})

    def execute_batch(self, *, context: InferenceBatchContext) -> None:
        if context.batch is None:
            raise ValueError("Inference batch context requires a non-null batch.")
        try:
            prediction_set = self._build_prediction_set(context=context)
        except InferenceFailure as failure:
            prediction_set = self.handle_failure(context=context, failure=failure)
        else:
            self.handle_success(context=context, prediction_set=prediction_set)
        if prediction_set is None:
            return
        self._emit_prediction(context=context, prediction_set=prediction_set)

    def _build_prediction_set(self, *, context: InferenceBatchContext) -> PredictionSet:
        try:
            model_args, model_kwargs = context.loader.build_inference_model_input(
                batch=context.batch,
                device=context.device,
                cfg=context.config,
            )
            if not isinstance(model_args, tuple):
                raise RuntimeError(
                    f"{context.loader.__class__.__name__}.build_inference_model_input(...) "
                    "must return tuple args as first element."
                )
            if not isinstance(model_kwargs, dict):
                raise RuntimeError(
                    f"{context.loader.__class__.__name__}.build_inference_model_input(...) "
                    "must return dict kwargs as second element."
                )
        except Exception as error:
            raise InferenceFailure(InferenceFailureStage.INPUT_CONVERSION, error) from error

        try:
            model_output = context.model(*model_args, **model_kwargs)
        except Exception as error:
            raise InferenceFailure(InferenceFailureStage.MODEL_EXECUTION, error) from error

        try:
            prediction_set = context.writer.build_prediction_set(
                batch=context.batch,
                model_output=model_output,
                src_path=context.source_path,
                num_rows=context.source_num_rows,
                cfg=context.config,
            )
            if not isinstance(prediction_set, PredictionSet):
                raise RuntimeError(
                    f"{context.writer.__class__.__name__}.build_prediction_set(...) "
                    "must return PredictionSet."
                )
            return prediction_set
        except Exception as error:
            raise InferenceFailure(InferenceFailureStage.PREDICTION_CONVERSION, error) from error

    def handle_failure(
        self,
        *,
        context: InferenceBatchContext,
        failure: InferenceFailure,
    ) -> PredictionSet | None:
        _ = context
        raise failure.error

    def handle_success(
        self,
        *,
        context: InferenceBatchContext,
        prediction_set: PredictionSet,
    ) -> None:
        _ = context
        _ = prediction_set

    def handle_loader_failure(
        self,
        *,
        context: InferenceBatchContext,
        error: Exception,
    ) -> None:
        _ = context
        raise error

    @staticmethod
    def _emit_prediction(*, context: InferenceBatchContext, prediction_set: PredictionSet) -> None:
        # Deliberately outside the recoverable execution stages. A partial
        # backend write cannot safely be treated as an event/model failure.
        context.writer.on_chunk(
            state=context.writer.chunk_state(
                prediction_set=prediction_set,
                output_dir=context.output_dir,
                output_path=context.output_path,
                write_timestamped=context.write_timestamped,
                timestamp=context.timestamp,
            )
        )
