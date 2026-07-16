import requests
from typing import Union, List
from langchain_core.tools import tool

@tool
def webVisitTool(query: str, url: Union[str, List[str]]) -> str:
    """
    访问一个或多个网页，并根据用户问题提取与目标相关的信息。调用前必须明确访问目标。

    category: 世界模型/检索类

    Args:
        query: 访问目标，即希望从网页中获取的具体信息；多个目标应在同一字符串中清楚描述。
        url: 要访问的目标网址，可以是单个 URL 字符串或 URL 字符串列表。

    """
    api_url = "http://172.16.0.33:9418/api/v1/webVisit"
    payload = {
        "query": query,
        "url": url
    }
    
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        
        # 解析 JSON 并优先提取大模型需要的最终结果 (content 字段)
        resp_json = response.json()
        if "content" in resp_json:
            return resp_json["content"]
            
        return response.text
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None

        # 4xx → 页面无法访问
        if status and 400 <= status < 500:
            return (
                f"页面访问失败 (HTTP {status})：目标网址无法访问或不存在。\n"
                "请尝试: 换一个相关网址、从 webSearchTool 的搜索结果中另选链接、或改用搜索获取信息。"
            )

        # 5xx → 服务端错误
        if status and status >= 500:
            return (
                "页面访问服务暂时不可用。\n"
                "请尝试: 稍后重试、换一个网址、或改用 webSearchTool 搜索替代来源。"
            )

        # 连接/超时错误
        error_msg = f"页面访问失败: {str(e)[:200]}。该网址可能无法访问，请尝试换一个相关网址或改用搜索。"
        return error_msg
    except Exception as e:
        return f"页面访问异常: {str(e)[:200]}。请尝试更换网址。"
