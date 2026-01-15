"""
Main window for PumpForge3D.

Provides the application shell with:
- Left navigation panel (Steps A-E)
- Central stacked widget for step panels
- Right info/warnings panel
- Status bar
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QSplitter,
    QTextEdit, QStatusBar, QMessageBox, QButtonGroup,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QAction

from pumpforge3d_core.geometry.inducer import InducerDesign

from .steps.step_a_main_dims import StepAMainDims
from .steps.step_b_meridional import StepBMeridional
from .steps.step_c_edges import StepCEdges
from .steps.step_d_views import StepDViews
from .steps.step_e_export import StepEExport


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Manages the design workflow with step-based navigation.
    """
    
    design_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("PumpForge3D — Inducer Meridional Designer")
        self.setMinimumSize(1200, 800)
        
        # Initialize design
        self.design = InducerDesign.create_default()
        
        # Setup UI
        self._setup_ui()
        self._setup_menu()
        self._setup_connections()
        
        # Start with Step A
        self._navigate_to_step(0)
    
    def _setup_ui(self):
        """Create the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left navigation panel
        nav_panel = self._create_nav_panel()
        main_layout.addWidget(nav_panel)
        
        # Main content splitter (steps + info panel)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Step content area
        self.step_stack = QStackedWidget()
        self._create_step_widgets()
        splitter.addWidget(self.step_stack)
        
        # Right info panel
        info_panel = self._create_info_panel()
        splitter.addWidget(info_panel)
        
        # Set splitter sizes (70% content, 30% info)
        splitter.setSizes([700, 300])
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_nav_panel(self) -> QWidget:
        """Create the left navigation panel."""
        nav_widget = QWidget()
        nav_widget.setFixedWidth(200)
        nav_widget.setStyleSheet("background-color: #181825;")
        
        layout = QVBoxLayout(nav_widget)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)
        
        # App title
        title = QLabel("PumpForge3D")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Inducer Designer")
        subtitle.setStyleSheet("color: #a6adc8; font-size: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Navigation buttons
        self.nav_buttons = []
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        steps = [
            ("A", "Main Dimensions", "Define basic geometry bounds"),
            ("B", "Meridional Contour", "Hub and tip curves"),
            ("C", "Leading/Trailing Edges", "Edge curves design"),
            ("D", "Analysis Views", "Curvature and area plots"),
            ("E", "Export", "Save and load designs"),
        ]
        
        for i, (letter, name, tooltip) in enumerate(steps):
            btn = QPushButton(f"  {letter}. {name}")
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setMinimumHeight(44)
            self.nav_group.addButton(btn, i)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Version info at bottom
        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet("color: #585b70; font-size: 10px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        return nav_widget
    
    def _create_step_widgets(self):
        """Create and add all step widgets to the stack."""
        self.step_a = StepAMainDims(self.design)
        self.step_b = StepBMeridional(self.design)
        self.step_c = StepCEdges(self.design)
        self.step_d = StepDViews(self.design)
        self.step_e = StepEExport(self.design)
        
        self.step_stack.addWidget(self.step_a)
        self.step_stack.addWidget(self.step_b)
        self.step_stack.addWidget(self.step_c)
        self.step_stack.addWidget(self.step_d)
        self.step_stack.addWidget(self.step_e)
    
    def _create_info_panel(self) -> QWidget:
        """Create the right info/warnings panel."""
        panel = QWidget()
        panel.setMinimumWidth(250)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("Design Info")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # Info display
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        self.info_display.setPlaceholderText("Design information will appear here...")
        layout.addWidget(self.info_display)
        
        # Warnings section
        warnings_title = QLabel("Validation")
        warnings_title.setObjectName("title")
        layout.addWidget(warnings_title)
        
        self.warnings_display = QTextEdit()
        self.warnings_display.setReadOnly(True)
        self.warnings_display.setMaximumHeight(150)
        self.warnings_display.setPlaceholderText("Validation messages...")
        layout.addWidget(self.warnings_display)
        
        return panel
    
    def _setup_menu(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Design", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_design)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_design)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save...", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_design)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        fit_action = QAction("&Fit View", self)
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self._fit_view)
        view_menu.addAction(fit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_connections(self):
        """Connect signals and slots."""
        # Navigation buttons
        self.nav_group.idClicked.connect(self._navigate_to_step)
        
        # Step signals
        self.step_a.dimensions_changed.connect(self._on_dimensions_changed)
        self.step_b.geometry_changed.connect(self._on_geometry_changed)
        self.step_c.geometry_changed.connect(self._on_geometry_changed)
        self.step_e.design_imported.connect(self._on_design_imported)
    
    def _navigate_to_step(self, index: int):
        """Navigate to a specific step."""
        self.step_stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        
        step_names = ["Main Dimensions", "Meridional Contour", 
                      "Leading/Trailing Edges", "Analysis Views", "Export"]
        self.status_bar.showMessage(f"Step {chr(65+index)}: {step_names[index]}")
        
        # Refresh the current step
        current_widget = self.step_stack.currentWidget()
        if hasattr(current_widget, 'refresh'):
            current_widget.refresh()
        
        self._update_info_panel()
    
    def _on_dimensions_changed(self):
        """Handle main dimensions change."""
        # Update contour endpoints
        self.design.contour.update_from_dimensions(self.design.main_dims)
        
        # Refresh dependent steps
        self.step_b.refresh()
        self.step_c.refresh()
        self.step_d.refresh()
        
        self._update_info_panel()
        self.design_changed.emit()
    
    def _on_geometry_changed(self):
        """Handle geometry change from curve editing."""
        self.step_d.refresh()
        self._update_info_panel()
        self.design_changed.emit()
    
    def _on_design_imported(self, design: InducerDesign):
        """Handle design import."""
        self.design = design
        
        # Update all steps with new design
        self.step_a.set_design(design)
        self.step_b.set_design(design)
        self.step_c.set_design(design)
        self.step_d.set_design(design)
        self.step_e.set_design(design)
        
        self._update_info_panel()
        self.status_bar.showMessage("Design imported successfully")
    
    def _update_info_panel(self):
        """Update the info and warnings panels."""
        # Update design info
        summary = self.design.get_summary()
        info_text = f"""<b>Design:</b> {summary['name']}<br>
