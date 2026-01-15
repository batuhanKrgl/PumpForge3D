"""
Numeric input dialog for control point coordinates.

CFturbo-inspired: right-click on a control point opens
a small dialog for entering exact coordinates.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QDoubleSpinBox, QPushButton, QWidget
)
from PySide6.QtCore import Qt, Signal
from typing import Tuple


class NumericInputDialog(QDialog):
    """
    Dialog for entering control point coordinates.
    
    Shows input fields for Z (axial) and R (radial) coordinates.
    """
    
    coordinates_accepted = Signal(float, float)
    
    def __init__(
        self,
        current_z: float,
        current_r: float,
        point_name: str = "Point",
        parent=None
    ):
        super().__init__(parent)
        
        self.setWindowTitle(f"Edit {point_name}")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Popup
        )
        self.setMinimumWidth(200)
        
        self._setup_ui(current_z, current_r, point_name)
    
    def _setup_ui(self, current_z: float, current_r: float, point_name: str):
        """Create the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title
        title = QLabel(f"<b>{point_name} Coordinates</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Form
        form = QFormLayout()
        form.setSpacing(8)
        
        # Z coordinate
        self.z_spin = QDoubleSpinBox()
        self.z_spin.setRange(-1000, 10000)
        self.z_spin.setDecimals(3)
        self.z_spin.setSuffix(" mm")
        self.z_spin.setValue(current_z)
        self.z_spin.setMinimumWidth(120)
        form.addRow("Z (axial):", self.z_spin)
        
        # R coordinate
        self.r_spin = QDoubleSpinBox()
        self.r_spin.setRange(0, 10000)
        self.r_spin.setDecimals(3)
        self.r_spin.setSuffix(" mm")
        self.r_spin.setValue(current_r)
        self.r_spin.setMinimumWidth(120)
        form.addRow("R (radial):", self.r_spin)
        
        layout.addLayout(form)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Focus on Z field
        self.z_spin.setFocus()
        self.z_spin.selectAll()
    
    def _apply(self):
        """Apply the new coordinates."""
        z = self.z_spin.value()
        r = self.r_spin.value()
        self.coordinates_accepted.emit(z, r)
        self.accept()
    
    def get_values(self) -> Tuple[float, float]:
        """Get the entered coordinate values."""
        return (self.z_spin.value(), self.r_spin.value())
    
    @staticmethod
    def get_coordinates(
        current_z: float,
        current_r: float,
        point_name: str = "Point",
        parent=None
    ) -> Tuple[bool, float, float]:
        """
        Static method to show dialog and get coordinates.
        
        Returns:
            Tuple of (accepted, z, r)
        """
        dialog = NumericInputDialog(current_z, current_r, point_name, parent)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            z, r = dialog.get_values()
            return (True, z, r)
        return (False, current_z, current_r)
