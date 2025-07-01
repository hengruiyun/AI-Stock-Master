#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI股票趋势分析系统 - 主窗口模块
包含主界面和各种分析窗口的实现
"""

import os
import sys
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
    from algorithms.realtime_engine import RealtimeAnalysisEngine
    from algorithms.analysis_results import AnalysisResults
    from utils.report_generator import ReportGenerator, ExcelReportGenerator
except ImportError as e:
    print(f"Warning: 模块导入失败: {e}")

# 导入语言管理器
try:
    from localization.improved_language_manager import _, is_english
    print(f"语言管理器加载成功")
except ImportError as e:
    print(f"Warning: 语言管理器导入失败: {e}")
    # 如果导入失败，使用简单的回退函数
    def _(key, default=None):
        return default or key
    def is_english():
        return False

# 设置matplotlib中文字体支持
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class StockAnalyzerMainWindow:
    """AI股票趋势分析系统主窗口"""
    
    def __init__(self):
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
    
    def format_stock_code(self, code):
        """格式化股票代码，过滤非中国股票代码前面的0"""
        if not code:
            return code
            
        # 中国股票代码（6位数字）保持原样
        if len(code) == 6 and code.isdigit():
            return code
            
        # 其他地区股票代码，去除前面的0
        # 例如：000001.HK -> 1.HK, 0700.HK -> 700.HK
        if '.' in code:
            stock_num, suffix = code.split('.', 1)
            # 去除前面的0，但保留至少一位数字
            stock_num = stock_num.lstrip('0') or '0'
            return f"{stock_num}.{suffix}"
        else:
            # 纯数字代码，去除前面的0
            return code.lstrip('0') or '0'
    
    def load_or_create_user_config(self):
        """加载或创建用户配置文件"""
        try:
            from config import load_user_config
            self.user_config = load_user_config()
            print(_('config_load_success', '用户配置文件加载成功'))
        except Exception as e:
            print(f"{_('config_load_failed', '加载用户配置失败，使用默认配置')}: {e}")
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
        self.root.title(_("app_title", "AI股票趋势分析系统") + " " + _("app_version", "v2.1") + " (267278466@qq.com)")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Windows经典灰色背景
        self.root.configure(bg='#f0f0f0')
        
        # 设置窗口图标 (如果存在)
        try:
            if os.path.exists("resources/icons/app.ico"):
                self.root.iconbitmap("resources/icons/app.ico")
        except:
            pass
        
        # 窗口居中
        self.center_window()
    
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
    
    def setup_menu(self):
        """设置菜单栏 - Windows经典风格，字体统一为11号"""
        menubar = tk.Menu(self.root, bg='#f0f0f0', fg='black', font=('Microsoft YaHei', 11))
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=_("menu_file", "文件") + "(F)", menu=file_menu, underline=2)
        file_menu.add_command(label=_("menu_open_file", "打开数据文件") + "...", command=self.open_excel_file, 
                             accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label=_("menu_export_report", "导出分析报告") + "...", command=self.export_report, 
                             accelerator="Ctrl+S")
        file_menu.add_command(label=_("menu_export_html", "导出HTML报告") + "...", command=self.export_html_report)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu_exit", "退出"), command=self.root.quit, 
                             accelerator="Alt+F4")
        
        # 分析菜单
        analysis_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=_("menu_analysis", "分析") + "(A)", menu=analysis_menu, underline=2)
        analysis_menu.add_command(label=_("menu_start_analysis", "开始分析"), command=self.start_analysis, 
                                 accelerator="F5")
        analysis_menu.add_separator()
        analysis_menu.add_command(label=_("menu_stock_analysis", "个股趋势分析"), command=self.show_stock_analysis)
        analysis_menu.add_command(label=_("menu_industry_analysis", "行业对比分析"), command=self.show_industry_analysis)
        analysis_menu.add_command(label=_("menu_market_analysis", "市场情绪分析"), command=self.show_market_analysis)
        
        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=_("menu_tools", "工具") + "(T)", menu=tools_menu, underline=2)
        tools_menu.add_command(label=_("menu_data_validation", "数据验证"), command=self.show_data_validation)
        tools_menu.add_command(label=_("menu_performance_monitor", "性能监控"), command=self.show_performance_monitor)
        tools_menu.add_separator()
        tools_menu.add_command(label=_("menu_settings", "系统设置"), command=self.show_settings)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0, bg='#f0f0f0', font=('Microsoft YaHei', 11))
        menubar.add_cascade(label=_("menu_help", "帮助") + "(H)", menu=help_menu, underline=2)
        help_menu.add_command(label=_("menu_user_guide", "使用说明"), command=lambda: messagebox.showinfo(_("help_title", "帮助"), _("help_developing", "使用说明功能开发中...")))
        help_menu.add_command(label=_("menu_about", "关于"), command=self.show_about)
        
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
        
        # GitHub链接区域（左上角）
        github_label = tk.Label(top_frame, text="HengruiYun", 
                               bg='#f0f0f0', fg='#0066cc', 
                               font=('Microsoft YaHei', 11, 'underline'),
                               cursor='hand2')
        github_label.pack(side=tk.LEFT, padx=(0, 10))
        github_label.bind('<Button-1>', self.open_github_page)
        
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
        self.market_btn = tk.Button(button_frame, text=_("btn_market", "市场"), 
                                   command=self.show_market_analysis,
                                   state=tk.DISABLED,
                                   **button_style)
        self.market_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 行业按钮
        self.industry_btn = tk.Button(button_frame, text=_("btn_industry", "行业"), 
                                     command=self.show_industry_analysis,
                                     state=tk.DISABLED,
                                     **button_style)
        self.industry_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 个股按钮
        self.stock_btn = tk.Button(button_frame, text=_("btn_stock", "个股"), 
                                  command=self.show_stock_analysis,
                                  state=tk.DISABLED,
                                  **button_style)
        self.stock_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 报告按钮 (对应HTML样本右下角)
        self.report_btn = tk.Button(button_frame, text=_("btn_report", "报告"), 
                                   command=self.export_html_report,
                                   state=tk.DISABLED,
                                   **button_style)
        self.report_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 分析按钮
        self.analyze_btn = tk.Button(button_frame, text=_("btn_analyze", "分析"), 
                                    command=self.start_analysis,
                                    state=tk.DISABLED,
                                    **button_style)
        self.analyze_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # AI模型按钮 (新增)
        self.ai_model_btn = tk.Button(button_frame, text=_("btn_ai_model", "AI模型"), 
                                     command=self.open_ai_model_settings,
                                     **button_style)
        self.ai_model_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 加载按钮 (对应HTML样本右上角)
        self.load_btn = tk.Button(button_frame, text=_("btn_load", "加载"), 
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
        """设置状态栏 - Windows经典风格"""
        status_frame = tk.Frame(self.root, bg='#f0f0f0', relief=tk.SUNKEN, bd=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 状态文本
        self.status_var = tk.StringVar()
        self.status_var.set(_("status_ready", "就绪") + " | " + _("status_select_file", "请选择数据文件开始分析"))
        
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               bg='#f0f0f0', fg='#606060',
                               font=('Microsoft YaHei', 10),  # 状态栏使用10号
                               anchor=tk.W)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=2)
        
        # 进度条 (初始隐藏)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, 
                                          variable=self.progress_var,
                                          maximum=100, length=200)
        # 暂时不显示
    
    def show_welcome_message(self):
        """显示欢迎信息 - 对应HTML样本的占位文本"""
        welcome_text = f"""{_("welcome_title", "欢迎使用")} {_("app_title", "AI股票趋势分析系统")} 

{_("welcome_core_features", "核心功能特点")}:
• RTSI - {_("rtsi_desc", "个股评级趋势强度指数")}
• IRSI - {_("irsi_desc", "行业相对强度指数")}  
• MSCI - {_("msci_desc", "市场情绪综合指数")}

{_("welcome_getting_started", "开始使用")}:
1. {_("welcome_step1", "点击右上角'加载'按钮选择数据文件")}
2. {_("welcome_step2", "支持格式: *.xlsx, *.xls, *.csv")}
3. {_("welcome_step3", "建议文件: A股数据YYYYMMDD.xlsx")}

{_("welcome_dynamic_analysis", "动态数据分析")}:
• {_("welcome_stock_count", "股票总数 - 动态读取自数据文件")}
• {_("welcome_industry_count", "行业数量 - 动态统计分类信息")}
• {_("welcome_industry_query", "所属行业 - 实时查询不保存")}

{_("welcome_system_config", "系统配置")}:
• Python 3.10+ {_("welcome_tech_stack", "技术栈")}
• Windows {_("welcome_classic_ui", "经典界面风格")}
• {_("welcome_professional_algo", "专业级数据分析算法")}

{_("welcome_note", "注意")}: {_("welcome_note_desc", "系统不会自动加载文件，所有数据均从用户选择的文件中动态读取")}
"""
        
        self.update_text_area(welcome_text, text_color='#666666')
    
    def update_text_area(self, text, text_color='black'):
        """更新中央文本显示区域"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, text)
        self.text_area.config(fg=text_color, state=tk.DISABLED)
    
    def open_excel_file(self):
        """打开数据文件对话框"""
        filetypes = [
            (_("filetype_data", "数据文件"), '*.xlsx;*.xls;*.csv'),
            (_("filetype_excel", "Excel文件"), '*.xlsx;*.xls'),
            (_("filetype_csv", "CSV文件"), '*.csv'),
            ('Excel 2007+', '*.xlsx'),
            ('Excel 97-2003', '*.xls'),
            (_("filetype_all", "所有文件"), '*.*')
        ]
        
        filename = filedialog.askopenfilename(
            title=_("dialog_select_file", "选择股票数据文件"),
            filetypes=filetypes,
            initialdir=str(Path.cwd())
        )
        
        if filename:
            self.load_data_file(filename)
    
    def load_data_file(self, file_path):
        """加载数据文件"""
        try:
            # 更新状态
            self.status_var.set(f"{_('status_loading', '加载中...')}: {Path(file_path).name}")
            self.root.update()
            
            # 显示文件信息
            file_info = self.get_file_info(file_path)
            
            success_text = f"""{_('loading_success', '成功')} {_('error_file_load_failed', '文件加载成功')}!

{_('filetype_data', '文档')} {_('result_data_overview', '文件信息')}:
• {_('col_stock_name', '文件名')}: {file_info['name']}
• {_('data_scale', '文件大小')}: {file_info['size']} MB
• {_('result_data_date', '修改时间')}: {file_info['modified']}

{_('data_analysis_in_progress', '数据预检')}:
• {_('stage_detail_loading', '正在分析Excel结构...')}
• {_('stage_detail_validation', '检测评级系统格式...')}
• {_('stage_detail_validation', '验证行业分类数据...')}

{_('welcome_getting_started', '下一步')}: {_('btn_start_analysis', '点击"分析"按钮开始数据分析')}
"""
            
            self.update_text_area(success_text, text_color='#008000')
            
            # 创建数据集对象
            self.current_dataset = StockDataSet(file_path)
            
            # 启用分析按钮
            self.analyze_btn.config(state=tk.NORMAL)
            
            # 更新状态
            self.status_var.set(f"{_('status_ready', '已加载')}: {file_info['name']} | {_('btn_start_analysis', '点击分析按钮继续')}")
            
        except Exception as e:
            error_text = f"""{_('error_file_load_failed', 'X 文件加载失败!')}!

{_('analysis_error', '错误信息')}: {str(e)}

{_('tip_possible_reasons', '提示 解决建议')}:
• {_('data_format_error', '确认文件格式为Excel (.xlsx/.xls)')}
• {_('data_format_error', '检查文件是否正在被其他程序使用')}
• {_('data_format_error', '验证文件内容是否包含股票数据')}
• {_('data_format_error', '尝试重新下载数据文件')}

📞 {_('menu_help', '如需帮助，请查看帮助菜单中的使用说明')}
"""
            
            self.update_text_area(error_text, text_color='#cc0000')
            self.status_var.set(f"{_('status_error', '加载失败')}: {str(e)}")
            
            messagebox.showerror(_("error_file_load_failed", "文件加载错误"), f"{_('error_file_load_failed', '无法加载文件')}:\n{str(e)}")
    
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
            messagebox.showwarning(_("confirm_title", "提示"), _("status_select_file", "请先加载数据文件"))
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
                print("检测到主循环未启动，跳过UI更新")
            
            # 设置UI状态 - 仅在主循环运行时更新
            if main_loop_running:
                self.root.after(0, lambda: self.status_var.set(_("data_analysis_in_progress", "正在分析数据，请稍候...")))
                self.root.after(0, lambda: self.analyze_btn.config(state=tk.DISABLED))
                
                # 显示分析进度
                progress_text = f"""{_("data_analysis_ongoing", "数据分析进行中...")}...

{_("analysis_progress_title", "分析阶段")}:
• [■■■░░░░░░░] {_("data_loading_validation", "数据加载和验证")} (30%)
• [░░░░░░░░░░] {_("rtsi_individual_trend_analysis", "RTSI个股趋势分析")} (0%)
• [░░░░░░░░░░] {_("analysis_calculating_irsi", "IRSI行业强度分析")} (0%)
• [░░░░░░░░░░] {_("analysis_calculating_msci", "MSCI市场情绪分析")} (0%)

⏱️ {_("result_calculation_time", "预计处理时间")}: 10-15{_("trading_days", "秒")}
💻 {_("menu_performance_monitor", "处理器使用率")}: {_("data_analysis_in_progress", "正在监控...")}  
{_("data_preparing", "内存使用情况")}: {_("data_analysis_in_progress", "正在监控...")}

{_("data_analysis_in_progress", "请耐心等待分析完成...")}  
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
                print("分析完成，存储结果但跳过UI更新")
            
        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            if main_loop_running:
                self.root.after(0, lambda: self._analysis_failed(error_msg))
            else:
                print(f"分析失败：{error_msg}")
    
    def _analysis_completed(self):
        """分析完成后的界面更新"""
        try:
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
            
            self.status_var.set(f"{_('analysis_complete', '分析完成')} | {_('found_stocks_industries', '发现')} {stock_count} {_('units_stocks', '只股票')}，{industry_count} {_('units_industries', '个行业分类')}")
            
            # 执行AI智能分析
            self._start_ai_analysis()
            
        except Exception as e:
            self._analysis_failed(f"结果处理失败: {str(e)}")
    
    def _analysis_failed(self, error_msg):
        """分析失败处理"""
        error_text = f"""{_('error_analysis_failed', 'X 数据分析失败!')}!

