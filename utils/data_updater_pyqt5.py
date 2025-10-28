#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI股票大师 - PyQt5数据自动更新模块

功能:
1. 自动下载最新的数据文件
2. 使用PyQt5显示下载进度
3. 覆盖本地文件
4. 兼容打包环境和开发环境

作者: 267278466@qq.com
版本: 2.0.0 (PyQt5版本)
"""

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QProgressBar, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

try:
    from config.gui_i18n import t_gui
except ImportError:
    def t_gui(key, **kwargs):
        return key


class DownloadThread(QThread):
    """下载线程"""
    progress_updated = pyqtSignal(int, str, str)  # 进度, 当前文件, 状态
    download_completed = pyqtSignal(int, int)      # 成功数, 总数
    
    def __init__(self, files_to_download, target_dir):
        super().__init__()
        self.files_to_download = files_to_download
        self.target_dir = target_dir
        self.cancel_download = False
        
    def run(self):
        """执行下载"""
        success_count = 0
        total_files = len(self.files_to_download)
        
        for index, file_info in enumerate(self.files_to_download):
            if self.cancel_download:
                break
                
            filename = file_info['filename']
            url = file_info['url']
            description = file_info['description']
            
            # 更新进度
            progress = int((index / total_files) * 100)
            self.progress_updated.emit(progress, filename, f"正在检查 {description}...")
            
            # 检查是否需要下载
            try:
                target_path = self.target_dir / filename
                
                # 获取远程文件信息
                need_download = True
                if target_path.exists():
                    print(f"📝 检查文件: {filename}")
                    try:
                        # 获取远程文件的头信息
                        req = urllib.request.Request(url, method='HEAD')
                        with urllib.request.urlopen(req, timeout=10) as response:
                            # 获取远程文件大小
                            remote_size = int(response.headers.get('Content-Length', 0))
                            # 获取远程文件修改时间
                            remote_time = response.headers.get('Last-Modified', '')
                            
                            # 获取本地文件大小
                            local_size = target_path.stat().st_size
                            
                            # 比对大小
                            if remote_size > 0 and remote_size == local_size:
                                print(f"✅ 文件大小相同 ({remote_size:,} 字节)，跳过下载: {filename}")
                                need_download = False
                                success_count += 1
                            else:
                                print(f"📊 文件大小不同 - 本地: {local_size:,} 字节, 远程: {remote_size:,} 字节")
                                need_download = True
                    
                    except Exception as e:
                        print(f"⚠️ 无法获取远程文件信息: {e}，将继续下载")
                        need_download = True
                
                # 如果需要下载
                if need_download:
                    # 更新进度提示
                    self.progress_updated.emit(progress, filename, f"正在下载 {description}...")
                    
                    # 下载到临时文件
                    temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
                    
                    urllib.request.urlretrieve(url, temp_path)
                    
                    # 下载成功，替换原文件
                    if temp_path.exists():
                        if target_path.exists():
                            target_path.unlink()
                        temp_path.rename(target_path)
                        success_count += 1
                        print(f"✅ 下载成功: {filename}")
                
            except Exception as e:
                print(f"❌ 下载失败 {filename}: {e}")
                # 清理临时文件
                temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
                if temp_path.exists():
                    temp_path.unlink()
        
        # 下载完成
        final_progress = 100 if success_count == total_files else int((success_count / total_files) * 100)
        self.progress_updated.emit(final_progress, "", "下载完成")
        self.download_completed.emit(success_count, total_files)
    
    def cancel(self):
        """取消下载"""
        self.cancel_download = True


class DataUpdaterDialog(QDialog):
    """PyQt5数据更新对话框"""
    
    def __init__(self, parent=None, target_dir=None):
        super().__init__(parent)
        self.target_dir = Path(target_dir) if target_dir else Path(__file__).parent.parent
        self.download_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("数据文件更新 / Data Update")
        self.setFixedSize(500, 280)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("📥 正在下载最新数据文件")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        
        # 当前文件信息
        self.current_file_label = QLabel("准备下载...")
        self.current_file_label.setFont(QFont("Microsoft YaHei", 10))
        self.current_file_label.setAlignment(Qt.AlignCenter)
        self.current_file_label.setStyleSheet("color: #333333; padding: 5px;")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                background-color: #f0f0f0;
                color: #333333;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                           stop:0 #4CAF50, stop:1 #45a049);
                border-radius: 5px;
            }
        """)
        
        # 状态信息
        self.status_label = QLabel("等待开始...")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666666; padding: 5px;")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        self.cancel_button = QPushButton("取消 / Cancel")
        self.cancel_button.setFont(QFont("Microsoft YaHei", 9))
        self.cancel_button.setFixedSize(100, 35)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_download)
        
        # 跳过按钮
        self.skip_button = QPushButton("跳过 / Skip")
        self.skip_button.setFont(QFont("Microsoft YaHei", 9))
        self.skip_button.setFixedSize(100, 35)
        self.skip_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #d39e00;
            }
        """)
        self.skip_button.clicked.connect(self.skip_update)
        
        button_layout.addWidget(self.skip_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        
        # 添加到主布局
        layout.addWidget(title_label)
        layout.addWidget(self.current_file_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addSpacing(10)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 居中显示
        if parent:
            self.move(parent.geometry().center() - self.rect().center())
    
    def start_download(self):
        """开始下载"""
        # 数据文件列表
        files_to_download = [
            {
                'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/CN_Data5000.json.gz',
                'filename': 'CN_Data5000.json.gz',
                'description': 'A股市场数据'
            },
            {
                'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/HK_Data1000.json.gz',
                'filename': 'HK_Data1000.json.gz',
                'description': '港股市场数据'
            },
            {
                'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/US_Data1000.json.gz',
                'filename': 'US_Data1000.json.gz',
                'description': '美股市场数据'
            },
            {
                'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/cn-lj.dat.gz',
                'filename': 'cn-lj.dat.gz',
                'description': '中国市场量价数据'
            },
            {
                'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/hk-lj.dat.gz',
                'filename': 'hk-lj.dat.gz',
                'description': '香港市场量价数据'
            },
            {
                'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/us-lj.dat.gz',
                'filename': 'us-lj.dat.gz',
                'description': '美国市场量价数据'
            }
        ]
        
        # 创建下载线程
        self.download_thread = DownloadThread(files_to_download, self.target_dir)
        self.download_thread.progress_updated.connect(self.on_progress_updated)
        self.download_thread.download_completed.connect(self.on_download_completed)
        self.download_thread.start()
    
    def on_progress_updated(self, progress, filename, status):
        """进度更新"""
        self.progress_bar.setValue(progress)
        if filename:
            self.current_file_label.setText(f"📄 {filename}")
        self.status_label.setText(status)
    
    def on_download_completed(self, success_count, total_files):
        """下载完成"""
        self.cancel_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        
        if success_count == total_files:
            self.current_file_label.setText("✅ 所有文件下载成功！")
            self.status_label.setText(f"成功下载 {success_count}/{total_files} 个文件")
        else:
            self.current_file_label.setText(f"⚠️ 部分文件下载失败")
            self.status_label.setText(f"成功: {success_count}/{total_files}")
        
        # 3秒后自动关闭
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, self.accept)
    
    def cancel_download(self):
        """取消下载"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.status_label.setText("❌ 下载已取消")
        self.reject()
    
    def skip_update(self):
        """跳过更新"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
        self.status_label.setText("⏭️ 跳过更新")
        self.reject()


def show_update_dialog(parent=None, target_dir=None):
    """显示更新对话框"""
    dialog = DataUpdaterDialog(parent, target_dir)
    dialog.start_download()
    return dialog.exec_() == QDialog.Accepted


def silent_update(target_dir=None):
    """静默更新（不显示界面）"""
    if target_dir is None:
        target_dir = Path(__file__).parent.parent
    else:
        target_dir = Path(target_dir)
    
    print("开始静默更新数据文件...")
    
    files_to_download = [
        {
            'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/CN_Data5000.json.gz',
            'filename': 'CN_Data5000.json.gz',
        },
        {
            'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/HK_Data1000.json.gz',
            'filename': 'HK_Data1000.json.gz',
        },
        {
            'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/US_Data1000.json.gz',
            'filename': 'US_Data1000.json.gz',
        },
        {
            'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/cn-lj.dat.gz',
            'filename': 'cn-lj.dat.gz',
        },
        {
            'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/hk-lj.dat.gz',
            'filename': 'hk-lj.dat.gz',
        },
        {
            'url': 'https://gh-proxy.com/https://github.com/hengruiyun/AI-Stock-Master/raw/refs/heads/main/us-lj.dat.gz',
            'filename': 'us-lj.dat.gz',
        }
    ]
    
    success_count = 0
    for file_info in files_to_download:
        filename = file_info['filename']
        url = file_info['url']
        
        try:
            target_path = target_dir / filename
            
            # 检查是否需要下载
            need_download = True
            if target_path.exists():
                print(f"📝 检查文件: {filename}")
                try:
                    # 获取远程文件的头信息
                    req = urllib.request.Request(url, method='HEAD')
                    with urllib.request.urlopen(req, timeout=10) as response:
                        # 获取远程文件大小
                        remote_size = int(response.headers.get('Content-Length', 0))
                        # 获取本地文件大小
                        local_size = target_path.stat().st_size
                        
                        # 比对大小
                        if remote_size > 0 and remote_size == local_size:
                            print(f"✅ 文件大小相同 ({remote_size:,} 字节)，跳过: {filename}")
                            need_download = False
                            success_count += 1
                        else:
                            print(f"📊 文件大小不同 - 本地: {local_size:,} 字节, 远程: {remote_size:,} 字节")
                            need_download = True
                
                except Exception as e:
                    print(f"⚠️ 无法获取远程文件信息: {e}，将继续下载")
                    need_download = True
            
            # 如果需要下载
            if need_download:
                temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
                
                print(f"⬇️ 下载 {filename}...")
                urllib.request.urlretrieve(url, temp_path)
                
                if temp_path.exists():
                    if target_path.exists():
                        target_path.unlink()
                    temp_path.rename(target_path)
                    success_count += 1
                    print(f"✅ 下载成功: {filename}")
        
        except Exception as e:
            print(f"❌ {filename}: {e}")
            temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
            if temp_path.exists():
                temp_path.unlink()
    
    print(f"更新完成: {success_count}/{len(files_to_download)}")
    return success_count == len(files_to_download)


if __name__ == "__main__":
    # 测试
    app = QApplication(sys.argv)
    result = show_update_dialog()
    sys.exit(0 if result else 1)













