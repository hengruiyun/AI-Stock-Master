#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from tools.unified_i18n_manager import _
LM Studio 工具模块
提供LM Studio服务器管理和模型操作功能
"""

import requests
import time
import os
from typing import List, Optional, Dict, Any
from colorama import Fore, Style

try:
    from exceptions import LMStudioError
    from config_manager import get_config
except ImportError:
    from exceptions import LMStudioError
    from config_manager import get_config


class LMStudioManager:
    """LM Studio管理器类"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初始化LM Studio管理器
        
        Args:
            base_url: LM Studio服务器基础URL
        """
        config = get_config()
        if base_url is None:
            # 优先使用完整的base_url配置
            base_url = config.get("LMSTUDIO_BASE_URL")
            if base_url is None:
                host = config.get("LMSTUDIO_HOST", "localhost")
                port = config.get("LMSTUDIO_PORT", 1234, int)
                base_url = f"http://{host}:{port}"
        
        self.base_url = base_url.rstrip('/')
        self.api_models_endpoint = f"{self.base_url}/v1/models"
        self.api_chat_endpoint = f"{self.base_url}/v1/chat/completions"
    
    def is_server_running(self) -> bool:
        """检查LM Studio服务器是否运行"""
        try:
            endpoint = f"{self.base_url}/v1/models"
            print(f"[LLM Debug] Checking LMStudio server at: {endpoint}")
            response = requests.get(endpoint, timeout=5)
            is_running = response.status_code == 200
            print(f"[LLM Debug] LMStudio server running: {is_running}")
            return is_running
        except Exception as e:
            print(f"[LLM Debug] LMStudio server check failed: {str(e)}")
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            print(f"[LLM Debug] Fetching LMStudio models from: {self.api_models_endpoint}")
            response = requests.get(
                self.api_models_endpoint,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get('data', [])
            print(f"[LLM Debug] Found {len(models)} LMStudio models")
            return models
        except Exception as e:
            print(f"[LLM Debug] Error fetching LMStudio models: {str(e)}")
            raise LMStudioError(f"获取LM Studio模型列表失败: {e}")
    
    def get_model_names(self) -> List[str]:
        """获取模型名称列表"""
        models = self.get_available_models()
        return [model.get('id', '') for model in models if model.get('id')]
    
    def is_model_available(self, model_name: str) -> bool:
        """检查指定模型是否可用"""
        try:
            available_models = self.get_model_names()
            return model_name in available_models
        except Exception:
            return False
    
    def wait_for_server(self, timeout: int = 30) -> bool:
        """等待服务器启动"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_server_running():
                return True
            time.sleep(1)
        return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        try:
            # 尝试获取模型信息作为服务器状态检查
            models = self.get_available_models()
            return {
                "status": "running",
                "base_url": self.base_url,
                "models_count": len(models),
                "available_models": [m.get('id') for m in models]
            }
        except Exception as e:
            return {
                "status": "error",
                "base_url": self.base_url,
                "error": str(e)
            }


def ensure_lmstudio_server(base_url: Optional[str] = None, timeout: int = 30) -> bool:
    """
    确保LM Studio服务器运行
    
    Args:
        base_url: LM Studio服务器URL
        timeout: 等待超时时间（秒）
        
    Returns:
        bool: 服务器是否可用
    """
    manager = LMStudioManager(base_url)
    
    print(f"{Fore.YELLOW}检查LM Studio服务器状态...{Style.RESET_ALL}")
    
    if manager.is_server_running():
        print(f"{Fore.GREEN}✓ LM Studio服务器正在运行{Style.RESET_ALL}")
        return True
    
    print(f"{Fore.RED}✗ LM Studio服务器未运行{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}请确保LM Studio已启动并且本地服务器正在运行{Style.RESET_ALL}")
    print(f"{Fore.CYAN}提示：在LM Studio中启动本地服务器，默认地址为 http://localhost:1234{Style.RESET_ALL}")
    
    return False


def ensure_lmstudio_and_model(model_name: str, base_url: Optional[str] = None) -> bool:
    """
    确保LM Studio服务器运行且指定模型可用
    
    Args:
        model_name: 模型名称
        base_url: LM Studio服务器URL
        
    Returns:
        bool: 服务器和模型是否都可用
    """
    # 首先确保服务器运行
    if not ensure_lmstudio_server(base_url):
        return False
    
    manager = LMStudioManager(base_url)
    
    print(f"{Fore.YELLOW}检查模型 {model_name} 是否可用...{Style.RESET_ALL}")
    
    if manager.is_model_available(model_name):
        print(f"{Fore.GREEN}✓ 模型 {model_name} 可用{Style.RESET_ALL}")
        return True
    
    print(f"{Fore.RED}✗ 模型 {model_name} 不可用{Style.RESET_ALL}")
    
    # 显示可用模型
    try:
        available_models = manager.get_model_names()
        if available_models:
            print(f"{Fore.CYAN}可用模型：{Style.RESET_ALL}")
            for model in available_models:
                print(f"  - {model}")
        else:
            print(f"{Fore.YELLOW}当前没有加载的模型{Style.RESET_ALL}")
            print(f"{Fore.CYAN}请在LM Studio中加载一个模型{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}获取模型列表失败: {e}{Style.RESET_ALL}")
    
    return False


def list_lmstudio_models(base_url: Optional[str] = None) -> List[str]:
    """
    列出LM Studio中的可用模型
    
    Args:
        base_url: LM Studio服务器URL
        
    Returns:
        List[str]: 模型名称列表
    """
    try:
        manager = LMStudioManager(base_url)
        return manager.get_model_names()
    except Exception as e:
        print(f"{Fore.RED}获取LM Studio模型列表失败: {e}{Style.RESET_ALL}")
        return []


def get_lmstudio_info(base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    获取LM Studio服务器信息
    
    Args:
        base_url: LM Studio服务器URL
        
    Returns:
        Dict[str, Any]: 服务器信息
    """
    manager = LMStudioManager(base_url)
    return manager.get_server_info()