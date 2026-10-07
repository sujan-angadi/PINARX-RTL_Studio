import os
import json
import tempfile
import unittest
from src.rtl_studio.optimization_engine import AdaptiveOptimizationEngine
from src.rtl_studio.eda_tools import YosysTool, get_tool_path

class TestAdaptiveOptimizationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AdaptiveOptimizationEngine()
        self.test_dir = tempfile.TemporaryDirectory()
        
        # Original Design
        self.v_file = os.path.join(self.test_dir.name, "random_design.v")
        self.orig_code = (
            "module random_design(input clk, input a, input b, output reg y, output z);\n"
            "    always @(posedge clk) y <= a & a;\n" # Candidate will simplify to 'a'
            "    assign z = a & 1'b1;\n"              # Candidate will simplify to 'a'
            "endmodule\n"
        )
        with open(self.v_file, "w", encoding="utf-8") as f: f.write(self.orig_code)

        # Valid Testbench
        self.tb_file = os.path.join(self.test_dir.name, "random_tb.v")
        self.tb_code = (
            "module random_tb;\n"
            "    reg clk, a, b;\n"
            "    wire y, z;\n"
            "    random_design dut (.clk(clk), .a(a), .b(b), .y(y), .z(z));\n"
            "    initial begin\n"
            "        clk = 0; a = 1; b = 0; #10 clk = 1; #10 clk = 0;\n"
            "        $display(\"y=%b z=%b\", y, z);\n"
            "        $finish;\n"
            "    end\n"
            "endmodule\n"
        )
        with open(self.tb_file, "w", encoding="utf-8") as f: f.write(self.tb_code)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_functional_validation_pass(self):
        # Only run if Icarus is installed
        if not get_tool_path("iverilog"):
            self.skipTest("Icarus Verilog not available. Skipping Phase 4 validation test.")
            
        findings = self.engine.analyze_design(self.test_dir.name)
        candidates = self.engine.generate_candidates(self.test_dir.name, findings)
        comps = self.engine.compare_candidates(self.test_dir.name, "random_design", candidates, ["random_design.v"])
        
        # Run Phase 4
        validated_comps = self.engine.validate_candidates(self.test_dir.name, comps, candidates, ["random_design.v"], ["random_tb.v"])
        
        for comp in validated_comps:
            self.assertEqual(comp.functional_validation_status, "PASS")
            
        json_path = os.path.join(self.test_dir.name, ".rtlstudio", "optimization", "results", "comparison.json")
        with open(json_path, 'r') as jf:
            saved_comps = json.load(jf)
            self.assertEqual(saved_comps[0]["functional_validation_status"], "PASS")

    def test_functional_validation_no_testbench(self):
        findings = self.engine.analyze_design(self.test_dir.name)
        candidates = self.engine.generate_candidates(self.test_dir.name, findings)
        comps = self.engine.compare_candidates(self.test_dir.name, "random_design", candidates, ["random_design.v"])
        
        # Run Phase 4 with empty testbench list
        validated_comps = self.engine.validate_candidates(self.test_dir.name, comps, candidates, ["random_design.v"], [])
        
        for comp in validated_comps:
            self.assertEqual(comp.functional_validation_status, "NO_TESTBENCH")

    def test_functional_validation_fail(self):
        if not get_tool_path("iverilog"):
            self.skipTest("Icarus Verilog not available.")
            
        findings = self.engine.analyze_design(self.test_dir.name)
        candidates = self.engine.generate_candidates(self.test_dir.name, findings)
        
        # Intentionally break a candidate file to simulate bad hardware optimization
        bad_cand = os.path.join(self.test_dir.name, candidates[0].candidate_file)
        with open(bad_cand, 'w') as f:
            f.write(self.orig_code.replace("a & 1'b1", "1'b0")) # z is now 0 instead of matching a
            
        comps = self.engine.compare_candidates(self.test_dir.name, "random_design", candidates, ["random_design.v"])
        validated_comps = self.engine.validate_candidates(self.test_dir.name, comps, candidates, ["random_design.v"], ["random_tb.v"])
        
        # Candidate 001 was broken, should FAIL
        self.assertEqual(validated_comps[0].functional_validation_status, "FAIL")

if __name__ == "__main__":
    unittest.main()