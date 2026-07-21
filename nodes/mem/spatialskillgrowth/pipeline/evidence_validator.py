"""异常检测结果的证据契约验证。"""

from nodes.mem.spatialskillgrowth.core.models import EvidenceDecision
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import (
    extract_anomaly_result,
)


class AnomalyEvidenceValidator:
    """校验 embedding 结论和其他图片/抽样帧视觉证据。"""

    def validate(
        self,
        event_type,
        question,
        answer,
        result,# 包含了整个工具调用轨迹(trajectory)的详细运行结果
        media_paths,
        media_type="",
    ):
        anomaly = extract_anomaly_result(result, event_type)
        normalized_answer = str(answer or "").strip().lower()
        answer_decision = ""
        if normalized_answer in {"是", "yes", "true"}:
            answer_decision = "是"
        elif normalized_answer in {"否", "no", "false"}:
            answer_decision = "否"

        observations = result.get("observations") or result.get("evidence") or []
        embedding_succeeded = any(
            str(item.get("tool") or "") == "embeddingTool"
            and bool((item.get("result") or {}).get("ok"))
            for item in observations
        )
        successful_visual_tools = {
            str(item.get("tool") or "")
            for item in observations
            if str(item.get("tool") or "") != "embeddingTool"
            and bool((item.get("result") or {}).get("ok"))
        }
        threshold = anomaly["threshold"]
        threshold_is_number = isinstance(threshold, (int, float))
        if isinstance(threshold, bool):
            threshold_is_number = False

        checks = {
            "single_media_input": len(media_paths) == 1,
            "successful_result": bool(result.get("success")),
            "event_type_matches": anomaly["event_type"] == event_type,
            "decision_present": anomaly["is_anomaly"] is not None,
            "answer_matches_decision": (
                bool(answer_decision) and answer_decision == anomaly["decision"]
            ),
        }
        if embedding_succeeded:
            checks.update({
                "embedding_supported_media": media_type in {"image", "video"},
                "threshold_numeric": threshold_is_number,
            })
        else:
            checks.update({
                "visual_evidence_called": bool(successful_visual_tools),
            })
        failed_checks = []
        for name, passed in checks.items():
            if not passed:
                failed_checks.append(name)
        accepted = not failed_checks
        if accepted:
            if embedding_succeeded:
                reason = "embeddingTool 判断、event_type 和阈值验证均通过。"
            else:
                reason = "图片或视频抽样帧的视觉证据和最终判断验证均通过。"
        else:
            reason = "异常检测验证失败：" + "、".join(failed_checks)
        return EvidenceDecision(
            accepted=accepted,
            validator="anomaly_contract",
            reason=reason,
            contract_checks=checks,
        )


def build_evidence_validator():
    return AnomalyEvidenceValidator()
