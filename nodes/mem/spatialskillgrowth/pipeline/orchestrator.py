"""SpatialSkillGrowth 的探索与冻结推理流水线。"""

from __future__ import annotations

import csv
import json
import threading
import traceback
from typing import Dict, List, Optional

from nodes.mem.spatialskillgrowth.core.experiment_config import (
    ExperimentConfig,
    ExperimentPaths,
)
from nodes.mem.spatialskillgrowth.core.models import (
    EvidenceDecision,
    TaskRecord,
    WorkflowSpec,
)
from nodes.mem.spatialskillgrowth.growth.mutation import (
    ApplicabilityGeneralizer,
    FailureRepairDirector,
    MutationCandidateSelector,
    SuccessEnhancementDirector,
    WorkflowMutationEngine,
)
from nodes.mem.spatialskillgrowth.growth.skill_consolidator import (
    ApplicabilityCompatibilityJudge,
    ParetoWorkflowPruner,
    StructuralCompatibilityChecker,
    WorkflowConsolidator,
)
from nodes.mem.spatialskillgrowth.growth.workflow_lifecycle import (
    WorkflowLifecycleManager,
)
from nodes.mem.spatialskillgrowth.pipeline.answer_evaluator import answer_matches
from nodes.mem.spatialskillgrowth.pipeline.evidence_validator import (
    build_evidence_validator,
)
from nodes.mem.spatialskillgrowth.pipeline.media_processing import MediaPreprocessor
from nodes.mem.spatialskillgrowth.pipeline.task_router import TaskPlanner
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import ToolRuntime
from nodes.mem.spatialskillgrowth.runtime.workflow_executor import (
    CandidateExecutionCoordinator,
    ReactSolver,
    WorkflowExecutor,
)
from nodes.mem.spatialskillgrowth.skills.skill_retriever import (
    build_retriever,
    workflow_structurally_eligible,
)
from nodes.mem.spatialskillgrowth.storage.growth_store import (
    ExperimentStore,
    WorkflowRepository,
)


PROBLEM_CLASS_LOCKS: Dict[str, threading.RLock] = {}
PROBLEM_CLASS_LOCK_GUARD = threading.Lock()


def problem_class_lock(problem_class: str) -> threading.RLock:
    with PROBLEM_CLASS_LOCK_GUARD:
        return PROBLEM_CLASS_LOCKS.setdefault(problem_class, threading.RLock())


