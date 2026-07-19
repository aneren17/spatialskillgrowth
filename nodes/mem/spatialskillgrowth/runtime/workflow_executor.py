"""JSON 工作流执行、候选回退和可选 Python 导出。"""

from __future__ import annotations

import json
import hashlib
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from nodes.mem.spatialskillgrowth.core.llm_utils import invoke_json, parse_json
from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec
from nodes.mem.spatialskillgrowth.growth.workflow_mutator import (
    build_anomaly_baseline_workflow,
)
from nodes.mem.spatialskillgrowth.growth.workflow_slots import (
    python_slot_parameters,
)
from nodes.mem.spatialskillgrowth.runtime.python_skill_runtime import (
    PythonSkillExecutor,
)
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import (
    SLOT_REFERENCE_PATTERN,
    STEP_REFERENCE_PATTERN,
    ToolRuntime,
    extract_anomaly_result,
    normalize_workflow_steps,
)
from prompt.spatialskillgrowth_prompts import (
    FINAL_ANSWER_NORMALIZATION_PROMPT,
    FREE_REACT_SYSTEM_PROMPT,
    REACT_FINALIZATION_PROMPT,
    REACT_ATTACHMENT_PROMPT,
    REACT_VIDEO_ATTACHMENT_PROMPT,
    WORKFLOW_REJECTION_CONTEXT_PROMPT,
)


class FinalAnswerNormalizer:
    """把 ReAct 的最终文本收口为“是”或“否”。"""

    def __init__(self, llm):
        self.llm = llm

    def normalize(self, raw_answer: str, question: str) -> str:
        raw = str(raw_answer or "").strip()
        if not raw:
            return ""
        try:
            parsed = parse_json(raw)
            answer = str(parsed.get("answer") or "").strip()
            if answer:
                return answer
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        if raw.lower() in {"是", "yes", "true"}:
            return "是"
        if raw.lower() in {"否", "no", "false"}:
            return "否"
        prompt = FINAL_ANSWER_NORMALIZATION_PROMPT.format(
            answer_type="bool",
            question=question,
            raw_answer=raw[-6000:],
        )
        try:
            parsed = invoke_json(self.llm, prompt, [])
            return str(parsed.get("answer") or "").strip() or raw
        except Exception:
            return raw


class WorkflowExecutor:
    """直接执行可读 Python Skill；JSON 只提供检索与工具许可契约。"""

    def __init__(
        self,
        runtime: ToolRuntime,
        repository=None,
        candidate_script_root: Path | None = None,
    ):
        self.runtime = runtime
        self.repository = repository
        self.candidate_script_root = candidate_script_root or (
            Path(tempfile.gettempdir()) / "spatialskillgrowth_python_candidates"
        )
        self.python_executor = PythonSkillExecutor(runtime)

    def execute(
        self,
        workflow: WorkflowSpec,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        media_path: str = "",
    ) -> Dict:
        started = time.perf_counter()
        # 1. 尝试从已有仓库中读取编译好的 Python 脚本路径
        script_path = (
            self.repository.script_path(workflow.workflow_id)
            if self.repository is not None
            else None
        )
        
        # 2. 如果本地不存在该脚本，则触发动态生成（代码生成机制）
        if script_path is None or not script_path.is_file():
            script_path = WorkflowPythonExporter(
                self.candidate_script_root
            ).export(workflow, force=True)
            
        # 3. 调用底层的 Python 运行时执行该 .py 脚本，并传入动态变量 (运行时上下文)
        result = self.python_executor.execute(
            script_path,
            workflow,
            question,
            image_paths,
            slot_bindings,
            media_path=media_path,
        )
        result["latency_ms"] = (time.perf_counter() - started) * 1000.0
        return result


