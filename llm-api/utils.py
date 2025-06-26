"""LLM API工具函数模块

提供与原有代码兼容的便捷函数
"""

from typing import Any, Optional, Type, Callable, Dict, Tuple
from pydantic import BaseModel

try:
    from client import LLMClient
    from models import get_model_info, LLMModel
    from exceptions import LLMAPIError
except ImportError:
    from client import LLMClient
    from models import get_model_info, LLMModel
    from exceptions import LLMAPIError

# 全局客户端实例
_global_client = None


def get_client() -> LLMClient:
    """获取全局LLM客户端实例"""
    global _global_client
    if _global_client is None:
        _global_client = LLMClient()
    return _global_client


def call_llm(
    prompt: Any,
    pydantic_model: Type[BaseModel],
    agent_name: Optional[str] = None,
    state: Optional[Any] = None,
    max_retries: int = 3,
    default_factory: Optional[Callable] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
) -> BaseModel:
    """
    调用LLM并返回结构化输出（兼容原有接口）
    
    Args:
        prompt: 提示词
        pydantic_model: Pydantic模型类
        agent_name: 代理名称（用于从state中提取模型配置）
        state: 状态对象
        max_retries: 最大重试次数
        default_factory: 默认值工厂函数
        model_name: 模型名称
        model_provider: 模型提供商
        
    Returns:
        结构化输出实例
    """
    client = get_client()
    
    # 从state中提取模型配置（如果提供）
    if state and agent_name and not model_name:
        extracted_model_name, extracted_provider = get_agent_model_config(state, agent_name)
        model_name = model_name or extracted_model_name
        provider = provider or extracted_provider
    
    # 使用默认值
    model_name = model_name or "gpt-4o"
    provider = provider or "OpenAI"
    
    try:
        return client.chat_with_structured_output(
            message=str(prompt),
            pydantic_model=pydantic_model,
            model=model_name,
            provider=provider,
            max_retries=max_retries
        )
    except Exception as e:
        print(f"LLM调用出错: {e}")
        if default_factory:
            return default_factory()
        return client._create_default_response(pydantic_model)


def get_agent_model_config(state: Any, agent_name: str) -> Tuple[str, str]:
    """
    从状态中获取代理的模型配置（兼容原有接口）
    
    Args:
        state: 状态对象
        agent_name: 代理名称
        
    Returns:
        (model_name, model_provider) 元组
    """
    try:
        request = state.get("metadata", {}).get("request")
        
        if agent_name == 'portfolio_manager':
            # 从state metadata中获取模型和提供商
            model_name = state.get("metadata", {}).get("model_name", "gpt-4o")
            provider = state.get("metadata", {}).get("model_provider", "OpenAI")
            return model_name, provider
        
        if request and hasattr(request, 'get_agent_model_config'):
            # 获取代理特定的模型配置
            model_name, provider = request.get_agent_model_config(agent_name)
            return model_name, provider.value if hasattr(provider, 'value') else str(provider)
        
        # 回退到全局配置
        model_name = state.get("metadata", {}).get("model_name", "gpt-4o")
        provider = state.get("metadata", {}).get("model_provider", "OpenAI")
        
        # 转换枚举为字符串
        if hasattr(provider, 'value'):
            provider = provider.value
        
        return model_name, provider
        
    except Exception:
        # 如果出错，返回默认值
        return "gpt-4o", "OpenAI"


def create_default_response(model_class: Type[BaseModel]) -> BaseModel:
    """创建默认响应（兼容原有接口）"""
    client = get_client()
    return client._create_default_response(model_class)


def extract_json_from_response(content: str) -> Optional[Dict[str, Any]]:
    """从响应中提取JSON（兼容原有接口）"""
    client = get_client()
    return client._extract_json_from_response(content)


# 便捷函数
def chat(
    message: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    system_message: Optional[str] = None,
    **kwargs
) -> str:
    """简单的聊天接口"""
    client = get_client()
    return client.chat(
        message=message,
        model=model,
        provider=provider,
        system_message=system_message,
        **kwargs
    )


def get_model(model_name: str, provider: str):
    """获取模型实例（兼容原有接口）"""
    client = get_client()
    return client.get_model(model_name, provider)


def list_models():
    """列出所有可用模型"""
    client = get_client()
    return client.list_available_models()