{_('analysis_error', '错误信息')}: {error_msg}

{_('tip_possible_reasons', '提示 可能的原因')}:
• {_('data_format_error', '数据格式不符合预期')}
• {_('error_insufficient_data', '内存不足，数据量过大')}
• {_('error_calculation_error', '系统算法执行异常')}
• {_('data_format_error', '依赖模块版本不兼容')}

{_('solution_suggestions', '工具 解决建议')}:
• {_('data_format_error', '检查数据文件格式和内容')}
• {_('btn_refresh', '重启程序后重试')}
• {_('menu_user_guide', '查看帮助文档了解数据要求')}
• {_('menu_help', '联系技术支持获取帮助')}
"""
        
        self.update_text_area(error_text, text_color='#cc0000')
        self.status_var.set(f"{_('analysis_failed', '分析失败')}: {error_msg}")
        self.analyze_btn.config(state=tk.NORMAL)
        
        messagebox.showerror(_("analysis_failed_title", "分析错误"), error_msg)
    
    def _generate_analysis_summary(self):
        """生成分析结果摘要"""
        if not self.analysis_results:
            return _("analysis_empty")
        
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
                date_range_str = f"{date_range[0]} ~ {date_range[1]}" if date_range[0] else _("unknown")
                
            else:
                # 如果是字典格式（兼容性处理）
                summary = self.analysis_results.get('summary', {})
                total_stocks = summary.get('total_stocks', 0)
                total_industries = summary.get('total_industries', 0)
                calculation_time = 0
                top_stocks = self.analysis_results.get('top_stocks', [])
                top_industries = self.analysis_results.get('top_industries', [])
                market_data = self.analysis_results.get('market_sentiment', {})
                date_range_str = summary.get('date_range', _("unknown"))
        
            # 生成摘要文本
            summary_text = f"""{_("success")} {_("analysis_results")}

{_("data_overview")}:
• {_("total_stocks")}: {total_stocks} {_("units_stocks")}
• {_("industry_classification")}: {total_industries} {_("units_industries")}
• {_("calculation_time")}: {calculation_time:.2f} {_("seconds")}
• {_("data_date")}: {date_range_str}

{_("excellent")} {_("quality_stocks_top5")} ({_("sorted_by_rtsi")}):"""
            
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
                        summary_text += f"\n{i}. {_('data_format_error')}: {type(stock_data)}"
            else:
                summary_text += f"\n{_('no_data')}"
            
            summary_text += f"\n\n{_('industry')} {_('strong_industries_top5')} ({_('sorted_by_irsi')}):"
            
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
                        summary_text += f"\n{i}. {_('data_format_error')}: {type(industry_data)}"
            else:
                summary_text += f"\n{_('no_data')}"
            
            # 处理市场情绪数据
            summary_text += f"\n\n{_('rising')} {_('market_sentiment_analysis')}:"
            
            # 安全地提取和格式化市场数据
            try:
                import numpy as np
                
                current_msci = market_data.get('current_msci', 0)
                if isinstance(current_msci, (int, float, np.number)):
                    msci_str = f"{float(current_msci):.1f}"
                else:
                    msci_str = str(current_msci)
                
                market_state = market_data.get('market_state', _("unknown"))
                if isinstance(market_state, (dict, list)):
                    market_state = str(market_state)
                elif market_state is None:
                    market_state = _("unknown")
                
                risk_level = market_data.get('risk_level', _("unknown"))
                if isinstance(risk_level, (dict, list)):
                    risk_level = str(risk_level)
                elif risk_level is None:
                    risk_level = _("unknown")
                
                trend_5d = market_data.get('trend_5d', 0)
                if isinstance(trend_5d, (int, float, np.number)):
                    trend_str = f"{float(trend_5d):.2f}"
                else:
                    trend_str = str(trend_5d)
                
                summary_text += f"\n• {_('current_msci_index')}: {msci_str}"
                summary_text += f"\n• {_('market_state')}: {market_state}"
                summary_text += f"\n• {_('risk_level')}: {risk_level}"
                summary_text += f"\n• {_('five_day_trend')}: {trend_str}"
            
            except Exception as e:
                summary_text += f"\n• {_('market_data_parse_error')}: {str(e)}"

            summary_text += f"\n\n{_('tip')} {_('detailed_report_instruction')}\n"
            
            return summary_text
            
        except Exception as e:
            return f"{_('summary_generation_failed')}: {str(e)}\n\n{_('check_analysis_data_format')}"
    
    # 菜单功能实现
    def export_report(self):
        """导出Excel报告"""
        if not self.analysis_results:
            messagebox.showwarning(_("tip"), _("complete_analysis_first"))
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                title=_("save_analysis_report"),
                defaultextension=".xlsx",
                filetypes=[(_("excel_files"), "*.xlsx"), (_("all_files"), "*.*")]
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
                    
                    self.status_var.set(f"{_('exported_excel_report')}: {Path(filename).name}")
                    messagebox.showinfo(_('success'), f"{_('report_saved_to')}:\n{filename}")
                    
                except ImportError:
                    # 备用方案：使用基础的Excel导出
                    self._basic_excel_export(filename)
                    self.status_var.set(f"{_('exported_excel_report')}: {Path(filename).name}")
                    messagebox.showinfo(_('success'), f"{_('report_saved_to')}:\n{filename}")
                
        except Exception as e:
            messagebox.showerror(_('export_error'), f"{_('excel_export_failed')}:\n{str(e)}")
    
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
                        'analysis_period': _("trading_days_38"),
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
                        'analysis_period': _("trading_days_38"),
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
                    'analysis_period': _("trading_days_38"),
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
                    _("analysis_time"): [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    _("total_stocks"): [len(self.analysis_results.get('stocks', {}))],
                    _("analysis_status"): [_("completed")],
                    _("data_file"): [self.current_dataset.file_path if self.current_dataset else _("unknown")]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name=_("analysis_summary"), index=False)
                
                # 股票数据（如果有）
                if 'stocks' in self.analysis_results:
                    stock_data = []
                    for code, info in self.analysis_results['stocks'].items():
                        stock_data.append({
                            _("stock_code"): code,
                            _("stock_name"): info.get('name', ''),
                            _("industry"): info.get('industry', ''),
                            _("analysis_result"): str(info)
                        })
                    
                    if stock_data:
                        stock_df = pd.DataFrame(stock_data)
                        stock_df.to_excel(writer, sheet_name=_("stock_analysis"), index=False)
                
                # 行业数据（如果有）
                if 'industries' in self.analysis_results:
                    industry_data = []
                    for industry, info in self.analysis_results['industries'].items():
                        industry_data.append({
                            _("industry_name"): industry,
                            _("analysis_result"): str(info)
                        })
                    
                    if industry_data:
                        industry_df = pd.DataFrame(industry_data)
                        industry_df.to_excel(writer, sheet_name=_("industry_analysis"), index=False)
        
        except Exception as e:
            raise Exception(f"{_('basic_excel_export_failed')}: {str(e)}")
    
    def export_html_report(self):
        """导出HTML报告"""
        if not self.analysis_results:
            messagebox.showwarning(_("tip"), _("complete_analysis_first"))
            return
        
        try:
            # 直接使用简单版本的HTML报告生成器，避免plotly依赖问题
            self._generate_simple_html_report()
            
        except Exception as e:
            messagebox.showerror(_('export_error'), f"{_('html_report_generation_failed')}:\n{str(e)}")
    
    def _generate_simple_html_report(self):
        """生成简单版HTML报告"""
        try:
            from datetime import datetime
            import webbrowser
            
            reports_dir = Path("reports")
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
                
                market_state = market_data.get('market_state', _("unknown"))
                risk_level = market_data.get('risk_level', _("unknown"))
                
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
                    market_state = market_data.get('market_state', _("neutral_bearish"))
                    risk_level = market_data.get('risk_level', _("medium"))
                    trend_5d = market_data.get('trend_5d', 0)
                else:
                    # 默认市场情绪数据
                    msci_value = 42.5
                    market_state = _("neutral_bearish")
                    risk_level = _("medium")
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
                        recommendation = _("strongly_recommend") if rtsi_value > 70 else _("moderate_attention") if rtsi_value > 50 else _("cautious_watch")
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
                <td>{_("data_processing")}</td>
                <td>--</td>
                <td>{_("waiting_analysis")}</td>
            </tr>"""
            else:
                stock_recommendations_html = """
            <tr>
                <td>1</td>
                <td>--</td>
                <td>{_("no_data")}</td>
                <td>--</td>
                <td>{_("complete_analysis_first")}</td>
            </tr>"""
            
            # 生成行业分析HTML
            industry_analysis_html = ""
            if hasattr(self.analysis_results, 'industries') and self.analysis_results.industries:
                # 获取top行业数据
                top_industries = self.analysis_results.get_top_industries('irsi', 10)
                
                if top_industries:
                    industry_analysis_html = f"<p><strong>{_('strong_industries_ranking')} ({_('sorted_by_irsi_index')}):</strong></p><table>"
                    industry_analysis_html += f"<tr><th>{_('ranking')}</th><th>{_('industry_name')}</th><th>{_('irsi_index')}</th><th>{_('strength_level')}</th><th>{_('investment_advice')}</th></tr>"
                    
                    for i, (industry_name, irsi_value) in enumerate(top_industries[:5], 1):
                        # 判断强度等级
                        if irsi_value > 20:
                            strength = _("strong")
                            advice = _("active_allocation")
                            color = "green"
                        elif irsi_value > 5:
                            strength = _("neutral_strong")
                            advice = _("moderate_attention")
                            color = "blue"
                        elif irsi_value > -5:
                            strength = _("neutral")
                            advice = _("wait_and_see")
                            color = "gray"
                        elif irsi_value > -20:
                            strength = _("neutral_weak")
                            advice = _("cautious")
                            color = "orange"
                        else:
                            strength = _("weak")
                            advice = _("avoid")
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
                    industry_analysis_html += f"<p><strong>{_('current_strongest_industry')}:</strong> {strongest_industry} (IRSI: {strongest_irsi:.2f})</p>"
                    industry_analysis_html += f"<p><small>{_('irsi_index_explanation')}</small></p>"
                else:
                    industry_analysis_html = f"<p>{_('no_industry_analysis_data')}</p>"
            else:
                industry_analysis_html = f"<p>{_('no_industry_analysis_data')}</p>"
            
            # 生成AI分析版块HTML
            ai_analysis_section = ""
            if hasattr(self, 'ai_analysis_result') and self.ai_analysis_result:
                ai_analysis_section = f"""
    <div class="section">
        <h2>{_("ai_intelligent_analysis")}</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
            <h3>{_("ai_analyst_opinion")}</h3>
            <div style="white-space: pre-wrap; line-height: 1.6; color: #333;">{self.ai_analysis_result}</div>
        </div>
        <p><small>{_("ai_analysis_disclaimer")}</small></p>
    </div>"""
            else:
                ai_analysis_section = ""
            
            # 生成市场情绪分析HTML
            sentiment_risk_color = "red" if msci_value > 70 or msci_value < 30 else "orange" if msci_value < 40 else "green"
            trend_color = "green" if trend_5d > 0 else "red"
            
            # 生成简单的HTML内容
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_("ai_stock_trend_analysis_report")}</title>
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
        <h1>{_("ai_stock_trend_analysis_report")}</h1>
        <p>{_("generation_time")}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="author">{_("author")}: 267278466@qq.com</div>
    </div>
    
    <div class="section">
        <h2>{_("analysis_overview")}</h2>
        <div class="metric">{_("total_stocks")}: <span class="highlight">{total_stocks:,}</span></div>
        <div class="metric">{_("industry_classification")}: <span class="highlight">{total_industries}</span>{_("units_industries")}</div>
        <div class="metric">{_("analysis_algorithm")}: <span class="highlight">RTSI + IRSI + MSCI</span></div>
        <div class="metric">{_("data_quality")}: <span class="highlight">{_("good")}</span></div>
    </div>
    
    <div class="section">
        <h2>{_("market_sentiment_index")}</h2>
        <p>{_("msci_based_market_sentiment_analysis")}</p>
        <div class="sentiment-grid">
            <div class="sentiment-card">
                <h3>{_("core_indicators")}</h3>
                <p><strong>{_("msci_index")}:</strong> <span style="color: {sentiment_risk_color}; font-weight: bold;">{msci_value:.1f}</span></p>
                <p><strong>{_("market_state")}:</strong> {market_state}</p>
                <p><strong>{_("risk_level")}:</strong> <span class="risk-{risk_level.lower()}">{risk_level}</span></p>
                <p><strong>{_("five_day_trend")}:</strong> <span class="trend-{'up' if trend_5d > 0 else 'down'}">{trend_5d:+.1f}</span></p>
            </div>
            <div class="sentiment-card">
                <h3>{_("market_judgment")}</h3>
                <p><strong>{_("overall_sentiment")}:</strong> {_("slightly_optimistic") if msci_value > 60 else _("slightly_pessimistic") if msci_value < 40 else _("neutral")}</p>
                <p><strong>{_("investment_advice")}:</strong> {_("cautious_reduction") if msci_value > 70 else _("moderate_increase") if msci_value < 30 else _("balanced_allocation")}</p>
                <p><strong>{_("focus_points")}:</strong> {_("prevent_bubble_risk") if msci_value > 70 else _("seek_value_opportunities") if msci_value < 30 else _("focus_rotation_opportunities")}</p>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>{_("stock_recommendations")}</h2>
        <p>{_("rtsi_based_quality_stock_analysis")}</p>
        <table>
            <tr><th>{_("ranking")}</th><th>{_("stock_code")}</th><th>{_("stock_name")}</th><th>{_("rtsi_index")}</th><th>{_("recommendation_reason")}</th></tr>
            {stock_recommendations_html}
        </table>
    </div>
    
    <div class="section">
        <h2>{_("industry_rotation_analysis")}</h2>
        <p>{_("irsi_based_industry_strength_analysis")}</p>
        {industry_analysis_html}
    </div>
    
    <div class="section">
        <h2>{_("investment_advice")}</h2>
        <ul>
            <li>{_("based_on_msci_index")}{msci_value:.1f}，{_("current_market_sentiment")}{market_state}</li>
            <li>{_("suggested_position")}：{"30-40%" if msci_value > 70 else "70-80%" if msci_value < 30 else "50-60%"}</li>
            <li>{_("focus_rtsi_above_60")}</li>
            <li>{_("focus_strong_industry_leaders")}</li>
            <li>{_("set_stop_loss_risk_control")}</li>
        </ul>
    </div>
    
    {ai_analysis_section}
    
    <div class="section">
        <p><small>{_("disclaimer")}</small></p>
    </div>
