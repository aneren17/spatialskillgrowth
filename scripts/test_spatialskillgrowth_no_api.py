"""SpatialSkillGrowth 无网络回归测试。

Run:
    python -m scripts.test_spatialskillgrowth_no_api
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from langchain_core.messages import AIMessage

from agents.spatialskillgrowth.online_data import (
    build_anomaly_task,
    infer_online_benchmark,
    load_online_tasks,
    parse_online_item,
)
from agents.spatialskillgrowth.spatialskillgrowth_infer_omni3d_agent import (
    _resolve_problem_classes as resolve_inference_problem_classes,
    _source_repository,
)
from agents.spatialskillgrowth.spatialskillgrowth_explore_omni3d_agent import (
    _resolve_problem_classes as resolve_exploration_problem_classes,
)
from config.spatialskillgrowth_config import SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE
from scripts.build_multibench_zeroshot_subset import (
    build_subset as build_multibench_subset,
)
from nodes.mem.spatialskillgrowth.benchmark_profiles import (
    ANOMALY_BENCHMARK,
    ANOMALY_EVENT_TYPES,
    LEGACY_PROBLEM_CLASSES,
    OMNI3D_PROBLEM_CLASSES,
)
from nodes.mem.spatialskillgrowth.answer_evaluator import answer_matches_typed
from nodes.mem.spatialskillgrowth.experiment_config import (
    DEFAULT_SKILL_WHITEBOARD_ROOT,
    ExperimentPaths,
    build_experiment_config,
)
from nodes.mem.spatialskillgrowth.models import (
    MutationMode,
    ParamAtom,
    TaskRecord,
    WorkflowStatus,
    WorkflowStep,
)
from nodes.mem.spatialskillgrowth.media_processing import MediaPreprocessor
from nodes.mem.spatialskillgrowth.param_space import ParamSpace
from nodes.mem.spatialskillgrowth.skill_consolidator import (
    ApplicabilityCompatibilityJudge,
    ParetoWorkflowPruner,
    StructuralCompatibilityChecker,
    WorkflowConsolidator,
)
from nodes.mem.spatialskillgrowth.evidence_validator import (
    HybridEvidenceValidator,
    NoEvidenceValidator,
    StructuralEvidenceValidator,
    build_evidence_validator,
)
from nodes.mem.spatialskillgrowth.workflow_executor import (
    CandidateExecutionCoordinator,
    FinalAnswerNormalizer,
    ReactSolver,
    WorkflowExecutor,
    WorkflowPythonExporter,
)
from nodes.mem.spatialskillgrowth.models import (
    ApplicabilitySpec,
    WorkflowMetrics,
    WorkflowSpec,
)
from nodes.mem.spatialskillgrowth.pipeline import ExperimentFactory
from nodes.mem.spatialskillgrowth.mutation import (
    FailureRepairDirector,
    MutationCandidateSelector,
    SuccessEnhancementDirector,
)
from nodes.mem.spatialskillgrowth.skill_retriever import (
    HistoryOnlyRetriever,
    MultimodalLLMFlatRetriever,
)
from nodes.mem.spatialskillgrowth.growth_store import ExperimentStore, WorkflowRepository
from nodes.mem.spatialskillgrowth.omni3d_eval_adapter import (
    evaluate_run,
    export_inference_predictions,
)
from nodes.mem.spatialskillgrowth.workflow_lifecycle import WorkflowLifecycleManager
from nodes.mem.spatialskillgrowth.tool_contracts import (
    PIXEL_DETECTION_TOOLS,
    compatible_producers,
    contract_signature,
    output_types,
)
from nodes.mem.spatialskillgrowth.tool_runtime import ToolRuntime
from nodes.mem.spatialskillgrowth.workflow_mutator import WorkflowMutator
from nodes.mem.spatialskillgrowth.task_router import (
    BenchmarkProblemClassifier,
    ToolAvailabilityPolicy,
)
from tools.basicTools.pythonSandboxTool import SAFE_MODULES
from tools.basicTools.embeddingTool import (
    DASHBOARD_EVENT_LABELS,
    EVENT_TYPE_ALIASES,
    RAG_EVENT_LABELS,
    STREAM_EVENT_LABELS,
    VALID_EVENT_TYPES,
    embeddingTool,
)


class FakeResponse:
    def __init__(self, content):
        self.content = content


class QueueLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.messages = []

    def invoke(self, messages):
        self.messages.append(messages)
        if not self.responses:
            raise AssertionError("Unexpected LLM call")
        response = self.responses.pop(0)
        if callable(response):
            response = response(messages)
        return FakeResponse(json.dumps(response))


class FakeTool:
    def __init__(self, name, output):
        self.name = name
        self.output = output

    def invoke(self, args):
        return self.output(args) if callable(self.output) else self.output


def workflow(
    workflow_id="wf",
    problem_class="object_counting",
    tools=("groundingdino", "MLLM"),
    answer_type="int",
    accuracy=(1, 1),
):
    steps = []
    for index, tool_name in enumerate(tools):
        if tool_name == "MLLM":
            args = {"query": "$question"}
        elif tool_name == "embeddingTool":
            args = {"file_path": "$media", "event_type": "$slot.event_type"}
        else:
            args = {
                "file": "$image",
                "filename": "$filename",
                "query": "$slot.target_a",
            }
        steps.append(WorkflowStep(
            tool_name=tool_name,
            args=args,
            step_id=f"step_{index}",
            depends_on=[f"step_{index - 1}"] if index else [],
        ))
    return WorkflowSpec(
        workflow_id=workflow_id,
        name=workflow_id,
        applicability=ApplicabilitySpec(
            problem_class=problem_class,
            required_slots=(
                ["event_type"] if "embeddingTool" in tools else ["target_a"]
            ),
            required_tools=list(tools),
            answer_types=[answer_type],
            description=f"Applicability for {workflow_id}",
            exclusions="Do not use outside its evidence boundary.",
            capability_boundary="Requires grounded target evidence.",
        ),
        steps=steps,
        metrics=WorkflowMetrics(
            trial_count=accuracy[1],
            correct_count=accuracy[0],
            evidence_accept_count=accuracy[0],
            total_tool_calls=2 * accuracy[1],
            structural_coverage=float(len(set(tools))),
        ),
    )


def temporary_run(root, experiment="full", run_id="test"):
    config = build_experiment_config(experiment)
    paths = ExperimentPaths(experiment, run_id, root)
    paths.ensure(config, "explore", False)
    return config, paths


def test_taxonomy_and_split():
    assert len(ANOMALY_EVENT_TYPES) == 55
    assert len(OMNI3D_PROBLEM_CLASSES) == 16
    dataset_path = Path("benchmark/Omni-3d/annotations.json")
    explore_path = Path("benchmark/Omni-3d/annotations_explore256.json")
    if not dataset_path.exists() or not explore_path.exists():
        return
    dataset = json.loads(dataset_path.read_text())
    explore = json.loads(explore_path.read_text())
    assert len(dataset["questions"]) == 501
    assert len(explore["questions"]) == 256
    assert set(explore["metadata"]["problem_classes"]) == set(OMNI3D_PROBLEM_CLASSES)
    explore_ids = {
        (str(item["image_index"]), str(item["question_index"]))
        for item in explore["questions"]
    }
    all_ids = {
        (str(item["image_index"]), str(item["question_index"]))
        for item in dataset["questions"]
    }
    assert len(explore_ids) == 256
    assert len(all_ids - explore_ids) == 245


def test_anomaly_taxonomy_and_embedding_workflow():
    assert len(ANOMALY_EVENT_TYPES) == 55
    assert len(DASHBOARD_EVENT_LABELS) == 38
    assert len(RAG_EVENT_LABELS) == 52
    assert len(STREAM_EVENT_LABELS) == 9
    assert set(ANOMALY_EVENT_TYPES) == set(VALID_EVENT_TYPES)
    assert EVENT_TYPE_ALIASES["tube_falls_and_breaks"] == [
        "试管掉落破碎",
        "管道坠落破裂",
    ]
    assert EVENT_TYPE_ALIASES["fire_door_unclosed"] == ["消防门未关闭"]
    assert "charger：充电器未归位" in embeddingTool.description
    assert (
        "tube_falls_and_breaks：试管掉落破碎；管道坠落破裂"
        in embeddingTool.description
    )
    spec = WorkflowMutator().extract(
        "fall",
        "视频中是否发生人员跌倒事件？",
        [],
        "anomaly_task",
        slot_bindings={"event_type": "fall"},
    )
    assert [step.tool_name for step in spec.steps] == ["embeddingTool"]
    assert spec.steps[0].args == {
        "file_path": "$media",
        "event_type": "$slot.event_type",
    }
    assert spec.applicability.required_slots == ["event_type"]

    def detect(args):
        assert args == {"file_path": "/tmp/demo.mp4", "event_type": "fall"}
        return "是 (判定阈值: 0.73)"

    with tempfile.TemporaryDirectory() as root:
        result = WorkflowExecutor(
            ToolRuntime({"embeddingTool": FakeTool("embeddingTool", detect)}),
            candidate_script_root=Path(root),
        ).execute(
            spec,
            "视频中是否发生人员跌倒事件？",
            ["/tmp/demo.mp4"],
            {"event_type": "fall"},
        )
    assert result["final_answer"] == "是"
    assert result["event_type"] == "fall"
    assert result["is_anomaly"] is True
    assert result["threshold"] == 0.73
    assert contract_signature("embeddingTool")["output_fields"] == {
        "event_type": "string",
        "is_anomaly": "boolean",
        "threshold": "number",
    }
    assert answer_matches_typed("是", "yes", "bool")

    video_task = build_anomaly_task("test/banner.mp4", "违规横幅检测")
    assert video_task.capability == "banner"
    assert video_task.media_type == "video"
    assert video_task.answer_type == "bool"
    assert "精确 event_type 为 `banner`" in video_task.question
    assert "判定阈值" in video_task.question
    assert not video_task.groundtruth

    image_task = parse_online_item(
        {"file_path": "banner.jpg", "event_type": "banner"},
        "test",
        require_groundtruth=False,
    )
    assert image_task.media_type == "image"
    assert image_task.capability == "banner"
    assert image_task.task_id.startswith("banner__banner__")

    runtime = ToolRuntime({
        "embeddingTool": FakeTool(
            "embeddingTool", "否 (判定阈值: 0.61)"
        )
    })
    with tempfile.TemporaryDirectory() as root:
        coordinator = CandidateExecutionCoordinator(
            WorkflowExecutor(runtime, candidate_script_root=Path(root)),
            ReactSolver(None, runtime, max_steps=1),
            build_evidence_validator("none", None),
            use_react=False,
        )
        execution = coordinator.run(
            "banner_direct",
            "banner",
            image_task.question,
            image_task.image_paths,
            "bool",
            [],
            {"event_type": "banner"},
            ["embeddingTool"],
        )
    assert execution["accepted"]
    assert execution["attempts"][0]["kind"] == "embedding_baseline"
    assert execution["answer"] == "否"
    assert execution["is_anomaly"] is False
    assert execution["threshold"] == 0.61

    with tempfile.TemporaryDirectory() as root:
        config = build_experiment_config("retrieval_only")
        paths = ExperimentPaths(
            config.name,
            "direct_anomaly",
            root,
            benchmark="anomaly_detection",
            problem_classes=list(ANOMALY_EVENT_TYPES),
        )
        paths.ensure(config, "infer", False)
        pipeline = ExperimentFactory(
            config,
            paths,
            QueueLLM([]),
            runtime=runtime,
            benchmark="anomaly_detection",
            problem_classes=list(ANOMALY_EVENT_TYPES),
        ).build_inference()
        summary = pipeline.ask(image_task, "online")
    assert summary["answer"] == "否"
    assert summary["event_type"] == "banner"
    assert summary["event_name"] == "违规横幅检测"
    assert summary["media_type"] == "image"
    assert summary["is_anomaly"] is False
    assert summary["threshold"] == 0.61
    assert summary["correct"] is None


def test_video_sampling_and_dual_media_routing():
    video_task = build_anomaly_task("test/banner.mp4", "banner")
    with tempfile.TemporaryDirectory() as root:
        prepared = MediaPreprocessor(Path(root)).prepare(video_task)
        assert prepared.media_path.endswith("banner.mp4")
        assert prepared.sampled_frame_paths
        assert all(path.endswith(".jpg") for path in prepared.sampled_frame_paths)
        assert prepared.media_metadata["sample_fps"] == 1.0
        assert prepared.media_metadata["sampled_frame_count"] == len(
            prepared.sampled_frame_paths
        )
        assert len(prepared.sampled_frame_paths) <= 12
        cached = MediaPreprocessor(Path(root)).prepare(video_task)
        assert cached.sampled_frame_paths == prepared.sampled_frame_paths

        embedding_calls = []
        image_calls = []

        def detect(args):
            embedding_calls.append(dict(args))
            return "是 (判定阈值: 0.65)"

        def detect_frame(args):
            image_calls.append(dict(args))
            frame_index = int(Path(args["file"]).stem.split("_")[1])
            return json.dumps({
                "status": "success",
                "detections": [{
                    "class_name": "person",
                    "bbox": [0, 0, 10, 10],
                    "score": frame_index / 100.0,
                }],
            })

        dual_workflow = WorkflowSpec(
            workflow_id="dual_media",
            name="dual_media",
            applicability=ApplicabilitySpec(
                problem_class="banner",
                required_slots=["event_type"],
                required_tools=["embeddingTool", "yoloTool"],
                answer_types=["bool"],
            ),
            steps=[
                WorkflowStep(
                    tool_name="embeddingTool",
                    args={
                        "file_path": "$media",
                        "event_type": "$slot.event_type",
                    },
                    step_id="embedding",
                ),
                WorkflowStep(
                    tool_name="yoloTool",
                    args={
                        "file": "$image",
                        "filename": "$filename",
                        "threshold": 0.5,
                    },
                    step_id="frames",
                ),
            ],
        )
        result = WorkflowExecutor(
            ToolRuntime({
                "embeddingTool": FakeTool("embeddingTool", detect),
                "yoloTool": FakeTool("yoloTool", detect_frame),
            }),
            candidate_script_root=Path(root) / "scripts",
        ).execute(
            dual_workflow,
            prepared.question,
            prepared.visual_paths,
            {"event_type": "banner"},
            media_path=prepared.media_path,
        )
        assert result["success"]
        assert embedding_calls == [{
            "file_path": prepared.media_path,
            "event_type": "banner",
        }]
        assert len(image_calls) == len(prepared.sampled_frame_paths)
        assert all(call["file"].endswith(".jpg") for call in image_calls)
        frame_data = result["observations"][1]["result"]["data"]
        assert frame_data["successful_frame_count"] == len(image_calls)
        assert frame_data["source_frame"].endswith(
            prepared.sampled_frame_paths[-1]
        )

def test_removed_tools_are_not_in_active_runtime():
    removed_tools = {
        "asrTool",
        "webSearchTool",
        "webVisitTool",
        "inspect_file_as_text",
    }
    registry = ToolRuntime().registry
    assert removed_tools.isdisjoint(registry)
    plan = ToolAvailabilityPolicy().select(registry)
    assert removed_tools.isdisjoint(plan["selected_tools"])
    assert removed_tools.isdisjoint(plan["excluded_tools"])
    assert {item["scope"] for item in plan["tool_decisions"]}.issubset({
        "general",
        "closed_set_detector",
    })
    assert {"requests", "bs4", "pydub", "PyPDF2", "pptx"}.isdisjoint(
        SAFE_MODULES
    )


def test_llm_temperature_is_fixed():
    assert SPATIAL_SKILL_GROWTH_LLM_TEMPERATURE == 0.7


def test_manifest_isolation():
    with tempfile.TemporaryDirectory() as root:
        config, paths = temporary_run(root)
        paths.ensure(config, "infer", False)
        mismatched = build_experiment_config("full", seed=7)
        try:
            paths.ensure(mismatched, "infer", True)
        except RuntimeError as exc:
            assert "config mismatch" in str(exc).lower()
        else:
            raise AssertionError("Config mixing must be rejected")


def test_benchmark_aware_problem_classes_and_skills():
    for resolver in (
        resolve_exploration_problem_classes,
        resolve_inference_problem_classes,
    ):
        assert set(resolver("omni3d", "", ["object_counting"])) == set(
            OMNI3D_PROBLEM_CLASSES
        )
        assert resolver("custom3d", "", ["custom_geometry"]) == [
            "custom_geometry"
        ]
    dataset_path = Path(
        "benchmark/STVQA-7K/spatial_debug_10/toolbatch_spatial_debug_10.json"
    )
    if dataset_path.exists():
        tasks = load_online_tasks(
            str(dataset_path),
            "benchmark/STVQA-7K/images",
        )
        assert infer_online_benchmark(str(dataset_path)) == "stvqa"
        assert {task.capability for task in tasks} == set(LEGACY_PROBLEM_CLASSES)
        assert all(task.image_paths for task in tasks)

    classifier = BenchmarkProblemClassifier(None, "stvqa")
    fixed = classifier.classify("unused", [], "distance_depth")
    assert fixed["problem_class"] == "distance_depth"
    dynamic = BenchmarkProblemClassifier(
        None,
        "custom3d",
        problem_classes=["custom_geometry"],
    )
    assert dynamic.classify("unused", [], "new_relation")["problem_class"] == (
        "new_relation"
    )

    with tempfile.TemporaryDirectory() as root:
        config = build_experiment_config("full")
        paths = ExperimentPaths(
            "full",
            "stvqa_test",
            root,
            benchmark="stvqa",
            problem_classes=list(LEGACY_PROBLEM_CLASSES),
        )
        paths.ensure(config, "explore", False)
        manifest = json.loads((paths.root / "manifest.json").read_text())
        assert manifest["benchmark"] == "stvqa"
        assert set(manifest["problem_classes"]) == set(LEGACY_PROBLEM_CLASSES)
        assert {
            path.name for path in paths.active_skill_root.iterdir() if path.is_dir()
        } == set(LEGACY_PROBLEM_CLASSES)
        assert not set(OMNI3D_PROBLEM_CLASSES).difference(
            LEGACY_PROBLEM_CLASSES
        ).intersection(path.name for path in paths.active_skill_root.iterdir())


def test_cross_benchmark_source_uses_source_taxonomy():
    with tempfile.TemporaryDirectory() as root:
        config = build_experiment_config("full")
        source_result_root = str(Path(root) / "source_results")
        source_paths = ExperimentPaths(
            "full",
            "omni_source",
            source_result_root,
            benchmark="omni3d",
            problem_classes=list(OMNI3D_PROBLEM_CLASSES),
        )
        source_paths.ensure(config, "explore", False)

        target_result_root = str(Path(root) / "target_results")
        target_paths = ExperimentPaths(
            "full",
            "stvqa_target",
            target_result_root,
            benchmark="stvqa",
            problem_classes=list(LEGACY_PROBLEM_CLASSES),
        )
        target_paths.ensure(config, "infer", False)
        args = SimpleNamespace(
            source_run_id="omni_source",
            source_experiment="full",
            source_benchmark="omni3d",
            source_result_root=source_result_root,
            result_root="",
        )
        repository, benchmark, problem_classes, metadata = _source_repository(
            args,
            target_paths,
            "stvqa",
            list(LEGACY_PROBLEM_CLASSES),
            {},
            target_result_root,
        )
        assert repository.paths.root == source_paths.root
        assert benchmark == "omni3d"
        assert tuple(problem_classes) == OMNI3D_PROBLEM_CLASSES
        assert set(metadata) == set(OMNI3D_PROBLEM_CLASSES)


def test_skill_whiteboard_initializes_without_overwriting():
    with tempfile.TemporaryDirectory() as root:
        config, paths = temporary_run(root)
        copied_whiteboard = paths.skill_root / "WHITEBOARD.json"
        assert copied_whiteboard.read_bytes() == (
            DEFAULT_SKILL_WHITEBOARD_ROOT / "WHITEBOARD.json"
        ).read_bytes()
        assert {
            path.name for path in paths.active_skill_root.iterdir() if path.is_dir()
        } == set(ANOMALY_EVENT_TYPES)
        assert {
            path.name for path in paths.archive_skill_root.iterdir() if path.is_dir()
        } == set(ANOMALY_EVENT_TYPES)
        assert {
            path.name for path in paths.provisional_skill_root.iterdir() if path.is_dir()
        } == set(ANOMALY_EVENT_TYPES)
        for problem_class in ANOMALY_EVENT_TYPES:
            for root_path in (
                paths.active_skill_root,
                paths.provisional_skill_root,
                paths.archive_skill_root,
            ):
                skill_path = root_path / problem_class
                assert (skill_path / "SKILL.md").is_file()
                assert (skill_path / "skill.json").is_file()
                assert (skill_path / "scripts").is_dir()
                assert (skill_path / "workflows").is_dir()
                skill_metadata = json.loads(
                    (skill_path / "skill.json").read_text()
                )
                assert skill_metadata["event_type"] == problem_class
                assert skill_metadata["primary_tool"] == "embeddingTool"
                assert skill_metadata["answer_type"] == "bool"
                assert skill_metadata["tool_template"]["args"]["event_type"] == (
                    problem_class
                )
                assert skill_metadata["display_names"]
                assert skill_metadata["aliases"]

        repository = WorkflowRepository(paths)
        repository.save(workflow(
            "whiteboard_generated",
            problem_class="fall",
            tools=("embeddingTool",),
            answer_type="bool",
        ))
        generated_path = (
            paths.active_skill_root
            / "fall"
            / "workflows"
            / "whiteboard_generated.json"
        )
        assert generated_path.is_file()
        assert (
            paths.active_skill_root
            / "fall"
            / "scripts"
            / "whiteboard_generated.py"
        ).is_file()
        skill_path = paths.active_skill_root / "fall"
        assert "whiteboard_generated" in (skill_path / "SKILL.md").read_text()
        skill_metadata = json.loads((skill_path / "skill.json").read_text())
        assert skill_metadata["workflow_count"] == 1
        assert skill_metadata["event_type"] == "fall"
        assert skill_metadata["display_names"]["dashboard"] == "人员摔倒"
        assert skill_metadata["tool_template"]["args"]["event_type"] == "fall"
        assert skill_metadata["workflows"][0]["path"] == (
            "workflows/whiteboard_generated.json"
        )
        active_index = json.loads(
            (paths.active_skill_root / "SKILLS.json").read_text()
        )
        indexed_skill = next(
            item for item in active_index["skills"]
            if item["problem_class"] == "fall"
        )
        assert indexed_skill["workflow_count"] == 1
        paths.ensure(config, "infer", False)
        assert generated_path.is_file()
        repository.archive(repository.get("whiteboard_generated"), "test_archive")
        archived_path = (
            paths.archive_skill_root
            / "fall"
            / "workflows"
            / "whiteboard_generated.json"
        )
        assert archived_path.is_file() and not generated_path.exists()
        assert (paths.archive_skill_root / "fall" / "SKILL.md").is_file()
        archived_skill_metadata = json.loads(
            (paths.archive_skill_root / "fall" / "skill.json").read_text()
        )
        assert archived_skill_metadata["event_type"] == "fall"
        assert archived_skill_metadata["display_names"]["rag"] == "跌倒"
        assert not list(DEFAULT_SKILL_WHITEBOARD_ROOT.rglob("whiteboard_generated.json"))


def test_retrievers_are_multimodal_and_support_reject():
    with tempfile.TemporaryDirectory() as root:
        _, paths = temporary_run(root)
        repository = WorkflowRepository(paths)
        for index in range(4):
            repository.save(workflow(f"wf_{index}", accuracy=(index + 1, index + 2)))
        image_path = Path(root) / "image.jpg"
        Image.new("RGB", (8, 8), "white").save(image_path)
        llm = QueueLLM([{
            "action": "select",
            "ranked_workflow_ids": ["wf_3", "wf_1", "wf_0", "wf_2"],
            "reason": "The first three match the evidence needs.",
        }])
        retriever = MultimodalLLMFlatRetriever(repository, llm, top_k=3)
        ranked, decision = retriever.retrieve(
            "object_counting",
            "Count the cups.",
            [str(image_path)],
            {"target_a": "cups"},
            {"groundingdino", "MLLM"},
            "int",
        )
        assert [item.workflow_id for item in ranked] == ["wf_3", "wf_1", "wf_0"]
        assert len(llm.messages[0][0].content) == 2
        assert not decision.rejected
        reject_llm = QueueLLM([{
            "action": "reject_all",
            "ranked_workflow_ids": [],
            "reason": "No candidate applies.",
        }])
        rejected, decision = MultimodalLLMFlatRetriever(
            repository, reject_llm, top_k=3
        ).retrieve(
            "object_counting", "Count", [], {"target_a": "cup"},
            {"groundingdino", "MLLM"}, "int"
        )
        assert not rejected and decision.rejected
        history, _ = HistoryOnlyRetriever(repository, 3).retrieve(
            "object_counting", "ignored", [], {"target_a": "cup"},
            {"groundingdino", "MLLM"}, "int"
        )
        assert len(history) == 3


def test_mutation_director_groundtruth_boundary_and_budget():
    atoms = [
        ParamAtom("MLLM", "scope", "whole_image", "world_model"),
        ParamAtom("groundingdino", "threshold", "low", "numerical"),
    ]

    def success_response(messages):
        text = messages[0].content[0]["text"]
        assert "secret-answer-91" not in text
        return {
            "objective": "add complementary localization",
            "preferred_atom_ids": [atoms[1].atom_id],
            "avoid_atom_ids": [],
            "tool_hints": {"groundingdino": "cups"},
            "diagnosis": "The route can gain grounded evidence.",
        }

    successful = SuccessEnhancementDirector(QueueLLM([success_response])).direct(
        problem_class="object_counting",
        question="Count cups",
        slot_bindings={"target_a": "cups"},
        workflow=workflow(),
        observations=[],
        atoms=atoms,
        allowed_tool_names=["MLLM", "groundingdino"],
    )
    assert successful.mode == "success_enhancement"
    failure_llm = QueueLLM([
        {
            "objective": "copy secret-answer-91",
            "preferred_atom_ids": [atoms[1].atom_id],
            "avoid_atom_ids": [],
            "tool_hints": {"groundingdino": "secret-answer-91"},
            "diagnosis": "prediction differs from secret-answer-91",
        },
        {
            "objective": "improve grounded instance localization",
            "preferred_atom_ids": [atoms[1].atom_id],
            "avoid_atom_ids": [],
            "tool_hints": {"groundingdino": "cups"},
            "diagnosis": "The evidence chain missed visible target instances.",
        },
    ])
    repaired = FailureRepairDirector(failure_llm).direct(
        problem_class="object_counting",
        question="Count cups",
        groundtruth="secret-answer-91",
        prediction="0",
        slot_bindings={"target_a": "cups"},
        workflow=workflow(),
        observations=[],
        atoms=atoms,
        allowed_tool_names=["MLLM", "groundingdino"],
    )
    assert "secret-answer-91" not in json.dumps(repaired.to_dict())
    selector = MutationCandidateSelector("direction_only")
    candidates = [(type("M", (), {"mutation_id": str(index)})(), object()) for index in range(5)]
    selected = selector.select(candidates, None, [], {}, None, budget=2, allow_zero_gain=False)
    assert len(selected) == 2
    parameter_space = ParamSpace()
    portfolios = parameter_space.candidate_portfolios(
        "depth_ordering",
        {},
        workflow_tools=["MLLM"],
        allowed_tool_names=["MLLM", "groundingdino", "unidepth"],
        preferred_atom_ids=["unidepth:evidence_role:relative_depth"],
        atoms_per_portfolio=3,
    )
    assert any(
        {atom.tool_name for atom in item.selected_atoms}
        >= {"groundingdino", "unidepth"}
        for item in portfolios
    )


def test_json_execution_and_optional_export():
    registry = {
        "groundingdino": FakeTool("groundingdino", json.dumps({
            "detections": [{"box": [0, 0, 4, 4], "cls": "cup", "score": 0.9}]
        })),
        "MLLM": FakeTool("MLLM", "Answer: 2"),
    }
    runtime = ToolRuntime(registry)
    executor = WorkflowExecutor(runtime)
    spec = workflow()
    direct = executor.execute(spec, "Count cups", [], {"target_a": "cups"})
    assert direct["final_answer"] == "2"
    with tempfile.TemporaryDirectory() as root:
        path = WorkflowPythonExporter(Path(root)).export(spec)
        source = path.read_text()
        assert "def solve(" in source
        assert 'target_a=""' in source
        assert "runtime.call(" in source
        assert "WorkflowSpec" not in source
        assert json.dumps(spec.to_dict()) not in source


def test_python_skill_is_execution_source_and_snapshot_is_local():
    with tempfile.TemporaryDirectory() as root:
        config = build_experiment_config("full")
        source_paths = ExperimentPaths("full", "source", root)
        source_paths.ensure(config, "explore", False)
        source_repository = WorkflowRepository(source_paths)
        spec = workflow("snapshot_wf")
        spec.status = WorkflowStatus.ACTIVE.value
        source_repository.save(spec)
        source_script = source_repository.script_path(spec.workflow_id)
        source_script.write_text(
            source_script.read_text() + "\n# manual-edit-is-preserved\n",
            encoding="utf-8",
        )
        source_repository.save(spec)
        assert "manual-edit-is-preserved" in source_script.read_text()
        legacy = workflow("legacy_wf")
        legacy.status = WorkflowStatus.ACTIVE.value
        source_repository.save(legacy)
        legacy_script = source_repository.script_path(legacy.workflow_id)
        legacy_script.write_text(
            "WorkflowSpec.from_dict({})\n"
            "WorkflowExecutor(runtime).execute(WORKFLOW, '', [], {})\n",
            encoding="utf-8",
        )

        target_paths = ExperimentPaths("full", "target", root)
        target_paths.ensure(config, "infer", False)
        target_repository = WorkflowRepository(target_paths)
        snapshot = target_repository.snapshot_active_from(source_repository)
        copied_script = target_repository.script_path(spec.workflow_id)
        assert snapshot["active_workflow_count"] == 2
        assert snapshot["legacy_scripts_migrated"] == ["legacy_wf"]
        assert copied_script is not None
        assert "manual-edit-is-preserved" in copied_script.read_text()
        migrated_script = target_repository.script_path(legacy.workflow_id)
        assert "def solve(" in migrated_script.read_text()
        assert "WorkflowSpec.from_dict" not in migrated_script.read_text()
        source_script.unlink()
        assert copied_script.is_file()


def test_python_skill_sandbox_and_answer_normalization():
    registry = {
        "groundingdino": FakeTool("groundingdino", "ok"),
        "MLLM": FakeTool("MLLM", "2"),
    }
    with tempfile.TemporaryDirectory() as root:
        path = WorkflowPythonExporter(Path(root)).export(workflow())
        path.write_text(
            path.read_text() + "\nimport os\n",
            encoding="utf-8",
        )
        result = WorkflowExecutor(ToolRuntime(registry)).python_executor.execute(
            path,
            workflow(),
            "Count cups",
            [],
            {"target_a": "cups"},
        )
        assert not result["success"]
        assert "Unsupported Python construct" in result["error"]
        assert str(path) in result["script_traceback"]
        path.write_text(
            "WORKFLOW_ID = 'wf'\n\n"
            "def solve(runtime, question, image_paths, *, target_a=''):\n"
            "    total = 0\n"
            "    for value in range(4):\n"
            "        if value > 0:\n"
            "            total += 1\n"
            "    return runtime.finish(total)\n",
            encoding="utf-8",
        )
        result = WorkflowExecutor(ToolRuntime(registry)).python_executor.execute(
            path,
            workflow(),
            "Count cups",
            [],
            {"target_a": "cups"},
        )
        assert result["success"]
        assert result["final_answer"] == "3"
    normalizer = FinalAnswerNormalizer(QueueLLM([{"answer": "3.5"}]))
    assert normalizer.normalize("The measured result is about 3.5 meters.", "distance?", "float") == "3.5"


def test_react_reserves_final_answer_after_tool_budget():
    class ToolLoop:
        def invoke(self, messages):
            return AIMessage(content="", tool_calls=[{
                "name": "MLLM",
                "args": {},
                "id": f"call_{len(messages)}",
                "type": "tool_call",
            }])

    class FinalizingLLM:
        def bind_tools(self, tools):
            return ToolLoop()

        def invoke(self, messages):
            return FakeResponse('{"answer": "2"}')

    solver = ReactSolver(
        FinalizingLLM(),
        ToolRuntime({"MLLM": FakeTool("MLLM", "visual evidence")}),
        max_steps=2,
    )
    result = solver.solve(
        "task", "How many cups?", [], ["MLLM"], "int"
    )
    assert result["success"]
    assert result["final_answer"] == "2"
    assert len(result["observations"]) == 2


def test_multibench_balanced_subset():
    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        image_path = root_path / "image.jpg"
        Image.new("RGB", (4, 4)).save(image_path)
        sources = []
        for name in ("bench_a", "bench_b"):
            dataset_path = root_path / f"{name}.json"
            dataset_path.write_text(json.dumps({
                "metadata": {"benchmark": name},
                "data": [
                    {
                        "task_id": str(index),
                        "question": f"question {index}",
                        "answer": "yes",
                        "image": image_path.name,
                    }
                    for index in range(3)
                ],
            }))
            sources.append({
                "name": name,
                "benchmark": name,
                "dataset": str(dataset_path),
                "image_root": root,
            })
        payload = build_multibench_subset({"sources": sources}, 4, 3407)
        assert len(payload["data"]) == 4
        assert payload["metadata"]["source_counts"] == {
            "bench_a": 2,
            "bench_b": 2,
        }
        assert len({item["task_id"] for item in payload["data"]}) == 4


def test_omni3d_prediction_export_and_official_float_tolerance():
    with tempfile.TemporaryDirectory() as root:
        run_root = Path(root) / "run"
        (run_root / "results").mkdir(parents=True)
        (run_root / "metrics").mkdir(parents=True)
        task_ids = ["image_1", "image_2"]
        (run_root / "split.json").write_text(json.dumps({
            "all_task_ids": task_ids,
            "splits": {"heldout2": task_ids},
        }))
        rows = [
            {
                "task_id": "image_1",
                "mode": "infer",
                "answer": "5.10",
                "selected_workflow_id": "metric_workflow",
                "fallback_react": False,
                "split": "heldout2",
                "error": "",
            },
            {
                "task_id": "image_2",
                "mode": "infer",
                "answer": "9.0",
                "selected_workflow_id": "",
                "fallback_react": True,
                "split": "heldout2",
                "error": "",
            },
        ]
        (run_root / "results" / "per_task.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n"
        )
        annotations = Path(root) / "annotations.json"
        annotations.write_text(json.dumps({"questions": [
            {
                "image_index": "image.jpg",
                "question_index": 1,
                "image_filename": "image.jpg",
                "question": "distance",
                "answer": "5.5",
                "answer_type": "float",
            },
            {
                "image_index": "image.jpg",
                "question_index": 2,
                "image_filename": "image.jpg",
                "question": "distance",
                "answer": "10",
                "answer_type": "float",
            },
        ]}))
        predictions = export_inference_predictions(run_root)
        assert predictions.is_file()
        summary = evaluate_run(run_root, annotations, predictions)
        assert summary["categories"]["numeric_other"]["correct"] == 1
        assert summary["total"] == 2
        assert (run_root / "results" / "omni3d_native_eval.json").is_file()
        assert (run_root / "metrics" / "omni3d_official_metrics.json").is_file()


def test_top3_sequential_then_react():
    class SequenceExecutor:
        def execute(self, item, question, image_paths, slot_bindings):
            answer = "2" if item.workflow_id == "second" else ""
            return {
                "success": bool(answer),
                "final_answer": answer,
                "observations": [],
                "failed_step_ids": [],
                "error": "" if answer else "empty",
            }

    class FakeReact:
        calls = 0

        def solve(self, *args, **kwargs):
            self.calls += 1
            return {
                "success": True,
                "final_answer": "3",
                "react_answer": True,
                "observations": [],
                "failed_step_ids": [],
                "error": "",
            }

    react = FakeReact()
    coordinator = CandidateExecutionCoordinator(
        SequenceExecutor(), react, NoEvidenceValidator(), use_react=True
    )
    result = coordinator.run(
        "task", "object_counting", "Count", [], "int",
        [workflow("first"), workflow("second"), workflow("third")],
        {"target_a": "cups"}, ["MLLM", "groundingdino"],
    )
    assert result["selected_workflow_id"] == "second"
    assert len(result["attempts"]) == 2
    assert react.calls == 0
    fallback = coordinator.run(
        "task2", "object_counting", "Count", [], "int",
        [workflow("first"), workflow("third")],
        {"target_a": "cups"}, ["MLLM", "groundingdino"],
    )
    assert fallback["fallback_react"] and fallback["answer"] == "3"
    assert react.calls == 1


def test_evidence_contracts():
    result = {
        "success": True,
        "final_answer": "2",
        "failed_step_ids": [],
        "observations": [
            {"tool": "groundingdino", "result": {"status": "success", "ok": True}},
            {"tool": "MLLM", "result": {"status": "success", "ok": True}},
        ],
    }
    decision = StructuralEvidenceValidator().validate(
        "object_counting", "Count cups", "2", "int", result, []
    )
    assert decision.accepted
    missing = dict(result)
    missing["observations"] = [result["observations"][1]]
    assert not StructuralEvidenceValidator().validate(
        "object_counting", "Count cups", "2", "int", missing, []
    ).accepted
    semantic_llm = QueueLLM([{"accepted": True, "reason": "Evidence supports it."}])
    hybrid = HybridEvidenceValidator(semantic_llm)
    assert hybrid.validate(
        "relative_3d_position", "Where", "left", "str", result, []
    ).accepted
    numerical_llm = QueueLLM([{
        "accepted": False,
        "reason": "The observations do not establish the count.",
    }])
    assert not HybridEvidenceValidator(numerical_llm).validate(
        "object_counting", "Count cups", "2", "int", result, []
    ).accepted


def test_workflow_lifecycle_promotes_repeated_repairs_only():
    with tempfile.TemporaryDirectory() as root:
        config, paths = temporary_run(root)
        repository = WorkflowRepository(paths)
        store = ExperimentStore(paths)
        lifecycle = WorkflowLifecycleManager(config, repository, store)
        candidate = workflow("repair_candidate")
        candidate.mutation_mode = MutationMode.FAILURE_REPAIR.value
        candidate.metrics = WorkflowMetrics()
        lifecycle.register(candidate, "task_1", True)
        assert candidate.status == WorkflowStatus.PROVISIONAL.value
        repository.update_metrics(candidate, "task_1", True, True, 2, 0, 1.0)
        first_review = lifecycle.review(candidate, "task_1")
        assert first_review["to"] == WorkflowStatus.PROVISIONAL.value
        repository.update_metrics(candidate, "task_2", True, True, 2, 0, 1.0)
        second_review = lifecycle.review(candidate, "task_2")
        assert second_review["to"] == WorkflowStatus.ACTIVE.value
        assert repository.get(candidate.workflow_id).status == WorkflowStatus.ACTIVE.value
        extracted = workflow("extracted_candidate")
        extracted.mutation_mode = MutationMode.EXTRACTED.value
        extracted.metrics = WorkflowMetrics()
        lifecycle.register(extracted, "task_3", True)
        assert extracted.status == WorkflowStatus.PROVISIONAL.value


def test_strict_answer_matching_and_error_persistence():
    assert answer_matches_typed("yes", "yes", "bool")
    assert not answer_matches_typed("yes, because it is visible", "yes", "bool")
    assert not answer_matches_typed("sunglasses", "glass", "str")
    assert answer_matches_typed("8.1", "8.103", "float")
    assert answer_matches_typed("5.10", "5.5", "float")
    assert not answer_matches_typed("9.0", "10", "float")
    assert not answer_matches_typed("approximately 8.1", "8.103", "float")
    assert not answer_matches_typed("2.4", "2", "int")
    with tempfile.TemporaryDirectory() as root:
        _, paths = temporary_run(root)
        store = ExperimentStore(paths)
        summary = store.fail_task(
            "explore__broken",
            "explore",
            "seen100",
            "object_counting",
            "Count cups",
            "2",
            "int",
            "ValueError: synthetic failure",
        )
        assert summary["failed"] and not summary["completed"]
        assert not store.is_complete("explore__broken")
        assert (paths.trajectory_root / "explore__broken" / "error.json").is_file()
        assert (paths.results_root / "errors.jsonl").is_file()


def test_sam3_mask_and_bbox_contract():
    assert output_types("sam3") == {"segmentation_image", "pixel_detections"}
    assert contract_signature("sam3")["bbox_format"] == "xyxy_pixel"
    assert "sam3" in PIXEL_DETECTION_TOOLS
    for dependent in (
        "crop_detections",
        "picRelativeCut",
        "unidepth",
        "python_code_sandbox",
    ):
        assert "sam3" in compatible_producers(dependent)

    runtime = ToolRuntime({
        "sam3": FakeTool("sam3", json.dumps({
            "status": "success",
            "file": "http://localhost/segmentation.png",
            "detections": [{
                "bbox": [10, 20, 110, 220],
                "class_name": "red chair",
                "score": 0.91,
            }],
        })),
    })
    result = runtime.execute("sam3", {
        "query": "red chair",
        "file": "image.jpg",
        "filename": "image.jpg",
        "threshold": 0.7,
    })
    assert result["ok"]
    assert result["output_type"] == "segmentation_image"
    assert set(result["output_types"]) == {
        "segmentation_image",
        "pixel_detections",
    }
    assert result["data"]["bbox_format"] == "xyxy_pixel"
    assert result["data"]["detections"][0]["bbox"] == [10, 20, 110, 220]
    invalid = runtime.execute("sam3", {
        "query": "the red chair beside table",
        "file": "image.jpg",
        "filename": "image.jpg",
    })
    assert not invalid["ok"] and "1-3 English words" in invalid["error"]

    sam_atom = ParamAtom(
        "sam3",
        "threshold",
        "high",
        "numerical",
        "Collect mask and bbox evidence.",
    )
    steps = WorkflowMutator._steps_for_atom(
        sam_atom,
        ApplicabilitySpec("occlusion_visibility"),
        {},
        {"sam_query_a": "red chair", "sam_query_b": "table"},
    )
    assert [step.args["query"] for step in steps] == [
        "$slot.sam_query_a",
        "$slot.sam_query_b",
    ]
    assert all(step.args["threshold"] == 0.7 for step in steps)
    normalized_crop = WorkflowMutator._normalize_args(
        "crop_detections",
        {"file": "/tmp/image.jpg", "folder": "/tmp/clocks"},
        0,
    )
    assert normalized_crop["file"] == "$image"
    assert normalized_crop["folder"] == "spatialskillgrowth_crops"


def test_structural_then_llm_consolidation_and_cap():
    with tempfile.TemporaryDirectory() as root:
        _, paths = temporary_run(root)
        repository = WorkflowRepository(paths)
        store = ExperimentStore(paths)
        existing = workflow("existing")
        repository.save(existing)
        llm = QueueLLM([{
            "action": "merge",
            "reason": "Same abstract evidence condition.",
            "generalized_name": "grounded_count",
            "generalized_description": "Use for grounded visible instance counting.",
            "generalized_exclusions": "Exclude non-visible capacity questions.",
            "generalized_capability_boundary": "Requires countable grounded instances.",
        }])
        consolidator = WorkflowConsolidator(
            repository,
            store,
            StructuralCompatibilityChecker(),
            ApplicabilityCompatibilityJudge(llm),
            ParetoWorkflowPruner(12),
            semantic_consolidation=True,
        )
        candidate = workflow("candidate", accuracy=(2, 2))
        result = consolidator.consolidate(candidate, "task")
        assert result["merged_with"]
        assert len(llm.messages) == 1
        different = workflow("different", tools=("MLLM",), accuracy=(1, 1))
        consolidator.consolidate(different, "task2")
        assert len(llm.messages) == 1
        candidates = [workflow(f"cap_{index}", accuracy=(index + 1, index + 2)) for index in range(13)]
        archived = ParetoWorkflowPruner(12).select_archive(candidates)
        assert len(archived) == 1


def test_exploration_pipeline_activation():
    class PipelineLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            first = messages[0].content
            text = first[0]["text"] if isinstance(first, list) else str(first)
            if "抽取可复用的运行时槽位" in text:
                return FakeResponse(json.dumps({
                    "target_a": "cups",
                    "target_b": "",
                    "reference_frame": "none",
                    "reference_entity": "",
                    "reference_value": "",
                    "reference_unit": "",
                    "measurement_dimension": "count",
                    "operation": "count",
                }))
            if "编写可复用" in text and "适用范围" in text:
                return FakeResponse(json.dumps({
                    "name": "direct_visible_count",
                    "description": "Use direct visual reasoning for visible instance counting.",
                    "exclusions": "Exclude volume capacity questions.",
                    "capability_boundary": "Requires visible countable targets.",
                    "required_slots": [],
                }))
            return AIMessage(content="2")

    with tempfile.TemporaryDirectory() as root:
        config = build_experiment_config("no_success_enhancement")
        paths = ExperimentPaths(
            config.name,
            "integration",
            root,
            benchmark="omni3d",
            problem_classes=list(OMNI3D_PROBLEM_CLASSES),
        )
        paths.ensure(config, "explore", False)
        pipeline = ExperimentFactory(
            config,
            paths,
            PipelineLLM(),
            runtime=ToolRuntime({"MLLM": FakeTool("MLLM", "Answer: 2")}),
            max_react_steps=2,
            benchmark="omni3d",
            problem_classes=list(OMNI3D_PROBLEM_CLASSES),
        ).build_exploration()
        result = pipeline.ask(TaskRecord(
            task_id="integration_task",
            question="How many cups are visible?",
            groundtruth="2",
            image_paths=[],
            capability="object_counting",
            answer_type="int",
        ))
        assert result["correct"]
        assert not result["activated_workflow_ids"]
        assert len(result["provisional_workflow_ids"]) == 1
        assert len(pipeline.repository.list_provisional("object_counting")) == 1
        validation = pipeline.validate_provisional([TaskRecord(
            task_id="integration_task",
            question="How many cups are visible?",
            groundtruth="2",
            image_paths=[],
            capability="object_counting",
            answer_type="int",
        )])
        assert validation["attempted"] == 0
        assert len(validation["skipped"]) == 1


def main():
    tests = [
        test_taxonomy_and_split,
        test_anomaly_taxonomy_and_embedding_workflow,
        test_removed_tools_are_not_in_active_runtime,
        test_llm_temperature_is_fixed,
        test_manifest_isolation,
        test_benchmark_aware_problem_classes_and_skills,
        test_cross_benchmark_source_uses_source_taxonomy,
        test_skill_whiteboard_initializes_without_overwriting,
        test_retrievers_are_multimodal_and_support_reject,
        test_mutation_director_groundtruth_boundary_and_budget,
        test_json_execution_and_optional_export,
        test_python_skill_is_execution_source_and_snapshot_is_local,
        test_python_skill_sandbox_and_answer_normalization,
        test_react_reserves_final_answer_after_tool_budget,
        test_multibench_balanced_subset,
        test_omni3d_prediction_export_and_official_float_tolerance,
        test_top3_sequential_then_react,
        test_evidence_contracts,
        test_workflow_lifecycle_promotes_repeated_repairs_only,
        test_strict_answer_matching_and_error_persistence,
        test_sam3_mask_and_bbox_contract,
        test_structural_then_llm_consolidation_and_cap,
        test_exploration_pipeline_activation,
    ]
    for test in tests:
        test()
        print(f"[PASS] {test.__name__}")
    print(f"SpatialSkillGrowth no-API tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
