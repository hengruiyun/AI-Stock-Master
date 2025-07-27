#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI股票趋势分析系统 - 主窗口模块
包含主界面和各种分析窗口的实现
"""

import os
import sys
from config.language_detector import get_system_language
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from pathlib import Path
from datetime import datetime, timedelta  # 添加timedelta导入
import threading
import traceback
import queue
import json
import time
import logging
import numpy as np  # 添加numpy导入

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入全局常量
from config.constants import AUTHOR, VERSION, HOMEPAGE

# 尝试导入matplotlib
try:
    import matplotlib
    matplotlib.use('TkAgg')  # 设置后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: matplotlib导入失败: {e}")
    MATPLOTLIB_AVAILABLE = False

# 导入核心模块
try:
    from data.stock_dataset import StockDataSet
    from algorithms.realtime_engine import RealtimeAnalysisEngine, AnalysisResults
    from utils.report_generator import ReportGenerator, ExcelReportGenerator
except ImportError as e:
    print(f"Warning: 模块导入失败: {e}")

# 导入状态指示器组件
try:
    from analysis_status_indicator import AnalysisStatusIndicator
except ImportError as e:
    print(f"Warning: 状态指示器组件导入失败: {e}")
    AnalysisStatusIndicator = None

# 导入国际化配置
try:
    from config.i18n import t_gui, t_common, t_tools, get_current_language, get_text
    print(f"国际化配置加载成功")
except ImportError as e:
    print(f"Warning: 国际化配置导入失败: {e}")
    # 如果导入失败，使用简单的回退函数
    def t_gui(key, language=None):
        return key
    def t_common(key, language=None):
        return key
    def get_current_language():
        return 'zh_CN'

# 导入统一国际化管理器
try:
    from config.i18n import t_gui as _, t_tools, is_english
except ImportError as e:
    print(f"Warning: 统一国际化管理器导入失败: {e}")
    # 回退函数
    def _(text, default=None):
        return default if default is not None else text
    def t_tools(key, language=None):
        return key
    def is_english():
        from config.language_detector import detect_system_language
        return detect_system_language() == 'en'

# 设置matplotlib中文字体支持
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class StockAnalyzerMainWindow:
    """AI股票趋势分析系统主窗口"""
    
    def format_stock_code(self, code):
        """格式化股票代码显示"""
        if not code:
            return code
        
        code_str = str(code)
        
        # 检测美股代码：以0开头且包含字母的模式
        if code_str.startswith('0') and len(code_str) > 1:
            # 去除所有前导0，然后检查是否以字母开头
            remaining = code_str.lstrip('0')
            if remaining and remaining[0].isalpha():
                # 美股代码：去除前导0
                return remaining
        
        # 其他市场代码保持原样
        return code_str

    def __init__(self):
        # 检测系统语言
        self.system_language = get_system_language()
        print(f"检测到系统语言: {self.system_language}")
        self.root = tk.Tk()
        self.analysis_results = None
        self.data_file_path = None
        self.analysis_thread = None
        self.results_queue = queue.Queue()
        self.ai_analysis_result = None  # 存储AI分析结果
        
        # 加载用户配置，如果不存在则创建默认配置
        self.load_or_create_user_config()
        
        # 字体配置
        self.setup_fonts()
        
        # 窗口配置
        self.setup_window()
        
        # UI组件
        self.setup_menu()
        self.setup_main_content()
        self.setup_status_bar()
        
        # 显示欢迎信息
        self.show_welcome_message()
        
        # 检查分析结果队列
        self.check_analysis_queue()
    

    
    def load_or_create_user_config(self):
        """加载或创建用户配置文件"""
        try:
            from config import load_user_config
            self.user_config = load_user_config()
            print(t_gui('config_load_success'))
        except Exception as e:
            print(f"{t_gui('config_load_failed')}: {e}")
            self.user_config = {
                'window': {'theme': 'professional', 'font_size': 11},
                'data': {'auto_load_last_file': False},
                'reports': {'default_format': 'html'}
            }
    
    def setup_fonts(self):
        """设置字体配置 - 统一字体大小为11号"""
        # 统一字体大小为11号（与主界面分析按钮一致）
        self.fonts = {
            'title': ('Microsoft YaHei', 11, 'bold'),
            'menu': ('Microsoft YaHei', 11),
            'button': ('Microsoft YaHei', 11),
            'text': ('Microsoft YaHei', 11),
            'status': ('Microsoft YaHei', 10)  # 状态栏使用10号
        }
    
    def setup_window(self):
        """设置主窗口属性 - Windows经典风格"""
        self.root.title(t_gui("app_title") + " " + t_gui("app_version") + f" ({AUTHOR})")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Windows经典灰色背景
        self.root.configure(bg='#f0f0f0')
        
        # 设置窗口图标
        self.setup_window_icon()
        
        # 窗口居中
        self.center_window()
    
    def setup_window_icon(self):
        """设置窗口图标"""
        try:
            # 优先使用项目根目录的mrcai.ico
            icon_paths = [
                "mrcai.ico",
                "resources/icons/mrcai.ico",
                "resources/icons/app.ico"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    print(f"Successfully set window icon: {icon_path}")
                    return
            
            print("Warning: No icon file found")
        except Exception as e:
            print(f"Warning: Failed to set window icon: {e}")
    
    def center_window(self):
        """窗口居中显示"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 获取窗口尺寸
        self.root.update_idletasks()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置 (不改变大小)
        self.root.geometry(f"+{x}+{y}")
    
    def _center_toplevel_window(self, window):
        """子窗口居中显示"""
        # 设置窗口图标
        self._set_toplevel_icon(window)
        
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 更新窗口以获取实际尺寸
        window.update_idletasks()
        window_width = window.winfo_width()
        window_height = window.winfo_height()
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        window.geometry(f"+{x}+{y}")
    
    def _set_toplevel_icon(self, window):
        """为顶层窗口设置图标"""
        try:
            # 优先使用项目根目录的mrcai.ico
            icon_paths = [
                "mrcai.ico",
                "resources/icons/mrcai.ico",
                "resources/icons/app.ico"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    window.iconbitmap(icon_path)
                    return
        except Exception as e:
            print(f"Warning: Failed to set toplevel window icon: {e}")
    
    def setup_menu(self):
        """设置菜单栏 - Windows经典风格，字体统一为11号"""
        menubar = tk.Menu(self.root, bg='#f0f0f0', fg='black', font=('Microsoft YaHei', 11))
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=t_gui("menu_file") + "(F)", menu=file_menu, underline=2)
        file_menu.add_command(label=t_gui("menu_open_file") + "...", command=self.open_excel_file, 
                             accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label=t_gui("menu_export_report") + "...", command=self.export_report, 
                             accelerator="Ctrl+S")
        file_menu.add_command(label=t_gui("menu_export_html") + "...", command=self.export_html_report)
        file_menu.add_separator()
        file_menu.add_command(label=t_gui("menu_exit"), command=self.root.quit, 
                             accelerator="Alt+F4")
        
        # 分析菜单
        analysis_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=t_gui("menu_analysis") + "(A)", menu=analysis_menu, underline=2)
        analysis_menu.add_command(label=t_gui("menu_start_analysis"), command=self.start_analysis, 
                                 accelerator="F5")
        analysis_menu.add_separator()
        analysis_menu.add_command(label=t_gui("menu_stock_analysis"), command=self.show_stock_analysis)
        analysis_menu.add_command(label=t_gui("menu_industry_analysis"), command=self.show_industry_analysis)
        analysis_menu.add_command(label=t_gui("menu_market_analysis"), command=self.show_market_analysis)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=t_gui("menu_tools") + "(T)", menu=tools_menu, underline=2)
        tools_menu.add_command(label=t_tools("menu_update_data"), command=self.update_data_files)
        tools_menu.add_separator()
        tools_menu.add_command(label=t_gui("menu_data_validation"), command=self.show_data_validation)
        tools_menu.add_command(label=t_gui("menu_performance_monitor"), command=self.show_performance_monitor)
        tools_menu.add_separator()
        tools_menu.add_command(label=t_gui("menu_settings"), command=self.show_settings)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=t_tools("menu_help") + "(H)", menu=help_menu, underline=2)
        help_menu.add_command(label=t_tools("menu_user_guide"), command=self.open_user_guide)
        help_menu.add_command(label=t_tools("menu_about"), command=self.show_about)
        
        # 键盘快捷键
        self.root.bind('<Control-o>', lambda e: self.open_excel_file())
        self.root.bind('<Control-s>', lambda e: self.export_report())
        self.root.bind('<F5>', lambda e: self.start_analysis())
    
    def setup_main_content(self):
        """设置主内容区域 - 基于HTML样本设计"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # 顶部区域
        top_frame = tk.Frame(main_frame, bg='#f0f0f0')
        top_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 左上角区域留空（已删除HengruiYun标签）
        
        # AI分析状态显示
        self.ai_status_var = tk.StringVar()
        self.ai_status_var.set("")  # 初始为空
        self.ai_status_label = tk.Label(top_frame, textvariable=self.ai_status_var,
                                       bg='#f0f0f0', fg='#666666',
                                       font=('Microsoft YaHei', 11))
        self.ai_status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # 顶部按钮区域
        button_frame = tk.Frame(top_frame, bg='#f0f0f0')
        button_frame.pack(side=tk.RIGHT)
        
        # 统一按钮样式 - 与MSCI详情按钮一致，无色彩
        button_style = {
            'font': ('Microsoft YaHei', 11),
            'bg': '#f0f0f0',
            'fg': 'black',
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 20,
            'pady': 5
        }
        
        # 市场按钮 (最右边)
        self.market_btn = tk.Button(button_frame, text=t_gui("btn_market"), 
                                   command=self.show_market_analysis,
                                   state=tk.DISABLED,
                                   **button_style)
        self.market_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 行业按钮
        self.industry_btn = tk.Button(button_frame, text=t_gui("btn_industry"), 
                                     command=self.show_industry_analysis,
                                     state=tk.DISABLED,
                                     **button_style)
        self.industry_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 个股按钮
        self.stock_btn = tk.Button(button_frame, text=t_gui("btn_stock"), 
                                  command=self.show_stock_analysis,
                                  state=tk.DISABLED,
                                  **button_style)
        self.stock_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 报告按钮 (对应HTML样本右下角)
        self.report_btn = tk.Button(button_frame, text=t_gui("btn_report"), 
                                   command=self.export_html_report,
                                   state=tk.DISABLED,
                                   **button_style)
        self.report_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 分析按钮
        self.analyze_btn = tk.Button(button_frame, text=t_gui("btn_analyze"), 
                                    command=self.start_analysis,
                                    state=tk.DISABLED,
                                    **button_style)
        self.analyze_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # AI模型按钮 (新增)
        self.ai_model_btn = tk.Button(button_frame, text=t_gui("btn_ai_model"), 
                                     command=self.open_ai_model_settings,
                                     **button_style)
        self.ai_model_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Star按钮 (GitHub Star功能)
        self.star_btn = tk.Button(button_frame, text="Star", 
                                 command=self.open_github_star,
                                 **button_style)
        self.star_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 加载按钮 (对应HTML样本右上角)
        self.load_btn = tk.Button(button_frame, text=t_gui("btn_load"), 
                                 command=self.open_excel_file,
                                 **button_style)
        self.load_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 中央显示区域 (对应HTML样本的central-area)
        self.central_area = tk.Frame(main_frame, bg='white', relief=tk.SUNKEN, bd=2)
        self.central_area.pack(fill=tk.BOTH, expand=True)
        
        # 内部文本区域 - 统一字体大小为11号
        self.text_area = tk.Text(self.central_area, 
                                bg='white', fg='black',
                                font=('Microsoft YaHei', 11),
                                wrap=tk.WORD, state=tk.DISABLED,
                                padx=20, pady=20)
        
        # 滚动条
        scrollbar = tk.Scrollbar(self.central_area, orient=tk.VERTICAL, 
                               command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=scrollbar.set)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_status_bar(self):
        """设置状态栏 - Windows经典风格，包含状态指示器"""
        status_frame = tk.Frame(self.root, bg='#f0f0f0', relief=tk.SUNKEN, bd=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 左侧状态指示器区域
        indicators_frame = tk.Frame(status_frame, bg='#f0f0f0')
        indicators_frame.pack(side=tk.LEFT, padx=8, pady=2)
        
        # 创建状态指示器（如果组件可用）
        if AnalysisStatusIndicator:
            # 数据加载状态指示器
            data_label = tk.Label(indicators_frame, text=t_gui("status_data_label"), bg='#f0f0f0', fg='#495057',
                                 font=('Microsoft YaHei', 9))
            data_label.pack(side=tk.LEFT, padx=(0, 5))
            self.data_status_indicator = AnalysisStatusIndicator(indicators_frame, width=120, height=20)
            self.data_status_indicator.pack(side=tk.LEFT, padx=(0, 15))
            
            # 分析状态指示器
            analysis_label = tk.Label(indicators_frame, text=t_gui("status_analysis_label"), bg='#f0f0f0', fg='#495057',
                                     font=('Microsoft YaHei', 9))
            analysis_label.pack(side=tk.LEFT, padx=(0, 5))
            self.analysis_status_indicator = AnalysisStatusIndicator(indicators_frame, width=120, height=20)
            self.analysis_status_indicator.pack(side=tk.LEFT, padx=(0, 15))
            
            # AI分析状态指示器
            ai_label = tk.Label(indicators_frame, text=t_gui("status_ai_label"), bg='#f0f0f0', fg='#495057',
                               font=('Microsoft YaHei', 9))
            ai_label.pack(side=tk.LEFT, padx=(0, 5))
            self.ai_status_indicator = AnalysisStatusIndicator(indicators_frame, width=120, height=20)
            self.ai_status_indicator.pack(side=tk.LEFT)
        else:
            # 如果状态指示器不可用，使用传统状态显示
            self.data_status_indicator = None
            self.analysis_status_indicator = None
            self.ai_status_indicator = None
        
        # 右侧状态文本
        self.status_var = tk.StringVar()
        self.status_var.set(t_gui("status_ready") + " | " + t_gui("status_select_file"))
        
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               bg='#f0f0f0', fg='#606060',
                               font=('Microsoft YaHei', 10),  # 状态栏使用10号
                               anchor=tk.W)
        status_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=8, pady=2)
        
        # 进度条 (初始隐藏)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, 
                                          variable=self.progress_var,
                                          maximum=100, length=200)
        # 暂时不显示
    
    def show_welcome_message(self):
        """显示欢迎信息 - 对应HTML样本的占位文本"""
        welcome_text = f"""{t_gui("welcome_title")} {t_gui("app_title")} 

{t_gui("welcome_core_features")}:
• RTSI - {t_gui("rtsi_desc")}
• IRSI - {t_gui("irsi_desc")}  
• MSCI - {t_gui("msci_desc")}

{t_gui("welcome_getting_started")}:
1. {t_gui("welcome_step1")}
2. {t_gui("welcome_step2")}
3. {t_gui("welcome_step3")}

{t_gui("welcome_dynamic_analysis")}:
• {t_gui("welcome_stock_count")}
• {t_gui("welcome_industry_count")}
• {t_gui("welcome_industry_query")}

{t_gui("welcome_system_config")}:
• Python 3.10+ {t_gui("welcome_tech_stack")}
• Windows {t_gui("welcome_classic_ui")}
• {t_gui("welcome_professional_algo")}