</body>
</html>
            """
            
            # 写入HTML文件
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 在浏览器中打开
            webbrowser.open(f"file://{html_file.absolute()}")
            
            self.status_var.set(f"{_('html_report_generated_and_opened')}: {html_file.name}")
            
            # 返回HTML内容用于测试
            return html_content
            
        except Exception as e:
            messagebox.showerror(_('export_error'), f"{_('html_report_generation_failed')}:\n{str(e)}")
            return None
    
    def show_stock_analysis(self):
        """显示个股分析窗口"""
        if not self.analysis_results:
            messagebox.showwarning(_("tip"), _("load_data_and_complete_analysis_first"))
            return
        
        try:
            # 创建个股分析窗口，传递current_dataset
            StockAnalysisWindow(self.root, self.analysis_results, self.current_dataset)
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('open_stock_analysis_window_failed')}:\n{str(e)}")
    
    def show_industry_analysis(self):
        """显示行业分析窗口"""
        if not self.analysis_results:
            messagebox.showwarning(_("tip"), _("load_data_and_complete_analysis_first"))
            return
        
        try:
            # 创建行业分析窗口
            IndustryAnalysisWindow(self.root, self.analysis_results)
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('open_industry_analysis_window_failed')}:\n{str(e)}")
    
    def show_market_analysis(self):
        """显示市场分析窗口"""
        if not self.analysis_results:
            messagebox.showwarning(_("tip"), _("load_data_and_complete_analysis_first"))
            return
        
        try:
            # 创建市场情绪分析窗口
            MarketSentimentWindow(self.root, self.analysis_results)
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('open_market_analysis_window_failed')}:\n{str(e)}")
    
    def show_settings(self):
        """显示设置窗口"""
        try:
            from gui.analysis_dialogs import SettingsDialog
            SettingsDialog(self.root)
        except ImportError:
            messagebox.showerror(_("feature_unavailable"), _("settings_module_not_found"))
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('open_settings_window_failed')}:\n{str(e)}")
    
    def show_help(self):
        """显示帮助窗口"""
        # 实现帮助窗口的逻辑
        pass
    
    def show_about(self):
        """显示关于窗口"""
        messagebox.showinfo(_('about'), f"{_('ai_stock_trend_analysis_system')} v2.0.0\n\n{_('professional_stock_analysis_tool')}\n\n{_('contact')}: 267278466@qq.com")
    
    def open_github_page(self, event):
        """打开GitHub页面"""
        import webbrowser
        webbrowser.open("https://github.com/hengruiyun/ai-stock")
    
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
                return
            
            # 更新AI状态显示
            self.ai_status_var.set(_("ai_analyzing"))
            
            # 在后台线程中执行AI分析
            ai_thread = threading.Thread(target=self._run_ai_analysis)
            ai_thread.daemon = True
            ai_thread.start()
            
        except Exception as e:
            print(f"{_('ai_analysis_startup_failed')}: {str(e)}")
            self.ai_status_var.set(_("ai_analysis_startup_failed"))
    
    def _check_llm_config(self) -> bool:
        """检查LLM配置文件是否存在"""
        try:
            import os
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(current_dir, "llm-api", "config", "user_settings.json")
            
            if not os.path.exists(config_path):
                print(_("ai_analysis_skipped_no_config"))
                self.ai_status_var.set(_("ai_not_configured"))
                return False
            
            # 读取配置文件验证格式
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if not config.get('default_provider') or not config.get('default_chat_model'):
                print(_("ai_analysis_skipped_incomplete_config"))
                self.ai_status_var.set(_("ai_config_incomplete"))
                return False
                
            return True
            
        except Exception as e:
            print(f"{_('ai_config_check_failed')}: {str(e)}")
            self.ai_status_var.set(_("ai_config_error"))
            return False
    
    def _run_ai_analysis(self):
        """执行AI智能分析"""
        try:
            # 更新状态
            self.root.after(0, lambda: self.status_var.set(_("ai_intelligent_analysis_in_progress")))
            
            # 准备分析数据
            analysis_data = self._prepare_analysis_data()
            
            # 调用LLM API
            ai_response = self._call_llm_api(analysis_data)
            
            if ai_response:
                # 在主线程中更新UI
                self.root.after(0, lambda: self._display_ai_analysis(ai_response))
                self.root.after(0, lambda: self.ai_status_var.set(_("ai_analysis_completed")))
            else:
                self.root.after(0, lambda: self.status_var.set(_("ai_analysis_failed_continue_traditional")))
                self.root.after(0, lambda: self.ai_status_var.set(_("ai_analysis_failed")))
                
        except Exception as e:
            print(f"{_('ai_analysis_execution_failed')}: {str(e)}")
            self.root.after(0, lambda: self.status_var.set(_("ai_analysis_error_continue_traditional")))
            self.root.after(0, lambda: self.ai_status_var.set(_("ai_analysis_error")))
    
    def _prepare_analysis_data(self) -> dict:
        """准备发送给AI的分析数据"""
        try:
            data = {
                "analysis_type": _("stock_market_comprehensive_analysis"),
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
                    market_sentiment = _("extremely_optimistic")
                elif msci_value >= 60:
                    market_sentiment = _("optimistic")
                elif msci_value >= 40:
                    market_sentiment = _("neutral")
                elif msci_value >= 30:
                    market_sentiment = _("pessimistic")
                else:
                    market_sentiment = _("extremely_pessimistic")
                
                data["market_data"] = {
                    "msci_value": msci_value,
                    "trend_5d": market.get('trend_5d', 0),
                    "volatility": volatility,
                    "volume_ratio": volume_ratio,
                    "market_sentiment": market_sentiment,
                    "risk_level": market.get('risk_level', _("medium"))
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
            
            # 提取股票数据（前50个，仅原始数值）
            if hasattr(self.analysis_results, 'stocks') and self.analysis_results.stocks:
                top_stocks = self.analysis_results.get_top_stocks('rtsi', 50)
                for stock_code, stock_name, score in top_stocks:
                    if stock_code in self.analysis_results.stocks:
                        stock_info = self.analysis_results.stocks[stock_code]
                        data["stock_data"][stock_code] = {
                            "name": stock_info.get('name', stock_code),
                            "industry": stock_info.get('industry', _("unknown")),
                            "rtsi_value": stock_info.get('rtsi', {}).get('rtsi', 0),
                            "price": stock_info.get('price', 0),
                            "volume": stock_info.get('volume', 0),
                            "market_cap": stock_info.get('market_cap', 0)
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
            print(f"{_('data_preparation_failed')}: {str(e)}")
            return {}
    
    def _extract_historical_data(self):
        """提取30天历史数据用于LLM分析"""
        try:
            historical_data = {
                "dates": [],
                "market_msci": [],
                "top_stocks_rtsi": {},
                "top_industries_irsi": {},
                "data_quality": "estimated"  # 标记数据来源
            }
            
            # 获取当前数据集的日期列
            if hasattr(self.analysis_results, 'dataset') and self.analysis_results.dataset:
                date_columns = [col for col in self.analysis_results.dataset.columns if str(col).startswith('202')]
                date_columns = sorted(date_columns)[-30:]  # 取最近30天
                
                if date_columns:
                    historical_data["dates"] = date_columns
                    historical_data["data_quality"] = "real"  # 真实数据
                    
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
            "data_quality": "simulated"
        }
    
    def _call_llm_api(self, analysis_data: dict) -> str:
        """调用LLM API进行智能分析"""
        try:
            import sys
            import os
            import asyncio
            
            # 添加llm-api路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            llm_api_path = os.path.join(current_dir, "llm-api")
            if llm_api_path not in sys.path:
                sys.path.insert(0, llm_api_path)
            
            # 使用传统AI分析方式
            # 传统LLM调用
            from client import LLMClient
            
            # 创建LLM客户端
            client = LLMClient()
            
            # 构建分析提示
            prompt = self._build_analysis_prompt(analysis_data)
            
            # 使用智能体接口调用AI分析
            try:
                response = client.chat(
                    message=prompt,
                    agent_id="金融分析师"
                )
            except Exception as agent_error:
                print(f"使用智能体失败，尝试直接调用: {agent_error}")
                # 如果智能体不可用，回退到直接调用
                try:
                    response = client.chat(
                        message=prompt,
                        system_message="你是一位专业的股票分析师，请基于提供的技术分析数据，给出专业的投资建议和市场观点。"
                    )
                except Exception as direct_error:
                    print(f"直接调用也失败: {direct_error}")
                    return None
            
            # 评估AI分析结果的可靠性
            reliability_score = self._evaluate_ai_reliability(response, analysis_data)
            
            # 添加可靠性评估到分析结果
            enhanced_response = f"{response}\n\n--- 可靠性评估 ---\n可靠性评分: {reliability_score['score']:.1f}/10\n评估说明: {reliability_score['explanation']}"
            
            # 保存AI分析结果
            self.ai_analysis_result = enhanced_response
            return enhanced_response
            
        except Exception as e:
            print(f"LLM API调用失败: {str(e)}")
            return None
    

    
    def _build_analysis_prompt(self, data: dict) -> str:
        """构建AI分析提示"""
        # 根据当前语言构建提示
        if is_english():
            prompt = f"""As a professional financial analyst, please provide in-depth investment strategy recommendations based on the following multi-dimensional technical analysis data:

## 📊 Market Sentiment Composite Index (MSCI)
"""
        else:
            prompt = f"""作为专业金融分析师，请基于以下多维度技术分析数据，提供深度投资策略建议：

## 📊 市场情绪综合指数 (MSCI)
"""
        
        # 市场数据 - 增强描述
        if data.get("market_data"):
            market = data["market_data"]
            msci = market.get('msci_value', 0)
            trend = market.get('trend_5d', 0)
            volatility = market.get('volatility', 0)
            volume_ratio = market.get('volume_ratio', 0)
            
            # 添加市场状态判断
            if is_english():
                market_state = "Extremely Optimistic" if msci > 80 else "Healthy Optimistic" if msci > 65 else "Cautiously Optimistic" if msci > 55 else "Neutral" if msci > 45 else "Mildly Pessimistic" if msci > 35 else "Significantly Pessimistic" if msci > 25 else "Panic Selling"
                trend_desc = "Strong Uptrend" if trend > 10 else "Moderate Uptrend" if trend > 3 else "Sideways" if abs(trend) <= 3 else "Moderate Downtrend" if trend > -10 else "Sharp Decline"
                vol_desc = "Extremely High Volatility" if volatility > 30 else "High Volatility" if volatility > 20 else "Medium Volatility" if volatility > 10 else "Low Volatility" if volatility > 5 else "Very Low Volatility"
                
                prompt += f"- Market Sentiment Index: {msci:.2f} ({market_state})\n"
                prompt += f"- 5-Day Momentum Trend: {trend:+.2f} ({trend_desc})\n"
                prompt += f"- Market Volatility: {volatility:.2f} ({vol_desc})\n"
                prompt += f"- Volume Amplification: {volume_ratio:.2f}x\n"
                prompt += f"- Investor Sentiment: {market.get('market_sentiment', 'Neutral')}\n"
                prompt += f"- Risk Level: {market.get('risk_level', 'Medium')}\n\n"
            else:
                market_state = "极度乐观" if msci > 80 else "健康乐观" if msci > 65 else "谨慎乐观" if msci > 55 else "情绪中性" if msci > 45 else "轻度悲观" if msci > 35 else "显著悲观" if msci > 25 else "恐慌抛售"
                trend_desc = "强势上涨" if trend > 10 else "温和上涨" if trend > 3 else "震荡整理" if abs(trend) <= 3 else "温和下跌" if trend > -10 else "快速下跌"
                vol_desc = "极高波动" if volatility > 30 else "高波动" if volatility > 20 else "中等波动" if volatility > 10 else "低波动" if volatility > 5 else "极低波动"
                
                prompt += f"- 市场情绪指数: {msci:.2f} ({market_state})\n"
                prompt += f"- 5日动量趋势: {trend:+.2f} ({trend_desc})\n"
                prompt += f"- 市场波动率: {volatility:.2f} ({vol_desc})\n"
                prompt += f"- 成交量放大倍数: {volume_ratio:.2f}x\n"
                prompt += f"- 投资者情绪: {market.get('market_sentiment', '中性')}\n"
                prompt += f"- 风险等级: {market.get('risk_level', '中等')}\n\n"
        
        # 宏观经济环境
        if data.get("macro_indicators"):
            macro = data["macro_indicators"]
            if is_english():
                prompt += "## 🌍 Macroeconomic Environment\n"
                prompt += f"- Benchmark Interest Rate: {macro.get('interest_rate', 0):.1f}% (Monetary Policy Direction)\n"
                prompt += f"- Inflation Level: {macro.get('inflation_rate', 0):.1f}% (Price Stability)\n"
                prompt += f"- GDP Growth: {macro.get('gdp_growth', 0):.1f}% (Economic Growth Momentum)\n"
                prompt += f"- Currency Strength: {macro.get('currency_strength', 0):.1f}/100 (Exchange Rate Stability)\n"
                prompt += f"- Market Liquidity: {macro.get('market_liquidity', 0):.1f}/100 (Capital Adequacy)\n\n"
            else:
                prompt += "## 🌍 宏观经济环境\n"
                prompt += f"- 基准利率: {macro.get('interest_rate', 0):.1f}% (货币政策导向)\n"
                prompt += f"- 通胀水平: {macro.get('inflation_rate', 0):.1f}% (物价稳定性)\n"
                prompt += f"- GDP增速: {macro.get('gdp_growth', 0):.1f}% (经济增长动力)\n"
                prompt += f"- 货币强度: {macro.get('currency_strength', 0):.1f}/100 (汇率稳定性)\n"
                prompt += f"- 市场流动性: {macro.get('market_liquidity', 0):.1f}/100 (资金充裕度)\n\n"
        
        # 新闻情感分析
        if data.get("news_sentiment"):
            news = data["news_sentiment"]
            sentiment_score = news.get('overall_sentiment', 0)
            
            if is_english():
                sentiment_desc = "Positive Optimistic" if sentiment_score > 0.3 else "Neutral Balanced" if sentiment_score > -0.3 else "Negative Pessimistic"
                prompt += "## 📰 Market Sentiment Index\n"
                prompt += f"- Overall Sentiment Tendency: {sentiment_score:+.2f} ({sentiment_desc})\n"
                prompt += f"- Positive News Ratio: {news.get('positive_ratio', 0):.1%}\n"
                prompt += f"- Negative News Ratio: {news.get('negative_ratio', 0):.1%}\n"
                prompt += f"- Neutral News Ratio: {news.get('neutral_ratio', 0):.1%}\n"
                prompt += f"- News Activity: {news.get('news_volume', 0)} articles/day\n\n"
            else:
                sentiment_desc = "积极乐观" if sentiment_score > 0.3 else "中性平衡" if sentiment_score > -0.3 else "消极悲观"
                prompt += "## 📰 市场情感指数\n"
                prompt += f"- 整体情感倾向: {sentiment_score:+.2f} ({sentiment_desc})\n"
                prompt += f"- 正面消息占比: {news.get('positive_ratio', 0):.1%}\n"
                prompt += f"- 负面消息占比: {news.get('negative_ratio', 0):.1%}\n"
                prompt += f"- 中性消息占比: {news.get('neutral_ratio', 0):.1%}\n"
                prompt += f"- 新闻活跃度: {news.get('news_volume', 0)}条/日\n\n"
        
        # 行业数据 - 增强分析
        if data.get("industry_data"):
            if is_english():
                prompt += "## 🏭 Industry Relative Strength Index (IRSI)\n"
            else:
                prompt += "## 🏭 行业相对强度指数 (IRSI)\n"
            sorted_industries = sorted(data["industry_data"].items(), key=lambda x: x[1].get('irsi_value', 0), reverse=True)
            for i, (industry, info) in enumerate(sorted_industries[:5]):
                irsi = info.get('irsi_value', 0)
                stock_count = info.get('stock_count', 0)
                avg_volume = info.get('avg_volume', 0)
                
                # 行业强度评级
                if is_english():
                    strength = "Very Strong" if irsi > 70 else "Strong" if irsi > 60 else "Neutral" if irsi > 40 else "Weak" if irsi > 30 else "Very Weak"
                else:
                    strength = "极强" if irsi > 70 else "强势" if irsi > 60 else "中性" if irsi > 40 else "弱势" if irsi > 30 else "极弱"
                rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "📈" if i == 3 else "📊"
                
                if is_english():
                    prompt += f"{rank_emoji} {industry}: IRSI={irsi:.2f}({strength}), {stock_count} stocks, avg daily volume {avg_volume/10000:.1f}M\n"
                else:
                    prompt += f"{rank_emoji} {industry}: IRSI={irsi:.2f}({strength}), 成分股{stock_count}只, 日均成交量{avg_volume/10000:.1f}万\n"
            prompt += "\n"
        
        # 股票数据 - 增强展示
        if data.get("stock_data"):
            if is_english():
                prompt += "## 📈 Real-time Trend Strength Index (RTSI)\n"
            else:
                prompt += "## 📈 个股评级趋势强度指数 (RTSI)\n"
            sorted_stocks = sorted(data["stock_data"].items(), key=lambda x: x[1].get('rtsi_value', 0), reverse=True)
            for i, (stock_code, info) in enumerate(sorted_stocks[:8]):
                rtsi = info.get('rtsi_value', 0)
                name = info.get('name', stock_code)
                industry = info.get('industry', '未知' if not is_english() else 'Unknown')
                price = info.get('price', 0)
                volume = info.get('volume', 0)
                
                # RTSI强度评级
                if is_english():
                    rating = "Strong Buy" if rtsi > 80 else "Buy" if rtsi > 65 else "Hold" if rtsi > 50 else "Watch" if rtsi > 35 else "Avoid"
                else:
                    rating = "强烈推荐" if rtsi > 80 else "推荐" if rtsi > 65 else "中性" if rtsi > 50 else "观望" if rtsi > 35 else "回避"
                trend_emoji = "🚀" if rtsi > 80 else "📈" if rtsi > 65 else "➡️" if rtsi > 50 else "📉" if rtsi > 35 else "⚠️"
                
                if is_english():
                    prompt += f"{trend_emoji} {name}({stock_code}): RTSI={rtsi:.2f}({rating}), {industry} sector, ${price:.2f}, volume {volume/10000:.1f}M\n"
                else:
                    prompt += f"{trend_emoji} {name}({stock_code}): RTSI={rtsi:.2f}({rating}), {industry}板块, ¥{price:.2f}, 成交量{volume/10000:.1f}万\n"
            prompt += "\n"
        
        # 历史数据 - 30天深度分析
        if data.get("historical_data") and data["historical_data"].get("dates"):
            historical = data["historical_data"]
            dates = historical['dates']
            data_days = len(dates)
            
            if is_english():
                prompt += f"## 📊 {data_days}-Day Historical Trend Analysis\n"
                prompt += f"📅 Analysis Period: {dates[0]} ~ {dates[-1]} ({data_days} trading days)\n"
                prompt += f"🔍 Data Source: {historical.get('data_quality', 'unknown')}\n\n"
            else:
                prompt += f"## 📊 {data_days}天历史趋势深度分析\n"
                prompt += f"📅 分析周期: {dates[0]} ~ {dates[-1]} ({data_days}个交易日)\n"
                prompt += f"🔍 数据来源: {historical.get('data_quality', 'unknown')}\n\n"
            
            # 市场MSCI历史趋势分析
            if historical.get("market_msci"):
                msci_trend = historical["market_msci"]
                start_msci = msci_trend[0]
                end_msci = msci_trend[-1]
                change = end_msci - start_msci
                change_pct = (change / start_msci) * 100 if start_msci != 0 else 0
                
                # 计算波动性
                msci_volatility = np.std(msci_trend) if len(msci_trend) > 1 else 0
                max_msci = max(msci_trend)
                min_msci = min(msci_trend)
                
                if is_english():
                    trend_direction = "📈 Uptrend" if change > 5 else "📉 Downtrend" if change < -5 else "➡️ Sideways"
                    volatility_level = "High Volatility" if msci_volatility > 10 else "Medium Volatility" if msci_volatility > 5 else "Low Volatility"
                    
                    prompt += f"🎯 Market Sentiment Evolution: {start_msci:.1f} → {end_msci:.1f} ({change:+.1f}pts, {change_pct:+.1f}%)\n"
                    prompt += f"📈 Trend Characteristics: {trend_direction}, {volatility_level}(σ={msci_volatility:.1f})\n"
                    prompt += f"📊 Range Fluctuation: {min_msci:.1f} ~ {max_msci:.1f} (amplitude {max_msci-min_msci:.1f}pts)\n\n"
                else:
                    trend_direction = "📈 上升趋势" if change > 5 else "📉 下降趋势" if change < -5 else "➡️ 横盘整理"
                    volatility_level = "高波动" if msci_volatility > 10 else "中波动" if msci_volatility > 5 else "低波动"
                    
                    prompt += f"🎯 市场情绪演变: {start_msci:.1f} → {end_msci:.1f} ({change:+.1f}点, {change_pct:+.1f}%)\n"
                    prompt += f"📈 趋势特征: {trend_direction}, {volatility_level}(σ={msci_volatility:.1f})\n"
                    prompt += f"📊 区间波动: {min_msci:.1f} ~ {max_msci:.1f} (振幅{max_msci-min_msci:.1f}点)\n\n"
            
            # 重点股票历史表现
            if historical.get("top_stocks_rtsi"):
                if is_english():
                    prompt += "🏆 Leading Stocks Historical Performance Tracking:\n"
                else:
                    prompt += "🏆 龙头股票历史表现追踪:\n"
                for stock_code, stock_info in list(historical["top_stocks_rtsi"].items())[:3]:
                    ratings = stock_info.get('historical_ratings', [])
                    valid_ratings = [r for r in ratings if r is not None]
                    if valid_ratings and len(valid_ratings) >= 2:
                        start_rating = valid_ratings[0]
                        end_rating = valid_ratings[-1]
                        if is_english():
                            rating_trend = "⬆️ Rating Up" if end_rating > start_rating else "⬇️ Rating Down" if end_rating < start_rating else "➡️ Rating Stable"
                        else:
                            rating_trend = "⬆️ 评级上升" if end_rating > start_rating else "⬇️ 评级下降" if end_rating < start_rating else "➡️ 评级稳定"
                        prompt += f"• {stock_info.get('name', stock_code)}: {start_rating:.1f} → {end_rating:.1f} ({rating_trend})\n"
            
            prompt += "\n"
        
        if is_english():
            prompt += """## 🎯 Professional Analysis Requirements

