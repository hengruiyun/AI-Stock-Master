#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动画面模块
Splash Screen Module

提供美观的应用启动画面，显示加载进度和状态信息
"""

import sys
from PyQt5.QtWidgets import QSplashScreen, QApplication, QProgressBar, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QLinearGradient
from pathlib import Path


class ModernSplashScreen(QSplashScreen):
    """现代化启动画面"""
    
    def __init__(self, pixmap=None, width=600, height=400):
        if pixmap is None:
            # 如果没有提供图片，创建一个渐变背景
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制渐变背景
            gradient = QLinearGradient(0, 0, 0, height)
            gradient.setColorAt(0, QColor(102, 126, 234))  # #667eea
            gradient.setColorAt(1, QColor(118, 75, 162))   # #764ba2
            painter.fillRect(0, 0, width, height, gradient)
            
            # 绘制标题
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            title_font = QFont("Microsoft YaHei", 36, QFont.Bold)
            painter.setFont(title_font)
            painter.drawText(0, 80, width, 100, Qt.AlignCenter, "AI股票大师")
            
            # 绘制副标题
            subtitle_font = QFont("Microsoft YaHei", 14)
            painter.setFont(subtitle_font)
            painter.setPen(QPen(QColor(255, 255, 255, 200)))
            painter.drawText(0, 150, width, 50, Qt.AlignCenter, "AI Stock Master")
            
            # 绘制版本信息
            version_font = QFont("Microsoft YaHei", 10)
            painter.setFont(version_font)
            painter.drawText(0, height - 40, width, 30, Qt.AlignCenter, "Professional Edition")
            
            painter.end()
        
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.SplashScreen)
        
        # 创建状态标签
        self.status_label = QLabel(self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-family: 'Microsoft YaHei';
                background-color: transparent;
                padding: 10px;
            }
        """)
        self.status_label.setGeometry(50, height - 130, width - 100, 32)
        
        # 创建进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(50, height - 80, width - 100, 25)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid white;
                border-radius: 12px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 255, 255, 0.8),
                    stop:1 rgba(255, 255, 255, 0.6)
                );
                border-radius: 10px;
            }
        """)
        self.progress_bar.setValue(0)
        
        # 详细信息标签（可选）
        self.detail_label = QLabel(self)
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 180);
                font-size: 11px;
                font-family: 'Microsoft YaHei';
                background-color: transparent;
            }
        """)
        self.detail_label.setGeometry(50, height - 155, width - 100, 30)
        self.detail_label.setWordWrap(True)
        self.detail_label.setText("")
    
    def showMessage(self, message, alignment=Qt.AlignBottom | Qt.AlignCenter, color=Qt.white):
        """显示状态消息"""
        self.status_label.setText(message)
        QApplication.processEvents()

    def showProgress(self, value, message=""):
        """更新进度条"""
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
        QApplication.processEvents()

    def showDetail(self, detail):
        """显示详细信息"""
        self.detail_label.setText(detail)
        QApplication.processEvents()


class SplashLogger(QObject):
    """将控制台输出重定向到启动画面状态标签并保留原始流"""

    def __init__(self, splash_screen: ModernSplashScreen):
        super().__init__()
        self.splash = splash_screen
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self._closed = False

    def install(self):
        sys.stdout = self
        sys.stderr = self

    def restore(self):
        """恢复原始的stdout和stderr"""
        if not self._closed:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self._closed = True

    def write(self, text):
        if self._closed:
            # 如果已经关闭，直接写到原始流
            if self.original_stdout and hasattr(self.original_stdout, 'write'):
                try:
                    self.original_stdout.write(text)
                except:
                    pass
            return
        
        if text.strip():
            try:
                self.splash.showMessage(text.strip())
            except:
                pass  # 如果splash已经被删除，忽略错误
        
        if self.original_stdout and hasattr(self.original_stdout, 'write'):
            try:
                self.original_stdout.write(text)
            except:
                pass

    def flush(self):
        if self._closed:
            if self.original_stdout and hasattr(self.original_stdout, 'flush'):
                try:
                    self.original_stdout.flush()
                except:
                    pass
            return
        
        if self.original_stdout and hasattr(self.original_stdout, 'flush'):
            try:
                self.original_stdout.flush()
            except:
                pass
    
    @property
    def closed(self):
        """colorama需要此属性"""
        return self._closed
    
    def isatty(self):
        """colorama需要此方法"""
        if self._closed and self.original_stdout and hasattr(self.original_stdout, 'isatty'):
            try:
                return self.original_stdout.isatty()
            except:
                return False
        return False
    
    def __del__(self):
        """析构时确保恢复原始流"""
        self.restore()


