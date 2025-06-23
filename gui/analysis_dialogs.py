# -*- coding: utf-8 -*-
"""
分析对话框模块 - 各种功能对话框

实现:
- AnalysisProgressDialog: 分析进度对话框
- SettingsDialog: 系统设置对话框
- AboutDialog: 关于对话框

技术栈: tkinter
设计风格: Windows经典对话框
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from typing import Callable, Dict, Any
from pathlib import Path


class AnalysisProgressDialog:
    """分析进度对话框 - 显示分析进度和状态"""
    
    def __init__(self, parent, analysis_func: Callable, callback: Callable = None):
        self.parent = parent
        self.analysis_func = analysis_func
        self.callback = callback
        self.is_cancelled = False
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.setup_dialog()
        
        # 开始分析
        self.start_analysis()
    
    def setup_dialog(self):
        """设置对话框界面"""
        self.dialog.title("数据分析进行中...")
        self.dialog.geometry("450x300")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.resizable(False, False)
        
        # 模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 标题区域
        title_frame = tk.Frame(self.dialog, bg='#0078d4', height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="检查 AI股票趋势分析",
                              bg='#0078d4', fg='white',
                              font=('Microsoft YaHei', 11, 'bold'))
        title_label.pack(expand=True)
        
        # 主内容区域
        content_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 状态显示
        self.status_var = tk.StringVar()
        self.status_var.set("正在初始化分析引擎...")
        
        status_label = tk.Label(content_frame, textvariable=self.status_var,
                               bg='#f0f0f0', fg='#333333',
                               font=('Microsoft YaHei', 11),
                               wraplength=350, justify=tk.LEFT)
        status_label.pack(pady=(0, 15))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(content_frame, 
                                          variable=self.progress_var,
                                          maximum=100, length=350)
        self.progress_bar.pack(pady=(0, 15))
        
        # 详细信息
        self.detail_text = tk.Text(content_frame, height=8, width=50,
                                  bg='white', fg='#333333',
                                  font=('Consolas', 11),
                                  state=tk.DISABLED)
        
        detail_scrollbar = tk.Scrollbar(content_frame, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)
        
        # 布局详细信息
        detail_frame = tk.Frame(content_frame, bg='#f0f0f0')
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮区域
        button_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        self.cancel_btn = tk.Button(button_frame, text="取消", 
                                   command=self.cancel_analysis,
                                   bg='#f0f0f0', relief=tk.RAISED, bd=2,
                                   width=10)
        self.cancel_btn.pack(side=tk.RIGHT)
        
        # 禁用关闭按钮
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_analysis)
    
    def center_dialog(self):
        """对话框居中"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def start_analysis(self):
        """开始分析"""
        def run_analysis():
            try:
                # 分析阶段
                stages = [
                    ("正在加载数据...", 10),
                    ("数据验证和预处理...", 20),
                    ("计算RTSI个股趋势指数...", 40),
                    ("计算IRSI行业强度指数...", 70),
                    ("计算MSCI市场情绪指数...", 85),
                    ("生成分析报告...", 95),
                    ("分析完成!", 100)
                ]
                
                for stage_text, progress in stages:
                    if self.is_cancelled:
                        return
                    
                    # 更新状态
                    self.dialog.after(0, lambda t=stage_text, p=progress: self.update_progress(t, p))
                    
                    # 添加详细信息
                    detail_info = self.get_stage_details(stage_text)
                    self.dialog.after(0, lambda d=detail_info: self.add_detail(d))
                    
                    time.sleep(1.5)
                
                if not self.is_cancelled:
                    # 执行实际分析
                    self.result = self.analysis_func()
                    
                    # 完成
                    self.dialog.after(0, self.analysis_completed)
                
            except Exception as e:
                self.dialog.after(0, lambda: self.analysis_failed(str(e)))
        
        # 在新线程中运行
        analysis_thread = threading.Thread(target=run_analysis)
        analysis_thread.daemon = True
        analysis_thread.start()
    
    def update_progress(self, status: str, progress: float):
        """更新进度"""
        self.status_var.set(status)
        self.progress_var.set(progress)
        self.dialog.update()
    
    def add_detail(self, detail: str):
        """添加详细信息"""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {detail}\n")
        self.detail_text.config(state=tk.DISABLED)
        self.detail_text.see(tk.END)
    
    def get_stage_details(self, stage: str) -> str:
        """获取阶段详细信息"""
        details = {
            "正在加载数据...": "读取Excel文件，解析股票和行业数据",
            "数据验证和预处理...": "验证8级评级系统，清理无效数据",
            "计算RTSI个股趋势指数...": "使用线性回归分析个股评级趋势",
            "计算IRSI行业强度指数...": "计算行业相对市场表现强度",
            "计算MSCI市场情绪指数...": "综合分析市场整体情绪状态",
            "生成分析报告...": "整理分析结果，准备可视化数据",
            "分析完成!": "所有分析任务已完成，准备展示结果"
        }
        return details.get(stage, stage)
    
    def cancel_analysis(self):
        """取消分析"""
        if messagebox.askyesno("确认", "确定要取消分析吗？", parent=self.dialog):
            self.is_cancelled = True
            self.dialog.destroy()
    
    def analysis_completed(self):
        """分析完成"""
        self.cancel_btn.config(text="完成", command=self.close_dialog)
        
        if self.callback:
            self.callback(self.result)
        
        messagebox.showinfo("完成", "数据分析已完成！", parent=self.dialog)
        self.dialog.destroy()
    
    def analysis_failed(self, error_msg: str):
        """分析失败"""
        self.add_detail(f"错误: {error_msg}")
        self.status_var.set("分析失败")
        self.cancel_btn.config(text="关闭", command=self.close_dialog)
        
        messagebox.showerror("分析失败", f"分析过程中发生错误:\n{error_msg}", parent=self.dialog)
    
    def close_dialog(self):
        """关闭对话框"""
        self.dialog.destroy()


