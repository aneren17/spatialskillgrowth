"""可消融的 工作流检索策略。"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List

from nodes.mem.spatialskillgrowth.llm_utils import invoke_json
from nodes.mem.spatialskillgrowth.models import RetrievalDecision, WorkflowSpec
from nodes.mem.spatialskillgrowth.benchmark_profiles import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.growth_store import WorkflowRepository
from prompt.spatialskillgrowth_prompts import WORKFLOW_TREE_RETRIEVAL_PROMPT
from prompt.spatialskillgrowth_prompts import FLAT_WORKFLOW_RETRIEVAL_PROMPT


class WorkflowRetriever(ABC):
    strategy = "abstract"

    def __init__(
        self,
        repository: WorkflowRepository,
        top_k: int = 3,
        include_provisional: bool = False,
    ):
        self.repository = repository
        self.top_k = max(1, min(3, int(top_k)))
        self.include_provisional = include_provisional

    def retrieve(
        self,
        problem_class: str,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        allowed_tool_names: Iterable[str],
        answer_type: str,
    ) -> tuple[List[WorkflowSpec], RetrievalDecision]:
        candidates = self._structured_candidates(
            problem_class,
            slot_bindings,
            allowed_tool_names,
            answer_type,
        )
        return self.rank(
            candidates,
            problem_class,
            question,
            image_paths,
            slot_bindings,
            answer_type,
        )

    def _structured_candidates(
        self,
        problem_class: str,
        slot_bindings: Dict[str, str],
        allowed_tool_names: Iterable[str],
        answer_type: str,
    ) -> List[WorkflowSpec]:
        output = []
        for workflow in self.repository.list_retrievable(
            problem_class,
            include_provisional=self.include_provisional,
        ):
            if workflow_structurally_eligible(
                workflow, slot_bindings, allowed_tool_names, answer_type
            ):
                output.append(workflow)
        return output

    @abstractmethod
    def rank(
        self,
        candidates: List[WorkflowSpec],
        problem_class: str,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        answer_type: str,
    ) -> tuple[List[WorkflowSpec], RetrievalDecision]:
        raise NotImplementedError


class MultimodalLLMFlatRetriever(WorkflowRetriever):
    strategy = "multimodal_llm_flat"

    def __init__(
        self,
        repository: WorkflowRepository,
        llm,
        top_k: int = 3,
        candidate_cap: int = 0,
        include_provisional: bool = False,
    ):
        super().__init__(repository, top_k, include_provisional)
        self.llm = llm
        self.candidate_cap = max(0, int(candidate_cap))

    def rank(
        self,
        candidates: List[WorkflowSpec],
        problem_class: str,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        answer_type: str,
    ) -> tuple[List[WorkflowSpec], RetrievalDecision]:
        if not candidates:
            return [], RetrievalDecision(self.strategy, rejected=True, reason="No structurally eligible workflow.")
        pool = candidates[: self.candidate_cap] if self.candidate_cap else candidates
        payload = [self._payload(workflow) for workflow in pool]
        prompt = FLAT_WORKFLOW_RETRIEVAL_PROMPT.format(
            top_k=self.top_k,
            problem_class=problem_class,
            answer_type=answer_type,
            slot_bindings=json.dumps(slot_bindings, ensure_ascii=False),
            question=question,
            skill_guidance=self.repository.skill_guidance(problem_class),
            candidates=json.dumps(payload, ensure_ascii=False),
        )
        try:
            parsed = invoke_json(self.llm, prompt, image_paths)
        except Exception as exc:
            return [], RetrievalDecision(
                self.strategy,
                rejected=True,
                reason=f"Retriever LLM failed: {type(exc).__name__}: {exc}",
            )
        if str(parsed.get("action") or "").lower() == "reject_all":
            return [], RetrievalDecision(
                self.strategy,
                rejected=True,
                reason=str(parsed.get("reason") or "LLM rejected all workflows."),
                raw_response=parsed,
            )
        by_id = {workflow.workflow_id: workflow for workflow in pool}
        ranked_ids = []
        raw_ids = parsed.get("ranked_workflow_ids") or []
        if isinstance(raw_ids, list):
            for raw_id in raw_ids:
                workflow_id = str(raw_id)
                if workflow_id in by_id and workflow_id not in ranked_ids:
                    ranked_ids.append(workflow_id)
                if len(ranked_ids) >= self.top_k:
                    break
        if not ranked_ids:
            return [], RetrievalDecision(
                self.strategy,
                rejected=True,
                reason="Retriever returned no valid candidate ID.",
                raw_response=parsed,
            )
        return [by_id[item] for item in ranked_ids], RetrievalDecision(
            self.strategy,
            ranked_workflow_ids=ranked_ids,
            reason=str(parsed.get("reason") or ""),
            raw_response=parsed,
        )

    @staticmethod
    def _payload(workflow: WorkflowSpec) -> Dict:
        return {
            "workflow_id": workflow.workflow_id,
            "status": workflow.status,
            "name": workflow.name,
            "applicability": workflow.applicability.to_dict(),
            "tool_graph": [
                {
                    "step_id": step.step_id,
                    "tool_name": step.tool_name,
                    "depends_on": step.depends_on,
                    "purpose": step.purpose,
                }
                for step in workflow.steps
            ],
            "validated_history": workflow.metrics.to_dict(),
        }


def workflow_structurally_eligible(
    workflow: WorkflowSpec,
    slot_bindings: Dict[str, str],
    allowed_tool_names: Iterable[str],
    answer_type: str,
) -> bool:
    """只比较结构契约；自然语言 applicability 仍交给 LLM。"""
    allowed = set(allowed_tool_names)
    applicability = workflow.applicability
    if any(
        not str(slot_bindings.get(slot) or "").strip()
        for slot in applicability.required_slots
    ):
        return False
    required_tools = set(applicability.required_tools)
    graph_tools = {step.tool_name for step in workflow.steps}
    if (
        applicability.problem_class in ANOMALY_EVENT_TYPES
        and "embeddingTool" not in graph_tools
    ):
        return False
    if not required_tools.issubset(allowed) or not graph_tools.issubset(allowed):
        return False
    return not applicability.answer_types or answer_type in applicability.answer_types


class HistoryOnlyRetriever(WorkflowRetriever):
    strategy = "history_only"

    def rank(
        self,
        candidates: List[WorkflowSpec],
        problem_class: str,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        answer_type: str,
    ) -> tuple[List[WorkflowSpec], RetrievalDecision]:
        ranked = sorted(
            candidates,
            key=lambda workflow: (
                -workflow.metrics.accuracy,
                -workflow.metrics.evidence_rate,
                workflow.metrics.average_cost,
                -workflow.metrics.trial_count,
                workflow.workflow_id,
            ),
        )[: self.top_k]
        ids = [workflow.workflow_id for workflow in ranked]
        return ranked, RetrievalDecision(
            self.strategy,
            ranked_workflow_ids=ids,
            rejected=not bool(ranked),
            reason="Ranked only by validated execution history.",
        )


class LegacyTreeRetriever(WorkflowRetriever):
    """仅用于消融：把 provenance 边临时视作旧版树边。"""

    strategy = "legacy_tree"

    def __init__(
        self,
        repository: WorkflowRepository,
        llm,
        top_k: int = 3,
        include_provisional: bool = False,
    ):
        super().__init__(repository, top_k, include_provisional)
        self.llm = llm

    def rank(
        self,
        candidates: List[WorkflowSpec],
        problem_class: str,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        answer_type: str,
    ) -> tuple[List[WorkflowSpec], RetrievalDecision]:
        if not candidates:
            return [], RetrievalDecision(self.strategy, rejected=True, reason="No eligible workflow.")
        by_id = {workflow.workflow_id: workflow for workflow in candidates}
        payload = _tree_payload(candidates)
        prompt = WORKFLOW_TREE_RETRIEVAL_PROMPT.format(
            problem_class=problem_class,
            slot_bindings=json.dumps(slot_bindings, ensure_ascii=False),
            question=question,
            workflow_tree=json.dumps(payload, ensure_ascii=False),
        )
        try:
            parsed = invoke_json(self.llm, prompt, [])
        except Exception as exc:
            return [], RetrievalDecision(
                self.strategy,
                rejected=True,
                reason=f"Legacy tree retriever failed: {type(exc).__name__}: {exc}",
            )
        selected_id = str(parsed.get("workflow_id") or "")
        if selected_id not in by_id:
            return [], RetrievalDecision(
                self.strategy,
                rejected=True,
                reason="Legacy tree retriever returned an invalid workflow.",
                raw_response=parsed,
            )
        history = HistoryOnlyRetriever(self.repository, self.top_k)
        backups, _ = history.rank(
            [item for item in candidates if item.workflow_id != selected_id],
            problem_class,
            question,
            image_paths,
            slot_bindings,
            answer_type,
        )
        ordered = [by_id[selected_id]] + backups[: self.top_k - 1]
        ids = [workflow.workflow_id for workflow in ordered]
        return ordered, RetrievalDecision(
            self.strategy,
            ranked_workflow_ids=ids,
            reason=str(parsed.get("reason") or ""),
            raw_response=parsed,
        )


def build_retriever(
    strategy: str,
    repository: WorkflowRepository,
    llm,
    top_k: int = 3,
) -> WorkflowRetriever:
    if strategy == MultimodalLLMFlatRetriever.strategy:
        return MultimodalLLMFlatRetriever(repository, llm, top_k)
    if strategy == LegacyTreeRetriever.strategy:
        return LegacyTreeRetriever(repository, llm, top_k)
    if strategy == HistoryOnlyRetriever.strategy:
        return HistoryOnlyRetriever(repository, top_k)
    raise ValueError(f"Unknown retriever strategy: {strategy}")


def _tree_payload(workflows: List[WorkflowSpec]) -> List[Dict]:
    ids = {workflow.workflow_id for workflow in workflows}
    children: Dict[str, List[WorkflowSpec]] = {}
    for workflow in workflows:
        parent = workflow.derived_from_workflow_id
        if parent not in ids:
            parent = ""
        children.setdefault(parent, []).append(workflow)

    def node(workflow: WorkflowSpec) -> Dict:
        return {
            "workflow_id": workflow.workflow_id,
            "derived_from_workflow_id": workflow.derived_from_workflow_id,
            "name": workflow.name,
            "description": workflow.applicability.description,
            "required_slots": workflow.applicability.required_slots,
            "tool_graph": [step.tool_name for step in workflow.steps],
            "success_count": workflow.metrics.correct_count,
            "failure_count": workflow.metrics.trial_count - workflow.metrics.correct_count,
            "children": [
                node(item)
                for item in sorted(children.get(workflow.workflow_id, []), key=lambda child: child.workflow_id)
            ],
        }

    return [node(item) for item in sorted(children.get("", []), key=lambda root: root.workflow_id)]
