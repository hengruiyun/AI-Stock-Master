#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM API Chat Web UI
基于Streamlit的聊天Web界面，支持多个LLM提供商
"""

import streamlit as st
import sys
import os
from typing import List, Dict, Any
import traceback

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client import LLMClient
    from models import ModelProvider, LLMModel
    from exceptions import LLMAPIError
    from config_manager import ConfigManager
    from ollama_utils import OllamaManager
    from lmstudio_utils import LMStudioManager
    from prompt_manager import get_prompt_manager, AgentRole
    from i18n import get_i18n, t, Language
except ImportError as e:
    st.error(f"Module import failed: {e}")
    st.error("Please ensure you are running this script in the llm-api project directory")
    st.stop()

# 初始化国际化
i18n = get_i18n()

# 页面配置
st.set_page_config(
    page_title=t("page_title"),
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    text-align: center;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.chat-message {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    border-left: 4px solid #667eea;
}

.user-message {
    background-color: #f0f2f6;
    border-left-color: #667eea;
}

.assistant-message {
    background-color: #e8f4fd;
    border-left-color: #1f77b4;
}

.error-message {
    background-color: #ffe6e6;
    border-left-color: #ff4444;
    color: #cc0000;
}

.success-message {
    background-color: #e6ffe6;
    border-left-color: #44ff44;
    color: #006600;
}

.sidebar .stSelectbox {
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=30)  # 缓存30秒
def get_local_server_info(provider: str) -> Dict[str, Any]:
    """获取本地服务器信息（带缓存）"""
    if provider == "Ollama":
        try:
            ollama_manager = OllamaManager()
            is_running = ollama_manager.is_server_running()
            models = ollama_manager.get_locally_available_models() if is_running else []
            return {
                "status": "running" if is_running else "stopped",
                "url": ollama_manager.base_url,
                "models": models,
                "models_count": len(models),
                "error": None
            }
        except Exception as e:
            return {
                "status": "error",
                "url": "http://localhost:11434",
                "models": [],
                "models_count": 0,
                "error": str(e)
            }
    elif provider == "LMStudio":
        try:
            lmstudio_manager = LMStudioManager()
            is_running = lmstudio_manager.is_server_running()
            models = lmstudio_manager.get_model_names() if is_running else []
            return {
                "status": "running" if is_running else "stopped",
                "url": lmstudio_manager.base_url,
                "models": models,
                "models_count": len(models),
                "error": None
            }
        except Exception as e:
            return {
                "status": "error",
                "url": "http://localhost:1234",
                "models": [],
                "models_count": 0,
                "error": str(e)
            }
    else:
        return {
            "status": "error",
            "url": "N/A",
            "models": [],
            "models_count": 0,
            "error": t("unsupported_provider", provider=provider)
        }

def get_local_ollama_models() -> List[str]:
    """获取本地Ollama模型列表"""
    server_info = get_local_server_info("Ollama")
    return server_info["models"]

def get_local_lmstudio_models() -> List[str]:
    """获取本地LM Studio模型列表"""
    server_info = get_local_server_info("LMStudio")
    return server_info["models"]

@st.cache_data(ttl=60)  # 缓存60秒
def get_cloud_models() -> Dict[str, List[str]]:
    """获取云端模型列表（带缓存）"""
    try:
        client = LLMClient()
        models = client.list_available_models()
        
        # 按提供商分组
        provider_models = {}
        for model in models:
            provider = model.provider.value
            if provider not in provider_models:
                provider_models[provider] = []
            provider_models[provider].append(model.model_name)
        
        return provider_models
    except Exception:
        # 返回默认云端模型列表
        return {
            "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            "Anthropic": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
            "Google": ["gemini-2.0-flash-exp", "gemini-1.5-pro"],
            "Groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            "DeepSeek": ["deepseek-chat", "deepseek-reasoner"]
        }

@st.cache_data(ttl=120)  # 缓存2分钟
def get_available_models() -> Dict[str, List[str]]:
    """获取可用的模型列表（优化版，带缓存）"""
    # 获取云端模型
    provider_models = get_cloud_models().copy()
    
    # 添加本地模型
    ollama_models = get_local_ollama_models()
    if ollama_models:
        provider_models["Ollama"] = ollama_models
    
    lmstudio_models = get_local_lmstudio_models()
    if lmstudio_models:
        provider_models["LMStudio"] = lmstudio_models
    
    return provider_models

def init_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "client" not in st.session_state:
        st.session_state.client = None
    
    if "connected" not in st.session_state:
        st.session_state.connected = False
    
    if "current_provider" not in st.session_state:
        st.session_state.current_provider = None
    
    if "current_model" not in st.session_state:
        st.session_state.current_model = None
    
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = None
    
    if "prompt_manager" not in st.session_state:
        st.session_state.prompt_manager = get_prompt_manager()
    
    # 初始化可用模型列表（避免每次对话都重新获取）
    if "available_models" not in st.session_state:
        st.session_state.available_models = get_available_models()

def connect_to_model(provider: str, model: str) -> bool:
    """连接到指定的模型"""
    try:
        client = LLMClient(default_model=model, default_provider=provider)
        
        # 测试连接 - Ollama使用num_predict而不是max_tokens
        if provider == "Ollama":
            test_response = client.chat(
                "Hello", 
                model=model, 
                provider=provider,
                num_predict=10
            )
        else:
            test_response = client.chat(
                "Hello", 
                model=model, 
                provider=provider,
                max_tokens=10
            )
        
        st.session_state.client = client
        st.session_state.connected = True
        st.session_state.current_provider = provider
        st.session_state.current_model = model
        
        return True
    except Exception as e:
        st.error(t("connection_failed", error=str(e)))
        return False

def send_message(message: str) -> str:
    """发送消息并获取回复"""
    try:
        if not st.session_state.client:
            raise Exception(t("not_connected"))
        
        # 如果设置了智能体，使用智能体进行聊天
        if st.session_state.current_agent:
            response = st.session_state.client.chat(
                message,
                model=st.session_state.current_model,
                provider=st.session_state.current_provider,
                agent_id=st.session_state.current_agent
            )
        else:
            response = st.session_state.client.chat(
                message,
                model=st.session_state.current_model,
                provider=st.session_state.current_provider
            )
        
        return response
    except Exception as e:
        raise Exception(t("send_message_error", error=str(e)))

def test_local_server_connection(provider: str) -> Dict[str, Any]:
    """测试本地服务器连接状态（使用缓存）"""
    return get_local_server_info(provider)

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # 自动检测系统语言，不显示语言选择器
        st.markdown("---")
        st.markdown(f"### 🔧 {t('model_configuration')}")
        
        # 模型配置控制
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button(f"🔄 {t('refresh_config')}", key="refresh_models", help=t('refresh_config')):
                # 清除所有相关缓存
                get_available_models.clear()
                get_cloud_models.clear()
                get_local_server_info.clear()
                # 重新获取可用模型并更新session_state
                st.session_state.available_models = get_available_models()
                st.rerun()
        
        # 使用session_state中的可用模型（避免每次对话都重新加载）
        available_models = st.session_state.available_models
        
        # 选择提供商
        provider = st.selectbox(
            t("select_provider"),
            options=list(available_models.keys()),
            key="provider_select"
        )
        
        # 显示本地服务器状态
        if provider in ["Ollama", "LMStudio"]:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"#### 📡 {provider} {t('server_status')}")
            with col2:
                if st.button("🔄", key=f"refresh_{provider}"):
                    # 清除缓存并重新获取
                    get_local_server_info.clear()
                    get_available_models.clear()
                    # 重新获取可用模型并更新session_state
                    st.session_state.available_models = get_available_models()
                    st.rerun()
            
            server_info = test_local_server_connection(provider)
            
            # 显示配置信息
            st.info(f"**{t('server_url')}**: {server_info.get('url', 'N/A')}")
            
            if server_info["status"] == "running":
                st.success(f"🟢 {provider} {t('running')}")
                st.info(f"**{t('available_models')}**: {server_info['models_count']}")
                if server_info['models']:
                    with st.expander(t('available_models')):
                        for model in server_info['models']:
                            st.text(f"• {model}")
            elif server_info["status"] == "stopped":
                st.error(f"🔴 {provider} {t('stopped')}")
                st.warning(t('ensure_server_running', server=provider))
                # 显示环境变量提示
                if provider == "Ollama":
                    st.info(f"💡 {t('environment_setup')} Ollama:")
                    st.code("OLLAMA_BASE_URL=http://your-host:port\nOLLAMA_HOST=your-host\nOLLAMA_PORT=your-port")
                elif provider == "LMStudio":
                    st.info(f"💡 {t('environment_setup')} LM Studio:")
                    st.code("LMSTUDIO_BASE_URL=http://your-host:port\nLMSTUDIO_HOST=your-host\nLMSTUDIO_PORT=your-port")
            else:
                st.error(f"❌ {provider} {t('connection_error')}")
                st.error(f"{t('error_details')}: {server_info.get('error', 'Unknown error')}")
                # 显示调试信息
                with st.expander(f"🔍 {t('debug_info')}"):
                    st.text(f"{t('server_url')}: {server_info.get('url', 'N/A')}")
                    st.text(f"{t('error_details')}: {server_info.get('error', 'Unknown error')}")
                    if provider == "Ollama":
                        st.text(t('please_check'))
                        st.text(t('ollama_check_1'))
                        st.text(t('ollama_check_2'))
                        st.text(t('ollama_check_3'))
                    elif provider == "LMStudio":
                        st.text(t('please_check'))
                        st.text(t('lmstudio_check_1'))
                        st.text(t('lmstudio_check_2'))
                        st.text(t('lmstudio_check_3'))
        
        # 选择模型
        if provider and provider in available_models:
            models_list = available_models[provider]
            if models_list:
                model = st.selectbox(
                    t("select_model"),
                    options=models_list,
                    key="model_select"
                )
            else:
                model = None
                if provider in ["Ollama", "LMStudio"]:
                    st.warning(t("no_local_models_detected", provider=provider))
                else:
                    st.warning(t("no_models_available"))
        else:
            model = None
            st.warning(t("select_model_first"))
        
        # 连接测试按钮（仅本地服务器）
        if provider in ["Ollama", "LMStudio"]:
            if st.button(f"🔍 {t('test_connection')} {provider}", use_container_width=True):
                with st.spinner(t("testing_connection")):
                    server_info = test_local_server_connection(provider)
                    if server_info["status"] == "running":
                        st.success(f"✅ {provider} {t('test_successful')}")
                        st.balloons()
                    else:
                        st.error(f"❌ {provider} {t('test_failed', error=server_info.get('error', 'Unknown error'))}")
                    st.rerun()
        
        # 连接模型按钮
        if st.button(f"🔗 {t('connect_model')}", type="primary", use_container_width=True):
            if provider and model:
                with st.spinner(t("connecting")):
                    if connect_to_model(provider, model):
                        st.success(f"✅ {t('connection_successful')} {provider} - {model}")
                        st.rerun()
            else:
                st.error(t("select_model_first"))
        
        # 智能体管理
        st.markdown("---")
        st.markdown(f"### 🤖 {t('agent_management')}")
        
        # 获取可用的智能体和模板
        available_agents = st.session_state.prompt_manager.list_agents()
        available_templates = st.session_state.prompt_manager.list_templates()
        
        # 创建智能体显示选项（显示中文名称）
        def get_agent_display_name(agent_id):
            """获取智能体的显示名称"""
            try:
                agent_config = st.session_state.prompt_manager.load_agent(agent_id)
                return agent_config.name if agent_config else agent_id
            except:
                return agent_id
        
        # 智能体选择
        agent_display_options = [t("default_agent")] + [get_agent_display_name(agent) for agent in available_agents]
        agent_id_mapping = {t("default_agent"): None}
        for i, agent_id in enumerate(available_agents):
            display_name = get_agent_display_name(agent_id)
            agent_id_mapping[display_name] = agent_id
        
        # 获取当前选中的显示名称
        current_display_name = t("default_agent")
        if st.session_state.current_agent:
            current_display_name = get_agent_display_name(st.session_state.current_agent)
        
        selected_display_name = st.selectbox(
            t("select_agent"),
            options=agent_display_options,
            index=agent_display_options.index(current_display_name) if current_display_name in agent_display_options else 0,
            key="agent_select"
        )
        
        # 获取对应的智能体ID
        selected_agent = agent_id_mapping.get(selected_display_name)
        
        # 更新当前智能体
        if selected_agent is None:
            st.session_state.current_agent = None
        else:
            st.session_state.current_agent = selected_agent
            if st.session_state.client:
                st.session_state.client.set_agent(selected_agent)
        
        # 显示当前智能体信息
        if st.session_state.current_agent:
            agent_config = st.session_state.prompt_manager.load_agent(st.session_state.current_agent)
            if agent_config:
                st.info(f"**{t('agent_role')}**: {agent_config.role.value}")
                with st.expander(f"📝 {t('agent_prompt')}"):
                    st.text_area(
                        t("system_prompt"),
                        value=agent_config.system_prompt,
                        height=100,
                        disabled=True,
                        key="current_agent_prompt"
                    )
        
        # 快速创建智能体
        with st.expander(f"➕ {t('create_agent')}"):
            new_agent_name = st.text_input(t("agent_name"))
            selected_template = st.selectbox(
                t("select_template"),
                options=available_templates,
                key="template_select"
            )
            
            if st.button(f"✨ {t('create_from_template')}", key="create_agent_btn"):
                if new_agent_name and selected_template:
                    agent_id = new_agent_name.lower().replace(" ", "_")
                    if st.session_state.client.create_agent_from_template(
                        agent_id=agent_id,
                        template_id=selected_template,
                        name=new_agent_name
                    ):
                        st.success(f"✅ {t('agent_created')}: {new_agent_name}")
                        st.rerun()
                    else:
                        st.error(f"❌ {t('agent_creation_failed')}")
                else:
                    st.error(t("fill_required_fields"))
        
        # 连接状态
        st.markdown("---")
        st.markdown(f"### 📊 {t('connection_status')}")
        if st.session_state.connected:
            st.success(t("connected"))
            st.info(f"**{t('provider')}**: {st.session_state.current_provider}")
            st.info(f"**{t('model')}**: {st.session_state.current_model}")
            if st.session_state.current_agent:
                st.info(f"**{t('agent', default='智能体')}**: {st.session_state.current_agent}")
            
            # 断开连接按钮
            if st.button(f"🔌 {t('disconnect')}", use_container_width=True):
                st.session_state.client = None
                st.session_state.connected = False
                st.session_state.current_provider = None
                st.session_state.current_model = None
                st.session_state.current_agent = None
                st.rerun()
        else:
            st.error(t("not_connected"))
        
        # 清空对话按钮
        st.markdown("---")
        if st.button(f"🗑️ {t('clear_conversation')}", use_container_width=True):
            st.session_state.messages = []
            st.success(t("conversation_cleared"))
            st.rerun()
        
        # 帮助信息
        st.markdown("---")
        st.markdown(f"### 💡 {t('usage_instructions')}")
        st.markdown(f"""
        {t('usage_step1')}
        {t('usage_step2')}
        {t('usage_step3')}
        """)
        
        # 环境配置提示
        st.markdown(f"### ⚙️ {t('environment_setup')}")
        
        # 云端API配置
        with st.expander(f"☁️ {t('api_key_required')}"):
            st.markdown("""
            Please set the corresponding API keys:
            - `OPENAI_API_KEY`
            - `ANTHROPIC_API_KEY`
            - `GOOGLE_API_KEY`
            - `GROQ_API_KEY`
            - `DEEPSEEK_API_KEY`
            """)
        
        # 本地服务器配置
        with st.expander(f"🏠 {t('local_server_setup')}"):
            st.markdown("""
            **Ollama Setup:**
            ```bash
            # Start Ollama service
            ollama serve
            
            # Download models (examples)
            ollama pull llama3.1
            ollama pull qwen2.5
            ```
            
            **LM Studio Setup:**
            1. Open LM Studio application
            2. Go to "Local Server" tab
            3. Select a model and click "Start Server"
            4. Default port: 1234
            
            **Local models do not require API keys**
            """)

def render_chat_interface():
    """渲染聊天界面"""
    # 主标题
    st.markdown(f'<h1 class="main-header">{t("main_header")}</h1>', unsafe_allow_html=True)
    
    # 显示历史消息
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(
                f'<div class="chat-message user-message"><strong>👤 {t("you")}:</strong><br>{message["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-message assistant-message"><strong>🤖 {t("assistant")}:</strong><br>{message["content"]}</div>',
                unsafe_allow_html=True
            )
    
    # 聊天输入
    if st.session_state.connected:
        # 使用chat_input组件
        if prompt := st.chat_input(t("chat_input_placeholder")):
            # 添加用户消息
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # 显示用户消息
            st.markdown(
                f'<div class="chat-message user-message"><strong>👤 {t("you")}:</strong><br>{prompt}</div>',
                unsafe_allow_html=True
            )
            
            # 获取AI回复
            with st.spinner(f"🤔 {t('ai_thinking')}"):
                try:
                    response = send_message(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # 显示AI回复
                    st.markdown(
                        f'<div class="chat-message assistant-message"><strong>🤖 {t("assistant")}:</strong><br>{response}</div>',
                        unsafe_allow_html=True
                    )
                    
                except Exception as e:
                    error_msg = f"{t('error_label')}: {str(e)}"
                    st.markdown(
                        f'<div class="chat-message error-message"><strong>❌ {t("error_label")}:</strong><br>{error_msg}</div>',
                        unsafe_allow_html=True
                    )
            
            # 重新运行以更新界面
            st.rerun()
    else:
        st.info(f"💡 {t('please_select_model')}")
        st.chat_input(t("please_connect_model"), disabled=True)

def main():
    """主函数"""
    # 初始化会话状态
    init_session_state()
    
    # 渲染侧边栏
    render_sidebar()
    
    # 渲染聊天界面
    render_chat_interface()
    
    # 页脚
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: #666; font-size: 0.8rem;'>"
        f"{t('powered_by')}"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()