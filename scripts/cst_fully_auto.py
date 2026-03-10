"""
CST 完全全自动控制器 - 零人工介入
使用命令行参数和项目嵌入实现真正自动执行
"""

import json
import subprocess
import sys
import tempfile
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading
import queue


class CSTFullyAutoController:
    """
    真正全自动的 CST 控制器
    
    策略：
    1. 生成一个"启动宏"文件，CST 打开时自动执行
    2. 宏中包含：参数更新、仿真、导出、退出
    3. 使用命令行启动 CST 时指定宏文件
    4. 监控输出文件，判断完成状态
    """

    def __init__(self, cst_install_path: Optional[str] = None):
        self.cst_install_path = cst_install_path or self._find_cst_install()
        self.cst_exe = Path(self.cst_install_path) / "CST DESIGN ENVIRONMENT.exe"
        self.work_dir = Path("outputs/cst_fully_auto")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.current_iteration = 0
        self.cst_process = None
        self._status_queue = queue.Queue()

    def _find_cst_install(self) -> str:
        """Find CST installation"""
        common_paths = [
            r"D:\Program Files (x86)\CST Studio Suite 2024",
            r"C:\Program Files (x86)\CST Studio Suite 2024",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path
        raise FileNotFoundError("CST not found")

    def connect(self) -> bool:
        """Check CST executable"""
        if not self.cst_exe.exists():
            print(f"[FullyAuto] CST not found: {self.cst_exe}")
            return False
        print(f"[FullyAuto] CST found: {self.cst_exe}")
        return True

    def open_project(self, project_path: str) -> bool:
        """Resolve and record CST project path (.cst preferred)."""
        abs_path = Path(project_path).resolve()

        # Prefer explicit .cst file.
        if abs_path.is_file() and abs_path.suffix.lower() == ".cst":
            self.project_path = str(abs_path)
            print(f"[FullyAuto] Project: {self.project_path}")
            return True

        # If user passes project folder name (e.g. templates/antenna_template),
        # try matching sibling .cst file (templates/antenna_template.cst).
        sibling_cst = abs_path.with_suffix(".cst")
        if sibling_cst.exists():
            self.project_path = str(sibling_cst)
            print(f"[FullyAuto] Project resolved from folder name: {self.project_path}")
            return True

        # If a directory is passed, try to find a .cst file inside it.
        if abs_path.is_dir():
            cst_candidates = sorted(abs_path.glob("*.cst"))
            if cst_candidates:
                self.project_path = str(cst_candidates[0].resolve())
                print(f"[FullyAuto] Project resolved from directory: {self.project_path}")
                return True

        # Last fallback: keep original if it exists (for legacy unpacked projects).
        if abs_path.exists():
            self.project_path = str(abs_path)
            print(f"[FullyAuto] Project (legacy path): {self.project_path}")
            return True

        print(f"[FullyAuto] Project path not found: {abs_path}")
        return False

    def _generate_autoexec_macro(self, params: Dict[str, float], export_path: str, iter_num: int) -> str:
        """
        生成一个完全自动执行的宏
        这个宏会：
        1. 更新参数
        2. 重建模型
        3. 运行仿真
        4. 导出 S11
        5. 写完成标志
        6. 关闭 CST（可选，为了连续迭代）
        """
        macro_file = self.work_dir / f"autoexec_{iter_num}.mcr"
        
        # 构建参数代码
        param_code = []
        for name, value in params.items():
            if name.startswith("_") or name in ["project_path", "targets"]:
                continue
            if isinstance(value, (int, float)):
                param_code.append(f'    StoreDoubleParameter "{name}", CDbl({value})')
        
        params_vba = "\n".join(param_code) if param_code else "    ' No parameters"
        
        abs_export_path = str(Path(export_path).resolve())
        vba_export_path = abs_export_path.replace("\\", "\\\\")
        flag_path = (abs_export_path + ".done").replace("\\", "\\\\")
        
        # 完全自动执行的宏
        vba_code = f'''\' CST FULLY AUTOMATIC EXECUTION - Iteration {iter_num}
\' This macro runs automatically when CST starts
\' NO USER INTERACTION REQUIRED

Sub Main()
    On Error Resume Next
    
    Dim proj As Object, solver As Object, results As Object
    Dim fso As Object, flagFile As Object
    Dim exportSuccess As Boolean
    Dim startTime As Double
    
    exportSuccess = False
    startTime = Timer
    
    Debug.Print "[AUTO] === Starting Automatic Execution {iter_num} ==="
    
    \' Get project
    Set proj = GetProject()
    If proj Is Nothing Then
        Debug.Print "[AUTO] ERROR: Cannot get project"
        WriteStatus "FAILED", "Cannot get project"
        Exit Sub
    End If
    
    \' Step 1: Parameters
    Debug.Print "[AUTO] Step 1: Setting parameters..."
{params_vba}
    If Err.Number <> 0 Then
        WriteStatus "FAILED", "Parameter error: " & Err.Description
        Exit Sub
    End If
    
    \' Step 2: Rebuild
    Debug.Print "[AUTO] Step 2: Rebuilding..."
    Err.Clear
    proj.Rebuild
    DoEvents  \' Allow UI update
    If Err.Number <> 0 Then
        WriteStatus "FAILED", "Rebuild error: " & Err.Description
        Exit Sub
    End If
    Debug.Print "[AUTO] Rebuild OK"
    
    \' Step 3: Run simulation
    Debug.Print "[AUTO] Step 3: Running simulation..."
    Set solver = proj.GetSolver()
    If solver Is Nothing Then
        WriteStatus "FAILED", "Cannot get solver"
        Exit Sub
    End If
    
    Err.Clear
    solver.Start
    If Err.Number <> 0 Then
        WriteStatus "FAILED", "Solver start error: " & Err.Description
        Exit Sub
    End If
    
    \' Wait with progress
    Debug.Print "[AUTO] Waiting for simulation..."
    Dim waitCount As Integer
    waitCount = 0
    Do While solver.IsSimulating
        Sleep 2000
        waitCount = waitCount + 2
        Debug.Print "[AUTO] Running... " & waitCount & "s"
        \' Timeout after 30 minutes
        If waitCount > 1800 Then
            WriteStatus "FAILED", "Simulation timeout (>30min)"
            Exit Sub
        End If
    Loop
    Debug.Print "[AUTO] Simulation completed!"
    
    \' Step 4: Export S11
    Debug.Print "[AUTO] Step 4: Exporting S11..."
    Set results = proj.GetResultsInTree()
    If results Is Nothing Then
        WriteStatus "FAILED", "No results"
        Exit Sub
    End If
    
    Debug.Print "[AUTO] Found " & results.Count & " results"
    
    Dim i As Integer
    Dim item As Object
    Dim itemName As String
    
    For i = 0 To results.Count - 1
        Set item = results.Item(i)
        If Not item Is Nothing Then
            itemName = item.GetName()
            If InStr(itemName, "S1,1") > 0 Or InStr(itemName, "S11") > 0 Or _
               InStr(itemName, "S-Parameter") > 0 Or InStr(itemName, "S Parameter") > 0 Then
                
                Debug.Print "[AUTO] Exporting: " & itemName
                Err.Clear
                item.ExportCurve "default", "{vba_export_path}", True
                
                If Err.Number = 0 Then
                    exportSuccess = True
                    Debug.Print "[AUTO] Export OK"
                Else
                    Debug.Print "[AUTO] Export failed: " & Err.Description
                End If
                Exit For
            End If
        End If
    Next
    
    If Not exportSuccess Then
        WriteStatus "FAILED", "S11 not found or export failed"
        Exit Sub
    End If
    
    \' Step 5: Write completion flag
    Debug.Print "[AUTO] Step 5: Writing status..."
    WriteStatus "SUCCESS", "Iteration {iter_num} completed"
    
    Debug.Print "[AUTO] === Execution Complete ==="
    
    \' Optional: Close CST for next iteration
    \' Uncomment the next line if you want CST to close after each iteration
    \' Quit
    
End Sub

Sub WriteStatus(status As String, msg As String)
    On Error Resume Next
    Dim fso As Object, ts As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile("{flag_path}", True)
    ts.WriteLine status & ": " & msg
    ts.WriteLine "Time: " & Now
    ts.Close
End Sub

Sub Sleep(ms As Long)
    Dim endTime As Double
    endTime = Timer + ms / 1000
    Do While Timer < endTime
        DoEvents
    Loop
End Sub

Sub Quit()
    On Error Resume Next
    Application.Quit
End Sub
'''
        
        macro_file.write_text(vba_code, encoding="utf-8")
        return str(macro_file)

    def set_parameters(self, params: Dict[str, float]) -> bool:
        """Generate macro and prepare for execution"""
        self.current_iteration += 1
        iter_num = self.current_iteration
        
        export_file = self.work_dir / f"s11_iter_{iter_num}.txt"
        flag_file = Path(str(export_file) + ".done")
        
        # Clean up old flag file
        if flag_file.exists():
            flag_file.unlink()
        
        # Generate auto-execution macro
        macro_file = self._generate_autoexec_macro(params, str(export_file), iter_num)
        macro_file_abs = str(Path(macro_file).resolve())
        
        print(f"\n[FullyAuto] Iteration {iter_num} prepared:")
        print(f"  Macro: {macro_file_abs}")
        print(f"  Expected S11: {export_file}")
        
        # Build command line - try different methods
        
        # Method 1: Direct command line with macro
        # CST supports: CST.exe <project> -macro <macro>
        cmd = [
            str(self.cst_exe),
            str(self.project_path),
            "-macro",
            macro_file_abs
        ]
        
        print(f"\n[FullyAuto] Launching CST with auto-execution...")
        print(f"  Command: {' '.join(cmd)}")
        
        try:
            # Launch with new console so we can see debug output
            self.cst_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(Path(self.project_path).resolve().parent)
            )
            print(f"[FullyAuto] CST started (PID: {self.cst_process.pid})")
            return True
            
        except Exception as e:
            print(f"[FullyAuto] Failed to start CST: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        """Wait for automatic completion"""
        if not self.cst_process:
            print("[FullyAuto] No CST process")
            return False
        
        if not wait_complete:
            return True
        
        print(f"\n[FullyAuto] Waiting for auto-completion (timeout: {timeout}s)...")
        
        export_file = self.work_dir / f"s11_iter_{self.current_iteration}.txt"
        flag_file = Path(str(export_file) + ".done")
        
        start_time = time.time()
        last_status = ""
        
        while time.time() - start_time < timeout:
            # Check flag file
            if flag_file.exists():
                try:
                    with open(flag_file, 'r') as f:
                        content = f.read().strip()
                    lines = content.split('\n')
                    status_line = lines[0] if lines else ""
                    
                    if status_line.startswith("SUCCESS"):
                        print(f"[FullyAuto] SUCCESS detected!")
                        return True
                    elif status_line.startswith("FAILED"):
                        error_msg = status_line.split(":", 1)[1].strip() if ":" in status_line else "Unknown"
                        print(f"[FullyAuto] FAILED: {error_msg}")
                        return False
                        
                except Exception as e:
                    pass
            
            # Check if process ended
            ret = self.cst_process.poll()
            if ret is not None:
                print(f"[FullyAuto] CST process ended (code: {ret})")
                # Check if results were created before exiting
                if flag_file.exists():
                    return True
                if export_file.exists() and export_file.stat().st_size > 0:
                    print(f"[FullyAuto] S11 file found after exit")
                    return True
                return False
            
            # Show progress every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                status_msg = f"Running {elapsed}s..."
                if status_msg != last_status:
                    print(f"  [FullyAuto] {status_msg}")
                    last_status = status_msg
                    
                    # Check file sizes
                    if export_file.exists():
                        size = export_file.stat().st_size
                        print(f"    S11 file: {size} bytes")
            
            time.sleep(1)
        
        print("[FullyAuto] TIMEOUT!")
        return False

    def get_s11_parameters(self) -> Dict[str, Any]:
        """Read S11 results"""
        export_file = self.work_dir / f"s11_iter_{self.current_iteration}.txt"
        
        # Wait up to 30 seconds for file
        for i in range(30):
            if export_file.exists():
                size = export_file.stat().st_size
                if size > 0:
                    break
            time.sleep(1)
        
        if not export_file.exists():
            return {
                "success": False,
                "message": "S11 file not created",
                "frequencies_GHz": [],
                "s11_dB": [],
            }
        
        return self._parse_s11(str(export_file))

    def _parse_s11(self, file_path: str) -> Dict[str, Any]:
        """Parse S11 file"""
        freqs, s11_db = [], []
        
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(("#", "!")):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            freqs.append(float(parts[0]))
                            s11_db.append(float(parts[1]))
                        except:
                            continue
            
            if freqs:
                min_idx = s11_db.index(min(s11_db))
                within_10db = [f for f, s in zip(freqs, s11_db) if s <= -10.0]
                bw = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0
                
                return {
                    "success": True,
                    "message": "S11 parsed successfully",
                    "frequencies_GHz": freqs,
                    "s11_dB": s11_db,
                    "s11_min_dB": round(s11_db[min_idx], 3),
                    "freq_at_min_GHz": round(freqs[min_idx], 3),
                    "bandwidth_10dB_MHz": round(bw, 1),
                }
        except:
            pass
        
        return {
            "success": False,
            "message": "Failed to parse S11 file",
            "frequencies_GHz": [],
            "s11_dB": [],
        }

    def save_project(self, new_path: Optional[str] = None) -> bool:
        """Auto-save not implemented in batch mode"""
        return True

    def close(self):
        """Cleanup"""
        if self.cst_process and self.cst_process.poll() is None:
            try:
                self.cst_process.terminate()
                self.cst_process.wait(timeout=5)
            except:
                try:
                    self.cst_process.kill()
                except:
                    pass
        print(f"[FullyAuto] Cleanup complete")


# Compatibility
from scripts.cst_controller import FakeCSTController