class StartupLoader(QThread):
    """启动加载线程"""
    
    progress_updated = pyqtSignal(int, str, str)  # progress, message, detail
    finished_loading = pyqtSignal(bool, str)  # success, error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = []
        self.current_step = 0
        
    def add_step(self, name, function, detail=""):
        """添加加载步骤"""
        self.steps.append({
            'name': name,
            'function': function,
            'detail': detail
        })
    
    def run(self):
        """执行加载步骤"""
        total_steps = len(self.steps)
        
        for i, step in enumerate(self.steps):
            try:
                # 更新进度
                progress = int((i / total_steps) * 100)
                self.progress_updated.emit(progress, step['name'], step['detail'])
                
                # 执行步骤
                if step['function']:
                    step['function']()
                
                # 短暂延迟，让用户能看到进度
                self.msleep(100)
                
            except Exception as e:
                error_msg = f"{step['name']} 失败: {str(e)}"
                self.finished_loading.emit(False, error_msg)
                return
        
        # 完成
        self.progress_updated.emit(100, "加载完成", "正在启动主界面...")
        self.msleep(300)
        self.finished_loading.emit(True, "")


def create_splash_screen(app=None):
    """创建启动画面的便捷函数"""
    if app is None:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
    
    # 尝试加载自定义启动图片
    splash_image_path = Path("resources/splash.png")
    
    if splash_image_path.exists():
        pixmap = QPixmap(str(splash_image_path))
        splash = ModernSplashScreen(pixmap)
    else:
        # 使用默认渐变背景
        splash = ModernSplashScreen()
    
    splash.show()
    app.processEvents()
    
    return splash


def show_splash_with_loader(loading_steps, on_complete_callback=None):
    """
    显示启动画面并执行加载步骤
    
    参数:
        loading_steps: list of dict, 每个dict包含 'name', 'function', 'detail'
        on_complete_callback: function, 加载完成后的回调函数
    
    示例:
        steps = [
            {'name': '加载配置...', 'function': load_config, 'detail': 'config.ini'},
            {'name': '初始化数据库...', 'function': init_db, 'detail': 'stock_data.db'},
        ]
        show_splash_with_loader(steps, lambda: main_window.show())
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # 创建启动画面
    splash = create_splash_screen(app)
    
    # 创建加载线程
    loader = StartupLoader()
    
    for step in loading_steps:
        loader.add_step(
            step.get('name', '加载中...'),
            step.get('function', None),
            step.get('detail', '')
        )
    
    # 连接信号
    def update_progress(progress, message, detail):
        splash.showProgress(progress, message)
        splash.showDetail(detail)
    
    def on_loading_finished(success, error_message):
        if success:
            splash.showProgress(100, "启动成功！")
            QTimer.singleShot(300, lambda: splash.finish(None))
            if on_complete_callback:
                QTimer.singleShot(400, on_complete_callback)
        else:
            splash.showProgress(0, f"启动失败: {error_message}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "启动错误", 
                               f"应用程序启动失败：\n\n{error_message}\n\n请查看日志文件获取更多信息。")
            QTimer.singleShot(2000, lambda: splash.finish(None))
            app.quit()
    
    loader.progress_updated.connect(update_progress)
    loader.finished_loading.connect(on_loading_finished)
    
    # 启动加载
    loader.start()
    
    return splash, loader


# 示例使用
if __name__ == "__main__":
    import time
    
    app = QApplication(sys.argv)
    
    # 定义加载步骤
    def step1():
        time.sleep(0.5)
        print("Step 1 completed")
    
    def step2():
        time.sleep(0.5)
        print("Step 2 completed")
    
    def step3():
        time.sleep(0.5)
        print("Step 3 completed")
    
    steps = [
        {'name': '正在加载配置文件...', 'function': step1, 'detail': 'config/app.ini'},
        {'name': '正在初始化数据模块...', 'function': step2, 'detail': 'data/stock_dataset.py'},
        {'name': '正在加载AI引擎...', 'function': step3, 'detail': 'algorithms/realtime_engine.py'},
    ]
    
    def show_main_window():
        print("Main window would show here")
        QTimer.singleShot(2000, app.quit)
    
    splash, loader = show_splash_with_loader(steps, show_main_window)
    
    sys.exit(app.exec_())