class ExplorationPipeline:
    def __init__(
        self,
        config: ExperimentConfig,
        paths: ExperimentPaths,
        store: ExperimentStore,
        repository: WorkflowRepository,
        planner: TaskPlanner,
        retriever,
        coordinator: CandidateExecutionCoordinator,
        mutation_engine: WorkflowMutationEngine,
        generalizer: ApplicabilityGeneralizer,
        consolidator: WorkflowConsolidator,
        lifecycle: WorkflowLifecycleManager,
        workflow_executor: WorkflowExecutor,
        split_name: str = "explore",
        media_preprocessor: Optional[MediaPreprocessor] = None,
    ):
        self.config = config
        self.paths = paths
        self.store = store
        self.repository = repository
        self.planner = planner
        self.retriever = retriever
        self.coordinator = coordinator
        self.mutation_engine = mutation_engine
        self.generalizer = generalizer
        self.consolidator = consolidator
        self.lifecycle = lifecycle
        self.workflow_executor = workflow_executor
        self.split_name = split_name
        self.media_preprocessor = media_preprocessor

    def ask(self, task: TaskRecord, resume: bool = False) -> Dict:
        state_task_id = f"explore__{task.task_id}"
        if resume and self.store.is_complete(state_task_id):
            summary = self.store.get_summary(state_task_id) or {}
            summary["cached"] = True
            return summary
        if self.media_preprocessor is not None:
            task = self.media_preprocessor.prepare(task)
        try:
            # {
            #     "problem_class": event_type,
            #     "slot_bindings": {"event_type": event_type},
            #     "selected_tools": selected_tools,
            #     "excluded_tools": excluded_tools,
            #     "tool_decisions": tool_decisions,
            # }
            plan = self.planner.plan(
                task.event_type,
                [task.media_path],
                self.workflow_executor.runtime.registry,
            )
            problem_class = plan["problem_class"]
            with problem_class_lock(problem_class):
                return self._ask_locked(state_task_id, task, plan)
        except Exception:
            self.store.fail_task(
                state_task_id,
                "explore",
                self.split_name,
                task.event_type,
                task.question,
                task.groundtruth,
                traceback.format_exc(),
            )
            raise

    def _ask_locked(self, state_task_id: str, task: TaskRecord, plan: Dict) -> Dict:
        problem_class = plan["problem_class"]
        self.store.begin_task(
            state_task_id,
            "explore",
            self.split_name,
            problem_class,
            task.question,
            task.groundtruth,
        )
        workflows, retrieval = self.retriever.retrieve(
            problem_class,
            task.question,
            task.visual_paths,
            plan["slot_bindings"],
            plan["selected_tools"],
        )
        self.store.save_retrieval(state_task_id, retrieval)
        execution = self.coordinator.run(
            state_task_id,
            problem_class,
            task.question,
            task.visual_paths,
            workflows,
            plan["slot_bindings"],
            plan["selected_tools"],
            media_path=task.media_path,
        )
        lifecycle_results = self._persist_execution_attempts(
            state_task_id, task, execution, update_metrics=True
        )
        parent_attempt = _selected_attempt(execution)
        parent_answer = str(execution.get("answer") or "")
        parent_correct = answer_matches(parent_answer, task.groundtruth)
        parent_workflow = self._parent_workflow(
            task,
            plan,
            execution,
            parent_attempt,
        )
        activated = []
        provisional = []
        consolidation_results = []
        for lifecycle_result in lifecycle_results:
            if (
                lifecycle_result.get("to") == "active"
                and lifecycle_result.get("from") != "active"
            ):
                activated.append(lifecycle_result["workflow_id"])
            elif lifecycle_result.get("to") == "provisional":
                provisional.append(lifecycle_result["workflow_id"])
            if lifecycle_result.get("consolidation"):
                consolidation_results.append(lifecycle_result["consolidation"])
        if parent_correct:
            persisted = self._persist_correct_workflow(
                parent_workflow,
                task,
                plan,
                parent_attempt,
            )
            if persisted.get("registered") and persisted["status"] == "active":
                activated.append(persisted["representative_workflow_id"])
            elif (
                persisted.get("registered")
                and persisted["status"] == "provisional"
            ):
                provisional.append(persisted["representative_workflow_id"])
            if persisted.get("consolidation"):
                consolidation_results.append(persisted["consolidation"])

        direction = None
        mutant_summaries = []
        mutation_enabled = (
            parent_correct and self.config.success_enhancement
        ) or (
            not parent_correct and self.config.failure_repair
        )
        if mutation_enabled:
            budget = (
                self.config.success_candidate_budget
                if parent_correct
                else self.config.failure_candidate_budget
            )
            direction, mutants = self.mutation_engine.generate(
                parent=parent_workflow,
                question=task.question,
                groundtruth=task.groundtruth,
                prediction=parent_answer,
                parent_correct=parent_correct,
                observations=_observations(parent_attempt),
                slot_bindings=plan["slot_bindings"],
                allowed_tool_names=plan["selected_tools"],
                task_id=task.task_id,
                active_workflows=self.repository.list_retrievable(
                    problem_class, include_provisional=True
                ),
                atom_stats=self.store.atom_stats(problem_class),
                budget=budget,
            )
            self.store.save_direction(state_task_id, direction.mode, direction.to_dict())
            for index, mutant in enumerate(mutants):
                mutant_summary, consolidation = self._execute_mutant(
                    state_task_id,
                    task,
                    plan,
                    mutant,
                    index,
                )
                mutant_summaries.append(mutant_summary)
                if consolidation:
                    if consolidation["status"] == "active":
                        activated.append(consolidation["representative_workflow_id"])
                    else:
                        provisional.append(consolidation["representative_workflow_id"])
                    if consolidation.get("consolidation"):
                        consolidation_results.append(consolidation["consolidation"])

        correct_mutant = next(
            (item for item in mutant_summaries if item["correct"]), None
        )
        final_answer = parent_answer if parent_correct or not correct_mutant else correct_mutant["answer"]
        final_correct = answer_matches(final_answer, task.groundtruth)
        final_detection = execution if parent_correct or not correct_mutant else correct_mutant
        summary = {
            "task_id": task.task_id,
            "state_task_id": state_task_id,
            "mode": "explore",
            "experiment": self.config.name,
            "run_id": self.paths.run_id,
            "split": self.split_name,
            "problem_class": problem_class,
            "question": task.question,
            "groundtruth": task.groundtruth,
            "answer": final_answer,
            "event_type": final_detection.get("event_type", problem_class),
            "event_name": self.paths.class_metadata.get(problem_class, {}).get(
                "title", problem_class
            ),
            "media_type": task.media_type,
            "sampled_frame_paths": task.sampled_frame_paths,
            "media_metadata": task.media_metadata,
            "is_anomaly": final_detection.get("is_anomaly"),
            "threshold": final_detection.get("threshold"),
            "correct": final_correct,
            "parent_correct": parent_correct,
            "base_workflow_id": parent_workflow.workflow_id,
            "retrieval": retrieval.to_dict(),
            "mutation_direction": direction.to_dict() if direction else {},
            "mutants": mutant_summaries,
            "activated_workflow_ids": list(dict.fromkeys(activated)),
            "provisional_workflow_ids": list(dict.fromkeys(provisional)),
            "consolidation": consolidation_results,
            "tool_plan": plan,
            "cached": False,
        }
        self.store.complete_task(state_task_id, final_answer, final_correct, summary)
        return summary

    def _persist_execution_attempts(
        self,
        state_task_id: str,
        task: TaskRecord,
        execution: Dict,
        update_metrics: bool,
    ) -> List[Dict]:
        lifecycle_results = []
        for index, attempt in enumerate(execution["attempts"]):
            answer = str(attempt.get("answer") or "")
            correct = answer_matches(answer, task.groundtruth)
            evidence = attempt["evidence"]
            self.store.save_trial(
                state_task_id,
                f"parent_{index}",
                attempt.get("workflow_id", ""),
                "",
                answer,
                correct,
                evidence,
                attempt["result"],
            )
            workflow = attempt.get("workflow")
            if update_metrics and isinstance(workflow, WorkflowSpec):
                if self.repository.get(workflow.workflow_id) is None:
                    workflow.metrics.structural_coverage = _structural_coverage(
                        workflow
                    )
                    workflow = self.lifecycle.register(
                        workflow,
                        task.task_id,
                        evidence.accepted,
                    )
                updated = _update_workflow_metrics(
                    self.repository,
                    workflow,
                    task.task_id,
                    correct,
                    evidence,
                    attempt["result"],
                )
                review = self.lifecycle.review(updated, task.task_id)
                review["workflow_id"] = updated.workflow_id
                if review["from"] != "active" and review["to"] == "active":
                    promoted = self.repository.get(updated.workflow_id) or updated
                    review["consolidation"] = self.consolidator.consolidate(
                        promoted, task.task_id
                    )
                    review["workflow_id"] = review["consolidation"][
                        "representative_workflow_id"
                    ]
                lifecycle_results.append(review)
        return lifecycle_results

    def _parent_workflow(self, task, plan, execution, attempt) -> WorkflowSpec:
        workflow = attempt.get("workflow") if attempt else None
        if isinstance(workflow, WorkflowSpec):
            return self.repository.get(workflow.workflow_id) or workflow
        result = attempt.get("result") if attempt else {}
        trajectory = result.get("trajectory") or result.get("observations") or []
        return self.mutation_engine.extract_parent(
            plan["problem_class"],
            task.question,
            trajectory,
            task.task_id,
            plan["slot_bindings"],
        )

    def _persist_correct_workflow(self, workflow, task, plan, attempt) -> Dict:
        existing = self.repository.get(workflow.workflow_id)
        evidence = attempt["evidence"] if attempt else EvidenceDecision(
            True, "groundtruth", "Ground-truth validated exploration execution."
        )
        result = attempt["result"] if attempt else {}
        if existing is None:
            workflow = self.generalizer.generalize(workflow, task.question, plan["slot_bindings"])
            workflow.metrics.structural_coverage = _structural_coverage(workflow)
            workflow = self.lifecycle.register(
                workflow, task.task_id, evidence.accepted
            )
            workflow = _update_workflow_metrics(
                self.repository,
                workflow,
                task.task_id,
                True,
                evidence,
                result,
            )
        else:
            return {
                "status": existing.status,
                "representative_workflow_id": existing.workflow_id,
                "consolidation": None,
                "registered": False,
            }
        if workflow.status == "active":
            consolidation = self.consolidator.consolidate(workflow, task.task_id)
            return {
                "status": "active",
                "representative_workflow_id": consolidation[
                    "representative_workflow_id"
                ],
                "consolidation": consolidation,
                "registered": True,
            }
        return {
            "status": workflow.status,
            "representative_workflow_id": workflow.workflow_id,
            "consolidation": None,
            "registered": True,
        }

    def _execute_mutant(self, state_task_id, task, plan, mutant, index):
        result = self.workflow_executor.execute(
            mutant,
            task.question,
            task.visual_paths,
            plan["slot_bindings"],
            media_path=task.media_path,
        )
        answer = str(result.get("final_answer") or "")
        correct = answer_matches(answer, task.groundtruth)
        evidence = self.coordinator.evidence_validator.validate(
            plan["problem_class"],
            task.question,
            answer,
            result,
            [task.media_path],
        )
        self.store.save_trial(
            state_task_id,
            f"mutant_{index}",
            mutant.workflow_id,
            mutant.mutation_mode,
            answer,
            correct,
            evidence,
            result,
        )
        selected_atoms = list(mutant.mutation_direction.get("selected_atom_ids") or [])
        self.store.record_atom_results(
            plan["problem_class"],
            {atom_id: correct for atom_id in selected_atoms},
        )
        consolidation = None
        if correct:
            mutant = self.generalizer.generalize(
                mutant, task.question, plan["slot_bindings"]
            )
            mutant.metrics.structural_coverage = _structural_coverage(mutant)
            mutant = self.lifecycle.register(
                mutant, task.task_id, evidence.accepted
            )
            mutant = _update_workflow_metrics(
                self.repository,
                mutant,
                task.task_id,
                True,
                evidence,
                result,
            )
            consolidation = {
                "status": mutant.status,
                "representative_workflow_id": mutant.workflow_id,
                "consolidation": None,
            }
        return {
            "role": f"mutant_{index}",
            "workflow_id": mutant.workflow_id,
            "mutation_mode": mutant.mutation_mode,
            "answer": answer,
            "event_type": result.get("event_type", plan["problem_class"]),
            "is_anomaly": result.get("is_anomaly"),
            "threshold": result.get("threshold"),
            "correct": correct,
            "evidence": evidence.to_dict(),
            "selected_atom_ids": selected_atoms,
            "error": str(result.get("error") or ""),
        }, consolidation

    def validate_provisional(self, tasks: List[TaskRecord]) -> Dict:
        """在未见过的同类探索样本上验证 provisional Skill，并触发晋升。"""
        report = {"attempted": 0, "promoted": [], "archived": [], "skipped": []}
        if not self.config.provisional_validation:
            return report
        task_problem_classes = set()
        for task in tasks:
            task_problem_classes.add(task.event_type)
        eligible_candidates = [
            workflow for workflow in self.repository.list_provisional()
            if workflow.metrics.correct_count > 0
            and workflow.applicability.problem_class in task_problem_classes
        ]
        candidates = []
        for problem_class in sorted({
            item.applicability.problem_class for item in eligible_candidates
        }):
            same_class = [
                item for item in eligible_candidates
                if item.applicability.problem_class == problem_class
            ]
            same_class.sort(key=lambda item: (
                -item.metrics.evidence_rate,
                -item.metrics.accuracy,
                -item.metrics.correct_count,
                item.metrics.average_cost,
                item.workflow_id,
            ))
            candidates.extend(same_class[
                : self.config.provisional_validation_candidates_per_class
            ])
        for candidate in candidates:
            workflow_id = candidate.workflow_id
            attempted_task_ids = {
                item.removeprefix("explore__")
                for item in self.store.workflow_task_ids(workflow_id)
            }
            attempted_task_ids.update(candidate.source_task_ids)
            validation_tasks = []
            for task in tasks:
                if task.task_id in attempted_task_ids:
                    continue
                summary = self.store.get_summary(f"explore__{task.task_id}") or {}
                plan = summary.get("tool_plan") or {}
                if plan.get("problem_class") != candidate.applicability.problem_class:
                    continue
                if not workflow_structurally_eligible(
                    candidate,
                    dict(plan.get("slot_bindings") or {}),
                    list(plan.get("selected_tools") or []),
                ):
                    continue
                validation_tasks.append((task, plan))
            if not validation_tasks:
                report["skipped"].append({
                    "workflow_id": workflow_id,
                    "reason": "No unseen structurally eligible exploration task.",
                })
                continue
            for index, (task, plan) in enumerate(
                validation_tasks[: self.config.provisional_validation_trials]
            ):
                if self.media_preprocessor is not None:
                    task = self.media_preprocessor.prepare(task)
                current = self.repository.get(workflow_id)
                if current is None or current.status != "provisional":
                    break
                result = self.workflow_executor.execute(
                    current,
                    task.question,
                    task.visual_paths,
                    dict(plan.get("slot_bindings") or {}),
                    media_path=task.media_path,
                )
                answer = str(result.get("final_answer") or "")
                correct = answer_matches(answer, task.groundtruth)
                evidence = self.coordinator.evidence_validator.validate(
                    current.applicability.problem_class,
                    task.question,
                    answer,
                    result,
                    [task.media_path],
                )
                state_task_id = f"explore__{task.task_id}"
                self.store.save_trial(
                    state_task_id,
                    f"validation_{workflow_id}_{index}",
                    workflow_id,
                    "provisional_validation",
                    answer,
                    correct,
                    evidence,
                    result,
                )
                updated = _update_workflow_metrics(
                    self.repository,
                    current,
                    task.task_id,
                    correct,
                    evidence,
                    result,
                )
                review = self.lifecycle.review(updated, task.task_id)
                report["attempted"] += 1
                self.store.save_trajectory(
                    state_task_id,
                    f"validation_{workflow_id}_{index}",
                    {
                        "workflow_id": workflow_id,
                        "task_id": task.task_id,
                        "answer": answer,
                        "correct": correct,
                        "evidence": evidence.to_dict(),
                        "lifecycle": review,
                    },
                )
                if review["to"] == "active":
                    promoted = self.repository.get(workflow_id) or updated
                    consolidation = self.consolidator.consolidate(
                        promoted, task.task_id
                    )
                    report["promoted"].append(
                        consolidation["representative_workflow_id"]
                    )
                    break
                if review["to"] == "archive":
                    report["archived"].append(workflow_id)
                    break
        report_path = self.paths.metrics_root / "provisional_validation.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report