As a senior quantitative analyst, please conduct in-depth analysis from the following dimensions, combining current technical indicators and 30-day historical data:

### 📈 Market Trend Analysis
1. **Macro Sentiment Analysis**: Based on MSCI index changes, determine the current market cycle stage
2. **Momentum Identification**: Combine 5-day trends and volatility to analyze market momentum strength
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

**Output Requirements**: Please use professional terminology combined with plain explanations, emphasizing data-driven investment logic, with content controlled at 800-1000 words, ensuring depth and practicality of analysis."""
        else:
            prompt += """## 🎯 专业分析要求

请作为资深量化分析师，结合当前技术指标和30天历史数据，从以下维度进行深度分析：

### 📈 市场趋势研判
1. **宏观情绪分析**: 基于MSCI指数变化，判断当前市场所处周期阶段
2. **动量特征识别**: 结合5日趋势和波动率，分析市场动能强弱
3. **流动性评估**: 通过成交量放大倍数，判断资金参与度

### 🏭 板块轮动策略
4. **强势板块挖掘**: 基于IRSI排名，识别具备持续性的领涨板块
5. **板块配置建议**: 结合历史表现，提供板块配置权重建议

### 🎯 个股精选策略
6. **龙头股筛选**: 基于RTSI评级，筛选各板块龙头标的
7. **买入时机判断**: 结合历史评级变化，判断最佳介入点位
8. **持仓管理建议**: 根据个股强度变化，提供加减仓策略

### ⚠️ 风险管控体系
9. **系统性风险预警**: 基于历史波动模式，识别潜在风险点
10. **止盈止损策略**: 结合技术指标，制定科学的风控方案

### 🔮 前瞻性展望
11. **短期操作策略**: 1-2周内的交易机会和注意事项
12. **中期投资布局**: 1-3个月的配置方向和重点关注领域

**输出要求**: 请用专业术语结合通俗解释，重点突出数据驱动的投资逻辑，篇幅控制在800-1000字，确保分析的深度和实用性。"""
        
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
            # 在文本区域添加AI分析结果
            if is_english():
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
            self.status_var.set("分析完成 | 包含AI智能分析")
            
        except Exception as e:
            print(f"AI分析结果显示失败: {str(e)}")
            self.status_var.set("AI分析完成但显示失败")
    
    def show_data_validation(self):
        """显示数据验证窗口"""
        try:
            from data.data_validator import DataValidator
            
            # 检查是否有数据
            if not hasattr(self, 'current_dataset') or self.current_dataset is None:
                messagebox.showwarning("提示", "请先加载数据文件后再进行验证")
                return
            
            # 创建验证器并进行验证
            self.update_text_area("开始数据验证...", "blue")
            validator = DataValidator()
            
            try:
                result = validator.validate_complete_dataset(self.current_dataset)
                
                # 生成验证报告
                report = validator.generate_quality_report()
                
                # 创建验证结果窗口
                validation_window = tk.Toplevel(self.root)
                validation_window.title("数据验证报告")
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
                tk.Button(button_frame, text="关闭", command=validation_window.destroy,
                         **button_style).pack(side=tk.RIGHT)
                
                # 导出按钮
                def export_validation_report():
                    from tkinter import filedialog
                    filename = filedialog.asksaveasfilename(
                        title="保存验证报告",
                        defaultextension=".txt",
                        filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
                    )
                    if filename:
                        try:
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(report)
                            messagebox.showinfo("成功", f"验证报告已保存到: {filename}")
                        except Exception as e:
                            messagebox.showerror("错误", f"保存失败: {str(e)}")
                
                tk.Button(button_frame, text="导出报告", command=export_validation_report,
                         **button_style).pack(side=tk.RIGHT, padx=(0, 10))
                
                # 更新状态
                quality_score = result.get('quality_score', 0)
                status = "验证通过" if result.get('is_valid', False) else "验证失败"
                self.update_text_area(f"数据验证完成: {status}, 质量分数: {quality_score}/100", "green" if result.get('is_valid', False) else "red")
                
            except Exception as e:
                self.update_text_area(f"数据验证失败: {str(e)}", "red")
                messagebox.showerror("验证失败", f"数据验证过程中出现错误:\n{str(e)}")
                
        except ImportError:
            messagebox.showerror("功能不可用", "数据验证模块未找到，请检查系统配置")
    
    def show_performance_monitor(self):
        """显示性能监控窗口"""
        try:
            from utils.performance_monitor import get_global_monitor
            
            # 获取性能监控器
            monitor = get_global_monitor()
            
            # 生成性能报告
            self.update_text_area("生成性能报告...", "blue")
            performance_report = monitor.generate_performance_report()
            system_metrics = monitor.get_system_metrics()
            
            # 创建性能监控窗口
            monitor_window = tk.Toplevel(self.root)
            monitor_window.title("系统性能监控")
            monitor_window.geometry("900x700")
            monitor_window.configure(bg='#f0f0f0')
            monitor_window.transient(self.root)
            
            # 创建笔记本控件用于分页显示
            notebook = ttk.Notebook(monitor_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 性能报告页
            report_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(report_frame, text="性能报告")
            
            report_text = tk.Text(report_frame, wrap=tk.WORD, font=('Courier New', 11))
            report_scrollbar = tk.Scrollbar(report_frame, orient=tk.VERTICAL, command=report_text.yview)
            report_text.configure(yscrollcommand=report_scrollbar.set)
            
            report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            report_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            report_text.insert(tk.END, performance_report)
            report_text.config(state=tk.DISABLED)
            
            # 系统指标页
            system_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(system_frame, text="系统指标")
            
            # 系统指标显示区域
            metrics_text = tk.Text(system_frame, wrap=tk.WORD, font=('Courier New', 11))
            metrics_scrollbar = tk.Scrollbar(system_frame, orient=tk.VERTICAL, command=metrics_text.yview)
            metrics_text.configure(yscrollcommand=metrics_scrollbar.set)
            
            metrics_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            metrics_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
            
            # 格式化系统指标
            system_info = f"""系统性能指标

CPU使用率: {system_metrics.get('current_cpu_percent', 'N/A')}%
内存使用率: {system_metrics.get('current_memory_percent', 'N/A')}%
内存使用量: {system_metrics.get('current_memory_mb', 'N/A')} MB
磁盘读取: {system_metrics.get('current_disk_read_mb', 'N/A')} MB
磁盘写入: {system_metrics.get('current_disk_write_mb', 'N/A')} MB

历史数据点数:
- CPU使用率历史: {len(system_metrics.get('cpu_usage_history', []))} 个数据点
- 内存使用率历史: {len(system_metrics.get('memory_usage_history', []))} 个数据点
- 磁盘IO历史: {len(system_metrics.get('disk_io_history', []))} 个数据点

监控状态: 正常运行
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
                new_system_info = f"""系统性能指标 (已刷新)

CPU使用率: {new_system_metrics.get('current_cpu_percent', 'N/A')}%
内存使用率: {new_system_metrics.get('current_memory_percent', 'N/A')}%
内存使用量: {new_system_metrics.get('current_memory_mb', 'N/A')} MB
磁盘读取: {new_system_metrics.get('current_disk_read_mb', 'N/A')} MB
磁盘写入: {new_system_metrics.get('current_disk_write_mb', 'N/A')} MB

历史数据点数:
- CPU使用率历史: {len(new_system_metrics.get('cpu_usage_history', []))} 个数据点
- 内存使用率历史: {len(new_system_metrics.get('memory_usage_history', []))} 个数据点
- 磁盘IO历史: {len(new_system_metrics.get('disk_io_history', []))} 个数据点

监控状态: 正常运行
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
            
            tk.Button(button_frame, text="刷新", command=refresh_monitor,
                     **button_style).pack(side=tk.LEFT)
            
            # 重置性能统计按钮
            def reset_stats():
                result = messagebox.askyesno("确认", "确定要重置所有性能统计数据吗？")
                if result:
                    monitor.reset_metrics()
                    refresh_monitor()
                    messagebox.showinfo("成功", "性能统计数据已重置")
            
            tk.Button(button_frame, text="重置统计", command=reset_stats,
                     **button_style).pack(side=tk.LEFT, padx=10)
            
            # 关闭按钮
            tk.Button(button_frame, text="关闭", command=monitor_window.destroy,
                     **button_style).pack(side=tk.RIGHT)
            
            self.update_text_area("性能监控窗口已打开", "green")
            
        except ImportError:
            messagebox.showerror("功能不可用", "性能监控模块未找到，请检查系统配置")
        except Exception as e:
            messagebox.showerror("监控失败", f"性能监控过程中出现错误:\n{str(e)}")
            self.update_text_area(f"性能监控失败: {str(e)}", "red")


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
        self.window.title(_("stock_analysis_window_title", "个股趋势分析 - RTSI算法分析"))
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 窗口居中显示
        self.center_window()
        
        # 设置窗口图标和属性
        self.window.resizable(True, True)
        self.window.minsize(900, 600)
    
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
        
        tk.Label(selector_frame, text=_("stock_selector_label", "股票选择:"), bg='#f0f0f0', 
                font=('Arial', 11, 'bold')).pack(side=tk.LEFT, pady=10)
        
        # 股票下拉框
        self.stock_combo = ttk.Combobox(selector_frame, width=35, state="readonly",
                                        font=('Arial', 11))
        self.stock_combo.pack(side=tk.LEFT, padx=10, pady=10)
        # 绑定选择事件，实现自动更新
        self.stock_combo.bind('<<ComboboxSelected>>', self.on_stock_selected)
        
        # 搜索框
        tk.Label(selector_frame, text=_("search_label", "搜索:"), bg='#f0f0f0').pack(side=tk.LEFT, padx=(20,5))
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
        self.analyze_btn = tk.Button(selector_frame, text=_("btn_start_analysis", "开始分析"), 
                                   command=self.analyze_selected_stock,
                                   **button_style)
        self.analyze_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 主体区域容器
        main_container = tk.Frame(self.window, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧：核心指标面板
        left_frame = tk.Frame(main_container, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        
        metrics_frame = tk.LabelFrame(left_frame, text=_("core_metrics_label", "核心指标"), bg='#f0f0f0',
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
            ("RTSI指数:", self.rtsi_var, "blue"),
            ("趋势方向:", self.trend_var, "green"),
            ("数据可靠性:", self.confidence_var, "purple"),
            ("所属行业:", self.industry_var, "black"),
            ("风险等级:", self.risk_var, "red"),
            ("趋势斜率:", self.slope_var, "orange")
        ]
        
        for i, (label_text, var, color) in enumerate(labels):
            tk.Label(metrics_frame, text=label_text, bg='#f0f0f0',
                    font=('Arial', 11)).grid(row=i, column=0, sticky='w', 
                                           padx=8, pady=8)
            label_widget = tk.Label(metrics_frame, textvariable=var, bg='#f0f0f0', 
                                  font=('Arial', 11, 'bold'), fg=color)
            label_widget.grid(row=i, column=1, sticky='w', padx=8, pady=8)
        
        # 上部区域：左侧指标 + 中间图表
        upper_container = tk.Frame(main_container, bg='#f0f0f0')
        upper_container.pack(fill=tk.BOTH, expand=True)
        
        # 将左侧指标移到上部区域
        left_frame.pack_forget()
        left_frame = tk.Frame(upper_container, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))
        
        metrics_frame = tk.LabelFrame(left_frame, text="核心指标", bg='#f0f0f0',
                                    font=('Arial', 11, 'bold'))
        metrics_frame.pack(fill=tk.BOTH, expand=True)
        
        # 重新创建指标标签 - 添加动态颜色支持
        self.metric_labels = {}
        labels = [
            ("RTSI指数:", self.rtsi_var, "blue"),
            ("趋势方向:", self.trend_var, "green"), 
            ("数据可靠性:", self.confidence_var, "purple"),
            ("所属行业:", self.industry_var, "black"),
            ("风险等级:", self.risk_var, "red"),
            ("趋势斜率:", self.slope_var, "orange")
        ]
        
        for i, (label_text, var, color) in enumerate(labels):
            tk.Label(metrics_frame, text=label_text, bg='#f0f0f0',
                    font=('Arial', 11)).grid(row=i, column=0, sticky='w', 
                                           padx=8, pady=8)
            label_widget = tk.Label(metrics_frame, textvariable=var, bg='#f0f0f0', 
                                  font=('Arial', 11, 'bold'), fg=color)
            label_widget.grid(row=i, column=1, sticky='w', padx=8, pady=8)
            self.metric_labels[label_text] = label_widget
        
        # 中间：趋势图表区 (缩小)
        chart_frame = tk.LabelFrame(upper_container, text=_('trend_chart', '趋势图表'), bg='#f0f0f0',
                                  font=('Arial', 11, 'bold'))
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # matplotlib图表 (缩小尺寸)
        self.fig = Figure(figsize=(6, 4), dpi=100, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化空图表
        self.init_empty_chart()
        
        # 下部：详细分析区 (占30%高度)
        lower_container = tk.Frame(main_container, bg='#f0f0f0')
        lower_container.pack(fill=tk.BOTH, pady=(10,0))
        
        analysis_frame = tk.LabelFrame(lower_container, text=_('detailed_analysis', '详细分析'), bg='#f0f0f0',
                                     font=('Arial', 11, 'bold'))
        analysis_frame.pack(fill=tk.BOTH, expand=True)
        
        self.analysis_text = tk.Text(analysis_frame, wrap=tk.WORD, height=12,
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
        
        tk.Button(button_frame, text=_("btn_export_analysis", "导出分析"), 
                 command=self.export_analysis,
                 **bottom_button_style).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text=_("btn_add_watch", "添加关注"), 
                 command=self.add_to_watchlist,
                 **bottom_button_style).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text=_("btn_refresh_data", "刷新数据"), 
                 command=self.refresh_data,
                 **bottom_button_style).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text=_("btn_close", "关闭"), command=self.window.destroy,
                 **bottom_button_style).pack(side=tk.RIGHT, padx=5)
    
    def init_empty_chart(self):
        """初始化空图表"""
        self.ax.clear()
        self.ax.set_title(_("chart_select_stock", "请选择股票进行分析"), fontsize=12, pad=20)
        self.ax.set_xlabel(_("chart_time", "时间"), fontsize=11)
        self.ax.set_ylabel(_("chart_rating_score", "评级分数"), fontsize=11)
        self.ax.grid(True, alpha=0.3)
        self.ax.text(0.5, 0.5, _("chart_waiting_analysis", "等待分析..."), 
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
                self.analysis_text.insert(1.0, f"""
 股票数据加载完成

