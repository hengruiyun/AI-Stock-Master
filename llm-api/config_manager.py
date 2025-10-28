#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from tools.unified_i18n_manager import _
配置管理模块
统一处理配置读取顺序：.env文件 -> 环境变量 -> 默认设置
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

# 尝试导入dotenv，如果失败则提供占位函数
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        print("Warning: python-dotenv not available")
        pass


class ConfigManager:
    """配置管理器，按优先级顺序读取配置"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            env_file: .env文件路径，默认为项目根目录下的.env
        """
        self._config_cache: Dict[str, Any] = {}
        self._user_config: Dict[str, Any] = {}
        self._load_env_file(env_file)
        self._load_user_config()
    
    def _load_env_file(self, env_file: Optional[str] = None) -> None:
        """加载.env文件"""
        if env_file is None:
            # 查找项目根目录下的.env文件
            current_dir = Path(__file__).parent
            env_file = current_dir / ".env"
        
        if Path(env_file).exists():
            load_dotenv(env_file, override=False)  # 不覆盖已存在的环境变量
    
    def _load_user_config(self) -> None:
        """加载用户配置文件"""
        config_file = Path(__file__).parent / "config" / "user_settings.json"
        try:
            if config_file.exists():
                print(f"[LLM Debug] Loading user config from: {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._user_config = json.load(f)
                print(f"[LLM Debug] User config loaded: {list(self._user_config.keys())}")
            else:
                print(f"[LLM Debug] User config file not found: {config_file}")
        except Exception as e:
            print(f"[LLM Debug] 加载用户配置失败: {e}")
            self._user_config = {}
    
    def get(self, key: str, default: Any = None, config_type: type = str) -> Any:
        """
        按优先级获取配置值：用户配置文件 -> .env文件 -> 环境变量 -> 默认值
        
        Args:
            key: 配置键名
            default: 默认值
            config_type: 配置值类型
            
        Returns:
            配置值
        """
        # 检查缓存
        cache_key = f"{key}:{config_type.__name__}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # 1. 优先从用户配置文件获取
        value = self._user_config.get(key)
        
        # 2. 从.env文件获取（通过dotenv加载到环境变量中的值）
        # 注意：这里需要区分.env文件中的值和系统环境变量
        if value is None:
            # 先尝试从当前环境变量获取（包含.env加载的值）
            value = os.getenv(key)
        
        # 3. 如果都不存在，使用默认值
        if value is None:
            value = default
        
        # 类型转换
        if value is not None and config_type != str:
            try:
                if config_type == bool:
                    value = str(value).lower() in ('true', '1', 'yes', 'on')
                elif config_type == int:
                    value = int(value)
                elif config_type == float:
                    value = float(value)
            except (ValueError, TypeError):
                value = default
        
        # 缓存结果
        self._config_cache[cache_key] = value
        return value
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """获取API密钥"""
        key_mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "google": "GOOGLE_API_KEY",
            "lmstudio": "LMSTUDIO_API_KEY",  # LMStudio通常不需要API密钥，但保留配置选项
            "siliconflow": "SILICONFLOW_API_KEY",
            "volcengine": "VOLCENGINE_API_KEY",
            "bailian": "BAILIAN_API_KEY",
        }
        
        env_key = key_mapping.get(provider.lower())
        if env_key:
            return self.get(env_key)
        return None
    
    def get_base_url(self, provider: str) -> Optional[str]:
        """获取基础URL"""
        url_mapping = {
            "openai": "OPENAI_BASE_URL",
            "anthropic": "ANTHROPIC_BASE_URL",
            "groq": "GROQ_BASE_URL",
            "deepseek": "DEEPSEEK_BASE_URL",
            "gemini": "GOOGLE_BASE_URL",
            "google": "GOOGLE_BASE_URL",
            "ollama": "OLLAMA_BASE_URL",
            "lmstudio": "LMSTUDIO_BASE_URL",
            "siliconflow": "SILICONFLOW_BASE_URL",
            "volcengine": "VOLCENGINE_BASE_URL",
            "bailian": "BAILIAN_BASE_URL",
        }
        
        env_key = url_mapping.get(provider.lower())
        if env_key:
            return self.get(env_key)
        return None
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置"""
        settings = {
            "default_provider": self.get("default_provider", self.get("DEFAULT_PROVIDER", "Ollama")),
            "default_chat_model": self.get("default_chat_model", self.get("DEFAULT_CHAT_MODEL", "qwen3:1.7b")),
            "default_structured_model": self.get("default_structured_model", self.get("DEFAULT_STRUCTURED_MODEL", "qwen3:1.7b")),
            "request_timeout": self.get("request_timeout", self.get("REQUEST_TIMEOUT", 600, int), int),
            "max_retries": self.get("MAX_RETRIES", 3, int),
            "enable_cache": self.get("ENABLE_CACHE", True, bool),
            "log_level": self.get("LOG_LEVEL", "INFO"),
            "ollama_host": self.get("OLLAMA_HOST", "localhost"),
            "ollama_port": self.get("OLLAMA_PORT", 11434, int),
            "lmstudio_host": self.get("LMSTUDIO_HOST", "localhost"),
            "lmstudio_port": self.get("LMSTUDIO_PORT", 1234, int),
            "agent_role": self.get("agent_role", self.get("AGENT_ROLE", "不使用")),
        }
        print(f"[LLM Debug] Default settings: {settings}")
        return settings
    
    def clear_cache(self) -> None:
        """清除配置缓存"""
        self._config_cache.clear()


# 全局配置管理器实例
_global_config = None


def get_config() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config