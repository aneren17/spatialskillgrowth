import requests
from typing import Union, List
from langchain_core.tools import tool


@tool
def webSearchTool(query: Union[str, List[str]]) -> str:
    """
    使用单个查询词或查询词列表执行网页搜索，为每个查询返回前 5 个网页链接和摘要。

    category: 世界模型/检索类

    Args:
        query: 单个搜索查询字符串，或需要并发执行的一组互补查询字符串。

    """
    url = "http://172.16.0.33:9418/api/v1/webSearch"
    payload = {
        "query": query
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # 尝试解析 JSON 并直接提取大模型需要的 Markdown 格式内容 (content 字段)
        # 这样大模型不需要额外阅读外层的 status 和 data 结构，节省 Token 且效果更好
        resp_json = response.json()
        if "content" in resp_json:
            return resp_json["content"]
            
        return response.text
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None

        # 422 / 无结果 → 引导换搜索词
        if status == 422 or (hasattr(e, 'response') and e.response is not None and 'No search results' in str(e.response.text)):
            return (
                "搜索失败：当前查询词未返回任何结果。\n"
                "请尝试以下操作:\n"
                "  - 简化搜索词，使用更通用/更短的关键词\n"
                "  - 换一种语言或表述方式重新搜索\n"
                "  - 从不同角度拆分问题，分批搜索\n"
                "  - 如果多次搜索均无结果，考虑换工具"
            )

        # 500 / 服务端错误 → 建议重试或换工具
        if status and status >= 500:
            return (
                "搜索服务暂时不可用。\n"
                "请尝试: 稍后重试，或换用 webVisitTool 直接访问已知网址，或使用其他工具。"
            )

        # 其他网络错误
        error_msg = f"搜索请求失败: {str(e)[:200]}。请尝试更换搜索关键词或搜索角度。"
        return error_msg
    except Exception as e:
        return f"搜索请求异常: {str(e)[:200]}。请尝试更换搜索关键词。"
