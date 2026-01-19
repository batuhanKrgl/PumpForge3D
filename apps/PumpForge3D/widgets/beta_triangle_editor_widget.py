"""
Combined Beta Editor + Velocity Triangle Widget.

This module combines the Beta Distribution Editor with the Velocity Triangle
visualization as a single standalone widget.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter
)
from PySide6.QtCore import Qt

from apps.PumpForge3D.widgets.beta_editor_widget import BetaDistributionEditorWidget
from apps.PumpForge3D.widgets.velocity_triangle_widget import VelocityTriangleWidget


class BetaTriangleEditorWidget(QWidget):
    """
    Combined widget with:
    - Top: Velocity Triangles
    - Bottom: Beta Table + Beta-Theta Plot
    
    Changes to beta values automatically update velocity triangles.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()
        self._connect_signals()
        self._sync_beta_to_triangles()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top: Velocity triangles
        self.triangle_widget = VelocityTriangleWidget()
        splitter.addWidget(self.triangle_widget)
        
        # Bottom: Beta editor
        self.beta_widget = BetaDistributionEditorWidget()
        splitter.addWidget(self.beta_widget)
        
        # Set initial sizes (triangles smaller)
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect signals between widgets."""
        # When beta model changes, update triangles
        self.beta_widget.modelChanged.connect(self._sync_beta_to_triangles)
    
    def _sync_beta_to_triangles(self):
        """Sync beta values from table to velocity triangles."""
        model = self.beta_widget.get_model()
        
        # Hub = row 0, Tip = row N-1
        beta_in_hub = model.beta_in[0]
        beta_in_tip = model.beta_in[-1]
        beta_out_hub = model.beta_out[0]
        beta_out_tip = model.beta_out[-1]
        
        self.triangle_widget.set_beta_values(
            beta_in_hub, beta_in_tip,
            beta_out_hub, beta_out_tip
        )
    
    # Public API
    def get_beta_widget(self) -> BetaDistributionEditorWidget:
        """Get the beta editor widget."""
        return self.beta_widget
    
    def get_triangle_widget(self) -> VelocityTriangleWidget:
        """Get the velocity triangle widget."""
        return self.triangle_widget


# Standalone demo
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 11px; }
        QGroupBox { border: 1px solid #45475a; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        QTableWidget { background-color: #181825; gridline-color: #313244; border: 1px solid #313244; }
        QHeaderView::section { background-color: #313244; color: #cdd6f4; padding: 4px; border: none; }
        QSpinBox, QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 2px 4px; }
        QToolButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; }
        QToolButton:hover { background-color: #45475a; }
        QSplitter::handle { background-color: #45475a; height: 3px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Beta + Velocity Triangle Editor")
    window.resize(1100, 800)
    
    widget = BetaTriangleEditorWidget()
    window.setCentralWidget(widget)
    
    window.show()
    sys.exit(app.exec())
