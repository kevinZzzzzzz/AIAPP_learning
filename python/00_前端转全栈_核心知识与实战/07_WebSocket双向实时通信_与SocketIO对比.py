"""
前端转全栈 07: WebSocket 双向实时通信 (对比 Socket.IO / ws)
==================================================================
对于语音 AI Agent (Voice AI)、实时多用户协作、即时心跳与推送应用，
传统的 HTTP 已经不能满足需求，需要全双工通信 protocol: `ws://` 或 `wss://`。

前端原生调用: `const ws = new WebSocket("ws://127.0.0.1:8000/ws/chat/user1");`
后端实现框架: FastAPI `@app.websocket("/ws/{client_id}")`

运行方法：python 07_WebSocket双向实时通信_与SocketIO对比.py
"""

import asyncio
from typing import List, Dict

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("⚠️ 提示: 请安装 `pip install fastapi uvicorn websockets`。")


if HAS_FASTAPI:
    app = FastAPI(title="WebSocket 实时通信 API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === 1. WebSocket 连接管理器 (Connection Manager) ===
    # 在 Node.js 中相当于 Socket.IO 的 io.sockets / Room 管理器
    class ConnectionManager:
        def __init__(self):
            # 存储在线客户端: { client_id: WebSocket }
            self.active_connections: Dict[str, WebSocket] = {}

        async def connect(self, client_id: str, websocket: WebSocket):
            await websocket.accept()  # 接受连接握手
            self.active_connections[client_id] = websocket
            print(f"🟢 客户端 [{client_id}] 已上线，当前在线数: {len(self.active_connections)}")

        def disconnect(self, client_id: str):
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                print(f"🔴 客户端 [{client_id}] 已下线")

        async def send_personal_message(self, message: str, websocket: WebSocket):
            """单播 (发送给特定客户端)"""
            await websocket.send_text(message)

        async def broadcast(self, message: str, sender_id: str = "System"):
            """广播 (发送给所有连接中的客户端)"""
            formatted = f"[{sender_id}]: {message}"
            for client_id, connection in list(self.active_connections.items()):
                try:
                    await connection.send_text(formatted)
                except Exception:
                    self.disconnect(client_id)

    manager = ConnectionManager()


    # === 2. WebSocket 端点路由 ===
    @app.websocket("/ws/chat/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        await manager.connect(client_id, websocket)
        
        # 建立连接后发送欢迎消息
        await manager.send_personal_message(
            f"欢迎进入 Python FastAPI WebSocket 实时房间！你的 Client ID 是: {client_id}", 
            websocket
        )
        await manager.broadcast(f"用户 `{client_id}` 加入了房间", sender_id="系统通知")

        try:
            while True:
                # 持续循环等待客户端发送消息 (对应前端 ws.send("hello"))
                data = await websocket.receive_text()
                print(f"收到 [{client_id}] 消息: {data}")
                
                # 模拟 AI Agent 实时回应或广播给其他在线用户
                if data.startswith("/ai "):
                    prompt = data.replace("/ai ", "")
                    await manager.send_personal_message(f"🤖 [AI 回复]: 收到你的指令 '{prompt}'", websocket)
                else:
                    await manager.broadcast(data, sender_id=client_id)

        except WebSocketDisconnect:
            manager.disconnect(client_id)
            await manager.broadcast(f"用户 `{client_id}` 离开了房间", sender_id="系统通知")

else:
    app = None


if __name__ == "__main__":
    if HAS_FASTAPI:
        import uvicorn
        print("🚀 启动 WebSocket 服务器: ws://127.0.0.1:8000/ws/chat/{client_id}")
        uvicorn.run(app, host="127.0.0.1", port=8000)