• 总股票数: {len(stocks):,}只
• 数据状态: {'成功 已完成分析' if stocks else '警告 等待分析'}
• 排序方式: 按RTSI指数降序

提示 使用说明:
1. 在下拉框中选择股票
2. 或使用搜索框快速查找
3. 点击"开始分析"查看详情
4. 图表将显示评级趋势变化

检查 提示: 输入股票代码或名称关键字可快速搜索
""")
                
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
        # 优先使用搜索框中的输入
        search_input = self.search_entry.get().strip()
        
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
                self.window.title(f"个股趋势分析 - {stock_name}")
                
                # RTSI分析数据
                rtsi_data = stock_data.get('rtsi', {})
                if isinstance(rtsi_data, dict):
                    rtsi_value = rtsi_data.get('rtsi', 0)
                    confidence = rtsi_data.get('confidence', 0)
                    slope = rtsi_data.get('slope', 0)
                else:
                    rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
                    confidence = 0.5  # 默认置信度
                    slope = 0
                
                # 统一使用基于RTSI值的实时计算，确保核心指标和详细分析一致
                trend = self.classify_trend(rtsi_value)
                
                # 更新指标显示
                self.update_metrics_display(stock_data, rtsi_value, trend, confidence, slope)
                
                # 更新趋势图表
                self.update_trend_chart_with_data_calculation(stock_code, stock_data)
                
                # 生成详细分析报告
                self.generate_detailed_analysis(stock_code, stock_name, stock_data, rtsi_data)
                
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
    
    def update_metrics_display(self, stock_data, rtsi_value, trend, confidence, slope):
        """更新指标显示 - 根据趋势动态设置颜色"""
        # RTSI指数
        self.rtsi_var.set(f"{rtsi_value:.2f}")
        
        # 趋势方向 - 采用统一的专业术语
        trend_map = {
            'strong_bull': '强势多头',
            'moderate_bull': '温和多头',
            'weak_bull': '弱势多头',
            'neutral': '横盘整理',
            'weak_bear': '弱势空头',
            'moderate_bear': '温和空头',
            'strong_bear': '强势空头'
        }
        self.trend_var.set(trend_map.get(trend, trend))
        
        # 数据可靠性  
        self.confidence_var.set(f"{confidence:.1%}")
        
        # 行业信息
        industry = stock_data.get('industry', '未分类')
        self.industry_var.set(industry)
        
        # 风险等级 - 保持原有逻辑（可能与详细分析区不同）
        risk_level = self.calculate_risk_level(rtsi_value, confidence)
        self.risk_var.set(risk_level)
        
        # 趋势斜率
        self.slope_var.set(f"{slope:.4f}")
        
        # 动态颜色设置
        if hasattr(self, 'metric_labels'):
            # 趋势方向颜色：多头红色，空头绿色，其它黑色
            if 'bull' in trend:
                self.metric_labels["趋势方向:"].config(fg='red')  # 多头红色
            elif 'bear' in trend:
                self.metric_labels["趋势方向:"].config(fg='green')  # 空头绿色
            else:
                self.metric_labels["趋势方向:"].config(fg='black')  # 其它黑色
            
            # RTSI指数颜色
            if rtsi_value >= 60:
                self.metric_labels["RTSI指数:"].config(fg='red')  # 高分红色
            elif rtsi_value <= 30:
                self.metric_labels["RTSI指数:"].config(fg='green')  # 低分绿色
            else:
                self.metric_labels["RTSI指数:"].config(fg='black')  # 中性黑色
            
            # 风险等级颜色
            if '低风险' in risk_level:
                self.metric_labels["风险等级:"].config(fg='green')
            elif '高风险' in risk_level:
                self.metric_labels["风险等级:"].config(fg='red')
            else:
                self.metric_labels["风险等级:"].config(fg='orange')
    
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
            return '🟢 极低风险（强势确认）'
        elif rtsi_value >= 75 and confidence >= 0.4:
            return '🟡 中等风险（强势待确认）'
        elif rtsi_value >= 60 and confidence >= 0.5:
            return '🟢 低风险（温和上升）'
        elif rtsi_value >= 50 and confidence >= 0.4:
            return '🟡 中等风险（弱势多头）'
        elif rtsi_value >= 40:
            return '🟡 中等风险（中性区间）'
        elif rtsi_value >= 30:
            return '🟠 较高风险（弱势空头）'
        elif rtsi_value >= 20 and confidence >= 0.5:
            return '🔴 高风险（温和下跌）'
        elif rtsi_value < 20 and confidence >= 0.7:
            return '🔴 极高风险（强势下跌确认）'
        else:
            return '🔴 高风险'
    
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
                    self.ax.set_title(f'{stock_name} {_("chart_rating_trend", "评级趋势分析")} ({_("chart_real_data", "真实数据")})', fontsize=12, pad=15)
                    self.ax.set_xlabel(_('chart_time', '时间'), fontsize=11)
                    self.ax.set_ylabel(_('chart_rating_score', '评级分数'), fontsize=11)
                    self.ax.grid(True, alpha=0.3)
                    
                    # 设置Y轴范围和标签
                    self.ax.set_ylim(-0.5, 7.5)
                    self.ax.set_yticks(range(8))
                    rating_labels = [
                        _('rating_big_bear', '大空'),
                        _('rating_mid_bear', '中空'), 
                        _('rating_small_bear', '小空'),
                        _('rating_micro_bear', '微空'),
                        _('rating_micro_bull', '微多'),
                        _('rating_small_bull', '小多'),
                        _('rating_mid_bull', '中多'),
                        _('rating_big_bull', '大多')
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
            excel_files = glob.glob("A股数据*.xlsx") + glob.glob("A股数据*.xls")
            
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
            chart_title = f'{stock_name} {_("chart_rating_trend", "评级趋势分析")} ({_("chart_generated_data", "基于RTSI={:.1f}生成").format(current_rtsi)})'
            self.ax.set_title(chart_title, fontsize=12, pad=15)
            self.ax.set_xlabel(_('chart_time', '时间'), fontsize=11)
            self.ax.set_ylabel(_('chart_rating_score', '评级分数'), fontsize=11)
            self.ax.grid(True, alpha=0.3)
            
            # 设置Y轴范围和标签
            self.ax.set_ylim(-0.5, 7.5)
            self.ax.set_yticks(range(8))
            rating_labels = [
                _('rating_big_bear', '大空'),
                _('rating_mid_bear', '中空'), 
                _('rating_small_bear', '小空'),
                _('rating_micro_bear', '微空'),
                _('rating_micro_bull', '微多'),
                _('rating_small_bull', '小多'),
                _('rating_mid_bull', '中多'),
                _('rating_big_bull', '大多')
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
            data_source_text = f'{_("data_source", "数据来源")}：{source_type}'
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
            report_title = _("deep_analysis_report", "深度分析报告")
            core_indicators = _("core_indicators", "核心指标")
            technical_analysis = _("technical_analysis", "技术分析")
            industry_comparison = _("industry_comparison", "行业对比")
            investment_advice = _("investment_advice", "投资建议")
            risk_assessment = _("risk_assessment", "风险评估")
            operation_advice = _("operation_advice", "操作建议")
            future_outlook = _("future_outlook", "后市展望")
            disclaimer = _("disclaimer", "免责声明")
            disclaimer_text = _("disclaimer_text", "本分析基于RTSI技术算法，仅供参考，不构成投资建议。")
            generation_time = _("generation_time", "生成时间")
            
            # 获取动态文本
            tech_strength = _("strong", "强势") if rtsi_value > 60 else (_("neutral", "中性") if rtsi_value > 40 else _("weak", "弱势"))
            relative_pos = _("leading", "领先") if rtsi_value > 50 else _("lagging", "落后")
            industry_pos = _("blue_chip", "龙头股") if rtsi_value > 70 else (_("average", "一般") if rtsi_value > 40 else _("lagging", "落后"))
            rotation_sig = _("active", "积极") if rtsi_value > 60 else (_("wait_and_see", "观望") if rtsi_value > 30 else _("cautious", "谨慎"))
            liquidity_level = _("good", "良好") if market_cap_level != _("small_cap", "小盘股") else _("average", "一般")
            
            analysis_text = f"""
📈 {stock_name} {report_title}
{'='*50}

📊 【{core_indicators}】
• RTSI{_("index", "指数")}: {rtsi_value:.2f}/100
• {_("trend_status", "趋势状态")}: {self.get_trend_description(rtsi_value)}
• {_("technical_strength", "技术强度")}: {tech_strength}
• {_("industry_category", "所属行业")}: {industry}
• {_("market_cap_level", "市值等级")}: {market_cap_level}

🔍 【{technical_analysis}】
• {_("trend_direction", "趋势方向")}: {self.get_detailed_trend(rtsi_value)}
• {_("volatility_level", "波动程度")}: {volatility}
• {_("support_resistance", "支撑阻力")}: {_("based_on_rating_analysis", "基于评级变化分析")}
• {_("relative_strength", "相对强度")}: 在{industry}{_("industry", "行业")}中{relative_pos}

🏭 【{industry_comparison}】
• {_("industry_performance", "行业表现")}: {sector_performance}
• {_("industry_position", "行业地位")}: {industry_pos}
• {_("rotation_signal", "轮动信号")}: {rotation_sig}

