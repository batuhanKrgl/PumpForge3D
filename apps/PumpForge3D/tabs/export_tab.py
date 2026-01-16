"""
Export Tab - wraps the existing StepEExport functionality.

This module provides the Export tab for the new unified layout.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from pumpforge3d_core.geometry.inducer import InducerDesign
from ..steps.step_e_export import StepEExport


class ExportTab(QWidget):
    """
    Export Tab wrapper.
    
    Wraps the existing StepEExport for compatibility with the new tab layout.
    All functionality is delegated to the inner widget.
    
    Signals:
        design_imported: Emitted when a design is imported
    """
    
    design_imported = Signal(object)  # InducerDesign
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.export_widget = StepEExport(self.design)
        self.export_widget.design_imported.connect(self._on_design_imported)
        layout.addWidget(self.export_widget)
    
    def _on_design_imported(self, design: InducerDesign):
        """Forward design import signal."""
        self.design = design
        self.design_imported.emit(design)
    
    def set_design(self, design: InducerDesign):
        """Set a new design."""
        self.design = design
        self.export_widget.set_design(design)
    
    def refresh(self):
        """Refresh the display."""
        self.export_widget.refresh()
    
    def export_json(self):
        """Trigger JSON export."""
        self.export_widget._export_json()
    
    def import_design(self):
        """Trigger design import."""
        self.export_widget._import_design()
