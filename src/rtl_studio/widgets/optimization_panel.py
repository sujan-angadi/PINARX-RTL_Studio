import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                               QScrollArea, QFrame, QGridLayout, QDialog, QTextEdit, 
                               QSizePolicy)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from src.rtl_studio.optimization_engine import AdaptiveOptimizationEngine

class OptimizationWorker(QThread):
    progress = Signal(str)
    finished_opt = Signal(list, list)  # candidates, comparisons
    error = Signal(str)

    def __init__(self, project_path, top_module, design_sources, tb_sources):
        super().__init__()
        self.project_path = project_path
        self.top_module = top_module
        self.design_sources = design_sources
        self.tb_sources = tb_sources

    def run(self):
        try:
            engine = AdaptiveOptimizationEngine()
            
            self.progress.emit("Analyzing RTL...")
            findings = engine.analyze_design(self.project_path, self.design_sources)
            if not findings:
                self.finished_opt.emit([], [])
                return
            
            self.progress.emit(f"Generating candidates for {len(findings)} findings...")
            candidates = engine.generate_candidates(self.project_path, findings)
            if not candidates:
                self.finished_opt.emit([], [])
                return
            
            self.progress.emit(f"Synthesizing {len(candidates)} candidates...")
            comps = engine.compare_candidates(self.project_path, self.top_module, candidates, self.design_sources)
            
            self.progress.emit("Validating candidates...")
            val_comps = engine.validate_candidates(self.project_path, comps, candidates, self.design_sources, self.tb_sources)
            
            self.progress.emit("Optimization analysis complete.")
            self.finished_opt.emit(candidates, val_comps)
        except Exception as e:
            self.error.emit(str(e))

