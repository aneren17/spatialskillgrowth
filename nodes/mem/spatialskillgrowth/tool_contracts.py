"""Tool input/output contracts used to build valid skill workflows."""

from __future__ import annotations

from typing import Dict, Iterable, Set


TOOL_CONTRACTS: Dict[str, Dict[str, object]] = {
    "embeddingTool": {
        "output": "anomaly_decision",
        "requires": {"image", "event_type"},
        "output_fields": {
            "event_type": "string",
            "is_anomaly": "boolean",
            "threshold": "number",
        },
    },
    "MLLM": {"output": "answer", "requires": set()},
    "yoloTool": {"output": "pixel_detections", "requires": {"image"}},
    "paddleHeadDetTool": {"output": "pixel_detections", "requires": {"image"}},
    "paddlePedriderDetTool": {"output": "pixel_detections", "requires": {"image"}},
    "sam3": {
        "output": "segmentation_image",
        "outputs": {"segmentation_image", "pixel_detections"},
        "requires": {"image", "target"},
        "bbox_format": "xyxy_pixel",
        "input_constraints": {
            "query": {
                "language": "english",
                "min_words": 1,
                "max_words": 3,
            },
            "threshold": {
                "minimum": 0.0,
                "maximum": 1.0,
                "abstract_recommended": 0.5,
                "concrete_recommended": [0.6, 0.8],
            },
        },
    },
    "groundingdino": {
        "output": "pixel_detections",
        "requires": {"image", "target"},
    },
    "unidepth": {
        "output": "metric_depth",
        "requires": {"image", "pixel_detections"},
    },
    "paddleOcrTool": {"output": "text_regions", "requires": {"image"}},
    "crop_detections": {
        "output": "cropped_images",
        "requires": {"image", "pixel_detections"},
    },
    "picRelativeCut": {
        "output": "relative_crop",
        "requires": {"image", "pixel_detections"},
    },
    "python_code_sandbox": {
        "output": "computed_result",
        "requires": {"pixel_detections"},
    },
}


def output_types(tool_name: str) -> Set[str]:
    contract = TOOL_CONTRACTS.get(tool_name) or {}
    values = contract.get("outputs")
    if isinstance(values, (set, list, tuple)):
        return {str(value) for value in values if value}
    primary = str(contract.get("output") or "evidence")
    return {primary}


PIXEL_DETECTION_TOOLS = {
    name
    for name in TOOL_CONTRACTS
    if "pixel_detections" in output_types(name)
}
PRODUCED_RESOURCE_TYPES = {
    output
    for name in TOOL_CONTRACTS
    for output in output_types(name)
}
DEPENDENT_TOOLS = {
    name
    for name, contract in TOOL_CONTRACTS.items()
    if set(contract.get("requires") or ()).intersection(PRODUCED_RESOURCE_TYPES)
}
FRAME_INDEPENDENT_IMAGE_TOOLS = {
    "groundingdino",
    "paddleHeadDetTool",
    "paddleOcrTool",
    "paddlePedriderDetTool",
    "sam3",
    "yoloTool",
}


def output_type(tool_name: str) -> str:
    return str((TOOL_CONTRACTS.get(tool_name) or {}).get("output") or "evidence")


def input_constraints(tool_name: str) -> Dict[str, object]:
    value = (TOOL_CONTRACTS.get(tool_name) or {}).get("input_constraints")
    return dict(value) if isinstance(value, dict) else {}


def contract_signature(tool_name: str) -> Dict[str, object]:
    contract = TOOL_CONTRACTS.get(tool_name) or {}
    return {
        "outputs": sorted(output_types(tool_name)),
        "requires": sorted(str(item) for item in contract.get("requires") or ()),
        "bbox_format": str(contract.get("bbox_format") or ""),
        "output_fields": dict(contract.get("output_fields") or {}),
    }


def compatible_producers(tool_name: str) -> Set[str]:
    contract = TOOL_CONTRACTS.get(tool_name) or {}
    required_outputs = set(contract.get("requires") or ()).intersection(
        PRODUCED_RESOURCE_TYPES
    )
    if not required_outputs:
        return set()
    return {
        name
        for name in TOOL_CONTRACTS
        if output_types(name).intersection(required_outputs)
    }


def can_add_tool(tool_name: str, existing_tools: Iterable[str]) -> bool:
    if tool_name not in DEPENDENT_TOOLS:
        return True
    return bool(set(existing_tools).intersection(compatible_producers(tool_name)))
