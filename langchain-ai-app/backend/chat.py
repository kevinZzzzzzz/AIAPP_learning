"""
基础对话模块 - 文章 2.1 实操1
简单对话接口，类似前端调用后端 API
"""
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL


def get_llm():
    """获取 LLM 实例"""
    return ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_BASE_URL,
        temperature=0.7,
    )


def chat_with_history(messages: list[dict]) -> str:
    """
    与 LLM 进行对话
    :param messages: 前端传来的消息列表 [{"role": "user"|"assistant"|"system", "content": "..."}]
    :return: LLM 回复文本
    """
    llm = get_llm()
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))

    response = llm.invoke(langchain_messages)
    return response.content


def stream_chat(messages: list[dict]):
    """
    流式对话 - 文章第五步进阶方向1：流式输出
    使用 SSE 实现类似 ChatGPT 的实时打字效果
    """
    llm = get_llm()
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))

    return llm.stream(langchain_messages)
