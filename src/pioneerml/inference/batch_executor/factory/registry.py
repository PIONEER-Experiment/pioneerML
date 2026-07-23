from __future__ import annotations

from pioneerml.plugin import NamespacedPluginRegistry

from ..base_batch_executor import BaseInferenceBatchExecutor

REGISTRY = NamespacedPluginRegistry[type[BaseInferenceBatchExecutor]](
    namespace="inference_batch_executor",
    expected_type=BaseInferenceBatchExecutor,
    label="Inference batch executor plugin",
)
