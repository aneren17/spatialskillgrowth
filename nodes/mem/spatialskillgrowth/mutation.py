"""成功增强与失败修复两条独立 mutation 路线。"""

from __future__ import annotations

import json
import random
import re
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Tuple

from nodes.mem.spatialskillgrowth.param_space import ParamSpace
from nodes.mem.spatialskillgrowth.llm_utils import invoke_json
from nodes.mem.spatialskillgrowth.models import (
    MutationDirection,
    MutationMode,
    WorkflowSpec,
)
from nodes.mem.spatialskillgrowth.workflow_mutator import WorkflowMutator
from nodes.mem.spatialskillgrowth.workflow_slots import referenced_slot_names
from prompt.spatialskillgrowth_prompts import (
    APPLICABILITY_GENERALIZATION_PROMPT,
    FAILURE_REPAIR_DIRECTION_PROMPT,
    GROUNDTRUTH_SAFE_DIRECTION_PROMPT,
    MUTATION_DIRECTION_RETRY_PROMPT,
    SUCCESS_ENHANCEMENT_DIRECTION_PROMPT,
)


class MutationDirector(ABC):
    mode = "abstract"

    def __init__(self, llm):
        self.llm = llm

    @abstractmethod
    def direct(self, **kwargs) -> MutationDirection:
        raise NotImplementedError

    @staticmethod
    def _validated_direction(
        parsed: Dict,
        allowed_atom_ids: Iterable[str],
        allowed_tool_names: Iterable[str],
        mode: str,
    ) -> MutationDirection:
        atom_ids = set(allowed_atom_ids)
        tools = set(allowed_tool_names)
        preferred = [
            str(item) for item in parsed.get("preferred_atom_ids", [])
            if str(item) in atom_ids
        ]
        avoid = [
            str(item) for item in parsed.get("avoid_atom_ids", [])
            if str(item) in atom_ids
        ]
        raw_hints = parsed.get("tool_hints") or {}
        hints = {
            str(name): " ".join(str(value).split()[:8])
            for name, value in raw_hints.items()
            if str(name) in tools and str(value).strip()
        } if isinstance(raw_hints, dict) else {}
        return MutationDirection(
            mode=mode,
            objective=" ".join(str(parsed.get("objective") or "").split())[:500],
            preferred_atom_ids=list(dict.fromkeys(preferred)),
            avoid_atom_ids=list(dict.fromkeys(avoid)),
            tool_hints=hints,
            diagnosis=" ".join(str(parsed.get("diagnosis") or "").split())[:1000],
        )

    def _ensure_directed(
        self,
        parsed: Dict,
        allowed_atom_ids: List[str],
        allowed_tool_names: List[str],
        mode: str,
    ) -> MutationDirection:
        direction = self._validated_direction(
            parsed, allowed_atom_ids, allowed_tool_names, mode
        )
        if direction.preferred_atom_ids:
            return direction
        retry_prompt = MUTATION_DIRECTION_RETRY_PROMPT.format(
            mode=mode,
            direction=json.dumps(direction.to_dict(), ensure_ascii=False),
            allowed_tools=json.dumps(allowed_tool_names, ensure_ascii=False),
            allowed_atom_ids=json.dumps(allowed_atom_ids, ensure_ascii=False),
        )
        retry = invoke_json(self.llm, retry_prompt, [])
        return self._validated_direction(
            retry, allowed_atom_ids, allowed_tool_names, mode
        )


class SuccessEnhancementDirector(MutationDirector):
    mode = MutationMode.SUCCESS_ENHANCEMENT.value

    def direct(
        self,
        problem_class: str,
        question: str,
        slot_bindings: Dict[str, str],
        workflow: WorkflowSpec,
        observations: List[Dict],
        atoms,
        allowed_tool_names: List[str],
    ) -> MutationDirection:
        """函数签名刻意不接收 groundtruth，防止成功路线看到答案。"""
        prompt = SUCCESS_ENHANCEMENT_DIRECTION_PROMPT.format(
            problem_class=problem_class,
            question=question,
            slot_bindings=json.dumps(slot_bindings, ensure_ascii=False),
            workflow_context=json.dumps({
                "workflow": workflow.to_dict(),
                "observations": observations,
            }, ensure_ascii=False, default=str)[-12000:],
            param_atoms=json.dumps([atom.to_dict() for atom in atoms], ensure_ascii=False),
        )
        parsed = invoke_json(self.llm, prompt, [])
        return self._ensure_directed(
            parsed,
            [atom.atom_id for atom in atoms],
            allowed_tool_names,
            self.mode,
        )


