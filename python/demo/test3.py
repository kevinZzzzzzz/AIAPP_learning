from os import curdir
import profile
import json
from typing import Dict, Any, Optional

def demo_1_dict_methods_vs_object_static_methods():
    print("\n--- 1. 字典/对象遍历 (Object.keys/values/entries vs dict.items) ---")
 
    person = {
        "name": "Kevin",
        "role": "Frontend Developer",
        "target": "AI Agent Engineer",
        "level": 5
    }

    # === A. Keys 遍历 ===
    # JS: Object.keys(person).forEach(key => ...)
    print('Keys(所有键)：', list(person.keys()))

    # === B. Values 遍历 ===
    # JS: Object.values(person).forEach(val => ...)
    print("Values(所有值)：", list(person.values()))

    # === C. Key-Value 映射遍历 (最常用) ===
    # JS: Object.entries(person).forEach(([key, val]) => ...)
    print(f"\nItems (键值对解构): {person.items()}")
    for k, v in person.items():
        print(f"   {k} : {v}")

def demo_2_safe_property_access():
    print("\n--- 2. 安全属性访问 (Optional Chaining ?. vs .get) ---")
        
    # 嵌套结构数据 (API 响应常见格式)
    api_response = {
        "status": 200,
        "data": {
            "user": {
                "profile": {
                    "nickname": "AI狂热者"
                    # 没有 email 字段
                }
            }
        }
    }

    # JS 链式可选访问: apiResponse?.data?.user?.profile?.nickname
    # JS: const email = apiResponse?.data?.user?.profile?.email ?? "no-email@test.com";

    # Python 方案 1: 层层 .get() 方法 (推荐用于单层/双层)
    user_data = api_response.get("data", {}).get("user", {})
    profile = user_data.get("profile", {})
    nickname = profile.get("nickname")
    email = profile.get("email", "default_email@domain.com")

    print(f"提取 nickname： {nickname}")
    print(f"提取 email（默认值）： {email}")

    # Python 方案 2: 使用 helper 函数实现深层安全获取 (类似 lodash.get(obj, 'a.b.c'))
    def loadsh_get(d: Dict[str, Any], path: str, default: str) -> Any:
        keys = path.split('.')
        current = d
        for i in keys:
            if isinstance(current, dict) and i in current:
                current = current[i]
            else:
                return default
        return current
    
    deep_email = loadsh_get(api_response, "data.user.profile.email", "not_found")
    print(f"自定义 deep_get 访问深层属性: {deep_email}")

def demo_3_json_serialization():
    print("\n--- 3. JSON 序列化与反序列化 (JSON.stringify / JSON.parse) ---")
    
    # === A. Python 字典转 JSON 字符串 (序列化) ===
    # JS: const jsonStr = JSON.stringify(data, null, 2);
    ai_prompt_payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": "写一段 Python 代码"}
        ],
        "temperature": 0.7,
        "stream": True,
        "metadata": None  # Python None 转为 JSON 的 null
    }

    # 💥 注意：ensure_ascii=False 极其重要！否则中文字符会被编码为 \u4f60\u597d
    # indent=2 相当于 JS JSON.stringify 的第三个参数 2 (格式化缩进)
    json_str = json.dumps(ai_prompt_payload, ensure_ascii=False, indent=1)
    print("Python 字典转 JSON 字符串 (json.dumps):")
    print(json_str)

    # === B. JSON 字符串转 Python 字典 (反序列化) ===
    # JS: const obj = JSON.parse(jsonStr);
    raw_llm_output_json = '{"tool_name": "get_weather", "arguments": {"city": "Beijing"}}'
    parsed_dict = json.loads(raw_llm_output_json)
    print("\n JSON 字符串转 Python 字典 (json.loads):")
    print(f"{parsed_dict} {type(parsed_dict)}")
    
def demo_4_llm_json_parse_error_handling():
    print("\n--- 4. 实战 AI 场景：处理 LLM 返回的不规范 JSON (容错解析) ---")
    
    # 大模型经常返回带有 markdown 标记的 JSON 字符串，例如: ```json { "key": "val" } ```
    bad_llm_response = """
    好的，这是为您生成的结构化数据：
    ```json
    {
        "status": "success",
        "summary": "AI 应用开发上手指南",
        "tags": ["Python", "FastAPI", "React"]
    }
    ```
    希望对您有帮助！
    """
    def clean_and_parse_llm_json(raw_text: str) ->  Optional[Dict[str, Any]]:
        try:
            if "```json" in raw_text:
                json_part = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                json_part = raw_text.split("```")[1].split("```")[0].strip()
            else:
                json_part = raw_text.strip()
            return json.loads(json_part)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"❌ JSON 解析失败: {e}")
            return None 
    clean_data = clean_and_parse_llm_json(bad_llm_response)
    print("清洗并解析 LLM 输出结果:", clean_data)

if __name__ == '__main__':
    print('='*50)
    print("  Python 字典与 JSON 处理 Demo (面向 JS/TS 开发者)")
    print('='*50)
    demo_1_dict_methods_vs_object_static_methods()
    demo_2_safe_property_access()
    demo_3_json_serialization()
    demo_4_llm_json_parse_error_handling()