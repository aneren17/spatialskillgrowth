import asyncio
import re
import time
from typing import Any, List, Optional

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

#8860
DEFAULT_BASE_URL = "http://127.0.0.1:8860/v1"
DEFAULT_BASE_JUDGE_URL = "http://127.0.0.1:8863/v1"
DEFAULT_MODEL = "Qwen3.6-27B-FP8"
DEFAULT_API_KEY = "saki"
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 10
RETRYABLE_HTTP_STATUS_CODES = {408, 409, 429}
RETRYABLE_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
}

# DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
# DEFAULT_MODEL = "Qwen/Qwen3.6-27B"
# DEFAULT_API_KEY = "sk-fdgovunqriiznbficwsmjjlktnreudfxqdbpoqrwftgwoiye"


# DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
# DEFAULT_MODEL = "Qwen/Qwen3.5-397B-A17B"
# DEFAULT_API_KEY = "sk-fdgovunqriiznbficwsmjjlktnreudfxqdbpoqrwftgwoiye"


# DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# DEFAULT_MODEL = "qwen3.6-27b"
# DEFAULT_API_KEY = "sk-30c595cd9f784d338e180274c1a6906a"


def _is_retryable_llm_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    if isinstance(status_code, int):
        if status_code in RETRYABLE_HTTP_STATUS_CODES:
            return True
        if 500 <= status_code <= 599:
            return True
    if type(error).__name__ in RETRYABLE_ERROR_NAMES:
        return True
    message = str(error).lower()
    markers = (
        "rate limit",
        "too many requests",
        "connection error",
        "timed out",
        "timeout",
    )
    return any(marker in message for marker in markers)


class MultimodalChatOpenAI(ChatOpenAI):
    """
    自定义的 ChatOpenAI 包装类（纯文本 & 工具驱动版）：
    去除了自动转换图片为 Base64 的逻辑，输入文本（含图片路径）将被原样保留。
    强制大模型依靠外部 Tools (如 MLLM, SAM3, PaddleOCR 等) 来处理和感知图片。
    保留了 <think> 标签清理和频控重试机制。
    """
    
    # 后处理剥离 think 框
    def _strip_think_tags(self, chat_result: ChatResult) -> ChatResult:
        """使用正则表达式清理大模型输出中的 <think> 标签块"""
        for gen in chat_result.generations:
            if hasattr(gen, 'message') and isinstance(gen.message.content, str):
                # 正则匹配 <think>到</think> 之间的所有内容
                cleaned_content = re.sub(r'<think>.*?(?:</think>|$)\s*', '', gen.message.content, flags=re.DOTALL).strip()
                
                # 更新 LangChain 对象的 content
                gen.message.content = cleaned_content
                if hasattr(gen, 'text'):
                    gen.text = cleaned_content
        return chat_result

    # 重写底层同步生成方法
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        for attempt in range(1, DEFAULT_RETRY_ATTEMPTS + 1):
            try:
                # 直接将原始 messages 发送给大模型，不做任何处理
                raw_result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                # 返回前剥离 think 框
                return self._strip_think_tags(raw_result)
            except Exception as error:
                if (
                    not _is_retryable_llm_error(error)
                    or attempt >= DEFAULT_RETRY_ATTEMPTS
                ):
                    raise
                print(
                    "LLM 暂时不可用，"
                    + type(error).__name__
                    + "，正在重试 ("
                    + str(attempt)
                    + "/"
                    + str(DEFAULT_RETRY_ATTEMPTS)
                    + ")..."
                )
                time.sleep(DEFAULT_RETRY_DELAY_SECONDS)

    # 重写底层异步生成方法
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        
        for attempt in range(1, DEFAULT_RETRY_ATTEMPTS + 1):
            try:
                # 直接将原始 messages 发送给大模型，不做任何处理
                raw_result = await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
                return self._strip_think_tags(raw_result)
            except Exception as error:
                if (
                    not _is_retryable_llm_error(error)
                    or attempt >= DEFAULT_RETRY_ATTEMPTS
                ):
                    raise
                print(
                    "LLM 暂时不可用，"
                    + type(error).__name__
                    + "，正在重试 ("
                    + str(attempt)
                    + "/"
                    + str(DEFAULT_RETRY_ATTEMPTS)
                    + ")..."
                )
                await asyncio.sleep(DEFAULT_RETRY_DELAY_SECONDS)


def get_llm():
    llm = MultimodalChatOpenAI(
        model=DEFAULT_MODEL,
        api_key=DEFAULT_API_KEY,
        base_url=DEFAULT_BASE_URL,
        max_retries=0, # 原生重试关掉，由我们重写的代码接管
        # max_tokens=8192,

        temperature=0.7,
        top_p=0.80,
        presence_penalty=1.5,
        extra_body = {
            "repetition_penalty": 1.0,
            "top_k": 20,
        }
    )
    return llm


def get_judge_llm():
    llm = MultimodalChatOpenAI(
        model=DEFAULT_MODEL,
        api_key=DEFAULT_API_KEY,
        base_url=DEFAULT_BASE_JUDGE_URL,
        max_retries=0,
        # max_tokens=8192,

        temperature=0.7,
        top_p=0.80,
        presence_penalty=1.5,
        extra_body = {
            "repetition_penalty": 1.0,
            "top_k": 20,
        }
    )
    return llm


# ============================================================
# 多实例支持：用于并行 benchmark 评测（4 端口各一个 LLM 实例）
# ============================================================

MULTI_BASE_URLS = [
    "http://127.0.0.1:8860/v1",
    "http://127.0.0.1:8861/v1",
    "http://127.0.0.1:8862/v1",
    "http://127.0.0.1:8863/v1",
]


def get_multi_llms(base_urls: Optional[List[str]] = None) -> List[MultimodalChatOpenAI]:
    """构建多个 LLM 实例，每个对应不同端口的模型服务。

    Args:
        base_urls: 端口列表，默认使用 MULTI_BASE_URLS (8860~8863)

    Returns:
        与 base_urls 等长的 MultimodalChatOpenAI 实例列表
    """
    urls = base_urls if base_urls else MULTI_BASE_URLS
    llms = []
    for url in urls:
        llm = MultimodalChatOpenAI(
            model=DEFAULT_MODEL,
            api_key=DEFAULT_API_KEY,
            base_url=url,
            max_retries=0,
            temperature=0.7,
            top_p=0.80,
            presence_penalty=1.5,
            extra_body={"repetition_penalty": 1.0, "top_k": 20},
        )
        llms.append(llm)
        print(f"  [LLM] {url}")
    return llms


def get_llm_by_url(base_url: str) -> MultimodalChatOpenAI:
    """按指定 URL 构建单个 LLM 实例。"""
    return MultimodalChatOpenAI(
        model=DEFAULT_MODEL,
        api_key=DEFAULT_API_KEY,
        base_url=base_url,
        max_retries=0,
        temperature=0.7,
        top_p=0.80,
        presence_penalty=1.5,
        extra_body={"repetition_penalty": 1.0, "top_k": 20},
    )
