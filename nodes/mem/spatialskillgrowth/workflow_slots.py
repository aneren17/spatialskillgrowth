"""从工作流工具图中提取可执行槽位。"""

from __future__ import annotations

import keyword
import re
from typing import Any, Dict, List

from nodes.mem.spatialskillgrowth.models import WorkflowSpec


SLOT_REFERENCE_PATTERN = re.compile(r"\$slot\.([A-Za-z_][A-Za-z0-9_]*)")


def referenced_slot_names(workflow: WorkflowSpec) -> List[str]:
    """按工具图首次出现顺序返回真正被引用的槽位。"""
    names: List[str] = []
    for step in workflow.steps:
        _collect_slots(step.args, names)
    return list(dict.fromkeys(names))


def python_slot_parameters(workflow: WorkflowSpec) -> List[str]:
    """返回能安全写入 Python 函数签名的槽位名。"""
    names = referenced_slot_names(workflow)
    invalid = [name for name in names if keyword.iskeyword(name)]
    if invalid:
        raise ValueError(
            f"Workflow {workflow.workflow_id} contains Python keyword slots: {invalid}"
        )
    return names


def slot_bindings_from_locals(
    workflow: WorkflowSpec,
    values: Dict[str, Any],
) -> Dict[str, str]:
    return {
        name: str(values.get(name) or "")
        for name in referenced_slot_names(workflow)
    }


def _collect_slots(value: Any, names: List[str]) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _collect_slots(item, names)
        return
    if isinstance(value, list):
        for item in value:
            _collect_slots(item, names)
        return
    if not isinstance(value, str):
        return
    names.extend(SLOT_REFERENCE_PATTERN.findall(value))
