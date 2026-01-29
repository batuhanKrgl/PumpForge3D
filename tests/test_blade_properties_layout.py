import pytest

pytest.importorskip("PySide6", reason="PySide6 is required for GUI tests.", exc_type=ImportError)
pytest.importorskip("pytestqt", reason="pytest-qt is required for GUI tests.", exc_type=ImportError)

from apps.PumpForge3D.tabs.blade_properties_tab import BladePropertiesTab
from apps.PumpForge3D.widgets.velocity_triangle_widget import VelocityTriangleWidget


def _expected_table_height(table) -> int:
    header_height = table.horizontalHeader().sizeHint().height()
    rows_height = sum(
        max(table.rowHeight(row), table.sizeHintForRow(row))
        for row in range(table.rowCount())
    )
    frame = table.frameWidth() * 2
    return header_height + rows_height + frame


def test_thickness_table_height_matches_rows(qtbot):
    tab = BladePropertiesTab()
    qtbot.addWidget(tab)
    tab.resize(900, 600)
    tab.show()

    table = tab.thickness_widget.table
    qtbot.waitUntil(lambda: table.height() > 0, timeout=1000)

    assert table.height() == _expected_table_height(table)


def test_velocity_triangle_legend_not_overlapping_toolbar(qtbot):
    widget = VelocityTriangleWidget()
    qtbot.addWidget(widget)
    widget.resize(700, 400)
    widget.show()

    qtbot.waitUntil(lambda: widget.toolbar.geometry().height() > 0, timeout=1000)

    toolbar_rect = widget.toolbar.geometry()
    legend_rect = widget.legend_row.geometry()

    assert not toolbar_rect.intersects(legend_rect)
    assert legend_rect.top() >= toolbar_rect.bottom()


def test_blade_properties_plain_labels(qtbot):
    tab = BladePropertiesTab()
    qtbot.addWidget(tab)
    tab.show()

    assert tab.triangle_info_label.property("role") == "plain"
    assert "background-color" not in tab.triangle_info_label.styleSheet()

    legend_labels = tab.triangle_widget.legend_widget.findChildren(type(tab.triangle_info_label))
    assert legend_labels, "Legend labels should exist."
    for label in legend_labels:
        assert label.property("role") == "plain"
        assert "background-color" not in label.styleSheet()
