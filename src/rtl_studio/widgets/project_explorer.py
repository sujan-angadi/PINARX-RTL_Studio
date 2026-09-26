"""
Project Explorer
Responsibility: Displays project files cleanly categorized and handles context menu actions.
"""
import os
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QStyle
from PySide6.QtCore import Qt, Signal

class ProjectExplorer(QTreeWidget):
    file_double_clicked = Signal(str)
    req_new_v = Signal()
    req_new_tb = Signal()
    req_rename = Signal(str)
    req_delete = Signal(str)
    req_reveal = Signal(str)
    req_refresh = Signal()

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_double_click)
        self.root_path = ""

    def load_project(self, path):
        self.clear()
        if not path or not os.path.exists(path):
            return
        
        self.root_path = path
        
        rtl_node = QTreeWidgetItem(self, ["RTL Sources"])
        tb_node = QTreeWidgetItem(self, ["Testbenches"])
        wave_node = QTreeWidgetItem(self, ["Waveforms"])
        synth_node = QTreeWidgetItem(self, ["Synthesis"])
        build_node = QTreeWidgetItem(self, ["Build Artifacts"])
        
        font = rtl_node.font(0)
        font.setBold(True)
        for node in [rtl_node, tb_node, wave_node, synth_node, build_node]:
            node.setFont(0, font)
            node.setExpanded(True)
            
        has_rtl, has_tb, has_wave, has_synth, has_build = False, False, False, False, False
        file_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("__pycache__")]
            
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, path).replace('\\', '/')
                
                item = QTreeWidgetItem([f])
                item.setData(0, Qt.ItemDataRole.UserRole, full_path)
                item.setIcon(0, file_icon)
                
                if f.endswith('.vcd'):
                    wave_node.addChild(item)
                    has_wave = True
                elif ".rtlstudio/synthesis" in rel_path:
                    synth_node.addChild(item)
                    has_synth = True
                elif ".rtlstudio/build" in rel_path:
                    build_node.addChild(item)
                    has_build = True
                elif f.endswith(('.v', '.sv', '.vh', '.svh')):
                    if "_tb" in f.lower() or "tb_" in f.lower():
                        tb_node.addChild(item)
                        has_tb = True
                    else:
                        rtl_node.addChild(item)
                        has_rtl = True
                        
        rtl_node.setHidden(not has_rtl)
        tb_node.setHidden(not has_tb)
        wave_node.setHidden(not has_wave)
        synth_node.setHidden(not has_synth)
        build_node.setHidden(not has_build)
        
        if not (has_rtl or has_tb or has_wave or has_synth or has_build):
            dummy = QTreeWidgetItem(self, ["(Empty Project)"])
            dummy.setDisabled(True)

    def on_double_click(self, item, column):
        filepath = item.data(0, Qt.ItemDataRole.UserRole)
        if filepath:
            self.file_double_clicked.emit(filepath)

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self)
        
        if item and item.data(0, Qt.ItemDataRole.UserRole):
            filepath = item.data(0, Qt.ItemDataRole.UserRole)
            open_act = menu.addAction("Open")
            open_act.triggered.connect(lambda: self.file_double_clicked.emit(filepath))
            
            # Only allow rename/delete on source files conceptually
            if filepath.endswith(('.v', '.sv', '.vh', '.svh')):
                rename_act = menu.addAction("Rename")
                rename_act.triggered.connect(lambda: self.req_rename.emit(filepath))
                
                del_act = menu.addAction("Delete")
                del_act.triggered.connect(lambda: self.req_delete.emit(filepath))
            
            menu.addSeparator()
            reveal_act = menu.addAction("Reveal in File Manager")
            reveal_act.triggered.connect(lambda: self.req_reveal.emit(filepath))
        else:
            new_v_act = menu.addAction("New Verilog File")
            new_v_act.triggered.connect(self.req_new_v.emit)
            
            new_tb_act = menu.addAction("New Testbench")
            new_tb_act.triggered.connect(self.req_new_tb.emit)
            
            menu.addSeparator()
            ref_act = menu.addAction("Refresh Project")
            ref_act.triggered.connect(self.req_refresh.emit)
            
            if self.root_path:
                reveal_act = menu.addAction("Reveal in File Manager")
                reveal_act.triggered.connect(lambda: self.req_reveal.emit(self.root_path))
        
        menu.exec(self.mapToGlobal(pos))