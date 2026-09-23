"""
Analysis Panel
Responsibility: Displays the parsed project hierarchy and Design / Synthesis statistics.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QTabWidget, QTextBrowser
from PySide6.QtCore import Qt, Signal
import os
import re

class AnalysisPanel(QWidget):
    module_double_clicked = Signal(str, int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Tab 1: Hierarchy ---
        self.hier_widget = QWidget()
        hier_layout = QVBoxLayout(self.hier_widget)
        hier_layout.setContentsMargins(4, 4, 4, 4)

        self.info_label = QLabel("No project loaded.")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #92929A; padding: 4px;")
        hier_layout.addWidget(self.info_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        hier_layout.addWidget(self.tree)
        
        self.tabs.addTab(self.hier_widget, "Hierarchy")

        # --- Tab 2: Design & PPA (Statistics) ---
        self.ppa_browser = QTextBrowser()
        self.ppa_browser.setOpenExternalLinks(False)
        self.tabs.addTab(self.ppa_browser, "Design & PPA")
        
        self.clear_ppa()

    def update_analysis(self, analyzer, config):
        self.tree.clear()
        if not analyzer.root_path or not config:
            self.info_label.setText("No project loaded.")
            return

        stats = (f"<b>Project:</b> {config.data.get('project_name', 'Unknown')}<br>"
                 f"<b>Sources:</b> {len(analyzer.rtl_files)}<br>"
                 f"<b>Modules:</b> {len(analyzer.modules)}<br>"
                 f"<b>Top Module:</b> {config.data.get('top_module') or 'None'}<br>"
                 f"<b>Testbench:</b> {config.data.get('testbench_module') or config.data.get('testbench') or 'None'}")
        self.info_label.setText(stats)

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

    def clear_ppa(self):
        self.ppa_browser.setHtml("<p style='padding:10px; color:#92929A;'>Synthesis required to view Design & PPA statistics.</p>")

    def update_ppa(self, log_text, analyzer, config):
        if not log_text:
            self.clear_ppa()
            return
            
        top_mod = config.data.get("top_module", "Unknown")
        mod_data = analyzer.modules.get(top_mod, {})
        
        num_inputs = mod_data.get("inputs", "—")
        num_outputs = mod_data.get("outputs", "—")
        num_regs = mod_data.get("regs", "—")
        num_modules = len([m for m, d in analyzer.modules.items() if not d.get("is_tb")])
        
        wires, cells, memories = "—", "—", "—"
        comb_cells, seq_cells = 0, 0
        total_cells_counted = 0
        cell_breakdown = ""
        
        clean_log = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', log_text)
        
        for line in clean_log.split('\n'):
            line_stripped = line.strip()
            low_line = line_stripped.lower()
            
            if line.startswith("==="):
                wires, cells, memories = "—", "—", "—"
                comb_cells, seq_cells, total_cells_counted = 0, 0, 0
                cell_breakdown = ""
                
            if low_line.startswith("number of wires:"): 
                wires = low_line.split(':')[-1].strip()
            elif low_line.startswith("number of memories:"): 
                memories = low_line.split(':')[-1].strip()
            elif low_line.startswith("number of cells:"): 
                cells = low_line.split(':')[-1].strip()
            elif "$_" in line_stripped or "\\" in line_stripped:
                parts = line_stripped.split()
                ctype, ccount = "", 0
                if len(parts) >= 2:
                    if parts[-1].isdigit():
                        ctype, ccount = " ".join(parts[:-1]), int(parts[-1])
                    elif parts[0].isdigit():
                        ctype, ccount = " ".join(parts[1:]), int(parts[0])
                        
                    if ctype:
                        cell_breakdown += f"<tr><td class='col1'>{ctype}</td><td>{ccount}</td></tr>"
                        total_cells_counted += ccount
                        if any(x in ctype.upper() for x in ["DFF", "LATCH", "SEQ", "FDRE", "FDC", "FDP"]):
                            seq_cells += ccount
                        else:
                            comb_cells += ccount
                            
        if cells == "—" and total_cells_counted > 0:
            cells = str(total_cells_counted)
            
        if not cell_breakdown:
            cell_breakdown = "<tr><td colspan='2' class='muted'>No cells inferred</td></tr>"
            if cells == "—": cells = "0"
            
        html = f"""
        <style>
            body {{ font-family: sans-serif; font-size: 12px; }}
            h3 {{ color: #d85c96; border-bottom: 1px solid #dcdce0; padding-bottom: 4px; margin-top: 16px; margin-bottom: 8px; font-size: 13px; text-transform: uppercase; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
            td {{ padding: 5px; border-bottom: 1px solid rgba(128,128,128,0.15); }}
            .col1 {{ font-weight: bold; width: 55%; opacity: 0.85; }}
            .muted {{ opacity: 0.6; font-style: italic; font-size: 11px; margin-top: 0px; }}
        </style>
        
        <h3>Design</h3>
        <table>
            <tr><td class="col1">Top Module</td><td>{top_mod}</td></tr>
            <tr><td class="col1">Modules</td><td>{num_modules}</td></tr>
            <tr><td class="col1">Inputs</td><td>{num_inputs}</td></tr>
            <tr><td class="col1">Outputs</td><td>{num_outputs}</td></tr>
            <tr><td class="col1">Registers / FFs</td><td>{num_regs}</td></tr>
            <tr><td class="col1">Internal Signals</td><td>{wires}</td></tr>
            <tr><td class="col1">Memories</td><td>{memories}</td></tr>
        </table>
        
        <h3>Synthesis</h3>
        <table>
            <tr><td class="col1">Total Cells</td><td>{cells}</td></tr>
            <tr><td class="col1">Combinational Cells</td><td>{comb_cells}</td></tr>
            <tr><td class="col1">Sequential Cells</td><td>{seq_cells}</td></tr>
        </table>
        
        <h3>Cell Breakdown</h3>
        <table>
            {cell_breakdown}
        </table>
        
        <h3>Area</h3>
        <p class="muted">Generic estimate based on synthesized cell statistics.</p>
        <table>
            <tr><td class="col1">Total Cells</td><td>{cells}</td></tr>
            <tr><td class="col1">Combinational</td><td>{comb_cells}</td></tr>
            <tr><td class="col1">Sequential</td><td>{seq_cells}</td></tr>
        </table>
        """
        self.ppa_browser.setHtml(html)

    def on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.module_double_clicked.emit(data["file"], data["line"])