"""
Main window for PumpForge3D.

Provides the application shell with:
- Horizontal splitter: [Tab widget] | [3D viewer + object list]
- Tab widget with Design and Export tabs
- Undo/Redo support via QUndoStack
- Fullscreen toggle (F11)
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QStatusBar, QMessageBox,
    QToolBar, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QIcon, QKeySequence, QAction, QUndoStack

import logging

from pumpforge3d_core.geometry.inducer import InducerDesign

from .app.state.app_state import AppState
from .app.controllers.blade_properties_binder import BladePropertiesBinder
from .tabs.design_tab import DesignTab
from .tabs.blade_properties_tab import BladePropertiesTab
from .tabs.export_tab import ExportTab
from .widgets.viewer_3d import Viewer3DWidget
from .widgets.object_list import ObjectVisibilityList


# Global stylesheet for the application
STYLE_SHEET = """
QMainWindow {
    background-color: #1e1e2e;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Inter", sans-serif;
}

QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 4px;
    background: #1e1e2e;
}

QTabBar::tab {
    background: #313244;
    color: #a6adc8;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    background: #45475a;
    color: #cdd6f4;
}

QSplitter::handle {
    background: #313244;
    width: 4px;
    height: 4px;
}

QSplitter::handle:hover {
    background: #89b4fa;
}

QScrollArea {
    border: none;
    background: transparent;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
    color: #cdd6f4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #89b4fa;
}

QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 8px 16px;
    color: #cdd6f4;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #585b70;
}

QToolButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
    color: #cdd6f4;
}

QToolButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QDoubleSpinBox, QSpinBox, QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    color: #cdd6f4;
}

QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: #89b4fa;
}

QLineEdit[error="true"], QDoubleSpinBox[error="true"], QSpinBox[error="true"], QComboBox[error="true"] {
    border: 1px solid #f38ba8;
    background-color: #3a1f2d;
}

QTableWidget[error="true"] {
    border: 1px solid #f38ba8;
}

QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #45475a;
    background: #313244;
}

QCheckBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
}

QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    color: #cdd6f4;
}

