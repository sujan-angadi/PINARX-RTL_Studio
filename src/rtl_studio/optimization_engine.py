"""
PINARX Adaptive RTL Optimization Engine (Phases 1, 2, 3 & 4)
Responsibility: Advisory analysis, candidate generation, synthesis comparison, and functional validation.
"""
import os
import re
import uuid
import json
import subprocess
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List

from src.rtl_studio.eda_tools import get_tool_path, get_eda_env_dict

@dataclass
class OptimizationFinding:
    opt_type: str
    file: str
    line: int
    signal: str
    description: str
    confidence: str
    evidence: str
    safe_to_apply: bool

@dataclass
class CandidateMetadata:
    candidate_id: str
    source_finding_id: str
    optimization_type: str
    original_file: str
    candidate_file: str
    transformation_description: str
    confidence: str
    status: str
    generated_at: str
    requires_validation: bool

@dataclass
class SynthesisMetrics:
    total_cells: int
    combinational_cells: int
    sequential_cells: int
    registers: int
    cell_breakdown: dict
    synthesis_success: bool
    synthesis_log: str
    error_message: str

@dataclass
class CandidateComparison:
    candidate_id: str
    original_metrics: SynthesisMetrics
    candidate_metrics: SynthesisMetrics
    cell_change: int
    cell_change_percent: float
    register_change: int
    register_change_percent: float
    synthesis_status: str
    functional_validation_status: str = "PENDING"
    validation_log: str = ""

