"""读取“一个媒体文件 + 一个异常类别”的任务数据。"""

import hashlib
import json
import os
import re

from nodes.mem.spatialskillgrowth.core.models import TaskRecord
from prompt.spatialskillgrowth_prompts import ANOMALY_MEDIA_TOOL_INSTRUCTIONS
from prompt.spatialskillgrowth_prompts import ANOMALY_INPUT_QUESTION_PROMPT
from tools.basicTools.embeddingTool import EVENT_TYPE_ALIASES
from tools.basicTools.embeddingTool import EVENT_TYPE_LABELS
from tools.basicTools.embeddingTool import VALID_EVENT_TYPES


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}
MEDIA_KEYS = ("media_path", "image_path", "video_path", "file_path")
EVENT_TYPES_BY_LABEL = {}

for event_type, labels in EVENT_TYPE_ALIASES.items():
    for label in labels:
        if label not in EVENT_TYPES_BY_LABEL:
            EVENT_TYPES_BY_LABEL[label] = set()
        EVENT_TYPES_BY_LABEL[label].add(event_type)


def load_online_tasks(dataset_path, media_root, limit=0, require_groundtruth=True):
    if not os.path.isfile(dataset_path):
        raise FileNotFoundError("数据集文件不存在：" + str(dataset_path))
    with open(dataset_path, "r", encoding="utf-8") as handle:
        items = json.load(handle)
    if not isinstance(items, list):
        raise ValueError("异常检测数据集必须是 JSON 数组。")
    if limit > 0:
        items = items[:limit]

    tasks = []
    for item in items:
        tasks.append(
            parse_online_item(item, media_root, require_groundtruth)
        )
    return tasks


def parse_online_item(item, media_root, require_groundtruth=True):
    if not isinstance(item, dict):
        raise ValueError("数据集中的每一项必须是 JSON 对象。")
    event_type = resolve_event_type(item.get("event_type"))
    media_value = ""
    for key in MEDIA_KEYS:
        if item.get(key):
            media_value = str(item[key])
            break
    if not media_value:
        raise ValueError("任务缺少 media_path、image_path、video_path 或 file_path。")

    media_path = media_value
    if not os.path.isabs(media_path):
        media_path = os.path.join(media_root, media_path)
    media_path = os.path.abspath(media_path)
    if not os.path.isfile(media_path):
        raise FileNotFoundError("媒体文件不存在：" + media_path)

    groundtruth = str(item.get("answer") or "").strip()
    if require_groundtruth and not groundtruth:
        raise ValueError("探索数据必须提供 answer：" + media_path)
    task_id = str(item.get("task_id") or "").strip()
    if not task_id:
        task_id = anomaly_task_id(media_path, event_type)
    media_type = detect_media_type(media_path)
    return TaskRecord(
        task_id=task_id,
        question=build_anomaly_question(event_type, media_type),
        media_path=media_path,
        event_type=event_type,
        groundtruth=groundtruth,
        media_type=media_type,
    )


def build_anomaly_task(file_path, event_type, task_id="", groundtruth=""):
    media_path = os.path.abspath(str(file_path or "").strip())
    if not os.path.isfile(media_path):
        raise FileNotFoundError("异常检测输入文件不存在：" + media_path)
    event_type = resolve_event_type(event_type)
    media_type = detect_media_type(media_path)
    if not task_id:
        task_id = anomaly_task_id(media_path, event_type)
    return TaskRecord(
        task_id=str(task_id),
        question=build_anomaly_question(event_type, media_type),
        media_path=media_path,
        event_type=event_type,
        groundtruth=str(groundtruth or "").strip(),
        media_type=media_type,
    )


def resolve_event_type(value):
    raw = str(value or "").strip()
    normalized = raw.lower()
    if normalized in VALID_EVENT_TYPES:
        return normalized
    matches = EVENT_TYPES_BY_LABEL.get(raw, set())
    if len(matches) == 1:
        for event_type in matches:
            return event_type
    if len(matches) > 1:
        raise ValueError("中文类别名称不唯一，请使用英文 event_type：" + raw)
    raise ValueError("不支持的异常事件类别：" + raw)


def detect_media_type(file_path):
    suffix = os.path.splitext(str(file_path or ""))[1].lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    raise ValueError("不支持的媒体类型：" + (suffix or "无扩展名"))


def build_anomaly_question(event_type, media_type):
    event_type = resolve_event_type(event_type)
    media_name = "图像"
    if media_type == "video":
        media_name = "视频"
    return ANOMALY_INPUT_QUESTION_PROMPT.format(
        media_name=media_name,
        event_name=EVENT_TYPE_LABELS[event_type],
        event_type=event_type,
        aliases="、".join(EVENT_TYPE_ALIASES[event_type]),
        media_tool_instruction=ANOMALY_MEDIA_TOOL_INSTRUCTIONS[media_type],
    )


def anomaly_task_id(file_path, event_type):
    stem = os.path.splitext(os.path.basename(file_path))[0]
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    if not safe_stem:
        safe_stem = "media"
    digest = hashlib.sha1(os.path.abspath(file_path).encode("utf-8")).hexdigest()
    return event_type + "__" + safe_stem + "__" + digest[:8]
