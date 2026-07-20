"""工作流 provisional/active/archive 生命周期。"""

from __future__ import annotations

from typing import Dict

from nodes.mem.spatialskillgrowth.core.experiment_config import ExperimentConfig
from nodes.mem.spatialskillgrowth.core.models import (
    MutationMode,
    WorkflowSpec,
    WorkflowStatus,
)
from nodes.mem.spatialskillgrowth.storage.growth_store import (
    ExperimentStore,
    WorkflowRepository,
)


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
        """
        【初始注册】
        当一个工作流刚被创建出来时（比如刚从大模型的回答中提取出来，或者刚变异生成），调用此方法。
        """
        # 判断是否允许直接转正：
        # 条件：配置文件允许 one_shot_activation + 它是纯提取出来的（不是变异出来的）+ 它的证据验证完全通过
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
        """
        【定期考核】
        每次这个工作流被运行了一次、并且更新了 metrics (KPI) 之后，都会调用 review。
        """
        current = self.repository.get(workflow.workflow_id) or workflow
        old_status = WorkflowStatus(current.status)
        new_status = self._target_status(current)
        if new_status == old_status:
            return {"from": old_status.value, "to": new_status.value, "reason": "unchanged"}
        reason = self._reason(current, new_status)
        # 如果状态变了（比如触发了晋升），生成改变的原因
        self.repository.transition(current, new_status, reason)
        self.store.record_workflow_event(
            current.workflow_id,
            task_id,
            f"{old_status.value}_to_{new_status.value}",
            {"reason": reason, "metrics": current.metrics.to_dict()},
        )
        return {"from": old_status.value, "to": new_status.value, "reason": reason}

    def _target_status(self, workflow: WorkflowSpec) -> WorkflowStatus:
        """
        【状态机核心规则引擎】
        严格根据 config 中的阈值，判断当前 workflow 的数据是否达标。
        """
        metrics = workflow.metrics
        status = WorkflowStatus(workflow.status)
        # 规则 1：【淘汰机制】
        # 如果尝试的次数已经达到了规定的上限 (provisional_archive_trials)，
        # 且历史准确率 (accuracy) 依然低于淘汰及格线 (archive_accuracy)，则直接淘汰 (ARCHIVE)。
        if (
            metrics.trial_count >= self.config.provisional_archive_trials
            and metrics.accuracy < self.config.archive_accuracy
        ):
            return WorkflowStatus.ARCHIVE
        # 规则 2：【晋升机制】
        # 如果当前是 PROVISIONAL，想要晋升必须满足“全能条件”：
        # - 尝试次数达标
        # - 做对的次数达标
        # - 证据链被接受的次数达标
        # - 整体准确率 和 证据率 都高于晋升线 (promotion_accuracy)
        if status == WorkflowStatus.PROVISIONAL and (
            metrics.trial_count >= self.config.provisional_promotion_trials
            and metrics.correct_count >= self.config.provisional_promotion_trials
            and metrics.evidence_accept_count >= self.config.provisional_promotion_trials
            and metrics.accuracy >= self.config.promotion_accuracy
            and metrics.evidence_rate >= self.config.promotion_accuracy
        ):
            return WorkflowStatus.ACTIVE
        # 规则 3：【降级机制】
        # 如果已经是 ACTIVE 状态，但在后续的使用中表现拉胯：
        # - 运行次数达到一定量，且准确率或证据率跌破了降级底线 (demotion_accuracy)
        # 则被打回 PROVISIONAL，重新接受考验。
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
