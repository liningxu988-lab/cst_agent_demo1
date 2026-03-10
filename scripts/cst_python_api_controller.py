"""
CST Python API Controller
使用 CST 官方 Python 接口控制 CST Studio Suite 2024
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CSTPythonAPIController:
    """
    使用 CST 官方 Python API 控制 CST

    工作原理：
    1. 添加 CST Python 库路径到 sys.path
    2. 使用 cst.interface.studio.DesignEnvironment 连接 CST
    3. 通过官方 API 控制参数、仿真和结果读取
    """

    def __init__(
        self,
        cst_install_path: Optional[str] = None,
        preferred_s11_tree_path: str = "",
        allow_proxy_curve: bool = False,
        radiation_mapping: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 CST Python API 控制器

        Args:
            cst_install_path: CST 安装路径，默认自动查找
        """
        self.cst_install_path = cst_install_path or self._find_cst_install()
        self.cst_libs_path = Path(self.cst_install_path) / "AMD64" / "python_cst_libraries"
        self.de = None  # DesignEnvironment instance
        self.project = None  # Current project
        self._api_available = False
        self.project_file = ""
        self.design_targets: Dict[str, float] = {}
        self.preferred_s11_tree_path = preferred_s11_tree_path or ""
        self.allow_proxy_curve = allow_proxy_curve
        self.requested_result_channels: List[str] = ["s_params"]
        self.port_plan: Dict[str, Any] = {}
        self.solver_plan: Dict[str, Any] = {}
        self.radiation_mapping = radiation_mapping or {}
        self.preferred_radiation_tree_paths: List[str] = list(self.radiation_mapping.get("preferred_tree_paths", []))
        self.radiation_fallback_keywords: List[str] = list(
            self.radiation_mapping.get(
                "fallback_keywords",
                ["farfield", "far field", "gain", "directivity", "radiation", "pattern"],
            )
        )
        self.radiation_primary_metric: str = str(self.radiation_mapping.get("primary_metric", "peak_gain_dBi"))
        self.radiation_axis_unit: str = str(self.radiation_mapping.get("axis_unit", "deg"))
        self.last_cst_error: Dict[str, Any] = {}

    def _record_error(self, stage: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """记录 CST 操作失败时的错误信息，供 AI 分析修复。"""
        self.last_cst_error = {
            "stage": stage,
            "message": message,
            "details": details or {},
            "cst_report": self._read_cst_logs(),
        }

    def _read_cst_logs(self) -> Dict[str, str]:
        """读取 CST 工程中的日志与输出文件，供 AI 分析错误原因。"""
        out: Dict[str, str] = {}
        project_file = self.project_file or self._project_filename()
        if not project_file:
            return out
        unpacked = Path(project_file).with_suffix("")
        candidates = [
            ("output_txt", unpacked / "Result" / "output.txt"),
            ("model_log", unpacked / "Result" / "Model.log"),
            ("model_mss", unpacked / "Result" / "Model.mss"),
        ]
        for key, path in candidates:
            if path.exists():
                try:
                    txt = path.read_text(encoding="utf-8", errors="ignore")
                    out[key] = txt[-8000:] if len(txt) > 8000 else txt
                except Exception:
                    out[key] = "(read failed)"
        return out

    def get_cst_error_report(self) -> Dict[str, Any]:
        """获取完整的 CST 错误报告，用于交给 AI 分析并决定修复方案。"""
        report = dict(self.last_cst_error)
        if not report.get("cst_report"):
            report["cst_report"] = self._read_cst_logs()
        return report

    def _find_cst_install(self) -> str:
        """自动查找 CST 安装路径"""
        common_paths = [
            r"D:\Program Files (x86)\CST Studio Suite 2024",
            r"C:\Program Files (x86)\CST Studio Suite 2024",
            r"D:\CST Studio Suite 2024",
            r"C:\CST Studio Suite 2024",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path
        raise FileNotFoundError("CST Studio Suite 2024 not found")

    def _setup_python_path(self) -> bool:
        """设置 Python 路径以导入 CST 库"""
        try:
            # 检查 Python 版本兼容性
            py_version = sys.version_info
            print(f"[PythonAPI] Current Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")

            # CST 支持的 Python 版本
            supported_versions = [(3, 6), (3, 7), (3, 8), (3, 9), (3, 10), (3, 11)]
            current_version = (py_version.major, py_version.minor)

            if current_version not in supported_versions:
                print(f"[PythonAPI] ERROR: Python {py_version.major}.{py_version.minor} is not supported by CST 2024")
                print(f"[PythonAPI] Supported versions: 3.6, 3.7, 3.8, 3.9, 3.10, 3.11")
                print(f"[PythonAPI] Please install a compatible Python version or use 'file' mode")
                return False

            # 添加 CST Python 库到 sys.path
            cst_lib_path = str(self.cst_libs_path)
            if cst_lib_path not in sys.path:
                sys.path.insert(0, cst_lib_path)
                print(f"[PythonAPI] Added to Python path: {cst_lib_path}")

            # 检查是否可以导入 cst 模块
            try:
                import cst
                print(f"[PythonAPI] Successfully imported cst module from {cst.__file__}")
                self._api_available = True
                return True
            except ImportError as e:
                print(f"[PythonAPI] Cannot import cst module: {e}")
                return False

        except Exception as e:
            print(f"[PythonAPI] Error setting up Python path: {e}")
            return False

    def connect(self) -> bool:
        """
        连接到 CST Design Environment

        返回:
            是否成功连接
        """
        # 首先设置 Python 路径
        if not self._setup_python_path():
            print("[PythonAPI] Failed to setup Python path")
            return False

        try:
            from cst.interface import studio

            # 尝试连接到一个运行的 CST 实例
            print("[PythonAPI] Connecting to CST...")

            try:
                # 方法 1: 连接到任意一个运行的 CST（官方高层封装）
                self.de = studio.DesignEnvironment.connect_to_any()
                print("[PythonAPI] Connected to running CST instance")
                return True
            except Exception as e1:
                err_str = str(e1)
                print(f"[PythonAPI] connect_to_any failed: {e1}")

                try:
                    # 方法 2: 连接到任意一个或启动新的（官方高层封装）
                    self.de = studio.DesignEnvironment.connect_to_any_or_new()
                    print("[PythonAPI] Connected to CST (new or existing)")
                    return True
                except Exception as e2:
                    err_str2 = str(e2)
                    print(f"[PythonAPI] connect_to_any_or_new failed: {e2}")

                    # Python 3.11 下部分版本会在 wrapper 的 __class__ 赋值处报 layout differs。
                    # 这里回退到底层 _cst_interface，绕过 wrapper 的类型重绑定。
                    if "layout differs" in err_str or "layout differs" in err_str2:
                        try:
                            from _cst_interface import DesignEnvironment as RawDesignEnvironment

                            try:
                                self.de = RawDesignEnvironment.connect_to_any()
                                print("[PythonAPI] Connected via low-level _cst_interface.connect_to_any")
                                return True
                            except Exception:
                                self.de = RawDesignEnvironment.connect_to_any_or_new()
                                print("[PythonAPI] Connected via low-level _cst_interface.connect_to_any_or_new")
                                return True
                        except Exception as e3:
                            print(f"[PythonAPI] Low-level fallback failed: {e3}")
                    return False

        except Exception as e:
            print(f"[PythonAPI] Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def open_project(self, project_path: str) -> bool:
        """
        打开 CST 项目

        Args:
            project_path: 项目路径（文件夹）

        返回:
            是否成功打开
        """
        if not self.de:
            if not self.connect():
                return False

        try:
            abs_path = Path(project_path).resolve()

            # Resolve folder-like input to a .cst file when possible.
            if abs_path.is_dir():
                sibling_cst = abs_path.with_suffix(".cst")
                if sibling_cst.exists():
                    abs_path = sibling_cst
                else:
                    inside = sorted(abs_path.glob("*.cst"))
                    if inside:
                        abs_path = inside[0].resolve()
            elif abs_path.suffix.lower() != ".cst":
                sibling_cst = abs_path.with_suffix(".cst")
                if sibling_cst.exists():
                    abs_path = sibling_cst

            print(f"[PythonAPI] Opening project: {abs_path}")

            # 尝试打开项目
            try:
                self.project = self.de.open_project(str(abs_path))
                self.project_file = str(abs_path)
                filename_attr = getattr(self.project, "filename", None)
                if callable(filename_attr):
                    filename_attr = filename_attr()
                    if filename_attr:
                        self.project_file = str(filename_attr)
                print(f"[PythonAPI] Successfully opened project: {filename_attr or abs_path}")
                return True
            except Exception as e:
                print(f"[PythonAPI] open_project failed: {e}")

                # 如果打开失败，尝试获取当前活动项目
                try:
                    self.project = self.de.active_project()
                    if self.project:
                        filename_attr = getattr(self.project, "filename", None)
                        if callable(filename_attr):
                            filename_attr = filename_attr()
                        if filename_attr:
                            self.project_file = str(filename_attr)
                        print(f"[PythonAPI] Using active project: {filename_attr or 'active project'}")
                        return True
                except Exception as e2:
                    print(f"[PythonAPI] active_project also failed: {e2}")
                    return False

        except Exception as e:
            print(f"[PythonAPI] Error opening project: {e}")
            return False

    def set_parameters(self, params: Dict[str, float]) -> bool:
        """
        设置项目参数

        Args:
            params: 参数字典

        返回:
            是否成功设置
        """
        if not self.project:
            print("[PythonAPI] No project open")
            return False

        try:
            print("[PythonAPI] Setting parameters...")

            ok, needs_recover = self._apply_parameters_once(params)
            if ok:
                return True

            if needs_recover:
                print("[PythonAPI] Detected busy/broken session, trying reconnect+reopen once...")
                if self._recover_connection():
                    ok2, _ = self._apply_parameters_once(params)
                    return ok2
            self._record_error("parameter_set", "设置参数或重建模型失败", {"params": dict(params)})
            return False

        except Exception as e:
            self._record_error("parameter_set", str(e), {"params": dict(params)})
            print(f"[PythonAPI] Error setting parameters: {e}")
            return False

    def _apply_parameters_once(self, params: Dict[str, float]) -> Tuple[bool, bool]:
        """Apply params and rebuild once. Returns (success, needs_recover)."""
        model3d = self.project.model3d
        self._ensure_solver_idle(model3d)

        failed = False
        needs_recover = False

        for name, value in params.items():
            # 跳过非数值参数
            if name.startswith("_") or name in ["project_path", "targets"]:
                continue
            if isinstance(value, (int, float)):
                try:
                    vba_code = f'"{name}", {value}'
                    model3d._execute_vba_code(f'Sub Main\nStoreDoubleParameter {vba_code}\nEnd Sub')
                    print(f"  [PythonAPI] Set {name} = {value}")
                except Exception as e:
                    failed = True
                    msg = str(e)
                    if "solver is running" in msg.lower() or "connection has been closed" in msg.lower() or "could not determine destination address" in msg.lower():
                        needs_recover = True
                    print(f"  [PythonAPI] Failed to set {name}: {e}")

        try:
            model3d._execute_vba_code('Sub Main\nRebuild\nEnd Sub')
            print("[PythonAPI] Model rebuilt")
        except Exception as e:
            msg = str(e)
            # Some CST API contexts reject Rebuild due to thread context limits after reconnect.
            # Keep going with updated parameters and let solver run.
            if "wrong thread context" in msg.lower() or "nested macro calls" in msg.lower():
                print(f"[PythonAPI] Rebuild skipped due to CST thread context limitation: {e}")
            else:
                failed = True
            if "solver is running" in msg.lower() or "connection has been closed" in msg.lower() or "could not determine destination address" in msg.lower():
                needs_recover = True
            if failed:
                print(f"[PythonAPI] Rebuild failed: {e}")

        return (not failed), needs_recover

    def _recover_connection(self) -> bool:
        """Reconnect to CST and reopen current project."""
        project_file = self.project_file or self._project_filename()
        try:
            self.close()
        except Exception:
            pass

        if not self.connect():
            print("[PythonAPI] Reconnect failed")
            return False

        if project_file:
            if not self.open_project(project_file):
                print("[PythonAPI] Reopen project failed")
                return False
        return True

    def _ensure_solver_idle(self, model3d) -> None:
        """Best-effort stop of running solver before parameter updates."""
        snippets = [
            "Sub Main\nOn Error Resume Next\nSolver.Abort\nEnd Sub",
            "Sub Main\nOn Error Resume Next\nSolver.Stop\nEnd Sub",
            "Sub Main\nOn Error Resume Next\nWith Solver\n    .Abort\nEnd With\nEnd Sub",
        ]
        for code in snippets:
            try:
                model3d._execute_vba_code(code)
            except Exception:
                pass
        # Give CST a short moment to release the solver state.
        time.sleep(1.0)

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        """
        运行仿真

        Args:
            wait_complete: 是否等待仿真完成
            timeout: 超时时间（秒）

        返回:
            是否成功完成
        """
        if not self.project:
            print("[PythonAPI] No project open")
            return False

        try:
            preflight = self.preflight_check()
            if not preflight.get("success", False):
                msg = preflight.get("message", "unknown")
                self._record_error("preflight", msg, {"preflight": preflight})
                print(f"[PythonAPI] Preflight check failed: {msg}")
                for issue in preflight.get("issues", []):
                    print(f"  [PythonAPI] Issue: {issue}")
                return False

            print("[PythonAPI] Starting simulation...")

            # 固定使用 HF Frequency Domain（简化：仅 S 参数，无 Transient/radiation）
            solver_type = "HF Frequency Domain"
            ai_solver = (self.solver_plan or {}).get("solver_type", "").strip()
            if ai_solver and "frequency" in ai_solver.lower():
                solver_type = ai_solver
                print(f"[PythonAPI] Using solver from AI fix_plan: {solver_type}")
            else:
                print("[PythonAPI] Using HF Frequency Domain solver (S-parameters only)")

            model3d = self.project.model3d
            solver_snippets = [
                f'Sub Main\nChangeSolverType "{solver_type}"\nFDSolver.Start\nEnd Sub',
                f'Sub Main\nChangeSolverType "{solver_type}"\nWith Solver\n    .Start\nEnd With\nEnd Sub',
                f'Sub Main\nChangeSolverType "{solver_type}"\nSolver.Start\nEnd Sub',
            ]

            started = False
            for idx, vba_code in enumerate(solver_snippets, 1):
                try:
                    model3d._execute_vba_code(vba_code)
                    print(f"[PythonAPI] Solver started via VBA variant #{idx}")
                    started = True
                    break
                except Exception as e:
                    print(f"[PythonAPI] Solver variant #{idx} failed: {e}")

            if not started:
                self._record_error("simulation", "求解器启动失败，所有 VBA 变体均失败", {})
                return False

            if wait_complete:
                print("[PythonAPI] Waiting for CST to finish and produce readable results...")

                if not self._wait_for_results_ready(timeout=timeout, channels=self.requested_result_channels):
                    self._record_error("simulation", "等待仿真结果超时或结果未就绪", {"channels": self.requested_result_channels})
                    print("[PythonAPI] Timeout waiting for CST results readiness")
                    return False

                print("[PythonAPI] Simulation finished and results are ready")
                mss_after = self._read_result_solver_type()
                if mss_after:
                    print(f"[PythonAPI] Result solver marker: {mss_after}")

                tree_info = self._list_1d_results()
                if tree_info.get("success"):
                    print(f"[PythonAPI] 1D results detected: {tree_info.get('count', 0)}")
                    for item in tree_info.get("sample_items", []):
                        print(f"  [PythonAPI] Result item: {item}")
                else:
                    print(f"[PythonAPI] Result tree check failed: {tree_info.get('message')}")
                return True
            else:
                print("[PythonAPI] Simulation started (not waiting)")
                return True

        except Exception as e:
            self._record_error("simulation", str(e), {})
            print(f"[PythonAPI] Simulation error: {e}")
            return False

    def _wait_for_results_ready(
        self,
        timeout: int = 600,
        poll_interval: float = 3.0,
        channels: Optional[List[str]] = None,
    ) -> bool:
        """
        Wait until CST finishes and S-parameter results are readable.
        This prevents reading results too early while solver is still running.
        """
        start = time.time()
        next_log = start

        requested = channels or ["s_params"]

        while time.time() - start < timeout:
            s_ok = True
            s_msg = "ok"

            if "s_params" in requested:
                s11_probe = self._read_s11_from_project_results(verbose=False)
                s_ok = bool(s11_probe.get("success"))
                s_msg = s11_probe.get("message", "s_params not ready")

            if s_ok:
                return True

            now = time.time()
            if now >= next_log:
                elapsed = int(now - start)
                print(f"  [PythonAPI] Waiting... {elapsed}s (s_params={s_msg})")
                next_log = now + 10

            time.sleep(poll_interval)

        return False

    def _read_result_solver_type(self) -> str:
        """Read solver type marker from unpacked project result files."""
        try:
            project_file = self.project_file or self._project_filename()
            if not project_file:
                return ""
            mss = Path(project_file).with_suffix("") / "Result" / "Model.mss"
            if not mss.exists():
                return ""
            txt = mss.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"Solver type\s*\r?\n([^\r\n]+)", txt, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
            return ""
        except Exception:
            return ""

    def set_design_targets(self, targets: Dict[str, float]) -> None:
        """Store design targets for preflight validation."""
        self.design_targets = targets or {}

    def set_result_channels(self, channels: List[str]) -> None:
        """Set requested result channels for readiness checks."""
        if channels:
            self.requested_result_channels = channels

    def set_port_plan(self, port_plan: Dict[str, Any]) -> None:
        """设置激励端口计划（由 AI 决定），仿真前会应用。"""
        self.port_plan = port_plan or {}

    def set_solver_plan(self, plan: Dict[str, Any]) -> None:
        """设置求解器计划（由 AI 的 solver_hint 注入），仿真前会优先使用。"""
        self.solver_plan = plan or {}

    def apply_structure_plan(self, structure_plan: Dict[str, Any]) -> bool:
        """
        根据 AI 的 structure_plan 创建/更新 CST 几何结构。
        plan: { "structure_type": "single_pec"|"three_layer", "params": {...} }
        """
        if not self.project or not structure_plan:
            return False
        try:
            from scripts.structure_builder import build_structure_vba
            vba = build_structure_vba(structure_plan)
            if not vba:
                return False
            model3d = self.project.model3d
            self._ensure_solver_idle(model3d)
            model3d._execute_vba_code(vba)
            print(f"[Structure] Applied: {structure_plan.get('structure_type', 'unknown')}")
            return True
        except Exception as e:
            print(f"[Structure] Apply failed: {e}")
            return False

    def apply_kiko_setup(self, freq_center_ghz: float, freq_min_ghz: Optional[float] = None, freq_max_ghz: Optional[float] = None) -> bool:
        """
        应用 Kiko 反射单元固定建模条件：Background、Boundaries（FloquetPort，unit cell，open）、zmax=λ/2、求解频率。
        """
        if not self.project:
            print("[PythonAPI] No project for Kiko setup")
            return False
        try:
            from scripts.kiko_config import zmax_from_freq_ghz, background_vba, boundaries_vba, unit_cell_boundaries_vba

            fmin = freq_min_ghz if freq_min_ghz is not None else max(0.1, freq_center_ghz - 0.5)
            fmax = freq_max_ghz if freq_max_ghz is not None else freq_center_ghz + 0.5
            zmax_mm = zmax_from_freq_ghz(freq_center_ghz)
            model3d = self.project.model3d
            model3d._execute_vba_code(f'Sub Main\nStoreDoubleParameter "zmax", {zmax_mm}\nEnd Sub')
            print(f"[Kiko] zmax = {zmax_mm:.2f} mm (λ/2 @ {freq_center_ghz} GHz)")
            model3d._execute_vba_code(unit_cell_boundaries_vba())
            print("[Kiko] Boundaries: x/y unit cell, z open")
            model3d._execute_vba_code(background_vba(zmax_mm))
            print("[Kiko] Background applied")
            model3d._execute_vba_code(boundaries_vba())
            print("[Kiko] FloquetPort applied")
            model3d._execute_vba_code(f'Sub Main\nSolver.FrequencyRange "{fmin}", "{fmax}"\nEnd Sub')
            print(f"[Kiko] Solver frequency: {fmin}-{fmax} GHz")
            return True
        except Exception as e:
            print(f"[Kiko] Setup failed: {e}")
            return False

    def _ensure_farfield_monitor(self, domain: str = "time", freq_ghz: float = 2.45) -> bool:
        """
        在求解前确保存在远场监视器。
        domain: "time" 用于 Transient（宽带远场），"frequency" 用于 HF FD（单频远场）。
        """
        if domain == "frequency":
            vba = (
                'Sub Main\n'
                'On Error Resume Next\n'
                'Monitor.Delete ("farfield_auto")\n'
                'On Error GoTo 0\n'
                'With Monitor\n'
                '    .Reset\n'
                '    .Name ("farfield_auto")\n'
                '    .FieldType ("Farfield")\n'
                '    .Domain ("frequency")\n'
                f'    .Frequency ({freq_ghz})\n'
                '    .Create\n'
                'End With\n'
                'End Sub'
            )
            label = f"frequency domain at {freq_ghz} GHz"
        else:
            vba = (
                'Sub Main\n'
                'On Error Resume Next\n'
                'Monitor.Delete ("farfield_auto")\n'
                'On Error GoTo 0\n'
                'With Monitor\n'
                '    .Reset\n'
                '    .Name ("farfield_auto")\n'
                '    .FieldType ("Farfield")\n'
                '    .Domain ("time")\n'
                '    .Create\n'
                'End With\n'
                'End Sub'
            )
            label = "time domain broadband"
        try:
            model3d = self.project.model3d
            model3d._execute_vba_code(vba)
            print(f"[PythonAPI] Farfield monitor created ({label})")
            return True
        except Exception as e:
            print(f"[PythonAPI] Farfield monitor create failed (may already exist): {e}")
            return False

    def _apply_port_plan(self, port_plan: Dict[str, Any]) -> bool:
        """
        应用 waveguide port 设置（由 AI 决定）。
        port_plan 结构: { "orientation": "zmin", "coordinates": "Free"|"Full",
          "xrange": [min,max], "yrange": [min,max], "zrange": [min,max],
          "number_of_modes": 1, "label": "port1" }
        """
        wp = port_plan.get("waveguide_port", port_plan) if isinstance(port_plan, dict) else {}
        if not wp:
            return False
        ori = str(wp.get("orientation", "zmin"))
        coords = str(wp.get("coordinates", "Full"))
        modes = int(wp.get("number_of_modes", 1))
        label = str(wp.get("label", "port_auto"))

        if coords == "Free":
            xr = wp.get("xrange", [0, 0])
            yr = wp.get("yrange", [0, 0])
            zr = wp.get("zrange", [0, 0])
            xmin, xmax = float(xr[0]), float(xr[1]) if len(xr) > 1 else 0.0
            ymin, ymax = float(yr[0]), float(yr[1]) if len(yr) > 1 else 0.0
            zmin, zmax = float(zr[0]), float(zr[1]) if len(zr) > 1 else 0.0
            vba = (
                'Sub Main\n'
                'On Error Resume Next\n'
                'Port.Delete "1"\n'
                'On Error GoTo 0\n'
                'With Port\n'
                '    .Reset\n'
                '    .PortNumber "1"\n'
                f'    .Label "{label}"\n'
                f'    .NumberOfModes {modes}\n'
                f'    .Orientation "{ori}"\n'
                f'    .Coordinates "Free"\n'
                f'    .Xrange "{xmin}", "{xmax}"\n'
                f'    .Yrange "{ymin}", "{ymax}"\n'
                f'    .Zrange "{zmin}", "{zmax}"\n'
                '    .Create\n'
                'End With\n'
                'End Sub'
            )
        else:
            vba = (
                'Sub Main\n'
                'On Error Resume Next\n'
                'Port.Delete "1"\n'
                'On Error GoTo 0\n'
                'With Port\n'
                '    .Reset\n'
                '    .PortNumber "1"\n'
                f'    .Label "{label}"\n'
                f'    .NumberOfModes {modes}\n'
                f'    .Orientation "{ori}"\n'
                '    .Coordinates "Full"\n'
                '    .Create\n'
                'End With\n'
                'End Sub'
            )
        try:
            model3d = self.project.model3d
            model3d._execute_vba_code(vba)
            print(f"[PythonAPI] Waveguide port applied: orientation={ori}, coordinates={coords}")
            return True
        except Exception as e:
            print(f"[PythonAPI] Port apply failed: {e}")
            return False

    def preflight_check(self) -> Dict[str, Any]:
        """Validate key CST setup items before simulation."""
        info = {
            "success": True,
            "message": "Preflight checks passed",
            "issues": [],
            "warnings": [],
            "detected": {},
        }

        project_file = self.project_file or self._project_filename()
        if not project_file:
            info["success"] = False
            info["message"] = "Cannot determine project file for preflight checks"
            info["issues"].append("Project filename is empty")
            return info

        unpacked_dir = Path(project_file).with_suffix("")
        model_mod = unpacked_dir / "Model" / "3D" / "Model.mod"
        model_history = unpacked_dir / "Model" / "3D" / "ModelHistory.json"
        result_output = unpacked_dir / "Result" / "output.txt"

        solver_type = ""
        boundary_has_unit_cell = False
        freq_min = None
        freq_max = None

        # Parse Model.mod (most direct source for solver/boundary/frequency commands).
        if model_mod.exists():
            txt = model_mod.read_text(encoding="utf-8", errors="ignore")
            m_solver = re.search(r'ChangeSolverType\s+"([^"]+)"', txt, flags=re.IGNORECASE)
            if m_solver:
                solver_type = m_solver.group(1).strip()

            m_freq = re.search(r'Solver\.FrequencyRange\s+"([^"]+)"\s*,\s*"([^"]+)"', txt, flags=re.IGNORECASE)
            if m_freq:
                try:
                    freq_min = float(m_freq.group(1))
                    freq_max = float(m_freq.group(2))
                except ValueError:
                    pass

            boundary_has_unit_cell = bool(re.search(r'\.(Xmin|Xmax|Ymin|Ymax)\s+"unit cell"', txt, flags=re.IGNORECASE))

        # Fallback to ModelHistory.json for frequency range.
        if (freq_min is None or freq_max is None) and model_history.exists():
            try:
                hist = json.loads(model_history.read_text(encoding="utf-8", errors="ignore"))
                general_freq = (hist.get("general", {}) or {}).get("frequency", {})
                freq_min = float(general_freq.get("minimum")) if general_freq.get("minimum") is not None else freq_min
                freq_max = float(general_freq.get("maximum")) if general_freq.get("maximum") is not None else freq_max
            except Exception:
                pass

        info["detected"] = {
            "project_file": project_file,
            "solver_type": solver_type or "unknown",
            "boundary_has_unit_cell": boundary_has_unit_cell,
            "frequency_range_GHz": [freq_min, freq_max],
        }

        # Frequency range check against design targets (if provided).
        tgt_min = self.design_targets.get("freq_min_GHz")
        tgt_max = self.design_targets.get("freq_max_GHz")
        if freq_min is not None and freq_max is not None and tgt_min is not None and tgt_max is not None:
            if freq_max < float(tgt_min) or freq_min > float(tgt_max):
                info["success"] = False
                info["issues"].append(
                    f"Project frequency range {freq_min}-{freq_max} GHz does not overlap target {tgt_min}-{tgt_max} GHz"
                )
            elif freq_min > float(tgt_min) or freq_max < float(tgt_max):
                info["warnings"].append(
                    f"Project frequency range {freq_min}-{freq_max} GHz does not fully cover target {tgt_min}-{tgt_max} GHz"
                )

        if not info["success"]:
            info["message"] = "Preflight failed: incompatible CST setup"
        elif info["warnings"]:
            info["message"] = "Preflight passed with warnings"

        print("[PythonAPI] Preflight detected settings:")
        print(f"  [PythonAPI] Solver type: {info['detected']['solver_type']}")
        print(f"  [PythonAPI] Unit Cell boundary: {info['detected']['boundary_has_unit_cell']}")
        print(f"  [PythonAPI] Frequency range (GHz): {info['detected']['frequency_range_GHz']}")
        for w in info["warnings"]:
            print(f"  [PythonAPI] Warning: {w}")

        return info

    def get_s11_parameters(self) -> Dict[str, Any]:
        """
        读取 S11 参数（兼容接口，内部调用 get_s_parameters_full 提取 S11）
        """
        if not self.project:
            return {
                "success": False,
                "message": "No project open",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

        full = self.get_s_parameters_full()
        if not full.get("success"):
            return {
                "success": False,
                "message": full.get("message", "S-parameters unavailable"),
                "frequencies_GHz": [],
                "s11_dB": [],
            }
        s11_ch = full.get("channels", {}).get("S11", {})
        summary = full.get("summary", {})
        return {
            "success": True,
            "message": full.get("message", "S11 from full S-params"),
            "frequencies_GHz": s11_ch.get("frequencies_GHz", []),
            "s11_dB": s11_ch.get("magnitude_dB", []),
            "s11_min_dB": summary.get("s11_min_dB"),
            "freq_at_min_GHz": summary.get("freq_at_min_GHz"),
            "bandwidth_10dB_MHz": summary.get("bandwidth_10dB_MHz"),
        }

    def _parse_s_param_path_to_key(self, path: str) -> Optional[str]:
        """Parse CST S-parameter tree path to Sij key (e.g. S11, S12, S21, S22)."""
        s = path.lower()
        # SZmax(1),Zmax(2) or SZmin(1),Zmin(2) -> S12
        m = re.search(r"sz\w*\((\d+)\)\s*,\s*z\w*\((\d+)\)", s)
        if m:
            return f"S{m.group(1)}{m.group(2)}"
        # S1,1 or S1,2
        m = re.search(r"s(\d+)\s*,\s*(\d+)", s)
        if m:
            return f"S{m.group(1)}{m.group(2)}"
        # S[1,1]
        m = re.search(r"s\[(\d+)\s*,\s*(\d+)\]", s)
        if m:
            return f"S{m.group(1)}{m.group(2)}"
        return None

    def _read_all_s_params_from_project(self, verbose: bool = True) -> Dict[str, Any]:
        """Read all S-parameters (S11, S12, S21, S22, ...) from CST project 1D results."""
        try:
            import cst.results as cst_results

            project_file = self._project_filename()
            if not project_file:
                return {
                    "success": False,
                    "message": "Cannot determine project filename",
                    "channels": {},
                    "summary": {},
                }

            pf = cst_results.ProjectFile(project_file, allow_interactive=True)
            module_3d = pf.get_3d()
            tree_items = list(module_3d.get_tree_items())

            # Collect S-parameter paths with their Sij keys
            s_param_paths: List[Tuple[str, str]] = []
            for item in tree_items:
                s = item.lower()
                if "s-parameter" not in s and "s parameters" not in s and "sparameters" not in s:
                    continue
                if "meshcells" in s or ("adaptive meshing" in s and "s-parameters" not in s):
                    continue
                if "all s-parameters" in s or "delta" in s:
                    continue
                key = self._parse_s_param_path_to_key(item)
                if key:
                    s_param_paths.append((key, item))

            # Deduplicate by key (prefer preferred path for S11)
            seen: Dict[str, str] = {}
            for key, path in s_param_paths:
                if key not in seen:
                    seen[key] = path
                elif key == "S11" and self.preferred_s11_tree_path and path.lower() == self.preferred_s11_tree_path.lower():
                    seen[key] = path

            if not seen:
                return {
                    "success": False,
                    "message": "No S-parameter curves found in project",
                    "channels": {},
                    "summary": {},
                }

            if verbose:
                print(f"[PythonAPI] Found S-parameter curves: {list(seen.keys())}")

            channels: Dict[str, Dict[str, Any]] = {}
            s11_min_dB = None
            freq_at_min_GHz = None
            bandwidth_10dB_MHz = None

            for key, tree_path in seen.items():
                try:
                    result_item = module_3d.get_result_item(tree_path)
                    x = list(result_item.get_xdata())
                    y = list(result_item.get_ydata())
                    if not x or not y or len(x) < 3:
                        continue
                    mag_db = self._normalize_to_db(y)
                    channels[key] = {
                        "frequencies_GHz": [float(v) for v in x],
                        "magnitude_dB": [float(v) for v in mag_db],
                        "phase_deg": [],
                    }
                    if key == "S11":
                        min_idx = mag_db.index(min(mag_db))
                        s11_min_dB = round(float(mag_db[min_idx]), 3)
                        freq_at_min_GHz = round(float(x[min_idx]), 3)
                        within_10db = [f for f, s in zip(x, mag_db) if s <= -10.0]
                        bandwidth_10dB_MHz = round((max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0, 1)
                except Exception as e:
                    if verbose:
                        print(f"[PythonAPI] Skip {key} ({tree_path}): {e}")
                    continue

            if not channels:
                return {
                    "success": False,
                    "message": "S-parameter paths found but none readable",
                    "channels": {},
                    "summary": {},
                }

            summary = {}
            if s11_min_dB is not None:
                summary["s11_min_dB"] = s11_min_dB
            if freq_at_min_GHz is not None:
                summary["freq_at_min_GHz"] = freq_at_min_GHz
            if bandwidth_10dB_MHz is not None:
                summary["bandwidth_10dB_MHz"] = bandwidth_10dB_MHz

            return {
                "success": True,
                "message": f"S-parameters from project: {list(channels.keys())}",
                "channels": channels,
                "summary": summary,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Read all S-params failed: {e}",
                "channels": {},
                "summary": {},
            }

    def get_s_parameters_full(self) -> Dict[str, Any]:
        """Read all S-parameters (S11, S12, S21, S22, ...) from result tree and return to AI."""
        if not self.project:
            return {
                "success": False,
                "message": "No project open",
                "channels": {},
                "summary": {},
            }

        try:
            print("[PythonAPI] Reading all S-parameters...")
            full = self._read_all_s_params_from_project(verbose=True)
            if full.get("success"):
                return full
            # Fallback to S11-only
            s11 = self._read_s11_from_project_results(verbose=True)
            if s11.get("success"):
                return {
                    "success": True,
                    "message": s11.get("message", "S11 only (fallback)"),
                    "channels": {
                        "S11": {
                            "frequencies_GHz": s11.get("frequencies_GHz", []),
                            "magnitude_dB": s11.get("s11_dB", []),
                            "phase_deg": [],
                        }
                    },
                    "summary": {
                        "s11_min_dB": s11.get("s11_min_dB"),
                        "freq_at_min_GHz": s11.get("freq_at_min_GHz"),
                        "bandwidth_10dB_MHz": s11.get("bandwidth_10dB_MHz"),
                    },
                }
            return full
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "channels": {},
                "summary": {},
            }

    def get_radiation_metrics(self, verbose: bool = True) -> Dict[str, Any]:
        """Best-effort read of radiation-pattern related curves/metrics."""
        try:
            import cst.results as cst_results

            project_file = self._project_filename()
            if not project_file:
                return {"success": False, "message": "No project filename"}

            pf = cst_results.ProjectFile(project_file, allow_interactive=True)
            module_3d = pf.get_3d()
            items = list(module_3d.get_tree_items())

            attempted_paths: List[str] = []
            rad_candidates = self._build_radiation_candidates(items)
            if verbose and rad_candidates:
                print(f"[PythonAPI] Radiation candidates: {', '.join(rad_candidates[:5])}")

            if not rad_candidates:
                return {"success": False, "message": "No radiation-pattern curves found", "attempted_paths": attempted_paths}

            for path in rad_candidates:
                attempted_paths.append(path)
                try:
                    item = module_3d.get_result_item(path)
                    x = [float(v) for v in item.get_xdata()]
                    y = [float(v) for v in item.get_ydata()]
                    if len(x) < 3 or len(y) < 3:
                        continue
                    y_max = max(y)
                    y_min = min(y)
                    idx_max = y.index(y_max)
                    return {
                        "success": True,
                        "message": f"Radiation data from: {path}",
                        "path": path,
                        "peak_value_dB": float(y_max),
                        "min_value_dB": float(y_min),
                        "peak_at_axis": float(x[idx_max]),
                        "axis_unit": self.radiation_axis_unit,
                        "primary_metric": self.radiation_primary_metric,
                        "metric_summary": {
                            "primary_metric": self.radiation_primary_metric,
                            "peak_value_dB": float(y_max),
                            "peak_at_axis": float(x[idx_max]),
                            "axis_unit": self.radiation_axis_unit,
                        },
                        "axis_samples": x,
                        "values_dB": y,
                    }
                except Exception:
                    continue

            return {
                "success": False,
                "message": "Radiation candidates exist but none parseable",
                "attempted_paths": attempted_paths,
            }
        except Exception as e:
            return {"success": False, "message": f"Radiation read failed: {e}"}

    def _build_radiation_candidates(self, tree_items: List[str]) -> List[str]:
        """Build prioritized radiation candidate paths: preferred -> mapped keywords -> defaults."""
        preferred = []
        if self.preferred_radiation_tree_paths:
            item_map = {p.lower(): p for p in tree_items}
            for path in self.preferred_radiation_tree_paths:
                found = item_map.get(path.lower())
                if found:
                    preferred.append(found)

        keyword_hits = []
        for p in tree_items:
            lp = p.lower()
            if any(k.lower() in lp for k in self.radiation_fallback_keywords):
                keyword_hits.append(p)

        default_hits = [
            p for p in tree_items
            if any(k in p.lower() for k in ["farfield", "far field", "gain", "directivity", "radiation", "pattern"])
        ]

        # Stable dedup while preserving priority order.
        out: List[str] = []
        seen = set()
        for p in preferred + keyword_hits + default_hits:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def _project_filename(self) -> str:
        """Get current project filename safely."""
        filename_attr = getattr(self.project, "filename", None)
        if callable(filename_attr):
            return str(filename_attr() or "")
        return str(filename_attr or "")

    def _list_1d_results(self) -> Dict[str, Any]:
        """List available 1D result tree items from project."""
        try:
            import cst.results as cst_results

            project_file = self._project_filename()
            if not project_file:
                return {"success": False, "message": "No project filename", "count": 0, "items": []}

            pf = cst_results.ProjectFile(project_file, allow_interactive=True)
            module_3d = pf.get_3d()
            items = list(module_3d.get_tree_items())
            return {
                "success": True,
                "message": "OK",
                "count": len(items),
                "items": items,
                "sample_items": items[:10],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Result tree read failed: {e}",
                "count": 0,
                "items": [],
            }

    def _read_s11_from_project_results(self, verbose: bool = True) -> Dict[str, Any]:
        """Try reading S11 directly from CST project 1D results."""
        try:
            import cst.results as cst_results

            project_file = self._project_filename()

            if not project_file:
                return {
                    "success": False,
                    "message": "Cannot determine project filename for results API",
                    "frequencies_GHz": [],
                    "s11_dB": [],
                }

            pf = cst_results.ProjectFile(project_file, allow_interactive=True)
            module_3d = pf.get_3d()
            tree_items = module_3d.get_tree_items()

            # Common S11 tree path patterns in CST (with stronger ranking for reflection terms).
            scored = []
            for item in tree_items:
                s = item.lower()
                score = 0
                if self.preferred_s11_tree_path and s == self.preferred_s11_tree_path.lower():
                    score += 1000
                if "s-parameter" in s or "s parameters" in s or "sparameters" in s:
                    score += 40
                if "s1,1" in s or "s11" in s:
                    score += 220
                if "szmax(1),zmax(1)" in s or "szmin(1),zmin(1)" in s:
                    score += 200
                if ("s(" in s and ",1)" in s) or ("s[1,1]" in s):
                    score += 120
                if "all s-parameters" in s or "\\delta\\" in s or "delta" in s:
                    score -= 120
                if "meshcells" in s or "adaptive meshing" in s and "s-parameters" not in s:
                    score -= 200
                if "db" in s:
                    score += 5
                if score > 0:
                    scored.append((score, item))

            if not scored:
                return {
                    "success": False,
                    "message": "No S11/S-Parameter 1D result found in project",
                    "frequencies_GHz": [],
                    "s11_dB": [],
                }

            scored.sort(key=lambda x: x[0], reverse=True)
            if verbose:
                preview = ", ".join([f"{p[1]}(score={p[0]})" for p in scored[:5]])
                print(f"[PythonAPI] Top S-parameter candidates: {preview}")

            last_err = "No usable S-parameter curve"
            for _, tree_path in scored[:25]:
                try:
                    result_item = module_3d.get_result_item(tree_path)
                    x = list(result_item.get_xdata())
                    y = list(result_item.get_ydata())
                    if not x or not y:
                        last_err = f"Empty curve: {tree_path}"
                        continue
                    if len(x) < 3:
                        last_err = f"Too few points ({len(x)}): {tree_path}"
                        continue

                    s11_db = self._normalize_to_db(y)
                    min_idx = s11_db.index(min(s11_db))
                    within_10db = [f for f, s in zip(x, s11_db) if s <= -10.0]
                    bandwidth = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0

                    return {
                        "success": True,
                        "message": f"S11 data from project results API: {tree_path}",
                        "frequencies_GHz": [float(v) for v in x],
                        "s11_dB": [float(v) for v in s11_db],
                        "s11_min_dB": round(float(s11_db[min_idx]), 3),
                        "freq_at_min_GHz": round(float(x[min_idx]), 3),
                        "bandwidth_10dB_MHz": round(float(bandwidth), 1),
                    }
                except Exception as inner_e:
                    last_err = f"{tree_path}: {inner_e}"
                    continue

            return {
                "success": False,
                "message": f"S-parameter candidates found but none usable: {last_err}",
                "frequencies_GHz": [],
                "s11_dB": [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Results API read failed: {e}",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

    def _normalize_to_db(self, y_values: List[float]) -> List[float]:
        """Normalize Y values to dB-like values."""
        mags = []
        for v in y_values:
            try:
                if isinstance(v, complex):
                    mags.append(abs(v))
                else:
                    # Some CST result APIs may return numeric-like strings or scalar wrappers.
                    fv = float(v)
                    mags.append(abs(fv))
            except Exception:
                try:
                    cv = complex(v)
                    mags.append(abs(cv))
                except Exception:
                    # Unparseable point: treat as very small magnitude.
                    mags.append(0.0)

        # If values already look like dB (mostly negative and not tiny linear magnitudes), keep as-is.
        # This can happen when returned values are scalar reals already in dB.
        if mags and min(mags) < -1.0 and max(mags) < 20.0:
            return mags

        import math
        db_vals = []
        for mag in mags:
            if mag <= 0:
                db_vals.append(-200.0)
            else:
                db_vals.append(20.0 * math.log10(mag))
        return db_vals

    def _read_any_1d_curve_as_s11_proxy(self) -> Dict[str, Any]:
        """Fallback: use any available 1D curve as proxy to keep loop alive."""
        try:
            import cst.results as cst_results

            project_file = self._project_filename()
            if not project_file:
                return {
                    "success": False,
                    "message": "No project filename",
                    "frequencies_GHz": [],
                    "s11_dB": [],
                }

            pf = cst_results.ProjectFile(project_file, allow_interactive=True)
            module_3d = pf.get_3d()
            tree_items = list(module_3d.get_tree_items())
            if not tree_items:
                return {
                    "success": False,
                    "message": "No 1D result items found",
                    "frequencies_GHz": [],
                    "s11_dB": [],
                }

            for tree_path in tree_items:
                try:
                    item = module_3d.get_result_item(tree_path)
                    x = [float(v) for v in item.get_xdata()]
                    y = [float(v) for v in item.get_ydata()]
                    if len(x) < 3 or len(y) < 3:
                        continue

                    s11_db = self._normalize_to_db(y)
                    min_idx = s11_db.index(min(s11_db))
                    within_10db = [f for f, s in zip(x, s11_db) if s <= -10.0]
                    bandwidth = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0

                    return {
                        "success": True,
                        "message": f"Proxy 1D curve used (non-S11): {tree_path}",
                        "frequencies_GHz": x,
                        "s11_dB": s11_db,
                        "s11_min_dB": round(float(s11_db[min_idx]), 3),
                        "freq_at_min_GHz": round(float(x[min_idx]), 3),
                        "bandwidth_10dB_MHz": round(float(bandwidth), 1),
                    }
                except Exception:
                    continue

            return {
                "success": False,
                "message": "No parseable 1D curve found",
                "frequencies_GHz": [],
                "s11_dB": [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Any-curve fallback failed: {e}",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

    def _parse_touchstone(self, file_path: str) -> Dict[str, Any]:
        """解析 Touchstone 文件"""
        freqs = []
        s11_db = []

        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("!") or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) >= 3:  # freq, mag, phase (DB format)
                        try:
                            freq_ghz = float(parts[0])
                            mag_db = float(parts[1])
                            freqs.append(freq_ghz)
                            s11_db.append(mag_db)
                        except ValueError:
                            continue

            if not freqs:
                return {
                    "success": False,
                    "message": "No valid data in Touchstone file",
                    "frequencies_GHz": [],
                    "s11_dB": [],
                }

            # 计算指标
            min_idx = s11_db.index(min(s11_db))
            s11_min = s11_db[min_idx]
            freq_at_min = freqs[min_idx]

            # 计算 10dB 带宽
            within_10db = [f for f, s in zip(freqs, s11_db) if s <= -10.0]
            bandwidth = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0

            return {
                "success": True,
                "message": "S11 data from Touchstone export",
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
        """保存项目"""
        if not self.project:
            print("[PythonAPI] No project open")
            return False

        try:
            if new_path:
                # 另存为
                self.de.save_project(str(new_path))
                print(f"[PythonAPI] Project saved to: {new_path}")
            else:
                # 保存当前项目
                self.project.save()
                print("[PythonAPI] Project saved")
            return True
        except Exception as e:
            print(f"[PythonAPI] Save failed: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.de:
            try:
                self.de.close()
                print("[PythonAPI] Connection closed")
            except Exception as e:
                print(f"[PythonAPI] Error closing: {e}")
            self.de = None
        self.project = None


def test_controller():
    """测试控制器"""
    print("=" * 60)
    print("Testing CST Python API Controller")
    print("=" * 60)

    ctrl = CSTPythonAPIController()

    if ctrl.connect():
        print("\nConnection successful!")

        # 尝试打开项目
        if ctrl.open_project("templates/antenna_template"):
            print("\nProject opened!")

            # 设置参数
            ctrl.set_parameters({"patch_length": 12.0, "patch_width": 10.0})

            # 读取 S11
            s11 = ctrl.get_s11_parameters()
            print("\nS11 Data:")
            print(json.dumps(s11, indent=2))

        ctrl.close()
    else:
        print("\nConnection failed!")


if __name__ == "__main__":
    test_controller()
