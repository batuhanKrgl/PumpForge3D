"""
Velocity Triangle Parameters Window.

A non-modal, always-visible window for inputting velocity triangle calculation parameters.
This is a mock implementation - these parameters will eventually come from the Design tab.

Parameters:
- n: Rotational speed (RPM)
- Q: Flow rate (L/s)
- α₁: Inlet flow angle (degrees)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QPushButton,
    QSizePolicy, QGroupBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon

# Import StyledSpinBox from blade_properties_widgets
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from blade_properties_widgets import StyledSpinBox


class VelocityTriangleParamsWindow(QWidget):
    """
    Non-modal parameter input window for velocity triangle calculations.

    Signals:
        parametersChanged: Emitted when any parameter changes
    """

    parametersChanged = Signal(dict)  # {'n': float, 'Q': float, 'alpha1': float}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Velocity Triangle Parameters")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

        # Default values
        self._rpm = 3000.0
        self._flow_rate_lps = 10.0  # L/s
        self._alpha1_deg = 90.0

        self._setup_ui()
        self._connect_signals()

        # Set size constraints
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)

    def _setup_ui(self):
        """Setup the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Apply dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-size: 10px;
            }
            QGroupBox {
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 11px;
                font-weight: bold;
                color: #89b4fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                left: 10px;
            }
        """)

        # Info label
        info_label = QLabel("⚠ Mock Parameters")
        info_label.setStyleSheet("""
            color: #f9e2af;
            background-color: #313244;
            padding: 8px;
            border-radius: 4px;
            font-size: 10px;
        """)
        info_label.setWordWrap(True)
        info_label.setText(
            "⚠ These are temporary input values.\n"
            "In the final version, these will be calculated automatically "
            "from the Design tab geometry."
        )
        main_layout.addWidget(info_label)

        # Parameters group
        params_group = QGroupBox("Operating Conditions")
        params_layout = QFormLayout(params_group)
        params_layout.setSpacing(10)
        params_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        # Helper to create labels (9px, right-aligned)
        def create_label(text):
            label = QLabel(text)
            label.setStyleSheet("color: #cdd6f4; font-size: 9px;")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return label

        # RPM (n)
        self.rpm_spin = StyledSpinBox()
        self.rpm_spin.setRange(100.0, 20000.0)
        self.rpm_spin.setDecimals(0)
        self.rpm_spin.setSingleStep(100.0)
        self.rpm_spin.setSuffix(" RPM")
        self.rpm_spin.setValue(self._rpm)
        params_layout.addRow(create_label("Rotational speed n:"), self.rpm_spin)

        # Flow rate Q (L/s)
        self.flow_rate_spin = StyledSpinBox()
        self.flow_rate_spin.setRange(0.1, 1000.0)
        self.flow_rate_spin.setDecimals(2)
        self.flow_rate_spin.setSingleStep(0.5)
        self.flow_rate_spin.setSuffix(" L/s")
        self.flow_rate_spin.setValue(self._flow_rate_lps)
        params_layout.addRow(create_label("Flow rate Q:"), self.flow_rate_spin)

        # Inlet flow angle α₁
        self.alpha1_spin = StyledSpinBox()
        self.alpha1_spin.setRange(0.0, 180.0)
        self.alpha1_spin.setDecimals(1)
        self.alpha1_spin.setSingleStep(1.0)
        self.alpha1_spin.setSuffix("°")
        self.alpha1_spin.setValue(self._alpha1_deg)
        params_layout.addRow(create_label("Inlet angle α₁:"), self.alpha1_spin)

        main_layout.addWidget(params_group)

        # Geometry info group (read-only display)
        geom_group = QGroupBox("Geometry (from Design tab)")
        geom_layout = QFormLayout(geom_group)
        geom_layout.setSpacing(6)

        self.r_hub_label = QLabel("--")
        self.r_hub_label.setStyleSheet("color: #a6adc8; font-size: 9px;")
        geom_layout.addRow(create_label("Hub radius r_hub:"), self.r_hub_label)

        self.r_tip_label = QLabel("--")
        self.r_tip_label.setStyleSheet("color: #a6adc8; font-size: 9px;")
        geom_layout.addRow(create_label("Tip radius r_tip:"), self.r_tip_label)

        main_layout.addWidget(geom_group)

        # Apply button
        apply_btn = QPushButton("Apply Parameters")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #74c7ec;
            }
            QPushButton:pressed {
                background-color: #45475a;
            }
        """)
        apply_btn.clicked.connect(self._on_apply)
        main_layout.addWidget(apply_btn)

        # Spacer
        main_layout.addStretch()

    def _connect_signals(self):
        """Connect value change signals."""
        self.rpm_spin.valueChanged.connect(self._on_rpm_changed)
        self.flow_rate_spin.valueChanged.connect(self._on_flow_rate_changed)
        self.alpha1_spin.valueChanged.connect(self._on_alpha1_changed)

    def _on_rpm_changed(self, value):
        """Handle RPM change."""
        self._rpm = value
        self._emit_parameters()

    def _on_flow_rate_changed(self, value):
        """Handle flow rate change."""
        self._flow_rate_lps = value
        self._emit_parameters()

    def _on_alpha1_changed(self, value):
        """Handle inlet angle change."""
        self._alpha1_deg = value
        self._emit_parameters()

    def _on_apply(self):
        """Emit parameters when Apply is clicked."""
        self._emit_parameters()

    def _emit_parameters(self):
        params = {
            "n": self._rpm,
            "Q": self._flow_rate_lps / 1000.0,  # Convert L/s to m³/s
            "alpha1": self._alpha1_deg,
        }
        self.parametersChanged.emit(params)

    def get_parameters(self) -> dict:
        """
        Get current parameter values.

        Returns:
            dict: {'n': RPM, 'Q': m³/s, 'alpha1': degrees}
        """
        return {
            'n': self._rpm,
            'Q': self._flow_rate_lps / 1000.0,  # Convert to m³/s
            'alpha1': self._alpha1_deg
        }

    def set_parameters(self, rpm: float, flow_rate_m3s: float, alpha1_deg: float) -> None:
        """Update window inputs without emitting change signals."""
        self._rpm = rpm
        self._flow_rate_lps = flow_rate_m3s * 1000.0
        self._alpha1_deg = alpha1_deg
        self.rpm_spin.setValue(self._rpm)
        self.flow_rate_spin.setValue(self._flow_rate_lps)
        self.alpha1_spin.setValue(self._alpha1_deg)

    def update_geometry_display(self, r_hub: float, r_tip: float):
        """
        Update the geometry display (for future integration).

        Args:
            r_hub: Hub radius (m)
            r_tip: Tip radius (m)
        """
        self.r_hub_label.setText(f"{r_hub*1000:.2f} mm")
        self.r_tip_label.setText(f"{r_tip*1000:.2f} mm")
