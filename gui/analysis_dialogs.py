# -*- coding: utf-8 -*-
"""
from config.i18n import t_gui
t_gui_alias = t_gui
_ = t_gui
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

# 导入全局常量
from config.constants import AUTHOR, VERSION

# 国际化配置
try:
    from localization.improved_language_manager import ImprovedLanguageManager, get_current_language
    lang_manager = ImprovedLanguageManager()
    t_gui = lambda key, default="": lang_manager.get_text(key, default)
    t_common = lambda key, default="": lang_manager.get_text(key, default)
except ImportError:
    # 回退函数
    def t_gui(key, default=""):
        return default if default else key
    def t_common(key, default=""):
        return default if default else key
    def get_current_language():
        return 'zh'
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
        self.dialog.title(t_gui('analysis_in_progress'))
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
                              text=t_gui('intelligent_analysis'),
                              bg='#0078d4', fg='white',
                              font=('Microsoft YaHei', 11, 'bold'))
        title_label.pack(expand=True)
        
        # 主内容区域
        content_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 状态显示
        self.status_var = tk.StringVar()
        self.status_var.set(t_gui('initializing_analysis_engine'))
        
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
        
        self.cancel_btn = tk.Button(button_frame, text=t_common('cancel', '取消'), 
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
                    (t_gui('status_loading_data'), 10),
                    (t_gui('status_data_validation'), 20),
                    (t_gui('status_calculating_rtsi'), 40),
                    (t_gui('status_calculating_irsi'), 70),
                    (t_gui('status_calculating_msci'), 85),
                    (t_gui('status_generating_report'), 95),
                    (t_gui('status_analysis_complete'), 100)
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
            t_gui('status_loading_data'): t_gui('detail_loading_data'),
            t_gui('status_data_validation'): t_gui('detail_data_validation'),
            t_gui('status_calculating_rtsi'): t_gui('detail_calculating_rtsi'),
            t_gui('status_calculating_irsi'): t_gui('detail_calculating_irsi'),
            t_gui('status_calculating_msci'): t_gui('detail_calculating_msci'),
            t_gui('status_generating_report'): t_gui('detail_generating_report'),
            t_gui('status_analysis_complete'): t_gui('detail_analysis_complete')
        }
        return details.get(stage, stage)
    
    def cancel_analysis(self):
        """取消分析"""
        if messagebox.askyesno(t_common('confirm', '确认'), t_gui('confirm_cancel_analysis'), parent=self.dialog):
            self.is_cancelled = True
            self.dialog.destroy()
    
    def analysis_completed(self):
        """分析完成"""
        self.cancel_btn.config(text=t_common('close', '关闭'), command=self.close_dialog)
        
        if self.callback:
            self.callback(self.result)
        
        messagebox.showinfo(t_common('complete', '完成'), t_gui('analysis_completed_msg'), parent=self.dialog)
        self.dialog.destroy()
    
    def analysis_failed(self, error_msg: str):
        """分析失败"""
        self.add_detail(f"{t_common('error', '错误')}: {error_msg}")
        self.status_var.set(t_gui('analysis_failed'))
        self.cancel_btn.config(text=t_common('close', '关闭'), command=self.close_dialog)
        
        messagebox.showerror(t_gui('analysis_failed'), f"{t_gui('analysis_error_msg')}:\n{error_msg}", parent=self.dialog)
    
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
        from config.i18n import t_tools
        self.dialog.title(t_tools('system_settings'))
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
        from config.i18n import t_tools
        frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(frame, text=t_tools('analysis_settings'))
        frame.columnconfigure(0, weight=1)
        
        # RTSI设置
        rtsi_group = tk.LabelFrame(frame, text=t_tools('rtsi_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        rtsi_group.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        # 最小数据点数
        tk.Label(rtsi_group, text=f"{t_tools('min_data_points')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.min_points_var = tk.IntVar(value=self.settings.get('rtsi_min_points', 5))
        tk.Spinbox(rtsi_group, from_=3, to=20, textvariable=self.min_points_var, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        
        # 一致性权重
        tk.Label(rtsi_group, text=f"{t_tools('consistency_weight')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.consistency_weight_var = tk.DoubleVar(value=self.settings.get('rtsi_consistency_weight', 0.4))
        tk.Scale(rtsi_group, from_=0.1, to=0.9, resolution=0.1, orient=tk.HORIZONTAL,
                variable=self.consistency_weight_var, length=200, font=('Microsoft YaHei', 11)).grid(row=1, column=1, padx=5, pady=5)
        
        # IRSI设置
        irsi_group = tk.LabelFrame(frame, text=t_tools('irsi_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        irsi_group.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(irsi_group, text=f"{t_tools('calculation_period')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.irsi_period_var = tk.IntVar(value=self.settings.get('irsi_period', 20))
        tk.Spinbox(irsi_group, from_=5, to=60, textvariable=self.irsi_period_var, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        
        # MSCI设置
        msci_group = tk.LabelFrame(frame, text=t_tools('msci_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        msci_group.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(msci_group, text=f"{t_tools('bull_market_threshold')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.msci_bull_threshold_var = tk.DoubleVar(value=self.settings.get('msci_bull_threshold', 0.02))
        tk.Scale(msci_group, from_=0.01, to=0.1, resolution=0.01, orient=tk.HORIZONTAL,
                variable=self.msci_bull_threshold_var, length=200, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
    
    def create_interface_tab(self, notebook):
        """创建界面设置页面"""
        from config.i18n import t_tools
        frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(frame, text=t_tools('interface_settings'))
        frame.columnconfigure(0, weight=1)
        
        # 主题设置
        theme_group = tk.LabelFrame(frame, text=t_tools('theme_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        theme_group.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.theme_var = tk.StringVar(value=self.settings.get('theme', 'classic'))
        themes = [(t_tools('theme_windows_classic'), 'classic'), (t_tools('theme_modern'), 'modern'), (t_tools('theme_dark'), 'dark')]
        
        for i, (text, value) in enumerate(themes):
            tk.Radiobutton(theme_group, text=text, variable=self.theme_var, value=value,
                          bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
        
        # 字体设置
        font_group = tk.LabelFrame(frame, text=t_tools('font_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        font_group.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(font_group, text=f"{t_tools('font_size')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.font_size_var = tk.IntVar(value=self.settings.get('font_size', 11))  # 改为默认11号
        tk.Spinbox(font_group, from_=8, to=16, textvariable=self.font_size_var, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        
        # 启动设置
        startup_group = tk.LabelFrame(frame, text=t_tools('startup_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        startup_group.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.remember_window_var = tk.BooleanVar(value=self.settings.get('remember_window', True))
        tk.Checkbutton(startup_group, text=t_tools('remember_window_position'), variable=self.remember_window_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        
        self.auto_load_var = tk.BooleanVar(value=self.settings.get('auto_load_last', False))
        tk.Checkbutton(startup_group, text=t_tools('auto_load_last_file'), variable=self.auto_load_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    
    def create_performance_tab(self, notebook):
        """创建性能设置页面"""
        from config.i18n import t_tools
        frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(frame, text=t_tools('performance_settings'))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        
        # 计算设置
        calc_group = tk.LabelFrame(frame, text=t_tools('calculation_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        calc_group.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.use_multithread_var = tk.BooleanVar(value=self.settings.get('use_multithread', True))
        tk.Checkbutton(calc_group, text=t_tools('enable_multithreading'), variable=self.use_multithread_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        tk.Label(calc_group, text=f"{t_tools('thread_count')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.thread_count_var = tk.IntVar(value=self.settings.get('thread_count', 4))
        tk.Spinbox(calc_group, from_=1, to=16, textvariable=self.thread_count_var, width=10, font=('Microsoft YaHei', 11)).grid(row=1, column=1, padx=5, pady=5)
        
        # 缓存设置
        cache_group = tk.LabelFrame(frame, text=t_tools('cache_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        cache_group.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=5)
        
        self.enable_cache_var = tk.BooleanVar(value=self.settings.get('enable_cache', True))
        tk.Checkbutton(cache_group, text=t_tools('enable_cache'), variable=self.enable_cache_var,
                      bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        tk.Label(cache_group, text=f"{t_tools('cache_size_limit')}(MB):", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.cache_size_var = tk.IntVar(value=self.settings.get('cache_size_mb', 100))
        tk.Spinbox(cache_group, from_=50, to=500, textvariable=self.cache_size_var, width=10, font=('Microsoft YaHei', 11)).grid(row=1, column=1, padx=5, pady=5)
        
        # 数据路径设置
        path_group = tk.LabelFrame(frame, text=t_tools('data_path_settings'), bg='#f0f0f0', font=('Microsoft YaHei', 11))
        path_group.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=5)
        
        tk.Label(path_group, text=f"{t_tools('default_data_path')}:", bg='#f0f0f0', font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.data_path_var = tk.StringVar(value=self.settings.get('data_path', str(Path.cwd())))
        tk.Entry(path_group, textvariable=self.data_path_var, width=40, font=('Microsoft YaHei', 11)).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(path_group, text=t_common('browse', '浏览'), command=self.browse_data_path, font=('Microsoft YaHei', 11)).grid(row=0, column=2, padx=5, pady=5)
    
    def create_buttons(self):
        """创建按钮区域"""
        button_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        button_frame.grid(row=10, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)
        button_frame.columnconfigure(1, weight=1)  # 中间空白区域
        
        # 恢复默认按钮 - 最左边
        tk.Button(button_frame, text=t_common('reset_defaults', '恢复默认'), command=self.reset_defaults,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        # 保存按钮 - 最右边第二个位置
        tk.Button(button_frame, text=t_common('save', '保存'), command=self.save_settings,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=2, sticky=tk.E, padx=5)
        
        # 取消按钮 - 最右边第一个位置
        tk.Button(button_frame, text=t_common('cancel', '取消'), command=self.dialog.destroy,
                 bg='#f0f0f0', relief=tk.RAISED, bd=2, width=10, font=('Microsoft YaHei', 11)).grid(row=0, column=3, sticky=tk.E, padx=5)
    
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
        print(f"{t_tools('settings_saved')}:", new_settings)
        
        messagebox.showinfo(t_common('success', '成功'), f"{t_tools('settings_saved_msg')}\n{t_tools('restart_required')}", parent=self.dialog)
        self.dialog.destroy()
    
    def reset_defaults(self):
        """恢复默认设置"""
        if messagebox.askyesno(t_common('confirm', '确认'), t_tools('confirm_reset_defaults'), parent=self.dialog):
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
        self.dialog.title(t_common('about', '关于'))
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
        
        icon_label = tk.Label(icon_frame, text=t_gui('app_icon'), font=('Arial', 36),
                             bg='#0078d4', fg='white')
        icon_label.pack(expand=True)
        
        # 主要信息
        info_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 产品名称
        tk.Label(info_frame, text=t_gui('app_name', 'AI股票大师'),
                font=('Microsoft YaHei', 11, 'bold'),
                bg='#f0f0f0', fg='#0078d4').pack(pady=(0, 5))
        
        # 版本信息
        tk.Label(info_frame, text=t_gui('version_info', f'版本 {VERSION}'),
                font=('Microsoft YaHei', 11),
                bg='#f0f0f0', fg='#666666').pack(pady=(0, 15))
        
        # 功能特点
        features_text = f"""{t_gui('core_features_title', '核心功能特点')}:
