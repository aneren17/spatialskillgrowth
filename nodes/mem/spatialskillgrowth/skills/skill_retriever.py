"""按同类别 SKILL.md、当前画面和已验证历史检索工作流。"""

import json

from nodes.mem.spatialskillgrowth.core.llm_utils import invoke_json
from nodes.mem.spatialskillgrowth.core.models import RetrievalDecision
from prompt.spatialskillgrowth_prompts import (
    SKILL_GUIDED_WORKFLOW_RETRIEVAL_PROMPT,
)


class WorkflowRetriever:
    """类别由输入给定；LLM 只依据该类别 SKILL.md 排序工作流。"""

    def __init__(
        self,
        repository,
        llm,
        top_k=3,
        include_provisional=False,
        return_all_candidates=False,
    ):
        self.repository = repository
        self.llm = llm
        self.top_k = max(1, int(top_k))
        self.include_provisional = include_provisional
        self.return_all_candidates = return_all_candidates

    def retrieve(
        self,
        event_type,
        question,
        image_paths,
        slot_bindings,
        allowed_tool_names,
        media_type="",
    ):
        candidates = []
        workflows = self.repository.list_retrievable(
            event_type,
            include_provisional=self.include_provisional,
        )
        for workflow in workflows:
            if workflow_structurally_eligible(
                workflow,
                slot_bindings,
                allowed_tool_names,
                media_type,
            ):
                candidates.append(workflow)

        if not candidates:
            return [], RetrievalDecision(
                strategy="skill_guided_multimodal",
                rejected=True,
                reason="当前类别没有结构契约合格的工作流。",
            )

        candidates.sort(key=_history_sort_key)
        if self.return_all_candidates:
            ranked_ids = [
                workflow.workflow_id
                for workflow in candidates
            ]
            return candidates, RetrievalDecision(
                strategy="all_structurally_eligible",
                ranked_workflow_ids=ranked_ids,
                reason="冻结推理返回当前类别全部结构契约合格工作流。",
            )

        skill_guidance = self.repository.skill_guidance(
            event_type,
            include_provisional=self.include_provisional,
        )
        if not skill_guidance:
            return self._history_fallback(
                candidates,
                "同类别 SKILL.md 不存在或为空，已退回历史指标排序。",
            )

        result_limit = self.top_k
        prompt = SKILL_GUIDED_WORKFLOW_RETRIEVAL_PROMPT.format(
            top_k=result_limit,
            event_type=event_type,
            slot_bindings=json.dumps(slot_bindings, ensure_ascii=False),
            question=question,
            skill_guidance=skill_guidance,
            candidates=json.dumps(
                [_workflow_payload(workflow) for workflow in candidates],
                ensure_ascii=False,
            ),
        )
        try:
            parsed = invoke_json(self.llm, prompt, image_paths)
        except Exception as exc:
            return self._history_fallback(
                candidates,
                "读取 SKILL.md 后的语义排序失败，已退回历史指标排序："
                + type(exc).__name__
                + ": "
                + str(exc),
            )

        if str(parsed.get("action") or "").lower() == "reject_all":
            return [], RetrievalDecision(
                strategy="skill_guided_multimodal",
                rejected=True,
                reason=str(parsed.get("reason") or "SKILL.md 不支持当前输入。"),
                raw_response=parsed,
            )

        by_id = {}
        for workflow in candidates:
            by_id[workflow.workflow_id] = workflow
        ranked_ids = []
        raw_ids = parsed.get("ranked_workflow_ids") or []
        if isinstance(raw_ids, list):
            for raw_id in raw_ids:
                workflow_id = str(raw_id)
                if workflow_id not in by_id:
                    continue
                if workflow_id in ranked_ids:
                    continue
                ranked_ids.append(workflow_id)
                if len(ranked_ids) >= result_limit:
                    break
        if not ranked_ids:
            return self._history_fallback(
                candidates,
                "SKILL.md 语义排序没有返回合法工作流 ID，已退回历史指标排序。",
            )
        ranked = []
        for workflow_id in ranked_ids:
            ranked.append(by_id[workflow_id])
        return ranked, RetrievalDecision(
            strategy="skill_guided_multimodal",
            ranked_workflow_ids=ranked_ids,
            reason=str(parsed.get("reason") or ""),
            raw_response=parsed,
        )

    def _history_fallback(self, candidates, reason):
        ranked = candidates[: self.top_k]
        ranked_ids = []
        for workflow in ranked:
            ranked_ids.append(workflow.workflow_id)
        return ranked, RetrievalDecision(
            strategy="skill_guided_history_fallback",
            ranked_workflow_ids=ranked_ids,
            rejected=not bool(ranked),
            reason=reason,
        )


def workflow_structurally_eligible(
    workflow,
    slot_bindings,
    allowed_tool_names,
    media_type="",
):
    # 结构契约检查：确保工作流的 slots 和 tools 符合要求
    applicability = workflow.applicability
    for slot_name in applicability.required_slots:
        if not str(slot_bindings.get(slot_name) or "").strip():
            return False

    allowed_tools = set(allowed_tool_names)
    required_tools = set(applicability.required_tools)
    graph_tools = set()
    for step in workflow.steps:
        graph_tools.add(step.tool_name)
    if "embeddingTool" in required_tools or "embeddingTool" in graph_tools:
        return False
    if not required_tools.issubset(allowed_tools):
        return False
    if not graph_tools.issubset(allowed_tools):
        return False
    return True


def build_retriever(repository, llm, top_k=3):
    return WorkflowRetriever(repository, llm, top_k)


def _history_sort_key(workflow):
    metrics = workflow.metrics
    return (
        -metrics.accuracy,
        -metrics.evidence_rate,
        metrics.average_cost,
        -metrics.trial_count,
        workflow.workflow_id,
    )


def _workflow_payload(workflow):
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "status": workflow.status,
        "applicability": workflow.applicability.to_dict(),
        "tool_chain": [
            {
                "step_id": step.step_id,
                "tool_name": step.tool_name,
                "depends_on": list(step.depends_on),
                "purpose": step.purpose,
            }
            for step in workflow.steps
        ],
        "validated_history": workflow.metrics.to_dict(),
    }
