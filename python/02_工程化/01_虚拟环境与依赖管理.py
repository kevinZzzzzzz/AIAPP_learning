"""
Python 工程化基础：虚拟环境、依赖管理、项目结构
=================================================================

前端开发者对比：
- npm init / package.json  ≈  pyproject.toml / requirements.txt
- node_modules             ≈  .venv（虚拟环境目录）
- npm install              ≈  pip install
- npx                      ≈  pipx / python -m
"""

# ======================== 1. 虚拟环境（Virtual Environment） ========================

"""
虚拟环境 = 项目级别的 Python 解释器 + 依赖隔离
相当于每个项目有自己的 node_modules，不共享

创建虚拟环境：
    python -m venv .venv
    
激活虚拟环境：
    Windows:  .venv\Scripts\activate
    Mac/Linux: source .venv/bin/activate
    
验证是否处于虚拟环境中：
    where python    # Windows 应指向 .venv 目录
    which python    # Mac/Linux

退出虚拟环境：
    deactivate

最佳实践：
    1. 每个项目一个虚拟环境
    2. .venv/ 加入 .gitignore
    3. 提交 requirements.txt，不提交 .venv/ 目录
"""


# ======================== 2. 依赖管理文件 ========================

"""
requirements.txt → 类似 package.json 的 dependencies

生成方式：
    pip freeze > requirements.txt    # 导出当前环境所有包
    # 或者手动写

示例 requirements.txt:
---
openai>=1.0.0,<2.0.0
httpx>=0.25.0
pydantic>=2.0.0
langchain>=0.1.0
fastapi>=0.100.0
uvicorn[standard]
python-dotenv>=1.0.0
chromadb>=0.4.0
---

安装依赖：
    pip install -r requirements.txt

更现代的方式：pyproject.toml（类似 package.json + tsconfig.json 合体）
    pip install -e .        # 以开发模式安装当前项目
"""


# ======================== 3. 环境变量管理（python-dotenv） ========================

"""
AI 开发必须管理 API Key！永远不要把 key 硬编码在代码里。

# .env 文件（加入 .gitignore！！！）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
DATABASE_URL=postgresql://localhost/mydb

# Python 中读取：
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件到环境变量
api_key = os.getenv("OPENAI_API_KEY")  # 读取

if not api_key:
    raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

注意：.env 必须加入 .gitignore，防止提交到 git！
"""


# ======================== 4. Python 包与模块导入 ========================

"""
项目目录结构示例：

my_ai_project/
├── .venv/                  # 虚拟环境（gitignore）
├── .env                    # 环境变量（gitignore）
├── .gitignore
├── requirements.txt
├── pyproject.toml          # 项目元数据
├── README.md
├── src/
│   ├── __init__.py         # 标记 src 为 Python 包
│   ├── main.py             # 入口文件
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py       # LLM 客户端封装
│   │   └── prompts.py      # Prompt 模板
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embedding.py    # Embedding 服务
│   │   ├── retriever.py    # 检索器
│   │   └── chunker.py      # 文档切片
│   └── utils/
│       ├── __init__.py
│       └── logger.py       # 日志工具
└── tests/
    ├── __init__.py
    ├── test_llm.py
    └── test_rag.py

__init__.py 的作用：
1. 标记目录为 Python 包（Python 3.3+ 非必需但推荐）
2. 控制 from package import * 的行为
3. 可以放初始化代码

导入规则：
    from src.llm.client import LLMClient        # 绝对导入（推荐）
    from .client import LLMClient               # 相对导入（包内部用）
"""


# ======================== 5. 日志配置 ========================

import logging

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """标准日志配置 —— AI 应用的调试全靠它"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # 防止重复添加 handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    
    return logger


# ======================== 6. 有用的内置模块速查 ========================

"""
pathlib — 现代路径处理（替代 os.path）
"""
from pathlib import Path

def demo_pathlib():
    # 路径拼接（和 JS 的 path.join 类似）
    project_dir = Path(__file__).parent.parent  # 项目根目录
    env_file = project_dir / ".env"
    data_dir = project_dir / "data"
    
    # 创建目录
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 读写文件
    # content = (data_dir / "example.txt").read_text(encoding="utf-8")
    # (data_dir / "output.txt").write_text("Hello", encoding="utf-8")
    
    # 遍历文件
    # for file in data_dir.glob("*.txt"):
    #     print(file.name)


"""
json — JSON 处理（JS 开发者直接上手）
"""
import json

def demo_json():
    # Python → JSON（序列化）
    data = {"name": "Alice", "age": 30, "skills": ["Python", "AI"]}
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    print(json_str)
    
    # JSON → Python（反序列化）
    parsed = json.loads(json_str)
    print(parsed["name"])


"""
dataclasses — 数据类（前面已详述，这里强调实战用法）
"""
@dataclass
class LLMConfig:
    """LLM 配置的数据类 —— 集中管理所有配置"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096
    base_url: str = "https://api.openai.com/v1"
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        import os
        return cls(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    
    def to_openai_kwargs(self) -> dict:
        """转换为 OpenAI SDK 的参数格式"""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


if __name__ == "__main__":
    demo_json()
    print()
    
    # 配置示例
    config = LLMConfig()
    print(f"Provider: {config.provider}")
    print(f"Model: {config.model}")
    print(f"SDK kwargs: {config.to_openai_kwargs()}")
    
    print("\n💡 提示: 运行 'pip install python-dotenv' 来安装环境变量管理包")
