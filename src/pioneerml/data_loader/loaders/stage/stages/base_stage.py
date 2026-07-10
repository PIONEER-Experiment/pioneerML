from __future__ import annotations

import warnings

from .base_loader_stage import BaseLoaderStage

warnings.warn(
    "pioneerml.data_loader.loaders.stage.stages.base_stage.BaseStage is deprecated; "
    "use pioneerml.data_loader.loaders.stage.stages.base_loader_stage.BaseLoaderStage instead.",
    DeprecationWarning,
    stacklevel=2,
)

BaseStage = BaseLoaderStage

__all__ = ["BaseLoaderStage", "BaseStage"]
