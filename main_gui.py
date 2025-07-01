#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI股票趋势分析系统 - 主程序入口

使用方法:
1. 直接运行: python main_gui.py
2. 点击"加载"按钮选择Excel数据文件
3. 点击"分析"按钮开始数据分析
4. 点击"报告"按钮查看HTML报告

作者: 267278466@qq.com
版本: 2.0.0
"""

import sys
import os
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入国际化模块
try:
    from localization.improved_language_manager import _
    print("语言管理器加载成功")
except ImportError as e:
    print(f"Warning: 语言管理器导入失败: {e}")
    # 如果导入失败，使用简单的回退函数
    def _(key, default=None):
        return default or key

# 导入GUI模块
try:
    from gui.main_window import StockAnalyzerMainWindowExtended
    print(_('gui_import_success', '成功 GUI模块导入成功'))
except ImportError as e:
    print(f"{_('gui_import_failed', '错误 GUI模块导入失败')}: {e}")
    print(_('gui_check_files', '请确保gui目录下的所有文件都已正确创建'))
    sys.exit(1)

# 导入核心模块 (可选，用于验证)
try:
    from config import get_config
    from data.stock_dataset import StockDataSet
    from algorithms.realtime_engine import RealtimeAnalysisEngine
    print(_('core_modules_available', '成功 核心模块可用'))
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"{_('core_modules_warning', '警告 核心模块部分不可用')}: {e}")
    print(_('gui_limited_functionality', 'GUI界面可以启动，但分析功能可能受限'))
    CORE_MODULES_AVAILABLE = False


def check_environment():
    """检查运行环境"""
    print(_('checking_environment', '检查 检查运行环境...'))
    
    # Python版本检查
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"{_('python_version_low', '错误 Python版本过低')}: {python_version.major}.{python_version.minor}")
        print(_('python_version_recommend', '建议使用Python 3.10+'))
        return False
    else:
        print(f"{_('python_version_ok', '成功 Python版本')}: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 必需模块检查
    required_modules = ['tkinter', 'pandas', 'numpy', 'matplotlib']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"{_('module_available', '成功')} {module} {_('available', '可用')}")
        except ImportError:
            missing_modules.append(module)
            print(f"{_('module_missing', '错误')} {module} {_('missing', '缺失')}")
    
    if missing_modules:
        print(f"\n{_('missing_modules', '缺失的模块')}: {', '.join(missing_modules)}")
        print(_('install_command', '请运行: pip install pandas numpy matplotlib'))
        return False
    
    # 可选模块检查
    optional_modules = ['plotly', 'openpyxl', 'scipy']
    for module in optional_modules:
        try:
            __import__(module)
            print(f"{_('module_available', '成功')} {module} ({_('optional', '可选')})")
        except ImportError:
            print(f"{_('module_warning', '警告')} {module} ({_('optional', '可选')}) {_('not_available', '不可用')}")
    
    print(f"{_('environment_check_complete', '成功 环境检查完成')}\n")
    return True


def show_startup_info():
    """显示启动信息"""
    print("="*60)
    print(_('startup_title', '快速 AI股票趋势分析系统'))
    print("="*60)
    print()
    print(_('startup_features', '数据 功能特点:'))
    print(f"• RTSI - {_('rtsi_desc', '个股评级趋势强度指数')}")
    print(f"• IRSI - {_('irsi_desc', '行业相对强度指数')}")  
    print(f"• MSCI - {_('msci_desc', '市场情绪综合指数')}")
    print(f"• {_('windows_classic_ui', 'Windows经典风格界面')}")
    print(f"• {_('realtime_analysis_engine', '实时数据分析引擎')}")
    print(f"• {_('advanced_visualization', '高级可视化报告')}")
    print()
    print(_('startup_data_support', '核心 支持数据:'))
    print(f"• {_('excel_format', 'Excel格式')}: *.xlsx, *.xls")
    print(f"• {_('stock_count', '股票数量')}: 5,000+ {_('stocks', '只')}")
    print(f"• {_('industry_classification', '行业分类')}: 85 {_('categories', '个')}")
    print(f"• {_('rating_system', '评级系统')}: 8{_('levels', '级')} ({_('rating_range', '大多→大空')})")
    print()
    print(_('startup_shortcuts', '快速 快捷操作:'))
    print(f"• Ctrl+O: {_('open_file', '打开文件')}")
    print(f"• F5: {_('start_analysis', '开始分析')}")
    print(f"• Ctrl+S: {_('export_report', '导出报告')}")
    print()


    """创建示例配置文件"""
    config_content = '''# AI股票趋势分析系统配置文件
# 第四期: GUI界面核心

[GUI]
theme = classic
font_size = 10
window_width = 1000
window_height = 700
remember_position = true

[Analysis]
rtsi_min_points = 5
rtsi_consistency_weight = 0.4
irsi_period = 20
msci_bull_threshold = 0.02
use_multithread = true
enable_cache = true

[Paths]
data_directory = ./data
output_directory = ./output
cache_directory = ./cache
'''
    
    config_file = project_root / "app.ini"
    if not config_file.exists():
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print(f"成功 创建配置文件: {config_file}")
        except Exception as e:
            print(f"警告 创建配置文件失败: {e}")


def main():
    """主程序入口"""
    try:
        # 显示启动信息
        show_startup_info()
        
        # 检查环境
        if not check_environment():
            input("按回车键退出...")
            return
        
        # 创建必要目录
        directories = ['data', 'output', 'cache', 'reports', 'logs']
        for dir_name in directories:
            dir_path = project_root / dir_name
            dir_path.mkdir(exist_ok=True)
        
        # 自动更新数据文件
        print("检查 检查数据文件更新...")
        try:
            from utils.data_updater import auto_update_data_files
            # 在控制台显示更新信息，但不显示GUI进度窗口
            print("更新 正在检查并下载最新数据文件...")
            update_success = auto_update_data_files(parent=None, show_progress=False)
            if update_success:
                print("成功 数据文件更新完成")
            else:
                print("警告 部分数据文件更新失败，将使用现有文件")
        except Exception as e:
            print(f"警告 数据文件更新失败: {e}")
            print("提示 将使用现有数据文件，不影响系统正常使用")
        
        # 初始化用户配置
        try:
            from config import load_user_config
            user_config = load_user_config()
            print("用户配置文件加载成功")
        except ImportError:
            print("配置模块未找到，使用默认配置")
        except Exception as e:
            print(f"未找到用户配置文件，使用默认配置")
        
        print("系统 启动GUI界面...")
        print("提示 提示: 可以通过菜单 -> 帮助 -> 使用说明 查看详细操作指南")
        print()
        
        # 启动GUI应用
        app = StockAnalyzerMainWindowExtended()
        app.run()
        
    except KeyboardInterrupt:
        print("\n退出 用户中断，程序退出")
    
    except Exception as e:
        print(f"\n失败 程序启动失败:")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print(f"\n列表 详细错误信息:")
        traceback.print_exc()
        
        # 显示错误对话框
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            
            error_msg = f"""程序启动时发生错误:

错误类型: {type(e).__name__}
错误信息: {str(e)}

可能的解决方案:
1. 检查Python版本是否为3.8+
2. 安装缺失的依赖包: pip install pandas numpy matplotlib
3. 确保gui目录下的所有文件都存在
4. 重新下载完整的项目文件

如需技术支持，请保存此错误信息并联系：267278466@qq.com"""
            
            messagebox.showerror("启动错误", error_msg)
            
        except:
            pass  # 如果连tkinter都不可用，就只显示控制台错误
        
        input("\n按回车键退出...")


def test_mode():
    """测试模式 - 仅测试GUI组件"""
    print("测试 进入测试模式...")
    
    try:
        import tkinter as tk
        
        # 测试主窗口
        print("测试主窗口...")
        root = tk.Tk()
        root.title("GUI测试 - AI股票趋势分析系统")
        root.geometry("800x600")
        root.configure(bg='#f0f0f0')
        
        # 测试界面
        test_frame = tk.Frame(root, bg='#f0f0f0')
        test_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(test_frame, 
                              text="核心 GUI组件测试",
                              bg='#f0f0f0', fg='#0078d4',
                              font=('Microsoft YaHei', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        status_text = """成功 tkinter界面框架正常
成功 Windows经典风格可用
成功 中文字体支持正常
成功 基础组件功能正常

配置 测试项目:
• 主窗口创建 ✓
• 菜单栏显示 ✓  
• 按钮控件 ✓
• 文本显示 ✓
• 布局管理 ✓

提示 如果看到此界面，说明GUI基础组件工作正常。
   关闭此窗口可继续测试其他组件。"""
        
        status_label = tk.Label(test_frame, text=status_text,
                               bg='#f0f0f0', fg='#333333',
                               font=('Microsoft YaHei', 10),
                               justify=tk.LEFT)
        status_label.pack()
        
        # 测试按钮
        def test_dialogs():
            """测试对话框"""
            from gui.analysis_dialogs import AboutDialog
            AboutDialog(root)
        
        test_btn = tk.Button(test_frame, text="测试关于对话框",
                            command=test_dialogs,
                            bg='#f0f0f0', relief=tk.RAISED, bd=2)
        test_btn.pack(pady=20)
        
        close_btn = tk.Button(test_frame, text="关闭测试",
                             command=root.destroy,
                             bg='#f0f0f0', relief=tk.RAISED, bd=2)
        close_btn.pack()
        
        root.mainloop()
        print("成功 GUI组件测试完成")
        
    except Exception as e:
        print(f"错误 GUI测试失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_mode()
    else:
        main()