"""使用少量有标签异常样本探索并生成 Skill。"""
# python -m agents.spatialskillgrowth.exploration_agent \
#     --dataset-root benchmark/anomaly/skill_datasets \
#     --run-id anomaly_explore_subset_relaxed
import argparse
import concurrent.futures
import json
from pathlib import Path

from dotenv import load_dotenv
from model.QwenFactory.pureQwenFactory import DEFAULT_API_KEY
from model.QwenFactory.pureQwenFactory import MultimodalChatOpenAI
from tqdm import tqdm

from agents.spatialskillgrowth.online_data import load_online_tasks
from agents.spatialskillgrowth.online_data import resolve_event_type
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_BASE_URL
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS
from nodes.mem.spatialskillgrowth.core.anomaly_events import (
    class_metadata_for_anomaly,
)
from nodes.mem.spatialskillgrowth.core.experiment_config import DEFAULT_RESULT_ROOT
from nodes.mem.spatialskillgrowth.core.experiment_config import DEFAULT_SEED
from nodes.mem.spatialskillgrowth.core.experiment_config import ExperimentPaths
from nodes.mem.spatialskillgrowth.core.experiment_config import build_experiment_config
from nodes.mem.spatialskillgrowth.pipeline.orchestrator import ExperimentFactory


DEFAULT_DATASET_ROOT = "benchmark/anomaly/skill_datasets"
DEFAULT_BASE_URLS = (
    "http://127.0.0.1:8861/v1",
    "http://127.0.0.1:8862/v1",
    "http://127.0.0.1:8863/v1",
)
load_dotenv()


def build_parser():
    parser = argparse.ArgumentParser(description="异常检测 Skill 探索")
    parser.add_argument(
        "--dataset-root",
        default=DEFAULT_DATASET_ROOT,
        help="包含 INDEX.json 的多类别 benchmark 根目录。",
    )
    parser.add_argument(
        "--dataset",
        default="",
        help="只探索一个 JSON 数据集；提供后不再读取 --dataset-root。",
    )
    parser.add_argument(
        "--media-root",
        default="",
        help="单数据集的媒体根目录；默认使用数据集所在目录。",
    )
    parser.add_argument(
        "--event-types",
        default="",
        help="只探索指定类别，多个英文 event_type 用逗号分隔。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="每个类别最多加载多少条；0 表示全部。",
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--result-root", default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--engine", default=SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE)
    parser.add_argument(
        "--base-url",
        default="",
        help="只使用一个模型端口；提供后覆盖 --base-urls。",
    )
    parser.add_argument(
        "--base-urls",
        default=",".join(DEFAULT_BASE_URLS),
        help="探索模型地址，使用逗号分隔。",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-react-steps", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="只检查数据并打印类别到端口的分配，不调用模型。",
    )
    return parser


def main():
    args = build_parser().parse_args()
    tasks = _load_tasks(args)
    base_urls = _parse_base_urls(args)
    worker_tasks = _partition_tasks_by_event_type(tasks, len(base_urls))
    worker_specs = _worker_specs(base_urls, worker_tasks)
    _print_worker_plan(worker_specs)
    if args.plan_only:
        return

    event_types = _event_types(tasks)
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config(args.seed)
    paths = ExperimentPaths(
        args.run_id,
        args.result_root,
        problem_classes=event_types,
        class_metadata=metadata,
    )
    paths.ensure(config, "explore", args.resume)
    _write_split(paths, tasks, config.seed, worker_specs)

    workers = []
    for worker_spec in worker_specs:
        llm = MultimodalChatOpenAI(
            base_url=worker_spec["base_url"],
            model_name=args.engine,
            api_key=DEFAULT_API_KEY,
            max_retries=0,
            timeout=SPATIAL_SKILL_GROWTH_LLM_TIMEOUT_SECONDS,
            temperature=SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE,
        )
        pipeline = ExperimentFactory(
            config,
            paths,
            llm,
            max_react_steps=args.max_react_steps,
            exploration_split_name="explore" + str(len(tasks)),
        ).build_exploration()
        workers.append(
            {
                "worker_id": worker_spec["worker_id"],
                "base_url": worker_spec["base_url"],
                "tasks": worker_tasks[worker_spec["worker_id"]],
                "pipeline": pipeline,
            }
        )

    worker_results = []
    with tqdm(total=len(tasks), desc="异常检测探索") as progress:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(workers)
        ) as executor:
            futures = []
            for worker in workers:
                future = executor.submit(
                    _run_worker,
                    worker,
                    args.resume,
                    progress,
                )
                futures.append(future)
            for future in concurrent.futures.as_completed(futures):
                worker_results.append(future.result())

    validation_reports = []
    for worker in workers:
        report = worker["pipeline"].validate_provisional(worker["tasks"])
        validation_reports.append(
            {
                "worker_id": worker["worker_id"],
                "base_url": worker["base_url"],
                "report": report,
            }
        )
    report = _merge_validation_reports(validation_reports)
    report_path = paths.metrics_root / "provisional_validation.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    failed_count = 0
    for result in worker_results:
        failed_count += result["failed_count"]
    if failed_count:
        raise RuntimeError(
            str(failed_count)
            + " 条探索任务失败；错误已保存，可使用 --resume 重试。"
        )


def _load_tasks(args):
    dataset = str(args.dataset or "").strip()
    if dataset:
        dataset_path = Path(dataset).resolve()
        media_root = str(args.media_root or "").strip()
        if not media_root:
            media_root = str(dataset_path.parent)
        tasks = load_online_tasks(
            str(dataset_path),
            media_root,
            args.limit,
        )
    else:
        tasks = _load_tasks_from_dataset_root(
            Path(args.dataset_root).resolve(),
            args.event_types,
            args.limit,
        )
    image_tasks = [
        task for task in tasks
        if task.media_type == "image"
    ]
    if not image_tasks:
        raise ValueError("探索数据中没有图片任务；视频只用于冻结推理。")
    return image_tasks


