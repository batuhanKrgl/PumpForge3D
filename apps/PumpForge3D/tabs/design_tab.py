"""
Design Tab - Unified design workspace.

Consolidates Main Dimensions, Meridional Contour, Edges, and Analysis into
a single integrated workspace with collapsible panels.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QGroupBox, QCheckBox, QPushButton, QToolButton,
    QFrame, QScrollArea, QDoubleSpinBox, QFormLayout,
    QComboBox, QTreeWidget, QTreeWidgetItem, QSizePolicy,
    QAbstractSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QSettings
from PySide6.QtGui import QFont

import logging

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.geometry.meridional import MainDimensions, CurveMode

from ..widgets.diagram_widget import DiagramWidget
from ..widgets.analysis_plot import AnalysisPlotWidget
from ..styles import apply_section_header_style
from ..utils.editor_commit_filter import attach_commit_filter

logger = logging.getLogger(__name__)


class StyledSpinBox(QWidget):
    """
    Custom spinbox without native arrows, with +/- buttons.
    Emits valueChanged signal like QDoubleSpinBox.
    """
    
    valueChanged = Signal(float)
    editingFinished = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Minus button
        self.minus_btn = QToolButton()
        self.minus_btn.setText("−")
        self.minus_btn.setFixedSize(20, 24)
        self.minus_btn.setAutoRepeat(True)
        self.minus_btn.setAccessibleName("Decrease value")
        self.minus_btn.setAccessibleDescription("Decrease the value.")
        self.minus_btn.clicked.connect(self._decrement)
        layout.addWidget(self.minus_btn)
        
        # Spinbox without arrows
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spinbox.setFixedWidth(80)
        self.spinbox.editingFinished.connect(self._on_editing_finished)
        layout.addWidget(self.spinbox)
        
        # Plus button
        self.plus_btn = QToolButton()
        self.plus_btn.setText("+")
        self.plus_btn.setFixedSize(20, 24)
        self.plus_btn.setAutoRepeat(True)
        self.plus_btn.setAccessibleName("Increase value")
        self.plus_btn.setAccessibleDescription("Increase the value.")
        self.plus_btn.clicked.connect(self._increment)
        layout.addWidget(self.plus_btn)
    
    def _increment(self):
        self.spinbox.stepUp()
        self.valueChanged.emit(self.spinbox.value())
    
    def _decrement(self):
        self.spinbox.stepDown()
        self.valueChanged.emit(self.spinbox.value())

    def _on_editing_finished(self):
        self.editingFinished.emit()
        self.valueChanged.emit(self.spinbox.value())
    
    # Delegate common methods to inner spinbox
    def value(self) -> float:
        return self.spinbox.value()
    
    def setValue(self, val: float):
        self.spinbox.setValue(val)
        self._set_last_valid_value(val)
    
    def setRange(self, min_val: float, max_val: float):
        self.spinbox.setRange(min_val, max_val)
    
    def setDecimals(self, decimals: int):
        self.spinbox.setDecimals(decimals)
    
    def setSuffix(self, suffix: str):
        self.spinbox.setSuffix(suffix)
    
    def setSingleStep(self, step: float):
        self.spinbox.setSingleStep(step)
    
    def blockSignals(self, block: bool) -> bool:
        return self.spinbox.blockSignals(block)

    def _set_last_valid_value(self, value: float) -> None:
        self.spinbox.setProperty("last_valid_value", value)

    def revert_to_last_valid(self) -> None:
        last_valid = self.spinbox.property("last_valid_value")
        if last_valid is not None:
            self.spinbox.setValue(float(last_valid))


class CollapsibleSection(QWidget):
    """A collapsible section with header and content."""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._is_collapsed = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        
        # Header button
        self.header = QPushButton(f"▼ {self.title}")
        apply_section_header_style(self.header)
        self.header.setAccessibleName(f"{self.title} section")
        self.header.setAccessibleDescription(f"Expand or collapse the {self.title} section.")
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)
        
        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.content)
    
    def _toggle(self):
        self._is_collapsed = not self._is_collapsed
        self.content.setVisible(not self._is_collapsed)
        arrow = "▶" if self._is_collapsed else "▼"
        self.header.setText(f"{arrow} {self.title}")
    
    def addWidget(self, widget: QWidget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


def create_subscript_label(base: str, subscript: str) -> QLabel:
    """Create a label with subscript formatting like r<sub>t,in</sub>."""
    label = QLabel(f"{base}<sub>{subscript}</sub>")
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


class DesignTab(QWidget):
    """
    Unified Design tab consolidating:
    - Main Dimensions
    - Meridional contour editing
    - Edge curve controls
    - Analysis plots (curvature, area)
    """
    
    geometry_changed = Signal()
    dimensions_changed = Signal()
    geometry_committed = Signal(dict)
    
    def __init__(self, design: InducerDesign, undo_stack=None, parent=None):
        super().__init__(parent)
        self.design = design
        self.undo_stack = undo_stack
        self._analysis_update_timer = QTimer(self)
        self._analysis_update_timer.setSingleShot(True)
        self._analysis_update_timer.setInterval(150)
        self._analysis_update_timer.timeout.connect(self._update_analysis_plots)
        self._last_valid_dims = {}
        self._setup_ui()
        self._load_from_design()
        self._connect_signals()
    
    def _setup_ui(self):
        """Create the main layout with left panel, center diagram, right panel."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)
        
        # Main splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(4)
        
        # LEFT PANEL - Controls
        left_panel = self._create_left_panel()
        self.splitter.addWidget(left_panel)
        
        # CENTER - Diagram widget with status bar
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        self.diagram = DiagramWidget(self.design)
        self.diagram.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.diagram.setAccessibleName("Meridional diagram")
        self.diagram.setAccessibleDescription("Interactive meridional contour editor.")
        center_layout.addWidget(self.diagram, 1)  # stretch factor 1
        
        # Status bar for selected point (F1 fix)
        self.point_status_bar = QLabel("No point selected")
        self.point_status_bar.setStyleSheet("""
            background: #181825;
            color: #a6adc8;
            padding: 4px 8px;
            border-top: 1px solid #313244;
            font-size: 11px;
        """)
        self.point_status_bar.setAccessibleName("Point status")
        center_layout.addWidget(self.point_status_bar)
        
        self.splitter.addWidget(center_widget)
        
        # RIGHT PANEL - Info and Analysis
        right_panel = self._create_right_panel()
        self.splitter.addWidget(right_panel)
        
        # Set splitter proportions and stretch factors (D1 fix)
        self.splitter.setSizes([250, 700, 300])
        self.splitter.setStretchFactor(0, 0)  # Left fixed
        self.splitter.setStretchFactor(1, 1)  # Center expands
        self.splitter.setStretchFactor(2, 0)  # Right fixed
        
        main_layout.addWidget(self.splitter, 1)

        QWidget.setTabOrder(self.r_h_in_spin.spinbox, self.r_t_in_spin.spinbox)
        QWidget.setTabOrder(self.r_t_in_spin.spinbox, self.r_h_out_spin.spinbox)
        QWidget.setTabOrder(self.r_h_out_spin.spinbox, self.r_t_out_spin.spinbox)
        QWidget.setTabOrder(self.r_t_out_spin.spinbox, self.separate_L_check)
        QWidget.setTabOrder(self.separate_L_check, self.L_hub_spin.spinbox)
        QWidget.setTabOrder(self.L_hub_spin.spinbox, self.L_tip_spin.spinbox)
        QWidget.setTabOrder(self.L_tip_spin.spinbox, self.le_mode_combo)
        QWidget.setTabOrder(self.le_mode_combo, self.le_hub_pos.spinbox)
        QWidget.setTabOrder(self.le_hub_pos.spinbox, self.le_tip_pos.spinbox)
        QWidget.setTabOrder(self.le_tip_pos.spinbox, self.te_mode_combo)
        QWidget.setTabOrder(self.te_mode_combo, self.te_hub_pos.spinbox)
        QWidget.setTabOrder(self.te_hub_pos.spinbox, self.te_tip_pos.spinbox)
        
        # Note: Overlay toolbar removed - using diagram's built-in toolbar
    
    def _create_left_panel(self) -> QWidget:
        """Create the left control panel with collapsible sections."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        scroll.setMaximumWidth(350)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # MAIN DIMENSIONS SECTION
        dims_section = CollapsibleSection("Main Dimensions")
        dims_form = QFormLayout()
        dims_form.setSpacing(8)
        dims_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Radial dimensions first
        self.r_h_in_spin = StyledSpinBox()
        self.r_h_in_spin.setRange(0, 1000)
        self.r_h_in_spin.setDecimals(2)
        self.r_h_in_spin.setSuffix(" mm")
        r_h_in_label = create_subscript_label("r", "h,in")
        r_h_in_label.setBuddy(self.r_h_in_spin.spinbox)
        dims_form.addRow(r_h_in_label, self.r_h_in_spin)
        self.r_h_in_spin.spinbox.setAccessibleName("Inlet hub radius")
        self.r_h_in_spin.spinbox.setAccessibleDescription("Inlet hub radius in millimeters.")
        
        self.r_t_in_spin = StyledSpinBox()
        self.r_t_in_spin.setRange(0, 1000)
        self.r_t_in_spin.setDecimals(2)
        self.r_t_in_spin.setSuffix(" mm")
        r_t_in_label = create_subscript_label("r", "t,in")
        r_t_in_label.setBuddy(self.r_t_in_spin.spinbox)
        dims_form.addRow(r_t_in_label, self.r_t_in_spin)
        self.r_t_in_spin.spinbox.setAccessibleName("Inlet tip radius")
        self.r_t_in_spin.spinbox.setAccessibleDescription("Inlet tip radius in millimeters.")
        
        self.r_h_out_spin = StyledSpinBox()
        self.r_h_out_spin.setRange(0, 1000)
        self.r_h_out_spin.setDecimals(2)
        self.r_h_out_spin.setSuffix(" mm")
        r_h_out_label = create_subscript_label("r", "h,out")
        r_h_out_label.setBuddy(self.r_h_out_spin.spinbox)
        dims_form.addRow(r_h_out_label, self.r_h_out_spin)
        self.r_h_out_spin.spinbox.setAccessibleName("Outlet hub radius")
        self.r_h_out_spin.spinbox.setAccessibleDescription("Outlet hub radius in millimeters.")
        
        self.r_t_out_spin = StyledSpinBox()
        self.r_t_out_spin.setRange(0, 1000)
        self.r_t_out_spin.setDecimals(2)
        self.r_t_out_spin.setSuffix(" mm")
        r_t_out_label = create_subscript_label("r", "t,out")
        r_t_out_label.setBuddy(self.r_t_out_spin.spinbox)
        dims_form.addRow(r_t_out_label, self.r_t_out_spin)
        self.r_t_out_spin.spinbox.setAccessibleName("Outlet tip radius")
        self.r_t_out_spin.spinbox.setAccessibleDescription("Outlet tip radius in millimeters.")
        
        # Axial lengths at bottom (properly aligned in form)
        self.separate_L_check = QCheckBox("Separate hub/tip axial length")
        self.separate_L_check.setAccessibleName("Separate hub and tip axial length")
        self.separate_L_check.setAccessibleDescription("Enable separate axial length inputs for hub and tip.")
        dims_form.addRow("", self.separate_L_check)
        
        self.L_hub_spin = StyledSpinBox()
        self.L_hub_spin.setRange(1, 10000)
        self.L_hub_spin.setDecimals(2)
        self.L_hub_spin.setSuffix(" mm")
        L_hub_label = create_subscript_label("L", "hub")
        L_hub_label.setBuddy(self.L_hub_spin.spinbox)
        dims_form.addRow(L_hub_label, self.L_hub_spin)
        self.L_hub_spin.spinbox.setAccessibleName("Hub axial length")
        self.L_hub_spin.spinbox.setAccessibleDescription("Hub axial length in millimeters.")
        
        self.L_tip_spin = StyledSpinBox()
        self.L_tip_spin.setRange(1, 10000)
        self.L_tip_spin.setDecimals(2)
        self.L_tip_spin.setSuffix(" mm")
        self.L_tip_spin.setEnabled(False)  # Disabled when locked
        L_tip_label = create_subscript_label("L", "tip")
        L_tip_label.setBuddy(self.L_tip_spin.spinbox)
        dims_form.addRow(L_tip_label, self.L_tip_spin)
        self.L_tip_spin.spinbox.setAccessibleName("Tip axial length")
        self.L_tip_spin.spinbox.setAccessibleDescription("Tip axial length in millimeters.")

        self.dimension_error_label = QLabel("")
        self.dimension_error_label.setWordWrap(True)
        self.dimension_error_label.setStyleSheet("color: #f38ba8; font-size: 10px;")
        self.dimension_error_label.setVisible(False)
        dims_section.addWidget(self.dimension_error_label)
        
        dims_section.addLayout(dims_form)
        
        # NOTE: Apply button removed - dimensions apply on edit finished
        
        layout.addWidget(dims_section)
        
        # NOTE: Display Options and Curve Constraints removed
        # Display toggles are in the diagram toolbar
        # Angle lock controls are in the coordinate-edit popup
        
        # EDGE CURVES SECTION
        edges_section = CollapsibleSection("Edge Curves")
        
        # Leading edge
        le_label = QLabel("<b>Leading Edge</b>")
        edges_section.addWidget(le_label)
        
        le_mode_row = QHBoxLayout()
        le_mode_label = QLabel("Mode:")
        le_mode_row.addWidget(le_mode_label)
        self.le_mode_combo = QComboBox()
        self.le_mode_combo.addItems(["Straight", "Bezier (Quadratic)"])
        self.le_mode_combo.setAccessibleName("Leading edge mode")
        self.le_mode_combo.setAccessibleDescription("Select the leading edge curve mode.")
        le_mode_label.setBuddy(self.le_mode_combo)
        le_mode_row.addWidget(self.le_mode_combo)
        edges_section.addLayout(le_mode_row)
        
        le_hub_row = QHBoxLayout()
        le_hub_label = QLabel("Hub position:")
        le_hub_row.addWidget(le_hub_label)
        self.le_hub_pos = StyledSpinBox()
        self.le_hub_pos.setRange(0, 1)
        self.le_hub_pos.setDecimals(3)
        self.le_hub_pos.setSingleStep(0.01)
        self.le_hub_pos.spinbox.setAccessibleName("Leading edge hub position")
        self.le_hub_pos.spinbox.setAccessibleDescription("Leading edge hub curve parameter (0 to 1).")
        le_hub_label.setBuddy(self.le_hub_pos.spinbox)
        le_hub_row.addWidget(self.le_hub_pos)
        edges_section.addLayout(le_hub_row)
        
        le_tip_row = QHBoxLayout()
        le_tip_label = QLabel("Tip position:")
        le_tip_row.addWidget(le_tip_label)
        self.le_tip_pos = StyledSpinBox()
        self.le_tip_pos.setRange(0, 1)
        self.le_tip_pos.setDecimals(3)
        self.le_tip_pos.setSingleStep(0.01)
        self.le_tip_pos.spinbox.setAccessibleName("Leading edge tip position")
        self.le_tip_pos.spinbox.setAccessibleDescription("Leading edge tip curve parameter (0 to 1).")
        le_tip_label.setBuddy(self.le_tip_pos.spinbox)
        le_tip_row.addWidget(self.le_tip_pos)
        edges_section.addLayout(le_tip_row)
        
        # Trailing edge
        te_label = QLabel("<b>Trailing Edge</b>")
        edges_section.addWidget(te_label)
        
        te_mode_row = QHBoxLayout()
        te_mode_label = QLabel("Mode:")
        te_mode_row.addWidget(te_mode_label)
        self.te_mode_combo = QComboBox()
        self.te_mode_combo.addItems(["Straight", "Bezier (Quadratic)"])
        self.te_mode_combo.setAccessibleName("Trailing edge mode")
        self.te_mode_combo.setAccessibleDescription("Select the trailing edge curve mode.")
        te_mode_label.setBuddy(self.te_mode_combo)
        te_mode_row.addWidget(self.te_mode_combo)
        edges_section.addLayout(te_mode_row)
        
        te_hub_row = QHBoxLayout()
        te_hub_label = QLabel("Hub position:")
        te_hub_row.addWidget(te_hub_label)
        self.te_hub_pos = StyledSpinBox()
        self.te_hub_pos.setRange(0, 1)
        self.te_hub_pos.setDecimals(3)
        self.te_hub_pos.setSingleStep(0.01)
        self.te_hub_pos.spinbox.setAccessibleName("Trailing edge hub position")
        self.te_hub_pos.spinbox.setAccessibleDescription("Trailing edge hub curve parameter (0 to 1).")
        te_hub_label.setBuddy(self.te_hub_pos.spinbox)
        te_hub_row.addWidget(self.te_hub_pos)
        edges_section.addLayout(te_hub_row)
        
        te_tip_row = QHBoxLayout()
        te_tip_label = QLabel("Tip position:")
        te_tip_row.addWidget(te_tip_label)
        self.te_tip_pos = StyledSpinBox()
        self.te_tip_pos.setRange(0, 1)
        self.te_tip_pos.setDecimals(3)
        self.te_tip_pos.setSingleStep(0.01)
        self.te_tip_pos.spinbox.setAccessibleName("Trailing edge tip position")
        self.te_tip_pos.spinbox.setAccessibleDescription("Trailing edge tip curve parameter (0 to 1).")
        te_tip_label.setBuddy(self.te_tip_pos.spinbox)
        te_tip_row.addWidget(self.te_tip_pos)
        edges_section.addLayout(te_tip_row)
        
        layout.addWidget(edges_section)
        
        # CP CONSTRAINTS SECTION
        cp_mode_section = CollapsibleSection("CP Motion")
        
        self.cp_mode_free = QCheckBox("Free movement")
        self.cp_mode_free.setChecked(True)
        self.cp_mode_free.setAccessibleName("Control point free movement")
        self.cp_mode_free.setAccessibleDescription("Allow free movement of control points.")
        cp_mode_section.addWidget(self.cp_mode_free)
        
        self.cp_mode_bbox = QCheckBox("Bounding box constraint")
        self.cp_mode_bbox.setAccessibleName("Control point bounding box constraint")
        self.cp_mode_bbox.setAccessibleDescription("Restrict control point movement to bounding box.")
        cp_mode_section.addWidget(self.cp_mode_bbox)
        
        layout.addWidget(cp_mode_section)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_right_panel(self) -> QWidget:
        """Create the right panel with design info and analysis plots."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(280)
        scroll.setMaximumWidth(400)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # DESIGN INFO SECTION
        info_section = CollapsibleSection("Design Info")
        
        self.info_tree = QTreeWidget()
        self.info_tree.setHeaderHidden(True)
        self.info_tree.setMinimumHeight(180)
        self.info_tree.setMaximumHeight(220)
        self.info_tree.setAccessibleName("Design summary")
        self.info_tree.setAccessibleDescription("Summary of key inducer dimensions and arc lengths.")
        info_section.addWidget(self.info_tree)
        
        layout.addWidget(info_section)
        
        # ANALYSIS SECTION with actual plots (C1 fix)
        analysis_section = CollapsibleSection("Analysis Plots")
        
        self.analysis_widget = AnalysisPlotWidget(self.design)
        self.analysis_widget.setAccessibleName("Analysis plots")
        self.analysis_widget.setAccessibleDescription("Curvature and area plots for the current design.")
        analysis_section.addWidget(self.analysis_widget)
        
        layout.addWidget(analysis_section)
        
        # VALIDATION SECTION
        validation_section = CollapsibleSection("Validation")
        
        self.validation_label = QLabel("✅ Design is valid")
        self.validation_label.setWordWrap(True)
        self.validation_label.setAccessibleName("Validation results")
        validation_section.addWidget(self.validation_label)
        
        layout.addWidget(validation_section)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _connect_signals(self):
        """Connect UI signals."""
        # Dimension spinboxes - commit on editing finished
        self.r_h_in_spin.editingFinished.connect(self._apply_dimensions)
        self.r_t_in_spin.editingFinished.connect(self._apply_dimensions)
        self.r_h_out_spin.editingFinished.connect(self._apply_dimensions)
        self.r_t_out_spin.editingFinished.connect(self._apply_dimensions)
        self.L_hub_spin.editingFinished.connect(self._apply_dimensions)
        self.L_tip_spin.editingFinished.connect(self._apply_dimensions)
        
        # Separate L toggle
        self.separate_L_check.toggled.connect(self._toggle_separate_lengths)
        
        # LE/TE controls - wire to update geometry
        self.le_mode_combo.currentIndexChanged.connect(self._on_edge_mode_changed)
        self.le_hub_pos.editingFinished.connect(self._on_edge_position_changed)
        self.le_tip_pos.editingFinished.connect(self._on_edge_position_changed)
        self.te_mode_combo.currentIndexChanged.connect(self._on_edge_mode_changed)
        self.te_hub_pos.editingFinished.connect(self._on_edge_position_changed)
        self.te_tip_pos.editingFinished.connect(self._on_edge_position_changed)
        
        # Diagram signals
        self.diagram.geometry_changed.connect(self._on_diagram_geometry_changed)
        self.diagram.point_selected.connect(self._on_point_selected)
        
        # CP mode (exclusive + wire to diagram)
        self.cp_mode_free.toggled.connect(self._on_cp_mode_free)
        self.cp_mode_bbox.toggled.connect(self._on_cp_mode_bbox)

        # Enter/Escape commit handling for spinboxes
        for spin in [
            self.r_h_in_spin, self.r_t_in_spin, self.r_h_out_spin, self.r_t_out_spin,
            self.L_hub_spin, self.L_tip_spin, self.le_hub_pos, self.le_tip_pos,
            self.te_hub_pos, self.te_tip_pos,
        ]:
            attach_commit_filter(spin.spinbox)
    
    def _load_from_design(self):
        """Load current values from design."""
        dims = self.design.main_dims
        
        self.r_h_in_spin.blockSignals(True)
        self.r_t_in_spin.blockSignals(True)
        self.r_h_out_spin.blockSignals(True)
        self.r_t_out_spin.blockSignals(True)
        self.L_hub_spin.blockSignals(True)
        self.L_tip_spin.blockSignals(True)
        
        self.r_h_in_spin.setValue(dims.r_h_in)
        self.r_t_in_spin.setValue(dims.r_t_in)
        self.r_h_out_spin.setValue(dims.r_h_out)
        self.r_t_out_spin.setValue(dims.r_t_out)
        self.L_hub_spin.setValue(dims.L)
        self.L_tip_spin.setValue(dims.L)  # Same value when locked
        
        self.r_h_in_spin.blockSignals(False)
        self.r_t_in_spin.blockSignals(False)
        self.r_h_out_spin.blockSignals(False)
        self.r_t_out_spin.blockSignals(False)
        self.L_hub_spin.blockSignals(False)
        self.L_tip_spin.blockSignals(False)

        self._last_valid_dims = {
            "r_h_in": dims.r_h_in,
            "r_t_in": dims.r_t_in,
            "r_h_out": dims.r_h_out,
            "r_t_out": dims.r_t_out,
            "L": dims.L,
        }
        self._clear_dimension_error()
        
        # Update edge positions
        self.le_hub_pos.setValue(getattr(self.design.contour.leading_edge, 'hub_t', 0.0))
        self.le_tip_pos.setValue(getattr(self.design.contour.leading_edge, 'tip_t', 0.0))
        self.te_hub_pos.setValue(getattr(self.design.contour.trailing_edge, 'hub_t', 1.0))
        self.te_tip_pos.setValue(getattr(self.design.contour.trailing_edge, 'tip_t', 1.0))
        
        self._update_info_tree()
        self._update_validation()
    
    def _apply_dimensions(self):
        """Apply dimension changes to design."""
        from ..undo_commands import ChangeDimensionsCommand

        old_dims = self.design.main_dims.to_dict()
        
        try:
            new_dims = MainDimensions(
                r_h_in=self.r_h_in_spin.value(),
                r_t_in=self.r_t_in_spin.value(),
                r_h_out=self.r_h_out_spin.value(),
                r_t_out=self.r_t_out_spin.value(),
                L=self.L_hub_spin.value(),  # Use hub length as primary
            )
            new_dims_dict = new_dims.to_dict()
            
            if self.undo_stack:
                cmd = ChangeDimensionsCommand(
                    self.design, old_dims, new_dims_dict,
                    on_change_callback=self._on_dimensions_applied
                )
                self.undo_stack.push(cmd)
            else:
                self.design.set_main_dimensions(new_dims)
                self._on_dimensions_applied()
            self._last_valid_dims = new_dims_dict
            self._clear_dimension_error()
            for spin in [
                self.r_h_in_spin, self.r_t_in_spin, self.r_h_out_spin,
                self.r_t_out_spin, self.L_hub_spin, self.L_tip_spin,
            ]:
                spin.spinbox.setProperty("last_valid_value", spin.value())

        except ValueError as e:
            logger.warning("Invalid dimension input: %s", e)
            self._set_dimension_error(str(e))
            self._restore_last_valid_dimensions()

    def _on_dimensions_applied(self):
        """Called after dimensions are applied."""
        self.design.contour.update_from_dimensions(self.design.main_dims)
        self.diagram.update_plot()
        self._update_info_tree()
        self._update_validation()
        self._schedule_analysis_update()
        self.dimensions_changed.emit()
        self.geometry_changed.emit()
        self.geometry_committed.emit(self._build_geometry_payload())
    
    def _set_display_option(self, option: str, value: bool):
        """Set a diagram display option (NOT undoable)."""
        setattr(self.diagram, option, value)
        self.diagram.update_plot()
    
    def _on_edge_mode_changed(self):
        """Handle LE/TE mode combo change."""
        # Update edge curve modes from combo boxes
        from pumpforge3d_core.geometry.meridional import CurveMode
        
        le_mode = CurveMode.STRAIGHT if self.le_mode_combo.currentIndex() == 0 else CurveMode.BEZIER
        te_mode = CurveMode.STRAIGHT if self.te_mode_combo.currentIndex() == 0 else CurveMode.BEZIER
        
        contour = self.design.contour
        contour.leading_edge.mode = le_mode
        contour.trailing_edge.mode = te_mode
        
        # Recompute edge curves with new mode
        contour.leading_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
        contour.trailing_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
        
        self._refresh_all()
    
    def _on_edge_position_changed(self):
        """Handle LE/TE position spinbox change."""
        # Update edge anchor positions
        contour = self.design.contour
        
        contour.leading_edge.hub_t = self.le_hub_pos.value()
        contour.leading_edge.tip_t = self.le_tip_pos.value()
        contour.trailing_edge.hub_t = self.te_hub_pos.value()
        contour.trailing_edge.tip_t = self.te_tip_pos.value()
        
        # Recompute edge curves from new positions
        contour.leading_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
        contour.trailing_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
        
        self._refresh_all()
    
    def _refresh_all(self):
        """Central refresh after geometry changes."""
        self.diagram.update_plot()
        self._update_info_tree()
        self._update_validation()
        self._schedule_analysis_update()
        self.geometry_changed.emit()
    
    def _on_cp_mode_free(self, checked: bool):
        """Handle free movement mode toggle."""
        if checked:
            self.cp_mode_bbox.setChecked(False)
            self.diagram.use_bounding_box = False
    
    def _on_cp_mode_bbox(self, checked: bool):
        """Handle bounding box mode toggle."""
        if checked:
            self.cp_mode_free.setChecked(False)
            self.diagram.use_bounding_box = True
    
    def _toggle_separate_lengths(self, checked: bool):
        """Toggle separate hub/tip axial length inputs (E1 fix)."""
        # Enable/disable tip field based on lock state
        self.L_tip_spin.setEnabled(checked)
        
        # When locking (unchecking), sync tip to hub
        if not checked:
            self.L_tip_spin.setValue(self.L_hub_spin.value())

    def _set_dimension_error(self, message: str) -> None:
        widgets = [
            self.r_h_in_spin.spinbox,
            self.r_t_in_spin.spinbox,
            self.r_h_out_spin.spinbox,
            self.r_t_out_spin.spinbox,
            self.L_hub_spin.spinbox,
            self.L_tip_spin.spinbox,
        ]
        for widget in widgets:
            widget.setProperty("error", True)
            widget.setToolTip(message)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.dimension_error_label.setText(f"⚠ {message}")
        self.dimension_error_label.setVisible(True)

    def _clear_dimension_error(self) -> None:
        widgets = [
            self.r_h_in_spin.spinbox,
            self.r_t_in_spin.spinbox,
            self.r_h_out_spin.spinbox,
            self.r_t_out_spin.spinbox,
            self.L_hub_spin.spinbox,
            self.L_tip_spin.spinbox,
        ]
        for widget in widgets:
            widget.setProperty("error", False)
            widget.setToolTip("")
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        if hasattr(self, "dimension_error_label"):
            self.dimension_error_label.setText("")
            self.dimension_error_label.setVisible(False)

    def _restore_last_valid_dimensions(self) -> None:
        if not self._last_valid_dims:
            return
        self.r_h_in_spin.blockSignals(True)
        self.r_t_in_spin.blockSignals(True)
        self.r_h_out_spin.blockSignals(True)
        self.r_t_out_spin.blockSignals(True)
        self.L_hub_spin.blockSignals(True)
        self.L_tip_spin.blockSignals(True)

        self.r_h_in_spin.setValue(self._last_valid_dims["r_h_in"])
        self.r_t_in_spin.setValue(self._last_valid_dims["r_t_in"])
        self.r_h_out_spin.setValue(self._last_valid_dims["r_h_out"])
        self.r_t_out_spin.setValue(self._last_valid_dims["r_t_out"])
        self.L_hub_spin.setValue(self._last_valid_dims["L"])
        self.L_tip_spin.setValue(self._last_valid_dims["L"])

        self.r_h_in_spin.blockSignals(False)
        self.r_t_in_spin.blockSignals(False)
        self.r_h_out_spin.blockSignals(False)
        self.r_t_out_spin.blockSignals(False)
        self.L_hub_spin.blockSignals(False)
        self.L_tip_spin.blockSignals(False)
    
    def _on_diagram_geometry_changed(self):
        """Handle geometry change from diagram."""
        # Sync LE/TE position spinboxes from design (for edge anchor dragging)
        self._sync_edge_positions_from_design()
        
        self._update_info_tree()
        self._update_validation()
        self._schedule_analysis_update()
        self.geometry_changed.emit()
        self.geometry_committed.emit(self._build_geometry_payload())

    def _build_geometry_payload(self) -> dict:
        """Build a geometry payload for Inducer station updates."""
        dims = self.design.main_dims
        z_in = 0.0
        z_out = dims.L / 1000.0
        return {
            "hub_le": {"z": z_in, "r": dims.r_h_in / 1000.0},
            "hub_te": {"z": z_out, "r": dims.r_h_out / 1000.0},
            "shroud_le": {"z": z_in, "r": dims.r_t_in / 1000.0},
            "shroud_te": {"z": z_out, "r": dims.r_t_out / 1000.0},
        }
    
    def _sync_edge_positions_from_design(self):
        """Sync LE/TE position spinboxes from current design values."""
        contour = self.design.contour
        
        # Block signals to avoid feedback loop
        self.le_hub_pos.blockSignals(True)
        self.le_tip_pos.blockSignals(True)
        self.te_hub_pos.blockSignals(True)
        self.te_tip_pos.blockSignals(True)
        
        self.le_hub_pos.setValue(contour.leading_edge.hub_t)
        self.le_tip_pos.setValue(contour.leading_edge.tip_t)
        self.te_hub_pos.setValue(contour.trailing_edge.hub_t)
        self.te_tip_pos.setValue(contour.trailing_edge.tip_t)
        
        self.le_hub_pos.blockSignals(False)
        self.le_tip_pos.blockSignals(False)
        self.te_hub_pos.blockSignals(False)
        self.te_tip_pos.blockSignals(False)
    
    def _on_point_selected(self, curve: str, index: int):
        """Handle point selection in diagram - update status bar (F1 fix)."""
        bezier = self.diagram._get_curve(curve)
        if bezier:
            pt = bezier.control_points[index]
            status = "locked" if pt.is_locked else "editable"
            angle = " • angle locked" if pt.angle_locked else ""
            self.point_status_bar.setText(
                f"{curve.capitalize()} P{index}: Z={pt.z:.2f} mm, R={pt.r:.2f} mm • {status}{angle}"
            )
    
    def _update_info_tree(self):
        """Update the design info tree."""
        self.info_tree.clear()
        
        summary = self.design.get_summary()
        
        # Dimensions
        dims_item = QTreeWidgetItem(["Dimensions"])
        dims_item.addChild(QTreeWidgetItem([f"Axial length: {summary['axial_length']:.2f} mm"]))
        dims_item.addChild(QTreeWidgetItem([f"Inlet hub R: {summary['inlet_hub_radius']:.2f} mm"]))
        dims_item.addChild(QTreeWidgetItem([f"Inlet tip R: {summary['inlet_tip_radius']:.2f} mm"]))
        dims_item.addChild(QTreeWidgetItem([f"Outlet hub R: {summary['outlet_hub_radius']:.2f} mm"]))
        dims_item.addChild(QTreeWidgetItem([f"Outlet tip R: {summary['outlet_tip_radius']:.2f} mm"]))
        self.info_tree.addTopLevelItem(dims_item)
        dims_item.setExpanded(True)
        
        # Arc lengths
        arcs_item = QTreeWidgetItem(["Arc Lengths"])
        arcs_item.addChild(QTreeWidgetItem([f"Hub: {summary['hub_arc_length']:.2f} mm"]))
        arcs_item.addChild(QTreeWidgetItem([f"Tip: {summary['tip_arc_length']:.2f} mm"]))
        self.info_tree.addTopLevelItem(arcs_item)
        arcs_item.setExpanded(True)
    
    def _update_validation(self):
        """Update the validation display."""
        is_valid, messages = self.design.validate()
        
        if messages:
            text = "<br>".join(
                f"{'⚠️' if 'Warning' in m else '❌' if 'Error' in m else 'ℹ️'} {m}"
                for m in messages
            )
        else:
            text = "✅ Design is valid"
        
        self.validation_label.setText(text)

    def _schedule_analysis_update(self) -> None:
        if self._analysis_update_timer.isActive():
            self._analysis_update_timer.stop()
        self._analysis_update_timer.start()

    def _update_analysis_plots(self):
        """Update analysis plots with current geometry."""
        if hasattr(self, 'analysis_widget'):
            if hasattr(self.analysis_widget, 'request_update'):
                self.analysis_widget.request_update()
            else:
                self.analysis_widget.update_plot()
    
    # Toolbar callbacks
    def _fit_view(self):
        self.diagram.fit_view()
    
    def _toggle_grid(self):
        self.grid_check.setChecked(not self.grid_check.isChecked())
    
    def _toggle_cps(self):
        self.cp_check.setChecked(not self.cp_check.isChecked())
    
    def _save_image(self):
        self.diagram._save_image()
    
    def _import_polyline(self):
        self.diagram._import_polyline()
    
    # Public methods
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh."""
        self.design = design
        self.diagram.set_design(design)
        self._load_from_design()
    
    def refresh(self):
        """Refresh all displays."""
        self.diagram.update_plot()
        self._update_info_tree()
        self._update_validation()
        self._schedule_analysis_update()
    
    def fit_view(self):
        """Fit the diagram view."""
        self.diagram.fit_view()

    def save_settings(self, settings: QSettings) -> None:
        settings.setValue("design_tab/splitter_sizes", self.splitter.sizes())

    def restore_settings(self, settings: QSettings) -> None:
        sizes = settings.value("design_tab/splitter_sizes")
        if sizes:
            self.splitter.setSizes([int(size) for size in sizes])
