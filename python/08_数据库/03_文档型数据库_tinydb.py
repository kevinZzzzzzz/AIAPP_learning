# 注意：运行此文件需要先安装 tinydb: pip install tinydb
from tinydb import TinyDB, Query

def main():
    print("--- 文档型数据库 (TinyDB/NoSQL) 示例：存储非结构化配置 ---")
    
    # 初始化数据库（类似 MongoDB，用纯文本 JSON 格式存储）
    db = TinyDB('ai_configs.json')
    
    # 场景：存储不同 Agent 的配置、Prompt 模板、用户偏好等
    # 在 AI 应用开发中，这类数据的结构经常变，用表结构（MySQL）很难维护，用文档型（NoSQL）最合适
    
    # 1. 插入一些灵活的数据（字段不需要完全一样）
    db.insert({
        'type': 'agent_config',
        'name': '代码助手',
        'model': 'gpt-4o',
        'temperature': 0.2,
        'system_prompt': "你是一个Python资深专家..."
    })
    
    db.insert({
        'type': 'user_preference',
        'user_id': 'kevin',
        'theme': 'dark',
        'favorite_models': ['claude-3.5-sonnet', 'gpt-4o']
    })
    
    print("数据插入完成 (可以打开 ai_configs.json 看看内容)\n")
    
    # 2. 查询数据
    Config = Query()
    
    # 查找所有的 agent_config
    agents = db.search(Config.type == 'agent_config')
    print("查询到的 Agent 配置:")
    for agent in agents:
        print(f"- {agent['name']} (使用模型: {agent['model']})")
        
    # 查找特定用户的偏好
    user_prefs = db.search((Config.type == 'user_preference') & (Config.user_id == 'kevin'))
    print(f"\n查询到的 Kevin 的偏好设置: {user_prefs[0]['favorite_models']}")

    # 清理测试数据
    db.truncate()

if __name__ == "__main__":
    main()
