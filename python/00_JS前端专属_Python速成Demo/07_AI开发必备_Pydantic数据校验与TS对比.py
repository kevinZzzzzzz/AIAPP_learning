"""
Pydantic 数据校验与规范 —— TS Interface & Zod 对比指南 (🔥 AI 开发核心组件)
========================================================================
如果你在前端用过 TypeScript 或 Zod / Yup 校验库，你就会明白“数据模型校验”的重要性。
在 Python 领域，Pydantic 就是绝对的霸主！
- FastAPI 框架用它定义 Request / Response Body。
- LangChain / LlamaIndex 用它定义 Tool 参数 schema。
- OpenAI API (Structured Outputs) 直接接收 Pydantic 模型生成 100% 结构化的 JSON。

运行方法：python 07_AI开发必备_Pydantic数据校验与TS对比.py
"""

from typing import List, Optional, Literal
import json

try:
    from pydantic import BaseModel, Field, field_validator, ValidationError
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    print("⚠️ 提示: 未检测到 `pydantic` 模块。可以通过命令 `pip install pydantic` 进行安装。")
    print("以下为您呈现 Pydantic 与 TS/Zod 的概念对照逻辑：\n")
    # 创建 Dummy 基类防止脚本崩溃
    class BaseModel: pass
    def Field(*args, **kwargs): return None
    def field_validator(*args, **kwargs): return lambda fn: fn
    class ValidationError(Exception): pass


# === 1. 定义 Pydantic 模型 (类似 TS Interface + Zod Schema) ===
"""
TS + Zod 等价代码:
import { z } from "zod";

const UserRoleSchema = z.enum(["admin", "user", "guest"]);

const UserProfileSchema = z.object({
  id: z.string().uuid(),
  username: z.string().min(3, "用户名至少3个字符"),
  age: z.number().int().positive(),
  role: UserRoleSchema.default("user"),
  email: z.string().email().optional(),
});

type UserProfile = z.infer<typeof UserProfileSchema>;
"""

class UserProfile(BaseModel):
    # Field 用于添加限制、默认值、描述 (描述信息会包含在 LLM 生成的 JSON Schema 中！)
    id: str = Field(description="用户唯一标示 ID", examples=["usr_1001"])
    username: str = Field(min_length=3, description="用户名，最少 3 个字符")
    age: int = Field(gt=0, lt=150, description="年龄，必须在 0 到 150 之间")
    role: Literal["admin", "user", "guest"] = "user"
    email: Optional[str] = None
    tags: list[str] = Field(default_factory=list, description="用户标签")

    # 自定义校验器 (类似 Zod .refine())
    @field_validator("username")
    @classmethod
    def validate_no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("用户名不能包含空格！")
        return v.title()  # 自动清洗：将首字母转为大写


# === 2. 实战 AI 场景：大模型 Tool (Function Calling) 定义 ===
"""
定义一个供大模型使用的天气查询工具 Schema
大模型会看到字段的 type, default 和 description 提示词！
"""
class WeatherQueryInput(BaseModel):
    city: str = Field(description="需要查询天气的城市名称，例如：北京、上海、Tokyo")
    unit: Literal["celsius", "fahrenheit"] = Field(default="celsius", description="温度单位：摄氏度或华氏度")
    days: int = Field(default=1, ge=1, le=7, description="预测未来几天天气 (1-7天)")


def demo_pydantic_validation():
    if not HAS_PYDANTIC:
        print("未安装 Pydantic 库，跳过真实校验运行。请运行 `pip install pydantic` 体验完整功能。")
        return

    print("\n--- 1. 正常数据解析与验证 (model_validate) ---")
    
    # 模拟从前端 API 提交过来的 JSON 字典
    raw_api_data = {
        "id": "usr_999",
        "username": "kevin python",  # 校验器会自动转换为 "Kevin Python"
        "age": 28,
        "email": "kevin@example.com",
        "tags": ["AI工程师", "Fullstack"]
    }

    # 实例化对象（如果数据格式不对会直接抛出 ValidationError 报错）
    user = UserProfile(**raw_api_data)
    print("✅ 数据验证成功，自动转为强类型对象:")
    print(f"用户名: {user.username} (类型: {type(user.username)})")
    print(f"年龄: {user.age}")
    print(f"对象转字典 (model_dump / 相当于 JS JSON): {user.model_dump()}")
    print(f"对象转 JSON 字符串: {user.model_dump_json(indent=2)}")

    print("\n--- 2. 异常捕获机制 (捕获校验失败) ---")
    bad_data = {
        "id": "usr_001",
        "username": "ab",  # ❌ 长度 < 3 抛错
        "age": -5          # ❌ age <= 0 抛错
    }
    
    try:
        UserProfile(**bad_data)
    except ValidationError as e:
        print("❌ 捕获到 Pydantic 校验错误 (结构与错误原因):")
        for err in e.errors():
            print(f"  - 字段 `{err['loc'][0]}`: {err['msg']}")


def demo_ai_tool_schema():
    if not HAS_PYDANTIC:
        return
    print("\n--- 3. 导出大模型所需的 JSON Schema (OpenAI / LangChain 机制) ---")
    
    # Pydantic 模型可以一键生成 JSON Schema！大模型就是靠这个知道该如何调用函数的！
    schema = WeatherQueryInput.model_json_schema()
    import json
    print("生成的大模型 Tool Schema:")
    print(json.dumps(schema, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    print("==================================================")
    print("  Pydantic 数据校验与 TS/Zod 对比 Demo")
    print("==================================================")
    demo_pydantic_validation()
    demo_ai_tool_schema()
