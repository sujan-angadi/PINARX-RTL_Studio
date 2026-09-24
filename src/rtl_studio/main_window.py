"""
Main Window
Responsibility: Central IDE orchestration, RTL Analysis, Icarus, GTKWave, Yosys, and Schematic Viewer.
"""
import os
import shutil
import re
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
                               QLabel, QStatusBar, QApplication, QFileDialog, 
                               QMessageBox, QInputDialog, QLineEdit, QPushButton, QTabWidget, QToolBar)
from PySide6.QtCore import Qt, QSettings, QProcess
from PySide6.QtGui import QAction, QKeySequence, QTextCursor, QTextDocument

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
        self.setWindowTitle("PINARX RTL Studio")
        self.resize(1200, 800)
        self.settings = QSettings("PINARX", "RTL_Studio")
        
        self.is_dark_theme = self.settings.value("is_dark_theme", False, type=bool)
        
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
        self.gtkwave_process.finished.connect(lambda: self.output_panel.log("✅ GTKWave closed."))
        
        self.yosys_process = QProcess(self)
        self.yosys_process.readyReadStandardOutput.connect(self.handle_yosys_stdout)
        self.yosys_process.readyReadStandardError.connect(self.handle_yosys_stderr)
        self.yosys_process.finished.connect(self.handle_yosys_finished)
        self.yosys_output_buffer = ""
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.apply_theme()
        
        self.output_panel.log("✅ Application started successfully.")
        self.check_eda_tools()
        self.update_toolbar_state()

    def check_eda_tools(self):
        status_text = ""
        if self.icarus.available:
            status_text += f" Icarus: v{self.icarus.version} "
        else:
            status_text += " Icarus: Not Found "

        if self.gtkwave.available:
            status_text += f"| GTKWave: v{self.gtkwave.version} "
        else:
            status_text += "| GTKWave: Not Found "
            
        if self.yosys.available:
            status_text += f"| Yosys: v{self.yosys.version} "
        else:
            status_text += "| Yosys: Not Found "
            
        if self.graphviz.available:
            status_text += f"| Graphviz: v{self.graphviz.version} "
        else:
            status_text += "| Graphviz: Not Found "
            self.output_panel.log("⚠️ WARNING: Graphviz (dot) is missing. Schematic generation will be skipped.")

        self.eda_status_label.setText(status_text)
        if not self.icarus.available or not self.gtkwave.available or not self.yosys.available:
            self.eda_status_label.setStyleSheet("color: #F28B9B; font-weight: bold;")

    def setup_ui(self):
        self.left_tabs = QTabWidget()
        self.project_explorer = ProjectExplorer()
        self.project_explorer.file_double_clicked.connect(self.open_file_in_editor)
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
        
        new_file_act = QAction("New File...", self)
        new_file_act.triggered.connect(self.new_file)
        file_menu.addAction(new_file_act)
        
        new_folder_act = QAction("New Folder...", self)
        new_folder_act.triggered.connect(self.new_folder)
        file_menu.addAction(new_folder_act)
        
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
        for txt, shortcut, cb in [("Find...", "Ctrl+F", self.show_find), ("Replace...", "Ctrl+H", self.show_replace), ("Go To Line...", "Ctrl+G", self.go_to_line), ("Search Project...", "Ctrl+Shift+F", self.search_project)]:
            act = QAction(txt, self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(cb)
            edit_menu.addAction(act)
            
        edit_menu.addSeparator()
        settings_act = QAction("Editor Settings...", self)
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
        self.build_act.triggered.connect(self.run_build)
        self.run_menu.addAction(self.build_act)
        
        self.sim_act = QAction("Run Simulation", self)
        self.sim_act.setIconText("Run")
        self.sim_act.triggered.connect(self.run_simulation)
        self.run_menu.addAction(self.sim_act)
        
        self.stop_act = QAction("Stop Process", self)
        self.stop_act.setIconText("Stop")
        self.stop_act.triggered.connect(self.stop_active_process)
        self.run_menu.addAction(self.stop_act)
        
        self.run_menu.addSeparator()
        
        self.gtkwave_act = QAction("Open Waveform", self)
        self.gtkwave_act.setIconText("Waveform")
        self.gtkwave_act.triggered.connect(self.open_waveform)
        self.run_menu.addAction(self.gtkwave_act)
        
        self.yosys_act = QAction("Synthesis", self)
        self.yosys_act.setIconText("Synthesis")
        self.yosys_act.triggered.connect(self.run_synthesis)
        self.run_menu.addAction(self.yosys_act)
        
        self.schematic_act = QAction("View Schematic", self)
        self.schematic_act.setIconText("Schematic")
        self.schematic_act.triggered.connect(self.open_schematic)
        self.run_menu.addAction(self.schematic_act)

        view_menu = menubar.addMenu("View")
        for item in ["Project Explorer", "Output", "Terminal"]: 
            view_menu.addAction(item)
            
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About RTL Studio")

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
        self.build_act.setIcon(create_eda_icon("build", self.is_dark_theme))
        self.sim_act.setIcon(create_eda_icon("run", self.is_dark_theme))
        self.stop_act.setIcon(create_eda_icon("stop", self.is_dark_theme))
        self.gtkwave_act.setIcon(create_eda_icon("waveform", self.is_dark_theme))
        self.yosys_act.setIcon(create_eda_icon("synthesis", self.is_dark_theme))
        self.schematic_act.setIcon(create_eda_icon("schematic", self.is_dark_theme))

    # --- PHASE 11: UNIFIED TOOLBAR & STATE MANAGEMENT ---
    def update_toolbar_state(self):
        """Intelligently configures all EDA actions based on disk artifacts and running processes."""
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
            
            vcd_files = [f for f in os.listdir(self.current_project) if f.endswith(".vcd")]
            self.gtkwave_act.setEnabled(self.gtkwave.available and len(vcd_files) > 0)
            
            schematic_path = os.path.join(self.current_project, ".rtlstudio", "synthesis", "schematic.svg")
            self.schematic_act.setEnabled(self.graphviz.available and os.path.exists(schematic_path))

    def stop_active_process(self):
        if self.build_process.state() == QProcess.ProcessState.Running: 
            self.build_process.kill()
            self.output_panel.log("⚠️ Build stopped by user.")
        if self.sim_process.state() == QProcess.ProcessState.Running: 
            self.sim_process.kill()
            self.output_panel.log("⚠️ Simulation stopped by user.")
        if self.yosys_process.state() == QProcess.ProcessState.Running: 
            self.yosys_process.kill()
            self.output_panel.log("⚠️ Synthesis stopped by user.")
            
        self.update_toolbar_state()
        self.update_status_bar("RTL Studio Ready")

    # --- RTL PROJECT ANALYSIS ---
    def analyze_project(self):
        if not self.current_project: 
            return
            
        self.project_analyzer.analyze()
        
        cfg = self.project_config.data
        sources_changed = False
        
        if cfg.get("design_sources"):
            for src in list(cfg["design_sources"]):
                abs_path = os.path.normpath(os.path.join(self.current_project, src))
                is_tb = False
                for m in self.project_analyzer.modules.values():
                    if os.path.normpath(m["file"]) == abs_path and m["is_tb"]:
                        is_tb = True
                        break
                if is_tb:
                    cfg["design_sources"].remove(src)
                    if src not in cfg.setdefault("testbench_sources", []):
                        cfg["testbench_sources"].append(src)
                    sources_changed = True
        
        if not cfg.get("design_sources") and not cfg.get("testbench_sources") and self.project_analyzer.rtl_files:
            for f in self.project_analyzer.rtl_files:
                rel_path = os.path.relpath(f, self.current_project)
                is_tb = False
                for m in self.project_analyzer.modules.values():
                    if m["file"] == f and m["is_tb"]:
                        is_tb = True
                        break
                
                if is_tb:
                    if rel_path not in cfg.setdefault("testbench_sources", []):
                        cfg["testbench_sources"].append(rel_path)
                else:
                    if rel_path not in cfg.setdefault("design_sources", []):
                        cfg["design_sources"].append(rel_path)
            sources_changed = True
            
        if not cfg.get("top_module") and self.project_analyzer.top_modules and len(self.project_analyzer.top_modules) == 1:
            cfg["top_module"] = self.project_analyzer.top_modules[0]
            sources_changed = True
            
        if not cfg.get("testbench_module") and self.project_analyzer.testbenches and len(self.project_analyzer.testbenches) == 1:
            cfg["testbench_module"] = self.project_analyzer.testbenches[0]
            sources_changed = True
            
        if sources_changed:
            self.project_config.save()
            self.output_panel.log("✅ Auto-configured project sources and modules.")
            
        self.analysis_panel.update_analysis(self.project_analyzer, self.project_config)

    def validate_project(self, quiet=False):
        if not self.ensure_project_open(): 
            return False
            
        if not quiet: 
            self.output_panel.log("▶ Project validation started.")
            
        errors = 0
        cfg = self.project_config.data
        
        design_sources = cfg.get("design_sources") or []
        tb_sources = cfg.get("testbench_sources") or []
        all_sources = design_sources + tb_sources
        
        if not all_sources:
            if not quiet: self.output_panel.log("❌ ERROR: No RTL source files configured.")
            errors += 1
        else:
            for rel_src in all_sources:
                if not os.path.exists(os.path.join(self.current_project, rel_src)):
                    if not quiet: self.output_panel.log(f"❌ ERROR: Source file does not exist: {rel_src}")
                    errors += 1
                
        top_mod = cfg.get("top_module")
        if not top_mod:
            if not quiet: self.output_panel.log("❌ ERROR: No Design Top module configured.")
            errors += 1
        elif top_mod not in self.project_analyzer.modules:
            if not quiet: self.output_panel.log(f"❌ ERROR: Design Top module '{top_mod}' not found.")
            errors += 1
            
        tb_mod = cfg.get("testbench_module")
        if tb_mod and tb_mod not in self.project_analyzer.modules:
            if not quiet: self.output_panel.log(f"❌ ERROR: Testbench '{tb_mod}' not found.")
            errors += 1

        if errors == 0: 
            if not quiet: self.output_panel.log("✅ Validation completed successfully.")
            return True
        else: 
            if not quiet: QMessageBox.warning(self, "Validation Failed", f"Found {errors} error(s). Check Output panel.")
            return False

    def load_previous_synthesis_log(self):
        if not self.current_project: return
        log_path = os.path.join(self.current_project, ".rtlstudio", "logs", "synthesis.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_text = f.read()
                self.analysis_panel.update_ppa(log_text, self.project_analyzer, self.project_config)
                return
            except Exception:
                pass
        self.analysis_panel.clear_ppa()

    # --- YOSYS SYNTHESIS, SCHEMATIC & PPA ---
    def run_synthesis(self, *args, **kwargs):
        try:
            if not self.ensure_project_open(): return
            if self.yosys_process.state() == QProcess.ProcessState.Running: return
            
            if not self.yosys.available:
                self.output_panel.log("❌ ERROR: Yosys is missing.")
                return
                
            if not self.validate_project(quiet=False):
                self.output_panel.log("❌ ERROR: Synthesis cancelled because project validation failed.")
                return
                
            cfg = self.project_config.data
            top_mod = cfg.get("top_module")
            
            raw_design_srcs = cfg.get("design_sources") or []
            design_srcs = []
            
            tb_mod = cfg.get("testbench_module")
            tb_path = None
            if tb_mod and tb_mod in self.project_analyzer.modules:
                tb_path = os.path.normpath(self.project_analyzer.modules[tb_mod]["file"])
                
            for src in raw_design_srcs:
                abs_src = os.path.normpath(os.path.join(self.current_project, src))
                if abs_src != tb_path:
                    design_srcs.append(abs_src)
            
            if not top_mod:
                self.output_panel.log("❌ ERROR: No Design Top module configured.")
                return
            if not design_srcs:
                self.output_panel.log("❌ ERROR: No hardware design sources configured for synthesis.")
                return

            self.editor_tabs.save_all_files()
            
            synth_dir = os.path.join(self.current_project, ".rtlstudio", "synthesis")
            logs_dir = os.path.join(self.current_project, ".rtlstudio", "logs")
            os.makedirs(synth_dir, exist_ok=True)
            os.makedirs(logs_dir, exist_ok=True)
            
            schematic_path = os.path.join(synth_dir, "schematic.svg")
            if os.path.exists(schematic_path):
                os.remove(schematic_path)

            self.output_panel.log("▶ --- Yosys Synthesis Started ---")
            self.output_panel.log(f"▶ Top module: {top_mod}")
            self.output_panel.log(f"▶ Hardware sources: {len(design_srcs)}")
            self.output_panel.log("▶ Running Yosys...")

            script_path = os.path.join(synth_dir, "synth.ys")
            output_v = os.path.join(synth_dir, "synthesized.v")
            
            with open(script_path, "w", encoding="utf-8") as f:
                for src in design_srcs:
                    f.write(f'read_verilog "{src.replace(os.sep, "/")}"\n')
                f.write(f'hierarchy -check -top {top_mod}\n')
                f.write(f'synth -top {top_mod}\n')
                f.write(f'write_verilog "{output_v.replace(os.sep, "/")}"\n')
                
                if self.graphviz.available:
                    f.write(f'show -format svg -prefix .rtlstudio/synthesis/schematic {top_mod}\n')
                    
                f.write('stat\n')

            self.yosys_output_buffer = ""
            self.yosys_process.setWorkingDirectory(self.current_project)
            self.yosys_process.start(self.yosys.path, ["-s", script_path])
            
            self.update_toolbar_state()
            self.update_status_bar("Running Yosys synthesis...")
            
        except Exception as e:
            self.output_panel.log(f"❌ INTERNAL ERROR during Synthesis: {str(e)}")
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
            with open(log_path, "w", encoding="utf-8") as f: 
                f.write(self.yosys_output_buffer)
        except Exception: 
            pass

        if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit:
            self.output_panel.log("✅ Synthesis completed successfully.")
            self.output_panel.log("▶ Synthesis Statistics:")
            
            for line in self.yosys_output_buffer.split('\n'):
                low = line.strip().lower()
                if low.startswith("number of") or "$_" in line or "\\" in line: 
                    self.output_panel.log("  " + line.strip())
                    
            self.output_panel.log("✅ Synthesized netlist generated in .rtlstudio/synthesis/")
            self.project_explorer.load_project(self.current_project)
            
            self.analysis_panel.update_ppa(self.yosys_output_buffer, self.project_analyzer, self.project_config)
            self.left_tabs.setCurrentWidget(self.analysis_panel)
            self.analysis_panel.tabs.setCurrentIndex(1)
            
            self.output_panel.log("✅ PPA analysis updated successfully.")
        else:
            self.output_panel.log(f"❌ ERROR: Synthesis failed with exit code {exit_code}.")
            for line in self.yosys_output_buffer.split('\n'):
                if "ERROR:" in line or "syntax error" in line.lower(): 
                    self.output_panel.log("  " + line.strip())

        self.update_toolbar_state()

    def open_schematic(self):
        schematic_path = os.path.join(self.current_project, ".rtlstudio", "synthesis", "schematic.svg")
        if not os.path.exists(schematic_path):
            self.output_panel.log("❌ ERROR: Schematic not found. Run synthesis first.")
            return
            
        try:
            self.schematic_viewer_dialog = SchematicViewer(schematic_path, self)
            self.schematic_viewer_dialog.show()
            self.output_panel.log("▶ Opened schematic viewer.")
        except Exception as e:
            self.output_panel.log(f"❌ ERROR launching Schematic Viewer: {str(e)}")

    # --- ICARUS BUILD & SIMULATION ---
    def setup_build_workspace(self):
        build_dir = os.path.join(self.current_project, ".rtlstudio", "build")
        logs_dir = os.path.join(self.current_project, ".rtlstudio", "logs")
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        return build_dir, logs_dir

    def run_build(self, *args, **kwargs):
        try:
            if not self.ensure_project_open(): return
            if self.build_process.state() == QProcess.ProcessState.Running: return
            
            if not self.icarus.available: 
                self.output_panel.log("❌ ERROR: Icarus Verilog is missing.")
                return
                
            self.analyze_project()
            
            cfg = self.project_config.data
            design_srcs = cfg.get("design_sources") or []
            tb_srcs = cfg.get("testbench_sources") or []
            all_srcs = design_srcs + tb_srcs
            
            if not all_srcs: 
                self.output_panel.log("❌ ERROR: No RTL source files configured for build.")
                return
                
            self.editor_tabs.save_all_files()
            build_dir, _ = self.setup_build_workspace()
            
            output_file = os.path.join(build_dir, "simulation.vvp")
            if os.path.exists(output_file):
                try: 
                    os.remove(output_file)
                except Exception: 
                    pass
                    
            self.output_panel.log("▶ --- Icarus Verilog Build Started ---")
            args_cmd = ["-g2012", "-o", output_file] 
            
            top_mod = cfg.get("testbench_module") or cfg.get("top_module")
            if top_mod: 
                args_cmd.extend(["-s", top_mod])
                
            for rel_src in all_srcs: 
                args_cmd.append(os.path.join(self.current_project, rel_src))
                
            self.build_process.setWorkingDirectory(self.current_project)
            self.build_process.start(self.icarus.iverilog_path, args_cmd)
            
            self.update_toolbar_state()
            self.update_status_bar("Building project...")
            
        except Exception as e:
            self.output_panel.log(f"❌ INTERNAL ERROR during Build: {str(e)}")
            self.update_toolbar_state()

    def handle_build_stdout(self): 
        self.output_panel.append_raw(self.build_process.readAllStandardOutput().data().decode('utf-8'))
        
    def handle_build_stderr(self): 
        self.output_panel.append_raw(self.build_process.readAllStandardError().data().decode('utf-8'))
        
    def handle_build_finished(self, exit_code, exit_status):
        self.update_status_bar("RTL Studio Ready")
        if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit: 
            self.output_panel.log("✅ Build successful.")
        else: 
            self.output_panel.log(f"❌ ERROR: Build failed with exit code {exit_code}.")
            
        self.update_toolbar_state()

    def run_simulation(self, *args, **kwargs):
        try:
            if not self.ensure_project_open() or not self.icarus.available: return
            if self.sim_process.state() == QProcess.ProcessState.Running: return
            
            vvp_file = os.path.join(self.current_project, ".rtlstudio", "build", "simulation.vvp")
            if not os.path.exists(vvp_file): 
                self.output_panel.log("❌ ERROR: simulation.vvp not found. Please build the project first.")
                return
                
            self.output_panel.log("▶ --- Simulation Started ---")
            
            self.sim_process.setWorkingDirectory(self.current_project)
            self.sim_process.start(self.icarus.vvp_path, [vvp_file])
            
            self.update_toolbar_state()
            self.update_status_bar("Running simulation...")
            
        except Exception as e:
            self.output_panel.log(f"❌ INTERNAL ERROR during Simulation: {str(e)}")
            self.update_toolbar_state()

    def handle_sim_stdout(self): 
        self.output_panel.append_raw(self.sim_process.readAllStandardOutput().data().decode('utf-8'))
        
    def handle_sim_stderr(self): 
        self.output_panel.append_raw(self.sim_process.readAllStandardError().data().decode('utf-8'))
        
    def handle_sim_finished(self, exit_code, exit_status):
        self.update_status_bar("RTL Studio Ready")
        if exit_status == QProcess.ExitStatus.CrashExit: 
            self.output_panel.log("⚠️ Simulation stopped by user or crashed.")
        else: 
            self.output_panel.log(f"✅ Simulation completed. Exit code: {exit_code}")
            
        self.check_for_vcd_artifacts()
        self.update_toolbar_state()

    # --- GTKWAVE ---
    def check_for_vcd_artifacts(self):
        vcd_files = [f for f in os.listdir(self.current_project) if f.endswith(".vcd")]
        if vcd_files:
            vcd_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.current_project, x)), reverse=True)
            self.current_vcd = os.path.join(self.current_project, vcd_files[0])
            self.output_panel.log(f"▶ Waveform detected: {vcd_files[0]}")
            self.project_explorer.load_project(self.current_project)
        else:
            self.current_vcd = None
            
        self.update_toolbar_state()

    def open_waveform(self):
        if not self.gtkwave.available: return
        if not self.current_vcd or not os.path.exists(self.current_vcd): 
            self.output_panel.log("❌ ERROR: No waveform available.")
            return
        if self.gtkwave_process.state() == QProcess.ProcessState.Running: return
        
        self.output_panel.log(f"▶ Launching GTKWave for {os.path.basename(self.current_vcd)}...")
        self.gtkwave_process.setWorkingDirectory(self.current_project)
        self.gtkwave_process.start(self.gtkwave.path, [self.current_vcd])

    def open_file_in_editor(self, filepath):
        if filepath.endswith(".vcd"): 
            self.current_vcd = filepath
            self.open_waveform()
            return
        if filepath.endswith("schematic.svg"): 
            self.open_schematic()
            return
            
        self.editor_tabs.open_file(filepath)

    # --- UI LOGIC ---
    def goto_error_definition(self, filepath, line):
        abs_path = filepath
        if not os.path.isabs(filepath): 
            abs_path = os.path.join(self.current_project, filepath)
        if os.path.exists(abs_path):
            self.open_file_in_editor(abs_path)
            editor = self.editor_tabs.currentWidget()
            if editor:
                cursor = QTextCursor(editor.document().findBlockByNumber(line - 1))
                editor.setTextCursor(cursor)
                editor.centerCursor()
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                editor.setTextCursor(cursor)

    def toggle_theme(self, event=None):
        self.is_dark_theme = not self.is_dark_theme
        self.settings.setValue("is_dark_theme", self.is_dark_theme)
        self.theme_toggle_btn.setText(" Theme: Dark " if self.is_dark_theme else " Theme: Light ")
        self.apply_theme()
        self.editor_tabs.set_theme(self.is_dark_theme)

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.is_dark_theme))
        self.update_toolbar_icons()

    def open_project_settings(self):
        if not self.ensure_project_open(): return
        dialog = ProjectSettingsDialog(self.project_config, self.project_analyzer, self)
        if dialog.exec(): 
            self.analyze_project()
            self.output_panel.log("✅ Project configuration updated.")

    def goto_module_definition(self, filepath, line): 
        self.goto_error_definition(filepath, line)
        
    def on_file_saved(self, path): 
        self.output_panel.log(f"▶ Saved: {os.path.basename(path)}")
        if path.endswith(('.v', '.sv', '.vh', '.svh')): 
            self.analyze_project()
            
    def update_status_bar(self, msg): 
        self.editor_status_label.setText(msg)
        
    def show_find(self): 
        self.find_bar.show()
        self.replace_input.hide()
        self.find_input.setFocus()
        
    def show_replace(self): 
        self.find_bar.show()
        self.replace_input.show()
        self.find_input.setFocus()
        
    def find_next(self): 
        e = self.editor_tabs.currentWidget()
        if e and not e.find(self.find_input.text()):
            c = e.textCursor()
            c.movePosition(QTextCursor.Start)
            e.setTextCursor(c)
            e.find(self.find_input.text())
            
    def find_prev(self): 
        e = self.editor_tabs.currentWidget()
        if e and not e.find(self.find_input.text(), QTextDocument.FindBackward):
            c = e.textCursor()
            c.movePosition(QTextCursor.End)
            e.setTextCursor(c)
            e.find(self.find_input.text(), QTextDocument.FindBackward)
            
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
            c = e.textCursor()
            count = 0
            c.beginEditBlock()
            c.movePosition(QTextCursor.Start)
            e.setTextCursor(c)
            while e.find(self.find_input.text()):
                e.textCursor().insertText(self.replace_input.text())
                count += 1
            c.endEditBlock()
            self.output_panel.log(f"▶ Replaced {count} occurrences.")
        
    def go_to_line(self): 
        e = self.editor_tabs.currentWidget()
        if e:
            line, ok = QInputDialog.getInt(self, "Go To Line", "Line number:", 1, 1, e.blockCount())
            if ok:
                e.setTextCursor(QTextCursor(e.document().findBlockByNumber(line - 1)))
                e.centerCursor()
                
    def open_settings(self): 
        dialog = SettingsDialog(self)
        if dialog.exec(): 
            self.editor_tabs.reload_settings()
    
    def open_project_dialog(self): 
        dir_path = QFileDialog.getExistingDirectory(self, "Open RTL Project")
        if dir_path: 
            self.open_project(dir_path)
    
    def open_project(self, path):
        if not self.close_project(): return
        if not os.path.exists(path): return
        
        self.current_project = path
        self.project_config = ProjectConfig(path)
        self.project_analyzer = ProjectAnalyzer(path)
        self.project_explorer.load_project(path)
        self.add_recent_project(path)
        self.output_panel.log(f"▶ Project opened: {os.path.basename(path)}")
        
        self.analyze_project()
        self.load_previous_synthesis_log()
        self.check_for_vcd_artifacts()
        
        self.update_toolbar_state()
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
        if self.current_project:
            return True
        else:
            QMessageBox.warning(self, "Error", "No project is currently open.")
            return False
    
    def new_file(self):
        if not self.ensure_project_open(): return
        name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
        if ok and name: 
            full_path = os.path.join(self.current_project, name)
            open(full_path, 'w').close()
            
            if name.endswith(('.v', '.sv', '.vh', '.svh')):
                if name not in self.project_config.data.get("design_sources", []):
                    self.project_config.data.setdefault("design_sources", []).append(name)
                    self.project_config.save()
                    
            self.project_explorer.load_project(self.current_project)
            self.open_file_in_editor(full_path)
            self.analyze_project()
            
    def new_folder(self):
        if not self.ensure_project_open(): return
        name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
        if ok and name: 
            os.makedirs(os.path.join(self.current_project, name))
            self.project_explorer.load_project(self.current_project)
            
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
        if isinstance(recents, str): 
            recents = [recents]
        elif not isinstance(recents, list): 
            recents = list(recents) if recents else []
            
        if not recents: 
            self.recent_menu.addAction("No recent projects").setEnabled(False)
        else:
            for path in recents:
                act = QAction(path, self)
                act.triggered.connect(lambda checked, p=path: self.open_project(p))
                self.recent_menu.addAction(act)
        
    def closeEvent(self, event): 
        if not self.editor_tabs.close_all_tabs(): 
            event.ignore() 
        else: 
            event.accept()