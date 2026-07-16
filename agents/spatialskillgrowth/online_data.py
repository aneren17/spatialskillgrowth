"""Load benchmark-independent normalized JSON tasks for online exploration."""

import json
import hashlib
import os
import re
from typing import Iterable, List

from nodes.mem.spatialskillgrowth.models import TaskRecord
from nodes.mem.spatialskillgrowth.benchmark_profiles import normalize_benchmark
from prompt.spatialskillgrowth_prompts import ANOMALY_INPUT_QUESTION_PROMPT
from tools.basicTools.embeddingTool import (
    EVENT_TYPE_ALIASES,
    EVENT_TYPE_LABELS,
    VALID_EVENT_TYPES,
)


TASK_LIST_KEYS = ("data", "items", "tasks", "questions")
BENCHMARK_KEYS = ("benchmark", "dataset", "source")
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}
EVENT_TYPES_BY_LABEL = {}
for _event_type, _labels in EVENT_TYPE_ALIASES.items():
    for _label in _labels:
        EVENT_TYPES_BY_LABEL.setdefault(_label, set()).add(_event_type)


def load_online_tasks(
    dataset_path: str,
    image_root: str,
    limit: int = 0,
    require_groundtruth: bool = True,
) -> List[TaskRecord]:
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset file does not exist: {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if isinstance(raw, dict):
        raw = next(
            (raw.get(key) for key in TASK_LIST_KEYS if isinstance(raw.get(key), list)),
            None,
        )
    if not isinstance(raw, list):
        raise ValueError(
            "Online dataset must be a JSON list or contain data/items/tasks/questions"
        )
    if limit > 0:
        raw = raw[:limit]
    return [
        parse_online_item(item, image_root, require_groundtruth=require_groundtruth)
        for item in raw
    ]


def parse_online_item(
    item: dict,
    image_root: str,
    require_groundtruth: bool = True,
) -> TaskRecord:
    if not isinstance(item, dict):
        raise ValueError("Each online task must be a JSON object")
    task_id = str(
        item.get("question_id")
        or item.get("task_id")
        or item.get("id")
        or _omni_task_id(item)
        or ""
    ).strip()
    capability = _resolve_capability(_extract_problem_class(item))
    groundtruth = _first_value(item, ("answer", "groundtruth", "ground_truth", "gt"))
    if require_groundtruth and (groundtruth is None or not str(groundtruth).strip()):
        raise ValueError(
            f"Online exploration requires a ground-truth answer: {task_id}"
        )
    image_field = _first_value(item, (
        "image_paths",
        "images",
        "image",
        "image_path",
        "image_filename",
        "video",
        "video_path",
        "video_filename",
        "file",
        "file_path",
    ))
    image_items: Iterable[str]
    if isinstance(image_field, list):
        image_items = [str(value) for value in image_field if value]
    else:
        image_items = [str(image_field)] if image_field else []
    image_paths = []
    for image_value in image_items:
        candidates = [image_value] if os.path.isabs(image_value) else [
            os.path.join(image_root, image_value),
            os.path.join(os.path.dirname(os.path.normpath(image_root)), image_value),
        ]
        path = next((candidate for candidate in candidates if os.path.exists(candidate)), "")
        if path:
            image_paths.append(os.path.abspath(path))
    if capability in VALID_EVENT_TYPES:
        if len(image_paths) != 1:
            raise ValueError(
                "异常检测输入必须且只能包含一个存在的视频或图像文件："
                f"event_type={capability}, resolved_files={len(image_paths)}"
            )
        media_type = detect_media_type(image_paths[0])
        question = build_anomaly_question(capability, media_type)
        task_id = task_id or anomaly_task_id(image_paths[0], capability)
        answer_type = "bool"
    else:
        question = str(item.get("question") or item.get("query") or "").strip()
        media_type = detect_media_type(image_paths[0]) if len(image_paths) == 1 else ""
        answer_type = str(item.get("answer_type") or "").strip().lower()
    if not task_id or not question:
        raise ValueError("每条任务必须能够确定 task_id 和问题描述。")
    return TaskRecord(
        task_id=task_id,
        question=question,
        groundtruth=str(groundtruth or "").strip(),
        image_paths=image_paths,
        capability=capability,
        answer_type=answer_type,
        media_type=media_type,
    )


def build_anomaly_task(
    file_path: str,
    event_type: str,
    task_id: str = "",
    groundtruth: str = "",
) -> TaskRecord:
    resolved_path = os.path.abspath(str(file_path or "").strip())
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"异常检测输入文件不存在：{resolved_path}")
    resolved_event_type = resolve_event_type(event_type)
    media_type = detect_media_type(resolved_path)
    return TaskRecord(
        task_id=str(task_id or "").strip() or anomaly_task_id(
            resolved_path, resolved_event_type
        ),
        question=build_anomaly_question(resolved_event_type, media_type),
        groundtruth=str(groundtruth or "").strip(),
        image_paths=[resolved_path],
        capability=resolved_event_type,
        answer_type="bool",
        media_type=media_type,
    )


