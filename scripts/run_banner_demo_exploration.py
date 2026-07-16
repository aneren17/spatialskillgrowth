"""使用模拟 embedding 后端运行 banner 演示数据集的离线探索流程。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from agents.spatialskillgrowth.online_data import load_online_tasks
from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    ANOMALY_BENCHMARK,
    class_metadata_for,
)
from nodes.mem.spatialskillgrowth.experiment_config import (
    DEFAULT_RESULT_ROOT,
    ExperimentPaths,
    build_experiment_config,
)
from nodes.mem.spatialskillgrowth.growth_store import WorkflowRepository
from nodes.mem.spatialskillgrowth.pipeline import ExperimentFactory
from nodes.mem.spatialskillgrowth.tool_runtime import ToolRuntime


DEFAULT_DATASET = Path("benchmark/anomaly/banner_demo/explore.json")
DEFAULT_IMAGE_ROOT = Path("benchmark/anomaly/banner_demo/images")
DEFAULT_RUN_ID = "banner_demo_mock_explore"
DEFAULT_EXPERIMENT = "retrieval_only"
DEFAULT_SPLIT = "explore10_demo"


class DemoEmbeddingTool:
    name = "embeddingTool"

    @staticmethod
    def invoke(args):
        filename = Path(str(args.get("file_path") or "")).stem
        match = re.search(r"banner_(\d+)_", filename)
        index = int(match.group(1)) if match else 0
        threshold = min(0.95, 0.55 + index * 0.01)
        return f"是 (判定阈值: {threshold:.2f})"


class DisabledDemoLLM:
    @staticmethod
    def invoke(_messages):
        raise RuntimeError("离线 banner 演示不应调用 LLM。")


def run_demo(
    dataset: Path,
    image_root: Path,
    result_root: Path,
    run_id: str,
    force: bool = False,
) -> Path:
    config = build_experiment_config(DEFAULT_EXPERIMENT)
    config.retriever = "history_only"
    config.extra = {
        "demo_mode": True,
        "embedding_backend": "deterministic_mock",
        "warning": "该 run 只用于展示框架流程，不代表真实模型效果。",
    }
    metadata = class_metadata_for(ANOMALY_BENCHMARK)
    paths = ExperimentPaths(
        config.name,
        run_id,
        str(result_root),
        benchmark=ANOMALY_BENCHMARK,
        problem_classes=["banner"],
        class_metadata=metadata,
    )
    if paths.root.exists() and force:
        shutil.rmtree(paths.root)
    paths.ensure(config, "explore", False)
    tasks = load_online_tasks(str(dataset), str(image_root))
    (paths.root / "split.json").write_text(
        json.dumps({
            "benchmark": ANOMALY_BENCHMARK,
            "seed": config.seed,
            "exploration_task_ids": [task.task_id for task in tasks],
            "demo_mode": True,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pipeline = ExperimentFactory(
        config,
        paths,
        DisabledDemoLLM(),
        runtime=ToolRuntime({"embeddingTool": DemoEmbeddingTool()}),
        benchmark=ANOMALY_BENCHMARK,
        problem_classes=["banner"],
        class_metadata=metadata,
        exploration_split_name=DEFAULT_SPLIT,
    ).build_exploration()
    summaries = [pipeline.ask(task) for task in tasks]
    validation = pipeline.validate_provisional(tasks)
    repository = WorkflowRepository(paths)
    report = {
        "demo_mode": True,
        "dataset": str(dataset.resolve()),
        "task_count": len(tasks),
        "correct_count": sum(bool(item.get("correct")) for item in summaries),
        "active_workflow_ids": [
            item.workflow_id for item in repository.list_active("banner")
        ],
        "provisional_workflow_ids": [
            item.workflow_id for item in repository.list_provisional("banner")
        ],
        "validation": validation,
        "conversation_files": [
            str(
                paths.trajectory_root
                / f"explore__{task.task_id}"
                / "conversation.md"
            )
            for task in tasks
        ],
    }
    (paths.root / "demo_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return paths.root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--img-root", type=Path, default=DEFAULT_IMAGE_ROOT)
    parser.add_argument("--result-root", type=Path, default=Path(DEFAULT_RESULT_ROOT))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run_root = run_demo(
        args.dataset,
        args.img_root,
        args.result_root,
        args.run_id,
        args.force,
    )
    print(f"banner 离线演示探索已完成：{run_root}")


if __name__ == "__main__":
    main()
