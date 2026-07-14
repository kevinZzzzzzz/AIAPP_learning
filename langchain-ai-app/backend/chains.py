"""
链式调用模块 - 文章 2.3 实操3
将多个 LLM 调用串联成流水线，前一输出作为后一输入
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL


def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        openai_api_base=OPENAI_BASE_URL,
        temperature=0.7,
    )


# ---------- 链1：头脑风暴 --> 方案评估 ----------
IDEATION_TEMPLATE = """
你是一位产品创新顾问。针对以下主题，列出 3 个有创意的方案：

主题：{topic}

请用简洁的方式列出 3 个方案，编号 1、2、3，每个一行。
"""

EVALUATION_TEMPLATE = """
请评估以下方案的可行性、创新性和实施难度：

方案列表：
{ideas}

请对每个方案按可行性(1-10)、创新性(1-10)、实施难度(1-10，1=最简单)给出评分和简短理由。
"""

ideation_prompt = PromptTemplate(
    input_variables=["topic"],
    template=IDEATION_TEMPLATE,
)

evaluation_prompt = PromptTemplate(
    input_variables=["ideas"],
    template=EVALUATION_TEMPLATE,
)


def brainstorm_and_evaluate(topic: str) -> dict:
    llm = get_llm()
    ideas_chain = ideation_prompt | llm
    ideas_result = ideas_chain.invoke({"topic": topic})
    ideas_text = ideas_result.content
    eval_chain = evaluation_prompt | llm
    eval_result = eval_chain.invoke({"ideas": ideas_text})
    eval_text = eval_result.content
    return {"topic": topic, "ideas": ideas_text, "evaluation": eval_text}


# ---------- 链2：代码生成 --> 代码优化 ----------
CODE_GEN_TEMPLATE = """
生成一段 {language} 代码，功能描述如下：
{description}

直接输出代码，不要额外解释。
"""

CODE_OPT_TEMPLATE = """
请对以下代码进行优化，使其更简洁、高效：

```{language}
{code}
```

输出优化后的代码，并简要说明优化点。
"""

code_gen_prompt = PromptTemplate(
    input_variables=["language", "description"],
    template=CODE_GEN_TEMPLATE,
)

code_opt_prompt = PromptTemplate(
    input_variables=["language", "code"],
    template=CODE_OPT_TEMPLATE,
)


def generate_and_optimize(language: str, description: str) -> dict:
    llm = get_llm()
    gen_chain = code_gen_prompt | llm
    gen_result = gen_chain.invoke({"language": language, "description": description})
    code_text = gen_result.content
    opt_chain = code_opt_prompt | llm
    opt_result = opt_chain.invoke({"language": language, "code": code_text})
    opt_text = opt_result.content
    return {"language": language, "original_code": code_text, "optimized_result": opt_text}


def get_available_chains() -> list[dict]:
    return [
        {
            "id": "brainstorm",
            "label": "头脑风暴评估链",
            "description": "先针对主题生成创意方案，再对方案进行可行性评估",
            "variables": [{"name": "topic", "label": "主题", "type": "text"}],
        },
        {
            "id": "code_gen_opt",
            "label": "代码生成优化链",
            "description": "先根据描述生成代码，再对代码进行优化",
            "variables": [
                {"name": "language", "label": "编程语言", "type": "text"},
                {"name": "description", "label": "功能描述", "type": "text"},
            ],
        },
    ]
