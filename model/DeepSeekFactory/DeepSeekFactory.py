from langchain_openai import ChatOpenAI 
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL ="deepseek-v4-flash"
DEFAULT_API_KEY = "sk-9978a3d7253a4d76b62e671ed4949ba9"

def get_llm():
    llm = ChatOpenAI(
        model=DEFAULT_MODEL,
        openai_api_key=DEFAULT_API_KEY,
        openai_api_base=DEFAULT_BASE_URL,
    )
    return llm


def get_judge_llm():
    """轻量判分调用，与 get_llm 同配置，仅独立函数名。"""
    return get_llm()

