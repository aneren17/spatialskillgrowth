"""把结构化执行轨迹渲染为便于审阅的对话式 Markdown。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


TRIAL_FILE_PREFIXES = ("parent_", "mutant_", "validation_", "inference_")


def write_conversation_trace(
    trajectory_root: Path,
    state_task_id: str,
    summary: Dict[str, Any],
) -> Path:
    task_root = Path(trajectory_root) / state_task_id
    task_root.mkdir(parents=True, exist_ok=True)
    trials = _load_trials(task_root)
    retrieval = _load_json(
        Path(trajectory_root).parent
        / "retrieval_rankings"
        / f"{state_task_id}.json"
    )
    markdown = _render(summary, retrieval, trials)
    output_path = task_root / "conversation.md"
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def _load_trials(task_root: Path) -> List[Dict[str, Any]]:
    trials = []
    for path in sorted(task_root.glob("*.json")):
        if not path.stem.startswith(TRIAL_FILE_PREFIXES):
            continue
        payload = _load_json(path)
        if payload:
            payload["_file"] = path.name
            trials.append(payload)
    return trials


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _render(
    summary: Dict[str, Any],
    retrieval: Dict[str, Any],
    trials: List[Dict[str, Any]],
) -> str:
    media = dict(summary.get("media_metadata") or {})
    accepted = summary.get("accepted")
    if accepted is None:
        accepted = any(
            bool((trial.get("evidence") or {}).get("accepted"))
            and str(trial.get("answer") or "") == str(summary.get("answer") or "")
            for trial in trials
        )
    lines = [
        "# 对话式执行轨迹",
        "",
        "> 该文件展示可审计的输入、路由、工具调用、工具返回和验收结论，"
        "不包含或伪造模型隐藏思维过程。",
        "",
        "## 用户",
        "",
        str(
            summary.get("question")
            or _question_from_trials(trials)
            or _reconstructed_question(summary)
        ),
        "",
        f"- 任务 ID：`{summary.get('task_id', '')}`",
        f"- 异常类别：`{summary.get('event_type') or summary.get('problem_class', '')}`",
        f"- 输入类型：`{summary.get('media_type', '')}`",
        f"- 原始媒体：`{media.get('source', '')}`",
        f"- 真实答案：`{summary.get('groundtruth') or '未提供'}`",
        "",
        "## 助手 · 任务规划",
        "",
        f"- problem class：`{summary.get('problem_class', '')}`",
        f"- 允许工具：{_code_list((summary.get('tool_plan') or {}).get('selected_tools', []))}",
        f"- 抽样帧数：{len(summary.get('sampled_frame_paths') or [])}",
        "",
        "## 助手 · Skill 检索",
        "",
        f"- 策略：`{retrieval.get('strategy', '')}`",
        f"- 排序结果：{_code_list(retrieval.get('ranked_workflow_ids') or [])}",
        f"- 是否拒绝全部：`{bool(retrieval.get('rejected'))}`",
        f"- 原因：{retrieval.get('reason') or '未记录'}",
        "",
    ]
    for trial_index, trial in enumerate(trials, start=1):
        result = dict(trial.get("result") or {})
        lines.extend([
            f"## 候选尝试 {trial_index} · `{trial.get('trial_id') or trial.get('_file', '')}`",
            "",
            f"- workflow：`{trial.get('workflow_id', '')}`",
            f"- mutation mode：`{trial.get('mutation_mode', '')}`",
            "",
        ])
        observations = result.get("observations") or result.get("evidence") or []
        for call_index, observation in enumerate(observations, start=1):
            tool_name = str(observation.get("tool") or "未知工具")
            tool_result = dict(observation.get("result") or {})
            lines.extend([
                f"### 助手 → {tool_name} · 调用 {call_index}",
                "",
                "```json",
                _json(observation.get("args") or {}),
                "```",
                "",
                f"### {tool_name} → 助手 · 返回 {call_index}",
                "",
                "```json",
                _json(_compact_tool_result(tool_result)),
                "```",
                "",
            ])
        evidence = dict(trial.get("evidence") or {})
        trial_correct = (
            bool(trial.get("correct"))
            if str(summary.get("groundtruth") or "").strip()
            else "未评估"
        )
        lines.extend([
            "### 助手 · 证据验收",
            "",
            f"- accepted：`{bool(evidence.get('accepted'))}`",
            f"- validator：`{evidence.get('validator', '')}`",
            f"- reason：{evidence.get('reason') or '未记录'}",
            f"- candidate answer：`{trial.get('answer', '')}`",
            f"- ground-truth correct：`{trial_correct}`",
            "",
        ])
    lines.extend([
        "## 助手 · Skill 生命周期",
        "",
        f"- 本任务激活：{_code_list(summary.get('activated_workflow_ids') or [])}",
        f"- 本任务 provisional：{_code_list(summary.get('provisional_workflow_ids') or [])}",
        f"- 选中 workflow：`{summary.get('selected_workflow_id') or summary.get('base_workflow_id', '')}`",
        "",
        "## 助手 · 最终回答",
        "",
        f"- answer：`{summary.get('answer', '')}`",
        f"- is_anomaly：`{summary.get('is_anomaly')}`",
        f"- threshold：`{summary.get('threshold')}`",
        f"- accepted：`{accepted}`",
        f"- correct：`{summary.get('correct')}`",
        "",
    ])
    return "\n".join(lines)


def _question_from_trials(trials: List[Dict[str, Any]]) -> str:
    for trial in trials:
        result = dict(trial.get("result") or {})
        trajectory = result.get("trajectory") or []
        for message in trajectory:
            if str(message.get("role") or "") in {"human", "user"}:
                return str(message.get("content") or "")
    return ""


def _reconstructed_question(summary: Dict[str, Any]) -> str:
    media_name = "视频" if summary.get("media_type") == "video" else "图像"
    event_name = summary.get("event_name") or summary.get("problem_class") or "指定"
    event_type = summary.get("event_type") or summary.get("problem_class") or ""
    return (
        f"请检测输入{media_name}中是否发生“{event_name}”异常事件。"
        f"精确 event_type 为 `{event_type}`。"
    )


def _compact_tool_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": result.get("ok"),
        "status": result.get("status"),
        "content": result.get("content", ""),
        "data": result.get("data") or {},
        "error": result.get("error", ""),
    }


def _code_list(values) -> str:
    items = [f"`{value}`" for value in values]
    return "、".join(items) if items else "无"


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)
