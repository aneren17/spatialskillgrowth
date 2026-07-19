"""从工作流工具图中提取可执行槽位。"""

from __future__ import annotations

import keyword
import re
from typing import Any, Dict, List

from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec

# 【核心正则匹配器】
# 专门用来匹配字符串中的 "$slot.变量名" 格式。
# 括号 () 里的内容表示要提取的部分：必须以字母或下划线开头，后面跟着字母、数字或下划线。
# 比如输入 "$slot.event_type"，会提取出 "event_type"。
SLOT_REFERENCE_PATTERN = re.compile(r"\$slot\.([A-Za-z_][A-Za-z0-9_]*)")


def referenced_slot_names(workflow: WorkflowSpec) -> List[str]:
    """按工具图首次出现顺序返回真正被引用的槽位。"""
    # 调用底层的递归提取函数，将找到的变量名追加到 names 列表中
    names: List[str] = []
    for step in workflow.steps:
        _collect_slots(step.args, names)
    # dict.fromkeys(names) 是一种 Pythonic 的去重方法，
    # 相比于 set()，它能保留元素首次插入时的顺序
    return list(dict.fromkeys(names))


def python_slot_parameters(workflow: WorkflowSpec) -> List[str]:
    """
    返回能安全写入 Python 函数签名的槽位名。
    系统联系： WorkflowPythonExporter 生成 `def solve(runtime, question, ...):` 时，
    就是调用这个函数来生成后面的动态参数的。
    """
    names = referenced_slot_names(workflow)
    invalid = [name for name in names if keyword.iskeyword(name)]
    # 【安全校验】
    # keyword.iskeyword(name) 检查提取出来的变量名是不是 Python 的系统保留字
    # 比如，如果大模型不小心生成了 "$slot.if" 或 "$slot.class"
    if invalid:
        raise ValueError(
            f"Workflow {workflow.workflow_id} contains Python keyword slots: {invalid}"
        )
    return names


def slot_bindings_from_locals(
    workflow: WorkflowSpec,
    values: Dict[str, Any],
) -> Dict[str, str]:
    """
    从运行时的局部变量字典（values）中，提取出工作流实际需要的槽位值（bindings）。
    逻辑：工作流声明需要哪些变量，就从 values 里捞哪些变量，全部转为字符串。如果没传，就默认给空字符串 ""。
    """
    return {
        name: str(values.get(name) or "")
        for name in referenced_slot_names(workflow)
    }


def _collect_slots(value: Any, names: List[str]) -> None:
    """
    【递归扫描器】
    这是底层的核心函数。因为工作流中某个工具的参数（args）可能是非常复杂的嵌套 JSON，
    比如：{"query": "$slot.event_type", "options": ["$slot.color", "other"]}。
    必须使用递归才能把深藏在列表或字典里面的槽位都挖出来。
    """
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
