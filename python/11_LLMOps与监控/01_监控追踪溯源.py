# 概念代码：演示 LLMOps 监控与评估
def main():
    print("--- LLMOps 与日志监控 (LangSmith / Langfuse) ---")
    
    print("\n[为什么 AI 应用必须做监控？]")
    print("1. 算账：大模型是按 Token 收费的，前端发送一个请求，后端可能调用了 5 次大模型（比如 Agent 反复思考）。你得知道到底花了多少钱。")
    print("2. 甩锅：用户说 AI 胡说八道，你得查当时的上下文，是不是 Prompt 没写好，或者 RAG 检索出来的外挂知识就是错的。")
    print("3. 延迟分析：一个请求 10 秒才返回，到底是检索数据库慢，还是网络慢，还是大模型回复慢？\n")
    
    print("[如何解决：使用 Langfuse 等工具]")
    print("在代码中，你只需要像埋点一样加上装饰器，例如：")
    print("  @observe()")
    print("  def generate_answer(query):")
    print("      ...")
    print("然后在后台控制面板上，你就能看到一个极其清晰的「瀑布流 (Trace)」，")
    print("每一层调用花了多少毫秒、输入是什么、输出是什么、甚至花了多少美元，都一目了然！")

if __name__ == "__main__":
    main()
