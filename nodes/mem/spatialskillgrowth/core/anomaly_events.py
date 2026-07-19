"""异常事件类别和 Skill 元数据。"""

from tools.basicTools.embeddingTool import EVENT_TYPE_ALIASES
from tools.basicTools.embeddingTool import EVENT_TYPE_LABELS
from tools.basicTools.embeddingTool import EVENT_TYPE_SOURCE_LABELS
from tools.basicTools.embeddingTool import VALID_EVENT_TYPES


ANOMALY_EVENT_TYPES = tuple(sorted(VALID_EVENT_TYPES))
ANOMALY_CLASS_METADATA = {}

for event_type in ANOMALY_EVENT_TYPES:
    label = EVENT_TYPE_LABELS[event_type]
    aliases = list(EVENT_TYPE_ALIASES[event_type])
    description = (
        "检测输入视频或图像中是否发生“"
        + label
        + "”异常事件（相关显示名称："
        + "、".join(aliases)
        + "）；调用 embeddingTool 时必须使用精确类别 ID `"
        + event_type
        + "`。"
    )
    ANOMALY_CLASS_METADATA[event_type] = {
        "title": label,
        "goal": "判断输入视频或图像中是否发生“" + label + "”异常事件",
        "description": description,
        "aliases": aliases,
        "display_names": dict(EVENT_TYPE_SOURCE_LABELS[event_type]),
        "primary_tool": "embeddingTool",
        "answer_type": "bool",
        "required_slots": ["event_type"],
        "tool_template": {
            "tool_name": "embeddingTool",
            "args": {"file_path": "$media", "event_type": event_type},
        },
        "evidence_requirements": [
            "embeddingTool 必须使用精确 event_type `" + event_type + "`。",
            "工具必须返回明确的异常判断和数值阈值 threshold。",
            "工具失败、类别不一致或缺少检测结果时不得接受答案。",
        ],
    }


def class_metadata_for_anomaly():
    metadata = {}
    for event_type in ANOMALY_EVENT_TYPES:
        metadata[event_type] = dict(ANOMALY_CLASS_METADATA[event_type])
    return metadata
