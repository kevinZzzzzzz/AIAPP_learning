"""
FastAPI 进阶：WebSocket

WebSocket 提供全双工（双向）通信通道。
在 AI 开发中，常常用来实现像 ChatGPT 那样的打字机效果流式输出，
或者实现实时语音/文字对话系统。
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio

app = FastAPI(title="WebSocket 聊天")


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
            var ws = new WebSocket("ws://" + window.location.host + "/ws/chat");
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


@app.get('/')
async def get():
    return HTMLResponse(html)


@app.websocket('/ws/chat')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() # 接受响应连接

    try:
        while True:
            # 接受客户端传来的信息
            data = await websocket.receive_text()
            print(f"收到用户信息： {data}")

            # 模拟ai 思考和流式输出
            reply = f"这是对您说的话 '{data}' 的回复，AI正在进行深度思考"

            for char in reply:
                await asyncio.sleep(.1)
                await websocket.send_text(char)

            # 发送换行符表示本次回答接受
            await websocket.send_text("\\n")
    except WebSocketDisconnect:
        print("客户端已断开连接")