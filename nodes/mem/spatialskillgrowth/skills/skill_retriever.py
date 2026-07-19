"""按异常类别和已验证历史检索工作流。"""

from nodes.mem.spatialskillgrowth.core.models import RetrievalDecision


class WorkflowRetriever:
    """类别由输入给定，因此不再使用 LLM 对候选工作流二次分类。"""

    def __init__(self, repository, top_k=3, include_provisional=False):
        self.repository = repository
        self.top_k = max(1, int(top_k))
        self.include_provisional = include_provisional

    def retrieve(
        self,
        event_type,
        question,
        image_paths,
        slot_bindings,
        allowed_tool_names,
    ):
        candidates = []
        workflows = self.repository.list_retrievable(
            event_type,
            include_provisional=self.include_provisional,
        )
        for workflow in workflows:
            if workflow_structurally_eligible(
                workflow,
                slot_bindings,
                allowed_tool_names,
            ):
                candidates.append(workflow)

        candidates.sort(key=_history_sort_key)
        ranked = candidates[: self.top_k]
        ranked_ids = []
        for workflow in ranked:
            ranked_ids.append(workflow.workflow_id)
        reason = "按同类别工作流的准确率、证据通过率和调用成本排序。"
        if not ranked:
            reason = "当前类别没有结构契约合格的工作流。"
        decision = RetrievalDecision(
            strategy="validated_history",
            ranked_workflow_ids=ranked_ids,
            rejected=not bool(ranked),
            reason=reason,
        )
        return ranked, decision


def workflow_structurally_eligible(
    workflow,
    slot_bindings,
    allowed_tool_names,
):
    # 结构契约检查：确保工作流的 slots 和 tools 符合要求
    applicability = workflow.applicability
    for slot_name in applicability.required_slots:
        if not str(slot_bindings.get(slot_name) or "").strip():
            return False

    allowed_tools = set(allowed_tool_names)
    required_tools = set(applicability.required_tools)
    graph_tools = set()
    for step in workflow.steps:
        graph_tools.add(step.tool_name)
    if "embeddingTool" not in graph_tools:
        return False
    if not required_tools.issubset(allowed_tools):
        return False
    if not graph_tools.issubset(allowed_tools):
        return False
    return True


def build_retriever(repository, top_k=3):
    return WorkflowRetriever(repository, top_k)


def _history_sort_key(workflow):
    metrics = workflow.metrics
    return (
        -metrics.accuracy,
        -metrics.evidence_rate,
        metrics.average_cost,
        -metrics.trial_count,
        workflow.workflow_id,
    )
