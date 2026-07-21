"""受限 Python Skill 执行环境。"""

from __future__ import annotations

import ast
import inspect
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List

from nodes.mem.spatialskillgrowth.core.models import WorkflowSpec
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import (
    ToolRuntime,
    build_evidence_text,
    execute_parallel_tools,
    extract_anomaly_result,
    extract_final_answer,
    resolve_workflow_args,
)
from nodes.mem.spatialskillgrowth.runtime.tool_contracts import (
    FRAME_INDEPENDENT_IMAGE_TOOLS,
)


VIDEO_SUFFIXES = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".mpeg", ".mpg", ".webm"}

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
    """
    Python Skill 唯一可访问的工具与轨迹接口。
    在生成的 .py 脚本中，函数签名是 def solve(runtime, question, ...):
    这个类的实例就是那个 `runtime` 参数。脚本中所有对外部的调用都必须经过它。
    """

    def __init__(
        self,
        tool_runtime: ToolRuntime,
        workflow: WorkflowSpec,
        question: str,
        image_paths: List[str],
        slot_bindings: Dict[str, str],
        media_path: str = "",
    ):
        self._tool_runtime = tool_runtime
        self._workflow = workflow
        self._question = question
        self._image_paths = list(image_paths)
        self._media_path = str(media_path or "")
        # 确定当前操作的主媒体路径和选定的单张代表帧
        if not self._media_path and self._image_paths:
            self._media_path = self._image_paths[0]
        self._selected_image_path = (
            self._image_paths[len(self._image_paths) // 2]
            if self._image_paths else self._media_path
        )
        self._slots = dict(slot_bindings)
        # 从 JSON 图中提取合法的工具白名单
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
        prepared_args = dict(args or {})
        # 2. 视频帧扩散 (Fan-out) 处理
        # 如果当前输入是视频 (多帧)，且请求的工具只支持单张图片，
        # 则调用 _call_sampled_frames 将该工具并发运行在所有帧上，并选出结果最好的一帧。
        embedding_media_is_video = (
            tool_name == "embeddingTool"
            and Path(self._media_path).suffix.lower() in VIDEO_SUFFIXES
        )
        if tool_name == "embeddingTool" and not embedding_media_is_video:
            result = ToolRuntime.skipped(
                tool_name,
                "embeddingTool 只支持原始视频，禁止传入图片或抽样帧。",
            )
        elif embedding_media_is_video:
            prepared_args["file_path"] = self._media_path
            result = self._tool_runtime.execute(tool_name, prepared_args)
        elif self._should_fan_out(tool_name, prepared_args):
            result = self._call_sampled_frames(tool_name, prepared_args)
        else:
            result = self._tool_runtime.execute(tool_name, prepared_args)
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

    def _should_fan_out(self, tool_name: str, args: Dict[str, Any]) -> bool:
        if tool_name not in FRAME_INDEPENDENT_IMAGE_TOOLS:
            return False
        if len(self._image_paths) <= 1:
            return False
        input_path = next(
            (
                str(args[key])
                for key in ("file", "image", "image_path")
                if key in args
            ),
            "",
        )
        return input_path in set(self._image_paths)

    def _call_sampled_frames(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        requests = []
        for frame_path in self._image_paths:
            current = dict(args)
            for key in ("file", "image", "image_path"):
                if key in current:
                    current[key] = frame_path
            if "filename" in current:
                current["filename"] = os.path.basename(frame_path)
            requests.append((tool_name, current))
        results = execute_parallel_tools(self._tool_runtime, requests)
        successful = [
            (index, result)
            for index, result in enumerate(results)
            if result.get("ok")
        ]
        if not successful:
            failed = results[0] if results else ToolRuntime.skipped(
                tool_name, "没有可处理的抽样帧。"
            )
            failed = dict(failed)
            failed["data"] = {
                **dict(failed.get("data") or {}),
                "frame_results": _frame_result_records(
                    self._image_paths, results
                ),
                "successful_frame_count": 0,
            }
            return failed
        best_index, best = max(successful, key=_frame_result_score)
        self._selected_image_path = self._image_paths[best_index]
        aggregate = dict(best)
        aggregate["data"] = {
            **dict(best.get("data") or {}),
            "source_frame": self._selected_image_path,
            "sampled_frame_count": len(self._image_paths),
            "successful_frame_count": len(successful),
            "frame_results": _frame_result_records(
                self._image_paths, results
            ),
        }
        return aggregate

    @staticmethod
    def require(result: Dict[str, Any], step_id: str) -> None:
        """断言方法：脚本可以用它来确保某一步成功，否则立刻抛异常终止执行。"""
        if not result.get("ok"):
            raise SkillStepExecutionError(
                f"Step {step_id} failed: {result.get('error') or 'unknown tool error'}"
            )

    @staticmethod
    def value(result: Dict[str, Any], field: str, default: Any = "") -> Any:
        if field in result:
            return result[field]
        return (result.get("data") or {}).get(field, default)

    def media_path(self) -> str:
        return self._media_path

    def image_path(self) -> str:
        return self._selected_image_path

    def filename(self, image_path: str = "") -> str:
        path = image_path or self._selected_image_path
        return os.path.basename(path) if path else "image"

    def evidence_text(self) -> str:
        return build_evidence_text(self._observations)

    def evidence_image(self) -> str:
        for item in reversed(self._observations):
            image = str(((item.get("result") or {}).get("data") or {}).get("image") or "")
            if image:
                return image
        return self._selected_image_path

    def render(self, value: Any) -> Any:
        image_path = self._selected_image_path
        return resolve_workflow_args(
            value,
            image_path=image_path,
            question=self._question,
            previous=self._previous,
            evidence=self.evidence_text(),
            step_results=self._results,
            slots=self._slots,
            evidence_image=self.evidence_image(),
            media_path=self._media_path,
            frame_paths=self._image_paths,
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
        media_path: str = "",
    ) -> Dict[str, Any]:
        context = SkillExecutionContext(
            self.tool_runtime,
            workflow,
            question,
            image_paths,
            slot_bindings,
            media_path=media_path,
        )
        try:
            namespace = self._load(script_path)
            declared_id = str(namespace.get("WORKFLOW_ID") or "")
            if declared_id != workflow.workflow_id:
                raise SkillScriptValidationError(
                    f"Python Skill declares WORKFLOW_ID={declared_id!r}, "
                    f"expected {workflow.workflow_id!r}"
                )
            # 4. 获取脚本中定义的入口函数 `solve`
            solve = namespace.get("solve")
            if not callable(solve):
                raise SkillScriptValidationError("Python Skill must define solve(...)")
            # 5. 动态参数绑定：通过反射(inspect)读取 solve 函数需要哪些参数
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
        return load_skill_script(script_path)


def load_skill_script(script_path: Path) -> Dict[str, Any]:
    source = Path(script_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    _validate_tree(tree, Path(script_path))
    namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    exec(compile(tree, str(script_path), "exec"), namespace, namespace)
    return namespace


def _frame_result_score(item) -> tuple:
    index, result = item
    data = dict(result.get("data") or {})
    detections = list(data.get("detections") or [])
    confidences = []
    for detection in detections:
        if not isinstance(detection, dict):
            continue
        value = detection.get("score", detection.get("confidence", 0.0))
        try:
            confidences.append(float(value))
        except (TypeError, ValueError):
            continue
    return (
        len(detections),
        max(confidences, default=0.0),
        bool(data.get("image")),
        len(str(result.get("content") or "")),
        -index,
    )


def _frame_result_records(
    frame_paths: List[str],
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    records = []
    for frame_path, result in zip(frame_paths, results):
        data = dict(result.get("data") or {})
        detections = list(data.get("detections") or [])
        confidences = []
        for detection in detections:
            if not isinstance(detection, dict):
                continue
            value = detection.get("score", detection.get("confidence", 0.0))
            try:
                confidences.append(float(value))
            except (TypeError, ValueError):
                continue
        records.append({
            "frame_path": frame_path,
            "ok": bool(result.get("ok")),
            "status": str(result.get("status") or ""),
            "detection_count": len(detections),
            "max_confidence": max(confidences, default=0.0),
            "image": str(data.get("image") or ""),
            "error": str(result.get("error") or ""),
        })
    return records


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
