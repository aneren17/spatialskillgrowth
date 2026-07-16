"""从多个标准化 benchmark 等额抽样，构建总量固定的 zeroshot 数据集。"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path
from typing import Dict, List

from agents.spatialskillgrowth.online_data import (
    infer_online_benchmark,
    load_online_tasks,
)


DEFAULT_SIZE = 256
DEFAULT_SEED = 3407


def build_subset(manifest: Dict, size: int, seed: int) -> Dict:
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Manifest must contain a non-empty sources list")
    randomizer = random.Random(seed)
    loaded = []
    for index, source in enumerate(sources):
        dataset = str(source.get("dataset") or "")
        image_root = str(source.get("image_root") or "")
        if not dataset:
            raise ValueError(f"sources[{index}] requires dataset")
        benchmark = str(
            source.get("benchmark") or infer_online_benchmark(dataset)
        )
        source_name = str(source.get("name") or f"{benchmark}_{index}")
        source_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", source_name).strip("_")
        tasks = load_online_tasks(dataset, image_root)
        randomizer.shuffle(tasks)
        quota = int(source.get("quota") or 0)
        loaded.append({
            "benchmark": benchmark,
            "source_name": source_name,
            "dataset": dataset,
            "tasks": tasks,
            "quota": quota,
        })
    quotas = _allocate_quotas(loaded, size)
    data = []
    counts = {}
    for source, quota in zip(loaded, quotas):
        benchmark = source["benchmark"]
        counts[benchmark] = counts.get(benchmark, 0) + quota
        for task in source["tasks"][:quota]:
            data.append({
                "task_id": f"{source['source_name']}__{task.task_id}",
                "question": task.question,
                "answer": task.groundtruth,
                "image_paths": task.image_paths,
                "problem_class": task.capability,
                "answer_type": task.answer_type or "str",
                "source_benchmark": benchmark,
            })
    randomizer.shuffle(data)
    return {
        "metadata": {
            "benchmark": "multibench_zeroshot",
            "purpose": "SpatialSkillGrowth cross-benchmark zeroshot validation",
            "seed": seed,
            "size": len(data),
            "source_counts": counts,
        },
        "data": data,
    }


def _allocate_quotas(sources: List[Dict], size: int) -> List[int]:
    available = sum(len(source["tasks"]) for source in sources)
    if size <= 0 or size > available:
        raise ValueError(f"Size must be between 1 and {available}, got {size}")
    quotas = [min(source["quota"], len(source["tasks"])) for source in sources]
    if sum(quotas) > size:
        raise ValueError("Explicit source quotas exceed requested total size")
    remaining = size - sum(quotas)
    unspecified = [index for index, source in enumerate(sources) if not source["quota"]]
    while remaining and unspecified:
        progressed = False
        for index in unspecified:
            if remaining <= 0:
                break
            if quotas[index] < len(sources[index]["tasks"]):
                quotas[index] += 1
                remaining -= 1
                progressed = True
        if not progressed:
            break
    if remaining:
        raise ValueError(
            "Explicit quotas leave samples unassigned; add a source without quota and with capacity"
        )
    return quotas


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = build_subset(manifest, args.size, args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(payload['data'])} tasks to {output}")
    print(json.dumps(payload["metadata"]["source_counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