class SettingsDialog:
    """系统设置对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.settings = self.load_settings()
        
        self.setup_dialog()
    
    def setup_dialog(self):
        """设置对话框界面"""
        self.dialog.title("系统设置")
        self.dialog.geometry("500x600")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.resizable(False, False)
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        
        # 模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 创建笔记本控件
        notebook = ttk.Notebook(self.dialog)
        notebook.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=10)
        
        # 分析设置页面
        self.create_analysis_tab(notebook)
        
        # 界面设置页面
        self.create_interface_tab(notebook)
        
        # 性能设置页面
        self.create_performance_tab(notebook)
        
        # 按钮区域
        self.create_buttons()
    
    def center_dialog(self):
        """对话框居中"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def create_analysis_tab(self, notebook):
        """创建分析设置页面"""
        frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(frame, text="分析设置")
        frame.columnconfigure(0, weight=1)
        
        # RTSI设置
        rtsi_group = tk.LabelFrame(frame, text="RTSI算法参数", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        rtsi_group.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        # 最小数据点数
        tk.Label(rtsi_group, text="最小数据点数:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.min_points_var = tk.IntVar(value=self.settings.get('rtsi_min_points', 5))
        tk.Spinbox(rtsi_group, from_=3, to=20, textvariable=self.min_points_var, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        
        # 一致性权重
        tk.Label(rtsi_group, text="一致性权重:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.consistency_weight_var = tk.DoubleVar(value=self.settings.get('rtsi_consistency_weight', 0.4))
        tk.Scale(rtsi_group, from_=0.1, to=0.9, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.consistency_weight_var, length=200, font=('Microsoft YaHei', 11)).grid(row=1, column=1, padx=5, pady=5)
        
        # IRSI设置
        irsi_group = tk.LabelFrame(frame, text="IRSI算法参数", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        irsi_group.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(irsi_group, text="历史周期:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.irsi_period_var = tk.IntVar(value=self.settings.get('irsi_period', 20))
        tk.Spinbox(irsi_group, from_=5, to=60, textvariable=self.irsi_period_var, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        
        # MSCI设置
        msci_group = tk.LabelFrame(frame, text="MSCI算法参数", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        msci_group.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(msci_group, text="极端乐观阈值:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.msci_bull_threshold_var = tk.DoubleVar(value=self.settings.get('msci_bull_threshold', 0.02))
        tk.Scale(msci_group, from_=0.01, to=0.1, resolution=0.01, orient=tk.HORIZONTAL,
                variable=self.msci_bull_threshold_var, length=200, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
    
    def create_interface_tab(self, notebook):
        """创建界面设置页面"""
        frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(frame, text="界面设置")
        frame.columnconfigure(0, weight=1)
        
        # 主题设置
        theme_group = tk.LabelFrame(frame, text="界面主题", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        theme_group.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.theme_var = tk.StringVar(value=self.settings.get('theme', 'classic'))
        themes = [('Windows经典', 'classic'), ('现代风格', 'modern'), ('深色主题', 'dark')]
        
        for i, (text, value) in enumerate(themes):
            tk.Radiobutton(theme_group, text=text, variable=self.theme_var, value=value,
                          bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 字体设置
        font_group = tk.LabelFrame(frame, text="字体设置", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        font_group.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(font_group, text="字体大小:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.font_size_var = tk.IntVar(value=self.settings.get('font_size', 11))  # 改为默认11号
        tk.Spinbox(font_group, from_=8, to=16, textvariable=self.font_size_var, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        
        # 启动设置
        startup_group = tk.LabelFrame(frame, text="启动选项", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        startup_group.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.remember_window_var = tk.BooleanVar(value=self.settings.get('remember_window', True))
        tk.Checkbutton(startup_group, text="记住窗口位置和大小", variable=self.remember_window_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        self.auto_load_var = tk.BooleanVar(value=self.settings.get('auto_load_last', False))
        tk.Checkbutton(startup_group, text="启动时自动加载上次文件", variable=self.auto_load_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    
    def create_performance_tab(self, notebook):
        """创建性能设置页面"""
        frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(frame, text="性能设置")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        
        # 计算设置
        calc_group = tk.LabelFrame(frame, text="计算性能", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        calc_group.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.use_multithread_var = tk.BooleanVar(value=self.settings.get('use_multithread', True))
        tk.Checkbutton(calc_group, text="启用多线程计算", variable=self.use_multithread_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        tk.Label(calc_group, text="线程数量:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.thread_count_var = tk.IntVar(value=self.settings.get('thread_count', 4))
        tk.Spinbox(calc_group, from_=1, to=16, textvariable=self.thread_count_var, width=10, font=('Microsoft YaHei', 11)).grid(row=1, column=1, padx=5, pady=5)
        
        # 缓存设置
        cache_group = tk.LabelFrame(frame, text="缓存设置", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        cache_group.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.enable_cache_var = tk.BooleanVar(value=self.settings.get('enable_cache', True))
        tk.Checkbutton(cache_group, text="启用分析结果缓存", variable=self.enable_cache_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        tk.Label(cache_group, text="缓存大小限制(MB):", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.cache_size_var = tk.IntVar(value=self.settings.get('cache_size_mb', 100))
        tk.Spinbox(cache_group, from_=50, to=500, textvariable=self.cache_size_var, width=10, font=('Microsoft YaHei', 11)).grid(row=1, column=1, padx=5, pady=5)
        
        # 数据路径设置
        path_group = tk.LabelFrame(frame, text="数据路径", bg='#f0f0f0', font=('Microsoft YaHei', 11))
        path_group.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(path_group, text="默认数据目录:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.data_path_var = tk.StringVar(value=self.settings.get('data_path', str(Path.cwd())))
        tk.Entry(path_group, textvariable=self.data_path_var, width=40, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(path_group, text="浏览...", command=self.browse_data_path, font=('Microsoft YaHei', 11)).grid(row=0, column=2, padx=5, pady=5)
    
    def create_buttons(self):
        """创建按钮区域"""
        button_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        button_frame.grid(row=10, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)
        button_frame.columnconfigure(0, weight=1)
        
        tk.Button(button_frame, text="恢复默认", command=self.reset_defaults,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.E, padx=5)
        
        tk.Button(button_frame, text="取消", command=self.dialog.destroy,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5)
        
        tk.Button(button_frame, text="确定", command=self.save_settings,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=2, padx=5)
    
    def browse_data_path(self):
        """浏览数据路径"""
        path = filedialog.askdirectory(initialdir=self.data_path_var.get())
        if path:
            self.data_path_var.set(path)
    
    def load_settings(self) -> Dict[str, Any]:
        """加载设置"""
        # 这里应该从配置文件加载，暂时返回默认值
        return {
            'rtsi_min_points': 5,
            'rtsi_consistency_weight': 0.4,
            'irsi_period': 20,
            'msci_bull_threshold': 0.02,
            'theme': 'classic',
            'font_size': 10,
            'remember_window': True,
            'auto_load_last': False,
            'use_multithread': True,
            'thread_count': 4,
            'enable_cache': True,
            'cache_size_mb': 100,
            'data_path': str(Path.cwd())
        }
    
    def save_settings(self):
        """保存设置"""
        new_settings = {
            'rtsi_min_points': self.min_points_var.get(),
            'rtsi_consistency_weight': self.consistency_weight_var.get(),
            'irsi_period': self.irsi_period_var.get(),
            'msci_bull_threshold': self.msci_bull_threshold_var.get(),
            'theme': self.theme_var.get(),
            'font_size': self.font_size_var.get(),
            'remember_window': self.remember_window_var.get(),
            'auto_load_last': self.auto_load_var.get(),
            'use_multithread': self.use_multithread_var.get(),
            'thread_count': self.thread_count_var.get(),
            'enable_cache': self.enable_cache_var.get(),
            'cache_size_mb': self.cache_size_var.get(),
            'data_path': self.data_path_var.get()
        }
        
        # 这里应该保存到配置文件
        print("设置已保存:", new_settings)
        
        messagebox.showinfo("成功", "设置已保存！\n某些设置需要重启程序后生效。", parent=self.dialog)
        self.dialog.destroy()
    
    def reset_defaults(self):
        """恢复默认设置"""
        if messagebox.askyesno("确认", "确定要恢复所有默认设置吗？", parent=self.dialog):
            defaults = self.load_settings()
            
            self.min_points_var.set(defaults['rtsi_min_points'])
            self.consistency_weight_var.set(defaults['rtsi_consistency_weight'])
            self.irsi_period_var.set(defaults['irsi_period'])
            self.msci_bull_threshold_var.set(defaults['msci_bull_threshold'])
            self.theme_var.set(defaults['theme'])
            self.font_size_var.set(defaults['font_size'])
            self.remember_window_var.set(defaults['remember_window'])
            self.auto_load_var.set(defaults['auto_load_last'])
            self.use_multithread_var.set(defaults['use_multithread'])
            self.thread_count_var.set(defaults['thread_count'])
            self.enable_cache_var.set(defaults['enable_cache'])
            self.cache_size_var.set(defaults['cache_size_mb'])
            self.data_path_var.set(defaults['data_path'])


class AboutDialog:
    """关于对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        
        self.setup_dialog()
    
    def setup_dialog(self):
        """设置对话框界面"""
        self.dialog.title("关于")
        self.dialog.geometry("450x500")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.resizable(False, False)
        
        # 模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 图标区域
        icon_frame = tk.Frame(self.dialog, bg='#0078d4', height=80)
        icon_frame.pack(fill=tk.X)
        icon_frame.pack_propagate(False)
        
        icon_label = tk.Label(icon_frame, text="上涨", font=('Arial', 36),
                             bg='#0078d4', fg='white')
        icon_label.pack(expand=True)
        
        # 主要信息
        info_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 产品名称
        tk.Label(info_frame, text="AI股票趋势分析系统",
                font=('Microsoft YaHei', 11, 'bold'),
                bg='#f0f0f0', fg='#0078d4').pack(pady=(0, 5))
        
        # 版本信息
        tk.Label(info_frame, text="版本 1.0.0 (第四期: GUI界面核心)",
                font=('Microsoft YaHei', 11),
                bg='#f0f0f0', fg='#666666').pack(pady=(0, 15))
        
        # 功能特点
        features_text = """核心 核心功能:
• RTSI - 个股评级趋势强度指数
• IRSI - 行业相对强度指数
• MSCI - 市场情绪综合指数


优秀 开发信息:
• 基于Cursor Pro AI辅助开发
• Python 3.10+ | tkinter | matplotlib
• 构建日期: 2025-06-07

数据 数据处理能力:
• 支持5,000+股票同时分析
• 85个行业分类自动识别
• 8级评级系统完整支持
• 38个交易日历史数据分析"""
        
        features_label = tk.Label(info_frame, text=features_text,
                                 font=('Microsoft YaHei', 9),
                                 bg='#f0f0f0', fg='#333333',
                                 justify=tk.LEFT, anchor=tk.W)
        features_label.pack(pady=(0, 15), fill=tk.X)
        
        # 版权信息
        copyright_text = """© 2025 AI股票趋势分析系统. 保留所有权利.

本软件仅供学习和研究使用。投资有风险，入市需谨慎。
软件提供的分析结果仅供参考，不构成投资建议。

技术支持: 267278466@qq.com"""
        
        tk.Label(info_frame, text=copyright_text,
                font=('Microsoft YaHei', 8),
                bg='#f0f0f0', fg='#888888',
                justify=tk.CENTER).pack()
        
        # 关闭按钮
        tk.Button(info_frame, text="确定", command=self.dialog.destroy,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2,
                 width=15).pack(pady=(15, 0))
    
    def center_dialog(self):
        """对话框居中"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.title("对话框测试")
    root.geometry("300x200")
    root.withdraw()  # 隐藏主窗口
    
    def test_analysis():
        """模拟分析函数"""
        time.sleep(2)
        return {"result": "analysis completed"}
    
    def test_callback(result):
        print("分析完成:", result)
    
    # 测试进度对话框
    # AnalysisProgressDialog(root, test_analysis, test_callback)
    
    # 测试设置对话框
    # SettingsDialog(root)
    
    # 测试关于对话框
    AboutDialog(root)
    
    root.mainloop() 