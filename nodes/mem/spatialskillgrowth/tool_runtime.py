"""Typed tool execution and dependency-aware workflow runtime."""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from PIL import Image

from config.spatialskillgrowth_config import (
    SPATIAL_SKILL_GROWTH_PARALLEL_TOOL_WORKERS,
    SPATIAL_SKILL_GROWTH_TOOLS_DIR,
)
from nodes.mem.spatialskillgrowth.models import WorkflowSpec, WorkflowStep
from nodes.mem.spatialskillgrowth.tool_contracts import (
    DEPENDENT_TOOLS,
    PIXEL_DETECTION_TOOLS,
    compatible_producers,
    input_constraints,
    output_type,
    output_types,
)
from utils import load_all_tools


STEP_REFERENCE_PATTERN = re.compile(r"\$step\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)")
SLOT_REFERENCE_PATTERN = re.compile(r"\$slot\.([A-Za-z0-9_]+)")
SEMANTIC_EMPTY_MARKERS = (
    "未检测到可分割的物体",
    "没有检测到物体",
    "no mask",
    "no object detected",
    "no detections",
)
ERROR_PREFIXES = (
    "error ",
    "error:",
    "network error",
    "error executing",
    "error reading",
    "api returned no result",
    "[tool execution failed]",
    "[tool not found]",
    "traceback ",
)
ANOMALY_RESULT_PATTERN = re.compile(
    r"^\s*(是|否)(?:\s*[（(]\s*判定阈值\s*[:：]\s*([^）)]+)\s*[）)])?\s*$"
)
EVIDENCE_IMAGE_PRIORITY = {
    "cropped_images": 3,
    "relative_crop": 3,
    "segmentation_image": 2,
    "pixel_detections": 1,
}


def build_default_registry() -> Dict[str, Any]:
    project_root = Path(__file__).resolve().parents[3]
    tools_dir = Path(SPATIAL_SKILL_GROWTH_TOOLS_DIR)
    if tools_dir.is_absolute():
        try:
            tools_dir = tools_dir.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(
                "SpatialSkillGrowth tools must be inside the project root"
            ) from exc
    if Path.cwd().resolve() != project_root:
        raise RuntimeError(
            "ToolRuntime must be created from the project root so the existing "
            "tool loader can resolve the tools package"
        )
    return {tool.name: tool for tool in load_all_tools(str(tools_dir))}