class InferencePipeline:
    def __init__(
        self,
        config: ExperimentConfig,
        paths: ExperimentPaths,
        store: ExperimentStore,
        planner: TaskPlanner,
        retriever,
        coordinator: CandidateExecutionCoordinator,
        runtime: ToolRuntime,
        media_preprocessor: Optional[MediaPreprocessor] = None,
    ):
        self.config = config
        self.paths = paths
        self.store = store
        self.planner = planner
        self.retriever = retriever
        self.coordinator = coordinator
        self.runtime = runtime
        self.media_preprocessor = media_preprocessor

    def ask(self, task: TaskRecord, split_name: str, resume: bool = False) -> Dict:
        state_task_id = f"infer__{task.task_id}"
        if resume and self.store.is_complete(state_task_id):
            summary = self.store.get_summary(state_task_id) or {}
            summary["cached"] = True
            return summary
        if self.media_preprocessor is not None:
            task = self.media_preprocessor.prepare(task)
        try:
            return self._ask(task, split_name, state_task_id)
        except Exception:
            self.store.fail_task(
                state_task_id,
                "infer",
                split_name,
                task.event_type,
                task.question,
                task.groundtruth,
                traceback.format_exc(),
            )
            raise

    def _ask(self, task: TaskRecord, split_name: str, state_task_id: str) -> Dict:
        plan = self.planner.plan(
            task.event_type,
            [task.media_path],
            self.runtime.registry,
        )
        self.store.begin_task(
            state_task_id,
            "infer",
            split_name,
            plan["problem_class"],
            task.question,
            task.groundtruth,
        )
        workflows, retrieval = self.retriever.retrieve(
            plan["problem_class"],
            task.question,
            task.visual_paths,
            plan["slot_bindings"],
            plan["selected_tools"],
        )
        self.store.save_retrieval(state_task_id, retrieval)
        execution = self.coordinator.run(
            state_task_id,
            plan["problem_class"],
            task.question,
            task.visual_paths,
            workflows,
            plan["slot_bindings"],
            plan["selected_tools"],
            media_path=task.media_path,
        )
        for index, attempt in enumerate(execution["attempts"]):
            answer = str(attempt.get("answer") or "")
            correct = bool(task.groundtruth) and answer_matches(
                answer, task.groundtruth
            )
            self.store.save_trial(
                state_task_id,
                f"inference_{index}",
                attempt.get("workflow_id", ""),
                "",
                answer,
                correct,
                attempt["evidence"],
                attempt["result"],
            )
        answer = str(execution.get("answer") or "")
        correct = (
            answer_matches(answer, task.groundtruth)
            if task.groundtruth
            else None
        )
        summary = {
            "task_id": task.task_id,
            "state_task_id": state_task_id,
            "mode": "infer",
            "experiment": self.config.name,
            "run_id": self.paths.run_id,
            "split": split_name,
            "problem_class": plan["problem_class"],
            "question": task.question,
            "groundtruth": task.groundtruth,
            "answer": answer,
            "event_type": execution.get("event_type", plan["problem_class"]),
            "event_name": self.paths.class_metadata.get(
                plan["problem_class"], {}
            ).get("title", plan["problem_class"]),
            "media_type": task.media_type,
            "sampled_frame_paths": task.sampled_frame_paths,
            "media_metadata": task.media_metadata,
            "is_anomaly": execution.get("is_anomaly"),
            "threshold": execution.get("threshold"),
            "correct": correct,
            "selected_workflow_id": execution["selected_workflow_id"],
            "fallback_react": execution["fallback_react"],
            "accepted": execution["accepted"],
            "retrieval": retrieval.to_dict(),
            "attempts": [_serializable_attempt(item) for item in execution["attempts"]],
            "tool_plan": plan,
            "error": execution["error"],
            "cached": False,
        }
        self.store.complete_task(state_task_id, answer, bool(correct), summary)
        return summary


