"""
Main Window
Responsibility: Central IDE orchestration, Project Explorer context logic, RTL Analysis, and EDA tools.
Version: 1.0 Release
"""
import os
import shutil
import re
import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
                               QLabel, QStatusBar, QApplication, QFileDialog, 
                               QMessageBox, QInputDialog, QLineEdit, QPushButton, QTabWidget, QToolBar)
from PySide6.QtCore import Qt, QSettings, QProcess, QUrl
from PySide6.QtGui import QAction, QKeySequence, QTextCursor, QTextDocument, QDesktopServices

from src.rtl_studio.theme import get_stylesheet, create_eda_icon
from src.rtl_studio.widgets.project_explorer import ProjectExplorer
from src.rtl_studio.widgets.editor import EditorTabs
from src.rtl_studio.widgets.output_panel import OutputPanel
from src.rtl_studio.widgets.search_dialog import SearchDialog
from src.rtl_studio.widgets.settings_dialog import SettingsDialog
from src.rtl_studio.widgets.analysis_panel import AnalysisPanel
from src.rtl_studio.widgets.project_settings import ProjectSettingsDialog
from src.rtl_studio.widgets.schematic_viewer import SchematicViewer
from src.rtl_studio.project_analyzer import ProjectAnalyzer
from src.rtl_studio.project_config import ProjectConfig
from src.rtl_studio.eda_tools import IcarusToolchain, GTKWaveTool, YosysTool, GraphvizTool

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTL Studio")
        self.resize(1200, 800)
        self.settings = QSettings("PINARX", "RTL_Studio")
        
        self.is_dark_theme = self.settings.value("is_dark_theme", False, type=bool)
        self.is_productive_theme = False
        self.is_candy_theme = False
        
        self.current_project = None
        self.project_config = None
        self.project_analyzer = None
        self.current_vcd = None
        self.schematic_viewer_dialog = None
        
        self.icarus = IcarusToolchain()
        self.gtkwave = GTKWaveTool()
        self.yosys = YosysTool()
        self.graphviz = GraphvizTool()
        
        self.build_process = QProcess(self)
        self.build_process.readyReadStandardOutput.connect(self.handle_build_stdout)
        self.build_process.readyReadStandardError.connect(self.handle_build_stderr)
        self.build_process.finished.connect(self.handle_build_finished)

        self.sim_process = QProcess(self)
        self.sim_process.readyReadStandardOutput.connect(self.handle_sim_stdout)
        self.sim_process.readyReadStandardError.connect(self.handle_sim_stderr)
        self.sim_process.finished.connect(self.handle_sim_finished)

        self.gtkwave_process = QProcess(self)
        self.gtkwave_process.finished.connect(lambda: self.output_panel.log("GTKWave viewer closed.", "INFO"))
        
        self.yosys_process = QProcess(self)
        self.yosys_process.readyReadStandardOutput.connect(self.handle_yosys_stdout)
        self.yosys_process.readyReadStandardError.connect(self.handle_yosys_stderr)
        self.yosys_process.finished.connect(self.handle_yosys_finished)
        self.yosys_output_buffer = ""
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.apply_theme()
        
        self.output_panel.log("Application started successfully.", "SUCCESS")
        self.check_eda_tools()
        self.update_toolbar_state()

    def check_eda_tools(self):
        status_text = ""
        
        if self.icarus.available:
            status_text += f" Icarus: v{self.icarus.version} "
        else:
            status_text += " Icarus: Not Found "
            self.output_panel.log("Icarus Verilog was not found. Install Icarus Verilog and ensure it is available in PATH. Then restart RTL Studio.", "ERROR")

        if self.gtkwave.available:
            status_text += f"| GTKWave: v{self.gtkwave.version} "
        else:
            status_text += "| GTKWave: Not Found "
            self.output_panel.log("GTKWave was not found. Install GTKWave and ensure it is available in PATH.", "ERROR")
            
        if self.yosys.available:
            status_text += f"| Yosys: v{self.yosys.version} "
        else:
            status_text += "| Yosys: Not Found "
            self.output_panel.log("Yosys was not found. Install Yosys (e.g. via OSS CAD Suite) and ensure it is available in PATH. Then restart RTL Studio.", "ERROR")
            
        if self.graphviz.available:
            status_text += f"| Graphviz: v{self.graphviz.version} "
        else:
            status_text += "| Graphviz: Not Found "
            self.output_panel.log("Graphviz (dot) was not found. Ensure it is in your PATH. Schematic generation will be skipped.", "WARNING")

        self.eda_status_label.setText(status_text)
        if not self.icarus.available or not self.gtkwave.available or not self.yosys.available:
            self.eda_status_label.setStyleSheet("color: #E01A4F; font-weight: bold;")

    def setup_ui(self):
        self.left_tabs = QTabWidget()
        
        self.project_explorer = ProjectExplorer()
        self.project_explorer.file_double_clicked.connect(self.open_file_in_editor)
        self.project_explorer.req_new_v.connect(self.handle_req_new_v)
        self.project_explorer.req_new_tb.connect(self.handle_req_new_tb)
        self.project_explorer.req_rename.connect(self.handle_req_rename)
        self.project_explorer.req_delete.connect(self.handle_req_delete)
        self.project_explorer.req_refresh.connect(self.handle_req_refresh)
        self.project_explorer.req_reveal.connect(self.handle_req_reveal)
        self.left_tabs.addTab(self.project_explorer, "Files")
        
        self.analysis_panel = AnalysisPanel()
        self.analysis_panel.module_double_clicked.connect(self.goto_module_definition)
        self.left_tabs.addTab(self.analysis_panel, "Analysis")

        self.editor_tabs = EditorTabs(self.is_dark_theme)
        self.editor_tabs.file_saved.connect(self.on_file_saved)
        self.editor_tabs.editor_status_changed.connect(self.update_status_bar)

        self.find_bar = QWidget()
        self.find_bar.hide()
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(4, 4, 4, 4)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find...")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        for text, cb in [("Next", self.find_next), ("Prev", self.find_prev), ("Replace", self.replace_text), ("Replace All", self.replace_all_text), ("X", self.find_bar.hide)]:
            btn = QPushButton(text)
            btn.clicked.connect(cb)
            find_layout.addWidget(self.find_input if text == "Next" else self.replace_input if text == "Replace" else btn)

        self.editor_container = QWidget()
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self.editor_tabs)
        editor_layout.addWidget(self.find_bar)

        self.output_panel = OutputPanel()
        self.output_panel.error_clicked.connect(self.goto_error_definition)
        
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.addWidget(self.left_tabs)
        self.top_splitter.addWidget(self.editor_container)
        self.top_splitter.setStretchFactor(0, 0)
        self.top_splitter.setStretchFactor(1, 1) 
        self.top_splitter.setSizes([240, 960]) 
        
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.output_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([650, 150]) 
        self.setCentralWidget(self.main_splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.editor_status_label = QLabel("RTL Studio Ready")
        self.status_bar.addWidget(self.editor_status_label)
        
        self.eda_status_label = QLabel(" Detecting EDA Tools... ")
        self.lang_indicator = QLabel(" | Language: Verilog ")
        self.lang_indicator.setStyleSheet("color: #92929A;")
        self.theme_toggle_btn = QLabel(" Theme: Dark " if self.is_dark_theme else " Theme: Light ")
        self.theme_toggle_btn.setStyleSheet("text-decoration: underline;")
        self.theme_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_toggle_btn.mousePressEvent = self.toggle_theme
        self.status_indicator = QLabel(" | ● PINARX ")
        self.status_indicator.setStyleSheet("color: #d85c96; font-weight: bold; font-family: monospace;")
        
        self.status_bar.addPermanentWidget(self.eda_status_label)
        self.status_bar.addPermanentWidget(self.lang_indicator)
        self.status_bar.addPermanentWidget(self.theme_toggle_btn)
        self.status_bar.addPermanentWidget(self.status_indicator)

    def setup_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        new_file_act = QAction("New Verilog File...", self)
        new_file_act.triggered.connect(self.handle_req_new_v)
        file_menu.addAction(new_file_act)
        
        new_tb_act = QAction("New Testbench...", self)
        new_tb_act.triggered.connect(self.handle_req_new_tb)
        file_menu.addAction(new_tb_act)
        
        file_menu.addSeparator()
        
        open_proj_act = QAction("Open Project...", self)
        open_proj_act.setShortcut(QKeySequence("Ctrl+O"))
        open_proj_act.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_proj_act)
        
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self.update_recent_projects_menu()
        
        close_proj_act = QAction("Close Project", self)
        close_proj_act.triggered.connect(self.close_project)
        file_menu.addAction(close_proj_act)
        file_menu.addSeparator()
        
        save_act = QAction("Save", self)
        save_act.setShortcut(QKeySequence("Ctrl+S"))
        save_act.triggered.connect(self.editor_tabs.save_active_file)
        file_menu.addAction(save_act)
        
        save_all_act = QAction("Save All", self)
        save_all_act.triggered.connect(self.editor_tabs.save_all_files)
        file_menu.addAction(save_all_act)
        
        file_menu.addSeparator()
        
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)
        
        edit_menu = menubar.addMenu("Edit")
        
        find_act = QAction("Find...", self)
        find_act.setShortcut(QKeySequence("Ctrl+F"))
        find_act.triggered.connect(self.show_find)
        edit_menu.addAction(find_act)
        
        replace_act = QAction("Replace...", self)
        replace_act.setShortcut(QKeySequence("Ctrl+H"))
        replace_act.triggered.connect(self.show_replace)
        edit_menu.addAction(replace_act)
        
        goto_act = QAction("Go To Line...", self)
        goto_act.setShortcut(QKeySequence("Ctrl+L"))
        goto_act.triggered.connect(self.go_to_line)
        edit_menu.addAction(goto_act)
        
        search_proj_act = QAction("Search Project...", self)
        search_proj_act.setShortcut(QKeySequence("Ctrl+Shift+F"))
        search_proj_act.triggered.connect(self.search_project)
        edit_menu.addAction(search_proj_act)
            
        edit_menu.addSeparator()
        
        prod_theme_act = QAction("Go Productive Theme", self)
        prod_theme_act.triggered.connect(self.activate_productive_theme)
        edit_menu.addAction(prod_theme_act)
        
        # ADDITION: Candy Pop Theme
        candy_theme_act = QAction("Candy Pop Theme", self)
        candy_theme_act.triggered.connect(self.activate_candy_theme)
        edit_menu.addAction(candy_theme_act)
        
        settings_act = QAction("Settings & Tools...", self)
        settings_act.triggered.connect(self.open_settings)
        edit_menu.addAction(settings_act)
        
        proj_menu = menubar.addMenu("Project")
        
        proj_settings_act = QAction("Project Settings...", self)
        proj_settings_act.triggered.connect(self.open_project_settings)
        proj_menu.addAction(proj_settings_act)
        
        refresh_act = QAction("Refresh Analysis", self)
        refresh_act.triggered.connect(self.analyze_project)
        proj_menu.addAction(refresh_act)
        
        validate_act = QAction("Validate Project", self)
        validate_act.triggered.connect(self.validate_project)
        proj_menu.addAction(validate_act)

        self.run_menu = menubar.addMenu("Run")
        
        self.build_act = QAction("Build Project", self)
        self.build_act.setIconText("Build")
        self.build_act.setShortcut(QKeySequence("Ctrl+B"))
        self.build_act.triggered.connect(self.run_build)
        self.run_menu.addAction(self.build_act)
        
        self.sim_act = QAction("Run Simulation", self)
        self.sim_act.setIconText("Run")
        self.sim_act.setShortcut(QKeySequence("F5"))
        self.sim_act.triggered.connect(self.run_simulation)
        self.run_menu.addAction(self.sim_act)
        
        self.stop_act = QAction("Stop Process", self)
        self.stop_act.setIconText("Stop")
        self.stop_act.setShortcut(QKeySequence("Shift+F5"))
        self.stop_act.triggered.connect(self.stop_active_process)
        self.stop_act.setEnabled(False)
        self.run_menu.addAction(self.stop_act)
        
        self.run_menu.addSeparator()
        
        self.gtkwave_act = QAction("Open Waveform", self)
        self.gtkwave_act.setIconText("Waveform")
        self.gtkwave_act.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self.gtkwave_act.triggered.connect(self.open_waveform)
        self.gtkwave_act.setEnabled(False)
        self.run_menu.addAction(self.gtkwave_act)
        
        self.yosys_act = QAction("Synthesis", self)
        self.yosys_act.setIconText("Synthesis")
        self.yosys_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.yosys_act.triggered.connect(self.run_synthesis)
        self.yosys_act.setEnabled(False)
        self.run_menu.addAction(self.yosys_act)
        
        self.schematic_act = QAction("View Schematic", self)
        self.schematic_act.setIconText("Schematic")
        self.schematic_act.setShortcut(QKeySequence("Ctrl+Shift+G"))
        self.schematic_act.triggered.connect(self.open_schematic)
        self.schematic_act.setEnabled(False)
        self.run_menu.addAction(self.schematic_act)

        view_menu = menubar.addMenu("View")
        for item in ["Project Explorer", "Output", "Terminal"]: 
            view_menu.addAction(item)
            
        help_menu = menubar.addMenu("Help")
        
        get_started_act = QAction("Getting Started", self)
        get_started_act.triggered.connect(self.show_getting_started)
        help_menu.addAction(get_started_act)
        
        shortcuts_act = QAction("Keyboard Shortcuts", self)
        shortcuts_act.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_act)
        
        docs_act = QAction("Documentation", self)
        docs_act.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_act)
        
        report_act = QAction("Report an Issue", self)
        report_act.triggered.connect(self.report_issue)
        help_menu.addAction(report_act)
        
        update_act = QAction("Check for Updates", self)
        update_act.triggered.connect(self.check_updates)
        help_menu.addAction(update_act)
        
        help_menu.addSeparator()
        
        github_act = QAction("GitHub Repository", self)
        github_act.triggered.connect(self.open_github)
        help_menu.addAction(github_act)
        
        pinarx_act = QAction("About PINARX", self)
        pinarx_act.triggered.connect(self.show_pinarx)
        help_menu.addAction(pinarx_act)
        
        dev_act = QAction("About the Developer", self)
        dev_act.triggered.connect(self.show_about_developer)
        help_menu.addAction(dev_act)
        
        about_act = QAction("About RTL Studio", self)
        about_act.triggered.connect(self.show_about_app)
        help_menu.addAction(about_act)

    def setup_toolbar(self):
        self.toolbar = QToolBar("EDA Workflow")
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.toolbar.addAction(self.build_act)
        self.toolbar.addAction(self.sim_act)
        self.toolbar.addAction(self.stop_act)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.gtkwave_act)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.yosys_act)
        self.toolbar.addAction(self.schematic_act)

    def update_toolbar_icons(self):
        self.build_act.setIcon(create_eda_icon("build", self.is_dark_theme, self.is_productive_theme, self.is_candy_theme))
        self.sim_act.setIcon(create_eda_icon("run", self.is_dark_theme, self.is_productive_theme, self.is_candy_theme))
        self.stop_act.setIcon(create_eda_icon("stop", self.is_dark_theme, self.is_productive_theme, self.is_candy_theme))
        self.gtkwave_act.setIcon(create_eda_icon("waveform", self.is_dark_theme, self.is_productive_theme, self.is_candy_theme))
        self.yosys_act.setIcon(create_eda_icon("synthesis", self.is_dark_theme, self.is_productive_theme, self.is_candy_theme))
        self.schematic_act.setIcon(create_eda_icon("schematic", self.is_dark_theme, self.is_productive_theme, self.is_candy_theme))

    def update_toolbar_state(self):
        if not self.current_project:
            self.build_act.setEnabled(False)
            self.sim_act.setEnabled(False)
            self.yosys_act.setEnabled(False)
            self.gtkwave_act.setEnabled(False)
            self.schematic_act.setEnabled(False)
            self.stop_act.setEnabled(False)
            return

        is_running = (self.build_process.state() == QProcess.ProcessState.Running or 
                      self.sim_process.state() == QProcess.ProcessState.Running or 
                      self.yosys_process.state() == QProcess.ProcessState.Running)

        self.stop_act.setEnabled(is_running)

        if is_running:
            self.build_act.setEnabled(False)
            self.sim_act.setEnabled(False)
            self.yosys_act.setEnabled(False)
            self.gtkwave_act.setEnabled(False)
            self.schematic_act.setEnabled(False)
        else:
            self.build_act.setEnabled(self.icarus.available)
            self.yosys_act.setEnabled(self.yosys.available)
            
            vvp_file = os.path.join(self.current_project, ".rtlstudio", "build", "simulation.vvp")
            self.sim_act.setEnabled(self.icarus.available and os.path.exists(vvp_file))
            
            self.gtkwave_act.setEnabled(self.gtkwave.available and bool(self.current_vcd) and os.path.exists(str(self.current_vcd)))
            
            schematic_path = os.path.join(self.current_project, ".rtlstudio", "synthesis", "schematic.svg")
            self.schematic_act.setEnabled(self.graphviz.available and os.path.exists(schematic_path))

    def stop_active_process(self):
        if self.build_process.state() == QProcess.ProcessState.Running: 
            self.build_process.kill()
            self.output_panel.log("Build stopped by user.", "WARNING")
        if self.sim_process.state() == QProcess.ProcessState.Running: 
            self.sim_process.kill()
            self.output_panel.log("Simulation stopped by user.", "WARNING")
        if self.yosys_process.state() == QProcess.ProcessState.Running: 
            self.yosys_process.kill()
            self.output_panel.log("Synthesis stopped by user.", "WARNING")
            
        self.update_toolbar_state()
        self.update_status_bar("RTL Studio Ready")

    def analyze_project(self):
        if not self.current_project: return
        
        # 1. Physical Filesystem Truth
        actual_files = []
        for root, _, files in os.walk(self.current_project):
            if '.rtlstudio' in root or '__pycache__' in root: continue
            for f in files:
                if f.endswith(('.v', '.sv', '.vh', '.svh')):
                    actual_files.append(os.path.relpath(os.path.join(root, f), self.current_project).replace('\\', '/'))
        
        # 2. Cleanup Stale JSON Configs safely
        cfg = self.project_config.data
        sources_changed = False
        
        for key in ["design_sources", "testbench_sources"]:
            if key in cfg:
                stale = [f for f in cfg[key] if f not in actual_files]
                for s in stale:
                    self.output_panel.log(f"Removed stale source: {s}", "INFO")
                    sources_changed = True
                cfg[key] = [f for f in cfg[key] if f in actual_files]

        # 3. Code-Aware Parse (No filename assumptions)
        self.project_analyzer.analyze(actual_files)
        
        design_mods = [name for name, data in self.project_analyzer.modules.items() if not data.get("is_tb")]
        tb_mods = [name for name, data in self.project_analyzer.modules.items() if data.get("is_tb")]

        # 4. Map active discovered hierarchy back to config, clearing stale cached modules
        if cfg.get("testbench_module") and cfg.get("testbench_module") not in tb_mods:
            cfg["testbench_module"] = tb_mods[0] if tb_mods else ""
            sources_changed = True
        if cfg.get("top_module") and cfg.get("top_module") not in design_mods:
            cfg["top_module"] = design_mods[0] if design_mods else ""
            sources_changed = True
        if not cfg.get("top_module") and design_mods:
            cfg["top_module"] = design_mods[0]
            sources_changed = True
        if not cfg.get("testbench_module") and tb_mods:
            cfg["testbench_module"] = tb_mods[0]
            sources_changed = True
            
        for f in self.project_analyzer.rtl_files:
            rel_path = f.replace('\\', '/')
            is_tb = False
            for m in self.project_analyzer.modules.values():
                if m["rel_file"] == rel_path and m["is_tb"]:
                    is_tb = True
                    break
            if is_tb:
                if rel_path in cfg.setdefault("design_sources", []):
                    cfg["design_sources"].remove(rel_path)
                    sources_changed = True
                if rel_path not in cfg.setdefault("testbench_sources", []):
                    cfg["testbench_sources"].append(rel_path)
                    sources_changed = True
            else:
                if rel_path in cfg.setdefault("testbench_sources", []):
                    cfg["testbench_sources"].remove(rel_path)
                    sources_changed = True
                if rel_path not in cfg.setdefault("design_sources", []):
                    cfg["design_sources"].append(rel_path)
                    sources_changed = True

        if sources_changed:
            self.project_config.save()
            
        self.analysis_panel.update_analysis(self.project_analyzer, self.project_config)

    def validate_project(self, quiet=False):
        if not self.ensure_project_open(): return False
        if not quiet: self.output_panel.log("Project validation started.", "INFO")
        
        self.analyze_project()
        cfg = self.project_config.data
        
        if not quiet:
            for f in cfg.get("design_sources", []) + cfg.get("testbench_sources", []):
                self.output_panel.log(f"Found Verilog source: {f}", "INFO")
                
            if cfg.get("top_module"):
                self.output_panel.log(f"Detected design module: {cfg.get('top_module')}", "INFO")
            if cfg.get("testbench_module"):
                self.output_panel.log(f"Detected testbench: {cfg.get('testbench_module')}", "INFO")
                
            self.output_panel.log("Project validation completed.", "SUCCESS")
        return True

    # --- FILE MANAGER AND CONTEXT MENUS ---
    def handle_req_new_v(self):
        if not self.ensure_project_open(): return
        name, ok = QInputDialog.getText(self, "New Verilog File", "Enter file name:")
        if not ok or not name.strip(): return
        
        name = name.strip()
        if not name.endswith('.v'): name += '.v'
        
        full_path = os.path.join(self.current_project, name)
        if os.path.exists(full_path):
            QMessageBox.warning(self, "Error", "File already exists.")
            return
            
        mod_name = name[:-2]
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', mod_name):
            mod_name = "new_module"
            
        template = f"module {mod_name} (\n);\n\nendmodule\n"
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(template)
        except Exception as e:
            self.output_panel.log(f"ERROR creating file: {e}", "ERROR")
            return
            
        cfg = self.project_config.data
        if name not in cfg.setdefault("design_sources", []):
            cfg["design_sources"].append(name)
            self.project_config.save()
            
        self.project_explorer.load_project(self.current_project)
        self.open_file_in_editor(full_path)
        self.analyze_project()

    def handle_req_new_tb(self):
        if not self.ensure_project_open(): return
        name, ok = QInputDialog.getText(self, "New Testbench", "Enter testbench file name:")
        if not ok or not name.strip(): return
        
        name = name.strip()
        if not name.endswith('.v'):
            if not name.endswith('_tb'): name += '_tb'
            name += '.v'
            
        full_path = os.path.join(self.current_project, name)
        if os.path.exists(full_path):
            QMessageBox.warning(self, "Error", "File already exists.")
            return
            
        mod_name = name[:-2]
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', mod_name):
            mod_name = "testbench"
            
        template = (f"`timescale 1ns/1ps\n\n"
                    f"module {mod_name};\n\n"
                    f"    initial begin\n"
                    f"        $dumpfile(\"wave.vcd\");\n"
                    f"        $dumpvars(0, {mod_name});\n\n"
                    f"        #100;\n"
                    f"        $finish;\n"
                    f"    end\n\n"
                    f"endmodule\n")
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(template)
        except Exception as e:
            self.output_panel.log(f"ERROR creating testbench: {e}", "ERROR")
            return
            
        cfg = self.project_config.data
        if name not in cfg.setdefault("testbench_sources", []):
            cfg["testbench_sources"].append(name)
            self.project_config.save()
            
        self.project_explorer.load_project(self.current_project)
        self.open_file_in_editor(full_path)
        self.analyze_project()

    def handle_req_rename(self, filepath):
        if self.editor_tabs.is_modified(filepath):
            ans = QMessageBox.question(self, "Unsaved Changes", 
                "This file has unsaved changes. Save before renaming?", 
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
            if ans == QMessageBox.StandardButton.Save:
                self.open_file_in_editor(filepath)
                self.editor_tabs.save_active_file()
            else:
                return
        
        old_name = os.path.basename(filepath)
        new_name, ok = QInputDialog.getText(self, "Rename File", "New name:", QLineEdit.EchoMode.Normal, old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name: return
        
        new_name = new_name.strip()
        if old_name.endswith('.v') and not new_name.endswith('.v'):
            new_name += '.v'
            
        new_path = os.path.join(os.path.dirname(filepath), new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Error", "A file with that name already exists.")
            return
            
        try:
            os.rename(filepath, new_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Rename failed: {e}")
            return
            
        self.editor_tabs.rename_file(filepath, new_path)
        
        cfg = self.project_config.data
        def update_list(src_list):
            for i in range(len(src_list)):
                if os.path.normpath(os.path.join(self.current_project, src_list[i])) == os.path.normpath(filepath):
                    src_list[i] = os.path.relpath(new_path, self.current_project).replace('\\', '/')
        
        update_list(cfg.setdefault("design_sources", []))
        update_list(cfg.setdefault("testbench_sources", []))
        self.project_config.save()
        
        self.project_explorer.load_project(self.current_project)
        self.analyze_project()

    def handle_req_delete(self, filepath):
        if self.editor_tabs.is_modified(filepath):
            ans = QMessageBox.question(self, "Unsaved Changes", 
                "This file has unsaved changes. Are you sure you want to delete it?", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if ans != QMessageBox.StandardButton.Yes:
                return
                
        # EXACT FIX: Changed .Delete to .Yes to match valid PySide6 UI enums
        ans = QMessageBox.question(self, "Confirm Delete", 
            f"Delete {os.path.basename(filepath)}?\nThis cannot be undone.", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            
        if ans == QMessageBox.StandardButton.Yes:
            try:
                os.remove(filepath)
                self.output_panel.log(f"Deleted file: {os.path.basename(filepath)}", "SUCCESS")
            except Exception as e:
                self.output_panel.log(f"Delete failed: {e}", "ERROR")
                return
                
            self.editor_tabs.close_file(filepath)
            self.analyze_project()
            self.project_explorer.load_project(self.current_project)
            self.output_panel.log("Project Explorer refreshed.", "INFO")

    def handle_req_refresh(self):
        if self.current_project:
            self.project_explorer.load_project(self.current_project)
            self.analyze_project()
            self.output_panel.log("Project Explorer refreshed.", "INFO")

    def handle_req_reveal(self, filepath):
        folder = os.path.dirname(filepath) if os.path.isfile(filepath) else filepath
        url = QUrl.fromLocalFile(folder)
        if not QDesktopServices.openUrl(url):
            self.output_panel.log(f"Your operating system ({sys.platform}) does not support revealing this file automatically.", "WARNING")

    def add_recent_project(self, path):
        recents = self.settings.value("recent_projects", [])
        if isinstance(recents, str): 
            recents = [recents]
        elif not isinstance(recents, list): 
            recents = list(recents) if recents else []
            
        if path in recents: 
            recents.remove(path)
            
        recents.insert(0, path)
        self.settings.setValue("recent_projects", recents[:5])
        self.update_recent_projects_menu()

    def update_recent_projects_menu(self):
        self.recent_menu.clear()
        recents = self.settings.value("recent_projects", [])
        if isinstance(recents, str): recents = [recents]
        elif not isinstance(recents, list): recents = list(recents) if recents else []
        
        recents = [p for p in recents if os.path.exists(p)]
            
        if not recents: 
            self.recent_menu.addAction("No recent projects").setEnabled(False)
        else:
            for path in recents:
                act = QAction(path, self)
                # STEP 1 FIX: Secure late-binding PySide lambda
                act.triggered.connect(lambda checked=False, p=path: self.open_project(p))
                self.recent_menu.addAction(act)

    # --- YOSYS SYNTHESIS, SCHEMATIC & PPA ---
    def run_synthesis(self, *args, **kwargs):
        try:
            if not self.ensure_project_open(): return
            if self.yosys_process.state() == QProcess.ProcessState.Running: return
            if not self.yosys.available:
                self.output_panel.log("Yosys is missing. Synthesis cannot proceed.", "ERROR")
                return
                
            self.analyze_project()
            cfg = self.project_config.data
            
            top_mod = cfg.get("top_module")
            if not top_mod:
                self.output_panel.log("No Design Top module configured.", "ERROR")
                return
                
            # STRICT GUARD: Ensure ONLY existing files go to Yosys
            valid_srcs = []
            for src in cfg.get("design_sources", []):
                abs_path = os.path.join(self.current_project, src)
                if os.path.exists(abs_path):
                    valid_srcs.append(abs_path)
            
            if not valid_srcs:
                self.output_panel.log("No valid hardware design sources configured for synthesis.", "ERROR")
                return

            self.editor_tabs.save_all_files()
            
            synth_dir = os.path.join(self.current_project, ".rtlstudio", "synthesis")
            logs_dir = os.path.join(self.current_project, ".rtlstudio", "logs")
            os.makedirs(synth_dir, exist_ok=True); os.makedirs(logs_dir, exist_ok=True)
            
            schematic_path = os.path.join(synth_dir, "schematic.svg")
            if os.path.exists(schematic_path): os.remove(schematic_path)

            self.output_panel.log("--- Yosys Synthesis Started ---", "INFO")
            self.output_panel.log(f"Synthesis target: {top_mod}", "INFO")

            script_path = os.path.join(synth_dir, "synth.ys")
            output_v = os.path.join(synth_dir, "synthesized.v")
            
            with open(script_path, "w", encoding="utf-8") as f:
                for src in valid_srcs: f.write(f'read_verilog "{src.replace(os.sep, "/")}"\n')
                f.write(f'hierarchy -check -top {top_mod}\n')
                f.write(f'synth -top {top_mod}\n')
                f.write(f'write_verilog "{output_v.replace(os.sep, "/")}"\n')
                if self.graphviz.available: f.write(f'show -format svg -prefix .rtlstudio/synthesis/schematic {top_mod}\n')
                f.write('stat\n')

            self.yosys_output_buffer = ""
            self.yosys_process.setWorkingDirectory(self.current_project)
            self.yosys_process.start(self.yosys.path, ["-s", script_path])
            
            self.update_toolbar_state()
            self.update_status_bar("Running Yosys synthesis...")
            
        except Exception as e:
            self.output_panel.log(f"INTERNAL ERROR during Synthesis: {str(e)}", "ERROR")
            self.update_toolbar_state()

    def handle_yosys_stdout(self): 
        raw = self.yosys_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', raw)
        self.yosys_output_buffer += clean
        
    def handle_yosys_stderr(self): 
        raw = self.yosys_process.readAllStandardError().data().decode('utf-8', errors='replace')
        clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', raw)
        self.yosys_output_buffer += clean
        
    def handle_yosys_finished(self, exit_code, exit_status):
        self.update_status_bar("RTL Studio Ready")
        log_path = os.path.join(self.current_project, ".rtlstudio", "logs", "synthesis.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f: f.write(self.yosys_output_buffer)
        except Exception: pass

        if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit:
            self.output_panel.log("Synthesis completed successfully.", "SUCCESS")
            for line in self.yosys_output_buffer.split('\n'):
                low = line.strip().lower()
                if low.startswith("number of") or "$_" in line or "\\" in line: 
                    self.output_panel.append_raw("  " + line.strip() + "\n")
                    
            self.project_explorer.load_project(self.current_project)
            self.analysis_panel.update_ppa(self.yosys_output_buffer, self.project_analyzer, self.project_config)
            self.left_tabs.setCurrentWidget(self.analysis_panel)
            self.analysis_panel.tabs.setCurrentIndex(1)
        else:
            self.output_panel.log(f"Synthesis failed with exit code {exit_code}.", "ERROR")
            for line in self.yosys_output_buffer.split('\n'):
                if "ERROR:" in line or "syntax error" in line.lower(): 
                    self.output_panel.append_raw("  " + line.strip() + "\n")

        self.check_for_synthesis_artifacts()
        self.update_toolbar_state()

    def check_for_synthesis_artifacts(self):
        if not self.current_project: return
        schematic_path = os.path.join(self.current_project, ".rtlstudio", "synthesis", "schematic.svg")
        if os.path.exists(schematic_path):
            self.output_panel.log("Schematic generated successfully.", "SUCCESS")

    def open_schematic(self):
        schematic_path = os.path.join(self.current_project, ".rtlstudio", "synthesis", "schematic.svg")
        if not os.path.exists(schematic_path):
            self.output_panel.log("Schematic not found. Run synthesis first.", "ERROR"); return
        try:
            self.schematic_viewer_dialog = SchematicViewer(schematic_path, self)
            self.schematic_viewer_dialog.show()
            self.output_panel.log("Opened schematic viewer.", "INFO")
        except Exception as e:
            self.output_panel.log(f"ERROR launching Schematic Viewer: {str(e)}", "ERROR")

    # --- ICARUS BUILD & SIMULATION ---
    def setup_build_workspace(self):
        build_dir = os.path.join(self.current_project, ".rtlstudio", "build")
        logs_dir = os.path.join(self.current_project, ".rtlstudio", "logs")
        os.makedirs(build_dir, exist_ok=True); os.makedirs(logs_dir, exist_ok=True)
        return build_dir, logs_dir

    def run_build(self, *args, **kwargs):
        try:
            if not self.ensure_project_open(): return
            if self.build_process.state() == QProcess.ProcessState.Running: return
            if not self.icarus.available: 
                self.output_panel.log("Icarus Verilog is missing.", "ERROR"); return
                
            self.analyze_project()
            cfg = self.project_config.data
            
            # STRICT GUARD: Ensure ONLY existing files go to Icarus
            valid_srcs = []
            for src in (cfg.get("design_sources") or []) + (cfg.get("testbench_sources") or []):
                abs_path = os.path.join(self.current_project, src)
                if os.path.exists(abs_path):
                    valid_srcs.append(abs_path)
                else:
                    self.output_panel.log(f"Skipping missing source: {src}", "WARNING")
            
            if not valid_srcs: 
                self.output_panel.log("No valid RTL source files found for build.", "ERROR"); return
                
            self.editor_tabs.save_all_files()
            build_dir, _ = self.setup_build_workspace()
            output_file = os.path.join(build_dir, "simulation.vvp")
            if os.path.exists(output_file):
                try: os.remove(output_file)
                except Exception: pass
                    
            self.output_panel.log("--- Icarus Verilog Build Started ---", "INFO")
            args_cmd = ["-g2012", "-o", output_file] 
            top_mod = cfg.get("testbench_module") or cfg.get("top_module")
            if top_mod: args_cmd.extend(["-s", top_mod])
            args_cmd.extend(valid_srcs)
                
            self.build_process.setWorkingDirectory(self.current_project)
            self.build_process.start(self.icarus.iverilog_path, args_cmd)
            self.update_toolbar_state()
            self.update_status_bar("Building project...")
            
        except Exception as e:
            self.output_panel.log(f"INTERNAL ERROR during Build: {str(e)}", "ERROR")
            self.update_toolbar_state()

    def handle_build_stdout(self): self.output_panel.append_raw(self.build_process.readAllStandardOutput().data().decode('utf-8'))
    def handle_build_stderr(self): self.output_panel.append_raw(self.build_process.readAllStandardError().data().decode('utf-8'))
    def handle_build_finished(self, exit_code, exit_status):
        self.update_status_bar("RTL Studio Ready")
        if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit: 
            self.output_panel.log("Build successful.", "SUCCESS")
        else: 
            self.output_panel.log(f"Build failed with exit code {exit_code}.", "ERROR")
        self.update_toolbar_state()

    def run_simulation(self, *args, **kwargs):
        try:
            if not self.ensure_project_open() or not self.icarus.available: return
            if self.sim_process.state() == QProcess.ProcessState.Running: return
            vvp_file = os.path.join(self.current_project, ".rtlstudio", "build", "simulation.vvp")
            if not os.path.exists(vvp_file): 
                self.output_panel.log("simulation.vvp not found. Please build the project first.", "ERROR"); return
                
            self.output_panel.log("--- Simulation Started ---", "INFO")
            self.sim_process.setWorkingDirectory(self.current_project)
            self.sim_process.start(self.icarus.vvp_path, [vvp_file])
            self.update_toolbar_state()
            self.update_status_bar("Running simulation...")
            
        except Exception as e:
            self.output_panel.log(f"INTERNAL ERROR during Simulation: {str(e)}", "ERROR")
            self.update_toolbar_state()

    def handle_sim_stdout(self): self.output_panel.append_raw(self.sim_process.readAllStandardOutput().data().decode('utf-8'))
    def handle_sim_stderr(self): self.output_panel.append_raw(self.sim_process.readAllStandardError().data().decode('utf-8'))
    def handle_sim_finished(self, exit_code, exit_status):
        self.update_status_bar("RTL Studio Ready")
        if exit_status == QProcess.ExitStatus.CrashExit: 
            self.output_panel.log("Simulation stopped by user or crashed.", "WARNING")
        else: 
            self.output_panel.log(f"Simulation completed. Exit code: {exit_code}", "SUCCESS")
            
        self.check_for_vcd_artifacts(from_sim=True)
        self.update_toolbar_state()

    # --- GTKWAVE & ARTIFACT DETECTION ---
    def check_for_vcd_artifacts(self, from_sim=False):
        if not self.current_project: return
        newest_vcd = None
        newest_time = 0
        
        for root, _, files in os.walk(self.current_project):
            for f in files:
                if f.endswith(".vcd"):
                    vcd_path = os.path.join(root, f)
                    mtime = os.path.getmtime(vcd_path)
                    if mtime > newest_time:
                        newest_time = mtime
                        newest_vcd = vcd_path

        if newest_vcd:
            self.current_vcd = newest_vcd
            if from_sim:
                self.output_panel.log(f"Waveform generated: {self.current_vcd}", "INFO")
                self.output_panel.log("Waveform viewer ready.", "INFO")
            else:
                self.output_panel.log(f"Waveform detected: {os.path.basename(self.current_vcd)}", "INFO")
            self.project_explorer.load_project(self.current_project)
        else:
            self.current_vcd = None
            if from_sim:
                self.output_panel.log("No waveform (.vcd) file found after simulation.", "WARNING")
        self.update_toolbar_state()

    def open_waveform(self):
        if not self.gtkwave.available: 
            self.output_panel.log("GTKWave was not found. Please ensure GTKWave is installed and available in PATH.", "ERROR")
            return
        if not self.current_vcd or not os.path.exists(self.current_vcd): 
            self.output_panel.log("No waveform available.", "ERROR")
            return
        if self.gtkwave_process.state() == QProcess.ProcessState.Running: 
            return
        
        self.output_panel.log("Launching GTKWave...", "INFO")
        self.output_panel.log(f"Waveform: {self.current_vcd}", "INFO")
        self.gtkwave_process.setWorkingDirectory(self.current_project)
        self.gtkwave_process.start(self.gtkwave.path, [self.current_vcd])

    def open_file_in_editor(self, filepath):
        if filepath.endswith(".vcd"): self.current_vcd = filepath; self.open_waveform(); return
        if filepath.endswith("schematic.svg"): self.open_schematic(); return
        if filepath.endswith(".vvp"):
            self.output_panel.log("Cannot open binary compilation artifact (.vvp) in text editor.", "WARNING")
            return
        self.editor_tabs.open_file(filepath)

    # --- THEME MANAGEMENT ---
    def toggle_theme(self, event=None):
        self.is_productive_theme = False
        self.is_candy_theme = False
        self.is_dark_theme = not self.is_dark_theme
        self.settings.setValue("is_dark_theme", self.is_dark_theme)
        self.theme_toggle_btn.setText(" Theme: Dark " if self.is_dark_theme else " Theme: Light ")
        self.status_indicator.setStyleSheet("color: #d85c96; font-weight: bold; font-family: monospace;")
        self.status_indicator.setText(" | ● PINARX ")
        
        self.apply_theme()
        if hasattr(self.editor_tabs, 'set_theme'):
            self.editor_tabs.set_theme(self.is_dark_theme, is_productive=False, is_candy=False)
        if hasattr(self.output_panel, 'set_theme'):
            self.output_panel.set_theme(self.is_dark_theme, is_productive=False, is_candy=False)

    def activate_productive_theme(self):
        self.is_productive_theme = True
        self.is_candy_theme = False
        self.is_dark_theme = True
        self.theme_toggle_btn.setText(" Theme: Productive ")
        self.status_indicator.setStyleSheet("color: #7C5CFF; font-weight: bold; font-family: monospace;")
        self.status_indicator.setText(" | ● RTL READY ")
        
        self.apply_theme()
        
        if hasattr(self.editor_tabs, 'set_theme'):
            self.editor_tabs.set_theme(is_dark=True, is_productive=True, is_candy=False)
        if hasattr(self.output_panel, 'set_theme'):
            self.output_panel.set_theme(is_dark=True, is_productive=True, is_candy=False)
            
        self.output_panel.log("BUILD. DEBUG. LEARN. REPEAT.", "INFO")

    def activate_candy_theme(self):
        self.is_candy_theme = True
        self.is_productive_theme = False
        self.is_dark_theme = False
        self.theme_toggle_btn.setText(" Theme: Candy Pop ")
        self.status_indicator.setStyleSheet("color: #FF6FA5; font-weight: bold; font-family: monospace;")
        self.status_indicator.setText(" | ● RTL READY ")
        
        self.apply_theme()
        
        if hasattr(self.editor_tabs, 'set_theme'):
            self.editor_tabs.set_theme(is_dark=False, is_productive=False, is_candy=True)
        if hasattr(self.output_panel, 'set_theme'):
            self.output_panel.set_theme(is_dark=False, is_productive=False, is_candy=True)

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.is_dark_theme, getattr(self, 'is_productive_theme', False), getattr(self, 'is_candy_theme', False)))
        self.update_toolbar_icons()

    # --- UI LOGIC ---
    def open_project_settings(self):
        if not self.ensure_project_open(): return
        dialog = ProjectSettingsDialog(self.project_config, self.project_analyzer, self)
        if dialog.exec(): 
            self.analyze_project()
            self.output_panel.log("Project configuration updated.", "SUCCESS")

    def goto_module_definition(self, filepath, line): self.goto_error_definition(filepath, line)
        
    def goto_error_definition(self, filepath, line):
        abs_path = filepath
        if not os.path.isabs(filepath): abs_path = os.path.join(self.current_project, filepath)
        if os.path.exists(abs_path):
            self.open_file_in_editor(abs_path)
            editor = self.editor_tabs.currentWidget()
            if editor:
                cursor = QTextCursor(editor.document().findBlockByNumber(line - 1))
                editor.setTextCursor(cursor)
                editor.centerCursor()
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                editor.setTextCursor(cursor)

    def on_file_saved(self, path): 
        self.output_panel.log(f"Saved: {os.path.basename(path)}", "INFO")
        if path.endswith(('.v', '.sv', '.vh', '.svh')): 
            self.analyze_project()
            
    def update_status_bar(self, msg): 
        self.editor_status_label.setText(msg)
        
    def show_find(self): 
        self.find_bar.show(); self.replace_input.hide(); self.find_input.setFocus()
        
    def show_replace(self): 
        self.find_bar.show(); self.replace_input.show(); self.find_input.setFocus()
        
    def find_next(self): 
        e = self.editor_tabs.currentWidget()
        if e and not e.find(self.find_input.text()):
            c = e.textCursor(); c.movePosition(QTextCursor.Start); e.setTextCursor(c); e.find(self.find_input.text())
            
    def find_prev(self): 
        e = self.editor_tabs.currentWidget()
        if e and not e.find(self.find_input.text(), QTextDocument.FindBackward):
            c = e.textCursor(); c.movePosition(QTextCursor.End); e.setTextCursor(c); e.find(self.find_input.text(), QTextDocument.FindBackward)
            
    def replace_text(self): 
        e = self.editor_tabs.currentWidget()
        if e:
            c = e.textCursor()
            if c.hasSelection() and c.selectedText() == self.find_input.text(): 
                c.insertText(self.replace_input.text())
            self.find_next()
        
    def replace_all_text(self): 
        e = self.editor_tabs.currentWidget()
        if e:
            c = e.textCursor(); count = 0
            c.beginEditBlock(); c.movePosition(QTextCursor.Start); e.setTextCursor(c)
            while e.find(self.find_input.text()):
                e.textCursor().insertText(self.replace_input.text()); count += 1
            c.endEditBlock()
            self.output_panel.log(f"Replaced {count} occurrences.", "INFO")
        
    def go_to_line(self): 
        e = self.editor_tabs.currentWidget()
        if e:
            line, ok = QInputDialog.getInt(self, "Go To Line", "Line number:", 1, 1, e.blockCount())
            if ok:
                e.setTextCursor(QTextCursor(e.document().findBlockByNumber(line - 1)))
                e.centerCursor()
                
    def open_settings(self): 
        dialog = SettingsDialog(self)
        dialog.exec()  # Wait for dialog to close
        # EXACT FIX: Force reload unconditionally so the V2.0 "Save" button works
        self.editor_tabs.reload_settings()
    
    def open_project_dialog(self): 
        dir_path = QFileDialog.getExistingDirectory(self, "Open RTL Project")
        if dir_path: self.open_project(dir_path)
    
    def open_project(self, path):
        if not self.close_project(): return
        if not os.path.exists(path): return
        
        self.output_panel.log(f"Opening project: {path}", "INFO")
        self.current_project = path
        self.project_config = ProjectConfig(path)
        self.project_analyzer = ProjectAnalyzer(path)
        
        # RESTORED: Analyze physical disk FIRST, then load UI tree
        self.analyze_project()
        
        self.project_explorer.load_project(path)
        self.add_recent_project(path)
        
        self.output_panel.log(f"Project opened: {os.path.basename(path)}", "INFO")
        self.output_panel.log("Project Explorer refreshed.", "INFO")
        
        # V2.0 BASELINE SAFEGUARD: Only call these advanced artifact checkers if they exist in your baseline
        if hasattr(self, 'load_previous_synthesis_log'):
            self.load_previous_synthesis_log()
        if hasattr(self, 'check_for_vcd_artifacts'):
            self.check_for_vcd_artifacts()
        if hasattr(self, 'check_for_synthesis_artifacts'):
            self.check_for_synthesis_artifacts()
        
        if hasattr(self, 'update_toolbar_state'):
            self.update_toolbar_state()
        if hasattr(self, 'update_status_bar'):
            self.update_status_bar(f"Project loaded: {os.path.basename(path)}")
    def close_project(self):
        if not self.editor_tabs.close_all_tabs(): return False
        
        self.current_project = None
        self.project_config = None
        self.project_analyzer = None
        self.current_vcd = None
        self.project_explorer.clear()
        self.project_explorer.setHeaderLabels(["PROJECT"])
        self.analysis_panel.update_analysis(ProjectAnalyzer(""), None)
        self.analysis_panel.clear_ppa()
        
        self.update_toolbar_state()
        self.update_status_bar("RTL Studio Ready")
        return True
        
    def search_project(self):
        if not self.current_project: return
        dialog = SearchDialog(self.current_project, self)
        if dialog.exec() and dialog.selected_file:
            self.goto_module_definition(dialog.selected_file, dialog.selected_line + 1)
        
    def ensure_project_open(self): 
        if self.current_project: return True
        else: QMessageBox.warning(self, "Error", "No project is currently open."); return False
    
    def show_getting_started(self):
        msg = ("<h3>RTL Studio Workflow</h3>"
               "<ol>"
               "<li><b>Create/Open</b> a project</li>"
               "<li><b>Write Verilog</b> in the editor</li>"
               "<li><b>Build</b> the design to check for syntax errors</li>"
               "<li><b>Run simulation</b> to generate waveforms</li>"
               "<li><b>Open Waveform</b> via GTKWave</li>"
               "<li><b>Run Synthesis</b> via Yosys</li>"
               "<li><b>Open Schematic</b> to view the generated circuit</li>"
               "<li>View <b>Design & PPA</b> for synthesized cell statistics</li>"
               "</ol>")
        QMessageBox.information(self, "Getting Started", msg)

    def show_shortcuts(self):
        msg = ("<h3>Keyboard Shortcuts</h3>"
               "<ul>"
               "<li><b>Ctrl+S</b> : Save active file</li>"
               "<li><b>Ctrl+B</b> : Build Project</li>"
               "<li><b>F5</b> : Run Simulation</li>"
               "<li><b>Shift+F5</b> : Stop Process</li>"
               "<li><b>Ctrl+Shift+W</b> : Open Waveform</li>"
               "<li><b>Ctrl+Shift+S</b> : Synthesis</li>"
               "<li><b>Ctrl+Shift+G</b> : View Schematic</li>"
               "<li><b>Ctrl+F</b> : Find</li>"
               "<li><b>Ctrl+H</b> : Replace</li>"
               "<li><b>Ctrl+L</b> : Go to Line</li>"
               "<li><b>Ctrl+Shift+F</b> : Search Project</li>"
               "</ul>")
        QMessageBox.information(self, "Keyboard Shortcuts", msg)

    def open_documentation(self):
        QMessageBox.information(self, "Documentation", "Documentation is coming in a future release.")

    def report_issue(self):
        QDesktopServices.openUrl(QUrl("https://github.com/sujan-angadi/PINARX-RTL_Studio/issues"))

    def check_updates(self):
        QMessageBox.information(self, "Updates", "You are running the latest version of RTL Studio.")

    def open_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/sujan-angadi/PINARX-RTL_Studio"))

    def show_pinarx(self):
        QMessageBox.about(self, "About PINARX", "<h3>PINARX</h3><p>Circuits for a Brighter Tomorrow</p>")

    def show_about_developer(self):
        msg = ("<h3>About the Developer</h3>"
               "<p><b>Sujan S A</b><br>"
               "Creator & Developer<br>"
               "RTL Studio</p>"
               "<p>Electronics Engineering Student</p>"
               "<p><b>Interests:</b><br>"
               "• VLSI & RTL Design<br>"
               "• Computer Architecture<br>"
               "• Embedded Systems<br>"
               "• Digital Design</p>"
               "<p><a href='https://github.com/sujan-angadi'>GitHub Profile</a></p>")
        box = QMessageBox(self)
        box.setWindowTitle("About the Developer")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(msg)
        box.exec()

    def show_about_app(self):
        msg = ("<h3>RTL Studio</h3>"
               "<p><b>By PINARX</b></p>"
               "<p>A modern RTL development environment for designing,<br>"
               "simulating, synthesizing and visualizing Verilog designs.</p>"
               "<p><b>Current Version: 1.0</b></p>"
               "<p><b>Technology:</b><br>"
               "Python<br>PySide6<br>Icarus Verilog<br>GTKWave<br>Yosys<br>Graphviz</p>")
        QMessageBox.about(self, "About RTL Studio", msg)