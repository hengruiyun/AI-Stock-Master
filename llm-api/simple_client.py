#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的LLM客户端
仅支持基本的Ollama调用
"""

import requests
import json
import os
from typing import Optional

class SimpleLLMClient:
    """简化的LLM客户端"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        # 从配置文件读取模型名称和超时设置
        try:
            import json
            config_path = os.path.join(os.path.dirname(__file__), "config", "user_settings.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.default_model = config.get('default_chat_model', 'gemma2:2b')
                    self.request_timeout = config.get('request_timeout', 300)  # 默认5分钟
                    print(f"[LLM Debug] 使用配置的模型: {self.default_model}")
                    print(f"[LLM Debug] 超时设置: {self.request_timeout}秒")
            else:
                self.default_model = "gemma2:2b"
                self.request_timeout = 300
        except Exception as e:
            print(f"[LLM Debug] 读取配置失败: {e}")
            self.default_model = "gemma2:2b"
            self.request_timeout = 300
    
    def chat(self, message: str, model: Optional[str] = None, **kwargs) -> str:
        """简单的聊天接口"""
        try:
            model = model or self.default_model
            print(f"[LLM Debug] 开始调用模型: {model}")
            
            # 简单检查Ollama是否可用（假设预检查已完成）
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    return f"Ollama服务不可用，状态码: {response.status_code}。请确保Ollama已启动。"
            except requests.exceptions.RequestException as e:
                return f"无法连接到Ollama服务: {e}。请确保Ollama已启动并监听端口11434。"
            
            # 发送聊天请求
            chat_data = {
                "model": model,
                "prompt": message,
                "stream": False
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=chat_data,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '无响应内容')
                print(f"[LLM Debug] 模型响应长度: {len(response_text)} 字符")
                print(f"[LLM Debug] 响应前100字符: {response_text[:100]}...")
                return response_text
            else:
                return f"API调用失败，状态码: {response.status_code}, 内容: {response.text}"
                
        except Exception as e:
            return f"LLM调用异常: {str(e)}"

# 兼容性函数
def LLMClient():
    """返回简化的LLM客户端"""
    return SimpleLLMClient()