class ReactSolver:
    def __init__(self, llm, runtime: ToolRuntime, max_steps: int = 8):
        self.llm = llm
        self.runtime = runtime
        self.max_steps = max(1, int(max_steps))

    def solve(
        self,
        task_id: str,
        question: str,
        image_paths: List[str],
        allowed_tool_names: Iterable[str],
        repair_context: str = "",
        media_path: str = "",
    ) -> Dict:
        started = time.perf_counter()
        task_text = question
        if media_path and image_paths and media_path not in image_paths:
            task_text += REACT_VIDEO_ATTACHMENT_PROMPT.format(
                media_path=media_path,
                frame_paths="\n".join(image_paths),
            )
        elif image_paths:
            task_text += REACT_ATTACHMENT_PROMPT.format(paths="\n".join(image_paths))
        messages = [
            SystemMessage(content=FREE_REACT_SYSTEM_PROMPT),
            HumanMessage(content=task_text),
        ]
        if repair_context:
            messages.append(HumanMessage(content=repair_context))
        allowed = set(allowed_tool_names)
        tools = [
            tool for name, tool in self.runtime.registry.items()
            if name in allowed
        ] or list(self.runtime.registry.values())
        bound = self.llm.bind_tools(tools)
        observations = []
        answer = ""
        raw_answer = ""
        error = ""
        for _ in range(self.max_steps):
            try:
                response = bound.invoke(messages)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                break
            messages.append(response)
            calls = getattr(response, "tool_calls", None) or []
            if not calls:
                raw_answer = str(getattr(response, "content", response) or "").strip()
                answer = FinalAnswerNormalizer(self.llm).normalize(
                    raw_answer, question
                )
                break
            for call in calls:
                tool_name = str(call.get("name") or "")
                tool_args = dict(call.get("args") or {})
                result = self.runtime.execute(tool_name, tool_args)
                index = len(observations)
                observations.append({
                    "step": index,
                    "step_id": f"react_{index}",
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result,
                })
                messages.append(ToolMessage(
                    content=result["content"] if result["ok"] else result["error"],
                    tool_call_id=str(call.get("id") or f"{tool_name}_{index}"),
                    name=tool_name,
                ))
        if not answer:
            messages.append(HumanMessage(content=REACT_FINALIZATION_PROMPT))
            try:
                response = self.llm.invoke(messages)
                messages.append(response)
                raw_answer = str(
                    getattr(response, "content", response) or ""
                ).strip()
                answer = FinalAnswerNormalizer(self.llm).normalize(
                    raw_answer, question
                )
                if answer:
                    error = ""
            except Exception as exc:
                if not error:
                    error = f"Finalization failed: {type(exc).__name__}: {exc}"
        output = {
            "success": bool(answer) and not error,
            "final_answer": answer,
            "raw_final_answer": raw_answer if answer else "",
            "react_answer": True,
            "observations": observations,
            "used_tools": [item["tool"] for item in observations],
            "trajectory": _serialize_messages(messages),
            "failed_step_ids": [
                item["step_id"]
                for item in observations
                if not (item.get("result") or {}).get("ok")
            ],
            "error": error or ("" if answer else "ReAct produced no final answer"),
            "latency_ms": (time.perf_counter() - started) * 1000.0,
        }
        output.update(extract_anomaly_result(output))
        return output


