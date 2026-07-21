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
        + "）；探索只使用图片输入，embedding 可按图片工具参与；图片基线仍为 MLLM；"
        + "视频推理并行调用原视频 embedding 与 Top-K 图片工作流并取 OR；event_type 为 `"
        + event_type
        + "`。"
    )
    ANOMALY_CLASS_METADATA[event_type] = {
        "title": label,
        "goal": "判断输入视频或图像中是否发生“" + label + "”异常事件",
        "description": description,
        "aliases": aliases,
        "display_names": dict(EVENT_TYPE_SOURCE_LABELS[event_type]),
        "primary_tool": "modality_aware",
        "video_primary_tool": "embeddingTool",
        "image_primary_tool": "MLLM",
        "exploration_media_type": "image",
        "video_inference_strategy": "parallel_or",
        "answer_type": "bool",
        "required_slots": ["event_type"],
        "tool_template": {
            "tool_name": "embeddingTool",
            "media_type": "video",
            "args": {"file_path": "$media", "event_type": event_type},
        },
        "evidence_requirements": [
            "视频 embeddingTool 必须使用精确 event_type `" + event_type + "`。",
            "图片 embeddingTool 必须传入图片路径和精确 event_type。",
            "图片基线仍为单步 MLLM；其他图片工作流可按需组合 embeddingTool、图像工具或 MLLM。",
            "视频 embedding 必须返回明确判断和数值阈值；帧工作流必须返回明确判断。",
            "视频推理并行执行 embedding 和 Top-K 检索工作流；任一有效结果为‘是’时最终结果为‘是’。",
            "工具失败、类别不一致或缺少有效证据时不得接受答案。",
        ],
    }


def class_metadata_for_anomaly():
    metadata = {}
    for event_type in ANOMALY_EVENT_TYPES:
        metadata[event_type] = dict(ANOMALY_CLASS_METADATA[event_type])
    return metadata
