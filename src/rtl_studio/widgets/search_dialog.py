"""
Search Dialog
Responsibility: Project-wide text search for Verilog source files.
"""
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QTreeWidget, QTreeWidgetItem, QLabel,
                               QApplication, QListWidget, QListWidgetItem)  # <--- ADDED LIST WIDGETS HERE
from PySide6.QtCore import Qt


class SearchDialog(QDialog):
    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Project")
        self.resize(600, 400)
        self.project_path = project_path
        
        self.selected_file = None
        self.selected_line = 0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Search Input
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in Verilog files...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)
        
        # Results List
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        # Use monospace font for code results
        font = self.results_list.font()
        font.setFamily("monospace")
        self.results_list.setFont(font)
        layout.addWidget(self.results_list)
        
        # Status Label
        self.status_label = QLabel("Enter text to search project sources.")
        self.status_label.setStyleSheet("color: #92929A;")
        layout.addWidget(self.status_label)

    def perform_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        self.results_list.clear()
        self.status_label.setText("Searching...")
        QApplication.processEvents() # Force UI update before heavy search
        
        valid_exts = ('.v', '.sv', '.vh', '.svh')
        count = 0
        
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden and output directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("build", "dist", "__pycache__")]
            
            for f in files:
                if f.endswith(valid_exts):
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            for line_num, line_text in enumerate(file, 1):
                                if query in line_text:
                                    rel_path = os.path.relpath(filepath, self.project_path).replace('\\', '/')
                                    display_text = f"{rel_path}:{line_num}  |  {line_text.strip()}"
                                    
                                    item = QListWidgetItem(display_text)
                                    # Store full path and zero-indexed line number for the editor
                                    item.setData(Qt.ItemDataRole.UserRole, (filepath, line_num - 1))
                                    self.results_list.addItem(item)
                                    count += 1
                    except Exception:
                        pass
                        
        self.status_label.setText(f"Found {count} occurrence(s).")

    def on_item_double_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.selected_file, self.selected_line = data
            self.accept()