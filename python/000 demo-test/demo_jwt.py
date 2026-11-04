
# 需要安装：pip install pyjwt
# pyrefly: ignore [missing-import]
import jwt
import datetime

SECRET_KEY = "my-super-secret-key-do-not-share"
ALGORITHM = "HS256"
# ======================== 1. 生成 JWT (登录成功后调用) ========================

def create_access_token(user_id: int, username: str):
    payload = {
        "sub": str(user_id),
        "name": username,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
    }
    excode_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return excode_jwt

def verify_token(token: str):
    try:
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"success": True, "data": decoded_payload}
    except jwt.ExpiredSignatureError:
        return {"success": False, "error": "Token 已过期，请重新登录"}
    except jwt.InvalidTokenError:
        return {"success": False, "error": "无效的token"}

if __name__ == "__main__":
    token = create_access_token(user_id=1001, username="kevinzzzzzz")
    print(f"生成的token:{token}")
    print("--- 模拟黑客篡改 Token ---")
    hacker_token = token[:-1] + "x"
    print(f"修改后的token:{hacker_token}")
    result_hacker = verify_token(hacker_token)
    print(f"验证被篡改的 token 结果：{result_hacker}")


