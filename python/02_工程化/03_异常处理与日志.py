"""
异常处理与日志最佳实践
=================================================================

Python 的异常处理和 JS 的 try-catch 很像，但有一些关键差异。
AI 开发中：网络超时、API Rate Limit、Token 超限等异常非常常见。
"""

import logging
import traceback
from typing import Any, Optional


# ======================== 1. 基本异常处理 ========================

def divide_safe(a: float, b: float) -> Optional[float]:
    """try-except 的基本用法 —— 和 JS 的 try-catch 一样"""
    try:
        return a / b
    except ZeroDivisionError:
        print("错误：除数不能为0")
        return None
    except TypeError:
        print("错误：参数类型不正确")
        return None


# ======================== 2. 多异常捕获 + else + finally ========================

def read_config(filepath: str) -> dict:
    """else 分支：try 块没有异常时执行
       finally 分支：无论是否异常都会执行（清理资源）
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"文件不存在: {filepath}")
        return {}
    except PermissionError:
        print(f"没有权限读取: {filepath}")
        return {}
    else:
        # 没有异常时执行
        print(f"成功读取 {filepath}")
    finally:
        # 总是执行
        print("读取操作完成")
    
    import json
    return json.loads(content)


# ======================== 3. 自定义异常 ========================

class LLMError(Exception):
    """LLM 调用错误的基类"""
    pass

class LLMTimeoutError(LLMError):
    """LLM 调用超时"""
    def __init__(self, provider: str, timeout: float):
        self.provider = provider
        self.timeout = timeout
        super().__init__(f"{provider} 请求超时（{timeout}秒）")

class LLMRateLimitError(LLMError):
    """API 频率限制"""
    def __init__(self, provider: str, retry_after: int = 60):
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(f"{provider} 频率限制，请 {retry_after}秒后重试")

class LLMTokenError(LLMError):
    """Token 超限"""
    def __init__(self, current: int, maximum: int):
        self.current = current
        self.maximum = maximum
        super().__init__(f"Token 超限: 当前{current}, 最大{maximum}")

class LLMAuthError(LLMError):
    """认证失败（API Key 无效）"""
    pass


# ======================== 4. AI 开发中的异常处理模式 ========================

import time
import random

def call_llm_with_retry(
    prompt: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> dict:
    """带指数退避的 LLM 调用 —— 生产级代码的标准模式
    
    指数退避（Exponential Backoff）：
    第1次重试等待 1s，第2次 2s，第3次 4s...
    防止大量请求同时涌入服务器
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            # 模拟 API 调用
            result = _simulate_api_call(prompt)
            return result
            
        except LLMRateLimitError as e:
            # 频率限制 → 等待后重试
            wait_time = base_delay * (2 ** (attempt - 1))  # 指数退避
            print(f"[重试 {attempt}/{max_retries}] 频率限制，等待 {wait_time:.1f}秒")
            time.sleep(wait_time)
            last_error = e
            
        except LLMTimeoutError as e:
            # 超时 → 等待后重试
            wait_time = base_delay * attempt
            print(f"[重试 {attempt}/{max_retries}] 超时，等待 {wait_time:.1f}秒")
            time.sleep(wait_time)
            last_error = e
            
        except LLMAuthError:
            # 认证失败 → 不重试，直接抛
            raise  # re-raise
        
        except LLMTokenError as e:
            # Token 超限 → 不重试（修改 prompt 才有意义）
            raise
    
    # 所有重试都失败
    raise LLMError(f"重试 {max_retries} 次后仍然失败: {last_error}")


def _simulate_api_call(prompt: str) -> dict:
    """模拟 API 调用（10% 概率失败）"""
    if random.random() < 0.1:  # 10% 失败率
        error_type = random.choice([
            LLMRateLimitError("OpenAI"),
            LLMTimeoutError("OpenAI", 30),
        ])
        raise error_type
    return {"content": f"回复: {prompt[:20]}...", "model": "gpt-4o-mini"}


# ======================== 5. 日志配置（生产级） ========================

def get_logger(name: str) -> logging.Logger:
    """获取配置好的 logger"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 控制台输出
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname).1s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(console)
        
        # 文件输出（生产环境）
        # file_handler = logging.FileHandler("app.log", encoding="utf-8")
        # file_handler.setLevel(logging.WARNING)
        # logger.addHandler(file_handler)
        
        logger.setLevel(logging.DEBUG)
    
    return logger


# ======================== 6. 上下文管理器：异常安全的资源管理 ========================

class LLMClient:
    """模拟 LLM 客户端 —— 演示上下文管理器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = get_logger("LLMClient")
    
    def __enter__(self):
        """进入 with 块"""
        self.logger.info("LLM 客户端初始化")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出 with 块（一定执行）"""
        self.logger.info("LLM 客户端关闭")
        if exc_type:
            self.logger.error(f"异常退出: {exc_type.__name__}: {exc_val}")
        return False  # 不吞异常
    
    def chat(self, prompt: str) -> str:
        """发送请求"""
        self.logger.info(f"发送请求: {prompt[:30]}...")
        return "这是 LLM 回复"


# ======================== 7. 装饰器异常处理 ========================

import functools

def safe_llm_call(default_return: Any = None):
    """装饰器：自动捕获 LLM 调用异常，返回默认值"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except LLMRateLimitError as e:
                print(f"[警告] 频率限制: {e}")
                return default_return
            except LLMTimeoutError as e:
                print(f"[警告] 超时: {e}")
                return default_return
            except LLMError as e:
                print(f"[错误] LLM 调用失败: {e}")
                return default_return
            except Exception as e:
                print(f"[错误] 未知错误: {e}")
                traceback.print_exc()
                return default_return
        return wrapper
    return decorator


# ======================== 8. 实战：批量 LLM 调用 + 错误收集 ========================

from dataclasses import dataclass, field
from typing import Union

@dataclass
class BatchResult:
    """批量调用结果"""
    successes: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        total = len(self.successes) + len(self.failures)
        return len(self.successes) / total if total > 0 else 0.0


def batch_llm_call(prompts: list[str]) -> BatchResult:
    """批量调用 LLM，收集成功和失败"""
    result = BatchResult()
    logger = get_logger("BatchLLM")
    
    for i, prompt in enumerate(prompts):
        try:
            response = _simulate_api_call(prompt)
            result.successes.append({
                "index": i,
                "prompt": prompt,
                "response": response,
            })
            logger.info(f"[{i+1}/{len(prompts)}] 成功: {prompt[:20]}...")
        except LLMError as e:
            result.failures.append({
                "index": i,
                "prompt": prompt,
                "error": str(e),
            })
            logger.error(f"[{i+1}/{len(prompts)}] 失败: {e}")
    
    logger.info(f"完成: 成功{len(result.successes)}/失败{len(result.failures)}")
    return result


if __name__ == "__main__":
    logger = get_logger("Main")
    logger.info("=== 异常处理 Demo ===")
    
    # 测试重试机制
    print("\n--- 重试测试 ---")
    try:
        result = call_llm_with_retry("你好", max_retries=3)
        print(f"成功: {result}")
    except LLMError as e:
        print(f"最终失败: {e}")
    
    # 测试上下文管理器
    print("\n--- 上下文管理器 ---")
    with LLMClient("sk-test-123") as client:
        response = client.chat("介绍一下 Python")
        print(response)
    
    # 测试批量调用
    print("\n--- 批量调用 ---")
    batch_result = batch_llm_call([f"prompt-{i}" for i in range(5)])
    print(f"成功率: {batch_result.success_rate:.0%}")
