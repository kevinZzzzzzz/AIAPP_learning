# 注意：运行此文件需要先安装 diskcache: pip install diskcache
import time
from diskcache import Cache

def mock_llm_api_call(prompt):
    """模拟一个耗时且费钱的大模型 API 调用"""
    print(f"\n[API 真实调用] 正在向大模型发送请求: '{prompt}' ...")
    time.sleep(2) # 模拟网络延迟
    return f"这是关于 '{prompt}' 的详细回答。 (生成时间: {time.time()})"

def main():
    print("--- 键值缓存 (Redis替代/DiskCache) 示例：大模型响应缓存 ---")
    
    # 初始化缓存，数据存在本地文件夹 cache_dir 里
    # 真实企业级项目中，这里通常会换成 Redis
    cache = Cache('./llm_cache_dir')
    
    # 我们定义一个带有缓存逻辑的调用函数
    def call_llm_with_cache(prompt):
        # 1. 查缓存（用 prompt 作为 key）
        cached_response = cache.get(prompt)
        
        if cached_response is not None:
            print(f"\n[命中缓存 🚀] '{prompt}' 直接返回结果，不调用API，省钱省时！")
            return cached_response
            
        # 2. 缓存没命中，才去调真实 API
        response = mock_llm_api_call(prompt)
        
        # 3. 调完 API 后，把结果存入缓存 (设置过期时间为 60 秒)
        cache.set(prompt, response, expire=60)
        return response

    # === 测试环节 ===
    prompt1 = "如何学习Python？"
    
    print(">>> 第一次提问：")
    res1 = call_llm_with_cache(prompt1)
    print("结果:", res1)
    
    print("\n>>> 第二次提问（同样的问题）：")
    res2 = call_llm_with_cache(prompt1)
    print("结果:", res2)
    
    print("\n>>> 第三次提问（换个问题）：")
    res3 = call_llm_with_cache("什么是大语言模型？")
    print("结果:", res3)

    # 清理缓存文件夹 (为了演示)
    cache.clear()

if __name__ == "__main__":
    main()
