import base64
import json
import os

import requests
from langchain_core.tools import tool


def process_file(file: str) -> str:
    """本地文件转换为 Base64，URL、文件标识和 Base64 保持原样。"""
    if isinstance(file, str) and os.path.exists(file):
        with open(file, "rb") as image_file:
            return base64.b64encode(
                image_file.read()
            ).decode("utf-8")

    return file


@tool
def groundingdino(
    query: str,
    file: str,
    filename: str,
    box_threshold: float = 0.35,
    text_threshold: float = 0.25,
) -> str:
    """
    使用 GroundingDINO 检测图像中的目标。该工具根据英文物体类别或英文指代表达执行
    开放词汇目标检测，返回目标类别、边界框和置信度。

    query 支持：
        单个类别或短语：
        ✅ "person"
        ✅ "red car"
        ✅ "person wearing a black shirt"

        JSON 字符串列表：
        ✅ '["person", "car", "dog"]'
        ✅ '["red car", "person wearing black"]'

    边界框格式：
        [xmin, ymin, xmax, ymax]

    category: 世界模型/检索类

    Args:
        query: 英文物体类别、英文指代表达，或类别组成的 JSON 字符串列表，不能为空。
        file: 输入图像 URL、本地路径、文件标识或 Base64 编码图像。
        filename: 输入图像文件名。
        box_threshold: 检测框置信度阈值，默认 0.35。
        text_threshold: 文本匹配阈值，默认 0.25。

    Returns:
        JSON 字符串，包含检测结果图 URL，以及目标类别、边界框和置信度。
    """
    try:
        processed_file = process_file(file)
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": f"Error reading input image: {exc}",
            },
            ensure_ascii=False,
        )

    url = "http://172.16.0.33:9418/api/v1/groundingDINO"

    payload = {
        "query": query,
        "file": processed_file,
        "filename": filename,
        "box_threshold": box_threshold,
        "text_threshold": text_threshold,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
        result = response.json()

        data = result.get("data", {})
        detections = (
            data.get("detections", [])
            if isinstance(data, dict)
            else []
        )

        return json.dumps(
            {
                "status": "success",
                "file": result.get("file", ""),
                "detections": detections,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    f"Error executing GroundingDINO: {exc}"
                ),
            },
            ensure_ascii=False,
        )