class FailureRepairDirector(MutationDirector):
    mode = MutationMode.FAILURE_REPAIR.value

    def direct(
        self,
        problem_class: str,
        question: str,
        groundtruth: str,
        prediction: str,
        slot_bindings: Dict[str, str],
        workflow: WorkflowSpec,
        observations: List[Dict],
        atoms,
        allowed_tool_names: List[str],
    ) -> MutationDirection:
        prompt = FAILURE_REPAIR_DIRECTION_PROMPT.format(
            problem_class=problem_class,
            question=question,
            prediction=prediction,
            groundtruth=groundtruth,
            slot_bindings=json.dumps(slot_bindings, ensure_ascii=False),
            workflow_context=json.dumps({
                "workflow": workflow.to_dict(),
                "observations": observations,
            }, ensure_ascii=False, default=str)[-12000:],
            param_atoms=json.dumps([atom.to_dict() for atom in atoms], ensure_ascii=False),
        )
        parsed = invoke_json(self.llm, prompt, [])
        atom_ids = [atom.atom_id for atom in atoms]
        direction = self._ensure_directed(
            parsed, atom_ids, allowed_tool_names, self.mode
        )
        safe_prompt = GROUNDTRUTH_SAFE_DIRECTION_PROMPT.format(
            groundtruth=groundtruth,
            direction=json.dumps(direction.to_dict(), ensure_ascii=False),
            allowed_tools=json.dumps(allowed_tool_names, ensure_ascii=False),
            allowed_atom_ids=json.dumps(atom_ids, ensure_ascii=False),
        )
        sanitized = invoke_json(self.llm, safe_prompt, [])
        return self._ensure_directed(
            sanitized, atom_ids, allowed_tool_names, self.mode
        )


class MutationCandidateSelector:
    """先按 Director 方向过滤，再使用指定的覆盖策略排序。"""

    def __init__(self, strategy: str = "direction_ucb", seed: int = 3407):
        self.strategy = strategy
        self.random = random.Random(seed)

    def select(
        self,
        candidates: List[Tuple],
        parent: WorkflowSpec,
        active: List[WorkflowSpec],
        atom_stats: Dict[str, Dict[str, int]],
        param_space: ParamSpace,
        budget: int,
        allow_zero_gain: bool,
    ) -> List[Tuple]:
        if self.strategy == "uniform":
            shuffled = list(candidates)
            self.random.shuffle(shuffled)
            return shuffled[:budget]
        if self.strategy == "direction_only":
            return sorted(candidates, key=lambda item: item[0].mutation_id)[:budget]
        if self.strategy != "direction_ucb":
            raise ValueError(f"Unknown mutation selector: {self.strategy}")
        return param_space.select_workflow_mutations(
            candidates,
            parent,
            active,
            atom_stats,
            count=budget,
            allow_zero_gain=allow_zero_gain,
        )


