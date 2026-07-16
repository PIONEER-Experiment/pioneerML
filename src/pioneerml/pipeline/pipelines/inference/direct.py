"""Direct inference execution without ZenML orchestration."""

from __future__ import annotations

from pioneerml.pipeline.steps import (
    BaseInferenceStep,
    BaseModelHandleBuilderStep,
    InferenceStepPayload,
)


class UnifiedModelHandleBuilderStep(BaseModelHandleBuilderStep):
    step_key = "model_handle_builder"


class UnifiedInferenceStep(BaseInferenceStep):
    step_key = "inference"


def run_direct_inference(
    pipeline_config: dict | None = None,
) -> InferenceStepPayload:
    """Run the unified inference flow directly and return prediction paths.

    This executes the same model-handle builder, inference loop, and output
    writer used by the ZenML pipeline without creating a ZenML pipeline run or
    materializing ZenML artifacts.
    """
    model_handle_payload = UnifiedModelHandleBuilderStep(
        pipeline_config=pipeline_config,
    ).execute()
    return UnifiedInferenceStep(pipeline_config=pipeline_config).execute(
        payloads={"model_handle_builder": model_handle_payload},
    )


__all__ = [
    "UnifiedInferenceStep",
    "UnifiedModelHandleBuilderStep",
    "run_direct_inference",
]
