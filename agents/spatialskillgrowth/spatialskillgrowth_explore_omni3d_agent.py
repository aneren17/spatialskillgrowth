"""SpatialSkillGrowth 的 benchmark-aware 在线探索入口。"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from collections import deque
from typing import List

from dotenv import load_dotenv
from model.QwenFactory.pureQwenFactory import DEFAULT_API_KEY, MultimodalChatOpenAI
from tqdm import tqdm

from agents.spatialskillgrowth.online_data import infer_online_benchmark, load_online_tasks
from agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent import (
    format_omni3d_question,
)
from config.spatialskillgrowth_config import (
    SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE,
    SPATIAL_SKILL_GROWTH_BASE_URL,
    SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE,
    SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS,
)
from nodes.mem.spatialskillgrowth.experiment_config import (
    DEFAULT_SEED,
    EXPERIMENT_PRESETS,
    ExperimentPaths,
    build_experiment_config,
    result_root_for_benchmark,
)
from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    ANOMALY_BENCHMARK,
    ANOMALY_EVENT_TYPES,
    class_metadata_for,
    has_benchmark_profile,
    normalize_benchmark,
    problem_classes_for,
)
from nodes.mem.spatialskillgrowth.pipeline import ExperimentFactory
from nodes.mem.spatialskillgrowth.workflow_executor import WorkflowPythonExporter
from nodes.mem.spatialskillgrowth.growth_store import WorkflowRepository
from nodes.mem.spatialskillgrowth.skill_layout import skill_directory


DEFAULT_DATASET = "benchmark/anomaly/explore.json"
DEFAULT_IMAGE_ROOT = "benchmark/anomaly/files"

DEFAULT_RUNID = "explore_anomaly"

# DEFAULT_DATASET = "benchmark/STVQA-7K/spatial_debug_10/toolbatch_spatial_debug_10.json"
# DEFAULT_IMAGE_ROOT = "benchmark/STVQA-7K/images"


DEFAULT_BASE_URLS = [
    "http://127.0.0.1:8861/v1",
    "http://127.0.0.1:8862/v1",
    "http://127.0.0.1:8863/v1",
]


load_dotenv()


def load_exploration_tasks(dataset: str, image_root: str, limit: int = 0):
    tasks = load_online_tasks(dataset, image_root, limit)
    for task in tasks:
        task.answer_type = task.answer_type or (
            "bool" if task.capability in ANOMALY_EVENT_TYPES else "str"
        )
        task.question = format_omni3d_question(task.question, task.answer_type)
    queues = {problem_class: deque() for problem_class in sorted({
        task.capability for task in tasks
    })}
    for task in tasks:
        queues[task.capability].append(task)
    ordered = []
    while any(queues.values()):
        for problem_class in queues:
            if queues[problem_class]:
                ordered.append(queues[problem_class].popleft())
    return ordered


def parse_base_urls(args) -> List[str]:
    if str(args.base_url or "").strip():
        return [str(args.base_url).strip()]
    urls = [url.strip() for url in str(args.base_urls or "").split(",") if url.strip()]
    return urls or [SPATIAL_SKILL_GROWTH_BASE_URL]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpatialSkillGrowth benchmark exploration")
    parser.add_argument("--engine", "-e", default=SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE)
    parser.add_argument("--base-url", default="", help="Use one endpoint only.")
    parser.add_argument("--base-urls", default=",".join(DEFAULT_BASE_URLS))
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--img-root", default=DEFAULT_IMAGE_ROOT)
    parser.add_argument("--benchmark", default=ANOMALY_BENCHMARK)
    parser.add_argument(
        "--problem-classes",
        default="",
        help="Optional comma-separated taxonomy for a custom benchmark.",
    )
    parser.add_argument("--result-root", default="")
    parser.add_argument("--experiment", choices=sorted(EXPERIMENT_PRESETS), default="full")
    parser.add_argument("--run-id", default=DEFAULT_RUNID)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-react-steps", type=int, default=8)
    parser.add_argument(
        "--export-python",
        action="store_true",
        help="Explicitly export debug Python wrappers after exploration.",
    )
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = build_experiment_config(args.experiment, args.seed)
    tasks = load_exploration_tasks(args.dataset, args.img_root, args.limit)
    benchmark = _resolve_benchmark(args.benchmark, args.dataset)
    problem_classes = _resolve_problem_classes(
        benchmark,
        args.problem_classes,
        [task.capability for task in tasks],
    )
    metadata = class_metadata_for(benchmark)
    result_root = args.result_root or result_root_for_benchmark(benchmark)
    paths = ExperimentPaths(
        args.experiment,
        args.run_id,
        result_root,
        benchmark=benchmark,
        problem_classes=problem_classes,
        class_metadata=metadata,
    )
    paths.ensure(config, "explore", args.resume)
    _write_split_manifest(paths, tasks, args.seed, benchmark)
    exploration_split_name = f"explore{len(tasks)}"
    base_urls: List[str] = parse_base_urls(args)
    pipelines = []
    for base_url in base_urls:
        llm = MultimodalChatOpenAI(
            base_url=base_url,
            model_name=args.engine,
            api_key=DEFAULT_API_KEY,
            timeout=SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS,
            temperature=SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE,
        )
        pipelines.append(ExperimentFactory(
            config,
            paths,
            llm,
            max_react_steps=args.max_react_steps,
            benchmark=benchmark,
            problem_classes=problem_classes,
            class_metadata=metadata,
            exploration_split_name=exploration_split_name,
        ).build_exploration())
    print(
        f"SpatialSkillGrowth {benchmark} exploration: {len(tasks)} tasks, "
        f"{len(pipelines)} workers, run={paths.root}"
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(pipelines)) as executor:
        futures = {}
        next_index = 0
        for pipeline in pipelines:
            if next_index >= len(tasks):
                break
            task = tasks[next_index]
            next_index += 1
            futures[executor.submit(pipeline.ask, task, args.resume)] = (pipeline, task)
        with tqdm(total=len(tasks), desc="SpatialSkillGrowth explore") as progress:
            while futures:
                done, _ = concurrent.futures.wait(
                    futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                for future in done:
                    pipeline, task = futures.pop(future)
                    try:
                        result = future.result()
                        print(
                            f"[{task.task_id}] class={result.get('problem_class')} "
                            f"correct={result.get('correct')} "
                            f"activated={result.get('activated_workflow_ids')}"
                        )
                    except Exception as exc:
                        print(f"[{task.task_id}] ERROR {type(exc).__name__}: {exc}")
                    progress.update(1)
                    if next_index < len(tasks):
                        next_task = tasks[next_index]
                        next_index += 1
                        futures[executor.submit(
                            pipeline.ask, next_task, args.resume
                        )] = (pipeline, next_task)
    validation_report = pipelines[0].validate_provisional(tasks)
    print(
        "Provisional validation: "
        f"attempted={validation_report['attempted']} "
        f"promoted={len(validation_report['promoted'])} "
        f"archived={len(validation_report['archived'])}"
    )
    if args.export_python:
        exporter = WorkflowPythonExporter(paths.export_root)
        exported = []
        for workflow in WorkflowRepository(paths).list_active():
            exported.append(exporter.export(workflow))
            skill_script_root = (
                skill_directory(
                    paths.active_skill_root,
                    workflow.applicability.problem_class,
                )
                / "scripts"
            )
            WorkflowPythonExporter(skill_script_root).export(workflow)
        print(f"Exported {len(exported)} optional Python workflow wrappers.")


def _resolve_benchmark(value: str, dataset: str) -> str:
    if str(value or "").strip().lower() != "auto":
        return normalize_benchmark(value)
    return infer_online_benchmark(dataset)


def _resolve_problem_classes(
    benchmark: str,
    configured: str,
    observed: List[str],
) -> List[str]:
    explicit = [item.strip() for item in str(configured or "").split(",") if item.strip()]
    observed_classes = [str(item).strip() for item in observed if str(item).strip()]
    if explicit:
        return list(dict.fromkeys(explicit))
    if has_benchmark_profile(benchmark):
        return list(problem_classes_for(benchmark))
    return list(dict.fromkeys(
        observed_classes or problem_classes_for(benchmark)
    ))


def _write_split_manifest(
    paths: ExperimentPaths,
    tasks,
    seed: int,
    benchmark: str,
) -> None:
    task_ids = [task.task_id for task in tasks]
    payload = {
        "benchmark": benchmark,
        "seed": seed,
        "exploration_task_ids": task_ids,
    }
    if benchmark == "omni3d":
        payload["exploration_split"] = f"explore{len(task_ids)}"
    (paths.root / "split.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
