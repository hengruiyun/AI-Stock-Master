#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI股票趋势分析系统 - 数据自动更新模块

功能:
1. 自动下载最新的演示数据文件
2. 显示下载进度
3. 覆盖本地文件

作者: 267278466@qq.com
版本: 1.0.0
"""

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

# 导入语言管理器
try:
    from localization.improved_language_manager import _, is_english
except ImportError:
    def _(key, default=None):
        return default or key
    def is_english():
        return False


class DataUpdater:
    """数据文件自动更新器"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.project_root = Path(__file__).parent.parent
        
        # 要下载的文件列表
        self.files_to_download = [
            {
                'url': 'https://github.com/hengruiyun/AI-Stock-Analysis/raw/refs/heads/main/CN_Demo300.xlsx',
                'filename': 'CN_Demo300.xlsx',
                'description': _('cn_demo_desc', '中国A股演示数据')
            },
            {
                'url': 'https://github.com/hengruiyun/AI-Stock-Analysis/raw/refs/heads/main/HK_Demo300.xlsx',
                'filename': 'HK_Demo300.xlsx',
                'description': _('hk_demo_desc', '香港股市演示数据')
            },
            {
                'url': 'https://github.com/hengruiyun/AI-Stock-Analysis/raw/refs/heads/main/US_Demo300.xlsx',
                'filename': 'US_Demo300.xlsx',
                'description': _('us_demo_desc', '美国股市演示数据')
            }
        ]
        
        self.download_window = None
        self.progress_var = None
        self.status_var = None
        self.current_file_var = None
        self.cancel_download = False
    
    def check_and_update(self, show_progress=True):
        """检查并更新数据文件"""
        if show_progress:
            self.show_progress_window()
            # 在新线程中执行下载
            download_thread = threading.Thread(target=self._download_files, daemon=True)
            download_thread.start()
        else:
            # 静默更新
            return self._download_files()
    
    def show_progress_window(self):
        """显示下载进度窗口"""
        self.download_window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.download_window.title(_('update_title', '数据文件更新'))
        self.download_window.geometry('500x300')
        self.download_window.resizable(False, False)
        self.download_window.configure(bg='#f0f0f0')
        
        # 窗口居中
        self._center_window()
        
        # 标题
        title_label = tk.Label(self.download_window, 
                              text=_('update_downloading', '正在更新数据文件...'),
                              font=('Microsoft YaHei', 12, 'bold'),
                              bg='#f0f0f0', fg='#0078d4')
        title_label.pack(pady=(20, 10))
        
        # 当前文件信息
        self.current_file_var = tk.StringVar()
        self.current_file_var.set(_('update_preparing', '准备下载...'))
        current_file_label = tk.Label(self.download_window,
                                     textvariable=self.current_file_var,
                                     font=('Microsoft YaHei', 10),
                                     bg='#f0f0f0', fg='#333333')
        current_file_label.pack(pady=(0, 10))
        
        # 进度条
        progress_frame = tk.Frame(self.download_window, bg='#f0f0f0')
        progress_frame.pack(pady=10, padx=40, fill=tk.X)
        
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame,
                                      variable=self.progress_var,
                                      maximum=100,
                                      length=400)
        progress_bar.pack(fill=tk.X)
        
        # 状态信息
        self.status_var = tk.StringVar()
        self.status_var.set(_('update_status_ready', '准备中...'))
        status_label = tk.Label(self.download_window,
                               textvariable=self.status_var,
                               font=('Microsoft YaHei', 9),
                               bg='#f0f0f0', fg='#666666')
        status_label.pack(pady=(10, 20))
        
        # 按钮区域
        button_frame = tk.Frame(self.download_window, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame,
                              text=_('btn_cancel', '取消'),
                              command=self._cancel_download,
                              font=('Microsoft YaHei', 10),
                              bg='#f0f0f0', relief=tk.RAISED, bd=2,
                              padx=20, pady=5)
        cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 跳过按钮
        skip_btn = tk.Button(button_frame,
                            text=_('btn_skip', '跳过更新'),
                            command=self._skip_update,
                            font=('Microsoft YaHei', 10),
                            bg='#f0f0f0', relief=tk.RAISED, bd=2,
                            padx=20, pady=5)
        skip_btn.pack(side=tk.LEFT)
        
        # 设置窗口关闭事件
        self.download_window.protocol("WM_DELETE_WINDOW", self._cancel_download)
        
        # 如果没有父窗口，启动主循环
        if not self.parent:
            self.download_window.mainloop()
    
    def _center_window(self):
        """窗口居中"""
        self.download_window.update_idletasks()
        width = self.download_window.winfo_width()
        height = self.download_window.winfo_height()
        x = (self.download_window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.download_window.winfo_screenheight() // 2) - (height // 2)
        self.download_window.geometry(f'{width}x{height}+{x}+{y}')
    
    def _download_files(self):
        """下载所有文件"""
        total_files = len(self.files_to_download)
        success_count = 0
        
        for i, file_info in enumerate(self.files_to_download):
            if self.cancel_download:
                break
                
            # 更新当前文件信息
            if self.current_file_var:
                self.current_file_var.set(f"{_('update_downloading_file', '正在下载')}: {file_info['description']}")
            
            # 更新状态
            if self.status_var:
                self.status_var.set(f"{_('update_progress', '进度')}: {i+1}/{total_files}")
            
            # 下载文件
            success = self._download_single_file(file_info, i, total_files)
            if success:
                success_count += 1
            
            # 更新总进度
            if self.progress_var:
                self.progress_var.set((i + 1) * 100 / total_files)
        
        # 下载完成
        if not self.cancel_download:
            self._download_completed(success_count, total_files)
        
        return success_count == total_files
    
    def _download_single_file(self, file_info, file_index, total_files):
        """下载单个文件"""
        url = file_info['url']
        filename = file_info['filename']
        local_path = self.project_root / filename
        
        try:
            # 创建请求
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # 开始下载
            with urllib.request.urlopen(request, timeout=30) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(local_path, 'wb') as f:
                    while True:
                        if self.cancel_download:
                            return False
                            
                        chunk = response.read(8192)
                        if not chunk:
                            break
                            
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新文件内进度
                        if total_size > 0 and self.progress_var:
                            file_progress = (downloaded / total_size) * (100 / total_files)
                            total_progress = file_index * (100 / total_files) + file_progress
                            self.progress_var.set(total_progress)
                        
                        # 更新状态
                        if self.status_var and total_size > 0:
                            size_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            self.status_var.set(f"{_('update_downloading', '下载中')}: {size_mb:.1f}MB / {total_mb:.1f}MB")
            
            print(f"{_('update_success', '成功下载')}: {filename}")
            return True
            
        except Exception as e:
            print(f"{_('update_failed', '下载失败')} {filename}: {e}")
            if self.status_var:
                self.status_var.set(f"{_('update_error', '错误')}: {filename} - {str(e)[:50]}")
            return False
    
    def _download_completed(self, success_count, total_files):
        """下载完成处理"""
        if self.download_window:
            if success_count == total_files:
                # 全部成功
                self.current_file_var.set(_('update_complete_success', '✓ 所有文件更新完成'))
                self.status_var.set(_('update_all_success', '数据文件已更新到最新版本'))
                self.progress_var.set(100)
            else:
                # 部分成功
                self.current_file_var.set(f"{_('update_partial_success', '部分文件更新完成')}: {success_count}/{total_files}")
                self.status_var.set(_('update_some_failed', '部分文件下载失败，可继续使用现有文件'))
            
            # 3秒后自动关闭
            self.download_window.after(3000, self._close_window)
    
    def _cancel_download(self):
        """取消下载"""
        self.cancel_download = True
        if self.status_var:
            self.status_var.set(_('update_cancelled', '下载已取消'))
        self._close_window()
    
    def _skip_update(self):
        """跳过更新"""
        self.cancel_download = True
        if self.status_var:
            self.status_var.set(_('update_skipped', '已跳过更新'))
        self._close_window()
    
    def _close_window(self):
        """关闭窗口"""
        if self.download_window:
            self.download_window.destroy()
            self.download_window = None


def auto_update_data_files(parent=None, show_progress=True):
    """自动更新数据文件的便捷函数"""
    updater = DataUpdater(parent)
    return updater.check_and_update(show_progress)


if __name__ == "__main__":
    # 独立运行测试
    print("开始测试数据文件更新功能...")
    auto_update_data_files(show_progress=True)