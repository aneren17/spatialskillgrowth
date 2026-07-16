"""SpatialSkillGrowth 推理结果到 Omni3D 原生评测格式的适配。"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List


FLOAT_ACC_TOLERANCE = 0.1
MRA_THRESHOLDS = (0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05)
CATEGORY_NAMES = ("yes_no", "multiple_choice", "numeric_count", "numeric_other")


def export_inference_predictions(run_root: Path) -> Path:
    """将 run 内部 JSONL 汇总为稳定、无数据库依赖的评测输入。"""
    run_root = Path(run_root)
    split_path = run_root / "split.json"
    result_path = run_root / "results" / "per_task.jsonl"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    task_ids = list(split.get("all_task_ids") or [])
    rows = {}
    if result_path.is_file():
        for line in result_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("mode") == "infer":
                rows[str(item.get("task_id") or "")] = item
    predictions = []
    for task_id in task_ids:
        row = rows.get(task_id) or {}
        answer = str(row.get("answer") or "").strip()
        predictions.append({
            "task_id": task_id,
            "prediction": answer if answer else None,
            "execution_success": bool(answer),
            "selected_workflow_id": str(row.get("selected_workflow_id") or ""),
            "fallback_react": bool(row.get("fallback_react")),
            "split": str(row.get("split") or ""),
            "error": str(row.get("error") or ""),
        })
    payload = {
        "run_id": run_root.name,
        "benchmark": "omni3d",
        "total_tasks": len(task_ids),
        "completed_tasks": sum(item["execution_success"] for item in predictions),
        "predictions": predictions,
    }
    output = run_root / "results" / "omni3d_predictions.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def evaluate_run(
    run_root: Path,
    annotations_path: Path,
    predictions_path: Path | None = None,
) -> Dict:
    run_root = Path(run_root)
    annotations_path = Path(annotations_path)
    predictions_path = predictions_path or (
        run_root / "results" / "omni3d_predictions.json"
    )
    if not predictions_path.is_file():
        predictions_path = export_inference_predictions(run_root)
    prediction_payload = json.loads(predictions_path.read_text(encoding="utf-8"))
    annotations_payload = json.loads(annotations_path.read_text(encoding="utf-8"))
    annotations = annotations_payload.get("questions") or annotations_payload.get("data") or []
    prediction_items = prediction_payload.get("predictions") or []
    predictions = {
        str(item.get("task_id") or ""): item
        for item in prediction_items
        if str(item.get("task_id") or "")
    }
    annotations_by_id = {_task_id(item): item for item in annotations}
    missing_annotations = sorted(set(predictions) - set(annotations_by_id))
    if missing_annotations:
        raise ValueError(
            "Predictions contain task IDs absent from annotations: "
            + ", ".join(missing_annotations[:5])
        )
    rows = []
    native_results = []
    categories = {
        name: {"total": 0, "correct": 0, "failed": 0, "mra_sum": 0.0}
        for name in CATEGORY_NAMES
    }
    threshold_correct = {threshold: 0 for threshold in MRA_THRESHOLDS}
    for item in annotations:
        task_id = _task_id(item)
        if task_id not in predictions:
            continue
        prediction_item = predictions[task_id]
        prediction = prediction_item.get("prediction")
        execution_success = prediction is not None and str(prediction).strip() != ""
        answer_type = str(item.get("answer_type") or "")
        groundtruth = item.get("answer")
        question = str(item.get("question") or "")
        category = categorize_question(answer_type, groundtruth)
        correct = execution_success and check_answer_match(
            prediction, groundtruth, category, question
        )
        category_metrics = categories[category]
        category_metrics["total"] += 1
        category_metrics["correct"] += int(correct)
        category_metrics["failed"] += int(not execution_success)
        mra_score = 0.0
        threshold_results = {threshold: False for threshold in MRA_THRESHOLDS}
        if category == "numeric_other" and execution_success:
            mra_score, threshold_results = calculate_mra_score(
                prediction, groundtruth, category
            )
            category_metrics["mra_sum"] += mra_score
            for threshold, matched in threshold_results.items():
                threshold_correct[threshold] += int(matched)
        rows.append({
            "task_id": task_id,
            "answer_type": answer_type,
            "category": category,
            "ground_truth": groundtruth,
            "prediction": prediction,
            "execution_success": execution_success,
            "correct": correct,
            "mra": mra_score,
            "selected_workflow_id": prediction_item.get("selected_workflow_id", ""),
            "fallback_react": bool(prediction_item.get("fallback_react")),
            "split": prediction_item.get("split", ""),
        })
        native_results.append({
            "image_index": item.get("image_index", ""),
            "question_index": item.get("question_index", ""),
            "image_filename": item.get("image_filename", ""),
            "question": question,
            "answer": groundtruth,
            "answer_type": answer_type,
            "pred_answer": {"iter1": prediction if execution_success else None},
            "program": {
                "iter1": (
                    f"workflow:{prediction_item.get('selected_workflow_id')}"
                    if prediction_item.get("selected_workflow_id")
                    else "SpatialSkillGrowth-ReAct"
                )
            },
            "meta_data": {
                "iterations_processed": 1,
                "execution_success_by_iteration": {"iter1": execution_success},
                "quality_ratings": {},
                "in_example_library": False,
            },
        })
    summary = summarize(categories, threshold_correct)
    native_payload = {
        "summary": {
            "run_id": prediction_payload.get("run_id") or run_root.name,
            "total_questions": len(native_results),
            "questions_in_library": 0,
            "learned_tools": 0,
            "deprecated_tools": 0,
            "iterations": 1,
        },
        "results": native_results,
    }
    _write_outputs(run_root, rows, summary, native_payload)
    return summary


def categorize_question(answer_type: str, groundtruth) -> str:
    if answer_type == "int":
        return "numeric_count"
    if answer_type == "float":
        return "numeric_other"
    if answer_type == "str":
        return "yes_no" if str(groundtruth).lower() in {"yes", "no"} else "multiple_choice"
    raise ValueError(f"Unsupported Omni3D answer type: {answer_type}")


def check_answer_match(prediction, groundtruth, category: str, question: str) -> bool:
    pred = normalize_answer(prediction, category)
    truth = normalize_answer(groundtruth, category)
    if category == "numeric_count":
        return pred == truth
    if category == "numeric_other":
        if not isinstance(pred, float) or not isinstance(truth, float):
            return False
        if truth == 0:
            return abs(pred - truth) < FLOAT_ACC_TOLERANCE
        return abs(pred - truth) / abs(truth) < FLOAT_ACC_TOLERANCE
    return fuzzy_match(str(pred), str(truth), question, category)


def normalize_answer(answer, category: str):
    if category == "numeric_count":
        number = _extract_number(answer)
        return int(round(number)) if number is not None else answer
    if category == "numeric_other":
        number = _extract_number(answer)
        return float(number) if number is not None else answer
    if category == "yes_no" and isinstance(answer, bool):
        return "yes" if answer else "no"
    text = str(answer).lower().strip().strip(".,!?;:")
    if category == "yes_no" and text in {"true", "false"}:
        return "yes" if text == "true" else "no"
    return text


def fuzzy_match(prediction: str, groundtruth: str, question: str, category: str) -> bool:
    if category == "yes_no":
        first = prediction.split()[0].strip(".,!?;:*") if prediction.split() else ""
        if groundtruth == "yes":
            return first == "yes"
        return first == "no" or "will not" in prediction or "would not" in prediction
    for prefix in ("the ", "a ", "an ", "leftmost ", "rightmost "):
        prediction = prediction.removeprefix(prefix).removeprefix(prefix)
        groundtruth = groundtruth.removeprefix(prefix).removeprefix(prefix)
    if prediction == groundtruth:
        return True
    if "what time is it" in question.lower().strip():
        try:
            return tuple(map(int, prediction.split(":"))) == tuple(
                map(int, groundtruth.split(":"))
            )
        except (TypeError, ValueError):
            return False
    return False


def calculate_mra_score(prediction, groundtruth, category: str):
    pred = normalize_answer(prediction, category)
    truth = normalize_answer(groundtruth, category)
    if not isinstance(pred, float) or not isinstance(truth, float):
        return 0.0, {threshold: False for threshold in MRA_THRESHOLDS}
    relative_error = (
        abs(pred - truth) / abs(truth)
        if truth != 0
        else abs(pred - truth)
    )
    results = {
        threshold: relative_error < threshold for threshold in MRA_THRESHOLDS
    }
    return sum(results.values()) / len(MRA_THRESHOLDS), results


def summarize(categories: Dict, threshold_correct: Dict) -> Dict:
    total = sum(item["total"] for item in categories.values())
    correct = sum(item["correct"] for item in categories.values())
    output = {
        "float_accuracy_tolerance": FLOAT_ACC_TOLERANCE,
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "categories": {},
    }
    for name, item in categories.items():
        metrics = dict(item)
        metrics["accuracy"] = item["correct"] / item["total"] if item["total"] else 0.0
        if name == "numeric_other":
            metrics["mra"] = item["mra_sum"] / item["total"] if item["total"] else 0.0
        output["categories"][name] = metrics
    numeric_total = categories["numeric_other"]["total"]
    output["mra_thresholds"] = {
        str(threshold): {
            "correct": threshold_correct[threshold],
            "total": numeric_total,
            "accuracy": threshold_correct[threshold] / numeric_total if numeric_total else 0.0,
        }
        for threshold in MRA_THRESHOLDS
    }
    return output


def print_summary(summary: Dict) -> None:
    labels = (
        ("Yes/No", "yes_no"),
        ("Multiple Choice", "multiple_choice"),
        ("Counting", "numeric_count"),
        ("Float@10%", "numeric_other"),
    )
    print("Omni3D SpatialSkillGrowth evaluation")
    print("=" * 78)
    for label, key in labels:
        item = summary["categories"][key]
        print(
            f"{label:<18} {item['correct']:>4}/{item['total']:<4} "
            f"{item['accuracy'] * 100:>6.1f}%  failed={item['failed']}"
        )
    numeric = summary["categories"]["numeric_other"]
    print(f"{'MRA Float':<18} {numeric.get('mra', 0.0) * 100:>11.1f}%")
    print("-" * 78)
    print(
        f"{'Overall':<18} {summary['correct']:>4}/{summary['total']:<4} "
        f"{summary['accuracy'] * 100:>6.1f}%"
    )


def _task_id(item: Dict) -> str:
    if item.get("task_id"):
        return str(item["task_id"])
    image_index = str(item.get("image_index") or item.get("image_filename") or "")
    return f"{Path(image_index).stem}_{item.get('question_index')}"


def _extract_number(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        match = re.search(r"-?\d+\.?\d*", str(value).strip())
        return float(match.group()) if match else None


def _write_outputs(run_root: Path, rows: List[Dict], summary: Dict, native: Dict) -> None:
    metrics_path = run_root / "metrics" / "omni3d_official_metrics.json"
    native_path = run_root / "results" / "omni3d_native_eval.json"
    csv_path = run_root / "results" / "omni3d_eval_details.csv"
    metrics_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    native_path.write_text(
        json.dumps(native, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["task_id"])
        writer.writeheader()
        writer.writerows(rows)