class ExperimentFactory:
    def __init__(
        self,
        config: ExperimentConfig,
        paths: ExperimentPaths,
        llm,
        runtime: Optional[ToolRuntime] = None,
        source_repository: Optional[WorkflowRepository] = None,
        max_react_steps: int = 8,
        exploration_split_name: str = "explore",
    ):
        self.config = config
        self.paths = paths
        self.llm = llm
        self.runtime = runtime or ToolRuntime()
        self.store = ExperimentStore(paths)
        self.repository = WorkflowRepository(paths)
        self.retrieval_repository = source_repository or self.repository
        self.exploration_split_name = exploration_split_name
        self.class_metadata = paths.class_metadata
        self.media_preprocessor = MediaPreprocessor(
            paths.state_dir / "sampled_frames",
            sample_fps=float(config.extra.get("video_sample_fps", 1.0)),
            max_sampled_frames=int(
                config.extra.get("max_sampled_frames", 12)
            ),
        )
        self.planner = TaskPlanner()
        self.retriever = build_retriever(
            self.retrieval_repository,
            llm,
            config.workflow_top_k,
        )
        self.workflow_executor = WorkflowExecutor(
            self.runtime,
            repository=self.retrieval_repository,
            candidate_script_root=paths.state_dir / "python_candidates",
        )
        self.evidence_validator = build_evidence_validator()
        self.coordinator = CandidateExecutionCoordinator(
            self.workflow_executor,
            ReactSolver(llm, self.runtime, max_steps=max_react_steps),
            self.evidence_validator,
            use_react=config.use_react,
            max_workflow_attempts=config.workflow_top_k, #3
        )

    def build_exploration(self) -> ExplorationPipeline:
        self.coordinator.use_react = self.config.use_react
        # 在探索阶段，允许检索到 provisional workflow，以便进行 mutation 和 consolidation。
        self.retriever.include_provisional = True
        mutation_engine = WorkflowMutationEngine(
            SuccessEnhancementDirector(self.llm),
            FailureRepairDirector(self.llm),
            MutationCandidateSelector(self.config.seed),
            {
                name: item.get("description", "")
                for name, item in self.class_metadata.items()
            },
        )
        consolidator = WorkflowConsolidator(
            self.repository,
            self.store,
            StructuralCompatibilityChecker(),
            ApplicabilityCompatibilityJudge(self.llm),
            ParetoWorkflowPruner(self.config.active_cap_per_class),
            semantic_consolidation=True,
        )
        lifecycle = WorkflowLifecycleManager(
            self.config, self.repository, self.store
        )
        return ExplorationPipeline(
            self.config,
            self.paths,
            self.store,
            self.repository,
            self.planner,
            self.retriever,
            self.coordinator,
            mutation_engine,
            ApplicabilityGeneralizer(self.llm),
            consolidator,
            lifecycle,
            self.workflow_executor,
            self.exploration_split_name,
            media_preprocessor=self.media_preprocessor,
        )

    def build_inference(self) -> InferencePipeline:
        self.coordinator.use_react = self.config.use_react
        self.retriever.include_provisional = False
        return InferencePipeline(
            self.config,
            self.paths,
            self.store,
            self.planner,
            self.retriever,
            self.coordinator,
            self.runtime,
            media_preprocessor=self.media_preprocessor,
        )


