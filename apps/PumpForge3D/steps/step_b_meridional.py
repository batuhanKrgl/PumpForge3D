"""
Step B: Meridional Contour panel.

Interactive editing of hub and tip Bezier curves.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QGroupBox, QCheckBox, QPushButton,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from pumpforge3d_core.geometry.inducer import InducerDesign

from ..widgets.diagram_widget import DiagramWidget


class StepBMeridional(QWidget):
    """
    Step B: Meridional Contour editing.
    
    Provides interactive Bezier curve editing for hub and tip curves.
    
    Signals:
        geometry_changed: Emitted when curves are modified
    """
    
    geometry_changed = Signal()
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("Step B: Meridional Contour")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        description = QLabel(
            "Edit the hub and tip (shroud) curves by dragging control points. "
            "Right-click for options. Use Fit View to see all geometry."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a6adc8; margin-bottom: 8px;")
        layout.addWidget(description)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side controls
        controls_widget = self._create_controls()
        splitter.addWidget(controls_widget)
        
        # Right side diagram
        self.diagram = DiagramWidget(self.design)
        self.diagram.geometry_changed.connect(self._on_geometry_changed)
        self.diagram.point_selected.connect(self._on_point_selected)
        splitter.addWidget(self.diagram)
        
        # Set splitter sizes (25% controls, 75% diagram)
        splitter.setSizes([250, 750])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        layout.addWidget(splitter, 1)
    
    def _create_controls(self) -> QWidget:
        """Create the left control panel."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(300)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(lambda c: self._set_diagram_option('show_grid', c))
        display_layout.addWidget(self.grid_check)
        
        self.cp_check = QCheckBox("Show Control Points")
        self.cp_check.setChecked(True)
        self.cp_check.toggled.connect(lambda c: self._set_diagram_option('show_control_points', c))
        display_layout.addWidget(self.cp_check)
        
        self.polygon_check = QCheckBox("Show Control Polygon")
        self.polygon_check.setChecked(True)
        self.polygon_check.toggled.connect(lambda c: self._set_diagram_option('show_control_polygon', c))
        display_layout.addWidget(self.polygon_check)
        
        layout.addWidget(display_group)
        
        # Hub curve constraints
        hub_group = QGroupBox("Hub Curve Constraints")
        hub_layout = QVBoxLayout(hub_group)
        
        self.hub_p1_lock = QCheckBox("Lock P1 tangent angle")
        self.hub_p1_lock.toggled.connect(lambda c: self._toggle_constraint('hub_p1_angle_locked', c))
        hub_layout.addWidget(self.hub_p1_lock)
        
        self.hub_p3_lock = QCheckBox("Lock P3 tangent angle")
        self.hub_p3_lock.toggled.connect(lambda c: self._toggle_constraint('hub_p3_angle_locked', c))
        hub_layout.addWidget(self.hub_p3_lock)
        
        layout.addWidget(hub_group)
        
        # Tip curve constraints
        tip_group = QGroupBox("Tip Curve Constraints")
        tip_layout = QVBoxLayout(tip_group)
        
        self.tip_p1_lock = QCheckBox("Lock P1 tangent angle")
        self.tip_p1_lock.toggled.connect(lambda c: self._toggle_constraint('tip_p1_angle_locked', c))
        tip_layout.addWidget(self.tip_p1_lock)
        
        self.tip_p3_lock = QCheckBox("Lock P3 tangent angle")
        self.tip_p3_lock.toggled.connect(lambda c: self._toggle_constraint('tip_p3_angle_locked', c))
        tip_layout.addWidget(self.tip_p3_lock)
        
        layout.addWidget(tip_group)
        
        # Point info
        self.point_info_group = QGroupBox("Selected Point")
        point_layout = QVBoxLayout(self.point_info_group)
        
        self.point_info_label = QLabel("No point selected")
        self.point_info_label.setStyleSheet("color: #a6adc8;")
        point_layout.addWidget(self.point_info_label)
        
        layout.addWidget(self.point_info_group)
        
        # Actions
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_group)
        
        fit_btn = QPushButton("Fit View")
        fit_btn.clicked.connect(self.fit_view)
        action_layout.addWidget(fit_btn)
        
        reset_btn = QPushButton("Reset Curves")
        reset_btn.clicked.connect(self._reset_curves)
        action_layout.addWidget(reset_btn)
        
        layout.addWidget(action_group)
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _set_diagram_option(self, option: str, value: bool):
        """Set a diagram display option."""
        setattr(self.diagram, option, value)
        self.diagram.update_plot()
    
    def _toggle_constraint(self, constraint: str, value: bool):
        """Toggle a curve constraint."""
        self.design.set_constraint(constraint, value)
        self.diagram.update_plot()
    
    def _on_geometry_changed(self):
        """Handle geometry change from diagram."""
        self.geometry_changed.emit()
    
    def _on_point_selected(self, curve: str, index: int):
        """Handle point selection."""
        self._update_point_info(curve, index)
    
    def _update_point_info(self, curve: str, index: int):
        """Update the point info display."""
        bezier = self.diagram._get_curve(curve)
        if bezier:
            pt = bezier.control_points[index]
            status = "locked" if pt.is_locked else "editable"
            angle = " (angle locked)" if pt.angle_locked else ""
            self.point_info_label.setText(
                f"<b>{curve.capitalize()} P{index}</b><br>"
                f"Z: {pt.z:.3f} mm<br>"
                f"R: {pt.r:.3f} mm<br>"
                f"Status: {status}{angle}"
            )
    
    def _reset_curves(self):
        """Reset curves to default shape."""
        from pumpforge3d_core.geometry.meridional import MeridionalContour
        
        self.design.contour = MeridionalContour.create_from_dimensions(self.design.main_dims)
        self.diagram.update_plot()
        self.geometry_changed.emit()
    
    def fit_view(self):
        """Fit the diagram view."""
        self.diagram.fit_view()
    
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh."""
        self.design = design
        self.diagram.set_design(design)
    
    def refresh(self):
        """Refresh the diagram."""
        self.diagram.update_plot()
        self.diagram.fit_view()
