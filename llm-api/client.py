"""LLM统一客户端实现"""

import os
import json
from typing import Any, Dict, List, Optional, Union, Type
from pydantic import BaseModel
# from tools.unified_i18n_manager import _

# LangChain imports - 使用try/except处理可选依赖
try:
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.language_models.chat_models import BaseChatModel
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("LangChain核心模块未安装")
    LANGCHAIN_AVAILABLE = False
    
    # 提供占位类
    class BaseChatModel:
        def __init__(self, **kwargs):
            pass
        
        def invoke(self, messages):
            raise ImportError("LangChain not available")
    
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    
    class SystemMessage:
        def __init__(self, content: str):
            self.content = content
    
    class AIMessage:
        def __init__(self, content: str):
            self.content = content
    
    class ChatOllama:
        def __init__(self, **kwargs):
            raise ImportError("ChatOllama not available")

# 可选的LangChain提供商
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from langchain_deepseek import ChatDeepSeek
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 本地模块导入
try:
    from config_manager import get_config
    from i18n import t
    from prompt_manager import AgentConfig, PromptManager
    from llm_models import ModelProvider, LLMModel
    from exceptions import LLMAPIError, ModelNotFoundError, APIKeyError, ModelProviderError
except ImportError:
    def get_config(): return {}
    def t(key, **kwargs): return key
    
    # 提供异常类的占位实现
    class LLMAPIError(Exception):
        """LLM API基础异常"""
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
    
    # 提供占位类
    class AgentConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class PromptManager:
        def __init__(self):
            pass
            
    # 提供ModelProvider的占位类
    from enum import Enum
    class ModelProvider(str, Enum):
        ANTHROPIC = "Anthropic"
        DEEPSEEK = "DeepSeek"
        GEMINI = "Gemini"
        GROQ = "Groq"
        OPENAI = "OpenAI"
        OLLAMA = "Ollama"
        LMSTUDIO = "LMStudio"
    
    # 提供LLMModel的占位类
    class LLMModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

# 异常类导入和定义
try:
    from exceptions import LLMAPIError, ModelNotFoundError, ModelProviderError
except ImportError:
    # 简化的异常类
    class LLMAPIError(Exception):
        pass

    class ModelNotFoundError(Exception):
        pass
        
    class ModelProviderError(Exception):
        pass

# 工具函数导入
try:
    from ollama_utils import ensure_ollama_and_model
    from lmstudio_utils import ensure_lmstudio_and_model
except ImportError:
    def ensure_ollama_and_model(model_name: str, base_url: str = None) -> bool:
        print(f"Warning: ensure_ollama_and_model not available")
        return True
    
    def ensure_lmstudio_and_model(model_name: str, base_url: str = None) -> bool:
        print(f"Warning: ensure_lmstudio_and_model not available")
        return True

# 自定义LangChain类导入
try:
    from langchain_lmstudio import ChatLMStudio
except ImportError:
    # 如果无法导入，创建一个占位类
    class ChatLMStudio:
        def __init__(self, **kwargs):
            raise ImportError("ChatLMStudio not available - LMStudio support disabled")


