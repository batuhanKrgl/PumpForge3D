"""
Step A: Main Dimensions panel.

Allows the user to define the basic geometry bounds:
- inlet/outlet hub radii
- inlet/outlet tip radii
- axial length
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QDoubleSpinBox, QPushButton, QGroupBox,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.geometry.meridional import MainDimensions


class StepAMainDims(QWidget):
    """
    Step A: Main Dimensions input panel.
    
    Signals:
        dimensions_changed: Emitted when dimensions are applied
    """
    
    dimensions_changed = Signal()
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._setup_ui()
        self._load_from_design()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("Step A: Main Dimensions")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        description = QLabel(
            "Define the basic geometry bounds for the inducer meridional section. "
            "These parameters fix the endpoints of the hub and tip curves."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a6adc8; margin-bottom: 16px;")
        layout.addWidget(description)
        
        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(16)
        
        # Inlet dimensions group
        inlet_group = QGroupBox("Inlet Dimensions (z = 0)")
        inlet_form = QFormLayout(inlet_group)
        inlet_form.setSpacing(12)
        
        self.r_h_in_spin = self._create_spin(0, 1000, "mm", 20)
        inlet_form.addRow("Hub Radius (r_h_in):", self.r_h_in_spin)
        
        self.r_t_in_spin = self._create_spin(0, 1000, "mm", 50)
        inlet_form.addRow("Tip/Shroud Radius (r_t_in):", self.r_t_in_spin)
        
        form_layout.addWidget(inlet_group)
        
        # Outlet dimensions group
        outlet_group = QGroupBox("Outlet Dimensions (z = L)")
        outlet_form = QFormLayout(outlet_group)
        outlet_form.setSpacing(12)
        
        self.r_h_out_spin = self._create_spin(0, 1000, "mm", 30)
        outlet_form.addRow("Hub Radius (r_h_out):", self.r_h_out_spin)
        
        self.r_t_out_spin = self._create_spin(0, 1000, "mm", 45)
        outlet_form.addRow("Tip/Shroud Radius (r_t_out):", self.r_t_out_spin)
        
        form_layout.addWidget(outlet_group)
        
        # Axial length group
        length_group = QGroupBox("Axial Length")
        length_form = QFormLayout(length_group)
        length_form.setSpacing(12)
        
        self.L_spin = self._create_spin(1, 10000, "mm", 80)
        length_form.addRow("Axial Length (L):", self.L_spin)
        
        form_layout.addWidget(length_group)
        
        form_layout.addStretch()
        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(reset_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("background-color: #89b4fa; color: #1e1e2e;")
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_spin(self, min_val: float, max_val: float, suffix: str, default: float) -> QDoubleSpinBox:
        """Create a styled double spin box."""
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(2)
        spin.setSuffix(f" {suffix}")
        spin.setValue(default)
        spin.setMinimumWidth(150)
        return spin
    
    def _load_from_design(self):
        """Load current values from design."""
        dims = self.design.main_dims
        self.r_h_in_spin.setValue(dims.r_h_in)
        self.r_t_in_spin.setValue(dims.r_t_in)
        self.r_h_out_spin.setValue(dims.r_h_out)
        self.r_t_out_spin.setValue(dims.r_t_out)
        self.L_spin.setValue(dims.L)
    
    def _apply(self):
        """Apply the current values to the design."""
        try:
            new_dims = MainDimensions(
                r_h_in=self.r_h_in_spin.value(),
                r_t_in=self.r_t_in_spin.value(),
                r_h_out=self.r_h_out_spin.value(),
                r_t_out=self.r_t_out_spin.value(),
                L=self.L_spin.value(),
            )
            self.design.set_main_dimensions(new_dims)
            self.dimensions_changed.emit()
        except ValueError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Dimensions", str(e))
    
    def _reset_defaults(self):
        """Reset to default dimension values."""
        self.r_h_in_spin.setValue(20)
        self.r_t_in_spin.setValue(50)
        self.r_h_out_spin.setValue(30)
        self.r_t_out_spin.setValue(45)
        self.L_spin.setValue(80)
    
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh."""
        self.design = design
        self._load_from_design()
    
    def refresh(self):
        """Refresh display from current design."""
        self._load_from_design()
