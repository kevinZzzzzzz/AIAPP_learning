"""
Pydantic 数据验证详解
=================================================================

Pydantic 是 AI 开发中最常用的数据验证库，用途：
1. 校验 API 请求/响应数据
2. 定义配置模型
3. 结构化 LLM 输出（OpenAI JSON Mode + Pydantic）
4. 定义 Function Calling 的参数 Schema

前端对比：Pydantic ≈ TypeScript 的 interface + Zod/Runtypes
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Annotated
from datetime import datetime
import json


# ======================== 1. BaseModel 基础 ========================

class User(BaseModel):
    """Pydantic BaseModel = 带运行时验证的 TS interface"""
    name: str
    age: int = Field(ge=0, le=150, description="用户年龄")
    email: str
    tags: list[str] = []

# 创建实例
user = User(name="张三", age=30, email="zhangsan@example.com")

# 自动类型转换：str → int
user2 = User(name="李四", age="25", email="lisi@example.com")  # "25" 会被转成 25

# 序列化为 dict
print(user.model_dump())  # {'name': '张三', 'age': 30, 'email': 'zhangsan@example.com', 'tags': []}

# 序列化为 JSON
print(user.model_dump_json())  # JSON 字符串

# 校验失败会抛出 ValidationError
try:
    User(name="王五", age=-1, email="wang@test.com")  # age < 0
except Exception as e:
    print(f"校验失败: {e}")


# ======================== 2. Field 约束 ========================

class LLMRequest(BaseModel):
    """AI 开发中最常见的结构 —— LLM 请求"""
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    messages: list[dict] = Field(min_length=1, description="消息列表")
    temperature: float = Field(
        default=0.7,
        ge=0.0,    # >= 0
        le=2.0,    # <= 2
        description="采样温度，越高越随机"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        gt=0,      # > 0
        le=128000,
        description="最大输出 token 数"
    )
    stream: bool = Field(default=False)

# JSON Schema 自动生成（Function Calling 的核心！）
print("LLMRequest Schema:", LLMRequest.model_json_schema())


# ======================== 3. 嵌套模型 ========================

class ToolParameter(BaseModel):
    """Function Calling 的工具参数定义"""
    name: str
    type: str = "string"
    description: str
    required: bool = True

class ToolDefinition(BaseModel):
    """Function Calling 的工具定义 —— 和 OpenAI API 格式一致"""
    name: str
    description: str
    parameters: list[ToolParameter]

class ChatCompletionRequest(BaseModel):
    """完整的 Chat Completion 请求"""
    model: str = "gpt-4o-mini"
    messages: list[dict]
    tools: Optional[list[ToolDefinition]] = None
    temperature: float = 0.7
    stream: bool = False


# ======================== 4. 自定义校验器 ========================

class UserRegistration(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    confirm_password: str
    email: str
    age: int
    
    @field_validator("username")
    @classmethod
    def username_must_be_alphanumeric(cls, v: str) -> str:
        """字段级校验器：验证单个字段"""
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v
    
    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("邮箱格式不正确")
        return v
    
    @model_validator(mode="after")
    def passwords_must_match(self):
        """模型级校验器：验证多个字段之间的关系"""
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


# ======================== 5. 实战：LLM 结构化输出 ========================

class SentimentResult(BaseModel):
    """让 LLM 输出情感分析结果 —— 用 Pydantic 约束格式"""
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    keywords: list[str]
    summary: str


class EntityExtraction(BaseModel):
    """实体提取的结果结构"""
    entities: list[dict] = Field(
        description="提取到的实体列表",
        example=[{"name": "张三", "type": "person", "mention": "text"}]
    )
    total_count: int
    confidence: float = Field(ge=0.0, le=1.0)


# ======================== 6. 从 dict 创建模型（API Response 解析） ========================

def parse_llm_response(response_text: str) -> Optional[SentimentResult]:
    """解析 LLM 返回的 JSON 字符串 —— 常见操作"""
    try:
        data = json.loads(response_text)
        return SentimentResult(**data)  # ** 展开 dict 为关键字参数
    except (json.JSONDecodeError, Exception) as e:
        print(f"解析失败: {e}")
        return None


# ======================== 7. model_config 配置 ========================

class StrictUser(BaseModel):
    model_config = {
        "extra": "forbid",            # 禁止额外字段（TS 的 exactOptionalPropertyTypes）
        "str_strip_whitespace": True, # 自动去除字符串两端空白
        "validate_default": True,     # 默认值也要校验
    }
    name: str
    age: int
    email: str


# ======================== 8. 泛型模型（Generic Model） ========================

from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应 —— 类似 TS 的 PaginatedResponse<T>"""
    items: list[T]
    total: int
    page: int
    page_size: int
    
    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total


class UserItem(BaseModel):
    id: int
    name: str

# 使用泛型
PaginatedUserResponse = PaginatedResponse[UserItem]


if __name__ == "__main__":
    # 测试基础用法
    user = User(name="测试用户", age=25, email="test@example.com")
    print(f"User dict: {user.model_dump()}")
    
    # 测试 Schema 生成
    schema = LLMRequest.model_json_schema()
    print(f"\nSchema properties: {list(schema['properties'].keys())}")
    
    # 测试校验
    try:
        UserRegistration(
            username="user@1",     # 包含特殊字符
            password="12345678",
            confirm_password="12345678",
            email="test@test.com",
            age=25,
        )
    except Exception as e:
        print(f"\n校验错误: {e}")
    
    # 解析 LLM 输出
    fake_response = json.dumps({
        "sentiment": "positive",
        "confidence": 0.95,
        "keywords": ["Python", "AI"],
        "summary": "这个技术很有前景"
    })
    result = parse_llm_response(fake_response)
    if result:
        print(f"\n情感分析: {result.sentiment}, 置信度: {result.confidence}")
