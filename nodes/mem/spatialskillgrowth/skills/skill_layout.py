"""SpatialSkillGrowth 标准 Skill 目录约定。"""

from __future__ import annotations

import re
from pathlib import Path


REFERENCES_DIR_NAME = "references"
SCRIPTS_DIR_NAME = "scripts"
SKILL_METADATA_FILE = "skill.json"
WORKFLOWS_DIR_NAME = "workflows"
WORKFLOW_CATALOG_START = "<!-- SPATIALSKILLGROWTH_WORKFLOWS_START -->"
WORKFLOW_CATALOG_END = "<!-- SPATIALSKILLGROWTH_WORKFLOWS_END -->"


def standard_skill_name(problem_class: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(problem_class or "").lower())
    value = value.strip("-")
    if not value or len(value) > 64:
        raise ValueError(f"无法生成标准 Skill 名称：{problem_class!r}")
    return value


def skill_directory(root: Path, problem_class: str) -> Path:
    return Path(root) / standard_skill_name(problem_class)


def skill_metadata_path(directory: Path) -> Path:
    return Path(directory) / REFERENCES_DIR_NAME / SKILL_METADATA_FILE


def workflow_reference_directory(directory: Path) -> Path:
    return Path(directory) / REFERENCES_DIR_NAME / WORKFLOWS_DIR_NAME