QComboBox:hover {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QTreeWidget {
    background: #181825;
    border: 1px solid #313244;
    border-radius: 4px;
    color: #cdd6f4;
}

QTreeWidget::item:selected {
    background: #313244;
}

QTextEdit {
    background: #181825;
    border: 1px solid #313244;
    border-radius: 4px;
    color: #cdd6f4;
}

QStatusBar {
    background: #181825;
    color: #a6adc8;
}

QMenuBar {
    background: #181825;
    color: #cdd6f4;
}

QMenuBar::item:selected {
    background: #313244;
}

QMenu {
    background: #1e1e2e;
    border: 1px solid #313244;
    color: #cdd6f4;
}

QMenu::item:selected {
    background: #313244;
}

QToolBar {
    background: #181825;
    border: none;
    spacing: 4px;
    padding: 4px;
}

QLabel#title {
    font-size: 14px;
    font-weight: bold;
    color: #89b4fa;
}
"""


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Features:
    - Unified Design + Export tab layout
    - Persistent 3D viewer on the right
    - Undo/Redo support
    - Fullscreen toggle
    """
    
    design_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self._settings = QSettings("PumpForge3D", "PumpForge3D")
        self._settings_restored = False
        self._logger = logging.getLogger(__name__)

        self.setWindowTitle("PumpForge3D — Inducer Meridional Designer")
        self.setMinimumSize(1400, 900)
        
        # Apply stylesheet
        self.setStyleSheet(STYLE_SHEET)
        
        # Initialize undo stack
        self.undo_stack = QUndoStack(self)
        
        # Initialize design
        self.design = InducerDesign.create_default()
        self.state = AppState.create_default()
        
        # Setup UI
        self._setup_ui()
        self._setup_toolbar()
        self._setup_menu()
        self._setup_connections()
        self._restore_settings()
    
    def _setup_ui(self):
        """Create the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main horizontal splitter: [Tabs] | [3D + Objects]
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(4)
        
        # LEFT SIDE: Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumWidth(520)
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab_widget.setAccessibleName("Main tabs")
        self.tab_widget.setAccessibleDescription("Main navigation tabs for design, blade properties, and export.")
        
        # Design tab
        self.design_tab = DesignTab(self.design, undo_stack=self.undo_stack)
        self.tab_widget.addTab(self.design_tab, "Design")

        # Blade Properties tab
        self.blade_properties_tab = BladePropertiesTab(app_state=self.state)
        self.tab_widget.addTab(self.blade_properties_tab, "Blade properties")

        # Export tab (always last)
        self.export_tab = ExportTab(self.design)
        self.tab_widget.addTab(self.export_tab, "Export")
        
        self.main_splitter.addWidget(self.tab_widget)
        
        # RIGHT SIDE: 3D Viewer + Object list (vertical splitter)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setChildrenCollapsible(False)
        right_splitter.setHandleWidth(4)
        right_splitter.setMinimumWidth(320)
        
        # 3D Viewer
        self.viewer_3d = Viewer3DWidget(self.design)
        self.viewer_3d.setMinimumHeight(320)
        self.viewer_3d.setAccessibleName("3D viewer")
        self.viewer_3d.setAccessibleDescription("3D visualization of the inducer geometry.")
        right_splitter.addWidget(self.viewer_3d)
        
        # Object visibility list
        self.object_list = ObjectVisibilityList()
        self.object_list.setMinimumHeight(160)
        self.object_list.setAccessibleName("Object visibility list")
        self.object_list.setAccessibleDescription("Toggle visibility for geometry components.")
        right_splitter.addWidget(self.object_list)
        
        # Set right splitter proportions (80% viewer, 20% list)
        right_splitter.setSizes([600, 150])
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 1)
        
        self.main_splitter.addWidget(right_splitter)

        # Store right splitter reference for hiding/showing
        self.right_splitter = right_splitter

        # Set main splitter proportions (75% tabs, 25% 3D)
        self.main_splitter.setSizes([1000, 400])
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 1)

        # Store initial 3D viewer size for restoration
        self._viewer_size_before_hide = 400
        self._viewer_needs_refresh = False

        main_layout.addWidget(self.main_splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        self.status_bar.setAccessibleName("Status bar")
    
    def _setup_toolbar(self):
        """Create the toolbar with undo/redo buttons."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Undo action
        self.undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setText("↶ Undo")
        self.undo_action.setStatusTip("Undo the last change")
        toolbar.addAction(self.undo_action)
        
        # Redo action
        self.redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setText("↷ Redo")
        self.redo_action.setStatusTip("Redo the last change")
        toolbar.addAction(self.redo_action)
        
        toolbar.addSeparator()
        
        # Fit view
        fit_action = QAction("⤢ Fit", self)
        fit_action.setShortcut("F")
        fit_action.setToolTip("Fit view to geometry")
        fit_action.triggered.connect(self._fit_view)
        toolbar.addAction(fit_action)
        
        # Reset 3D camera
        reset_3d_action = QAction("🎥 Reset 3D", self)
        reset_3d_action.setToolTip("Reset 3D camera")
        reset_3d_action.triggered.connect(self._reset_3d_camera)
        toolbar.addAction(reset_3d_action)
    
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
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        fit_action = QAction("&Fit View", self)
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self._fit_view)
        view_menu.addAction(fit_action)
        
        view_menu.addSeparator()
        
        fullscreen_action = QAction("Toggle &Fullscreen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")

        help_action = QAction("&Help", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_connections(self):
        """Connect signals and slots."""
        # Design tab signals
        self.design_tab.geometry_changed.connect(self._on_geometry_changed)
        self.design_tab.dimensions_changed.connect(self._on_dimensions_changed)
        self.design_tab.geometry_committed.connect(self.state.apply_geometry_payload)
        
        # Export tab signals
        self.export_tab.design_imported.connect(self._on_design_imported)
        
        # Object visibility
        self.object_list.visibility_changed.connect(self._on_visibility_changed)
        
        # Tab change
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Blade properties -> inducer binding
        self.blade_binder = BladePropertiesBinder(self.blade_properties_tab, self.state, self)
        self.blade_binder.connect_signals()
        self.state.validation_failed.connect(self._on_state_validation_failed)
    
    def _on_geometry_changed(self):
        """Handle geometry change from design tab."""
        # Update 3D viewer only when visible
        if self.right_splitter.isVisible():
            self.viewer_3d.update_geometry(self.design)
        else:
            self._viewer_needs_refresh = True
        self.status_bar.showMessage("Geometry updated")
        self.design_changed.emit()
        self._logger.info("Geometry updated from design tab.")
    
    def _on_dimensions_changed(self):
        """Handle main dimensions change."""
        # Update 3D viewer only when visible
        if self.right_splitter.isVisible():
            self.viewer_3d.update_geometry(self.design)
        else:
            self._viewer_needs_refresh = True
        self.status_bar.showMessage("Dimensions updated")
        self.design_changed.emit()
        self._logger.info("Main dimensions updated.")
    
    def _on_design_imported(self, design: InducerDesign):
        """Handle design import."""
        self._logger.info("Design imported: %s", design.name)
        self.design = design
        self.undo_stack.clear()
        
        # Update all components
        self.design_tab.set_design(design)
        self.export_tab.set_design(design)
        self.viewer_3d.set_design(design)
        
        self.status_bar.showMessage(f"Design '{design.name}' imported successfully")
    
    def _on_visibility_changed(self, name: str, visible: bool):
        """Handle object visibility toggle."""
        self._logger.debug("Visibility toggle: %s=%s", name, visible)
        self.viewer_3d.set_object_visibility(name, visible)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change - hide 3D viewer for Blade Properties tab."""
        tab_names = ["Design", "Blade properties", "Export"]

        # Get current tab name
        current_tab_name = self.tab_widget.tabText(index)

        # Hide 3D viewer for Blade Properties tab
        if current_tab_name == "Blade properties":
            # Store current splitter sizes if not already hidden
            sizes = self.main_splitter.sizes()
            if sizes[1] > 0:
                self._viewer_size_before_hide = sizes[1]

            # Hide the right panel (3D viewer + object list)
            self.right_splitter.setVisible(False)
            self.main_splitter.setSizes([sizes[0] + sizes[1], 0])

            self.status_bar.showMessage("Blade properties tab (3D viewer hidden)")
            if hasattr(self, "blade_binder"):
                self.blade_binder.refresh_from_state(reason="tab_enter")
        else:
            # Show 3D viewer for other tabs
            if not self.right_splitter.isVisible():
                self.right_splitter.setVisible(True)
                # Restore previous size
                total_width = self.main_splitter.width()
                tab_width = total_width - self._viewer_size_before_hide
                self.main_splitter.setSizes([tab_width, self._viewer_size_before_hide])
                if self._viewer_needs_refresh:
                    self.viewer_3d.update_geometry(self.design)
                    self._viewer_needs_refresh = False

            if 0 <= index < len(tab_names):
                self.status_bar.showMessage(f"{tab_names[index]} tab")
                self._logger.debug("Tab changed to %s.", tab_names[index])
    
    def _new_design(self):
        """Create a new design."""
        self._logger.info("New design requested.")
        reply = QMessageBox.question(
            self, "New Design",
            "Create a new design? Unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.design = InducerDesign.create_default()
            self.undo_stack.clear()
            self._on_design_imported(self.design)
            self.tab_widget.setCurrentIndex(0)
    
    def _open_design(self):
        """Open a design file."""
        self._logger.info("Open design action triggered.")
        self.export_tab.import_design()
    
    def _save_design(self):
        """Save the current design."""
        self._logger.info("Save design action triggered.")
        self.export_tab.export_json()
    
    def _fit_view(self):
        """Fit the current diagram view."""
        self.design_tab.fit_view()
    
    def _reset_3d_camera(self):
        """Reset 3D viewer camera."""
        self.viewer_3d.reset_camera()
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _show_help(self):
        """Show a help placeholder dialog."""
        self._logger.info("Help dialog opened.")
        QMessageBox.information(
            self, "PumpForge3D Help",
            "<h3>PumpForge3D Help</h3>"
            "<p>Keyboard shortcuts:</p>"
            "<ul>"
            "<li><b>Ctrl+O</b>: Open design</li>"
            "<li><b>Ctrl+S</b>: Save design</li>"
            "<li><b>F1</b>: Help</li>"
            "</ul>"
            "<p>Editing policy: changes are committed on Enter or focus-out.</p>"
        )
    
    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self, "About PumpForge3D",
            "<h2>PumpForge3D</h2>"
            "<p>Inducer Meridional Designer</p>"
            "<p>Version 0.2.0</p>"
            "<p>A modular tool for inducer geometry design, "
            "inspired by CFturbo workflow principles.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Interactive Bezier curve editing</li>"
            "<li>Real-time 3D visualization</li>"
            "<li>Undo/Redo support</li>"
            "<li>Versioned JSON export</li>"
            "</ul>"
        )

    def _on_state_validation_failed(self, message: str) -> None:
        self.status_bar.showMessage(f"Validation error: {message}")
        self._logger.warning("Validation error: %s", message)

    def _restore_settings(self) -> None:
        if self._settings_restored:
            return
        geometry = self._settings.value("main_window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.showMaximized()
        splitter_sizes = self._settings.value("main_window/splitter_sizes")
        if splitter_sizes:
            self.main_splitter.setSizes([int(size) for size in splitter_sizes])
        right_sizes = self._settings.value("main_window/right_splitter_sizes")
        if right_sizes:
            self.right_splitter.setSizes([int(size) for size in right_sizes])
        self.design_tab.restore_settings(self._settings)
        self.blade_properties_tab.restore_settings(self._settings)
        self._settings_restored = True

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self._settings.setValue("main_window/geometry", self.saveGeometry())
        self._settings.setValue("main_window/splitter_sizes", self.main_splitter.sizes())
        self._settings.setValue("main_window/right_splitter_sizes", self.right_splitter.sizes())
        self.design_tab.save_settings(self._settings)
        self.blade_properties_tab.save_settings(self._settings)
        super().closeEvent(event)
