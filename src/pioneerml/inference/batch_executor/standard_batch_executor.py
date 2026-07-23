from __future__ import annotations

from .base_batch_executor import BaseInferenceBatchExecutor
from .factory.registry import REGISTRY


@REGISTRY.register("standard")
class StandardInferenceBatchExecutor(BaseInferenceBatchExecutor):
    """Default fail-fast inference execution."""

