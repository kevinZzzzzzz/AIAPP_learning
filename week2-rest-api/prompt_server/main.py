"""
Prompt Server —— 提示词管理 REST API
======================================

一个完整的 FastAPI CRUD 服务，用于管理 AI Prompt 模板。

涵盖知识点：
- FastAPI 路由（GET/POST/PUT/DELETE）
- Pydantic 请求/响应模型
- 路径参数 & 查询参数
- 依赖注入
- 异常处理（HTTPException）
- CORS 中间件
- 数据持久化（JSON 文件）

启动方式：
  cd week2-rest-api/prompt_server
  pip install fastapi uvicorn pydantic
  python main.py

然后访问：
  API 文档: http://localhost:8000/docs
  API:      http://localhost:8000/api/v1/prompts
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator


# ====================== 1. 数据模型（Pydantic） ======================

class PromptCreate(BaseModel):
    """创建 Prompt 的请求体 —— 前端提交的数据"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Prompt 名称",
        examples=["Python 代码审查助手"],
    )
    system_prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="System Prompt 内容",
    )
    category: str = Field(
        default="通用",
        min_length=1,
        max_length=50,
        description="分类标签",
        examples=["代码", "写作", "翻译"],
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="标签列表",
        examples=[["Python", "代码审查"]],
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM 温度参数",
    )

    @field_validator("tags")
    @classmethod
    def tags_must_be_unique(cls, v: list[str]) -> list[str]:
        """自定义校验：标签不能重复"""
        if len(v) != len(set(v)):
            raise ValueError("标签不能重复")
        return v


class PromptUpdate(BaseModel):
    """更新 Prompt 的请求体 —— 所有字段可选"""
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)


class PromptResponse(BaseModel):
    """返回给前端的 Prompt 数据"""
    id: str
    name: str
    system_prompt: str
    category: str
    tags: list[str]
    temperature: float
    created_at: str
    updated_at: str
    usage_count: int


