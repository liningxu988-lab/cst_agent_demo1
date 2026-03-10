"""
CST 反射单元结构构建器
根据 AI 的 structure_plan 生成 VBA，创建 PEC、介质板等几何结构。
支持：single_pec、three_layer（PEC-介质-PEC）等。
"""

from typing import Any, Dict, List, Optional


def build_structure_vba(plan: Dict[str, Any]) -> Optional[str]:
    """
    根据 structure_plan 生成 CST VBA 宏。
    plan 格式:
    {
      "structure_type": "single_pec" | "three_layer",
      "params": {
        "patch_length": 12, "patch_width": 10,
        "substrate_height": 1.6, "dielectric_er": 4.4, ...
      }
    }
    """
    stype = (plan.get("structure_type") or "single_pec").lower()
    params = plan.get("params") or {}

    patch_length = float(params.get("patch_length", 12.0))
    patch_width = float(params.get("patch_width", 10.0))
    substrate_height = float(params.get("substrate_height", 1.6))
    dielectric_er = float(params.get("dielectric_er", 4.4))
    dielectric_tand = float(params.get("dielectric_tand", 0.02))

    if stype == "single_pec":
        return _vba_single_pec(patch_length, patch_width)
    if stype == "three_layer":
        return _vba_three_layer(patch_length, patch_width, substrate_height, dielectric_er, dielectric_tand)
    return _vba_single_pec(patch_length, patch_width)


def _vba_single_pec(patch_length: float, patch_width: float) -> str:
    """单层 PEC 贴片。"""
    return f'''Sub Main
StoreDoubleParameter "patch_length", {patch_length}
StoreDoubleParameter "patch_width", {patch_width}
Component.Delete "component1"
Component.New "component1"
With Brick
    .Reset
    .Name "solid1"
    .Component "component1"
    .Material "PEC"
    .Xrange "-patch_width/2", "patch_width/2"
    .Yrange "-patch_length/2", "patch_length/2"
    .Zrange "0", "0"
    .Create
End With
Rebuild
End Sub'''


def _vba_three_layer(
    patch_length: float,
    patch_width: float,
    substrate_height: float,
    dielectric_er: float,
    dielectric_tand: float,
) -> str:
    """三层结构：底层 PEC 地板 + 介质基板 + 顶层 PEC 贴片。"""
    mat_name = "Substrate"
    er_str = str(dielectric_er)
    tand_str = str(dielectric_tand)
    return f'''Sub Main
StoreDoubleParameter "patch_length", {patch_length}
StoreDoubleParameter "patch_width", {patch_width}
StoreDoubleParameter "substrate_height", {substrate_height}

' 创建介质材料
With Material
    .Reset
    .Name "{mat_name}"
    .FrqType "all"
    .Type "Normal"
    .MaterialUnit "Frequency", "GHz"
    .MaterialUnit "Geometry", "mm"
    .Epsilon "{er_str}"
    .Mu "1.0"
    .TanD "{tand_str}"
    .Create
End With

' 删除旧组件
On Error Resume Next
Component.Delete "component1"
Component.Delete "component2"
Component.Delete "component3"
On Error GoTo 0

' 底层 PEC 地板
Component.New "component1"
With Brick
    .Reset
    .Name "ground"
    .Component "component1"
    .Material "PEC"
    .Xrange "-patch_width/2", "patch_width/2"
    .Yrange "-patch_length/2", "patch_length/2"
    .Zrange "-substrate_height", "0"
    .Create
End With

' 介质基板
Component.New "component2"
With Brick
    .Reset
    .Name "substrate"
    .Component "component2"
    .Material "{mat_name}"
    .Xrange "-patch_width/2", "patch_width/2"
    .Yrange "-patch_length/2", "patch_length/2"
    .Zrange "0", "substrate_height"
    .Create
End With

' 顶层 PEC 贴片
Component.New "component3"
With Brick
    .Reset
    .Name "patch"
    .Component "component3"
    .Material "PEC"
    .Xrange "-patch_width/2", "patch_width/2"
    .Yrange "-patch_length/2", "patch_length/2"
    .Zrange "substrate_height", "substrate_height"
    .Create
End With

Rebuild
End Sub'''
