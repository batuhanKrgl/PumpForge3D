"""
Step C: Leading/Trailing Edges panel.

Design edge curves between hub and tip.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QGroupBox, QComboBox, QPushButton,
    QFrame, QScrollArea, QDoubleSpinBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.geometry.meridional import CurveMode
from pumpforge3d_core.geometry.bezier import BezierCurve4, StraightLine

from ..widgets.diagram_widget import DiagramWidget


class StepCEdges(QWidget):
    """
    Step C: Leading/Trailing Edge design.
    
    Allows switching between straight line and Bezier modes.
    
    Signals:
        geometry_changed: Emitted when edge geometry changes
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
        header = QLabel("Step C: Leading/Trailing Edges")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        description = QLabel(
            "Define the leading and trailing edge curves. Choose between "
            "straight lines or Bezier curves for each edge."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a6adc8; margin-bottom: 8px;")
        layout.addWidget(description)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left controls
        controls = self._create_controls()
        splitter.addWidget(controls)
        
        # Right diagram
        self.diagram = DiagramWidget(self.design)
        self.diagram.geometry_changed.connect(self._on_geometry_changed)
        splitter.addWidget(self.diagram)
        
        splitter.setSizes([300, 700])
        layout.addWidget(splitter, 1)
    
    def _create_controls(self) -> QWidget:
        """Create the left control panel."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(320)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        # Leading edge group
        le_group = QGroupBox("Leading Edge")
        le_layout = QVBoxLayout(le_group)
        
        le_form = QFormLayout()
        
        self.le_mode_combo = QComboBox()
        self.le_mode_combo.addItems(["Straight Line", "Bezier Curve"])
        self.le_mode_combo.currentIndexChanged.connect(lambda i: self._set_edge_mode('leading', i))
        le_form.addRow("Mode:", self.le_mode_combo)
        
        self.le_hub_pos = QDoubleSpinBox()
        self.le_hub_pos.setRange(0, 0.5)
        self.le_hub_pos.setDecimals(3)
        self.le_hub_pos.setValue(0)
        self.le_hub_pos.setSingleStep(0.01)
        self.le_hub_pos.valueChanged.connect(self._update_le_position)
        le_form.addRow("Hub position (t):", self.le_hub_pos)
        
        self.le_tip_pos = QDoubleSpinBox()
        self.le_tip_pos.setRange(0, 0.5)
        self.le_tip_pos.setDecimals(3)
        self.le_tip_pos.setValue(0)
        self.le_tip_pos.setSingleStep(0.01)
        self.le_tip_pos.valueChanged.connect(self._update_le_position)
        le_form.addRow("Tip position (t):", self.le_tip_pos)
        
        le_layout.addLayout(le_form)
        layout.addWidget(le_group)
        
        # Trailing edge group
        te_group = QGroupBox("Trailing Edge")
        te_layout = QVBoxLayout(te_group)
        
        te_form = QFormLayout()
        
        self.te_mode_combo = QComboBox()
        self.te_mode_combo.addItems(["Straight Line", "Bezier Curve"])
        self.te_mode_combo.currentIndexChanged.connect(lambda i: self._set_edge_mode('trailing', i))
        te_form.addRow("Mode:", self.te_mode_combo)
        
        self.te_hub_pos = QDoubleSpinBox()
        self.te_hub_pos.setRange(0, 0.5)
        self.te_hub_pos.setDecimals(3)
        self.te_hub_pos.setValue(0)
        self.te_hub_pos.setSingleStep(0.01)
        self.te_hub_pos.valueChanged.connect(self._update_te_position)
        te_form.addRow("Hub position (t):", self.te_hub_pos)
        
        self.te_tip_pos = QDoubleSpinBox()
        self.te_tip_pos.setRange(0, 0.5)
        self.te_tip_pos.setDecimals(3)
        self.te_tip_pos.setValue(0)
        self.te_tip_pos.setSingleStep(0.01)
        self.te_tip_pos.valueChanged.connect(self._update_te_position)
        te_form.addRow("Tip position (t):", self.te_tip_pos)
        
        te_layout.addLayout(te_form)
        layout.addWidget(te_group)
        
        # Info section
        info_group = QGroupBox("Edge Information")
        info_layout = QVBoxLayout(info_group)
        
        self.edge_info_label = QLabel("")
        self.edge_info_label.setStyleSheet("color: #a6adc8;")
        self.edge_info_label.setWordWrap(True)
        info_layout.addWidget(self.edge_info_label)
        
        layout.addWidget(info_group)
        
        # Actions
        action_layout = QHBoxLayout()
        
        fit_btn = QPushButton("Fit View")
        fit_btn.clicked.connect(self.fit_view)
        action_layout.addWidget(fit_btn)
        
        layout.addLayout(action_layout)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _set_edge_mode(self, edge: str, mode_index: int):
        """Set the mode for an edge curve."""
        mode = CurveMode.STRAIGHT if mode_index == 0 else CurveMode.BEZIER
        
        if edge == 'leading':
            edge_obj = self.design.contour.leading_edge
        else:
            edge_obj = self.design.contour.trailing_edge
        
        edge_obj.mode = mode
        
        # Create appropriate curve
        hub_curve = self.design.contour.hub_curve
        tip_curve = self.design.contour.tip_curve
        
        if edge == 'leading':
            hub_pt = hub_curve.evaluate(edge_obj.hub_position)
            tip_pt = tip_curve.evaluate(edge_obj.tip_position)
        else:
            hub_pt = hub_curve.evaluate(1.0 - edge_obj.hub_position)
            tip_pt = tip_curve.evaluate(1.0 - edge_obj.tip_position)
        
        if mode == CurveMode.STRAIGHT:
            edge_obj.straight_line = StraightLine(hub_pt, tip_pt, edge)
            edge_obj.bezier_curve = None
        else:
            edge_obj.bezier_curve = BezierCurve4.create_default(hub_pt, tip_pt, edge)
            edge_obj.straight_line = None
        
        self._update_edge_info()
        self.diagram.update_plot()
        self.geometry_changed.emit()
    
    def _update_le_position(self):
        """Update leading edge position."""
        le = self.design.contour.leading_edge
        le.hub_position = self.le_hub_pos.value()
        le.tip_position = self.le_tip_pos.value()
        self._rebuild_edge('leading')
    
    def _update_te_position(self):
        """Update trailing edge position."""
        te = self.design.contour.trailing_edge
        te.hub_position = self.te_hub_pos.value()
        te.tip_position = self.te_tip_pos.value()
        self._rebuild_edge('trailing')
    
    def _rebuild_edge(self, edge: str):
        """Rebuild an edge curve after position change."""
        if edge == 'leading':
            edge_obj = self.design.contour.leading_edge
            hub_pt = self.design.contour.hub_curve.evaluate(edge_obj.hub_position)
            tip_pt = self.design.contour.tip_curve.evaluate(edge_obj.tip_position)
        else:
            edge_obj = self.design.contour.trailing_edge
            hub_pt = self.design.contour.hub_curve.evaluate(1.0 - edge_obj.hub_position)
            tip_pt = self.design.contour.tip_curve.evaluate(1.0 - edge_obj.tip_position)
        
        if edge_obj.mode == CurveMode.STRAIGHT:
            edge_obj.straight_line = StraightLine(hub_pt, tip_pt, edge)
        else:
            edge_obj.bezier_curve = BezierCurve4.create_default(hub_pt, tip_pt, edge)
        
        self._update_edge_info()
        self.diagram.update_plot()
        self.geometry_changed.emit()
    
    def _update_edge_info(self):
        """Update edge information display."""
        le = self.design.contour.leading_edge
        te = self.design.contour.trailing_edge
        
        le_mode = "Straight" if le.mode == CurveMode.STRAIGHT else "Bezier"
        te_mode = "Straight" if te.mode == CurveMode.STRAIGHT else "Bezier"
        
        hub_le = le.get_hub_point()
        tip_le = le.get_tip_point()
        hub_te = te.get_hub_point()
        tip_te = te.get_tip_point()
        
        self.edge_info_label.setText(
            f"<b>Leading Edge</b><br>"
            f"Mode: {le_mode}<br>"
            f"Hub: ({hub_le[0]:.1f}, {hub_le[1]:.1f})<br>"
            f"Tip: ({tip_le[0]:.1f}, {tip_le[1]:.1f})<br><br>"
            f"<b>Trailing Edge</b><br>"
            f"Mode: {te_mode}<br>"
            f"Hub: ({hub_te[0]:.1f}, {hub_te[1]:.1f})<br>"
            f"Tip: ({tip_te[0]:.1f}, {tip_te[1]:.1f})"
        )
    
    def fit_view(self):
        """Fit the diagram view."""
        self.diagram.fit_view()
    
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh."""
        self.design = design
        self.diagram.set_design(design)
        self._load_from_design()
    
    def _load_from_design(self):
        """Load edge settings from design."""
        le = self.design.contour.leading_edge
        te = self.design.contour.trailing_edge
        
        self.le_mode_combo.setCurrentIndex(0 if le.mode == CurveMode.STRAIGHT else 1)
        self.le_hub_pos.setValue(le.hub_position)
        self.le_tip_pos.setValue(le.tip_position)
        
        self.te_mode_combo.setCurrentIndex(0 if te.mode == CurveMode.STRAIGHT else 1)
        self.te_hub_pos.setValue(te.hub_position)
        self.te_tip_pos.setValue(te.tip_position)
        
        self._update_edge_info()
    
    def _on_geometry_changed(self):
        """Handle geometry change from diagram."""
        self.geometry_changed.emit()
    
    def refresh(self):
        """Refresh the display."""
        self._load_from_design()
        self.diagram.update_plot()
        self.diagram.fit_view()
