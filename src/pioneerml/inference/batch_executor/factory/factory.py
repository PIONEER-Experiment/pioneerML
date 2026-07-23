from __future__ import annotations

from pioneerml.plugin import NamespacedPluginFactory

from ..base_batch_executor import BaseInferenceBatchExecutor


class InferenceBatchExecutorFactory(NamespacedPluginFactory[BaseInferenceBatchExecutor]):
    def __init__(
        self,
        *,
        executor_cls: type[BaseInferenceBatchExecutor] | None = None,
        executor_name: str | None = None,
        config: dict | None = None,
    ) -> None:
        super().__init__(
            namespace="inference_batch_executor",
            plugin_cls=executor_cls,
            plugin_name=executor_name,
            expected_instance_type=BaseInferenceBatchExecutor,
            label="Inference batch executor",
            base_config=config,
        )
