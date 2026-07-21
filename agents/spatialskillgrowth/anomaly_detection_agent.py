"""单个媒体或异常检测数据集的冻结 Skill 推理入口。"""

import argparse
import json

from dotenv import load_dotenv
from model.QwenFactory.pureQwenFactory import DEFAULT_API_KEY
from model.QwenFactory.pureQwenFactory import MultimodalChatOpenAI
from tqdm import tqdm

from agents.spatialskillgrowth.online_data import build_anomaly_task
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
from nodes.mem.spatialskillgrowth.pipeline.orchestrator import (
    write_evaluation_summary,
)
from nodes.mem.spatialskillgrowth.storage.growth_store import WorkflowRepository

"""
  python -m agents.spatialskillgrowth.anomaly_detection_agent \
    --input-file test/corpus/banner2/3q3LTsfxKkq.mp4 \
    --event-type banner \
    --run-id video_skill_banner_02
    
改个runid event-type input-file
"""



DEFAULT_FILE_ROOT = "benchmark/anomaly/files"
load_dotenv()


class SpatialSkillGrowthAnomalyDetectionAgent:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def ask(self, task, split_name="online", resume=False):
        return self.pipeline.ask(task, split_name, resume)

    def detect(self, file_path, event_type, task_id="", resume=False):
        task = build_anomaly_task(file_path, event_type, task_id=task_id)
        return self.ask(task, "online", resume)


def build_parser():
    parser = argparse.ArgumentParser(description="异常事件冻结 Skill 推理")
    parser.add_argument("--input-file", default="")
    parser.add_argument("--event-type", default="")
    parser.add_argument("--task-id", default="")
    parser.add_argument("--dataset", default="")
    parser.add_argument("--media-root", default=DEFAULT_FILE_ROOT)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--result-root", default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--source-result-root", default="")
    parser.add_argument("--engine", default=SPATIAL_SKILL_GROWTH_DEFAULT_ENGINE)
    parser.add_argument("--base-url", default=SPATIAL_SKILL_GROWTH_BASE_URL)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-react-steps", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    tasks = _load_tasks(args)
    event_types = _event_types(tasks)
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config(args.seed)
    paths = ExperimentPaths(
        args.run_id,
        args.result_root,
        problem_classes=event_types,
        class_metadata=metadata,
    )
    paths.ensure(config, "infer", args.resume)

    repository = WorkflowRepository(paths)
    if args.source_run_id:
        source_root = args.source_result_root or args.result_root
        source_paths = ExperimentPaths(
            args.source_run_id,
            source_root,
            problem_classes=event_types,
            class_metadata=metadata,
        )
        if not source_paths.active_skill_root.is_dir():
            raise FileNotFoundError("探索 Skill 运行不存在：" + str(source_paths.root))
        repository.snapshot_active_from(WorkflowRepository(source_paths))

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
        source_repository=repository,
        max_react_steps=args.max_react_steps,
    ).build_inference()
    agent = SpatialSkillGrowthAnomalyDetectionAgent(pipeline)

    for task in tqdm(tasks, desc="异常检测推理"):
        result = agent.ask(task, "online", args.resume)
        print(json.dumps(_result_line(result), ensure_ascii=False))
    summary = write_evaluation_summary(paths)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _load_tasks(args):
    input_file = str(args.input_file or "").strip()
    dataset = str(args.dataset or "").strip()
    if bool(input_file) == bool(dataset):
        raise ValueError("--input-file 和 --dataset 必须且只能提供一个。")
    if input_file:
        if not str(args.event_type or "").strip():
            raise ValueError("使用 --input-file 时必须提供 --event-type。")
        task = build_anomaly_task(input_file, args.event_type, args.task_id)
        return [task]
    return load_online_tasks(
        dataset,
        args.media_root,
        args.limit,
        require_groundtruth=False,
    )


def _event_types(tasks):
    output = []
    for task in tasks:
        if task.event_type not in output:
            output.append(task.event_type)
    return output


def _result_line(result):
    return {
        "task_id": result.get("task_id"),
        "event_type": result.get("event_type"),
        "is_anomaly": result.get("is_anomaly"),
        "threshold": result.get("threshold"),
        "answer": result.get("answer"),
        "workflow_id": result.get("selected_workflow_id"),
        "error": result.get("error"),
    }


if __name__ == "__main__":
    main()