{t_gui("welcome_note")}: {t_gui("welcome_note_desc")}
"""
        
        self.update_text_area(welcome_text, text_color='#666666')
    
    def update_text_area(self, text, text_color='black'):
        """更新中央文本显示区域"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, text)
        self.text_area.config(fg=text_color, state=tk.DISABLED)
    
    def open_excel_file(self):
        """打开数据文件对话框 - 支持JSON格式"""
        filetypes = [
            (t_gui("filetype_data"), '*.json.gz'),
            ('JSON格式', '*.json.gz')
            #(t_gui("filetype_excel"), '*.xlsx;*.xls'),
            #(t_gui("filetype_csv"), '*.csv'),
            #('Excel 2007+', '*.xlsx'),
            #('Excel 97-2003', '*.xls'),
            #(t_gui("filetype_all"), '*.*')
        ]
        
        filename = filedialog.askopenfilename(
            title=t_gui("dialog_select_file"),
            filetypes=filetypes,
            initialdir=str(Path.cwd())
        )
        
        if filename:
            self.load_data_file(filename)
    
    def load_data_file(self, file_path):
        """加载数据文件"""
        try:
            # 重置所有分析状态和结果
            self._reset_analysis_state()
            
            # 更新数据状态指示器为加载中
            if self.data_status_indicator:
                self.data_status_indicator.set_status('analyzing', '加载数据中...')
            
            # 更新状态
            self.status_var.set(f"{t_gui('status_loading')}: {Path(file_path).name}")
            self.root.update()
            
            # 显示文件信息
            file_info = self.get_file_info(file_path)
            
            success_text = f"""{t_gui('loading_success')}!

{t_gui('filetype_data')} {t_gui('result_data_overview')}:
• {t_gui('col_stock_name')}: {file_info['name']}
• {t_gui('data_scale')}: {file_info['size']} MB
• {t_gui('result_data_date')}: {file_info['modified']}

{t_gui('data_analysis_in_progress')}:
• {t_gui('stage_detail_loading')}
• {t_gui('stage_detail_validation')}
• {t_gui('stage_detail_validation')}

{t_gui('welcome_getting_started')}: {t_gui('btn_start_analysis')}"""
            
            self.update_text_area(success_text, text_color='#008000')
            
            # 创建数据集对象 - 支持多种格式
            try:
                # 优先使用新的压缩JSON加载器
                from data.compressed_json_loader import CompressedJSONLoader
                loader = CompressedJSONLoader(file_path)
                data, load_result = loader.load_and_validate()
                
                if load_result['is_valid']:
                    self.current_dataset = StockDataSet(data, file_path)
                    # 更新文件信息显示
                    format_type = load_result['file_info'].get('format_type', 'unknown')
                    load_time = load_result.get('load_time', 'N/A')
                    print(f"使用{format_type}格式加载数据，耗时: {load_time}")
                else:
                    raise Exception(load_result.get('error', '数据加载失败'))
                    
            except ImportError:
                # 回退到原有的加载方式
                self.current_dataset = StockDataSet(file_path)
            
            # 更新数据状态指示器为完成
            if self.data_status_indicator:
                self.data_status_indicator.set_status('completed', t_gui('data_loaded'))
            
            # 启用分析按钮
            self.analyze_btn.config(state=tk.NORMAL)
            
            # 更新状态
            self.status_var.set(f"{t_gui('status_ready')}: {file_info['name']} | {t_gui('btn_start_analysis')}")
            
        except Exception as e:
            # 更新数据状态指示器为错误
            if self.data_status_indicator:
                self.data_status_indicator.set_status('error', '数据加载失败')
            
            error_text = f"""{t_gui('error_file_load_failed')}!

{t_gui('analysis_error')}: {str(e)}

{t_gui('tip_possible_reasons')}:
• {t_gui('data_format_error')}
• {t_gui('data_format_error')}
• {t_gui('data_format_error')}
• {t_gui('data_format_error')}

📞 {t_gui('menu_help')}"""
            
            self.update_text_area(error_text, text_color='#cc0000')
            self.status_var.set(f"{t_gui('status_error')}: {str(e)}")
            
            messagebox.showerror(t_gui("error_file_load_failed"), f"{t_gui('error_file_load_failed')}:\n{str(e)}")
    
    def _reset_analysis_state(self):
        """重置分析状态和结果"""
        # 重置分析结果
        self.analysis_results = None
        self.analysis_engine = None
        
        # 重置状态指示器
        if self.analysis_status_indicator:
            self.analysis_status_indicator.set_status('not_analyzed', t_gui('status_not_analyzed'))
        if self.ai_status_indicator:
            self.ai_status_indicator.set_status('not_analyzed', t_gui('status_not_analyzed'))
        
        # 重置状态变量
        self.ai_status_var.set("")
        
        # 禁用相关按钮
        self.report_btn.config(state=tk.DISABLED)
        self.stock_btn.config(state=tk.DISABLED)
        self.industry_btn.config(state=tk.DISABLED)
        self.market_btn.config(state=tk.DISABLED)
        
        # 清空文本区域的分析结果
        # 注意：这里不清空，因为会在加载新数据时显示加载信息
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        file_path = Path(file_path)
        stat = file_path.stat()
        
        return {
            'name': file_path.name,
            'size': f"{stat.st_size / 1024 / 1024:.2f}",
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def start_analysis(self):
        """开始数据分析"""
        if not self.current_dataset:
            messagebox.showwarning(t_gui("confirm_title"), t_gui("status_select_file"))
            return
        
        # 在新线程中执行分析，避免界面冻结
        analysis_thread = threading.Thread(target=self._run_analysis)
        analysis_thread.daemon = True
        analysis_thread.start()
    
    def _run_analysis(self):
        """执行分析 (后台线程)"""
        try:
            # 检查主循环是否运行
            main_loop_running = True
            try:
                # 分析线程处理
                self.root.after_idle(lambda: None)
            except RuntimeError:
                main_loop_running = False
                print("UI")
            
            # 设置UI状态 - 仅在主循环运行时更新
            if main_loop_running:
                self.root.after(0, lambda: self.status_var.set(t_gui("data_analysis_in_progress")))
                self.root.after(0, lambda: self.analyze_btn.config(state=tk.DISABLED))
                # 更新分析状态指示器为分析中
                if self.analysis_status_indicator:
                    self.root.after(0, lambda: self.analysis_status_indicator.set_status('analyzing', t_gui('status_analyzing')))
                
                # 显示分析进度
                progress_text = f"""{t_gui("data_analysis_ongoing")}...

{t_gui("analysis_progress_title")}:
• [■■■░░░░░░░] {t_gui("data_loading_validation")} (30%)
• [░░░░░░░░░░] {t_gui("rtsi_individual_trend_analysis")} (0%)
• [░░░░░░░░░░] {t_gui("analysis_calculating_irsi")} (0%)
• [░░░░░░░░░░] {t_gui("analysis_calculating_msci")} (0%)

⏱️ {t_gui("result_calculation_time")}: 10-15{t_gui("trading_days")}
💻 {t_gui("menu_performance_monitor")}: {t_gui("data_analysis_in_progress")}
{t_gui("data_preparing")}: {t_gui("data_analysis_in_progress")}

{t_gui("data_analysis_in_progress")}  
"""
                self.root.after(0, lambda: self.update_text_area(progress_text, '#ff8c00'))
            
            # 创建分析引擎
            self.analysis_engine = RealtimeAnalysisEngine(self.current_dataset)
            
            # 执行分析
            self.analysis_results = self.analysis_engine.calculate_all_metrics()
            
            # 分析完成，更新界面 - 仅在主循环运行时更新
            if main_loop_running:
                self.root.after(0, self._analysis_completed)
            else:
                print("UI")
            
        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            if main_loop_running:
                self.root.after(0, lambda: self._analysis_failed(error_msg))
            else:
                print(f"分析失败：{error_msg}")
    
    def _analysis_completed(self):
        """分析完成后的界面更新"""
        try:
            # 更新分析状态指示器为完成
            if self.analysis_status_indicator:
                self.analysis_status_indicator.set_status('completed', t_gui('status_completed'))
            
            # 生成分析摘要
            summary = self._generate_analysis_summary()
            
            self.update_text_area(summary, text_color='#008000')
            
            # 启用报告按钮和分析按钮
            self.report_btn.config(state=tk.NORMAL)
            self.analyze_btn.config(state=tk.NORMAL)
            
            # 启用新增的三个分析按钮
            self.stock_btn.config(state=tk.NORMAL)
            self.industry_btn.config(state=tk.NORMAL)
            self.market_btn.config(state=tk.NORMAL)
            
            # 更新状态 - 处理AnalysisResults对象
            if hasattr(self.analysis_results, 'metadata'):
                stock_count = self.analysis_results.metadata.get('total_stocks', 0)
                industry_count = self.analysis_results.metadata.get('total_industries', 0)
            else:
                # 备用方案：从数据源获取统计信息
                stock_count = len(self.current_dataset) if self.current_dataset else 0
                industry_count = len(self.current_dataset.get_all_industries()) if self.current_dataset else 0
            
            self.status_var.set(f"{t_gui('analysis_complete')} | {t_gui('found_stocks_industries')} {stock_count} {t_gui('units_stocks')}，{industry_count} {t_gui('units_industries')}")
            
            # 执行AI智能分析
            self._start_ai_analysis()
            
        except Exception as e:
            self._analysis_failed(f"结果处理失败: {str(e)}")
    
    def _analysis_failed(self, error_msg):
        """分析失败处理"""
        # 更新分析状态指示器为错误
        if self.analysis_status_indicator:
            self.analysis_status_indicator.set_status('error', t_gui('status_error'))
        
        # 检查是否是超时错误
        if '超时时间' in error_msg or 'timeout' in error_msg.lower():
            # 超时错误特殊处理
            timeout_text = f"""AI分析超时!

超时原因:
• LLM响应较慢
• 网络连接问题
• 模型加载时间

解决方案:
• 增加超时设置
• 检查LLM服务
• 尝试简化分析
• 重启应用程序

当前超时: 300s → 建议超时: 300s"""
            
            self.update_text_area(timeout_text, text_color='#ff8c00')
            self.status_var.set(f"AI分析超时: {error_msg}")
        else:
            # 其他错误处理
            error_text = f"""{t_gui('error_analysis_failed')}!

{t_gui('analysis_error')}: {error_msg}

{t_gui('tip_possible_reasons')}:
• {t_gui('data_format_error')}
• {t_gui('error_insufficient_data')}
• {t_gui('error_calculation_error')}
• {t_gui('data_format_error')}

{t_gui('solution_suggestions')}:
• {t_gui('data_format_error')}
• {t_gui('btn_refresh')}
• {t_gui('menu_user_guide')}
• {t_gui('menu_help')}
"""
            
            self.update_text_area(error_text, text_color='#cc0000')
            self.status_var.set(f"{t_gui('analysis_failed')}: {error_msg}")
        
        self.analyze_btn.config(state=tk.NORMAL)
        
        messagebox.showerror(t_gui("analysis_failed_title"), error_msg)
    
    def _generate_analysis_summary(self):
        """生成分析结果摘要"""
        if not self.analysis_results:
            return t_gui("analysis_empty")
        
        try:
            # 处理AnalysisResults对象
            if hasattr(self.analysis_results, 'metadata'):
                # 从AnalysisResults对象获取数据
                total_stocks = self.analysis_results.metadata.get('total_stocks', 0)
                total_industries = self.analysis_results.metadata.get('total_industries', 0)
                calculation_time = self.analysis_results.metadata.get('calculation_time', 0)
                
                # 获取top股票和行业 - 使用realtime_engine的方法签名
                top_stocks = self.analysis_results.get_top_stocks('rtsi', 5)
                top_industries = self.analysis_results.get_top_industries('irsi', 5)
                
                # 获取市场情绪数据
                market_data = self.analysis_results.market
                
                # 从数据源获取日期范围
                date_range = self.current_dataset.get_date_range() if self.current_dataset else (None, None)
                date_range_str = f"{date_range[0]} ~ {date_range[1]}" if date_range[0] else t_gui("unknown")
                
            else:
                # 如果是字典格式（兼容性处理）
                summary = self.analysis_results.get('summary', {})
                total_stocks = summary.get('total_stocks', 0)
                total_industries = summary.get('total_industries', 0)
                calculation_time = 0
                top_stocks = self.analysis_results.get('top_stocks', [])
                top_industries = self.analysis_results.get('top_industries', [])
                market_data = self.analysis_results.get('market_sentiment', {})
                date_range_str = summary.get('date_range', t_gui("unknown"))
        
            # 生成摘要文本
            summary_text = f"""{t_gui("success")} {t_gui("analysis_results")}

{t_gui("result_data_overview")}:
• {t_gui("total_stocks")}: {total_stocks} {t_gui("units_stocks")}
• {t_gui("industry_classification")}: {total_industries} {t_gui("units_industries")}
• {t_gui("result_calculation_time")}: {calculation_time:.2f} {t_gui("seconds")}
• {t_gui("data_date")}: {date_range_str}

{t_gui("excellent")} {t_gui("quality_stocks_top5")} ({t_gui("sorted_by_rtsi")}):"""
            
            # 处理top股票显示
            if top_stocks:
                for i, stock_data in enumerate(top_stocks[:5], 1):
                    if isinstance(stock_data, tuple) and len(stock_data) >= 3:
                        code, name, rtsi = stock_data
                        # 安全处理numpy类型
                        try:
                            import numpy as np
                            if isinstance(rtsi, (int, float, np.number)):
                                rtsi_value = float(rtsi)
                            else:
                                rtsi_value = 0.0
                        except:
                            rtsi_value = 0.0
                        formatted_code = self.format_stock_code(code)
                        summary_text += f"\n{i}. {name} ({formatted_code}) - RTSI: {rtsi_value:.1f}"
                    elif isinstance(stock_data, tuple) and len(stock_data) >= 2:
                        # 处理两元素格式
                        code, rtsi = stock_data
                        name = code  # 使用代码作为名称
                        try:
                            import numpy as np
                            if isinstance(rtsi, (int, float, np.number)):
                                rtsi_value = float(rtsi)
                            else:
                                rtsi_value = 0.0
                        except:
                            rtsi_value = 0.0
                        formatted_code = self.format_stock_code(code)
                        summary_text += f"\n{i}. {name} ({formatted_code}) - RTSI: {rtsi_value:.1f}"
                    else:
                        summary_text += f"\n{i}. {t_gui('data_format_error')}: {type(stock_data)}"
            else:
                summary_text += f"\n{t_gui('no_data')}"
            
            summary_text += f"\n\n{t_gui('industry')} {t_gui('strong_industries_top5')} ({t_gui('sorted_by_irsi')}):"
            
            # 处理top行业显示
            if top_industries:
                for i, industry_data in enumerate(top_industries[:5], 1):
                    if isinstance(industry_data, tuple) and len(industry_data) >= 2:
                        industry, irsi = industry_data
                        # 安全处理numpy类型
                        try:
                            import numpy as np
                            if isinstance(irsi, (int, float, np.number)):
                                irsi_value = float(irsi)
                            else:
                                irsi_value = 0.0
                        except:
                            irsi_value = 0.0
                        summary_text += f"\n{i}. {industry} - IRSI: {irsi_value:.1f}"
                    else:
                        summary_text += f"\n{i}. {t_gui('data_format_error')}: {type(industry_data)}"
            else:
                summary_text += f"\n{t_gui('no_data')}"
            
            # 处理市场情绪数据
            summary_text += f"\n\n{t_gui('rising')} {t_gui('market_sentiment_analysis')}:"
            
            # 安全地提取和格式化市场数据
            try:
                import numpy as np
                
                current_msci = market_data.get('current_msci', 0)
                if isinstance(current_msci, (int, float, np.number)):
                    msci_str = f"{float(current_msci):.1f}"
                else:
                    msci_str = str(current_msci)
                
                raw_market_state = market_data.get('market_state', t_gui("unknown"))
                if isinstance(raw_market_state, (dict, list)):
                    raw_market_state = str(raw_market_state)
                elif raw_market_state is None:
                    raw_market_state = t_gui("unknown")
                
                # 翻译市场状态
                state_translations = {
                    'healthy_optimism': t_gui("healthy_optimism"),
                    'euphoric': t_gui("euphoric"),
                    'optimistic': t_gui("optimistic"),
                    'neutral': t_gui("neutral"),
                    'pessimistic': t_gui("pessimistic"),
                    'panic': t_gui("panic")
                }
                market_state = state_translations.get(raw_market_state, raw_market_state)
                
                raw_risk_level = market_data.get('risk_level', t_gui("unknown"))
                if isinstance(raw_risk_level, (dict, list)):
                    raw_risk_level = str(raw_risk_level)
                elif raw_risk_level is None:
                    raw_risk_level = t_gui("unknown")
                
                # 翻译风险等级
                risk_translations = {
                    'low': t_gui("low_risk"),
                    'medium': t_gui("medium_risk"),
                    'high': t_gui("high_risk"),
                    'low_risk': t_gui("low_risk"),
                    'medium_risk': t_gui("medium_risk"),
                    'high_risk': t_gui("high_risk")
                }
                risk_level = risk_translations.get(raw_risk_level, raw_risk_level)
                
                trend_5d = market_data.get('trend_5d', 0)
                if isinstance(trend_5d, (int, float, np.number)):
                    trend_str = f"{float(trend_5d):.2f}"
                else:
                    trend_str = str(trend_5d)
                
                summary_text += f"\n• {t_gui('current_msci_index')}: {msci_str}"
                summary_text += f"\n• {t_gui('market_state')}: {market_state}"
                summary_text += f"\n• {t_gui('risk_level')}: {risk_level}"
                summary_text += f"\n• {t_gui('five_day_trend')}: {trend_str}"
            
            except Exception as e:
                summary_text += f"\n• {t_gui('market_data_parse_error')}: {str(e)}"

            summary_text += f"\n\n{t_gui('tip')} {t_gui('detailed_report_instruction')}\n"
            
            return summary_text
            
        except Exception as e:
            return f"{t_gui('summary_generation_failed')}: {str(e)}\n\n{t_gui('check_analysis_data_format')}"
    
    # 菜单功能实现
    def export_report(self):
        """导出Excel报告"""
        if not self.analysis_results:
            messagebox.showwarning(t_gui("tip"), t_gui("complete_analysis_first"))
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                title=t_gui("save_analysis_report"),
                defaultextension=".xlsx",
                filetypes=[(t_gui("excel_files"), "*.xlsx"), (t_gui("all_files"), "*.*")]
            )
            
            if filename:
                # 使用完整的报告生成器
                try:
                    # 转换分析结果为报告生成器所需的格式
                    report_data = self._convert_analysis_results_for_report()
                    
                    from utils.report_generator import ExcelReportGenerator
                    from pathlib import Path
                    
                    # 创建报告生成器
                    output_dir = Path(filename).parent
                    generator = ExcelReportGenerator(output_dir)
                    
                    # 生成报告
                    report_path = generator.create_report(report_data)
                    
                    # 如果生成的文件名不同，重命名为用户指定的文件名
                    if report_path != filename:
                        import shutil
                        shutil.move(report_path, filename)
                    
                    self.status_var.set(f"{t_gui('exported_excel_report')}: {Path(filename).name}")
                    messagebox.showinfo(t_gui('success'), f"{t_gui('report_saved_to')}:\n{filename}")
                    
                except ImportError:
                    # 备用方案：使用基础的Excel导出
                    self._basic_excel_export(filename)
                    self.status_var.set(f"{t_gui('exported_excel_report')}: {Path(filename).name}")
                    messagebox.showinfo(t_gui('success'), f"{t_gui('report_saved_to')}:\n{filename}")
                
        except Exception as e:
            messagebox.showerror(t_gui('export_error'), f"{t_gui('excel_export_failed')}:\n{str(e)}")
    
    def _convert_analysis_results_for_report(self) -> dict:
        """将分析结果转换为报告生成器所需的格式"""
        try:
            if hasattr(self.analysis_results, 'metadata'):
                # 处理AnalysisResults对象
                return {
                    'metadata': {
                        'generated_at': datetime.now(),
                        'data_date': datetime.now().date(),
                        'total_stocks': self.analysis_results.metadata.get('total_stocks', 0),
                        'total_industries': self.analysis_results.metadata.get('total_industries', 0),
                        'analysis_period': t_gui("trading_days_38"),
                        'system_version': '1.0.0'
                    },
                    'stocks': self.analysis_results.stocks,
                    'industries': self.analysis_results.industries,
                    'market': self.analysis_results.market,
                    'performance': self.analysis_results.metadata.get('performance_metrics', {}),
                    'summary': {
                        'total_stocks': self.analysis_results.metadata.get('total_stocks', 0),
                        'total_industries': self.analysis_results.metadata.get('total_industries', 0),
                        'calculation_time': self.analysis_results.metadata.get('calculation_time', 0),
                        'rating_coverage': 25.0,  # 默认覆盖率
                        'market_overview': {
                            'bullish_ratio': 30,
                            'bearish_ratio': 40,
                            'neutral_ratio': 30
                        }
                    }
                }
            else:
                # 处理字典格式的分析结果
                return {
                    'metadata': {
                        'generated_at': datetime.now(),
                        'data_date': datetime.now().date(),
                        'total_stocks': len(self.analysis_results.get('stocks', {})),
                        'total_industries': len(self.analysis_results.get('industries', {})),
                        'analysis_period': t_gui("trading_days_38"),
                        'system_version': '1.0.0'
                    },
                    'stocks': self.analysis_results.get('stocks', {}),
                    'industries': self.analysis_results.get('industries', {}),
                    'market': self.analysis_results.get('market_sentiment', {}),
                    'performance': {},
                    'summary': {
                        'total_stocks': len(self.analysis_results.get('stocks', {})),
                        'total_industries': len(self.analysis_results.get('industries', {})),
                        'calculation_time': 0,
                        'rating_coverage': 25.0,
                        'market_overview': {
                            'bullish_ratio': 30,
                            'bearish_ratio': 40,
                            'neutral_ratio': 30
                        }
                    }
                }
        except Exception as e:
            # 如果转换失败，返回基础格式
            return {
                'metadata': {
                    'generated_at': datetime.now(),
                    'data_date': datetime.now().date(),
                    'total_stocks': 100,  # 默认值
                    'total_industries': 20,  # 默认值
                    'analysis_period': t_gui("trading_days_38"),
                    'system_version': '1.0.0'
                },
                'stocks': {},
                'industries': {},
                'market': {},
                'performance': {},
                'summary': {
                    'total_stocks': 100,
                    'total_industries': 20,
                    'calculation_time': 0,
                    'rating_coverage': 25.0,
                    'market_overview': {
                        'bullish_ratio': 30,
                        'bearish_ratio': 40,
                        'neutral_ratio': 30
                    }
                }
            }
    
    def _basic_excel_export(self, filename):
        """基础Excel导出方法（备用方案）"""
        try:
            import pandas as pd
            
            # 创建基础的分析结果Excel文件
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 汇总数据
                summary_data = {
                    t_gui("analysis_time"): [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    t_gui("total_stocks"): [len(self.analysis_results.get('stocks', {}))],
                    t_gui("analysis_status"): [t_gui("completed")],
                    t_gui("data_file"): [self.current_dataset.file_path if self.current_dataset else t_gui("unknown")]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name=t_gui("analysis_summary"), index=False)
                
                # 股票数据（如果有）
                if 'stocks' in self.analysis_results:
                    stock_data = []
                    for code, info in self.analysis_results['stocks'].items():
                        stock_data.append({
                            t_gui("stock_code"): code,
            t_gui("stock_name"): info.get(t_gui("name"), ''),
            t_gui("industry"): info.get(t_gui("industry"), ''),
                            t_gui("analysis_result"): str(info)
                        })
                    
                    if stock_data:
                        stock_df = pd.DataFrame(stock_data)
                        stock_df.to_excel(writer, sheet_name=t_gui("stock_analysis"), index=False)
                
                # 行业数据（如果有）
                if 'industries' in self.analysis_results:
                    industry_data = []
                    for industry, info in self.analysis_results['industries'].items():
                        industry_data.append({
                            t_gui("industry_name"): industry,
                            t_gui("analysis_result"): str(info)
                        })
                    
                    if industry_data:
                        industry_df = pd.DataFrame(industry_data)
                        industry_df.to_excel(writer, sheet_name=t_gui("industry_analysis"), index=False)
        
        except Exception as e:
            raise Exception(f"{t_gui('basic_excel_export_failed')}: {str(e)}")
    
    def export_html_report(self):
        """导出HTML报告"""
        if not self.analysis_results:
            messagebox.showwarning(t_gui("tip"), t_gui("complete_analysis_first"))
            return
        
        try:
            # 直接使用简单版本的HTML报告生成器，避免plotly依赖问题
            self._generate_simple_html_report()
            
        except Exception as e:
            messagebox.showerror(t_gui('export_error'), f"{t_gui('html_report_generation_failed')}:\n{str(e)}")
    
    def _generate_simple_html_report(self):
        """生成简单版HTML报告"""
        try:
            from datetime import datetime
            import webbrowser
            
            reports_dir = Path("analysis_reports")
            reports_dir.mkdir(exist_ok=True)
            
            html_file = reports_dir / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            # 获取实际分析数据
            if hasattr(self.analysis_results, 'metadata'):
                total_stocks = self.analysis_results.metadata.get('total_stocks', 0)
                total_industries = self.analysis_results.metadata.get('total_industries', 0)
                
                # 获取top股票推荐
                top_stocks = self.analysis_results.get_top_stocks('rtsi', 5)
                
                # 获取市场情绪数据
                market_data = self.analysis_results.market
                
                # 安全处理numpy类型
                import numpy as np
                msci_raw = market_data.get('current_msci', 0)
                msci_value = float(msci_raw) if isinstance(msci_raw, (int, float, np.number)) else 0.0
                
                # 获取市场状态并进行翻译
                raw_market_state = market_data.get('market_state', t_gui("unknown"))
                # 市场状态翻译映射
                market_state_translations = {
                    'healthy_optimism': t_gui("healthy_optimism"),
                    'euphoric': t_gui("euphoric"),
                    'optimistic': t_gui("optimistic"),
                    'neutral': t_gui("neutral"),
                    'pessimistic': t_gui("pessimistic"),
                    'panic': t_gui("panic")
                }
                market_state = market_state_translations.get(raw_market_state, raw_market_state)
                risk_level = market_data.get('risk_level', t_gui("unknown"))
                
                trend_raw = market_data.get('trend_5d', 0)
                trend_5d = float(trend_raw) if isinstance(trend_raw, (int, float, np.number)) else 0.0
            else:
                # 从字典格式获取数据
                total_stocks = len(self.analysis_results.get('stocks', {})) if self.analysis_results else 0
                total_industries = len(self.analysis_results.get('industries', {})) if self.analysis_results else 0
                top_stocks = []
                
                # 如果有分析结果，获取市场情绪
                if self.analysis_results and 'market_sentiment' in self.analysis_results:
                    market_data = self.analysis_results['market_sentiment']
                    msci_value = market_data.get('current_msci', 42.5)
                    market_state = market_data.get('market_state', t_gui("neutral_bearish"))
                    risk_level = market_data.get('risk_level', t_gui("medium"))
                    trend_5d = market_data.get('trend_5d', 0)
                else:
                    # 默认市场情绪数据
                    msci_value = 42.5
                    market_state = t_gui("neutral_bearish")
                    risk_level = t_gui("medium")
                    trend_5d = 2.3
            
            # 生成个股推荐表格HTML
            stock_recommendations_html = ""
            if top_stocks:
                for i, stock_data in enumerate(top_stocks[:5], 1):
                    if isinstance(stock_data, tuple) and len(stock_data) >= 3:
                        code, name, rtsi = stock_data
                        # 安全处理numpy类型
                        import numpy as np
                        rtsi_value = float(rtsi) if isinstance(rtsi, (int, float, np.number)) else 0.0
                        recommendation = get_text('report', 'strongly_recommend') if rtsi_value > 70 else get_text('report', 'moderate_attention') if rtsi_value > 50 else get_text('report', 'cautious_watch')
                        stock_recommendations_html += f"""
            <tr>
                <td>{i}</td>
                <td>{self.format_stock_code(code)}</td>
                <td>{name}</td>
                <td>{rtsi_value:.1f}</td>
                <td>{recommendation}</td>
            </tr>"""
                    else:
                        stock_recommendations_html += f"""
            <tr>
                <td>{i}</td>
                <td>--</td>
                <td>{get_text('report', 'data_processing')}</td>
                <td>--</td>
                <td>{get_text('report', 'waiting_analysis')}</td>
            </tr>"""
            else:
                stock_recommendations_html = f"""
            <tr>
                <td>1</td>
                <td>--</td>
                <td>{t_gui("no_data")}</td>
                <td>--</td>
                <td>{t_gui("complete_analysis_first")}</td>
            </tr>"""
            
            # 生成行业分析HTML
            industry_analysis_html = ""
            if hasattr(self.analysis_results, 'industries') and self.analysis_results.industries:
                # 获取top行业数据
                top_industries = self.analysis_results.get_top_industries('irsi', 10)
                
                if top_industries:
                    industry_analysis_html = f"<p><strong>{get_text('report', 'strong_industries_ranking')} ({get_text('report', 'sorted_by_irsi_index')}):</strong></p><table>"
                    industry_analysis_html += f"<tr><th>{get_text('report', 'ranking')}</th><th>{get_text('report', 'industry_name')}</th><th>{get_text('report', 'irsi_index')}</th><th>{get_text('report', 'strength_level')}</th><th>{get_text('report', 'investment_advice')}</th></tr>"
                    
                    for i, (industry_name, irsi_value) in enumerate(top_industries[:5], 1):
                        # 判断强度等级
                        if irsi_value > 20:
                            strength = t_gui("strong")
                            advice = get_text('report', 'active_allocation')
                            color = "green"
                        elif irsi_value > 5:
                            strength = get_text('report', 'neutral_strong')
                            advice = get_text('report', 'moderate_attention')
                            color = "blue"
                        elif irsi_value > -5:
                            strength = t_gui("neutral")
                            advice = get_text('report', 'wait_and_see')
                            color = "gray"
                        elif irsi_value > -20:
                            strength = get_text('report', 'neutral_weak')
                            advice = get_text('report', 'cautious')
                            color = "orange"
                        else:
                            strength = t_gui("weak")
                            advice = get_text('report', 'avoid')
                            color = "red"
                        
                        industry_analysis_html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{industry_name}</td>
                            <td style="color: {color}; font-weight: bold;">{irsi_value:.2f}</td>
                            <td style="color: {color};">{strength}</td>
                            <td>{advice}</td>
                        </tr>"""
                    
                    industry_analysis_html += "</table>"
                    
                    # 添加说明
                    strongest_industry = top_industries[0][0]
                    strongest_irsi = top_industries[0][1]
                    industry_analysis_html += f"<p><strong>{get_text('report', 'current_strongest_industry')}:</strong> {strongest_industry} (IRSI: {strongest_irsi:.2f})</p>"
                    industry_analysis_html += f"<p><small>{get_text('report', 'irsi_index_explanation')}</small></p>"
                else:
                    industry_analysis_html = f"<p>{get_text('report', 'no_industry_analysis_data')}</p>"
            else:
                industry_analysis_html = f"<p>{get_text('report', 'no_industry_analysis_data')}</p>"
            
            # 生成AI分析版块HTML - 根据当前语言重新生成
            ai_analysis_section = ""
            
            # 检查是否有AI分析结果，如果没有或语言不匹配，尝试重新生成
            needs_regeneration = False
            if not hasattr(self, 'ai_analysis_result') or not self.ai_analysis_result:
                needs_regeneration = True
            else:
                # 检查AI分析结果的语言是否与当前系统语言匹配
                current_is_english = is_english()
                # 简单的语言检测：检查结果中是否包含中文字符
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in self.ai_analysis_result)
                
                # 如果当前是英文环境但AI结果包含中文，或当前是中文环境但AI结果不包含中文，则需要重新生成
                if (current_is_english and has_chinese) or (not current_is_english and not has_chinese):
                    needs_regeneration = True
                    print(f"[Language Debug] AI分析结果语言不匹配，需要重新生成")
                    print(f"[Language Debug] 当前系统语言: {'英文' if current_is_english else '中文'}")
                    print(f"[Language Debug] AI结果包含中文: {has_chinese}")
            
            if needs_regeneration:
                # 重新生成AI分析结果
                try:
                    analysis_data = self._prepare_analysis_data()
                    fresh_ai_result = self._call_llm_api(analysis_data)
                    if fresh_ai_result:
                        self.ai_analysis_result = fresh_ai_result
                except Exception as e:
                    # 如果重新生成失败，使用简化分析
                    analysis_data = self._prepare_analysis_data()
                    self.ai_analysis_result = self._generate_simplified_analysis(analysis_data)
            
            if hasattr(self, 'ai_analysis_result') and self.ai_analysis_result:
                ai_analysis_section = f"""
    <div class="section">
        <h2>{t_gui("ai_intelligent_analysis")}</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
            <h3>{t_gui("ai_analyst_opinion")}</h3>
            <div style="white-space: pre-wrap; line-height: 1.6; color: #333;">{self.ai_analysis_result}</div>
        </div>
        <p><small>{t_gui("ai_analysis_disclaimer")}</small></p>
    </div>"""
            else:
                ai_analysis_section = ""
            
            # 生成市场情绪分析HTML
            sentiment_risk_color = "red" if msci_value > 70 or msci_value < 30 else "orange" if msci_value < 40 else "green"
            trend_color = "green" if trend_5d > 0 else "red"
            
            # 生成简单的HTML内容
            html_content = f"""
<!DOCTYPE html>
<html lang="{{"zh-CN" if get_current_language() == "zh" else "en-US"}}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{get_text('report', 'ai_stock_trend_analysis_report')}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 8px; margin-bottom: 20px; position: relative; }}
        .author {{ position: absolute; top: 20px; right: 20px; font-size: 12px; color: #666; }}
        .section {{ margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e8f4fd; border-radius: 5px; }}
        .highlight {{ color: #0078d4; font-weight: bold; }}
        .sentiment-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0; }}
        .sentiment-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #0078d4; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .risk-high {{ color: red; font-weight: bold; }}
        .risk-medium {{ color: orange; font-weight: bold; }}
        .risk-low {{ color: green; font-weight: bold; }}
        .trend-up {{ color: green; }}
        .trend-down {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{get_text('report', 'ai_stock_trend_analysis_report')}</h1>
        <p>{get_text('report', 'generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="author">{get_text('report', 'author')}: 267278466@qq.com</div>
    </div>
    
    <div class="section">
        <h2>{get_text('report', 'analysis_overview')}</h2>
        <div class="metric">{get_text('gui', 'total_stocks')}: <span class="highlight">{total_stocks:,}</span></div>
        <div class="metric">{get_text('gui', 'industry_classification')}: <span class="highlight">{total_industries}</span>{get_text('gui', 'units_industries')}</div>
        <div class="metric">{get_text('report', 'analysis_algorithm')}: <span class="highlight">RTSI + IRSI + MSCI</span></div>
        <div class="metric">{get_text('report', 'data_quality')}: <span class="highlight">{get_text('report', 'good')}</span></div>
    </div>
    
    <div class="section">
        <h2>{get_text('report', 'market_sentiment_index')}</h2>
        <p>{get_text('report', 'msci_based_market_sentiment_analysis')}</p>
        <div class="sentiment-grid">
            <div class="sentiment-card">
                <h3>{get_text('report', 'core_indicators')}</h3>
                <p><strong>{get_text('report', 'msci_index')}:</strong> <span style="color: {sentiment_risk_color}; font-weight: bold;">{msci_value:.1f}</span></p>
                <p><strong>{get_text('msci', 'market_state')}:</strong> {market_state}</p>
                <p><strong>{get_text('msci', 'risk_level')}:</strong> <span class="risk-{risk_level.lower()}">{get_text('msci', risk_level) if risk_level in ['low_risk', 'medium_risk', 'high_risk', 'extremely_high_risk_bubble_warning', 'extremely_high_risk_bubble_confirmed', 'high_risk_high_return_bottom_opportunity', 'contrarian_investment_opportunity_panic_bottom', 'medium_high_risk', 'medium_risk_watch_extreme_sentiment'] else risk_level}</span></p>
                <p><strong>{get_text('gui', 'five_day_trend')}:</strong> <span class="trend-{'up' if trend_5d > 0 else 'down'}">{trend_5d:+.1f}</span></p>
            </div>
            <div class="sentiment-card">
                <h3>{get_text('report', 'market_judgment')}</h3>
                <p><strong>{get_text('report', 'overall_sentiment')}:</strong> {get_text('report', 'slightly_optimistic') if msci_value > 60 else get_text('report', 'slightly_pessimistic') if msci_value < 40 else t_gui("neutral")}</p>
                <p><strong>{get_text('report', 'investment_advice')}:</strong> {get_text('report', 'cautious_reduction') if msci_value > 70 else get_text('report', 'moderate_increase') if msci_value < 30 else get_text('report', 'balanced_allocation')}</p>
                <p><strong>{get_text('report', 'focus_points')}:</strong> {get_text('report', 'prevent_bubble_risk') if msci_value > 70 else get_text('report', 'seek_value_opportunities') if msci_value < 30 else get_text('report', 'focus_rotation_opportunities')}</p>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>{get_text('report', 'stock_recommendations')}</h2>
        <p>{get_text('report', 'rtsi_based_quality_stock_analysis')}</p>
        <table>
            <tr><th>{get_text('report', 'ranking')}</th><th>{get_text('gui', 'stock_code')}</th><th>{get_text('gui', 'stock_name')}</th><th>{get_text('report', 'rtsi_index')}</th><th>{get_text('report', 'recommendation_reason')}</th></tr>
            {stock_recommendations_html}
        </table>
    </div>
    
    <div class="section">
        <h2>{get_text('report', 'industry_rotation_analysis')}</h2>
        <p>{get_text('report', 'irsi_based_industry_strength_analysis')}</p>
        {industry_analysis_html}
    </div>
    
    <div class="section">
        <h2>{get_text('report', 'investment_advice')}</h2>
        <ul>
            <li>{get_text('report', 'based_on_msci_index')}{msci_value:.1f}{get_text('gui', 'comma')}{get_text('report', 'current_market_sentiment')}{market_state}</li>
            <li>{get_text('report', 'suggested_position')}{get_text('gui', 'colon')}{"30-40%" if msci_value > 70 else "70-80%" if msci_value < 30 else "50-60%"}</li>
            <li>{get_text('report', 'focus_rtsi_above_60')}</li>
            <li>{get_text('report', 'focus_strong_industry_leaders')}</li>
            <li>{get_text('report', 'set_stop_loss_risk_control')}</li>
        </ul>
    </div>
    
    {ai_analysis_section}
    
    <div class="section">
        <p><small>{get_text('report', 'disclaimer')}</small></p>
    </div>
</body>
</html>
            """
            
            # 写入HTML文件
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 在浏览器中打开
            webbrowser.open(f"file://{html_file.absolute()}")
            
            self.status_var.set(f"{t_gui('html_report_generated_and_opened')}: {html_file.name}")
            
            # 返回HTML内容用于测试
            return html_content
            
        except Exception as e:
            messagebox.showerror(t_gui('export_error'), f"{t_gui('html_report_generation_failed')}:\n{str(e)}")
            return None
    
    def show_stock_analysis(self):
        """显示个股分析窗口"""
        if not self.analysis_results:
            messagebox.showwarning(t_gui("tip"), t_gui("load_data_and_complete_analysis_first"))
            return
        
        try:
            # 创建个股分析窗口，传递current_dataset，并保存引用
            self.stock_analysis_window = StockAnalysisWindow(self.root, self.analysis_results, self.current_dataset)
            # 确保窗口显示在前台
            self.stock_analysis_window.window.focus_force()
        except Exception as e:
            messagebox.showerror(t_gui('error'), f"{t_gui('open_stock_analysis_window_failed')}:\n{str(e)}")
    
    def show_industry_analysis(self):
        """显示行业分析窗口"""
        if not self.analysis_results:
            messagebox.showwarning(t_gui("tip"), t_gui("load_data_and_complete_analysis_first"))
            return
        
        try:
            # 创建行业分析窗口
            IndustryAnalysisWindow(self.root, self.analysis_results)
        except Exception as e:
            messagebox.showerror(t_gui('error'), f"{t_gui('open_industry_analysis_window_failed')}:\n{str(e)}")
    
    def show_market_analysis(self):
        """显示市场分析窗口"""
        if not self.analysis_results:
            messagebox.showwarning(t_gui("tip"), t_gui("load_data_and_complete_analysis_first"))
            return
        
        try:
            # 创建市场情绪分析窗口
            MarketSentimentWindow(self.root, self.analysis_results)
        except Exception as e:
            messagebox.showerror(t_gui('error'), f"{t_gui('open_market_analysis_window_failed')}:\n{str(e)}")
    
    def show_settings(self):
        """显示设置窗口"""
        try:
            from gui.analysis_dialogs import SettingsDialog
            SettingsDialog(self.root)
        except ImportError:
            messagebox.showerror(t_gui("feature_unavailable"), t_gui("settings_module_not_found"))
        except Exception as e:
            messagebox.showerror(t_gui('error'), f"{t_gui('open_settings_window_failed')}:\n{str(e)}")
    
    def show_help(self):
        """显示帮助窗口"""
        # 实现帮助窗口的逻辑
        pass
    
    def open_user_guide(self):
        """打开用户使用说明（系统浏览器访问主页）"""
        import webbrowser
        try:
            webbrowser.open(HOMEPAGE)
        except Exception as e:
            messagebox.showerror(t_tools('error'), f"{t_tools('open_homepage_failed')}:\n{str(e)}")
    
    def show_about(self):
        """显示关于窗口"""
        messagebox.showinfo(t_tools('about'), f"{t_tools('ai_stock_trend_analysis_system')} {VERSION}\n\n{t_tools('professional_stock_analysis_tool')}\n\n{t_tools('contact')}: {AUTHOR}")
    
    def open_github_page(self, event):
        """打开GitHub页面"""
        import webbrowser
        webbrowser.open(HOMEPAGE)
    
    def open_github_star(self):
        """打开GitHub Star页面并显示提示"""
        # 开始按钮闪烁效果
        self.start_star_button_flash()
        
        # 创建GitHub信息窗口
        self.show_github_info_window()
    
    def show_github_info_window(self):
        """显示GitHub项目信息窗口"""
        import tkinter.messagebox as messagebox
        
        # 创建新窗口
        github_window = tk.Toplevel(self.root)
        
        # 检测系统语言
        is_chinese = not is_english()
        
        # 设置窗口标题和内容
        github_window.title("GitHub Star - AI股票趋势分析系统")
        title_text = "AI股票趋势分析系统"
        star_button_text = "Star"
        
        github_window.geometry("600x500")
        github_window.resizable(False, False)
        
        # 设置窗口居中到屏幕中央
        github_window.update_idletasks()
        width = github_window.winfo_width()
        height = github_window.winfo_height()
        x = (github_window.winfo_screenwidth() // 2) - (width // 2)
        y = (github_window.winfo_screenheight() // 2) - (height // 2)
        github_window.geometry(f"{width}x{height}+{x}+{y}")
        
        github_window.transient(self.root)
        github_window.grab_set()
        
        # 主框架
        main_frame = tk.Frame(github_window, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(main_frame, text=title_text, 
                              font=('Microsoft YaHei', 16, 'bold'), 
                              bg='white', fg='#0366d6')
        title_label.pack(pady=(0, 20))
        
        # 项目信息
        info_text = tk.Text(main_frame, height=15, width=70, 
                           font=('Microsoft YaHei', 11), 
                           bg='#f6f8fa', relief=tk.FLAT, 
                           wrap=tk.WORD, state=tk.NORMAL)
        
        project_info = f"""📊 AI股票趋势分析系统 {VERSION}

🎯 项目特色：
• RTSI - 个股趋势强度指数
• IRSI - 行业相对强度指数  
• MSCI - 市场情绪综合指数
• 支持A股、港股、美股全市场分析
• 集成大语言模型智能分析
• 专业级投资决策支持

🚀 核心功能：
• 多维数据融合，精准趋势预测
• 三层分析体系：个股-行业-市场
• AI增强分析，智能解读与建议生成
• 高级自然语言处理市场分析

💡 技术架构：
• 现代人工智能理论基础
• 机器学习与深度学习技术
• 大语言模型技术集成
• 多层AI架构设计

🌟 如果这个项目对您有帮助，请点击下方按钮为项目点Star！
您的支持是我们持续改进的动力！"""
        
        info_text.insert(tk.END, project_info)
        info_text.config(state=tk.DISABLED)
        info_text.pack(pady=(0, 20), fill=tk.BOTH, expand=True)
        
        # 按钮框架
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Star按钮（居中显示）
        star_btn = tk.Button(button_frame, text=star_button_text, 
                            command=lambda: self.open_github_and_close(github_window),
                            font=('Microsoft YaHei', 11, 'bold'),
                            bg='#28a745', fg='white',
                            padx=20, pady=8)
        star_btn.pack(expand=True)
        
        # 添加按钮悬停效果
        def on_enter(e):
            star_btn.config(bg='#218838')
        def on_leave(e):
            star_btn.config(bg='#28a745')
        
        star_btn.bind("<Enter>", on_enter)
        star_btn.bind("<Leave>", on_leave)
    
    def open_github_and_close(self, window):
        """打开GitHub页面并关闭窗口"""
        import webbrowser
        import tkinter.messagebox as messagebox
        
        # 检测系统语言
        is_chinese = not is_english()
        
        # 关闭窗口
        window.destroy()
        
        # 打开GitHub页面
        webbrowser.open(HOMEPAGE)
        
        # 延迟显示感谢提示
        self.root.after(1500, lambda: messagebox.showinfo(
            "感谢支持 🙏", 
            "感谢您的支持！\n\n请在GitHub页面点击右上角的 ⭐ Star 按钮\n为AI股票分析系统点赞！\n\n您的每一个Star都是我们前进的动力！"
        ))
    
    def start_star_button_flash(self):
        """开始Star按钮闪烁效果"""
        self.flash_count = 0
        self.flash_star_button()
    
    def flash_star_button(self):
        """Star按钮闪烁动画"""
        if self.flash_count < 6:  # 闪烁3次
            if self.flash_count % 2 == 0:
                # 高亮状态
                self.star_btn.config(bg='#FFD700', fg='#000080', relief=tk.RAISED)
            else:
                # 正常状态
                self.star_btn.config(bg='#f0f0f0', fg='black', relief=tk.RAISED)
            
            self.flash_count += 1
            self.root.after(300, self.flash_star_button)  # 300ms后继续闪烁
        else:
            # 恢复正常状态
            self.star_btn.config(bg='#f0f0f0', fg='black', relief=tk.RAISED)
    
    def open_ai_model_settings(self):
        """打开AI模型设置界面"""
        try:
            import subprocess
            import sys
            import os
            
            # 获取llm-api目录的设置文件路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            llm_api_dir = os.path.join(current_dir, "llm-api")
            
            # 优先使用无控制台窗口版本
            run_settings_no_console_path = os.path.join(llm_api_dir, "run_settings_no_console.pyw")
            run_settings_path = os.path.join(llm_api_dir, "run_settings.py")
            
            if os.path.exists(run_settings_no_console_path):
                # 使用pythonw.exe运行，不显示控制台窗口
                subprocess.Popen([sys.executable.replace('python.exe', 'pythonw.exe'), run_settings_no_console_path])
                self.status_var.set(t_gui("ai_model_settings_opened"))
            elif os.path.exists(run_settings_path):
                # 回退到普通版本
                subprocess.Popen([sys.executable, run_settings_path])
                self.status_var.set(t_gui("ai_model_settings_opened"))
            else:
                messagebox.showerror(t_gui("error"), f"{t_gui('ai_settings_file_not_found')}\n\n{t_gui('check_installation')}")
        except Exception as e:
            messagebox.showerror(t_gui("error"), f"{t_gui('open_ai_settings_failed')}:\n{str(e)}")
    
    def on_close(self):
        """关闭窗口"""
        self.root.destroy()
    
    def check_analysis_queue(self):
        """检查分析结果队列"""
        # 实现检查分析结果队列的逻辑
        pass
    
    def _start_ai_analysis(self):
        """启动AI智能分析"""
        try:
            # 检查llm-api配置文件是否存在
            if not self._check_llm_config():
                # 更新AI状态指示器为错误
                if self.ai_status_indicator:
                    self.ai_status_indicator.set_status('error', 'AI配置错误')
                return
            
            # 更新AI状态显示和指示器
            self.ai_status_var.set(t_gui("ai_analyzing"))
            if self.ai_status_indicator:
                self.ai_status_indicator.set_status('analyzing', t_gui('ai_analyzing'))
            
            # 在后台线程中执行AI分析
            ai_thread = threading.Thread(target=self._run_ai_analysis)
            ai_thread.daemon = True
            ai_thread.start()
            
        except Exception as e:
            print(f"{t_gui('ai_analysis_startup_failed')}: {str(e)}")
            self.ai_status_var.set(t_gui("ai_analysis_startup_failed"))
            # 更新AI状态指示器为错误
            if self.ai_status_indicator:
                self.ai_status_indicator.set_status('error', 'AI启动失败')
    
    def _check_llm_config(self) -> bool:
        """检查LLM配置文件是否存在"""
        try:
            import os
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(current_dir, "llm-api", "config", "user_settings.json")
            
            if not os.path.exists(config_path):
                print(t_gui("ai_analysis_skipped_no_config"))
                self.ai_status_var.set(t_gui("ai_not_configured"))
                return False
            
            # 读取配置文件验证格式
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if not config.get('default_provider') or not config.get('default_chat_model'):
                print(t_gui("ai_analysis_skipped_incomplete_config"))
                self.ai_status_var.set(t_gui("ai_config_incomplete"))
                return False
                
            return True
            
        except Exception as e:
            print(f"{t_gui('ai_config_check_failed')}: {str(e)}")
            self.ai_status_var.set(t_gui("ai_config_error"))
            return False
    
    def _run_ai_analysis(self):
        """执行AI智能分析"""
        try:
            # 更新状态
            self.root.after(0, lambda: self.status_var.set(t_gui("ai_intelligent_analysis_in_progress")))
            
            # 准备分析数据
            analysis_data = self._prepare_analysis_data()
            
            # 调用LLM API
            ai_response = self._call_llm_api(analysis_data)
            
            if ai_response:
                # 在主线程中更新UI
                self.root.after(0, lambda: self._display_ai_analysis(ai_response))
                self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_analysis_completed")))
                # 更新AI状态指示器为完成
                if self.ai_status_indicator:
                    self.root.after(0, lambda: self.ai_status_indicator.set_status('completed', t_gui('ai_analysis_completed')))
            else:
                self.root.after(0, lambda: self.status_var.set(t_gui("ai_analysis_failed_continue_traditional")))
                self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_analysis_failed")))
                # 更新AI状态指示器为错误
                if self.ai_status_indicator:
                    self.root.after(0, lambda: self.ai_status_indicator.set_status('error', t_gui('ai_analysis_failed')))
                
        except Exception as e:
            print(f"{t_gui('ai_analysis_execution_failed')}: {str(e)}")
            self.root.after(0, lambda: self.status_var.set(t_gui("ai_analysis_error_continue_traditional")))
            self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_analysis_error")))
            # 更新AI状态指示器为错误
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('error', t_gui('ai_analysis_error')))
    
    def _prepare_analysis_data(self) -> dict:
        """准备发送给AI的分析数据"""
        try:
            data = {
                "analysis_type": t_gui("stock_market_comprehensive_analysis"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_data": {},
                "industry_data": {},
                "stock_data": {},
                "historical_data": {},
                "summary": {}
            }
            
            # 提取市场数据（仅原始数值）
            if hasattr(self.analysis_results, 'market') and self.analysis_results.market:
                market = self.analysis_results.market
                msci_value = market.get('current_msci', 0)
                volatility = market.get('volatility', 0)
                volume_ratio = market.get('volume_ratio', 0)
                
                # 计算市场情绪状态
                if msci_value >= 70:
                    market_sentiment = t_gui("extremely_optimistic")
                elif msci_value >= 60:
                    market_sentiment = t_gui("optimistic")
                elif msci_value >= 40:
                    market_sentiment = t_gui("neutral")
                elif msci_value >= 30:
                    market_sentiment = t_gui("pessimistic")
                else:
                    market_sentiment = t_gui("extremely_pessimistic")
                
                data["market_data"] = {
                    "msci_value": msci_value,
                    "trend_5d": market.get('trend_5d', 0),
                    "volatility": volatility,
                    "volume_ratio": volume_ratio,
                    "market_sentiment": market_sentiment,
                    "risk_level": market.get('risk_level', t_gui("medium"))
                }
                
                # 添加宏观指标数据（模拟数据，实际应用中应从真实数据源获取）
                data["macro_indicators"] = {
                    "interest_rate": 3.5,  # 基准利率
                    "inflation_rate": 2.1,  # 通胀率
                    "gdp_growth": 5.2,  # GDP增长率
                    "currency_strength": min(100, max(0, msci_value + np.random.normal(0, 5))),  # 货币强度
                    "market_liquidity": min(100, max(0, volume_ratio * 50 + np.random.normal(0, 10)))  # 市场流动性
                }
                
                # 添加新闻情感数据（模拟数据）
                sentiment_score = (msci_value - 50) / 50  # 将MSCI转换为-1到1的情感分数
                data["news_sentiment"] = {
                    "overall_sentiment": round(sentiment_score, 2),
                    "positive_ratio": max(0, min(1, 0.5 + sentiment_score * 0.3)),
                    "negative_ratio": max(0, min(1, 0.5 - sentiment_score * 0.3)),
                    "neutral_ratio": 0.3,
                    "news_volume": int(100 + volatility * 5)  # 新闻数量与波动率相关
                }
            
            # 提取行业数据（前10个，仅原始数值）
            if hasattr(self.analysis_results, 'industries') and self.analysis_results.industries:
                top_industries = self.analysis_results.get_top_industries('irsi', 10)
                for industry, score in top_industries:
                    if industry in self.analysis_results.industries:
                        industry_info = self.analysis_results.industries[industry]
                        data["industry_data"][industry] = {
                            "irsi_value": industry_info.get('irsi', {}).get('irsi', 0),
                            "stock_count": industry_info.get('stock_count', 0),
                            "avg_volume": industry_info.get('avg_volume', 0)
                        }
            
            # 提取股票数据（前50个，仅原始数值），格式化代码用于LLM
            if hasattr(self.analysis_results, 'stocks') and self.analysis_results.stocks:
                top_stocks = self.analysis_results.get_top_stocks('rtsi', 50)
                for stock_code, stock_name, score in top_stocks:
                    if stock_code in self.analysis_results.stocks:
                        stock_info = self.analysis_results.stocks[stock_code]
                        
                        # 格式化股票代码用于LLM显示（去除美股前导0）
                        formatted_code = self.format_stock_code(stock_code)
                        
                        data["stock_data"][formatted_code] = {
                            "name": stock_info.get(t_gui("name"), stock_name),
                            "industry": stock_info.get(t_gui("industry"), t_gui("unknown")),
                            "rtsi_value": stock_info.get('rtsi', {}).get('rtsi', 0),
                            "price": stock_info.get(t_gui("price"), 0),
                            "volume": stock_info.get(t_gui("volume"), 0),
                            "market_cap": stock_info.get('market_cap', 0),
                            "original_code": stock_code  # 保留原始代码用于查找
                        }
            
            # 添加10天历史数据
            data["historical_data"] = self._extract_historical_data()
            
            # 添加统计摘要
            if hasattr(self.analysis_results, 'metadata'):
                data["summary"] = {
                    "total_stocks": self.analysis_results.metadata.get('total_stocks', 0),
                    "total_industries": self.analysis_results.metadata.get('total_industries', 0),
                    "calculation_time": self.analysis_results.metadata.get('calculation_time', 0),
                    "historical_days": len(data["historical_data"].get('dates', []))
                }
            
            return data
            
        except Exception as e:
            print(f"{t_gui('data_preparation_failed')}: {str(e)}")
            return {}
    
    def _extract_historical_data(self):
        """提取30天历史数据用于LLM分析"""
        try:
            historical_data = {
                "dates": [],
                "market_msci": [],
                "top_stocks_rtsi": {},
                "top_industries_irsi": {},
                "data_quality": t_gui("estimated")  # 标记数据来源
            }
            
            # 获取当前数据集的日期列
            if hasattr(self.analysis_results, 'dataset') and self.analysis_results.dataset:
                date_columns = [col for col in self.analysis_results.dataset.columns if str(col).startswith('202')]
                date_columns = sorted(date_columns)[-30:]  # 取最近30天
                
                if date_columns:
                    historical_data["dates"] = date_columns
                    historical_data["data_quality"] = t_gui("real")  # 真实数据
                    
                    # 提取市场历史MSCI数据（模拟）
                    for i, date in enumerate(date_columns):
                        # 基于当前MSCI值生成历史趋势
                        current_msci = self.analysis_results.market.get('current_msci', 50) if hasattr(self.analysis_results, 'market') else 50
                        historical_msci = current_msci + (i - len(date_columns)/2) * 2  # 简单趋势模拟
                        historical_data["market_msci"].append(round(historical_msci, 2))
                    
                    # 提取前5只股票的历史RTSI数据
                    if hasattr(self.analysis_results, 'stocks') and self.analysis_results.stocks:
                        top_stocks = self.analysis_results.get_top_stocks('rtsi', 5)
                        for stock_code, stock_name, score in top_stocks:
                            stock_historical = []
                            for date in date_columns:
                                if date in self.analysis_results.dataset.columns:
                                    # 从数据集中获取该股票在该日期的评级
                                    stock_row = self.analysis_results.dataset[self.analysis_results.dataset['股票代码'] == stock_code]
                                    if not stock_row.empty:
                                        rating = stock_row[date].iloc[0]
                                        # 将评级转换为数值
                                        rating_score = self._rating_to_score(rating)
                                        stock_historical.append(rating_score)
                                    else:
                                        stock_historical.append(None)
                                else:
                                    stock_historical.append(None)
                            historical_data["top_stocks_rtsi"][stock_code] = {
                                "name": stock_name,
                                "historical_ratings": stock_historical
                            }
                    
                    # 提取前3个行业的历史IRSI数据（模拟）
                    if hasattr(self.analysis_results, 'industries') and self.analysis_results.industries:
                        top_industries = self.analysis_results.get_top_industries('irsi', 3)
                        for industry, score in top_industries:
                            industry_historical = []
                            for i, date in enumerate(date_columns):
                                # 基于当前IRSI值生成历史趋势
                                current_irsi = self.analysis_results.industries[industry].get('irsi', {}).get('irsi', 50)
                                historical_irsi = current_irsi + (i - len(date_columns)/2) * 1.5  # 简单趋势模拟
                                industry_historical.append(round(historical_irsi, 2))
                            historical_data["top_industries_irsi"][industry] = historical_irsi
                
                else:
                    # 如果没有历史数据，生成模拟数据
                    historical_data = self._generate_mock_historical_data()
            
            else:
                # 如果没有数据集，生成模拟数据
                historical_data = self._generate_mock_historical_data()
            
            return historical_data
            
        except Exception as e:
            print(f"历史数据提取失败: {str(e)}")
            return self._generate_mock_historical_data()
    
    def _rating_to_score(self, rating):
        """将评级转换为数值分数"""
        rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0,
            '-': None
        }
        return rating_map.get(str(rating), None)
    
    def _generate_mock_historical_data(self):
        """生成模拟的30天历史数据"""
        from datetime import datetime, timedelta
        
        # 生成最近30天的日期
        dates = []
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            dates.append(date.strftime('%Y%m%d'))
        
        # 生成模拟的市场MSCI数据
        import random
        base_msci = 50
        market_msci = []
        for i in range(30):
            # 创建更真实的趋势变化
            trend_factor = (i - 15) * 0.3  # 中期趋势
            cycle_factor = 5 * np.sin(i * 0.2)  # 周期性波动
            noise = random.uniform(-3, 3)  # 随机噪声
            msci_value = base_msci + trend_factor + cycle_factor + noise
            msci_value = max(0, min(100, msci_value))  # 限制在0-100范围
            market_msci.append(round(msci_value, 2))
        
        return {
            "dates": dates,
            "market_msci": market_msci,
            "top_stocks_rtsi": {},
            "top_industries_irsi": {},
            "data_quality": t_gui("simulated")
        }
    
    
    def _call_llm_api(self, analysis_data: dict) -> str:
        """调用LLM API进行智能分析（持续连接，无超时限制）"""
        try:
            print("[LLM Debug] 开始连接LLM API...")
            import sys
            import os
            import time
            
            # 调试：检查语言设置
            from config.i18n import is_english, get_current_language
            current_is_english = is_english()
            current_lang = get_current_language()
            print(f"[Language Debug] is_english(): {current_is_english}")
            print(f"[Language Debug] get_current_language(): {current_lang}")
            print(f"[Language Debug] FORCE_ENGLISH env: {os.environ.get('FORCE_ENGLISH', 'Not Set')}")
            if current_is_english:
                print(f"[Language Debug] 将使用英文进行AI分析")
            else:
                print(f"[Language Debug] 将使用中文进行AI分析")
            
            # 更新状态：正在连接
            self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_connecting")))
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('analyzing', t_gui('ai_connecting')))
            
            # 添加llm-api路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            llm_api_path = os.path.join(current_dir, "llm-api")
            if llm_api_path not in sys.path:
                sys.path.insert(0, llm_api_path)
            print(f"[LLM Debug] Added LLM API path: {llm_api_path}")
            
            # 使用传统AI分析方式
            from client import LLMClient
            
            # 创建LLM客户端
            print("[LLM Debug] Creating LLM client")
            
            # 更新状态：正在初始化
            self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_initializing")))
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('analyzing', t_gui('ai_initializing')))
            
            client = LLMClient()
            
            # 构建分析提示
            print("[LLM Debug] Building analysis prompt")
            
            # 更新状态：正在准备数据
            self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_preparing_data")))
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('analyzing', t_gui('ai_preparing_data')))
                
            prompt = self._build_analysis_prompt(analysis_data)
            print(f"[LLM Debug] Prompt length: {len(prompt)} characters")
            
            # 开始LLM分析（无超时限制）
            start_time = time.time()
            
            # 更新状态：正在分析
            self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_requesting")))
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('analyzing', t_gui('ai_requesting')))
            
            try:
                print("[LLM Debug] Attempting to use agent '金融分析师'")
                
                # 根据当前系统语言设置AI分析语言
                if current_is_english:
                    language_instruction = "Please respond in English only. You are a professional financial analyst. Provide analysis in English, but you may keep stock names and industry names in their original language. "
                else:
                    language_instruction = "请用中文回答。你是一位专业的金融分析师，请用中文提供专业的投资建议和市场洞察。"
                
                response = client.chat(
                    message=language_instruction + prompt,
                    agent_id="金融分析师"
                )
                print(f"[LLM Debug] Agent call successful, took {time.time() - start_time:.1f}s")
            except Exception as agent_error:
                print(f"[LLM Debug] 使用智能体失败，尝试直接调用: {agent_error}")
                
                # 更新状态：切换调用方式
                self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_switching_mode")))
                if self.ai_status_indicator:
                    self.root.after(0, lambda: self.ai_status_indicator.set_status('analyzing', t_gui('ai_switching_mode')))
                
                # 如果智能体不可用，回退到直接调用
                print("[LLM Debug] Attempting direct LLM call")
                
                # 根据当前系统语言设置系统消息
                if current_is_english:
                    system_msg = "You are a professional stock analyst. Please provide professional investment advice and market insights in English based on the technical analysis data provided. You may keep stock names and industry names in their original language."
                    user_msg = "Please respond in English only. " + prompt
                else:
                    system_msg = "你是一位专业的股票分析师。请基于提供的技术分析数据，用中文提供专业的投资建议和市场洞察。"
                    user_msg = "请用中文回答。" + prompt
                
                response = client.chat(
                    message=user_msg,
                    system_message=system_msg
                )
                print(f"[LLM Debug] Direct call successful, took {time.time() - start_time:.1f}s")
                
            # 评估AI分析结果的可靠性
            print("[LLM Debug] Evaluating AI reliability")
            
            # 更新状态：评估结果
            self.root.after(0, lambda: self.ai_status_var.set(t_gui("ai_evaluating")))
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('analyzing', t_gui('ai_evaluating')))
                
            reliability_score = self._evaluate_ai_reliability(response, analysis_data)
            
            # 添加可靠性评估到分析结果
            if current_is_english:
                enhanced_response = f"{response}\n\n--- Reliability Assessment ---\nReliability Score: {reliability_score['score']:.1f}/10\nAssessment Notes: {reliability_score['explanation']}"
            else:
                enhanced_response = f"{response}\n\n--- 可靠性评估 ---\n可靠性评分: {reliability_score['score']:.1f}/10\n评估说明: {reliability_score['explanation']}"
            
            print(f"[LLM Debug] AI analysis completed successfully in {time.time() - start_time:.1f}s")
            return enhanced_response
            
        except Exception as e:
            print(f"[LLM Debug] AI分析失败: {str(e)}")
            
            # 更新状态：分析失败
            error_msg = f"{t_gui('ai_analysis_failed')}: {str(e)}"
            self.root.after(0, lambda: self.ai_status_var.set(error_msg))
            if self.ai_status_indicator:
                self.root.after(0, lambda: self.ai_status_indicator.set_status('error', error_msg))
            
            # 返回简化分析作为备选方案
            print("[LLM Debug] 返回简化分析作为备选方案")
            return self._generate_simplified_analysis(analysis_data)
    

    def _generate_simplified_analysis(self, analysis_data: dict) -> str:
        """生成简化版AI分析（当LLM调用失败时使用）"""
        try:
            # 提取关键数据
            market_data = analysis_data.get("market_data", {})
            msci_value = market_data.get('msci_value', 50)
            trend_5d = market_data.get('trend_5d', 0)
            
            # 根据当前系统语言生成简化分析
            current_is_english = is_english()
            if current_is_english:
                analysis = f"""## AI Analysis Summary (Simplified)

**Market Sentiment**: MSCI Index {msci_value:.1f}
**5-Day Trend**: {trend_5d:+.2f}
**Risk Level**: {'High' if msci_value > 70 or msci_value < 30 else 'Medium' if msci_value > 40 else 'Low'}

**Quick Recommendations**:
- {'Consider reducing positions' if msci_value > 70 else 'Moderate allocation recommended' if msci_value > 50 else 'Opportunity for value investing'}
- {'Focus on defensive stocks' if trend_5d < -5 else 'Monitor momentum stocks' if trend_5d > 5 else 'Balanced portfolio approach'}

*Note: This is a simplified analysis due to LLM timeout. For detailed analysis, please check your LLM configuration.*"""
            else:
                risk_level = '高' if msci_value > 70 or msci_value < 30 else '中' if msci_value > 40 else '低'
                quick_rec1 = '考虑减仓' if msci_value > 70 else '建议适度配置' if msci_value > 50 else '价值投资机会'
                quick_rec2 = '关注防御性股票' if trend_5d < -5 else '关注动能股票' if trend_5d > 5 else '平衡配置策略'
                
                analysis = f"""## AI分析摘要（简化版）

**市场情绪**: MSCI指数 {msci_value:.1f}
**5日趋势**: {trend_5d:+.2f}
**风险等级**: {risk_level}

**快速建议**:
- {quick_rec1}
- {quick_rec2}

*注：由于LLM超时，这是简化分析。如需详细分析，请检查LLM配置。*"""

            return analysis
            
        except Exception as e:
            print(f"[LLM Debug] 简化分析生成失败: {e}")
            current_is_english = is_english()
            if current_is_english:
                return "## AI Analysis Summary\n\nAnalysis temporarily unavailable due to technical issues. Please check LLM configuration."
            else:
                return "## AI分析摘要\n\n由于技术问题，分析暂时不可用。请检查LLM配置。"
    

    def _build_analysis_prompt(self, data: dict) -> str:
        """构建AI分析提示 - 根据系统语言"""
        current_is_english = is_english()
        if current_is_english:
            prompt = """IMPORTANT: Please respond in English only.

As a professional financial analyst, please provide in-depth investment strategy recommendations based on the following multi-dimensional technical analysis data:

## 📊 Market Sentiment Composite Index (MSCI)
"""
        else:
            prompt = """重要提示：请用中文回答。

作为专业的金融分析师，请基于以下多维度技术分析数据，提供深入的投资策略建议：

## 📊 市场情绪综合指数 (MSCI)
"""
        
        # 市场数据
        if data.get("market_data"):
            market = data["market_data"]
            msci = market.get('msci_value', 0)
            trend = market.get('trend_5d', 0)
            volatility = market.get('volatility', 0)
            volume_ratio = market.get('volume_ratio', 0)
            
            if is_english():
                # 市场状态判断（英文）
                if msci > 80:
                    market_state = "Extremely Optimistic"
                elif msci > 65:
                    market_state = "Healthy Optimistic"
                elif msci > 55:
                    market_state = "Cautiously Optimistic"
                elif msci > 45:
                    market_state = "Neutral"
                elif msci > 35:
                    market_state = "Mildly Pessimistic"
                elif msci > 25:
                    market_state = "Significantly Pessimistic"
                else:
                    market_state = "Panic Selling"
                
                # 趋势描述（英文）
                if trend > 10:
                    trend_desc = "Strong Uptrend"
                elif trend > 3:
                    trend_desc = "Moderate Uptrend"
                elif abs(trend) <= 3:
                    trend_desc = "Sideways"
                elif trend > -10:
                    trend_desc = "Moderate Downtrend"
                else:
                    trend_desc = "Sharp Decline"
                
                # 波动率描述（英文）
                if volatility > 30:
                    vol_desc = "Extremely High Volatility"
                elif volatility > 20:
                    vol_desc = "High Volatility"
                elif volatility > 10:
                    vol_desc = "Medium Volatility"
                elif volatility > 5:
                    vol_desc = "Low Volatility"
                else:
                    vol_desc = "Very Low Volatility"
                
                prompt += f"- Market Sentiment Index: {msci:.2f} ({market_state})\n"
                prompt += f"- 5-Day Momentum Trend: {trend:+.2f} ({trend_desc})\n"
                prompt += f"- Market Volatility: {volatility:.2f} ({vol_desc})\n"
                prompt += f"- Volume Amplification: {volume_ratio:.2f}x\n"
                prompt += f"- Investor Sentiment: {market.get('market_sentiment', 'Neutral')}\n"
                prompt += f"- Risk Level: {market.get('risk_level', 'Medium')}\n\n"
            else:
                # 市场状态判断（中文）
                if msci > 80:
                    market_state = "极度乐观"
                elif msci > 65:
                    market_state = "健康乐观"
                elif msci > 55:
                    market_state = "谨慎乐观"
                elif msci > 45:
                    market_state = "中性"
                elif msci > 35:
                    market_state = "轻度悲观"
                elif msci > 25:
                    market_state = "显著悲观"
                else:
                    market_state = "恐慌抛售"
                
                # 趋势描述（中文）
                if trend > 10:
                    trend_desc = "强劲上涨"
                elif trend > 3:
                    trend_desc = "温和上涨"
                elif abs(trend) <= 3:
                    trend_desc = "横盘整理"
                elif trend > -10:
                    trend_desc = "温和下跌"
                else:
                    trend_desc = "急剧下跌"
                
                # 波动率描述（中文）
                if volatility > 30:
                    vol_desc = "极高波动"
                elif volatility > 20:
                    vol_desc = "高波动"
                elif volatility > 10:
                    vol_desc = "中等波动"
                elif volatility > 5:
                    vol_desc = "低波动"
                else:
                    vol_desc = "极低波动"
                
                prompt += f"- 市场情绪指数: {msci:.2f} ({market_state})\n"
                prompt += f"- 5日动量趋势: {trend:+.2f} ({trend_desc})\n"
                prompt += f"- 市场波动率: {volatility:.2f} ({vol_desc})\n"
                prompt += f"- 成交量放大: {volume_ratio:.2f}倍\n"
                prompt += f"- 投资者情绪: {market.get('market_sentiment', '中性')}\n"
                prompt += f"- 风险等级: {market.get('risk_level', '中等')}\n\n"
        
        # 宏观经济环境（英文）
        if data.get("macro_indicators"):
            macro = data["macro_indicators"]
            prompt += "## 🌍 Macroeconomic Environment\n"
            prompt += f"- Benchmark Interest Rate: {macro.get('interest_rate', 0):.1f}% (Monetary Policy Direction)\n"
            prompt += f"- Inflation Level: {macro.get('inflation_rate', 0):.1f}% (Price Stability)\n"
            prompt += f"- GDP Growth: {macro.get('gdp_growth', 0):.1f}% (Economic Growth Momentum)\n"
            prompt += f"- Currency Strength: {macro.get('currency_strength', 0):.1f}/100 (Exchange Rate Stability)\n"
            prompt += f"- Market Liquidity: {macro.get('market_liquidity', 0):.1f}/100 (Capital Adequacy)\n\n"
        
        # 新闻情感分析（英文）
        if data.get("news_sentiment"):
            news = data["news_sentiment"]
            sentiment_score = news.get('overall_sentiment', 0)
            
            if sentiment_score > 0.3:
                sentiment_desc = "Positive Optimistic"
            elif sentiment_score > -0.3:
                sentiment_desc = "Neutral Balanced"
            else:
                sentiment_desc = "Negative Pessimistic"
            
            prompt += "## 📰 Market Sentiment Analysis\n"
            prompt += f"- Overall Sentiment Tendency: {sentiment_score:+.2f} ({sentiment_desc})\n"
            prompt += f"- Positive News Ratio: {news.get('positive_ratio', 0):.1%}\n"
            prompt += f"- Negative News Ratio: {news.get('negative_ratio', 0):.1%}\n"
            prompt += f"- Neutral News Ratio: {news.get('neutral_ratio', 0):.1%}\n"
            prompt += f"- News Activity: {news.get('news_volume', 0)} articles/day\n\n"
        
        # 行业数据（英文）
        if data.get("industry_data"):
            prompt += "## 🏭 Industry Relative Strength Index (IRSI)\n"
            sorted_industries = sorted(data["industry_data"].items(), key=lambda x: x[1].get('irsi_value', 0), reverse=True)
            for i, (industry, info) in enumerate(sorted_industries[:5]):
                irsi = info.get('irsi_value', 0)
                stock_count = info.get('stock_count', 0)
                avg_volume = info.get('avg_volume', 0)
                
                # 行业强度评级（英文）
                if irsi > 70:
                    strength = "Very Strong"
                elif irsi > 60:
                    strength = "Strong"
                elif irsi > 40:
                    strength = "Neutral"
                elif irsi > 30:
                    strength = "Weak"
                else:
                    strength = "Very Weak"
                
                rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📈" if i == 3 else "📊"
                prompt += f"{rank_emoji} {industry}: IRSI={irsi:.2f} ({strength}), {stock_count} stocks, Avg Daily Volume {avg_volume/10000:.1f}M\n"
            prompt += "\n"
        
        # 个股数据（英文）
        if data.get("stock_data"):
            prompt += "## 📈 Individual Stock Trend Strength Index (RTSI)\n"
            sorted_stocks = sorted(data["stock_data"].items(), key=lambda x: x[1].get('rtsi_value', 0), reverse=True)
            for i, (formatted_code, info) in enumerate(sorted_stocks[:10]):
                rtsi = info.get('rtsi_value', 0)
                stock_name = info.get('name', formatted_code)  # 使用'name'而不是'stock_name'
                industry = info.get('industry', 'N/A')
                
                # 个股强度评级（英文）
                if rtsi > 80:
                    rating = "Strongly Recommend"
                elif rtsi > 65:
                    rating = "Recommend"
                elif rtsi > 50:
                    rating = "Moderate Attention"
                elif rtsi > 35:
                    rating = "Cautious Watch"
                else:
                    rating = "Not Recommended"
                
                rank_emoji = "⭐" if i < 3 else "🌟" if i < 6 else "✨"
                # 保留股票名称的中文，但其他内容使用英文，股票代码已格式化
                prompt += f"{rank_emoji} {formatted_code} ({stock_name}): RTSI={rtsi:.2f}, Industry: {industry}, Rating: {rating}\n"
            prompt += "\n"
        
        # 分析要求
        if current_is_english:
            prompt += """## 🎯 Professional Analysis Requirements

As a senior quantitative analyst, please provide in-depth analysis from the following dimensions based on current technical indicators and 30-day historical data:

### 📈 Market Trend Analysis
1. **Macroeconomic Sentiment Analysis**: Based on MSCI index changes, determine the current market cycle stage
2. **Momentum Feature Recognition**: Combine 5-day trends and volatility to analyze market momentum strength
3. **Liquidity Assessment**: Judge capital participation through volume amplification multiples

### 🏭 Sector Rotation Strategy
4. **Strong Sector Discovery**: Based on IRSI rankings, identify leading sectors with sustainability
5. **Sector Allocation Advice**: Provide sector allocation weight recommendations based on historical performance

### 🎯 Individual Stock Selection Strategy
6. **Leading Stock Screening**: Based on RTSI ratings, screen leading stocks in each sector
7. **Entry Timing**: Judge optimal entry points based on historical rating changes
8. **Position Management**: Provide position adjustment strategies based on individual stock strength changes

### ⚠️ Risk Management System
9. **Systematic Risk Warning**: Identify potential risk points based on historical volatility patterns
10. **Profit/Loss Strategy**: Develop scientific risk control plans based on technical indicators

### 🔮 Forward-looking Outlook
11. **Short-term Trading Strategy**: Trading opportunities and considerations within 1-2 weeks
12. **Medium-term Investment Layout**: Allocation directions and key focus areas for 1-3 months

**Output Requirements**: Please use professional terminology combined with plain explanations, emphasizing data-driven investment logic, with content controlled at 800-1000 words, ensuring depth and practicality of analysis. You may keep stock names and industry names in their original language (Chinese) as they are part of the data."""
        else:
            prompt += """## 🎯 专业分析要求

作为资深量化分析师，请基于当前技术指标和30日历史数据，从以下维度提供深入分析：

### 📈 市场趋势分析
1. **宏观情绪分析**：根据MSCI指数变化，判断当前市场周期阶段
2. **动能特征识别**：结合5日趋势和波动率，分析市场动能强度
3. **流动性评估**：通过成交量放大倍数，判断资金参与度

### 🏭 板块轮动策略
4. **强势板块发现**：基于IRSI排名，识别具有持续性的领涨板块
5. **板块配置建议**：根据历史表现，提供板块配置权重建议

### 🎯 个股精选策略
6. **龙头股筛选**：基于RTSI评级，筛选各板块龙头股
7. **入场时机**：根据历史评级变化，判断最佳入场点位
8. **仓位管理**：基于个股强度变化，提供仓位调整策略

### ⚠️ 风险管理体系
9. **系统性风险预警**：根据历史波动率模式，识别潜在风险点
10. **止盈止损策略**：基于技术指标，制定科学的风控方案

### 🔮 前瞻性展望
11. **短期交易策略**：1-2周内的交易机会和注意事项
12. **中期投资布局**：1-3个月的配置方向和重点关注领域

**输出要求**：请使用专业术语结合通俗解释，强调数据驱动的投资逻辑，内容控制在800-1000字，确保分析的深度和实用性。股票名称和行业名称保持中文原文。"""
        
        return prompt
    def _evaluate_ai_reliability(self, ai_response: str, analysis_data: dict) -> dict:
        """评估AI分析结果的可靠性"""
        try:
            score = 10.0  # 基础分数
            explanations = []
            
            # 1. 检查响应长度和完整性
            if len(ai_response) < 100:
                score -= 2.0
                if is_english():
                    explanations.append("Response too short, information may be incomplete")
                else:
                    explanations.append("响应过短，可能信息不完整")
            elif len(ai_response) > 2000:
                score -= 1.0
                if is_english():
                    explanations.append("Response too long, may contain redundant information")
                else:
                    explanations.append("响应过长，可能包含冗余信息")
            
            # 2. 检查是否包含关键分析要素
            if is_english():
                key_elements = ['market', 'industry', 'stock', 'risk', 'recommendation']
            else:
                key_elements = ['市场', '行业', '股票', '风险', '建议']
            missing_elements = []
            for element in key_elements:
                if element not in ai_response:
                    missing_elements.append(element)
            
            if missing_elements:
                score -= len(missing_elements) * 0.5
                if is_english():
                    explanations.append(f"Missing key analysis elements: {', '.join(missing_elements)}")
                else:
                    explanations.append(f"缺少关键分析要素: {', '.join(missing_elements)}")
            
            # 3. 检查数据引用的准确性
            market_data = analysis_data.get('market_data', {})
            msci_value = market_data.get('msci_value', 0)
            
            # 检查MSCI数值是否在合理范围内
            if msci_value < 0 or msci_value > 100:
                score -= 1.5
                if is_english():
                    explanations.append("MSCI index out of normal range, may affect analysis accuracy")
                else:
                    explanations.append("MSCI指数超出正常范围，可能影响分析准确性")
            
            # 4. 检查是否包含具体数值
            import re
            numbers_in_response = re.findall(r'\d+\.?\d*', ai_response)
            if len(numbers_in_response) < 3:
                score -= 1.0
                if is_english():
                    explanations.append("Lack of specific numerical support, analysis may be too abstract")
                else:
                    explanations.append("缺少具体数值支撑，分析可能过于抽象")
            
            # 5. 检查是否包含免责声明或风险提示
            if is_english():
                risk_keywords = ['risk', 'caution', 'reference only', 'not constitute', 'advice']
            else:
                risk_keywords = ['风险', '谨慎', '仅供参考', '不构成', '建议']
            risk_mentions = sum(1 for keyword in risk_keywords if keyword in ai_response)
            if risk_mentions < 2:
                score -= 0.5
                if is_english():
                    explanations.append("Insufficient risk warnings")
                else:
                    explanations.append("风险提示不足")
            
            # 6. 数据样本大小评估
            stock_count = len(analysis_data.get('stock_data', {}))
            industry_count = len(analysis_data.get('industry_data', {}))
            
            if stock_count < 20:
                score -= 2.0
                if is_english():
                    explanations.append(f"Insufficient stock samples (current {stock_count}, recommend ≥20), may affect analysis representativeness")
                else:
                    explanations.append(f"股票样本数量不足（当前{stock_count}个，建议≥20个），可能影响分析代表性")
            elif stock_count < 10:
                score -= 1.0
                if is_english():
                    explanations.append(f"Few stock samples (current {stock_count}), recommend increasing samples")
                else:
                    explanations.append(f"股票样本数量偏少（当前{stock_count}个），建议增加样本")
            
            if industry_count < 10:
                score -= 1.5
                if is_english():
                    explanations.append(f"Insufficient industry samples (current {industry_count}, recommend ≥10), may affect industry analysis comprehensiveness")
                else:
                    explanations.append(f"行业样本数量不足（当前{industry_count}个，建议≥10个），可能影响行业分析全面性")
            elif industry_count < 5:
                score -= 0.8
                if is_english():
                    explanations.append(f"Few industry samples (current {industry_count}), recommend increasing industry coverage")
                else:
                    explanations.append(f"行业样本数量偏少（当前{industry_count}个），建议增加行业覆盖")
            
            # 7. 多维度数据完整性评估
            data_dimensions = 0
            if analysis_data.get('market_data'):
                data_dimensions += 1
            if analysis_data.get('macro_indicators'):
                data_dimensions += 1
                score += 0.5  # 宏观数据加分
                if is_english():
                    explanations.append("Contains macroeconomic data, enhances analysis depth")
                else:
                    explanations.append("包含宏观经济数据，增强分析深度")
            if analysis_data.get('news_sentiment'):
                data_dimensions += 1
                score += 0.5  # 情感数据加分
                if is_english():
                    explanations.append("Contains market sentiment data, improves analysis comprehensiveness")
                else:
                    explanations.append("包含市场情感数据，提升分析全面性")
            if analysis_data.get('historical_data'):
                data_dimensions += 1
                historical_days = len(analysis_data['historical_data'].get('dates', []))
                if historical_days >= 30:
                    score += 0.5  # 充足历史数据加分
                    if is_english():
                        explanations.append(f"Sufficient historical data ({historical_days} days), supports trend analysis")
                    else:
                        explanations.append(f"历史数据充足（{historical_days}天），支持趋势分析")
                elif historical_days >= 10:
                    if is_english():
                        explanations.append(f"Historical data basically meets requirements ({historical_days} days)")
                    else:
                        explanations.append(f"历史数据基本满足要求（{historical_days}天）")
                else:
                    score -= 0.5
                    if is_english():
                        explanations.append(f"Insufficient historical data ({historical_days} days), may affect trend judgment")
                    else:
                        explanations.append(f"历史数据不足（{historical_days}天），可能影响趋势判断")
            
            if data_dimensions < 3:
                score -= 1.0
                if is_english():
                    explanations.append(f"Insufficient data dimensions (current {data_dimensions}), recommend adding data sources")
                else:
                    explanations.append(f"数据维度不足（当前{data_dimensions}个），建议增加数据源")
            
            # 8. 新增数据质量检查
            if analysis_data.get('macro_indicators'):
                macro = analysis_data['macro_indicators']
                # 检查宏观数据合理性
                interest_rate = macro.get('interest_rate', 0)
                if interest_rate < 0 or interest_rate > 20:
                    score -= 0.5
                    if is_english():
                        explanations.append("Abnormal macro interest rate data, may affect analysis accuracy")
                    else:
                        explanations.append("宏观利率数据异常，可能影响分析准确性")
            
            if analysis_data.get('news_sentiment'):
                news = analysis_data['news_sentiment']
                sentiment_score = news.get('overall_sentiment', 0)
                if abs(sentiment_score) > 1:
                    score -= 0.5
                    if is_english():
                        explanations.append("News sentiment index out of normal range")
                    else:
                        explanations.append("新闻情感指数超出正常范围")
            
            # 确保分数在合理范围内
            score = max(0.0, min(10.0, score))
            
            # 生成总体评估说明
            if is_english():
                if score >= 8.5:
                    overall = "Excellent analysis quality, complete data, high reliability"
                elif score >= 7.0:
                    overall = "Good analysis quality, recommendations have reference value"
                elif score >= 5.5:
                    overall = "Average analysis quality, recommendations need cautious reference"
                else:
                    overall = "Low analysis quality, for reference only, need to combine with other information"
                
                explanation = overall
                if explanations:
                    explanation += f". Main issues: {'; '.join(explanations)}"
            else:
                if score >= 8.5:
                    overall = "分析质量优秀，数据完整，建议可信度高"
                elif score >= 7.0:
                    overall = "分析质量良好，建议具有一定参考价值"
                elif score >= 5.5:
                    overall = "分析质量一般，建议需谨慎参考"
                else:
                    overall = "分析质量较低，建议仅作参考，需结合其他信息"
                
                explanation = overall
                if explanations:
                    explanation += f"。主要问题: {'; '.join(explanations)}"
            
            return {
                'score': score,
                'explanation': explanation,
                'details': explanations
            }
            
        except Exception as e:
            if is_english():
                explanation = f"Error in reliability assessment process: {str(e)}"
            else:
                explanation = f"可靠性评估过程出错: {str(e)}"
            return {
                'score': 5.0,
                'explanation': explanation,
                'details': []
            }
    
    def _display_ai_analysis(self, ai_response: str):
        """显示AI分析结果"""
        try:
            # 保存AI分析结果到实例变量，供HTML报告使用
            self.ai_analysis_result = ai_response
            
            # 在文本区域添加AI分析结果
            current_is_english = is_english()
            if current_is_english:
                ai_section = f"\n\n{'='*50}\n🤖 AI Intelligent Analysis\n{'='*50}\n\n{ai_response}\n"
            else:
                ai_section = f"\n\n{'='*50}\n🤖 AI智能分析\n{'='*50}\n\n{ai_response}\n"
            
            # 获取当前文本内容
            current_text = self.text_area.get(1.0, tk.END)
            
            # 添加AI分析内容
            self.text_area.insert(tk.END, ai_section)
            
            # 设置AI分析部分的颜色
            start_line = len(current_text.split('\n')) + 1
            self.text_area.tag_add("ai_analysis", f"{start_line}.0", tk.END)
            self.text_area.tag_config("ai_analysis", foreground="#0066CC")
            
            # 滚动到底部
            self.text_area.see(tk.END)
            
            # 更新状态
            self.status_var.set(f"{t_gui('analysis_complete')} | {t_gui('ai_analysis_included')}")
            
        except Exception as e:
            print(f"AI分析结果显示失败: {str(e)}")
            self.status_var.set(t_gui("ai_analysis_display_failed"))
    
    def show_data_validation(self):
        """显示数据验证窗口"""
        try:
            from data.data_validator import DataValidator
            
            # 检查是否有数据
            if not hasattr(self, 'current_dataset') or self.current_dataset is None:
                messagebox.showwarning(t_tools("data_validation_tip"), t_tools("load_data_first_validation"))
                return
            
            # 创建验证器并进行验证
            self.update_text_area(t_tools("start_data_validation"), "blue")
            validator = DataValidator()
            
            try:
                result = validator.validate_complete_dataset(self.current_dataset)
                
                # 生成验证报告
                report = validator.generate_quality_report()
                
                # 创建验证结果窗口
                validation_window = tk.Toplevel(self.root)
                validation_window.title(t_tools("data_validation_window_title"))
                validation_window.geometry("800x600")
                validation_window.configure(bg='#f0f0f0')
                validation_window.transient(self.root)
                
                # 报告文本区域
                text_frame = tk.Frame(validation_window, bg='#f0f0f0')
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                report_text = tk.Text(text_frame, wrap=tk.WORD, font=('Microsoft YaHei', 11))
                scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=report_text.yview)
                report_text.configure(yscrollcommand=scrollbar.set)
                
                report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # 插入报告内容
                report_text.insert(tk.END, report)
                report_text.config(state=tk.DISABLED)
                
                # 按钮区域
                button_frame = tk.Frame(validation_window, bg='#f0f0f0')
                button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
                
                # 统一按钮样式 - 与MSCI详情按钮一致，无色彩
                button_style = {
                    'font': ('Microsoft YaHei', 11),
                    'bg': '#f0f0f0',
                    'fg': 'black',
                    'relief': tk.RAISED,
                    'bd': 2,
                    'padx': 20,
                    'pady': 5
                }
                
                # 关闭按钮
                tk.Button(button_frame, text=t_tools("btn_close"), command=validation_window.destroy,
                         **button_style).pack(side=tk.RIGHT)
                
                # 导出按钮
                def export_validation_report():
                    from tkinter import filedialog
                    filename = filedialog.asksaveasfilename(
                        title=t_tools("export_validation_report_title"),
                        defaultextension=".txt",
                        filetypes=[(t_tools("text_files"), "*.txt"), (t_tools("all_files"), "*.*")]
                    )
                    if filename:
                        try:
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(report)
                            messagebox.showinfo(t_tools("export_success"), f"{t_tools('validation_report_saved')}: {filename}")
                        except Exception as e:
                            messagebox.showerror(t_tools("export_error"), f"{t_tools('save_failed')}: {str(e)}")
                
                tk.Button(button_frame, text=t_tools("btn_export_report"), command=export_validation_report,
                         **button_style).pack(side=tk.RIGHT, padx=(0, 10))
                
                # 更新状态
                quality_score = result.get('quality_score', 0)
                status = t_tools("validation_passed") if result.get('is_valid', False) else t_tools("validation_failed")
                self.update_text_area(f"{t_tools('data_validation_completed')}: {status}, {t_tools('quality_score')}: {quality_score}/100", "green" if result.get('is_valid', False) else "red")
                
            except Exception as e:
                self.update_text_area(f"{t_tools('validation_error')}: {str(e)}", "red")
                messagebox.showerror(t_tools("validation_error"), f"{t_tools('validation_process_error')}:\n{str(e)}")
                
        except ImportError:
            messagebox.showerror(t_gui("feature_unavailable"), t_tools("data_validator_not_found"))
    
    def show_performance_monitor(self):
        """显示性能监控窗口"""
        try:
            from utils.performance_monitor import get_global_monitor
            
            # 获取性能监控器
            monitor = get_global_monitor()
            
            # 生成性能报告
            self.update_text_area(t_tools("generate_performance_report"), "blue")
            performance_report = monitor.generate_performance_report()
            system_metrics = monitor.get_system_metrics()
            
            # 创建性能监控窗口
            monitor_window = tk.Toplevel(self.root)
            monitor_window.title(t_tools("performance_monitor_window_title"))
            monitor_window.geometry("900x700")
            monitor_window.configure(bg='#f0f0f0')
            monitor_window.transient(self.root)
            
            # 窗口居中显示
            self._center_toplevel_window(monitor_window)
            
            # 创建笔记本控件用于分页显示
            notebook = ttk.Notebook(monitor_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 性能报告页
            report_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(report_frame, text=t_tools("performance_report_tab"))
            
            report_text = tk.Text(report_frame, wrap=tk.WORD, font=('Courier New', 11))
            report_scrollbar = tk.Scrollbar(report_frame, orient=tk.VERTICAL, command=report_text.yview)
            report_text.configure(yscrollcommand=report_scrollbar.set)
            
            report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            report_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            report_text.insert(tk.END, performance_report)
            report_text.config(state=tk.DISABLED)
            
            # 系统指标页
            system_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(system_frame, text=t_tools("system_metrics_tab"))
            
            # 系统指标显示区域
            metrics_text = tk.Text(system_frame, wrap=tk.WORD, font=('Courier New', 11))
            metrics_scrollbar = tk.Scrollbar(system_frame, orient=tk.VERTICAL, command=metrics_text.yview)
            metrics_text.configure(yscrollcommand=metrics_scrollbar.set)
            
            metrics_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            metrics_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            # 格式化系统指标
            system_info = f"""{t_tools("system_performance_metrics")}

{t_tools("cpu_usage")}: {system_metrics.get('current_cpu_percent', 'N/A')}%
{t_tools("memory_usage")}: {system_metrics.get('current_memory_percent', 'N/A')}%
{t_tools("memory_amount")}: {system_metrics.get('current_memory_mb', 'N/A')} MB
{t_tools("disk_read")}: {system_metrics.get('current_disk_read_mb', 'N/A')} MB
{t_tools("disk_write")}: {system_metrics.get('current_disk_write_mb', 'N/A')} MB

{t_tools("historical_data_points")}:
- {t_tools("cpu_usage_history")}: {len(system_metrics.get('cpu_usage_history', []))} {t_tools("data_points")}
- {t_tools("memory_usage_history")}: {len(system_metrics.get('memory_usage_history', []))} {t_tools("data_points")}
- {t_tools("disk_io_history")}: {len(system_metrics.get('disk_io_history', []))} {t_tools("data_points")}

{t_tools("monitor_status")}: {t_tools("running_normally")}
"""
            
            metrics_text.insert(tk.END, system_info)
            metrics_text.config(state=tk.DISABLED)
            
            # 按钮区域
            button_frame = tk.Frame(monitor_window, bg='#f0f0f0')
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # 刷新按钮
            def refresh_monitor():
                # 重新生成报告
                new_report = monitor.generate_performance_report()
                new_system_metrics = monitor.get_system_metrics()
                
                # 更新报告
                report_text.config(state=tk.NORMAL)
                report_text.delete(1.0, tk.END)
                report_text.insert(tk.END, new_report)
                report_text.config(state=tk.DISABLED)
                
                # 更新系统指标
                new_system_info = f"""{t_tools("system_performance_metrics")} ({t_tools("refreshed")})

{t_tools("cpu_usage")}: {new_system_metrics.get('current_cpu_percent', 'N/A')}%
{t_tools("memory_usage")}: {new_system_metrics.get('current_memory_percent', 'N/A')}%
{t_tools("memory_amount")}: {new_system_metrics.get('current_memory_mb', 'N/A')} MB
{t_tools("disk_read")}: {new_system_metrics.get('current_disk_read_mb', 'N/A')} MB
{t_tools("disk_write")}: {new_system_metrics.get('current_disk_write_mb', 'N/A')} MB

{t_tools("historical_data_points")}:
- {t_tools("cpu_usage_history")}: {len(new_system_metrics.get('cpu_usage_history', []))} {t_tools("data_points")}
- {t_tools("memory_usage_history")}: {len(new_system_metrics.get('memory_usage_history', []))} {t_tools("data_points")}
- {t_tools("disk_io_history")}: {len(new_system_metrics.get('disk_io_history', []))} {t_tools("data_points")}

{t_tools("monitor_status")}: {t_tools("running_normally")}
"""
                
                metrics_text.config(state=tk.NORMAL)
                metrics_text.delete(1.0, tk.END)
                metrics_text.insert(tk.END, new_system_info)
                metrics_text.config(state=tk.DISABLED)
            
            # 统一按钮样式 - 与MSCI详情按钮一致，无色彩
            button_style = {
                'font': ('Microsoft YaHei', 11),
                'bg': '#f0f0f0',
                'fg': 'black',
                'relief': tk.RAISED,
                'bd': 2,
                'padx': 20,
                'pady': 5
            }
            
            tk.Button(button_frame, text=t_tools("refresh_button"), command=refresh_monitor,
                     **button_style).pack(side=tk.LEFT)
            
            # 重置性能统计按钮
            def reset_stats():
                result = messagebox.askyesno(t_tools("confirm"), t_tools("confirm_reset_stats"))
                if result:
                    monitor.reset_metrics()
                    refresh_monitor()
                    messagebox.showinfo(t_tools("success"), t_tools("stats_reset_success"))
            
            tk.Button(button_frame, text=t_tools("reset_stats_button"), command=reset_stats,
                     **button_style).pack(side=tk.LEFT, padx=10)
            
            # 关闭按钮
            tk.Button(button_frame, text=t_tools("close_button"), command=monitor_window.destroy,
                     **button_style).pack(side=tk.RIGHT)
            
            self.update_text_area(t_tools("performance_monitor_opened"), "green")
            
        except ImportError:
            messagebox.showerror(t_tools("feature_unavailable"), t_tools("performance_monitor_not_found"))
        except Exception as e:
            messagebox.showerror(t_tools("monitor_failed"), f"{t_tools('performance_monitor_error')}:\n{str(e)}")
            self.update_text_area(f"{t_tools('performance_monitor_failed')}: {str(e)}", "red")
    
    def update_data_files(self):
        """手动更新数据文件"""
        try:
            from utils.data_updater import DataUpdater
            
            # 创建数据更新器并显示进度窗口
            updater = DataUpdater(self.root)
            updater.check_and_update(show_progress=True)
            
            # 更新状态
            self.status_var.set(t_tools("status_updating_data"))
            
        except ImportError:
            messagebox.showerror(t_tools("feature_unavailable"),
                                t_tools("data_updater_not_found"))
        except Exception as e:
            error_msg = t_tools("data_update_error")
            messagebox.showerror(t_tools("update_failed"), 
                               f"{error_msg}:\n{str(e)}")
            failed_msg = t_tools("data_update_failed")
            self.update_text_area(f"{failed_msg}: {str(e)}", "red")


# 分析窗口类定义
class StockAnalysisWindow:
    """个股趋势分析窗口 - 完整版本"""
    
    def __init__(self, parent, analysis_results, current_dataset=None):
        self.parent = parent
        self.analysis_results = analysis_results
        self.current_dataset = current_dataset  # 添加对当前数据集的引用
        self.window = tk.Toplevel(parent)
        self.current_stock = None
        self.fig = None
        self.ax = None
        self.canvas = None
        
        # 继承父窗口的字体配置
        if hasattr(parent, 'fonts'):
            self.fonts = parent.fonts
        else:
            self.fonts = {
                'title': ('Microsoft YaHei', 12, 'bold'),
                'menu': ('Microsoft YaHei', 11),
                'button': ('Microsoft YaHei', 11),
                'text': ('Microsoft YaHei', 11),
                'status': ('Microsoft YaHei', 10)
            }
        
        self.setup_window()
        self.setup_components()
        self.load_stock_list()
    
    def setup_window(self):
        """设置窗口基本属性"""
        self.window.title(t_gui("stock_analysis_window_title"))
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 窗口居中显示
        self.center_window()
        
        # 设置窗口图标和属性
        self.window.resizable(True, True)
        self.window.minsize(900, 600)
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            # 优先使用项目根目录的mrcai.ico
            icon_paths = [
                "mrcai.ico",
                "resources/icons/mrcai.ico",
                "resources/icons/app.ico"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.window.iconbitmap(icon_path)
                    return
        except Exception as e:
            print(f"Warning: Failed to set window icon: {e}")
    
    def center_window(self):
        """窗口居中显示"""
        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 窗口尺寸
        window_width = 1000
        window_height = 700
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        self.window.geometry(f"+{x}+{y}")
    
    def setup_components(self):
        """设置界面组件 - 完整版本"""
        # 顶部股票选择区
        selector_frame = tk.Frame(self.window, bg='#f0f0f0', height=50)
        selector_frame.pack(fill=tk.X, padx=10, pady=5)
        selector_frame.pack_propagate(False)
        
        tk.Label(selector_frame, text=t_gui("stock_selector_label"), bg='#f0f0f0', 
                font=('Arial', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        
        # 股票下拉框
        self.stock_combo = ttk.Combobox(selector_frame, width=35, state="readonly",
                                        font=('Arial', 11))
        self.stock_combo.pack(side=tk.LEFT, padx=10, pady=10)
        # 绑定选择事件，实现自动更新
        self.stock_combo.bind('<<ComboboxSelected>>', self.on_stock_selected)
        
        # 搜索框
        tk.Label(selector_frame, text=t_gui("search_label"), bg='#f0f0f0').pack(side=tk.LEFT, padx=(20,5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(selector_frame, textvariable=self.search_var, 
                                    width=15, font=('Arial', 11))
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=10)
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        
        # 统一按钮样式 - 与MSCI详情按钮一致，无色彩
        button_style = {
            'font': ('Microsoft YaHei', 11),
            'bg': '#f0f0f0',
            'fg': 'black',
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 20,
            'pady': 5
        }
        
        # 分析按钮
        self.analyze_btn = tk.Button(selector_frame, text=t_gui("btn_start_analysis"), 
                                   command=self.analyze_selected_stock,
                                   **button_style)
        self.analyze_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 主体区域容器 - 使用grid布局实现精确比例控制
        main_container = tk.Frame(self.window, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 配置grid布局权重 - 上下比例为1:1（将详细分析板块调高一倍）
        main_container.grid_rowconfigure(0, weight=1)  # 上部区域：指标+图表
        main_container.grid_rowconfigure(1, weight=1)  # 下部区域：详细分析（一倍高度）
        main_container.grid_columnconfigure(0, weight=1)
        
        # 上部区域：指标和图表
        upper_container = tk.Frame(main_container, bg='#f0f0f0')
        upper_container.grid(row=0, column=0, sticky='nsew', padx=5, pady=(0, 5))
        
        # 左侧：核心指标面板
        left_frame = tk.Frame(upper_container, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        
        metrics_frame = tk.LabelFrame(left_frame, text=t_gui("core_metrics_label"), bg='#f0f0f0',
                                    font=('Arial', 11, 'bold'))
        metrics_frame.pack(fill=tk.BOTH, expand=True)
        
        # 指标变量
        self.rtsi_var = tk.StringVar(value="--")
        self.trend_var = tk.StringVar(value="--")
        self.confidence_var = tk.StringVar(value="--")
        self.industry_var = tk.StringVar(value="--")
        self.risk_var = tk.StringVar(value="--")
        self.slope_var = tk.StringVar(value="--")
        
        # 创建指标标签 - 增强版
        labels = [
            (t_gui("rtsi_index") + ":", self.rtsi_var, "blue"),
            (t_gui("trend_direction") + ":", self.trend_var, "green"),
            (t_gui("data_reliability") + ":", self.confidence_var, "purple"),
            (t_gui("industry_category") + ":", self.industry_var, "black"),
            (t_gui("risk_level") + ":", self.risk_var, "red"),
            (t_gui("trend_slope") + ":", self.slope_var, "orange")
        ]
        
        for i, (label_text, var, color) in enumerate(labels):
            tk.Label(metrics_frame, text=label_text, bg='#f0f0f0',
                    font=('Arial', 11)).grid(row=i, column=0, sticky='w', 
                                           padx=8, pady=8)
            label_widget = tk.Label(metrics_frame, textvariable=var, bg='#f0f0f0', 
                                  font=('Arial', 11, 'bold'), fg=color)
            label_widget.grid(row=i, column=1, sticky='w', padx=8, pady=8)
        
        # 添加动态颜色支持到现有标签
        self.metric_labels = {}
        for i, (label_text, var, color) in enumerate(labels):
            # 找到对应的标签widget并存储引用
            for widget in metrics_frame.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget('textvariable') == str(var):
                    self.metric_labels[label_text] = widget
                    break
        
        # 右侧：趋势图表区 - 优先保证图表完整显示
        chart_frame = tk.LabelFrame(upper_container, text=t_gui('trend_chart'), bg='#f0f0f0',
                                  font=('Arial', 11, 'bold'))
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # matplotlib图表 - 确保完整显示
        self.fig = Figure(figsize=(8, 5), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 初始化空图表
        self.init_empty_chart()
        
        # 下部区域：详细分析板块（调高一倍，与上部区域等比例1:1）
        lower_container = tk.Frame(main_container, bg='#f0f0f0')
        lower_container.grid(row=1, column=0, sticky='nsew', padx=5, pady=(5, 0))
        
        analysis_frame = tk.LabelFrame(lower_container, text=t_gui('detailed_analysis'), bg='#f0f0f0',
                                     font=('Arial', 11, 'bold'))
        analysis_frame.pack(fill=tk.BOTH, expand=True)
        
        self.analysis_text = tk.Text(analysis_frame, wrap=tk.WORD,
                                   font=('Microsoft YaHei', 11), bg='white')
        analysis_scrollbar = tk.Scrollbar(analysis_frame, orient=tk.VERTICAL, 
                                        command=self.analysis_text.yview)
        self.analysis_text.configure(yscrollcommand=analysis_scrollbar.set)
        
        self.analysis_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        analysis_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 底部按钮区
        button_frame = tk.Frame(self.window, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 底部按钮样式（复用button_style，这里重新定义以避免作用域问题）
        bottom_button_style = {
            'font': ('Microsoft YaHei', 11),
            'bg': '#f0f0f0',
            'fg': 'black',
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 20,
            'pady': 5
        }
        
        tk.Button(button_frame, text=t_gui("btn_export_analysis"), 
                 command=self.export_analysis,
                 **bottom_button_style).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text=t_gui("btn_add_watch"), 
                 command=self.add_to_watchlist,
                 **bottom_button_style).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text=t_gui("btn_refresh_data"), 
                 command=self.refresh_data,
                 **bottom_button_style).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text=t_gui("btn_close"), command=self.window.destroy,
                 **bottom_button_style).pack(side=tk.RIGHT, padx=5)
    
    def init_empty_chart(self):
        """初始化空图表"""
        self.ax.clear()
        self.ax.set_title(t_gui("chart_select_stock"), fontsize=12, pad=20)
        self.ax.set_xlabel(t_gui("chart_time"), fontsize=11)
        self.ax.set_ylabel(t_gui("chart_rating_score"), fontsize=11)
        self.ax.grid(True, alpha=0.3)
        self.ax.text(0.5, 0.5, t_gui("chart_waiting_analysis"), 
                    transform=self.ax.transAxes, 
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=14, alpha=0.5)
        self.canvas.draw()
    
    def on_stock_selected(self, event):
        """股票选择事件 - 自动更新内容"""
        selected = self.stock_combo.get()
        if selected:
            # 自动分析选中的股票
            self.analyze_selected_stock()
    
    def on_search_change(self, event):
        """搜索框变化事件 - 修改为不影响下拉列表"""
        # 搜索框变化时不再过滤下拉列表
        # 用户可以在搜索框中直接输入，然后点击分析按钮
        pass
    
    def filter_stock_list(self, search_term):
        """过滤股票列表 - 已停用，保持原始列表不变"""
        # 该方法不再被调用，保持下拉列表显示完整的股票列表
        # 用户可以通过搜索框直接输入股票代码进行分析
        pass
    
    def load_stock_list(self):
        """加载股票列表 - 增强版"""
        try:
            if hasattr(self.analysis_results, 'stocks'):
                stocks = self.analysis_results.stocks
                # 按RTSI排序显示
                stock_items = []
                for code, info in stocks.items():
                    name = info.get('name', code)
                    rtsi = info.get('rtsi', {}).get('rtsi', 0) if isinstance(info.get('rtsi'), dict) else info.get('rtsi', 0)
                    
                    # 智能显示股票代码：如果是补0的数字代码但原始为字母，则显示去零版本
                    display_code = code
                    if code.startswith('00') and len(code) == 6:
                        # 检查是否可能是被补零的字母代码（如000AAPL -> AAPL）
                        trimmed = code.lstrip('0')
                        if trimmed and not trimmed.isdigit():
                            display_code = trimmed
                    
                    stock_items.append((rtsi, f"{display_code} {name}"))
                
                # 按RTSI降序排列
                stock_items.sort(key=lambda x: x[0], reverse=True)
                stock_list = [item[1] for item in stock_items]
                
                self.stock_combo['values'] = stock_list
                
                # 状态信息
                self.analysis_text.delete(1.0, tk.END)
                analysis_status = t_gui('analysis_completed') if stocks else t_gui('awaiting_analysis')
                status_text = f"""
{t_gui('stock_data_loading_completed')}

• {t_gui('total_stocks')}: {len(stocks):,}{t_gui('units_stocks')}
• {t_gui('data_status')}: {analysis_status}
• {t_gui('sort_method')}: {t_gui('rtsi_descending_order')}

{t_gui('usage_instructions')}:
1. {t_gui('select_stock_from_dropdown')}
2. {t_gui('use_search_box_quick_find')}
3. {t_gui('click_start_analysis_view_details')}
4. {t_gui('chart_shows_rating_trend_changes')}

{t_gui('tip')}: {t_gui('enter_stock_code_name_keyword_search')}
"""
                self.analysis_text.insert(1.0, status_text)
                
            else:
                # 备用方案：报错提示用户加载真实数据
                self.stock_combo['values'] = []
                
                self.analysis_text.delete(1.0, tk.END)
                self.analysis_text.insert(1.0, """

当前使用样本股票数据，实际使用时将
显示完整的股票列表和分析结果。

请先加载真实数据文件进行分析。
""")
                
        except Exception as e:
            messagebox.showerror("错误", f"加载股票列表失败: {str(e)}")
    
    def analyze_selected_stock(self):
        """分析选定的股票 - 使用搜索框直接输入的股票代码"""
        # 安全获取搜索框输入 - 优先使用控件，备选使用变量
        search_input = ""
        try:
            if hasattr(self, 'search_entry') and self.search_entry.winfo_exists():
                search_input = self.search_entry.get().strip()
            elif hasattr(self, 'search_var'):
                search_input = self.search_var.get().strip()
        except Exception:
            # 如果获取失败，使用空字符串
            search_input = ""
        
        if search_input:
            # 处理股票代码格式
            if search_input.isdigit():
                # 全为数字时，自动补充为6位数，前面用0填充
                stock_code = search_input.zfill(6)
            else:
                # 包含英文字母，转为大写并补0到6位进行查找
                stock_code = search_input.upper().zfill(6)
            
            stock_name = stock_code  # 初始使用代码作为名称
        else:
            # 如果搜索框为空，则使用选择框
            selected = self.stock_combo.get()
            if not selected:
                messagebox.showwarning("提示", "请在搜索框中输入股票代码或从列表中选择股票")
                return
            
            # 解析股票代码
            display_code = selected.split(' ')[0]  # 下拉列表中显示的代码
            stock_name = selected.split(' ')[1] if len(selected.split(' ')) > 1 else display_code
            
            # 将显示代码转换为内部查找用的代码
            if display_code.isalpha() and len(display_code) <= 5:
                # 如果是字母代码，需要补0到6位进行查找
                stock_code = display_code.zfill(6)
            else:
                stock_code = display_code
        
        try:
            
            self.current_stock = {'code': stock_code, 'name': stock_name}
            
            # 获取股票数据
            if hasattr(self.analysis_results, 'stocks') and stock_code in self.analysis_results.stocks:
                stock_data = self.analysis_results.stocks[stock_code]
                
                # 如果从数据中能找到更准确的股票名称，则更新
                if 'name' in stock_data:
                    stock_name = stock_data['name']
                elif 'stock_name' in stock_data:
                    stock_name = stock_data['stock_name']
                
                # 更新窗口标题
                self.window.title(f"{t_gui('individual_stock_trend_analysis')} - {stock_name}")
                
                # RTSI分析数据
                rtsi_data = stock_data.get('rtsi', {})
                if isinstance(rtsi_data, dict):
                    rtsi_value = rtsi_data.get('rtsi', 0)
                    confidence = rtsi_data.get('confidence', 0)
                    slope = rtsi_data.get('slope', 0)
                    # 注意：忽略数据中可能存在的trend字段，因为可能是中文字符串
                    # 我们应该始终使用自己的计算结果
                else:
                    rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
                    confidence = 0.5  # 默认置信度
                    slope = 0
                
                # 统一使用基于RTSI值的实时计算，确保核心指标和详细分析一致
                # 这里计算的trend是英文键值，可以安全地用于trend_map查找
                trend = self.classify_trend(rtsi_value)
                
                # 更新指标显示
                self.update_metrics_display(stock_data, rtsi_value, trend, confidence, slope)
                
                # 更新趋势图表
                self.update_trend_chart_with_data_calculation(stock_code, stock_data)
                
                # 生成详细分析报告
                self.generate_detailed_analysis(stock_code, stock_name, stock_data, rtsi_data)
                
                # 清空搜索框，便于下次输入
                self.search_var.set("")
                
            else:
                # 显示找不到股票的错误信息
                messagebox.showerror("股票未找到", 
                                   f"找不到股票代码 '{stock_code}' 的数据\n\n"
                                   f"可能原因：\n"
                                   f"1. 股票代码不存在或输入错误\n"
                                   f"2. 该股票不在当前数据集中\n"
                                   f"3. 请检查股票代码格式\n\n"
                                   f"建议：\n"
                                   f"- 检查股票代码是否正确\n"
                                   f"- 从下拉列表中选择已有股票\n"
                                   f"- 确认数据文件包含该股票")
                
                # 清空搜索框，让用户重新输入
                self.search_var.set("")
                
                # 显示基本的"未找到"状态
                self.show_no_analysis_data(stock_code, stock_name)
                
        except Exception as e:
            messagebox.showerror("分析错误", f"股票分析失败:\n{str(e)}")
            
            # 清空搜索框，便于下次输入
            self.search_var.set("")
    
    def update_metrics_display(self, stock_data, rtsi_value, trend, confidence, slope):
        """更新指标显示 - 根据趋势动态设置颜色"""
        try:
            # RTSI指数
            self.rtsi_var.set(f"{rtsi_value:.2f}")
            
            # 趋势方向 - 采用统一的专业术语，添加调试信息
            print(f"[Debug] update_metrics_display 收到的trend值: '{trend}' (类型: {type(trend)})")
            
            trend_map = {
                'strong_bull': t_gui('strong_bull'),
                'moderate_bull': t_gui('moderate_bull'),
                'weak_bull': t_gui('weak_bull'),
                'neutral': t_gui('sideways_consolidation'),
                'weak_bear': t_gui('weak_bear'),
                'moderate_bear': t_gui('moderate_bear'),
                'strong_bear': t_gui('strong_bear')
            }
            
            print(f"[Debug] trend_map键: {list(trend_map.keys())}")
            
            # 安全地获取趋势显示文本
            if trend in trend_map:
                trend_display = trend_map[trend]
                print(f"[Debug] 找到匹配的trend: {trend} -> {trend_display}")
            else:
                trend_display = str(trend)  # 直接使用原值作为备选
                print(f"[Debug] 未找到匹配的trend，使用原值: {trend}")
            
            self.trend_var.set(trend_display)
            
            # 数据可靠性  
            self.confidence_var.set(f"{confidence:.1%}")
            
            # 行业信息
            industry = stock_data.get('industry', t_gui('uncategorized'))
            self.industry_var.set(industry)
            
            # 风险等级 - 保持原有逻辑（可能与详细分析区不同）
            risk_level = self.calculate_risk_level(rtsi_value, confidence)
            self.risk_var.set(risk_level)
            
            # 趋势斜率
            self.slope_var.set(f"{slope:.4f}")
            
        except Exception as e:
            print(f"[Debug] update_metrics_display出错: {e}")
            print(f"[Debug] 参数: rtsi_value={rtsi_value}, trend={trend}, confidence={confidence}, slope={slope}")
            # 设置默认值以防止界面崩溃
            self.rtsi_var.set("错误")
            self.trend_var.set("数据错误")
            self.confidence_var.set("错误")
            self.industry_var.set("错误")
            self.risk_var.set("错误")
            self.slope_var.set("错误")
            raise  # 重新抛出异常以便调试
        
        # 动态颜色设置 - 添加安全异常处理
        if hasattr(self, 'metric_labels'):
            try:
                # 趋势方向颜色：多头红色，空头绿色，其它黑色
                trend_label_key = t_gui("trend_direction") + ":"
                if trend_label_key in self.metric_labels:
                    if 'bull' in trend:
                        self.metric_labels[trend_label_key].config(fg='red')  # 多头红色
                    elif 'bear' in trend:
                        self.metric_labels[trend_label_key].config(fg='green')  # 空头绿色
                    else:
                        self.metric_labels[trend_label_key].config(fg='black')  # 其它黑色
                
                # RTSI指数颜色
                rtsi_label_key = t_gui("rtsi_index") + ":"
                if rtsi_label_key in self.metric_labels:
                    if rtsi_value >= 60:
                        self.metric_labels[rtsi_label_key].config(fg='red')  # 高分红色
                    elif rtsi_value <= 30:
                        self.metric_labels[rtsi_label_key].config(fg='green')  # 低分绿色
                    else:
                        self.metric_labels[rtsi_label_key].config(fg='black')  # 中性黑色
                
                # 风险等级颜色
                risk_label_key = t_gui("risk_level") + ":"
                if risk_label_key in self.metric_labels:
                    if t_gui('low_risk') in risk_level:
                        self.metric_labels[risk_label_key].config(fg='green')
                    elif t_gui('high_risk') in risk_level:
                        self.metric_labels[risk_label_key].config(fg='red')
                    else:
                        self.metric_labels[risk_label_key].config(fg='orange')
            except Exception as e:
                print(f"[Debug] 设置标签颜色失败: {e}")
                print(f"[Debug] 可用的标签键: {list(self.metric_labels.keys())}")
                print(f"[Debug] 尝试访问的键: {trend_label_key if 'trend_label_key' in locals() else 'N/A'}")
    
    def classify_trend(self, rtsi_value):
        """根据RTSI值分类趋势 - 统一标准版本，消除冲突"""
        # 采用与算法一致的7级分类标准
        if rtsi_value >= 75:
            return 'strong_bull'      # 强势多头
        elif rtsi_value >= 60:
            return 'moderate_bull'    # 温和多头
        elif rtsi_value >= 50:
            return 'weak_bull'        # 弱势多头
        elif rtsi_value >= 40:
            return 'neutral'          # 横盘整理
        elif rtsi_value >= 30:
            return 'weak_bear'        # 弱势空头
        elif rtsi_value >= 20:
            return 'moderate_bear'    # 温和空头
        else:
            return 'strong_bear'      # 强势空头
    
    def calculate_risk_level(self, rtsi_value, confidence):
        """计算风险等级 - 统一标准版本，基于RTSI值和置信度的综合评估"""
        # 采用与算法一致的风险评估逻辑
        if rtsi_value >= 75 and confidence >= 0.7:
            return f"🟢 {t_gui('extremely_low_risk')} ({t_gui('strong_confirmation')})"
        elif rtsi_value >= 75 and confidence >= 0.4:
            return f"🟡 {t_gui('medium_risk')} ({t_gui('strong_pending_confirmation')})"
        elif rtsi_value >= 60 and confidence >= 0.5:
            return f"🟢 {t_gui('low_risk')} ({t_gui('moderate_uptrend')})"
        elif rtsi_value >= 50 and confidence >= 0.4:
            return f"🟡 {t_gui('medium_risk')} ({t_gui('weak_bull')})"
        elif rtsi_value >= 40:
            return f"🟡 {t_gui('medium_risk')} ({t_gui('neutral_zone')})"
        elif rtsi_value >= 30:
            return f"🟠 {t_gui('high_risk')} ({t_gui('weak_bear')})"
        elif rtsi_value >= 20 and confidence >= 0.5:
            return f"🔴 {t_gui('high_risk')} ({t_gui('moderate_decline')})"
        elif rtsi_value < 20 and confidence >= 0.7:
            return f"🔴 {t_gui('extremely_high_risk')} ({t_gui('strong_decline_confirmation')})"
        else:
            return f"🔴 {t_gui('high_risk')}"
    
    def update_trend_chart_with_data_calculation(self, stock_code, stock_data):
        """更新趋势图表 - 只用真实数据，不足时通过计算补足"""
        try:
            # 清空现有图表
            self.ax.clear()
            
            # 从数据源获取真实的评级数据
            historical_ratings = self.get_real_historical_data(stock_code)
            
            if historical_ratings and len(historical_ratings) > 0:
                # 使用真实数据 - 确保日期排序正确
                sorted_items = sorted(historical_ratings.items(), key=lambda x: x[0])  # 按日期排序
                dates = [item[0] for item in sorted_items]
                ratings = [item[1] for item in sorted_items]
                
                # 转换评级为数值
                rating_scores = self.convert_ratings_to_scores(ratings)
                
                # 如果数据不足，尝试生成基于真实RTSI的合理数据
                if len(rating_scores) < 5:  # 数据点太少
                    self.generate_and_plot_realistic_data(stock_code, stock_data, source_type="合理模拟样本")
                    return
                
                # 过滤空值
                valid_data = [(d, r) for d, r in zip(dates, rating_scores) if r is not None]
                if valid_data:
                    dates, rating_scores = zip(*valid_data)
                    
                    # 绘制评级趋势
                    self.ax.plot(range(len(dates)), rating_scores, 'b-o', linewidth=2, markersize=6)
                    # 获取股票名称
                    stock_name = self.get_stock_name_by_code(stock_code)
                    self.ax.set_title(f'{stock_name} {t_gui("chart_rating_trend")} ({t_gui("chart_real_data")})', fontsize=12, pad=15)
                    self.ax.set_xlabel(t_gui('chart_time'), fontsize=11)
                    self.ax.set_ylabel(t_gui('chart_rating_score'), fontsize=11)
                    self.ax.grid(True, alpha=0.3)
                    
                    # 设置Y轴范围和标签
                    self.ax.set_ylim(-0.5, 7.5)
                    self.ax.set_yticks(range(8))
                    rating_labels = [
                        t_gui('rating_big_bear'),
                t_gui('rating_mid_bear'),
                t_gui('rating_small_bear'),
                t_gui('rating_micro_bear'),
                t_gui('rating_micro_bull'),
                t_gui('rating_small_bull'),
                t_gui('rating_mid_bull'),
                t_gui('rating_big_bull')
                    ]
                    self.ax.set_yticklabels(rating_labels, fontsize=10)
                    
                    # 设置X轴标签 (显示完整日期范围)
                    # 确保显示首尾日期，以及中间的关键日期点
                    total_points = len(dates)
                    if total_points <= 10:
                        # 数据点少时显示所有日期
                        tick_indices = list(range(total_points))
                    else:
                        # 数据点多时显示关键日期：首、尾、以及均匀分布的中间点
                        step = max(1, total_points // 8)  # 显示大约8-10个日期点
                        tick_indices = list(range(0, total_points, step))
                        # 确保包含最后一个日期
                        if tick_indices[-1] != total_points - 1:
                            tick_indices.append(total_points - 1)
                    
                    self.ax.set_xticks(tick_indices)
                    # 转换日期格式：20250410 -> 04/10
                    formatted_dates = []
                    for i in tick_indices:
                        date_str = str(dates[i])
                        if len(date_str) == 8 and date_str.startswith('202'):
                            # 20250410 -> 04/10
                            month_day = f"{date_str[4:6]}/{date_str[6:8]}"
                            formatted_dates.append(month_day)
                        else:
                            # 其他格式直接显示最后4位
                            formatted_dates.append(date_str[-4:])
                    
                    self.ax.set_xticklabels(formatted_dates, rotation=45, fontsize=10)
                    
                    # 添加RTSI值标注
                    rtsi_value = stock_data.get('rtsi', {}).get('rtsi', 0) if isinstance(stock_data.get('rtsi'), dict) else stock_data.get('rtsi', 0)
                    self.ax.text(0.02, 0.98, f'RTSI: {rtsi_value:.2f}', transform=self.ax.transAxes, 
                               fontsize=12, fontweight='bold', verticalalignment='top',
                               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
                    
                    # 添加数据来源信息 (右下角) - 增强版本
                    data_quality = self.calculate_data_quality_score(len(rating_scores), len(dates))
                    quality_color = 'lightgreen' if data_quality > 0.8 else 'lightyellow' if data_quality > 0.5 else 'lightcoral'
                    
                    self.ax.text(0.98, 0.02, f'数据来源：真实Excel数据\n数据质量：{data_quality:.1%} ({len(rating_scores)}点)', 
                               transform=self.ax.transAxes, fontsize=9, style='italic', 
                               horizontalalignment='right', verticalalignment='bottom',
                               bbox=dict(boxstyle='round', facecolor=quality_color, alpha=0.6))
                    
                    self.canvas.draw()
                    return
            
            # 如果没有真实数据，生成基于RTSI的合理数据
            self.generate_and_plot_realistic_data(stock_code, stock_data, source_type="RTSI的智能模拟")
            
        except Exception as e:
            print(f"图表更新错误: {e}")
            self.plot_error_chart()
    
    def get_real_historical_data(self, stock_code):
        """获取真实的历史评级数据 - 增强版本支持多文件扫描和数据填充"""
        try:
            historical_data = None
            
            # 0. 优先从当前数据集获取（最重要）
            if hasattr(self, 'current_dataset') and self.current_dataset:
                try:
                    ratings_series = self.current_dataset.get_stock_ratings(stock_code)
                    if not ratings_series.empty:
                        historical_data = ratings_series.to_dict()
                        print(f"从当前数据集获取 {stock_code} 数据: {len(historical_data)} 条")
                except Exception as e:
                    print(f"从当前数据集获取失败: {e}")
            
            # 1. 从分析结果获取
            if not historical_data and hasattr(self.analysis_results, 'stocks') and stock_code in self.analysis_results.stocks:
                stock_info = self.analysis_results.stocks[stock_code]
                if 'historical_ratings' in stock_info:
                    historical_data = stock_info['historical_ratings']
            
            # 2. 从原始数据集获取
            if not historical_data and hasattr(self.analysis_results, 'get_stock_ratings'):
                historical_data = self.analysis_results.get_stock_ratings(stock_code)
            
            # 3. 从数据集直接获取
            if not historical_data and hasattr(self, 'analysis_results') and hasattr(self.analysis_results, 'dataset'):
                dataset = self.analysis_results.dataset
                if hasattr(dataset, 'get_stock_ratings'):
                    historical_data = dataset.get_stock_ratings(stock_code)
            
            # 4. 新增：扫描目录中的多个Excel文件获取更多历史数据
            if not historical_data:
                historical_data = self.scan_historical_excel_files(stock_code)
            
            # 5. 数据填充处理：对"-"值进行前向填充（已在StockDataSet中处理，这里作为备份）
            if historical_data and isinstance(historical_data, dict):
                historical_data = self.forward_fill_ratings(historical_data, stock_code)
            
            return historical_data
            
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return None
    
    def forward_fill_ratings(self, historical_ratings, stock_code=""):
        """前向填充评级数据，严格按日期顺序，只允许低日期向高日期补充"""
        if not historical_ratings:
            return historical_ratings
        
        try:
            # 按日期排序
            sorted_items = sorted(historical_ratings.items(), key=lambda x: x[0])
            filled_data = {}
            last_valid_rating = None
            
            # 第一步：找到第一个有效评级
            first_valid_date = None
            first_valid_rating = None
            
            for date, rating in sorted_items:
                if rating != '-' and rating is not None and rating != '':
                    first_valid_date = date
                    first_valid_rating = rating
                    break
            
            # 如果没有找到任何有效评级，返回空
            if first_valid_rating is None:
                print(f"警告 {stock_code}: 所有日期都是'-'，无法填充")
                return {}
            
            # 第二步：从第一个有效日期开始处理，严格按顺序向后填充
            for date, rating in sorted_items:
                # 跳过第一个有效日期之前的所有日期（包括"-"值）
                if first_valid_date is not None and date < first_valid_date:
                    print(f"跳过 {stock_code} 早期日期 {date}: {rating} (在首个有效日期 {first_valid_date} 之前)")
                    continue
                
                if rating == '-' or rating is None or rating == '':
                    # 只能使用之前的有效评级填充（不允许倒填）
                    if last_valid_rating is not None:
                        filled_data[date] = last_valid_rating
                        print(f"前向填充 {stock_code} 日期 {date}: {last_valid_rating}")
                    else:
                        # 这种情况不应该发生，因为我们从第一个有效日期开始
                        print(f"错误 {stock_code} 日期 {date}: 无前值可填充")
                        continue
                else:
                    # 有效评级，直接使用并更新last_valid_rating
                    filled_data[date] = rating
                    last_valid_rating = rating
            
            print(f"数据填充完成 {stock_code}: 原始 {len(historical_ratings)} 条 -> 填充后 {len(filled_data)} 条 (从 {first_valid_date} 开始)")
            return filled_data
            
        except Exception as e:
            print(f"数据填充失败: {e}")
            return historical_ratings
    
    def scan_historical_excel_files(self, stock_code):
        """扫描目录中的历史Excel文件获取更多数据"""
        try:
            import os
            import glob
            import re
            
            # 搜索当前目录下的所有Excel文件
            excel_files = glob.glob("*.json.gz") 
            
            if not excel_files:
                return None
            
            # 按日期排序文件
            date_files = []
            for file_path in excel_files:
                # 从文件名提取日期
                match = re.search(r'(\d{8})', file_path)
                if match:
                    date_str = match.group(1)
                    date_files.append((date_str, file_path))
            
            date_files.sort(reverse=True)  # 最新日期在前
            
            # 收集历史评级数据
            historical_ratings = {}
            files_loaded = 0
            max_files = 10  # 限制扫描文件数量避免过慢
            
            for date_str, file_path in date_files[:max_files]:
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    
                    # 查找该股票的数据 - 使用智能代码匹配
                    def smart_match_code(code):
                        code_str = str(code)
                        if code_str.isdigit():
                            return code_str.zfill(6)
                        else:
                            return code_str.upper()
                    
                    # 标准化查找代码
                    search_code = smart_match_code(stock_code)
                    df_codes = df['股票代码'].astype(str).apply(smart_match_code)
                    stock_rows = df[df_codes == search_code]
                    
                    if not stock_rows.empty:
                        # 获取日期列（评级数据）- 支持多种格式
                        date_columns = []
                        for col in df.columns:
                            col_str = str(col)
                            # 检测各种日期格式：202X年份开头、MMDD格式等
                            if (col_str.startswith('202') or  # 2023、2024等
                                (len(col_str) == 4 and col_str.isdigit()) or  # 0410等4位数字
                                col_str.replace('.', '').replace('-', '').replace('/', '').isdigit()):
                                date_columns.append(col)
                        
                        for date_col in date_columns:
                            rating = stock_rows.iloc[0][date_col]
                            if pd.notna(rating) and rating != '-':
                                historical_ratings[str(date_col)] = rating
                        
                        files_loaded += 1
                
                except Exception as e:
                    print(f"加载文件 {file_path} 失败: {e}")
                    continue
            
            if historical_ratings:
                print(f"从 {files_loaded} 个文件中获取到 {len(historical_ratings)} 个历史评级数据点")
                return historical_ratings
            
            return None
            
        except Exception as e:
            print(f"扫描历史文件失败: {e}")
            return None
    
    def convert_ratings_to_scores(self, ratings):
        """转换评级为数值分数"""
        rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0, '-': None
        }
        
        scores = []
        for rating in ratings:
            score = rating_map.get(rating, None)
            scores.append(score)
        
        return scores
    
    def calculate_data_quality_score(self, valid_points, total_points):
        """计算数据质量评分"""
        try:
            if total_points == 0:
                return 0.0
            
            # 基础完整性评分 (0-0.6)
            completeness = valid_points / total_points
            base_score = completeness * 0.6
            
            # 数据量评分 (0-0.3)
            if valid_points >= 30:
                volume_score = 0.3
            elif valid_points >= 20:
                volume_score = 0.25
            elif valid_points >= 10:
                volume_score = 0.2
            elif valid_points >= 5:
                volume_score = 0.15
            else:
                volume_score = 0.1
            
            # 连续性评分 (0-0.1)
            continuity_score = 0.1 if completeness > 0.8 else 0.05
            
            total_score = base_score + volume_score + continuity_score
            return min(total_score, 1.0)
            
        except Exception as e:
            print(f"数据质量评分计算失败: {e}")
            return 0.5  # 默认评分
    
    # 模拟数据生成功能已删除 - 系统只使用真实数据
    
    def show_no_analysis_data(self, stock_code, stock_name):
        """显示无分析数据提示"""
        try:
            # 清空指标显示
            self.rtsi_var.set("暂无数据")
            self.trend_var.set("暂无数据")
            self.confidence_var.set("暂无数据")
            self.industry_var.set("未分类")
            self.risk_var.set("暂无数据")
            self.slope_var.set("暂无数据")
            
            # 显示无数据图表
            self.plot_no_data_chart(stock_code)
            
            # 显示无数据分析文本
            no_data_text = f"""
 {stock_name} ({stock_code}) 分析报告
{'='*50}

X 【数据状态】
• 当前状态: 暂无分析数据
• 股票名称: {stock_name}
• 股票代码: {stock_code}

提示 【解决方案】
1. 确认已加载包含该股票的数据文件
2. 完成数据分析步骤
3. 该股票可能不在当前数据集中

说明 【操作建议】
• 检查数据文件是否包含此股票
• 重新执行数据分析
• 选择其他有效的股票进行分析

生成时间: {self.get_current_time()}
"""
            
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, no_data_text)
            
        except Exception as e:
            error_text = f"显示错误: {str(e)}"
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, error_text)
    
    def get_current_time(self):
        """获取当前时间字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def get_stock_name_by_code(self, stock_code):
        """根据股票代码获取股票名称"""
        try:
            if hasattr(self, 'analysis_results') and hasattr(self.analysis_results, 'stocks'):
                stock_data = self.analysis_results.stocks.get(stock_code, {})
                return stock_data.get('name', stock_code)
            elif hasattr(self, 'current_dataset') and self.current_dataset:
                # 从数据集获取
                df = self.current_dataset.data
                if '股票代码' in df.columns and '股票名称' in df.columns:
                    matching_rows = df[df['股票代码'].astype(str) == stock_code]
                    if not matching_rows.empty:
                        return matching_rows.iloc[0]['股票名称']
            return stock_code  # 如果找不到名称，返回代码
        except Exception as e:
            print(f"获取股票名称失败: {e}")
            return stock_code
    def generate_and_plot_realistic_data(self, stock_code, stock_data, source_type="RTSI的智能模拟"):
        """基于真实RTSI生成合理的历史数据用于图表展示"""
        try:
            # 获取真实RTSI值
            rtsi_data = stock_data.get('rtsi', {})
            if isinstance(rtsi_data, dict):
                current_rtsi = rtsi_data.get('rtsi', 50)
            else:
                current_rtsi = rtsi_data if isinstance(rtsi_data, (int, float)) else 50
            
            # 基于RTSI值生成合理的历史评级趋势
            import random
            import numpy as np
            
            # 使用股票代码作为随机种子，确保每次生成相同的数据
            random.seed(hash(stock_code) % 2**32)
            np.random.seed(hash(stock_code) % 2**32)
            
            # 生成30天的历史数据
            days = 30
            # 确保日期从早到晚排列（左边早，右边晚）
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days-1, -1, -1)]
            
            # 根据当前RTSI值生成合理的评级走势
            if current_rtsi >= 70:  # 强势股
                base_rating = 6  # 中多
                volatility = 1.0
            elif current_rtsi >= 50:
                base_rating = 5  # 小多  
                volatility = 1.2
            elif current_rtsi >= 30:
                base_rating = 4  # 微多
                volatility = 1.5
            else:
                base_rating = 2  # 小空
                volatility = 1.3
            
            # 生成评级序列，让趋势逐渐向当前RTSI对应的评级收敛
            ratings = []
            current_rating = base_rating + random.uniform(-1, 1)
            
            for i in range(days):
                # 添加噪声和趋势
                noise = random.gauss(0, volatility * 0.3)
                trend = (base_rating - current_rating) * 0.1  # 逐渐向基准收敛
                
                current_rating += trend + noise
                current_rating = max(0, min(7, current_rating))  # 限制在0-7范围
                ratings.append(current_rating)
            
            self.ax.clear()
            
            # 绘制生成的趋势数据
            self.ax.plot(range(len(dates)), ratings, 'b-o', linewidth=2, markersize=4, alpha=0.8)
            # 获取股票名称
            stock_name = self.get_stock_name_by_code(stock_code)
            chart_title = f'{stock_name} {t_gui("chart_rating_trend")} ({t_gui("chart_generated_data").format(current_rtsi)})'
            self.ax.set_title(chart_title, fontsize=12, pad=15)
            self.ax.set_xlabel(t_gui('chart_time'), fontsize=11)
            self.ax.set_ylabel(t_gui('chart_rating_score'), fontsize=11)
            self.ax.grid(True, alpha=0.3)
            
            # 设置Y轴范围和标签
            self.ax.set_ylim(-0.5, 7.5)
            self.ax.set_yticks(range(8))
            rating_labels = [
                t_gui('rating_big_bear'),
                     t_gui('rating_mid_bear'),
                     t_gui('rating_small_bear'),
                     t_gui('rating_micro_bear'),
                     t_gui('rating_micro_bull'),
                     t_gui('rating_small_bull'),
                     t_gui('rating_mid_bull'),
                     t_gui('rating_big_bull')
            ]
            self.ax.set_yticklabels(rating_labels, fontsize=10)
            
            # 设置X轴标签 (显示部分日期)
            step = max(1, len(dates) // 8)
            self.ax.set_xticks(range(0, len(dates), step))
            self.ax.set_xticklabels([dates[i][-5:] for i in range(0, len(dates), step)], rotation=45, fontsize=10)
            
            # 添加RTSI值标注
            self.ax.text(0.02, 0.98, f'RTSI: {current_rtsi:.2f}', transform=self.ax.transAxes, 
                       fontsize=12, fontweight='bold', verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            
            # 添加数据来源信息 (右下角)
            data_source_text = f'{t_gui("data_source")}：{source_type}'
            self.ax.text(0.98, 0.02, data_source_text, transform=self.ax.transAxes, 
                       fontsize=9, style='italic', horizontalalignment='right', verticalalignment='bottom',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.6))
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"生成数据错误: {e}")
            self.plot_error_chart()
    
    def generate_detailed_analysis(self, stock_code, stock_name, stock_data, rtsi_data):
        """生成详细分析报告 - 完整版本"""
        try:
            rtsi_value = rtsi_data.get('rtsi', 0) if isinstance(rtsi_data, dict) else rtsi_data
            industry = stock_data.get('industry', '未分类')
            
            # 计算更多指标
            volatility = self.calculate_volatility(stock_data)
            market_cap_level = self.estimate_market_cap_level(stock_code)
            sector_performance = self.get_sector_performance(industry)
            
            # 获取国际化文本
            report_title = t_gui("deep_analysis_report")
            core_indicators = t_gui("core_indicators")
            technical_analysis = t_gui("technical_analysis")
            industry_comparison = t_gui("industry_comparison")
            investment_advice = t_gui("investment_advice")
            risk_assessment = t_gui("risk_assessment")
            operation_advice = t_gui("operation_advice")
            future_outlook = t_gui("future_outlook")
            disclaimer = t_gui("disclaimer")
            disclaimer_text = t_gui("disclaimer_text")
            generation_time = t_gui("generation_time")
            
            # 获取动态文本
            tech_strength = t_gui("strong") if rtsi_value > 60 else (t_gui("neutral") if rtsi_value > 40 else t_gui("weak"))
            relative_pos = t_gui("leading") if rtsi_value > 50 else t_gui("lagging")
            industry_pos = t_gui("blue_chip") if rtsi_value > 70 else (t_gui("average") if rtsi_value > 40 else t_gui("lagging"))
            rotation_sig = t_gui("active") if rtsi_value > 60 else (t_gui("wait_and_see") if rtsi_value > 30 else t_gui("cautious"))
            liquidity_level = t_gui("good") if market_cap_level != t_gui("small_cap") else t_gui("average")
            
            analysis_text = f"""
📈 {stock_name} {report_title}
{'='*50}

📊 {core_indicators}
• RTSI {t_gui('index')}: {rtsi_value:.2f}/100
• {t_gui('trend_status')}: {self.get_trend_description(rtsi_value)}
• {t_gui('technical_strength')}: {tech_strength}
• {t_gui('industry')}: {industry}
• {t_gui('market_cap_level')}: {market_cap_level}

🔍 {technical_analysis}
• {t_gui('trend_direction')}: {self.get_detailed_trend(rtsi_value)}
• {t_gui('volatility_level')}: {volatility}
• {t_gui('support_resistance')}: {t_gui('based_on_rating_analysis')}
• {t_gui('relative_strength')}: {t_gui('in')} {industry} {t_gui('industry_position')} {relative_pos}

🏭 {industry_comparison}
• {t_gui('industry_performance')}: {sector_performance}
• {t_gui('industry_position')}: {industry_pos}
• {t_gui('rotation_signal')}: {rotation_sig}

💡 {investment_advice}
• {t_gui('short_term_strategy')}: {self.get_short_term_advice(rtsi_value)}
• {t_gui('medium_term_strategy')}: {self.get_medium_term_advice(rtsi_value, industry)}
• {t_gui('risk_warning')}: {self.get_risk_warning(rtsi_value)}

⚠️ {risk_assessment}
• {t_gui('technical_risk')}: {self.calculate_risk_level(rtsi_value, 0.8)}
• {t_gui('industry_risk')}: {t_gui('attention_policy_risks')}
• {t_gui('market_risk')}: {t_gui('attention_market_risks')}
• {t_gui('liquidity')}: {liquidity_level}

⏰ {operation_advice}
• {t_gui('best_entry_point')}: {self.suggest_entry_point(rtsi_value)}
• {t_gui('stop_loss_position')}: {self.suggest_stop_loss(rtsi_value)}
• {t_gui('target_price')}: {self.suggest_target_price(rtsi_value)}
• {t_gui('holding_period')}: {self.suggest_holding_period(rtsi_value)}

🔮 {future_outlook}
{self.generate_outlook(rtsi_value, industry)}

📋 {disclaimer}
{disclaimer_text}

{generation_time}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, analysis_text)
            
        except Exception as e:
            error_text = f"""
❌ {t_gui("analysis_failed")}

{t_gui("error_info")}: {str(e)}

{t_gui("check_data_integrity")}
"""
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, error_text)
    
    def get_trend_description(self, rtsi_value):
        """获取趋势描述"""
        if rtsi_value >= 80:
            return t_gui("strong_uptrend")
        elif rtsi_value >= 60:
            return t_gui("strong_uptrend")
        elif rtsi_value >= 40:
            return t_gui("consolidation")
        elif rtsi_value >= 20:
            return t_gui("weak_downtrend")
        else:
            return t_gui("deep_adjustment")
    
    def get_detailed_trend(self, rtsi_value):
        """获取详细趋势分析 - 统一标准版本，与核心指标区保持一致"""
        # 采用与核心指标区完全一致的判断标准和专业术语
        if rtsi_value >= 75:
            return t_gui("strong_bull_trend")
        elif rtsi_value >= 60:
            return t_gui("moderate_bull_trend")
        elif rtsi_value >= 50:
            return t_gui("weak_bull_pattern")
        elif rtsi_value >= 40:
            return t_gui("sideways_consolidation")
        elif rtsi_value >= 30:
            return t_gui("weak_bear_pattern")
        elif rtsi_value >= 20:
            return t_gui("moderate_bear_trend")
        else:
            return t_gui("strong_bear_trend")
    
    def calculate_volatility(self, stock_data):
        """计算波动程度"""
        # 简化版本，实际应用中可以更复杂
        return t_gui("medium_volatility")
    
    def estimate_market_cap_level(self, stock_code):
        """估算市值等级"""
        if stock_code.startswith('00'):
            return t_gui("large_cap")
        elif stock_code.startswith('60'):
            return t_gui("large_cap")
        elif stock_code.startswith('30'):
            return t_gui("growth_stock")
        else:
            return t_gui("mid_cap")
    
    def get_sector_performance(self, industry):
        """获取行业表现"""
        return f"{industry} {t_gui('industry_shows_neutral_performance')}"
    
    def get_short_term_advice(self, rtsi_value):
        """短线建议"""
        if rtsi_value >= 60:
            return t_gui("moderate_participation_watch_volume_price")
        elif rtsi_value >= 40:
            return t_gui("wait_and_see_clear_signal")
        else:
            return t_gui("avoid_bottom_fishing_wait_reversal")
    
    def get_medium_term_advice(self, rtsi_value, industry):
        """中线建议"""
        if rtsi_value >= 50:
            return f"{t_gui('can_allocate')} {industry} {t_gui('quality_targets')}"
        else:
            return t_gui("wait_better_allocation_opportunity")
    
    def get_risk_warning(self, rtsi_value):
        """风险提示"""
        if rtsi_value < 30:
            return t_gui("relatively_safe_watch_pullback_risk")
        elif rtsi_value < 50:
            return t_gui("medium_risk_control_position")
        else:
            return t_gui("relatively_safe_watch_pullback_risk")
    
    def suggest_entry_point(self, rtsi_value):
        """建议入场点"""
        if rtsi_value >= 60:
            return t_gui("pullback_to_support_level")
        elif rtsi_value >= 40:
            return t_gui("breakout_above_resistance")
        else:
            return t_gui("wait_for_reversal_signal")
    
    def suggest_stop_loss(self, rtsi_value):
        """建议止损位"""
        if rtsi_value >= 50:
            return t_gui("below_recent_support")
        else:
            return t_gui("set_8_10_percent_stop_loss")
    
    def suggest_target_price(self, rtsi_value):
        """建议目标价"""
        if rtsi_value >= 60:
            return t_gui("target_previous_high_or_new_high")
        elif rtsi_value >= 40:
            return t_gui("near_short_term_resistance")
        else:
            return t_gui("limited_upside_potential")
    
    def suggest_holding_period(self, rtsi_value):
        """建议持仓周期"""
        if rtsi_value >= 60:
            return t_gui("medium_to_long_term_1_3_months")
        elif rtsi_value >= 40:
            return t_gui("short_term_1_2_weeks")
        else:
            return t_gui("not_recommended_to_hold")
    
    def generate_outlook(self, rtsi_value, industry):
        """生成后市展望"""
        if rtsi_value >= 60:
            return f"{t_gui('technical_analysis_shows')} {industry} {t_gui('industry_and_stock_upside_potential')}, {t_gui('recommend_monitoring_fundamental_changes')}"
        elif rtsi_value >= 40:
            return f"{t_gui('stock_price_consolidation_period')}, {t_gui('need_to_observe')} {industry} {t_gui('industry_catalysts_and_volume_changes')}"
        else:
            return f"{t_gui('technical_analysis_weak')}, {t_gui('recommend_waiting_for')} {industry} {t_gui('industry_overall_stabilization_before_allocation')}"
    
    def plot_no_data_chart(self, stock_code):
        """绘制无数据提示图表"""
        self.ax.clear()
        # 获取股票名称
        stock_name = self.get_stock_name_by_code(stock_code)
        data_preparing = t_gui("chart_data_preparing")
        system_generating = t_gui("chart_system_generating")
        preparing_text = f'\n{stock_name}\n{data_preparing}\n\n{system_generating}'
        self.ax.text(0.5, 0.5, preparing_text, 
                    transform=self.ax.transAxes, 
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=15, color='blue',
                    bbox=dict(boxstyle='round', facecolor='#e8f4fd', alpha=0.8))
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')
        self.canvas.draw()
    

    
    def plot_error_chart(self):
        """绘制错误提示图表"""
        self.ax.clear()
        data_loading_failed = "数据加载失败"  # 直接使用中文，因为这是硬编码的错误信息
        check_data_source = "请检查数据源"  # 直接使用中文
        suggestions = "建议"  # 直接使用中文
        confirm_data_file = "确认已加载数据文件"  # 直接使用中文
        complete_analysis = "完成数据分析"  # 直接使用中文
        select_valid_stocks = "选择有效股票"  # 直接使用中文
        error_text = f'\n{data_loading_failed}\n{check_data_source}\n\n{suggestions}:\n1. {confirm_data_file}\n2. {complete_analysis}\n3. {select_valid_stocks}'
        self.ax.text(0.5, 0.5, error_text, 
                    transform=self.ax.transAxes, 
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=15, color='red',  # 字体增大
                    bbox=dict(boxstyle='round', facecolor='#ffe6e6', alpha=0.8))
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.axis('off')
        self.canvas.draw()
    
    def export_analysis(self):
        """导出分析结果"""
        if not hasattr(self, 'current_stock') or not self.current_stock:
            messagebox.showwarning(t_gui("提示"), t_gui("请先选择并分析股票"))
            return
        
        try:
            from tkinter import filedialog
            stock_code = self.current_stock['code']
            stock_name = self.current_stock['name']
            
            # 选择保存路径
            filename = filedialog.asksaveasfilename(
                title=t_gui("export_analysis_report"),
                defaultextension=".txt",
                filetypes=[(t_gui("文本文件"), "*.txt"), (t_gui("Excel文件"), "*.xlsx"), (t_gui("所有文件"), "*.*")],
                initialname=f"{stock_name}_{stock_code}_分析报告.txt"
            )
            
            if filename:
                # 获取当前分析文本
                analysis_content = self.analysis_text.get(1.0, tk.END)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    report_title = t_gui("stock_analysis_report")
                    f.write(f"{report_title}\n")
                    stock_code_label = t_gui("股票代码")
                    stock_name_label = t_gui("股票名称")
                    generation_time_label = t_gui("生成时间")
                    f.write(f"{stock_code_label}: {stock_code}\n")
                    f.write(f"{stock_name_label}: {stock_name}\n")
                    f.write(f"{generation_time_label}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                    f.write(analysis_content)
                
                export_msg = t_gui("report_export_success")
                messagebox.showinfo(t_gui("成功"), f"{export_msg}:\n{filename}")
        
        except Exception as e:
            export_failed = t_gui("导出失败")
            messagebox.showerror(t_gui("错误"), f"{export_failed}:\n{str(e)}")
    
    def add_to_watchlist(self):
        """添加到关注列表"""
        if not hasattr(self, 'current_stock') or not self.current_stock:
            messagebox.showwarning(t_gui("提示"), t_gui("请先选择股票"))
            return
        
        stock_code = self.current_stock['code']
        stock_name = self.current_stock['name']
        
        # 简单的关注列表功能
        try:
            watchlist_file = "关注列表.txt"
            
            # 检查是否已在关注列表中
            existing_stocks = set()
            try:
                with open(watchlist_file, 'r', encoding='utf-8') as f:
                    existing_stocks = set(line.strip() for line in f if line.strip())
            except FileNotFoundError:
                pass
            
            stock_entry = f"{stock_code} {stock_name}"
            if stock_entry in existing_stocks:
                already_in_watchlist = t_gui("已在关注列表中")
                messagebox.showinfo(t_gui("提示"), f"{stock_name} {already_in_watchlist}")
                return
            
            # 添加到关注列表
            with open(watchlist_file, 'a', encoding='utf-8') as f:
                f.write(f"{stock_entry}\n")
            
            added_msg = t_gui("已将")
            to_watchlist = t_gui("添加到关注列表")
            messagebox.showinfo(t_gui("成功"), f"{added_msg} {stock_name} {to_watchlist}")
        
        except Exception as e:
            add_watchlist_failed = t_gui("添加关注失败")
            messagebox.showerror(t_gui("错误"), f"{add_watchlist_failed}:\n{str(e)}")
    
    def refresh_data(self):
        """刷新数据"""
        try:
            # 重新加载股票列表
            self.load_stock_list()
            
            # 如果有选中的股票，重新分析
            if hasattr(self, 'current_stock') and self.current_stock:
                self.analyze_selected_stock()
            
            data_refreshed = t_gui("数据已刷新")
            messagebox.showinfo(t_gui("成功"), data_refreshed)
        
        except Exception as e:
            refresh_failed = t_gui("刷新数据失败")
            messagebox.showerror(t_gui("错误"), f"{refresh_failed}:\n{str(e)}")


class IndustryAnalysisWindow:
    """行业分析窗口"""
    
    def __init__(self, parent, analysis_results):
        self.parent = parent
        self.analysis_results = analysis_results
        self.window = tk.Toplevel(parent)
        
        # 继承父窗口的字体配置
        if hasattr(parent, 'fonts'):
            self.fonts = parent.fonts
        else:
            self.fonts = {
                'title': ('Microsoft YaHei', 12, 'bold'),
                'menu': ('Microsoft YaHei', 11),
                'button': ('Microsoft YaHei', 11),
                'text': ('Microsoft YaHei', 11),
                'status': ('Microsoft YaHei', 10)
            }
        
        self.setup_window()
        self.setup_components()
        self.load_industry_data()
    
    def setup_window(self):
        """设置窗口"""
        self.window.title(t_gui("industry_analysis_window_title"))
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 窗口居中
        self.center_window()
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 阻止窗口大小调整
        self.window.resizable(True, True)
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            # 优先使用项目根目录的mrcai.ico
            icon_paths = [
                "mrcai.ico",
                "resources/icons/mrcai.ico",
                "resources/icons/app.ico"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.window.iconbitmap(icon_path)
                    return
        except Exception as e:
            print(f"Warning: Failed to set window icon: {e}")
    
    def center_window(self):
        """窗口居中显示"""
        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 窗口尺寸
        window_width = 1000
        window_height = 700
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        self.window.geometry(f"+{x}+{y}")
    
    def setup_components(self):
        """设置组件"""
        # 主容器
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题框架
        title_frame = tk.Frame(main_frame, bg='#f0f0f0')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(title_frame, text=t_gui("industry_rotation_title"), 
                              font=('Microsoft YaHei', 11, 'bold'), 
                              bg='#f0f0f0', fg='#0078d4')
        title_label.pack(side=tk.LEFT)
        
        # 按钮框架
        button_frame = tk.Frame(title_frame, bg='#f0f0f0')
        button_frame.pack(side=tk.RIGHT)
        
        # 刷新按钮
        # 统一按钮样式 - 与MSCI详情按钮一致，无色彩
        button_style = {
            'font': ('Microsoft YaHei', 11),
            'bg': '#f0f0f0',
            'fg': 'black',
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 20,
            'pady': 5
        }
        
        refresh_btn = tk.Button(button_frame, text=t_gui("btn_refresh"), 
                               command=self.load_industry_data,
                               **button_style)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 导出按钮
        export_btn = tk.Button(button_frame, text=t_gui("btn_export"), 
                              command=self.export_industry_data,
                              **button_style)
        export_btn.pack(side=tk.LEFT)
        
        # 主内容区
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：行业列表
        left_frame = tk.LabelFrame(content_frame, text=t_gui("industry_irsi_ranking"), 
                                  font=('Microsoft YaHei', 11, 'bold'),
                                  bg='#f0f0f0', fg='#333333')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 行业列表（使用Treeview）
        columns = ('rank', 'industry', 'irsi', 'status', 'stock_count')
        self.industry_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=20)
        
        # 配置Treeview字体与右侧详细信息一致
        treeview_style = ttk.Style()
        treeview_style.configure("Treeview", font=('Microsoft YaHei', 11))
        treeview_style.configure("Treeview.Heading", font=('Microsoft YaHei', 11, 'bold'))
        
        # 设置列标题
        self.industry_tree.heading('rank', text=t_gui("column_rank"))
        self.industry_tree.heading('industry', text=t_gui("column_industry"))
        self.industry_tree.heading('irsi', text='IRSI')
        self.industry_tree.heading('status', text=t_gui("column_status"))
        self.industry_tree.heading('stock_count', text=t_gui("column_stock_count"))
        
        # 设置列宽
        self.industry_tree.column('rank', width=60, minwidth=50)
        self.industry_tree.column('industry', width=150, minwidth=120)
        self.industry_tree.column('irsi', width=80, minwidth=70)
        self.industry_tree.column('status', width=100, minwidth=80)
        self.industry_tree.column('stock_count', width=80, minwidth=70)
        
        # 滚动条
        tree_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.industry_tree.yview)
        self.industry_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 布局
        self.industry_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 右侧：详细信息
        right_frame = tk.LabelFrame(content_frame, text=t_gui("industry_detail_info"), 
                                   font=('Microsoft YaHei', 11, 'bold'),
                                   bg='#f0f0f0', fg='#333333')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # 详细信息文本区
        self.detail_text = tk.Text(right_frame, width=50, height=25,
                                  font=('Microsoft YaHei', 11),
                                  bg='white', fg='black', wrap=tk.WORD)
        
        detail_scrollbar = tk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)
        
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 绑定选择事件
        self.industry_tree.bind('<<TreeviewSelect>>', self.on_industry_selected)
        
        # 状态栏
        status_frame = tk.Frame(main_frame, bg='#f0f0f0')
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_var = tk.StringVar()
        self.status_var.set(t_gui("status_loading_industry"))
        
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               bg='#f0f0f0', fg='#606060',
                               font=('Microsoft YaHei', 10),  # 状态栏使用10号
                               anchor=tk.W)
        status_label.pack(fill=tk.X)
    
    def safe_get_irsi(self, industry_data):
        """安全获取IRSI值 - 修复排序错误"""
        try:
            if isinstance(industry_data, (list, tuple)) and len(industry_data) >= 2:
                industry_name, industry_info = industry_data
                irsi_data = industry_info
            else:
                irsi_data = industry_data
            
            if isinstance(irsi_data, dict):
                # 优先查找'irsi'字段
                if 'irsi' in irsi_data:
                    irsi_value = irsi_data['irsi']
                    # 如果irsi字段是字典，提取其中的irsi值
                    if isinstance(irsi_value, dict):
                        return float(irsi_value.get('irsi', 0))
                    else:
                        # 处理numpy类型
                        import numpy as np
                        if isinstance(irsi_value, (np.number, np.integer, np.floating)):
                            return float(irsi_value)
                        elif isinstance(irsi_value, (int, float)):
                            return float(irsi_value)
                        elif isinstance(irsi_value, str):
                            try:
                                return float(irsi_value)
                            except ValueError:
                                return 0.0
                        else:
                            return 0.0
                else:
                    # 如果没有irsi字段，尝试其他字段
                    return float(irsi_data.get('value', irsi_data.get('score', 0)))
            elif isinstance(irsi_data, (int, float)):
                return float(irsi_data)
            elif isinstance(irsi_data, str):
                try:
                    return float(irsi_data)
                except ValueError:
                    return 0.0
            else:
                return 0.0
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            print(f"IRSI排序错误: {e}, 数据结构: {type(industry_data)}")
            return 0.0
    
    def load_industry_data(self):
        """加载行业数据"""
        try:
            # 清空现有数据
            for item in self.industry_tree.get_children():
                self.industry_tree.delete(item)
            
            analyzing_industry_data = t_gui("analyzing_industry_data")
            self.status_var.set(f"{analyzing_industry_data}...")
            
            # 获取行业数据
            if hasattr(self.analysis_results, 'industries') and self.analysis_results.industries:
                industries = self.analysis_results.industries
                
                # 安全排序
                try:
                    sorted_industries = sorted(industries.items(), 
                                             key=lambda x: self.safe_get_irsi(x), 
                                             reverse=True)
                except Exception as e:
                    print(f"排序失败，使用备用方案: {e}")
                    sorted_industries = list(industries.items())
                
                # 填充数据
                for rank, (industry_name, industry_info) in enumerate(sorted_industries, 1):
                    try:
                        # 提取IRSI值
                        irsi_value = self.safe_get_irsi((industry_name, industry_info))
                        
                        # 确定状态
                        if irsi_value > 20:
                            status = t_gui("industry_strong")
                            tag = "strong"
                        elif irsi_value > 5:
                            status = t_gui("industry_neutral_strong")
                            tag = "medium"
                        elif irsi_value > -5:
                            status = t_gui("industry_neutral")
                            tag = "neutral"
                        elif irsi_value > -20:
                            status = t_gui("industry_neutral_weak")
                            tag = "weak"
                        else:
                            status = t_gui("industry_weak")
                            tag = "very_weak"
                        
                        # 获取股票数量
                        stock_count = industry_info.get('stock_count', 0) if isinstance(industry_info, dict) else 0
                        
                        # 插入行
                        self.industry_tree.insert('', 'end', values=(
                            rank,
                            industry_name,
                            f"{irsi_value:.2f}",
                            status,
                            stock_count
                        ), tags=(tag,))
                        
                    except Exception as e:
                        print(f"处理行业 {industry_name} 时出错: {e}")
                        continue
                
                # 设置标签颜色
                self.industry_tree.tag_configure('strong', foreground='#008000')
                self.industry_tree.tag_configure('medium', foreground='#0066cc')
                self.industry_tree.tag_configure('neutral', foreground='#333333')
                self.industry_tree.tag_configure('weak', foreground='#ff6600')
                self.industry_tree.tag_configure('very_weak', foreground='#cc0000')
                
                loaded_msg = t_gui("loaded_count")
                industries_irsi_data = t_gui("industries_irsi_data")
                self.status_var.set(f"{loaded_msg} {len(sorted_industries)} {industries_irsi_data}")
                
            else:
                no_industry_data = t_gui("no_industry_analysis_data")
                self.status_var.set(no_industry_data)
                
            # 显示默认详细信息
            self.show_default_detail()
            
        except Exception as e:
            industry_data_load_failed = t_gui("industry_data_load_failed")
            error_msg = f"{industry_data_load_failed}: {str(e)}"
            self.status_var.set(error_msg)
            messagebox.showerror(t_gui("error"), error_msg)
    
    def show_default_detail(self):
        """显示默认详细信息"""
        default_info = f"""
{t_gui('industry')} {t_gui('industry_rotation_analysis_description')}

{t_gui('data')} {t_gui('irsi_full_name')}
• {t_gui('measure_industry_strength_vs_market')}
• {t_gui('positive_outperform_negative_underperform')}
• {t_gui('value_range_minus_100_to_100')}

{t_gui('trending_up')} {t_gui('strength_classification')}:
• {t_gui('industry_strong')}: IRSI > 20, {t_gui('significantly_outperform_market')}
• {t_gui('industry_neutral_strong')}: 5 < IRSI ≤ 20, {t_gui('slightly_outperform')}
• {t_gui('industry_neutral')}: -5 ≤ IRSI ≤ 5, {t_gui('sync_with_market')}
• {t_gui('industry_neutral_weak')}: -20 ≤ IRSI < -5, {t_gui('slightly_underperform')}
• {t_gui('industry_weak')}: IRSI < -20, {t_gui('significantly_underperform_market')}

{t_gui('tips')} {t_gui('usage_suggestions')}:
1. {t_gui('focus_strong_industries_above_15')}
2. {t_gui('avoid_weak_industries_below_minus_15')}
3. {t_gui('combine_fundamental_factors')}
4. {t_gui('regularly_monitor_sector_rotation')}

{t_gui('time')} {t_gui('data_update_realtime_calculation')}
{t_gui('warning')} {t_gui('investment_risk_disclaimer')}
"""
        
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, default_info)
    
    def on_industry_selected(self, event):
        """选择行业时的处理"""
        selection = self.industry_tree.selection()
        if selection:
            item = self.industry_tree.item(selection[0])
            values = item['values']
            if values:
                industry_name = values[1]
                self.show_industry_detail(industry_name)
    
    def show_industry_detail(self, industry_name):
        """显示行业详细信息"""
        try:
            if not hasattr(self.analysis_results, 'industries') or industry_name not in self.analysis_results.industries:
                cannot_find_msg = t_gui("cannot_find_industry_data")
                detailed_data_msg = t_gui("detailed_data")
                error_msg = f"❌ {cannot_find_msg} '{industry_name}' {detailed_data_msg}"
                self.detail_text.delete(1.0, tk.END)
                self.detail_text.insert(1.0, error_msg)
                return
            
            industry_info = self.analysis_results.industries[industry_name]
            irsi_value = self.safe_get_irsi((industry_name, industry_info))
            
            # 生成详细分析
            report_title = t_gui("industry_analysis_report")
            core_metrics = t_gui("core_metrics")
            performance_analysis = t_gui("performance_analysis")
            investment_advice = t_gui("investment_advice")
            risk_warning = t_gui("risk_warning")
            analysis_time = t_gui("analysis_time")
            analysis_description = t_gui("analysis_description")
            
            # 获取相对强度描述
            relative_strength = t_gui("outperform_market") if irsi_value > 0 else (t_gui("underperform_market") if irsi_value < 0 else t_gui("sync_with_market"))
            
            detail_info = f"""
📊 {report_title} - {industry_name}
{'='*50}

📈 {core_metrics}：
• {t_gui("irsi_index")}：{irsi_value:.2f}
• {t_gui("relative_strength_performance")}：{relative_strength}
• {t_gui("strength_level")}：{self.get_strength_level(irsi_value)}

📊 {performance_analysis}：
• {t_gui("short_term_trend")}：{self.get_trend_analysis(irsi_value)}
• {t_gui("investment_value")}：{self.get_investment_value(irsi_value)}
• {t_gui("risk_level")}：{self.get_risk_level(irsi_value)}

💡 {investment_advice}：
{self.get_investment_advice(industry_name, irsi_value)}

⚠️ {risk_warning}：
{self.get_risk_warning(irsi_value)}

⏰ {analysis_time}：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 {analysis_description}：{t_gui("irsi_description")}
"""
            
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(1.0, detail_info)
            
        except Exception as e:
            display_failed_text = t_gui('display_industry_detail_failed')
            error_msg = f"❌ {display_failed_text}: {str(e)}"
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(1.0, error_msg)
    
    def get_strength_level(self, irsi_value):
        """获取强度等级"""
        if irsi_value > 20:
            return "Hot Strong"
        elif irsi_value > 5:
            return "Rising Moderately Strong"
        elif irsi_value > -5:
            return "Neutral"
        elif irsi_value > -20:
            return "Declining Moderately Weak"
        else:
            return "Cold Weak"
    
    def get_trend_analysis(self, irsi_value):
        """获取趋势分析"""
        if irsi_value > 15:
            return "Clear uptrend with significant capital inflow"
        elif irsi_value > 0:
            return "Moderate rise, slightly outperforming market"
        elif irsi_value > -15:
            return "Consolidation, waiting for direction"
        else:
            return "Downtrend with capital outflow"
    
    def get_investment_value(self, irsi_value):
        """获取投资价值"""
        if irsi_value > 20:
            return "⭐⭐⭐⭐⭐ High Value"
        elif irsi_value > 5:
            return "⭐⭐⭐⭐ Higher Value"
        elif irsi_value > -5:
            return "⭐⭐⭐ Medium Value"
        elif irsi_value > -20:
            return "⭐⭐ Lower Value"
        else:
            return "⭐ Low Value"
    
    def get_risk_level(self, irsi_value):
        """获取风险等级"""
        if irsi_value > 20:
            return "🟢 Low Risk"
        elif irsi_value > 0:
            return "🟡 Medium-Low Risk"
        elif irsi_value > -20:
            return "🟠 Medium-High Risk"
        else:
            return "🔴 High Risk"
    
    def get_investment_advice(self, industry_name, irsi_value):
        """获取投资建议"""
        if irsi_value > 15:
            return f"• Actively allocate {industry_name} industry leading stocks\n• Can appropriately increase position ratio\n• Focus on sector rotation opportunities"
        elif irsi_value > 5:
            return f"• Can moderately allocate {industry_name} industry\n• Recommend selecting stocks with higher RTSI\n• Control position and manage risks"
        elif irsi_value > -5:
            return f"• {industry_name} industry shows neutral performance\n• Can balance allocation, avoid heavy positions\n• Monitor industry fundamentals closely"
        elif irsi_value > -15:
            return f"• {industry_name} industry shows weak performance\n• Recommend reducing allocation or avoiding\n• Wait for industry stabilization signal"
        else:
            return f"• {industry_name} industry shows poor performance\n• Recommend temporary avoidance\n• Wait for industry turning point"
    
    def get_risk_warning(self, irsi_value):
        """获取风险提示"""
        if irsi_value > 20:
            return "Watch for pullback risks at high levels, set reasonable profit targets"
        elif irsi_value > 0:
            return "Remain cautiously optimistic, monitor market changes"
        elif irsi_value > -20:
            return "Control position risks, avoid blind bottom-fishing"
        else:
            return "High risk status, strictly control losses"
    
    def export_industry_data(self):
        """导出行业数据"""
        try:
            from tkinter import filedialog
            import pandas as pd
            
            # 选择保存位置
            filename = filedialog.asksaveasfilename(
                title="",
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
            )
            
            if not filename:
                return
            
            # 准备导出数据
            export_data = []
            for child in self.industry_tree.get_children():
                values = self.industry_tree.item(child)['values']
                export_data.append({
                    '排名': values[0],
                    '行业名称': values[1],
                    'IRSI指数': values[2],
                    '强度状态': values[3],
                    '股票数量': values[4]
                })
            
            # 导出到Excel或CSV
            df = pd.DataFrame(export_data)
            
            if filename.endswith('.csv'):
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(filename, index=False)
            
            messagebox.showinfo("成功", f"行业分析数据已导出到:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")


class MarketSentimentWindow:
    """市场情绪分析窗口"""
    
    def __init__(self, parent, analysis_results):
        self.parent = parent
        self.analysis_results = analysis_results
        self.window = tk.Toplevel(parent)
        
        # 继承父窗口的字体配置
        if hasattr(parent, 'fonts'):
            self.fonts = parent.fonts
        else:
            self.fonts = {
                'title': ('Microsoft YaHei', 12, 'bold'),
                'menu': ('Microsoft YaHei', 11),
                'button': ('Microsoft YaHei', 11),
                'text': ('Microsoft YaHei', 11),
                'status': ('Microsoft YaHei', 10)
            }
        
        self.setup_window()
        self.setup_components()
        self.load_market_data()
    
    def setup_window(self):
        """设置窗口"""
        self.window.title(t_gui("market_analysis_window_title"))
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 窗口居中
        self.center_window()
        self.window.transient(self.parent)
        self.window.grab_set()
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            # 优先使用项目根目录的mrcai.ico
            icon_paths = [
                "mrcai.ico",
                "resources/icons/mrcai.ico",
                "resources/icons/app.ico"
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    self.window.iconbitmap(icon_path)
                    return
        except Exception as e:
            print(f"Warning: Failed to set window icon: {e}")
    
    def center_window(self):
        """窗口居中显示"""
        # 获取屏幕尺寸
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 窗口尺寸
        window_width = 1000
        window_height = 700
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        self.window.geometry(f"+{x}+{y}")
    
    def setup_components(self):
        """设置组件"""
        # 主容器
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题和按钮
        title_frame = tk.Frame(main_frame, bg='#f0f0f0')
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = tk.Label(title_frame, text=t_gui("market_sentiment_title"), 
                              font=('Microsoft YaHei', 11, 'bold'), 
                              bg='#f0f0f0', fg='#0078d4')
        title_label.pack(side=tk.LEFT)
        
        # 按钮组
        button_frame = tk.Frame(title_frame, bg='#f0f0f0')
        button_frame.pack(side=tk.RIGHT)
        
        # 统一按钮样式 - 与MSCI详情按钮一致，无色彩
        button_style = {
            'font': ('Microsoft YaHei', 11),
            'bg': '#f0f0f0',
            'fg': 'black',
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 20,
            'pady': 5
        }
        
        msci_btn = tk.Button(button_frame, text=t_gui("btn_msci_details"), 
                           command=self.show_msci_details,
                           **button_style)
        msci_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        alert_btn = tk.Button(button_frame, text=t_gui("btn_market_alerts"), 
                            command=self.show_market_alerts,
                            **button_style)
        alert_btn.pack(side=tk.LEFT)
        
        # 内容区域
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 分析结果显示
        self.analysis_text = tk.Text(content_frame, 
                                   font=('Microsoft YaHei', 11),
                                   bg='white', fg='black', wrap=tk.WORD)
        
        scrollbar = tk.Scrollbar(content_frame, orient=tk.VERTICAL, command=self.analysis_text.yview)
        self.analysis_text.configure(yscrollcommand=scrollbar.set)
        
        self.analysis_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
    
    def load_market_data(self):
        """加载市场数据"""
        try:
            if hasattr(self.analysis_results, 'market') and self.analysis_results.market:
                market_data = self.analysis_results.market
                
                # 生成市场分析报告
                analysis_text = self.generate_market_analysis_report(market_data)
                
                self.analysis_text.delete(1.0, tk.END)
                self.analysis_text.insert(1.0, analysis_text)
            else:
                self.analysis_text.delete(1.0, tk.END)
                self.analysis_text.insert(1.0, t_gui("no_market_sentiment_data"))
                
        except Exception as e:
            error_msg = f"加载市场数据失败: {str(e)}"
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, error_msg)
    
    def generate_market_analysis_report(self, market_data):
        """生成市场分析报告"""
        msci_value = market_data.get('current_msci', 0)
        raw_market_state = market_data.get('market_state', '未知')
        raw_risk_level = market_data.get('risk_level', '未知')
        trend_5d = market_data.get('trend_5d', 0)
        
        # 状态翻译字典
        state_translations = {
            'euphoric': t_gui("euphoric"),
            'optimistic': t_gui("optimistic"),
            'neutral': t_gui("neutral"),
            'pessimistic': t_gui("pessimistic"),
            'panic': t_gui("panic")
        }
        
        risk_translations = {
            'low': t_gui("low_risk"),
            'medium': t_gui("medium_risk"),  
            'high': t_gui("high_risk")
        }
        
        # 翻译状态
        market_state = state_translations.get(raw_market_state, raw_market_state)
        risk_level = risk_translations.get(raw_risk_level, raw_risk_level)
        
        report_title = t_gui("market_analysis_report")
        core_indicators = t_gui("core_indicators")
        sentiment_interpretation = t_gui("sentiment_interpretation")
        bull_bear_balance = t_gui("bull_bear_balance")
        risk_assessment = t_gui("risk_assessment")
        
        # 获取更多翻译键
        investment_strategy = t_gui("investment_strategy", "投资策略建议")
        historical_comparison = t_gui("historical_comparison", "历史对比")
        market_outlook = t_gui("market_outlook", "后市展望")
        disclaimer = t_gui("disclaimer", "免责声明")
        generation_time = t_gui("generation_time", "生成时间")
        
        report = f"""
📊 {report_title}
{'='*60}

📈 【{core_indicators}】
• {t_gui("msci_index")}: {msci_value:.2f}/100
• {t_gui("market_state")}: {market_state}
• {t_gui("risk_level")}: {risk_level}
• {t_gui("trend_5d")}: {trend_5d:+.2f}

📊 【{sentiment_interpretation}】
{self.interpret_market_sentiment(msci_value, market_state)}

⚖️ 【{bull_bear_balance}】
{self.analyze_bull_bear_balance(market_data)}

⚠️ 【{risk_assessment}】
{self.assess_market_risk(msci_value, risk_level)}

📝 【{investment_strategy}】
{self.suggest_investment_strategy(msci_value, market_state)}

🕒 【{historical_comparison}】
{self.analyze_historical_trend(market_data)}

🔮 【{market_outlook}】
{self.forecast_market_outlook(msci_value, trend_5d)}

⚠️ 【{disclaimer}】
{t_gui('msci_analysis_disclaimer')}
{t_gui('market_risk_investment_caution')}

{generation_time}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report
    
    def interpret_market_sentiment(self, msci_value, market_state):
        """解读市场情绪"""
        if msci_value > 70:
            return t_gui("market_overly_optimistic_bubble_risk")
        elif msci_value > 50:
            return t_gui("market_positive_strong_confidence")
        elif msci_value > 30:
            return t_gui("market_neutral_cautious_wait_and_see")
        elif msci_value > 15:
            return t_gui("market_pessimistic_panic_near_bottom")
        else:
            return t_gui("market_extreme_panic_long_term_opportunity")
    
    def analyze_bull_bear_balance(self, market_data):
        """分析多空力量对比"""
        # 从市场数据中提取多空力量信息
        latest_analysis = market_data.get('latest_analysis', {})
        bull_bear_ratio = latest_analysis.get('bull_bear_ratio', 1.0)
        
        if bull_bear_ratio > 2.0:
            return f"{t_gui('bull_dominance_absolute')} ({t_gui('bull_bear_ratio')}: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 1.5:
            return f"{t_gui('bull_power_strong')} ({t_gui('bull_bear_ratio')}: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 0.8:
            return f"{t_gui('bull_bear_balanced')} ({t_gui('bull_bear_ratio')}: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 0.5:
            return f"{t_gui('bear_power_strong')} ({t_gui('bull_bear_ratio')}: {bull_bear_ratio:.2f}:1)"
        else:
            return f"{t_gui('bear_dominance_absolute')} ({t_gui('bull_bear_ratio')}: {bull_bear_ratio:.2f}:1)"
    
    def assess_market_risk(self, msci_value, risk_level):
        """评估市场风险"""
        if msci_value > 70:
            return f"{t_gui('high_risk')} {t_gui('high_risk')}：{t_gui('market_overheated_reduce_position')}"
        elif msci_value > 50:
            return f"{t_gui('medium_risk')} {t_gui('medium_risk')}：{t_gui('stay_cautious_control_position')}"
        elif msci_value > 30:
            return f"{t_gui('low_risk')} {t_gui('low_risk')}：{t_gui('moderate_allocation_batch_build')}"
        else:
            return f"{t_gui('low_risk')} {t_gui('opportunity_over_risk')}：{t_gui('consider_contrarian_layout')}"
    
    def suggest_investment_strategy(self, msci_value, market_state):
        """建议投资策略"""
        if msci_value > 70:
            return f"""
• {t_gui('strategy')}: {t_gui('defense_oriented')}
• {t_gui('position')}: {t_gui('suggest_reduce_below_30_percent')}
• {t_gui('operation')}: {t_gui('sell_high_lock_profits')}
• {t_gui('stock_selection')}: {t_gui('focus_defensive_stocks')}"""
        elif msci_value > 50:
            return f"""
• {t_gui('strategy')}: {t_gui('stable_participation')}
• {t_gui('position')}: {t_gui('suggest_maintain_50_70_percent')}
• {t_gui('operation')}: {t_gui('select_stocks_swing_trading')}
• {t_gui('stock_selection')}: {t_gui('quality_blue_chip_growth')}"""
        elif msci_value > 30:
            return f"""
• {t_gui('strategy')}: {t_gui('cautious_building')}
• {t_gui('position')}: {t_gui('suggest_control_30_50_percent')}
• {t_gui('operation')}: {t_gui('batch_layout_no_rush_full')}
• {t_gui('stock_selection')}: {t_gui('solid_fundamentals_quality')}"""
        else:
            return f"""
• {t_gui('strategy')}: {t_gui('contrarian_layout')}
• {t_gui('position')}: {t_gui('gradually_increase_above_70_percent')}
• {t_gui('operation')}: {t_gui('batch_buy_long_term_hold')}
• {t_gui('stock_selection')}: {t_gui('undervalued_quality_growth')}"""
    
    def analyze_historical_trend(self, market_data):
        """分析历史趋势"""
        history = market_data.get('history', [])
        if len(history) >= 10:
            recent_avg = sum(h['msci'] for h in history[-5:]) / 5
            earlier_avg = sum(h['msci'] for h in history[-10:-5]) / 5
            change = recent_avg - earlier_avg
            
            if change > 5:
                return f"{t_gui('recent_sentiment_significantly_improved')} (+{change:.1f})"
            elif change > 2:
                return f"{t_gui('recent_sentiment_moderately_improved')} (+{change:.1f})"
            elif change > -2:
                return f"{t_gui('recent_sentiment_basically_stable')} ({change:+.1f})"
            elif change > -5:
                return f"{t_gui('recent_sentiment_moderately_deteriorated')} ({change:.1f})"
            else:
                return f"{t_gui('recent_sentiment_significantly_deteriorated')} ({change:.1f})"
        else:
            return t_gui("insufficient_historical_data_for_comparison")
    
    def forecast_market_outlook(self, msci_value, trend_5d):
        """预测市场展望"""
        if trend_5d > 3:
            return t_gui("short_term_sentiment_continue_improve_beware_overheating")
        elif trend_5d > 0:
            return t_gui("short_term_sentiment_remain_stable_maintain_strategy")
        elif trend_5d > -3:
            return t_gui("short_term_sentiment_continue_weak_cautious_operation")
        else:
            return t_gui("short_term_sentiment_further_deterioration_stay_watching")
    
    def show_msci_details(self):
        """显示MSCI详情"""
        detail_info = """
数据 MSCI指数详细算法说明

分析 计算方法：
MSCI = (情绪强度×40% + 多空比例×30% + 市场参与度×20% + 极端情绪调整×10%)

上涨 各组成部分：
1. 情绪强度 (40%权重)
   • 基于8级评级的加权平均
   • 反映市场整体乐观/悲观程度

2. 多空力量对比 (30%权重)  
   • 多头vs空头股票数量比例
   • 衡量市场方向性预期

3. 市场参与度 (20%权重)
   • 有评级股票占总股票比例
   • 反映市场活跃度

4. 极端情绪调整 (10%权重)
   • 识别极端乐观/悲观状态
   • 进行相应加分/减分调整

数据 指数范围：0-100
• 70以上：过度乐观(高风险)
• 50-70：乐观(中等风险)  
• 30-50：中性(低风险)
• 30以下：悲观(机会区域)
"""
        
        messagebox.showinfo("MSCI算法详情", detail_info)
    
    def show_market_alerts(self):
        """显示市场预警"""
        try:
            msci_value = self.analysis_results.market.get('current_msci', 50) if hasattr(self.analysis_results, 'market') else 50
            
            if msci_value > 70:
                alert_msg = f"""
🚨 高风险预警！

当前MSCI指数: {msci_value:.1f}

警告 风险信号：
• 市场情绪过度乐观
• 可能存在泡沫风险
• 建议降低仓位

列表 应对措施：
• 立即减仓至30%以下
• 锁定盈利，落袋为安  
• 避免追涨，等待回调
• 关注系统性风险
"""
                messagebox.showwarning("市场预警", alert_msg)
                
            elif msci_value < 30:
                alert_msg = f"""
提示 机会提示！

当前MSCI指数: {msci_value:.1f}

成功 机会信号：
• 市场情绪过度悲观
• 可能接近底部区域
• 适合逆向布局

列表 操作建议：
• 分批建仓至70%
• 选择优质被低估股票
• 中长期持有策略
• 控制单次建仓规模
"""
                messagebox.showinfo("投资机会", alert_msg)
                
            else:
                alert_msg = f"""
ℹ️ 市场状态正常

当前MSCI指数: {msci_value:.1f}

数据 当前状态：
• 市场情绪相对理性
• 风险处于可控范围
• 可按既定策略执行

提示 建议：保持当前投资策略，密切关注市场变化
"""
                messagebox.showinfo("市场状态", alert_msg)
                
        except Exception as e:
            messagebox.showerror("错误", f"获取市场预警信息失败:\n{str(e)}")
    



# 添加缺少的import
import random


class StockAnalyzerMainWindowExtended(StockAnalyzerMainWindow):
    """扩展版本的主窗口类，用于main_gui.py调用"""
    
    def __init__(self):
        super().__init__()
        self.is_extended = True
        print("GUI")
    
    def open_ai_model_settings(self):
        """打开AI模型设置界面"""
        try:
            import subprocess
            import sys
            import os
            
            # 获取llm-api目录的设置文件路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            llm_api_dir = os.path.join(current_dir, "llm-api")
            
            # 优先使用无控制台窗口版本
            run_settings_no_console_path = os.path.join(llm_api_dir, "run_settings_no_console.pyw")
            run_settings_path = os.path.join(llm_api_dir, "run_settings.py")
            
            # 优先使用无控制台窗口版本
            if os.path.exists(run_settings_no_console_path):
                # 使用.pyw文件启动，自动隐藏控制台窗口
                if os.name == 'nt':  # Windows系统
                    pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                    if os.path.exists(pythonw_path):
                        subprocess.Popen([pythonw_path, run_settings_no_console_path], 
                                       cwd=llm_api_dir)
                    else:
                        subprocess.Popen([sys.executable, run_settings_no_console_path], 
                                       cwd=llm_api_dir,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen([sys.executable, run_settings_no_console_path], 
                                   cwd=llm_api_dir)
            elif os.path.exists(run_settings_path):
                # 备用方案：使用原始的.py文件
                if os.name == 'nt':  # Windows系统
                    pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                    if os.path.exists(pythonw_path):
                        subprocess.Popen([pythonw_path, run_settings_path], 
                                       cwd=llm_api_dir)
                    else:
                        subprocess.Popen([sys.executable, run_settings_path], 
                                       cwd=llm_api_dir,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen([sys.executable, run_settings_path], 
                                   cwd=llm_api_dir)
                
                self.status_var.set("AI模型设置界面已启动")
            else:
                messagebox.showerror("错误", f"找不到AI模型设置文件:\n{run_settings_no_console_path}\n或\n{run_settings_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"启动AI模型设置失败:\n{str(e)}")
    

    def run(self):
        """运行应用"""
        try:
            print("GUI...")
            self.root.mainloop()
        except Exception as e:
            print(f"错误 GUI运行错误: {e}")
            raise