import os
import base64
import requests
from langchain_core.tools import tool

@tool
def paddleOcrTool(file: str, filename: str) -> str:
    """
    基于 Paddle 的光学字符识别（OCR）工具。输入图像 URL、本地路径或 Base64 字符串
    以及图像文件名，提取并返回图像中的文字。

    category: 固定检测类

    Args:
        file: 图像路径、URL 或 Base64 编码字符串。
        filename: 图像文件名。

    """
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

    url = "http://172.16.0.33:9418/api/v1/paddle_ocr_api"
    payload = {
        "file": processed_file,
        "filename": filename
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # 解析 JSON 并优先提取大模型需要的最终结果 (content 字段)
        resp_json = response.json()
        if "content" in resp_json:
            return resp_json["content"]
        return response.text
        
    except Exception as e:
        return f"Error executing paddleOcrTool: {str(e)}"
