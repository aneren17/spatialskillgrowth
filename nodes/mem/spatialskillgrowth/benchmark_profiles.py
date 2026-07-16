"""按 benchmark 隔离的任务类别、异常事件 taxonomy 与 Skill 命名空间。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

from tools.basicTools.embeddingTool import (
    EVENT_TYPE_ALIASES,
    EVENT_TYPE_LABELS,
    EVENT_TYPE_SOURCE_LABELS,
    VALID_EVENT_TYPES,
)


DEFAULT_BENCHMARK = "generic"
ANOMALY_BENCHMARK = "anomaly_detection"
ANOMALY_EVENT_TYPES = tuple(sorted(VALID_EVENT_TYPES))
ANOMALY_CLASS_METADATA = {
    event_type: {
        "title": label,
        "goal": f"判断输入视频或图像中是否发生“{label}”异常事件",
        "description": (
            f"检测输入视频或图像中是否发生“{label}”异常事件"
            f"（相关显示名称：{'、'.join(EVENT_TYPE_ALIASES[event_type])}）；"
            f"调用异常检测工具时，"
            f"必须使用精确类别 ID `{event_type}`。"
        ),
        "aliases": list(EVENT_TYPE_ALIASES[event_type]),
        "display_names": dict(EVENT_TYPE_SOURCE_LABELS[event_type]),
        "primary_tool": "embeddingTool",
        "answer_type": "bool",
        "required_slots": ["event_type"],
        "tool_template": {
            "tool_name": "embeddingTool",
            "args": {
                "file_path": "$image",
                "event_type": event_type,
            },
        },
        "evidence_requirements": [
            f"embeddingTool 必须使用精确 event_type `{event_type}`。",
            "工具调用必须成功返回明确的‘是’或‘否’，并包含判定阈值 threshold。",
            "工具失败、event_type 不一致或缺少检测结果时不得接受答案。",
        ],
    }
    for event_type, label in EVENT_TYPE_LABELS.items()
}
LEGACY_PROBLEM_CLASSES = (
    "counting",
    "spatial_relation",
    "size",
    "distance_depth",
    "orientation",
)
LEGACY_CLASS_METADATA = {
    "counting": {
        "title": "Counting",
        "description": "Count requested visible object instances with explicit visual evidence.",
    },
    "spatial_relation": {
        "title": "Spatial Relation",
        "description": "Determine the requested spatial relation between visible objects.",
    },
    "size": {
        "title": "Size",
        "description": "Compare visible size, area, scale, or relative extent.",
    },
    "distance_depth": {
        "title": "Distance and Depth",
        "description": "Determine relative distance, depth order, or front-behind relations.",
    },
    "orientation": {
        "title": "Orientation",
        "description": "Determine orientation, facing direction, pose, or rotation.",
    },
}
OMNI3D_PROBLEM_CLASSES = (
    "metric_dimension_scaling",
    "metric_distance_scaling",
    "dimension_ratio",
    "volume_capacity",
    "linear_fit_stacking",
    "object_counting",
    "count_arithmetic",
    "count_comparison",
    "depth_ordering",
    "depth_filtered_counting",
    "compass_direction",
    "occlusion_visibility",
    "physical_interaction",
    "size_fit_comparison",
    "relative_3d_position",
    "visual_attribute_recognition",
)
BENCHMARK_ALIASES = {
    "": DEFAULT_BENCHMARK,
    "default": DEFAULT_BENCHMARK,
    "generic": DEFAULT_BENCHMARK,
    "st-vqa": "stvqa",
    "st_vqa": "stvqa",
    "omni-3d": "omni3d",
    "omni_3d": "omni3d",
    "anomaly": ANOMALY_BENCHMARK,
    "anomaly-detection": ANOMALY_BENCHMARK,
    "anomaly_detection": ANOMALY_BENCHMARK,
    "异常检测": ANOMALY_BENCHMARK,
}
BENCHMARK_PROBLEM_CLASSES = {
    DEFAULT_BENCHMARK: LEGACY_PROBLEM_CLASSES,
    "stvqa": LEGACY_PROBLEM_CLASSES,
    "omni3d": OMNI3D_PROBLEM_CLASSES,
    ANOMALY_BENCHMARK: ANOMALY_EVENT_TYPES,
}
OMNI3D_CLASS_METADATA = {
    "metric_dimension_scaling": {
        "title": "Metric Dimension Scaling",
        "goal": "estimating a target 3D dimension from a measured reference dimension",
        "description": "Transfer a known length, width, height, radius, or size to another target using image geometry.",
    },
    "metric_distance_scaling": {
        "title": "Metric Distance Scaling",
        "goal": "estimating a target metric distance from a measured reference distance",
        "description": "Calibrate target depth or inter-object distance from a supplied metric reference and unit.",
    },
    "dimension_ratio": {
        "title": "Dimension Ratio",
        "goal": "computing ratios or differences between object dimensions",
        "description": "Compare lengths, widths, heights, areas, or dimension expressions as a numeric ratio or difference.",
    },
    "volume_capacity": {
        "title": "Volume Capacity",
        "goal": "estimating how many source volumes fit inside a target volume",
        "description": "Reason about 3D volume ratios and capacity rather than visible instance counts.",
    },
    "linear_fit_stacking": {
        "title": "Linear Fit and Stacking",
        "goal": "estimating repeated-object fit, alignment, covering, or stacking counts",
        "description": "Compute how many repeated dimensions are needed to match a requested length, width, height, or area.",
    },
    "object_counting": {
        "title": "Object Counting",
        "goal": "counting requested visible instances or parts",
        "description": "Count visible objects, parts, or instances with any inclusion and exclusion constraints.",
    },
    "count_arithmetic": {
        "title": "Count Arithmetic",
        "goal": "computing ratios, sums, or differences of object counts",
        "description": "Count multiple groups and apply deterministic arithmetic to their counts.",
    },
    "count_comparison": {
        "title": "Count Comparison",
        "goal": "comparing the counts of two or more object groups",
        "description": "Determine which group has more, fewer, the same number, or enough instances.",
    },
    "depth_ordering": {
        "title": "Depth Ordering",
        "goal": "comparing relative depth or distance without metric calibration",
        "description": "Determine which target is closer, farther, nearest, or furthest in 3D.",
    },
    "depth_filtered_counting": {
        "title": "Depth-filtered Counting",
        "goal": "counting objects constrained by relative depth",
        "description": "Count targets that are in front of, behind, closer than, or farther than a reference.",
    },
    "compass_direction": {
        "title": "Egocentric Compass Direction",
        "goal": "mapping a target to a compass direction in a stated reference frame",
        "description": "Resolve N, NE, E, SE, S, SW, W, or NW from the supplied observer position and facing direction.",
    },
    "occlusion_visibility": {
        "title": "Occlusion and Visibility",
        "goal": "predicting visibility after an object placement or occlusion",
        "description": "Determine whether a target remains visible or becomes covered after a hypothetical placement.",
    },
    "physical_interaction": {
        "title": "Physical Interaction",
        "goal": "predicting collision, falling, support, or motion outcomes",
        "description": "Reason about falling, hitting, pushing, tipping, hanging over an edge, or collision order.",
    },
    "size_fit_comparison": {
        "title": "Size and Fit Comparison",
        "goal": "qualitatively comparing 3D size, extent, fit, or support",
        "description": "Compare dimensions or decide whether one object fits on, under, inside, or across another.",
    },
    "relative_3d_position": {
        "title": "Relative 3D Position",
        "goal": "determining non-depth relative positions between scene objects",
        "description": "Resolve above, below, left, right, inside, on, under, adjacency, or elevation relations.",
    },
    "visual_attribute_recognition": {
        "title": "Visual Attribute Recognition",
        "goal": "recognizing an object, color, material, text, time, or other requested visual attribute",
        "description": "Answer residual Omni3D visual attribute and object-identification questions that are not geometric operations.",
    },
}


def normalize_benchmark(benchmark: str) -> str:
    raw = str(benchmark or "").strip().lower()
    if raw in BENCHMARK_ALIASES:
        return BENCHMARK_ALIASES[raw]
    value = re.sub(r"[^a-z0-9_-]+", "", raw)
    return BENCHMARK_ALIASES.get(value, value or DEFAULT_BENCHMARK)


def problem_classes_for(benchmark: str) -> Tuple[str, ...]:
    normalized = normalize_benchmark(benchmark)
    return BENCHMARK_PROBLEM_CLASSES.get(normalized, LEGACY_PROBLEM_CLASSES)


def class_metadata_for(benchmark: str) -> Dict[str, Dict[str, str]]:
    normalized = normalize_benchmark(benchmark)
    if normalized == ANOMALY_BENCHMARK:
        return {name: dict(metadata) for name, metadata in ANOMALY_CLASS_METADATA.items()}
    if normalized == "omni3d":
        return {name: dict(metadata) for name, metadata in OMNI3D_CLASS_METADATA.items()}
    if normalized in {DEFAULT_BENCHMARK, "stvqa"}:
        return {name: dict(metadata) for name, metadata in LEGACY_CLASS_METADATA.items()}
    return {}


def has_benchmark_profile(benchmark: str) -> bool:
    return normalize_benchmark(benchmark) in BENCHMARK_PROBLEM_CLASSES


def resolve_benchmark_skill_root(skill_root: str, benchmark: str) -> str:
    """Keep legacy STVQA paths stable and isolate benchmark-specific skills."""
    normalized = normalize_benchmark(benchmark)
    root = Path(skill_root)
    if normalized in {DEFAULT_BENCHMARK, "stvqa"}:
        return str(root)
    if root.name == normalized and root.parent.name == "benchmarks":
        return str(root)
    namespace = root / "benchmarks" / normalized
    return str(namespace)


def heuristic_problem_class(question: str, benchmark: str = DEFAULT_BENCHMARK) -> str:
    if normalize_benchmark(benchmark) == "omni3d":
        return _heuristic_omni3d_class(question)
    return _heuristic_legacy_class(question)


def _heuristic_legacy_class(question: str) -> str:
    text = str(question or "").lower()
    if any(term in text for term in ("how many", "number of", "count")):
        return "counting"
    if any(term in text for term in ("larger", "smaller", "bigger", "size", "area")):
        return "size"
    if any(term in text for term in (
        "perspective", "facing", "direction", "oriented", "orientation", "rotated",
        "pose", "upright",
    )):
        return "orientation"
    if any(term in text for term in (
        "front", "behind", "closer", "farther", "nearer", "depth", "foreground",
        "background", "occlude",
    )):
        return "distance_depth"
    return "spatial_relation"


def _heuristic_omni3d_class(question: str) -> str:
    text = " ".join(str(question or "").lower().split())
    if re.search(r"\bchoose from n,? ne,? e,? se,? s,? sw,? w,? nw\b", text):
        return "compass_direction"
    if _contains_metric_distance_scaling(text):
        return "metric_distance_scaling"
    if _contains_metric_dimension_scaling(text):
        return "metric_dimension_scaling"
    if "volume" in text and any(term in text for term in (" fit", "fit ", "capacity", "same volume")):
        return "volume_capacity"
    if _contains_linear_fit(text):
        return "linear_fit_stacking"
    if _contains_depth_filtered_count(text):
        return "depth_filtered_counting"
    if _contains_count_arithmetic(text):
        return "count_arithmetic"
    if _contains_count_comparison(text):
        return "count_comparison"
    if _contains_object_count(text):
        return "object_counting"
    if _contains_visual_attribute(text):
        return "visual_attribute_recognition"
    if _contains_occlusion(text):
        return "occlusion_visibility"
    if _contains_physical_interaction(text):
        return "physical_interaction"
    if _contains_dimension_ratio(text):
        return "dimension_ratio"
    if _contains_depth_ordering(text):
        return "depth_ordering"
    if _contains_size_fit_comparison(text):
        return "size_fit_comparison"
    if _contains_relative_position(text):
        return "relative_3d_position"
    return "visual_attribute_recognition"


def _contains_metric_distance_scaling(text: str) -> bool:
    if not text.startswith("if "):
        return False
    has_unit = bool(re.search(
        r"\b\d+(?:\.\d+)?\s*(?:cm|centimeters?|m|meters?|km|kilometers?|feet|foot|inches?|miles?)\b",
        text,
    ))
    reference_clause = text.split(",", 1)[0]
    has_distance_reference = any(term in reference_clause for term in (
        "distance", " away", "walk ", "get to ",
    ))
    return has_unit and has_distance_reference


def _contains_metric_dimension_scaling(text: str) -> bool:
    if not text.startswith(("if ", "assuming ")):
        return False
    has_unit = bool(re.search(
        r"\b\d+(?:\.\d+)?\s*(?:cm|centimeters?|m|meters?|km|kilometers?|feet|foot|inches?|miles?)\b",
        text,
    ))
    dimension_terms = (
        " tall", " height", " wide", " width", " long", " length", " radius",
        " diameter", " shorter", " taller", " higher", " size",
    )
    return has_unit and any(term in text for term in dimension_terms)


def _contains_linear_fit(text: str) -> bool:
    operations = (
        "stack", "fit on", "fit along", "place next to", "placed next to", "align next",
        "line next", "cover the", "make a structure", "multiply the", "times is the 3d",
        "laid down end to end", "same height", "same width", "same length",
    )
    return any(term in text for term in operations) and any(
        term in text for term in ("how many", "what number", "how much taller", "length of")
    )


def _contains_depth_filtered_count(text: str) -> bool:
    return _contains_object_count(text) and any(term in text for term in (
        "further away", "farther away", "closer to", "in front of", "behind ",
    ))


def _contains_count_arithmetic(text: str) -> bool:
    if any(term in text for term in ("sum of the number", "total number of", "number of ")) and any(
        term in text for term in (" plus ", " and ", "divided by", "difference")
    ):
        return True
    return any(term in text for term in ("ratio of", "ratio of ", " divided by ", " per ")) and not any(
        dimension in text for dimension in ("height", "width", "length", "volume", "area", "radius")
    )


def _contains_count_comparison(text: str) -> bool:
    return any(term in text for term in (
        "are there more", "is there more", "more than", "fewer than", "same number",
        "enough ", "which chair has more", "are the number of", "two of the same",
        "3 or more of the same", "three of the same object",
    ))


def _contains_object_count(text: str) -> bool:
    return any(term in text for term in (
        "how many", "what shelf", "what is the number of", "including all", "counting from",
    ))


def _contains_occlusion(text: str) -> bool:
    return any(term in text for term in (
        "still be visible", "remain visible", "would be visible", "how many shelves would be visible",
        "cover the entirety", "be covering", "covered the shelves", "partially visible",
    ))


def _contains_physical_interaction(text: str) -> bool:
    return any(term in text for term in (
        " fall", "fell", " hit", "pushed", "moved ", "swung", "detach", "tipping",
        "falling", "hang over", "fall off", "raised to match", "collisions",
    ))


def _contains_depth_ordering(text: str) -> bool:
    if "distance between" in text:
        return True
    if re.search(r"\bis .+ (?:closer to|farther from|further from)\b", text):
        return True
    return any(term in text for term in (
        "what is closer", "what is farther", "what is further",
        "which object is closer", "which object is farther", "which object is further",
        "which one is closer", "which one is farther", "which one is further",
        "which is closer", "which is farther", "which is further",
        "is closer to", "is farther from", "is further from",
        "closer to the camera than", "farther away from the camera than",
        "further away from the camera than", "closest to the camera:",
        "closer in 3d to the camera", "further in 3d from the camera",
    ))


def _contains_dimension_ratio(text: str) -> bool:
    return any(term in text for term in (
        "ratio", "difference in", "how much taller", "how much higher", "how many times",
        "height-to-width", "width-to-height",
    )) and any(term in text for term in (
        "height", "width", "length", "volume", "area", "radius", "size", "taller", "higher",
    ))


def _contains_size_fit_comparison(text: str) -> bool:
    return any(term in text for term in (
        "taller", "shorter", "larger", "smaller", "greater than", "large enough", "fit under",
        "fit inside", "fit on top", "stack the", "same size", "largest 3d", "largest height",
        "largest length", "largest width", "higher than", "lower than",
    ))


def _contains_relative_position(text: str) -> bool:
    return any(term in text for term in (
        "above", "below", "under", "on top of", "inside", "left of", "right of", "adjacent",
        "next to", "elevation", "surface of", "edge of", "corner",
    ))


def _contains_visual_attribute(text: str) -> bool:
    return any(term in text for term in (
        "what color", "what material", "same color", "same material", "lighter color",
        "color of", "material of", "what time", "letters is in the word", "partially visible in",
    ))
