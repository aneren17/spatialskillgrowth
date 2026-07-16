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
def unidepth(
    detections: str,
    file: str,
    filename: str,
) -> str:
    """
    使用 UniDepthV2 估计已检测目标的度量深度。输入目标检测结果后，计算每个边界框区域内
    以米为单位的中位深度。

    detections 必须是 JSON 字符串列表，每项必须包含：
        cls: 目标类别名。
        box: [xmin, ymin, xmax, ymax] 格式的边界框。
        score: 检测置信度。

    示例：
        '[{"cls":"person","box":[120,80,460,690],"score":0.92}]'

    GroundingDINO 返回的检测结果转换成 JSON 字符串后可直接传入。

    category: 空间度量类

    Args:
        detections: 包含检测框、类别和置信度的 JSON 字符串。
        file: 输入图像 URL、本地路径、文件标识或 Base64 编码图像。
        filename: 输入图像文件名。

    Returns:
        JSON 字符串，包含每个目标的类别、边界框、置信度和估计深度（米）。
    """
    try:
        parsed_detections = json.loads(detections)

        if isinstance(parsed_detections, dict):
            parsed_detections = [parsed_detections]

        if not isinstance(parsed_detections, list):
            raise ValueError(
                "detections must be a JSON list"
            )

        processed_file = process_file(file)

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    f"Invalid detections or input image: {exc}"
                ),
            },
            ensure_ascii=False,
        )

    url = "http://172.16.0.33:9418/api/v1/unidepth"

    payload = {
        "detections": json.dumps(
            parsed_detections,
            ensure_ascii=False,
        ),
        "file": processed_file,
        "filename": filename,
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
        depth_results = (
            data.get("originalResponse", [])
            if isinstance(data, dict)
            else []
        )

        return json.dumps(
            {
                "status": "success",
                "detections": depth_results,
            },
            ensure_ascii=False,
        )

    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "message": (
                    f"Error executing UniDepth: {exc}"
                ),
            },
            ensure_ascii=False,
        )
