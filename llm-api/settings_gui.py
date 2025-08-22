# -*- coding: utf-8 -*-
"""
from tools.unified_i18n_manager import _
设置界面 - Windows经典风格
功能：选择模型供应商、模型、填写API Key
配置读取顺序：配置文件 -> .env文件 -> 环境变量 -> 默认值
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from config_manager import ConfigManager
from i18n import get_i18n, t, Language


class SettingsWindow:
    """设置窗口类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        self.config_file_path = Path(__file__).parent / "config" / "user_settings.json"
        self.providers_models = self._load_models_config()
        self.current_config = {}
        
        # 初始化国际化
        self.i18n = get_i18n()
        # 自动检测系统语言
        # i18n已经在初始化时自动检测了系统语言，无需手动设置
        
        self._setup_window()
        self._create_widgets()
        self._load_current_settings()
        # 初始化界面语言
        self._update_ui_language()
        
    def _setup_window(self):
        """设置窗口属性"""
        self.root.title(self._t("settings_title", "Settings", "设置"))
        self.root.geometry("600x580")  # 增加高度以显示语言选择器
        self.root.resizable(False, False)
        
        # Windows经典风格
        self.root.configure(bg='#f0f0f0')
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (580 // 2)
        self.root.geometry(f"600x580+{x}+{y}")
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            # 优先使用项目根目录的mrcai.ico
            icon_paths = [
                "../mrcai.ico",
                "../resources/icons/mrcai.ico",
                "../resources/icons/app.ico"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    return
        except Exception as e:
            print(f"Warning: Failed to set window icon: {e}")
    
    def _t(self, key: str, en_text: str, zh_text: str) -> str:
        """简化的翻译函数"""
        if self.i18n.get_current_language() == Language.CHINESE:
            return zh_text
        return en_text
    
    def _update_ui_language(self):
        """更新界面语言"""
        # 更新窗口标题
        self.root.title(self._t("settings_title", "Settings", "设置"))
        
        # 更新所有文本控件
        self._update_widget_texts()
    

    
    def _update_widget_texts(self):
        """更新所有控件的文本"""
        # 更新标签文本
        self.title_label.config(text=self._t("app_title", "LLM API Settings", "LLM API 设置"))
        self.provider_label.config(text=self._t("provider", "Model Provider:", "模型供应商:"))
        self.model_label.config(text=self._t("model", "Model:", "模型:"))
        self.api_key_label.config(text=self._t("api_key", "API Key:", "API Key:"))
        self.agent_label.config(text=self._t("agent_setting", "Agent Setting:", "智能体功能设定:"))
        self.advanced_frame.config(text=self._t("advanced_settings", "Advanced Settings", "高级设置"))
        self.base_url_label.config(text=self._t("base_url", "Base URL (Optional):", "Base URL (可选):"))
        self.timeout_label.config(text=self._t("timeout", "Request Timeout (seconds):", "请求超时 (秒):"))
        self.cancel_btn.config(text=self._t("cancel", "Cancel", "取消"))
        self.save_btn.config(text=self._t("save", "Save", "保存"))
        
        # 更新智能体默认值
        current_agent = self.agent_var.get()
        if current_agent in ["不使用", "None"]:
            self.agent_combo.set(self._t("no_agent", "None", "不使用"))
        
        # 更新供应商改变时的相关文本
        provider = self.provider_var.get()
        if provider:
            self._update_provider_specific_texts(provider)
    
    def _update_provider_specific_texts(self, provider):
        """更新供应商特定的文本"""
        if provider in ['Ollama', 'LMStudio']:
            self.api_key_label.config(text=self._t("api_key_not_needed", "API Key (Not Required):", "API Key (不需要):"))
            self.model_label.config(text=self._t("model_name", "Model Name:", "模型名称:"))
        else:
            api_key_labels_en = {
                'OpenAI': 'OpenAI API Key:',
                'Anthropic': 'Anthropic API Key:',
                'DeepSeek': 'DeepSeek API Key:',
                'Groq': 'Groq API Key:',
                'Gemini': 'Google API Key:'
            }
            api_key_labels_zh = {
                'OpenAI': 'OpenAI API Key:',
                'Anthropic': 'Anthropic API Key:',
                'DeepSeek': 'DeepSeek API Key:',
                'Groq': 'Groq API Key:',
                'Gemini': 'Google API Key:'
            }
            en_text = api_key_labels_en.get(provider, 'API Key:')
            zh_text = api_key_labels_zh.get(provider, 'API Key:')
            self.api_key_label.config(text=self._t(f"api_key_{provider.lower()}", en_text, zh_text))
            self.model_label.config(text=self._t("model", "Model:", "模型:"))
        
    def _load_models_config(self) -> Dict[str, List[Dict]]:
        """加载模型配置"""
        config_path = Path(__file__).parent / "config" / "api_models.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                models = json.load(f)
            
            # 按供应商分组
            providers = {}
            for model in models:
                provider = model['provider']
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(model)
            
            return providers
        except Exception as e:
            messagebox.showerror("错误", f"加载模型配置失败: {e}")
            return {}
    
    def _get_available_agents(self) -> List[str]:
        """获取所有可用的智能体角色"""
        agents = ["不使用"]  # 默认选项
        
        # 从prompts目录读取所有可用的智能体
        prompts_dir = Path(__file__).parent / "prompts"
        if prompts_dir.exists():
            # 扫描prompts目录下的json文件
            for json_file in prompts_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                        # 获取智能体名称，优先使用name字段，否则使用文件名
                        agent_name = prompt_data.get('name', json_file.stem)
                        if agent_name not in agents:
                            agents.append(agent_name)
                except Exception as e:
                    print(f"读取智能体文件 {json_file} 失败: {e}")
                    continue
        
        # 添加一些预定义的智能体角色（如果文件中没有的话）
        predefined_agents = [
            "通用助手", "数据分析师", "翻译专家", "编程助手", "教学助手", 
            "写作助手", "研究助手", "业务顾问", "金融分析师", "法律顾问",
            "专业厨师", "健身教练", "医生", "心理医生", "木匠", "营养师",
            "室内设计师", "摄影师", "电脑专家", "音乐家", "画家"
        ]
        
        for agent in predefined_agents:
            if agent not in agents:
                agents.append(agent)
        
        return agents
    
    def _create_widgets(self):
        """创建界面组件"""
        # 统一字体大小
        self.font_normal = ('MS Sans Serif', 10)
        self.font_title = ('MS Sans Serif', 14, 'bold')
        
        # 主框架
        main_frame = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # 自动检测系统语言，不显示语言选择控件
        
        # 标题
        self.title_label = tk.Label(main_frame, text=self._t("app_title", "LLM API Settings", "LLM API 设置"), 
                                   font=self.font_title,
                                   bg='#f0f0f0', fg='#000000')
        self.title_label.pack(pady=(0, 20))
        
        # 供应商选择
        provider_frame = tk.Frame(main_frame, bg='#f0f0f0')
        provider_frame.pack(fill='x', pady=(0, 10))
        
        self.provider_label = tk.Label(provider_frame, text=self._t("provider", "Model Provider:", "模型供应商:"), 
                                      font=self.font_normal, bg='#f0f0f0')
        self.provider_label.pack(anchor='w')
        
        self.provider_var = tk.StringVar()
        self.provider_combo = ttk.Combobox(provider_frame, textvariable=self.provider_var,
                                          values=list(self.providers_models.keys()),
                                          state='readonly', width=40, font=self.font_normal)
        self.provider_combo.pack(fill='x', pady=(5, 0))
        self.provider_combo.bind('<<ComboboxSelected>>', self._on_provider_changed)
        
        # 模型选择/输入框架
        model_frame = tk.Frame(main_frame, bg='#f0f0f0')
        model_frame.pack(fill='x', pady=(0, 10))
        
        self.model_label = tk.Label(model_frame, text=self._t("model", "Model:", "模型:"), 
                                   font=self.font_normal, bg='#f0f0f0')
        self.model_label.pack(anchor='w')
        
        # 模型选择下拉框（用于有预定义模型的供应商）
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                       state='readonly', width=40, font=self.font_normal)
        self.model_combo.pack(fill='x', pady=(5, 0))
        
        # 模型名称输入框（用于Ollama/LMStudio）
        self.model_name_var = tk.StringVar()
        self.model_name_entry = tk.Entry(model_frame, textvariable=self.model_name_var,
                                        width=50, font=self.font_normal)
        
        # API Key输入框架
        self.api_key_frame = tk.Frame(main_frame, bg='#f0f0f0')
        self.api_key_frame.pack(fill='x', pady=(0, 10))
        
        self.api_key_label = tk.Label(self.api_key_frame, text=self._t("api_key", "API Key:", "API Key:"), 
                                     font=self.font_normal, bg='#f0f0f0')
        self.api_key_label.pack(anchor='w')
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = tk.Entry(self.api_key_frame, textvariable=self.api_key_var,
                                     width=50, font=self.font_normal)
        self.api_key_entry.pack(fill='x', pady=(5, 0))
        
        # 智能体功能设定
        agent_frame = tk.Frame(main_frame, bg='#f0f0f0')
        agent_frame.pack(fill='x', pady=(0, 10))
        
        self.agent_label = tk.Label(agent_frame, text=self._t("agent_setting", "Agent Setting:", "智能体功能设定:"), 
                                   font=self.font_normal, bg='#f0f0f0')
        self.agent_label.pack(anchor='w')
        
        self.agent_var = tk.StringVar()
        # 获取所有可用的智能体角色
        agent_options = self._get_available_agents()
        self.agent_combo = ttk.Combobox(agent_frame, textvariable=self.agent_var,
                                       values=agent_options,
                                       state='readonly', width=40, font=self.font_normal)
        self.agent_combo.pack(fill='x', pady=(5, 0))
        self.agent_combo.set(self._t("no_agent", "None", "不使用"))  # 默认值
        
        # 高级设置
        self.advanced_frame = tk.LabelFrame(main_frame, text=self._t("advanced_settings", "Advanced Settings", "高级设置"), 
                                           font=self.font_normal,
                                           bg='#f0f0f0', fg='#000000')
        self.advanced_frame.pack(fill='x', pady=(10, 0))
        
        # Base URL
        base_url_frame = tk.Frame(self.advanced_frame, bg='#f0f0f0')
        base_url_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        self.base_url_label = tk.Label(base_url_frame, text=self._t("base_url", "Base URL (Optional):", "Base URL (可选):"), 
                                      font=self.font_normal, bg='#f0f0f0')
        self.base_url_label.pack(anchor='w')
        
        self.base_url_var = tk.StringVar()
        self.base_url_entry = tk.Entry(base_url_frame, textvariable=self.base_url_var,
                                      width=50, font=self.font_normal)
        self.base_url_entry.pack(fill='x', pady=(5, 0))
        
        # Request Timeout
        timeout_frame = tk.Frame(self.advanced_frame, bg='#f0f0f0')
        timeout_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        self.timeout_label = tk.Label(timeout_frame, text=self._t("timeout", "Request Timeout (seconds):", "请求超时 (秒):"), 
                                     font=self.font_normal, bg='#f0f0f0')
        self.timeout_label.pack(anchor='w')
        
        self.timeout_var = tk.StringVar()
        self.timeout_entry = tk.Entry(timeout_frame, textvariable=self.timeout_var,
                                     width=20, font=self.font_normal)
        self.timeout_entry.pack(anchor='w', pady=(5, 0))
        
        # 按钮框架
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill='x', pady=(20, 0))
        
        # 取消按钮
        self.cancel_btn = tk.Button(button_frame, text=self._t("cancel", "Cancel", "取消"), width=10, height=1,
                                   font=self.font_normal,
                                   command=self._on_cancel)
        self.cancel_btn.pack(side='right', padx=(10, 0))
        
        # 保存按钮
        self.save_btn = tk.Button(button_frame, text=self._t("save", "Save", "保存"), width=10, height=1,
                                 font=self.font_normal,
                                 command=self._on_save)
        self.save_btn.pack(side='right')
        
    def _on_provider_changed(self, event=None):
        """供应商改变时的处理"""
        provider = self.provider_var.get()
        
        # 所有供应商都显示模型输入框，同时也显示下拉选择（如果有预定义模型）
        self.model_label.config(text="模型名称:")
        
        # 清空模型名称输入框的内容
        self.model_name_var.set('')
        
        # 始终显示文本输入框用于自定义模型
        self.model_name_entry.pack(fill='x', pady=(5, 0))
        self.model_name_entry.config(state='normal')
        
        # 如果供应商有预定义模型，也显示下拉选择框
        if provider in self.providers_models and self.providers_models[provider]:
            self.model_combo.pack(fill='x', pady=(5, 0))
            models = [model['display_name'] for model in self.providers_models[provider]]
            self.model_combo['values'] = models
            if models:
                self.model_combo.set(models[0])
            else:
                self.model_combo.set('')
        else:
            self.model_combo.pack_forget()
            self.model_combo.set('')
        
        # 始终显示API Key输入框，但根据供应商设置状态
        self.api_key_frame.pack(fill='x', pady=(0, 10))
        
        # 根据供应商更新API Key标签和状态
        if provider in ['Ollama', 'LMStudio']:
            self.api_key_label.config(text="API Key (不需要):")
            self.api_key_entry.config(state='disabled')  # 禁止状态而不是隐藏
            self.api_key_var.set('')  # 清空内容
        else:
            api_key_labels = {
                'OpenAI': 'OpenAI API Key:',
                'Anthropic': 'Anthropic API Key:',
                'DeepSeek': 'DeepSeek API Key:',
                'Groq': 'Groq API Key:',
                'Gemini': 'Google API Key:'
            }
            self.api_key_label.config(text=api_key_labels.get(provider, 'API Key:'))
            self.api_key_entry.config(state='normal')  # 启用状态
                
        # 加载对应的API Key
        self._load_api_key_for_provider(provider)
        
        # 加载对应的Base URL
        self._load_base_url_for_provider(provider)
        
        # 更新供应商特定的文本
        self._update_provider_specific_texts(provider)
    
    def _load_api_key_for_provider(self, provider):
        """为指定供应商加载API Key"""
        # API Key环境变量映射
        api_key_mapping = {
            'OpenAI': 'OPENAI_API_KEY',
            'Anthropic': 'ANTHROPIC_API_KEY', 
            'DeepSeek': 'DEEPSEEK_API_KEY',
            'Groq': 'GROQ_API_KEY',
            'Gemini': 'GOOGLE_API_KEY'
        }
        
        env_key = api_key_mapping.get(provider)
        if env_key:
            # 从配置中获取API Key
            api_key = self.config_manager.get(env_key, '')
            self.api_key_var.set(api_key)
        else:
            # 对于Ollama、LMStudio等不需要API Key的供应商，保持为空
            # 但不主动清空，因为字段现在是禁止状态
            pass
    
    def _load_base_url_for_provider(self, provider):
        """为指定供应商加载Base URL"""
        # Base URL环境变量映射和默认值
        base_url_mapping = {
            'OpenAI': ('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
            'Anthropic': ('ANTHROPIC_BASE_URL', 'https://api.anthropic.com'),
            'DeepSeek': ('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
            'Groq': ('GROQ_BASE_URL', 'https://api.groq.com/openai/v1'),
            'Gemini': ('GOOGLE_BASE_URL', 'https://generativelanguage.googleapis.com'),
            'Ollama': ('OLLAMA_BASE_URL', 'http://localhost:11434'),
            'LMStudio': ('LMSTUDIO_BASE_URL', 'http://localhost:1234/v1')
        }
        
        if provider in base_url_mapping:
            env_key, default_url = base_url_mapping[provider]
            # 优先从当前配置读取Base URL，如果没有则使用配置管理器的值，最后才使用默认值
            base_url = self.current_config.get(env_key) or self.config_manager.get(env_key, default_url)
            self.base_url_var.set(base_url)
        else:
            # 未知供应商，清空base_url
            self.base_url_var.set('')
    
    def _load_current_settings(self):
        """加载当前设置"""
        # 读取顺序：配置文件 -> .env文件 -> 环境变量 -> 默认值
        
        # 1. 尝试从配置文件读取
        config_from_file = self._load_config_file()
        
        # 2. 从配置管理器获取（包含.env和环境变量）
        default_settings = self.config_manager.get_default_settings()
        
        # 合并配置（配置文件优先）
        self.current_config = {**default_settings, **config_from_file}
        
        # 设置界面值
        provider = self.current_config.get('default_provider', 'OpenAI')
        if provider in self.providers_models or provider in ['Ollama', 'LMStudio']:
            self.provider_var.set(provider)
            self._on_provider_changed()
            
            # 设置模型
            model_name = self.current_config.get('default_chat_model', '')
            if model_name:
                if provider in ['Ollama', 'LMStudio']:
                    # 对于Ollama和LMStudio，直接设置模型名称
                    self.model_name_var.set(model_name)
                else:
                    # 先尝试在预定义模型中查找
                    found_in_predefined = False
                    if provider in self.providers_models:
                        for model in self.providers_models[provider]:
                            if model['model_name'] == model_name:
                                self.model_var.set(model['display_name'])
                                found_in_predefined = True
                                break
                    
                    # 如果在预定义模型中没找到，说明是自定义模型，设置到输入框
                    if not found_in_predefined:
                        self.model_name_var.set(model_name)
        
        # 设置API Key
        api_key = self.config_manager.get_api_key(provider.lower())
        if api_key:
            self.api_key_var.set(api_key)
        
        # 设置基础URL
        base_url = self.config_manager.get_base_url(provider.lower())
        if base_url:
            self.base_url_var.set(base_url)
        
        # 设置超时
        timeout = self.current_config.get('request_timeout', 30)
        self.timeout_var.set(str(timeout))
        
        # 设置智能体
        agent_role = self.current_config.get('agent_role', '不使用')
        self.agent_var.set(agent_role)
    
    def _load_config_file(self) -> Dict[str, Any]:
        """从配置文件加载设置"""
        try:
            if self.config_file_path.exists():
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
        return {}
    
    def _save_config_file(self, config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return False
    
    def _get_selected_model_info(self):
        """获取选中的模型信息"""
        provider = self.provider_var.get()
        
        # 优先检查用户是否在输入框中输入了自定义模型名称
        custom_model_name = self.model_name_var.get().strip()
        if custom_model_name:
            # 用户输入了自定义模型名称，使用自定义名称
            return {
                'display_name': custom_model_name,
                'model_name': custom_model_name,
                'provider': provider
            }
        
        # 如果没有自定义输入，且有预定义模型，则使用下拉选择的模型
        if provider in self.providers_models:
            model_display_name = self.model_var.get()
            for model in self.providers_models[provider]:
                if model['display_name'] == model_display_name:
                    return model
        
        return None
    
    def _validate_settings(self) -> bool:
        """验证设置"""
        # 检查供应商
        provider = self.provider_var.get()
        if not provider:
            messagebox.showerror("错误", "请选择模型供应商")
            return False
        
        # 检查模型（所有供应商都需要模型名称）
        custom_model_name = self.model_name_var.get().strip()
        selected_model = self.model_var.get()
        
        if not custom_model_name and not selected_model:
            messagebox.showerror("错误", "请输入模型名称或选择预定义模型")
            return False
        
        # 检查API Key（仅对需要API Key的供应商）
        if provider not in ['Ollama', 'LMStudio']:
            if not self.api_key_var.get().strip():
                messagebox.showerror("错误", f"请输入{provider} API Key")
                return False
        
        # 检查超时设置
        try:
            timeout = int(self.timeout_var.get())
            if timeout <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "请输入有效的超时时间（正整数）")
            return False
        
        return True
    
    def _on_save(self):
        """保存设置"""
        if not self._validate_settings():
            return
        
        try:
            # 获取选中的模型信息
            model_info = self._get_selected_model_info()
            if not model_info:
                messagebox.showerror("错误", "无法获取模型信息")
                return
            
            provider = self.provider_var.get()
            
            # 构建配置
            config = {
                'default_provider': provider,
                'default_chat_model': model_info['model_name'],
                'default_structured_model': model_info['model_name'],
                'request_timeout': int(self.timeout_var.get()),
                'agent_role': self.agent_var.get(),
            }
            
            # 添加API Key（仅对需要API Key的供应商）
            if provider not in ['Ollama', 'LMStudio']:
                api_key = self.api_key_var.get().strip()
                if api_key:
                    api_key_mapping = {
                        'OpenAI': 'OPENAI_API_KEY',
                        'Anthropic': 'ANTHROPIC_API_KEY',
                        'DeepSeek': 'DEEPSEEK_API_KEY',
                        'Groq': 'GROQ_API_KEY',
                        'Gemini': 'GOOGLE_API_KEY'
                    }
                    if provider in api_key_mapping:
                        config[api_key_mapping[provider]] = api_key
            
            # 添加基础URL（如果提供）
            base_url = self.base_url_var.get().strip()
            if base_url:
                base_url_mapping = {
                    'OpenAI': 'OPENAI_BASE_URL',
                    'Anthropic': 'ANTHROPIC_BASE_URL',
                    'Groq': 'GROQ_BASE_URL',
                    'DeepSeek': 'DEEPSEEK_BASE_URL',
                    'Gemini': 'GOOGLE_BASE_URL',
                    'Ollama': 'OLLAMA_BASE_URL',
                    'LMStudio': 'LMSTUDIO_BASE_URL'
                }
                base_url_key = base_url_mapping.get(provider)
                if base_url_key:
                    config[base_url_key] = base_url
            
            # 保存配置
            if self._save_config_file(config):
                messagebox.showinfo("成功", "设置已保存")
                self.root.destroy()
                
        except Exception as e:
            messagebox.showerror("错误", f"保存设置时出错: {e}")
    
    def _on_cancel(self):
        """取消设置"""
        self.root.destroy()
    
    def run(self):
        """运行设置窗口"""
        self.root.mainloop()


def main():
    """主函数"""
    app = SettingsWindow()
    app.run()


if __name__ == "__main__":
    main()