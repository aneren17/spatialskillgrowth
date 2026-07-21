"""结构候选生成、LLM applicability 兼容判断和 Pareto 生命周期。"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

from nodes.mem.spatialskillgrowth.core.llm_utils import invoke_json
from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec, WorkflowStatus
from nodes.mem.spatialskillgrowth.runtime.tool_contracts import contract_signature
from nodes.mem.spatialskillgrowth.storage.growth_store import (
    ExperimentStore,
    WorkflowRepository,
)
from prompt.spatialskillgrowth_prompts import APPLICABILITY_COMPATIBILITY_PROMPT


class StructuralCompatibilityChecker:
    """只比较工具 DAG、参数形状和工具输出契约，不读取 applicability 文本。"""

    def signature(self, workflow: WorkflowSpec) -> str:
        payload = self.graph_payload(workflow)
        return hashlib.sha1(
            json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()

    def compatible(self, left: WorkflowSpec, right: WorkflowSpec) -> bool:
        # 如果连解决的问题类型都不一样（一个测摔倒，一个测失火），直接判定为不像
        if left.applicability.problem_class != right.applicability.problem_class:
            return False
        return (
            self.graph_payload(left) == self.graph_payload(right)
            or self.compatibility_payload(left) == self.compatibility_payload(right)
        )

    def graph_payload(self, workflow: WorkflowSpec) -> List[Dict]:
        step_index = {step.step_id: index for index, step in enumerate(workflow.steps)}
        payload = []
        for index, step in enumerate(workflow.steps):
            payload.append({
                "index": index,
                "tool": step.tool_name,
                "output_contract": contract_signature(step.tool_name),
                "arg_shape": _argument_shape(step.args),
                "dependencies": sorted(
                    step_index[dependency]
                    for dependency in step.depends_on
                    if dependency in step_index
                ),
                "param_axes": sorted(
                    (atom.tool_name, atom.axis, atom.kind)
                    for atom in step.param_atoms
                ),
            })
        return payload

    def compatibility_payload(self, workflow: WorkflowSpec) -> List[Dict]:
        """忽略具体参数值，但保留工具契约和 DAG 拓扑作为候选门。"""
        step_index = {step.step_id: index for index, step in enumerate(workflow.steps)}
        return [
            {
                "index": index,
                "tool": step.tool_name,
                "output_contract": contract_signature(step.tool_name),
                "dependencies": sorted(
                    step_index[dependency]
                    for dependency in step.depends_on
                    if dependency in step_index
                ),
            }
            for index, step in enumerate(workflow.steps)
        ]


class ApplicabilityCompatibilityJudge:
    """所有自然语言兼容结论均来自 LLM，不使用关键词规则。"""

    def __init__(self, llm):
        self.llm = llm

    def judge(self, left: WorkflowSpec, right: WorkflowSpec) -> Dict:
        # 把两个技能的“适用范围描述”发给 LLM，问它：
        # “这两个技能能合并成一个更通用的技能吗？如果能，帮我重写一份通用的适用范围描述。”
        prompt = APPLICABILITY_COMPATIBILITY_PROMPT.format(
            left=json.dumps(_semantic_payload(left), ensure_ascii=False),
            right=json.dumps(_semantic_payload(right), ensure_ascii=False),
        )
        parsed = invoke_json(self.llm, prompt, [])
        action = str(parsed.get("action") or "").lower()
        if action not in {"merge", "separate"}:
            raise ValueError(f"Invalid applicability compatibility action: {action}")
        return {
            "action": action,
            "reason": str(parsed.get("reason") or ""),
            "generalized_name": str(parsed.get("generalized_name") or ""),
            "generalized_description": str(parsed.get("generalized_description") or ""),
            "generalized_exclusions": str(parsed.get("generalized_exclusions") or ""),
            "generalized_capability_boundary": str(
                parsed.get("generalized_capability_boundary") or ""
            ),
        }


class ParetoWorkflowPruner:
    """以正确性、证据率、成本和结构覆盖维护每类 soft cap。"""

    def __init__(self, cap_per_class: int = 12):
        self.cap_per_class = max(1, int(cap_per_class))

    def select_archive(self, workflows: List[WorkflowSpec]) -> List[WorkflowSpec]:
        if len(workflows) <= self.cap_per_class:
            return []
        # 什么是被支配 (dominated)？
        # 如果技能 A 的准确率比 B 高，证据率比 B 高，成本比 B 低，覆盖率比 B 大。
        dominated = [
            workflow for workflow in workflows
            if any(
                other.workflow_id != workflow.workflow_id
                and _dominates(other, workflow)
                for other in workflows
            )
        ]
        archive = sorted(dominated, key=_retention_key)
        remaining = [item for item in workflows if item not in archive]
        if len(remaining) > self.cap_per_class:
            archive.extend(sorted(remaining, key=_retention_key)[: len(remaining) - self.cap_per_class])
        if len(workflows) - len(archive) < self.cap_per_class:
            archive = archive[: len(workflows) - self.cap_per_class]
        return list({item.workflow_id: item for item in archive}.values())


class WorkflowConsolidator:
    def __init__(
        self,
        repository: WorkflowRepository,
        store: ExperimentStore,
        structural_checker: StructuralCompatibilityChecker,
        semantic_judge: ApplicabilityCompatibilityJudge,
        pruner: ParetoWorkflowPruner,
        semantic_consolidation: bool = True,
    ):
        self.repository = repository
        self.store = store
        self.structural_checker = structural_checker
        self.semantic_judge = semantic_judge
        self.pruner = pruner
        self.semantic_consolidation = semantic_consolidation

    def consolidate(self, workflow: WorkflowSpec, task_id: str) -> Dict:
        """
        一个新技能(workflow)要转正了！
        """
        if workflow.metrics.correct_count < 1:
            raise ValueError("Only a correct validated workflow can be activated")
        # 1. 找同类：拉出当前库里所有的正式老技能
        active = self.repository.list_active(workflow.applicability.problem_class)
        # 2. 查结构：让“结构查重员”找出所有骨架一样的老技能
        compatible = [
            item for item in active
            if item.workflow_id != workflow.workflow_id
            and self.structural_checker.compatible(workflow, item)
        ]
        comparisons = []
        representative = workflow
        merged_with = ""
        # 3. 查语义并合并
        if self.semantic_consolidation:
            for existing in compatible:
                decision = self.semantic_judge.judge(representative, existing)
                comparisons.append({
                    "workflow_id": existing.workflow_id,
                    "structurally_compatible": True,
                    **decision,
                })
                if decision["action"] != "merge":
                    continue
                # 如果能合并，执行真正的合并逻辑！
                # _merge 会比较两者的 KPI，保留成绩好的那个作为代表(representative)，把被合并的变成历史归档(archived)。
                # 同时，把两个技能的历史战绩加在一起！
                representative, archived = self._merge(representative, existing, decision)
                merged_with = archived.workflow_id

                self.repository.archive(archived, "semantic_merge")
                self.store.record_workflow_event(
                    archived.workflow_id,
                    task_id,
                    "archive_semantic_merge",
                    {"representative": representative.workflow_id, "decision": decision},
                )
                break
        representative.status = WorkflowStatus.ACTIVE.value
        self.repository.save(representative)
        self.store.record_workflow_event(
            representative.workflow_id,
            task_id,
            "activate" if not merged_with else "merge_representative",
            {"merged_with": merged_with, "comparisons": comparisons},
        )
        archived_by_cap = []
        # 5. 容量裁剪：库里加入新代表后，让帕累托专员看看是不是超载了，超载了就杀掉弱
        refreshed = self.repository.list_active(workflow.applicability.problem_class)
        for item in self.pruner.select_archive(refreshed):
            self.repository.archive(item, "pareto_soft_cap")
            archived_by_cap.append(item.workflow_id)
            self.store.record_workflow_event(
                item.workflow_id, task_id, "archive_pareto_cap", {}
            )
        return {
            "representative_workflow_id": representative.workflow_id,
            "merged_with": merged_with,
            "structural_candidate_ids": [item.workflow_id for item in compatible],
            "comparisons": comparisons,
            "archived_by_cap": archived_by_cap,
        }

    @staticmethod
    def _merge(
        candidate: WorkflowSpec,
        existing: WorkflowSpec,
        decision: Dict,
    ) -> Tuple[WorkflowSpec, WorkflowSpec]:
        representative, archived = (
            (candidate, existing)
            if _representative_key(candidate) >= _representative_key(existing)
            else (existing, candidate)
        )
        representative.metrics = _merge_metrics(candidate, existing)
        representative.source_task_ids = list(dict.fromkeys(
            candidate.source_task_ids + existing.source_task_ids
        ))
        if decision.get("generalized_name"):
            representative.name = str(decision["generalized_name"])[:80]
        representative.applicability.description = str(
            decision.get("generalized_description")
            or representative.applicability.description
        )[:1000]
        representative.applicability.exclusions = str(
            decision.get("generalized_exclusions")
            or representative.applicability.exclusions
        )[:600]
        representative.applicability.capability_boundary = str(
            decision.get("generalized_capability_boundary")
            or representative.applicability.capability_boundary
        )[:600]
        return representative, archived


def _argument_shape(value):
    if isinstance(value, dict):
        return {key: _argument_shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_argument_shape(item) for item in value]
    if isinstance(value, str):
        if value.startswith("$slot."):
            return "$slot"
        if value.startswith("$step."):
            return "$step"
        if value.startswith("$"):
            return value
        return "text"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def _semantic_payload(workflow: WorkflowSpec) -> Dict:
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "applicability": workflow.applicability.to_dict(),
        "tool_graph": [step.tool_name for step in workflow.steps],
    }


def _merge_metrics(left: WorkflowSpec, right: WorkflowSpec):
    merged = left.metrics.__class__()
    for name in merged.__dataclass_fields__:
        setattr(
            merged,
            name,
            getattr(left.metrics, name) + getattr(right.metrics, name),
        )
    return merged


def _representative_key(workflow: WorkflowSpec) -> tuple:
    return (
        workflow.metrics.accuracy,
        workflow.metrics.evidence_rate,
        -workflow.metrics.average_cost,
        workflow.metrics.structural_coverage,
        workflow.metrics.trial_count,
        workflow.workflow_id,
    )


def _retention_key(workflow: WorkflowSpec) -> tuple:
    return (
        workflow.metrics.accuracy,
        workflow.metrics.evidence_rate,
        -workflow.metrics.average_cost,
        workflow.metrics.structural_coverage,
        workflow.metrics.trial_count,
        workflow.workflow_id,
    )


def _dominates(left: WorkflowSpec, right: WorkflowSpec) -> bool:
    left_values = (
        left.metrics.accuracy,
        left.metrics.evidence_rate,
        -left.metrics.average_cost,
        left.metrics.structural_coverage,
    )
    right_values = (
        right.metrics.accuracy,
        right.metrics.evidence_rate,
        -right.metrics.average_cost,
        right.metrics.structural_coverage,
    )
    return all(a >= b for a, b in zip(left_values, right_values)) and any(
        a > b for a, b in zip(left_values, right_values)
    )
