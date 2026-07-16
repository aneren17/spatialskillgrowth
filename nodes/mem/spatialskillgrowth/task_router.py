"""Omni3D 分类、槽位抽取与确定性工具可用性策略。"""

from __future__ import annotations

import json
from typing import Dict, List, Mapping, Optional

from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    ANOMALY_EVENT_TYPES,
    class_metadata_for,
    has_benchmark_profile,
    normalize_benchmark,
    problem_classes_for,
)
from nodes.mem.spatialskillgrowth.llm_utils import invoke_json
from prompt.spatialskillgrowth_prompts import (
    PROBLEM_CLASSIFIER_PROMPT,
    SLOT_EXTRACTION_PROMPT,
)


DEFAULT_SLOTS = {
    "event_type": "",
    "target_a": "",
    "target_b": "",
    "sam_query_a": "",
    "sam_query_b": "",
    "reference_frame": "none",
    "reference_entity": "",
    "reference_value": "",
    "reference_unit": "",
    "measurement_dimension": "",
    "operation": "",
}
SLOT_WORD_LIMITS = {
    "sam_query_a": 3,
    "sam_query_b": 3,
}
CLOSED_SET_DETECTION_TOOLS = {
    "paddleHeadDetTool",
    "paddlePedriderDetTool",
}


class BenchmarkProblemClassifier:
    """优先采用数据集专用标签；无标签时由多模态 LLM 分类。"""

    def __init__(
        self,
        llm,
        benchmark: str = "omni3d",
        problem_classes: Optional[List[str]] = None,
        class_metadata: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        self.llm = llm
        self.benchmark = normalize_benchmark(benchmark)
        supplied_classes = [
            str(item).strip() for item in problem_classes or [] if str(item).strip()
        ]
        self.problem_classes = tuple(dict.fromkeys(
            supplied_classes or problem_classes_for(self.benchmark)
        ))
        self.metadata = class_metadata or class_metadata_for(self.benchmark)
        self.allow_dynamic_problem_classes = not has_benchmark_profile(self.benchmark)

    def classify(
        self,
        question: str,
        image_paths: List[str],
        fixed_problem_class: str = "",
    ) -> Dict:
        if fixed_problem_class:
            if fixed_problem_class not in self.problem_classes:
                if not self.allow_dynamic_problem_classes:
                    raise ValueError(
                        f"Unknown {self.benchmark} problem class: {fixed_problem_class}"
                    )
                self.problem_classes = (*self.problem_classes, fixed_problem_class)
            return {
                "problem_class": fixed_problem_class,
                "reason": "Provided by benchmark-specific annotation.",
                "source": "benchmark",
            }
        definitions = []
        for name in self.problem_classes:
            metadata = self.metadata.get(name, {})
            definitions.append({
                "name": name,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "aliases": metadata.get("aliases", []),
            })
        prompt = PROBLEM_CLASSIFIER_PROMPT.format(
            class_definitions=json.dumps(definitions, ensure_ascii=False),
            question=question,
        )
        parsed = invoke_json(self.llm, prompt, image_paths)
        problem_class = str(parsed.get("problem_class") or "")
        if problem_class not in self.problem_classes:
            raise ValueError(f"Classifier returned invalid problem class: {problem_class}")
        return {
            "problem_class": problem_class,
            "reason": str(parsed.get("reason") or ""),
            "source": "multimodal_llm",
        }


class SlotExtractor:
    def __init__(self, llm):
        self.llm = llm

    def extract(
        self,
        question: str,
        image_paths: List[str],
        problem_class: str,
    ) -> Dict[str, str]:
        prompt = SLOT_EXTRACTION_PROMPT.format(
            problem_class=problem_class,
            question=question,
        )
        try:
            parsed = invoke_json(self.llm, prompt, image_paths)
        except Exception:
            return dict(DEFAULT_SLOTS)
        return {
            key: _compact_value(
                (
                    problem_class
                    if key == "event_type" and problem_class in ANOMALY_EVENT_TYPES
                    else parsed.get(key)
                )
                or (
                    parsed.get("target_a")
                    if key == "sam_query_a"
                    else parsed.get("target_b") if key == "sam_query_b" else ""
                ),
                SLOT_WORD_LIMITS.get(key, 8),
            )
            for key in DEFAULT_SLOTS
        }


class ToolAvailabilityPolicy:
    """只根据显式输入模态和工具契约做确定性剪枝，不分析描述文本。"""

    def select(
        self,
        registry: Mapping[str, object],
        allowed_closed_set_tools: Optional[List[str]] = None,
    ) -> Dict:
        allowed_closed = set(allowed_closed_set_tools or [])
        selected = []
        excluded = []
        decisions = []
        for tool_name in registry:
            scope = (
                "closed_set_detector"
                if tool_name in CLOSED_SET_DETECTION_TOOLS
                else "general"
            )
            keep = True
            reason = "保留通用工具。"
            if scope == "closed_set_detector" and tool_name not in allowed_closed:
                keep = False
                reason = "当前任务没有显式启用该闭集检测器。"
            if keep:
                selected.append(tool_name)
            else:
                excluded.append(tool_name)
            decisions.append({
                "tool_name": tool_name,
                "scope": scope,
                "decision": "keep" if keep else "exclude",
                "reason": reason,
            })
        return {
            "selected_tools": selected,
            "excluded_tools": excluded,
            "tool_decisions": decisions,
        }


class TaskPlanner:
    def __init__(self, classifier: BenchmarkProblemClassifier, slots: SlotExtractor, tools: ToolAvailabilityPolicy):
        self.classifier = classifier
        self.slots = slots
        self.tools = tools

    def plan(
        self,
        question: str,
        image_paths: List[str],
        registry: Mapping[str, object],
        fixed_problem_class: str = "",
    ) -> Dict:
        classification = self.classifier.classify(
            question, image_paths, fixed_problem_class=fixed_problem_class
        )
        problem_class = classification["problem_class"]
        if problem_class in ANOMALY_EVENT_TYPES:
            if len(image_paths) != 1:
                raise ValueError("异常检测任务必须且只能输入一个视频或图像文件。")
            slot_bindings = dict(DEFAULT_SLOTS)
            slot_bindings["event_type"] = problem_class
        else:
            slot_bindings = self.slots.extract(question, image_paths, problem_class)
        tool_plan = self.tools.select(registry)
        if problem_class in ANOMALY_EVENT_TYPES and "embeddingTool" not in tool_plan[
            "selected_tools"
        ]:
            raise RuntimeError("异常检测运行时没有注册必需的 embeddingTool。")
        return {
            "problem_class": problem_class,
            "classification": classification,
            "slot_bindings": slot_bindings,
            **tool_plan,
        }


def _compact_value(value, max_words: int) -> str:
    return " ".join(str(value or "").strip().split()[:max_words])
