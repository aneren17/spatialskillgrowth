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


def workflow_catalog_markdown(workflows) -> str:
    lines = [
        WORKFLOW_CATALOG_START,
        "## 可选工作流",
        "",
        "根据当前输入选择下列工作流；详细参数按需读取对应资源。",
        "",
    ]
    if not workflows:
        lines.extend([
            "当前没有可检索工作流。",
            WORKFLOW_CATALOG_END,
            "",
        ])
        return "\n".join(lines)

    for workflow in sorted(workflows, key=lambda item: item.workflow_id):
        applicability = workflow.applicability
        tool_chain = " -> ".join(
            step.tool_name for step in workflow.steps
        )
        lines.extend([
            "### " + (workflow.name or workflow.workflow_id),
            "",
            "- ID：`" + workflow.workflow_id + "`",
            "- 选择条件：" + (applicability.description or "未说明"),
            "- 不选择：" + (applicability.exclusions or "未说明"),
            "- 执行边界：" + (
                applicability.capability_boundary or "未说明"
            ),
            "- 工具链：`" + (tool_chain or "无") + "`",
            "- 资源：`references/workflows/"
            + workflow.workflow_id
            + ".json`；`scripts/"
            + workflow.workflow_id
            + ".py`",
            "",
        ])
    lines.extend([WORKFLOW_CATALOG_END, ""])
    return "\n".join(lines)


def replace_workflow_catalog(
    skill_markdown: str,
    workflow_catalog: str,
) -> str:
    start = skill_markdown.find(WORKFLOW_CATALOG_START)
    end = skill_markdown.find(WORKFLOW_CATALOG_END)
    if start >= 0 and end > start:
        end += len(WORKFLOW_CATALOG_END)
        prefix = skill_markdown[:start].rstrip()
        suffix = skill_markdown[end:].lstrip()
        output = prefix + "\n\n" + workflow_catalog.rstrip() + "\n"
        if suffix:
            output += "\n" + suffix.rstrip() + "\n"
        return output
    return skill_markdown.rstrip() + "\n\n" + workflow_catalog.rstrip() + "\n"
