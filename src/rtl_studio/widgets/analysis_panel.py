"""
Analysis Panel
Responsibility: Displays the parsed project structure and module list cleanly.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, Signal
import os

class AnalysisPanel(QWidget):
    module_double_clicked = Signal(str, int) # (filepath, line_number)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.info_label = QLabel("No project loaded.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #92929A; padding: 4px;")
        layout.addWidget(self.info_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)

    def update_analysis(self, analyzer, config):
        self.tree.clear()
        if not analyzer.root_path or not config:
            self.info_label.setText("No project loaded.")
            return

        # FIX: Safely use .get() for all configuration reads to prevent KeyError 
        # when migrating from Phase 5/7 schemas to the Phase 8 split schema.
        stats = (f"<b>Project:</b> {config.data.get('project_name', 'Unknown')}<br>"
                 f"<b>Sources:</b> {len(analyzer.rtl_files)}<br>"
                 f"<b>Modules:</b> {len(analyzer.modules)}<br>"
                 f"<b>Top Module:</b> {config.data.get('top_module') or 'None'}<br>"
                 f"<b>Testbench:</b> {config.data.get('testbench_module') or config.data.get('testbench') or 'None'}")
        self.info_label.setText(stats)

        # Build Tree
        top_node = QTreeWidgetItem(self.tree, ["Possible Top Modules"])
        tb_node = QTreeWidgetItem(self.tree, ["Possible Testbenches"])
        all_node = QTreeWidgetItem(self.tree, ["All Modules"])

        for mod in analyzer.top_modules:
            item = QTreeWidgetItem(top_node, [mod])
            item.setData(0, Qt.ItemDataRole.UserRole, analyzer.modules[mod])

        for mod in analyzer.testbenches:
            item = QTreeWidgetItem(tb_node, [mod])
            item.setData(0, Qt.ItemDataRole.UserRole, analyzer.modules[mod])

        for mod_name, data in analyzer.modules.items():
            item = QTreeWidgetItem(all_node, [mod_name])
            item.setData(0, Qt.ItemDataRole.UserRole, data)

        self.tree.expandAll()

    def on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data: # It's a module item
            self.module_double_clicked.emit(data["file"], data["line"])