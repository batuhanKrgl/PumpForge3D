"""Slider with throttled preview and commit-on-release behavior."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import QSlider


class CommitSlider(QSlider):
    """QSlider that throttles preview updates and commits on release."""

    previewChanged = Signal(int)
    valueCommitted = Signal(int)

    def __init__(self, orientation: Qt.Orientation = Qt.Orientation.Horizontal, parent=None) -> None:
        super().__init__(orientation, parent)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._emit_preview)
        self.valueChanged.connect(self._schedule_preview)
        self.sliderReleased.connect(self._emit_commit)

    def _schedule_preview(self, value: int) -> None:
        self._pending_value = value
        if self.isSliderDown():
            if self._preview_timer.isActive():
                self._preview_timer.stop()
            self._preview_timer.start()
        else:
            self.previewChanged.emit(value)

    def _emit_preview(self) -> None:
        value = getattr(self, "_pending_value", self.value())
        self.previewChanged.emit(value)

    def _emit_commit(self) -> None:
        self._preview_timer.stop()
        self.valueCommitted.emit(self.value())
