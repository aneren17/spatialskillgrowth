"""Build a deterministic, problem-class-stratified Omni3D exploration subset."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    OMNI3D_CLASS_METADATA,
    OMNI3D_PROBLEM_CLASSES,
    heuristic_problem_class,
)


DEFAULT_SOURCE = "benchmark/Omni-3d/annotations.json"
DEFAULT_OUTPUT = ""
DEFAULT_SIZE = 100
DEFAULT_SEED = 3407
MINIMUM_PER_CLASS = 4
SMOKE_TEST_CLASS_PRIORITY = (
    "metric_dimension_scaling",
    "metric_distance_scaling",
    "dimension_ratio",
    "volume_capacity",
    "object_counting",
    "count_arithmetic",
    "depth_ordering",
    "compass_direction",
    "physical_interaction",
    "visual_attribute_recognition",
    "linear_fit_stacking",
    "depth_filtered_counting",
    "count_comparison",
    "occlusion_visibility",
    "size_fit_comparison",
    "relative_3d_position",
)


def classify_questions(questions: List[Dict]) -> Dict[str, List[Dict]]:
    grouped = defaultdict(list)
    for item in questions:
        question = str(item.get("question") or "")
        problem_class = str(item.get("problem_class") or "").strip()
        if problem_class not in OMNI3D_PROBLEM_CLASSES:
            problem_class = heuristic_problem_class(question, "omni3d")
        classified = dict(item)
        classified["problem_class"] = problem_class
        grouped[problem_class].append(classified)
    return {name: grouped.get(name, []) for name in OMNI3D_PROBLEM_CLASSES}


def allocate_quotas(grouped: Dict[str, List[Dict]], size: int) -> Dict[str, int]:
    available_total = sum(len(items) for items in grouped.values())
    if size <= 0 or size > available_total:
        raise ValueError(f"Subset size must be between 1 and {available_total}, got {size}")
    missing = [name for name, items in grouped.items() if not items]
    if missing:
        raise ValueError(f"No Omni3D examples were classified into: {', '.join(missing)}")
    if size < len(OMNI3D_PROBLEM_CLASSES):
        quotas = {name: 0 for name in OMNI3D_PROBLEM_CLASSES}
        for name in SMOKE_TEST_CLASS_PRIORITY[:size]:
            quotas[name] = 1
        return quotas
    minimum_per_class = (
        MINIMUM_PER_CLASS
        if size >= MINIMUM_PER_CLASS * len(OMNI3D_PROBLEM_CLASSES)
        else 1
    )
    quotas = {
        name: min(minimum_per_class, len(items))
        for name, items in grouped.items()
    }
    remaining = size - sum(quotas.values())
    while remaining:
        capacities = {
            name: len(items) - quotas[name]
            for name, items in grouped.items()
            if len(items) > quotas[name]
        }
        if not capacities:
            break
        capacity_total = sum(capacities.values())
        additions = {
            name: min(capacity, int(remaining * capacity / capacity_total))
            for name, capacity in capacities.items()
        }
        assigned = sum(additions.values())
        for name, addition in additions.items():
            quotas[name] += addition
        remaining -= assigned
        if remaining:
            ranked = sorted(
                capacities,
                key=lambda name: (
                    -(capacities[name] / capacity_total),
                    OMNI3D_PROBLEM_CLASSES.index(name),
                ),
            )
            for name in ranked:
                if remaining <= 0:
                    break
                if quotas[name] < len(grouped[name]):
                    quotas[name] += 1
                    remaining -= 1
    return quotas


def build_subset(questions: List[Dict], size: int, seed: int) -> Dict:
    grouped = classify_questions(questions)
    quotas = allocate_quotas(grouped, size)
    randomizer = random.Random(seed)
    selected = []
    for problem_class in OMNI3D_PROBLEM_CLASSES:
        candidates = list(grouped[problem_class])
        randomizer.shuffle(candidates)
        selected.extend(candidates[:quotas[problem_class]])
    selected.sort(key=lambda item: int(item.get("question_index", 0)))
    source_counts = {name: len(grouped[name]) for name in OMNI3D_PROBLEM_CLASSES}
    selected_counts = {name: quotas[name] for name in OMNI3D_PROBLEM_CLASSES}
    selected_classes = [name for name, count in selected_counts.items() if count]
    smoke_test = size < len(OMNI3D_PROBLEM_CLASSES)
    return {
        "metadata": {
            "benchmark": "omni3d",
            "purpose": (
                "SpatialSkillGrowth smoke testing only"
                if smoke_test
                else "SpatialSkillGrowth benchmark-specific skill exploration"
            ),
            "sampling": (
                "deterministic diverse-class smoke sampling"
                if smoke_test
                else "deterministic stratified sampling with per-class minimum coverage"
            ),
            "seed": seed,
            "size": len(selected),
            "problem_classes": selected_classes,
            "class_descriptions": {
                name: OMNI3D_CLASS_METADATA[name] for name in selected_classes
            },
            "source_class_counts": source_counts,
            "selected_class_counts": selected_counts,
        },
        "questions": selected,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source = Path(args.source)
    output = Path(
        args.output
        or f"benchmark/Omni-3d/annotations_explore{args.size}.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    questions = payload.get("questions") or []
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"No questions found in {source}")
    subset = build_subset(questions, args.size, args.seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(subset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(subset['questions'])} questions to {output}")
    for name, count in subset["metadata"]["selected_class_counts"].items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
