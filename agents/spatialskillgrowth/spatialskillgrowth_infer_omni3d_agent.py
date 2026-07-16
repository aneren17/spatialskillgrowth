"""SpatialSkillGrowth 的 benchmark-aware 冻结技能推理入口。"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from dotenv import load_dotenv
from model.QwenFactory.pureQwenFactory import DEFAULT_API_KEY, MultimodalChatOpenAI
from tqdm import tqdm

from agents.spatialskillgrowth.online_data import infer_online_benchmark, load_online_tasks
from config.spatialskillgrowth_config import (
    SPATIAL_SKILL_GROWTH_BASE_URL,
    SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE,
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
    class_metadata_for,
    has_benchmark_profile,
    normalize_benchmark,
    problem_classes_for,
)
from nodes.mem.spatialskillgrowth.models import TaskRecord
from nodes.mem.spatialskillgrowth.answer_evaluator import answer_matches_typed
from nodes.mem.spatialskillgrowth.pipeline import (
    ExperimentFactory,
    write_evaluation_summary,
)
from nodes.mem.spatialskillgrowth.growth_store import WorkflowRepository
from nodes.mem.spatialskillgrowth.omni3d_eval_adapter import (
    export_inference_predictions,
)


OMNI3D_DEFAULT_DATASET_DIR = "benchmark/Omni-3d"
OMNI3D_DEFAULT_ANNOTATIONS_FILE = "annotations.json"
OMNI3D_DEFAULT_EXPLORE_FILE = "annotations_explore256.json"
OMNI3D_DEFAULT_IMAGES_DIR = "images"
DEFAULT_BASE_URLS = [
    "http://127.0.0.1:8861/v1",
    "http://127.0.0.1:8862/v1",
    "http://127.0.0.1:8863/v1",
]
load_dotenv()


class SpatialSkillGrowthOmni3DInferenceAgent:
    """保留清晰的 Agent 外壳，内部职责由各模块类组合完成。"""

    def __init__(self, pipeline):
        self.pipeline = pipeline

    def ask(self, task: TaskRecord, split_name: str, resume: bool = False) -> Dict:
        return self.pipeline.ask(task, split_name, resume)


def load_omni3d_tasks(
    dataset_dir: str = OMNI3D_DEFAULT_DATASET_DIR,
    annotations_file: str = OMNI3D_DEFAULT_ANNOTATIONS_FILE,
    images_dir: str = OMNI3D_DEFAULT_IMAGES_DIR,
    limit: int = 0,
) -> List[Dict]:
    root = Path(dataset_dir)
    ann_path = root / annotations_file
    if not ann_path.exists():
        raise FileNotFoundError(f"Omni3D annotations file not found: {ann_path}")
    data = json.loads(ann_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])
    if not questions:
        raise ValueError(f"No questions found in {ann_path}")
    image_root = root / images_dir
    tasks = []
    skipped = 0
    for item in questions:
        image_filename = str(item.get("image_filename") or "")
        image_path = image_root / image_filename
        if not image_path.exists():
            skipped += 1
            continue
        image_stem = Path(str(item.get("image_index") or image_filename)).stem
        task_id = f"{image_stem}_{item.get('question_index')}"
        answer_type = str(item.get("answer_type") or "float")
        tasks.append({
            "task": TaskRecord(
                task_id=task_id,
                question=format_omni3d_question(str(item.get("question") or ""), answer_type),
                groundtruth=str(item.get("answer") or ""),
                image_paths=[str(image_path.resolve())],
                capability=str(item.get("problem_class") or ""),
                answer_type=answer_type,
            ),
            "answer_type": answer_type,
        })
        if limit > 0 and len(tasks) >= limit:
            break
    if skipped:
        print(f"[WARN] skipped {skipped} Omni3D items because image files were missing.")
    return tasks


def format_omni3d_question(question: str, answer_type: str) -> str:
    instruction = {
        "float": "Answer format: output only a number, without unit or explanation.",
        "int": "Answer format: output only an integer, without unit or explanation.",
        "bool": "Answer format: output only yes or no.",
        "str": "Answer format: output only the target name or short phrase.",
    }.get(answer_type, "Answer format: output only the final answer.")
    return f"{question}\n{instruction}"


def answer_matches_type(answer: str, answer_type: str) -> bool:
    value = str(answer or "").strip()
    if answer_type in {"float", "int"}:
        return extract_number(value) is not None
    if answer_type == "bool":
        return value.lower() in {"yes", "no"}
    return bool(value)


def check_match(prediction: str, groundtruth: str, answer_type: str = "float") -> bool:
    return answer_matches_typed(prediction, groundtruth, answer_type)


def extract_number(text: str) -> Optional[float]:
    match = re.search(r"-?\d+\.?\d*", str(text).strip())
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpatialSkillGrowth frozen benchmark inference")
    parser.add_argument("--engine", "-e", default=SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--base-urls", default=",".join(DEFAULT_BASE_URLS))
    parser.add_argument("--dataset-dir", default=OMNI3D_DEFAULT_DATASET_DIR)
    parser.add_argument(
        "--dataset",
        default="",
        help="Normalized JSON dataset for a non-Omni3D or custom benchmark.",
    )
    parser.add_argument("--img-root", default="")
    parser.add_argument("--benchmark", default="auto")
    parser.add_argument("--problem-classes", default="")
    parser.add_argument("--annotations-file", default=OMNI3D_DEFAULT_ANNOTATIONS_FILE)
    parser.add_argument("--explore-file", default=OMNI3D_DEFAULT_EXPLORE_FILE)
    parser.add_argument("--images-dir", default=OMNI3D_DEFAULT_IMAGES_DIR)
    parser.add_argument("--result-root", default="")
    parser.add_argument("--experiment", choices=sorted(EXPERIMENT_PRESETS), default="full")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--source-experiment", default="")
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-benchmark", default="")
    parser.add_argument("--source-result-root", default="")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-react-steps", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    return parser


def parse_base_urls(args) -> List[str]:
    if str(args.base_url or "").strip():
        return [str(args.base_url).strip()]
    urls = [url.strip() for url in str(args.base_urls or "").split(",") if url.strip()]
    return urls or [SPATIAL_SKILL_GROWTH_BASE_URL]


def main() -> None:
    args = build_parser().parse_args()
    config = build_experiment_config(args.experiment, args.seed)
    if args.dataset:
        normalized_tasks = load_online_tasks(args.dataset, args.img_root, args.limit)
        for task in normalized_tasks:
            task.answer_type = task.answer_type or "str"
            task.question = format_omni3d_question(task.question, task.answer_type)
        tasks = [
            {"task": task, "answer_type": task.answer_type}
            for task in normalized_tasks
        ]
        benchmark = _resolve_benchmark(args.benchmark, args.dataset)
        seen_ids: Set[str] = set()
        default_split = "zeroshot"
    else:
        tasks = load_omni3d_tasks(
            args.dataset_dir, args.annotations_file, args.images_dir, args.limit
        )
        benchmark = (
            "omni3d"
            if str(args.benchmark).strip().lower() == "auto"
            else normalize_benchmark(args.benchmark)
        )
        seen_ids = _load_seen_ids(Path(args.dataset_dir) / args.explore_file)
        default_split = "heldout"
    problem_classes = _resolve_problem_classes(
        benchmark,
        args.problem_classes,
        [item["task"].capability for item in tasks],
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
    paths.ensure(config, "infer", args.resume)
    (
        source_repository,
        planner_benchmark,
        planner_problem_classes,
        planner_metadata,
    ) = _source_repository(
        args,
        paths,
        benchmark,
        problem_classes,
        metadata,
        result_root,
    )
    if args.source_run_id:
        source = source_repository
        local_repository = WorkflowRepository(paths)
        snapshot = local_repository.snapshot_active_from(
            source,
            provenance={
                "source_benchmark": planner_benchmark,
                "target_benchmark": benchmark,
            },
        )
        source_repository = local_repository
        _record_skill_snapshot(paths, snapshot)
    if args.source_run_id and (
        planner_benchmark != benchmark
        or any(
            item["task"].capability
            and item["task"].capability not in planner_problem_classes
            for item in tasks
        )
    ):
        for item in tasks:
            item["task"].capability = ""
    seen_split = f"seen{len(seen_ids)}" if seen_ids else ""
    heldout_count = sum(
        item["task"].task_id not in seen_ids for item in tasks
    )
    heldout_split = (
        f"heldout{heldout_count}"
        if seen_ids and default_split == "heldout"
        else default_split
    )
    _write_split_manifest(
        paths,
        tasks,
        seen_ids,
        args.seed,
        benchmark,
        seen_split,
        heldout_split,
    )
    agents = []
    for base_url in parse_base_urls(args):
        llm = MultimodalChatOpenAI(
            base_url=base_url,
            model_name=args.engine,
            api_key=DEFAULT_API_KEY,
            timeout=SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS,
            temperature=SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE,
        )
        pipeline = ExperimentFactory(
            config,
            paths,
            llm,
            source_repository=source_repository,
            max_react_steps=args.max_react_steps,
            benchmark=planner_benchmark,
            problem_classes=planner_problem_classes,
            class_metadata=planner_metadata,
        ).build_inference()
        agents.append(SpatialSkillGrowthOmni3DInferenceAgent(pipeline))
    print(
        f"SpatialSkillGrowth {benchmark} inference: {len(tasks)} tasks, "
        f"{len(agents)} workers, run={paths.root}"
    )

    def process(agent, item):
        task = item["task"]
        split_name = seen_split if task.task_id in seen_ids else heldout_split
        return agent.ask(task, split_name, args.resume)

    with tqdm(total=len(tasks), desc="SpatialSkillGrowth infer") as progress:
        for start in range(0, len(tasks), len(agents)):
            batch = tasks[start:start + len(agents)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = {
                    executor.submit(process, agents[index], item): item
                    for index, item in enumerate(batch)
                }
                for future in concurrent.futures.as_completed(futures):
                    item = futures[future]
                    task = item["task"]
                    try:
                        result = future.result()
                        print(
                            f"[{task.task_id}] {'OK' if result.get('correct') else 'MISS'} "
                            f"split={result.get('split')} answer={str(result.get('answer'))[:80]} "
                            f"workflow={result.get('selected_workflow_id')}"
                        )
                    except Exception as exc:
                        print(f"[{task.task_id}] ERROR {type(exc).__name__}: {exc}")
                    progress.update(1)
    summary = write_evaluation_summary(paths)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if benchmark == "omni3d":
        predictions_path = export_inference_predictions(paths.root)
        print(f"Omni3D evaluation input: {predictions_path}")
        if not args.dataset:
            annotations_path = Path(args.dataset_dir) / args.annotations_file
            print(
                "Manual evaluation command:\n"
                "python evaluate/omni-3d/eval_spatialskillgrowth.py "
                f"--run-dir {paths.root} --annotations {annotations_path}"
            )


def _source_repository(
    args,
    paths: ExperimentPaths,
    benchmark: str,
    problem_classes: List[str],
    metadata: Dict[str, Dict[str, str]],
    result_root: str,
) -> tuple[WorkflowRepository, str, List[str], Dict[str, Dict[str, str]]]:
    if not args.source_run_id:
        return WorkflowRepository(paths), benchmark, problem_classes, metadata
    source_experiment = args.source_experiment or "full"
    source_benchmark = normalize_benchmark(args.source_benchmark or benchmark)
    source_result_root = (
        args.source_result_root
        or (
            result_root
            if source_benchmark == benchmark and args.result_root
            else result_root_for_benchmark(source_benchmark)
        )
    )
    source_paths = ExperimentPaths(
        source_experiment,
        args.source_run_id,
        source_result_root,
        benchmark=source_benchmark,
        problem_classes=problem_classes,
        class_metadata=metadata,
    )
    if not source_paths.active_skill_root.exists():
        raise FileNotFoundError(f"Source skill run does not exist: {source_paths.root}")
    manifest_path = source_paths.root / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )
    source_benchmark = normalize_benchmark(
        manifest.get("benchmark") or source_benchmark
    )
    source_problem_classes = [
        str(item) for item in manifest.get("problem_classes") or [] if str(item)
    ] or list(problem_classes_for(source_benchmark))
    source_metadata = class_metadata_for(source_benchmark)
    return (
        WorkflowRepository(source_paths),
        source_benchmark,
        source_problem_classes,
        source_metadata,
    )


def _load_seen_ids(path: Path) -> Set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    output = set()
    for item in data.get("questions", []):
        image_stem = Path(str(item.get("image_index") or item.get("image_filename") or "")).stem
        output.add(f"{image_stem}_{item.get('question_index')}")
    return output


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
    paths,
    tasks,
    seen_ids,
    seed,
    benchmark,
    seen_split,
    heldout_split,
):
    all_ids = [item["task"].task_id for item in tasks]
    splits = {heldout_split: [task_id for task_id in all_ids if task_id not in seen_ids]}
    if seen_split:
        splits[seen_split] = [task_id for task_id in all_ids if task_id in seen_ids]
    payload = {
        "benchmark": benchmark,
        "seed": seed,
        "all_task_ids": all_ids,
        "splits": splits,
    }
    if benchmark == "omni3d":
        if seen_split:
            payload["seen_task_ids"] = payload["splits"][seen_split]
        payload["heldout_task_ids"] = payload["splits"][heldout_split]
    (paths.root / "split.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _record_skill_snapshot(paths: ExperimentPaths, snapshot: Dict) -> None:
    manifest_path = paths.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["skill_source"] = {
        "source_root": snapshot.get("source_root"),
        "source_experiment": snapshot.get("source_experiment"),
        "source_run_id": snapshot.get("source_run_id"),
        "active_workflow_count": snapshot.get("active_workflow_count", 0),
        "snapshot_manifest": "skills/SOURCE_SNAPSHOT.json",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
