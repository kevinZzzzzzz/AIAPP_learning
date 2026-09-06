import json
from pydantic import BaseModel, Field

# 模拟大模型调用返回 JSON 字符串
def mock_llm_json_call(prompt):
    # 真实情况是通过 API 传参 response_format={ "type": "json_object" }
    print(f"[API] 正在请求提取信息: {prompt}")
    return '{"name": "Kevin", "skills": ["React", "Vue", "TypeScript"], "years_of_experience": 3}'

class DeveloperProfile(BaseModel):
    name: str = Field(description="开发者的名字")
    skills: list[str] = Field(description="掌握的技术栈")
    years_of_experience: int = Field(description="工作年限")

def main():
    print("--- 结构化输出示例：把自然语言变成前端好处理的 JSON/对象 ---")
    
    text = "我叫Kevin，做了3年前端了，平时主要用React和Vue，当然TS也是必须的。"
    
    # 1. 大模型返回 JSON 字符串
    json_str = mock_llm_json_call(text)
    
    # 2. 解析 JSON
    data_dict = json.loads(json_str)
    
    # 3. 使用 Pydantic 进行校验，将其转化为强类型的对象 (极度推荐！)
    # 这就像你在前端收到了后端的 API 数据，然后用 Zod 进行校验一样
    profile = DeveloperProfile(**data_dict)
    
    print("\n✅ 成功提取结构化数据:")
    print(f"姓名: {profile.name}")
    print(f"技能: {profile.skills}")
    print(f"经验: {profile.years_of_experience} 年")
    
    # 如果数据类型不对，Pydantic 会立刻报错，避免前端渲染时出现 undefined 导致白屏

if __name__ == "__main__":
    main()