class WorkflowMutationEngine:
    def __init__(
        self,
        success_director: SuccessEnhancementDirector,
        failure_director: FailureRepairDirector,
        selector: MutationCandidateSelector,
        class_descriptions: Dict[str, str],
        param_space: ParamSpace | None = None,
    ):
        self.success_director = success_director
        self.failure_director = failure_director
        self.selector = selector
        self.param_space = param_space or ParamSpace()
        self.mutator = WorkflowMutator(class_descriptions)

    def extract_parent(
        self,
        problem_class: str,
        question: str,
        trajectory: List[Dict],
        task_id: str,
        slot_bindings: Dict[str, str],
        answer_type: str,
    ) -> WorkflowSpec:
        workflow = self.mutator.extract(
            problem_class,
            question,
            trajectory,
            task_id,
            slot_bindings=slot_bindings,
        )
        workflow.applicability.answer_types = [answer_type] if answer_type else []
        workflow.mutation_mode = MutationMode.EXTRACTED.value
        workflow.mutation_direction = {}
        return workflow

    def generate(
        self,
        parent: WorkflowSpec,
        question: str,
        groundtruth: str,
        prediction: str,
        parent_correct: bool,
        observations: List[Dict],
        slot_bindings: Dict[str, str],
        allowed_tool_names: List[str],
        task_id: str,
        active_workflows: List[WorkflowSpec],
        atom_stats: Dict[str, Dict[str, int]],
        budget: int,
    ) -> tuple[MutationDirection, List[WorkflowSpec]]:
        atoms = self.param_space.atoms_for(parent.applicability.problem_class)
        if parent_correct:
            direction = self.success_director.direct(
                problem_class=parent.applicability.problem_class,
                question=question,
                slot_bindings=slot_bindings,
                workflow=parent,
                observations=observations,
                atoms=atoms,
                allowed_tool_names=allowed_tool_names,
            )
        else:
            direction = self.failure_director.direct(
                problem_class=parent.applicability.problem_class,
                question=question,
                groundtruth=groundtruth,
                prediction=prediction,
                slot_bindings=slot_bindings,
                workflow=parent,
                observations=observations,
                atoms=atoms,
                allowed_tool_names=allowed_tool_names,
            )
        if not direction.preferred_atom_ids:
            return direction, []
        specs = self.param_space.candidate_portfolios(
            problem_class=parent.applicability.problem_class,
            atom_stats=atom_stats,
            workflow_tools=[step.tool_name for step in parent.steps],
            allowed_tool_names=allowed_tool_names,
            preferred_atom_ids=direction.preferred_atom_ids,
            avoid_atom_ids=direction.avoid_atom_ids,
            atoms_per_portfolio=3,
        )
        compiled = []
        for mutation in specs:
            workflow = self.mutator.mutate(
                parent,
                mutation,
                task_id,
                tool_hints=direction.tool_hints,
                slot_bindings=slot_bindings,
                question=question,
            )
            compiled.append((mutation, workflow))
        selected = self.selector.select(
            compiled,
            parent,
            active_workflows,
            atom_stats,
            self.param_space,
            budget,
            allow_zero_gain=not parent_correct,
        )
        workflows = []
        for mutation, workflow in selected:
            direction_payload = direction.to_dict()
            direction_payload["selected_atom_ids"] = [
                atom.atom_id for atom in mutation.selected_atoms
            ]
            workflow.applicability.answer_types = list(
                parent.applicability.answer_types
            )
            workflow.derived_from_workflow_id = parent.workflow_id
            workflow.mutation_mode = direction.mode
            workflow.mutation_direction = direction_payload
            workflows.append(workflow)
        return direction, workflows


class ApplicabilityGeneralizer:
    def __init__(self, llm):
        self.llm = llm

    def generalize(
        self,
        workflow: WorkflowSpec,
        question: str,
        slot_bindings: Dict[str, str],
    ) -> WorkflowSpec:
        prompt = APPLICABILITY_GENERALIZATION_PROMPT.format(
            problem_class=workflow.applicability.problem_class,
            question=question,
            slot_bindings=json.dumps(slot_bindings, ensure_ascii=False),
            mutation_mode=workflow.mutation_mode,
            tool_graph=json.dumps([
                {
                    "step_id": step.step_id,
                    "tool": step.tool_name,
                    "depends_on": step.depends_on,
                    "purpose": step.purpose,
                }
                for step in workflow.steps
            ], ensure_ascii=False),
        )
        parsed = invoke_json(self.llm, prompt, [])
        workflow.name = _safe_name(str(parsed.get("name") or workflow.name))
        workflow.applicability.description = _clean_text(parsed.get("description"), 1000)
        workflow.applicability.exclusions = _clean_text(parsed.get("exclusions"), 600)
        workflow.applicability.capability_boundary = _clean_text(
            parsed.get("capability_boundary"), 600
        )
        workflow.applicability.required_slots = referenced_slot_names(workflow)
        workflow.applicability.required_tools = list(dict.fromkeys(
            step.tool_name for step in workflow.steps
        ))
        return workflow


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return name[:80] or "validated_workflow"


def _clean_text(value, limit: int) -> str:
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value)
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    return " ".join(str(value or "").split())[:limit]
