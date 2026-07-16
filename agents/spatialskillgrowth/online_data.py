"""Load benchmark-independent normalized JSON tasks for online exploration."""

import json
import os
import re
from typing import Iterable, List

from nodes.mem.spatialskillgrowth.models import TaskRecord
from nodes.mem.spatialskillgrowth.benchmark_profiles import normalize_benchmark


TASK_LIST_KEYS = ("data", "items", "tasks", "questions")
BENCHMARK_KEYS = ("benchmark", "dataset", "source")


def load_online_tasks(
    dataset_path: str,
    image_root: str,
    limit: int = 0,
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
    return [parse_online_item(item, image_root) for item in raw]


def parse_online_item(item: dict, image_root: str) -> TaskRecord:
    if not isinstance(item, dict):
        raise ValueError("Each online task must be a JSON object")
    task_id = str(
        item.get("question_id")
        or item.get("task_id")
        or item.get("id")
        or _omni_task_id(item)
        or ""
    ).strip()
    question = str(item.get("question") or item.get("query") or "").strip()
    groundtruth = _first_value(item, ("answer", "groundtruth", "ground_truth", "gt"))
    if not task_id or not question:
        raise ValueError("Each online task requires an id and question/query")
    if groundtruth is None or not str(groundtruth).strip():
        raise ValueError(
            f"Online exploration requires a ground-truth answer: {task_id}"
        )
    image_field = _first_value(item, (
        "image_paths",
        "images",
        "image",
        "image_path",
        "image_filename",
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
    return TaskRecord(
        task_id=task_id,
        question=question,
        groundtruth=str(groundtruth).strip(),
        image_paths=image_paths,
        capability=_extract_problem_class(item),
        answer_type=str(item.get("answer_type") or "").strip().lower(),
    )


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
    direct = str(item.get("problem_class") or "").strip()
    if direct:
        return direct
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    metadata_class = str(
        metadata.get("problem_class")
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
