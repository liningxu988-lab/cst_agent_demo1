"""
CST Batch Controller - Fully Automated
Launch CST and execute macros automatically
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class CSTBatchController:
    """
    Fully automated CST controller using batch scripts
    """

    def __init__(self, cst_install_path: Optional[str] = None):
        self.cst_install_path = cst_install_path or self._find_cst_install()
        self.cst_exe = Path(self.cst_install_path) / "CST DESIGN ENVIRONMENT.exe"
        self.work_dir = Path("outputs/cst_batch")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.current_iteration = 0
        self.cst_process = None

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
            print(f"[Batch] CST not found: {self.cst_exe}")
            return False
        print(f"[Batch] CST found: {self.cst_exe}")
        return True

    def open_project(self, project_path: str) -> bool:
        """Record project path"""
        abs_path = Path(project_path).resolve()
        if abs_path.exists():
            self.project_path = str(abs_path)
            print(f"[Batch] Project: {self.project_path}")
            return True
        return False

    def set_parameters(self, params: Dict[str, float]) -> bool:
        """Generate and launch batch script"""
        self.current_iteration += 1
        iter_num = self.current_iteration

        export_file = self.work_dir / f"s11_iter_{iter_num}.txt"
        macro_file, batch_file = self._generate_files(params, str(export_file), iter_num)

        print(f"\n[Batch] Generated:")
        print(f"  Macro: {macro_file}")
        print(f"  Batch: {batch_file}")

        # Launch batch script
        print(f"\n[Batch] Launching CST automatically...")
        try:
            self.cst_process = subprocess.Popen(
                [str(batch_file)],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"[Batch] CST started (PID: {self.cst_process.pid})")
            return True
        except Exception as e:
            print(f"[Batch] Failed to start: {e}")
            return False

    def _generate_files(self, params: Dict[str, float], export_path: str, iter_num: int) -> tuple:
        """Generate macro and batch files"""
        macro_file = self.work_dir / f"auto_run_{iter_num}.mcr"

        # Build parameter code
        param_code = []
        for name, value in params.items():
            if name.startswith("_") or name in ["project_path", "targets"]:
                continue
            if isinstance(value, (int, float)):
                param_code.append(f'    StoreDoubleParameter "{name}", {value}')

        params_vba = "\n".join(param_code) if param_code else "    ' No parameters"
        vba_export_path = export_path.replace("\\", "\\\\")

        vba_code = f'''\' CST Auto Run - Iteration {iter_num}
Sub Main()
    On Error Resume Next
    Dim proj As Object, solver As Object, results As Object
    Dim exportSuccess As Boolean
    exportSuccess = False

    Set proj = GetProject()
    If proj Is Nothing Then
        MsgBox "Error: Cannot access project!", vbCritical
        Exit Sub
    End If

    Debug.Print "[{iter_num}] Updating parameters..."
{params_vba}

    Debug.Print "[{iter_num}] Rebuilding..."
    proj.Rebuild

    Debug.Print "[{iter_num}] Starting simulation..."
    Set solver = proj.GetSolver()
    If Not solver Is Nothing Then
        solver.Start
        Do While solver.IsSimulating
            Sleep 1000
        Loop
        Debug.Print "[{iter_num}] Simulation done"

        Debug.Print "[{iter_num}] Exporting S11..."
        Set results = proj.GetResultsInTree()
        Dim i As Integer
        For i = 0 To results.Count - 1
            Dim item As Object
            Set item = results.Item(i)
            If Not item Is Nothing Then
                Dim itemName As String
                itemName = item.GetName()
                If InStr(itemName, "S1,1") > 0 Or InStr(itemName, "S11") > 0 Then
                    item.ExportCurve "default", "{vba_export_path}", True
                    exportSuccess = True
                    Exit For
                End If
            End If
        Next
    End If

    Dim fso As Object, flagFile As Object
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set flagFile = fso.CreateTextFile("{vba_export_path}.done", True)
    flagFile.WriteLine "Iteration {iter_num} completed"
    flagFile.Close

    If exportSuccess Then
        MsgBox "Iteration {iter_num} completed!", vbInformation
    Else
        MsgBox "Iteration {iter_num} done, export may have failed", vbExclamation
    End If
End Sub

Sub Sleep(milliseconds As Long)
    Dim endTime As Double
    endTime = Timer + milliseconds / 1000
    Do While Timer < endTime
        DoEvents
    Loop
End Sub
'''

        macro_file.write_text(vba_code, encoding="utf-8")

        # Generate batch file
        batch_file = self.work_dir / f"run_iteration_{iter_num}.bat"
        batch_content = f'''@echo off
echo Starting CST Auto Run - Iteration {iter_num}
echo.
echo Opening CST with macro...
"{self.cst_exe}" "{self.project_path}" -macro "{macro_file}"
echo.
echo CST launched. Check progress in CST window.
'''
        batch_file.write_text(batch_content, encoding="utf-8")

        return str(macro_file), str(batch_file)

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        """Wait for completion"""
        if not self.cst_process:
            return False

        if wait_complete:
            print(f"\n[Batch] Waiting for completion (timeout: {timeout}s)...")
            export_file = self.work_dir / f"s11_iter_{self.current_iteration}.txt"
            flag_file = Path(str(export_file) + ".done")

            start_time = time.time()
            while time.time() - start_time < timeout:
                if flag_file.exists():
                    print(f"[Batch] Completion detected!")
                    return True
                ret = self.cst_process.poll()
                if ret is not None:
                    print(f"[Batch] Process exited: {ret}")
                    return True
                time.sleep(2)
                print("  [Batch] Waiting...")

            print("[Batch] Timeout")
            return False
        return True

    def get_s11_parameters(self) -> Dict[str, Any]:
        """Read S11 results"""
        export_file = self.work_dir / f"s11_iter_{self.current_iteration}.txt"

        # Wait for file
        for _ in range(60):
            if export_file.exists():
                break
            time.sleep(1)

        if export_file.exists():
            return self._parse_s11(str(export_file))

        return {
            "success": False,
            "message": "S11 file not found",
            "frequencies_GHz": [],
            "s11_dB": [],
        }

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
                        except ValueError:
                            continue

            if freqs:
                min_idx = s11_db.index(min(s11_db))
                within_10db = [f for f, s in zip(freqs, s11_db) if s <= -10.0]
                bw = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0
                return {
                    "success": True,
                    "message": "S11 loaded",
                    "frequencies_GHz": freqs,
                    "s11_dB": s11_db,
                    "s11_min_dB": round(s11_db[min_idx], 3),
                    "freq_at_min_GHz": round(freqs[min_idx], 3),
                    "bandwidth_10dB_MHz": round(bw, 1),
                }
        except Exception:
            pass

        return {
            "success": False,
            "message": "Parse error",
            "frequencies_GHz": [],
            "s11_dB": [],
        }

    def save_project(self, new_path: Optional[str] = None) -> bool:
        print("[Batch] Please save manually in CST if needed")
        return True

    def close(self):
        if self.cst_process and self.cst_process.poll() is None:
            try:
                self.cst_process.terminate()
            except:
                pass
        print(f"[Batch] Work files: {self.work_dir}")
