"""
前端转全栈 06: 文件上传与多模态图片处理 (FormData vs UploadFile)
==================================================================
在多模态 AI 应用（如 GPT-4 Vision 图片识别、文档 RAG 上传、语音文件转写）中，
文件上传是全栈开发的刚需！

前端提交方式: `const formData = new FormData(); formData.append("file", fileObject);`
后端接收方式: FastAPI `UploadFile = File(...)`

运行方法：python 06_文件上传与多模态图片处理_FormData对比.py
"""

import os
import shutil
from typing import List

try:
    from fastapi import FastAPI, File, UploadFile, HTTPException, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 请安装依赖 `pip install fastapi uvicorn python-multipart`。")


if HAS_FASTAPI:
    app = FastAPI(title="全栈文件上传与多模态处理 API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 上传文件存储目录
    UPLOAD_DIR = "uploaded_files"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 允许访问上传的静态文件 (相当于 Express: app.use('/static', express.static('uploads')))
    app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

    # 限制扩展名与大小
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".markdown"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


    # === 1. 单文件上传接口 ===
    # 前端: axios.post('/api/upload', formData)
    @app.post("/api/upload")
    async def upload_file(
        file: UploadFile = File(..., description="上传的文件对象"),
        prompt: str = Form("分析这张图片", description="伴随文件提交的文本参数 (Form Data)")
    ):
        # 1. 检查扩展名
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")

        # 2. 保存文件到本地
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. 模拟多模态 AI 识别处理
        ai_multimodal_summary = f"多模态 AI 识别完成！提示词: '{prompt}', 文件: {file.filename}, 大小: {os.path.getsize(save_path)} bytes"

        return {
            "success": True,
            "filename": file.filename,
            "content_type": file.content_type,
            "url": f"http://127.0.0.1:8000/static/{file.filename}",
            "ai_analysis": ai_multimodal_summary
        }


    # === 2. 多文件批量上传接口 ===
    # 前端: files.forEach(f => formData.append("files", f))
    @app.post("/api/upload-batch")
    async def upload_batch_files(files: List[UploadFile] = File(...)):
        uploaded_list = []
        for file in files:
            save_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_list.append({
                "filename": file.filename,
                "url": f"http://127.0.0.1:8000/static/{file.filename}"
            })
        
        return {"success": True, "total": len(uploaded_list), "files": uploaded_list}

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动文件上传服务器: http://127.0.0.1:8000")
        print("📁 静态文件可访问路径: http://127.0.0.1:8000/static/<filename>")
        uvicorn.run(app, host="127.0.0.1", port=8000)
