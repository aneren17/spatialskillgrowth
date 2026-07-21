"""使用指定异常类别的 benchmark 样本直接测试异常检测接口。"""
# python -m scripts.test_embedding_benchmark fall --all-videos
import argparse
import json
import os
from pathlib import Path

import requests

from agents.spatialskillgrowth.online_data import load_online_tasks
from agents.spatialskillgrowth.online_data import resolve_event_type

# 旧的 Runtime 测试路径保留作对照；当前脚本直接请求检测接口，不再使用这两个依赖。
# from nodes.mem.spatialskillgrowth.runtime.tool_runtime import ToolRuntime
# from tools.basicTools.embeddingTool import embeddingTool


DEFAULT_API_URL = "http://172.16.0.91:8080/api/detect"
DEFAULT_DATASET_ROOT = "benchmark/anomaly/skill_datasets"
DEFAULT_TASK_INDEX = 0
DEFAULT_TIMEOUT_SECONDS = 600


def build_parser():
    parser = argparse.ArgumentParser(
        description="使用 embedding 接口测试指定类别的一条或全部视频。"
    )
    parser.add_argument(
        "event_type",
        nargs="?",
        default="",
        help="异常事件类别，例如 banner、fire、fall。",
    )
    parser.add_argument(
        "--dataset-root",
        default=DEFAULT_DATASET_ROOT,
        help="包含 INDEX.json 的 benchmark 根目录。",
    )
    parser.add_argument(
        "--task-index",
        type=int,
        default=DEFAULT_TASK_INDEX,
        help="要测试的任务序号，从 0 开始。",
    )
    parser.add_argument(
        "--all-videos",
        action="store_true",
        help="测试指定类别 benchmark 中的全部视频，忽略 --task-index。",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="异常检测接口地址。",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="单次接口请求的超时秒数。",
    )
    return parser


def load_benchmark_tasks(dataset_root, event_type):
    index_path = dataset_root / "INDEX.json"
    if not index_path.is_file():
        raise FileNotFoundError("benchmark 总索引不存在：" + str(index_path))

    with open(index_path, "r", encoding="utf-8") as handle:
        index = json.load(handle)
    entries = index.get("datasets")
    if not isinstance(entries, list):
        raise ValueError("INDEX.json 缺少 datasets 数组。")

    selected_entry = None
    for entry in entries:
        if entry.get("event_type") == event_type:
            selected_entry = entry
            break
    if selected_entry is None:
        raise ValueError("benchmark 中没有该异常类别：" + event_type)

    dataset_path = dataset_root / str(selected_entry.get("dataset_path") or "")
    media_root = dataset_root / str(selected_entry.get("media_root") or "")
    tasks = load_online_tasks(
        str(dataset_path),
        str(media_root),
        require_groundtruth=True,
    )
    return tasks


def load_benchmark_task(dataset_root, event_type, task_index):
    tasks = [
        task
        for task in load_benchmark_tasks(dataset_root, event_type)
        if task.media_type == "video"
    ]
    if not tasks:
        raise ValueError("该类别 benchmark 中没有视频任务：" + event_type)
    if task_index < 0 or task_index >= len(tasks):
        raise IndexError(
            "task-index 超出范围："
            + str(task_index)
            + "，可用范围是 0 到 "
            + str(len(tasks) - 1)
        )
    return tasks[task_index], len(tasks)


def result_is_valid(response, response_json, event_type):
    if not isinstance(response_json, dict):
        return False
    data = response_json.get("data") or {}
    if not isinstance(data, dict):
        return False
    metrics = data.get("metrics") or {}
    if not isinstance(metrics, dict):
        return False
    threshold = metrics.get("threshold")
    threshold_is_number = isinstance(threshold, (int, float))
    if isinstance(threshold, bool):
        threshold_is_number = False
    return (
        200 <= response.status_code < 300
        and response_json.get("status") == "success"
        and data.get("event_type") == event_type
        and isinstance(data.get("is_anomaly"), bool)
        and threshold_is_number
    )


def groundtruth_is_anomaly(groundtruth):
    normalized = str(groundtruth or "").strip().lower()
    if normalized in {"是", "yes", "true", "1"}:
        return True
    if normalized in {"否", "no", "false", "0"}:
        return False
    raise ValueError("无法识别 benchmark answer：" + str(groundtruth))


