"""工作流 provisional/active/archive 生命周期。"""

from __future__ import annotations

from typing import Dict

from nodes.mem.spatialskillgrowth.experiment_config import ExperimentConfig
from nodes.mem.spatialskillgrowth.growth_store import ExperimentStore, WorkflowRepository
from nodes.mem.spatialskillgrowth.models import MutationMode, WorkflowSpec, WorkflowStatus


class WorkflowLifecycleManager:
    """失败修复先作为局部候选，只有重复验证后才进入冻结技能库。"""

    def __init__(
        self,
        config: ExperimentConfig,
        repository: WorkflowRepository,
        store: ExperimentStore,
    ):
        self.config = config
        self.repository = repository
        self.store = store

    def register(
        self,
        workflow: WorkflowSpec,
        task_id: str,
        evidence_accepted: bool,
    ) -> WorkflowSpec:
        directly_active = (
            self.config.one_shot_activation
            and workflow.mutation_mode == MutationMode.EXTRACTED.value
            and evidence_accepted
        )
        target = (
            WorkflowStatus.ACTIVE
            if directly_active
            else WorkflowStatus.PROVISIONAL
        )
        workflow.status = target.value
        self.repository.save(workflow)
        self.store.record_workflow_event(
            workflow.workflow_id,
            task_id,
            "activate" if directly_active else "register_provisional",
            {
                "mutation_mode": workflow.mutation_mode,
                "evidence_accepted": evidence_accepted,
            },
        )
        return workflow

    def review(self, workflow: WorkflowSpec, task_id: str) -> Dict[str, str]:
        current = self.repository.get(workflow.workflow_id) or workflow
        old_status = WorkflowStatus(current.status)
        new_status = self._target_status(current)
        if new_status == old_status:
            return {"from": old_status.value, "to": new_status.value, "reason": "unchanged"}
        reason = self._reason(current, new_status)
        self.repository.transition(current, new_status, reason)
        self.store.record_workflow_event(
            current.workflow_id,
            task_id,
            f"{old_status.value}_to_{new_status.value}",
            {"reason": reason, "metrics": current.metrics.to_dict()},
        )
        return {"from": old_status.value, "to": new_status.value, "reason": reason}

    def _target_status(self, workflow: WorkflowSpec) -> WorkflowStatus:
        metrics = workflow.metrics
        status = WorkflowStatus(workflow.status)
        if (
            metrics.trial_count >= self.config.provisional_archive_trials
            and metrics.accuracy < self.config.archive_accuracy
        ):
            return WorkflowStatus.ARCHIVE
        if status == WorkflowStatus.PROVISIONAL and (
            metrics.trial_count >= self.config.provisional_promotion_trials
            and metrics.correct_count >= self.config.provisional_promotion_trials
            and metrics.evidence_accept_count >= self.config.provisional_promotion_trials
            and metrics.accuracy >= self.config.promotion_accuracy
            and metrics.evidence_rate >= self.config.promotion_accuracy
        ):
            return WorkflowStatus.ACTIVE
        if status == WorkflowStatus.ACTIVE and (
            metrics.trial_count >= self.config.active_demotion_trials
            and (
                metrics.accuracy < self.config.demotion_accuracy
                or metrics.evidence_rate < self.config.demotion_accuracy
            )
        ):
            return WorkflowStatus.PROVISIONAL
        return status

    @staticmethod
    def _reason(workflow: WorkflowSpec, status: WorkflowStatus) -> str:
        metrics = workflow.metrics
        return (
            f"quality_review:{status.value}:trials={metrics.trial_count},"
            f"accuracy={metrics.accuracy:.4f},evidence_rate={metrics.evidence_rate:.4f}"
        )
