"""异常检测主链路的无网络回归测试。"""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from agents.spatialskillgrowth.online_data import build_anomaly_task
from agents.spatialskillgrowth.online_data import load_online_tasks
from agents.spatialskillgrowth.online_data import resolve_event_type
from nodes.mem.spatialskillgrowth.core.anomaly_events import ANOMALY_EVENT_TYPES
from nodes.mem.spatialskillgrowth.core.anomaly_events import class_metadata_for_anomaly
from nodes.mem.spatialskillgrowth.core.experiment_config import DEFAULT_EDITABLE_SKILL_ROOT
from nodes.mem.spatialskillgrowth.core.experiment_config import ExperimentPaths
from nodes.mem.spatialskillgrowth.core.experiment_config import build_experiment_config
from nodes.mem.spatialskillgrowth.growth.param_space import ParamSpace
from nodes.mem.spatialskillgrowth.growth.workflow_mutator import (
    build_anomaly_baseline_workflow,
)
from nodes.mem.spatialskillgrowth.pipeline.answer_evaluator import answer_matches
from nodes.mem.spatialskillgrowth.pipeline.evidence_validator import (
    build_evidence_validator,
)
from nodes.mem.spatialskillgrowth.pipeline.media_processing import MediaPreprocessor
from nodes.mem.spatialskillgrowth.pipeline.orchestrator import ExperimentFactory
from nodes.mem.spatialskillgrowth.pipeline.task_router import TaskPlanner
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import ToolRuntime
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import extract_anomaly_result
from nodes.mem.spatialskillgrowth.skills.human_skill_validation import (
    validate_human_skill,
)
from nodes.mem.spatialskillgrowth.skills.skill_retriever import (
    workflow_structurally_eligible,
)
from nodes.mem.spatialskillgrowth.storage.growth_store import WorkflowRepository
from scripts.run_banner_demo_exploration import run_demo
from server import anomaly_detection_server


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BANNER_DATASET = PROJECT_ROOT / "benchmark/anomaly/banner_demo/explore.json"
BANNER_IMAGE_ROOT = PROJECT_ROOT / "benchmark/anomaly/banner_demo/images"
BANNER_IMAGE = BANNER_IMAGE_ROOT / "banner_00_00252ms.jpg"
BANNER_VIDEO = PROJECT_ROOT / "test/banner.mp4"
BANNER_SKILL = PROJECT_ROOT / "skills/spatialskillgrowth/banner"
BANNER_SCRIPT = BANNER_SKILL / "scripts/banner-human-review-v1.py"


class MockEmbeddingTool:
    name = "embeddingTool"

    @staticmethod
    def invoke(args):
        event_type = str(args.get("event_type") or "")
        return {
            "status": "success",
            "event_type": event_type,
            "is_anomaly": True,
            "decision": "是",
            "threshold": 0.66,
        }


class MockTool:
    def __init__(self, name):
        self.name = name

    def invoke(self, args):
        return "ok"


class DisabledLLM:
    def invoke(self, messages):
        raise RuntimeError("该测试不应调用 LLM。")

    def bind_tools(self, tools):
        raise RuntimeError("该测试不应进入 ReAct。")


class MockDetectionAgent:
    def __init__(self):
        self.media_path = ""

    def detect(self, file_path, event_type, task_id="", resume=False):
        self.media_path = file_path
        assert event_type == "banner"
        assert task_id.startswith("api__")
        return {
            "is_anomaly": False,
            "threshold": 0.42,
            "attempts": [
                {
                    "success": True,
                    "answer": "是",
                    "successful_tools": ["embeddingTool", "MLLM"],
                }
            ],
        }


def test_event_taxonomy_and_bool_evaluator():
    assert len(ANOMALY_EVENT_TYPES) == 55
    assert "banner" in ANOMALY_EVENT_TYPES
    assert resolve_event_type("横幅异常") == "banner"
    assert answer_matches("是", "yes")
    assert answer_matches("正常", "否")
    assert not answer_matches("是", "否")
    metadata = class_metadata_for_anomaly()
    assert set(metadata) == set(ANOMALY_EVENT_TYPES)
    assert metadata["banner"]["primary_tool"] == "embeddingTool"


def test_input_is_one_media_and_one_event_type():
    tasks = load_online_tasks(str(BANNER_DATASET), str(BANNER_IMAGE_ROOT), limit=2)
    assert len(tasks) == 2
    for task in tasks:
        assert task.event_type == "banner"
        assert task.media_path
        assert task.media_type == "image"
        assert "event_type 为 `banner`" in task.question
    direct = build_anomaly_task(str(BANNER_VIDEO), "banner")
    assert direct.media_type == "video"
    assert direct.media_path == str(BANNER_VIDEO.resolve())


