"""LLM API异常类定义"""


class LLMAPIError(Exception):
    """LLM API基础异常类"""
    pass


class ModelNotFoundError(LLMAPIError):
    """模型未找到异常"""
    pass


class APIKeyError(LLMAPIError):
    """API密钥错误异常"""
    pass


class ModelProviderError(LLMAPIError):
    """模型提供商错误异常"""
    pass


class OllamaError(LLMAPIError):
    """Ollama相关错误"""
    pass


class LMStudioError(LLMAPIError):
    """LM Studio相关错误"""
    pass


class ConfigurationError(LLMAPIError):
    """配置错误异常"""
    pass