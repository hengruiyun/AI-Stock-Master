# -*- coding: utf-8 -*-
"""
Internationalization (i18n) module for LLM API
国际化模块，支持英文和中文语言切换
"""

import os
import locale
from typing import Dict, Any, Optional
from enum import Enum


class Language(Enum):
    """支持的语言枚举"""
    ENGLISH = "en"
    CHINESE = "zh"


class I18n:
    """国际化管理类"""
    
    def __init__(self, default_language: Language = Language.ENGLISH):
        """
        初始化国际化管理器
        
        Args:
            default_language: 默认语言，默认为英文
        """
        self._current_language = self._detect_system_language() or default_language
        self._translations = self._load_translations()
    
    def _detect_system_language(self) -> Optional[Language]:
        """检测系统语言"""
        try:
            # 检查环境变量
            lang_env = os.environ.get('LANG', '').lower()
            if 'zh' in lang_env or 'chinese' in lang_env:
                return Language.CHINESE
            
            # 检查系统locale
            system_locale = locale.getdefaultlocale()[0]
            if system_locale and ('zh' in system_locale.lower() or 'chinese' in system_locale.lower()):
                return Language.CHINESE
            
            # 检查Windows系统语言
            if os.name == 'nt':
                import ctypes
                windll = ctypes.windll.kernel32
                language_id = windll.GetUserDefaultUILanguage()
                # 中文语言ID范围
                if language_id in [0x0804, 0x0404, 0x0c04, 0x1004, 0x1404]:
                    return Language.CHINESE
            
            return Language.ENGLISH
        except Exception:
            return Language.ENGLISH
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """加载翻译文本"""
        return {
            # 通用消息
            "api_key_not_found": {
                "en": "API key not found for {provider}. Please set the corresponding API key in environment variables or .env file.",
                "zh": "未找到{provider}的API密钥。请在环境变量或.env文件中设置相应的API密钥。"
            },
            "model_not_found": {
                "en": "Unable to ensure {provider} model {model} is available",
                "zh": "无法确保{provider}模型 {model} 可用"
            },
            "unsupported_provider": {
                "en": "Unsupported provider: {provider}",
                "zh": "不支持的提供商: {provider}"
            },
            "create_model_error": {
                "en": "Error creating model instance: {error}",
                "zh": "创建模型实例时出错: {error}"
            },
            "connection_test_failed": {
                "en": "Connection test failed: {error}",
                "zh": "连接测试失败: {error}"
            },
            "send_message_error": {
                "en": "Error sending message: {error}",
                "zh": "发送消息时出错: {error}"
            },
            
            # Web UI 文本
            "page_title": {
                "en": "LLM API Chat",
                "zh": "LLM API 聊天"
            },
            "main_header": {
                "en": "🤖 LLM API Chat Interface",
                "zh": "🤖 LLM API 聊天界面"
            },
            "model_configuration": {
                "en": "Model Configuration",
                "zh": "模型配置"
            },
            "select_provider": {
                "en": "Select Provider",
                "zh": "选择提供商"
            },
            "select_model": {
                "en": "Select Model",
                "zh": "选择模型"
            },
            "connect_model": {
                "en": "Connect Model",
                "zh": "连接模型"
            },
            "disconnect": {
                "en": "Disconnect",
                "zh": "断开连接"
            },
            "test_connection": {
                "en": "Test Connection",
                "zh": "测试连接"
            },
            "refresh_config": {
                "en": "Refresh Configuration",
                "zh": "刷新配置"
            },
            "clear_conversation": {
                "en": "Clear Conversation",
                "zh": "清空对话"
            },
            "connection_status": {
                "en": "Connection Status",
                "zh": "连接状态"
            },
            "connected": {
                "en": "✅ Connected",
                "zh": "✅ 已连接"
            },
            "not_connected": {
                "en": "❌ Not Connected",
                "zh": "❌ 未连接"
            },
            "provider": {
                "en": "Provider",
                "zh": "提供商"
            },
            "model": {
                "en": "Model",
                "zh": "模型"
            },
            "server_status": {
                "en": "Server Status",
                "zh": "服务器状态"
            },
            "running": {
                "en": "Running",
                "zh": "运行中"
            },
            "stopped": {
                "en": "Stopped",
                "zh": "已停止"
            },
            "available_models": {
                "en": "Available Models",
                "zh": "可用模型"
            },
            "server_url": {
                "en": "Server URL",
                "zh": "服务器地址"
            },
            "environment_setup": {
                "en": "Environment Setup",
                "zh": "环境配置"
            },
            "api_key_required": {
                "en": "API Key Required",
                "zh": "需要API密钥"
            },
            "set_env_variable": {
                "en": "Set environment variable: {var}",
                "zh": "设置环境变量: {var}"
            },
            "local_server_setup": {
                "en": "Local Server Setup",
                "zh": "本地服务器配置"
            },
            "ensure_server_running": {
                "en": "Ensure {server} server is running",
                "zh": "确保{server}服务器正在运行"
            },
            "connection_error": {
                "en": "Connection Error",
                "zh": "连接错误"
            },
            "debug_info": {
                "en": "Debug Info",
                "zh": "调试信息"
            },
            "error_details": {
                "en": "Error Details",
                "zh": "错误详情"
            },
            "chat_input_placeholder": {
                "en": "Type your message here...",
                "zh": "在此输入您的消息..."
            },
            "send": {
                "en": "Send",
                "zh": "发送"
            },
            "you": {
                "en": "You",
                "zh": "您"
            },
            "assistant": {
                "en": "Assistant",
                "zh": "助手"
            },
            "usage_instructions": {
                "en": "Usage Instructions",
                "zh": "使用说明"
            },
            "usage_step1": {
                "en": "1. Select a provider and model",
                "zh": "1. 选择提供商和模型"
            },
            "usage_step2": {
                "en": "2. Click 'Connect Model' to establish connection",
                "zh": "2. 点击'连接模型'建立连接"
            },
            "usage_step3": {
                "en": "3. Start chatting in the main interface",
                "zh": "3. 在主界面开始聊天"
            },
            "import_error": {
                "en": "Module import failed: {error}",
                "zh": "导入模块失败: {error}"
            },
            "run_in_project_dir": {
                "en": "Please ensure you are running this script in the llm-api project directory",
                "zh": "请确保在llm-api项目目录中运行此脚本"
            },
            "connecting": {
                "en": "Connecting...",
                "zh": "连接中..."
            },
            "connection_successful": {
                "en": "Connection successful!",
                "zh": "连接成功！"
            },
            "connection_failed": {
                "en": "Connection failed: {error}",
                "zh": "连接失败: {error}"
            },
            "testing_connection": {
                "en": "Testing connection...",
                "zh": "测试连接中..."
            },
            "test_successful": {
                "en": "Test successful!",
                "zh": "测试成功！"
            },
            "test_failed": {
                "en": "Test failed: {error}",
                "zh": "测试失败: {error}"
            },
            "config_refreshed": {
                "en": "Configuration refreshed!",
                "zh": "配置已刷新！"
            },
            "conversation_cleared": {
                "en": "Conversation cleared!",
                "zh": "对话已清空！"
            },
            "no_models_available": {
                "en": "No models available for the selected provider",
                "zh": "所选提供商没有可用模型"
            },
            "loading_models": {
                "en": "Loading models...",
                "zh": "加载模型中..."
            },
            "select_model_first": {
                "en": "Please select a model first",
                "zh": "请先选择一个模型"
            },
            "language_setting": {
                "en": "Language",
                "zh": "语言"
            },
            "english": {
                "en": "English",
                "zh": "英文"
            },
            "chinese": {
                "en": "Chinese",
                "zh": "中文"
            },
            "json_extract_failed": {
                "en": "Failed to extract JSON from response",
                "zh": "从响应中提取JSON失败"
            },
            "analysis_error_default": {
                "en": "Analysis error",
                "zh": "分析错误"
            },
            "clear_conversation": {
                "en": "Clear Conversation",
                "zh": "清空对话"
            },
            "conversation_cleared": {
                "en": "Conversation cleared successfully",
                "zh": "对话已清空"
            },
            "usage_instructions": {
                "en": "Usage Instructions",
                "zh": "使用说明"
            },
            "usage_step1": {
                "en": "1. Select LLM provider",
                "zh": "1. 选择LLM提供商"
            },
            "usage_step2": {
                "en": "2. Select specific model",
                "zh": "2. 选择具体模型"
            },
            "usage_step3": {
                "en": "3. Click 'Connect Model' and start chatting",
                "zh": "3. 点击'连接模型'开始聊天"
            },
            "environment_setup": {
                "en": "Environment Setup",
                "zh": "环境配置"
            },
            "api_key_required": {
                "en": "Cloud API Configuration",
                "zh": "云端API配置"
            },
            "local_server_setup": {
                "en": "Local Server Configuration",
                "zh": "本地服务器配置"
            },
            "main_header": {
                "en": "🤖 LLM API Chat",
                "zh": "🤖 LLM API 聊天"
            },
            "you": {
                "en": "You",
                "zh": "用户"
            },
            "assistant": {
                "en": "Assistant",
                "zh": "助手"
            },
            "chat_input_placeholder": {
        "en": "Type your message...",
        "zh": "输入您的消息..."
    },
    "please_select_model": {
        "en": "Please select and connect to a model in the sidebar first",
        "zh": "请先在左侧选择并连接模型"
    },
    "please_connect_model": {
        "en": "Please connect to a model first...",
        "zh": "请先连接模型..."
    },
    "powered_by": {
        "en": "Powered by LLM API | Unified interface for multiple LLM providers",
        "zh": "由 LLM API 驱动 | 支持多个LLM提供商的统一接口"
    },
    "ai_thinking": {
        "en": "AI thinking...",
        "zh": "AI正在思考..."
    },
    "error_label": {
        "en": "Error",
        "zh": "错误"
    },
    "please_check": {
        "en": "Please check:",
        "zh": "请检查："
    },
    "ollama_check_1": {
        "en": "1. Ollama service is running (ollama serve)",
        "zh": "1. Ollama服务正在运行 (ollama serve)"
    },
    "ollama_check_2": {
        "en": "2. Port is correct (default 11434)",
        "zh": "2. 端口正确 (默认 11434)"
    },
    "ollama_check_3": {
        "en": "3. Environment variable OLLAMA_BASE_URL is set correctly",
        "zh": "3. 环境变量 OLLAMA_BASE_URL 设置正确"
    },
    "lmstudio_check_1": {
        "en": "1. LM Studio Local Server is running",
        "zh": "1. LM Studio 本地服务器正在运行"
    },
    "lmstudio_check_2": {
        "en": "2. Port is correct (default 1234)",
        "zh": "2. 端口正确 (默认 1234)"
    },
    "lmstudio_check_3": {
        "en": "3. Environment variable LMSTUDIO_BASE_URL is set correctly",
        "zh": "3. 环境变量 LMSTUDIO_BASE_URL 设置正确"
    },
    "no_local_models_detected": {
                "en": "No {provider} models detected. Please ensure the server is running and models are loaded.",
                "zh": "未检测到{provider}模型。请确保服务器正在运行且模型已加载。"
            },
            "agent_management": {
                "en": "Agent Management",
                "zh": "智能体管理"
            },
            "select_agent": {
                "en": "Select Agent",
                "zh": "选择智能体"
            },
            "create_agent": {
                "en": "Create Agent",
                "zh": "创建智能体"
            },
            "agent_name": {
                "en": "Agent Name",
                "zh": "智能体名称"
            },
            "select_template": {
                "en": "Select Template",
                "zh": "选择模板"
            },
            "create_from_template": {
                "en": "Create from Template",
                "zh": "从模板创建"
            },
            "agent_created": {
                "en": "Agent created successfully",
                "zh": "智能体创建成功"
            },
            "agent_creation_failed": {
                "en": "Agent creation failed",
                "zh": "智能体创建失败"
            },
            "fill_required_fields": {
                "en": "Please fill in all required fields",
                "zh": "请填写必要字段"
            },
            "agent_role": {
                "en": "Role",
                "zh": "角色"
            },
            "agent_prompt": {
                "en": "Agent Prompt",
                "zh": "智能体提示词"
            },
            "system_prompt": {
                "en": "System Prompt",
                "zh": "系统提示词"
            },
            "default_agent": {
                "en": "Default",
                "zh": "默认"
            }
        }
    
    def get_current_language(self) -> Language:
        """获取当前语言"""
        return self._current_language
    
    def set_language(self, language: Language) -> None:
        """设置当前语言"""
        self._current_language = language
    
    def t(self, key: str, **kwargs) -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键
            **kwargs: 格式化参数
        
        Returns:
            翻译后的文本
        """
        translations = self._translations.get(key, {})
        text = translations.get(self._current_language.value, key)
        
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        
        return text
    
    def get_language_options(self) -> Dict[str, str]:
        """获取语言选项"""
        return {
            self.t("english"): Language.ENGLISH.value,
            self.t("chinese"): Language.CHINESE.value
        }


# 全局实例
_i18n_instance = None


def get_i18n() -> I18n:
    """获取全局国际化实例"""
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance


def t(key: str, **kwargs) -> str:
    """快捷翻译函数"""
    return get_i18n().t(key, **kwargs)


def set_language(language: Language) -> None:
    """设置全局语言"""
    get_i18n().set_language(language)


def get_current_language() -> Language:
    """获取当前语言"""
    return get_i18n().get_current_language()