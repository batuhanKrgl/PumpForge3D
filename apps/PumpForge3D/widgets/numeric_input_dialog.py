"""
Coordinate edit popup for control points.

CFturbo-inspired: right-click on a control point opens
a styled popup for entering exact coordinates and angle lock settings.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QDoubleSpinBox, QPushButton, QWidget, QCheckBox,
    QFrame, QAbstractSpinBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from typing import Tuple, Optional


class NumericInputDialog(QDialog):
    """
    Styled dialog for editing control point coordinates and angle lock.
    
    Shows input fields for Z (axial) and R (radial) coordinates,
    plus angle lock controls for inlet/outlet constraints.
    """
    
    coordinates_accepted = Signal(float, float)
    applied = Signal(dict)
    
    def __init__(
        self,
        current_z: float,
        current_r: float,
        point_name: str = "Point",
        curve_name: str = "hub",
        point_index: int = 0,
        angle_locked: bool = False,
        angle_value: float = 0.0,
        parent=None,
        fields: Optional[list[dict]] = None,
        dialog_title: Optional[str] = None,
    ):
        super().__init__(parent)

        self.curve_name = curve_name
        self.point_index = point_index
        self._angle_locked = angle_locked
        self._angle_value = angle_value
        self.angle_spin = None  # Will be created in _setup_ui if needed
        self._fields = fields
        self._field_spins: dict[str, QDoubleSpinBox] = {}

        title = dialog_title or f"Edit {point_name}"
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Popup
        )
        self.setMinimumWidth(240)
        
        # Dark theme styling with border
        self.setStyleSheet("""
            QDialog {
                background: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 8px;
            }
            QLabel {
                color: #cdd6f4;
            }
            QDoubleSpinBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QDoubleSpinBox:disabled {
                background: #1e1e2e;
                color: #6c7086;
            }
            QPushButton {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #45475a;
            }
            QPushButton:pressed {
                background: #585b70;
            }
            QPushButton#apply_btn {
                background: #89b4fa;
                color: #1e1e2e;
                border: none;
            }
            QPushButton#apply_btn:hover {
                background: #b4befe;
            }
            QCheckBox {
                color: #a6adc8;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        if self._fields:
            self._setup_fields_ui(point_name)
        else:
            self._setup_ui(current_z, current_r, point_name)

    def _setup_fields_ui(self, point_name: str) -> None:
        """Create a dialog UI for generic numeric fields."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"<b>{point_name}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 13px; color: #89b4fa;")
        layout.addWidget(title)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background: #45475a;")
        layout.addWidget(sep1)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for field in self._fields or []:
            key = field["key"]
            label = field.get("label", key)
            spin = QDoubleSpinBox()
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setRange(field.get("min", -1e9), field.get("max", 1e9))
            spin.setDecimals(field.get("decimals", 2))
            if "suffix" in field:
                spin.setSuffix(field["suffix"])
            if "step" in field:
                spin.setSingleStep(field["step"])
            spin.setValue(field.get("value", 0.0))
            spin.setFixedWidth(field.get("width", 120))
            self._field_spins[key] = spin
            form.addRow(label, spin)

        layout.addLayout(form)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: #45475a;")
        layout.addWidget(sep2)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("apply_btn")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

        if self._field_spins:
            first_spin = next(iter(self._field_spins.values()))
            first_spin.setFocus()
            first_spin.selectAll()

    def _setup_ui(self, current_z: float, current_r: float, point_name: str):
        """Create the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel(f"<b>{point_name}</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 13px; color: #89b4fa;")
        layout.addWidget(title)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background: #45475a;")
        layout.addWidget(sep1)
        
        # Coordinates section
        coord_label = QLabel("Coordinates")
        coord_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #a6adc8;")
        layout.addWidget(coord_label)
        
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Z coordinate - styled spinbox (no arrows)
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.z_spin.setRange(-1000, 10000)
        self.z_spin.setDecimals(2)
        self.z_spin.setSuffix(" mm")
        self.z_spin.setValue(current_z)
        self.z_spin.setFixedWidth(100)
        form.addRow("Z (axial):", self.z_spin)
        
        # R coordinate
        self.r_spin = QDoubleSpinBox()
        self.r_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.r_spin.setRange(0, 10000)
        self.r_spin.setDecimals(2)
        self.r_spin.setSuffix(" mm")
        self.r_spin.setValue(current_r)
        self.r_spin.setFixedWidth(100)
        form.addRow("R (radial):", self.r_spin)
        
        layout.addLayout(form)
        
        # Angle Lock section (only for P1 and P3)
        if self.point_index in [1, 3]:
            sep2 = QFrame()
            sep2.setFrameShape(QFrame.Shape.HLine)
            sep2.setStyleSheet("background: #45475a;")
            layout.addWidget(sep2)
            
            lock_label = QLabel("Tangent Constraint")
            lock_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #a6adc8;")
            layout.addWidget(lock_label)
            
            # Lock checkbox
            self.angle_lock_check = QCheckBox("Lock tangent angle")
            self.angle_lock_check.setChecked(self._angle_locked)
            self.angle_lock_check.toggled.connect(self._on_angle_lock_toggled)
            layout.addWidget(self.angle_lock_check)
            
            # Angle value form - always visible, editable when locked
            angle_form = QFormLayout()
            angle_form.setSpacing(4)
            self.angle_spin = QDoubleSpinBox()
            self.angle_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self.angle_spin.setRange(-90, 90)
            self.angle_spin.setDecimals(1)
            self.angle_spin.setSuffix("°")
            self.angle_spin.setValue(self._angle_value)
            self.angle_spin.setFixedWidth(80)
            # Always visible, but only editable when locked
            self.angle_spin.setReadOnly(not self._angle_locked)
            if not self._angle_locked:
                self.angle_spin.setStyleSheet("color: #6c7086;")  # Greyed out
            angle_form.addRow("Angle:", self.angle_spin)
            layout.addLayout(angle_form)
            
            hint = QLabel("Locks CP movement to fixed angle from endpoint")
            hint.setStyleSheet("font-size: 10px; color: #6c7086;")
            hint.setWordWrap(True)
            layout.addWidget(hint)
        else:
            self.angle_lock_check = None
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        sep3.setStyleSheet("background: #45475a;")
        layout.addWidget(sep3)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("apply_btn")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Focus on Z field
        self.z_spin.setFocus()
        self.z_spin.selectAll()
    
    def _apply(self):
        """Apply the new coordinates."""
        if self._fields:
            payload = self.get_field_values()
            self.applied.emit(payload)
            self.accept()
            return
        z = self.z_spin.value()
        r = self.r_spin.value()
        self.coordinates_accepted.emit(z, r)
        self.applied.emit({"z": z, "r": r})
        self.accept()
    
    def _on_angle_lock_toggled(self, checked: bool):
        """Enable/disable angle spinbox based on lock state."""
        if self.angle_spin:
            self.angle_spin.setReadOnly(not checked)
            if checked:
                self.angle_spin.setStyleSheet("")  # Normal
            else:
                self.angle_spin.setStyleSheet("color: #6c7086;")  # Greyed out
    
    def get_values(self) -> Tuple[float, float]:
        """Get the entered coordinate values."""
        return (self.z_spin.value(), self.r_spin.value())

    def get_field_values(self) -> dict:
        """Get the entered field values."""
        return {key: spin.value() for key, spin in self._field_spins.items()}
    
    def get_angle_locked(self) -> bool:
        """Get the angle lock state."""
        if self.angle_lock_check:
            return self.angle_lock_check.isChecked()
        return self._angle_locked
    
    def get_angle_value(self) -> float:
        """Get the angle value."""
        if self.angle_spin:
            return self.angle_spin.value()
        return self._angle_value
    
    @staticmethod
    def get_coordinates(
        current_z: float,
        current_r: float,
        point_name: str = "Point",
        parent=None,
        curve_name: str = "hub",
        point_index: int = 0,
        angle_locked: bool = False,
        angle_value: float = 0.0
    ) -> Tuple[bool, float, float, bool, float]:
        """
        Static method to show dialog and get coordinates.
        
        Returns:
            Tuple of (accepted, z, r, angle_locked, angle_value)
        """
        dialog = NumericInputDialog(
            current_z, current_r, point_name, 
            curve_name, point_index, angle_locked, angle_value, parent
        )
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            z, r = dialog.get_values()
            return (True, z, r, dialog.get_angle_locked(), dialog.get_angle_value())
        return (False, current_z, current_r, angle_locked, angle_value)
