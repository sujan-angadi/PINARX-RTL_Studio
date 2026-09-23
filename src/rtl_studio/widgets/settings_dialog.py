"""
Editor Settings Dialog
Responsibility: Configure font, tabs, and line numbers securely via QSettings.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSpinBox, QCheckBox, QPushButton, QComboBox)
from PySide6.QtCore import QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editor Settings")
        self.resize(300, 200)
        self.settings = QSettings("PINARX", "RTL_Studio")
        
        layout = QVBoxLayout(self)

        # Tab Width
        tab_layout = QHBoxLayout()
        tab_layout.addWidget(QLabel("Tab Width:"))
        self.tab_spin = QSpinBox()
        self.tab_spin.setRange(2, 8)
        self.tab_spin.setValue(int(self.settings.value("tab_width", 4)))
        tab_layout.addWidget(self.tab_spin)
        layout.addLayout(tab_layout)

        # Font Size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setValue(int(self.settings.value("font_size", 11)))
        font_layout.addWidget(self.font_spin)
        layout.addLayout(font_layout)

        # Checkboxes
        self.spaces_check = QCheckBox("Use Spaces instead of Tabs")
        self.spaces_check.setChecked(self.settings.value("use_spaces", True, type=bool))
        layout.addWidget(self.spaces_check)

        self.line_num_check = QCheckBox("Show Line Numbers")
        self.line_num_check.setChecked(self.settings.value("show_line_numbers", True, type=bool))
        layout.addWidget(self.line_num_check)
        
        self.current_line_check = QCheckBox("Highlight Current Line")
        self.current_line_check.setChecked(self.settings.value("highlight_current_line", True, type=bool))
        layout.addWidget(self.current_line_check)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def save_settings(self):
        self.settings.setValue("tab_width", self.tab_spin.value())
        self.settings.setValue("font_size", self.font_spin.value())
        self.settings.setValue("use_spaces", self.spaces_check.isChecked())
        self.settings.setValue("show_line_numbers", self.line_num_check.isChecked())
        self.settings.setValue("highlight_current_line", self.current_line_check.isChecked())
        self.accept()