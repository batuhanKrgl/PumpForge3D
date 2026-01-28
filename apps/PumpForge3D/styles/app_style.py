"""Shared UI styling helpers for PumpForge3D tabs and widgets."""

from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QLabel, QPushButton, QGroupBox


GROUP_HEADER_STYLE = """
    QPushButton {
        text-align: left;
        padding: 8px;
        background: #313244;
        border: none;
        border-radius: 4px;
        color: #cdd6f4;
        font-weight: bold;
        font-size: 11px;
    }
    QPushButton:hover {
        background: #45475a;
    }
"""

FORM_LABEL_STYLE = """
    QLabel#FormLabel {
        color: #cdd6f4;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 4px;
    }
"""

NUMERIC_SPINBOX_STYLE = """
    QAbstractSpinBox {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        border-radius: 4px;
        padding: 4px 6px;
        font-size: 11px;
    }
    QAbstractSpinBox:focus {
        border-color: #89b4fa;
    }
"""

COMBOBOX_STYLE = """
    QComboBox {
        background-color: #313244;
        color: #cdd6f4;
        border: 1px solid #45475a;
        padding: 4px 6px;
        font-size: 11px;
        border-radius: 4px;
    }
    QComboBox:hover { background-color: #45475a; }
    QComboBox::drop-down { border: none; }
    QComboBox QAbstractItemView {
        background-color: #313244;
        color: #cdd6f4;
        selection-background-color: #45475a;
    }
"""

GROUPBOX_STYLE = """
    QGroupBox {
        border: 1px solid #45475a;
        border-radius: 4px;
        margin-top: 10px;
        color: #cdd6f4;
        font-weight: 600;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        background-color: #313244;
        color: #cdd6f4;
        border-radius: 3px;
    }
"""

SPLITTER_STYLE = """
    QSplitter::handle {
        background-color: #313244;
    }
"""


def apply_section_header_style(button: QPushButton) -> None:
    button.setStyleSheet(GROUP_HEADER_STYLE)


def apply_form_label_style(label: QLabel) -> None:
    label.setObjectName("FormLabel")
    label.setAutoFillBackground(False)
    label.setStyleSheet(
        FORM_LABEL_STYLE
        + """
        QLabel#FormLabel {
            background: transparent;
            border: none;
        }
        """
    )


def apply_numeric_spinbox_style(spinbox: QAbstractSpinBox) -> None:
    spinbox.setStyleSheet(NUMERIC_SPINBOX_STYLE)


def apply_combobox_style(combo: QComboBox) -> None:
    combo.setStyleSheet(COMBOBOX_STYLE)


def apply_groupbox_style(groupbox: QGroupBox) -> None:
    groupbox.setStyleSheet(GROUPBOX_STYLE)


def apply_splitter_style(splitter) -> None:
    splitter.setStyleSheet(SPLITTER_STYLE)
