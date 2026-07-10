from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from .base_loader_stage import BaseLoaderStage


class BaseTargetStage(BaseLoaderStage):
    """Base stage for target construction."""

    provides: tuple[str, ...] = ()

    @staticmethod
    def include_targets(*, owner, state: MutableMapping[str, Any]) -> bool:
        _ = state
        return bool(getattr(owner, "include_targets", False))