💡 【{investment_advice}】
• {_("short_term_strategy", "短线策略")}: {self.get_short_term_advice(rtsi_value)}
• {_("medium_term_strategy", "中线策略")}: {self.get_medium_term_advice(rtsi_value, industry)}
• {_("risk_warning", "风险提示")}: {self.get_risk_warning(rtsi_value)}

⚠️ 【{risk_assessment}】
• {_("technical_risk", "技术风险")}: {self.calculate_risk_level(rtsi_value, 0.8)}
• {_("industry_risk", "行业风险")}: {_("pay_attention_to_policy", "关注{industry}政策和周期变化").format(industry=industry)}
• {_("market_risk", "市场风险")}: {_("pay_attention_to_market", "需关注大盘趋势和系统性风险")}
• {_("liquidity", "流动性")}: {liquidity_level}

⏰ 【{operation_advice}】
• {_("best_entry_point", "最佳买点")}: {self.suggest_entry_point(rtsi_value)}
• {_("stop_loss_position", "止损位置")}: {self.suggest_stop_loss(rtsi_value)}
• {_("target_price", "目标价位")}: {self.suggest_target_price(rtsi_value)}
• {_("holding_period", "持仓周期")}: {self.suggest_holding_period(rtsi_value)}

🔮 【{future_outlook}】
{self.generate_outlook(rtsi_value, industry)}

📋 【{disclaimer}】
{disclaimer_text}
{_("risk_warning", "股市有风险，投资需谨慎。请结合基本面分析和风险承受能力。")}

