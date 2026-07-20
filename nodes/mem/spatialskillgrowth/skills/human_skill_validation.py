"""人工 SpatialSkillGrowth Skill 的结构、脚本契约和 mock 执行验证。"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from nodes.mem.spatialskillgrowth.core.models import (
    ApplicabilitySpec,
    WorkflowMetrics,
    WorkflowSpec,
    WorkflowStep,
)
from nodes.mem.spatialskillgrowth.runtime.python_skill_runtime import (
    PythonSkillExecutor,
    load_skill_script,
)
from nodes.mem.spatialskillgrowth.runtime.tool_runtime import (
    ToolRuntime,
    normalize_workflow_steps,
)
from nodes.mem.spatialskillgrowth.runtime.tool_contracts import TOOL_CONTRACTS
from nodes.mem.spatialskillgrowth.skills.skill_layout import (
    skill_metadata_path,
    standard_skill_name,
    workflow_reference_directory,
)


REQUIRED_SCRIPT_PARAMETERS = ("runtime", "question", "image_paths")
ALLOWED_SKILL_ENTRIES = {"SKILL.md", "scripts", "references"}
MOCK_MEDIA_PATH = "mock-input.mp4"
MOCK_IMAGE_PATHS = [
    "mock-frame-001.jpg",
    "mock-frame-002.jpg",
]


def validate_human_skill(
    skill_dir: Path,
    script_path: Path,
) -> Dict[str, Any]:
    skill_dir = Path(skill_dir).resolve()
    script_path = Path(script_path).resolve()
    errors = []
    checks = {}
    frontmatter = _validate_skill_directory(skill_dir, errors)
    checks["standard_skill_layout"] = not errors
    namespace = {}
    workflow = None
    declared_tools: Tuple[str, ...] = ()
    if not script_path.is_file():
        errors.append(f"脚本不存在：{script_path}")
    else:
        try:
            namespace = load_skill_script(script_path)
            checks["safe_python_ast"] = True
        except Exception as exc:
            errors.append(f"脚本 AST/加载失败：{type(exc).__name__}: {exc}")
            checks["safe_python_ast"] = False
    if namespace:
        workflow, declared_tools = _validate_script_contract(
            skill_dir,
            script_path,
            namespace,
            frontmatter,
            errors,
        )
    checks["script_contract"] = workflow is not None and not errors
    execution = {}
    if workflow is not None and not errors:
        execution = _execute_mock_validation(
            workflow,
            script_path,
            declared_tools,
        )
        if not execution.get("success"):
            errors.append(
                "mock 执行失败："
                + str(execution.get("error") or "没有产生最终答案")
            )
        elif execution.get("final_answer") not in {"是", "否"}:
            errors.append(
                "mock 执行必须返回“是”或“否”，实际返回："
                + repr(execution.get("final_answer"))
            )
    checks["mock_execution"] = (
        bool(execution.get("success"))
        and execution.get("final_answer") in {"是", "否"}
    )
    return {
        "valid": not errors,
        "skill_dir": str(skill_dir),
        "script_path": str(script_path),
        "workflow_id": workflow.workflow_id if workflow else "",
        "problem_class": (
            workflow.applicability.problem_class if workflow else ""
        ),
        "declared_tools": list(declared_tools),
        "checks": checks,
        "execution": execution,
        "errors": errors,
    }


def _validate_skill_directory(
    skill_dir: Path,
    errors: List[str],
) -> Dict[str, str]:
    if not skill_dir.is_dir():
        errors.append(f"Skill 目录不存在：{skill_dir}")
        return {}
    unexpected = sorted(
        path.name for path in skill_dir.iterdir()
        if path.name not in ALLOWED_SKILL_ENTRIES
    )
    if unexpected:
        errors.append(
            "Skill 根目录只允许 SKILL.md、scripts、references；发现："
            + "、".join(unexpected)
        )
    for name in ("SKILL.md", "scripts", "references"):
        path = skill_dir / name
        if not path.exists():
            errors.append(f"缺少必需的标准路径：{path}")
    if not skill_metadata_path(skill_dir).is_file():
        errors.append("缺少 references/skill.json。")
    if not workflow_reference_directory(skill_dir).is_dir():
        errors.append("缺少 references/workflows/。")
    frontmatter = _parse_frontmatter(skill_dir / "SKILL.md", errors)
    name = str(frontmatter.get("name") or "")
    if name and name != skill_dir.name:
        errors.append(
            f"SKILL.md name={name!r} 必须与目录名 {skill_dir.name!r} 一致。"
        )
    if name:
        try:
            if standard_skill_name(name) != name:
                errors.append(f"Skill 名称不是标准小写连字符格式：{name}")
        except ValueError as exc:
            errors.append(str(exc))
    return frontmatter


def _parse_frontmatter(path: Path, errors: List[str]) -> Dict[str, str]:
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append("SKILL.md 必须以 YAML frontmatter 的 `---` 开始。")
        return {}
    try:
        end = next(
            index for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration:
        errors.append("SKILL.md frontmatter 缺少结束 `---`。")
        return {}
    values = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"无法解析 frontmatter 行：{line}")
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        try:
            value = json.loads(raw) if raw.startswith(('"', "'")) else raw
        except json.JSONDecodeError:
            value = raw.strip("\"'")
        values[key] = str(value)
    if set(values) != {"name", "description"}:
        errors.append("SKILL.md frontmatter 只能且必须包含 name、description。")
    if not values.get("description", "").strip():
        errors.append("SKILL.md description 不能为空。")
    return values


def _validate_script_contract(
    skill_dir: Path,
    script_path: Path,
    namespace: Dict[str, Any],
    frontmatter: Dict[str, str],
    errors: List[str],
) -> tuple[WorkflowSpec | None, Tuple[str, ...]]:
    workflow_id = str(namespace.get("WORKFLOW_ID") or "")
    problem_class = str(namespace.get("PROBLEM_CLASS") or "")
    declared_tools = tuple(
        str(item) for item in (namespace.get("DECLARED_TOOLS") or ())
        if str(item)
    )
    if not workflow_id:
        errors.append("脚本必须声明 WORKFLOW_ID。")
    if workflow_id and script_path.stem != workflow_id:
        errors.append("脚本文件名必须等于 WORKFLOW_ID，例如 <WORKFLOW_ID>.py。")
    if not problem_class:
        errors.append("脚本必须声明 PROBLEM_CLASS。")
    if problem_class and standard_skill_name(problem_class) != skill_dir.name:
        errors.append("PROBLEM_CLASS 与 Skill 目录不匹配。")
    if not declared_tools:
        errors.append("脚本必须声明非空 DECLARED_TOOLS。")
    unknown_tools = sorted(set(declared_tools).difference(TOOL_CONTRACTS))
    if unknown_tools:
        errors.append(
            "DECLARED_TOOLS 包含未注册工具："
            + "、".join(unknown_tools)
        )
    solve = namespace.get("solve")
    if not callable(solve):
        errors.append("脚本必须定义 solve(runtime, question, image_paths, ...) 函数。")
    else:
        parameters = tuple(inspect.signature(solve).parameters)
        if parameters[:3] != REQUIRED_SCRIPT_PARAMETERS:
            errors.append(
                "solve 的前三个参数必须依次为 runtime、question、image_paths。"
            )
    contract = namespace.get("WORKFLOW_CONTRACT")
    workflow = None
    if isinstance(contract, dict):
        workflow = _workflow_from_contract(contract)
    else:
        errors.append("人工脚本必须声明 WORKFLOW_CONTRACT。")
    if workflow is None:
        return None, declared_tools
    if workflow.workflow_id != workflow_id:
        errors.append("WORKFLOW_CONTRACT 中的 workflow_id 与 WORKFLOW_ID 不一致。")
    if workflow.applicability.problem_class != problem_class:
        errors.append("工作流契约中的 problem_class 与 PROBLEM_CLASS 不一致。")
    graph_tools = tuple(dict.fromkeys(
        step.tool_name for step in workflow.steps
    ))
    if set(graph_tools) != set(declared_tools):
        errors.append("DECLARED_TOOLS 必须与工作流契约中的工具集合完全一致。")
    if set(workflow.applicability.required_tools) != set(declared_tools):
        errors.append("工作流 required_tools 必须与 DECLARED_TOOLS 完全一致。")
    calls = _runtime_calls(script_path)
    called_tools = {item[0] for item in calls}
    called_step_ids = {item[1] for item in calls}
    contract_step_ids = {step.step_id for step in normalize_workflow_steps(
        workflow.steps
    )}
    if called_tools != set(declared_tools):
        errors.append("脚本 runtime.call 工具集合与 DECLARED_TOOLS 不一致。")
    if called_step_ids != contract_step_ids:
        errors.append("脚本 runtime.call 的 step_id 与工作流契约不一致。")
    if frontmatter.get("name") != standard_skill_name(problem_class):
        errors.append("SKILL.md name 与脚本 PROBLEM_CLASS 不一致。")
    required_slots = set(workflow.applicability.required_slots)
    if solve:
        solve_parameters = inspect.signature(solve).parameters
        missing_slots = required_slots.difference(solve_parameters)
        if missing_slots:
            errors.append(
                "solve 缺少工作流必需槽位参数："
                + "、".join(sorted(missing_slots))
            )
    return workflow, declared_tools


def _workflow_from_contract(contract: Dict[str, Any]) -> WorkflowSpec:
    problem_class = str(contract.get("problem_class") or "")
    steps = [
        WorkflowStep.from_dict(item)
        for item in contract.get("steps", [])
        if isinstance(item, dict)
    ]
    steps = normalize_workflow_steps(steps)
    metrics = WorkflowMetrics(
        structural_coverage=float(
            len({step.tool_name for step in steps})
            + sum(len(step.depends_on) for step in steps)
        )
    )
    return WorkflowSpec(
        workflow_id=str(contract.get("workflow_id") or ""),
        name=str(contract.get("name") or "manual_workflow"),
        applicability=ApplicabilitySpec(
            problem_class=problem_class,
            required_slots=list(contract.get("required_slots") or []),
            required_tools=list(contract.get("required_tools") or []),
            description=str(contract.get("description") or ""),
            exclusions=str(contract.get("exclusions") or ""),
            capability_boundary=str(
                contract.get("capability_boundary") or ""
            ),
        ),
        steps=steps,
        status="active",
        mutation_mode="manual",
        metrics=metrics,
    )


def _runtime_calls(script_path: Path) -> List[Tuple[str, str]]:
    tree = ast.parse(
        script_path.read_text(encoding="utf-8"),
        filename=str(script_path),
    )
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "runtime"
            and function.attr == "call"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            continue
        step_id = ""
        for keyword in node.keywords:
            if keyword.arg == "step_id" and isinstance(keyword.value, ast.Constant):
                step_id = str(keyword.value.value)
        calls.append((str(node.args[0].value), step_id))
    return calls


def _execute_mock_validation(
    workflow: WorkflowSpec,
    script_path: Path,
    declared_tools: Tuple[str, ...],
) -> Dict[str, Any]:
    runtime = ToolRuntime(
        _mock_registry(declared_tools, MOCK_IMAGE_PATHS[0])
    )
    question = (
        "请判断输入视频中是否发生异常事件："
        + workflow.applicability.problem_class
        + "。最终回答“是”或“否”。"
    )
    return PythonSkillExecutor(runtime).execute(
        script_path,
        workflow,
        question,
        MOCK_IMAGE_PATHS,
        {"event_type": workflow.applicability.problem_class},
        media_path=MOCK_MEDIA_PATH,
    )


class _MockTool:
    def __init__(self, name: str, output):
        self.name = name
        self.output = output

    def invoke(self, args):
        return self.output(args) if callable(self.output) else self.output


def _mock_registry(
    declared_tools: Tuple[str, ...],
    image_path: str,
) -> Dict[str, _MockTool]:
    detections = json.dumps({
        "status": "success",
        "file": image_path,
        "detections": [{
            "class_name": "banner",
            "bbox": [0.1, 0.1, 0.9, 0.9],
            "score": 0.9,
        }],
    }, ensure_ascii=False)
    outputs = {
        "embeddingTool": "是 (判定阈值: 0.66)",
        "MLLM": "是",
        "paddleOcrTool": "示例横幅文字",
        "yoloTool": detections,
        "groundingdino": detections,
        "sam3": detections,
        "paddleHeadDetTool": detections,
        "paddlePedriderDetTool": detections,
        "crop_detections": json.dumps({
            "status": "success",
            "files": [image_path, "mock-crop-002.jpg"],
        }, ensure_ascii=False),
        "picRelativeCut": json.dumps({
            "status": "success", "file": image_path
        }, ensure_ascii=False),
        "unidepth": detections,
        "python_code_sandbox": "是",
    }
    return {
        name: _MockTool(name, outputs.get(name, "是"))
        for name in declared_tools
    }
