"""
FastAPI 进阶：WebSocket

WebSocket 提供全双工（双向）通信通道。
在 AI 开发中，常常用来实现像 ChatGPT 那样的打字机效果流式输出，
或者实现实时语音/文字对话系统。
"""

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio

app = FastAPI()

# 简单的 HTML 客户端代码，方便在浏览器中测试
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket 测试</title>
    </head>
    <body>
        <h1>WebSocket AI 流式输出模拟</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off" placeholder="输入你想问 AI 的问题..."/>
            <button>发送</button>
        </form>
        <div id="messages" style="margin-top: 20px; font-family: monospace; white-space: pre-wrap;"></div>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws/chat");
            var messageBox = document.getElementById('messages');
            
            ws.onmessage = function(event) {
                // 每次收到消息，追加到页面上
                messageBox.innerHTML += event.data;
            };
            
            function sendMessage(event) {
                var input = document.getElementById("messageText");
                messageBox.innerHTML += "<br/><b>你:</b> " + input.value + "<br/><b>AI:</b> ";
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    # 1. 接受 WebSocket 连接
    await websocket.accept()
    
    try:
        while True:
            # 2. 接收客户端发送的消息
            data = await websocket.receive_text()
            print(f"收到用户消息: {data}")
            
            # 3. 模拟 AI 思考和流式输出（打字机效果）
            reply = f"这是对您说的话 '{data}' 的回复。AI 正在进行深度思考..."
            
            # 将回复拆分成一个个字发送
            for char in reply:
                await asyncio.sleep(0.1) # 模拟每个字的生成延迟
                await websocket.send_text(char)
                
            # 发送换行符表示本次回答结束
            await websocket.send_text("\\n")
            
    except WebSocketDisconnect:
        print("客户端已断开连接")


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("05_WebSocket实时通信:app", host="127.0.0.1", port=8000, reload=True)
