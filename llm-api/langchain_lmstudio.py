#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangChain LMStudio 适配器
为LMStudio提供LangChain兼容的接口
"""

import json
import requests
from typing import Any, Dict, Iterator, List, Optional, Union
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

try:
    from config_manager import get_config
    from exceptions import LMStudioError
except ImportError:
    from config_manager import get_config
    from exceptions import LMStudioError


class ChatLMStudio(BaseChatModel):
    """LMStudio聊天模型的LangChain适配器"""
    
    model: str = Field(default="")
    base_url: str = Field(default="")
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    top_p: float = Field(default=1.0)
    frequency_penalty: float = Field(default=0.0)
    presence_penalty: float = Field(default=0.0)
    request_timeout: int = Field(default=30)
    
    def __init__(self, **kwargs):
        # 设置默认值
        config = get_config()
        if not kwargs.get('base_url'):
            host = config.get("LMSTUDIO_HOST", "localhost")
            port = config.get("LMSTUDIO_PORT", 1234, int)
            kwargs['base_url'] = f"http://{host}:{port}"
        
        if not kwargs.get('request_timeout'):
            kwargs['request_timeout'] = config.get("REQUEST_TIMEOUT", 30, int)
        
        super().__init__(**kwargs)
    
    @property
    def _llm_type(self) -> str:
        """返回LLM类型标识"""
        return "lmstudio"
    
    def _convert_messages_to_lmstudio_format(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """将LangChain消息格式转换为LMStudio API格式"""
        lmstudio_messages = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                lmstudio_messages.append({
                    "role": "user",
                    "content": message.content
                })
            elif isinstance(message, AIMessage):
                lmstudio_messages.append({
                    "role": "assistant",
                    "content": message.content
                })
            elif isinstance(message, SystemMessage):
                lmstudio_messages.append({
                    "role": "system",
                    "content": message.content
                })
            else:
                # 对于其他类型的消息，默认作为用户消息处理
                lmstudio_messages.append({
                    "role": "user",
                    "content": str(message.content)
                })
        
        return lmstudio_messages
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """生成聊天回复"""
        # 准备请求数据
        lmstudio_messages = self._convert_messages_to_lmstudio_format(messages)
        
        payload = {
            "model": self.model,
            "messages": lmstudio_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
            "stream": False,
        }
        
        if self.max_tokens:
            payload["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        
        if stop:
            payload["stop"] = stop
        
        # 发送请求
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 解析响应
            if "choices" not in result or not result["choices"]:
                raise LMStudioError("LMStudio API返回了空的choices")
            
            choice = result["choices"][0]
            message_content = choice["message"]["content"]
            
            # 创建AI消息
            ai_message = AIMessage(content=message_content)
            
            # 创建生成结果
            generation = ChatGeneration(
                message=ai_message,
                generation_info={
                    "finish_reason": choice.get("finish_reason"),
                    "model": result.get("model", self.model),
                    "usage": result.get("usage", {})
                }
            )
            
            return ChatResult(generations=[generation])
            
        except requests.exceptions.RequestException as e:
            raise LMStudioError(f"LMStudio API请求失败: {e}")
        except json.JSONDecodeError as e:
            raise LMStudioError(f"LMStudio API响应解析失败: {e}")
        except Exception as e:
            raise LMStudioError(f"LMStudio调用出错: {e}")
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        """流式生成聊天回复"""
        # 准备请求数据
        lmstudio_messages = self._convert_messages_to_lmstudio_format(messages)
        
        payload = {
            "model": self.model,
            "messages": lmstudio_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
            "stream": True,
        }
        
        if self.max_tokens:
            payload["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        
        if stop:
            payload["stop"] = stop
        
        # 发送流式请求
        try:
            response = requests.post(
                f"{self.base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"},
                stream=True
            )
            response.raise_for_status()
            
            # 处理流式响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 移除 'data: ' 前缀
                        
                        if data.strip() == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                choice = chunk["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                                    if content:
                                        ai_message = AIMessage(content=content)
                                        generation = ChatGeneration(
                                            message=ai_message,
                                            generation_info={
                                                "finish_reason": choice.get("finish_reason"),
                                                "model": chunk.get("model", self.model)
                                            }
                                        )
                                        
                                        if run_manager:
                                            run_manager.on_llm_new_token(content)
                                        
                                        yield generation
                        except json.JSONDecodeError:
                            continue  # 跳过无法解析的行
            
        except requests.exceptions.RequestException as e:
            raise LMStudioError(f"LMStudio流式API请求失败: {e}")
        except Exception as e:
            raise LMStudioError(f"LMStudio流式调用出错: {e}")
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """获取标识参数"""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }