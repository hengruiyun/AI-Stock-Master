#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 配置对话框

功能：
版本：1.0.0
"""

import sys
import json
import webbrowser
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QComboBox, QCheckBox,
    QGroupBox, QTextBrowser, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon


class APIKeyDialog(QDialog):
    """API Key 配置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 服务配置 - SiliconFlow")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # 获取配置文件路径
        self.config_path = self._get_config_path()
        
        # 加载模型配置
        self.models_config = self._load_models_config()
        
        # 设置UI
        self.setup_ui()
        
    def _get_config_path(self):
        """获取配置文件路径"""
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = Path(sys.executable).parent
        else:
            # 开发环境
            base_path = Path(__file__).parent
        
        config_file = base_path / "llm-api" / "config" / "user_settings.json"
        
        # 确保目录存在
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        return config_file
    
    def _load_models_config(self):
        """加载模型配置"""
        # 获取项目根目录
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
        
        models_file = base_path / "llm-api" / "config" / "api_models.json"
        
        try:
            with open(models_file, 'r', encoding='utf-8') as f:
                models = json.load(f)
            
            # 筛选出 SiliconFlow 的模型（排除 custom）
            siliconflow_models = [
                model for model in models 
                if model['provider'] == 'SiliconFlow' and 'custom' not in model['display_name'].lower()
            ]
            
            return siliconflow_models
        except Exception as e:
            print(f"加载模型配置失败: {e}")
            # 返回默认模型列表
            return [
                {"display_name": "[siliconflow] Qwen3-8B", "model_name": "Qwen/Qwen3-8B", "provider": "SiliconFlow"},
                {"display_name": "[siliconflow] DeepSeek-V3", "model_name": "deepseek-ai/DeepSeek-V3", "provider": "SiliconFlow"},
            ]
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("欢迎使用 AI 股票分析大师")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("首次使用需要配置 AI 服务，让我们开始吧！")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(subtitle_label)
        
        # 供应商简介组
        intro_group = QGroupBox("📖 关于 SiliconFlow（硅基流动）")
        intro_layout = QVBoxLayout()
        
        intro_text = QTextBrowser()
        intro_text.setMaximumHeight(120)
        intro_text.setOpenExternalLinks(False)
        intro_text.setHtml("""
        <div style="font-family: Arial, 'Microsoft YaHei'; font-size: 11px; line-height: 1.6;">
            <p><b>SiliconFlow</b> 是国内领先的 AI 模型推理加速服务提供商，提供：</p>
            <ul style="margin: 5px 0; padding-left: 20px;">
                <li>✅ <b>高性价比</b>：相比其他服务商价格更低，性能更优</li>
                <li>✅ <b>多模型支持</b>：DeepSeek、Qwen、GLM 等主流模型</li>
                <li>✅ <b>稳定可靠</b>：99.9% 可用性保证，国内访问速度快</li>
                <li>✅ <b>新用户福利</b>：注册即送免费额度，无需信用卡</li>
            </ul>
            <p style="margin-top: 10px; color: #0078d4;">
                <b>官网：</b> <a href="https://cloud.siliconflow.cn/i/GvCcTpzt" style="color: #0078d4;">https://cloud.siliconflow.cn/i/GvCcTpzt</a>
            </p>
        </div>
        """)
        intro_text.anchorClicked.connect(self._open_url)
        intro_layout.addWidget(intro_text)
        
        # 官方注册按钮
        register_btn = QPushButton("🌐 前往官网注册并获取 API Key")
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        register_btn.clicked.connect(lambda: self._open_url("https://cloud.siliconflow.cn/i/GvCcTpzt"))
        intro_layout.addWidget(register_btn)
        
        intro_group.setLayout(intro_layout)
        layout.addWidget(intro_group)
        
        # 配置组
        config_group = QGroupBox("⚙️ API 配置")
        config_layout = QVBoxLayout()
        config_layout.setSpacing(10)
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("选择模型：")
        model_label.setMinimumWidth(80)
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(30)
        for model in self.models_config:
            self.model_combo.addItem(model['display_name'], model['model_name'])
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        config_layout.addLayout(model_layout)
        
        # API Key 输入
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel("API Key：")
        api_key_label.setMinimumWidth(80)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入您的 SiliconFlow API Key（以 sk- 开头）")
        self.api_key_input.setMinimumHeight(30)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        config_layout.addLayout(api_key_layout)
        
        # 提示信息
        hint_label = QLabel("💡 提示：API Key 可在 SiliconFlow 控制台的「API Keys」页面获取")
        hint_label.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        hint_label.setWordWrap(True)
        config_layout.addWidget(hint_label)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 下次不再显示选项
        self.dont_show_again_checkbox = QCheckBox("下次不再显示此窗口")
        self.dont_show_again_checkbox.setStyleSheet("font-size: 11px;")
        # 连接状态改变信号，立即保存
        self.dont_show_again_checkbox.stateChanged.connect(self._on_dont_show_changed)
        layout.addWidget(self.dont_show_again_checkbox)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("稍后配置")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # 保存按钮
        save_btn = QPushButton("保存配置")
        save_btn.setMinimumWidth(100)
        save_btn.setMinimumHeight(35)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _open_url(self, url):
        """打开URL"""
        if isinstance(url, str):
            webbrowser.open(url)
        else:
            # QUrl 对象
            webbrowser.open(url.toString())
    
    def _on_dont_show_changed(self, state):
        """下次不再显示选项改变时立即保存"""
        try:
            # 读取现有配置
            config = {}
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except Exception as e:
                    print(f"读取配置文件失败: {e}")
            
            # 更新"下次不再显示"选项
            config['dont_show_api_dialog'] = self.dont_show_again_checkbox.isChecked()
            
            # 保存配置
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                status = "已启用" if config['dont_show_api_dialog'] else "已禁用"
                print(f"[API配置] 下次不再显示选项已保存: {status}")
                
            except Exception as e:
                print(f"[API配置] 保存下次不再显示选项失败: {e}")
                
        except Exception as e:
            print(f"[API配置] 处理下次不再显示选项时出错: {e}")
    
    def save_config(self):
        """保存配置"""
        # 验证 API Key
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(
                self,
                "输入错误",
                "请输入 API Key！\n\n如果您还没有 API Key，请点击「前往官网注册」按钮获取。"
            )
            return
        
        if not api_key.startswith('sk-'):
            QMessageBox.warning(
                self,
                "格式错误",
                "API Key 格式不正确！\n\nSiliconFlow 的 API Key 应该以 'sk-' 开头。"
            )
            return
        
        # 获取选中的模型
        selected_model = self.model_combo.currentData()
        
        # 读取现有配置
        config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                print(f"读取配置文件失败: {e}")
        
        # 更新配置
        config['default_provider'] = 'SiliconFlow'
        config['default_chat_model'] = selected_model
        config['default_structured_model'] = selected_model
        config['SILICONFLOW_API_KEY'] = api_key
        config['SILICONFLOW_BASE_URL'] = 'https://api.siliconflow.cn/v1'
        
        # "下次不再显示"选项已经在 _on_dont_show_changed 中实时保存了
        # 这里保持配置文件中的值不变
        if 'dont_show_api_dialog' not in config:
            config['dont_show_api_dialog'] = self.dont_show_again_checkbox.isChecked()
        
        # 保存配置
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(
                self,
                "保存成功",
                f"配置已保存！\n\n"
                f"供应商：SiliconFlow\n"
                f"模型：{self.model_combo.currentText()}\n\n"
                f"您现在可以使用 AI 分析功能了。"
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"保存配置文件失败：\n\n{str(e)}\n\n请检查文件权限。"
            )


