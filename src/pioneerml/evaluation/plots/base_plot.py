from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import torch


class BasePlot:
    """Base plot interface."""

    name: str = "base"

    def render(self, *args, **kwargs):
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.render(*args, **kwargs)

    @staticmethod
    def _finalize_figure(
        fig,
        *,
        save_path: Optional[str | Path] = None,
        show: bool = False,
    ) -> str | None:
        """Save/display a figure and then release its pyplot-managed state."""
        resolved_save_path = None if save_path is None else str(save_path)
        if resolved_save_path is not None:
            fig.savefig(resolved_save_path, dpi=150, bbox_inches="tight")

        if show:
            try:
                from IPython import get_ipython
                from IPython.display import Image, display

                shell = get_ipython()
                if shell is not None and shell.__class__.__name__ == "ZMQInteractiveShell":
                    # Emit a concrete image payload. ``display(fig)`` depends on
                    # IPython having registered Matplotlib's rich formatter; without
                    # ``%matplotlib inline`` it falls back to ``<Figure ...>`` text.
                    payload = BytesIO()
                    fig.savefig(payload, format="png", dpi=150, bbox_inches="tight")
                    display(Image(data=payload.getvalue()))
                else:
                    plt.show()
            except Exception:  # pragma: no cover - IPython is optional
                plt.show()

        plt.close(fig)
        return resolved_save_path


def _to_numpy(arr):
    if torch.is_tensor(arr):
        return arr.detach().cpu().numpy()
    if isinstance(arr, (list, tuple)):
        return np.asarray(arr)
    if isinstance(arr, np.ndarray):
        return arr
    raise TypeError(f"Unsupported input type for plotting: {type(arr)}")