class ToolRuntime:
    def __init__(self, registry: Optional[Mapping[str, Any]] = None):
        self.registry = dict(registry) if registry is not None else build_default_registry()

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.registry.get(tool_name)
        if tool is None:
            return self._failure(tool_name, f"Tool not found: {tool_name}")
        try:
            prepared_args = self._prepare_args(tool_name, args)
            result = tool.invoke(prepared_args) if hasattr(tool, "invoke") else tool(**prepared_args)
            normalized = self._normalize_result(tool_name, result)
            if tool_name == "embeddingTool" and normalized.get("ok"):
                normalized["data"]["event_type"] = str(
                    prepared_args.get("event_type") or ""
                )
                normalized["data"]["file_path"] = str(
                    prepared_args.get("file_path") or ""
                )
            return normalized
        except Exception as exc:
            return self._failure(tool_name, f"{type(exc).__name__}: {exc}")

    @staticmethod
    def skipped(tool_name: str, error: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "status": "skipped",
            "tool": tool_name,
            "output_type": output_type(tool_name),
            "output_types": sorted(output_types(tool_name)),
            "content": "",
            "data": {},
            "raw": None,
            "error": error,
        }

    @staticmethod
    def _failure(
        tool_name: str,
        error: str,
        raw=None,
        status: str = "error",
        content: str = "",
    ) -> Dict[str, Any]:
        return {
            "ok": False,
            "status": status,
            "tool": tool_name,
            "output_type": output_type(tool_name),
            "output_types": sorted(output_types(tool_name)),
            "content": content,
            "data": {},
            "raw": raw,
            "error": error,
        }

    @staticmethod
    def _prepare_args(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(args or {})
        if tool_name == "sam3":
            constraints = input_constraints(tool_name)
            query_constraints = dict(constraints.get("query") or {})
            query = str(prepared.get("query") or "").strip()
            words = query.split()
            minimum_words = int(query_constraints.get("min_words") or 1)
            maximum_words = int(query_constraints.get("max_words") or 3)
            english_words = all(
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", word)
                for word in words
            )
            if not minimum_words <= len(words) <= maximum_words or not english_words:
                raise ValueError("sam3 query must contain 1-3 English words")
            threshold_constraints = dict(constraints.get("threshold") or {})
            threshold = float(prepared.get("threshold", 0.6))
            minimum = float(threshold_constraints.get("minimum", 0.0))
            maximum = float(threshold_constraints.get("maximum", 1.0))
            if not minimum <= threshold <= maximum:
                raise ValueError(f"sam3 threshold must be between {minimum} and {maximum}")
            prepared["query"] = query
            prepared["threshold"] = threshold
            return prepared
        if tool_name not in {"crop_detections", "picRelativeCut", "unidepth"}:
            return prepared
        detections = ToolRuntime._coerce_detections(prepared.get("detections"))
        if not detections:
            raise ValueError(f"{tool_name} requires non-empty detection boxes")
        if tool_name == "unidepth":
            prepared["detections"] = json.dumps([
                {
                    "cls": str(
                        item.get("cls")
                        or item.get("class_name")
                        or item.get("label")
                        or "object"
                    ),
                    "box": item["bbox"],
                    "score": item.get("score", item.get("confidence", 0.0)),
                }
                for item in detections
            ], ensure_ascii=False)
            return prepared
        if tool_name == "picRelativeCut":
            detections = ToolRuntime._normalize_detection_boxes(
                detections,
                str(prepared.get("file") or ""),
            )
        prepared["detections"] = json.dumps(
            {"detections": detections}, ensure_ascii=False
        )
        return prepared

    @staticmethod
    def _coerce_detections(value) -> List[Dict[str, Any]]:
        parsed = value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except Exception:
                return []
        return ToolRuntime._extract_detections(parsed)

    @staticmethod
    def _normalize_detection_boxes(
        detections: List[Dict[str, Any]],
        image_path: str,
    ) -> List[Dict[str, Any]]:
        needs_normalization = any(
            any(float(value) > 1.0 for value in item.get("bbox", []))
            for item in detections
        )
        if not needs_normalization:
            return detections
        path = Path(image_path)
        if not path.is_file():
            raise ValueError("picRelativeCut needs a local image to normalize pixel boxes")
        with Image.open(path) as image:
            width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("Cannot normalize detections for an empty image")
        normalized = []
        for item in detections:
            x1, y1, x2, y2 = [float(value) for value in item["bbox"]]
            copied = dict(item)
            copied["bbox"] = [x1 / width, y1 / height, x2 / width, y2 / height]
            normalized.append(copied)
        return normalized

    @staticmethod
    def _normalize_result(tool_name: str, raw) -> Dict[str, Any]:
        text = "" if raw is None else str(raw)
        lowered = text.strip().lower()
        if lowered.startswith(ERROR_PREFIXES):
            return ToolRuntime._failure(tool_name, text, raw=raw)
        parsed = ToolRuntime._parse_json(raw)
        if (
            isinstance(parsed, dict)
            and str(parsed.get("status") or "").strip().lower()
            in {"error", "failed", "failure"}
        ):
            error = str(
                parsed.get("message")
                or parsed.get("error")
                or f"{tool_name} returned an error status"
            )
            return ToolRuntime._failure(tool_name, error, raw=raw, content=text)
        if any(marker in lowered for marker in SEMANTIC_EMPTY_MARKERS):
            return ToolRuntime._failure(
                tool_name,
                f"{tool_name} returned no usable evidence",
                raw=raw,
                status="empty",
                content=text,
            )
        anomaly_output = parse_anomaly_tool_output(raw)
        if tool_name == "embeddingTool" and anomaly_output["is_anomaly"] is None:
            return ToolRuntime._failure(
                tool_name,
                "embeddingTool 未返回可识别的异常判断。",
                raw=raw,
                status="invalid",
                content=text,
            )
        detections = ToolRuntime._extract_detections(parsed)
        image_refs = ToolRuntime._extract_image_refs(parsed, text)
        if tool_name in PIXEL_DETECTION_TOOLS and not detections:
            return ToolRuntime._failure(
                tool_name,
                f"{tool_name} returned no detection boxes",
                raw=raw,
                status="empty",
                content=text,
            )
        if tool_name == "unidepth" and not detections:
            return ToolRuntime._failure(
                tool_name,
                "unidepth returned no metric-depth detections",
                raw=raw,
                status="empty",
                content=text,
            )
        if tool_name == "sam3" and not image_refs:
            return ToolRuntime._failure(
                tool_name,
                "sam3 returned no segmentation image",
                raw=raw,
                status="empty",
                content=text,
            )
        if tool_name in {"crop_detections", "picRelativeCut"} and not image_refs:
            return ToolRuntime._failure(
                tool_name,
                f"{tool_name} returned no cropped image",
                raw=raw,
                status="empty",
                content=text,
            )
        data = {
            "detections": detections,
            "detections_json": json.dumps(
                {"detections": detections}, ensure_ascii=False
            ),
            "image_refs": image_refs,
            "image": image_refs[0] if image_refs else "",
            "bbox_format": "xyxy_pixel" if detections else "",
        }
        if tool_name == "embeddingTool":
            data.update(anomaly_output)
        return {
            "ok": True,
            "status": "success",
            "tool": tool_name,
            "output_type": output_type(tool_name),
            "output_types": sorted(output_types(tool_name)),
            "content": text,
            "data": data,
            "raw": raw if isinstance(raw, (dict, list)) else text,
            "error": "",
        }

    @staticmethod
    def _parse_json(value):
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(str(value or ""))
        except Exception:
            return None

    @staticmethod
    def _extract_detections(value) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            detections = [
                ToolRuntime._canonical_detection(item)
                for item in value
                if isinstance(item, dict)
            ]
            detections = [item for item in detections if item]
            if detections:
                return detections
            for item in value:
                found = ToolRuntime._extract_detections(item)
                if found:
                    return found
        if isinstance(value, dict):
            detection = ToolRuntime._canonical_detection(value)
            if detection:
                return [detection]
            for key in ("detections", "originalResponse", "data", "result", "content"):
                if key not in value:
                    continue
                found = ToolRuntime._extract_detections(value[key])
                if found:
                    return found
        return []

    @staticmethod
    def _canonical_detection(value: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        box = value.get("bbox") or value.get("box")
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            return None
        detection = dict(value)
        detection["bbox"] = list(box)
        if not detection.get("class_name"):
            detection["class_name"] = str(
                detection.get("cls")
                or detection.get("label")
                or detection.get("class")
                or ""
            )
        return detection

    @staticmethod
    def _extract_image_refs(value, text: str = "") -> List[str]:
        refs = []
        if isinstance(value, dict):
            for key in ("file", "files", "image", "images", "url"):
                item = value.get(key)
                if isinstance(item, str) and item:
                    refs.append(item)
                elif isinstance(item, list):
                    refs.extend(str(path) for path in item if path)
            for key in ("data", "result", "content"):
                refs.extend(ToolRuntime._extract_image_refs(value.get(key), ""))
        elif isinstance(value, list):
            for item in value:
                refs.extend(ToolRuntime._extract_image_refs(item, ""))
        refs.extend(re.findall(r"https?://[^\s\"']+\.(?:png|jpe?g|webp|bmp)", text, flags=re.I))
        return list(dict.fromkeys(refs))


def execute_workflow_payload(
    payload: Dict[str, Any],
    workflow_value,
    registry: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    workflow = (
        workflow_value
        if isinstance(workflow_value, WorkflowSpec)
        else WorkflowSpec.from_dict(workflow_value)
    )
    runtime = ToolRuntime(registry)
    image_paths = payload.get("image_paths", [])
    image_path = image_paths[0] if isinstance(image_paths, list) and image_paths else ""
    question = str(payload.get("question") or "")
    slots = dict(payload.get("slot_bindings") or payload.get("hints") or {})
    observations = []
    results_by_step: Dict[str, Dict[str, Any]] = {}
    previous = ""
    steps = normalize_workflow_steps(workflow.steps)
    for group_index, group in enumerate(workflow_step_groups(steps)):
        evidence = build_evidence_text(observations)
        evidence_image = _best_evidence_image(observations) or image_path
        requests = []
        skipped = {}
        for index, step in group:
            failed_refs = [
                step_id
                for step_id, _ in _step_references(step.args)
                if (results_by_step.get(step_id) or {}).get("status") != "success"
            ]
            if failed_refs:
                skipped[index] = runtime.skipped(
                    step.tool_name,
                    "Required step did not produce usable evidence: "
                    + ", ".join(failed_refs),
                )
                continue
            args = resolve_workflow_args(
                step.args,
                image_path=image_path,
                question=question,
                previous=previous,
                evidence=evidence,
                step_results=results_by_step,
                slots=slots,
                evidence_image=evidence_image,
            )
            requests.append((index, step, args))
        executed_results = execute_parallel_tools(
            runtime,
            [(step.tool_name, args) for _, step, args in requests],
        )
        result_by_index = {
            index: (step, args, result)
            for (index, step, args), result in zip(requests, executed_results)
        }
        parallel_group = group_index if len(requests) > 1 else None
        for index, step in group:
            if index in skipped:
                args = {}
                result = skipped[index]
            else:
                _, args, result = result_by_index[index]
            results_by_step[step.step_id] = result
            observations.append({
                "step": index,
                "step_id": step.step_id,
                "tool": step.tool_name,
                "parallel_group": parallel_group,
                "purpose": step.purpose,
                "depends_on": list(step.depends_on),
                "args": args,
                "result": result,
            })
            if result["ok"]:
                previous = result["content"]
    answer_source = next(
        (
            item["result"]["content"]
            for item in reversed(observations)
            if item["tool"] == "MLLM" and item["result"].get("ok")
        ),
        "",
    )
    answer = extract_final_answer(answer_source)
    failed = [
        item["step_id"]
        for item in observations
        if item["result"].get("status") != "success"
    ]
    return {
        "success": bool(answer),
        "final_answer": answer,
        "evidence": observations,
        "used_tools": [item["tool"] for item in observations],
        "observations": observations,
        "valid_step_ids": [
            item["step_id"]
            for item in observations
            if item["result"].get("status") == "success"
        ],
        "failed_step_ids": failed,
        "error": "" if answer else "Workflow produced no final answer",
        "workflow_id": workflow.workflow_id,
    }


def normalize_workflow_steps(steps: List[WorkflowStep]) -> List[WorkflowStep]:
    normalized = [WorkflowStep.from_dict(step.to_dict()) for step in steps]
    counts: Dict[str, int] = {}
    used_ids = set()
    for step in normalized:
        base = re.sub(r"[^a-z0-9]+", "_", step.tool_name.lower()).strip("_") or "step"
        counts[base] = counts.get(base, 0) + 1
        if not step.step_id or step.step_id in used_ids:
            step.step_id = f"{base}_{counts[base] - 1}"
        used_ids.add(step.step_id)
    for index, step in enumerate(normalized):
        dependencies = list(dict.fromkeys(step.depends_on))
        dependencies.extend(
            step_id for step_id, _ in _step_references(step.args)
            if step_id not in dependencies
        )
        if step.tool_name in DEPENDENT_TOOLS:
            producers = compatible_producers(step.tool_name)
            producer = next(
                (
                    previous.step_id
                    for previous in reversed(normalized[:index])
                    if previous.tool_name in producers
                ),
                "",
            )
            if producer and producer not in dependencies:
                dependencies.append(producer)
        if step.tool_name == "MLLM":
            for previous in normalized[:index]:
                if previous.tool_name != "MLLM" and previous.step_id not in dependencies:
                    dependencies.append(previous.step_id)
        step.depends_on = dependencies
    return normalized


def workflow_step_groups(
    steps: List[WorkflowStep],
) -> List[List[Tuple[int, WorkflowStep]]]:
    normalized = normalize_workflow_steps(steps)
    remaining = list(enumerate(normalized))
    completed = set()
    groups = []
    while remaining:
        ready = [
            item for item in remaining
            if set(item[1].depends_on).issubset(completed)
        ]
        if not ready:
            cycle = ", ".join(step.step_id for _, step in remaining)
            raise ValueError(f"Workflow contains unresolved dependencies: {cycle}")
        groups.append(ready)
        ready_ids = {step.step_id for _, step in ready}
        completed.update(ready_ids)
        remaining = [item for item in remaining if item[1].step_id not in ready_ids]
    return groups


def execute_parallel_tools(
    runtime: ToolRuntime,
    requests: List[Tuple[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    if len(requests) <= 1:
        return [runtime.execute(*requests[0])] if requests else []
    worker_count = min(
        len(requests),
        max(1, SPATIAL_SKILL_GROWTH_PARALLEL_TOOL_WORKERS),
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(runtime.execute, tool_name, args)
            for tool_name, args in requests
        ]
        return [future.result() for future in futures]


def resolve_workflow_args(
    value,
    image_path: str,
    question: str,
    previous: str,
    evidence: str = "",
    step_results: Optional[Dict[str, Dict[str, Any]]] = None,
    slots: Optional[Dict[str, Any]] = None,
    evidence_image: str = "",
):
    if isinstance(value, dict):
        return {
            key: resolve_workflow_args(
                item,
                image_path=image_path,
                question=question,
                previous=previous,
                evidence=evidence,
                step_results=step_results,
                slots=slots,
                evidence_image=evidence_image,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            resolve_workflow_args(
                item,
                image_path=image_path,
                question=question,
                previous=previous,
                evidence=evidence,
                step_results=step_results,
                slots=slots,
                evidence_image=evidence_image,
            )
            for item in value
        ]
    if not isinstance(value, str):
        return value
    results = step_results or {}
    slot_values = slots or {}
    exact_step = STEP_REFERENCE_PATTERN.fullmatch(value)
    if exact_step:
        return _step_result_field(results.get(exact_step.group(1)) or {}, exact_step.group(2))
    exact_slot = SLOT_REFERENCE_PATTERN.fullmatch(value)
    if exact_slot:
        return slot_values.get(exact_slot.group(1), "")
    replacements = {
        "$image": image_path,
        "$filename": os.path.basename(image_path) if image_path else "image",
        "$question": question,
        "$previous": previous,
        "$evidence": evidence,
        "$previous_image": _extract_image_reference(previous) or image_path,
        "$evidence_image": evidence_image or image_path,
    }
    if value in replacements:
        return replacements[value]
    output = value
    for key, replacement in replacements.items():
        output = output.replace(key, str(replacement))
    output = SLOT_REFERENCE_PATTERN.sub(
        lambda match: str(slot_values.get(match.group(1), "")), output
    )
    output = STEP_REFERENCE_PATTERN.sub(
        lambda match: _stringify_reference(
            _step_result_field(results.get(match.group(1)) or {}, match.group(2))
        ),
        output,
    )
    return output


def build_evidence_text(observations: List[Dict[str, Any]], limit: int = 6000) -> str:
    chunks = []
    for item in observations:
        result = item.get("result") or {}
        content = str(result.get("content") or result.get("error") or "").strip()
        if not content:
            continue
        chunks.append(
            f"{item.get('step_id', item.get('tool', 'tool'))} "
            f"[{result.get('status', 'unknown')}]:\n{content}"
        )
    return "\n\n".join(chunks)[-limit:]


def parse_anomaly_tool_output(raw: Any) -> Dict[str, Any]:
    """兼容 embeddingTool 的结构化响应和“是/否（判定阈值）”文本响应。"""
    parsed = ToolRuntime._parse_json(raw)
    payload = parsed if isinstance(parsed, dict) else {}
    nested = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    metrics = nested.get("metrics") if isinstance(nested.get("metrics"), dict) else {}
    if not metrics and isinstance(payload.get("metrics"), dict):
        metrics = payload["metrics"]
    is_anomaly = nested.get("is_anomaly", payload.get("is_anomaly"))
    answer = str(nested.get("answer") or payload.get("answer") or "").strip()
    if is_anomaly is None and answer.lower() in {"是", "yes", "true"}:
        is_anomaly = True
    elif is_anomaly is None and answer.lower() in {"否", "no", "false"}:
        is_anomaly = False
    threshold = nested.get("threshold", payload.get("threshold"))
    if threshold is None:
        threshold = metrics.get("threshold")
    if is_anomaly is None:
        match = ANOMALY_RESULT_PATTERN.fullmatch(str(raw or ""))
        if match:
            is_anomaly = match.group(1) == "是"
            threshold = match.group(2) if match.group(2) is not None else threshold
    threshold = _normalize_threshold(threshold)
    return {
        "is_anomaly": is_anomaly if isinstance(is_anomaly, bool) else None,
        "decision": "是" if is_anomaly is True else "否" if is_anomaly is False else "",
        "threshold": threshold,
    }


def extract_anomaly_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """从一次工作流/ReAct 结果中提取最后一次成功的 embeddingTool 判断。"""
    observations = result.get("observations") or result.get("evidence") or []
    for item in reversed(observations):
        if str(item.get("tool") or "") != "embeddingTool":
            continue
        tool_result = item.get("result") or {}
        if not tool_result.get("ok"):
            continue
        data = tool_result.get("data") or {}
        return {
            "event_type": str(data.get("event_type") or ""),
            "is_anomaly": data.get("is_anomaly"),
            "decision": str(data.get("decision") or ""),
            "threshold": data.get("threshold"),
        }
    return {
        "event_type": "",
        "is_anomaly": None,
        "decision": "",
        "threshold": None,
    }


def _normalize_threshold(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan", "n/a", "unknown"}:
        return None
    try:
        return float(text)
    except ValueError:
        return text


def extract_final_answer(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    anomaly = parse_anomaly_tool_output(raw)
    if anomaly["decision"]:
        return anomaly["decision"]
    patterns = (
        r"(?:final answer|answer)\s*[:：]\s*([^\n]+)",
        r"\(([A-Z])\)\s*$",
        r"\b([A-Z])\s*$",
        r"\b(-?\d+(?:\.\d+)?)\s*$",
        r"\b(yes|no)\s*$",
        r"(是|否)\s*$",
    )
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            return match.group(1).strip().rstrip(".")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return lines[-1][:300] if lines else ""


def _step_references(value) -> List[Tuple[str, str]]:
    if isinstance(value, dict):
        refs = []
        for item in value.values():
            refs.extend(_step_references(item))
        return refs
    if isinstance(value, list):
        refs = []
        for item in value:
            refs.extend(_step_references(item))
        return refs
    if not isinstance(value, str):
        return []
    return list(dict.fromkeys(STEP_REFERENCE_PATTERN.findall(value)))


def _step_result_field(result: Dict[str, Any], field: str):
    if field in result:
        return result[field]
    data = result.get("data") or {}
    if field in data:
        return data[field]
    if field == "images":
        return data.get("image_refs") or []
    return ""


def _stringify_reference(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value or "")


def _best_evidence_image(observations: List[Dict[str, Any]]) -> str:
    candidates = []
    for index, item in enumerate(observations):
        result = item.get("result") or {}
        if result.get("status") != "success":
            continue
        image_ref = str((result.get("data") or {}).get("image") or "")
        if image_ref:
            candidates.append((
                EVIDENCE_IMAGE_PRIORITY.get(str(result.get("output_type") or ""), 0),
                index,
                image_ref,
            ))
    return max(candidates)[2] if candidates else ""


def _extract_image_reference(value: str) -> str:
    text = str(value or "")
    match = re.search(
        r"((?:[A-Za-z]:[\\/]|/)[^\"'\n]+?\.(?:png|jpe?g|webp|bmp))",
        text,
        flags=re.I,
    )
    if match:
        return match.group(1)
    match = re.search(r"(https?://[^\s\"']+\.(?:png|jpe?g|webp|bmp))", text, flags=re.I)
    return match.group(1) if match else ""