def should_show_api_dialog():
    """
    检查是否应该显示 API Key 配置对话框
    
    必须同时满足所有条件：
    1. 当前是中文系统
    2. "下次不再显示"开关没有开启
    3. 当前供应商的API Key为空
    4. 供应商不是Ollama或LMStudio
    5. AI累计使用量>20（试用期结束）
    
    Returns:
        bool: 是否应该显示对话框
    """
    # 检查系统语言
    try:
        from config.gui_i18n import get_system_language
        system_lang = get_system_language()
        if not system_lang.startswith('zh'):
            return False
    except Exception as e:
        print(f"检测系统语言失败: {e}")
        # 默认认为是中文系统
        pass
    
    # 获取配置文件路径
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent
    
    config_file = base_path / "llm-api" / "config" / "user_settings.json"
    
    # 检查配置文件
    if not config_file.exists():
        return True  # 配置文件不存在，应该显示
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查"下次不再显示"选项
        if config.get('dont_show_api_dialog', False):
            return False
        
        # 检查当前供应商
        default_provider = config.get('default_provider', '').lower()
        print(f"[API配置] 当前供应商: {default_provider}")
        
        # 如果是Ollama或LMStudio，不需要API Key，不显示对话框
        if default_provider in ['ollama', 'lmstudio']:
            print(f"[API配置] 供应商为 {default_provider}，不需要API Key，不显示对话框")
            return False
        
        # 检查当前供应商是否有API Key
        provider_key_mapping = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'google': 'GOOGLE_API_KEY',
            'groq': 'GROQ_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'siliconflow': 'SILICONFLOW_API_KEY',
            'volcengine': 'VOLCENGINE_API_KEY',
            'bailian': 'BAILIAN_API_KEY',
        }
        
        # 获取当前供应商对应的API Key字段
        key_field = provider_key_mapping.get(default_provider)
        current_api_key = ''
        if key_field:
            current_api_key = config.get(key_field, '').strip()
        
        print(f"[API配置] 当前供应商 {default_provider} 的API Key: {'已配置' if current_api_key else '未配置'}")
        
        # 如果当前供应商有API Key，不显示对话框
        if current_api_key:
            print(f"[API配置] 当前供应商已配置API Key，不显示对话框")
            return False
        
        # 检查AI使用量
        ai_usage_count = 0
        try:
            from utils.ai_usage_counter import get_ai_usage_count
            ai_usage_count = get_ai_usage_count()
            print(f"[API配置] 当前AI使用次数: {ai_usage_count}")
        except Exception as e:
            print(f"[API配置] 获取AI使用次数失败: {e}")
        
        # 判断是否显示对话框
        # 必须同时满足所有条件：
        # 1. 中文系统（已在前面检查）
        # 2. 当前供应商API Key为空（已在上面检查）
        # 3. 供应商不是Ollama/LMStudio（已在上面检查）
        # 4. AI使用量>20
        if ai_usage_count > 20:
            print(f"[API配置] 所有条件满足：中文系统 + 供应商({default_provider})API Key为空 + 非本地模型 + AI使用量({ai_usage_count})>20，显示配置对话框")
            return True
        else:
            print(f"[API配置] AI使用次数（{ai_usage_count}）未超过20次，试用期内，不显示对话框")
            return False
        
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return True  # 读取失败，显示对话框


# 测试代码
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 测试是否应该显示对话框
    if should_show_api_dialog():
        print("应该显示 API Key 配置对话框")
        dialog = APIKeyDialog()
        result = dialog.exec_()
        print(f"对话框结果: {'已保存' if result == QDialog.Accepted else '已取消'}")
    else:
        print("不需要显示 API Key 配置对话框")
    
    sys.exit(0)

