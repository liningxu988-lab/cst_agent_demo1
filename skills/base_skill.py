"""
Skill 基类。
领域能力以 Skill 插件形式组织，复用已有 tools。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkillMeta:
    """Skill 元信息"""
    name: str
    description: str
    tools: List[str]
    scenarios: List[str]
    version: str = "0.1.0"


class BaseSkill(ABC):
    """
    Skill 基类。
    子类需实现 run()，内部复用 tools，不重复实现底层逻辑。
    """

    meta: SkillMeta = None

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path(__file__).parent

    @property
    def name(self) -> str:
        return self.meta.name if self.meta else "unknown"

    @property
    def description(self) -> str:
        return self.meta.description if self.meta else ""

    @property
    def tools(self) -> List[str]:
        return self.meta.tools if self.meta else []

    @property
    def scenarios(self) -> List[str]:
        return self.meta.scenarios if self.meta else []

    def load_prompt(self) -> str:
        """加载 prompt.md"""
        path = self.root / "prompt.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def load_schemas(self) -> Dict[str, Any]:
        """加载 schemas.json"""
        path = self.root / "schemas.json"
        if path.exists():
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    @abstractmethod
    def run(self, context: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        执行 Skill。
        context 含 tool_registry、task_state 等。
        返回结构化结果。
        """
        raise NotImplementedError
