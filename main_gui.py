#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from config.i18n import t_gui as _
"""
AI股票趋势分析系统 - 主程序入口

使用方法:
1. 直接运行: python main_gui.py
2. 点击"加载"按钮选择JSON数据文件
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

# 已导入国际化模块 (config.i18n)

# 导入GUI模块
try:
    from gui.main_window import StockAnalyzerMainWindowExtended
    print(_('gui_import_success'))
except ImportError as e:
    print(f"{_('gui_import_failed')}: {e}")
    print(_('gui_check_files'))
    sys.exit(1)

# 导入核心模块 (可选，用于验证)
try:
    from config import get_config
    from data.stock_dataset import StockDataSet
    from algorithms.realtime_engine import RealtimeAnalysisEngine
    print(_('core_modules_available'))
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"{_('core_modules_warning')}: {e}")
    print(_('gui_limited_functionality'))
    CORE_MODULES_AVAILABLE = False


def check_environment():
    """检查运行环境"""
    print(_('checking_environment'))
    
    # Python版本检查
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"{_('python_version_low')}: {python_version.major}.{python_version.minor}")
        print(_('python_version_recommend'))
        return False
    else:
        print(f"{_('python_version_ok')}: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 必需模块检查
    required_modules = ['tkinter', 'pandas', 'numpy', 'matplotlib']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"{_('module_available')} {module} {_('available')}")
        except ImportError:
            missing_modules.append(module)
            print(f"{_('module_missing')} {module} {_('missing')}")
    
    if missing_modules:
        print(f"\n{_('missing_modules')}: {', '.join(missing_modules)}")
        print(_('install_command'))
        return False
    
    # 可选模块检查
    optional_modules = ['plotly', 'openpyxl', 'scipy']
    for module in optional_modules:
        try:
            __import__(module)
            print(f"{_('module_available')} {module} ({_('optional')})")
        except ImportError:
            print(f"{_('module_warning')} {module} ({_('optional')}) {_('not_available')}")
    
    print(f"{_('environment_check_complete')}\n")
    return True


def show_startup_info():
    """显示启动信息"""
    print(""*60)
    print(_('startup_title'))
    print(""*60)
    print()
    print(_('startup_features'))
    print(f"• RTSI - {_('rtsi_desc')}")
    print(f"• IRSI - {_('irsi_desc')}")  
    print(f"• MSCI - {_('msci_desc')}")
    print(f"• {_('windows_classic_ui')}")
    print(f"• {_('realtime_analysis_engine')}")
    print(f"• {_('advanced_visualization')}")
    print()
    print(_('startup_data_support'))
    print(f"• {_('excel_format')}: *.json.gz")
    print(f"• {_('stock_count')}: 5,000+ {_('units_stocks')}")
    print(f"• {_('industry_classification')}: 85 {_('units_categories')}")
    print(f"• {_('rating_system')}: 8{_('units_levels')} ({_('rating_range')})")
    print()
    print(_('startup_shortcuts'))
    print(f"• Ctrl+O: {_('open_file')}")
    print(f"• F5: {_('start_analysis')}")
    print(f"• Ctrl+S: {_('export_report')}")
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
            input(_('press_enter_to_exit'))
            return
        
        # 创建必要目录
        directories = ['data', 'output', 'cache', 'reports', 'logs']
        for dir_name in directories:
            dir_path = project_root / dir_name
            dir_path.mkdir(exist_ok=True)
        
        # 自动更新数据文件
        print(_('updating_data_files'))
        try:
            from utils.data_updater import auto_update_data_files
            # 在控制台显示更新信息，但不显示GUI进度窗口
            print(_('checking_updates'))
            update_success = auto_update_data_files(parent=None, show_progress=False)
            if update_success:
                print(_('update_success'))
            else:
                print(_('update_not_needed'))
        except Exception as e:
            print(f"{_('update_failed')}: {e}")
            print(_('continuing_without_update'))
        
        # 初始化用户配置
        try:
            from config import load_user_config
            user_config = load_user_config()
            print(_('config_loaded'))
        except ImportError:
            print(_('config_import_error'))
        except Exception as e:
            print(f"{_('config_not_found_using_defaults')}")
        
        print(_('starting_gui'))
        print(_('initializing_components'))
        print()
        
        # 启动GUI应用
        app = StockAnalyzerMainWindowExtended()
        app.run()
        
    except KeyboardInterrupt:
        print(f"\n{_('exit_user_interrupt')}")
    
    except Exception as e:
        print(f"\n{_('startup_failed')}:")
        print(f"{_('error_type')}: {type(e).__name__}")
        print(f"{_('error_message')}: {str(e)}")
        print(f"\n{_('detailed_error_info')}:")
        traceback.print_exc()
        
        # 显示错误对话框
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            
            error_msg = f"""{_('startup_error_occurred')}:

{_('error_type')}: {type(e).__name__}
{_('error_message')}: {str(e)}

{_('possible_solutions')}:
1. {_('check_python_version')}
2. {_('install_missing_dependencies')}: pip install pandas numpy matplotlib
3. {_('ensure_gui_files_exist')}
4. {_('download_complete_project')}

{_('technical_support_contact')}: 267278466@qq.com"""
            
            messagebox.showerror(_('startup_error'), error_msg)
            
        except:
            pass  # 如果连tkinter都不可用，就只显示控制台错误
        
        input(f"\n{_('press_enter_to_exit')}")


def test_mode():
    """测试模式 - 仅测试GUI组件"""
    print("...")
    
    try:
        import tkinter as tk
        
        # 测试主窗口
        print("...")
        root = tk.Tk()
        root.title("GUI测试 - AI股票趋势分析系统")
        root.geometry("800x600")
        root.configure(bg='#f0f0f0')
        
        # 测试界面
        test_frame = tk.Frame(root, bg='#f0f0f0')
        test_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        title_label = tk.Label(test_frame, 
                              text="GUI",
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
        
        test_btn = tk.Button(test_frame, text="",
                            command=test_dialogs,
                            bg='#f0f0f0', relief=tk.RAISED, bd=2)
        test_btn.pack(pady=20)
        
        close_btn = tk.Button(test_frame, text="",
                             command=root.destroy,
                             bg='#f0f0f0', relief=tk.RAISED, bd=2)
        close_btn.pack()
        
        root.mainloop()
        print("GUI")
        
    except Exception as e:
        print(f"错误 GUI测试失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_mode()
    else:
        main()