def test_media_preprocessor_keeps_video_and_samples_frames():
    task = build_anomaly_task(str(BANNER_VIDEO), "banner", task_id="video_test")
    with tempfile.TemporaryDirectory() as root:
        processor = MediaPreprocessor(Path(root), sample_fps=1.0, max_sampled_frames=3)
        prepared = processor.prepare(task)
        assert prepared.media_path == str(BANNER_VIDEO.resolve())
        assert 1 <= len(prepared.visual_paths) <= 3
        assert prepared.media_metadata["sampled_frame_count"] == len(prepared.visual_paths)
        for frame_path in prepared.visual_paths:
            assert Path(frame_path).is_file()


def test_planner_has_no_llm_classification_or_omni_slots():
    registry = {
        "embeddingTool": MockEmbeddingTool(),
        "MLLM": MockTool("MLLM"),
        "paddleHeadDetTool": MockTool("paddleHeadDetTool"),
    }
    plan = TaskPlanner().plan("banner", [str(BANNER_IMAGE)], registry)
    assert plan["problem_class"] == "banner"
    assert plan["slot_bindings"] == {"event_type": "banner"}
    assert "embeddingTool" in plan["selected_tools"]
    assert "paddleHeadDetTool" in plan["selected_tools"]
    assert plan["excluded_tools"] == []


def test_run_workspace_uses_editable_skills_only():
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config()
    with tempfile.TemporaryDirectory() as root:
        paths = ExperimentPaths(
            "workspace_test",
            root,
            problem_classes=["banner"],
            class_metadata=metadata,
        )
        paths.ensure(config, "explore")
        assert (paths.skill_root / "SKILLSET.json").is_file()
        assert not (paths.skill_root / "WHITEBOARD.json").exists()
        source_markdown = DEFAULT_EDITABLE_SKILL_ROOT / "banner/SKILL.md"
        for status_root in (
            paths.active_skill_root,
            paths.provisional_skill_root,
            paths.archive_skill_root,
        ):
            target_markdown = status_root / "banner/SKILL.md"
            assert target_markdown.read_bytes() == source_markdown.read_bytes()
        assert (paths.active_skill_root / "banner/scripts/banner-human-review-v1.py").is_file()
        assert not list(paths.provisional_skill_root.glob("*/scripts/*.py"))


def test_baseline_workflow_and_embedding_result():
    workflow = build_anomaly_baseline_workflow("banner")
    assert workflow.applicability.problem_class == "banner"
    assert workflow.steps[0].tool_name == "embeddingTool"
    assert workflow_structurally_eligible(
        workflow,
        {"event_type": "banner"},
        ["embeddingTool"],
    )
    runtime = ToolRuntime({"embeddingTool": MockEmbeddingTool()})
    result = runtime.execute("embeddingTool", {
        "file_path": str(BANNER_IMAGE),
        "event_type": "banner",
    })
    anomaly = extract_anomaly_result({
        "success": result["ok"],
        "used_tools": ["embeddingTool"],
        "observations": [{"tool": "embeddingTool", "result": result}],
    })
    assert anomaly["event_type"] == "banner"
    assert anomaly["is_anomaly"] is True
    assert anomaly["threshold"] == 0.66


def test_evidence_validator_rejects_missing_threshold():
    validator = build_evidence_validator()
    runtime = ToolRuntime({"embeddingTool": MockEmbeddingTool()})
    tool_result = runtime.execute("embeddingTool", {
        "file_path": str(BANNER_IMAGE),
        "event_type": "banner",
    })
    valid_result = {
        "success": True,
        "used_tools": ["embeddingTool"],
        "observations": [{"tool": "embeddingTool", "result": tool_result}],
    }
    decision = validator.validate(
        "banner", "question", "是", valid_result, [str(BANNER_IMAGE)]
    )
    assert decision.accepted
    invalid_result = dict(valid_result)
    invalid_tool_result = dict(tool_result)
    invalid_tool_result["data"] = dict(tool_result["data"])
    invalid_tool_result["data"]["threshold"] = None
    invalid_result["observations"] = [
        {"tool": "embeddingTool", "result": invalid_tool_result}
    ]
    decision = validator.validate(
        "banner", "question", "是", invalid_result, [str(BANNER_IMAGE)]
    )
    assert not decision.accepted


def test_human_banner_skill_executes():
    report = validate_human_skill(
        BANNER_SKILL,
        BANNER_SCRIPT,
        BANNER_IMAGE,
        "banner",
    )
    assert report["valid"]
    assert report["checks"]["execution"]
    assert report["checks"]["evidence_contract"]
    assert report["execution"]["threshold"] == 0.66