class AdaptiveOptimizationEngine:
    def __init__(self):
        self.re_reg_width = re.compile(r'\breg\s+\[(\d+)\s*:\s*(\d+)\]\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:;|,)')
        self.re_constant_assign = re.compile(r'\bassign\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+\'[bhdBHD][0-9a-fA-F_xXzZ]+|\d+)\s*;')
        self.re_redundant_logic = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*([&|])\s*\1\b')
        self.re_arithmetic = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(\+|-|\*|/)\s*(0|1|\d+\'[bhdBHD][01]+)\b')
        self.re_constant_expr = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*&\s*(1\'b1|1)\b')

    def analyze_design(self, project_path: str, files: List[str] = None) -> List[OptimizationFinding]:
        findings = []
        if not project_path or not os.path.exists(project_path): return findings

        files_to_scan = files if files is not None else []
        if not files_to_scan:
            for root, dirs, filenames in os.walk(project_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("build", "__pycache__")]
                for f in filenames:
                    if f.endswith(('.v', '.sv', '.vh', '.svh')):
                        files_to_scan.append(os.path.relpath(os.path.join(root, f), project_path).replace('\\', '/'))

        for rel_file in files_to_scan:
            abs_file = os.path.join(project_path, rel_file)
            if not os.path.exists(abs_file): continue

            try:
                with open(abs_file, 'r', encoding='utf-8') as f: lines = f.readlines()
                for line_idx, line in enumerate(lines):
                    line_num = line_idx + 1
                    clean_line = line.split('//')[0].strip()
                    if not clean_line: continue

                    for match in self.re_reg_width.finditer(clean_line):
                        try:
                            width = abs(int(match.group(1)) - int(match.group(2))) + 1
                            if width >= 32:
                                findings.append(OptimizationFinding("Register Width Analysis", rel_file, line_num, match.group(3),
                                    f"Wide register ({width} bits) detected.", "LOW", clean_line.strip(), False))
                        except ValueError: pass

                    for match in self.re_constant_assign.finditer(clean_line):
                        findings.append(OptimizationFinding("Constant Signal", rel_file, line_num, match.group(1),
                            f"Signal assigned to constant ({match.group(2)}).", "MEDIUM", clean_line.strip(), False))

                    for match in self.re_redundant_logic.finditer(clean_line):
                        findings.append(OptimizationFinding("Redundant Logic", rel_file, line_num, match.group(1),
                            f"Redundant self-operation ({match.group(2)}).", "HIGH", clean_line.strip(), False))

                    for match in self.re_arithmetic.finditer(clean_line):
                        if (match.group(2) in ['+', '-'] and match.group(3) in ['0', "1'b0", "32'd0"]) or (match.group(2) in ['*', '/'] and match.group(3) in ['1', "1'b1", "32'd1"]):
                            findings.append(OptimizationFinding("Arithmetic Simplification", rel_file, line_num, match.group(1),
                                f"Trivial arithmetic ({match.group(2)} {match.group(3)}).", "HIGH", clean_line.strip(), False))
                            
                    for match in self.re_constant_expr.finditer(clean_line):
                        findings.append(OptimizationFinding("Constant Expression Simplification", rel_file, line_num, match.group(1),
                            f"Constant operand ({match.group(2)}) can be simplified.", "HIGH", clean_line.strip(), False))
            except Exception: pass
        return findings

    def generate_candidates(self, project_path: str, findings: List[OptimizationFinding]) -> List[CandidateMetadata]:
        candidates = []
        if not project_path or not os.path.exists(project_path): return candidates

        cands_dir = os.path.join(project_path, ".rtlstudio", "optimization", "candidates")
        os.makedirs(cands_dir, exist_ok=True)

        for idx, finding in enumerate(findings):
            cand_id = f"candidate_{idx+1:03d}"
            specific_cand_dir = os.path.join(cands_dir, cand_id)
            os.makedirs(specific_cand_dir, exist_ok=True)
            
            orig_file_path = os.path.join(project_path, finding.file)
            cand_file_path = os.path.join(specific_cand_dir, os.path.basename(finding.file))
            if not os.path.exists(orig_file_path): continue
                
            with open(orig_file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
            if finding.line < 1 or finding.line > len(lines): continue
                
            original_line = lines[finding.line - 1]
            new_line, transformation_desc = original_line, ""
            
            if finding.opt_type == "Redundant Logic":
                new_line = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[&|]\s*\1\b', r'\1', original_line)
                transformation_desc = "Removed structurally obvious redundant self-operation."
            elif finding.opt_type == "Arithmetic Simplification":
                new_line = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(\+|-)\s*(0|32\'d0|1\'b0)\b', r'\1', original_line)
                new_line = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(\*|/)\s*(1|32\'d1|1\'b1)\b', r'\1', new_line)
                transformation_desc = "Eliminated trivial arithmetic constant."
            elif finding.opt_type == "Constant Expression Simplification":
                new_line = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*&\s*(1\'b1|1)\b', r'\1', original_line)
                transformation_desc = "Simplified constant operand."
            elif finding.opt_type == "Register Width Analysis":
                new_line = re.sub(r'(\breg\s+)\[\d+\s*:\s*\d+\](\s+[a-zA-Z_][a-zA-Z0-9_]*)', r'\1[7:0]\2', original_line)
                transformation_desc = "Speculatively proposed reducing register width to 8 bits."
                
            if new_line != original_line:
                lines[finding.line - 1] = new_line
                with open(cand_file_path, 'w', encoding='utf-8') as f: f.writelines(lines)
                candidates.append(CandidateMetadata(cand_id, f"fnd_{uuid.uuid4().hex[:8]}", finding.opt_type, finding.file,
                    os.path.relpath(cand_file_path, project_path).replace('\\', '/'), transformation_desc, finding.confidence, "GENERATED", datetime.now().isoformat(), True))
        return candidates

    def compare_candidates(self, project_path: str, top_module: str, candidates: List[CandidateMetadata], original_files: List[str]) -> List[CandidateComparison]:
        comparisons = []
        if not project_path or not os.path.exists(project_path): return comparisons

        opt_dir = os.path.join(project_path, ".rtlstudio", "optimization")
        results_dir = os.path.join(opt_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        orig_work_dir = os.path.join(opt_dir, "original_synth")
        os.makedirs(orig_work_dir, exist_ok=True)
        abs_original_files = [os.path.join(project_path, f) for f in original_files]
        orig_metrics = self._run_headless_synthesis(project_path, abs_original_files, top_module, orig_work_dir)

        for cand in candidates:
            cand_work_dir = os.path.join(opt_dir, "candidates", cand.candidate_id)
            cand_files = []
            for f in original_files:
                if f == cand.original_file:
                    cand_files.append(os.path.join(project_path, cand.candidate_file))
                else:
                    cand_files.append(os.path.join(project_path, f))
                    
            cand_metrics = self._run_headless_synthesis(project_path, cand_files, top_module, cand_work_dir)
            
            cell_change = orig_metrics.total_cells - cand_metrics.total_cells
            cell_change_pct = (cell_change / orig_metrics.total_cells * 100.0) if orig_metrics.total_cells > 0 else 0.0
            
            reg_change = orig_metrics.registers - cand_metrics.registers
            reg_change_pct = (reg_change / orig_metrics.registers * 100.0) if orig_metrics.registers > 0 else 0.0
            
            if not cand_metrics.synthesis_success:
                status = "SYNTHESIS FAILED"
            elif cell_change > 0 or reg_change > 0:
                status = "IMPROVED"
            elif cell_change < 0 or reg_change < 0:
                status = "WORSE"
            else:
                status = "UNCHANGED"
                
            comp = CandidateComparison(
                candidate_id=cand.candidate_id,
                original_metrics=orig_metrics,
                candidate_metrics=cand_metrics,
                cell_change=cell_change,
                cell_change_percent=round(cell_change_pct, 2),
                register_change=reg_change,
                register_change_percent=round(reg_change_pct, 2),
                synthesis_status=status,
                functional_validation_status="PENDING",
                validation_log=""
            )
            comparisons.append(comp)
            
            with open(os.path.join(results_dir, f"{cand.candidate_id}.json"), "w", encoding="utf-8") as jf:
                json.dump(asdict(comp), jf, indent=4)
                
        with open(os.path.join(results_dir, "comparison.json"), "w", encoding="utf-8") as jf:
            json.dump([asdict(c) for c in comparisons], jf, indent=4)
            
        return comparisons

    def validate_candidates(self, project_path: str, comparisons: List[CandidateComparison], candidates: List[CandidateMetadata], original_files: List[str], testbench_files: List[str]) -> List[CandidateComparison]:
        if not project_path or not os.path.exists(project_path): return comparisons
        
        opt_dir = os.path.join(project_path, ".rtlstudio", "optimization")
        val_dir = os.path.join(opt_dir, "validation")
        results_dir = os.path.join(opt_dir, "results")
        os.makedirs(val_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)

        if not testbench_files:
            for comp in comparisons:
                comp.functional_validation_status = "NO_TESTBENCH"
                comp.validation_log = "No testbench available for functional validation."
            self._save_comparisons(results_dir, comparisons)
            return comparisons

        iverilog_exe = get_tool_path("iverilog")
        vvp_exe = get_tool_path("vvp")

        if not iverilog_exe or not vvp_exe:
            for comp in comparisons:
                comp.functional_validation_status = "NOT_VALIDATED"
                comp.validation_log = "Icarus Verilog toolchain not found."
            self._save_comparisons(results_dir, comparisons)
            return comparisons

        # 1. Simulate Original Baseline
        orig_val_dir = os.path.join(val_dir, "original")
        os.makedirs(orig_val_dir, exist_ok=True)
        
        abs_original_files = [os.path.join(project_path, f) for f in original_files]
        abs_tb_files = [os.path.join(project_path, f) for f in testbench_files]
        
        baseline_out, baseline_success, baseline_err = self._run_simulation(iverilog_exe, vvp_exe, abs_original_files + abs_tb_files, orig_val_dir)
        
        if not baseline_success:
            for comp in comparisons:
                comp.functional_validation_status = "SIMULATION FAILED"
                comp.validation_log = f"Baseline compilation/simulation failed:\n{baseline_err}"
            self._save_comparisons(results_dir, comparisons)
            return comparisons

        # 2. Simulate Candidates and Compare
        cand_meta_map = {c.candidate_id: c for c in candidates}

        for comp in comparisons:
            cand = cand_meta_map.get(comp.candidate_id)
            if not cand: continue
            
            cand_val_dir = os.path.join(val_dir, comp.candidate_id)
            os.makedirs(cand_val_dir, exist_ok=True)
            
            cand_files = []
            for f in original_files:
                if f == cand.original_file:
                    cand_files.append(os.path.join(project_path, cand.candidate_file))
                else:
                    cand_files.append(os.path.join(project_path, f))
                    
            cand_out, cand_success, cand_err = self._run_simulation(iverilog_exe, vvp_exe, cand_files + abs_tb_files, cand_val_dir)
            
            if not cand_success:
                comp.functional_validation_status = "SIMULATION FAILED"
                comp.validation_log = f"Candidate compilation/simulation failed:\n{cand_err}"
            elif baseline_out.strip() == cand_out.strip():
                comp.functional_validation_status = "PASS"
                comp.validation_log = "Observable testbench outputs matched baseline perfectly."
            else:
                comp.functional_validation_status = "FAIL"
                comp.validation_log = "Output mismatch detected. Candidate logic is not equivalent."

        self._save_comparisons(results_dir, comparisons)
        return comparisons

    def _run_simulation(self, iverilog_exe: str, vvp_exe: str, source_files: List[str], work_dir: str):
        vvp_out_file = os.path.join(work_dir, "sim.vvp")
        env = get_eda_env_dict()
        
        # Compile
        compile_cmd = [iverilog_exe, "-g2012", "-o", vvp_out_file] + source_files
        try:
            comp_res = subprocess.run(compile_cmd, cwd=work_dir, capture_output=True, text=True, env=env, timeout=10)
            if comp_res.returncode != 0:
                return "", False, comp_res.stderr + comp_res.stdout
        except Exception as e:
            return "", False, str(e)
            
        # Execute
        try:
            sim_res = subprocess.run([vvp_exe, vvp_out_file], cwd=work_dir, capture_output=True, text=True, env=env, timeout=15)
            if sim_res.returncode != 0:
                return "", False, sim_res.stderr + sim_res.stdout
            return sim_res.stdout, True, ""
        except Exception as e:
            return "", False, str(e)

    def _save_comparisons(self, results_dir: str, comparisons: List[CandidateComparison]):
        for comp in comparisons:
            with open(os.path.join(results_dir, f"{comp.candidate_id}.json"), "w", encoding="utf-8") as jf:
                json.dump(asdict(comp), jf, indent=4)
        with open(os.path.join(results_dir, "comparison.json"), "w", encoding="utf-8") as jf:
            json.dump([asdict(c) for c in comparisons], jf, indent=4)

    def _run_headless_synthesis(self, project_path: str, source_files: List[str], top_module: str, work_dir: str) -> SynthesisMetrics:
        ys_path = os.path.join(work_dir, "synth.ys")
        try:
            with open(ys_path, "w", encoding="utf-8") as f:
                for src in source_files: f.write(f'read_verilog "{src.replace(os.sep, "/")}"\n')
                f.write(f'hierarchy -check -top {top_module}\n')
                f.write(f'synth -top {top_module}\n')
                f.write('stat\n')
        except Exception as e:
            return SynthesisMetrics(0,0,0,0,{},False,"",f"Failed to write script: {str(e)}")

        yosys_exe = get_tool_path("yosys")
        if not yosys_exe:
            return SynthesisMetrics(0,0,0,0,{},False,"","Yosys executable not found.")

        try:
            result = subprocess.run([yosys_exe, "-s", ys_path], cwd=project_path, capture_output=True, text=True, env=get_eda_env_dict(), timeout=60)
            log = result.stdout + result.stderr
            success = (result.returncode == 0) and ("ERROR:" not in log)
            if not success: return SynthesisMetrics(0,0,0,0,{},False,log,"Synthesis failed.")
            return self._parse_yosys_stat(log)
        except subprocess.TimeoutExpired:
            return SynthesisMetrics(0,0,0,0,{},False,"","Synthesis timed out.")
        except Exception as e:
            return SynthesisMetrics(0,0,0,0,{},False,"",str(e))

    def _parse_yosys_stat(self, log: str) -> SynthesisMetrics:
        total_cells, cell_breakdown, in_cell_area = 0, {}, False
        re_cells_new = re.compile(r'^\s*(\d+)\s+cells\s*$')
        
        for line in log.split('\n'):
            if "Number of cells:" in line:
                try: total_cells = int(line.split()[-1])
                except ValueError: pass
                in_cell_area = True
                continue
                
            match_cells = re_cells_new.match(line)
            if match_cells:
                total_cells = int(match_cells.group(1))
                in_cell_area = True
                continue
                
            if in_cell_area:
                if line.strip() != "" and not line.startswith(" ") and not line.startswith("===") and not line.startswith("+"):
                    in_cell_area = False
                    continue
                    
                line_stripped = line.strip()
                if line_stripped:
                    parts = line_stripped.split()
                    count, cell_type = None, None
                    if len(parts) == 2 and parts[0].isdigit():
                        count, cell_type = int(parts[0]), parts[1]
                    elif len(parts) >= 2 and parts[-1].isdigit():
                        count, cell_type = int(parts[-1]), parts[0]
                        
                    if count is not None and cell_type is not None:
                        if cell_type.lower() not in ['wires', 'ports', 'cells', 'memories', 'wire', 'port', 'memory', 'public']:
                            cell_breakdown[cell_type] = count
                            
        seq_cells = sum(count for ctype, count in cell_breakdown.items() if any(k in ctype.upper() for k in ["DFF", "DLATCH", "FD"]))
        return SynthesisMetrics(total_cells, total_cells - seq_cells, seq_cells, seq_cells, cell_breakdown, True, log, "")