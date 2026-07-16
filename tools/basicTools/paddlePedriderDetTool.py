import os
import base64
import requests
from langchain_core.tools import tool

@tool
def paddlePedriderDetTool(file: str, filename: str, tool: str) -> str:
    """
    Submit a Paddle-based object detection task. The API detects class_name including car, bus, truck, bicycle, tricycle and pedestrian.
    The API accepts an image URL, local image path, or Base64 string; image's name and paddle model name; the API returns detected bounding boxes and a result image URL.

    ⚠️ 仅检测行人/骑行者/车辆。不要用于找文字、公式、室内物体、动物或其他非交通目标。

    category: 固定检测类

    Args:
        file: Image path, URL, or Base64 encoded string
        filename: Image filename
        tool: Tool identifier for OCR processing: one of [paddlePedriderDetTool]

    """
    # ================= 修改逻辑开始 =================
    processed_file = file
    
    # 判断是否为本地存在的文件路径
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                # 转换为 base64 并且 decode 为 utf-8 字符串，以便通过 JSON payload 发送
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"
    # ================= 修改逻辑结束 =================

    url = "http://172.16.0.33:9418/api/v1/paddle_ocr"
    payload = {
        "file": processed_file,
        "filename": filename,
        "tool": tool
    }
    
    try:
        # 如果有些接口是 GET，可以把 json=payload 换成 params=payload
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error executing paddlePedriderDetTool: {str(e)}"