def resolve_event_type(value: str) -> str:
    raw = str(value or "").strip()
    normalized = raw.lower()
    if normalized in VALID_EVENT_TYPES:
        return normalized
    matches = EVENT_TYPES_BY_LABEL.get(raw, set())
    if len(matches) == 1:
        return next(iter(matches))
    if len(matches) > 1:
        raise ValueError(f"中文类别名称对应多个 event_type，请改用英文 ID：{raw}")
    raise ValueError(f"不支持的异常事件类别：{raw}")


def detect_media_type(file_path: str) -> str:
    suffix = os.path.splitext(str(file_path or ""))[1].lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    raise ValueError(f"不支持的异常检测文件类型：{suffix or '无扩展名'}")


def build_anomaly_question(event_type: str, media_type: str) -> str:
    resolved_event_type = resolve_event_type(event_type)
    return ANOMALY_INPUT_QUESTION_PROMPT.format(
        media_name="视频" if media_type == "video" else "图像",
        event_name=EVENT_TYPE_LABELS[resolved_event_type],
        event_type=resolved_event_type,
        aliases="、".join(EVENT_TYPE_ALIASES[resolved_event_type]),
    )


def anomaly_task_id(file_path: str, event_type: str) -> str:
    stem = os.path.splitext(os.path.basename(file_path))[0]
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "media"
    digest = hashlib.sha1(os.path.abspath(file_path).encode("utf-8")).hexdigest()[:8]
    return f"{event_type}__{safe_stem}__{digest}"


def _resolve_capability(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.lower() in VALID_EVENT_TYPES or raw in EVENT_TYPES_BY_LABEL:
        return resolve_event_type(raw)
    return raw


def infer_online_benchmark(dataset_path: str) -> str:
    with open(dataset_path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    candidates = [dataset_path]
    if isinstance(raw, dict):
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        candidates.extend(str(raw.get(key) or "") for key in BENCHMARK_KEYS)
        candidates.extend(str(metadata.get(key) or "") for key in BENCHMARK_KEYS)
        items = next(
            (raw.get(key) for key in TASK_LIST_KEYS if isinstance(raw.get(key), list)),
            [],
        )
    else:
        items = raw if isinstance(raw, list) else []
    if items and isinstance(items[0], dict):
        candidates.extend(str(items[0].get(key) or "") for key in BENCHMARK_KEYS)
    joined = " ".join(candidates).lower()
    if "omni-3d" in joined or "omni_3d" in joined or "omni3d" in joined:
        return "omni3d"
    if "stvqa" in re.sub(r"[^a-z0-9]+", "", joined):
        return "stvqa"
    for candidate in candidates[1:]:
        normalized = normalize_benchmark(candidate)
        if normalized and normalized != "generic":
            return normalized
    return "generic"


def _first_value(item: dict, keys: Iterable[str]):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


def _extract_problem_class(item: dict) -> str:
    direct = str(item.get("problem_class") or item.get("event_type") or "").strip()
    if direct:
        return direct
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    metadata_class = str(
        metadata.get("event_type")
        or metadata.get("problem_class")
        or metadata.get("spatial_problem_class")
        or ""
    ).strip()
    if metadata_class:
        return metadata_class
    capability = str(item.get("capability") or "").strip()
    match = re.search(r"(?:^|,)\s*problem_class=([^,]+)", capability, flags=re.I)
    if match:
        return match.group(1).strip()
    if re.fullmatch(r"[A-Za-z0-9_.-]+", capability):
        return capability
    return ""


def _omni_task_id(item: dict) -> str:
    image_index = str(item.get("image_index") or "").strip()
    question_index = str(item.get("question_index") or "").strip()
    if not image_index:
        return ""
    stem = os.path.splitext(os.path.basename(image_index))[0]
    return f"{stem}_{question_index}" if question_index else stem
