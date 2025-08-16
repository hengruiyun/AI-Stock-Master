#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动设置界面的无控制台窗口脚本
使用.pyw扩展名确保在Windows上不显示控制台窗口
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from settings_gui import SettingsWindow
    
    def main():
        """主函数 - 无控制台输出"""
        app = SettingsWindow()
        app.run()
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    # 无控制台模式下，错误处理需要使用GUI
    import tkinter as tk
    from tkinter import messagebox
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    messagebox.showerror("导入错误", f"导入错误: {e}\n请确保所有依赖已安装")
    root.destroy()
    
except Exception as e:
    # 无控制台模式下，错误处理需要使用GUI
    import tkinter as tk
    from tkinter import messagebox
    
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    messagebox.showerror("运行错误", f"运行错误: {e}")
    root.destroy() 