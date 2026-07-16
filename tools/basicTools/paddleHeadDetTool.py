import os
import base64
import requests
from langchain_core.tools import tool

@tool
def paddleHeadDetTool(file: str, filename: str, tool: str) -> str:
    """
    基于 Paddle 的人头检测工具。输入图像 URL、本地路径或 Base64 字符串、图像文件名
    和模型标识，返回人头边界框及结果图 URL。

    ⚠️ 仅检测人类头部。不要用于找文字区域、数学公式、动物、车辆或其他非人目标。

    category: 固定检测类

    Args:
        file: 图像路径、URL 或 Base64 编码字符串。
        filename: 图像文件名。
        tool: 检测工具标识，必须为 paddleHeadDetTool。

    """
    processed_file = file
    
    # 判断是否为本地存在的文件路径
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                # 转换为 base64 并且 decode 为 utf-8 字符串
                # (必须 decode，否则 bytes 类型在 requests.post 的 json payload 中会报错)
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"
    # 如果不是本地文件，直接保留原内容（URL 或 已经是Base64）传给后端处理

    url = "http://172.16.0.33:9418/api/v1/paddle_ocr"
    payload = {
        "file": processed_file,
        "filename": filename,
        "tool": tool
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error executing paddleHeadDetTool: {str(e)}"
