"""
Search Dialog
Responsibility: Provides a lightweight local text search within RTL files.
"""
import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt

class SearchDialog(QDialog):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Search")
        self.resize(600, 400)
        self.project_root = project_root
        self.selected_file = None
        self.selected_line = None

        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search .v, .sv, .vh files...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.on_result_clicked)
        layout.addWidget(self.results_list)

    def perform_search(self):
        self.results_list.clear()
        query = self.search_input.text().strip()
        if not query or not self.project_root: return

        valid_exts = ('.v', '.sv', '.vh', '.svh')
        for root_dir, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("build", "dist", "__pycache__")]
            for file in files:
                if file.endswith(valid_exts):
                    path = os.path.join(root_dir, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            for i, line in enumerate(f):
                                if query in line:
                                    rel_path = os.path.relpath(path, self.project_root)
                                    item_text = f"{rel_path}:{i+1}  -  {line.strip()}"
                                    item = QListWidgetItem(item_text)
                                    item.setData(Qt.ItemDataRole.UserRole, (path, i))
                                    self.results_list.addItem(item)
                    except Exception: pass

    def on_result_clicked(self, item):
        self.selected_file, self.selected_line = item.data(Qt.ItemDataRole.UserRole)
        self.accept()