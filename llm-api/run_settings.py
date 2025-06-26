#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动设置界面的简单脚本
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
        """主函数"""
        print("启动LLM API设置界面...")
        app = SettingsWindow()
        app.run()
        print("设置界面已关闭")
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有依赖已安装")
    input("按回车键退出...")
except Exception as e:
    print(f"运行错误: {e}")
    input("按回车键退出...")