class CandidateExecutionCoordinator:
    """依次尝试最多三个检索工作流，全部拒绝后才进入 ReAct。"""

    def __init__(
        self,
        workflow_executor: WorkflowExecutor,
        react_solver: ReactSolver,
        evidence_validator,
        use_react: bool = True,
        max_workflow_attempts: int = 3,
    ):
        self.workflow_executor = workflow_executor
        self.react_solver = react_solver
        self.evidence_validator = evidence_validator
        self.use_react = use_react
        self.max_workflow_attempts = max(1, min(3, max_workflow_attempts))

    def run(
        self,
        task_id: str,
        problem_class: str,
        question: str,
        image_paths: List[str],
        workflows: List[WorkflowSpec],
        slot_bindings: Dict[str, str],
        allowed_tool_names: List[str],
        media_path: str = "",
    ) -> Dict:
        attempts = []
        repair_contexts = []
         # 1. 尝试执行检索命中的历史工作流 (Top-K)
        for workflow in workflows[: self.max_workflow_attempts]:
            result = _execute_workflow_with_media(
                # execute 
                self.workflow_executor,
                workflow,
                question,
                image_paths,
                slot_bindings,
                media_path,
            )
            answer = str(result.get("final_answer") or "").strip()
            evidence = self.evidence_validator.validate(
                problem_class,
                question,
                answer,
                result,
                _validation_paths(media_path, image_paths),
            )
            attempt = {
                "kind": "workflow",
                "workflow": workflow,
                "workflow_id": workflow.workflow_id,
                "answer": answer,
                "accepted": evidence.accepted,
                "evidence": evidence,
                "result": result,
            }
            attempts.append(attempt)
            if evidence.accepted:
                # 一旦有一个工作流成功，立刻中断并返回成功结果
                return {
                    "answer": answer,
                    "selected_workflow_id": workflow.workflow_id,
                    "fallback_react": False,
                    "accepted": True,
                    "attempts": attempts,
                    "error": "",
                    **extract_anomaly_result(result),
                }
            # 如果失败，收集该工作流的失败原因，留作 ReAct 的先验上下文    
            repair_contexts.append(
                WORKFLOW_REJECTION_CONTEXT_PROMPT.format(
                    workflow_id=workflow.workflow_id,
                    reason=evidence.reason,
                    answer=answer or "空",
                )
            )
        if "embeddingTool" not in set(allowed_tool_names):
            return {
                "answer": "",
                "selected_workflow_id": "",
                "fallback_react": False,
                "accepted": False,
                "attempts": attempts,
                "error": "异常检测任务缺少必需的 embeddingTool。",
                "event_type": problem_class,
                "is_anomaly": None,
                "decision": "",
                "threshold": None,
            }
            
        # 2. 如果存在 baseline（基线算法），作为最后一道静态兜底尝试运行
        baseline = build_anomaly_baseline_workflow(problem_class)
        attempted_ids = set()
        for attempt in attempts:
            attempted_ids.add(attempt.get("workflow_id"))
        if baseline.workflow_id not in attempted_ids:
            result = _execute_workflow_with_media(
                self.workflow_executor,
                baseline,
                question,
                image_paths,
                slot_bindings,
                media_path,
            )
            answer = str(result.get("final_answer") or "").strip()
            evidence = self.evidence_validator.validate(
                problem_class,
                question,
                answer,
                result,
                _validation_paths(media_path, image_paths),
            )
            attempts.append({
                "kind": "embedding_baseline",
                "workflow": baseline,
                "workflow_id": baseline.workflow_id,
                "answer": answer,
                "accepted": evidence.accepted,
                "evidence": evidence,
                "result": result,
            })
            if evidence.accepted:
                return {
                    "answer": answer,
                    "selected_workflow_id": baseline.workflow_id,
                    "fallback_react": False,
                    "accepted": True,
                    "attempts": attempts,
                    "error": "",
                    **extract_anomaly_result(result),
                }
            repair_contexts.append(
                WORKFLOW_REJECTION_CONTEXT_PROMPT.format(
                    workflow_id=baseline.workflow_id,
                    reason=evidence.reason,
                    answer=answer or "空",
                )
            )
        
        # 3. 终极回退：所有已知工作流均失败，且允许使用 ReAct
        if not self.use_react:
            last_result = attempts[-1]["result"] if attempts else {}
            return {
                "answer": attempts[-1]["answer"] if attempts else "",
                "selected_workflow_id": "",
                "fallback_react": False,
                "accepted": False,
                "attempts": attempts,
                "error": "No workflow passed evidence validation and ReAct is disabled.",
                **extract_anomaly_result(last_result),
            }
        result = self.react_solver.solve(
            task_id,
            question,
            image_paths,
            allowed_tool_names,
            repair_context="\n".join(repair_contexts)[-6000:],
            media_path=media_path,
        )
        answer = str(result.get("final_answer") or "").strip()
        evidence = self.evidence_validator.validate(
            problem_class,
            question,
            answer,
            result,
            _validation_paths(media_path, image_paths),
        )
        attempts.append({
            "kind": "react",
            "workflow_id": "",
            "answer": answer,
            "accepted": evidence.accepted,
            "evidence": evidence,
            "result": result,
        })
        return {
            "answer": answer,
            "selected_workflow_id": "",
            "fallback_react": True,
            "accepted": evidence.accepted,
            "attempts": attempts,
            "error": "" if evidence.accepted else evidence.reason or result.get("error", ""),
            **extract_anomaly_result(result),
        }


