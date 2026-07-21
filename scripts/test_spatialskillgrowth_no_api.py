"""异常检测主链路的无网络回归测试。"""

import json
import shutil
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
from nodes.mem.spatialskillgrowth.core.models import ApplicabilitySpec
from nodes.mem.spatialskillgrowth.core.models import MutationSpec
from nodes.mem.spatialskillgrowth.core.models import ParamAtom
from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec
from nodes.mem.spatialskillgrowth.core.models import WorkflowStep
from nodes.mem.spatialskillgrowth.growth.param_space import ParamSpace
from nodes.mem.spatialskillgrowth.growth.workflow_lifecycle import (
    WorkflowLifecycleManager,
)
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
from nodes.mem.spatialskillgrowth.skills.human_skill_deployment import (
    deploy_human_skill,
)
from nodes.mem.spatialskillgrowth.skills.human_skill_validation import (
    validate_human_skill,
)
from nodes.mem.spatialskillgrowth.skills.skill_retriever import (
    build_retriever,
    workflow_structurally_eligible,
)
from nodes.mem.spatialskillgrowth.storage.growth_store import ExperimentStore
from nodes.mem.spatialskillgrowth.storage.growth_store import WorkflowRepository
from scripts.run_banner_demo_exploration import run_demo
from server import anomaly_detection_server


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BANNER_DATASET = PROJECT_ROOT / "benchmark/anomaly/banner_demo/explore.json"
BANNER_IMAGE_ROOT = PROJECT_ROOT / "benchmark/anomaly/banner_demo/images"
BANNER_IMAGE = BANNER_IMAGE_ROOT / "banner_00_00252ms.jpg"
BANNER_VIDEO = PROJECT_ROOT / "test/banner.mp4"
BANNER_SKILL = PROJECT_ROOT / "skills/spatialskillgrowth/banner"
WHITEBOARD_SKILL_ROOT = PROJECT_ROOT / "skills/spatialskillgrowth_whiteboard"
BANNER_SCRIPT = BANNER_SKILL / "scripts/banner-ocr-example.py"
BANNER_CROP_SCRIPT = BANNER_SKILL / "scripts/banner-crop-example.py"


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


class MockNegativeEmbeddingTool:
    name = "embeddingTool"

    @staticmethod
    def invoke(args):
        event_type = str(args.get("event_type") or "")
        return {
            "status": "success",
            "event_type": event_type,
            "is_anomaly": False,
            "decision": "否",
            "threshold": 0.31,
        }


class MockAnswerTool:
    def __init__(self, name, answer):
        self.name = name
        self.answer = answer

    def invoke(self, args):
        return self.answer


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


class SkillSelectionLLM:
    def __init__(self, workflow_id):
        self.workflow_id = workflow_id
        self.messages = []

    def invoke(self, messages):
        self.messages = messages
        return json.dumps({
            "action": "select",
            "ranked_workflow_ids": [self.workflow_id],
            "reason": "SKILL.md 说明该路线适合当前画面。",
        }, ensure_ascii=False)


class SkillSelectionRepository:
    def __init__(self, workflows, guidance):
        self.workflows = workflows
        self.guidance = guidance

    def list_retrievable(self, _event_type, include_provisional=False):
        return list(self.workflows)

    def skill_guidance(self, _event_type, include_provisional=False):
        return self.guidance


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
    assert metadata["banner"]["primary_tool"] == "modality_aware"
    assert metadata["banner"]["video_primary_tool"] == "embeddingTool"


