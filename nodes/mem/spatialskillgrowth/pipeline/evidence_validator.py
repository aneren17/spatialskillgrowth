"""异常检测结果的证据契约验证。"""

from nodes.mem.spatialskillgrowth.core.models import EvidenceDecision
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import (
    extract_anomaly_result,
)


class AnomalyEvidenceValidator:
    """
    针对“异常检测”场景的专门校验器。
    核心原则：AI 的文本回答、底层工具（embeddingTool）的判断、检测的目标类别以及判定的阈值，
    这四者必须在逻辑上严丝合缝，缺一不可。
    """

    def validate(
        self,
        event_type,
        question,
        answer,
        result,# 包含了整个工具调用轨迹(trajectory)的详细运行结果
        media_paths,
    ):
        anomaly = extract_anomaly_result(result)
        normalized_answer = str(answer or "").strip().lower()
        answer_decision = ""
        if normalized_answer in {"是", "yes", "true"}:
            answer_decision = "是"
        elif normalized_answer in {"否", "no", "false"}:
            answer_decision = "否"
        
        # 校验阈值 (Threshold) 数据类型的合法性
        # 在异常检测中，必须要有一个具体的数值阈值（0到1之间）来做判断，不能是 None 或者布尔值
        threshold = anomaly["threshold"]
        threshold_is_number = isinstance(threshold, (int, float))
        if isinstance(threshold, bool):
            threshold_is_number = False

        # 4. 【核心契约项】建立必须全部满足的 7 条硬性规则（True 代表通过）
        checks = {
            # 规则1: 异常检测框架规定，一次只能处理 1 个视频或图像文件，不能多也不能少。
            "single_media_input": len(media_paths) == 1,
            
            # 规则2: 整个工作流的执行过程不能有抛出崩溃或未捕获的错误。
            "successful_result": bool(result.get("success")),
            
            # 规则3: 必须实质性地调用了 `embeddingTool`（防止 AI 纯靠语言模型瞎猜）。
            "embedding_called": "embeddingTool" in set(result.get("used_tools") or []),
            
            # 规则4: 工具实际检测的异常类型，必须和任务要求的类型完全一致。
            # （防止任务要求测“摔倒”，工具却去测了“火焰”）。
            "event_type_matches": anomaly["event_type"] == event_type,
            
            # 规则5: 工具必须给出了明确的判断（不能返回 None 或异常状态）。
            "decision_present": anomaly["is_anomaly"] is not None,
            
            # 规则6: 最终输出的文本答案，必须和底层工具的判断结果保持一致！
            # （防止工具说“没有异常”，但 AI 最后由于幻觉总结回答“是，有异常”）。
            "answer_matches_decision": (
                bool(answer_decision) and answer_decision == anomaly["decision"]
            ),
            
            # 规则7: 前面校验过的，阈值必须是个合法的数字。
            "threshold_numeric": threshold_is_number,
        }
        failed_checks = []
        for name, passed in checks.items():
            if not passed:
                failed_checks.append(name)
        accepted = not failed_checks
        if accepted:
            reason = "embeddingTool 异常判断、event_type 和阈值验证均通过。"
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