class WorkflowPythonExporter:
    """把 JSON 工具图格式化为可读、可编辑、可直接执行的 Python Skill。
    AI 生成的工作流（Workflow）是以 JSON 图（Graph）的形式存储的。但 JSON 无法直接运行，因此系统采用了“代码生成”策略。
    WorkflowExecutor 的任务是：接收 JSON 格式的工作流，如果本地没有对应的 .py 文件，
    就调用 WorkflowPythonExporter 将其编译/转化为原生的 Python 代码，然后交由底层的 PythonSkillExecutor 运行。
    """

    def __init__(self, export_root: Path):
        self.export_root = export_root

    def export(self, workflow: WorkflowSpec, force: bool = False) -> Path:
        
        self.export_root.mkdir(parents=True, exist_ok=True)
        path = self.export_root / f"{workflow.workflow_id}.py"
        if path.exists() and not force:
            return path
        slot_names = python_slot_parameters(workflow)
        slot_parameters = "".join(
            f"\n    {name}=\"\"," for name in slot_names
        )
        keyword_separator = "\n    *," if slot_names else ""
        # 1. 解析 JSON 中的所有节点 (steps)，按依赖关系排序
        steps = normalize_workflow_steps(workflow.steps)
        graph_payload = [step.to_dict() for step in steps]
        graph_hash = hashlib.sha256(
            json.dumps(graph_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        tool_names = tuple(dict.fromkeys(step.tool_name for step in steps))
        contract = _workflow_contract(workflow, steps)
        variables = {
            step.step_id: _safe_python_identifier(step.step_id)
            for step in steps
        }
        # 2. 构建 Python 脚本头部 (Import、常量定义、函数签名)
        lines = [
            f'"""Executable SpatialSkillGrowth Skill: {workflow.name or workflow.workflow_id}."""',
            "",
            f"WORKFLOW_ID = {workflow.workflow_id!r}",
            f"PROBLEM_CLASS = {workflow.applicability.problem_class!r}",
            f"WORKFLOW_GRAPH_SHA256 = {graph_hash!r}",
            f"DECLARED_TOOLS = {tool_names!r}",
            f"WORKFLOW_CONTRACT = {contract!r}",
            "",
            "",
            "def solve(",
            "    runtime,",
            "    question,",
            f"    image_paths,{keyword_separator}{slot_parameters}",
            "):",
        ]
        # 3. 将 JSON 的 Step 转化为 Python 变量与函数调用
        for step in steps:
            variable = variables[step.step_id]
            args_code = _python_value(step.args, variables)
            lines.extend([
                "",
                f"    # {step.purpose or step.tool_name}",
                f"    {variable} = runtime.call(",
                f"        {step.tool_name!r},",
                f"        {args_code},",
                f"        step_id={step.step_id!r},",
                f"        purpose={step.purpose!r},",
                f"        depends_on={list(step.depends_on)!r},",
                "    )",
                f"    runtime.require({variable}, {step.step_id!r})",
            ])
        answer_variable = next(
            (
                variables[step.step_id]
                for step in reversed(steps)
                if step.tool_name == "MLLM"
            ),
            variables[steps[-1].step_id] if steps else "\"\"",
        )
        lines.extend(["", f"    return runtime.finish({answer_variable})", ""])
        code = "\n".join(lines)
        # 4. 写入本地 .py 文件，返回文件路径供 Executor 执行
        path.write_text(code, encoding="utf-8")
        return path


def _validation_paths(media_path: str, image_paths: List[str]) -> List[str]:
    return [media_path] if media_path else image_paths


def _execute_workflow_with_media(
    executor,
    workflow: WorkflowSpec,
    question: str,
    image_paths: List[str],
    slot_bindings: Dict[str, str],
    media_path: str,
) -> Dict:
    if media_path:
        return executor.execute(
            workflow,
            question,
            image_paths,
            slot_bindings,
            media_path=media_path,
        )
    return executor.execute(workflow, question, image_paths, slot_bindings)


def _python_value(value: Any, variables: Dict[str, str]) -> str:
    if isinstance(value, dict):
        items = [
            f"{key!r}: {_python_value(item, variables)}"
            for key, item in value.items()
        ]
        return "{" + ", ".join(items) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_python_value(item, variables) for item in value) + "]"
    if not isinstance(value, str):
        return repr(value)
    exact_values = {
        "$image": "runtime.image_path()",
        "$media": "runtime.media_path()",
        "$frames": "image_paths",
        "$filename": "runtime.filename()",
        "$media_filename": "runtime.filename(runtime.media_path())",
        "$question": "question",
        "$evidence": "runtime.evidence_text()",
        "$evidence_image": "runtime.evidence_image()",
        "$previous": "runtime.render('$previous')",
        "$previous_image": "runtime.render('$previous_image')",
    }
    if value in exact_values:
        return exact_values[value]
    slot_match = SLOT_REFERENCE_PATTERN.fullmatch(value)
    if slot_match:
        return slot_match.group(1)
    step_match = STEP_REFERENCE_PATTERN.fullmatch(value)
    if step_match and step_match.group(1) in variables:
        return (
            f"runtime.value({variables[step_match.group(1)]}, "
            f"{step_match.group(2)!r})"
        )
    if "$" in value:
        return f"runtime.render({value!r})"
    return repr(value)


def _workflow_contract(
    workflow: WorkflowSpec,
    steps,
) -> Dict[str, Any]:
    applicability = workflow.applicability
    return {
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "problem_class": applicability.problem_class,
        "required_slots": list(applicability.required_slots),
        "required_tools": list(applicability.required_tools),
        "description": applicability.description,
        "exclusions": applicability.exclusions,
        "capability_boundary": applicability.capability_boundary,
        "steps": [step.to_dict() for step in steps],
    }


def _safe_python_identifier(value: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", str(value or "step"))
    if not identifier or identifier[0].isdigit():
        identifier = f"step_{identifier}"
    return f"{identifier}_result"


def _serialize_messages(messages) -> List[Dict]:
    output = []
    for message in messages:
        item = {
            "role": getattr(message, "type", ""),
            "content": getattr(message, "content", ""),
        }
        calls = getattr(message, "tool_calls", None)
        if calls:
            item["tool_calls"] = calls
        output.append(item)
    return output
