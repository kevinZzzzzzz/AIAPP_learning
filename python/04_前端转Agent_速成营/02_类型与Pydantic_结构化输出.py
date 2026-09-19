# 02_类型与Pydantic_结构化输出.py

"""
第 3-5 天：Pydantic 与类型系统 (Type Hints)
对标前端：TypeScript + Zod
重要性：⭐⭐⭐⭐⭐ (极高)
大模型时代的结构化输出 (Structured Output) 和工具调用 (Tool Calling)，
几乎 100% 依赖 JSON Schema，而在 Python 中生成 JSON Schema 的标准就是 Pydantic。
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError

# 1. 定义数据结构模型 (继承 BaseModel)
# 相当于 TS 的 interface 或者 Zod 的 schema
class UserInfo(BaseModel):
    # Field 用于添加元数据、默认值、描述。这些描述会被大模型读取！
    name: str = Field(..., description="用户的全名")  # ... 表示必填
    age: int = Field(..., ge=0, description="用户的年龄，必须大于等于0")
    hobbies: List[str] = Field(default_factory=list, description="用户的爱好列表")
    is_vip: bool = Field(default=False)

# 2. 嵌套模型 (在定义大模型的复杂结构化输出时非常有用)
class AgentResponse(BaseModel):
    thought_process: str = Field(..., description="AI的思考过程")
    extracted_user: UserInfo = Field(..., description="从文本中提取出的用户信息")


def pydantic_demo():
    print("--- 1. 数据校验与实例化 ---")
    
    # 模拟大模型返回的一段 JSON (已经被 json.loads 解析成了字典)
    llm_json_output = {
        "thought_process": "用户提到他叫张三，今年25岁，喜欢打篮球和游泳。",
        "extracted_user": {
            "name": "张三",
            "age": 25,
            "hobbies": ["打篮球", "游泳"]
            # is_vip 没传，会使用默认值 False
        }
    }
    
    try:
        # 将字典转换为 Pydantic 对象，自动进行深度类型校验
        response_obj = AgentResponse(**llm_json_output)
        
        # 现在你可以像访问对象属性一样，安全地获取数据，并且 IDE 会有完美的代码补全！
        print(f"AI 思考过程: {response_obj.thought_process}")
        print(f"提取的用户姓名: {response_obj.extracted_user.name}")
        print(f"是否是 VIP: {response_obj.extracted_user.is_vip}")
        
    except ValidationError as e:
        print("大模型输出的数据格式不符合要求！")
        print(e.json())
        
    print("\n--- 2. 导出 JSON Schema (给大模型 Tool Calling 用) ---")
    # 这就是为什么所有 Agent 框架都用 Pydantic 的原因：
    # 它可以一键导出 OpenAI 支持的 JSON Schema 格式
    schema = UserInfo.model_json_schema()
    import json
    print(json.dumps(schema, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    pydantic_demo()
