"""
Skill 加载器。
从 skills/ 目录加载 Skill 插件。
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base_skill import BaseSkill, SkillMeta


def _ensure_skills_importable() -> None:
    """确保 skills 包可被加载的子模块 import。"""
    root = Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def load_skill_from_dir(skill_dir: Path) -> Optional[BaseSkill]:
    """
    从目录加载 Skill。
    目录需含 skill.py 且定义 Skill 类。
    """
    _ensure_skills_importable()
    skill_py = skill_dir / "skill.py"
    if not skill_py.exists():
        return None

    spec = importlib.util.spec_from_file_location("skill_module", skill_py)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for attr in dir(mod):
        cls = getattr(mod, attr)
        if isinstance(cls, type) and issubclass(cls, BaseSkill) and cls is not BaseSkill:
            return cls(root=skill_dir)
    return None


def load_all_skills(skills_root: Optional[Path] = None) -> Dict[str, BaseSkill]:
    """
    加载 skills 根目录下所有子目录中的 Skill。
    """
    root = skills_root or Path(__file__).parent
    skills: Dict[str, BaseSkill] = {}

    for item in root.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            skill = load_skill_from_dir(item)
            if skill:
                skills[skill.name] = skill
    return skills


def get_skill_by_scenario(skills: Dict[str, BaseSkill], scenario: str) -> Optional[BaseSkill]:
    """按适用场景查找 Skill。"""
    for s in skills.values():
        if scenario in s.scenarios:
            return s
    return None