class PromptListResponse(BaseModel):
    """Prompt 列表响应 + 分页信息"""
    items: list[PromptResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    detail: Optional[str] = None


# ====================== 2. 数据存储层 ======================

DATA_FILE = Path(__file__).parent / "data" / "prompts.json"


class PromptStore:
    """Prompt 数据存储 —— 用 JSON 文件模拟数据库
    
    对应关系：
    - PromptStore.read_all()      ≈  SQL SELECT * FROM prompts
    - PromptStore.read_by_id()    ≈  SQL SELECT * WHERE id = ?
    - PromptStore.create()        ≈  SQL INSERT INTO prompts
    - PromptStore.update()        ≈  SQL UPDATE prompts SET ... WHERE id = ?
    - PromptStore.delete()        ≈  SQL DELETE FROM prompts WHERE id = ?
    """

    def __init__(self):
        DATA_FILE.parent.mkdir(exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        """确保数据文件存在"""
        if not DATA_FILE.exists():
            DATA_FILE.write_text("{}", encoding="utf-8")

    def _load(self) -> dict:
        """从文件加载所有数据"""
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def _save(self, data: dict):
        """保存数据到文件"""
        DATA_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---- CRUD 操作 ----

    def read_all(
        self,
        page: int = 1,
        page_size: int = 10,
        category: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict:
        """分页查询 + 过滤 + 搜索"""
        data = self._load()
        items = list(data.values())

        # 按分类过滤
        if category:
            items = [p for p in items if p["category"] == category]

        # 按关键词搜索（名称、内容、标签）
        if search:
            search_lower = search.lower()
            filtered = []
            for p in items:
                if (
                    search_lower in p["name"].lower()
                    or search_lower in p["system_prompt"].lower()
                    or any(search_lower in t.lower() for t in p.get("tags", []))
                ):
                    filtered.append(p)
            items = filtered

        # 按更新时间倒序
        items.sort(key=lambda x: x["updated_at"], reverse=True)

        # 分页
        total = len(items)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        paged = items[start:start + page_size]

        return {
            "items": paged,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    def read_by_id(self, prompt_id: str) -> Optional[dict]:
        """根据 ID 查询单条记录"""
        data = self._load()
        return data.get(prompt_id)

    def create(self, prompt_data: PromptCreate) -> dict:
        """创建新记录"""
        data = self._load()

        prompt_id = str(uuid.uuid4())[:8]  # 8位短 ID
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "id": prompt_id,
            "name": prompt_data.name,
            "system_prompt": prompt_data.system_prompt,
            "category": prompt_data.category,
            "tags": prompt_data.tags,
            "temperature": prompt_data.temperature,
            "created_at": now,
            "updated_at": now,
            "usage_count": 0,
        }

        data[prompt_id] = record
        self._save(data)
        return record

    def update(self, prompt_id: str, update_data: PromptUpdate) -> dict:
        """更新记录（部分更新）"""
        data = self._load()

        if prompt_id not in data:
            return None

        record = data[prompt_id]

        # 只更新传入的字段（PATCH 语义）
        update_dict = update_data.model_dump(exclude_unset=True)
        record.update(update_dict)
        record["updated_at"] = datetime.now(timezone.utc).isoformat()

        data[prompt_id] = record
        self._save(data)
        return record

    def delete(self, prompt_id: str) -> bool:
        """删除记录"""
        data = self._load()

        if prompt_id not in data:
            return False

        del data[prompt_id]
        self._save(data)
        return True

    def increment_usage(self, prompt_id: str) -> Optional[dict]:
        """使用次数 +1"""
        data = self._load()
        if prompt_id not in data:
            return None

        data[prompt_id]["usage_count"] += 1
        self._save(data)
        return data[prompt_id]

    def get_categories(self) -> list[str]:
        """获取所有分类"""
        data = self._load()
        categories = {p.get("category", "未分类") for p in data.values()}
        return sorted(categories)

    def get_stats(self) -> dict:
        """获取统计信息"""
        data = self._load()
        items = list(data.values())
        
        categories = {}
        total_usage = 0
        for p in items:
            cat = p.get("category", "未分类")
            categories[cat] = categories.get(cat, 0) + 1
            total_usage += p.get("usage_count", 0)

        return {
            "total_prompts": len(items),
            "total_usage": total_usage,
            "categories": categories,
            "avg_tags": round(
                sum(len(p.get("tags", [])) for p in items) / max(len(items), 1), 1
            ),
        }


# ====================== 3. FastAPI 应用 ======================

app = FastAPI(
    title="Prompt Server API",
    description="AI Prompt 模板管理服务 — 支持 CRUD、搜索、分页、统计",
    version="1.0.0",
)

# CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境放行所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局数据存储（依赖注入）
def get_store() -> PromptStore:
    """依赖注入：获取 PromptStore 实例"""
    return PromptStore()


# ====================== 4. API 路由 ======================

@app.get("/", response_model=MessageResponse)
async def root():
    """根路径 —— 健康检查"""
    return {"message": "Prompt Server 运行中", "detail": "访问 /docs 查看 API 文档"}


# ---- Prompts CRUD ----

@app.get("/api/v1/prompts", response_model=PromptListResponse)
async def list_prompts(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(default=None, description="按分类过滤"),
    search: Optional[str] = Query(default=None, description="搜索关键词"),
    store: PromptStore = Depends(get_store),
):
    """获取 Prompt 列表（分页 + 过滤 + 搜索）
    
    示例:
      GET /api/v1/prompts                          → 第1页，10条
      GET /api/v1/prompts?page=2&page_size=20      → 第2页，20条
      GET /api/v1/prompts?category=代码            → 只看"代码"分类
      GET /api/v1/prompts?search=Python            → 搜索含"Python"的
    """
    result = store.read_all(page=page, page_size=page_size, category=category, search=search)
    return result


@app.get("/api/v1/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    store: PromptStore = Depends(get_store),
):
    """获取单个 Prompt 详情
    
    示例: GET /api/v1/prompts/abc123
    """
    record = store.read_by_id(prompt_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} 不存在")
    return record


@app.post("/api/v1/prompts", response_model=PromptResponse, status_code=201)
async def create_prompt(
    prompt: PromptCreate,
    store: PromptStore = Depends(get_store),
):
    """创建新的 Prompt 模板
    
    示例:
      POST /api/v1/prompts
      Body: {
        "name": "代码审查助手",
        "system_prompt": "你是一个资深代码审查员...",
        "category": "代码",
        "tags": ["Python", "审查"]
      }
    """
    record = store.create(prompt)
    return record


@app.put("/api/v1/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    prompt: PromptUpdate,
    store: PromptStore = Depends(get_store),
):
    """更新 Prompt（全量替换）
    
    示例: PUT /api/v1/prompts/abc123
    """
    record = store.update(prompt_id, prompt)
    if not record:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} 不存在")
    return record


@app.patch("/api/v1/prompts/{prompt_id}", response_model=PromptResponse)
async def patch_prompt(
    prompt_id: str,
    prompt: PromptUpdate,
    store: PromptStore = Depends(get_store),
):
    """部分更新 Prompt（只更新传入的字段）
    
    示例: PATCH /api/v1/prompts/abc123
    Body: { "temperature": 0.5 }
    """
    record = store.update(prompt_id, prompt)
    if not record:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} 不存在")
    return record


@app.delete("/api/v1/prompts/{prompt_id}", response_model=MessageResponse)
async def delete_prompt(
    prompt_id: str,
    store: PromptStore = Depends(get_store),
):
    """删除 Prompt
    
    示例: DELETE /api/v1/prompts/abc123
    """
    success = store.delete(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} 不存在")
    return {"message": f"Prompt {prompt_id} 已删除"}


# ---- 使用统计 ----

@app.post("/api/v1/prompts/{prompt_id}/use", response_model=PromptResponse)
async def use_prompt(
    prompt_id: str,
    store: PromptStore = Depends(get_store),
):
    """记录一次 Prompt 使用（usage_count +1）
    
    示例: POST /api/v1/prompts/abc123/use
    """
    record = store.increment_usage(prompt_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} 不存在")
    return record


# ---- 分类 & 统计 ----

@app.get("/api/v1/categories")
async def get_categories(
    store: PromptStore = Depends(get_store),
):
    """获取所有分类列表"""
    categories = store.get_categories()
    return {"categories": categories}


@app.get("/api/v1/stats")
async def get_stats(
    store: PromptStore = Depends(get_store),
):
    """获取统计信息"""
    return store.get_stats()


# ---- 批量操作 ----

@app.post("/api/v1/prompts/seed", response_model=MessageResponse)
async def seed_data(
    store: PromptStore = Depends(get_store),
):
    """初始化示例数据（用于学习和测试）"""
    sample_prompts = [
        PromptCreate(
            name="Python 代码审查助手",
            system_prompt="你是一位资深 Python 代码审查员。请审查以下代码，从代码质量、性能、安全、可维护性四个维度给出改进建议。用中文回复。",
            category="代码",
            tags=["Python", "审查", "质量"],
            temperature=0.3,
        ),
        PromptCreate(
            name="中英翻译专家",
            system_prompt="你是一个专业翻译。把用户输入翻译成英文。只输出译文，不要解释。保持原文的语气和风格。",
            category="翻译",
            tags=["翻译", "中英"],
            temperature=0.1,
        ),
        PromptCreate(
            name="技术文档写手",
            system_prompt="你是一位专业的技术文档写手。请用简洁清晰的中文，使用 Markdown 格式，写出结构良好的技术文档。包含概述、安装步骤、使用示例、API 参考等必要部分。",
            category="写作",
            tags=["文档", "技术写作", "Markdown"],
            temperature=0.5,
        ),
        PromptCreate(
            name="AI 概念大白话解释器",
            system_prompt="你是一个擅长用大白话解释技术概念的导师。请用日常生活中的比喻来解释给定的 AI/编程概念，让完全没有技术背景的人也能听懂。先给一句话总结，再给比喻，最后给一个简单的代码示例。",
            category="学习",
            tags=["教学", "AI", "科普"],
            temperature=0.7,
        ),
        PromptCreate(
            name="SQL 查询生成器",
            system_prompt="你是一个 SQL 专家。根据用户用自然语言描述的查询需求，生成对应的 SQL 语句。只输出 SQL，用代码块包裹。需要时加上注释。",
            category="代码",
            tags=["SQL", "数据库", "代码生成"],
            temperature=0.2,
        ),
    ]

    created = []
    for p in sample_prompts:
        record = store.create(p)
        created.append(record["name"])

    return {
        "message": f"已初始化 {len(created)} 条示例数据",
        "detail": str(created),
    }


# ====================== 5. 启动入口 ======================

if __name__ == "__main__":
    import uvicorn

    print("""
╔══════════════════════════════════════════════╗
║     Prompt Server — 提示词管理 API           ║
║                                              ║
║  📡 API:     http://localhost:8000            ║
║  📖 Swagger: http://localhost:8000/docs       ║
║  📖 ReDoc:   http://localhost:8000/redoc      ║
║                                              ║
║  快速测试:                                    ║
║  curl http://localhost:8000/api/v1/prompts    ║
║  curl -X POST .../api/v1/prompts/seed        ║
╚══════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
