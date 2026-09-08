"""
网络与 API：JWT (JSON Web Token) 认证机制

在前后端分离的架构中，服务器不再使用 Session 存储登录状态，
而是普遍采用 JWT。

流程：
1. 用户提交账号密码。
2. 服务器验证通过，将用户ID等信息“签名”生成一个 JWT 字符串，返回给前端。
3. 前端将 JWT 存在 localStorage 中。
4. 前端每次请求 API 时，都在 HTTP Header 中带上 `Authorization: Bearer <JWT>`。
5. 服务器验证 JWT 的签名是否合法（是否被篡改），如果合法则允许访问。
"""

# 需要安装：pip install pyjwt
# pyrefly: ignore [missing-import]
import jwt
import datetime

# 这是服务器的终极机密，绝对不能泄露！
# 如果泄露，任何人都可以伪造合法用户的 Token
SECRET_KEY = "my-super-secret-key-do-not-share"
ALGORITHM = "HS256"

# ======================== 1. 生成 JWT (登录成功后调用) ========================

def create_access_token(user_id: int, username: str):
    """
    生成一个有效期为 2 小时的 JWT
    """
    # 负载信息 (Payload)
    payload = {
        "sub": str(user_id),          # 主题 (Subject)，通常放用户 ID
        "name": username,             # 自定义字段
        # exp (Expiration Time): 必须是一个 Unix 时间戳，表示过期时间
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
    }
    
    # 使用密钥进行签名
    # 结果是一个类似 eyJhbG... 这样的字符串
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ======================== 2. 验证与解析 JWT (处理 API 请求时调用) ========================

def verify_token(token: str):
    """
    解析前端传来的 Token。
    如果被篡改或者已过期，jwt.decode 会抛出异常。
    """
    try:
        # 解码并验证签名与过期时间
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"success": True, "data": decoded_payload}
        
    except jwt.ExpiredSignatureError:
        # Token 过了有效期
        return {"success": False, "error": "Token 已过期，请重新登录"}
    except jwt.InvalidTokenError:
        # Token 格式错误或签名不匹配（被篡改）
        return {"success": False, "error": "无效的 Token"}


# ======================== 测试代码 ========================

if __name__ == "__main__":
    print("--- 1. 用户登录成功，生成 Token ---")
    token = create_access_token(user_id=1001, username="Alice")
    print(f"生成的 Token: \\n{token}\\n")
    
    print("--- 2. 前端携带 Token 请求接口，服务器验证 ---")
    result = verify_token(token)
    print(f"验证结果: {result}\\n")
    
    print("--- 3. 模拟黑客篡改 Token ---")
    # 随便改动一个字母
    hacker_token = token[:-1] + "X"
    result_hacker = verify_token(hacker_token)
    print(f"验证被篡改的 Token 结果: {result_hacker}")
