"""受限 Python Skill 执行环境。"""

from __future__ import annotations

import ast
import inspect
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List

from nodes.mem.spatialskillgrowth.models import WorkflowSpec
from nodes.mem.spatialskillgrowth.tool_runtime import (
    ToolRuntime,
    build_evidence_text,
    extract_anomaly_result,
    extract_final_answer,
    resolve_workflow_args,
)


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}
BANNED_CALL_NAMES = {
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
    "__import__",
}
BANNED_NODES = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


class SkillScriptValidationError(ValueError):
    pass


class SkillStepExecutionError(RuntimeError):
    pass


class SkillExecutionContext:
    """Python Skill 唯一可访问的工具与轨迹接口。"""

    def __init__(
        self,
        tool_runtime: ToolRuntime,
        workflow: WorkflowSpec,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
    ):
        self._tool_runtime = tool_runtime
        self._workflow = workflow
        self._question = question
        self._image_paths = list(image_paths)
        self._slots = dict(slot_bindings)
        self._allowed_tools = {step.tool_name for step in workflow.steps}
        self._observations: List[Dict[str, Any]] = []
        self._results: Dict[str, Dict[str, Any]] = {}
        self._previous = ""

    def call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        step_id: str,
        purpose: str = "",
        depends_on: List[str] | None = None,
    ) -> Dict[str, Any]:
        if tool_name not in self._allowed_tools:
            raise SkillScriptValidationError(
                f"Python Skill called undeclared tool {tool_name!r}; "
                "add it to the JSON workflow graph before executing the script"
            )
        result = self._tool_runtime.execute(tool_name, dict(args or {}))
        self._results[step_id] = result
        self._observations.append({
            "step": len(self._observations),
            "step_id": step_id,
            "tool": tool_name,
            "parallel_group": None,
            "purpose": purpose,
            "depends_on": list(depends_on or []),
            "args": dict(args or {}),
            "result": result,
        })
        if result.get("ok"):
            self._previous = str(result.get("content") or "")
        return result

    @staticmethod
    def require(result: Dict[str, Any], step_id: str) -> None:
        if not result.get("ok"):
            raise SkillStepExecutionError(
                f"Step {step_id} failed: {result.get('error') or 'unknown tool error'}"
            )

    @staticmethod
    def value(result: Dict[str, Any], field: str, default: Any = "") -> Any:
        if field in result:
            return result[field]
        return (result.get("data") or {}).get(field, default)

    @staticmethod
    def filename(image_path: str) -> str:
        return os.path.basename(image_path) if image_path else "image"

    def evidence_text(self) -> str:
        return build_evidence_text(self._observations)

    def evidence_image(self) -> str:
        for item in reversed(self._observations):
            image = str(((item.get("result") or {}).get("data") or {}).get("image") or "")
            if image:
                return image
        return self._image_paths[0] if self._image_paths else ""

    def render(self, value: Any) -> Any:
        image_path = self._image_paths[0] if self._image_paths else ""
        return resolve_workflow_args(
            value,
            image_path=image_path,
            question=self._question,
            previous=self._previous,
            evidence=self.evidence_text(),
            step_results=self._results,
            slots=self._slots,
            evidence_image=self.evidence_image(),
        )

    @staticmethod
    def finish(value: Any) -> str:
        if isinstance(value, dict):
            value = value.get("content") or value.get("answer") or ""
        return extract_final_answer(str(value or ""))

    def result(
        self,
        answer: str,
        script_path: Path,
        error: str = "",
        script_traceback: str = "",
    ) -> Dict[str, Any]:
        failed = [
            item["step_id"]
            for item in self._observations
            if (item.get("result") or {}).get("status") != "success"
        ]
        output = {
            "success": bool(answer) and not error,
            "final_answer": str(answer or ""),
            "evidence": self._observations,
            "observations": self._observations,
            "used_tools": [item["tool"] for item in self._observations],
            "valid_step_ids": [
                item["step_id"]
                for item in self._observations
                if (item.get("result") or {}).get("status") == "success"
            ],
            "failed_step_ids": failed,
            "error": error,
            "script_path": str(script_path),
            "script_traceback": script_traceback,
            "workflow_id": self._workflow.workflow_id,
            "execution_backend": "python_skill",
        }
        output.update(extract_anomaly_result(output))
        return output


class PythonSkillExecutor:
    def __init__(self, tool_runtime: ToolRuntime):
        self.tool_runtime = tool_runtime

    def execute(
        self,
        script_path: Path,
        workflow: WorkflowSpec,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
    ) -> Dict[str, Any]:
        context = SkillExecutionContext(
            self.tool_runtime,
            workflow,
            question,
            image_paths,
            slot_bindings,
        )
        try:
            namespace = self._load(script_path)
            declared_id = str(namespace.get("WORKFLOW_ID") or "")
            if declared_id != workflow.workflow_id:
                raise SkillScriptValidationError(
                    f"Python Skill declares WORKFLOW_ID={declared_id!r}, "
                    f"expected {workflow.workflow_id!r}"
                )
            solve = namespace.get("solve")
            if not callable(solve):
                raise SkillScriptValidationError("Python Skill must define solve(...)")
            parameters = inspect.signature(solve).parameters
            call_args: Dict[str, Any] = {
                "runtime": context,
                "question": question,
                "image_paths": image_paths,
            }
            for name in parameters:
                if name in call_args:
                    continue
                if name in slot_bindings:
                    call_args[name] = slot_bindings[name]
            answer = solve(**call_args)
            if isinstance(answer, dict):
                answer = answer.get("answer") or answer.get("final_answer") or ""
            return context.result(str(answer or ""), script_path)
        except Exception as exc:
            trace = traceback.format_exc()
            return context.result(
                "",
                script_path,
                error=f"{type(exc).__name__}: {exc}",
                script_traceback=trace,
            )

    @staticmethod
    def _load(script_path: Path) -> Dict[str, Any]:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(script_path))
        _validate_tree(tree, script_path)
        namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
        exec(compile(tree, str(script_path), "exec"), namespace, namespace)
        return namespace


def _validate_tree(tree: ast.AST, script_path: Path) -> None:
    for node in ast.walk(tree):
        location = f"{script_path}:{getattr(node, 'lineno', 1)}"
        if isinstance(node, BANNED_NODES):
            raise SkillScriptValidationError(
                f"Unsupported Python construct in Skill at {location}: "
                f"{type(node).__name__}"
            )
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise SkillScriptValidationError(
                f"Private attribute access is not allowed at {location}: {node.attr}"
            )
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise SkillScriptValidationError(
                f"Private name access is not allowed at {location}: {node.id}"
            )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in BANNED_CALL_NAMES
        ):
            raise SkillScriptValidationError(
                f"Unsafe call is not allowed in Python Skill at {location}: "
                f"{node.func.id}"
            )
