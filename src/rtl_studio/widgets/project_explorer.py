"""
Project Explorer
Responsibility: Displays and manages the actual project file tree with centralized icon assignment.
"""
import os
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QFileIconProvider
from PySide6.QtCore import Qt, Signal, QFileInfo

IGNORE_DIRS = {".git", "__pycache__", ".venv", "build", "dist", "target", "node_modules", ".idea", ".vscode"}

class ProjectExplorer(QTreeWidget):
    file_double_clicked = Signal(str) # Emits the absolute path of the file

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["PROJECT"])
        self.setAnimated(True)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.project_root = None
        
        # Native Qt provider that intelligently determines the correct icon for files/folders
        self.icon_provider = QFileIconProvider()

    def assign_icon(self, item, path):
        """
        Centralized logic to assign the correct icon based on the filesystem item.
        This guarantees new, existing, and renamed items all receive consistent icons.
        """
        file_info = QFileInfo(path)
        icon = self.icon_provider.icon(file_info)
        item.setIcon(0, icon)

    def load_project(self, root_path):
        """Clears the tree and populates it with the filesystem structure."""
        self.clear()
        self.project_root = root_path
        if not root_path or not os.path.exists(root_path):
            return

        self.setHeaderLabels([os.path.basename(root_path)])
        self.populate_tree(self.invisibleRootItem(), root_path)
        
        # Expand root level folders automatically
        for i in range(self.topLevelItemCount()):
            self.topLevelItem(i).setExpanded(True)

    def populate_tree(self, parent_item, dir_path):
        """Recursively populates the tree, sorting folders first, then files."""
        try:
            entries = os.listdir(dir_path)
        except PermissionError:
            return

        folders = []
        files = []

        for entry in entries:
            if entry in IGNORE_DIRS:
                continue
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                folders.append((entry, full_path))
            else:
                files.append((entry, full_path))

        # Alphabetical sorting
        folders.sort(key=lambda x: x[0].lower())
        files.sort(key=lambda x: x[0].lower())

        # Process Folders
        for name, path in folders:
            item = QTreeWidgetItem(parent_item, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            self.assign_icon(item, path)  # <-- Centralized Icon Assignment
            self.populate_tree(item, path)

        # Process Files
        for name, path in files:
            item = QTreeWidgetItem(parent_item, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            self.assign_icon(item, path)  # <-- Centralized Icon Assignment

    def on_item_double_clicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isfile(path):
            self.file_double_clicked.emit(path)

    def get_selected_path(self):
        """Returns the path of the currently selected item, or the project root."""
        items = self.selectedItems()
        if items:
            return items[0].data(0, Qt.ItemDataRole.UserRole)
        return self.project_root