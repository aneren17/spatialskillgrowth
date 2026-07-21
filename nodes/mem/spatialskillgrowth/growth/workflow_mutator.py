"""Extract, generalize, and mutate reusable dependency-aware workflows."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List

from nodes.mem.spatialskillgrowth.core.anomaly_events import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.core.models import (
    ApplicabilitySpec,
    MutationSpec,
    ParamAtom,
    WorkflowSpec,
    WorkflowStep,
)
from nodes.mem.spatialskillgrowth.runtime.tool_contracts import (
    DEPENDENT_TOOLS,
    PIXEL_DETECTION_TOOLS,
    compatible_producers,
)
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import (
    normalize_workflow_steps,
)
from prompt.spatialskillgrowth_prompts import (
    WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT,
    WORKFLOW_FINAL_ANSWER_PROMPT,
    WORKFLOW_NORMALIZED_QUERY_PROMPT,
)


PYTHON_DETECTION_SUMMARY_CODE = """import json

detections = json.loads(r'''__DETECTIONS__''').get("detections", [])
summary = []
for item in detections:
    box = item.get("bbox", [])
    if len(box) != 4:
        continue
    width = max(0.0, float(box[2]) - float(box[0]))
    height = max(0.0, float(box[3]) - float(box[1]))
    summary.append({
        "class_name": item.get("class_name", ""),
        "score": item.get("score", 0.0),
        "area": width * height,
        "center": [(float(box[0]) + float(box[2])) / 2, (float(box[1]) + float(box[3])) / 2],
    })
