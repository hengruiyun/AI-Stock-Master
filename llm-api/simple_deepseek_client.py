#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的DeepSeek客户端
不依赖LangChain，直接调用DeepSeek API
"""

import requests
import json
import os
from typing import Optional

class SimpleDeepSeekClient:
    """简化的DeepSeek客户端"""
    
    def __init__(self):
        # 从配置文件读取设置
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config", "user_settings.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get('DEEPSEEK_API_KEY', '')
                    self.base_url = config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
                    self.default_model = config.get('default_chat_model', 'deepseek-chat')
                    self.request_timeout = config.get('request_timeout', 300)
                    print(f"[DeepSeek Debug] 使用配置的模型: {self.default_model}")
                    print(f"[DeepSeek Debug] API Base URL: {self.base_url}")
                    print(f"[DeepSeek Debug] 超时设置: {self.request_timeout}秒")
            else:
                raise Exception("配置文件不存在")
        except Exception as e:
            print(f"[DeepSeek Debug] 读取配置失败: {e}")
            # 使用环境变量作为后备
            self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
            self.base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
            self.default_model = 'deepseek-chat'
            self.request_timeout = 300
    
    def chat(self, message: str, model: Optional[str] = None, **kwargs) -> str:
        """简单的聊天接口"""
        try:
            model = model or self.default_model
            print(f"[DeepSeek Debug] 开始调用模型: {model}")
            
            if not self.api_key:
                return "DeepSeek API密钥未配置。请在配置文件中设置DEEPSEEK_API_KEY。"
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建请求数据
            chat_data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "stream": False,
                "temperature": kwargs.get('temperature', 0.7),
                "max_tokens": kwargs.get('max_tokens', 2048)
            }
            
            # 发送请求
            url = f"{self.base_url}/v1/chat/completions"
            print(f"[DeepSeek Debug] 请求URL: {url}")
            
            response = requests.post(
                url,
                headers=headers,
                json=chat_data,
                timeout=self.request_timeout
            )
            
            print(f"[DeepSeek Debug] 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # 检查响应格式
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
                    print(f"[DeepSeek Debug] 模型响应长度: {len(response_text)} 字符")
                    print(f"[DeepSeek Debug] 响应前100字符: {response_text[:100]}...")
                    return response_text
                else:
                    return f"API响应格式异常: {result}"
            else:
                error_text = response.text
                print(f"[DeepSeek Debug] API调用失败: {error_text}")
                return f"API调用失败，状态码: {response.status_code}, 内容: {error_text}"
                
        except requests.exceptions.Timeout:
            return f"DeepSeek API调用超时（{self.request_timeout}秒）。请检查网络连接。"
        except requests.exceptions.RequestException as e:
            return f"网络请求异常: {e}"
        except Exception as e:
            return f"DeepSeek API调用异常: {str(e)}"

# 兼容性函数
def create_deepseek_client():
    """创建DeepSeek客户端"""
    return SimpleDeepSeekClient()