def test_param_space_has_no_omni_slots():
    param_space = ParamSpace()
    serialized = json.dumps(
        [atom.to_dict() for atom in param_space.atoms_for("banner")],
        ensure_ascii=False,
    )
    assert "target_a" not in serialized
    assert "sam_query_a" not in serialized
    assert "reference_value" not in serialized
    assert "embeddingTool" in serialized


def test_inference_pipeline_returns_threshold_without_llm():
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config()
    config.use_react = False
    with tempfile.TemporaryDirectory() as root:
        paths = ExperimentPaths(
            "infer_test",
            root,
            problem_classes=["banner"],
            class_metadata=metadata,
        )
        paths.ensure(config, "infer")
        runtime = ToolRuntime({"embeddingTool": MockEmbeddingTool()})
        pipeline = ExperimentFactory(
            config,
            paths,
            DisabledLLM(),
            runtime=runtime,
        ).build_inference()
        task = build_anomaly_task(str(BANNER_IMAGE), "banner", groundtruth="是")
        result = pipeline.ask(task, "online")
        assert result["answer"] == "是"
        assert result["is_anomaly"] is True
        assert result["threshold"] == 0.66
        assert result["correct"] is True


def test_source_skill_snapshot():
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config()
    with tempfile.TemporaryDirectory() as root:
        source_paths = ExperimentPaths(
            "source_run", root, ["banner"], metadata
        )
        source_paths.ensure(config, "explore")
        target_paths = ExperimentPaths(
            "target_run", root, ["banner"], metadata
        )
        target_paths.ensure(config, "infer")
        target = WorkflowRepository(target_paths)
        source = WorkflowRepository(source_paths)
        snapshot = target.snapshot_active_from(source)
        assert snapshot["source_run_id"] == "source_run"
        assert (target_paths.skill_root / "SOURCE_SNAPSHOT.json").is_file()
        assert not (target_paths.skill_root / "WHITEBOARD.json").exists()


def test_fastapi_upload_and_other_tool_override():
    original_agent = anomaly_detection_server.AGENT
    mock_agent = MockDetectionAgent()
    anomaly_detection_server.AGENT = mock_agent
    try:
        client = TestClient(anomaly_detection_server.app)
        response = client.post(
            "/detect",
            data={"event_type": "banner"},
            files={"file": ("window.mp4", b"mock-video", "video/mp4")},
        )
        assert response.status_code == 200
        assert response.json() == {"is_anomaly": 1, "threshold": 1.0}
        assert mock_agent.media_path
        assert not Path(mock_agent.media_path).exists()
    finally:
        anomaly_detection_server.AGENT = original_agent


def test_fastapi_keeps_embedding_threshold():
    positive = anomaly_detection_server._build_response({
        "is_anomaly": True,
        "threshold": 0.65,
        "attempts": [],
    })
    negative = anomaly_detection_server._build_response({
        "is_anomaly": False,
        "threshold": 0.31,
        "attempts": [],
    })
    assert positive.model_dump() == {"is_anomaly": 1, "threshold": 0.65}
    assert negative.model_dump() == {"is_anomaly": 0, "threshold": 0.31}


def test_ten_item_banner_demo():
    with tempfile.TemporaryDirectory() as root:
        run_root = run_demo(
            BANNER_DATASET,
            BANNER_IMAGE_ROOT,
            Path(root),
            "banner_demo",
        )
        report = json.loads(
            (run_root / "demo_report.json").read_text(encoding="utf-8")
        )
        assert report["task_count"] == 10
        assert report["correct_count"] == 10
        lines = (run_root / "results/per_task.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(lines) == 10


def main():
    tests = [
        test_event_taxonomy_and_bool_evaluator,
        test_input_is_one_media_and_one_event_type,
        test_media_preprocessor_keeps_video_and_samples_frames,
        test_planner_has_no_llm_classification_or_omni_slots,
        test_run_workspace_uses_editable_skills_only,
        test_baseline_workflow_and_embedding_result,
        test_evidence_validator_rejects_missing_threshold,
        test_human_banner_skill_executes,
        test_param_space_has_no_omni_slots,
        test_inference_pipeline_returns_threshold_without_llm,
        test_source_skill_snapshot,
        test_fastapi_upload_and_other_tool_override,
        test_fastapi_keeps_embedding_threshold,
        test_ten_item_banner_demo,
    ]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print("SpatialSkillGrowth anomaly no-API tests passed:", len(tests))


if __name__ == "__main__":
    main()
