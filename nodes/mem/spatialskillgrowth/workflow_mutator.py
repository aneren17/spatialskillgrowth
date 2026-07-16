"""Extract, generalize, and mutate reusable dependency-aware workflows."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List

from nodes.mem.spatialskillgrowth.models import (
    ApplicabilitySpec,
    MutationSpec,
    ParamAtom,
    WorkflowSpec,
    WorkflowStep,
)
from nodes.mem.spatialskillgrowth.benchmark_profiles import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.tool_contracts import (
    DEPENDENT_TOOLS,
    PIXEL_DETECTION_TOOLS,
    compatible_producers,
)
from nodes.mem.spatialskillgrowth.tool_runtime import normalize_workflow_steps
from prompt.spatialskillgrowth_prompts import (
    WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT,
    WORKFLOW_DEFAULT_ANSWER_PROMPT,
    WORKFLOW_FINAL_ANSWER_PROMPT,
    WORKFLOW_NORMALIZED_QUERY_PROMPT,
)


CLASS_DESCRIPTIONS = {
    "counting": "Count visible instances of the target requested at runtime.",
    "spatial_relation": "Compare the spatial relation between runtime-selected targets.",
    "size": "Compare the visible size or extent of runtime-selected targets.",
    "distance_depth": "Estimate distance or depth order between runtime-selected targets.",
    "orientation": "Determine direction, orientation, or pose in the requested reference frame.",
}
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
        self.class_descriptions = dict(CLASS_DESCRIPTIONS)
        self.class_descriptions.update(class_descriptions or {})

    def register_problem_class(self, problem_class: str, description: str) -> None:
        if problem_class and description:
            self.class_descriptions[problem_class] = description

    def extract(
        self,
        problem_class: str,
        question: str,
        trajectory: List[Dict[str, Any]],
        source_task_id: str,
        derived_from_workflow_id: str = "",
        slot_bindings: Dict[str, str] = None,
    ) -> WorkflowSpec:
        steps: List[WorkflowStep] = []
        seen_calls = set()
        tool_counts: Dict[str, int] = {}
        for item in trajectory or []:
            calls = item.get("tool_calls", []) if isinstance(item, dict) else []
            for call in calls or []:
                tool_name = str(call.get("name") or "")
                if not tool_name:
                    continue
                occurrence = tool_counts.get(tool_name, 0)
                tool_counts[tool_name] = occurrence + 1
                args = self._normalize_args(
                    tool_name,
                    call.get("args") or {},
                    occurrence,
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
        steps = self._compact_steps(steps, problem_class)
        if not steps:
            steps = [self._default_step(problem_class)]
        steps = self._order_and_wire(steps, problem_class)
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
        sam_index = 0
        grounding_index = 0
        for step in generalized.steps:
            if step.tool_name == "sam3":
                slot = "sam_query_a" if sam_index == 0 else "sam_query_b"
                step.args["query"] = f"$slot.{slot}"
                sam_index += 1
            if step.tool_name == "groundingdino":
                multiple_targets = WorkflowMutator._multiple_grounding_targets(
                    step.args.get("query")
                )
                if multiple_targets:
                    step.args["query"] = WorkflowMutator._grounding_query(True)
                else:
                    slot = "target_a" if grounding_index == 0 else "target_b"
                    step.args["query"] = f"$slot.{slot}"
                grounding_index += 1
            if step.tool_name == "MLLM":
                world_atoms = [
                    atom for atom in step.param_atoms if atom.kind == "world_model"
                ]
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
        generalized_parent = self.generalize(parent)
        steps = copy.deepcopy(generalized_parent.steps)
        hints = tool_hints or {}
        slots = slot_bindings or {}
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
        matching = [step for step in steps if step.tool_name == atom.tool_name]
        if matching:
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
            slot_names = ["sam_query_a"]
            if str(
                slot_bindings.get("sam_query_b")
                or slot_bindings.get("target_b")
                or ""
            ).strip():
                slot_names.append("sam_query_b")
            return [
                WorkflowStep(
                    tool_name="sam3",
                    args={
                        "file": "$image",
                        "filename": "$filename",
                        "query": f"$slot.{slot_name}",
                        "threshold": WorkflowMutator._numeric_value(atom.value),
                        "tool": "sam3Tool",
                    },
                    param_atoms=[atom],
                    purpose=(
                        f"定位 ${slot_name}，并收集掩码和 xyxy 边界框。"
                        if "box" in atom.value else
                        f"定位 ${slot_name}。"
                    ),
                )
                for slot_name in slot_names
            ]
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
            has_target_b = bool(str(slot_bindings.get("target_b") or "").strip())
            return [WorkflowStep(
                tool_name="groundingdino",
                args={
                    "query": WorkflowMutator._grounding_query(has_target_b),
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
                "detections": "",
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
        occurrence: int,
    ) -> Dict[str, Any]:
        normalized = copy.deepcopy(args)
        for key in list(normalized):
            if key in {"file", "file_path", "image", "image_path"}:
                normalized[key] = "$image"
            elif key == "filename":
                normalized[key] = "$filename"
            elif key == "query" and tool_name == "MLLM":
                normalized[key] = WORKFLOW_NORMALIZED_QUERY_PROMPT
            elif key == "query" and tool_name == "sam3":
                slot = "sam_query_a" if occurrence == 0 else "sam_query_b"
                normalized[key] = f"$slot.{slot}"
            elif key == "query" and tool_name == "groundingdino":
                if WorkflowMutator._multiple_grounding_targets(normalized[key]):
                    normalized[key] = WorkflowMutator._grounding_query(True)
                else:
                    slot = "target_a" if occurrence == 0 else "target_b"
                    normalized[key] = f"$slot.{slot}"
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
        if not reasoning_steps and problem_class in ANOMALY_EVENT_TYPES:
            embedding_steps = [
                step for step in evidence_steps if step.tool_name == "embeddingTool"
            ]
            return embedding_steps[:1] or [WorkflowMutator._default_step(problem_class)]
        final_step = (
            copy.deepcopy(reasoning_steps[-1])
            if reasoning_steps else WorkflowMutator._default_step(problem_class)
        )
        final_step.args["query"] = WORKFLOW_FINAL_ANSWER_PROMPT
        final_step.purpose = "汇总已收集的视觉证据并生成最终答案。"
        return evidence_steps[:4] + [final_step]

    @staticmethod
    def _order_and_wire(
        steps: List[WorkflowStep],
        problem_class: str,
    ) -> List[WorkflowStep]:
        reasoning = [step for step in steps if step.tool_name == "MLLM"]
        evidence = [step for step in steps if step.tool_name != "MLLM"]
        independent = [step for step in evidence if step.tool_name not in DEPENDENT_TOOLS]
        dependent = [step for step in evidence if step.tool_name in DEPENDENT_TOOLS]
        ordered = independent + dependent
        if reasoning:
            ordered.append(reasoning[-1])
        normalized = normalize_workflow_steps(ordered)
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
            reference = f"$step.{producer.step_id}.detections_json"
            if step.tool_name in {"crop_detections", "picRelativeCut"}:
                step.args["detections"] = reference
            elif step.tool_name == "unidepth":
                step.args["detections"] = reference
            elif step.tool_name == "python_code_sandbox":
                step.args["code"] = PYTHON_DETECTION_SUMMARY_CODE.replace(
                    "__DETECTIONS__", reference
                )
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
        if problem_class in ANOMALY_EVENT_TYPES:
            return WorkflowStep(
                tool_name="embeddingTool",
                args={
                    "file_path": "$image",
                    "event_type": "$slot.event_type",
                },
                purpose=f"检测 {problem_class} 异常事件。",
            )
        role = {
            "counting": "目标计数",
            "size": "尺寸比较",
            "distance_depth": "深度排序",
            "orientation": "方向判断",
        }.get(problem_class, "视觉关系判断")
        return WorkflowStep(
            tool_name="MLLM",
            args={
                "file": "$image",
                "filename": "$filename",
                "query": WORKFLOW_DEFAULT_ANSWER_PROMPT.format(role=role),
                "tool": "qwen36Tool",
            },
            purpose=role,
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
    def _grounding_query(multiple_targets: bool) -> str:
        if multiple_targets:
            return '["$slot.target_a", "$slot.target_b"]'
        return "$slot.target_a"

    @staticmethod
    def _multiple_grounding_targets(value) -> bool:
        text = str(value or "")
        if "$slot.target_b" in text:
            return True
        try:
            parsed = json.loads(text)
        except Exception:
            return False
        return isinstance(parsed, list) and len(parsed) > 1

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
    """构造未命中已验证 Skill 时使用的确定性 embeddingTool 基线。"""
    if event_type not in ANOMALY_EVENT_TYPES:
        raise ValueError(f"不支持的异常事件类别：{event_type}")
    step = WorkflowMutator._default_step(event_type)
    workflow_id = WorkflowMutator._workflow_id(event_type, [step])
    return WorkflowSpec(
        workflow_id=workflow_id,
        name=f"{event_type}_embedding_baseline",
        applicability=ApplicabilitySpec(
            problem_class=event_type,
            required_slots=["event_type"],
            required_tools=["embeddingTool"],
            answer_types=["bool"],
            description=f"使用 embeddingTool 检测 {event_type} 异常事件。",
            exclusions="只适用于输入中已明确给出该 event_type 的视频或图像。",
            capability_boundary="必须取得 embeddingTool 的异常判断和判定阈值。",
        ),
        steps=[step],
        status="provisional",
        mutation_mode="extracted",
    )
