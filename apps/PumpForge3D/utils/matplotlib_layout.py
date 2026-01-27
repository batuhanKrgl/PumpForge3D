"""Matplotlib layout helpers with version-safe fallbacks."""

from matplotlib.figure import Figure


def apply_layout_to_figure(fig: Figure) -> None:
    """Apply layout in a version-compatible way."""
    try:
        fig.set_constrained_layout(True)
        return
    except Exception:
        pass
    try:
        fig.tight_layout()
    except Exception:
        fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.12, wspace=0.25)