• RTSI - {t_gui('rtsi_description', '相对趋势强度指数')}
• IRSI - {t_gui('irsi_description', '改进相对强度指数')}
• MSCI - {t_gui('msci_description', '市场情绪周期指数')}


{t_gui('development_info_title', '开发信息')}:
• {t_gui('ai_assisted_development', 'AI辅助开发')}
• {t_gui('tech_stack_details', 'Python 3.10+ | tkinter | matplotlib')}
• {t_gui('build_date', '构建日期')}: {t_gui('build_date_value', '2025-06-07')}

{t_gui('data_processing_title', '数据处理能力')}:
• {t_gui('stock_analysis_capacity', '支持大规模股票数据分析')}
• {t_gui('industry_classification', '行业分类与对比')}
• {t_gui('rating_system_support', '评级系统支持')}
• {t_gui('historical_data_analysis', '历史数据分析')}"""
        
        features_label = tk.Label(info_frame, text=features_text,
                                 font=('Microsoft YaHei', 9),
                                 bg='#f0f0f0', fg='#333333',
                                 justify=tk.LEFT, anchor=tk.W)
        features_label.pack(pady=(0, 15), fill=tk.X)
        
        # 版权信息
        copyright_text = f"""{t_gui('copyright_year', '© 2025')} {t_gui('app_name', 'AI股票大师')}. {t_gui('all_rights_reserved', '保留所有权利')}.

{t_gui('disclaimer_text', '本软件仅供研究学习使用，投资决策请基于自己的判断。')}
{t_gui('analysis_disclaimer', '软件开发者不承担任何投资损失责任。')}

{t_gui('technical_support', '技术支持')}: {AUTHOR}"""
        
        tk.Label(info_frame, text=copyright_text,
                font=('Microsoft YaHei', 8),
                bg='#f0f0f0', fg='#888888',
                justify=tk.CENTER).pack()
        
        # 关闭按钮
        tk.Button(info_frame, text=t_common('close', '关闭'), command=self.dialog.destroy,
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
    root.title(t_gui('dialog_test'))
    root.geometry("300x200")
    root.withdraw()  # 隐藏主窗口
    
    def test_analysis():
        """模拟分析函数"""
        time.sleep(2)
        return {"result": "analysis completed"}
    
    def test_callback(result):
        print(f"{t_gui('analysis_result')}:", result)
    
    # 测试进度对话框
    # AnalysisProgressDialog(root, test_analysis, test_callback)
    
    # 测试设置对话框
    # SettingsDialog(root)
    
    # 测试关于对话框
    AboutDialog(root)
    
    root.mainloop()