from __future__ import annotations

import torch

from pioneerml.inference import BaseInferenceBatchExecutor, InferenceBatchContext

from .payloads import InferenceStepPayload
from .resolvers import InferenceConfigResolver, InferenceStateResolver
from ..base_model_runner_step import BaseModelRunnerStep
from ..utils import merge_nested_dicts


class BaseInferenceStep(BaseModelRunnerStep):
    DEFAULT_CONFIG = merge_nested_dicts(
        base=BaseModelRunnerStep.DEFAULT_CONFIG,
        override={
            "runtime": {
                "prefer_cuda": True,
            },
            "batch_executor": {"type": "standard", "config": {}},
            "writer": {
                "type": "required",
                "config": {
                    "output_backend": {
                        "type": "parquet",
                        "config": {
                            "target_row_group_rows": 1024,
                        },
                    },
                    "fallback_output_dir": "data/inference",
                    "output_dir": None,
                    "output_path": None,
                    "streaming": True,
                    "write_timestamped": False,
                    "timestamp": None,
                    "writer_params": {},
                },
            },
            "loader_manager": {
                "config": {
                    "defaults": {
                        "type": "group_classifier",
                        "config": {
                            "mode": "inference",
                            "batch_size": 64,
                            "chunk_row_groups": 4,
                            "chunk_workers": 0,
                            "sample_fraction": 1.0,
                            "split_seed": 0,
                        },
                    },
                    "loaders": {
                        "inference_loader": {
                            "config": {
                                "mode": "inference",
                                "shuffle_batches": False,
                                "shuffle_within_batch": False,
                                "log_diagnostics": False,
                            },
                        },
                    },
                },
            },
        },
    )
    config_resolver_classes = BaseModelRunnerStep.config_resolver_classes + (InferenceConfigResolver,)
    payload_resolver_classes = BaseModelRunnerStep.payload_resolver_classes + (InferenceStateResolver,)

    def _execute(self, *, inputs: dict | None = None) -> InferenceStepPayload:
        _ = inputs
        cfg = dict(self.config_json)

        runtime = self.runtime_state.get("inference_runtime")
        if not isinstance(runtime, dict):
            raise RuntimeError("Inference runtime_state missing valid 'inference_runtime'.")

        writer = runtime.get("writer")
        batch_executor = runtime.get("batch_executor")
        source_items = runtime.get("source_items")
        if writer is None or not hasattr(writer, "on_start"):
            raise RuntimeError("Inference runtime missing valid writer object.")
        if not isinstance(source_items, list):
            raise RuntimeError("Inference runtime missing valid source_items list.")
        if not isinstance(batch_executor, BaseInferenceBatchExecutor):
            raise RuntimeError("Inference runtime missing valid batch_executor.")

        writer_cfg = writer.run_config
        chunk_output_path = runtime.get("output_path") if len(source_items) == 1 else None

        start_state = {
            "source_contexts": [{"src_path": str(i["src_path"]), "num_rows": int(i["num_rows"])} for i in source_items],
            "output_dir": writer_cfg.output_dir,
            "output_path": runtime.get("output_path"),
            "write_timestamped": bool(writer_cfg.write_timestamped),
            "timestamp": writer_cfg.timestamp,
            "streaming": bool(writer_cfg.streaming),
        }
        writer.on_start(state=start_state)

        shuffle_batches = bool(runtime.get("shuffle_batches", False))
        shuffle_within_batch = bool(runtime.get("shuffle_within_batch", True))
        model = runtime.get("model")
        device = runtime.get("device")
        with torch.no_grad():
            for source_item in source_items:
                source_loader = source_item.get("loader")
                if source_loader is None or not hasattr(source_loader, "make_dataloader"):
                    raise RuntimeError("Inference runtime source item missing valid loader provider.")
                if not hasattr(source_loader, "build_inference_model_input"):
                    raise RuntimeError(
                        "Inference source loader must implement build_inference_model_input(...)."
                    )
                if not hasattr(writer, "build_prediction_set"):
                    raise RuntimeError("Inference writer must implement build_prediction_set(...).")

                source_context = InferenceBatchContext(
                    batch=None,
                    loader=source_loader,
                    model=model,
                    writer=writer,
                    device=device,
                    source_path=source_item["src_path"],
                    source_num_rows=int(source_item["num_rows"]),
                    config=cfg,
                    output_dir=writer_cfg.output_dir,
                    output_path=chunk_output_path,
                    write_timestamped=bool(writer_cfg.write_timestamped),
                    timestamp=writer_cfg.timestamp,
                )

                try:
                    batches = iter(
                        source_loader.make_dataloader(
                            shuffle_batches=shuffle_batches,
                            shuffle_within_batch=shuffle_within_batch,
                        )
                    )
                except Exception as error:
                    batch_executor.handle_loader_failure(context=source_context, error=error)
                    continue

                while True:
                    try:
                        batch = next(batches)
                    except StopIteration:
                        break
                    except Exception as error:
                        batch_executor.handle_loader_failure(context=source_context, error=error)
                        break
                    batch_executor.execute_batch(context=source_context.with_batch(batch))

        finalized = writer.on_finalize(state=start_state)
        run_outputs = dict(finalized.get("run_outputs") or {})
        prediction_paths = [str(path) for path in run_outputs.get("predictions_paths") or []]
        timestamped_prediction_paths = [str(path) for path in run_outputs.get("timestamped_predictions_paths") or []]

        return InferenceStepPayload(
            predictions_path=prediction_paths[0] if len(prediction_paths) == 1 else None,
            predictions_paths=prediction_paths,
            timestamped_predictions_path=(
                timestamped_prediction_paths[0] if len(timestamped_prediction_paths) == 1 else None
            ),
            timestamped_predictions_paths=timestamped_prediction_paths,
        )
