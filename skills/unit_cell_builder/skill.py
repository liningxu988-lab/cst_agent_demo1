"""
Unit Cell Builder Skill。
超表面反射单元结构构建，复用 structure_builder 与 set_parameter。
"""

from pathlib import Path
from typing import Any, Dict

from skills.base_skill import BaseSkill, SkillMeta


class UnitCellBuilderSkill(BaseSkill):
    """反射单元结构构建 Skill"""

    meta = SkillMeta(
        name="unit_cell_builder",
        description="超表面反射单元结构构建，支持 single_pec、three_layer 等结构类型",
        tools=["open_project", "set_parameter", "run_solver"],
        scenarios=["reflection_unit", "unit_cell_design", "structure_build"],
    )

    def __init__(self, root: Path = None):
        super().__init__(root or Path(__file__).parent)

    def run(self, context: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        执行结构构建。
        kwargs: structure_plan={structure_type, params}, project_path, ...
        """
        registry = context.get("tool_registry")
        structure_plan = kwargs.get("structure_plan", {})
        project_path = kwargs.get("project_path", "")
        params = (structure_plan.get("params") or {}).copy()
        if not params:
            params = kwargs.get("params", {})

        if not registry:
            return {"success": False, "error": "tool_registry not in context"}

        results = []
        if project_path:
            r = registry.run("open_project", project_path=project_path)
            results.append({"tool": "open_project", "result": r.status.value})
            if r.status.value == "failed":
                return {"success": False, "results": results, "error": r.error}

        r = registry.run("set_parameter", params=params)
        results.append({"tool": "set_parameter", "result": r.status.value})
        if r.status.value == "failed":
            return {"success": False, "results": results, "error": r.error}

        return {"success": True, "results": results, "params_applied": params}
