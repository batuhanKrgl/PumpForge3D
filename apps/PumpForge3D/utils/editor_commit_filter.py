"""Event filters for commit/revert keyboard behavior."""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import QAbstractSpinBox, QLineEdit


class CommitRevertFilter(QObject):
    """Handle Enter to commit and Esc to revert for editors."""

    def __init__(
        self,
        commit_callback: Optional[Callable[[], None]] = None,
        revert_callback: Optional[Callable[[], None]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._commit_callback = commit_callback
        self._revert_callback = revert_callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt naming
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._commit_callback:
                    self._commit_callback()
                else:
                    if hasattr(watched, "clearFocus"):
                        watched.clearFocus()
                return True
            if key == Qt.Key.Key_Escape:
                if self._revert_callback:
                    self._revert_callback()
                else:
                    self._restore_last_valid(watched)
                return True
        return super().eventFilter(watched, event)

    @staticmethod
    def _restore_last_valid(watched: QObject) -> None:
        last_valid = watched.property("last_valid_value")
        if last_valid is None:
            return
        if isinstance(watched, QLineEdit):
            watched.setText(str(last_valid))
            watched.selectAll()
        elif isinstance(watched, QAbstractSpinBox):
            watched.setValue(float(last_valid))
            watched.lineEdit().selectAll()


def attach_commit_filter(
    widget: QObject,
    *,
    commit_callback: Optional[Callable[[], None]] = None,
    revert_callback: Optional[Callable[[], None]] = None,
) -> CommitRevertFilter:
    """Attach a commit/revert filter to a widget and return it."""

    filt = CommitRevertFilter(commit_callback, revert_callback, parent=widget)
    widget.installEventFilter(filt)
    return filt