print(json.dumps({"count": len(summary), "objects": summary}, ensure_ascii=False))
"""


class WorkflowMutator:
    def __init__(self, class_descriptions: Dict[str, str] = None):
        self.class_descriptions = dict(class_descriptions or {})

    def extract(
        self,
        problem_class: str,
        question: str,
        trajectory: List[Dict[str, Any]],
        source_task_id: str,
        derived_from_workflow_id: str = "",
        slot_bindings: Dict[str, str] = None,
    ) -> WorkflowSpec:
        """
        [轨迹固化]：将一次纯 ReAct 的自由探索轨迹，抽取成标准的 JSON 工作流。
        假设大模型为了做题，先后调用了：yoloTool -> 失败报错 -> 重新 yoloTool -> MLLM回答。
        这个函数会把它清洗成干净的：yoloTool -> MLLM。
        """
        steps: List[WorkflowStep] = []
        seen_calls = set()
        for item in trajectory or []:
            calls = item.get("tool_calls", []) if isinstance(item, dict) else []
            for call in calls or []:
                tool_name = str(call.get("name") or "")
                if not tool_name:
                    continue
                args = self._normalize_args(
                    tool_name,
                    call.get("args") or {},
                )
                signature = (tool_name, json.dumps(args, sort_keys=True, ensure_ascii=True))
                if signature in seen_calls:
                    continue
                seen_calls.add(signature)
                steps.append(WorkflowStep(
                    tool_name=tool_name,
                    args=args,
                    purpose=self._step_purpose(tool_name, problem_class),
                ))
        # 2. 压缩与精简：把步骤控制在合理数量内，强制最后一个步骤是 MLLM 或 embeddingTool
        steps = self._compact_steps(steps, problem_class)
        if not steps:
            steps = [self._default_step(problem_class)]
        # 3. 理顺执行依赖顺序并连线 (非常重要！)
        # 比如：先跑独立工具 (yolo)，再跑依赖工具 (crop 裁剪需要 yolo 的框)，最后跑总结 (MLLM)
        steps = self._order_and_wire(steps, problem_class)
        # 4. 封装成完整的 WorkflowSpec 并返回
        applicability = ApplicabilitySpec(
            problem_class=problem_class,
            description=self.class_descriptions.get(
                problem_class, "Reusable spatial reasoning route."
            ),
            required_slots=self._required_slots(steps),
            required_tools=list(dict.fromkeys(step.tool_name for step in steps)),
        )
        workflow_id = self._workflow_id(problem_class, steps)
        return WorkflowSpec(
            workflow_id=workflow_id,
            name=f"{problem_class}_route",
            applicability=applicability,
            steps=steps,
            derived_from_workflow_id=derived_from_workflow_id,
            source_task_ids=[source_task_id],
        )

    def generalize(self, workflow: WorkflowSpec, question: str = "") -> WorkflowSpec:

        generalized = copy.deepcopy(workflow)
        for step in generalized.steps:
            if step.tool_name == "MLLM":
                # 提取控制大模型认知方式的“配置原子” (比如是看全图，还是看局部)
                world_atoms = [
                    atom for atom in step.param_atoms if atom.kind == "world_model"
                ]
                # 动态生成全新的、不含具体物品名称的通用 Prompt
                # 例如生成："请根据局部区域的视觉线索，判断是否发生了 {problem_class} 异常。"
                step.args["query"] = (
                    self._semantic_query_for_atoms(
                        world_atoms, generalized.applicability
                    )
                    if world_atoms else WORKFLOW_FINAL_ANSWER_PROMPT
                )
        generalized.steps = self._order_and_wire(
            generalized.steps,
            generalized.applicability.problem_class,
        )
        if not generalized.applicability.description:
            generalized.applicability.description = self.class_descriptions.get(
                generalized.applicability.problem_class,
                "Reusable spatial reasoning route.",
            )
         # 4. 重新扫描这个工作流到底需要哪些外部变量输入（比如是否需要 $slot.event_type）
        generalized.applicability.required_slots = self._required_slots(generalized.steps)
        return generalized

    def mutate(
        self,
        parent: WorkflowSpec,
        mutation: MutationSpec,
        source_task_id: str,
        tool_hints: Dict[str, str] = None,
        slot_bindings: Dict[str, str] = None,
        question: str = "",
    ) -> WorkflowSpec:
        """
        把参数变异原子 (mutation.selected_atoms) 植入到原有的 JSON 工作流中。
        """
        # 1. 先对原工作流做一次泛化清理 (把一些硬编码的东西换成占位符)
        generalized_parent = self.generalize(parent)
        steps = copy.deepcopy(generalized_parent.steps)
        hints = tool_hints or {}
        slots = slot_bindings or {}
        # 2. 遍历大模型挑选出来的变异原子（比如选了 yolo改低阈值 和 增加裁剪工具）
        for atom in mutation.selected_atoms:
            self._apply_atom(
                steps,
                atom,
                generalized_parent.applicability,
                hints,
                slots,
            )
        applicability = copy.deepcopy(generalized_parent.applicability)
        steps = self._order_and_wire(steps, applicability.problem_class)
        applicability.required_slots = self._required_slots(steps)
        applicability.required_tools = list(dict.fromkeys(
            step.tool_name for step in steps
        ))
        workflow_id = self._workflow_id(applicability.problem_class, steps)
        return WorkflowSpec(
            workflow_id=workflow_id,
            name=f"{applicability.problem_class}_route_{workflow_id[-8:]}",
            applicability=applicability,
            steps=steps,
            derived_from_workflow_id=parent.workflow_id,
            mutation_direction={"selected_atom_ids": [
                atom.atom_id for atom in mutation.selected_atoms
            ]},
            source_task_ids=[source_task_id],
        )

    @staticmethod
    def workflow_signature(workflow: WorkflowSpec) -> str:
        steps = normalize_workflow_steps(workflow.steps)
        payload = [
            {
                "tool": step.tool_name,
                "args": step.args,
                "depends_on": step.depends_on,
                "atoms": sorted(atom.atom_id for atom in step.param_atoms),
            }
            for step in steps
        ]
        return json.dumps(payload, sort_keys=True, ensure_ascii=True)

    @staticmethod
    def _apply_atom(
        steps: List[WorkflowStep],
        atom: ParamAtom,
        applicability: ApplicabilitySpec,
        tool_hints: Dict[str, str],
        slot_bindings: Dict[str, str],
    ) -> None:
        """
        【手术刀核心逻辑】根据原子的类型，决定是修改现有步骤，还是插入新步骤。
        """
        # 在现有的步骤里找，看看有没有原子里提到的工具（比如要改 yolo 阈值，先看看当前流里有没有 yolo）
        matching = [step for step in steps if step.tool_name == atom.tool_name]
        if matching:
            # 路线 A：工作流里已经有这个工具了，直接改参数！
            targets = matching if atom.kind == "numerical" else [matching[-1]]
            for step in targets:
                if atom.kind == "numerical":
                    step.args[atom.axis] = WorkflowMutator._numeric_value(atom.value)
                step.param_atoms = WorkflowMutator._replace_axis(step.param_atoms, atom)
                if atom.kind == "world_model":
                    step.args["query"] = WorkflowMutator._semantic_query_for_atoms(
                        step.param_atoms,
                        applicability,
                    )
            return
        # 路线 B：工作流里没有这个工具（这是一种 structural 结构突变），需要无中生有插一个新步骤！
        # 调用 _steps_for_atom 生成一个全新的 WorkflowStep 塞进步骤列表里。
        steps.extend(
            WorkflowMutator._steps_for_atom(
                atom,
                applicability,
                tool_hints,
                slot_bindings,
            )
        )

    @staticmethod
    def _steps_for_atom(
        atom: ParamAtom,
        applicability: ApplicabilitySpec,
        tool_hints: Dict[str, str],
        slot_bindings: Dict[str, str],
    ) -> List[WorkflowStep]:
        if atom.tool_name == "embeddingTool":
            return [WorkflowStep(
                tool_name="embeddingTool",
                args={
                    "file_path": "$image",
                    "event_type": "$slot.event_type",
                },
                param_atoms=[atom],
                purpose=atom.description,
            )]
        if atom.tool_name == "MLLM":
            args = {
                "file": "$evidence_image",
                "filename": "$filename",
                "query": WorkflowMutator._semantic_query_for_atoms(
                    [atom], applicability
                ),
                "tool": "qwen36Tool",
            }
            return [WorkflowStep(
                tool_name=atom.tool_name,
                args=args,
                param_atoms=[atom],
                purpose=atom.description,
            )]
        if atom.tool_name == "sam3":
            query = str(tool_hints.get("sam3") or "").strip()
            if not query:
                query = applicability.problem_class
            return [WorkflowStep(
                tool_name="sam3",
                args={
                    "file": "$image",
                    "filename": "$filename",
                    "query": query,
                    "threshold": WorkflowMutator._numeric_value(atom.value),
                    "tool": "sam3Tool",
                },
                param_atoms=[atom],
                purpose=atom.description,
            )]
        if atom.tool_name == "yoloTool":
            return [WorkflowStep(
                tool_name="yoloTool",
                args={
                    "file": "$image",
                    "filename": "$filename",
                    "threshold": WorkflowMutator._numeric_value(atom.value),
                },
                param_atoms=[atom],
                purpose=atom.description,
            )]
        if atom.tool_name == "groundingdino":
            query = str(tool_hints.get("groundingdino") or "").strip()
            if not query:
                query = applicability.problem_class
            return [WorkflowStep(
                tool_name="groundingdino",
                args={
                    "query": query,
                    "file": "$image",
                    "filename": "$filename",
                    "box_threshold": (
                        WorkflowMutator._numeric_value(atom.value)
                        if atom.axis == "box_threshold" else 0.35
                    ),
                    "text_threshold": 0.25,
                },
                param_atoms=[atom],
                purpose=atom.description,
            )]
        if atom.tool_name == "paddleOcrTool":
            args = {"file": "$image", "filename": "$filename"}
        elif atom.tool_name in {"paddleHeadDetTool", "paddlePedriderDetTool"}:
            args = {
                "file": "$image",
                "filename": "$filename",
                "tool": atom.tool_name,
            }
        elif atom.tool_name in {"crop_detections", "picRelativeCut"}:
            args = {
                "file": "$image",
                "detections": "",# 注意：这里故意留空！在后面的 _order_and_wire 步骤中，会自动把上游 YOLO 的结果路径注入到这里
                "folder": "spatialskillgrowth",
                "score": "0.5",
                "className": tool_hints.get(atom.tool_name, ""),
            }
        elif atom.tool_name == "python_code_sandbox":
            args = {"code": ""}
        elif atom.tool_name == "unidepth":
            args = {
                "detections": "",
                "file": "$image",
                "filename": "$filename",
            }
        else:
            args = copy.deepcopy(atom.args)
        return [WorkflowStep(
            tool_name=atom.tool_name,
            args=args,
            param_atoms=[atom],
            purpose=atom.description,
        )]

    @staticmethod
    def _normalize_args(
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = copy.deepcopy(args)
        for key in list(normalized):
            if key in {"file", "file_path", "image", "image_path"}:
                normalized[key] = "$image"
            elif key == "filename":
                normalized[key] = "$filename"
            elif key == "query" and tool_name == "MLLM":
                normalized[key] = WORKFLOW_NORMALIZED_QUERY_PROMPT
            elif key == "event_type" and tool_name == "embeddingTool":
                normalized[key] = "$slot.event_type"
            elif key == "detections":
                normalized[key] = ""
            elif key == "folder" and tool_name in {"crop_detections", "picRelativeCut"}:
                normalized[key] = "spatialskillgrowth_crops"
        return normalized

    @staticmethod
    def _compact_steps(
        steps: List[WorkflowStep],
        problem_class: str,
    ) -> List[WorkflowStep]:
        if not steps:
            return []
        reasoning_steps = [step for step in steps if step.tool_name == "MLLM"]
        evidence_steps = [step for step in steps if step.tool_name != "MLLM"]
        # 2. 如果整个过程根本没有用到 MLLM (说明这是一个纯判断任务，比如直接调 embeddingTool 就算出结果了)
        if not reasoning_steps:
            embedding_steps = [
                step for step in evidence_steps if step.tool_name == "embeddingTool"
            ]
            if embedding_steps:
                return embedding_steps[:1]
            return (
                evidence_steps[:4]
                + [WorkflowMutator._default_step(problem_class)]
            )
        # 3. 如果用到了 MLLM，提取最后一次 MLLM 调用作为“最终判决节点”
        final_step = (
            copy.deepcopy(reasoning_steps[-1])
            if reasoning_steps else WorkflowMutator._default_step(problem_class)
        )
        # 强制覆盖最后一步的 prompt，要求它给出最终答案 (覆盖掉大模型在探索时可能说的废话)
        final_step.args["query"] = WORKFLOW_FINAL_ANSWER_PROMPT
        final_step.purpose = "汇总已收集的视觉证据并生成最终答案。"
        return evidence_steps[:4] + [final_step]

    @staticmethod
    def _order_and_wire(
        steps: List[WorkflowStep],
        problem_class: str,
    ) -> List[WorkflowStep]:
        """
        AI 生成的步骤通常是散装的，这里用硬逻辑把它们的顺序排好，并把变量连起来。
        """
        # 1. 强行排序：先独立工具 -> 再依赖工具 -> 最后推理模型 (MLLM)
        reasoning = [step for step in steps if step.tool_name == "MLLM"]
        evidence = [step for step in steps if step.tool_name != "MLLM"]
        independent = [step for step in evidence if step.tool_name not in DEPENDENT_TOOLS]
        dependent = [step for step in evidence if step.tool_name in DEPENDENT_TOOLS]
        ordered = independent + dependent
        if reasoning:
            ordered.append(reasoning[-1])
        normalized = normalize_workflow_steps(ordered)
        # 3. 自动注入上游数据 (Dependency Injection)
        for index, step in enumerate(normalized):
            if step.tool_name not in DEPENDENT_TOOLS:
                continue
            producer_tools = compatible_producers(step.tool_name)
            producer = next(
                (
                    previous
                    for previous in reversed(normalized[:index])
                    if previous.tool_name in producer_tools
                ),
                None,
            )
            if not producer:
                continue
            step.depends_on = [producer.step_id]
            # 最精妙的一步：把上游工具的结果输出路径，作为魔法变量塞给当前工具！
            # 比如把 `$step.yolo_1.detections_json` 塞给 crop 工具的 detections 参数。
            reference = f"$step.{producer.step_id}.detections_json"
            if step.tool_name in {"crop_detections", "picRelativeCut"}:
                step.args["detections"] = reference
            elif step.tool_name == "unidepth":
                step.args["detections"] = reference
            elif step.tool_name == "python_code_sandbox":
                step.args["code"] = PYTHON_DETECTION_SUMMARY_CODE.replace(
                    "__DETECTIONS__", reference
                )
        # 4. 如果最后一步是 MLLM，让它依赖前面所有收集证据的工具
        if normalized and normalized[-1].tool_name == "MLLM":
            final_step = normalized[-1]
            final_step.depends_on = [
                step.step_id for step in normalized[:-1]
            ]
            if normalized[:-1]:
                final_step.args["file"] = "$evidence_image"
                world_atoms = [
                    atom for atom in final_step.param_atoms
                    if atom.kind == "world_model"
                ]
                final_step.args["query"] = (
                    WorkflowMutator._semantic_query_for_atoms(
                        world_atoms,
                        ApplicabilitySpec(problem_class),
                    )
                    if world_atoms else WORKFLOW_FINAL_ANSWER_PROMPT
                )
        return normalized

    @staticmethod
    def _default_step(problem_class: str) -> WorkflowStep:
        return WorkflowStep(
            tool_name="MLLM",
            args={
                "file": "$evidence_image",
                "filename": "$filename",
                "query": WORKFLOW_FINAL_ANSWER_PROMPT,
                "tool": "qwen36Tool",
            },
            purpose=f"依据图像证据判断 {problem_class} 异常事件。",
        )

    @staticmethod
    def _embedding_step(problem_class: str) -> WorkflowStep:
        return WorkflowStep(
            tool_name="embeddingTool",
            args={
                "file_path": "$media",
                "event_type": "$slot.event_type",
            },
            purpose=f"检测 {problem_class} 异常事件。",
        )

    @staticmethod
    def _replace_axis(atoms: List[ParamAtom], new_atom: ParamAtom) -> List[ParamAtom]:
        kept = [
            atom for atom in atoms
            if not (atom.tool_name == new_atom.tool_name and atom.axis == new_atom.axis)
        ]
        return kept + [new_atom]

    @staticmethod
    def _numeric_value(value: str) -> float:
        return {"low": 0.3, "medium": 0.5, "high": 0.7}.get(value, 0.5)

    @staticmethod
    def _semantic_query_for_atoms(
        atoms: List[ParamAtom],
        applicability: ApplicabilitySpec,
    ) -> str:
        scope_atom = next((atom for atom in atoms if atom.axis == "scope"), None)
        scope = (
            "局部区域"
            if scope_atom and scope_atom.value == "local_regions"
            else "完整图像"
        )
        requirements = "; ".join(
            atom.description.rstrip(".")
            for atom in atoms
            if atom.kind == "world_model" and atom.description
        ) or "使用明确的视觉证据"
        return WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT.format(
            scope=scope,
            problem_class=applicability.problem_class,
            requirements=requirements,
        )

    @staticmethod
    def _step_purpose(tool_name: str, problem_class: str) -> str:
        if tool_name == "MLLM":
            return f"依据图像和已收集证据判断 {problem_class}。"
        if tool_name == "embeddingTool":
            return f"使用精确 event_type 检测 {problem_class} 异常事件。"
        if tool_name == "sam3":
            return "分割运行时指定目标并收集边界框。"
        if tool_name == "groundingdino":
            return "用开放词汇检测定位运行时指定目标并收集边界框。"
        if tool_name == "unidepth":
            return "估计已有检测框内目标的度量深度。"
        if tool_name in PIXEL_DETECTION_TOOLS:
            return "定位可见目标并获取边界框证据。"
        if tool_name in {"crop_detections", "picRelativeCut"}:
            return "根据兼容检测框生成重点观察区域。"
        if tool_name == "python_code_sandbox":
            return "计算已有检测证据的结构化摘要。"
        return f"使用 {tool_name} 收集支持证据。"

    @staticmethod
    def _workflow_id(problem_class: str, steps: List[WorkflowStep]) -> str:
        signature = WorkflowMutator.workflow_signature(WorkflowSpec(
            workflow_id="",
            name="",
            applicability=ApplicabilitySpec(problem_class),
            steps=steps,
        ))
        digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
        return f"{problem_class}_{digest}"

    @staticmethod
    def _required_slots(steps: Iterable[WorkflowStep]) -> List[str]:
        serialized = json.dumps(
            [step.args for step in steps], ensure_ascii=False, default=str
        )
        slots = re.findall(r"\$slot\.([A-Za-z0-9_]+)", serialized)
        return list(dict.fromkeys(slots))


def build_anomaly_baseline_workflow(event_type: str) -> WorkflowSpec:
    """构造冻结视频推理的原视频 embeddingTool 并行通道。"""
    if event_type not in ANOMALY_EVENT_TYPES:
        raise ValueError(f"不支持的异常事件类别：{event_type}")
    step = WorkflowMutator._embedding_step(event_type)
    workflow_id = WorkflowMutator._workflow_id(event_type, [step])
    return WorkflowSpec(
        workflow_id=workflow_id,
        name=f"{event_type}_embedding_baseline",
        applicability=ApplicabilitySpec(
            problem_class=event_type,
            required_slots=["event_type"],
            required_tools=["embeddingTool"],
            description=f"使用原始视频 embeddingTool 检测 {event_type} 异常事件。",
            exclusions="只适用于视频输入；图片和视频抽样帧禁止使用。",
            capability_boundary="必须取得 embeddingTool 的异常判断和判定阈值。",
        ),
        steps=[step],
        status="provisional",
        mutation_mode="extracted",
    )


def build_anomaly_image_baseline_workflow(event_type: str) -> WorkflowSpec:
    """构造图片任务未命中已验证 Skill 时使用的单步 MLLM 基线。"""
    if event_type not in ANOMALY_EVENT_TYPES:
        raise ValueError(f"不支持的异常事件类别：{event_type}")
    step = WorkflowMutator._default_step(event_type)
    workflow_id = WorkflowMutator._workflow_id(event_type, [step])
    return WorkflowSpec(
        workflow_id=workflow_id,
        name=f"{event_type}_image_baseline",
        applicability=ApplicabilitySpec(
            problem_class=event_type,
            required_tools=["MLLM"],
            description=f"使用单张图片或视频代表帧判断 {event_type} 异常事件。",
            exclusions="不处理原始视频时序，只依据当前图片证据。",
            capability_boundary="必须取得 MLLM 基于可见画面的明确判断。",
        ),
        steps=[step],
        status="provisional",
        mutation_mode="extracted",
    )
