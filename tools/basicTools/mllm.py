import os
import base64
import requests
from langchain_core.tools import tool

@tool
def MLLM(file: str, filename: str, query: str, tool: str) -> str:
    """
    MLLM model for visual language processing. The API accepts an image URL, local image path, or Base64 string; image's name, and a text query, and returns the text response.

    category: 世界模型/检索类

    Args:
        file: Image path, URL, or Base64 encoded string
        filename: Image filename can be get from the file
        query: Text query for the model
        tool: choose one of the running mllm [qwen36Tool]

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