class CandidateDetailsDialog(QDialog):
    def __init__(self, meta, comp, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Candidate Details - {meta.candidate_id}")
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        header = QLabel(f"<b>Optimization Type:</b> {meta.optimization_type}")
        desc = QLabel(f"<b>Description:</b> {meta.transformation_description}")
        layout.addWidget(header)
        layout.addWidget(desc)
        
        layout.addWidget(QLabel("<b>Functional Validation Log:</b>"))
        val_log = QTextEdit()
        val_log.setReadOnly(True)
        val_log.setPlainText(comp.validation_log if comp.validation_log else "No log available.")
        layout.addWidget(val_log)
        
        layout.addWidget(QLabel("<b>Synthesis Log (Candidate):</b>"))
        syn_log = QTextEdit()
        syn_log.setReadOnly(True)
        syn_log.setPlainText(comp.candidate_metrics.synthesis_log)
        layout.addWidget(syn_log)
        
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

class OptimizationPanel(QWidget):
    req_open_file = Signal(str)

    def __init__(self):
        super().__init__()
        self.project_path = None
        self.project_config = None
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        title = QLabel("ADAPTIVE RTL OPTIMIZATION")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        subtitle = QLabel("Analyze your RTL and evaluate hardware optimization candidates.")
        
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        
        # Action Area
        action_layout = QHBoxLayout()
        self.path_label = QLabel("No project is currently open.")
        self.path_label.setStyleSheet("color: #888;")
        self.run_btn = QPushButton("Run Optimization Analysis")
        self.run_btn.setFixedWidth(220)
        self.run_btn.clicked.connect(self.run_pipeline)
        self.run_btn.setEnabled(False)
        
        action_layout.addWidget(self.path_label)
        action_layout.addStretch()
        action_layout.addWidget(self.run_btn)
        main_layout.addLayout(action_layout)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        main_layout.addWidget(self.status_label)
        
        # Summary
        self.summary_label = QLabel("")
        main_layout.addWidget(self.summary_label)
        
        # Scroll Area for Candidates
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.candidates_container = QWidget()
        self.candidates_layout = QVBoxLayout(self.candidates_container)
        self.candidates_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.candidates_container)
        
        main_layout.addWidget(self.scroll_area)

    def set_project(self, project_path, project_config):
        self.project_path = project_path
        self.project_config = project_config
        if self.project_path:
            self.path_label.setText(f"Project: {os.path.basename(self.project_path)}")
            self.run_btn.setEnabled(True)
        else:
            self.path_label.setText("No project is currently open.")
            self.run_btn.setEnabled(False)

    def run_pipeline(self):
        if not self.project_path or not self.project_config:
            return
            
        cfg = self.project_config.data
        top_mod = cfg.get("top_module", "")
        ds = cfg.get("design_sources", [])
        tb = cfg.get("testbench_sources", [])
        
        # Clear existing
        for i in reversed(range(self.candidates_layout.count())): 
            w = self.candidates_layout.itemAt(i).widget()
            if w: w.deleteLater()
            
        self.summary_label.setText("")
        self.run_btn.setEnabled(False)
        
        self.worker = OptimizationWorker(self.project_path, top_mod, ds, tb)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.error.connect(self.handle_error)
        self.worker.finished_opt.connect(self.populate_candidates)
        self.worker.start()

    def handle_error(self, err):
        self.status_label.setText(f"Error: {err}")
        self.run_btn.setEnabled(True)

    def populate_candidates(self, candidates, comparisons):
        self.run_btn.setEnabled(True)
        if not candidates or not comparisons:
            self.status_label.setText("No optimization opportunities were detected.")
            return
            
        self.status_label.setText("Optimization analysis complete.")
        
        imp, unch, fail = 0, 0, 0
        for c in comparisons:
            if c.synthesis_status == "IMPROVED": imp += 1
            elif c.synthesis_status == "UNCHANGED": unch += 1
            else: fail += 1
            
        self.summary_label.setText(f"<b>Findings:</b> {len(candidates)} | <b>Improved:</b> {imp} | <b>Unchanged:</b> {unch} | <b>Failed:</b> {fail}")
        
        cand_map = {c.candidate_id: c for c in candidates}
        
        for comp in comparisons:
            meta = cand_map.get(comp.candidate_id)
            if not meta: continue
            self.add_candidate_card(meta, comp)

    def add_candidate_card(self, meta, comp):
        card = QFrame()
        card.setObjectName("CandidateCard")
        card.setStyleSheet("#CandidateCard { border: 1px solid #7B8496; border-radius: 8px; padding: 10px; margin-bottom: 10px; }")
        
        layout = QVBoxLayout(card)
        
        # Top Row
        top_row = QHBoxLayout()
        title = QLabel(f"<b>{meta.candidate_id.upper()}</b> — {meta.optimization_type}")
        title.setFont(QFont("Segoe UI", 11))
        
        val_color = "#E01A4F"
        if comp.functional_validation_status == "PASS": val_color = "#7CB518"
        elif comp.functional_validation_status == "PENDING": val_color = "#F3A712"
        elif comp.functional_validation_status == "NO_TESTBENCH": val_color = "#92929A"
        
        val_status = QLabel(f"<b>Validation:</b> <span style='color:{val_color};'>{comp.functional_validation_status}</span>")
        
        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(val_status)
        layout.addLayout(top_row)
        
        # Source & Desc
        layout.addWidget(QLabel(f"{meta.original_file}"))
        desc = QLabel(f"<i>{meta.transformation_description}</i>")
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)
        
        # Grid metrics
        grid = QGridLayout()
        grid.addWidget(QLabel("<b>Cells:</b>"), 0, 0)
        grid.addWidget(QLabel(f"{comp.original_metrics.total_cells} → {comp.candidate_metrics.total_cells}"), 0, 1)
        grid.addWidget(QLabel(f"({comp.cell_change_percent}%)"), 0, 2)
        
        grid.addWidget(QLabel("<b>Registers:</b>"), 1, 0)
        grid.addWidget(QLabel(f"{comp.original_metrics.registers} → {comp.candidate_metrics.registers}"), 1, 1)
        grid.addWidget(QLabel(f"({comp.register_change_percent}%)"), 1, 2)
        
        grid.addWidget(QLabel("<b>Synthesis:</b>"), 2, 0)
        grid.addWidget(QLabel(f"{comp.synthesis_status}"), 2, 1)
        
        layout.addLayout(grid)
        
        # Buttons
        btn_row = QHBoxLayout()
        view_btn = QPushButton("View Candidate")
        open_btn = QPushButton("Open RTL")
        view_btn.clicked.connect(lambda: CandidateDetailsDialog(meta, comp, self).exec())
        open_btn.clicked.connect(lambda: self.req_open_file.emit(os.path.join(self.project_path, meta.candidate_file)))
        
        btn_row.addStretch()
        btn_row.addWidget(view_btn)
        btn_row.addWidget(open_btn)
        layout.addLayout(btn_row)
        
        self.candidates_layout.addWidget(card)