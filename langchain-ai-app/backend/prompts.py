"""
Prompt模板管理 - 文章 2.2 实操2
借鉴前端模板化思维，将 Prompt 做成可复用的模板
"""
from langchain.prompts import ChatPromptTemplate, PromptTemplate


# ---------- 代码生成模板 ----------
CODE_GENERATION_TEMPLATE = """
你是一位资深的前端开发工程师。
请根据以下需求生成 {language} 代码：

需求描述：
{requirement}

要求：
- 代码风格简洁、可读性强
- 添加必要的中文注释
- 使用最新的语法特性
"""

code_generation_prompt = PromptTemplate(
    input_variables=["language", "requirement"],
    template=CODE_GENERATION_TEMPLATE,
)


# ---------- 代码评审模板 ----------
CODE_REVIEW_TEMPLATE = """
请作为高级代码审查员，审查以下 {language} 代码：

```{language}
{code}
```

请从以下几个方面进行评审：
1. 代码质量和可读性
2. 潜在 Bug 和性能问题
3. 安全风险
4. 改进建议
"""

code_review_prompt = PromptTemplate(
    input_variables=["language", "code"],
    template=CODE_REVIEW_TEMPLATE,
)


# ---------- 翻译模板 ----------
TRANSLATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是一位专业的翻译专家，精通多种语言。"),
    ("human", "请将以下 {source_lang} 文本翻译成 {target_lang}：\n\n{text}"),
])


# ---------- 模板注册表 ----------
PROMPT_REGISTRY = {
    "code_generation": {
        "label": "代码生成",
        "description": "根据需求描述生成指定语言的代码",
        "variables": ["language", "requirement"],
    },
    "code_review": {
        "label": "代码评审",
        "description": "审查代码质量、安全性和性能",
        "variables": ["language", "code"],
    },
    "translation": {
        "label": "翻译",
        "description": "将文本从一种语言翻译成另一种语言",
        "variables": ["source_lang", "target_lang", "text"],
    },
}


def get_available_templates() -> list[dict]:
    """获取所有可用的 Prompt 模板列表"""
    return [
        {
            "id": template_id,
            "label": info["label"],
            "description": info["description"],
            "variables": info["variables"],
        }
        for template_id, info in PROMPT_REGISTRY.items()
    ]


def apply_template(template_id: str, variables: dict) -> str:
    """
    应用指定模板并返回格式化后的 Prompt
    """
    if template_id == "code_generation":
        return code_generation_prompt.format(**variables)
    elif template_id == "code_review":
        return code_review_prompt.format(**variables)
    elif template_id == "translation":
        return TRANSLATION_PROMPT.format(**variables)
    else:
        raise ValueError(f"未知的模板ID: {template_id}")


def run_template_with_llm(template_id: str, variables: dict) -> str:
    """
    应用模板后直接调用 LLM 获取结果
    """
    from langchain_openai import ChatOpenAI
    from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_BASE_URL,
        temperature=0.7,
    )

    if template_id == "translation":
        chain = TRANSLATION_PROMPT | llm
    elif template_id == "code_generation":
        chain = code_generation_prompt | llm
    elif template_id == "code_review":
        chain = code_review_prompt | llm
    else:
        raise ValueError(f"未知的模板ID: {template_id}")

    result = chain.invoke(variables)
    return result.content
