# 概念代码：演示 Python 后端如何与前端深度对接
def main():
    print("--- 现代 AI 应用：前端与后端的握手 ---")
    
    print("\n在开发真实的 AI Web 应用时，Python 通常扮演核心大脑，而前端则是灵魂交互层。")
    print("作为前端开发者，你必须掌握以下两种对接方式：\n")
    
    print("【方式一：Vercel AI SDK 协议对接】")
    print("目前前端开发 AI UI 最火的库就是 Vercel AI SDK (React/Vue均支持)。")
    print("用它，你前端只需要一行代码: `const { messages, input, handleInputChange, handleSubmit } = useChat()`")
    print("而你的 Python 后端 (如 FastAPI) 只需要按它的特定格式 (Data Stream Protocol) 返回流式字符串。")
    print("这极大地减少了前端手写 WebSocket/SSE 和管理状态的痛苦。\n")
    
    print("【方式二：Streamlit / Gradio (无前端代码快速原型)】")
    print("如果你想在 10 分钟内把 Python AI 脚本变成一个漂亮的 Web UI 发给别人体验，")
    print("你根本不需要写 HTML/CSS/JS。")
    print("使用 Streamlit:")
    print("  import streamlit as st")
    print("  st.chat_input('请输入你的问题')")
    print("  st.write('AI的回答...')")
    print("它会自动渲染成一个高度定制的聊天界面！这是 AI 开发者必备的武器。\n")

if __name__ == "__main__":
    main()