def _load_tasks_from_dataset_root(dataset_root, event_types_value, limit):
    index_path = dataset_root / "INDEX.json"
    if not index_path.is_file():
        raise FileNotFoundError("benchmark 总索引不存在：" + str(index_path))
    with open(index_path, "r", encoding="utf-8") as handle:
        index = json.load(handle)
    entries = index.get("datasets")
    if not isinstance(entries, list):
        raise ValueError("INDEX.json 缺少 datasets 数组。")

    selected_event_types = _parse_event_types(event_types_value)
    tasks = []
    loaded_event_types = []
    for entry in entries:
        event_type = resolve_event_type(entry.get("event_type"))
        if selected_event_types and event_type not in selected_event_types:
            continue
        dataset_path = dataset_root / str(entry.get("dataset_path") or "")
        media_root = dataset_root / str(entry.get("media_root") or "")
        class_tasks = load_online_tasks(
            str(dataset_path),
            str(media_root),
            limit,
        )
        for task in class_tasks:
            if task.event_type != event_type:
                raise ValueError(
                    "数据集中的 event_type 与 INDEX.json 不一致："
                    + str(dataset_path)
                )
        tasks.extend(class_tasks)
        loaded_event_types.append(event_type)

    if selected_event_types:
        missing = selected_event_types.difference(loaded_event_types)
        if missing:
            raise ValueError(
                "INDEX.json 中缺少指定类别：" + "、".join(sorted(missing))
            )
    if not tasks:
        raise ValueError("没有加载到探索任务。")
    return tasks


def _parse_event_types(value):
    event_types = set()
    for item in str(value or "").split(","):
        item = item.strip()
        if item:
            event_types.add(resolve_event_type(item))
    return event_types


def _parse_base_urls(args):
    base_url = str(args.base_url or "").strip()
    if base_url:
        return [base_url]
    base_urls = []
    for value in str(args.base_urls or "").split(","):
        value = value.strip()
        if value:
            base_urls.append(value)
    if not base_urls:
        base_urls.append(SPATIAL_SKILL_GROWTH_BASE_URL)
    return base_urls


def _event_types(tasks):
    event_types = []
    for task in tasks:
        if task.event_type not in event_types:
            event_types.append(task.event_type)
    return event_types


def _partition_tasks_by_event_type(tasks, worker_count):
    if worker_count <= 0:
        raise ValueError("至少需要一个模型端口。")
    tasks_by_event_type = {}
    event_types = []
    for task in tasks:
        if task.event_type not in tasks_by_event_type:
            tasks_by_event_type[task.event_type] = []
            event_types.append(task.event_type)
        tasks_by_event_type[task.event_type].append(task)

    worker_tasks = []
    for unused_index in range(worker_count):
        worker_tasks.append([])
    for index, event_type in enumerate(event_types):
        worker_index = index % worker_count
        worker_tasks[worker_index].extend(tasks_by_event_type[event_type])
    return worker_tasks


def _worker_specs(base_urls, worker_tasks):
    specs = []
    for worker_id, tasks in enumerate(worker_tasks):
        if not tasks:
            continue
        specs.append(
            {
                "worker_id": worker_id,
                "base_url": base_urls[worker_id],
                "event_types": _event_types(tasks),
                "task_ids": [task.task_id for task in tasks],
                "task_count": len(tasks),
            }
        )
    return specs


def _print_worker_plan(worker_specs):
    payload = {
        "worker_count": len(worker_specs),
        "workers": [],
    }
    for spec in worker_specs:
        payload["workers"].append(
            {
                "worker_id": spec["worker_id"],
                "base_url": spec["base_url"],
                "event_types": spec["event_types"],
                "event_type_count": len(spec["event_types"]),
                "task_count": spec["task_count"],
            }
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _run_worker(worker, resume, progress):
    failed_count = 0
    completed_count = 0
    pipeline = worker["pipeline"]
    for task in worker["tasks"]:
        try:
            result = pipeline.ask(task, resume)
            tqdm.write(
                "[worker="
                + str(worker["worker_id"])
                + "]["
                + task.task_id
                + "] event_type="
                + str(result.get("event_type"))
                + " correct="
                + str(result.get("correct"))
            )
            completed_count += 1
        except Exception as error:
            failed_count += 1
            tqdm.write(
                "[worker="
                + str(worker["worker_id"])
                + "]["
                + task.task_id
                + "] ERROR "
                + type(error).__name__
                + ": "
                + str(error)
            )
        finally:
            progress.update(1)
    return {
        "worker_id": worker["worker_id"],
        "completed_count": completed_count,
        "failed_count": failed_count,
    }


def _merge_validation_reports(worker_reports):
    merged = {
        "attempted": 0,
        "promoted": [],
        "archived": [],
        "skipped": [],
        "workers": worker_reports,
    }
    for worker_report in worker_reports:
        report = worker_report["report"]
        merged["attempted"] += int(report.get("attempted") or 0)
        for key in ("promoted", "archived"):
            for value in report.get(key) or []:
                if value not in merged[key]:
                    merged[key].append(value)
        merged["skipped"].extend(report.get("skipped") or [])
    return merged


def _write_split(paths, tasks, seed, worker_specs):
    task_ids = []
    for task in tasks:
        task_ids.append(task.task_id)
    payload = {
        "seed": seed,
        "exploration_task_ids": task_ids,
        "model_workers": worker_specs,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    (paths.root / "split.json").write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
