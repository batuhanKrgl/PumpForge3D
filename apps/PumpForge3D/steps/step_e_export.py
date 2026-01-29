"""
Step E: Export panel.

Export and import inducer designs.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QPushButton, QFileDialog, QMessageBox,
    QLineEdit, QFormLayout, QTextEdit
)
from PySide6.QtCore import Qt, Signal

import logging

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.io.export import export_json, export_csv_samples, export_summary
from pumpforge3d_core.io.import_handler import import_json
from pumpforge3d_core.io.schema import SCHEMA_VERSION
from pumpforge3d_core.validation.checks import validate_design
from ..utils.editor_commit_filter import attach_commit_filter

logger = logging.getLogger(__name__)


class StepEExport(QWidget):
    """
    Step E: Export / Import panel.
    
    Signals:
        design_imported: Emitted when a design is successfully imported
    """
    
    design_imported = Signal(object)  # InducerDesign
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("Step E: Export & Import")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        description = QLabel(
            "Save your design to a versioned JSON file or load an existing design. "
            "You can also export sampled geometry points as CSV."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a6adc8; margin-bottom: 16px;")
        layout.addWidget(description)
        
        # Design info
        info_group = QGroupBox("Design Information")
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.design.name)
        self.name_edit.setProperty("last_valid_value", self.design.name)
        self.name_edit.editingFinished.connect(self._update_name)
        name_label = QLabel("Design Name:")
        name_label.setBuddy(self.name_edit)
        info_layout.addRow(name_label, self.name_edit)
        self.name_edit.setAccessibleName("Design name")
        self.name_edit.setAccessibleDescription("Name for the current design.")
        attach_commit_filter(self.name_edit)
        
        schema_label = QLabel(f"Schema Version: {SCHEMA_VERSION}")
        schema_label.setStyleSheet("color: #a6adc8;")
        info_layout.addRow(schema_label)
        
        layout.addWidget(info_group)
        
        # Export options
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        
        export_btn_layout = QHBoxLayout()
        
        json_btn = QPushButton("Export JSON")
        json_btn.clicked.connect(self._export_json)
        json_btn.setAccessibleName("Export JSON")
        json_btn.setAccessibleDescription("Export the design to JSON.")
        export_btn_layout.addWidget(json_btn)
        
        csv_btn = QPushButton("Export CSV Samples")
        csv_btn.clicked.connect(self._export_csv)
        csv_btn.setAccessibleName("Export CSV samples")
        csv_btn.setAccessibleDescription("Export sampled geometry points as CSV.")
        export_btn_layout.addWidget(csv_btn)
        
        summary_btn = QPushButton("Export Summary")
        summary_btn.clicked.connect(self._export_summary)
        summary_btn.setAccessibleName("Export summary")
        summary_btn.setAccessibleDescription("Export a text summary of the design.")
        export_btn_layout.addWidget(summary_btn)
        
        export_layout.addLayout(export_btn_layout)
        layout.addWidget(export_group)
        
        # Import options
        import_group = QGroupBox("Import")
        import_layout = QVBoxLayout(import_group)
        
        import_btn = QPushButton("Import JSON Design...")
        import_btn.clicked.connect(self._import_design)
        import_btn.setAccessibleName("Import design")
        import_btn.setAccessibleDescription("Import a design from JSON.")
        import_layout.addWidget(import_btn)
        
        layout.addWidget(import_group)
        
        # Validation
        validation_group = QGroupBox("Validation")
        val_layout = QVBoxLayout(validation_group)
        
        validate_btn = QPushButton("Validate Design")
        validate_btn.clicked.connect(self._run_validation)
        validate_btn.setAccessibleName("Validate design")
        validate_btn.setAccessibleDescription("Run validation checks for the design.")
        val_layout.addWidget(validate_btn)
        
        self.validation_display = QTextEdit()
        self.validation_display.setReadOnly(True)
        self.validation_display.setMaximumHeight(200)
        self.validation_display.setAccessibleName("Validation output")
        val_layout.addWidget(self.validation_display)
        
        layout.addWidget(validation_group)
        
        layout.addStretch()
    
    def _update_name(self):
        """Update the design name."""
        self.design.name = self.name_edit.text()
        self.name_edit.setProperty("last_valid_value", self.design.name)
        logger.info("Design name updated to %s.", self.design.name)
    
    def _export_json(self):
        """Export the design to JSON."""
        logger.info("Export JSON requested.")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Design",
            f"{self.design.name}.json",
            "JSON Files (*.json)"
        )
        
        if path:
            try:
                export_json(self.design, Path(path))
                QMessageBox.information(
                    self, "Export Successful",
                    f"Design exported to:\n{path}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Error", str(e))
    
    def _export_csv(self):
        """Export sampled geometry to CSV."""
        logger.info("Export CSV samples requested.")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV Samples",
            f"{self.design.name}",
            "Base name (will create _hub.csv, etc.)"
        )
        
        if path:
            try:
                export_csv_samples(self.design, Path(path))
                QMessageBox.information(
                    self, "Export Successful",
                    f"CSV files exported with base name:\n{path}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Error", str(e))
    
    def _export_summary(self):
        """Export a human-readable summary."""
        logger.info("Export summary requested.")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Summary",
            f"{self.design.name}_summary.txt",
            "Text Files (*.txt)"
        )
        
        if path:
            try:
                export_summary(self.design, Path(path))
                QMessageBox.information(
                    self, "Export Successful",
                    f"Summary exported to:\n{path}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Error", str(e))
    
    def _import_design(self):
        """Import a design from JSON."""
        logger.info("Import design requested.")
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Design",
            "",
            "JSON Files (*.json)"
        )
        
        if path:
            try:
                design, warnings = import_json(Path(path))
                
                if warnings:
                    warning_text = "\n".join(warnings)
                    QMessageBox.warning(
                        self, "Import Warnings",
                        f"Design imported with warnings:\n\n{warning_text}"
                    )
                
                self.design = design
                self.name_edit.setText(design.name)
                self.design_imported.emit(design)
                
                QMessageBox.information(
                    self, "Import Successful",
                    f"Design '{design.name}' imported successfully."
                )
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))
    
    def _run_validation(self):
        """Run validation and display results."""
        logger.info("Validation run requested.")
        result = validate_design(self.design)
        
        lines = []
        if result.is_valid:
            lines.append("✅ <b>Design is valid</b><br>")
        else:
            lines.append("❌ <b>Design has issues</b><br>")
        
        for msg in result.errors:
            lines.append(f"❌ [{msg.code}] {msg.message}")
        
        for msg in result.warnings:
            lines.append(f"⚠️ [{msg.code}] {msg.message}")
        
        for msg in result.info:
            lines.append(f"ℹ️ [{msg.code}] {msg.message}")
        
        self.validation_display.setHtml("<br>".join(lines))
    
    def set_design(self, design: InducerDesign):
        """Set a new design."""
        self.design = design
        self.name_edit.setText(design.name)
    
    def refresh(self):
        """Refresh the display."""
        self.name_edit.setText(self.design.name)
