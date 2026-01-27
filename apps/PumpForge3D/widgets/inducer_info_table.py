"""Inducer info table model and widget."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class InducerInfoRow:
    key: str
    label: str
    tooltip: str


ROWS = [
    InducerInfoRow("z", "z", "Axial position"),
    InducerInfoRow("r", "r", "Radial coordinate"),
    InducerInfoRow("d", "d", "Diameter"),
    InducerInfoRow("αF", "αF", "Angle of absolute flow to circumferential direction"),
    InducerInfoRow("βF", "βF", "Angle of relative flow to circumferential direction"),
    InducerInfoRow("u", "u", "Circumferential velocity"),
    InducerInfoRow("c_m", "cₘ", "Meridional velocity (cₘ = wₘ)"),
    InducerInfoRow("c_u", "cᵤ", "Circumferential component of absolute velocity"),
    InducerInfoRow("c_r", "cᵣ", "Radial component of absolute velocity"),
    InducerInfoRow("c_z", "c_z", "Axial component of absolute velocity"),
    InducerInfoRow("c", "c", "Absolute velocity"),
    InducerInfoRow("w_u", "wᵤ", "Circumferential component of relative velocity"),
    InducerInfoRow("w", "w", "Relative velocity"),
    InducerInfoRow("τ", "τ", "Obstruction by blades"),
    InducerInfoRow("i | δ", "i | δ", "Incidence i = β₁B − β₁ (LE), deviation δ = β₂B − β₂ (TE)"),
    InducerInfoRow("w₂/w₁", "w₂/w₁", "Deceleration ratio of relative velocity"),
    InducerInfoRow("c₂/c₁", "c₂/c₁", "Absolute velocity ratio"),
    InducerInfoRow("ΔαF", "ΔαF", "Absolute deflection angle: αF₂ − αF₁"),
    InducerInfoRow("ΔβF", "ΔβF", "Relative deflection angle: βF₂ − βF₁"),
    InducerInfoRow("φ=ΔβB", "φ=ΔβB", "Blade camber angle: β₂B − β₁B"),
    InducerInfoRow("γ", "γ", "Slip coefficient"),
    InducerInfoRow("Δ(c_u·r)", "Δ(cᵤ·r)", "Swirl difference"),
    InducerInfoRow("T", "T", "Torque"),
    InducerInfoRow("H/Δp_t", "H/Δp_t", "Head/pressure difference (total-total)"),
]


ANGLE_KEYS = {"αF", "βF", "ΔαF", "ΔβF", "φ=ΔβB"}
PAIR_KEYS = {"w₂/w₁", "c₂/c₁", "ΔαF", "ΔβF", "φ=ΔβB", "γ", "Δ(c_u·r)", "T", "H/Δp_t"}


class InducerInfoTableModel(QAbstractTableModel):
    """Table model for Inducer info snapshot data."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._snapshot: dict[str, Any] = {"columns": [], "rows": {}}

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.beginResetModel()
        self._snapshot = snapshot
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(ROWS)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 4

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = ROWS[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return self._format_value(row.key, index.column())
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            return None
        if orientation == Qt.Orientation.Vertical:
            row = ROWS[section]
            return row.tooltip if role == Qt.ItemDataRole.ToolTipRole else row.label
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return [
                "Leading edge\n@Hub",
                "Trailing edge\n@Hub",
                "Leading edge\n@Shroud",
                "Trailing edge\n@Shroud",
            ][section]
        return None

    def _format_value(self, key: str, column: int) -> str:
        rows = self._snapshot.get("rows", {})
        if key == "i | δ":
            value = rows.get("i", [None] * 4)[column] if column in (0, 2) else rows.get("δ", [None] * 4)[column]
            return self._format_angle(value)
        if key == "H/Δp_t":
            if column in (0, 2):
                idx = 1 if column == 0 else 3
                h = rows.get("H_euler", [None] * 4)[idx]
                dp = rows.get("Δp_t", [None] * 4)[idx]
                if h is None or dp is None:
                    return "—"
                return f"H={h:.2f} m / Δp={dp:.2f} bar"
            return "—"
        if key in PAIR_KEYS:
            if column in (0, 2):
                idx = 1 if column == 0 else 3
                value = rows.get(key, [None] * 4)[idx]
            else:
                return "—"
        else:
            value = rows.get(key, [None] * 4)[column]
        if value is None:
            return "—"
        if key in ANGLE_KEYS:
            return self._format_angle(value)
        if key in {"w₂/w₁", "c₂/c₁"}:
            return f"{value:.3f}"
        if key in {"γ"}:
            return f"{value:.3f}"
        if key in {"Δ(c_u·r)", "T"}:
            return f"{value:.3f}"
        return f"{value:.2f}"

    @staticmethod
    def _format_angle(value: Optional[float]) -> str:
        if value is None:
            return "—"
        return f"{math.degrees(value):.2f}"


class InducerInfoLegendDialog(QDialog):
    """Dialog showing Inducer info legend text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Inducer Info Legend")
        layout = QVBoxLayout(self)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            "z  Axial position\n"
            "r  Radial coordinate\n"
            "d  Diameter\n"
            "αF Angle of absolute flow to circumferential direction\n"
            "βF Angle of relative flow to circumferential direction\n"
            "u  Circumferential velocity\n"
            "cₘ Meridional velocity (cₘ = wₘ)\n"
            "cᵤ Circumferential component of absolute velocity\n"
            "cᵣ Radial component of absolute velocity\n"
            "c_z Axial component of absolute velocity\n"
            "c  Absolute velocity\n"
            "wᵤ Circumferential component of relative velocity\n"
            "w  Relative velocity\n"
            "τ  Obstruction by blades\n"
            "i  Incidence angle: i = β₁B − β₁\n"
            "δ  Deviation angle: δ = β₂B − β₂\n"
            "w₂/w₁ Deceleration ratio of relative velocity\n"
            "c₂/c₁ Absolute velocity ratio\n"
            "ΔαF Absolute deflection angle: αF₂ − αF₁\n"
            "ΔβF Relative deflection angle: βF₂ − βF₁\n"
            "φ=ΔβB Blade camber angle: φ = β₂B − β₁B\n"
            "γ  Slip coefficient\n"
            "Δ(cᵤ·r) Swirl difference\n"
            "T  Torque\n"
            "H/Δp_t Head/pressure difference (total-total)\n"
        )
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class InducerInfoTableWidget(QWidget):
    """Widget wrapper for the Inducer info table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        header_label = QLabel("Inducer Info")
        header_label.setStyleSheet("font-weight: bold; color: #89b4fa;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        info_btn = QToolButton()
        info_btn.setText("ℹ")
        info_btn.setToolTip("Legend")
        info_btn.clicked.connect(self._show_legend)
        header_layout.addWidget(info_btn)
        layout.addLayout(header_layout)

        self._model = InducerInfoTableModel(self)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setAlternatingRowColors(True)

        glyph_font = QFont("Segoe UI Symbol")
        if not glyph_font.exactMatch():
            glyph_font = QFont("DejaVu Sans")
        self._table.setFont(glyph_font)
        self._table.horizontalHeader().setFont(glyph_font)
        self._table.verticalHeader().setFont(glyph_font)

        layout.addWidget(self._table)
        self._apply_spans()

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._model.set_snapshot(snapshot)
        self._apply_spans()

    def _show_legend(self) -> None:
        dialog = InducerInfoLegendDialog(self)
        dialog.exec()

    def _apply_spans(self) -> None:
        for row_index, row in enumerate(ROWS):
            if row.key in PAIR_KEYS or row.key == "H/Δp_t":
                self._table.setSpan(row_index, 0, 1, 2)
                self._table.setSpan(row_index, 2, 1, 2)
