import os
import base64
import requests
from langchain_core.tools import tool

@tool
def MLLM(file: str, filename: str, query: str, tool: str) -> str:
    """
    多模态视觉语言理解工具。输入图像 URL、本地路径或 Base64 字符串、图像文件名和
    文本问题，返回模型生成的文本回答。

    category: 世界模型/检索类

    Args:
        file: 图像路径、URL 或 Base64 编码字符串。
        filename: 图像文件名，可从 file 中获取。
        query: 提交给模型的文本问题或任务要求。
        tool: 要调用的多模态模型标识，当前使用 qwen36Tool。

    """
    processed_file = file
    
    # 判断是否为本地存在的文件路径
    if isinstance(file, str) and os.path.exists(file):
        try:
            with open(file, 'rb') as f:
                image_data = f.read()
                # 转换为 base64 并且 decode 为 utf-8 字符串，兼容 JSON payload
                processed_file = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            return f"Error reading local file to base64: {str(e)}"

    url = "http://172.16.0.33:9418/api/v1/MLLM"
    payload = {
        "file": processed_file,
        "filename": filename,
        "query": query,
        "tool": tool
    }
    
    try:
        # 如果有些接口是 GET，可以把 json=payload 换成 params=payload
        response = requests.post(url, json=payload)
        # 解析 JSON 并优先提取大模型需要的最终结果 (content 字段)
        resp_json = response.json()
        if "content" in resp_json:
            return resp_json["content"]
        return response.text
    except Exception as e:
        return f"Error executing MLLM: {str(e)}"