<b>Units:</b> {summary['units']}<br>
<br>
<b>Main Dimensions:</b><br>
• Axial length: {summary['axial_length']:.1f} {summary['units']}<br>
• Inlet hub R: {summary['inlet_hub_radius']:.1f} {summary['units']}<br>
• Inlet tip R: {summary['inlet_tip_radius']:.1f} {summary['units']}<br>
• Outlet hub R: {summary['outlet_hub_radius']:.1f} {summary['units']}<br>
• Outlet tip R: {summary['outlet_tip_radius']:.1f} {summary['units']}<br>
<br>
<b>Arc Lengths:</b><br>
• Hub: {summary['hub_arc_length']:.1f} {summary['units']}<br>
• Tip: {summary['tip_arc_length']:.1f} {summary['units']}
"""
        self.info_display.setHtml(info_text)
        
        # Update validation
        is_valid, messages = self.design.validate()
        
        if messages:
            warnings_text = "<br>".join(
                f"{'⚠️' if 'Warning' in m else '❌' if 'Error' in m else 'ℹ️'} {m}"
                for m in messages
            )
        else:
            warnings_text = "✅ Design is valid"
        
        self.warnings_display.setHtml(warnings_text)
    
    def _new_design(self):
        """Create a new design."""
        reply = QMessageBox.question(
            self, "New Design",
            "Create a new design? Unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.design = InducerDesign.create_default()
            self._on_design_imported(self.design)
            self._navigate_to_step(0)
    
    def _open_design(self):
        """Open a design file."""
        self.step_e._import_design()
    
    def _save_design(self):
        """Save the current design."""
        self.step_e._export_json()
    
    def _fit_view(self):
        """Fit the current diagram view."""
        current_widget = self.step_stack.currentWidget()
        if hasattr(current_widget, 'fit_view'):
            current_widget.fit_view()
    
    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self, "About PumpForge3D",
            "<h2>PumpForge3D</h2>"
            "<p>Inducer Meridional Designer</p>"
            "<p>Version 0.1.0</p>"
            "<p>A modular tool for inducer geometry design, "
            "inspired by CFturbo workflow principles.</p>"
        )
