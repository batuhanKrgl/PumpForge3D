"""
Object visibility list widget for the 3D viewer.

Displays checkboxes for each rendered object to control their visibility.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QScrollArea, QFrame
)
from PySide6.QtCore import Signal


class ObjectVisibilityList(QWidget):
    """
    Widget with checkboxes to control 3D object visibility.
    
    Signals:
        visibility_changed: Emitted when any checkbox is toggled (name, visible)
    """
    
    visibility_changed = Signal(str, bool)
    
    # Default objects and their display names
    OBJECTS = [
        ('hub', 'Hub Curve'),
        ('tip', 'Tip Curve'),
        ('leading_edge', 'Leading Edge'),
        ('trailing_edge', 'Trailing Edge'),
        ('inlet_hub_circle', 'Inlet Hub Circle'),
        ('inlet_tip_circle', 'Inlet Tip Circle'),
        ('outlet_hub_circle', 'Outlet Hub Circle'),
        ('outlet_tip_circle', 'Outlet Tip Circle'),
        ('reference', 'Reference Polyline'),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checkboxes = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Title
        title = QLabel("Displayed Objects")
        title.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 12px;")
        layout.addWidget(title)
        
        # Scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(200)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 4, 0, 0)
        container_layout.setSpacing(2)
        
        # Create checkboxes for each object
        for obj_name, display_name in self.OBJECTS:
            checkbox = QCheckBox(display_name)
            checkbox.setChecked(True)
            checkbox.setStyleSheet("color: #cdd6f4;")
            checkbox.toggled.connect(lambda checked, name=obj_name: self._on_toggled(name, checked))
            container_layout.addWidget(checkbox)
            self._checkboxes[obj_name] = checkbox
        
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Show/Hide all buttons
        from PySide6.QtWidgets import QHBoxLayout, QPushButton
        
        btn_layout = QHBoxLayout()
        
        show_all_btn = QPushButton("Show All")
        show_all_btn.setFixedHeight(24)
        show_all_btn.clicked.connect(self._show_all)
        btn_layout.addWidget(show_all_btn)
        
        hide_all_btn = QPushButton("Hide All")
        hide_all_btn.setFixedHeight(24)
        hide_all_btn.clicked.connect(self._hide_all)
        btn_layout.addWidget(hide_all_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_toggled(self, name: str, visible: bool):
        """Handle checkbox toggle."""
        self.visibility_changed.emit(name, visible)
    
    def _show_all(self):
        """Show all objects."""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(True)
    
    def _hide_all(self):
        """Hide all objects."""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)
    
    def set_visibility(self, name: str, visible: bool):
        """Set a specific checkbox state without emitting signal."""
        if name in self._checkboxes:
            self._checkboxes[name].blockSignals(True)
            self._checkboxes[name].setChecked(visible)
            self._checkboxes[name].blockSignals(False)
    
    def get_visibility(self, name: str) -> bool:
        """Get visibility state for an object."""
        if name in self._checkboxes:
            return self._checkboxes[name].isChecked()
        return True
