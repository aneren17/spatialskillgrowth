"""实验状态、轨迹和 JSON 工作流仓库。"""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from nodes.mem.spatialskillgrowth.core.experiment_config import ExperimentPaths
from nodes.mem.spatialskillgrowth.core.models import (
    EvidenceDecision,
    RetrievalDecision,
    WorkflowSpec,
    WorkflowStatus,
)
from nodes.mem.spatialskillgrowth.runtime.workflow_executor import (
    WorkflowPythonExporter,
)
from nodes.mem.spatialskillgrowth.skills.skill_layout import (
    skill_directory,
    skill_metadata_path,
    standard_skill_name,
    workflow_reference_directory,
)
from nodes.mem.spatialskillgrowth.storage.conversation_trace import (
    write_conversation_trace,
)

class ExperimentStore:
    """
    SQLite 实验状态记录员。
    只保存实验的客观事实（做没做完、对没对），具体的复杂 JSON 文件存在硬盘文件夹里。
    """

    def __init__(self, paths: ExperimentPaths):
        self.paths = paths
        self.db_path = paths.state_dir / "spatialskillgrowth.db"
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _init_schema(self) -> None:
        """
        【初始化表格】
        tasks表：记录所有题目的宏观状态（未开始、已完成）。
        trials表：记录每一道题工人可能尝试了多次（比如用了旧方法、用了变异方法）。
        workflow_events表：记录某个 SOP（工作流）的晋升/降级大事件。
        """
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    split_name TEXT NOT NULL DEFAULT '',
                    problem_class TEXT NOT NULL DEFAULT '',
                    question TEXT NOT NULL,
                    groundtruth TEXT NOT NULL DEFAULT '',
                    final_answer TEXT NOT NULL DEFAULT '',
                    correct INTEGER NOT NULL DEFAULT 0,
                    completed INTEGER NOT NULL DEFAULT 0,
                    summary_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS trials (
                    task_id TEXT NOT NULL,
                    trial_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL DEFAULT '',
                    mutation_mode TEXT NOT NULL DEFAULT '',
                    answer TEXT NOT NULL DEFAULT '',
                    correct INTEGER NOT NULL DEFAULT 0,
                    evidence_accepted INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT NOT NULL,
                    PRIMARY KEY(task_id, trial_id)
                );
                CREATE TABLE IF NOT EXISTS retrievals (
                    task_id TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    PRIMARY KEY(task_id, strategy)
                );
                CREATE TABLE IF NOT EXISTS mutation_directions (
                    task_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    direction_json TEXT NOT NULL,
                    PRIMARY KEY(task_id, mode)
                );
                CREATE TABLE IF NOT EXISTS workflow_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    task_id TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS atom_coverage (
                    problem_class TEXT NOT NULL,
                    atom_id TEXT NOT NULL,
                    trial_count INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(problem_class, atom_id)
                );
                """
            )

    def begin_task(
        self,
        task_id: str,
        mode: str,
        split_name: str,
        problem_class: str,
        question: str,
        groundtruth: str,
    ) -> None:
        """
        开始做 task_id
        把之前的旧尝试记录全部清空（DELETE FROM trials），准备写新的。
        """
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, mode, split_name, problem_class, question,
                    groundtruth
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    mode=excluded.mode,
                    split_name=excluded.split_name,
                    problem_class=excluded.problem_class,
                    question=excluded.question,
                    groundtruth=excluded.groundtruth,
                    final_answer='', correct=0, completed=0, summary_json='{}',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    task_id,
                    mode,
                    split_name,
                    problem_class,
                    question,
                    groundtruth,
                ),
            )
            connection.execute("DELETE FROM trials WHERE task_id=?", (task_id,))

    def is_complete(self, task_id: str) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT completed FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        return bool(row and row["completed"])

    def get_summary(self, task_id: str) -> Optional[Dict]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT summary_json FROM tasks WHERE task_id=?", (task_id,)
            ).fetchone()
        return json.loads(row["summary_json"]) if row else None

    def save_trial(
        self,
        task_id: str,
        trial_id: str,
        workflow_id: str,
        mutation_mode: str,
        answer: str,
        correct: bool,
        evidence: EvidenceDecision,
        result: Dict,
    ) -> None:
        payload = {
            "task_id": task_id,
            "trial_id": trial_id,
            "workflow_id": workflow_id,
            "mutation_mode": mutation_mode,
            "answer": answer,
            "correct": bool(correct),
            "evidence": evidence.to_dict(),
            "result": result,
        }
        self.save_trajectory(task_id, trial_id, payload)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO trials(
                    task_id, trial_id, workflow_id, mutation_mode, answer,
                    correct, evidence_accepted, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    trial_id,
                    workflow_id,
                    mutation_mode,
                    answer,
                    int(correct),
                    int(evidence.accepted),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def save_retrieval(self, task_id: str, decision: RetrievalDecision) -> None:
        payload = decision.to_dict()
        _write_json(self.paths.retrieval_root / f"{task_id}.json", payload)
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO retrievals VALUES (?, ?, ?)",
                (task_id, decision.strategy, json.dumps(payload, ensure_ascii=False)),
            )

    def save_direction(self, task_id: str, mode: str, direction: Dict) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO mutation_directions VALUES (?, ?, ?)",
                (task_id, mode, json.dumps(direction, ensure_ascii=False)),
            )

    def record_workflow_event(
        self,
        workflow_id: str,
        task_id: str,
        event_type: str,
        payload: Optional[Dict] = None,
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_events(workflow_id, task_id, event_type, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    task_id,
                    event_type,
                    json.dumps(payload or {}, ensure_ascii=False),
                ),
            )

    def atom_stats(self, problem_class: str) -> Dict[str, Dict[str, int]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT atom_id, trial_count, success_count FROM atom_coverage
                WHERE problem_class=?
                """,
                (problem_class,),
            ).fetchall()
        return {
            str(row["atom_id"]): {
                "trial_count": int(row["trial_count"]),
                "success_count": int(row["success_count"]),
            }
            for row in rows
        }

    def record_atom_results(self, problem_class: str, atom_results: Dict[str, bool]) -> None:
        with self._lock, self._connect() as connection:
            for atom_id, success in atom_results.items():
                connection.execute(
                    """
                    INSERT INTO atom_coverage(
                        problem_class, atom_id, trial_count, success_count
                    ) VALUES (?, ?, 1, ?)
                    ON CONFLICT(problem_class, atom_id) DO UPDATE SET
                        trial_count=trial_count + 1,
                        success_count=success_count + excluded.success_count
                    """,
                    (problem_class, str(atom_id), int(bool(success))),
                )

    def workflow_task_ids(self, workflow_id: str) -> List[str]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT task_id FROM trials WHERE workflow_id=?",
                (workflow_id,),
            ).fetchall()
        return [str(row["task_id"]) for row in rows]

    def complete_task(self, task_id: str, answer: str, correct: bool, summary: Dict) -> None:
        """
        这道题彻底做完了。把最终的答案（final_answer）和对错写进数据库。
        同时，把最详细的做题全过程（summary）写进硬盘里（save_trajectory），
        然后把 completed 设为 1，标志着这题不用重做了。
        """
        self.save_trajectory(task_id, "summary", summary)
        write_conversation_trace(
            self.paths.trajectory_root,
            task_id,
            summary,
        )
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks SET final_answer=?, correct=?, completed=1,
                    summary_json=?, updated_at=CURRENT_TIMESTAMP WHERE task_id=?
                """,
                (answer, int(correct), json.dumps(summary, ensure_ascii=False), task_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Cannot complete unknown task: {task_id}")
        self._append_result(summary)

    def fail_task(
        self,
        task_id: str,
        mode: str,
        split_name: str,
        problem_class: str,
        question: str,
        groundtruth: str,
        error: str,
    ) -> Dict:
        """持久化异常但保持 completed=0，使 --resume 可以重试。"""
        summary = {
            "task_id": _public_task_id(task_id),
            "state_task_id": task_id,
            "mode": mode,
            "split": split_name,
            "problem_class": problem_class,
            "groundtruth": groundtruth,
            "answer": "",
            "correct": False,
            "failed": True,
            "completed": False,
            "error": error,
        }
        self.save_trajectory(task_id, "error", summary)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, mode, split_name, problem_class, question,
                    groundtruth, completed, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    problem_class=excluded.problem_class,
                    summary_json=excluded.summary_json,
                    completed=0,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    task_id,
                    mode,
                    split_name,
                    problem_class,
                    question,
                    groundtruth,
                    json.dumps(summary, ensure_ascii=False),
                ),
            )
        path = self.paths.results_root / "errors.jsonl"
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
        return summary

    def save_trajectory(self, task_id: str, name: str, payload: Dict) -> Path:
        path = self.paths.trajectory_root / task_id / f"{name}.json"
        _write_json(path, payload)
        return path

    def _append_result(self, summary: Dict) -> None:
        path = self.paths.results_root / "per_task.jsonl"
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(summary, ensure_ascii=False) + "\n")


class WorkflowRepository:
    """
    工作流/技能 (SOP) 操作。
    JSON 用来保存大模型读得懂的结构契约，同时会自动导出成人类可读的 Python 代码。
    """

    def __init__(self, paths: ExperimentPaths):
        self.paths = paths
        self._lock = threading.RLock()

    def save(self, workflow: WorkflowSpec) -> Path:
        """
        【存档 SOP】
        把 AI 刚刚生成的工作流（Workflow）保存到硬盘。
        1. 写入 JSON 文件。
        2. 调用 WorkflowPythonExporter，把 JSON 翻译成真正的 Python 代码 (.py)。
        3. 重建技能说明书（_rebuild_docs）。
        """
        status = WorkflowStatus(workflow.status)
        root = self._root_for_status(status)
        path = (
            workflow_reference_directory(skill_directory(
                root, workflow.applicability.problem_class
            ))
            / f"{workflow.workflow_id}.json"
        )
        with self._lock:
            existing_script = self.script_path(workflow.workflow_id)
            existing_script_content = (
                existing_script.read_bytes()
                if existing_script is not None and existing_script.is_file()
                else None
            )
            self._remove_from_other_statuses(workflow, status)
            _write_json_atomic(path, workflow.to_dict())
            skill_root = path.parents[2]
            target_script = skill_root / "scripts" / f"{workflow.workflow_id}.py"
            if not target_script.exists() and existing_script_content is not None:
                target_script.parent.mkdir(parents=True, exist_ok=True)
                target_script.write_bytes(existing_script_content)
            WorkflowPythonExporter(skill_root / "scripts").export(
                workflow,
                force=False,
            )
            self._rebuild_docs(workflow.applicability.problem_class, status)
        return path

    def load(self, path: Path) -> WorkflowSpec:
        return WorkflowSpec.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def get(self, workflow_id: str) -> Optional[WorkflowSpec]:
        for root in self._status_roots().values():
            matches = list(root.glob(
                f"*/references/workflows/{workflow_id}.json"
            ))
            if matches:
                return self.load(matches[0])
        return None

    def script_path(self, workflow_id: str) -> Optional[Path]:
        for root in self._status_roots().values():
            matches = list(root.glob(f"*/scripts/{workflow_id}.py"))
            if matches:
                return matches[0]
        return None

    def snapshot_active_from(
        self,
        source: "WorkflowRepository",
        provenance: Optional[Dict] = None,
    ) -> Dict:
        """复制推理所用 active Skill，并使本地快照成为后续唯一读取源。"""
        snapshot_path = self.paths.skill_root / "SOURCE_SNAPSHOT.json"
        requested_source = str(source.paths.root.resolve())
        if snapshot_path.exists():
            existing = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if existing.get("source_root") != requested_source:
                raise RuntimeError(
                    "Inference run already contains a snapshot from another source: "
                    f"{existing.get('source_root')}"
                )
            return existing
        if self.paths.active_skill_root.exists():
            shutil.rmtree(self.paths.active_skill_root)
        shutil.copytree(
            source.paths.active_skill_root,
            self.paths.active_skill_root,
        )
        source_skillset = source.paths.skill_root / "SKILLSET.json"
        if source_skillset.is_file():
            shutil.copy2(source_skillset, self.paths.skill_root / "SKILLSET.json")
        files = []
        for path in sorted(self.paths.active_skill_root.rglob("*")):
            if not path.is_file():
                continue
            files.append({
                "path": str(path.relative_to(self.paths.skill_root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        payload = {
            "source_root": requested_source,
            "source_experiment": source.paths.experiment,
            "source_run_id": source.paths.run_id,
            "active_workflow_count": len(self.list_active()),
            "files": files,
            **dict(provenance or {}),
        }
        _write_json_atomic(snapshot_path, payload)
        return payload

    def list_active(self, problem_class: str = "") -> List[WorkflowSpec]:
        return self._list(self.paths.active_skill_root, problem_class)

    def list_provisional(self, problem_class: str = "") -> List[WorkflowSpec]:
        return self._list(self.paths.provisional_skill_root, problem_class)

    def list_archive(self, problem_class: str = "") -> List[WorkflowSpec]:
        return self._list(self.paths.archive_skill_root, problem_class)

    def list_retrievable(
        self,
        problem_class: str = "",
        include_provisional: bool = False,
    ) -> List[WorkflowSpec]:
        workflows = self.list_active(problem_class)
        if include_provisional:
            workflows.extend(self.list_provisional(problem_class))
        return workflows

    def transition(
        self,
        workflow: WorkflowSpec,
        status: WorkflowStatus,
        reason: str = "",
    ) -> WorkflowSpec:
        """
        【SOP 调岗/晋升】
        控制技能的生命周期。比如把一个 'provisional' (试用期) 的技能，
        改为 'active' (正式转正)，或者 'archive' (淘汰)。
        这个方法不仅改状态，还会把文件从一个文件夹挪到另一个文件夹（通过底层 _remove_from_other_statuses）。
        """
        previous_status = WorkflowStatus(workflow.status)
        workflow.status = status.value
        self.save(workflow)
        if reason and status == WorkflowStatus.ARCHIVE:
            metadata = workflow_reference_directory(
                skill_directory(
                    self.paths.archive_skill_root,
                    workflow.applicability.problem_class,
                )
            )
            _write_json_atomic(
                metadata / f"{workflow.workflow_id}.archive.json",
                {"workflow_id": workflow.workflow_id, "reason": reason},
            )
        if previous_status != status:
            self._rebuild_docs(workflow.applicability.problem_class, previous_status)
        return workflow

    def archive(self, workflow: WorkflowSpec, reason: str = "") -> WorkflowSpec:
        return self.transition(workflow, WorkflowStatus.ARCHIVE, reason)

    def update_metrics(
        self,
        workflow: WorkflowSpec,
        task_id: str,
        correct: bool,
        evidence_accepted: bool,
        tool_calls: int,
        tool_failures: int,
        latency_ms: float,
    ) -> WorkflowSpec:
        """
        【更新 SOP 】
        每次用了这个 SOP 去做题，不论对错，都要更新它：
        - trial_count += 1 (尝试次数加一)
        - correct_count (做对了几次)
        - total_tool_calls (用了几次基础工具，计算成本)
        这个指标直接决定了检索时（Retriever）谁排在前面！
        """
        current = self.get(workflow.workflow_id) or workflow
        metrics = current.metrics
        metrics.trial_count += 1
        #bool
        metrics.correct_count += int(correct)
        metrics.evidence_accept_count += int(evidence_accepted)
        
        metrics.total_tool_calls += max(0, int(tool_calls))
        metrics.tool_failure_count += max(0, int(tool_failures))
        metrics.total_latency_ms += max(0.0, float(latency_ms))
        if correct and task_id not in current.source_task_ids:
            current.source_task_ids.append(task_id)
        self.save(current)
        return current

    def _list(self, root: Path, problem_class: str) -> List[WorkflowSpec]:
        # 最底层的查询
        pattern = (
            f"{standard_skill_name(problem_class)}/references/workflows/*.json"
            if problem_class
            else "*/references/workflows/*.json"
        )
        paths = list(root.glob(pattern))
        workflows = []
        seen = set()
        for path in sorted(paths):
            if path.name.endswith(".archive.json"):
                continue
            workflow = self.load(path)
            if workflow.workflow_id in seen:
                continue
            seen.add(workflow.workflow_id)
            workflows.append(workflow)
        return workflows

    def _rebuild_docs(self, problem_class: str, status: WorkflowStatus) -> None:
        """
        【撰写说明书】
        每多了一个新 SOP，或者状态变了，
        它会自动在文件夹里生成/更新一个 `SKILL.md` (Markdown说明书)，
        以及一个 `skill.json` 索引
        """
        workflows = self._list(self._root_for_status(status), problem_class)
        root = self._root_for_status(status)
        directory = skill_directory(root, problem_class)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "scripts").mkdir(parents=True, exist_ok=True)
        workflow_reference_directory(directory).mkdir(parents=True, exist_ok=True)
        metadata_path = skill_metadata_path(directory)
        existing_metadata = {}
        if metadata_path.exists():
            existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        existing_workflows = {
            str(item.get("workflow_id") or ""): item
            for item in existing_metadata.get("workflows", [])
            if isinstance(item, dict)
        }
        description = str(
            existing_metadata.get("description")
            or next(
                (
                    item.applicability.description
                    for item in workflows
                    if item.applicability.description
                ),
                f"Reusable validated workflows for {problem_class}.",
            )
        )
        title = str(existing_metadata.get("title") or problem_class.replace("_", " ").title())
        skill_markdown_path = directory / "SKILL.md"
        event_type = str(existing_metadata.get("event_type") or "")
        if not skill_markdown_path.is_file():
            skill_markdown_path.write_text(
                _default_skill_markdown(
                    standard_skill_name(problem_class),
                    title,
                    description,
                    event_type,
                ),
                encoding="utf-8",
            )
        metadata = dict(existing_metadata)
        metadata.update({
            "name": standard_skill_name(problem_class),
            "title": title,
            "problem_class": problem_class,
            "description": description,
            "status": status.value,
            "workflow_count": len(workflows),
            "workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "path": f"references/workflows/{workflow.workflow_id}.json",
                    "script": f"scripts/{workflow.workflow_id}.py",
                    "authorship": str(
                        existing_workflows.get(workflow.workflow_id, {}).get(
                            "authorship"
                        )
                        or (
                            "human"
                            if workflow.mutation_mode == "manual"
                            else "generated"
                        )
                    ),
                }
                for workflow in sorted(workflows, key=lambda item: item.workflow_id)
            ],
        })
        _write_json_atomic(metadata_path, metadata)
        self._rebuild_skill_index(root)

    def _remove_from_other_statuses(
        self,
        workflow: WorkflowSpec,
        target_status: WorkflowStatus,
    ) -> None:
        problem_class = workflow.applicability.problem_class
        for status, root in self._status_roots().items():
            if status == target_status:
                continue
            directory = skill_directory(root, problem_class)
            workflow_path = (
                workflow_reference_directory(directory)
                / f"{workflow.workflow_id}.json"
            )
            script_path = directory / "scripts" / f"{workflow.workflow_id}.py"
            removed = False
            for path in (
                workflow_path,
                script_path,
            ):
                if path.exists():
                    path.unlink()
                    removed = True
            if removed:
                self._rebuild_docs(problem_class, status)

    def _root_for_status(self, status: WorkflowStatus) -> Path:
        return self._status_roots()[status]

    def _status_roots(self) -> Dict[WorkflowStatus, Path]:
        return {
            WorkflowStatus.ACTIVE: self.paths.active_skill_root,
            WorkflowStatus.PROVISIONAL: self.paths.provisional_skill_root,
            WorkflowStatus.ARCHIVE: self.paths.archive_skill_root,
        }

    @staticmethod
    def _rebuild_skill_index(root: Path) -> None:
        skills_by_class = {}
        paths = list(root.glob("*/references/skill.json"))
        for path in sorted(paths):
            metadata = json.loads(path.read_text(encoding="utf-8"))
            key = str(metadata.get("problem_class") or metadata.get("name") or path)
            skills_by_class[key] = metadata
        skills = [skills_by_class[key] for key in sorted(skills_by_class)]
        _write_json_atomic(root / "SKILLS.json", {"skills": skills})


def _default_skill_markdown(
    skill_name: str,
    title: str,
    description: str,
    event_type: str,
) -> str:
    event_line = f"- 精确 `event_type`：`{event_type}`\n" if event_type else ""
    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## 用途\n\n"
        f"{description}\n\n"
        "## 执行约束\n\n"
        f"{event_line}"
        "- 使用 `scripts/*.py` 执行工作流。\n"
        "- 按需读取 `references/skill.json` 和 `references/workflows/*.json`。\n"
        "- 人工脚本必须通过项目提供的 Skill 验证程序。\n"
    )


def _write_json(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _public_task_id(task_id: str) -> str:
    for prefix in ("explore__", "infer__"):
        if task_id.startswith(prefix):
            return task_id[len(prefix):]
    return task_id


def _write_json_atomic(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
