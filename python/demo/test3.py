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


if __name__ == '__main__':
    print('='*50)
    print("  Python 字典与 JSON 处理 Demo (面向 JS/TS 开发者)")
    print('='*50)
    demo_1_dict_methods_vs_object_static_methods()
    demo_2_safe_property_access()