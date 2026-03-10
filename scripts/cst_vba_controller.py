"""
CST VBA 宏控制器
通过生成 VBA 宏文件让 CST 执行
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import win32com.client


class CSTVBAController:
    """使用 VBA 宏控制 CST"""

    def __init__(self, cst_exe_path: Optional[str] = None):
        self.cst_exe_path = cst_exe_path or self._find_cst_exe()
        self.cst = None
        self.project = None
        self.vba_log_file = Path("outputs/vba_result.json")

    def _find_cst_exe(self) -> str:
        """自动查找 CST 安装路径"""
        common_paths = [
            r"D:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe",
            r"C:\Program Files (x86)\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe",
            r"D:\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe",
            r"C:\CST Studio Suite 2024\CST DESIGN ENVIRONMENT.exe",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path
        raise FileNotFoundError("CST not found")

    def connect(self) -> bool:
        """连接到 CST"""
        try:
            self.cst = win32com.client.Dispatch("CSTStudio.Application")
            print("[OK] Connected to CST")
            return True
        except Exception as e:
            print(f"[FAIL] Cannot connect to CST: {e}")
            return False

    def run_vba_macro(self, vba_code: str) -> bool:
        """执行 VBA 宏代码"""
        if not self.cst:
            if not self.connect():
                return False

        try:
            # 通过 Schematic 执行 VBA
            result = self.cst.RunVBACode(vba_code)
            print("[OK] VBA macro executed")
            return True
        except Exception as e:
            print(f"[FAIL] VBA execution failed: {e}")
            return False

    def set_parameters(self, params: Dict[str, float]) -> bool:
        """通过 VBA 设置参数"""
        # 构建 VBA 代码
        param_lines = []
        for name, value in params.items():
            param_lines.append(f'DoubleParam("{name}", {value})')

        vba_code = f'''
Sub Main()
    Dim params As Object
    Set params = GetProject().GetParameters()

    ' Set parameters
    {chr(10).join(param_lines)}

    ' Rebuild model
    GetProject().Rebuild
End Sub
'''
        return self.run_vba_macro(vba_code)

    def run_simulation(self) -> bool:
        """通过 VBA 运行仿真"""
        vba_code = '''
Sub Main()
    Dim solver As Object
    Set solver = GetProject().GetSolver()
    solver.Start
End Sub
'''
        return self.run_vba_macro(vba_code)

    def export_s11_to_file(self, export_path: str) -> bool:
        """通过 VBA 导出 S11 到文件"""
        vba_code = f'''
Sub Main()
    Dim sParams As Object
    Dim exportFile As String
    exportFile = "{export_path}"

    ' Export S11
    Set sParams = GetProject().GetSParameters()
    sParams.ExportToASCII "S11", exportFile
End Sub
'''
        return self.run_vba_macro(vba_code)

    def close(self):
        """关闭连接"""
        self.cst = None
        self.project = None


class FakeCSTController:
    """模拟 CST 控制器（测试用）"""

    def __init__(self, cst_exe_path: Optional[str] = None):
        self._params = {}

    def connect(self) -> bool:
        print("[FakeCST] Connected")
        return True

    def set_parameters(self, params: Dict[str, float]) -> bool:
        self._params = params.copy()
        print(f"[FakeCST] Parameters set: {params}")
        return True

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        print("[FakeCST] Simulating (2s)...")
        time.sleep(2)
        print("[FakeCST] Done")
        return True

    def get_s11_parameters(self) -> Dict[str, Any]:
        """Simulate S11 based on parameters"""
        import random

        length = self._params.get("patch_length", 10.0)
        width = self._params.get("patch_width", 8.0)

        # Simple simulation formula
        freq_center = 3.0 - length * 0.05
        s11_depth = -5.0 - width * 0.4

        # Generate simulated S11 curve
        freqs = [2.0 + i * 0.01 for i in range(101)]
        s11_values = []

        for f in freqs:
            detune = (f - freq_center) / 0.1
            s11 = s11_depth * (1 / (1 + detune**2)) + random.uniform(-0.5, 0.5)
            s11_values.append(s11)

        # Find minimum
        min_idx = s11_values.index(min(s11_values))
        s11_min = s11_values[min_idx]
        freq_at_min = freqs[min_idx]

        # Calculate bandwidth
        within_10db = [f for f, s in zip(freqs, s11_values) if s <= -10.0]
        bandwidth = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0

        return {
            "success": True,
            "message": "[FakeCST] Simulated S11",
            "frequencies_GHz": freqs,
            "s11_dB": s11_values,
            "s11_min_dB": round(s11_min, 3),
            "freq_at_min_GHz": round(freq_at_min, 3),
            "bandwidth_10dB_MHz": round(bandwidth, 1),
        }

    def save_project(self, new_path: Optional[str] = None) -> bool:
        print(f"[FakeCST] Saved: {new_path or 'original'}")
        return True

    def close(self):
        print("[FakeCST] Closed")