def write_evaluation_summary(paths: ExperimentPaths) -> Dict:
    result_path = paths.results_root / "per_task.jsonl"
    rows = []
    if result_path.exists():
        for line in result_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("mode") == "infer":
                rows.append(item)
    summary = {"overall": _metrics(rows)}
    split_names = sorted({str(item.get("split") or "") for item in rows})
    for split_name in split_names:
        summary[split_name] = _metrics([
            item for item in rows if item.get("split") == split_name
        ])
    overall_label = f"overall{len(rows)}"
    summary[overall_label] = summary["overall"]
    per_class = {}
    for problem_class in sorted({str(item.get("problem_class") or "") for item in rows}):
        per_class[problem_class] = _metrics([
            item for item in rows if item.get("problem_class") == problem_class
        ])
    summary["per_problem_class"] = per_class
    repository = WorkflowRepository(paths)
    summary["skill_library"] = {
        "active": len(repository.list_active()),
        "provisional": len(repository.list_provisional()),
        "archive": len(repository.list_archive()),
    }
    snapshot_path = paths.skill_root / "SOURCE_SNAPSHOT.json"
    if snapshot_path.is_file():
        summary["skill_source"] = json.loads(snapshot_path.read_text(encoding="utf-8"))
    path = paths.metrics_root / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = paths.results_root / "per_task.csv"
    columns = [
        "task_id", "split", "problem_class", "groundtruth",
        "event_type", "event_name", "media_type", "answer", "is_anomaly",
        "threshold", "correct", "selected_workflow_id", "fallback_react", "error",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})
    markdown = ["# 异常检测结果汇总", ""]
    for label in [overall_label] + split_names:
        metrics = summary[label]
        if metrics["total"]:
            markdown.append(
                f"- {label}: {metrics['correct']}/{metrics['total']} "
                f"({metrics['accuracy']:.4f})"
            )
        else:
            markdown.append(
                f"- {label}: {metrics['predictions']} 条无标签检测结果"
            )
    markdown.append("")
    (paths.root / "summary.md").write_text("\n".join(markdown), encoding="utf-8")
    return summary


