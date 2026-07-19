"""根据已知异常类别生成确定性的工具计划。"""

from nodes.mem.spatialskillgrowth.core.anomaly_events import ANOMALY_EVENT_TYPES

#这里添加未来更多工具的扩展
CLOSED_SET_DETECTION_TOOLS = {
    # "paddleHeadDetTool",
    # "paddlePedriderDetTool",
}


class TaskPlanner:
    """输入已经带 event_type，不再调用 LLM 做类别分类或槽位抽取。"""

    def plan(self, event_type, media_paths, registry):
        if event_type not in ANOMALY_EVENT_TYPES:
            raise ValueError("不支持的异常事件类别：" + str(event_type))
        if len(media_paths) != 1:
            raise ValueError("异常检测任务必须且只能输入一个视频或图像文件。")
        if "embeddingTool" not in registry:
            raise RuntimeError("异常检测运行时没有注册必需的 embeddingTool。")

        selected_tools = []
        excluded_tools = []
        tool_decisions = []
        for tool_name in registry:
            if tool_name in CLOSED_SET_DETECTION_TOOLS:
                excluded_tools.append(tool_name)
                decision = "exclude"
                reason = "该闭集检测器未针对当前异常类别显式启用。"
            else:
                selected_tools.append(tool_name)
                decision = "keep"
                reason = "该工具可参与异常证据收集。"
            tool_decisions.append({
                "tool_name": tool_name,
                "decision": decision,
                "reason": reason,
            })

        return {
            "problem_class": event_type,
            "slot_bindings": {"event_type": event_type},
            "selected_tools": selected_tools,
            "excluded_tools": excluded_tools,
            "tool_decisions": tool_decisions,
        }
