from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import numpy as np
import pyarrow as pa

from .base_loader_stage import BaseLoaderStage


class RowShuffleStage(BaseLoaderStage):
    """Shuffle surviving rows before loader-specific tensor packing."""

    name = "row_shuffle"
    requires = ("table",)
    provides = ("table",)

    def __init__(
        self,
        *,
        enabled: bool = True,
        runtime_flag_key: str = "shuffle_within_batch",
    ) -> None:
        self.enabled = bool(enabled)
        self.runtime_flag_key = str(runtime_flag_key)

    def run_loader(self, *, state: MutableMapping[str, Any], owner) -> None:
        _ = owner
        if not self.enabled:
            return
        if self.runtime_flag_key and not bool(state.get(self.runtime_flag_key, False)):
            return

        table = state.get("table")
        if table is None or int(table.num_rows) == 0:
            state["table"] = None
            state["chunk_out"] = None
            state["stop_pipeline"] = True
            return

        n_rows = int(table.num_rows)
        if n_rows <= 1:
            return

        perm = np.random.permutation(n_rows).astype(np.int64, copy=False)
        state["table"] = table.take(pa.array(perm, type=pa.int64())).combine_chunks()
