"""
CST Studio Suite COM 接口控制器
通过 Python COM 接口自动化控制 CST，从内存读取仿真结果
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CSTController:
    """CST Studio Suite 控制器（基于 COM 接口）"""

    def __init__(self, cst_exe_path: Optional[str] = None):
        """
        初始化 CST 控制器

        Args:
            cst_exe_path: CST 可执行文件路径，默认自动查找
        """
        self.cst_exe_path = cst_exe_path or self._find_cst_exe()
        self.cst = None  # CST 应用对象
        self.project = None  # 当前项目对象
        self._com_loaded = False

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
        raise FileNotFoundError("未找到 CST 安装，请手动指定 cst_exe_path")

    def _ensure_com(self):
        """确保 COM 接口已加载"""
        if self._com_loaded:
            return

        try:
            import win32com.client
            self.win32com = win32com.client
            self._com_loaded = True
        except ImportError:
            raise RuntimeError(
                "需要安装 pywin32 库来使用 COM 接口:\n"
                "pip install pywin32"
            )

    def connect(self) -> bool:
        """
        连接到已运行的 CST 实例

        Returns:
            是否成功连接
        """
        self._ensure_com()

        # 首先尝试连接已运行的 CST 实例
        try:
            self.cst = self.win32com.GetActiveObject("CSTStudio.Application")
            print("已连接到运行中的 CST 实例")
            return True
        except Exception as e:
            print(f"未找到运行中的 CST: {e}")
            print("请先手动启动 CST Studio Suite 并打开模板项目")
            print(f"项目路径: {self.cst_exe_path}")
            return False

    def open_project(self, project_path: str) -> bool:
        """
        打开 CST 项目 - 使用已打开的项目

        如果项目已经在 CST 中打开，直接使用当前项目
        否则尝试通过 COM 接口打开
        """
        if not self.cst:
            if not self.connect():
                return False

        try:
            # 转换为绝对路径
            abs_path = Path(project_path).resolve()
            print(f"项目绝对路径: {abs_path}")

            # 方法1: 尝试获取当前已打开的项目
            try:
                current_project = self.cst.GetActiveProject()
                if current_project:
                    proj_path = current_project.GetProjectPath()
                    print(f"CST 中当前已打开的项目: {proj_path}")

                    # 检查是否是我们想要的项目
                    if str(abs_path) in proj_path or proj_path in str(abs_path):
                        self.project = current_project
                        print("使用 CST 中当前已打开的项目")
                        return True
            except Exception as e:
                print(f"获取当前项目失败: {e}")

            # 方法2: 尝试通过 OpenProject 打开
            try:
                print(f"尝试通过 OpenProject 打开: {abs_path}")
                self.project = self.cst.OpenProject(str(abs_path))
                if self.project:
                    print(f"成功打开项目: {abs_path}")
                    return True
            except Exception as e:
                print(f"OpenProject 失败: {e}")

            # 方法3: 尝试找到 .cst 文件
            if abs_path.is_dir():
                cst_files = list(abs_path.glob("*.cst"))
                if cst_files:
                    cst_file = str(cst_files[0])
                    print(f"尝试打开 .cst 文件: {cst_file}")
                    try:
                        self.project = self.cst.OpenProject(cst_file)
                        if self.project:
                            print(f"成功打开项目: {cst_file}")
                            return True
                    except Exception as e:
                        print(f"打开 .cst 文件失败: {e}")

            print("无法通过 COM 接口打开项目")
            print("请确保在 CST 中已经手动打开了正确的项目")
            return False

        except Exception as e:
            print(f"打开项目时发生错误: {e}")
            return False

    def set_parameters(self, params: Dict[str, float]) -> bool:
        """
        设置项目参数（结构参数）

        Args:
            params: 参数字典，如 {"patch_length": 12.0, "patch_width": 10.0}

        Returns:
            是否成功设置
        """
        if not self.project:
            print("错误: 未打开项目")
            return False

        try:
            for name, value in params.items():
                self.project.StoreDoubleParameter(name, float(value))
                print(f"  设置参数 {name} = {value}")

            # 重建模型
            self.project.Rebuild()
            print("模型已重建")
            return True
        except Exception as e:
            print(f"设置参数失败: {e}")
            return False

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        """
        运行仿真

        Args:
            wait_complete: 是否等待仿真完成
            timeout: 超时时间（秒）

        Returns:
            是否成功完成仿真
        """
        if not self.project:
            print("错误: 未打开项目")
            return False

        try:
            # 启动仿真器
            simulator = self.project.GetSimulator()
            print("启动仿真...")

            # 开始仿真
            simulator.Start()

            if wait_complete:
                print(f"等待仿真完成（超时: {timeout}秒）...")
                start_time = time.time()
                while time.time() - start_time < timeout:
                    status = simulator.IsSimulating()
                    if not status:
                        print("仿真完成")
                        return True
                    time.sleep(2)
                    print("  仿真中...")

                print("仿真超时")
                return False
            else:
                print("仿真已启动，不等待完成")
                return True

        except Exception as e:
            print(f"运行仿真失败: {e}")
            return False

    def get_s11_parameters(self) -> Dict[str, Any]:
        """
        从内存中读取 S11 参数

        Returns:
            {
                "frequencies_GHz": List[float],  # 频率点列表
                "s11_dB": List[float],  # S11 幅度（dB）
                "s11_min_dB": float,  # 最小 S11 值
                "freq_at_min_GHz": float,  # 最小值对应的频率
                "bandwidth_10dB_MHz": float,  # 10dB 带宽
                "success": bool,
                "message": str,
            }
        """
        if not self.project:
            return {
                "success": False,
                "message": "未打开项目",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

        try:
            # 获取结果对象
            results = self.project.GetResultsInTree()

            # 查找 S 参数结果
            s_params_found = False
            freqs = []
            s11_values = []

            for i in range(results.Count()):
                result_item = results.Item(i)
                name = result_item.GetName()

                # 查找 S 参数相关的 1D 结果
                if "S-Parameters" in name or "S11" in name or "1D" in name:
                    try:
                        # 获取结果数据
                        result_1d = result_item.Get1DResult("dB")
                        if result_1d:
                            # 提取频率和幅度数据
                            freqs = list(result_1d.GetArray("x"))  # 频率
                            s11_values = list(result_1d.GetArray("y"))  # S11 in dB
                            s_params_found = True
                            print(f"找到 S 参数结果: {name}")
                            break
                    except Exception as e:
                        print(f"读取结果 {name} 失败: {e}")
                        continue

            if not s_params_found:
                # 尝试其他方式获取 S 参数
                return self._get_s11_alternative()

            # 计算关键指标
            return self._analyze_s11_data(freqs, s11_values)

        except Exception as e:
            return {
                "success": False,
                "message": f"读取 S 参数失败: {e}",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

    def _get_s11_alternative(self) -> Dict[str, Any]:
        """替代方法：通过 ASCII 导出再读取（内存操作，不保存到磁盘）"""
        try:
            # 尝试通过 ASCII 导出获取数据
            export_path = r"C:\Temp\cst_s11_export.tmp"

            # 使用 VBA 宏导出数据
            vba_code = f'''
            Sub Main
                Dim sTree As Object
                Set sTree = Resulttree.GetResultTreeView()
                sTree.ExportCurve "1D Results\\S-Parameters\\S1,1", "{export_path}", True
            End Sub
            '''

            self.project.RunVBACode(vba_code)
            time.sleep(1)  # 等待导出完成

            # 读取导出的数据
            if Path(export_path).exists():
                freqs, s11_values = self._parse_ascii_export(export_path)
                Path(export_path).unlink()  # 删除临时文件

                if freqs and s11_values:
                    return self._analyze_s11_data(freqs, s11_values)

            return {
                "success": False,
                "message": "无法通过 ASCII 导出获取 S 参数",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"替代方法失败: {e}",
                "frequencies_GHz": [],
                "s11_dB": [],
            }

    def _parse_ascii_export(self, file_path: str) -> Tuple[List[float], List[float]]:
        """解析 ASCII 导出的数据文件"""
        freqs = []
        values = []

        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        freq = float(parts[0])
                        val = float(parts[1])
                        freqs.append(freq)
                        values.append(val)
                    except ValueError:
                        continue

        return freqs, values

    def _analyze_s11_data(
        self, freqs: List[float], s11_db: List[float]
    ) -> Dict[str, Any]:
        """分析 S11 数据，提取关键指标"""
        if not freqs or not s11_db or len(freqs) != len(s11_db):
            return {
                "success": False,
                "message": "S11 数据为空或格式错误",
                "frequencies_GHz": freqs,
                "s11_dB": s11_db,
            }

        # 找到最小 S11（最佳匹配点）
        min_idx = s11_db.index(min(s11_db))
        s11_min = s11_db[min_idx]
        freq_at_min = freqs[min_idx]

        # 计算 10dB 带宽
        bandwidth_10db = self._calculate_bandwidth(freqs, s11_db, -10.0)

        return {
            "success": True,
            "message": "成功读取 S11 参数",
            "frequencies_GHz": freqs,
            "s11_dB": s11_db,
            "s11_min_dB": round(s11_min, 3),
            "freq_at_min_GHz": round(freq_at_min, 3),
            "bandwidth_10dB_MHz": round(bandwidth_10db, 1),
        }

    def _calculate_bandwidth(
        self, freqs: List[float], s11_db: List[float], threshold: float
    ) -> float:
        """计算指定阈值下的带宽（MHz）"""
        within_threshold = [f for f, s in zip(freqs, s11_db) if s <= threshold]

        if not within_threshold:
            return 0.0

        min_freq = min(within_threshold)
        max_freq = max(within_threshold)
        bandwidth = (max_freq - min_freq) * 1000  # 转换为 MHz

        return bandwidth

    def save_project(self, new_path: Optional[str] = None) -> bool:
        """
        保存项目

        Args:
            new_path: 新路径，None 则保存到原路径

        Returns:
            是否成功保存
        """
        if not self.project:
            print("错误: 未打开项目")
            return False

        try:
            if new_path:
                self.project.SaveAs(str(new_path))
                print(f"项目已另存为: {new_path}")
            else:
                self.project.Save()
                print("项目已保存")
            return True
        except Exception as e:
            print(f"保存项目失败: {e}")
            return False

    def close(self):
        """关闭项目并释放资源"""
        if self.project:
            try:
                self.project.Close()
                print("项目已关闭")
            except Exception as e:
                print(f"关闭项目失败: {e}")
            self.project = None

        self.cst = None


class FakeCSTController:
    """假的 CST 控制器（用于测试，不依赖实际 CST）"""

    def __init__(self, cst_exe_path: Optional[str] = None):
        self.cst_exe_path = cst_exe_path
        self._fake_params = {}
        self.last_cst_error: Dict[str, Any] = {}

    def apply_kiko_setup(self, freq_center_ghz: float, freq_min_ghz: Optional[float] = None, freq_max_ghz: Optional[float] = None) -> bool:
        print(f"[FakeCST] Kiko setup: freq_center={freq_center_ghz} GHz")
        return True

    def apply_structure_plan(self, structure_plan: Dict[str, Any]) -> bool:
        print(f"[FakeCST] Structure plan: {structure_plan.get('structure_type', 'unknown')}")
        return True

    def set_design_targets(self, targets: Dict[str, float]) -> None:
        pass

    def set_result_channels(self, channels: List[str]) -> None:
        pass

    def get_cst_error_report(self) -> Dict[str, Any]:
        return dict(self.last_cst_error)

    def connect(self) -> bool:
        print("[FakeCST] 模拟连接成功")
        return True

    def open_project(self, project_path: str) -> bool:
        print(f"[FakeCST] 模拟打开项目: {project_path}")
        return True

    def set_parameters(self, params: Dict[str, float]) -> bool:
        self._fake_params = params.copy()
        print(f"[FakeCST] 设置参数: {params}")
        return True

    def run_simulation(self, wait_complete: bool = True, timeout: int = 600) -> bool:
        print("[FakeCST] 模拟仿真运行（2秒）...")
        time.sleep(2)
        print("[FakeCST] 仿真完成")
        return True

    def get_s_parameters_full(self) -> Dict[str, Any]:
        """基于参数计算模拟的全部 S 参数（S11、S12、S21、S22）"""
        import random

        length = self._fake_params.get("patch_length", 10.0)
        width = self._fake_params.get("patch_width", 8.0)

        freq_center = 3.0 - length * 0.05
        s11_depth = -5.0 - width * 0.4

        freqs = [2.0 + i * 0.01 for i in range(101)]
        s11_values = []
        for f in freqs:
            detune = (f - freq_center) / 0.1
            s11 = s11_depth * (1 / (1 + detune**2)) + random.uniform(-0.5, 0.5)
            s11_values.append(s11)

        min_idx = s11_values.index(min(s11_values))
        s11_min = s11_values[min_idx]
        freq_at_min = freqs[min_idx]
        within_10db = [f for f, s in zip(freqs, s11_values) if s <= -10.0]
        bandwidth = (max(within_10db) - min(within_10db)) * 1000 if within_10db else 0.0

        s12_values = [-30.0 + random.uniform(-1, 1) for _ in freqs]
        s21_values = [-30.0 + random.uniform(-1, 1) for _ in freqs]
        s22_values = [-25.0 + random.uniform(-1, 1) for _ in freqs]

        return {
            "success": True,
            "message": "[FakeCST] 模拟全部 S 参数",
            "channels": {
                "S11": {"frequencies_GHz": freqs, "magnitude_dB": s11_values, "phase_deg": []},
                "S12": {"frequencies_GHz": freqs, "magnitude_dB": s12_values, "phase_deg": []},
                "S21": {"frequencies_GHz": freqs, "magnitude_dB": s21_values, "phase_deg": []},
                "S22": {"frequencies_GHz": freqs, "magnitude_dB": s22_values, "phase_deg": []},
            },
            "summary": {
                "s11_min_dB": round(s11_min, 3),
                "freq_at_min_GHz": round(freq_at_min, 3),
                "bandwidth_10dB_MHz": round(bandwidth, 1),
            },
        }

    def get_s11_parameters(self) -> Dict[str, Any]:
        """兼容接口：从 get_s_parameters_full 提取 S11"""
        full = self.get_s_parameters_full()
        if not full.get("success"):
            return {"success": False, "message": full.get("message", ""), "frequencies_GHz": [], "s11_dB": []}
        s11_ch = full.get("channels", {}).get("S11", {})
        summary = full.get("summary", {})
        return {
            "success": True,
            "message": full.get("message", ""),
            "frequencies_GHz": s11_ch.get("frequencies_GHz", []),
            "s11_dB": s11_ch.get("magnitude_dB", []),
            "s11_min_dB": summary.get("s11_min_dB"),
            "freq_at_min_GHz": summary.get("freq_at_min_GHz"),
            "bandwidth_10dB_MHz": summary.get("bandwidth_10dB_MHz"),
        }

    def save_project(self, new_path: Optional[str] = None) -> bool:
        print(f"[FakeCST] 模拟保存项目: {new_path or '原路径'}")
        return True

    def close(self):
        print("[FakeCST] 模拟关闭")


def quick_test():
    """快速测试控制器"""
    # 使用假控制器进行测试
    ctrl = FakeCSTController()

    if ctrl.connect():
        ctrl.open_project("test.cst")
        ctrl.set_parameters({"patch_length": 12.0, "patch_width": 10.0})
        ctrl.run_simulation()

        result = ctrl.get_s11_parameters()
        print("\nS11 结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        ctrl.close()


if __name__ == "__main__":
    quick_test()
