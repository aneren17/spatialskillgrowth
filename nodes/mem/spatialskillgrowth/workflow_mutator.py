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
                        f"Localize ${slot_name} and collect its mask and xyxy boxes."
                        if "box" in atom.value else
                        f"Localize ${slot_name}."
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
            if key in {"file", "image", "image_path"}:
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
        final_step = (
            copy.deepcopy(reasoning_steps[-1])
            if reasoning_steps else WorkflowMutator._default_step(problem_class)
        )
        final_step.args["query"] = WORKFLOW_FINAL_ANSWER_PROMPT
        final_step.purpose = "Synthesize collected visual evidence into the final answer."
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
        role = {
            "counting": "counting",
            "size": "size comparison",
            "distance_depth": "depth ordering",
            "orientation": "orientation",
        }.get(problem_class, "spatial relationship")
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
            "localized regions"
            if scope_atom and scope_atom.value == "local_regions"
            else "the full image"
        )
        requirements = "; ".join(
            atom.description.rstrip(".")
            for atom in atoms
            if atom.kind == "world_model" and atom.description
        ) or "Use explicit visual evidence"
        return WORKFLOW_COMBINED_SEMANTIC_ANSWER_PROMPT.format(
            scope=scope,
            problem_class=applicability.problem_class,
            requirements=requirements,
        )

    @staticmethod
    def _step_purpose(tool_name: str, problem_class: str) -> str:
        if tool_name == "MLLM":
            return f"Reason over the image and collected evidence for {problem_class}."
        if tool_name == "sam3":
            return "Segment a runtime-selected target and collect its bounding boxes."
        if tool_name == "groundingdino":
            return "Open-vocabulary localize runtime-selected targets and collect boxes."
        if tool_name == "unidepth":
            return "Estimate metric depth in prior detection boxes."
        if tool_name in PIXEL_DETECTION_TOOLS:
            return "Locate visible objects and obtain bounding-box evidence."
        if tool_name in {"crop_detections", "picRelativeCut"}:
            return "Create a focused region from compatible detection boxes."
        if tool_name == "python_code_sandbox":
            return "Compute a structured summary of prior detection evidence."
        return f"Collect supporting evidence with {tool_name}."

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
