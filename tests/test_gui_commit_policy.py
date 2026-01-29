import pytest

pytest.importorskip("PySide6", reason="PySide6 is required for GUI tests.", exc_type=ImportError)
pytest.importorskip("PySide6.QtTest", reason="QtTest backend requires system libraries.", exc_type=ImportError)

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy

from apps.PumpForge3D.tabs.design_tab import DesignTab
from apps.PumpForge3D.widgets.blade_properties_widgets import BladeInputsWidget, BladeThicknessMatrixWidget
from apps.PumpForge3D.widgets.commit_slider import CommitSlider
from pumpforge3d_core.geometry.inducer import InducerDesign


def test_editing_finished_commits_blade_count(qtbot):
    widget = BladeInputsWidget()
    qtbot.addWidget(widget)

    line_edit = widget.blade_count_spin.spinbox.lineEdit()
    line_edit.setFocus()
    line_edit.selectAll()

    with qtbot.waitSignal(widget.bladeCountChanged, timeout=1000) as blocker:
        qtbot.keyClicks(line_edit, "7")
        qtbot.keyPress(line_edit, Qt.Key_Return)

    assert blocker.args[0] == 7


def test_invalid_thickness_input_marks_error(qtbot):
    widget = BladeThicknessMatrixWidget()
    qtbot.addWidget(widget)

    original = widget.get_thickness().hub_inlet
    item = widget.table.item(0, 0)
    item.setText("abc")

    assert widget.get_thickness().hub_inlet == pytest.approx(original)
    assert widget.error_label.isVisible()
    assert "⚠" in widget.error_label.text()
    assert widget.table.property("error") is True


def test_slider_drag_throttles_and_commits_once(qtbot):
    slider = CommitSlider(Qt.Orientation.Horizontal)
    qtbot.addWidget(slider)
    slider.setRange(0, 100)

    preview_spy = QSignalSpy(slider.previewChanged)
    commit_spy = QSignalSpy(slider.valueCommitted)

    slider.setSliderDown(True)
    slider.setValue(10)
    slider.setValue(25)
    slider.setValue(40)

    qtbot.waitUntil(lambda: len(preview_spy) >= 1, timeout=1000)

    slider.setSliderDown(False)
    slider.sliderReleased.emit()

    qtbot.waitUntil(lambda: len(commit_spy) == 1, timeout=1000)

    assert slider.value() == 40
    assert len(commit_spy) == 1
    assert len(preview_spy) <= 2


def test_separate_length_toggle_enables_tip(qtbot):
    design = InducerDesign.create_default()
    tab = DesignTab(design)
    qtbot.addWidget(tab)

    assert not tab.L_tip_spin.isEnabled()
    qtbot.mouseClick(tab.separate_L_check, Qt.MouseButton.LeftButton)
    assert tab.L_tip_spin.isEnabled()
