"""根据已知异常类别生成确定性的工具计划。"""

from pathlib import Path

from nodes.mem.spatialskillgrowth.core.anomaly_events import ANOMALY_EVENT_TYPES


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}

#这里添加未来更多工具的扩展
CLOSED_SET_DETECTION_TOOLS = {
    # "paddleHeadDetTool",
    # "paddlePedriderDetTool",
}


class TaskPlanner:
    """输入已经带 event_type，不再调用 LLM 做类别分类或槽位抽取。"""

    def plan(self, event_type, media_paths, registry, media_type=""):
        if event_type not in ANOMALY_EVENT_TYPES:
            raise ValueError("不支持的异常事件类别：" + str(event_type))
        if len(media_paths) != 1:
            raise ValueError("异常检测任务必须且只能输入一个视频或图像文件。")
        media_type = _resolve_media_type(media_paths[0], media_type)
        if media_type == "video" and "embeddingTool" not in registry:
            raise RuntimeError("视频异常检测运行时没有注册 embeddingTool。")

        selected_tools = []
        excluded_tools = []
        tool_decisions = []
        for tool_name in registry:
            if tool_name == "embeddingTool" and media_type != "video":
                excluded_tools.append(tool_name)
                decision = "exclude"
                reason = "embeddingTool 只支持原始视频，图片任务禁止调用。"
            elif tool_name in CLOSED_SET_DETECTION_TOOLS:
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
            "media_type": media_type,
            "slot_bindings": {
                "event_type": event_type,
                "media_type": media_type,
            },
            "selected_tools": selected_tools,
            "excluded_tools": excluded_tools,
            "tool_decisions": tool_decisions,
        }


def _resolve_media_type(media_path, media_type):
    normalized = str(media_type or "").strip().lower()
    if normalized in {"image", "video"}:
        return normalized
    suffix = Path(str(media_path or "")).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    raise ValueError("无法判断输入媒体类型：" + str(media_path))
