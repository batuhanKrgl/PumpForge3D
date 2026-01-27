from matplotlib.figure import Figure

from apps.PumpForge3D.utils.matplotlib_layout import apply_layout_to_figure


def test_apply_layout_to_figure_no_error() -> None:
    fig = Figure()
    apply_layout_to_figure(fig)