def test_input_is_one_media_and_one_event_type():
    tasks = load_online_tasks(str(BANNER_DATASET), str(BANNER_IMAGE_ROOT), limit=2)
    assert len(tasks) == 2
    for task in tasks:
        assert task.event_type == "banner"
        assert task.media_path
        assert task.media_type == "image"
        assert "event_type 为 `banner`" in task.question
        assert "embeddingTool 可使用图片能力" in task.question
    direct = build_anomaly_task(str(BANNER_VIDEO), "banner")
    assert direct.media_type == "video"
    assert direct.media_path == str(BANNER_VIDEO.resolve())
    assert "原始视频 embedding 由独立工作流执行" in direct.question


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
    assert plan["slot_bindings"] == {
        "event_type": "banner",
        "media_type": "image",
    }
    assert "embeddingTool" in plan["selected_tools"]
    assert "embeddingTool" not in plan["excluded_tools"]
    assert "paddleHeadDetTool" in plan["selected_tools"]
    video_plan = TaskPlanner().plan(
        "banner",
        [str(BANNER_VIDEO)],
        registry,
    )
    assert video_plan["media_type"] == "video"
    assert "embeddingTool" in video_plan["selected_tools"]


def test_image_skill_is_eligible_for_video_frame_inference():
    workflow = WorkflowSpec(
        workflow_id="banner_frame_skill",
        name="banner_frame_skill",
        applicability=ApplicabilitySpec(
            problem_class="banner",
            required_tools=["MLLM"],
        ),
        steps=[WorkflowStep(
            tool_name="MLLM",
            args={"file": "$image", "query": "判断横幅异常。"},
        )],
    )
    allowed_tools = ["MLLM", "embeddingTool"]
    slots = {"event_type": "banner", "media_type": "video"}
    assert workflow_structurally_eligible(
        workflow,
        slots,
        allowed_tools,
        "video",
    )


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
        assert (paths.active_skill_root / "banner/scripts/banner-ocr-example.py").is_file()
        assert (paths.active_skill_root / "banner/scripts/banner-crop-example.py").is_file()
        assert not list(paths.provisional_skill_root.glob("*/scripts/*.py"))


def test_skill_markdowns_are_compact():
    forbidden_headings = (
        "## 用途",
        "## 事件接口",
        "## 各端显示名称",
        "## 工具调用模板",
        "## 证据要求",
    )
    roots = [DEFAULT_EDITABLE_SKILL_ROOT, WHITEBOARD_SKILL_ROOT]
    checked = 0
    for root in roots:
        for skill_path in sorted(root.glob("*/SKILL.md")):
            text = skill_path.read_text(encoding="utf-8")
            assert "## Skill 作用" in text
            assert "## 工作流选择" in text
            assert "## 可选工作流" in text
            assert "## 资源" in text
            for heading in forbidden_headings:
                assert heading not in text
            checked += 1
    assert checked == 110


