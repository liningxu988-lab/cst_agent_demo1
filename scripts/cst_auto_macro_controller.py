"""
CST 自动宏控制器
生成完整的 VBA 宏，一键完成：参数更新 + 仿真运行 + S11 导出
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os


class CSTAutoMacroController:
    """
    自动生成完整工作流程的 VBA 宏

    功能：
    1. 一键宏：参数更新 + 仿真 + S11 导出（合并到一个宏）
    2. 批量宏：生成多轮迭代的宏文件
    3. 结果监控：自动检测导出的 S11 文件
    4. 智能等待：自动判断仿真是否完成
    """

    def __init__(self, cst_exe_path: Optional[str] = None, project_path: Optional[str] = None):
        self.cst_exe_path = cst_exe_path
        self.project_path = project_path
        self.work_dir = Path("outputs/cst_auto")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.current_iteration = 0

    def connect(self) -> bool:
        """检查工作目录"""
        print("[AutoMacro] Ready")
        return True

    def open_project(self, project_path: str) -> bool:
        """记录项目路径"""
        abs_path = Path(project_path).resolve()
        if abs_path.exists():
            self.project_path = str(abs_path)
            print(f"[AutoMacro] Project: {self.project_path}")
            print(f"[AutoMacro] Please open this project in CST first")
            return True
        return False

    def generate_all_in_one_macro(self, params: Dict[str, float], export_path: str) -> str:
        """
        生成一键完成所有操作的宏

        包含：
        1. 参数更新
        2. 模型重建
        3. 运行仿真
        4. 导出 S11 到文件
        """
        macro_file = self.work_dir / f"auto_iteration_{self.current_iteration + 1}.mcr"

        # 转换导出路径为 VBA 格式（双反斜杠）
        vba_export_path = export_path.replace("\\", "\\\\")

        # 构建参数更新代码
        param_lines = []
        for name, value in params.items():
            if name.startswith("_") or name in ["project_path", "targets"]:
                continue
            if isinstance(value, (int, float)):
                param_lines.append(f'    StoreDoubleParameter "{name}", {value}')

        params_code = "\n".join(param_lines) if param_lines else "    ' No parameters to update"

        vba_code = f'''\' CST Auto Design - All-in-One Macro
\' Iteration: {self.current_iteration + 1}
\'
Sub Main()
    Dim proj As Object
    Dim solver As Object
    Dim results As Object
    Dim s11_result As Object
    Dim exportSuccess As Boolean
    
    exportSuccess = False
    
    On Error Resume Next
    
    \' Step 1: Get project
    Set proj = GetProject()
    If proj Is Nothing Then
        MsgBox "Error: Cannot get project!"
        Exit Sub
    End If
    
    \' Step 2: Update parameters
    Debug.Print "Updating parameters..."
{params_code}
    
    \' Step 3: Rebuild model
    Debug.Print "Rebuilding model..."
    proj.Rebuild
    
    \' Step 4: Run simulation
    Debug.Print "Starting simulation..."
    Set solver = proj.GetSolver()
    If Not solver Is Nothing Then
        solver.Start
        
        \' Wait for simulation to complete
        Debug.Print "Waiting for simulation..."
        Do While solver.IsSimulating
            Debug.Print "Simulating..."
            Sleep 2000  \' Wait 2 seconds
        Loop
        
        Debug.Print "Simulation completed!"
        
        \' Step 5: Export S11
        Debug.Print "Exporting S11..."
        Set results = proj.GetResultsInTree()
        
        If Not results Is Nothing Then
            Dim i As Integer
            For i = 0 To results.Count - 1
                Dim item As Object
                Set item = results.Item(i)
                
                If Not item Is Nothing Then
                    Dim itemName As String
                    itemName = item.GetName()
                    
                    \' Look for S11 result
                    If InStr(itemName, "S1,1") > 0 Or InStr(itemName, "S11") > 0 Then
                        Debug.Print "Found S11: " & itemName
                        
                        \' Export to ASCII
                        On Error Resume Next
                        item.ExportCurve "default", "{vba_export_path}", True
                        
                        If Err.Number = 0 Then
                            exportSuccess = True
                            Debug.Print "Export successful!"
                        Else
                            Debug.Print "Export error: " & Err.Description
                        End If
                        On Error GoTo 0
                        
                        Exit For
                    End If
                End If
            Next
        End If
    End If
    
    \' Show result
    If exportSuccess Then
        MsgBox "Iteration {self.current_iteration + 1} completed!" & vbCrLf & _
               "Parameters updated, simulation run, S11 exported to:" & vbCrLf & _
               "{export_path}", vbInformation
    Else
        MsgBox "Iteration {self.current_iteration + 1} completed, but S11 export failed." & vbCrLf & _
               "Please manually export S11 to: {export_path}", vbExclamation
    End If
End Sub

\' Helper function
Sub Sleep(milliseconds As Long)
    Dim endTime As Double
    endTime = Timer + milliseconds / 1000
    Do While Timer < endTime
        DoEvents
    Loop
End Sub
'''

        macro_file.write_text(vba_code, encoding="utf-8")
        print(f"[AutoMacro] Generated all-in-one macro: {macro_file}")
        return str(macro_file)

    def set_parameters(self, params: Dict[str, float]) -> bool:
        """
        设置参数 - 生成自动宏
        """
        self.current_iteration += 1

        # 设置导出文件路径
        export_file = self.work_dir / f"s11_iteration_{self.current_iteration}.txt"

        # 生成一键宏
        macro_file = self.generate_all_in_one_macro(params, str(export_file))

        print("\n" + "="*70)
        print("AUTO-MACRO MODE: Single macro for all operations")
        print("="*70)
        print(f"\n1. In CST: Macros -> Import -> Select: {macro_file}")
        print(f"2. Run the macro - it will automatically:")
        print(f"   - Update parameters: {params}")
        print(f"   - Rebuild the model")
        print(f"   - Run simulation")
        print(f"   - Export S11 to: {export_file}")
        print(f"3. After the macro completes, press Enter here")
        print("="*70 + "\n")

        # 保存导出路径供后续读取
        self._last_export_path = str(export_file)

        return True

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        """
        仿真已经在宏中运行，这里只需要等待用户确认
        """
        if wait_complete:
            input("\n>>> Press Enter after the macro completes in CST...")
        return True

    def get_s11_parameters(self) -> Dict[str, Any]:
        """
        读取 S11 参数 - 自动检测导出的文件
        """
        # 尝试读取最后一次导出的文件
        export_file = Path(self._last_export_path)

        # 如果文件不存在，尝试查找任何 s11 文件
        if not export_file.exists():
            s11_files = list(self.work_dir.glob("s11_iteration_*.txt"))
            if s11_files:
                # 取最新的文件
                s11_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                export_file = s11_files[0]
                print(f"[AutoMacro] Using latest S11 file: {export_file}")

        if export_file.exists():
            return self._parse_s11_file(str(export_file))

        # 如果文件不存在，提示用户导出
        print("\n" + "="*70)
        print("S11 file not found. Please export manually:")
        print(f"Expected file: {export_file}")
        print("="*70 + "\n")

        # 让用户输入文件路径
        user_path = input("Enter the S11 export file path (or press Enter to retry): ").strip()
        if user_path:
            return self._parse_s11_file(user_path)

        return {
            "success": False,
            "message": "S11 file not found",
            "frequencies_GHz": [],
            "s11_dB": [],
        }

    def _parse_s11_file(self, file_path: str) -> Dict[str, Any]:
        """解析 S11 ASCII 文件"""
        freqs = []
        s11_db = []

        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("!"):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            freq = float(parts[0])
                            s11 = float(parts[1])
                            freqs.append(freq)
                            s11_db.append(s11)
                        except ValueError:
                            continue

            if not freqs:
                return {
                    "success": False,
                    "message": "No valid data in S11 file",
                    "frequencies_GHz": [],
                    "s11_dB": [],
                }

            # 计算指标
            min_idx = s11_db.index(min(s11_db))
            s11_min = s11_db[min_idx]
            freq_at_min = freqs[min_idx]

            within_10db = [f for f, s in zip(freqs, s11_db) if s <= -10.0]
            bandwidth = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0

            return {
                "success": True,
                "message": "S11 loaded from auto-export",
                "frequencies_GHz": freqs,
                "s11_dB": s11_db,
                "s11_min_dB": round(s11_min, 3),
                "freq_at_min_GHz": round(freq_at_min, 3),
                "bandwidth_10dB_MHz": round(bandwidth, 1),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Parse error: {e}",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

    def save_project(self, new_path: Optional[str] = None) -> bool:
        """提示用户保存"""
        print(f"\n[AutoMacro] Please save project in CST if needed")
        return True

    def close(self):
        """清理"""
        print(f"\n[AutoMacro] Work files saved in: {self.work_dir}")


# 保持兼容性
from scripts.cst_controller import FakeCSTController
