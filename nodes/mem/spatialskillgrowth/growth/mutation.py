"""成功增强与失败修复两条独立 mutation 路线。"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Tuple

from nodes.mem.spatialskillgrowth.core.llm_utils import invoke_json
from nodes.mem.spatialskillgrowth.core.models import (
    MutationDirection,
    MutationMode,
    WorkflowSpec,
)
from nodes.mem.spatialskillgrowth.growth.param_space import ParamSpace
from nodes.mem.spatialskillgrowth.growth.workflow_mutator import WorkflowMutator
from nodes.mem.spatialskillgrowth.growth.workflow_slots import (
    referenced_slot_names,
)
from prompt.spatialskillgrowth_prompts import (
    APPLICABILITY_GENERALIZATION_PROMPT,
    FAILURE_REPAIR_DIRECTION_PROMPT,
    GROUNDTRUTH_SAFE_DIRECTION_PROMPT,
    MUTATION_DIRECTION_RETRY_PROMPT,
    SUCCESS_ENHANCEMENT_DIRECTION_PROMPT,
)


class MutationDirector(ABC):
    """
    变异方向指导器的基类。
    负责将底层数据打包成 Prompt，调用 LLM，并把 LLM 返回的 JSON 解析为标准的 MutationDirection 对象。
    """
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
        # 3. 提取“提示指令 (hints)”：大模型可以对某个工具写一句具体的指令（比如针对 MLLM 写：注意看画面左下角）。
        # 这里限制了提示词不能超过 8 个单词，防止大模型写小作文导致系统崩溃。
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
        """
        [重试兜底]：如果大模型返回的 JSON 里没选出任何合法的 preferred_atom_ids，
        说明它犯糊涂了。把它刚才的错误拼成一个 Retry Prompt 强迫它再选一次。
        """
        direction = self._validated_direction(
            parsed, allowed_atom_ids, allowed_tool_names, mode
        )
        if direction.preferred_atom_ids:
            return direction
        # 【容错机制】如果 LLM 偷懒或者输出的 JSON 不合法（没有选出推荐修改的原子节点），
        # 系统会把刚才的错误拼进 Retry Prompt 里，强迫 LLM 再重新输出一次。
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
        """
        【成功增强路线】
        当工作流得出了正确答案时调用。
        核心逻辑：注意函数签名里**刻意没有传入 groundtruth (标准答案)**。
        原因：防止 LLM 看到答案后产生数据泄露（比如直接把“结果是True”硬编码到 prompt 里），
        而是强迫 LLM 关注如何“精简步骤”、“提高泛化性”或“减少 token 消耗”。
        """
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
        """
        【失败修复路线】
        当工作流得出错误答案时调用。
        核心逻辑：
        1. 把标准答案 (groundtruth) 和 错误预测 (prediction) 同时交给 LLM，让它做“尸检”诊断。
        2. LLM 输出修复方向 (direction)。
        3. 【防作弊机制】调用 GROUNDTRUTH_SAFE_DIRECTION_PROMPT 进行二次清洗（sanitized）。
           因为 LLM 经常会作弊，直接把 groundtruth 写进修改后的工具提示(tool_hints)里。
           这一步专门用来洗掉工具参数里硬编码的答案信息，保证修复后的工作流依然具备通用性。
        """
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
    """保留独立对象，便于工作流引擎注入选择策略。"""

    def __init__(self, seed: int = 3407):
        self.seed = seed

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
        """
        负责从海量的参数变异组合中，挑选出符合预算 (budget) 的子集。
        通过调用 param_space 的统计算法，优先尝试历史上未被充分探索或成功率较高的修改原子。
        """
        return param_space.select_workflow_mutations(
            candidates,
            parent,
            active,
            atom_stats,
            count=budget,
            allow_zero_gain=allow_zero_gain,
        )


class WorkflowMutationEngine:
    """
    变异引擎：协调 Director (确定方向)、Mutator (执行修改) 和 Selector (过滤数量)。
    """
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
    ) -> WorkflowSpec:
        """
        将一次纯 ReAct 的自由探索轨迹，抽取/固化成一个标准的 JSON 工作流，作为后续变异的父代(Parent)。
        """
        workflow = self.mutator.extract(
            problem_class,
            question,
            trajectory,
            task_id,
            slot_bindings=slot_bindings,
        )
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
        """
        【核心变异流程】
        输入：原始工作流 (parent) 及其执行轨迹。
        输出：1 个修改指导意见 (direction) + 若干个修改好的新工作流实例 (workflows)。
        """
        atoms = self.param_space.atoms_for(parent.applicability.problem_class)
        # 1. 兵分两路：对错走 enhancement，做错走 repair，获取 LLM 的修改指导 (direction)
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
        # 2. 生成排列组合：根据 LLM 推荐的原子 (preferred_atom_ids)，
        # 让 ParamSpace 生成所有可能的参数修改组合方案 (specs)。
        specs = self.param_space.candidate_portfolios(
            problem_class=parent.applicability.problem_class,
            atom_stats=atom_stats,
            workflow_tools=[step.tool_name for step in parent.steps],
            allowed_tool_names=allowed_tool_names,
            preferred_atom_ids=direction.preferred_atom_ids,
            avoid_atom_ids=direction.avoid_atom_ids,
            atoms_per_portfolio=3,
        )
        # 3. 执行物理修改：利用 Mutator 将修改方案真正应用到 Parent 工作流上，生成编译后的新工作流。
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
        # 4. 预算裁剪：如果有 20 种修改方案，但 budget 只有 3，就通过 Selector 挑出最好的 3 个。
        selected = self.selector.select(
            compiled,
            parent,
            active_workflows,
            atom_stats,
            self.param_space,
            budget,
            allow_zero_gain=not parent_correct,
        )
        # 5. 元数据组装：给挑选出的新工作流打上溯源标签（它是由谁派生来的，基于什么方向修改的）。
        workflows = []
        for mutation, workflow in selected:
            direction_payload = direction.to_dict()
            direction_payload["selected_atom_ids"] = [
                atom.atom_id for atom in mutation.selected_atoms
            ]
            workflow.derived_from_workflow_id = parent.workflow_id
            workflow.mutation_mode = direction.mode
            workflow.mutation_direction = direction_payload
            workflows.append(workflow)
        return direction, workflows


class ApplicabilityGeneralizer:
    """
    技术文档自动生成器。
    当一个变异出来的工作流经过测试被证明确实有效后，
    调用 LLM 帮它写文档（命名、描述适用范围、总结能力边界、梳理所需的依赖工具）。
    """
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
        # 将 LLM 总结的信息回填到工作流的 applicability 属性中
        workflow.name = _safe_name(str(parsed.get("name") or workflow.name))
        workflow.applicability.description = _clean_text(parsed.get("description"), 1000)
        workflow.applicability.exclusions = _clean_text(parsed.get("exclusions"), 600)
        workflow.applicability.capability_boundary = _clean_text(
            parsed.get("capability_boundary"), 600
        )
        # 代码级严格约束：覆盖 LLM 的幻觉，通过 AST/工具代码硬解析来获取它到底用了哪些变量和工具
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