class LLMClient:
    """统一的LLM客户端类"""
    
    def __init__(self, default_model: Optional[str] = None, default_provider: Optional[str] = None, temp_config: Optional[Dict] = None):
        """
        初始化LLM客户端
        
        Args:
            default_model: 默认模型名称
            default_provider: 默认提供商
            temp_config: 临时配置字典（用于试用模式等场景）
        """
        self.config = get_config()
        
        # 如果提供了临时配置，将其合并到配置中
        if temp_config:
            print(f"[LLM Client] 使用临时配置: {list(temp_config.keys())}")
            self.temp_config = temp_config
            # 临时覆盖配置管理器中的用户配置
            if hasattr(self.config, '_user_config'):
                self.config._user_config.update(temp_config)
                print(f"[LLM Client] 临时配置已合并到 _user_config")
            # 同时清空缓存，强制重新读取
            if hasattr(self.config, '_config_cache'):
                self.config._config_cache.clear()
                print(f"[LLM Client] 配置缓存已清空")
        else:
            self.temp_config = None
        
        default_settings = self.config.get_default_settings()
        
        self.default_model = default_model or default_settings["default_chat_model"]
        self.default_provider = default_provider or default_settings["default_provider"]
        self._model_cache: Dict[str, BaseChatModel] = {}
        
        # 初始化提示词管理器
        try:
            self.prompt_manager = PromptManager()
        except:
            self.prompt_manager = None
        
        # 当前智能体配置
        self.current_agent: Optional[AgentConfig] = None
    
    def set_agent(self, agent_id: str) -> bool:
        """
        设置当前智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            是否设置成功
        """
        agent = self.prompt_manager.load_agent(agent_id)
        if agent:
            self.current_agent = agent
            return True
        return False
    
    def create_agent_from_template(
        self,
        agent_id: str,
        template_id: str,
        name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        从模板创建智能体
        
        Args:
            agent_id: 智能体ID
            template_id: 模板ID
            name: 智能体名称
            temperature: 温度参数
            max_tokens: 最大token数
            model: 模型名称
            provider: 提供商名称
            custom_parameters: 自定义参数
            
        Returns:
            是否创建成功
        """
        template = self.prompt_manager.load_template(template_id)
        if not template:
            return False
        
        agent = self.prompt_manager.create_agent(
            name=name or template.name,
            template_id=template_id,
            temperature=temperature or 0.7,
            max_tokens=max_tokens,
            model=model,
            provider=provider,
            custom_parameters=custom_parameters
        )
        
        self.prompt_manager.save_agent(agent_id, agent)
        return True
    
    def get_current_agent(self) -> Optional[AgentConfig]:
        """
        获取当前智能体配置
        
        Returns:
            当前智能体配置
        """
        return self.current_agent
    
    def clear_agent(self) -> None:
        """
        清除当前智能体配置
        """
        self.current_agent = None
    
    def list_available_agents(self) -> List[str]:
        """
        列出所有可用的智能体
        
        Returns:
            智能体ID列表
        """
        return self.prompt_manager.list_agents()
    
    def list_available_templates(self) -> List[str]:
        """
        列出所有可用的模板
        
        Returns:
            模板ID列表
        """
        return self.prompt_manager.list_templates()
    
    def _get_api_key(self, provider: ModelProvider) -> str:
        """获取指定提供商的API密钥"""
        # Ollama和LMStudio通常不需要API密钥
        if provider in [ModelProvider.OLLAMA, ModelProvider.LMSTUDIO]:
            return ""
        
        api_key = self.config.get_api_key(provider.value.lower())
        if not api_key:
            raise APIKeyError(t("api_key_not_found", provider=provider.value))
        
        return api_key
    
    def _create_model_instance(self, model_name: str, provider: ModelProvider) -> BaseChatModel:
        """创建模型实例"""
        cache_key = f"{provider}:{model_name}"
        if cache_key in self._model_cache:
            print(f"[LLM Debug] Using cached model instance: {cache_key}")
            return self._model_cache[cache_key]
        
        print(f"[LLM Debug] Creating new model instance: {provider.value} - {model_name}")
        
        try:
            if provider == ModelProvider.OPENAI:
                api_key = self._get_api_key(provider)
                base_url = self.config.get_base_url("openai")
                print(f"[LLM Debug] OpenAI config - Base URL: {base_url}, API Key: {'***' if api_key else 'None'}")
                model = ChatOpenAI(
                    model=model_name, 
                    api_key=api_key, 
                    base_url=base_url
                )
            
            elif provider == ModelProvider.ANTHROPIC:
                api_key = self._get_api_key(provider)
                print(f"[LLM Debug] Anthropic config - API Key: {'***' if api_key else 'None'}")
                model = ChatAnthropic(
                    model=model_name, 
                    api_key=api_key
                )
            
            elif provider == ModelProvider.GROQ:
                api_key = self._get_api_key(provider)
                print(f"[LLM Debug] Groq config - API Key: {'***' if api_key else 'None'}")
                model = ChatGroq(
                    model=model_name, 
                    api_key=api_key
                )
            
            elif provider == ModelProvider.DEEPSEEK:
                api_key = self._get_api_key(provider)
                print(f"[LLM Debug] DeepSeek config - API Key: {'***' if api_key else 'None'}")
                model = ChatDeepSeek(
                    model=model_name, 
                    api_key=api_key
                )
            
            elif provider == ModelProvider.GEMINI:
                api_key = self._get_api_key(provider)
                print(f"[LLM Debug] Gemini config - API Key: {'***' if api_key else 'None'}")
                model = ChatGoogleGenerativeAI(
                    model=model_name, 
                    api_key=api_key
                )
            
            elif provider == ModelProvider.OLLAMA:
                print(f"[LLM Debug] Ollama - Checking model availability: {model_name}")
                
                # 获取base_url
                base_url = self.config.get_base_url("ollama")
                if not base_url:
                    ollama_host = self.config.get("OLLAMA_HOST", "localhost")
                    ollama_port = self.config.get("OLLAMA_PORT", 11434, int)
                    base_url = f"http://{ollama_host}:{ollama_port}"
                
                print(f"[LLM Debug] Ollama config - Base URL: {base_url}")
                
                # 确保Ollama和模型可用
                if not ensure_ollama_and_model(model_name, base_url):
                    print(f"[LLM Debug] Ollama - Model not available: {model_name}")
                    raise ModelNotFoundError(t("model_not_found", provider="Ollama", model=model_name))
                
                model = ChatOllama(
                    model=model_name,
                    base_url=base_url
                )
            
            elif provider == ModelProvider.LMSTUDIO:
                print(f"[LLM Debug] LMStudio - Checking model availability: {model_name}")
                # 确保LMStudio服务器和模型可用
                if not ensure_lmstudio_and_model(model_name):
                    print(f"[LLM Debug] LMStudio - Model not available: {model_name}")
                    raise ModelNotFoundError(t("model_not_found", provider="LMStudio", model=model_name))
                
                base_url = self.config.get_base_url("lmstudio")
                if not base_url:
                    lmstudio_host = self.config.get("LMSTUDIO_HOST", "localhost")
                    lmstudio_port = self.config.get("LMSTUDIO_PORT", 1234, int)
                    base_url = f"http://{lmstudio_host}:{lmstudio_port}"
                
                print(f"[LLM Debug] LMStudio config - Base URL: {base_url}")
                model = ChatLMStudio(
                    model=model_name,
                    base_url=base_url
                )
            
            elif provider == ModelProvider.SILICONFLOW:
                api_key = self._get_api_key(provider)
                base_url = self.config.get_base_url("siliconflow")
                if not base_url:
                    base_url = "https://api.siliconflow.cn/v1"
                print(f"[LLM Debug] SiliconFlow config - Base URL: {base_url}, API Key: {'***' if api_key else 'None'}")
                # SiliconFlow 使用 OpenAI 兼容接口
                model = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    base_url=base_url
                )
            
            elif provider == ModelProvider.VOLCENGINE:
                api_key = self._get_api_key(provider)
                base_url = self.config.get_base_url("volcengine")
                if not base_url:
                    base_url = "https://ark.cn-beijing.volces.com/api/v3"
                print(f"[LLM Debug] Volcengine config - Base URL: {base_url}, API Key: {'***' if api_key else 'None'}")
                # Volcengine 使用 OpenAI 兼容接口
                model = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    base_url=base_url
                )
            
            elif provider == ModelProvider.BAILIAN:
                api_key = self._get_api_key(provider)
                base_url = self.config.get_base_url("bailian")
                if not base_url:
                    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                print(f"[LLM Debug] Bailian config - Base URL: {base_url}, API Key: {'***' if api_key else 'None'}")
                # Bailian 使用 OpenAI 兼容接口
                model = ChatOpenAI(
                    model=model_name,
                    api_key=api_key,
                    base_url=base_url
                )
            
            else:
                print(f"[LLM Debug] Unsupported provider: {provider.value}")
                raise ModelProviderError(t("unsupported_provider", provider=provider.value))
            
            print(f"[LLM Debug] Model instance created successfully: {cache_key}")
            self._model_cache[cache_key] = model
            return model
            
        except Exception as e:
            print(f"[LLM Debug] Error creating model instance: {str(e)}")
            if isinstance(e, (LLMAPIError, ModelNotFoundError, APIKeyError, ModelProviderError)):
                raise
            raise LLMAPIError(t("create_model_error", error=str(e)))
    
    def get_model(self, model_name: Optional[str] = None, provider: Optional[str] = None) -> BaseChatModel:
        """
        获取模型实例
        
        Args:
            model_name: 模型名称
            provider: 提供商名称
            
        Returns:
            模型实例
        """
        model_name = model_name or self.default_model
        provider = provider or self.default_provider
        
        # 转换为枚举
        if isinstance(provider, str):
            try:
                provider_enum = ModelProvider(provider)
            except ValueError:
                raise ModelProviderError(t("unsupported_provider", provider=provider))
        else:
            provider_enum = provider
        
        return self._create_model_instance(model_name, provider_enum)
    
    def chat(
        self, 
        message: Union[str, List[Dict[str, str]]], 
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        num_predict: Optional[int] = None,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        发送聊天消息
        
        Args:
            message: 用户消息（字符串或消息列表）
            model: 模型名称
            provider: 提供商名称
            system_message: 系统消息
            temperature: 温度参数
            max_tokens: 最大token数
            agent_id: 智能体ID（如果指定，将使用智能体配置）
            **kwargs: 其他参数
            
        Returns:
            AI回复内容
        """
        # 如果指定了智能体ID，临时设置智能体
        original_agent = self.current_agent
        if agent_id:
            self.set_agent(agent_id)
        
        # 从当前智能体获取配置
        if self.current_agent:
            model = model or self.current_agent.model
            provider = provider or self.current_agent.provider
            system_message = system_message or self.current_agent.system_prompt
            temperature = temperature if temperature is not None else self.current_agent.temperature
            max_tokens = max_tokens or self.current_agent.max_tokens
            
            # 合并自定义参数
            if self.current_agent.custom_parameters:
                kwargs.update(self.current_agent.custom_parameters)
        
        try:
            model_name = model or self.default_model
            provider_name = provider or self.default_provider
            print(f"[LLM Debug] Chat request - Model: {model_name}, Provider: {provider_name}")
            print(f"[LLM Debug] Chat parameters - Temperature: {temperature}, Max tokens: {max_tokens}")
            
            llm = self.get_model(model, provider)
            
            # 设置参数
            if temperature is not None:
                print(f"[LLM Debug] Setting temperature: {temperature}")
                llm = llm.bind(temperature=temperature)
            
            # 根据提供商设置token限制参数
            provider_name = provider or self.default_provider
            if provider_name == "Ollama":
                # Ollama的num_predict参数需要在创建时设置，不能在bind中设置
                # 如果需要动态设置，需要重新创建模型实例
                if num_predict is not None or max_tokens is not None:
                    # 重新创建Ollama模型实例，包含num_predict参数
                    token_limit = num_predict if num_predict is not None else max_tokens
                    base_url = self.config.get_base_url("ollama")
                    if not base_url:
                        ollama_host = self.config.get("OLLAMA_HOST", "localhost")
                        ollama_port = self.config.get("OLLAMA_PORT", 11434, int)
                        base_url = f"http://{ollama_host}:{ollama_port}"
                    
                    llm = ChatOllama(
                        model=model or self.default_model,
                        base_url=base_url,
                        num_predict=token_limit
                    )
            else:
                # 其他提供商使用max_tokens
                if max_tokens is not None:
                    llm = llm.bind(max_tokens=max_tokens)
            
            # 构建消息
            messages = []
            
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            if isinstance(message, str):
                messages.append(HumanMessage(content=message))
            elif isinstance(message, list):
                for msg in message:
                    if msg.get("role") == "system":
                        messages.append(SystemMessage(content=msg["content"]))
                    elif msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg.get("role") == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            # 发送消息并获取响应
            print(f"[LLM Debug] Sending {len(messages)} messages to LLM")
            print(f"[LLM Debug] Message types: {[type(msg).__name__ for msg in messages]}")
            response = llm.invoke(messages)
            print(f"[LLM Debug] Response received, length: {len(response.content) if response.content else 0} characters")
            return response.content
            
        except Exception as e:
            print(f"[LLM Debug] Chat error: {str(e)}")
            raise LLMAPIError(t("send_message_error", error=str(e)))
        finally:
            # 恢复原始智能体配置
            if agent_id:
                self.current_agent = original_agent
    
    def chat_with_structured_output(
        self,
        message: Union[str, List[Dict[str, str]]],
        pydantic_model: Type[BaseModel],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_message: Optional[str] = None,
        max_retries: int = 3,
        **kwargs
    ) -> BaseModel:
        """
        发送聊天消息并返回结构化输出
        
        Args:
            message: 用户消息
            pydantic_model: Pydantic模型类
            model: 模型名称
            provider: 提供商名称
            system_message: 系统消息
            max_retries: 最大重试次数
            **kwargs: 其他参数
            
        Returns:
            结构化输出实例
        """
        model_name = model or self.default_model
        provider_name = provider or self.default_provider
        
        # 获取模型信息
        model_info = get_model_info(model_name, provider_name)
        llm = self.get_model(model_name, provider_name)
        
        # 对于支持JSON模式的模型，使用结构化输出
        if model_info and model_info.has_json_mode():
            llm = llm.with_structured_output(pydantic_model, method="json_mode")
        
        # 构建消息
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        if isinstance(message, str):
            messages.append(HumanMessage(content=message))
        elif isinstance(message, list):
            for msg in message:
                if msg.get("role") == "system":
                    messages.append(SystemMessage(content=msg["content"]))
                elif msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        # 重试逻辑
        for attempt in range(max_retries):
            try:
                result = llm.invoke(messages)
                
                # 对于不支持JSON模式的模型，手动解析JSON
                if model_info and not model_info.has_json_mode():
                    parsed_result = self._extract_json_from_response(result.content)
                    if parsed_result:
                        return pydantic_model(**parsed_result)
                    else:
                        raise ValueError(t("json_extract_failed") if hasattr(self, 't') else "Unable to extract JSON from response")
                else:
                    return result
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    # 最后一次尝试失败，返回默认值
                    return self._create_default_response(pydantic_model)
                continue
        
        return self._create_default_response(pydantic_model)
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """从Markdown格式的响应中提取JSON"""
        import re
        
        try:
            # 尝试多种JSON提取方式
            # 1. 从```json代码块中提取
            json_match = re.search(r'```json\s*\n([\s\S]*?)\n```', content)
            if json_match:
                json_text = json_match.group(1).strip()
                return json.loads(json_text)
            
            # 2. 从```代码块中提取（无json标识）
            code_match = re.search(r'```\s*\n([\s\S]*?)\n```', content)
            if code_match:
                json_text = code_match.group(1).strip()
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass
            
            # 3. 直接尝试解析整个内容
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                pass
                
            # 4. 查找JSON对象模式
            json_pattern = r'\{[\s\S]*\}'
            json_matches = re.findall(json_pattern, content)
            for match in json_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            print(f"JSON extraction error: {e}")
            
        return None
    
    def _create_default_response(self, model_class: Type[BaseModel]) -> BaseModel:
        """创建默认响应"""
        default_values = {}
        for field_name, field in model_class.model_fields.items():
            if field.annotation == str:
                default_values[field_name] = t("analysis_error_default") if hasattr(self, 't') else "Analysis error, using default value"
            elif field.annotation == float:
                default_values[field_name] = 0.0
            elif field.annotation == int:
                default_values[field_name] = 0
            elif hasattr(field.annotation, "__origin__") and field.annotation.__origin__ == dict:
                default_values[field_name] = {}
            else:
                # 对于其他类型（如Literal），尝试使用第一个允许的值
                if hasattr(field.annotation, "__args__"):
                    default_values[field_name] = field.annotation.__args__[0]
                else:
                    default_values[field_name] = None
        
        return model_class(**default_values)
    
    def list_available_models(self) -> List[LLMModel]:
        """列出所有可用模型"""
        return list_all_models()
    
    def get_model_info(self, model_name: str, provider: str) -> Optional[LLMModel]:
        """获取模型信息"""
        return get_model_info(model_name, provider)
    
    def clear_cache(self):
        """清除模型缓存"""
        self._model_cache.clear()