def test_embedding_parallel_channel_is_not_retrievable_skill():
    workflow = build_anomaly_baseline_workflow("banner")
    assert workflow.applicability.problem_class == "banner"
    assert workflow.steps[0].tool_name == "embeddingTool"
    assert not workflow_structurally_eligible(
        workflow,
        {"event_type": "banner", "media_type": "video"},
        ["embeddingTool"],
        "video",
    )
    runtime = ToolRuntime({"embeddingTool": MockEmbeddingTool()})
    result = runtime.execute("embeddingTool", {
        "file_path": str(BANNER_VIDEO),
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

    image_workflow = WorkflowSpec(
        workflow_id="banner_image_embedding",
        name="banner_image_embedding",
        applicability=ApplicabilitySpec(
            problem_class="banner",
            required_slots=["event_type"],
            required_tools=["embeddingTool"],
        ),
        steps=[WorkflowStep(
            tool_name="embeddingTool",
            args={
                "file_path": "$image",
                "event_type": "$slot.event_type",
            },
        )],
    )
    assert workflow_structurally_eligible(
        image_workflow,
        {"event_type": "banner", "media_type": "image"},
        ["embeddingTool"],
        "image",
    )


def test_evidence_validator_rejects_missing_threshold():
    validator = build_evidence_validator()
    runtime = ToolRuntime({"embeddingTool": MockEmbeddingTool()})
    tool_result = runtime.execute("embeddingTool", {
        "file_path": str(BANNER_VIDEO),
        "event_type": "banner",
    })
    valid_result = {
        "success": True,
        "used_tools": ["embeddingTool"],
        "observations": [{"tool": "embeddingTool", "result": tool_result}],
    }
    decision = validator.validate(
        "banner",
        "question",
        "是",
        valid_result,
        [str(BANNER_VIDEO)],
        "video",
    )
    assert decision.accepted
    image_decision = validator.validate(
        "banner",
        "question",
        "是",
        valid_result,
        [str(BANNER_IMAGE)],
        "image",
    )
    assert image_decision.accepted
    invalid_result = dict(valid_result)
    invalid_tool_result = dict(tool_result)
    invalid_tool_result["data"] = dict(tool_result["data"])
    invalid_tool_result["data"]["threshold"] = None
    invalid_result["observations"] = [
        {"tool": "embeddingTool", "result": invalid_tool_result}
    ]
    decision = validator.validate(
        "banner",
        "question",
        "是",
        invalid_result,
        [str(BANNER_VIDEO)],
        "video",
    )
    assert not decision.accepted

    visual_result = {
        "success": True,
        "final_answer": "是",
        "used_tools": ["MLLM"],
        "observations": [{
            "tool": "MLLM",
            "result": {"ok": True, "status": "success"},
        }],
    }
    decision = validator.validate(
        "banner",
        "question",
        "是",
        visual_result,
        [str(BANNER_IMAGE)],
        "image",
    )
    assert decision.accepted
    assert decision.contract_checks["visual_evidence_called"]


def test_human_banner_skill_executes():
    before = {}
    for path in BANNER_SKILL.rglob("*"):
        if path.is_file():
            before[str(path.relative_to(BANNER_SKILL))] = path.read_bytes()
    report = validate_human_skill(
        BANNER_SKILL,
        BANNER_SCRIPT,
    )
    assert report["valid"]
    assert report["checks"]["mock_execution"]
    assert report["execution"]["final_answer"] == "是"
    assert report["execution"]["threshold"] is None
    assert report["declared_tools"] == ["paddleOcrTool", "MLLM"]
    assert "evidence" not in report
    assert "installed" not in report
    after = {}
    for path in BANNER_SKILL.rglob("*"):
        if path.is_file():
            after[str(path.relative_to(BANNER_SKILL))] = path.read_bytes()
    assert after == before

    crop_report = validate_human_skill(
        BANNER_SKILL,
        BANNER_CROP_SCRIPT,
    )
    assert crop_report["valid"]
    assert crop_report["checks"]["mock_execution"]


def test_human_skill_deployment_and_quality_prior():
    with tempfile.TemporaryDirectory() as root:
        skill_root = Path(root) / "skills"
        skill_dir = skill_root / "banner"
        shutil.copytree(BANNER_SKILL, skill_dir)
        script_path = skill_dir / "scripts/banner-crop-example.py"

        deployment = deploy_human_skill(skill_dir, script_path)
        assert deployment["deployed"]
        assert deployment["status"] == "active"
        assert deployment["mutation_mode"] == "manual"
        workflow_path = (
            skill_dir
            / "references/workflows/banner-crop-example.json"
        )
        workflow = WorkflowSpec.from_dict(
            json.loads(workflow_path.read_text(encoding="utf-8"))
        )
        assert workflow.status == "active"
        assert workflow.mutation_mode == "manual"
        metadata = json.loads(
            (skill_dir / "references/skill.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(
            item for item in metadata["workflows"]
            if item["workflow_id"] == "banner-crop-example"
        )
        assert entry["authorship"] == "human"
        assert "banner-crop-example" in (
            skill_dir / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert (skill_root / "SKILLS.json").is_file()

        repeated = deploy_human_skill(skill_dir, script_path)
        assert repeated["deployed"]
        assert repeated["preserved_metrics"]

    generated = WorkflowSpec(
        workflow_id="generated_observed",
        name="generated_observed",
        applicability=ApplicabilitySpec(
            problem_class="banner",
            required_tools=["MLLM"],
        ),
        steps=[WorkflowStep(
            tool_name="MLLM",
            args={"file": "$image", "query": "$question"},
        )],
    )
    generated.metrics.trial_count = 10
    generated.metrics.correct_count = 7
    generated.metrics.evidence_accept_count = 7
    manual = WorkflowSpec(
        workflow_id="manual_unobserved",
        name="manual_unobserved",
        applicability=ApplicabilitySpec(
            problem_class="banner",
            required_tools=["MLLM"],
        ),
        steps=[WorkflowStep(
            tool_name="MLLM",
            args={"file": "$image", "query": "$question"},
        )],
        mutation_mode="manual",
    )
    retriever = build_retriever(
        SkillSelectionRepository([generated, manual], ""),
        SkillSelectionLLM(""),
        top_k=1,
    )
    ranked, unused_decision = retriever.retrieve(
        "banner",
        "question",
        [str(BANNER_IMAGE)],
        {"event_type": "banner", "media_type": "image"},
        ["MLLM"],
        "image",
    )
    assert [item.workflow_id for item in ranked] == ["manual_unobserved"]

    manual.metrics.trial_count = 1
    ranked, unused_decision = retriever.retrieve(
        "banner",
        "question",
        [str(BANNER_IMAGE)],
        {"event_type": "banner", "media_type": "image"},
        ["MLLM"],
        "image",
    )
    assert [item.workflow_id for item in ranked] == ["generated_observed"]


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


def test_param_space_prioritizes_workflow_diversity():
    parent = build_anomaly_baseline_workflow("banner")
    ocr_atom = ParamAtom(
        "paddleOcrTool",
        "evidence_role",
        "text_reading",
        "fixed",
    )
    yolo_atom = ParamAtom(
        "yoloTool",
        "threshold",
        "low",
        "numerical",
    )
    ocr_step = WorkflowStep(
        tool_name="paddleOcrTool",
        step_id="ocr",
        param_atoms=[ocr_atom],
    )
    yolo_step = WorkflowStep(
        tool_name="yoloTool",
        step_id="yolo",
        param_atoms=[yolo_atom],
    )
    active_ocr = WorkflowSpec(
        workflow_id="active_ocr",
        name="active_ocr",
        applicability=parent.applicability,
        steps=[parent.steps[0], ocr_step],
    )
    candidate_ocr = WorkflowSpec(
        workflow_id="candidate_ocr",
        name="candidate_ocr",
        applicability=parent.applicability,
        steps=[parent.steps[0], ocr_step],
    )
    candidate_yolo = WorkflowSpec(
        workflow_id="candidate_yolo",
        name="candidate_yolo",
        applicability=parent.applicability,
        steps=[parent.steps[0], yolo_step],
    )
    ocr_mutation = MutationSpec(
        mutation_id="mutation_ocr",
        kind="fixed",
        atom=ocr_atom,
        operation="insert_tool",
        description="加入 OCR。",
    )
    yolo_mutation = MutationSpec(
        mutation_id="mutation_yolo",
        kind="numerical",
        atom=yolo_atom,
        operation="set_parameter",
        description="加入 YOLO。",
    )
    candidates = [
        (ocr_mutation, candidate_ocr),
        (yolo_mutation, candidate_yolo),
    ]

    selected = ParamSpace().select_workflow_mutations(
        candidates,
        parent,
        [active_ocr],
        {},
        count=1,
        allow_zero_gain=False,
    )

    assert len(selected) == 1
    assert selected[0][0].mutation_id == "mutation_yolo"
    score = selected[0][0].score_parts["workflow"]
    assert score["coverage_gain"] > 0
    assert score["feature_count"] == 3.0


def test_top_k_retriever_reads_skill_markdown():
    first = WorkflowSpec(
        workflow_id="history_first",
        name="history_first",
        applicability=ApplicabilitySpec(
            problem_class="banner",
            required_tools=["MLLM"],
        ),
        steps=[WorkflowStep(
            tool_name="MLLM",
            args={"file": "$image", "query": "判断横幅异常。"},
        )],
    )
    first.metrics.trial_count = 10
    first.metrics.correct_count = 10
    second = WorkflowSpec(
        workflow_id="skill_selected",
        name="skill_selected",
        applicability=ApplicabilitySpec(
            problem_class="banner",
            required_tools=["MLLM"],
        ),
        steps=[WorkflowStep(
            tool_name="MLLM",
            args={"file": "$image", "query": "检查横幅是否违规。"},
        )],
    )
    repository = SkillSelectionRepository(
        [first, second],
        "SKILL_GUIDANCE_SENTINEL：当前画面应选择 skill_selected。",
    )
    llm = SkillSelectionLLM("skill_selected")
    retriever = build_retriever(repository, llm, top_k=1)

    ranked, decision = retriever.retrieve(
        "banner",
        "检测当前画面是否存在横幅异常。",
        [str(BANNER_IMAGE)],
        {"event_type": "banner", "media_type": "image"},
        ["MLLM"],
        "image",
    )

    assert [workflow.workflow_id for workflow in ranked] == [
        "skill_selected"
    ]
    assert decision.strategy == "skill_guided_multimodal"
    prompt = llm.messages[0].content[0]["text"]
    assert "同类别 SKILL.md" in prompt
    assert "SKILL_GUIDANCE_SENTINEL" in prompt
    assert "history_first" in prompt
    assert "skill_selected" in prompt


def test_repository_updates_workflow_manual_section():
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config()
    with tempfile.TemporaryDirectory() as root:
        paths = ExperimentPaths(
            "skill_manual_test",
            root,
            problem_classes=["banner"],
            class_metadata=metadata,
        )
        paths.ensure(config, "explore")
        repository = WorkflowRepository(paths)
        workflow = build_anomaly_baseline_workflow("banner")
        workflow.status = "active"
        repository.save(workflow)
        workflow = repository.update_metrics(
            workflow,
            "video_metric_test",
            True,
            True,
            1,
            0,
            10.0,
        )
        assert workflow.metrics.trial_count == 1

        skill_path = paths.active_skill_root / "banner/SKILL.md"
        first_text = skill_path.read_text(encoding="utf-8")
        assert "## Skill 作用" in first_text
        assert "## 工作流选择" in first_text
        assert "## 可选工作流" in first_text
        assert workflow.workflow_id in first_text
        assert "工具链：`embeddingTool`" in first_text
        assert "## 事件接口" not in first_text
        assert "## 工具调用模板" not in first_text
        assert "## 证据要求" not in first_text
        assert "历史表现：" not in first_text
        assert "必需运行时槽位：" not in first_text
        assert first_text.count(
            "SPATIALSKILLGROWTH_WORKFLOWS_START"
        ) == 1

        workflow.applicability.description = "只在目标外观清晰时选择。"
        repository.save(workflow)
        second_text = skill_path.read_text(encoding="utf-8")
        assert "选择条件：只在目标外观清晰时选择。" in second_text
        assert second_text.count(
            "SPATIALSKILLGROWTH_WORKFLOWS_START"
        ) == 1


def test_single_success_promotes_provisional_workflow():
    metadata = class_metadata_for_anomaly()
    config = build_experiment_config()
    assert config.provisional_promotion_trials == 1
    assert config.promotion_accuracy == 0.5
    with tempfile.TemporaryDirectory() as root:
        paths = ExperimentPaths(
            "single_promotion_test",
            root,
            problem_classes=["banner"],
            class_metadata=metadata,
        )
        paths.ensure(config, "explore")
        repository = WorkflowRepository(paths)
        store = ExperimentStore(paths)
        workflow = WorkflowSpec(
            workflow_id="banner_single_success",
            name="banner_single_success",
            applicability=ApplicabilitySpec(
                problem_class="banner",
                required_tools=["MLLM"],
            ),
            steps=[WorkflowStep(
                tool_name="MLLM",
                args={"file": "$image", "query": "判断横幅异常。"},
            )],
            status="provisional",
        )
        workflow.metrics.trial_count = 1
        workflow.metrics.correct_count = 1
        workflow.metrics.evidence_accept_count = 1
        repository.save(workflow)
        lifecycle = WorkflowLifecycleManager(config, repository, store)

        review = lifecycle.review(workflow, "image_positive_00")

        assert review["from"] == "provisional"
        assert review["to"] == "active"
        assert repository.get(workflow.workflow_id).status == "active"


def test_video_inference_parallel_or_without_llm():
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
        for path in (
            paths.active_skill_root
            / "banner/references/workflows"
        ).glob("*.json"):
            path.unlink()
        frame_workflow = WorkflowSpec(
            workflow_id="banner_image_frame_skill",
            name="banner_image_frame_skill",
            applicability=ApplicabilitySpec(
                problem_class="banner",
                required_tools=["MLLM"],
            ),
            steps=[WorkflowStep(
                tool_name="MLLM",
                args={"file": "$image", "query": "判断横幅异常。"},
            )],
            status="active",
        )
        repository = WorkflowRepository(paths)
        repository.save(frame_workflow)
        ocr_workflow = WorkflowSpec(
            workflow_id="banner_ocr_frame_skill",
            name="banner_ocr_frame_skill",
            applicability=ApplicabilitySpec(
                problem_class="banner",
                required_tools=["paddleOcrTool"],
            ),
            steps=[WorkflowStep(
                tool_name="paddleOcrTool",
                args={"file": "$image", "filename": "$filename"},
            )],
            status="active",
        )
        repository.save(ocr_workflow)
        runtime = ToolRuntime({
            "embeddingTool": MockNegativeEmbeddingTool(),
            "MLLM": MockAnswerTool("MLLM", "是"),
            "paddleOcrTool": MockAnswerTool("paddleOcrTool", "否"),
        })
        pipeline = ExperimentFactory(
            config,
            paths,
            DisabledLLM(),
            runtime=runtime,
        ).build_inference()
        task = build_anomaly_task(str(BANNER_VIDEO), "banner", groundtruth="是")
        result = pipeline.ask(task, "online")
        assert result["answer"] == "是"
        assert result["is_anomaly"] is True
        assert result["threshold"] == 0.31
        assert result["correct"] is True
        assert result["aggregation_strategy"] == "parallel_or"
        assert result["retrieval"]["strategy"] == "all_structurally_eligible"
        assert len(result["attempts"]) == 3
        assert result["attempts"][0]["kind"] == "embedding_baseline"
        assert result["attempts"][0]["answer"] == "否"
        assert {
            item["workflow_id"]
            for item in result["attempts"][1:]
        } == {
            frame_workflow.workflow_id,
            ocr_workflow.workflow_id,
        }
        assert result["selected_workflow_id"] == frame_workflow.workflow_id


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
        workflow_paths = list(
            (run_root / "skills/active/banner/references/workflows").glob(
                "*.json"
            )
        )
        workflows = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in workflow_paths
            if not path.name.endswith(".archive.json")
        ]
        assert workflows
        assert any(
            item["metrics"]["correct_count"] >= 2
            for item in workflows
        )
        assert all(
            "validated_media_types"
            not in item.get("applicability", {})
            for item in workflows
        )
        assert all(
            "media_type_metrics" not in item.get("metrics", {})
            for item in workflows
        )


def main():
    tests = [
        test_event_taxonomy_and_bool_evaluator,
        test_input_is_one_media_and_one_event_type,
        test_media_preprocessor_keeps_video_and_samples_frames,
        test_planner_has_no_llm_classification_or_omni_slots,
        test_image_skill_is_eligible_for_video_frame_inference,
        test_run_workspace_uses_editable_skills_only,
        test_skill_markdowns_are_compact,
        test_embedding_parallel_channel_is_not_retrievable_skill,
        test_evidence_validator_rejects_missing_threshold,
        test_human_banner_skill_executes,
        test_human_skill_deployment_and_quality_prior,
        test_param_space_has_no_omni_slots,
        test_param_space_prioritizes_workflow_diversity,
        test_top_k_retriever_reads_skill_markdown,
        test_repository_updates_workflow_manual_section,
        test_single_success_promotes_provisional_workflow,
        test_video_inference_parallel_or_without_llm,
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
