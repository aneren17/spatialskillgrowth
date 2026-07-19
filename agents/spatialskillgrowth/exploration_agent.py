"""使用少量有标签异常样本探索并生成 Skill。"""

import argparse
import json

from dotenv import load_dotenv
from model.QwenFactory.pureQwenFactory import DEFAULT_API_KEY
from model.QwenFactory.pureQwenFactory import MultimodalChatOpenAI
from tqdm import tqdm

from agents.spatialskillgrowth.online_data import load_online_tasks
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


DEFAULT_DATASET = "benchmark/anomaly/explore.json"
DEFAULT_MEDIA_ROOT = "benchmark/anomaly/files"
load_dotenv()


def build_parser():
    parser = argparse.ArgumentParser(description="异常检测 Skill 探索")
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--media-root", default=DEFAULT_MEDIA_ROOT)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--result-root", default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--engine", default=SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE)
    parser.add_argument("--base-url", default=SPATIAL_SKILL_GROWTH_BASE_URL)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-react-steps", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    tasks = load_online_tasks(args.dataset, args.media_root, args.limit)
    event_types = []
    for task in tasks:
        if task.event_type not in event_types:
            event_types.append(task.event_type)

    metadata = class_metadata_for_anomaly()
    config = build_experiment_config(args.seed)
    paths = ExperimentPaths(
        args.run_id,
        args.result_root,
        problem_classes=event_types,
        class_metadata=metadata,
    )
    paths.ensure(config, "explore", args.resume)
    _write_split(paths, tasks, config.seed)

    llm = MultimodalChatOpenAI(
        base_url=args.base_url,
        model_name=args.engine,
        api_key=DEFAULT_API_KEY,
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

    for task in tqdm(tasks, desc="异常检测探索"):
        result = pipeline.ask(task, args.resume)
        print(
            "["
            + task.task_id
            + "] event_type="
            + str(result.get("event_type"))
            + " correct="
            + str(result.get("correct"))
        )
    report = pipeline.validate_provisional(tasks)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _write_split(paths, tasks, seed):
    task_ids = []
    for task in tasks:
        task_ids.append(task.task_id)
    payload = {
        "seed": seed,
        "exploration_task_ids": task_ids,
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    (paths.root / "split.json").write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
