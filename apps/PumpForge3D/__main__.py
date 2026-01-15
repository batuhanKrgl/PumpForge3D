"""
PumpForge3D entry point.

Run with: python -m apps.PumpForge3D
"""

import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from apps.PumpForge3D.main_window import MainWindow


def main():
    """Application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("PumpForge3D")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("PumpForge")
    
    # Set default font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Apply modern dark theme
    app.setStyleSheet(get_stylesheet())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


def get_stylesheet() -> str:
    """Return the application stylesheet."""
    return """
    QMainWindow {
        background-color: #1e1e2e;
    }
    
    QWidget {
        background-color: #1e1e2e;
        color: #cdd6f4;
        font-family: 'Segoe UI', sans-serif;
    }
    
    QLabel {
        color: #cdd6f4;
        background-color: transparent;
    }
    
    QLabel#title {
        font-size: 14px;
        font-weight: bold;
        color: #89b4fa;
    }
    
    QPushButton {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 8px 16px;
        color: #cdd6f4;
        font-weight: 500;
    }
    
    QPushButton:hover {
        background-color: #45475a;
        border-color: #89b4fa;
    }
    
    QPushButton:pressed {
        background-color: #585b70;
    }
    
    QPushButton:checked {
        background-color: #89b4fa;
        color: #1e1e2e;
        border-color: #89b4fa;
    }
    
    QPushButton#navButton {
        text-align: left;
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 11px;
    }
    
    QPushButton#navButton:checked {
        background-color: #89b4fa;
        color: #1e1e2e;
    }
    
    QLineEdit, QSpinBox, QDoubleSpinBox {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 6px 10px;
        color: #cdd6f4;
    }
    
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border-color: #89b4fa;
    }
    
    QGroupBox {
        font-weight: bold;
        border: 1px solid #45475a;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 8px;
        background-color: #181825;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: #89b4fa;
    }
    
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    
    QScrollBar:vertical {
        background-color: #181825;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #45475a;
        border-radius: 6px;
        min-height: 30px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #585b70;
    }
    
    QCheckBox {
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #45475a;
        background-color: #313244;
    }
    
    QCheckBox::indicator:checked {
        background-color: #89b4fa;
        border-color: #89b4fa;
    }
    
    QComboBox {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 6px;
        padding: 6px 10px;
        color: #cdd6f4;
    }
    
    QComboBox::drop-down {
        border: none;
        padding-right: 10px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #313244;
        border: 1px solid #45475a;
        selection-background-color: #89b4fa;
        selection-color: #1e1e2e;
    }
    
    QSplitter::handle {
        background-color: #45475a;
    }
    
    QSplitter::handle:horizontal {
        width: 2px;
    }
    
    QSplitter::handle:vertical {
        height: 2px;
    }
    
    QMenu {
        background-color: #313244;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 4px;
    }
    
    QMenu::item {
        padding: 8px 24px;
        border-radius: 4px;
    }
    
    QMenu::item:selected {
        background-color: #89b4fa;
        color: #1e1e2e;
    }
    
    QMenu::separator {
        height: 1px;
        background-color: #45475a;
        margin: 4px 8px;
    }
    
    QStatusBar {
        background-color: #181825;
        color: #a6adc8;
    }
    
    QTextEdit {
        background-color: #181825;
        border: 1px solid #45475a;
        border-radius: 8px;
        padding: 8px;
        color: #cdd6f4;
    }
    
    QTabWidget::pane {
        border: 1px solid #45475a;
        border-radius: 8px;
        background-color: #181825;
    }
    
    QTabBar::tab {
        background-color: #313244;
        border: 1px solid #45475a;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        margin-right: 2px;
    }
    
    QTabBar::tab:selected {
        background-color: #181825;
        border-bottom: 2px solid #89b4fa;
    }
    """


if __name__ == "__main__":
    main()
