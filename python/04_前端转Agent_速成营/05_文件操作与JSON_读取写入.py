# 05_文件操作与JSON_读取写入.py

"""
第 5 课：文件 I/O 与 JSON 解析
对应 Node.js 中的：fs.readFile, fs.writeFile, JSON.parse, JSON.stringify
重要性：⭐⭐⭐⭐
在 AI Agent 开发中，你经常需要读取本地文档（如 Markdown、PDF）给大模型做 RAG，
或者将大模型生成的配置、分析报告保存到本地，以及解析大模型返回的复杂 JSON 字符串。
"""

import json
import os

def file_io_demo():
    print("--- 1. 文本文件的读写 (替代 Node 的 fs 模块) ---")
    
    # 模拟我们要处理的文件路径
    file_path = "demo_document.txt"
    
    # 【写入文件】
    # Python 强推使用 `with open(...) as f` 语法，这叫上下文管理器。
    # 它的好处是：代码块执行完毕或发生异常时，会自动帮你 close() 文件，防止内存/句柄泄漏。
    # mode="w" 是覆盖写入，"a" 是追加，encoding="utf-8" 是必须的（尤其在 Windows 上）。
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write("这是第一行，用于 AI 的知识库素材。\n")
        f.write("这是第二行。\n")
    print(f"✅ 文件已成功写入: {file_path}")

    # 【读取文件】
    # mode="r" 是只读模式
    with open(file_path, mode="r", encoding="utf-8") as f:
        # .read() 读全部，.readlines() 读成数组，.read(100) 读前 100 字符
        content = f.read()
    print(f"📖 读取文件内容:\n{content}")
    
    # 演示完后清理文件
    if os.path.exists(file_path):
        os.remove(file_path)


def json_demo():
    print("--- 2. JSON 处理 (对应 JSON.parse / JSON.stringify) ---")
    
    # 模拟大模型 Tool Calling 返回的字符串
    llm_json_string = '{"action": "search_web", "query": "Python 异步编程", "limit": 5}'
    
    # JSON.parse(str) -> json.loads(str) (loads = load string)
    try:
        parsed_data = json.loads(llm_json_string)
        print(f"🔍 解析后的字典类型: {type(parsed_data)}")
        print(f"   动作: {parsed_data['action']}, 关键词: {parsed_data['query']}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败，这在处理大模型输出时经常发生: {e}")
        
    # JSON.stringify(obj) -> json.dumps(obj) (dumps = dump string)
    response_obj = {
        "status": "success",
        "data": ["文章1", "文章2"],
        "cost": 0.02
    }
    # ensure_ascii=False 是为了让中文正常显示而不是变成 \u4e2d\u6587
    # indent=2 是为了格式化输出漂亮
    json_str = json.dumps(response_obj, ensure_ascii=False, indent=2)
    print(f"\n📦 序列化后的 JSON 字符串:\n{json_str}")


if __name__ == "__main__":
    file_io_demo()
    print("\n")
    json_demo()
