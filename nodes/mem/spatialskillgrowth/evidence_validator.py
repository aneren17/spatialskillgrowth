"""按 Omni3D problem class 切换的证据验收策略。"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, List

from nodes.mem.spatialskillgrowth.llm_utils import invoke_json
from nodes.mem.spatialskillgrowth.models import EvidenceDecision
from nodes.mem.spatialskillgrowth.benchmark_profiles import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.tool_runtime import extract_anomaly_result
from prompt.spatialskillgrowth_prompts import SEMANTIC_EVIDENCE_VALIDATION_PROMPT


NUMERICAL_PROBLEM_CLASSES = {
    "metric_dimension_scaling",
    "metric_distance_scaling",
    "dimension_ratio",
    "volume_capacity",
    "linear_fit_stacking",
    "object_counting",
    "count_arithmetic",
    "depth_filtered_counting",
}
LOCALIZATION_TOOLS = {
    "sam3",
    "groundingdino",
    "yoloTool",
    "paddleHeadDetTool",
    "paddlePedriderDetTool",
    "unidepth",
    "picRelativeCut",
    "crop_detections",
}


class EvidenceValidator(ABC):
    @abstractmethod
    def validate(
        self,
        problem_class: str,
        question: str,
        answer: str,
        answer_type: str,
        result: Dict,
        image_paths: List[str],
    ) -> EvidenceDecision:
        raise NotImplementedError


class AnomalyEvidenceValidator(EvidenceValidator):
    """异常检测的不可消融契约：类别匹配、明确判断和阈值必须同时存在。"""

    def validate(self, problem_class, question, answer, answer_type, result, image_paths):
        anomaly = extract_anomaly_result(result)
        normalized_answer = str(answer or "").strip().lower()
        answer_decision = (
            "是" if normalized_answer in {"是", "yes", "true"}
            else "否" if normalized_answer in {"否", "no", "false"}
            else ""
        )
        checks = {
            "single_media_input": len(image_paths) == 1,
            "successful_result": bool(result.get("success")),
            "embedding_called": "embeddingTool" in set(result.get("used_tools") or []),
            "event_type_matches": anomaly["event_type"] == problem_class,
            "decision_present": anomaly["is_anomaly"] is not None,
            "answer_matches_decision": bool(answer_decision) and (
                answer_decision == anomaly["decision"]
            ),
            "threshold_numeric": (
                isinstance(anomaly["threshold"], (int, float))
                and not isinstance(anomaly["threshold"], bool)
            ),
        }
        accepted = all(checks.values())
        failed_checks = [name for name, passed in checks.items() if not passed]
        return EvidenceDecision(
            accepted=accepted,
            validator="anomaly_contract",
            reason=(
                "embeddingTool 异常判断、event_type 和阈值契约均通过。"
                if accepted
                else "异常检测契约失败：" + "、".join(failed_checks)
            ),
            contract_checks=checks,
        )


class AnomalyAwareEvidenceValidator(EvidenceValidator):
    def __init__(self, delegate: EvidenceValidator):
        self.delegate = delegate
        self.anomaly = AnomalyEvidenceValidator()

    def validate(self, problem_class, question, answer, answer_type, result, image_paths):
        if problem_class in ANOMALY_EVENT_TYPES:
            return self.anomaly.validate(
                problem_class, question, answer, answer_type, result, image_paths
            )
        return self.delegate.validate(
            problem_class, question, answer, answer_type, result, image_paths
        )


class NoEvidenceValidator(EvidenceValidator):
    def validate(self, problem_class, question, answer, answer_type, result, image_paths):
        accepted = answer_format_valid(answer, answer_type)
        return EvidenceDecision(
            accepted=accepted,
            validator="none",
            reason="Evidence validation ablated; only final-answer format was checked.",
            contract_checks={"answer_format": accepted},
        )


class StructuralEvidenceValidator(EvidenceValidator):
    """数值类只检查结构化 observation，不读取自然语言来做语义匹配。"""

    def validate(self, problem_class, question, answer, answer_type, result, image_paths):
        observations = [
            item for item in (result.get("observations") or result.get("evidence") or [])
            if isinstance(item, dict)
        ]
        successful = [
            item for item in observations
            if (item.get("result") or {}).get("status") == "success"
            or (item.get("result") or {}).get("ok") is True
        ]
        failed = [
            item for item in observations
            if item not in successful
        ]
        tools = {str(item.get("tool") or "") for item in successful}
        has_synthesis = "MLLM" in tools or bool(result.get("react_answer"))
        requires_localization = problem_class in {
            "object_counting",
            "depth_filtered_counting",
            "count_arithmetic",
            "metric_dimension_scaling",
            "metric_distance_scaling",
            "dimension_ratio",
        }
        checks = {
            "answer_format": answer_format_valid(answer, answer_type),
            "successful_result": bool(result.get("success")) and bool(answer),
            "no_failed_steps": not failed and not list(result.get("failed_step_ids") or []),
            "has_successful_observation": bool(successful),
            "has_synthesis": has_synthesis,
            "has_required_localization": (
                bool(tools.intersection(LOCALIZATION_TOOLS))
                if requires_localization
                else True
            ),
        }
        accepted = all(checks.values())
        failed_checks = [name for name, passed in checks.items() if not passed]
        return EvidenceDecision(
            accepted=accepted,
            validator="structural",
            reason=(
                "All numerical evidence contracts passed."
                if accepted
                else "Failed contracts: " + ", ".join(failed_checks)
            ),
            contract_checks=checks,
        )


class SemanticEvidenceValidator(EvidenceValidator):
    def __init__(self, llm):
        self.llm = llm

    def validate(self, problem_class, question, answer, answer_type, result, image_paths):
        format_valid = answer_format_valid(answer, answer_type)
        if not format_valid:
            return EvidenceDecision(
                accepted=False,
                validator="semantic_llm",
                reason="Candidate answer has the wrong format.",
                contract_checks={"answer_format": False},
            )
        prompt = SEMANTIC_EVIDENCE_VALIDATION_PROMPT.format(
            problem_class=problem_class,
            answer_type=answer_type,
            question=question,
            answer=answer,
            observations=json.dumps(
                result.get("observations") or result.get("evidence") or [],
                ensure_ascii=False,
                default=str,
            )[-10000:],
        )
        try:
            parsed = invoke_json(self.llm, prompt, image_paths)
            accepted = parsed.get("accepted") is True
            reason = str(parsed.get("reason") or "")
        except Exception as exc:
            accepted = False
            reason = f"Semantic evidence judge failed closed: {type(exc).__name__}: {exc}"
        return EvidenceDecision(
            accepted=accepted,
            validator="semantic_llm",
            reason=reason,
            contract_checks={"answer_format": True, "semantic_judge": accepted},
        )


class HybridEvidenceValidator(EvidenceValidator):
    def __init__(self, llm):
        self.structural = StructuralEvidenceValidator()
        self.semantic = SemanticEvidenceValidator(llm)

    def validate(self, problem_class, question, answer, answer_type, result, image_paths):
        if answer_type in {"int", "float"} or problem_class in NUMERICAL_PROBLEM_CLASSES:
            structural = self.structural.validate(
                problem_class, question, answer, answer_type, result, image_paths
            )
            if not structural.accepted:
                return EvidenceDecision(
                    accepted=False,
                    validator="hybrid",
                    reason=structural.reason,
                    contract_checks=structural.contract_checks,
                )
            semantic = self.semantic.validate(
                problem_class, question, answer, answer_type, result, image_paths
            )
            checks = dict(structural.contract_checks)
            checks.update(semantic.contract_checks)
            return EvidenceDecision(
                accepted=semantic.accepted,
                validator="hybrid",
                reason=(
                    "Structural contracts passed; " + semantic.reason
                    if semantic.reason
                    else "Structural contracts passed; semantic judge returned no reason."
                ),
                contract_checks=checks,
            )
        return self.semantic.validate(
            problem_class, question, answer, answer_type, result, image_paths
        )


def build_evidence_validator(strategy: str, llm) -> EvidenceValidator:
    if strategy == "none":
        validator = NoEvidenceValidator()
    elif strategy == "structural":
        validator = StructuralEvidenceValidator()
    elif strategy == "semantic":
        validator = SemanticEvidenceValidator(llm)
    elif strategy == "hybrid":
        validator = HybridEvidenceValidator(llm)
    else:
        raise ValueError(f"Unknown evidence validation strategy: {strategy}")
    return AnomalyAwareEvidenceValidator(validator)


def answer_format_valid(answer: str, answer_type: str) -> bool:
    value = str(answer or "").strip()
    if not value:
        return False
    if answer_type == "int":
        return bool(re.fullmatch(r"[-+]?\d+", value))
    if answer_type == "float":
        return bool(re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", value))
    if answer_type == "bool":
        return value.lower() in {"yes", "no", "是", "否"}
    return len(value.split()) <= 20


# 兼容已有的内部导入；新代码统一使用公开名称。
_answer_format_valid = answer_format_valid
