"""调用 SpatialSkillGrowth 异常检测 HTTP 服务。"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18061
DEFAULT_FILE_PATH = "test/banner.mp4"
DEFAULT_EVENT_TYPE = "banner"
DEFAULT_TIMEOUT_SECONDS = 600
SUPPORTED_PORTS = (18061, 18062)


def build_parser():
    parser = argparse.ArgumentParser(
        description="调用本地 SpatialSkillGrowth 异常检测后端。"
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default=DEFAULT_FILE_PATH,
        help="要上传的图片或视频路径。",
    )
    parser.add_argument(
        "event_type",
        nargs="?",
        default=DEFAULT_EVENT_TYPE,
        help="精确异常类别 ID，例如 banner、fire、fall。",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="后端地址，默认 127.0.0.1。",
    )
    parser.add_argument(
        "--port",
        type=int,
        choices=SUPPORTED_PORTS,
        default=DEFAULT_PORT,
        help="后端端口：18061 或 18062，默认 18061。",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="请求超时秒数，默认 600。",
    )
    return parser


def response_is_valid(response, payload):
    if not 200 <= response.status_code < 300:
        return False
    if not isinstance(payload, dict):
        return False
    is_anomaly = payload.get("is_anomaly")
    threshold = payload.get("threshold")
    return (
        type(is_anomaly) is int
        and is_anomaly in {0, 1}
        and isinstance(threshold, (int, float))
        and not isinstance(threshold, bool)
    )


def main():
    arguments = build_parser().parse_args()
    file_path = Path(arguments.file_path).expanduser().resolve()
    if not file_path.is_file():
        print("媒体文件不存在：" + str(file_path), file=sys.stderr)
        return 2
    if arguments.timeout <= 0:
        print("timeout 必须大于 0。", file=sys.stderr)
        return 2

    url = "http://" + arguments.host + ":" + str(arguments.port) + "/detect"
    print("请求地址：" + url)
    print("媒体文件：" + str(file_path))
    print("event_type：" + arguments.event_type)

    try:
        with requests.Session() as session:
            session.trust_env = False
            with open(file_path, "rb") as handle:
                response = session.post(
                    url,
                    files={
                        "file": (
                            os.path.basename(file_path),
                            handle,
                        )
                    },
                    data={"event_type": arguments.event_type},
                    timeout=arguments.timeout,
                )
    except (OSError, requests.exceptions.RequestException) as exc:
        print(
            "请求失败：" + type(exc).__name__ + ": " + str(exc),
            file=sys.stderr,
        )
        return 1

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        payload = None

    print("HTTP 状态码：" + str(response.status_code))
    if payload is None:
        print("响应正文：" + response.text)
    else:
        print("响应 JSON：")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not response_is_valid(response, payload):
        print("接口测试失败：响应不符合约定。", file=sys.stderr)
        return 1

    print("接口测试通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
