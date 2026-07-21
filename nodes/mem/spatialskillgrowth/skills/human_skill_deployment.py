"""将通过 mock 校验的人工 Python Skill 部署为可检索 active Workflow。"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec
from nodes.mem.spatialskillgrowth.skills.human_skill_validation import (
    validate_human_skill,
)
from nodes.mem.spatialskillgrowth.skills.skill_layout import (
    replace_workflow_catalog,
    skill_metadata_path,
    workflow_catalog_markdown,
    workflow_reference_directory,
)


HUMAN_AUTHORSHIP = "human"
MANUAL_MUTATION_MODE = "manual"
ACTIVE_STATUS = "active"


def deploy_human_skill(
    skill_dir: Path,
    script_path: Path,
    force: bool = False,
) -> Dict[str, Any]:
    """校验人工脚本，写入 Workflow JSON，并同步 Skill 文档和索引。"""
    skill_dir = Path(skill_dir).resolve()
    script_path = Path(script_path).resolve()
    validation = validate_human_skill(skill_dir, script_path)
    if not validation.get("valid"):
        return {
            "deployed": False,
            "validation": validation,
            "error": "人工 Skill 未通过 mock 校验，未写入任何部署文件。",
        }

    workflow = WorkflowSpec.from_dict(validation["workflow"])
    workflow.status = ACTIVE_STATUS
    workflow.mutation_mode = MANUAL_MUTATION_MODE
    workflow_path = (
        workflow_reference_directory(skill_dir)
        / f"{workflow.workflow_id}.json"
    )
    deployed_script_path = skill_dir / "scripts" / f"{workflow.workflow_id}.py"

    existing_workflow = None
    if workflow_path.is_file():
        existing_workflow = WorkflowSpec.from_dict(
            json.loads(workflow_path.read_text(encoding="utf-8"))
        )
        if (
            not force
            and _workflow_definition(existing_workflow)
            != _workflow_definition(workflow)
        ):
            raise FileExistsError(
                "同 ID Workflow JSON 已存在且契约不同；确认覆盖时使用 --force："
                + str(workflow_path)
            )
        workflow.metrics = existing_workflow.metrics
        workflow.source_task_ids = list(existing_workflow.source_task_ids)

    if (
        deployed_script_path.is_file()
        and deployed_script_path.resolve() != script_path
        and deployed_script_path.read_bytes() != script_path.read_bytes()
        and not force
    ):
        raise FileExistsError(
            "同 ID Python 脚本已存在且内容不同；确认覆盖时使用 --force："
            + str(deployed_script_path)
        )

    deployed_script_path.parent.mkdir(parents=True, exist_ok=True)
    if deployed_script_path.resolve() != script_path:
        shutil.copy2(script_path, deployed_script_path)
    _write_json_atomic(workflow_path, workflow.to_dict())
    workflows = _load_workflows(skill_dir)
    _rebuild_skill_files(skill_dir, workflows)

    return {
        "deployed": True,
        "workflow_id": workflow.workflow_id,
        "problem_class": workflow.applicability.problem_class,
        "status": workflow.status,
        "mutation_mode": workflow.mutation_mode,
        "workflow_path": str(workflow_path),
        "script_path": str(deployed_script_path),
        "preserved_metrics": existing_workflow is not None,
        "validation": {
            "valid": validation["valid"],
            "checks": validation["checks"],
            "errors": validation["errors"],
        },
        "error": "",
    }


def _workflow_definition(workflow: WorkflowSpec) -> Dict[str, Any]:
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "applicability": workflow.applicability.to_dict(),
        "steps": [step.to_dict() for step in workflow.steps],
    }


def _load_workflows(skill_dir: Path) -> List[WorkflowSpec]:
    workflows = []
    seen = set()
    for path in sorted(workflow_reference_directory(skill_dir).glob("*.json")):
        if path.name.endswith(".archive.json"):
            continue
        workflow = WorkflowSpec.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        if workflow.workflow_id in seen:
            continue
        seen.add(workflow.workflow_id)
        workflows.append(workflow)
    return workflows


def _rebuild_skill_files(
    skill_dir: Path,
    workflows: List[WorkflowSpec],
) -> None:
    metadata_path = skill_metadata_path(skill_dir)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    existing_entries = {
        str(item.get("workflow_id") or ""): item
        for item in metadata.get("workflows", [])
        if isinstance(item, dict)
    }
    metadata["status"] = ACTIVE_STATUS
    metadata["workflow_count"] = len(workflows)
    metadata["workflows"] = [
        {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "path": f"references/workflows/{workflow.workflow_id}.json",
            "script": f"scripts/{workflow.workflow_id}.py",
            "authorship": (
                HUMAN_AUTHORSHIP
                if workflow.mutation_mode == MANUAL_MUTATION_MODE
                else str(
                    existing_entries.get(workflow.workflow_id, {}).get(
                        "authorship"
                    )
                    or "generated"
                )
            ),
        }
        for workflow in sorted(workflows, key=lambda item: item.workflow_id)
    ]
    _write_json_atomic(metadata_path, metadata)

    skill_markdown_path = skill_dir / "SKILL.md"
    skill_markdown = skill_markdown_path.read_text(encoding="utf-8")
    skill_markdown = replace_workflow_catalog(
        skill_markdown,
        workflow_catalog_markdown(workflows),
    )
    skill_markdown_path.write_text(skill_markdown, encoding="utf-8")
    _rebuild_root_index(skill_dir.parent)


def _rebuild_root_index(skill_root: Path) -> None:
    skills = []
    for path in sorted(skill_root.glob("*/references/skill.json")):
        skills.append(json.loads(path.read_text(encoding="utf-8")))
    _write_json_atomic(skill_root / "SKILLS.json", {"skills": skills})


def _write_json_atomic(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(
        prefix=path.name,
        dir=str(path.parent),
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