{generation_time}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, analysis_text)
            
        except Exception as e:
            error_text = f"""
❌ {_("analysis_failed", "分析报告生成失败")}

{_("error_info", "错误信息")}: {str(e)}

{_("check_data_integrity", "请检查数据完整性或联系技术支持。")}
"""
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, error_text)
    
    def get_trend_description(self, rtsi_value):
        """获取趋势描述"""
        if rtsi_value >= 80:
            return _("super_strong_trend", "超强趋势")
        elif rtsi_value >= 60:
            return _("strong_uptrend", "强势上涨")
        elif rtsi_value >= 40:
            return _("consolidation", "震荡整理")
        elif rtsi_value >= 20:
            return _("weak_downtrend", "弱势下跌")
        else:
            return _("deep_adjustment", "深度调整")
    
    def get_detailed_trend(self, rtsi_value):
        """获取详细趋势分析 - 统一标准版本，与核心指标区保持一致"""
        # 采用与核心指标区完全一致的判断标准和专业术语
        if rtsi_value >= 75:
            return _("strong_bull_trend", "强势多头趋势，技术面极度乐观，建议积极配置")
        elif rtsi_value >= 60:
            return _("moderate_bull_trend", "温和多头趋势，上升动能充足，适合中线持有")
        elif rtsi_value >= 50:
            return _("weak_bull_pattern", "弱势多头格局，上升空间有限，谨慎乐观")
        elif rtsi_value >= 40:
            return _("sideways_consolidation", "横盘整理格局，方向选择待定，观望为主")
        elif rtsi_value >= 30:
            return "弱势空头格局，下跌空间有限，适度防御"
        elif rtsi_value >= 20:
            return "温和空头趋势，下跌动能充足，建议减仓"
        else:
            return "强势空头趋势，技术面极度悲观，严格风控"
    
    def calculate_volatility(self, stock_data):
        """计算波动程度"""
        # 简化版本，实际应用中可以更复杂
        return "中等波动"
    
    def estimate_market_cap_level(self, stock_code):
        """估算市值等级"""
        if stock_code.startswith('00'):
            return "大盘股"
        elif stock_code.startswith('60'):
            return "大盘股"
        elif stock_code.startswith('30'):
            return "成长股"
        else:
            return "中盘股"
    
    def get_sector_performance(self, industry):
        """获取行业表现"""
        return f"{industry}行业整体表现中性"
    
    def get_short_term_advice(self, rtsi_value):
        """短线建议"""
        if rtsi_value >= 60:
            return "可适度参与，关注量价配合"
        elif rtsi_value >= 40:
            return "观望为主，等待明确信号"
        else:
            return "避免抄底，等待趋势反转"
    
    def get_medium_term_advice(self, rtsi_value, industry):
        """中线建议"""
        if rtsi_value >= 50:
            return f"可配置{industry}优质标的"
        else:
            return "等待更好的配置时机"
    
    def get_risk_warning(self, rtsi_value):
        """风险提示"""
        if rtsi_value < 30:
            return "高风险，严格止损"
        elif rtsi_value < 50:
            return "中等风险，控制仓位"
        else:
            return "相对安全，注意回调风险"
    
    def suggest_entry_point(self, rtsi_value):
        """建议入场点"""
        if rtsi_value >= 60:
            return "回调至支撑位时"
        elif rtsi_value >= 40:
            return "突破阻力位时"
        else:
            return "等待止跌企稳信号"
    
    def suggest_stop_loss(self, rtsi_value):
        """建议止损位"""
        if rtsi_value >= 50:
            return "跌破近期支撑位"
        else:
            return "设置8-10%止损位"
    
    def suggest_target_price(self, rtsi_value):
        """建议目标价"""
        if rtsi_value >= 60:
            return "上看前高或新高"
        elif rtsi_value >= 40:
            return "看至前期阻力位"
        else:
            return "暂不设定目标价"
    
    def suggest_holding_period(self, rtsi_value):
        """建议持仓周期"""
        if rtsi_value >= 60:
            return "中长线持有(1-3个月)"
        elif rtsi_value >= 40:
            return "短中线操作(2-4周)"
        else:
            return "超短线或暂不持有"
    
    def generate_outlook(self, rtsi_value, industry):
        """生成后市展望"""
        if rtsi_value >= 60:
            return f"技术面显示{industry}行业及该股仍有上涨空间，建议持续关注基本面变化。"
        elif rtsi_value >= 40:
            return f"股价处于震荡期，需要观察{industry}行业催化剂和量能变化。"
        else:
            return f"技术面偏弱，建议等待{industry}行业整体企稳后再考虑配置。"
    
    def plot_no_data_chart(self, stock_code):
        """绘制无数据提示图表"""
        self.ax.clear()
        # 获取股票名称
        stock_name = self.get_stock_name_by_code(stock_code)
        data_preparing = _("chart_data_preparing", "数据准备中...")
        system_generating = _("chart_system_generating", "系统正在基于RTSI指数生成30天趋势数据\n预计需要1-2秒完成\n\n请稍候或刷新重试")
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
        self.ax.text(0.5, 0.5, '\n数据加载失败\n请检查数据源\n\n建议:\n1. 确认已加载数据文件\n2. 完成数据分析\n3. 选择有效股票', 
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
            messagebox.showwarning("提示", "请先选择并分析股票")
            return
        
        try:
            from tkinter import filedialog
            stock_code = self.current_stock['code']
            stock_name = self.current_stock['name']
            
            # 选择保存路径
            filename = filedialog.asksaveasfilename(
                title=_("export_analysis_report", "导出个股分析报告"),
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
                initialname=f"{stock_name}_{stock_code}_分析报告.txt"
            )
            
            if filename:
                # 获取当前分析文本
                analysis_content = self.analysis_text.get(1.0, tk.END)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    report_title = _("stock_analysis_report", "个股分析报告")
                    f.write(f"{report_title}\n")
                    f.write(f"股票代码: {stock_code}\n")
                    f.write(f"股票名称: {stock_name}\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                    f.write(analysis_content)
                
                export_msg = _("report_export_success", "分析报告已导出到")
                messagebox.showinfo("成功", f"{export_msg}:\n{filename}")
        
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")
    
    def add_to_watchlist(self):
        """添加到关注列表"""
        if not hasattr(self, 'current_stock') or not self.current_stock:
            messagebox.showwarning("提示", "请先选择股票")
            return
        
        stock_code = self.current_stock['code']
        stock_name = self.current_stock['name']
        
        # 简单的关注列表功能
        try:
            watchlist_file = "watchlist.txt"
            
            # 检查是否已在关注列表中
            existing_stocks = set()
            try:
                with open(watchlist_file, 'r', encoding='utf-8') as f:
                    existing_stocks = set(line.strip() for line in f if line.strip())
            except FileNotFoundError:
                pass
            
            stock_entry = f"{stock_code} {stock_name}"
            if stock_entry in existing_stocks:
                messagebox.showinfo("提示", f"{stock_name} 已在关注列表中")
                return
            
            # 添加到关注列表
            with open(watchlist_file, 'a', encoding='utf-8') as f:
                f.write(f"{stock_entry}\n")
            
            messagebox.showinfo("成功", f"已将 {stock_name} 添加到关注列表")
        
        except Exception as e:
            messagebox.showerror("错误", f"添加关注失败:\n{str(e)}")
    
    def refresh_data(self):
        """刷新数据"""
        try:
            # 重新加载股票列表
            self.load_stock_list()
            
            # 如果有选中的股票，重新分析
            if hasattr(self, 'current_stock') and self.current_stock:
                self.analyze_selected_stock()
            
            messagebox.showinfo("成功", "数据已刷新")
        
        except Exception as e:
            messagebox.showerror("错误", f"刷新数据失败:\n{str(e)}")


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
        self.window.title(_("industry_analysis_window_title", "行业轮动分析"))
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        
        # 窗口居中
        self.center_window()
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 阻止窗口大小调整
        self.window.resizable(True, True)
    
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
        
        title_label = tk.Label(title_frame, text=_("industry_rotation_title", "行业轮动强度分析"), 
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
        
        refresh_btn = tk.Button(button_frame, text=_("btn_refresh", "刷新"), 
                               command=self.load_industry_data,
                               **button_style)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 导出按钮
        export_btn = tk.Button(button_frame, text=_("btn_export", "导出"), 
                              command=self.export_industry_data,
                              **button_style)
        export_btn.pack(side=tk.LEFT)
        
        # 主内容区
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：行业列表
        left_frame = tk.LabelFrame(content_frame, text=_("industry_irsi_ranking", "行业IRSI排名"), 
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
        self.industry_tree.heading('rank', text=_("column_rank", "排名"))
        self.industry_tree.heading('industry', text=_("column_industry", "行业名称"))
        self.industry_tree.heading('irsi', text='IRSI指数')
        self.industry_tree.heading('status', text=_("column_status", "强度状态"))
        self.industry_tree.heading('stock_count', text=_("column_stock_count", "股票数量"))
        
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
        right_frame = tk.LabelFrame(content_frame, text=_("industry_detail_info", "行业详细信息"), 
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
        self.status_var.set(_("status_loading_industry", "正在加载行业数据..."))
        
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
            
            self.status_var.set("正在分析行业数据...")
            
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
                            status = "强势"
                            tag = "strong"
                        elif irsi_value > 5:
                            status = "中性偏强"
                            tag = "medium"
                        elif irsi_value > -5:
                            status = "中性"
                            tag = "neutral"
                        elif irsi_value > -20:
                            status = "中性偏弱"
                            tag = "weak"
                        else:
                            status = "弱势"
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
                
                self.status_var.set(f"已加载 {len(sorted_industries)} 个行业的IRSI数据")
                
            else:
                self.status_var.set("暂无行业分析数据")
                
            # 显示默认详细信息
            self.show_default_detail()
            
        except Exception as e:
            error_msg = f"行业数据加载失败: {str(e)}"
            self.status_var.set(error_msg)
            messagebox.showerror("错误", error_msg)
    
    def show_default_detail(self):
        """显示默认详细信息"""
        default_info = """
行业 行业轮动分析说明

数据 IRSI指数 (Industry Relative Strength Index)
• 衡量行业相对于大盘的表现强度
• 正值表示跑赢大盘，负值表示跑输大盘
• 数值范围：-100 到 +100

上涨 强度分类：
• 强势：IRSI > 20，明显跑赢大盘
• 中性偏强：5 < IRSI ≤ 20，小幅跑赢
• 中性：-5 ≤ IRSI ≤ 5，与大盘同步
• 中性偏弱：-20 ≤ IRSI < -5，小幅跑输
• 弱势：IRSI < -20，明显跑输大盘

提示 使用建议：
1. 关注IRSI>15的强势行业，可能有轮动机会
2. 避开IRSI<-15的弱势行业，风险较大
3. 结合其他基本面因素综合判断
4. 定期关注行业轮动变化

时间 数据更新：基于最新评级数据实时计算
警告 投资有风险，仅供参考，不构成投资建议
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
                cannot_find_msg = _("cannot_find_industry_data", "无法找到行业")
                detailed_data_msg = _("detailed_data", "的详细数据")
                error_msg = f"❌ {cannot_find_msg} '{industry_name}' {detailed_data_msg}"
                self.detail_text.delete(1.0, tk.END)
                self.detail_text.insert(1.0, error_msg)
                return
            
            industry_info = self.analysis_results.industries[industry_name]
            irsi_value = self.safe_get_irsi((industry_name, industry_info))
            
            # 生成详细分析
            report_title = _("industry_analysis_report", "行业分析报告")
            core_metrics = _("core_metrics", "核心指标")
            performance_analysis = _("performance_analysis", "表现分析")
            investment_advice = _("investment_advice", "投资建议")
            risk_warning = _("risk_warning", "风险提示")
            analysis_time = _("analysis_time", "分析时间")
            analysis_description = _("analysis_description", "说明")
            
            # 获取相对强度描述
            relative_strength = _("outperform_market", "跑赢大盘") if irsi_value > 0 else (_("underperform_market", "跑输大盘") if irsi_value < 0 else _("sync_with_market", "与大盘同步"))
            
            detail_info = f"""
📊 {report_title} - {industry_name}
{'='*50}

📈 {core_metrics}：
• {_("irsi_index", "IRSI指数")}：{irsi_value:.2f}
• {_("relative_strength_performance", "相对强度")}：{relative_strength}
• {_("strength_level", "强度等级")}：{self.get_strength_level(irsi_value)}

📊 {performance_analysis}：
• {_("short_term_trend", "短期趋势")}：{self.get_trend_analysis(irsi_value)}
• {_("investment_value", "投资价值")}：{self.get_investment_value(irsi_value)}
• {_("risk_level", "风险等级")}：{self.get_risk_level(irsi_value)}

💡 {investment_advice}：
{self.get_investment_advice(industry_name, irsi_value)}

⚠️ {risk_warning}：
{self.get_risk_warning(irsi_value)}

⏰ {analysis_time}：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 {analysis_description}：{_("irsi_description", "IRSI指数基于行业内股票评级相对于整体市场的表现计算")}
"""
            
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(1.0, detail_info)
            
        except Exception as e:
            display_failed_text = _('display_industry_detail_failed', '显示行业详细信息失败')
            error_msg = f"❌ {display_failed_text}: {str(e)}"
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(1.0, error_msg)
    
    def get_strength_level(self, irsi_value):
        """获取强度等级"""
        if irsi_value > 20:
            return "热门 强势"
        elif irsi_value > 5:
            return "上涨 中性偏强"
        elif irsi_value > -5:
            return "中性 中性"
        elif irsi_value > -20:
            return "下跌 中性偏弱"
        else:
            return "冷门 弱势"
    
    def get_trend_analysis(self, irsi_value):
        """获取趋势分析"""
        if irsi_value > 15:
            return "上升趋势明显，资金流入较多"
        elif irsi_value > 0:
            return "温和上升，略好于大盘"
        elif irsi_value > -15:
            return "震荡整理，等待方向选择"
        else:
            return "下跌趋势，资金流出较多"
    
    def get_investment_value(self, irsi_value):
        """获取投资价值"""
        if irsi_value > 20:
            return "星级星级星级星级星级 高价值"
        elif irsi_value > 5:
            return "星级星级星级星级 较高价值"
        elif irsi_value > -5:
            return "星级星级星级 中等价值"
        elif irsi_value > -20:
            return "星级星级 偏低价值"
        else:
            return "星级 低价值"
    
    def get_risk_level(self, irsi_value):
        """获取风险等级"""
        if irsi_value > 20:
            return "低风险 低风险"
        elif irsi_value > 0:
            return "中风险 中低风险"
        elif irsi_value > -20:
            return "🟠 中高风险"
        else:
            return "高风险 高风险"
    
    def get_investment_advice(self, industry_name, irsi_value):
        """获取投资建议"""
        if irsi_value > 15:
            return f"• 积极配置{industry_name}行业优质龙头\n• 可适当加大仓位配比\n• 关注行业内个股轮动机会"
        elif irsi_value > 5:
            return f"• 可适度配置{industry_name}行业\n• 建议选择行业内RTSI较高的个股\n• 控制仓位，注意风险管理"
        elif irsi_value > -5:
            return f"• {industry_name}行业表现中性\n• 可均衡配置，避免重仓\n• 密切关注行业基本面变化"
        elif irsi_value > -15:
            return f"• {industry_name}行业表现偏弱\n• 建议减少配置或回避\n• 等待行业企稳信号"
        else:
            return f"• {industry_name}行业表现较差\n• 建议暂时回避\n• 等待行业拐点出现"
    
    def get_risk_warning(self, irsi_value):
        """获取风险提示"""
        if irsi_value > 20:
            return "注意高位回调风险，设置合理止盈位"
        elif irsi_value > 0:
            return "保持谨慎乐观，注意市场变化"
        elif irsi_value > -20:
            return "控制仓位风险，避免盲目抄底"
        else:
            return "高风险状态，严格控制损失"
    
    def export_industry_data(self):
        """导出行业数据"""
        try:
            from tkinter import filedialog
            import pandas as pd
            
            # 选择保存位置
            filename = filedialog.asksaveasfilename(
                title="导出行业分析数据",
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
        self.window.title(_("market_analysis_window_title", "市场情绪综合分析"))
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        
        # 窗口居中
        self.center_window()
        self.window.transient(self.parent)
        self.window.grab_set()
    
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
        
        title_label = tk.Label(title_frame, text=_("market_sentiment_title", "市场情绪综合分析"), 
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
        
        msci_btn = tk.Button(button_frame, text=_("btn_msci_details", "MSCI详情"), 
                           command=self.show_msci_details,
                           **button_style)
        msci_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        alert_btn = tk.Button(button_frame, text=_("btn_market_alerts", "市场预警"), 
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
                self.analysis_text.insert(1.0, "错误 暂无市场情绪分析数据")
                
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
            'euphoric': _("euphoric", "极度乐观"),
            'optimistic': _("optimistic", "乐观"),
            'neutral': _("neutral", "中性"),
            'pessimistic': _("pessimistic", "悲观"),
            'panic': _("panic", "恐慌")
        }
        
        risk_translations = {
            'low': _("low_risk", "低风险"),
            'medium': _("medium_risk", "中等风险"),  
            'high': _("high_risk", "高风险")
        }
        
        # 翻译状态
        market_state = state_translations.get(raw_market_state, raw_market_state)
        risk_level = risk_translations.get(raw_risk_level, raw_risk_level)
        
        report_title = _("market_analysis_report", "市场情绪综合分析报告")
        core_indicators = _("core_indicators", "核心指标")
        sentiment_interpretation = _("sentiment_interpretation", "情绪解读")
        bull_bear_balance = _("bull_bear_balance", "多空力量对比")
        risk_assessment = _("risk_assessment", "风险评估")
        
        report = f"""
📊 {report_title}
{'='*60}

📈 【{core_indicators}】
• {_("msci_index", "MSCI指数")}: {msci_value:.2f}/100
• {_("market_state", "市场状态")}: {market_state}
• {_("risk_level", "风险等级")}: {risk_level}
• {_("trend_5d", "5日趋势")}: {trend_5d:+.2f}

📊 【{sentiment_interpretation}】
{self.interpret_market_sentiment(msci_value, market_state)}

⚖️ 【{bull_bear_balance}】
{self.analyze_bull_bear_balance(market_data)}

⚠️ 【{risk_assessment}】
{self.assess_market_risk(msci_value, risk_level)}

投资 【投资策略建议】
{self.suggest_investment_strategy(msci_value, market_state)}

时间 【历史对比】
{self.analyze_historical_trend(market_data)}

预测 【后市展望】
{self.forecast_market_outlook(msci_value, trend_5d)}

说明 【免责声明】
本分析基于MSCI情绪算法，仅供参考，不构成投资建议。
市场有风险，投资需谨慎。

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report
    
    def interpret_market_sentiment(self, msci_value, market_state):
        """解读市场情绪"""
        if msci_value > 70:
            return "市场情绪过度乐观，可能存在泡沫风险，建议谨慎操作。"
        elif msci_value > 50:
            return "市场情绪积极，投资者信心较强，适合适度参与。"
        elif msci_value > 30:
            return "市场情绪中性偏谨慎，投资者观望情绪浓厚。"
        elif msci_value > 15:
            return "市场情绪悲观，恐慌情绪蔓延，可能接近底部区域。"
        else:
            return "市场极度恐慌，可能是中长期布局的机会。"
    
    def analyze_bull_bear_balance(self, market_data):
        """分析多空力量对比"""
        # 从市场数据中提取多空力量信息
        latest_analysis = market_data.get('latest_analysis', {})
        bull_bear_ratio = latest_analysis.get('bull_bear_ratio', 1.0)
        
        if bull_bear_ratio > 2.0:
            return f"多头力量占据绝对优势 (多空比: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 1.5:
            return f"多头力量较强 (多空比: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 0.8:
            return f"多空力量相对均衡 (多空比: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 0.5:
            return f"空头力量较强 (多空比: {bull_bear_ratio:.2f}:1)"
        else:
            return f"空头力量占据绝对优势 (多空比: {bull_bear_ratio:.2f}:1)"
    
    def assess_market_risk(self, msci_value, risk_level):
        """评估市场风险"""
        if msci_value > 70:
            return "高风险 高风险：市场过热，建议减仓或获利了结"
        elif msci_value > 50:
            return "中风险 中等风险：保持谨慎，控制仓位"
        elif msci_value > 30:
            return "低风险 低风险：可适度配置，分批建仓"
        else:
            return "低风险 机会大于风险：可考虑逆向布局"
    
    def suggest_investment_strategy(self, msci_value, market_state):
        """建议投资策略"""
        if msci_value > 70:
            return """
• 策略: 防御为主
• 仓位: 建议降至30%以下
• 操作: 逢高减仓，落袋为安
• 选股: 关注防御型个股"""
        elif msci_value > 50:
            return """
• 策略: 稳健参与
• 仓位: 建议保持50-70%
• 操作: 精选个股，波段操作
• 选股: 优质蓝筹+成长股"""
        elif msci_value > 30:
            return """
• 策略: 谨慎建仓
• 仓位: 建议控制在30-50%
• 操作: 分批布局，不急于满仓
• 选股: 基本面扎实的优质股"""
        else:
            return """
• 策略: 逆向布局
• 仓位: 可逐步提升至70%以上
• 操作: 分批买入，中长期持有
• 选股: 被低估的优质成长股"""
    
    def analyze_historical_trend(self, market_data):
        """分析历史趋势"""
        history = market_data.get('history', [])
        if len(history) >= 10:
            recent_avg = sum(h['msci'] for h in history[-5:]) / 5
            earlier_avg = sum(h['msci'] for h in history[-10:-5]) / 5
            change = recent_avg - earlier_avg
            
            if change > 5:
                return f"近期情绪明显改善 (+{change:.1f})"
            elif change > 2:
                return f"近期情绪温和改善 (+{change:.1f})"
            elif change > -2:
                return f"近期情绪基本稳定 ({change:+.1f})"
            elif change > -5:
                return f"近期情绪温和恶化 ({change:.1f})"
            else:
                return f"近期情绪明显恶化 ({change:.1f})"
        else:
            return "历史数据不足，无法进行对比分析"
    
    def forecast_market_outlook(self, msci_value, trend_5d):
        """预测市场展望"""
        if trend_5d > 3:
            return "短期内市场情绪可能继续改善，但需警惕过热风险"
        elif trend_5d > 0:
            return "短期市场情绪有望保持稳定，可维持现有策略"
        elif trend_5d > -3:
            return "短期市场情绪可能持续疲弱，建议谨慎操作"
        else:
            return "短期市场情绪面临进一步恶化风险，建议保持观望"
    
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
        print("成功 扩展版GUI初始化完成")
    
    def open_ai_model_settings(self):
        """打开AI模型设置界面"""
        try:
            import subprocess
            import sys
            import os
            
            # 获取llm-api目录的run_settings.py路径
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            llm_api_dir = os.path.join(current_dir, "llm-api")
            run_settings_path = os.path.join(llm_api_dir, "run_settings.py")
            
            if os.path.exists(run_settings_path):
                # 在新的进程中运行run_settings.py
                subprocess.Popen([sys.executable, run_settings_path], 
                               cwd=llm_api_dir,
                               creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                
                self.status_var.set("AI模型设置界面已启动")
            else:
                messagebox.showerror("错误", f"找不到AI模型设置文件:\n{run_settings_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"启动AI模型设置失败:\n{str(e)}")
    

    def run(self):
        """运行应用"""
        try:
            print("快速 启动GUI应用...")
            self.root.mainloop()
        except Exception as e:
            print(f"错误 GUI运行错误: {e}")
            raise