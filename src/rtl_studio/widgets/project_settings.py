"""
Project Settings Dialog
Responsibility: Configure the active Top Module, Testbench, and cleanly split Source Files.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QListWidget, QFileDialog)
from PySide6.QtCore import Qt
import os

class ProjectSettingsDialog(QDialog):
    def __init__(self, config, analyzer, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Project Settings - {config.data['project_name']}")
        self.resize(550, 500)
        self.config = config
        self.analyzer = analyzer

        layout = QVBoxLayout(self)

        # Top Module (Hardware) - Only show non-testbench modules
        layout.addWidget(QLabel("Design Top Module:"))
        self.top_combo = QComboBox()
        self.top_combo.addItem("")
        design_mods = [m for m, d in analyzer.modules.items() if not d["is_tb"]]
        self.top_combo.addItems(design_mods)
        self.top_combo.setCurrentText(config.data.get("top_module", ""))
        layout.addWidget(self.top_combo)

        # Testbench Module (Simulation)
        layout.addWidget(QLabel("Simulation Testbench Module:"))
        self.tb_combo = QComboBox()
        self.tb_combo.addItem("")
        self.tb_combo.addItems(analyzer.testbenches)
        self.tb_combo.setCurrentText(config.data.get("testbench_module", ""))
        layout.addWidget(self.tb_combo)

        # Split Source Lists
        lists_layout = QHBoxLayout()
        
        design_layout = QVBoxLayout()
        design_layout.addWidget(QLabel("Design Sources (Synthesis):"))
        self.design_list = QListWidget()
        for src in config.data.get("design_sources", []): self.design_list.addItem(src)
        design_layout.addWidget(self.design_list)
        lists_layout.addLayout(design_layout)
        
        tb_layout = QVBoxLayout()
        tb_layout.addWidget(QLabel("Testbench Sources (Sim Only):"))
        self.tb_list = QListWidget()
        for src in config.data.get("testbench_sources", []): self.tb_list.addItem(src)
        tb_layout.addWidget(self.tb_list)
        lists_layout.addLayout(tb_layout)
        
        layout.addLayout(lists_layout)

        # Auto-Detect Button
        btn_layout = QHBoxLayout()
        auto_btn = QPushButton("Auto-Detect All Sources")
        auto_btn.clicked.connect(self.auto_detect)
        btn_layout.addWidget(auto_btn)
        layout.addLayout(btn_layout)

        # Dialog Buttons
        dialog_btns = QHBoxLayout()
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        dialog_btns.addStretch()
        dialog_btns.addWidget(cancel_btn)
        dialog_btns.addWidget(save_btn)
        layout.addLayout(dialog_btns)

    def auto_detect(self):
        self.design_list.clear()
        self.tb_list.clear()
        for f in self.analyzer.rtl_files:
            rel = os.path.relpath(f, self.config.root_path)
            is_tb = False
            for m in self.analyzer.modules.values():
                if m["file"] == f and m["is_tb"]:
                    is_tb = True
                    break
            if is_tb:
                self.tb_list.addItem(rel)
            else:
                self.design_list.addItem(rel)

    def save_settings(self):
        self.config.data["top_module"] = self.top_combo.currentText()
        self.config.data["testbench_module"] = self.tb_combo.currentText()
        self.config.data["design_sources"] = [self.design_list.item(i).text() for i in range(self.design_list.count())]
        self.config.data["testbench_sources"] = [self.tb_list.item(i).text() for i in range(self.tb_list.count())]
        self.config.save()
        self.accept()