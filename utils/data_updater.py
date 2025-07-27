#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.i18n import t_gui, is_english
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

# 使用config.i18n中的t_gui作为翻译函数
_ = t_gui


class DataUpdater:
    """数据文件自动更新器"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.project_root = Path(__file__).parent.parent
        
        # 要下载的文件列表
        from config.i18n import t_tools
        self.files_to_download = [
            {
                'url': 'https://github.com/hengruiyun/AI-Stock-Analysis/raw/refs/heads/main/CN_Demo300.json.gz',
                'filename': 'CN_Demo300.json.gz',
                'description': t_tools('cn_demo_desc')
            },
            {
                'url': 'https://github.com/hengruiyun/AI-Stock-Analysis/raw/refs/heads/main/HK_Demo300.json.gz',
                'filename': 'HK_Demo300.json.gz',
                'description': t_tools('hk_demo_desc')
            },
            {
                'url': 'https://github.com/hengruiyun/AI-Stock-Analysis/raw/refs/heads/main/US_Demo300.json.gz',
                'filename': 'US_Demo300.json.gz',
                'description': t_tools('us_demo_desc')
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
        from config.i18n import t_tools
        self.download_window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.download_window.title(t_tools('update_title'))
        self.download_window.geometry('500x300')
        self.download_window.resizable(False, False)
        self.download_window.configure(bg='#f0f0f0')
        
        # 窗口居中
        self._center_window()
        
        # 标题
        title_label = tk.Label(self.download_window, 
                              text=t_tools('update_downloading'),
                              font=('Microsoft YaHei', 12, 'bold'),
                              bg='#f0f0f0', fg='#0078d4')
        title_label.pack(pady=(20, 10))
        
        # 当前文件信息
        self.current_file_var = tk.StringVar()
        self.current_file_var.set(t_tools('update_preparing'))
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
        self.status_var.set(t_tools('update_status_ready'))
        status_label = tk.Label(self.download_window,
                               textvariable=self.status_var,
                               font=('Microsoft YaHei', 9),
                               bg='#f0f0f0', fg='#666666')
        status_label.pack(pady=(10, 20))
        
        # 按钮区域
        button_frame = tk.Frame(self.download_window, bg='#f0f0f0')
        button_frame.pack(pady=10)
        
        # 跳过按钮
        skip_btn = tk.Button(button_frame,
                            text=t_tools('btn_skip'),
                            command=self._skip_update,
                            font=('Microsoft YaHei', 10),
                            bg='#f0f0f0', relief=tk.RAISED, bd=2,
                            padx=20, pady=5)
        skip_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame,
                              text=t_tools('btn_cancel'),
                              command=self._cancel_download,
                              font=('Microsoft YaHei', 10),
                              bg='#f0f0f0', relief=tk.RAISED, bd=2,
                              padx=20, pady=5)
        cancel_btn.pack(side=tk.LEFT)
        
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
        # 首先检查哪些文件需要下载
        files_need_download = self._check_files_need_update()
        
        if not files_need_download:
            # 所有文件都是最新的
            from config.i18n import t_tools
            if self.current_file_var:
                self.current_file_var.set(t_tools('update_all_latest'))
            if self.status_var:
                self.status_var.set(t_tools('update_no_need'))
            if self.progress_var:
                self.progress_var.set(100)
            
            # 2秒后关闭窗口
            if self.download_window:
                self.download_window.after(2000, self._close_window)
            return True
        
        total_files = len(files_need_download)
        success_count = 0
        
        for i, file_info in enumerate(files_need_download):
            if self.cancel_download:
                break
                
            # 更新当前文件信息
            if self.current_file_var:
                from config.i18n import t_tools
                self.current_file_var.set(t_tools('update_downloading_file') + f": {file_info['description']}")
            
            # 更新状态
            if self.status_var:
                self.status_var.set(t_tools('update_progress') + f": {i+1}/{total_files}")
            
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
    
    def _check_files_need_update(self):
        """检查哪些文件需要下载"""
        files_need_download = []
        
        for file_info in self.files_to_download:
            filename = file_info['filename']
            local_path = self.project_root / filename
            
            # 检查文件是否存在
            if not local_path.exists():
                files_need_download.append(file_info)
                continue
            
            # 检查文件大小是否一致
            try:
                # 获取远程文件大小
                request = urllib.request.Request(file_info['url'])
                request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                request.get_method = lambda: 'HEAD'  # 只获取头信息
                
                with urllib.request.urlopen(request, timeout=10) as response:
                    remote_size = int(response.headers.get('Content-Length', 0))
                
                # 获取本地文件大小
                local_size = local_path.stat().st_size
                
                # 如果大小不一致，需要下载
                if remote_size != local_size:
                    files_need_download.append(file_info)
                    from config.i18n import t_tools
                    print(f"{t_tools('update_size_mismatch')}: {filename} ({local_size} != {remote_size})")
                else:
                    from config.i18n import t_tools
                    print(f"{t_tools('update_file_latest')}: {filename}")
                    
            except Exception as e:
                # 如果检查失败，保险起见重新下载
                files_need_download.append(file_info)
                from config.i18n import t_tools
                print(f"{t_tools('update_check_failed')}: {filename} - {e}")
        
        return files_need_download
    
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
                            from config.i18n import t_tools
                            size_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            self.status_var.set(t_tools('update_downloading') + f": {size_mb:.1f}MB / {total_mb:.1f}MB")
            
            from config.i18n import t_tools
            print(t_tools('update_success') + f": {filename}")
            return True
            
        except Exception as e:
            from config.i18n import t_tools
            print(t_tools('update_failed') + f" {filename}: {e}")
            if self.status_var:
                self.status_var.set(t_tools('update_error') + f": {filename} - {str(e)[:50]}")
            return False
    
    def _download_completed(self, success_count, total_files):
        """下载完成处理"""
        if self.download_window:
            from config.i18n import t_tools
            if success_count == total_files:
                # 全部成功
                self.current_file_var.set(t_tools('update_complete_success'))
                self.status_var.set(t_tools('update_all_success'))
                self.progress_var.set(100)
            else:
                # 部分成功
                self.current_file_var.set(t_tools('update_partial_success') + f": {success_count}/{total_files}")
                self.status_var.set(t_tools('update_some_failed'))
            
            # 3秒后自动关闭
            self.download_window.after(3000, self._close_window)
    
    def _cancel_download(self):
        """取消下载"""
        self.cancel_download = True
        if self.status_var:
            from config.i18n import t_tools
            self.status_var.set(t_tools('update_cancelled'))
        self._close_window()
    
    def _skip_update(self):
        """跳过更新"""
        self.cancel_download = True
        if self.status_var:
            from config.i18n import t_tools
            self.status_var.set(t_tools('update_skipped'))
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
    print("...")
    auto_update_data_files(show_progress=True)