# 旧实现通过 ToolRuntime 调用 embeddingTool：
#
# result = runtime.execute(
#     "embeddingTool",
#     {
#         "file_path": task.media_path,
#         "event_type": task.event_type,
#     },
# )
#
# 当前实现直接发送 multipart/form-data，以便只验证原始 HTTP 接口。
def execute_task(api_url, timeout_seconds, task):
    with requests.Session() as session:
        # 检测服务是内网地址，直接测试时不继承宿主机的 HTTP 代理。
        session.trust_env = False
        with open(task.media_path, "rb") as handle:
            response = session.post(
                api_url,
                files={
                    "file": (
                        os.path.basename(task.media_path),
                        handle,
                    )
                },
                data={"event_type": task.event_type},
                timeout=timeout_seconds,
            )

    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        response_json = None

    valid = result_is_valid(response, response_json, task.event_type)
    data = {}
    if isinstance(response_json, dict):
        data = response_json.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    metrics = data.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    prediction = data.get("is_anomaly")
    threshold = metrics.get("threshold")
    expected = groundtruth_is_anomaly(task.groundtruth)
    correct = valid and prediction == expected
    return response, response_json, valid, prediction, threshold, correct


def test_all_videos(api_url, timeout_seconds, tasks, event_type):
    media_tasks = [task for task in tasks if task.media_type == "video"]
    media_name = "视频"
    if not media_tasks:
        raise ValueError(
            "该类别 benchmark 中没有" + media_name + "任务：" + event_type
        )

    print("准备测试该类别 benchmark 中的全部" + media_name + "：")
    print("  event_type：" + event_type)
    print("  " + media_name + "数量：" + str(len(media_tasks)))
    print("  api_url：" + api_url)

    valid_count = 0
    correct_count = 0
    for index, task in enumerate(media_tasks):
        print(
            "\n["
            + str(index + 1)
            + "/"
            + str(len(media_tasks))
            + "] "
            + task.task_id
        )
        print("  media_path：" + task.media_path)
        print("  benchmark answer：" + task.groundtruth)
        try:
            (
                response,
                response_json,
                valid,
                prediction,
                threshold,
                correct,
            ) = execute_task(api_url, timeout_seconds, task)
        except (OSError, requests.exceptions.RequestException) as exc:
            print(
                "  接口请求失败："
                + type(exc).__name__
                + ": "
                + str(exc)
            )
            continue

        if valid:
            valid_count += 1
        if correct:
            correct_count += 1

        print("  HTTP 状态码：" + str(response.status_code))
        print("  API 原始响应：" + response.text)
        print("  异常判断：" + str(prediction))
        print("  threshold：" + str(threshold))
        print("  接口响应有效：" + str(valid))
        print("  判断正确：" + str(correct))

    total_count = len(media_tasks)
    accuracy = correct_count / total_count
    print("\n汇总：")
    print("  " + media_name + "总数：" + str(total_count))
    print("  有效调用数：" + str(valid_count))
    print("  无效调用数：" + str(total_count - valid_count))
    print("  判断正确数：" + str(correct_count))
    print("  判断错误数：" + str(total_count - correct_count))
    print("  准确率：" + format(accuracy, ".2%"))

    if valid_count == total_count:
        return 0
    return 1


def main():
    arguments = build_parser().parse_args()
    event_type_value = str(arguments.event_type or "").strip()
    if not event_type_value:
        event_type_value = input("请输入异常事件 event_type：").strip()
    event_type = resolve_event_type(event_type_value)
    dataset_root = Path(arguments.dataset_root).resolve()
    api_url = str(arguments.api_url or "").strip()
    if not api_url:
        raise ValueError("api-url 不能为空。")
    if arguments.timeout <= 0:
        raise ValueError("timeout 必须大于 0。")

    if arguments.all_videos:
        tasks = load_benchmark_tasks(dataset_root, event_type)
        return test_all_videos(
            api_url,
            arguments.timeout,
            tasks,
            event_type,
        )

    task, task_count = load_benchmark_task(
        dataset_root,
        event_type,
        arguments.task_index,
    )

    print("准备调用异常检测接口：")
    print("  event_type：" + task.event_type)
    print("  task_id：" + task.task_id)
    print("  task_index：" + str(arguments.task_index) + "/" + str(task_count - 1))
    print("  media_type：" + task.media_type)
    print("  media_path：" + task.media_path)
    print("  benchmark answer：" + task.groundtruth)
    print("  api_url：" + api_url)

    try:
        (
            response,
            response_json,
            valid,
            prediction,
            threshold,
            correct,
        ) = execute_task(api_url, arguments.timeout, task)
    except (OSError, requests.exceptions.RequestException) as exc:
        print(
            "\n接口请求失败："
            + type(exc).__name__
            + ": "
            + str(exc)
        )
        return 1

    print("\nAPI 原始响应：")
    print("  HTTP 状态码：" + str(response.status_code))
    print(response.text)
    print("\n检查结果：")
    api_status = None
    if isinstance(response_json, dict):
        api_status = response_json.get("status")
    print("  API status：" + str(api_status))
    print("  异常判断：" + str(prediction))
    print("  threshold：" + str(threshold))
    print("  接口响应有效：" + str(valid))
    print("  判断正确：" + str(correct))

    if valid:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