def _update_workflow_metrics(
    repository: WorkflowRepository,
    workflow: WorkflowSpec,
    task_id: str,
    correct: bool,
    evidence: EvidenceDecision,
    result: Dict,
) -> WorkflowSpec:
    observations = result.get("observations") or result.get("evidence") or []
    failures = len(result.get("failed_step_ids") or [])
    return repository.update_metrics(
        workflow,
        task_id,
        correct,
        evidence.accepted,
        len(observations),
        failures,
        float(result.get("latency_ms") or 0.0),
    )


def _selected_attempt(execution: Dict) -> Dict:
    selected = str(execution.get("selected_workflow_id") or "")
    if selected:
        return next(
            (item for item in execution["attempts"] if item.get("workflow_id") == selected),
            execution["attempts"][-1],
        )
    return execution["attempts"][-1] if execution["attempts"] else {}


def _observations(attempt: Dict) -> List[Dict]:
    result = attempt.get("result") or {}
    return list(result.get("observations") or result.get("evidence") or [])


def _structural_coverage(workflow: WorkflowSpec) -> float:
    tools = {step.tool_name for step in workflow.steps}
    edges = sum(len(step.depends_on) for step in workflow.steps)
    return float(len(tools) + edges)


def _serializable_attempt(attempt: Dict) -> Dict:
    result = attempt.get("result") or {}
    observations = result.get("observations") or result.get("evidence") or []
    successful_tools = []
    for observation in observations:
        tool_result = observation.get("result") or {}
        tool_name = str(observation.get("tool") or "")
        if tool_name and tool_result.get("ok") and tool_name not in successful_tools:
            successful_tools.append(tool_name)
    return {
        "kind": attempt.get("kind", ""),
        "workflow_id": attempt.get("workflow_id", ""),
        "answer": attempt.get("answer", ""),
        "event_type": result.get("event_type", ""),
        "is_anomaly": result.get("is_anomaly"),
        "threshold": result.get("threshold"),
        "success": bool(result.get("success")),
        "successful_tools": successful_tools,
        "accepted": bool(attempt.get("accepted")),
        "evidence": attempt["evidence"].to_dict(),
        "error": str(result.get("error") or ""),
    }


def _metrics(rows: List[Dict]) -> Dict:
    labeled = [item for item in rows if str(item.get("groundtruth") or "").strip()]
    total = len(labeled)
    correct = sum(bool(item.get("correct")) for item in labeled)
    return {
        "correct": correct,
        "total": total,
        "predictions": len(rows),
        "accuracy": correct / total if total else 0.0,
    }
