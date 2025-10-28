#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI股票大师界面

作者:267278466@qq.com
"""

import sys
import os
import json
import gzip
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import io

# 修复 console=False 模式下 sys.stdout/stderr 为 None 的问题
# 必须在最开始就设置，避免后续任何模块导入时出错
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# 过滤警告信息
import warnings
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*')
warnings.filterwarnings('ignore', category=UserWarning, module='.*pkg_resources.*')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 全局变量：跟踪本次运行的解压状态
DECOMPRESSED_FILES_THIS_RUN = set()  # 记录本次运行已解压的文件

# 跨平台字体配置
def get_cross_platform_font():
    """获取跨平台兼容的字体名称"""
    import platform
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return "PingFang SC"
    elif system == "Windows":
        return "Microsoft YaHei"
    else:  # Linux
        return "Arial"

def get_cross_platform_font_family():
    """获取跨平台兼容的字体族"""
    return "Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif"

# =====================================

# PyQt5相关导入
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QFileDialog,
    QProgressBar, QTextEdit, QSplitter, QFrame, QStackedWidget,
    QMessageBox, QScrollArea, QGridLayout, QGroupBox, QTextBrowser,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor, QIcon

try:
    import psutil
except ImportError:
    psutil = None


# 备用翻译函数（在导入失败时使用）- 必须在任何使用前定义
def t_gui_fallback(key, **kwargs):
    return key

def t_common_fallback(key, **kwargs):
    return key

# 可选导入 WebEngine
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    print("WebEngine unavailable")  # 暂时不使用t_gui
    QWebEngineView = None
    QWebEngineSettings = None
    WEBENGINE_AVAILABLE = False

# 项目模块导入
try:
    from data.stock_dataset import StockDataSet
    from algorithms.realtime_engine import RealtimeAnalysisEngine
    from utils.report_generator import ReportGenerator
    try:
        from utils.path_helper import (
            get_base_path, get_resource_path, get_data_path, get_data_file_path,
            get_reports_dir, get_cache_dir, get_logs_dir,
            is_frozen, print_path_info
        )
    except ImportError as e:
        print(f"[ERROR] 导入path_helper失败: {e}")
        # 提供备用实现
        import sys
        from pathlib import Path
        def get_base_path():
            if getattr(sys, 'frozen', False):
                return Path(sys.executable).parent
            return Path(__file__).parent
        def get_resource_path(relative_path):
            return get_base_path() / relative_path
        def get_data_path():
            return get_base_path()
        def get_data_file_path(filename):
            return get_base_path() / filename
        def get_reports_dir():
            return get_base_path() / 'reports'
        def get_cache_dir():
            return get_base_path() / 'cache'
        def get_logs_dir():
            return get_base_path() / 'logs'
        def is_frozen():
            return getattr(sys, 'frozen', False)
        def print_path_info():
            print(f"Base path: {get_base_path()}")
    # 移除不存在的config.i18n导入
    # from config.i18n import t_common
    from config.gui_i18n import t_gui, set_language, get_system_language
    from config import get_config
    # 暂时注释掉mini模块导入，避免导入错误
    # from mini import MiniInvestmentMasterGUI
    
    # 定义t_common函数
    def t_common(key, **kwargs):
        """通用翻译函数，目前直接返回键名"""
        return key
    
    MODULES_AVAILABLE = True
    
    # 打印路径信息（调试用）
    # if is_frozen():
    #     print("\n" + "="*60)
    #     print("检测到打包环境，打印路径信息...")
    #     print_path_info()
    #     print("="*60 + "\n")
        
except ImportError as e:
    print(f"模块导入失败 / Module import failed: {str(e)}")
    MODULES_AVAILABLE = False
    # 使用备用翻译函数
    t_gui = t_gui_fallback
    t_common = t_common_fallback
    # 如果导入失败，提供备用路径函数
    def get_reports_dir():
        return Path("analysis_reports")
    def get_cache_dir():
        return Path("cache")
    def is_frozen():
        return getattr(sys, 'frozen', False)
    # 提供备用的语言检测函数
    def get_system_language():
        """备用语言检测函数"""
        import locale
        try:
            lang = locale.getdefaultlocale()[0]
            if lang and lang.startswith('zh'):
                return 'zh'
            return 'en'
        except:
            return 'zh'  # 默认中文


class AnalysisWorker(QThread):
    """分析工作线程"""
    progress_updated = pyqtSignal(int, str)  # 进度，状态文本
    analysis_completed = pyqtSignal(dict)    # 分析完成，结果数据
    analysis_failed = pyqtSignal(str)        # 分析失败，错误信息
    
    # 类级别的配置缓存，所有实例共享
    _ai_config_cache = None
    _ai_config_cache_time = 0
    _ai_config_cache_ttl = 300  # 缓存5分钟
    _is_trial_mode = False  # 试用模式标记
    
    def __init__(self, data_file_path: str, enable_ai_analysis: bool = True):
        super().__init__()
        self.data_file_path = data_file_path
        self.enable_ai_analysis = enable_ai_analysis
        self.is_cancelled = False
        
    def run(self):
        """执行分析 - 复用原界面的实现"""
        try:
            if not MODULES_AVAILABLE:
                self.analysis_failed.emit(t_gui('module_unavailable'))
                return
                
            # 第1阶段：加载数据 - 10%
            self.progress_updated.emit(10, t_gui('loading_data'))
            
            # 优先使用新的压缩JSON加载器 - 与原界面完全一致
            try:
                from data.compressed_json_loader import CompressedJSONLoader
                loader = CompressedJSONLoader(self.data_file_path)
                data, load_result = loader.load_and_validate()
                
                if load_result['is_valid']:
                    current_dataset = StockDataSet(data, self.data_file_path)
                    format_type = load_result['file_info'].get('format_type', 'unknown')
                    load_time = load_result.get('load_time', 'N/A')
                    print(t_gui('format_loading_data', format_type=format_type, load_time=load_time))
                else:
                    raise Exception(load_result.get('error', t_gui('data_load_failed')))
                    
            except ImportError:
                # 回退到原有的加载方式
                current_dataset = StockDataSet(self.data_file_path)
                    
            # 第2阶段：数据加载完成 - 25%
            self.progress_updated.emit(25, t_gui('data_loading_complete'))
            
            # 第3阶段：创建分析引擎 - 35%
            self.progress_updated.emit(35, t_gui('创建分析引擎...'))
            # 使用单线程模式以启用批量增强RTSI计算
            analysis_engine = RealtimeAnalysisEngine(current_dataset, enable_multithreading=False)
            
            # 第4阶段：执行股票分析 - 40%
            self.progress_updated.emit(40, t_gui('executing_stock_analysis'))
            
            # 平滑的进度更新
            import time
            time.sleep(0.1)  # 短暂暂停让用户看到进度
            self.progress_updated.emit(45, t_gui('计算技术指标...'))
            
            analysis_results = analysis_engine.calculate_all_metrics()
            
            # 【关键调试】检查分析结果
            print(f"🚨 [分析引擎调试] analysis_results 类型: {type(analysis_results)}")
            print(f"🚨 [分析引擎调试] analysis_results 是否为None: {analysis_results is None}")
            if analysis_results is not None:
                print(f"🚨 [分析引擎调试] 是否有market属性: {hasattr(analysis_results, 'market')}")
                print(f"🚨 [分析引擎调试] 是否有industries属性: {hasattr(analysis_results, 'industries')}")
                print(f"🚨 [分析引擎调试] 是否有stocks属性: {hasattr(analysis_results, 'stocks')}")
                
                if hasattr(analysis_results, 'market'):
                    print(f"🚨 [分析引擎调试] market数据内容: {analysis_results.market}")
                if hasattr(analysis_results, 'industries'):
                    print(f"🚨 [分析引擎调试] industries数据长度: {len(analysis_results.industries) if analysis_results.industries else 0}")
                if hasattr(analysis_results, 'stocks'):
                    print(f"🚨 [分析引擎调试] stocks数据长度: {len(analysis_results.stocks) if analysis_results.stocks else 0}")
            
            # 第5阶段：分析完成 - 55%
            self.progress_updated.emit(55, t_gui('generating_basic_report'))
            time.sleep(0.05)
            
            # 第6阶段：准备报告 - 60%
            self.progress_updated.emit(60, t_gui('生成报告数据...'))
            time.sleep(0.05)
            
            # 第7阶段：准备AI分析 - 65%
            self.progress_updated.emit(65, t_gui('preparing_ai_analysis'))
            
            # 第4阶段：生成HTML报告
            try:
                report_generator = ReportGenerator()
                # 将AnalysisResults对象转换为字典
                analysis_dict = analysis_results.to_dict()
                report_files = report_generator.generate_complete_report(
                    analysis_dict, formats=['html']
                )
                
                # 将报告路径和原始分析结果都保存，包括数据源引用
                final_results = {
                    'analysis_results': analysis_results,  # 原始AnalysisResults对象
                    'analysis_dict': analysis_dict,       # 字典格式
                    'html_report_path': report_files.get('html', ''),
                    'data_source': current_dataset  # 添加数据源引用，用于获取日期范围
                }
            except Exception as e:
                print(t_gui('report_generation_failed', error=str(e)))
                # 即使报告生成失败，也返回分析结果
                final_results = {
                    'analysis_results': analysis_results,
                    'analysis_dict': analysis_results.to_dict(),
                    'html_report_path': '',
                    'data_source': current_dataset  # 添加数据源引用
                }
            
            # 第8阶段：AI智能分析 - 70% (仅在启用时执行)
            if self.enable_ai_analysis:
                self.progress_updated.emit(70, t_gui('ai_analysis'))
                time.sleep(0.1)
                
                # AI分析进行中 - 75%
                self.progress_updated.emit(75, '正在进行AI分析...')
                
                ai_analysis_result = self.run_ai_analysis(analysis_results)
                if ai_analysis_result:
                    final_results['ai_analysis'] = ai_analysis_result
                    print(t_gui('ai_analysis_complete'))
                else:
                    print(t_gui('ai_analysis_failed'))
                
                # AI分析处理中 - 80%
                self.progress_updated.emit(80, '处理AI分析结果...')
                time.sleep(0.05)
                
                # 第9阶段：AI分析完成 - 85%
                self.progress_updated.emit(85, t_gui('ai_analysis_complete_status'))
            else:
                # 跳过AI分析，直接进入下一阶段
                self.progress_updated.emit(75, '跳过AI分析...')
                time.sleep(0.05)
                self.progress_updated.emit(80, '准备完成...')
                time.sleep(0.05)
                self.progress_updated.emit(85, t_gui("skip_ai_analysis"))
                print(t_gui("user_disabled_ai_analysis"))
            
            # 第10阶段：生成HTML报告 - 90%
            self.progress_updated.emit(90, '生成HTML报告...')
            html_report_path = self.generate_html_report(final_results)
            if html_report_path:
                final_results['html_report_path'] = html_report_path
                print(t_gui('html_report_generated', path=html_report_path))
            
            # 第11阶段：完成准备 - 95%
            self.progress_updated.emit(95, '完成最后处理...')
            time.sleep(0.1)
            
            # 第12阶段：分析完成 - 100%
            self.progress_updated.emit(100, t_gui('analysis_complete'))
            time.sleep(0.2)  # 让用户看到100%完成状态
            
            self.analysis_completed.emit(final_results)
            
        except Exception as e:
            error_msg = t_gui('analysis_process_error', error=str(e))
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.analysis_failed.emit(error_msg)
    
    def _ai_analysis_before(self, analysis_type="AI分析"):
        """AI分析执行前的统一处理
        
        Args:
            analysis_type: 分析类型名称（用于日志）
            
        Returns:
            bool: True表示可以继续执行，False表示应该终止
        """
        try:
            print(f"[{analysis_type}] 执行前检查...")
            
            # 1. 检查LLM配置文件是否存在
            if not self._check_llm_config():
                print(f"[{analysis_type}] LLM配置文件不存在")
                return False
            
            # 2. 重新加载AI配置（确保使用最新配置）
            try:
                import json
                import time
                from pathlib import Path
                from utils.path_helper import get_base_path
                
                base_path = get_base_path()
                config_path = base_path / "llm-api" / "config" / "user_settings.json"
                
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        # 更新缓存
                        AnalysisWorker._ai_config_cache = config
                        AnalysisWorker._ai_config_cache_time = time.time()
                        print(f"[{analysis_type}] 已重新加载AI配置")
                else:
                    print(f"[{analysis_type}] 配置文件不存在")
                    return False
            except Exception as e:
                print(f"[{analysis_type}] 加载配置失败: {e}")
                return False
            
            # 3. 试用功能检查（必须在API Key检查之前）
            try:
                from utils.ai_usage_counter import get_ai_usage_count
                
                provider = config.get('default_provider', '').lower()
                api_key = config.get('SILICONFLOW_API_KEY', '').strip()
                current_count = get_ai_usage_count()
                
                # 检查是否符合试用条件：SiliconFlow + 无API Key + 计数<20
                if provider == 'siliconflow' and not api_key and current_count < 20:
                    print(f"[试用模式] 符合试用条件（{current_count}/20次）")
                    print(f"[试用模式] 使用预设试用配置")
                    
                    # 使用硬编码的试用配置
                    trial_config = {
                        "default_provider": "SiliconFlow",
                        "default_chat_model": "Qwen/Qwen3-8B",
                        "default_structured_model": "Qwen/Qwen3-8B",
                        "request_timeout": 600,
                        "agent_role": "不使用",
                        "SILICONFLOW_API_KEY": "",
                        "SILICONFLOW_BASE_URL": "https://api.siliconflow.cn/v1",
                        "dont_show_api_dialog": True
                    }
                    
                    # 更新缓存为试用配置
                    AnalysisWorker._ai_config_cache = trial_config
                    AnalysisWorker._ai_config_cache_time = time.time()
                    
                    # 标记为试用模式，后续跳过API Key检查
                    AnalysisWorker._is_trial_mode = True
                    
                    print(f"[试用模式] 配置已切换为试用模式，剩余 {20 - current_count} 次试用机会")
                else:
                    # 不符合试用条件，清除试用标记
                    AnalysisWorker._is_trial_mode = False
                    
                    if provider == 'siliconflow' and not api_key and current_count >= 20:
                        print(f"[试用模式] 试用次数已用完（{current_count}/20），请配置API Key")
                        
            except Exception as e:
                print(f"[{analysis_type}] 试用检查出错: {e}")
                AnalysisWorker._is_trial_mode = False
            
            print(f"[{analysis_type}] 执行前检查通过")
            return True
            
        except Exception as e:
            print(f"[{analysis_type}] 执行前检查出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _ai_analysis_after(self, success=True, analysis_type="AI分析"):
        """AI分析执行后的统一处理
        
        Args:
            success: 分析是否成功
            analysis_type: 分析类型名称（用于日志）
        """
        try:
            print(f"[{analysis_type}] 执行后处理...")
            
            if success:
                # 1. 增加AI使用计数
                try:
                    from utils.ai_usage_counter import increment_ai_usage
                    count = increment_ai_usage()
                    print(f"[AI计数] {analysis_type}完成，累计使用: {count} 次")
                except Exception as e:
                    print(f"[AI计数] 计数失败: {e}")
                
                # 2. 可以添加其他成功后的处理
                # 例如：记录分析日志、更新统计信息等
            else:
                print(f"[{analysis_type}] 分析未成功，跳过后续处理")
            
        except Exception as e:
            print(f"[{analysis_type}] 执行后处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    def run_ai_analysis(self, analysis_results):
        """运行AI智能分析 - 移植自旧版main_window.py
        
        注意：这是主AI分析的数据处理和调用逻辑
        与行业分析和个股分析的AI功能分离，提供综合性的投资分析
        """
        analysis_type = "主AI分析"
        
        try:
            # ===== 执行前检查 =====
            if not self._ai_analysis_before(analysis_type):
                return None
            
            # 准备分析数据
            analysis_data = self._prepare_analysis_data(analysis_results)
            
            # 调用LLM API
            ai_response = self._call_llm_api(analysis_data)
            
            # 检查是否是API Key错误信息（用户取消配置或没有输入API Key）
            if ai_response and isinstance(ai_response, str) and ("需要配置API Key" in ai_response or "API Key configuration required" in ai_response):
                print(f"[{analysis_type}] API Key配置取消，终止分析")
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                return None
            
            # ===== 执行后处理 =====
            if ai_response:
                self._ai_analysis_after(success=True, analysis_type=analysis_type)
            else:
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
            
            return ai_response
            
        except Exception as e:
            print(f"{t_gui('ai_analysis_execution_failed')}: {str(e)}")
            self._ai_analysis_after(success=False, analysis_type=analysis_type)
            return None
    
    def _is_large_cap_stock(self, stock_code: str) -> bool:
        """判断是否为大盘股（与algorithms模块中的逻辑保持一致）"""
        code = str(stock_code).strip()
        
        # A股大盘股判断
        if len(code) == 6 and code.isdigit():
            # 主板大盘股
            if code.startswith(('000', '001', '002', '003')):  # 深交所主板
                return True
            elif code.startswith(('600', '601', '603', '605')):  # 上交所主板
                return True
            # 科创板和创业板一般不算大盘股
            elif code.startswith('688'):  # 科创板
                return False
            elif code.startswith('300'):  # 创业板
                return False
        
        # 港股大盘股判断（恒生指数成分股）
        elif len(code) == 5 and code.isdigit():
            large_cap_hk = [
                '00700', '00939', '00941', '01299', '02318', '00388', '01398', '03988',
                '00883', '02628', '01109', '00005', '01177', '00011', '00016', '00017',
                '00066', '00083', '00101', '00151', '00175', '00267', '00288', '00386',
                '00669', '00688', '00762', '00823', '00857', '00868', '00914', '00968',
                '01038', '01044', '01066', '01093', '01113', '01171', '01199', '01211',
                '01339', '01359', '01378', '01988', '01997', '02007', '02018', '02020',
                '02313', '02319', '02382', '02388', '02688', '03328', '03968', '06098'
            ]
            return code in large_cap_hk
        
        # 美股大盘股判断（简化版，基于常见大盘股）
        elif isinstance(code, str) and not code.isdigit():
            large_cap_us = [
                'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'BRK.A', 'BRK.B',
                'UNH', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'PFE', 'BAC', 'ABBV', 'KO', 'AVGO',
                'PEP', 'TMO', 'COST', 'MRK', 'WMT', 'ACN', 'DHR', 'VZ', 'ABT', 'ADBE', 'LIN',
                'NKE', 'TXN', 'PM', 'NEE', 'RTX', 'CRM', 'WFC', 'DIS', 'BMY', 'ORCL', 'MDT',
                'SCHW', 'QCOM', 'UPS', 'T', 'AMGN', 'LOW', 'HON', 'ELV', 'IBM', 'CVS', 'SPGI',
                'GS', 'CAT', 'AXP', 'DE', 'GILD', 'BKNG', 'AMD', 'SYK', 'MU', 'TJX', 'BLK',
                'BA', 'MDLZ', 'CI', 'C', 'ISRG', 'VRTX', 'SO', 'MMM', 'PLD', 'ADI', 'REGN',
                'ZTS', 'MO', 'CVX', 'DUK', 'TGT', 'AON', 'PYPL', 'INTC', 'EQIX', 'KLAC'
            ]
            return code.upper() in large_cap_us
        
        return False
    
    def _check_llm_config(self) -> bool:
        """检查LLM配置文件是否存在"""
        try:
            import os
            import json
            from utils.path_helper import get_base_path
            base_path = get_base_path()  # 打包环境下返回EXE所在目录
            config_path = base_path / "llm-api" / "config" / "user_settings.json"
            
            if not config_path.exists():
                return False
            
            # 读取配置文件验证格式
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if not config.get('default_provider') or not config.get('default_chat_model'):
                return False
                
            return True
            
        except Exception as e:
            print(f"{t_gui('ai_config_check_failed')}: {str(e)}")
            return False
    
    def _prepare_analysis_data(self, analysis_results):
        """准备发送给AI的分析数据 - 移植自旧版"""
        try:
            from datetime import datetime
            import numpy as np
            
            data = {
                "analysis_type": t_gui('stock_market_analysis'),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_data": {},
                "industry_data": {},
                "stock_data": {},
                "summary": {}
            }
            
            # 【关键调试】分析输入参数
            print(f"🚨 [数据传递调试] analysis_results 参数: {analysis_results}")
            print(f"🚨 [数据传递调试] analysis_results 类型: {type(analysis_results)}")
            print(f"🚨 [数据传递调试] analysis_results 是否为None: {analysis_results is None}")
            
            if analysis_results is None:
                print(f"[ERROR] [严重错误] analysis_results 为 None，无法继续数据准备")
                return data
            
            # 【调试日志】分析数据结构
            print(f" [数据传递调试] 分析结果对象类型: {type(analysis_results)}")
            print(f" [数据传递调试] 是否有market属性: {hasattr(analysis_results, 'market')}")
            if hasattr(analysis_results, 'market'):
                print(f" [数据传递调试] market数据: {analysis_results.market}")
            else:
                print(f" [数据传递调试] analysis_results属性列表: {dir(analysis_results) if hasattr(analysis_results, '__dict__') else '无法获取属性'}")
            
            # 提取市场数据
            if hasattr(analysis_results, 'market') and analysis_results.market:
                market = analysis_results.market
                msci_value = market.get('current_msci', 0)
                volatility = market.get('volatility', 0)
                volume_ratio = market.get('volume_ratio', 0)
                
                print(f" [MSCI调试] 原始MSCI值: {msci_value}, 类型: {type(msci_value)}")
                print(f" [MSCI调试] 波动率: {volatility}, 成交量比率: {volume_ratio}")
                
                # 计算市场情绪状态
                if msci_value >= 70:
                    market_sentiment = t_gui('extremely_optimistic')
                elif msci_value >= 60:
                    market_sentiment = t_gui('optimistic')
                elif msci_value >= 40:
                    market_sentiment = t_gui('neutral')
                elif msci_value >= 30:
                    market_sentiment = t_gui('pessimistic')
                else:
                    market_sentiment = t_gui('extremely_pessimistic')
                
                data["market_data"] = {
                    "msci_value": msci_value,
                    "trend_5d": market.get('trend_5d', 0),
                    "volatility": volatility,
                    "volume_ratio": volume_ratio,
                    "market_sentiment": market_sentiment,
                    "risk_level": market.get('risk_level', t_gui('moderate_risk'))
                }
                
                print(f" [MSCI调试] 市场数据已准备: MSCI={msci_value}, 情绪={market_sentiment}")
            else:
                print(f" [MSCI调试] 未找到市场数据，将使用默认值0")
            
            # 提取行业数据
            print(f" [行业调试] 是否有industries属性: {hasattr(analysis_results, 'industries')}")
            if hasattr(analysis_results, 'industries'):
                print(f" [行业调试] industries数据: {analysis_results.industries}")
                print(f" [行业调试] industries长度: {len(analysis_results.industries) if analysis_results.industries else 0}")
            
            if hasattr(analysis_results, 'industries') and analysis_results.industries:
                industries_summary = {}
                sorted_industries = []
                
                for industry_name, industry_info in analysis_results.industries.items():
                    tma_value = industry_info.get('irsi', 0)
                    if isinstance(tma_value, dict):
                        tma_value = tma_value.get('irsi', 0)
                    sorted_industries.append((industry_name, float(tma_value)))
                    print(f" [行业调试] 行业: {industry_name}, TMA: {tma_value}")
                
                sorted_industries.sort(key=lambda x: x[1], reverse=True)
                
                # 取前10个行业
                top_industries = sorted_industries[:10]
                industries_summary["top_performers"] = top_industries
                industries_summary["sector_count"] = len(analysis_results.industries)
                
                data["industry_data"] = industries_summary
                
                print(f" [行业调试] 行业数据已准备: 共{len(analysis_results.industries)}个行业")
                print(f" [行业调试] 前5个强势行业: {top_industries[:5]}")
            else:
                print(f" [行业调试] 未找到行业数据，sector_count将为0")
            
            # 提取股票数据 - 按RTSI最高的20个股票，且所属行业TMA排名前20
            if hasattr(analysis_results, 'stocks') and analysis_results.stocks:
                stocks_summary = {}
                
                # 第一步：获取行业TMA值，并排序得到前20个行业
                print(f"[AI分析数据准备-行业筛选] 开始按TMA排序行业...")
                industry_tma = {}  # {行业名: TMA值}
                industry_stocks_map = {}  # {行业名: [(股票代码, 股票名, RTSI), ...]}
                
                # 遍历所有行业
                if hasattr(analysis_results, 'industries') and analysis_results.industries:
                    for industry_name, industry_info in analysis_results.industries.items():
                        if industry_name == "指数":  # 跳过指数行业
                            continue
                        
                        if isinstance(industry_info, dict):
                            # 获取行业TMA值
                            tma_value = industry_info.get('irsi', 0)
                            if isinstance(tma_value, dict):
                                tma_value = tma_value.get('irsi', 0)
                            if not isinstance(tma_value, (int, float)):
                                tma_value = 0
                            industry_tma[industry_name] = float(tma_value)
                            
                        # 收集该行业所有股票
                        stocks = industry_info.get('stocks', [])
                        stock_details = []
                        
                        # 【修复】正确处理stocks为列表的情况
                        # stocks格式: [{'code': '000001', 'name': '平安银行', 'rtsi': 95.5}, ...]
                        if isinstance(stocks, list):
                            print(f"[股票收集] 行业={industry_name}, stocks类型=list, stocks数量={len(stocks)}")
                            
                            # 【调试】打印该行业前3个股票的详细信息
                            debug_count = 0
                            for stock_item in stocks:
                                if isinstance(stock_item, dict):
                                    stock_code = stock_item.get('code', '')
                                    stock_name = stock_item.get('name', stock_code)
                                    rtsi = stock_item.get('rtsi', 0)
                                    
                                    # 【调试】打印前3个股票的详细RTSI信息
                                    if debug_count < 3:
                                        print(f"[股票筛选-调试] 行业={industry_name}, 股票={stock_code} {stock_name}: RTSI={rtsi} (类型={type(rtsi)})")
                                        debug_count += 1
                                    
                                    # 筛选RTSI > 0的股票
                                    if isinstance(rtsi, (int, float, np.number)) and rtsi > 0:
                                        stock_details.append((stock_code, stock_name, float(rtsi)))
                        
                        elif isinstance(stocks, dict):
                            # 兼容旧格式：stocks是字典 {股票代码: {name: xxx, rtsi: xxx}}
                            print(f"[股票收集] 行业={industry_name}, stocks类型=dict, stocks数量={len(stocks)}")
                            
                            debug_count = 0
                            for stock_code, stock_info in stocks.items():
                                if isinstance(stock_info, dict):
                                    rtsi = stock_info.get('rtsi', 0)
                                    
                                    # 处理RTSI可能是字典的情况
                                    if isinstance(rtsi, dict):
                                        rtsi = rtsi.get('rtsi', 0)
                                    
                                    # 【调试】打印前3个股票的详细RTSI信息
                                    if debug_count < 3:
                                        stock_name = stock_info.get('name', stock_code)
                                        print(f"[股票筛选-调试] 行业={industry_name}, 股票={stock_code} {stock_name}: RTSI={rtsi} (类型={type(rtsi)})")
                                        debug_count += 1
                                    
                                    if isinstance(rtsi, (int, float, np.number)) and rtsi > 0:
                                        stock_name = stock_info.get('name', stock_code)
                                        stock_details.append((stock_code, stock_name, float(rtsi)))
                        
                        # 按RTSI排序该行业的股票
                        if stock_details:
                            stock_details.sort(key=lambda x: x[2], reverse=True)
                            industry_stocks_map[industry_name] = stock_details
                            print(f"[行业筛选] {industry_name}: TMA={tma_value:.2f}, 股票数={len(stock_details)}, 前3股={[f'{s[0]}({s[2]:.1f})' for s in stock_details[:3]]}")
                        else:
                            print(f"[行业筛选-警告] {industry_name}: TMA={tma_value:.2f}, 股票数=0 (原始stocks={len(stocks)})")
                
                # 按TMA排序行业，取前20个
                top20_industries = sorted(industry_tma.items(), key=lambda x: x[1], reverse=True)[:20]
                top20_industry_names = [name for name, _ in top20_industries]
                
                print(f"[AI分析数据准备-行业筛选] TMA排名前20的行业:")
                for i, (name, tma) in enumerate(top20_industries):
                    print(f"  {i+1}. {name}: TMA={tma:.2f}")
                
                # 第二步：从前20个行业中筛选RTSI最高的20个股票
                print(f"[AI分析数据准备-股票筛选] 从TMA前20行业中筛选RTSI最高的20个股票...")
                candidate_stocks = []
                
                for industry_name in top20_industry_names:
                    if industry_name in industry_stocks_map:
                        for stock_code, stock_name, rtsi in industry_stocks_map[industry_name]:
                            candidate_stocks.append((stock_code, stock_name, rtsi, industry_name))
                
                # 按RTSI排序，取前20个
                candidate_stocks.sort(key=lambda x: x[2], reverse=True)
                top20_stocks = candidate_stocks[:20]
                
                # 转换为输出格式
                top_stocks = [(code, name, rtsi) for code, name, rtsi, _ in top20_stocks]
                stocks_summary["top_performers"] = top_stocks
                stocks_summary["total_count"] = len(analysis_results.stocks)
                
                # 添加调试日志
                print(f"[AI分析数据准备-股票筛选] 筛选完成:")
                print(f"  原始股票总数: {len(analysis_results.stocks)}")
                print(f"  候选股票数（来自TMA前20行业）: {len(candidate_stocks)}")
                print(f"  最终推荐股票数: {len(top20_stocks)}")
                print(f"  传递给AI的推荐股票:")
                for i, (code, name, rtsi, industry) in enumerate(top20_stocks):
                    print(f"    {i+1}. {code} {name} [{industry}]: RTSI={rtsi:.2f}")
                
                # 数据质量验证
                if len(top_stocks) == 0:
                    print(f" [AI分析警告] 没有股票数据传递给LLM，可能导致AI编造股票")
                elif len(top_stocks) < 10:
                    print(f" [AI分析警告] 传递给LLM的股票数量较少({len(top_stocks)}只)，可能影响分析质量")
                
                # 计算分布统计（使用所有股票的RTSI）
                all_stocks_rtsi = []
                for stock_code, stock_info in analysis_results.stocks.items():
                    rtsi_value = stock_info.get('rtsi', 0)
                    if isinstance(rtsi_value, dict):
                        rtsi_value = rtsi_value.get('rtsi', 0)
                    if isinstance(rtsi_value, (int, float)):
                        all_stocks_rtsi.append(float(rtsi_value))
                rtsi_values = all_stocks_rtsi
                # 基于优化增强RTSI 0-100分制的分类（方案C v2.3）
                stocks_summary["statistics"] = {
                    "average_rtsi": np.mean(rtsi_values) if rtsi_values else 0,
                    "strong_count": len([x for x in rtsi_values if x >= 50]),  # 强势股：50+ (中强势+强势)
                    "neutral_count": len([x for x in rtsi_values if 40 <= x < 50]),  # 中性股：40-49
                    "weak_count": len([x for x in rtsi_values if x < 40])  # 弱势股：<40
                }
                
                data["stock_data"] = stocks_summary
            
            # ===== 新增：获取指数量价数据 =====
            # 仅对中国市场获取指数数据
            current_market = self._get_reliable_market_info()
            if current_market == 'cn':
                try:
                    from utils.index_data_fetcher import IndexDataFetcher
                    fetcher = IndexDataFetcher(verbose=False)
                    indices_data = fetcher.fetch_cn_indices_data(days=20)
                    data["indices_data"] = indices_data
                    print(f"[指数数据] 已获取 {len(indices_data)} 个指数的量价数据")
                except Exception as e:
                    print(f"[指数数据] 获取失败: {e}")
                    data["indices_data"] = {}
            else:
                data["indices_data"] = {}
            
            return data
            
        except Exception as e:
            print(t_gui('prepare_ai_data_failed', error=str(e)))
            return {}
    
    def _check_api_key_before_llm(self, config, provider, use_english, base_path):
        """
        在执行AI前检查API Key
        
        Args:
            config: 配置字典
            provider: 供应商名称
            use_english: 是否使用英文
            base_path: 基础路径
            
        Returns:
            None: 检查通过，继续执行
            str: 错误信息，终止执行
        """
        try:
            # 如果是Ollama或LMStudio，跳过API Key检查
            if provider.lower() in ['ollama', 'lmstudio']:
                print(f"[API Key检查] {provider} 不需要API Key，跳过检查")
                return None
            
            # 检查是否有API Key配置
            has_api_key = False
            
            # 检查各个供应商的API Key
            provider_keys = {
                'openai': 'OPENAI_API_KEY',
                'deepseek': 'DEEPSEEK_API_KEY',
                'siliconflow': 'SILICONFLOW_API_KEY',
                'anthropic': 'ANTHROPIC_API_KEY',
                'google': 'GOOGLE_API_KEY',
                'zhipu': 'ZHIPU_API_KEY',
                'moonshot': 'MOONSHOT_API_KEY',
            }
            
            # 获取当前供应商对应的API Key字段名
            key_field = provider_keys.get(provider.lower())
            if key_field:
                api_key = config.get(key_field, '').strip()
                if api_key and api_key != '':
                    has_api_key = True
                    print(f"[API Key检查] 检测到 {provider} 的 API Key")
            
            # 如果没有API Key，弹出设置窗口
            if not has_api_key:
                print(f"[API Key检查] 未检测到 {provider} 的 API Key，需要配置")
                
                # 根据系统语言决定弹出哪个窗口
                from config.gui_i18n import get_system_language
                system_language = get_system_language()
                
                if system_language == 'zh':
                    # 中文系统：弹出新的API配置对话框
                    print("[API Key检查] 中文系统，弹出API配置对话框")
                    try:
                        from api_key_dialog import APIKeyDialog
                        from PyQt5.QtWidgets import QApplication
                        
                        # 在主线程中显示对话框
                        dialog = APIKeyDialog()
                        dialog.exec_()
                        
                        # 对话框关闭后，返回提示信息
                        if use_english:
                            return "API Key configuration required. Please configure your API Key and try again."
                        else:
                            return "需要配置API Key。请配置您的API Key后重试。"
                    except Exception as e:
                        print(f"[API Key检查] 显示API配置对话框失败: {e}")
                        if use_english:
                            return f"Failed to show API configuration dialog: {str(e)}"
                        else:
                            return f"显示API配置对话框失败：{str(e)}"
                else:
                    # 非中文系统：运行 setting.exe
                    print("[API Key检查] 非中文系统，运行 setting.exe")
                    try:
                        import subprocess
                        import os
                        
                        setting_exe = base_path / "llm-api" / "setting.exe"
                        if setting_exe.exists():
                            subprocess.Popen([str(setting_exe)], cwd=str(setting_exe.parent))
                            if use_english:
                                return "API Key configuration required. Please configure your API Key in the settings window and try again."
                            else:
                                return "需要配置API Key。请在设置窗口中配置您的API Key后重试。"
                        else:
                            if use_english:
                                return f"Settings program not found: {setting_exe}"
                            else:
                                return f"设置程序未找到：{setting_exe}"
                    except Exception as e:
                        print(f"[API Key检查] 运行 setting.exe 失败: {e}")
                        if use_english:
                            return f"Failed to run settings program: {str(e)}"
                        else:
                            return f"运行设置程序失败：{str(e)}"
            
            # 检查通过
            return None
            
        except Exception as e:
            print(f"[API Key检查] 检查过程出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错时不阻止执行，让后续的API调用自己处理错误
            return None
    
    def _call_llm_api(self, analysis_data):
        """调用LLM API进行分析 - 移植自旧版main_window.py，完全一致"""
        try:
            import sys
            import time
            
            # 检测当前系统语言
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            
            # 添加llm-api到路径（使用path_helper确保打包环境正确）
            from utils.path_helper import get_base_path
            base_path = get_base_path()  # 打包环境下返回EXE所在目录
            llm_api_path = base_path / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # ===== 使用缓存的配置（可能是试用配置） =====
            config = AnalysisWorker._ai_config_cache
            
            if config is None:
                # 如果缓存为空，从文件加载
                import json
                config_path = llm_api_path / "config" / "user_settings.json"
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        AnalysisWorker._ai_config_cache = config
                        AnalysisWorker._ai_config_cache_time = time.time()
                        print(f"[LLM Debug] 缓存为空，从文件加载AI配置")
                else:
                    config = {}
                    print("[LLM Debug] 未找到配置文件，使用默认设置")
            else:
                # 使用缓存的配置（可能是试用配置）
                if AnalysisWorker._is_trial_mode:
                    print(f"[LLM Debug] 使用试用模式配置")
                    # 临时设置环境变量，让LLM客户端能够使用试用API Key
                    import os
                    os.environ['SILICONFLOW_API_KEY'] = config.get('SILICONFLOW_API_KEY', '')
                    os.environ['SILICONFLOW_BASE_URL'] = config.get('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
                    print(f"[LLM Debug] 已设置试用模式环境变量")
                else:
                    print(f"[LLM Debug] 使用缓存的AI配置")
            
            default_provider = config.get('default_provider', 'OpenAI')
            print(f"[LLM Debug] {t_gui('current_llm_provider')}: {default_provider}")
            
            # ===== 检查API Key（如果不是试用模式才检查） =====
            if not AnalysisWorker._is_trial_mode:
                api_key_check_result = self._check_api_key_before_llm(config, default_provider, use_english, base_path)
                if api_key_check_result is not None:
                    # 返回错误信息或None，终止AI执行
                    return api_key_check_result
            else:
                print(f"[LLM Debug] 试用模式，跳过API Key检查")
            
            # 继续原有逻辑
            try:
                
                # 如果使用Ollama，先检查并启动服务
                if default_provider.lower() == 'ollama':
                    print(f"[LLM Debug] {t_gui('detected_ollama_provider')}")
                    
                    # 导入Ollama工具
                    try:
                        from ollama_utils import ensure_ollama_and_model
                        model_name = config.get('default_chat_model', 'gemma3:1b')
                        base_url = config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
                        
                        print(f"{t_gui('LLM_Debug前缀')} {t_gui('正在启动Ollama服务并确保模型可用').format(model_name=model_name)}")
                        if not ensure_ollama_and_model(model_name, base_url):
                            return t_gui("无法启动Ollama服务或模型不可用_详细说明")
                        
                        print(f"{t_gui('LLM_Debug前缀')} {t_gui('Ollama服务检查完成，准备进行AI分析')}")
                        
                    except ImportError as e:
                        print(f"{t_gui('LLM_Debug前缀')} {t_gui('无法导入Ollama工具').format(error=str(e))}")
                        return t_gui("Ollama工具模块导入失败").format(error=str(e))
                        
            except Exception as e:
                print(f"[LLM Debug] 读取配置文件时出错: {e}")
                config = {}
            
            # 根据配置的提供商选择合适的LLM客户端
            default_provider = config.get('default_provider', 'OpenAI')
            
            if default_provider.lower() == 'ollama':
                # Ollama使用SimpleLLMClient
                try:
                    from simple_client import SimpleLLMClient as LLMClient
                    print("[LLM Debug] 使用SimpleLLMClient（Ollama专用）")
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                    client_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(client_module)
                    LLMClient = client_module.SimpleLLMClient
                    print("[LLM Debug] 使用绝对路径导入SimpleLLMClient")
            elif default_provider.lower() == 'deepseek':
                # DeepSeek使用简化客户端（避免LangChain依赖）
                try:
                    from simple_deepseek_client import SimpleDeepSeekClient as LLMClient
                    print("[LLM Debug] 使用SimpleDeepSeekClient（DeepSeek专用）")
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("simple_deepseek_client", llm_api_path / "simple_deepseek_client.py")
                    client_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(client_module)
                    LLMClient = client_module.SimpleDeepSeekClient
                    print("[LLM Debug] 使用绝对路径导入SimpleDeepSeekClient")
            else:
                # 其他提供商使用完整的LLMClient
                try:
                    from client import LLMClient
                    print(f"[LLM Debug] 使用LLMClient（支持{default_provider}）")
                except ImportError:
                    # 如果无法导入，回退到SimpleLLMClient
                    try:
                        from simple_client import SimpleLLMClient as LLMClient
                        print("[LLM Debug] 回退到SimpleLLMClient")
                    except ImportError:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                        client_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(client_module)
                        LLMClient = client_module.SimpleLLMClient
                        print("[LLM Debug] 使用绝对路径导入SimpleLLMClient作为回退")
            
            # 创建LLM客户端（试用模式下传递临时配置）
            if AnalysisWorker._is_trial_mode:
                print(f"[LLM Debug] 使用试用配置创建客户端")
                client = LLMClient(temp_config=config)
            else:
                client = LLMClient()
            
            # 准备提示词
            prompt = self._create_analysis_prompt(analysis_data)
            
            # 调用LLM - 与旧版本完全一致的方式
            start_time = time.time()
            
            # 根据系统语言选择指令
            if use_english:
                system_msg = "You are a professional financial analyst with expertise in stock analysis, technical analysis, and fundamental analysis. Please respond in English and provide professional investment advice."
                user_msg = "Please analyze the following stock data and provide investment advice:\n\n" + prompt
            else:
                system_msg = t_gui('chinese_financial_analyst')
                user_msg = t_gui('chinese_answer_request') + prompt
            
            # 使用SimpleLLMClient统一调用方式（合并system_message到用户消息）
            combined_message = f"{system_msg}\n\n{user_msg}"
            response = client.chat(message=combined_message)
            print(f"[LLM Debug] LLM调用成功，耗时 {time.time() - start_time:.1f}s")
            
            # 旧版本中client.chat直接返回字符串响应，不是字典
            if isinstance(response, str) and response.strip():
                return response
            elif isinstance(response, dict) and response.get('success'):
                return response.get('content', '')
            else:
                print(f"{t_gui('llm_api_call_failed')}: {response}")
                return None
                
        except ImportError as e:
            print(f"{t_gui('llm_api_module_import_failed')}: {str(e)}")
            return None
        except Exception as e:
            print(f"{t_gui('llm_api_call_exception')}: {str(e)}")
            return None
    
    def _detect_market_from_file_path(self):
        """从文件路径检测市场类型"""
        try:
            import os
            file_name = os.path.basename(self.data_file_path).lower()
            
            # 根据文件名前2个字母识别市场
            if file_name.startswith('cn'):
                return 'cn'
            elif file_name.startswith('hk'):
                return 'hk'  
            elif file_name.startswith('us'):
                return 'us'
            else:
                # 如果没有明确前缀，尝试从文件名中寻找关键字
                if 'china' in file_name or 'cn_' in file_name:
                    return 'cn'
                elif 'hongkong' in file_name or 'hk_' in file_name or 'hong' in file_name:
                    return 'hk'
                elif 'america' in file_name or 'us_' in file_name or 'usa' in file_name:
                    return 'us'
                else:
                    # 默认返回cn市场
                    print(f"无法从文件名识别市场类型: {file_name}，默认使用CN市场")
                    return 'cn'
        except Exception as e:
            print(f"检测市场类型失败: {e}，默认使用CN市场")
            return 'cn'
    
    def _get_reliable_market_info(self) -> str:
        """获取可靠的市场信息 - 优先从主界面检测结果获取"""
        try:
            # 方法1：优先使用主界面检测到的市场类型
            if hasattr(self.parent(), 'detected_market') and self.parent().detected_market:
                detected_market = self.parent().detected_market
                print(f"[市场检测] 使用主界面检测的市场类型: {detected_market.upper()}")
                return detected_market
            
            # 方法2：从全局应用中查找主窗口的检测结果
            try:
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, 'detected_market') and widget.detected_market:
                            print(f"[市场检测] 从主窗口获取市场类型: {widget.detected_market.upper()}")
                            return widget.detected_market
                        if hasattr(widget, 'current_data_file_path') and widget.current_data_file_path:
                            import os
                            file_name = os.path.basename(widget.current_data_file_path).lower()
                            if file_name.startswith('cn') or 'cn_data' in file_name:
                                print(f"[市场检测] 从文件路径推断: CN市场 ({file_name})")
                                return 'cn'
                            elif file_name.startswith('hk') or 'hk_data' in file_name:
                                print(f"[市场检测] 从文件路径推断: HK市场 ({file_name})")
                                return 'hk'
                            elif file_name.startswith('us') or 'us_data' in file_name:
                                print(f"[市场检测] 从文件路径推断: US市场 ({file_name})")
                                return 'us'
            except Exception as e:
                print(f"[市场检测] 从全局应用获取市场信息失败: {e}")
            
            # 方法3：从数据文件路径检测
            try:
                detected_market = self._detect_market_from_file_path()
                if detected_market:
                    return detected_market
            except Exception as e:
                print(f"[市场检测] 从文件路径检测失败: {e}")
            
            # 默认使用CN市场
            print("[市场检测] 所有检测方法失败，使用默认CN市场")
            return 'cn'
            
        except Exception as e:
            print(f"[市场检测] 获取可靠市场信息失败: {e}，使用默认CN市场")
            return 'cn'
    
    def _create_analysis_prompt(self, analysis_data):
        """创建分析提示词 - 移植自旧版
        
        注意：这是主AI分析的提示词，与行业分析和个股分析的AI功能不同
        主分析需要综合讨论大盘、行业、个股三个层面的投资分析
        """
        # 检测当前界面语言
        from config.i18n import is_english
        use_english = is_english()
        
        market_data = analysis_data.get('market_data', {})
        industry_data = analysis_data.get('industry_data', {})
        stock_data = analysis_data.get('stock_data', {})
        indices_data = analysis_data.get('indices_data', {})
        
        # 获取当前市场类型 - 优先从主界面检测结果获取
        current_market = self._get_reliable_market_info()
        
        # 根据语言设置市场名称
        if use_english:
            market_names = {'cn': 'China A-Share Market', 'hk': 'Hong Kong Stock Market', 'us': 'US Stock Market'}
            market_name = market_names.get(current_market, 'Stock Market')
        else:
            market_names = {'cn': '中国A股市场', 'hk': '香港股票市场', 'us': '美国股票市场'}
            market_name = market_names.get(current_market, '股票市场')
        
        # 调试信息：确保市场名称正确传递给LLM
        print(f"[市场检测] 主分析AI - 检测到市场: {current_market}, 市场名称: {market_name}")
        
        # 构建市场特色说明
        market_context = ""
        if use_english:
            # 英文版本的市场特色说明
            if current_market == 'cn':
                market_context = """
【Market Context Reminder】
▪ Current Analysis Target: China A-Share Market
▪ Stock Code Format: 6-digit numbers (e.g., 000001 Ping An Bank, 600036 China Merchants Bank)
▪ Stock Recommendation Requirement: Must use real existing A-share stock codes and names
▪ Currency Unit: Chinese Yuan (RMB)
▪ Market Features: T+1 trading, price limit restrictions (Main Board ±10%, ChiNext/STAR ±20%)
"""
            elif current_market == 'hk':
                market_context = """
【Market Context Reminder】
▪ Current Analysis Target: Hong Kong Stock Market (HKEX)
▪ Stock Code Format: 5-digit numbers (e.g., 00700 Tencent Holdings, 00388 HKEX)
▪ Stock Recommendation Requirement: Must use real existing Hong Kong stock codes and names
▪ Currency Unit: Hong Kong Dollar (HKD)
▪ Market Features: T+0 trading, no price limit restrictions
"""
            elif current_market == 'us':
                market_context = """
【Market Context Reminder】
▪ Current Analysis Target: US Stock Market
▪ Stock Code Format: Letter codes (e.g., AAPL Apple Inc., MSFT Microsoft Corp.)
▪ Stock Recommendation Requirement: Must use real existing US stock codes and names
▪ Currency Unit: US Dollar (USD)
▪ Market Features: T+0 trading, no price limit restrictions, pre-market and after-hours trading
"""
        else:
            # 中文版本的市场特色说明
            if current_market == 'cn':
                market_context = """
【市场特色提醒】
▪ 当前分析对象：中国A股市场
▪ 股票代码格式：6位数字（如：000001 平安银行，600036 招商银行）
▪ 推荐股票要求：必须使用真实存在的A股股票代码和名称
▪ 价格单位：人民币元
▪ 市场特点：T+1交易，涨跌停限制（主板±10%，创业板/科创板±20%）
"""
            elif current_market == 'hk':
                market_context = """
【市场特色提醒】
▪ 当前分析对象：香港股票市场（港股）
▪ 股票代码格式：5位数字（如：00700 腾讯控股，00388 香港交易所）
▪ 推荐股票要求：必须使用真实存在的港股股票代码和名称
▪ 价格单位：港币元
▪ 市场特点：T+0交易，无涨跌停限制
"""
            elif current_market == 'us':
                market_context = """
【市场特色提醒】
▪ 当前分析对象：美国股票市场（美股）
▪ 股票代码格式：英文字母代码（如：AAPL 苹果公司，MSFT 微软公司）
▪ 推荐股票要求：必须使用真实存在的美股股票代码和名称
▪ 价格单位：美元
▪ 市场特点：T+0交易，无涨跌停限制，盘前盘后交易
"""
        
        if use_english:
            # 英文版本的提示词
            prompt = f"""
===== {market_name} Comprehensive Investment Analysis Report =====
Please provide a professional three-tier investment analysis report (Market-Industry-Stock) based on the following complete market data:
{market_context}
【I. Market Analysis Data】
▪ MSCI Market Sentiment Index: {market_data.get('msci_value', 0):.2f}
▪ Market Sentiment Status: {market_data.get('market_sentiment', 'Unknown Sentiment')}
▪ Market 5-day Trend: {market_data.get('trend_5d', 0):.2f}%
▪ Market Volatility: {market_data.get('volatility', 0):.2f}%
▪ Volume Ratio: {market_data.get('volume_ratio', 1):.2f}

【II. Industry Rotation Analysis Data】
▪ Number of Industries Covered: {industry_data.get('sector_count', 0)}
▪ Strong Industry Rankings (sorted by TMA Index):
"""
            
            # 添加行业信息
            top_industries = industry_data.get('top_performers', [])
            for i, (industry, tma) in enumerate(top_industries[:5]):
                prompt += f"  {i+1}. {industry}: TMA {tma:.2f}\n"
            
            prompt += f"""

【III. Individual Stock Performance Analysis Data】
▪ Total Number of Analyzed Stocks: {stock_data.get('total_count', 0)}
▪ Average RTSI Index: {stock_data.get('statistics', {}).get('average_rtsi', 0):.2f} (Optimized Enhanced RTSI v2.3, Range: 0-90)
▪ Strong Stocks Count: {stock_data.get('statistics', {}).get('strong_count', 0)} (RTSI≥50, Strong Technical Performance)
▪ Neutral Stocks Count: {stock_data.get('statistics', {}).get('neutral_count', 0)} (40≤RTSI<50, Balanced Technical Performance)
▪ Weak Stocks Count: {stock_data.get('statistics', {}).get('weak_count', 0)} (RTSI<40, Weak Technical Performance)

▪ Quality Stock Recommendations (sorted by RTSI Index):
"""
            
            # 添加股票信息
            top_stocks = stock_data.get('top_performers', [])
            for i, (code, name, rtsi) in enumerate(top_stocks[:10]):
                prompt += f"  {i+1}. {code} {name}: RTSI {rtsi:.2f}\n"
            
            # ===== 添加指数量价数据 (仅中国市场) =====
            if indices_data:
                from utils.index_data_fetcher import IndexDataFetcher
                fetcher = IndexDataFetcher(verbose=False)
                prompt += f"\n{fetcher.format_indices_data_for_ai(indices_data)}\n"
        else:
            # 【调试日志】提示词数据确认
            print(f" [提示词调试] 构建提示词时的数据:")
            print(f"   市场数据: {market_data}")
            print(f"   行业数据: {industry_data}") 
            print(f"   股票数据: {stock_data}")
            print(f"   MSCI值: {market_data.get('msci_value', 0)}")
            print(f"   行业数量: {industry_data.get('sector_count', 0)}")
            
            # 中文版本的提示词
            prompt = f"""
===== {market_name}综合投资分析报告 =====
请基于以下完整的市场数据，提供专业的三层级投资分析报告（大盘-行业-个股）：
{market_context}
【一、大盘市场分析数据】
▪ MSCI市场情绪指数: {market_data.get('msci_value', 0):.2f}
▪ 市场情绪状态: {market_data.get('market_sentiment', t_gui('unknown_sentiment'))}
▪ 市场5日趋势: {market_data.get('trend_5d', 0):.2f}%
▪ 市场波动率: {market_data.get('volatility', 0):.2f}%
▪ 成交量比率: {market_data.get('volume_ratio', 1):.2f}

【二、行业轮动分析数据】
▪ 覆盖行业数量: {industry_data.get('sector_count', 0)}个
▪ 强势行业排行（按TMA指数排序）:
"""
            
            # 添加行业信息
            top_industries = industry_data.get('top_performers', [])
            for i, (industry, tma) in enumerate(top_industries[:5]):
                prompt += f"  {i+1}. {industry}: TMA {tma:.2f}\n"
            
            prompt += f"""

【三、个股表现分析数据】
▪ 分析股票总数: {stock_data.get('total_count', 0)}只
▪ 平均RTSI指数: {stock_data.get('statistics', {}).get('average_rtsi', 0):.2f} (优化增强RTSI v2.3算法，范围0-90)
▪ 强势股票数量: {stock_data.get('statistics', {}).get('strong_count', 0)}只 (RTSI≥50，技术面较好及以上)
▪ 中性股票数量: {stock_data.get('statistics', {}).get('neutral_count', 0)}只 (40≤RTSI<50，技术面平衡)
▪ 弱势股票数量: {stock_data.get('statistics', {}).get('weak_count', 0)}只 (RTSI<40，技术面较弱)

▪ 优质个股推荐（按RTSI指数排序）:
"""
            
            # 添加股票信息
            top_stocks = stock_data.get('top_performers', [])
            for i, (code, name, rtsi) in enumerate(top_stocks[:10]):
                prompt += f"  {i+1}. {code} {name}: RTSI {rtsi:.2f}\n"
            
            # ===== 添加指数量价数据 (仅中国市场) =====
            if indices_data:
                from utils.index_data_fetcher import IndexDataFetcher
                fetcher = IndexDataFetcher(verbose=False)
                prompt += f"\n{fetcher.format_indices_data_for_ai(indices_data)}\n"
            
            # 添加数据完整性验证信息
            prompt += f"\n【数据完整性确认】\n"
            prompt += f"▪ 实际传递的优质股票数量: {len(top_stocks)}只\n"
            prompt += f"▪ 筛选后可推荐股票总数: {len(top_stocks)}只\n"
            if len(top_stocks) == 0:
                prompt += f"▪  警告：当前没有符合条件的股票数据，请基于此情况给出相应的市场分析\n"
        
        if use_english:
            # 英文版本的分析要求
            prompt += f"""

===== In-depth Analysis Requirements =====
Please conduct comprehensive and in-depth investment analysis from the following three levels:

【Tier 1: Market Analysis】
1. Market Trend Assessment:
   • Based on MSCI index and technical indicators, determine the current bull/bear cycle stage of the market
   • Analyze the sustainability of market sentiment and potential turning points
   • Evaluate systemic risks and market liquidity conditions

2. Macroeconomic Environment Assessment:
   • Analyze the overall impact of current market environment on investments
   • Evaluate the supporting or suppressing effects of policy, economy, and capital on the market
   • Predict the possible trading range of the market in the next 3-6 months

【Tier 2: Industry Rotation Analysis】
3. Industry Allocation Strategy:
   • In-depth analysis of investment value and sustainability of top 3 strong industries
   • Identify potential industries about to rotate and catalysts
   • Evaluate risk-return ratio and optimal allocation timing for each industry

4. Thematic Investment Opportunities:
   • Discover current market hot themes and long-term value themes
   • Analyze policy guidance and industry trends' significance for industry selection
   • Provide specific weight recommendations for industry allocation

【Tier 3: Individual Stock Selection Analysis】
5. Quality Stock Screening:
   • Analyze buying timing and target prices for recommended stocks from technical perspective
   • Combine fundamental analysis to evaluate medium to long-term investment value of individual stocks
   • Analyze industry position and competitive advantages of individual stocks

6. Portfolio Construction Recommendations:
   • Recommend specific investment portfolios based on risk diversification principles
   • Provide allocation strategies for investors with different risk preferences
   • Set profit-taking and stop-loss levels and dynamic adjustment strategies

【Comprehensive Recommendations】
7. Operational Strategy Development:
   • Provide clear buy, hold, sell signals
   • Offer specific plans for gradual position building and position management
   • Develop response strategies for different market conditions

8. Risk Control Measures:
   • Identify the most important risk points to focus on currently
   • Provide specific risk control measures and warning signals
   • Recommend maximum drawdown control targets for investment portfolios

【Analysis Requirements】
• Price Unit: Please use your local currency unit for all price-related data consistently
• Operational Recommendations: Operational recommendation percentages (buy, hold, sell, etc.) do not need to add up to 100%, can be flexibly adjusted based on actual conditions
• Market Benchmark: For China A-share market analysis, use Shanghai Composite Index (上证指数) as the market benchmark
• Response Language: Please respond in English only

【Important: Stock Recommendation Requirements】
• 【Strict Constraint】Only recommend stocks explicitly listed in the "Quality Stock Recommendations" section above, absolutely forbidden to recommend any stocks outside the analysis data
• If more stock recommendations are needed, re-analyze and interpret existing stocks from the above list, do not fabricate new stock codes
• Stock codes and names must be exactly consistent with those in the analysis data, no modifications or variants allowed
• If the number of stocks above is limited, clearly state "Based on current analysis data, qualified quality stocks are as follows"
• Absolutely forbidden to use fictitious stock codes like "BYD", "TTE Company", "XCN Energy", etc.
• When recommending stocks, must use real {current_market.upper()} market code formats as provided in the data

Please use professional and systematic analysis methods, ensuring clear analysis logic, definitive conclusions, and specific actionable recommendations. Analysis should balance risk and return, avoiding extreme viewpoints.
"""
        else:
            # 中文版本的分析要求
            prompt += f"""

===== 深度分析要求 =====
请从以下三个层面进行全面、深入的投资分析：

【第一层：大盘分析】
1. 市场趋势判断：
   • 基于MSCI指数和技术指标，判断当前市场所处的牛熊周期阶段
   • 分析市场情绪的持续性和转折可能性
   • 评估系统性风险和市场流动性状况

2. 宏观环境评估：
   • 分析当前市场环境对投资的整体影响
   • 评估政策、经济、资金面对市场的支撑或压制作用
   • 预测未来3-6个月大盘可能的运行区间

【第二层：行业轮动分析】
3. 行业配置策略：
   • 深度分析排名前3的强势行业投资价值和持续性
   • 识别即将轮动的潜力行业和催化因素
   • 评估各行业的风险收益比和最佳配置时机

4. 主题投资机会：
   • 挖掘当前市场热点主题和长期价值主题
   • 分析政策导向和产业趋势对行业选择的指导意义
   • 提供行业配置的具体权重建议

【第三层：个股精选分析】
5. 优质标的筛选：
   • 从技术面角度分析推荐个股的买入时机和目标价位
   • 结合基本面评估个股的中长期投资价值
   • 分析个股所在行业地位和竞争优势

6. 组合构建建议：
   • 基于风险分散原则，推荐具体的投资组合
   • 提供不同风险偏好投资者的配置方案
   • 设置止盈止损位和动态调整策略

【综合建议】
7. 操作策略制定：
   • 给出明确的买入、持有、卖出信号
   • 提供分批建仓和仓位管理的具体方案
   • 制定不同市场情况下的应对策略

8. 风险控制措施：
   • 识别当前最需要关注的风险点
   • 提供风险控制的具体措施和预警信号
   • 建议投资组合的最大回撤控制目标

【分析要求】
• 价格单位：所有价格相关数据请统一使用"元"作为单位（如：股价12.50元，目标价15.00元）
• 操作建议：各项操作建议（买入、持有、卖出等）比例不需要加起来等于100%，可以根据实际情况灵活调整
• 市场基准：分析A股市场时，请以上证指数为基准
• 回复语言：请用中文回复所有内容

【重要：股票推荐要求】
• 【严格约束】只能推荐上述"个股推荐"部分明确列出的股票，绝对禁止推荐分析数据之外的任何股票
• 【数据验证】在推荐任何股票前，必须先确认该股票在上述列表中存在
• 如果上述列表为空或股票数量为0，必须明确说明"当前分析数据中没有符合推荐标准的股票"
• 不得编造、假设或推测任何股票代码和名称，即使是为了举例说明
• 股票代码和名称必须与分析数据中的完全一致，包括标点符号和空格
• 【逻辑一致性】确保推荐的股票数量与数据确认部分的数量一致
• 绝对禁止使用任何虚构的股票代码，如"000818景德镇卫国"、"000921汇川石化"等
• 如果数据有限，重点分析现有股票的投资价值，而不是寻求推荐更多股票

请用专业、系统的分析方法，确保分析逻辑清晰、结论明确、建议具体可操作。分析应当平衡风险与收益，避免极端观点。

【重要：数据完整性确认】
▪ 当前MSCI指数: {market_data.get('msci_value', 0):.2f}
▪ 当前行业数量: {industry_data.get('sector_count', 0)}个
▪ 当前股票数量: {len(stock_data.get('top_performers', []))}只

{f" 数据缺失警告：MSCI指数为0.00，可能存在市场数据传递问题，请在分析中说明" if market_data.get('msci_value', 0) == 0 else ""}
{f" 数据缺失警告：行业数量为0，无法进行行业轮动分析，请在分析中说明" if industry_data.get('sector_count', 0) == 0 else ""}
{f" 数据缺失警告：股票数量为0，无法进行个股推荐，请在分析中说明" if len(stock_data.get('top_performers', [])) == 0 else ""}

如果出现数据缺失，必须在相应分析部分明确说明数据不足的情况，不得编造或假设数据。
"""
        
        # 添加调试日志：确认提示词中的股票信息和约束条件
        stock_count_in_prompt = len(stock_data.get('top_performers', []))
        msci_value_in_prompt = market_data.get('msci_value', 0)
        industry_count_in_prompt = industry_data.get('sector_count', 0)
        
        print(f"[AI分析提示词] 提示词中包含的股票数量: {stock_count_in_prompt}")
        print(f"[AI分析提示词] 提示词中的MSCI值: {msci_value_in_prompt}")
        print(f"[AI分析提示词] 提示词中的行业数量: {industry_count_in_prompt}")
        print(f"[AI分析提示词] 市场类型: {current_market} ({market_name})")
        print(f"[AI分析提示词] 语言模式: {'英文' if use_english else '中文'}")
        print(f"[AI分析约束] 已启用强制股票验证和逻辑一致性检查")
        print(f"[AI分析约束] 已启用虚构股票禁止约束")
        print(f"[AI分析约束] 已启用数据完整性验证")
        
        if msci_value_in_prompt == 0:
            print(f" [数据问题] MSCI为0，AI将被提醒说明数据不足")
        if industry_count_in_prompt == 0:
            print(f" [数据问题] 行业数量为0，AI将被提醒无法进行行业分析")
        if stock_count_in_prompt > 0:
            print(f"[AI分析期望] AI应推荐 {stock_count_in_prompt} 只真实股票，禁止编造")
        else:
            print(f" [数据问题] 股票数量为0，AI将被提醒无法推荐股票")
        
        return prompt
    
    def generate_html_report(self, results_data):
        """生成HTML报告 - 移植自旧版main_window.py"""
        try:
            from datetime import datetime
            
            # 检测当前界面语言
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            html_lang = "en" if use_english else "zh-CN"
            
            # 提取AnalysisResults对象
            if isinstance(results_data, dict) and 'analysis_results' in results_data:
                analysis_results = results_data['analysis_results']
            else:
                analysis_results = results_data
            
            # 创建报告目录（使用正确的路径）
            reports_dir = get_reports_dir()
            
            html_file = reports_dir / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            # 获取分析数据 - 修复数据传递问题
            if isinstance(analysis_results, dict) and 'analysis_results' in analysis_results:
                # 从字典格式的final_results中获取真正的分析结果对象
                real_analysis_results = analysis_results['analysis_results']
                
                if hasattr(real_analysis_results, 'metadata'):
                    total_stocks = real_analysis_results.metadata.get('total_stocks', 0)
                    total_industries = real_analysis_results.metadata.get('total_industries', 0)
                    
                    # 获取top股票推荐（仅大盘股）
                    top_stocks = real_analysis_results.get_top_stocks('rtsi', 5, large_cap_only=True)
                    
                    # 获取市场情绪数据
                    market_data = real_analysis_results.market
                    
                    # 安全处理数值类型
                    import numpy as np
                    msci_raw = market_data.get('current_msci', 0)
                    msci_value = float(msci_raw) if isinstance(msci_raw, (int, float, np.number)) else 0.0
                    
                    market_state = market_data.get('market_state', t_gui('unknown_state'))
                    risk_level = market_data.get('risk_level', t_gui('moderate_level'))
                    
                    trend_raw = market_data.get('trend_5d', 0)
                    trend_5d = float(trend_raw) if isinstance(trend_raw, (int, float, np.number)) else 0.0
                else:
                    # 从对象属性直接获取
                    total_stocks = len(real_analysis_results.stocks) if hasattr(real_analysis_results, 'stocks') else 0
                    total_industries = len(real_analysis_results.industries) if hasattr(real_analysis_results, 'industries') else 0
                    
                    # 获取top股票（仅大盘股）
                    top_stocks = []
                    if hasattr(real_analysis_results, 'stocks'):
                        stocks_list = []
                        for code, info in real_analysis_results.stocks.items():
                            # 优化筛选逻辑：基于RTSI分数筛选优质股票，避免过度严格的大盘股限制
                            stock_industry = info.get('industry', '')
                            
                            # 指数行业的股票直接通过
                            if stock_industry == "指数":
                                pass  # 指数股票直接通过
                            else:
                                # 对于其他股票，优先基于RTSI分数筛选，辅以大盘股判断
                                rtsi_value = info.get('rtsi', 0)
                                if isinstance(rtsi_value, dict):
                                    rtsi_value = rtsi_value.get('rtsi', 0)
                                
                                # 放宽筛选条件：RTSI >= 45 或者是大盘股
                                if float(rtsi_value) < 45 and not self._is_large_cap_stock(code):
                                    continue
                                
                            rtsi_value = info.get('rtsi', 0)
                            if isinstance(rtsi_value, dict):
                                rtsi_value = rtsi_value.get('rtsi', 0)
                            if isinstance(rtsi_value, (int, float)):
                                stocks_list.append((code, info.get('name', code), float(rtsi_value)))
                        
                        stocks_list.sort(key=lambda x: x[2], reverse=True)
                        top_stocks = stocks_list[:5]
                    
                    # 市场数据
                    if hasattr(real_analysis_results, 'market'):
                        market_data = real_analysis_results.market
                        msci_value = float(market_data.get('current_msci', 42.5))
                        market_state = market_data.get('market_state', t_gui('neutral_bearish'))
                        risk_level = market_data.get('risk_level', t_gui('moderate_level'))
                        trend_5d = float(market_data.get('trend_5d', 0))
                    else:
                        msci_value = 42.5
                        market_state = t_gui('neutral_bearish')
                        risk_level = t_gui('moderate_level')
                        trend_5d = 2.4
            else:
                # 旧版本直接传递对象的情况
                if hasattr(analysis_results, 'metadata'):
                    total_stocks = analysis_results.metadata.get('total_stocks', 0)
                    total_industries = analysis_results.metadata.get('total_industries', 0)
                    top_stocks = analysis_results.get_top_stocks('rtsi', 5, large_cap_only=True)
                    market_data = analysis_results.market
                    
                    import numpy as np
                    msci_raw = market_data.get('current_msci', 0)
                    msci_value = float(msci_raw) if isinstance(msci_raw, (int, float, np.number)) else 0.0
                    market_state = market_data.get('market_state', t_gui('unknown_state'))
                    risk_level = market_data.get('risk_level', t_gui('moderate_level'))
                    trend_raw = market_data.get('trend_5d', 0)
                    trend_5d = float(trend_raw) if isinstance(trend_raw, (int, float, np.number)) else 0.0
                else:
                    # 默认值
                    total_stocks = 0
                    total_industries = 0
                    top_stocks = []
                    msci_value = 42.5
                    market_state = t_gui('neutral_bearish')
                    risk_level = t_gui('moderate_level')
                    trend_5d = 2.4
            
            # 生成个股推荐表格HTML
            stock_recommendations_html = ""
            if top_stocks:
                for i, stock_data in enumerate(top_stocks[:5], 1):
                    if isinstance(stock_data, tuple) and len(stock_data) >= 3:
                        code, name, rtsi = stock_data
                        rtsi_value = float(rtsi) if isinstance(rtsi, (int, float)) else 0.0
                        # 基于优化增强RTSI 0-100分制的推荐级别（方案C v2.3）
                        if rtsi_value >= 70:
                            recommendation = "强烈推荐"
                        elif rtsi_value >= 60:
                            recommendation = "积极关注"
                        elif rtsi_value >= 50:
                            recommendation = "适度关注"
                        elif rtsi_value >= 40:
                            recommendation = "谨慎观望"
                        elif rtsi_value >= 30:
                            recommendation = "规避风险"
                        else:
                            recommendation = "严重警告"
                        stock_recommendations_html += f"""
            <tr>
                <td>{i}</td>
                <td>{code}</td>
                <td>{name}</td>
                <td>{rtsi_value:.1f}</td>
                <td>{recommendation}</td>
            </tr>"""
            else:
                stock_recommendations_html = """
            <tr>
                <td>1</td>
                <td>--</td>
                <td>{t_gui('no_data')}</td>
                <td>--</td>
                <td>{t_gui('please_complete_analysis_first')}</td>
            </tr>"""
            
            # 生成行业分析HTML
            industry_analysis_html = ""
            if hasattr(analysis_results, 'industries') and analysis_results.industries:
                # 使用正确的方法获取top行业数据
                try:
                    top_industries = analysis_results.get_top_industries('irsi', 10)
                except:
                    # 如果方法不存在，使用备用方法
                    industries_list = []
                    for name, info in analysis_results.industries.items():
                        tma_value = info.get('irsi', 0)
                        if isinstance(tma_value, dict):
                            tma_value = tma_value.get('irsi', 0)
                        if isinstance(tma_value, (int, float)):
                            industries_list.append((name, float(tma_value)))
                    
                    industries_list.sort(key=lambda x: x[1], reverse=True)
                    top_industries = industries_list[:5]
                
                if top_industries:
                    industry_analysis_html = f"<p><strong>{t_gui('强势行业排名_按TMA指数排序')}:</strong></p><table>"
                    industry_analysis_html += f"<tr><th>{t_gui('排名')}</th><th>{t_gui('行业名称')}</th><th>{t_gui('TMA指数')}</th><th>{t_gui('强度等级')}</th></tr>"
                    
                    for i, (industry_name, tma_value) in enumerate(top_industries, 1):
                        # 判断强度等级
                        if tma_value > 20:
                            strength = t_gui('strong_trend')
                            color = "red"  # 强势用红色（涨）
                        elif tma_value > 5:
                            strength = t_gui('neutral_strong')
                            color = "#ff6600"  # 中性偏强用橙色
                        elif tma_value > -5:
                            strength = t_gui('neutral')
                            color = "#666666"  # 中性用灰色
                        elif tma_value > -20:
                            strength = t_gui('neutral_weak')
                            color = "#009900"  # 偏弱用深绿色
                        else:
                            strength = t_gui('weak_trend')
                            color = "green"  # 弱势用绿色（跌）
                        
                        industry_analysis_html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{industry_name}</td>
                            <td style="color: {color}; font-weight: bold;">{tma_value:.2f}</td>
                            <td style="color: {color};">{strength}</td>
                        </tr>"""
                    
                    industry_analysis_html += "</table>"
                    
                    # 添加说明
                    strongest_industry = top_industries[0][0]
                    strongest_tma = top_industries[0][1]
                    industry_analysis_html += f"<p><strong>{t_gui('当前最强行业')}:</strong> {strongest_industry} ({t_gui('TMA指数')}: {strongest_tma:.2f})</p>"
                    industry_analysis_html += f"<p><small>{t_gui('TMA指数反映行业相对强度说明')}</small></p>"
                else:
                    industry_analysis_html = f"<p>{t_gui('暂无行业分析数据')}</p>"
            else:
                industry_analysis_html = f"<p>{t_gui('no_industry_analysis_data')}</p>"
            
            # 生成AI分析版块HTML
            ai_analysis_section = ""
            # 正确提取AI分析结果
            if isinstance(results_data, dict) and 'ai_analysis' in results_data:
                ai_analysis = results_data['ai_analysis']
            else:
                ai_analysis = ""
            
            # 根据是否有AI分析结果决定报告标题
            has_ai_analysis = bool(ai_analysis and ai_analysis.strip())
            report_title = t_gui("AI智能趋势分析报告") if has_ai_analysis else t_gui("智能分析报告")
            
            if ai_analysis:
                ai_analysis_section = f"""
    <div class="section">
        <h2> {t_gui('ai_intelligent_analysis')}</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
            <h3>{t_gui('ai_analyst_opinion')}</h3>
            <div style="white-space: pre-wrap; line-height: 1.6; color: #333;">{ai_analysis}</div>
        </div>
        <p><small>{t_gui('ai_analysis_disclaimer')}</small></p>
    </div>"""
            else:
                # 如果没有AI分析，添加提示信息
                ai_analysis_section = f"""
    <div class="section">
        <h2> {t_gui('ai_intelligent_analysis')}</h2>
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; text-align: center;">
            <h3 style="color: #856404;">{t_gui('ai_function_not_executed')}</h3>
            <p style="color: #856404; margin: 10px 0;">{t_gui('please_check_ai_settings')}</p>
            <p style="color: #6c757d; font-size: 12px;">{t_gui('click_ai_settings_button_to_configure')}</p>
        </div>
    </div>"""
            
            # 生成市场情绪分析HTML - 符合红涨绿跌规范
            sentiment_risk_color = "green" if msci_value > 70 else "red" if msci_value < 30 else "orange"  # 高位风险用绿色，低位机会用红色
            trend_color = "red" if trend_5d > 0 else "green"  # 上涨用红色，下跌用绿色（红涨绿跌）
            
            # 生成HTML内容
            html_content = f"""
<!DOCTYPE html>
<html lang="{html_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        body {{ font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 8px; margin-bottom: 20px; position: relative; }}
        .author {{ position: absolute; top: 20px; right: 20px; font-size: 12px; color: #666; }}
        .section {{ margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e8f4fd; border-radius: 5px; }}
        .highlight {{ color: #0078d4; font-weight: bold; }}
        .sentiment-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0; }}
        .sentiment-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #0078d4; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .risk-high {{ color: red; font-weight: bold; }}  /* 高风险用红色（警告信号） */
        .risk-medium {{ color: orange; font-weight: bold; }}
        .risk-low {{ color: green; font-weight: bold; }}  /* 低风险用绿色（安全信号） */
        .trend-up {{ color: red; }}  /* 上涨用红色（红涨绿跌） */
        .trend-down {{ color: green; }}  /* 下跌用绿色（红涨绿跌） */
    </style>
</head>
<body>
    <div class="header">
        <h1>{report_title}</h1>
        <p>{t_gui('generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="author">{t_gui('author')}: 267278466@qq.com</div>
    </div>
    
    <div class="section">
        <h2>{t_gui('analysis_overview')}</h2>
        <div class="metric">{t_gui('analyzed_stocks_count')}: <span class="highlight">{total_stocks:,}</span></div>
        <div class="metric">{t_gui('industry_classification')}: <span class="highlight">{total_industries}</span>{t_gui('industries_unit')}</div>
        <div class="metric">{t_gui('analysis_algorithm')}: <span class="highlight">优化RTSI + TMA + MSCI</span></div>
        <div class="metric">{t_gui('data_quality')}: <span class="highlight">{t_gui('good_quality')}</span></div>
    </div>
    
    <div class="section">
        <h2>{t_gui('market_sentiment_index')}</h2>
        <p>{t_gui('msci_based_market_sentiment_analysis')}</p>
        <div class="sentiment-grid">
            <div class="sentiment-card">
                <h3>{t_gui('core_indicators')}</h3>
                <p><strong>{t_gui('msci_index')}:</strong> <span style="color: {sentiment_risk_color}; font-weight: bold;">{msci_value:.1f}</span></p>
                <p><strong>{t_gui('market_status')}:</strong> {t_gui(market_state) if market_state in ['mild_pessimism', 'significant_pessimism', 'neutral_sentiment', 'healthy_optimism', 'cautious_optimism', 'extreme_euphoria', 'panic_selling'] else market_state}</p>
                <p><strong>{t_gui('risk_level')}:</strong> <span class="risk-{risk_level.lower()}">{t_gui(risk_level) if risk_level in ['medium_high_risk', 'high_risk', 'low_risk', 'medium_risk', 'extremely_high_risk'] else risk_level}</span></p>
                <p><strong>{t_gui('5_day_trend')}:</strong> <span class="trend-{'up' if trend_5d > 0 else 'down'}">{trend_5d:+.1f}</span></p>
            </div>
            <div class="sentiment-card">
                <h3>{t_gui('market_judgment')}</h3>
                <p><strong>{t_gui('overall_sentiment')}:</strong> {t_gui('slightly_optimistic') if msci_value > 60 else t_gui('slightly_pessimistic') if msci_value < 40 else t_gui('neutral')}</p>
                <p><strong>{t_gui('investment_advice')}:</strong> {t_gui('cautious_reduction') if msci_value > 70 else t_gui('moderate_increase') if msci_value < 30 else t_gui('balanced_allocation')}</p>
                <p><strong>{t_gui('focus_points')}:</strong> {t_gui('prevent_bubble_risk') if msci_value > 70 else t_gui('seek_value_opportunities') if msci_value < 30 else t_gui('focus_rotation_opportunities')}</p>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>{t_gui('stock_recommendations')}</h2>
        <p>{t_gui('rtsi_based_quality_stock_analysis')}</p>
        <table>
            <tr><th>{t_gui('rank')}</th><th>{t_gui('stock_code')}</th><th>{t_gui('stock_name')}</th><th>{t_gui('rtsi_index')}</th><th>{t_gui('recommendation_reason')}</th></tr>
            {stock_recommendations_html}
        </table>
    </div>
    
    <div class="section">
        <h2>{t_gui('industry_analysis')}</h2>
        <p>{t_gui('tma_based_industry_strength_analysis')}</p>
        {industry_analysis_html}
    </div>
    
    <div class="section">
                 <h2>{t_gui('investment_advice')}</h2>
        <ul>
            <li>{t_gui('based_on_msci_index')} {msci_value:.1f}，{t_gui('current_market_sentiment')} {market_state}</li>
            <li>{t_gui('suggested_position')}: {"30-40%" if msci_value > 70 else "70-80%" if msci_value < 30 else "50-60%"}</li>
            <li>{t_gui('focus_on_quality_stocks_above_rtsi_60')}</li>
            <li>{t_gui('pay_attention_to_leading_stocks_in_strong_industries')}</li>
            <li>{t_gui('set_stop_loss_control_risk')}</li>
        </ul>
    </div>
    
    {ai_analysis_section}
    
    <div class="section">
        <p><small>{t_gui('disclaimer')}</small></p>
    </div>
</body>
</html>
            """
            
            # 写入HTML文件
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"{t_gui('html_report_generated')}: {html_file}")
            return str(html_file)
            
        except Exception as e:
            print(t_gui('html_report_generation_failed', error=str(e)))
            return None


class FileSelectionPage(QWidget):
    """首页 - 市场分析卡片页面"""
    file_selected = pyqtSignal(str)  # 文件选择信号
    
    def __init__(self):
        super().__init__()
        self.enable_ai_analysis = False  # AI分析标志
        self.loading_progress = None  # 加载进度条
        self.loading_label = None  # 加载状态标签
        self.cards_widget = None  # 卡片容器
        self.setup_ui()
        self.load_data_dates()  # 加载数据日期
        
    def setup_ui(self):
        """设置UI - 商务风格设计"""
        # 设置整体背景
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8f9fa, stop:0.3 #e9ecef, stop:0.7 #dee2e6, stop:1 #ced4da);
                font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(22)
        main_layout.setContentsMargins(40, 32, 40, 28)
        

        
        # 主标题区域
        title_container = QWidget()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(30)
        title_layout.setContentsMargins(32, 28, 32, 28)
        
        # 主标题
        title_label = QLabel(t_gui('main_title'))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont(get_cross_platform_font(), 30, QFont.Bold))
        title_label.setStyleSheet("""
            color: #2c3e50;
            margin: 8px 0px;
        """)
        
        # 副标题
        subtitle_label = QLabel(t_gui('subtitle'))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setFont(QFont(get_cross_platform_font(), 16))
        subtitle_label.setStyleSheet("""
            color: #34495e;
            margin-bottom: 10px;
        """)
        
        # 商务口号区域
        slogan_container = QWidget()
        slogan_layout = QHBoxLayout()
        slogan_layout.setSpacing(24)
        slogan_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧口号
        slogan1_label = QLabel(t_gui("智能分析，精准投资"))
        slogan1_label.setAlignment(Qt.AlignCenter)
        slogan1_label.setFont(QFont(get_cross_platform_font(), 14, QFont.Bold))
        slogan1_label.setStyleSheet("""
            color: #667eea;
            background: rgba(102, 126, 234, 0.12);
            padding: 9px 18px;
            border-radius: 22px;
            border: 1px solid rgba(102, 126, 234, 0.25);
        """)
        
        # 右侧口号
        slogan2_label = QLabel(t_gui("数据驱动，决策无忧"))
        slogan2_label.setAlignment(Qt.AlignCenter)
        slogan2_label.setFont(QFont(get_cross_platform_font(), 14, QFont.Bold))
        slogan2_label.setStyleSheet("""
            color: #764ba2;
            background: rgba(118, 75, 162, 0.12);
            padding: 9px 18px;
            border-radius: 22px;
            border: 1px solid rgba(118, 75, 162, 0.25);
        """)
        
        slogan_layout.addStretch()
        slogan_layout.addWidget(slogan1_label)
        slogan_layout.addWidget(slogan2_label)
        slogan_layout.addStretch()
        slogan_container.setLayout(slogan_layout)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addWidget(slogan_container)
        title_container.setLayout(title_layout)
        title_container.setMaximumHeight(420)
        
        # 设置标题容器样式
        title_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.88);
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.45);
            }
        """)
        
        # 创建卡片容器
        self.cards_widget = QWidget()
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建三个市场分析卡片
        self.cn_card = self.create_market_card(t_gui("A股分析"), "#e74c3c", "CN_Data5000.json.gz", t_gui("加载中..."))
        self.hk_card = self.create_market_card(t_gui("港股分析"), "#9b59b6", "HK_Data1000.json.gz", t_gui("加载中..."))
        self.us_card = self.create_market_card(t_gui("美股分析"), "#3498db", "US_Data1000.json.gz", t_gui("加载中..."))
        
        cards_layout.addWidget(self.cn_card)
        cards_layout.addWidget(self.hk_card)
        cards_layout.addWidget(self.us_card)
        
        self.cards_widget.setLayout(cards_layout)
        self.cards_widget.setMaximumHeight(260)
        
        # 商务风格加载区域（初始隐藏）
        loading_container = QWidget()
        loading_layout = QVBoxLayout()
        loading_layout.setSpacing(14)
        loading_layout.setContentsMargins(18, 28, 18, 20)
        
        # 加载状态标签
        self.loading_label = QLabel(t_gui("正在启动智能分析引擎..."))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont(get_cross_platform_font(), 14, QFont.Bold))
        self.loading_label.setStyleSheet("""
            color: #2c3e50;
            background: rgba(255, 255, 255, 0.95);
            padding: 16px 22px;
            border-radius: 20px;
            border: 1px solid rgba(102, 126, 234, 0.3);
        """)
        self.loading_label.setVisible(False)
        
        # 高级进度条
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 100)
        self.loading_progress.setValue(0)
        self.loading_progress.setFixedHeight(12)
        # 默认进度条样式，后续会根据市场动态更新
        self.loading_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background: rgba(255, 255, 255, 0.3);
                color: transparent;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:0.5 #764ba2, stop:1 #667eea);
                border-radius: 6px;
                margin: 0px;
            }
        """)
        self.loading_progress.setVisible(False)
        
        # 加载提示文字
        loading_hint = QLabel(t_gui("提示：系统正在智能分析市场数据，请稍候..."))
        loading_hint.setAlignment(Qt.AlignCenter)
        loading_hint.setFont(QFont(get_cross_platform_font(), 11))
        loading_hint.setStyleSheet("""
            color: #7f8c8d;
            background: transparent;
            padding: 5px;
        """)
        loading_hint.setVisible(False)
        self.loading_hint = loading_hint
        
        loading_layout.addWidget(self.loading_label)
        loading_layout.addWidget(self.loading_progress)
        loading_layout.addWidget(loading_hint)
        loading_container.setLayout(loading_layout)
        loading_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.6);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)
        loading_container.setVisible(False)
        self.loading_container = loading_container
        self.loading_container.setMaximumHeight(200)
        
        # 布局组装
        main_layout.addWidget(title_container, stretch=13)
        main_layout.addWidget(self.cards_widget, stretch=7)
        main_layout.addWidget(self.loading_container)
        
        self.setLayout(main_layout)
        
    def create_market_card(self, title, color, data_file, date_text):
        """创建商务风格市场分析卡片"""
        card = QPushButton()
        card.setFixedSize(310, 220)
        card.setCursor(Qt.PointingHandCursor)
        
        # 根据卡片类型设置渐变色
        if t_gui("A股分析") in title:
            gradient_colors = "stop:0 #e74c3c, stop:1 #c0392b"  # 红色渐变
            icon = t_gui("中国")
        elif t_gui("港股分析") in title:
            gradient_colors = "stop:0 #9b59b6, stop:1 #8e44ad"  # 紫色渐变
            icon = t_gui("中国")
        else:  # 美股
            gradient_colors = "stop:0 #4facfe, stop:1 #00f2fe"  # 保持蓝色渐变
            icon = t_gui("美国")
        
        # 设置商务风格卡片样式
        card.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {gradient_colors});
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                font-weight: bold;
                text-align: center;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {gradient_colors});
                border: 2px solid rgba(255, 255, 255, 0.4);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {gradient_colors});
                border: 2px solid rgba(255, 255, 255, 0.6);
            }}
        """)
        
        # 创建卡片内容布局
        card_layout = QVBoxLayout()
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(22, 22, 22, 22)
        
        # 顶部图标和标题容器
        header_container = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        # 市场标识
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        icon_label.setStyleSheet("""
            background: transparent;
            color: white;
        """)
        
        # 市场标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setFont(QFont(get_cross_platform_font(), 20, QFont.Bold))
        title_label.setStyleSheet("""
            color: white; 
            background: transparent;
        """)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_container.setLayout(header_layout)
        
        # 分隔线
        separator = QWidget()
        separator.setFixedHeight(2)
        separator.setStyleSheet("""
            background: rgba(255, 255, 255, 0.3);
            border-radius: 1px;
        """)
        
        # 数据信息容器
        info_container = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)
        
        # 数据日期
        date_label = QLabel(date_text)
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setFont(QFont(get_cross_platform_font(), 11))
        date_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9); 
            background: transparent;
        """)
        date_label.setWordWrap(False)
        
        # 状态指示器
        status_label = QLabel(t_gui("数据就绪"))
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setFont(QFont(get_cross_platform_font(), 10))
        status_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.8);
            background: rgba(255, 255, 255, 0.1);
            padding: 4px 12px;
            border-radius: 12px;
        """)
        
        info_layout.addWidget(date_label)
        info_layout.addWidget(status_label)
        info_container.setLayout(info_layout)
        
        # 组装完整的卡片布局
        card_layout.addWidget(header_container)
        card_layout.addWidget(separator)
        card_layout.addStretch()
        card_layout.addWidget(info_container)
        card_layout.addStretch()
        
        # 将布局应用到卡片（通过创建一个容器widget）
        card_widget = QWidget(card)
        card_widget.setLayout(card_layout)
        card_widget.setGeometry(0, 0, 310, 220)
        card_widget.setStyleSheet("background: transparent;")
        
        # 绑定点击事件
        card.clicked.connect(lambda: self.on_card_clicked(data_file, color))
        
        # 保存日期标签引用以便后续更新
        setattr(card, 'date_label', date_label)
        
        return card
    
    def darken_color(self, hex_color, factor=0.2):
        """将颜色变暗"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * (1 - factor)) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"
    
    def load_data_dates(self):
        """从数据文件中加载日期信息"""
        import json
        import gzip
        from pathlib import Path
        
        data_files = {
            "CN_Data5000.json.gz": self.cn_card,
            "HK_Data1000.json.gz": self.hk_card,
            "US_Data1000.json.gz": self.us_card
        }
        
        for filename, card in data_files.items():
            try:
                # 使用智能路径查找，优先从EXE目录读取
                file_path = get_data_file_path(filename)
                if file_path.exists():
                    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 从metadata中获取日期信息
                    if data and 'metadata' in data:
                        metadata = data['metadata']
                        if 'columns' in metadata:
                            columns = metadata['columns']
                            # 过滤出日期列（8位数字格式：YYYYMMDD）
                            date_columns = [col for col in columns if isinstance(col, str) and col.isdigit() and len(col) == 8]
                            
                            if date_columns:
                                # 排序日期
                                sorted_dates = sorted(date_columns)
                                start_date = sorted_dates[0]
                                end_date = sorted_dates[-1]
                                
                                # 格式化日期显示（YYYY-MM-DD格式）
                                start_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
                                end_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
                                
                                date_text = f"{start_formatted} - {end_formatted}"
                                print(f" {filename} 日期解析成功: {date_text}")
                            else:
                                print(f" {filename} 无有效日期列，columns: {columns[:5]}...")
                                date_text = "无日期数据"
                        else:
                            print(f" {filename} metadata中无columns字段")
                            date_text = "无列信息"
                    else:
                        print(f" {filename} 无metadata字段，keys: {list(data.keys()) if data else 'None'}")
                        date_text = "无元数据"
                else:
                    print(f" {filename} 文件不存在")
                    date_text = "文件不存在"
                    
            except Exception as e:
                print(f"[ERROR] 读取{filename}日期信息失败: {e}")
                import traceback
                traceback.print_exc()
                date_text = "读取失败"
            
            # 更新卡片上的日期显示
            if hasattr(card, 'date_label'):
                card.date_label.setText(date_text)
    
    def on_card_clicked(self, data_file, color):
        """卡片点击处理"""
        # 使用智能路径查找，优先从EXE目录读取
        file_path = get_data_file_path(data_file)
        if not file_path.exists():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, t_gui("文件不存在"), t_gui("数据文件 {data_file} 不存在！").format(data_file=data_file))
            return
        
        # 显示加载进度
        self.show_loading_progress(color)
            
            # 发射文件选择信号
        self.file_selected.emit(str(file_path))
    
    def show_loading_progress(self, color):
        """显示商务风格加载进度"""
        self.cards_widget.setVisible(False)
        self.loading_container.setVisible(True)
        self.loading_label.setVisible(True)
        self.loading_progress.setVisible(True)
        self.loading_hint.setVisible(True)
        
        # 根据不同市场设置进度条颜色和加载消息
        if "#e74c3c" in str(color) or "cn" in str(color).lower():
            # A股 - 红色
            market_msg = "正在分析A股市场数据..."
            progress_gradient = "stop:0 #e74c3c, stop:1 #c0392b"
        elif "#9b59b6" in str(color) or "hk" in str(color).lower():
            # 港股 - 紫色
            market_msg = "正在分析港股市场数据..."
            progress_gradient = "stop:0 #9b59b6, stop:1 #8e44ad"
        elif "#4facfe" in str(color) or "us" in str(color).lower():
            # 美股 - 蓝色
            market_msg = "正在分析美股市场数据..."
            progress_gradient = "stop:0 #4facfe, stop:1 #00f2fe"
        else:
            # 默认
            market_msg = "正在启动智能分析引擎..."
            progress_gradient = "stop:0 #667eea, stop:1 #764ba2"
        
        # 更新进度条颜色
        self.loading_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 6px;
                text-align: center;
                background: rgba(255, 255, 255, 0.3);
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {progress_gradient});
                border-radius: 6px;
                margin: 0px;
            }}
        """)
        
        self.loading_label.setText(market_msg)
    
    def update_loading_progress(self, value, text):
        """更新商务风格加载进度"""
        if self.loading_progress:
            self.loading_progress.setValue(value)
        if self.loading_label:
            # 直接显示文本，不添加emoji
            self.loading_label.setText(text)
        
        # 更新提示文字
        if hasattr(self, 'loading_hint') and self.loading_hint:
            if value < 50:
                self.loading_hint.setText(t_gui("系统正在智能分析海量数据，预计还需要几秒钟..."))
            elif value < 80:
                self.loading_hint.setText(t_gui("分析即将完成，正在优化结果展示..."))
            else:
                self.loading_hint.setText(t_gui("分析完成，准备为您呈现专业投资建议..."))
    
    def hide_loading_progress(self):
        """隐藏加载进度界面"""
        if hasattr(self, 'loading_container'):
            self.loading_container.setVisible(False)
        if self.loading_progress:
            self.loading_progress.setVisible(False)
        if self.loading_label:
            self.loading_label.setVisible(False)
        if hasattr(self, 'loading_hint'):
            self.loading_hint.setVisible(False)
        if self.cards_widget:
            self.cards_widget.setVisible(True)
    
    def on_ai_checkbox_changed(self, state):
        """AI复选框状态变化回调"""
        self.enable_ai_analysis = (state == Qt.Checked)
    
    def get_ai_analysis_enabled(self):
        """获取AI分析是否启用"""
        return self.enable_ai_analysis


class AnalysisPage(QWidget):
    """第二页 - 分析结果页面，移植原界面的窗口内容"""
    
    def __init__(self):
        super().__init__()
        
        self.analysis_results = None
        self.analysis_results_obj = None
        self.analysis_dict = None
        
        # AI分析相关
        self.stock_ai_cache = {}  # 缓存AI分析结果
        self.ai_analysis_in_progress = False  # 防止重复分析
        self.current_ai_stock = None  # 当前分析的股票
        self.ai_analysis_executed = False  # 是否已执行过AI分析
        
        # 迷你投资大师相关
        self.mini_master_cache = {}  # 缓存迷你投资大师分析结果
        self.mini_master_analysis_in_progress = False  # 防止重复分析
        self.current_mini_master_stock = None  # 当前分析的股票
        
        # 行业AI分析相关
        self.industry_ai_cache = {}  # 缓存行业AI分析结果
        self.industry_ai_analysis_in_progress = False  # 防止重复分析
        self.current_industry_name = None  # 当前分析的行业
        
        # 服务器状态
        self.server_started = False  # 服务器是否已启动
        self.server_started_by_us = False  # 是否是本软件启动的
        self.server_process = None  # 服务器进程
        
        # 主窗口引用
        self.main_window = None
        
        # 调用setup_ui创建界面
        self.setup_ui()
    
    def _ai_analysis_before(self, analysis_type="AI分析"):
        """AI分析执行前的统一处理（AnalysisPage版本）
        
        Args:
            analysis_type: 分析类型名称（用于日志）
            
        Returns:
            tuple: (success: bool, config: dict)
                success: True表示可以继续执行，False表示应该终止
                config: 加载的配置字典
        """
        try:
            print(f"[{analysis_type}] 执行前检查...")
            
            # 1. 重新加载AI配置（确保使用最新配置）
            config = {}
            try:
                import json
                from pathlib import Path
                from utils.path_helper import get_base_path
                
                base_path = get_base_path()
                config_path = base_path / "llm-api" / "config" / "user_settings.json"
                
                if config_path.exists():
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        print(f"[{analysis_type}] 已重新加载AI配置")
                else:
                    print(f"[{analysis_type}] 配置文件不存在")
                    return False, {}
            except Exception as e:
                print(f"[{analysis_type}] 加载配置失败: {e}")
                return False, {}
            
            # 2. 试用功能检查（必须在API Key检查之前）
            is_trial_mode = False
            try:
                from utils.ai_usage_counter import get_ai_usage_count
                
                provider = config.get('default_provider', '').lower()
                api_key = config.get('SILICONFLOW_API_KEY', '').strip()
                current_count = get_ai_usage_count()
                
                # 检查是否符合试用条件：SiliconFlow + 无API Key + 计数<20
                if provider == 'siliconflow' and not api_key and current_count < 20:
                    print(f"[试用模式] 符合试用条件（{current_count}/20次）")
                    print(f"[试用模式] 使用预设试用配置")
                    
                    # 使用硬编码的试用配置
                    trial_config = {
                        "default_provider": "SiliconFlow",
                        "default_chat_model": "Qwen/Qwen3-8B",
                        "default_structured_model": "Qwen/Qwen3-8B",
                        "request_timeout": 600,
                        "agent_role": "不使用",
                        "SILICONFLOW_API_KEY": "sk-zbzzqzrcjyemnxlgcwiznrkuxrpdkrnpbneurezszujaqfjg",
                        "SILICONFLOW_BASE_URL": "https://api.siliconflow.cn/v1",
                        "dont_show_api_dialog": True
                    }
                    
                    # 使用试用配置
                    config = trial_config
                    is_trial_mode = True
                    
                    print(f"[试用模式] 配置已切换为试用模式，剩余 {20 - current_count} 次试用机会")
                else:
                    if provider == 'siliconflow' and not api_key and current_count >= 20:
                        print(f"[试用模式] 试用次数已用完（{current_count}/20），请配置API Key")
                        
            except Exception as e:
                print(f"[{analysis_type}] 试用检查出错: {e}")
            
            # 3. 检查API Key（如果不是试用模式才检查）
            if not is_trial_mode:
                provider = config.get('default_provider', 'OpenAI')
                from config.gui_i18n import get_system_language
                use_english = get_system_language() == 'en'
                
                api_key_error = self._check_api_key_for_stock_analysis(config, provider, use_english, base_path)
                if api_key_error:
                    print(f"[{analysis_type}] API Key检查失败: {api_key_error}")
                    return False, config
            else:
                print(f"[{analysis_type}] 试用模式，跳过API Key检查")
            
            print(f"[{analysis_type}] 执行前检查通过")
            return True, config
            
        except Exception as e:
            print(f"[{analysis_type}] 执行前检查出错: {e}")
            import traceback
            traceback.print_exc()
            return False, {}
    
    def _ai_analysis_after(self, success=True, analysis_type="AI分析"):
        """AI分析执行后的统一处理（AnalysisPage版本）
        
        Args:
            success: 分析是否成功
            analysis_type: 分析类型名称（用于日志）
        """
        try:
            print(f"[{analysis_type}] 执行后处理...")
            
            if success:
                # 1. 增加AI使用计数
                try:
                    from utils.ai_usage_counter import increment_ai_usage
                    count = increment_ai_usage()
                    print(f"[AI计数] {analysis_type}完成，累计使用: {count} 次")
                except Exception as e:
                    print(f"[AI计数] 计数失败: {e}")
                
                # 2. 可以添加其他成功后的处理
                # 例如：记录分析日志、更新缓存等
            else:
                print(f"[{analysis_type}] 分析未成功，跳过后续处理")
            
        except Exception as e:
            print(f"[{analysis_type}] 执行后处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    def set_main_window(self, main_window):
        """设置主窗口引用，用于访问detected_market等属性"""
        self.main_window = main_window
        # 更新Tab可见性
        self.update_cn_market_tabs_visibility()
    
    def update_cn_market_tabs_visibility(self):
        """根据市场类型和语言更新中国市场专属Tab的可见性"""
        try:
            # 获取当前语言
            current_lang = get_system_language() if callable(get_system_language) else 'zh'
            
            # 获取市场类型
            detected_market = 'cn'  # 默认值
            if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'detected_market'):
                detected_market = self.main_window.detected_market
            
            is_cn_market = (detected_market or 'cn').lower() == 'cn'
            should_show_cn_tabs = current_lang.startswith('zh') and is_cn_market
            
            print(f"[Tab可见性更新] 语言: {current_lang}, 市场: {detected_market}, 显示中国市场Tab: {should_show_cn_tabs}")
            
            # 更新市场分析页面的Tab
            # 注意：market_tab_widget 和 market_html_tabs 是 AnalysisPage 的属性，不是 market_page 的属性
            if hasattr(self, 'market_tab_widget') and hasattr(self, 'market_html_tabs'):
                print(f"[Tab可见性更新] market_html_tabs 数量: {len(self.market_html_tabs)}")
                for tab_index, view, html_path in self.market_html_tabs:
                    print(f"[Tab可见性更新] 设置市场Tab {tab_index} 可见性为: {should_show_cn_tabs}")
                    self.market_tab_widget.setTabVisible(tab_index, should_show_cn_tabs)
            else:
                print(f"[Tab可见性更新] market_tab_widget 或 market_html_tabs 不存在")
                print(f"  - hasattr market_tab_widget: {hasattr(self, 'market_tab_widget')}")
                print(f"  - hasattr market_html_tabs: {hasattr(self, 'market_html_tabs')}")
            
            # 更新个股分析页面的Tab
            # 注意：stock_tab_widget 和 stock_extra_tabs 是 AnalysisPage 的属性，不是 stock_page 的属性
            if hasattr(self, 'stock_tab_widget') and hasattr(self, 'stock_extra_tabs'):
                print(f"[Tab可见性更新] stock_extra_tabs 数量: {len(self.stock_extra_tabs)}")
                for tab_index, view, html_path in self.stock_extra_tabs:
                    print(f"[Tab可见性更新] 设置个股Tab {tab_index} 可见性为: {should_show_cn_tabs}")
                    self.stock_tab_widget.setTabVisible(tab_index, should_show_cn_tabs)
            else:
                print(f"[Tab可见性更新] stock_tab_widget 或 stock_extra_tabs 不存在")
                print(f"  - hasattr stock_tab_widget: {hasattr(self, 'stock_tab_widget')}")
                print(f"  - hasattr stock_extra_tabs: {hasattr(self, 'stock_extra_tabs')}")
                        
        except Exception as e:
            print(f"[ERROR] 更新Tab可见性失败: {e}")
            import traceback
            traceback.print_exc()
        
    def _get_html_lang(self):
        """获取HTML语言标识"""
        try:
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            return "en" if is_english() else "zh-CN"
        except:
            return "zh-CN"
        
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧树形导航 - 增大字体与行业分析标题一致
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel(t_gui('analysis_items_header'))
        self.tree_widget.setMaximumWidth(350)
        self.tree_widget.setMinimumWidth(300)
        self.tree_widget.setFont(QFont(get_cross_platform_font(), 14))  # 增大字体与行业分析标题一致
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                font-size: 14px;
            }
            QTreeWidget::item {
                height: 36px;
                padding: 8px;
            }
            QTreeWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #e9ecef;
            }
            QTreeWidget::item:has-children {
                font-weight: bold;
            }
        """)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        
        # 右侧内容显示区域
        self.content_area = QStackedWidget()
        self.content_area.setStyleSheet("""
            QStackedWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        # 添加到分割器
        splitter.addWidget(self.tree_widget)
        splitter.addWidget(self.content_area)
        splitter.setStretchFactor(0, 0)  # 左侧固定宽度
        splitter.setStretchFactor(1, 1)  # 右侧占满剩余空间
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # 初始化树形结构和内容页面
        self.setup_tree_structure()
        self.setup_content_pages()
        
    def _create_item_with_new_badge(self, text):
        """创建带有红色NEW标志的TreeWidget项"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(8)
        
        # 文本标签
        text_label = QLabel(text)
        text_label.setStyleSheet("background: transparent; color: #2c3e50; font-size: 13px;")
        
        # NEW标志
        new_label = QLabel("NEW")
        new_label.setStyleSheet("""
            background-color: #ff0000;
            color: white;
            font-weight: bold;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 3px;
        """)
        new_label.setFixedHeight(18)
        
        layout.addWidget(text_label)
        layout.addWidget(new_label)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def setup_tree_structure(self):
        """设置树形结构 - 带子项目"""
        # AI建议
        ai_item = QTreeWidgetItem([t_gui('ai_suggestions')])
        ai_item.setData(0, Qt.UserRole, "ai_suggestions")
        self.tree_widget.addTopLevelItem(ai_item)
        
        # 大盘分析
        market_item = QTreeWidgetItem()
        market_item.setData(0, Qt.UserRole, "market_analysis")
        self.tree_widget.addTopLevelItem(market_item)
        self.tree_widget.setItemWidget(market_item, 0, self._create_item_with_new_badge(t_gui('market_analysis')))
        
        # 行业列表 - 动态添加子项目
        self.industry_item = QTreeWidgetItem([t_gui('industry_list')])
        self.industry_item.setData(0, Qt.UserRole, "industry_list")
        self.tree_widget.addTopLevelItem(self.industry_item)
        
        # 个股列表 - 动态添加子项目  
        self.stock_item = QTreeWidgetItem()
        self.stock_item.setData(0, Qt.UserRole, "stock_list")
        self.tree_widget.addTopLevelItem(self.stock_item)
        self.tree_widget.setItemWidget(self.stock_item, 0, self._create_item_with_new_badge(t_gui('stock_list')))
        
        # 默认选中AI建议
        self.tree_widget.setCurrentItem(ai_item)
        
    def setup_content_pages(self):
        """设置内容页面 - 移植原界面的实现"""
        # AI建议页面
        self.ai_page = self.create_ai_suggestions_page()
        self.content_area.addWidget(self.ai_page)
        
        # 大盘分析页面 - 移植MarketSentimentWindow的内容
        self.market_page = self.create_market_analysis_page()
        self.content_area.addWidget(self.market_page)
        
        # 行业分析页面 - 移植IndustryAnalysisWindow的内容
        self.industry_page = self.create_industry_analysis_page()
        self.content_area.addWidget(self.industry_page)
        
        # 个股分析页面 - 移植StockAnalysisWindow的内容
        self.stock_page = self.create_stock_analysis_page()
        self.content_area.addWidget(self.stock_page)
        
        # 默认显示AI建议页面
        self.content_area.setCurrentWidget(self.ai_page)
        
    def create_ai_suggestions_page(self):
        """创建AI建议页面 - 改用WebView显示HTML报告，添加功能按钮"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(3, 3, 3, 3)  # 减少边距从5到3
        main_layout.setSpacing(3)  # 减少间距从5到3
        
        # 顶部区域：标题和按钮
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        self.ai_title_label = QLabel(t_gui('ai_intelligent_analysis'))
        self.ai_title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        self.ai_title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        self.ai_title_label.setTextFormat(Qt.RichText)  # 支持HTML格式
        header_layout.addWidget(self.ai_title_label)
        
        # 添加弹性空间
        header_layout.addStretch()
        
        # AI设置按钮
        self.ai_settings_btn = QPushButton(t_gui('ai_settings_btn'))
        self.ai_settings_btn.setFont(QFont(get_cross_platform_font(), 10))
        self.ai_settings_btn.setFixedSize(100, 35)
        self.ai_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.ai_settings_btn.clicked.connect(self.open_ai_settings)
        header_layout.addWidget(self.ai_settings_btn)
        
        # 安装AI按钮 - 改为蓝色
        self.install_ai_btn = QPushButton(t_gui("安装AI"))
        self.install_ai_btn.setFont(QFont(get_cross_platform_font(), 10))
        self.install_ai_btn.setFixedSize(100, 35)
        self.install_ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.install_ai_btn.clicked.connect(self.install_ai)
        header_layout.addWidget(self.install_ai_btn)
        
        # AI分析按钮 - 插入在AI设置和另存为之间
        self.ai_analysis_btn = QPushButton(t_gui("ai_analysis"))
        self.ai_analysis_btn.setFont(QFont(get_cross_platform_font(), 10))
        self.ai_analysis_btn.setFixedSize(100, 35)
        self.ai_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.ai_analysis_btn.clicked.connect(self.start_ai_analysis)
        header_layout.addWidget(self.ai_analysis_btn)
        
        # 保存HTML按钮
        self.save_html_btn = QPushButton(t_gui('save_html_btn'))
        self.save_html_btn.setFont(QFont(get_cross_platform_font(), 10))
        self.save_html_btn.setFixedSize(100, 35)
        self.save_html_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e7e34;
            }
            QPushButton:pressed {
                background-color: #155724;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.save_html_btn.clicked.connect(self.save_html_report)
        self.save_html_btn.setEnabled(False)  # 初始状态为禁用
        header_layout.addWidget(self.save_html_btn)
        
        # 将头部布局添加到主布局
        main_layout.addLayout(header_layout)
        
        # 内容显示区域
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 根据WebEngine可用性选择显示方式
        if WEBENGINE_AVAILABLE and QWebEngineView:
            # 使用WebView显示HTML报告
            self.ai_webview = QWebEngineView()
            self.ai_webview.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    background-color: white;
                }
            """)
            
            # 显示初始提示
            initial_html = """
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { 
                        font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; 
                        padding: 20px; 
                        text-align: center;
                        background: #f8f9fa;
                        margin: 0;
                    }
                    .container {
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 30px;
                        background: white;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    .icon { 
                        font-size: 48px; 
                        margin-bottom: 20px; 
                        color: #007bff;
                    }
                    .title { 
                        color: #495057; 
                        font-size: 18px; 
                        margin-bottom: 15px; 
                        font-weight: bold;
                    }
                    .description { 
                        color: #6c757d; 
                        font-size: 14px; 
                        line-height: 1.6; 
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon"></div>
                    <div class="title">等待分析完成</div>
                    <div class="description">
                        分析完成后，此处将显示完整的HTML分析报告<br/>
                        包含市场情绪分析、个股分析、行业分析和AI智能建议<br/><br/>
                        如果AI分析未执行，请检查AI设置
                    </div>
                </div>
            </body>
            </html>
            """
            self.ai_webview.setHtml(initial_html)
            content_layout.addWidget(self.ai_webview)
        else:
            # WebEngine不可用，使用文本显示
            print(t_gui("webengine_unavailable_using_text"))
            self.ai_browser = QTextBrowser()
            self.ai_browser.setFont(QFont(get_cross_platform_font(), 10))
            self.ai_browser.setStyleSheet("""
                QTextBrowser {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 15px;
                    background-color: white;
                    color: #495057;
                    line-height: 1.6;
                }
            """)
            self.ai_browser.setPlainText(
                f"{t_gui('ai_function_preparing')}\n\n"
                f"{t_gui('load_data_tip')}\n"
                f"{t_gui('ai_settings_tip')}\n\n"
                f"{t_gui('using_text_display_mode')}"
            )
            content_layout.addWidget(self.ai_browser)
        
        # 将内容布局添加到主布局
        main_layout.addLayout(content_layout)
        
        widget.setLayout(main_layout)
        return widget
    
    def open_ai_settings(self):
        """打开AI设置界面 - 始终运行 llm-api\aisetting.exe"""
        try:
            import subprocess
            import os
            
            # 清除AI配置缓存，确保下次AI分析时重新加载配置
            AnalysisWorker._ai_config_cache = None
            AnalysisWorker._ai_config_cache_time = 0
            print("[AI设置] 已清除AI配置缓存，下次分析将重新加载配置")
            
            # 获取当前exe所在目录（打包后）或脚本所在目录（开发时）
            if getattr(sys, 'frozen', False):
                # 打包后：exe所在目录
                exe_dir = os.path.dirname(sys.executable)
            else:
                # 开发时：脚本所在目录
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 在 llm-api 子目录下查找 aisetting.exe
            aisetting_exe = os.path.join(exe_dir, "llm-api", "aisetting.exe")
            
            if os.path.exists(aisetting_exe):
                # 找到了 aisetting.exe，直接运行
                subprocess.Popen([aisetting_exe], cwd=os.path.dirname(aisetting_exe))
                return
            else:
                # 未找到 aisetting.exe，显示错误信息
                QMessageBox.warning(
                    self,
                    "AI设置程序未找到",
                    f"未找到 aisetting.exe\n\n"
                    f"查找路径: {aisetting_exe}\n\n"
                    f"请确保 llm-api\\aisetting.exe 存在。"
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "错误",
                f"打开AI设置失败：\n\n{str(e)}"
            )
    
    def install_ai(self):
        """安装AI功能 - 跨平台支持"""
        try:
            import subprocess
            import os
            import platform
            from pathlib import Path
            from utils.path_helper import get_base_path
            
            # 获取当前目录（在打包环境下应该是EXE所在目录）
            current_dir = Path(get_base_path())
            
            # 检测操作系统
            system = platform.system()
            print(f"检测到操作系统: {system}")
            print(f"查找安装文件的目录: {current_dir}")
            
            # 优先执行InstOlla.exe (仅Windows)
            if system == "Windows":
                instolla_path = current_dir / "InstOlla.exe"
                print(f"检查 InstOlla.exe: {instolla_path}, 存在={instolla_path.exists()}")
                if instolla_path.exists():
                    print("执行InstOlla.exe...")
                    subprocess.Popen([str(instolla_path)], cwd=str(current_dir))
                    QMessageBox.information(self, t_gui("安装AI"), t_gui("已启动InstOlla.exe安装程序"))
                    return
            
            # 根据系统选择对应的安装脚本
            if system == "Windows":
                # Windows系统 - 使用.bat脚本
                install_script_path = current_dir / "InstallOllama.bat"
                script_name = "InstallOllama.bat"
                print(f"检查 {script_name}: {install_script_path}, 存在={install_script_path.exists()}")
                
                if install_script_path.exists():
                    print(f"执行{script_name}...")
                    subprocess.Popen([str(install_script_path)], cwd=str(current_dir), shell=True)
                    QMessageBox.information(self, t_gui("安装AI"), t_gui("已启动InstallOllama.bat安装脚本"))
                    return
                    
            elif system == "Darwin":
                # macOS系统 - 使用.sh脚本
                install_script_path = current_dir / "InstallOllama.sh"
                script_name = "InstallOllama.sh"
                
                if install_script_path.exists():
                    print(f"执行{script_name}...")
                    # 确保脚本有执行权限
                    os.chmod(str(install_script_path), 0o755)
                    # 使用Terminal.app打开脚本，这样用户可以看到安装进度
                    apple_script = f'''
                    tell application "Terminal"
                        activate
                        do script "cd '{current_dir}' && ./InstallOllama.sh"
                    end tell
                    '''
                    subprocess.run(['osascript', '-e', apple_script])
                    QMessageBox.information(self, t_gui("安装AI"), 
                                          "已在终端中启动 InstallOllama.sh 安装脚本\n"
                                          "请在终端窗口中查看安装进度")
                    return
                    
            elif system == "Linux":
                # Linux系统 - 使用.sh脚本
                install_script_path = current_dir / "InstallOllama.sh"
                script_name = "InstallOllama.sh"
                
                if install_script_path.exists():
                    print(f"执行{script_name}...")
                    # 确保脚本有执行权限
                    os.chmod(str(install_script_path), 0o755)
                    # 在新的终端窗口中运行脚本
                    try:
                        # 尝试不同的终端模拟器
                        terminal_commands = [
                            ['gnome-terminal', '--', 'bash', '-c', f'cd "{current_dir}" && ./InstallOllama.sh; read -p "按Enter键关闭..."'],
                            ['konsole', '-e', 'bash', '-c', f'cd "{current_dir}" && ./InstallOllama.sh; read -p "按Enter键关闭..."'],
                            ['xterm', '-e', 'bash', '-c', f'cd "{current_dir}" && ./InstallOllama.sh; read -p "按Enter键关闭..."'],
                        ]
                        
                        for cmd in terminal_commands:
                            try:
                                subprocess.Popen(cmd)
                                QMessageBox.information(self, t_gui("安装AI"), 
                                                      "已在终端中启动 InstallOllama.sh 安装脚本\n"
                                                      "请在终端窗口中查看安装进度")
                                return
                            except FileNotFoundError:
                                continue
                        
                        # 如果没有找到图形终端，使用后台运行
                        subprocess.Popen(['bash', str(install_script_path)], cwd=str(current_dir))
                        QMessageBox.information(self, t_gui("安装AI"), 
                                              "已启动 InstallOllama.sh 安装脚本\n"
                                              "安装过程在后台进行")
                        return
                        
                    except Exception as e:
                        print(f"启动终端失败: {e}")
                        # 回退到后台运行
                        subprocess.Popen(['bash', str(install_script_path)], cwd=str(current_dir))
                        QMessageBox.information(self, t_gui("安装AI"), 
                                              "已启动 InstallOllama.sh 安装脚本\n"
                                              "安装过程在后台进行")
                        return
            
            # 构建错误消息
            missing_files = []
            if system == "Windows":
                if not (current_dir / "InstOlla.exe").exists():
                    missing_files.append("InstOlla.exe")
                if not (current_dir / "InstallOllama.bat").exists():
                    missing_files.append("InstallOllama.bat")
            else:
                if not (current_dir / "InstallOllama.sh").exists():
                    missing_files.append("InstallOllama.sh")
            
            if missing_files:
                QMessageBox.warning(self, t_gui("安装AI"), 
                                  f"未找到适用于 {system} 系统的安装文件：\n" +
                                  "\n".join(f"- {file}" for file in missing_files) +
                                  "\n\n请确保安装文件存在于程序目录中。")
            else:
                QMessageBox.warning(self, t_gui("安装AI"), 
                                  f"不支持的操作系统: {system}\n"
                                  "目前支持: Windows, macOS, Linux")
                
        except Exception as e:
            QMessageBox.critical(self, t_gui("错误"), f"{t_gui('启动AI安装程序失败')}\n{str(e)}")
    
    def save_html_report(self):
        """保存HTML报告到用户指定位置"""
        try:
            # 检查是否有分析结果
            if not hasattr(self, 'analysis_results') or not self.analysis_results:
                QMessageBox.warning(self, t_gui('warning'), t_gui('no_analysis_data'))
                return
            
            # 检查是否有HTML报告文件
            if not hasattr(self, 'current_html_path') or not self.current_html_path:
                QMessageBox.warning(self, t_gui('warning'), t_gui('no_html_report'))
                return
            
            # 打开文件保存对话框
            from PyQt5.QtWidgets import QFileDialog
            # 根据是否有AI分析结果决定文件名
            if self.ai_analysis_executed:
                default_name = f"AI智能分析报告_{time.strftime('%Y%m%d_%H%M%S')}.html"
            else:
                default_name = f"{t_gui('ai_stock_analysis_report')}_{time.strftime('%Y%m%d_%H%M%S')}.html"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                t_gui('save_html_report'),
                default_name,
                t_gui("html_files_filter")
            )
            
            if file_path:
                # 复制当前HTML文件到指定位置
                import shutil
                shutil.copy2(self.current_html_path, file_path)
                
                QMessageBox.information(self, t_gui('success'), t_gui('html_saved_success', path=file_path))
                
        except Exception as e:
            QMessageBox.critical(self, t_gui('error'), t_gui('html_report_save_failed', error=str(e)))
        
    def create_market_analysis_page(self):
        """创建大盘分析页面 - 添加Tab结构，与行业分析/个股分析保持一致"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 标题
        self.market_title_label = QLabel(t_gui('market_sentiment_analysis'))
        self.market_title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))  # 统一为16号字体
        self.market_title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        self.market_title_label.setTextFormat(Qt.RichText)  # 支持HTML格式
        
        # Tab控件 - 与行业分析/个股分析保持一致的样式
        from PyQt5.QtWidgets import QTabWidget
        self.market_tab_widget = QTabWidget()
        self.market_tab_widget.setFont(QFont(get_cross_platform_font(), 10))
        self.market_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #007bff;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)

        # Tab 1: 详细分析 - 包含原有的市场情绪分析内容
        self.market_detail_tab = self.create_market_detail_tab()
        self.market_tab_widget.addTab(self.market_detail_tab, t_gui("详细分析"))
        
        # Tab 2/3/4: 中国市场专属Tab（初始创建，可见性稍后由update_cn_market_tabs_visibility控制）
        # 初始化市场HTML Tab列表
        self.market_html_tabs = []
        
        # 始终创建这些Tab，但可见性由市场类型决定
        # 已删除：股票排行榜Tab
        
        tab_widget2, view2, html_path2 = self.create_market_html_tab("股票涨停板.html")
        index2 = self.market_tab_widget.addTab(tab_widget2, t_gui("股票涨停板"))
        self.market_html_tabs.append((index2, view2, html_path2))
        
        tab_widget3, view3, html_path3 = self.create_market_html_tab("行业趋势.html")
        index3 = self.market_tab_widget.addTab(tab_widget3, t_gui("行业趋势"))
        self.market_html_tabs.append((index3, view3, html_path3))
        
        # 默认隐藏这些Tab，等待update_cn_market_tabs_visibility更新可见性
        for tab_index, _, _ in self.market_html_tabs:
            self.market_tab_widget.setTabVisible(tab_index, False)
        
        # 连接Tab切换事件
        self.market_tab_widget.currentChanged.connect(self.on_market_tab_changed)
        
        # 布局
        main_layout.addWidget(self.market_title_label)
        main_layout.addWidget(self.market_tab_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_market_detail_tab(self):
        """创建市场详细分析Tab - 原有的市场情绪分析内容"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 内容区域 - 使用WebEngineView显示HTML内容
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.market_text = QWebEngineView()
            self.market_text.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.market_text = QTextEdit()
            self.market_text.setFont(QFont(get_cross_platform_font(), 11))
            self.market_text.setReadOnly(True)
        self.market_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        
        layout.addWidget(self.market_text)
        widget.setLayout(layout)
        return widget
    
    def create_market_html_tab(self, filename):
        """创建打开本地HTML文件的Tab（延迟加载）"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        from utils.path_helper import get_base_path
        base_path = Path(get_base_path())
        html_path = base_path / "html" / filename
        if not html_path.exists():
            alt_path = project_root / "html" / filename
            if alt_path.exists():
                html_path = alt_path
            else:
                print(f"HTML文件未找到: {html_path} 或 {alt_path}")
        
        if WEBENGINE_AVAILABLE and QWebEngineView:
            view = QWebEngineView()
            try:
                settings = view.settings()
                settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            except Exception as e:
                print(f"配置WebEngine设置时出错: {e}")
            view.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    background-color: white;
                }
            """)
            # 不在这里加载HTML，而是在Tab切换时加载
            view.setHtml(f"<div style='padding:20px;font-family:{get_cross_platform_font_family()};color:#666;text-align:center;'>切换到此Tab查看内容</div>")
        else:
            view = QTextEdit()
            view.setReadOnly(True)
            view.setFont(QFont(get_cross_platform_font(), 11))
            view.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 12px;
                }
            """)
            # 不在这里加载HTML，而是在Tab切换时加载
            view.setPlainText("切换到此Tab查看内容")
        
        layout.addWidget(view)
        widget.setLayout(layout)
        return widget, view, html_path

        
    def create_industry_analysis_page(self):
        """创建行业分析页面 - 增加Tab结构，包含AI分析"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 标题
        self.industry_title_label = QLabel(t_gui('industry_analysis'))
        self.industry_title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))  # 统一为16号字体
        self.industry_title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        self.industry_title_label.setTextFormat(Qt.RichText)  # 支持HTML格式
        
        # Tab控件 - 类似个股分析的结构
        from PyQt5.QtWidgets import QTabWidget
        self.industry_tab_widget = QTabWidget()
        self.industry_tab_widget.setFont(QFont(get_cross_platform_font(), 10))
        
        # 连接Tab切换事件，用于AI分析自动显示
        self.industry_tab_widget.currentChanged.connect(self.on_industry_tab_changed)
        self.industry_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #007bff;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)

        # Tab 1: 详细分析 - 原有的行业分析显示
        self.industry_detail_tab = self.create_industry_detail_tab()
        self.industry_tab_widget.addTab(self.industry_detail_tab, t_gui("📋_详细分析"))
        
        # Tab 2: 趋势图表 - 新增行业趋势图表功能（指数行业会动态隐藏）
        self.industry_chart_tab = self.create_industry_chart_tab()
        self.industry_chart_tab_index = self.industry_tab_widget.addTab(self.industry_chart_tab, t_gui("趋势图表"))
        

        
        # Tab 4: 行业AI分析 - 新增AI分析功能
        self.industry_ai_analysis_tab = self.create_industry_ai_analysis_tab()
        self.industry_tab_widget.addTab(self.industry_ai_analysis_tab, t_gui("AI分析"))
        
        main_layout.addWidget(self.industry_title_label)
        main_layout.addWidget(self.industry_tab_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_industry_detail_tab(self):
        """创建行业详细分析Tab - 原有的显示区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 详细信息显示区域 - 使用WebEngineView
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.industry_detail_text = QWebEngineView()
            self.industry_detail_text.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.industry_detail_text = QTextEdit()
            self.industry_detail_text.setFont(QFont(get_cross_platform_font(), 11))
            self.industry_detail_text.setReadOnly(True)
        self.industry_detail_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        initial_html = f"""
        <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
            <h3 style="color: #007bff;"> 行业详细分析</h3>
            <p>{t_gui("select_industry_from_left_panel")}</p>
        </div>
        """
        self.set_industry_detail_html(initial_html)
        
        layout.addWidget(self.industry_detail_text)
        widget.setLayout(layout)
        return widget
    
    def create_industry_chart_tab(self):
        """创建行业趋势图表Tab - 支持等待画面的趋势图表"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 使用QStackedWidget来切换等待画面和结果画面
        from PyQt5.QtWidgets import QStackedWidget
        self.industry_chart_stacked_widget = QStackedWidget()
        
        # 页面0: 初始提示页面
        initial_page = QWidget()
        initial_layout = QVBoxLayout()
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.industry_chart_initial_view = QWebEngineView()
            self.industry_chart_initial_view.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
            """)
            initial_layout.addWidget(self.industry_chart_initial_view)
        else:
            self.industry_chart_initial_text = QTextEdit()
            self.industry_chart_initial_text.setReadOnly(True)
            self.industry_chart_initial_text.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 15px;
                    line-height: 1.6;
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                }
            """)
            initial_layout.addWidget(self.industry_chart_initial_text)
        initial_page.setLayout(initial_layout)
        
        # 页面1: 等待页面 - 按迷你投资大师风格设计
        loading_page = self.create_industry_chart_loading_page()
        
        # 页面2: 结果页面
        result_page = QWidget()
        result_layout = QVBoxLayout()
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.industry_chart_webview = QWebEngineView()
            self.industry_chart_webview.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
            """)
            result_layout.addWidget(self.industry_chart_webview)
            
        else:
            self.industry_chart_text = QTextEdit()
            self.industry_chart_text.setReadOnly(True)
            self.industry_chart_text.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 15px;
                    line-height: 1.6;
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                }
            """)
            result_layout.addWidget(self.industry_chart_text)
        result_page.setLayout(result_layout)
        
        # 添加页面到stacked widget
        self.industry_chart_stacked_widget.addWidget(initial_page)  # 索引0
        self.industry_chart_stacked_widget.addWidget(loading_page)  # 索引1
        self.industry_chart_stacked_widget.addWidget(result_page)   # 索引2
        
        layout.addWidget(self.industry_chart_stacked_widget)
        
        # 设置初始内容
        default_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-align: center;
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .placeholder {{
                    background: rgba(255, 255, 255, 0.1);
                    padding: 40px;
                    border-radius: 15px;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                .icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 15px;
                }}
                .description {{
                    font-size: 16px;
                    line-height: 1.6;
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <div class="placeholder">
                <div class="icon"></div>
                <div class="title">点击此Tab开始计算趋势图表</div>
                <div class="description">
                    将显示：<br/>
                    • 行业加权涨跌幅走势图<br/>
                    • 行业平均成交量<br/>
                    • 行业平均评级趋势<br/>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 设置各页面内容
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.industry_chart_initial_view.setHtml(default_html)
        else:
            self.industry_chart_initial_text.setPlainText(t_gui("点击此Tab开始计算趋势图表"))
        
        # 默认显示初始页面
        self.industry_chart_stacked_widget.setCurrentIndex(0)
        
        widget.setLayout(layout)
        return widget
    
    def create_industry_chart_loading_page(self):
        """创建行业趋势图表等待页面 - 按迷你投资大师风格设计"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addSpacing(30)
        
        # 主要内容区域
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 30px;
            }
        """)
        content_layout = QVBoxLayout()
        
        # 旋转图标 - 使用定时器实现旋转动画
        self.industry_loading_icon = QLabel("")
        self.industry_loading_icon.setFont(QFont(get_cross_platform_font(), 36))
        self.industry_loading_icon.setAlignment(Qt.AlignCenter)
        self.industry_loading_icon.setStyleSheet("color: #0078d4; margin-bottom: 20px;")
        
        # 创建旋转动画
        from PyQt5.QtCore import QTimer
        self.industry_loading_timer = QTimer()
        self.industry_loading_timer.timeout.connect(self.rotate_industry_loading_icon)
        self.industry_loading_rotation = 0
        
        # 标题
        title_label = QLabel("🔄 正在计算行业趋势图表...")
        title_label.setFont(QFont(get_cross_platform_font(), 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #0078d4; margin-bottom: 15px;")
        
        # 描述信息
        desc_label = QLabel("正在分析行业数据，请稍候...\n\n• 获取行业股票数据\n• 计算加权平均值\n• 生成趋势图表")
        desc_label.setFont(QFont(get_cross_platform_font(), 12))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; line-height: 1.6;")
        desc_label.setWordWrap(True)
        
        # 进度指示器
        progress_label = QLabel("⚡ 数据处理中...")
        progress_label.setFont(QFont(get_cross_platform_font(), 11))
        progress_label.setAlignment(Qt.AlignCenter)
        progress_label.setStyleSheet("color: #ffc107; margin-top: 20px;")
        
        content_layout.addWidget(self.industry_loading_icon)
        content_layout.addWidget(title_label)
        content_layout.addWidget(desc_label)
        content_layout.addWidget(progress_label)
        
        content_frame.setLayout(content_layout)
        layout.addWidget(content_frame)
        layout.addSpacing(30)
        
        widget.setLayout(layout)
        return widget
    
    def rotate_industry_loading_icon(self):
        """旋转行业趋势图表等待页面的图标"""
        try:
            self.industry_loading_rotation = (self.industry_loading_rotation + 15) % 360
            # 使用transform来旋转图标（虽然QLabel不直接支持，但可以通过样式实现视觉效果）
            # 这里我们改变图标内容来创建旋转效果
            icons = ["", "", "📉", "💹", "", "", "📉", "💹"]
            icon_index = (self.industry_loading_rotation // 45) % len(icons)
            self.industry_loading_icon.setText(icons[icon_index])
        except Exception as e:
            print(f"旋转图标失败: {e}")
    
    def start_industry_loading_animation(self):
        """开始行业趋势图表等待动画"""
        if hasattr(self, 'industry_loading_timer'):
            self.industry_loading_timer.start(200)  # 每200ms更新一次
    
    def stop_industry_loading_animation(self):
        """停止行业趋势图表等待动画"""
        if hasattr(self, 'industry_loading_timer'):
            self.industry_loading_timer.stop()
    

    

    

    

    

    

    

    

    
    def create_industry_ai_analysis_tab(self):
        """创建行业AI分析Tab - 复制个股AI分析的样式和逻辑"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.industry_ai_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.industry_ai_button_page = self.create_industry_ai_button_page()
        self.industry_ai_stacked_widget.addWidget(self.industry_ai_button_page)
        
        # 第2页：分析结果页面
        self.industry_ai_result_page = self.create_industry_ai_result_page()
        self.industry_ai_stacked_widget.addWidget(self.industry_ai_result_page)
        
        # 默认显示第1页
        self.industry_ai_stacked_widget.setCurrentIndex(0)
        
        return self.industry_ai_stacked_widget
    
    def create_industry_ai_button_page(self):
        """创建行业AI分析按钮页面（第1页）- 复制个股AI分析的样式"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addStretch(1)
        
        # 主标题
        title_label = QLabel(t_gui("行业AI智能分析"))
        title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #007bff; margin-bottom: 15px;")
        
        # 描述文字
        desc_label = QLabel(t_gui("industry_ai_analysis_desc"))
        desc_label.setFont(QFont(get_cross_platform_font(), 11))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        
        # 分析按钮
        self.industry_ai_analyze_btn = QPushButton(t_gui("开始AI分析"))
        self.industry_ai_analyze_btn.setFont(QFont(get_cross_platform_font(), 12, QFont.Bold))
        self.industry_ai_analyze_btn.setFixedHeight(45)
        self.industry_ai_analyze_btn.setFixedWidth(180)
        self.industry_ai_analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #007bff, stop: 1 #0056b3);
                color: white;
                border: none;
                border-radius: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #0056b3, stop: 1 #004494);
            }
            QPushButton:pressed {
                background: #004494;
            }
            QPushButton:disabled {
                background: #cccccc;
                color: #666666;
            }
        """)
        self.industry_ai_analyze_btn.clicked.connect(self.perform_industry_ai_analysis)
        
        # 状态标签
        self.industry_ai_status_label = QLabel("")
        self.industry_ai_status_label.setFont(QFont(get_cross_platform_font(), 10))
        self.industry_ai_status_label.setAlignment(Qt.AlignCenter)
        self.industry_ai_status_label.setStyleSheet("color: #28a745; margin-top: 15px;")
        
        # 布局
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        
        # 按钮居中布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.industry_ai_analyze_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addWidget(self.industry_ai_status_label)
        layout.addStretch(2)
        
        widget.setLayout(layout)
        return widget
    
    def create_industry_ai_result_page(self):
        """创建行业AI分析结果页面（第2页）- 复制个股AI分析的样式"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # AI分析结果显示区域 - 使用WebEngineView显示HTML报告
        if WEBENGINE_AVAILABLE and QWebEngineView:
            # 使用WebView显示HTML报告
            self.industry_ai_result_browser = QWebEngineView()
            self.industry_ai_result_browser.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.industry_ai_result_browser = QTextEdit()
            self.industry_ai_result_browser.setFont(QFont(get_cross_platform_font(), 11))
            self.industry_ai_result_browser.setReadOnly(True)
        self.industry_ai_result_browser.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                    padding: 0px;
                line-height: 1.6;
            }
        """)
        # 设置初始HTML内容
        initial_html = f"""
        <div style="text-align: center; margin-top: 50px; color: #666;">
            <h3 style="color: #007bff;">{t_gui(" 行业AI分析")}</h3>
            <p>{t_gui("AI分析结果将在这里显示...")}</p>
            <p style="font-size: 12px; color: #999;">{t_gui("click_start_ai_analysis_button")}</p>
        </div>
        """
        self.set_industry_ai_html(initial_html)
        
        layout.addWidget(self.industry_ai_result_browser)
        widget.setLayout(layout)
        return widget
        
    def create_stock_analysis_page(self):
        """创建个股分析页面 - 添加搜索功能，美化样式"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 标题 - 增大字体与行业分析一致
        self.stock_title_label = QLabel(t_gui('stock_trend_analysis'))
        self.stock_title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))  # 与行业分析标题字体一致
        self.stock_title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        self.stock_title_label.setTextFormat(Qt.RichText)  # 支持HTML格式
        
        # 个股查询区域 - 移植自旧版main_window.py
        search_frame = QWidget()
        search_frame.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(8, 6, 8, 6)  # 减少边距从10,8到8,6
        
        # 查询标签 - 增大字体
        search_label = QLabel(t_gui('stock_query_label'))
        search_label.setFont(QFont(get_cross_platform_font(), 13, QFont.Bold))  # 增大字体
        search_label.setStyleSheet("color: #495057; background: transparent; border: none; padding: 0;")
        
        # 输入框 - 增大字体
        from PyQt5.QtWidgets import QLineEdit
        self.stock_search_input = QLineEdit()
        self.stock_search_input.setPlaceholderText(t_gui('stock_search_placeholder'))
        self.stock_search_input.setFont(QFont(get_cross_platform_font(), 12))  # 增大字体
        self.stock_search_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
                color: #495057;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #6c757d;
            }
        """)
        self.stock_search_input.setMaximumWidth(200)
        
        # 查询按钮 - 增大字体
        self.stock_search_btn = QPushButton(t_gui('stock_query_btn'))
        self.stock_search_btn.setFont(QFont(get_cross_platform_font(), 12))
        self.stock_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.stock_search_btn.clicked.connect(self.search_and_analyze_stock)
        
        # 添加到搜索布局
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.stock_search_input)
        search_layout.addWidget(self.stock_search_btn)
        search_layout.addStretch()  # 添加弹性空间
        search_frame.setLayout(search_layout)
        
        # Tab控件 - 只保留两个区域：详细分析和趋势图表
        from PyQt5.QtWidgets import QTabWidget
        self.stock_tab_widget = QTabWidget()
        self.stock_tab_widget.setFont(QFont(get_cross_platform_font(), 10))
        
        # 连接Tab切换事件，用于AI分析自动显示缓存
        self.stock_tab_widget.currentChanged.connect(self.on_stock_tab_changed)
        self.stock_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #007bff;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)

        # Tab 1: 详细分析（含核心指标）
        self.detail_tab = self.create_detail_tab()
        self.stock_tab_widget.addTab(self.detail_tab, t_gui("📋_详细分析"))
        
        # Tab 2/3/4: 中国市场专属Tab（初始创建，可见性稍后由update_cn_market_tabs_visibility控制）
        self.stock_extra_tabs = []
        
        # 始终创建这些Tab，但可见性由市场类型决定
        extra_tabs = [
            ("html/智能个股分析.html", t_gui("个股洞察")),
            ("html/多空博弈大师版.html", t_gui("多空博弈")),
            ("html/逐笔分析.html", t_gui("逐笔分析"))
        ]
        for html_file, tab_title in extra_tabs:
            tab_widget, view, html_path = self.create_stock_html_tab(html_file)
            index = self.stock_tab_widget.addTab(tab_widget, tab_title)
            self.stock_extra_tabs.append((index, view, html_path))
        
        # 默认隐藏这些Tab，等待update_cn_market_tabs_visibility更新可见性
        for tab_index, _, _ in self.stock_extra_tabs:
            self.stock_tab_widget.setTabVisible(tab_index, False)
        
        # Tab 5: 迷你投资大师
        self.mini_master_tab = self.create_mini_master_tab()
        self.stock_tab_widget.addTab(self.mini_master_tab, t_gui("迷你投资大师"))
        
        # Tab 6: 趋势图表
        self.chart_tab = self.create_chart_tab()
        self.stock_tab_widget.addTab(self.chart_tab, t_gui("趋势图表"))
        
        # Tab 7: AI技术分析师
        self.technical_ai_tab = self.create_technical_ai_tab()
        self.stock_tab_widget.addTab(self.technical_ai_tab, t_gui("AI技术分析师"))
        
        # Tab 8: AI精选投资大师分析
        self.master_ai_tab = self.create_master_ai_tab()
        self.stock_tab_widget.addTab(self.master_ai_tab, t_gui("AI精选投资大师分析"))
        
        main_layout.addWidget(self.stock_title_label)
        main_layout.addWidget(search_frame)
        main_layout.addWidget(self.stock_tab_widget)
        
        widget.setLayout(main_layout)
        return widget
    
    def create_stock_html_tab(self, relative_path):
        """创建个股详情额外HTML Tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        from utils.path_helper import get_base_path
        base_path = Path(get_base_path())
        html_path = base_path / relative_path
        if not html_path.exists():
            alt_path = project_root / relative_path
            if alt_path.exists():
                html_path = alt_path
            else:
                print(f"HTML文件未找到: {html_path} 或 {alt_path}")
        
        if WEBENGINE_AVAILABLE and QWebEngineView:
            view = QWebEngineView()
            try:
                settings = view.settings()
                settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            except Exception as e:
                print(f"配置个股WebEngine设置时出错: {e}")
            view.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background: white;
                }
            """)
            layout.addWidget(view)
            widget.setLayout(layout)
            # 不在这里加载HTML，而是在Tab切换时加载（带股票代码参数）
            # 先显示一个提示信息
            view.setHtml(f"<div style='padding:20px;font-family:{get_cross_platform_font_family()};color:#666;text-align:center;'>请先查询股票，然后切换到此Tab查看分析</div>")
            return widget, view, html_path
        else:
            view = QTextEdit()
            view.setReadOnly(True)
            view.setFont(QFont(get_cross_platform_font(), 11))
            view.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 12px;
                }
            """)
            # 不在这里加载HTML，而是在Tab切换时加载（带股票代码参数）
            view.setPlainText("请先查询股票，然后切换到此Tab查看分析")
            layout.addWidget(view)
            widget.setLayout(layout)
            return widget, view, html_path
        
    def create_chart_tab(self):
        """创建趋势图表Tab - 使用WebView显示HTML图表，集成38天量价走势"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 使用WebView显示HTML图表
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            self.chart_webview = QWebEngineView()
            self.chart_webview.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    background-color: white;
                }
            """)
            
            # 设置默认HTML内容
            default_html = f"""
            <!DOCTYPE html>
            <html lang="{self._get_html_lang()}">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{t_gui('waiting_stock_title')}</title>
                <style>
                    body {{
                        font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                        margin: 0;
                        padding: 40px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    
                    .placeholder {{
                        background: white;
                        border-radius: 15px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        padding: 60px;
                        text-align: center;
                        max-width: 500px;
                    }}
                    
                    .icon {{
                        font-size: 48px;
                        margin-bottom: 20px;
                    }}
                    
                    .title {{
                        color: #2c3e50;
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 15px;
                    }}
                    
                    .description {{
                        color: #6c757d;
                        font-size: 16px;
                        line-height: 1.6;
                    }}
                </style>
            </head>
            <body>
                <div class="placeholder">
                    <div class="icon"></div>
                    <div class="title">{t_gui('select_stock_to_view_charts')}</div>
                    <div class="description">
                        {t_gui('charts_description_will_show')}<br/>
                        • {t_gui('volume_price_chart')}<br/>
                        • {t_gui('rating_trend_analysis')}<br/>
                        • {t_gui('technical_indicator_analysis')}<br/>
                        • {t_gui('investment_recommendations')}
                    </div>
                </div>
            </body>
            </html>
            """
            self.chart_webview.setHtml(default_html)
            layout.addWidget(self.chart_webview)
            
        except ImportError:
            # 如果WebView不可用，回退到QTextEdit
            self.chart_text = QTextEdit()
            self.chart_text.setFont(QFont(get_cross_platform_font(), 12))
            self.chart_text.setReadOnly(True)
            self.chart_text.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 15px;
                    line-height: 1.6;
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                }
            """)
            self.chart_text.setPlainText(t_gui("请选择股票查看趋势图表"))
            layout.addWidget(self.chart_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_technical_ai_tab(self):
        """创建AI技术分析师Tab - 直接执行技术面分析"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.technical_ai_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.technical_ai_button_page = self.create_technical_ai_button_page()
        self.technical_ai_stacked_widget.addWidget(self.technical_ai_button_page)
        
        # 第2页：分析结果页面
        self.technical_ai_result_page = self.create_technical_ai_result_page()
        self.technical_ai_stacked_widget.addWidget(self.technical_ai_result_page)
        
        return self.technical_ai_stacked_widget
    
    def create_master_ai_tab(self):
        """创建AI投资大师分析Tab - 直接执行投资大师分析"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.master_ai_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.master_ai_button_page = self.create_master_ai_button_page()
        self.master_ai_stacked_widget.addWidget(self.master_ai_button_page)
        
        # 第2页：分析结果页面
        self.master_ai_result_page = self.create_master_ai_result_page()
        self.master_ai_stacked_widget.addWidget(self.master_ai_result_page)
        
        return self.master_ai_stacked_widget
    
    def create_technical_ai_button_page(self):
        """创建AI技术分析师按钮页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addStretch(1)
        
        # 主标题
        title_label = QLabel(" AI技术分析师")
        title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #007bff; margin-bottom: 15px;")
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel(t_gui("专业的技术面分析，基于技术指标和图表模式"))
        subtitle_label.setFont(QFont(get_cross_platform_font(), 12))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        layout.addWidget(subtitle_label)
        
        # 分析按钮
        self.technical_ai_analyze_btn = QPushButton(" 开始技术面AI分析")
        self.technical_ai_analyze_btn.setFont(QFont(get_cross_platform_font(), 14, QFont.Bold))
        self.technical_ai_analyze_btn.setFixedSize(300, 60)
        self.technical_ai_analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #007bff, stop:1 #0056b3);
                border: none;
                border-radius: 30px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #0056b3, stop:1 #004085);
            }
            QPushButton:pressed {
                background: #004085;
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.technical_ai_analyze_btn.clicked.connect(self.start_technical_analysis)
        
        # 居中按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.technical_ai_analyze_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 状态标签
        self.technical_ai_status_label = QLabel("")
        self.technical_ai_status_label.setAlignment(Qt.AlignCenter)
        self.technical_ai_status_label.setStyleSheet("color: #666; margin-top: 20px;")
        layout.addWidget(self.technical_ai_status_label)
        
        # 添加底部空间
        layout.addStretch(2)
        
        widget.setLayout(layout)
        return widget
    
    def create_technical_ai_result_page(self):
        """创建AI技术分析师结果页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # AI分析结果显示区域 - 使用WebEngineView显示HTML报告
        if WEBENGINE_AVAILABLE and QWebEngineView:
            # 使用WebView显示HTML报告
            self.technical_ai_result_browser = QWebEngineView()
            self.technical_ai_result_browser.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: white;
                }
            """)
            # 设置初始HTML内容
            initial_html = f"""
            <div style="text-align: center; margin-top: 50px; color: #666;">
                <h3 style="color: #007bff;"> AI技术分析师</h3>
                <p>技术面分析结果将在这里显示...</p>
                <p style="font-size: 12px; color: #999;">点击"开始技术面AI分析"按钮开始分析</p>
            </div>
            """
            self.technical_ai_result_browser.setHtml(initial_html)
            layout.addWidget(self.technical_ai_result_browser)
        else:
            # WebEngine不可用，使用文本显示
            self.technical_ai_result_text = QTextBrowser()
            self.technical_ai_result_text.setStyleSheet("""
                QTextBrowser {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: white;
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                    padding: 15px;
                }
            """)
            self.technical_ai_result_text.setHtml("""
                <div style="text-align: center; margin-top: 50px; color: #666;">
                    <h3 style="color: #007bff;"> AI技术分析师</h3>
                    <p>技术面分析结果将在这里显示...</p>
                    <p style="font-size: 12px; color: #999;">点击"开始技术面AI分析"按钮开始分析</p>
                </div>
            """)
            layout.addWidget(self.technical_ai_result_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_master_ai_button_page(self):
        """创建AI投资大师分析按钮页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addStretch(1)
        
        # 主标题
        title_label = QLabel("AI精选投资大师分析")
        title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #dc3545; margin-bottom: 15px;")
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel(t_gui("精选世界级投资大师的智慧，基于投资策略和风险管理"))
        subtitle_label.setFont(QFont(get_cross_platform_font(), 12))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        layout.addWidget(subtitle_label)
        
        # 分析按钮
        self.master_ai_analyze_btn = QPushButton(" 开始投资大师AI分析")
        self.master_ai_analyze_btn.setFont(QFont(get_cross_platform_font(), 14, QFont.Bold))
        self.master_ai_analyze_btn.setFixedSize(300, 60)
        self.master_ai_analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #dc3545, stop:1 #c82333);
                border: none;
                border-radius: 30px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #c82333, stop:1 #bd2130);
            }
            QPushButton:pressed {
                background: #bd2130;
            }
            QPushButton:disabled {
                background: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.master_ai_analyze_btn.clicked.connect(self.start_master_analysis)
        
        # 居中按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.master_ai_analyze_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 状态标签
        self.master_ai_status_label = QLabel("")
        self.master_ai_status_label.setAlignment(Qt.AlignCenter)
        self.master_ai_status_label.setStyleSheet("color: #666; margin-top: 20px;")
        layout.addWidget(self.master_ai_status_label)
        
        # 添加底部空间
        layout.addStretch(2)
        
        widget.setLayout(layout)
        return widget
    
    def create_master_ai_result_page(self):
        """创建AI投资大师分析结果页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # AI分析结果显示区域 - 使用WebEngineView显示HTML报告
        if WEBENGINE_AVAILABLE and QWebEngineView:
            # 使用WebView显示HTML报告
            self.master_ai_result_browser = QWebEngineView()
            self.master_ai_result_browser.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: white;
                }
            """)
            # 设置初始HTML内容
            initial_html = f"""
            <div style="text-align: center; margin-top: 50px; color: #666;">
                <h3 style="color: #dc3545;">AI精选投资大师分析</h3>
                <p>精选投资大师分析结果将在这里显示...</p>
                <p style="font-size: 12px; color: #999;">点击"开始投资大师AI分析"按钮开始分析</p>
            </div>
            """
            self.master_ai_result_browser.setHtml(initial_html)
            layout.addWidget(self.master_ai_result_browser)
        else:
            # WebEngine不可用，使用文本显示
            self.master_ai_result_text = QTextBrowser()
            self.master_ai_result_text.setStyleSheet("""
                QTextBrowser {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: white;
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                    padding: 15px;
                }
            """)
            self.master_ai_result_text.setHtml("""
                <div style="text-align: center; margin-top: 50px; color: #666;">
                    <h3 style="color: #dc3545;">AI精选投资大师分析</h3>
                    <p>精选投资大师分析结果将在这里显示...</p>
                    <p style="font-size: 12px; color: #999;">点击"开始投资大师AI分析"按钮开始分析</p>
                </div>
            """)
            layout.addWidget(self.master_ai_result_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_technical_analysis_widget(self):
        """创建技术面分析师Widget"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.technical_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.technical_button_page = self.create_technical_button_page()
        self.technical_stacked_widget.addWidget(self.technical_button_page)
        
        # 第2页：分析结果页面
        self.technical_result_page = self.create_technical_result_page()
        self.technical_stacked_widget.addWidget(self.technical_result_page)
        
        # 默认显示第1页
        self.technical_stacked_widget.setCurrentIndex(0)
        
        return self.technical_stacked_widget
    
    def create_master_analysis_widget(self):
        """创建投资大师分析Widget"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.master_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.master_button_page = self.create_master_button_page()
        self.master_stacked_widget.addWidget(self.master_button_page)
        
        # 第2页：分析结果页面
        self.master_result_page = self.create_master_result_page()
        self.master_stacked_widget.addWidget(self.master_result_page)
        
        # 默认显示第1页
        self.master_stacked_widget.setCurrentIndex(0)
        
        return self.master_stacked_widget
    
    def create_technical_button_page(self):
        """创建技术面分析师按钮页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addSpacing(10)
        
        # 主要内容区域
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 30px;
            }
        """)
        content_layout = QVBoxLayout()
        
        # 图标和标题
        icon_label = QLabel("🔧")
        icon_label.setFont(QFont(get_cross_platform_font(), 28))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #007bff; margin-bottom: 10px;")
        
        title_label = QLabel(t_gui("技术面分析师"))
        title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #007bff; margin-bottom: 10px;")
        
        # 分析说明
        desc_label = QLabel(t_gui("基于RTSI指数、30天评级趋势、行业TMA状况和大盘情绪，为您提供专业的技术分析建议"))
        desc_label.setFont(QFont(get_cross_platform_font(), 11))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        
        # 分析按钮
        self.technical_analyze_btn = QPushButton(" 开始技术面分析")
        self.technical_analyze_btn.setFont(QFont(get_cross_platform_font(), 12, QFont.Bold))
        self.technical_analyze_btn.setFixedHeight(45)
        self.technical_analyze_btn.setFixedWidth(200)
        self.technical_analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.technical_analyze_btn.clicked.connect(self.start_technical_analysis)
        
        # 状态标签
        self.technical_status_label = QLabel("")
        self.technical_status_label.setFont(QFont(get_cross_platform_font(), 10))
        self.technical_status_label.setAlignment(Qt.AlignCenter)
        self.technical_status_label.setStyleSheet("color: #ffc107; margin-top: 10px;")
        
        content_layout.addWidget(icon_label)
        content_layout.addWidget(title_label)
        content_layout.addWidget(desc_label)
        
        # 按钮居中布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.technical_analyze_btn)
        button_layout.addStretch()
        content_layout.addLayout(button_layout)
        
        content_layout.addWidget(self.technical_status_label)
        
        content_frame.setLayout(content_layout)
        layout.addWidget(content_frame)
        layout.addSpacing(10)
        
        widget.setLayout(layout)
        return widget
    
    def create_master_button_page(self):
        """创建投资大师分析按钮页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addSpacing(10)
        
        # 主要内容区域
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 30px;
            }
        """)
        content_layout = QVBoxLayout()
        
        # 图标和标题
        icon_label = QLabel("")
        icon_label.setFont(QFont(get_cross_platform_font(), 28))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #28a745; margin-bottom: 10px;")
        
        title_label = QLabel(t_gui("投资大师分析"))
        title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #28a745; margin-bottom: 10px;")
        
        # 分析说明
        desc_label = QLabel(t_gui("融合巴菲特、彼得林奇、格雷厄姆等投资大师策略，AI模拟大师们的投资思路和评分"))
        desc_label.setFont(QFont(get_cross_platform_font(), 11))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        
        # 分析按钮
        self.master_analyze_btn = QPushButton("开始投资大师分析")
        self.master_analyze_btn.setFont(QFont(get_cross_platform_font(), 12, QFont.Bold))
        self.master_analyze_btn.setFixedHeight(45)
        self.master_analyze_btn.setFixedWidth(200)
        self.master_analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.master_analyze_btn.clicked.connect(self.start_master_analysis)
        
        # 状态标签
        self.master_status_label = QLabel("")
        self.master_status_label.setFont(QFont(get_cross_platform_font(), 10))
        self.master_status_label.setAlignment(Qt.AlignCenter)
        self.master_status_label.setStyleSheet("color: #ffc107; margin-top: 10px;")
        
        content_layout.addWidget(icon_label)
        content_layout.addWidget(title_label)
        content_layout.addWidget(desc_label)
        
        # 按钮居中布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.master_analyze_btn)
        button_layout.addStretch()
        content_layout.addLayout(button_layout)
        
        content_layout.addWidget(self.master_status_label)
        
        content_frame.setLayout(content_layout)
        layout.addWidget(content_frame)
        layout.addSpacing(10)
        
        widget.setLayout(layout)
        return widget
    
    def create_technical_result_page(self):
        """创建技术面分析结果页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 技术面分析结果显示区域
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.technical_result_browser = QWebEngineView()
            self.technical_result_browser.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.technical_result_browser = QTextEdit()
            self.technical_result_browser.setFont(QFont(get_cross_platform_font(), 11))
            self.technical_result_browser.setReadOnly(True)
            self.technical_result_browser.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 15px;
                    line-height: 1.6;
                }
            """)
        
        layout.addWidget(self.technical_result_browser)
        widget.setLayout(layout)
        return widget
    
    def create_master_result_page(self):
        """创建投资大师分析结果页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 投资大师分析结果显示区域
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.master_result_browser = QWebEngineView()
            self.master_result_browser.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.master_result_browser = QTextEdit()
            self.master_result_browser.setFont(QFont(get_cross_platform_font(), 11))
            self.master_result_browser.setReadOnly(True)
            self.master_result_browser.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 15px;
                    line-height: 1.6;
                }
            """)
        
        layout.addWidget(self.master_result_browser)
        widget.setLayout(layout)
        return widget
    
    def create_ai_button_page(self):
        """创建AI分析按钮页面（第1页）"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)  # 减少边距从20到15
        
        # 添加少量顶部空间
        layout.addSpacing(10)  # 减小顶部空间
        
        # 主要内容区域
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                padding: 30px;
            }
        """)
        content_layout = QVBoxLayout()
        
        # AI图标和标题
        icon_label = QLabel("")
        icon_label.setFont(QFont(get_cross_platform_font(), 28))  # 进一步减小字体大小
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #0078d4; margin-bottom: 10px;")
        
        title_label = QLabel(t_gui("AI智能股票分析"))
        title_label.setFont(QFont(get_cross_platform_font(), 16, QFont.Bold))  # 减小字体大小
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #0078d4; margin-bottom: 10px;")
        
        # 分析说明
        desc_label = QLabel(t_gui("基于RTSI指数_30天评级趋势_行业TMA状况和大盘情绪_为您提供专业的投资操作建议"))
        desc_label.setFont(QFont(get_cross_platform_font(), 11))  # 减小字体大小
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        
        # 分析按钮
        self.stock_ai_analyze_btn = QPushButton(t_gui("开始AI分析"))
        self.stock_ai_analyze_btn.setFont(QFont(get_cross_platform_font(), 12, QFont.Bold))  # 减小字体
        self.stock_ai_analyze_btn.setFixedHeight(45)  # 减小高度
        self.stock_ai_analyze_btn.setFixedWidth(180)  # 减小宽度
        self.stock_ai_analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #f8f9fa;
            }
        """)
        self.stock_ai_analyze_btn.clicked.connect(self.start_stock_ai_analysis)
        
        # 状态标签
        self.ai_status_label = QLabel("")
        self.ai_status_label.setFont(QFont(get_cross_platform_font(), 10))  # 减小字体
        self.ai_status_label.setAlignment(Qt.AlignCenter)
        self.ai_status_label.setStyleSheet("color: #ffc107; margin-top: 10px;")
        
        # 删除分析特色说明以减小Tab高度
        
        content_layout.addWidget(icon_label)
        content_layout.addWidget(title_label)
        content_layout.addWidget(desc_label)
        
        # 按钮居中布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.stock_ai_analyze_btn)
        button_layout.addStretch()
        content_layout.addLayout(button_layout)
        
        # 只保留状态标签，删除特色说明以减小高度
        content_layout.addWidget(self.ai_status_label)
        
        content_frame.setLayout(content_layout)
        layout.addWidget(content_frame)
        layout.addSpacing(10)  # 底部固定空间，减小高度
        
        widget.setLayout(layout)
        return widget
    
    def create_ai_result_page(self):
        """创建AI分析结果页面（第2页）"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # AI分析结果显示区域 - 使用WebEngineView
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.stock_ai_result_browser = QWebEngineView()
            self.stock_ai_result_browser.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.stock_ai_result_browser = QTextEdit()
            self.stock_ai_result_browser.setFont(QFont(get_cross_platform_font(), 11))
            self.stock_ai_result_browser.setReadOnly(True)
        self.stock_ai_result_browser.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: #333333;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 15px;
                line-height: 1.6;
            }
        """)
        
        layout.addWidget(self.stock_ai_result_browser)
        widget.setLayout(layout)
        return widget
    
    def create_mini_master_tab(self):
        """创建迷你投资大师Tab - 采用2页方式（改进版）"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.mini_master_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.mini_master_button_page = self.create_mini_master_button_page()
        self.mini_master_stacked_widget.addWidget(self.mini_master_button_page)
        
        # 第2页：分析结果页面
        self.mini_master_result_page = self.create_mini_master_result_page()
        self.mini_master_stacked_widget.addWidget(self.mini_master_result_page)
        
        # 默认显示第1页
        self.mini_master_stacked_widget.setCurrentIndex(0)
        
        return self.mini_master_stacked_widget
    
    def create_mini_master_button_page(self):
        """创建迷你投资大师分析按钮页面（第1页）- 简洁版"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # 不使用边框，直接设置背景
        widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #ffffff);
            }
        """)
        
        # 投资大师图标
        icon_label = QLabel("💼")
        icon_label.setFont(QFont(get_cross_platform_font(), 48))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("margin-bottom: 10px;")
        
        # 标题
        title_label = QLabel("迷你投资大师")
        title_label.setFont(QFont(get_cross_platform_font(), 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        
        # 副标题
        subtitle_label = QLabel("AI驱动的智能投资分析系统")
        subtitle_label.setFont(QFont(get_cross_platform_font(), 12))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 15px;")
        
        # 功能特性列表（简化版）
        features_text = QLabel(
            " 技术指标分析 ·  资金流向追踪\n"
            " 大师策略融合 ·  AI智能评分"
        )
        features_text.setFont(QFont(get_cross_platform_font(), 11))
        features_text.setAlignment(Qt.AlignCenter)
        features_text.setStyleSheet("""
            color: #5a6c7d;
            padding: 15px;
            line-height: 1.8;
        """)
        features_text.setWordWrap(True)
        
        # 分析按钮
        self.mini_master_analyze_btn = QPushButton(" 开始深度分析")
        self.mini_master_analyze_btn.setFont(QFont(get_cross_platform_font(), 13, QFont.Bold))
        self.mini_master_analyze_btn.setFixedHeight(50)
        self.mini_master_analyze_btn.setMinimumWidth(200)
        self.mini_master_analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 25px;
                padding: 15px 40px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #764ba2, stop:1 #667eea);
            }
            QPushButton:pressed {
                background: #5a3d7a;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.mini_master_analyze_btn.clicked.connect(self.start_mini_master_analysis)
        
        # 状态标签
        self.mini_master_status_label = QLabel("")
        self.mini_master_status_label.setFont(QFont(get_cross_platform_font(), 10))
        self.mini_master_status_label.setAlignment(Qt.AlignCenter)
        self.mini_master_status_label.setStyleSheet("color: #e74c3c; margin-top: 10px;")
        
        # 提示信息
        hint_label = QLabel(" 提示：请先在左侧选择或搜索股票")
        hint_label.setFont(QFont(get_cross_platform_font(), 9))
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("color: #95a5a6; margin-top: 5px;")
        
        # 添加所有组件到主布局
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addSpacing(20)
        layout.addWidget(features_text)
        layout.addSpacing(25)
        
        # 按钮居中布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.mini_master_analyze_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addWidget(self.mini_master_status_label)
        layout.addWidget(hint_label)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_mini_master_result_page(self):
        """创建迷你投资大师分析结果页面（第2页）"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 使用QWebEngineView显示HTML报告
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            self.mini_master_result_browser = QWebEngineView()
            self.mini_master_result_browser.setStyleSheet("""
                QWebEngineView {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                }
            """)
        except ImportError:
            # 如果没有QWebEngineView，使用QTextEdit作为备选
            from PyQt5.QtWidgets import QTextEdit
            self.mini_master_result_browser = QTextEdit()
            self.mini_master_result_browser.setFont(QFont(get_cross_platform_font(), 11))
            self.mini_master_result_browser.setReadOnly(True)
            self.mini_master_result_browser.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 15px;
                    line-height: 1.6;
                }
            """)
        
        layout.addWidget(self.mini_master_result_browser)
        widget.setLayout(layout)
        return widget
        
    def create_detail_tab(self):
        """创建详细分析Tab - 合并核心指标和详细分析，美化样式"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 减少边距从10到5
        
        # 详细分析文本区域（包含核心指标） - 使用WebEngineView
        if WEBENGINE_AVAILABLE and QWebEngineView:
            self.stock_detail_text = QWebEngineView()
            self.stock_detail_text.setStyleSheet("""
                QWebEngineView {
                    border: 1px solid #ddd;
                    border-radius: 6px;
                }
            """)
        else:
            # 备选方案：使用QTextEdit
            self.stock_detail_text = QTextEdit()
            self.stock_detail_text.setFont(QFont(get_cross_platform_font(), 12))  # 增大字体提升可读性
            self.stock_detail_text.setReadOnly(True)
        self.stock_detail_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: #333333;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 15px;
                line-height: 1.6;
                font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
            }
        """)
        initial_html = f"""
        <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
            <h3 style="color: #007bff;"> 个股详细分析</h3>
            <p>{t_gui('select_stock_prompt')}</p>
        </div>
        """
        self.set_stock_detail_html(initial_html)
        
        layout.addWidget(self.stock_detail_text)
        widget.setLayout(layout)
        return widget
    
    def search_and_analyze_stock(self):
        """个股查询功能 - 增强版：支持去除前导零、文字搜索、无弹窗提示"""
        try:
            # 获取搜索关键词
            search_text = self.stock_search_input.text().strip()
            if not search_text:
                return  # 空输入直接返回，不显示警告
            
            # print(f"[调试] 搜索关键词: {search_text}")
            
            # 清空输入框
            self.stock_search_input.clear()
            
            # 尝试多种搜索策略
            found_item = self.find_stock_in_tree(search_text)
            
            if found_item:
                # 找到股票，自动选择并切换
                self.select_and_analyze_stock_item(found_item)
            else:
                # print(f"[调试] 未找到匹配项: {search_text}")
                pass
                
        except Exception as e:
            # print(f"[调试] 个股查询异常: {str(e)}")
            pass
    
    def find_stock_in_tree(self, search_text):
        """在TreeView中查找股票 - 支持多种搜索策略"""
        try:
            # 遍历TreeView找到个股列表项
            root = self.tree_widget.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                if item.data(0, Qt.UserRole) == "stock_list":
                    # 遍历股票子项
                    for j in range(item.childCount()):
                        child_item = item.child(j)
                        item_text = child_item.text(0)  # TreeView显示的完整文本
                        stored_code = child_item.data(0, Qt.UserRole + 1)  # 存储的股票代码
                        
                        # 策略1: 精确匹配存储的股票代码
                        if stored_code and str(stored_code).upper() == str(search_text).upper():
                            # print(f"[调试] 策略1匹配 - 精确代码: {stored_code}")
                            return child_item
                        
                        # 策略2: 去除前导零匹配（输入11匹配000011）
                        if stored_code and self.match_without_leading_zeros(str(stored_code), search_text):
                            # print(f"[调试] 策略2匹配 - 去除前导零: {stored_code} ← {search_text}")
                            return child_item
                        
                        # 策略3: 文字搜索（在TreeView显示文本中查找）
                        if self.match_text_search(item_text, search_text):
                            # print(f"[调试] 策略3匹配 - 文字搜索: {item_text}")
                            return child_item
            
            return None
            
        except Exception as e:
            # print(f"[调试] 搜索失败: {str(e)}")
            return None
    
    def match_without_leading_zeros(self, stored_code, search_text):
        """匹配去除前导零的股票代码"""
        try:
            # 将两个字符串都转换为数字再比较，这样会自动去除前导零
            stored_num = int(stored_code)
            search_num = int(search_text)
            return stored_num == search_num
        except (ValueError, TypeError):
            return False
    
    def match_text_search(self, item_text, search_text):
        """文字搜索匹配"""
        try:
            # 在TreeView显示文本中搜索关键词（不区分大小写）
            return search_text.lower() in item_text.lower()
        except:
            return False
    
    def select_and_analyze_stock_item(self, tree_item):
        """选择并分析TreeView中的股票项"""
        try:
            # 展开个股分析节点
            parent = tree_item.parent()
            if parent:
                parent.setExpanded(True)
            
            # 选中项目
            self.tree_widget.setCurrentItem(tree_item)
            tree_item.setSelected(True)
            self.tree_widget.scrollToItem(tree_item)
            
            # 触发点击事件，执行正常的点击处理逻辑
            self.on_tree_item_clicked(tree_item, 0)
            
            # print(f"[调试] 已选择并分析股票: {tree_item.text(0)}")
            
        except Exception as e:
            # print(f"[调试] 选择股票失败: {str(e)}")
            pass
    
    def get_all_stock_codes(self):
        """获取所有可用的股票代码 - 用于调试"""
        stock_codes = []
        try:
            root = self.tree_widget.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                if item.data(0, Qt.UserRole) == "stock_list":
                    for j in range(item.childCount()):
                        child_item = item.child(j)
                        item_code = child_item.data(0, Qt.UserRole + 1)
                        if item_code:
                            stock_codes.append(str(item_code))
        except Exception as e:
            # print(f"[调试] 获取股票代码失败: {str(e)}")
            pass
        return stock_codes
    
    def select_stock_in_tree(self, stock_code):
        """在TreeView中定位并选中指定的股票代码 - 保留兼容性"""
        found_item = self.find_stock_in_tree(stock_code)
        if found_item:
            self.select_and_analyze_stock_item(found_item)
            return True
        return False
    
    def trigger_stock_analysis_from_tree(self, stock_code):
        """触发TreeView中股票的分析"""
        try:
            if not self.analysis_results or 'analysis_results' not in self.analysis_results:
                return
            
            analysis_obj = self.analysis_results['analysis_results']
            if not hasattr(analysis_obj, 'stocks'):
                return
            
            # 查找股票数据
            for code, stock_data in analysis_obj.stocks.items():
                if str(code).upper() == str(stock_code).upper():
                    # 找到股票，触发分析
                    self.analyze_selected_stock_complete(code)
                    return
                    
        except Exception as e:
            print(f"触发股票分析失败: {str(e)}")
        
    def on_tree_item_clicked(self, item, column):
        """树形控件点击事件 - 区分主项目和子项目"""
        item_type = item.data(0, Qt.UserRole)
        
        if item_type == "ai_suggestions":
            self.content_area.setCurrentWidget(self.ai_page)
        elif item_type == "market_analysis":
            self.content_area.setCurrentWidget(self.market_page)
        elif item_type == "industry_list":
            # 主项目：显示行业分析页面
            self.content_area.setCurrentWidget(self.industry_page)
            # 显示默认提示信息
            initial_html = f"""
            <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
                <h3 style="color: #007bff;"> 行业详细分析</h3>
                <p>{t_gui("select_industry_from_left_panel")}</p>
            </div>
            """
            self.set_industry_detail_html(initial_html)
        elif item_type == "stock_list":
            # 主项目：显示个股分析页面
            self.content_area.setCurrentWidget(self.stock_page)
            # 切换到Tab1（详细分析）
            if hasattr(self, 'stock_tab_widget'):
                self.stock_tab_widget.setCurrentIndex(0)
            # 显示默认提示信息
            if hasattr(self, 'stock_detail_text'):
                initial_html = f"""
                <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
                    <h3 style="color: #007bff;"> 个股详细分析</h3>
                    <p>{t_gui("请从左侧个股列表中选择一只股票查看详细分析")}</p>
                </div>
                """
                self.set_stock_detail_html(initial_html)
            self.clear_stock_analysis()
        elif item_type and item_type.startswith("industry_"):
            # 子项目：直接显示行业详细信息
            industry_name = item_type[9:]  # 去掉 "industry_" 前缀
            self.content_area.setCurrentWidget(self.industry_page)
            self.show_industry_detail(industry_name)
        elif item_type and item_type.startswith("stock_"):
            # 子项目：直接显示股票详细信息
            stock_code = item_type[6:]  # 去掉 "stock_" 前缀
            self.content_area.setCurrentWidget(self.stock_page)
            # 切换到Tab1（详细分析）- 特别是个股分析
            if hasattr(self, 'stock_tab_widget'):
                self.stock_tab_widget.setCurrentIndex(0)
            self.analyze_selected_stock_complete(stock_code)
            
    def update_analysis_results(self, results: Dict[str, Any]):
        """更新分析结果并填充树形控件"""
        try:
            print("[update_analysis_results] 开始更新分析结果...")
            self.analysis_results = results
            
            # 提取不同格式的结果
            self.analysis_results_obj = results.get('analysis_results')  # AnalysisResults对象
            self.analysis_dict = results.get('analysis_dict', {})        # 字典格式
            
            # 检查是否包含AI分析结果
            self.ai_analysis_executed = 'ai_analysis' in results and results['ai_analysis'] is not None
            
            # 获取数据日期范围
            print("[update_analysis_results] 获取日期范围...")
            self.date_range_text = self.get_data_date_range()
            
            # 更新所有页面标题（添加日期范围）
            print("[update_analysis_results] 更新页面标题...")
            self.update_page_titles_with_date_range()
            
            # 填充树形控件的子项目
            print("[update_analysis_results] 填充树形控件...")
            self.populate_tree_items()
            
            # 更新内容页面
            print("[update_analysis_results] 更新AI建议...")
            self.update_ai_suggestions()
            
            print("[update_analysis_results] 更新市场分析...")
            self.update_market_analysis()
            
            # 更新AI按钮状态
            print("[update_analysis_results] 更新AI按钮状态...")
            self.update_ai_buttons_state()
            
            print("[update_analysis_results] 更新分析结果完成")
        except Exception as e:
            print(f"[update_analysis_results] 更新分析结果时出错: {e}")
            import traceback
            traceback.print_exc()
        
    def get_data_date_range(self) -> str:
        """获取数据文件的日期范围 - 参考main_window.py实现"""
        try:
            # 定义日期格式化函数 - 修复编码错误
            def format_date(date_str):
                try:
                    date_str = str(date_str)
                    if len(date_str) == 8:  # YYYYMMDD格式
                        year = date_str[:4]
                        month = date_str[4:6].lstrip('0') or '0'
                        day = date_str[6:8].lstrip('0') or '0'
                        # 使用安全的字符串格式化，避免locale编码错误
                        return f"{year}-{month}-{day}"
                    return date_str
                except Exception as e:
                    print(f"日期格式化错误: {e}")
                    return str(date_str)
            
            # 方法1：从结果中的直接数据源引用获取（最新方式）
            if self.analysis_results and 'data_source' in self.analysis_results:
                dataset = self.analysis_results['data_source']
                if hasattr(dataset, 'get_date_range'):
                    date_range = dataset.get_date_range()
                    if date_range and date_range[0] and date_range[1]:
                        start_date = str(date_range[0])
                        end_date = str(date_range[1])
                        formatted_start = format_date(start_date)
                        formatted_end = format_date(end_date)
                        print(f" 从直接数据源获取日期范围: {start_date} ~ {end_date}")
                        return t_gui('date_range_format', start_date=formatted_start, end_date=formatted_end)
            
            # 方法2：从分析结果对象中获取数据集信息（通过data_source属性）
            if self.analysis_results_obj and hasattr(self.analysis_results_obj, 'data_source'):
                dataset = self.analysis_results_obj.data_source
                if hasattr(dataset, 'get_date_range'):
                    date_range = dataset.get_date_range()
                    if date_range and date_range[0] and date_range[1]:
                        start_date = str(date_range[0])
                        end_date = str(date_range[1])
                        formatted_start = format_date(start_date)
                        formatted_end = format_date(end_date)
                        print(f" 从分析对象数据源获取日期范围: {start_date} ~ {end_date}")
                        return t_gui('date_range_format', start_date=formatted_start, end_date=formatted_end)
            
            # 方法3：通过metadata获取（备用方案1）
            if self.analysis_results_obj and hasattr(self.analysis_results_obj, 'data_source'):
                dataset = self.analysis_results_obj.data_source
                if hasattr(dataset, 'get_metadata'):
                    metadata = dataset.get_metadata()
                    date_range = metadata.get('date_range', (None, None))
                    if date_range[0] and date_range[1]:
                        start_date = str(date_range[0])
                        end_date = str(date_range[1])
                        formatted_start = format_date(start_date)
                        formatted_end = format_date(end_date)
                        print(f" 通过metadata获取日期范围: {start_date} ~ {end_date}")
                        return t_gui('date_range_format', start_date=formatted_start, end_date=formatted_end)
            
            # 方法4：从分析字典中获取（兼容性方案）
            if self.analysis_dict and 'metadata' in self.analysis_dict:
                metadata = self.analysis_dict['metadata']
                if 'date_range' in metadata:
                    date_range = metadata['date_range']
                    if isinstance(date_range, str) and '~' in date_range:
                        start, end = date_range.split('~')
                        start = start.strip()
                        end = end.strip()
                        print(f" 从分析字典获取日期范围: {start} ~ {end}")
                        return f"（{start}至{end}）"
            
            print(" 无法获取日期范围，使用默认值")
            return t_gui('date_range_unknown')
        except Exception as e:
            print(f" 获取日期范围失败: {e}")
            import traceback
            traceback.print_exc()
            return t_gui('date_range_unknown')
    
    def update_page_titles_with_date_range(self):
        """更新所有页面标题，添加日期范围"""
        try:
            # 生成带样式的HTML标题（主标题 + 日期范围，超过2天时红色闪烁）
            def format_title_with_date(main_title, date_range):
                # 检查日期是否超过2天
                date_color = "black"
                should_blink = False
                
                try:
                    from datetime import datetime, timedelta
                    
                    print(f" 检查日期范围: {date_range}")
                    
                    # 解析日期范围，获取结束日期
                    end_date_str = None
                    if " - " in date_range:
                        end_date_str = date_range.split(" - ")[1].strip()
                        print(f" 结束日期字符串: {end_date_str}")
                    elif "至" in date_range:
                        # 处理中文格式：（2024-7-9至2024-8-29）
                        end_date_str = date_range.split("至")[1].strip().rstrip("）")
                        print(f" 中文格式结束日期字符串: {end_date_str}")
                    else:
                        print(f" 无法识别的日期范围格式: {date_range}")
                    
                    # 解析日期格式 YYYY-MM-DD 或 YYYY-M-D
                    if end_date_str and "-" in end_date_str:
                        try:
                            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                        except ValueError:
                            # 尝试其他格式，如 YYYY-M-D
                            try:
                                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                            except ValueError:
                                # 手动解析，处理单位数月份和日期
                                parts = end_date_str.split("-")
                                if len(parts) == 3:
                                    year = int(parts[0])
                                    month = int(parts[1])
                                    day = int(parts[2])
                                    end_date = datetime(year, month, day)
                                else:
                                    raise ValueError(f"无法解析日期格式: {end_date_str}")
                        
                        # 计算与今天的差距
                        today = datetime.now()
                        days_diff = (today - end_date).days
                        print(f" 今天: {today}, 结束日期: {end_date}, 相差天数: {days_diff}")
                        
                        if days_diff > 2:
                            print(f" 需要闪烁！相差{days_diff}天")
                            date_color = "#dc3545"  # 红色
                            should_blink = True
                            # 启动闪烁定时器
                            if not hasattr(self, 'date_blink_timer'):
                                self.date_blink_timer = QTimer()
                                self.date_blink_timer.timeout.connect(self.toggle_date_blink)
                                self.date_blink_visible = True
                                print(f" 创建闪烁定时器")
                            if not self.date_blink_timer.isActive():
                                self.date_blink_timer.start(1000)  # 每1秒闪烁一次
                                print(f" 启动闪烁定时器")
                        else:
                            print(f" 不需要闪烁，相差{days_diff}天")
                                
                except Exception as e:
                    print(f"日期检查失败: {e}")
                
                # 存储闪烁状态
                self.date_should_blink = should_blink
                self.date_color = date_color
                self.main_title = main_title
                self.date_range = date_range
                
                return f"""
                <span style="color: #0078d4; font-size: 16px; font-weight: bold;">{main_title}</span>
                <span style="color: {date_color}; font-size: 14px; font-weight: normal; margin-left: 10px;">{date_range}</span>
                """
            
            # 更新AI分析页面标题
            if hasattr(self, 'ai_title_label'):
                html_title = format_title_with_date(t_gui('ai_intelligent_analysis'), self.date_range_text)
                self.ai_title_label.setText(html_title)
                self.ai_title_label.setStyleSheet("padding: 10px;")  # 移除颜色设置，使用HTML样式
            
            # 更新大盘分析页面标题
            if hasattr(self, 'market_title_label'):
                html_title = format_title_with_date(t_gui('市场情绪分析'), self.date_range_text)
                self.market_title_label.setText(html_title)
                self.market_title_label.setStyleSheet("padding: 10px;")
            
            # 更新行业分析页面标题
            if hasattr(self, 'industry_title_label'):
                html_title = format_title_with_date(t_gui('🏭_行业分析'), self.date_range_text)
                self.industry_title_label.setText(html_title)
                self.industry_title_label.setStyleSheet("padding: 10px;")
            
            # 更新个股分析页面标题
            if hasattr(self, 'stock_title_label'):
                html_title = format_title_with_date(t_gui('个股趋势分析'), self.date_range_text)
                self.stock_title_label.setText(html_title)
                self.stock_title_label.setStyleSheet("padding: 10px;")
                
        except Exception as e:
            print(f"更新页面标题失败: {e}")
    
    def toggle_date_blink(self):
        """切换日期闪烁状态"""
        if not hasattr(self, 'date_should_blink') or not self.date_should_blink:
            return
            
        # 切换可见性
        self.date_blink_visible = not self.date_blink_visible
        
        # 根据可见性设置颜色
        if self.date_blink_visible:
            date_color = self.date_color  # 红色
        else:
            date_color = "#cccccc"  # 浅灰色，闪烁效果
        
        # 更新所有标题
        html_template = f"""
        <span style="color: #0078d4; font-size: 16px; font-weight: bold;">{{}}</span>
        <span style="color: {date_color}; font-size: 14px; font-weight: normal; margin-left: 10px;">{self.date_range}</span>
        """
        
        if hasattr(self, 'ai_title_label'):
            self.ai_title_label.setText(html_template.format(t_gui('ai_intelligent_analysis')))
        if hasattr(self, 'market_title_label'):
            self.market_title_label.setText(html_template.format(t_gui('市场情绪分析')))
        if hasattr(self, 'industry_title_label'):
            self.industry_title_label.setText(html_template.format(t_gui('🏭_行业分析')))
        if hasattr(self, 'stock_title_label'):
            self.stock_title_label.setText(html_template.format(t_gui('个股趋势分析')))
    

    def get_risk_warning_html(self):
        """获取HTML格式的风险警告"""
        return """
        <div style="
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            margin: 20px 0;
            padding: 15px;
            font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
        ">
            <div style="
                display: flex;
                align-items: center;
                margin-bottom: 8px;
            ">
                <span style="
                    font-size: 16px;
                    margin-right: 8px;
                "></span>
                <strong style="
                    color: #856404;
                    font-size: 14px;
                    font-weight: bold;
                ">风险警告</strong>
            </div>
            <div style="
                color: #856404;
                font-size: 12px;
                line-height: 1.2;
                max-height: 40px;
                overflow: hidden;
            ">
                本系统所有内容均为测试数据，仅供学习和研究使用。投资有风险，决策需谨慎。
            </div>
        </div>
        """
        
    def populate_tree_items(self):
        """填充树形控件的子项目"""
        if not self.analysis_results_obj:
            return
            
        # 清除现有子项目
        self.industry_item.takeChildren()
        self.stock_item.takeChildren()
        
        # 添加行业子项目
        if hasattr(self.analysis_results_obj, 'industries'):
            industries_data = self.analysis_results_obj.industries
            # 按行业内最高RTSI排序，但指数固定第一位
            sorted_industries = []
            index_industry = None
            
            for industry_name, industry_info in industries_data.items():
                tma_value = 0
                
                if isinstance(industry_info, dict):
                    # 获取TMA值用于显示和排序
                    tma_value = industry_info.get('irsi', 0)
                    if isinstance(tma_value, dict):
                        tma_value = tma_value.get('irsi', 0)
                
                # 确保tma_value是数字
                if not isinstance(tma_value, (int, float)):
                    tma_value = 0
                
                # 检查是否是指数行业
                if industry_name == "指数":
                    index_industry = (industry_name, float(tma_value))
                else:
                    sorted_industries.append((industry_name, float(tma_value)))
            
            # 按TMA值排序（从高到低）
            sorted_industries.sort(key=lambda x: x[1], reverse=True)
            
            # 指数固定在第一位
            if index_industry:
                final_industries = [index_industry] + sorted_industries
            else:
                final_industries = sorted_industries
            
            for industry_name, tma_value in final_industries:  # 显示所有行业
                child_item = QTreeWidgetItem([f"🏢 {industry_name} (TMA: {tma_value:.1f})"])
                child_item.setData(0, Qt.UserRole, f"industry_{industry_name}")
                self.industry_item.addChild(child_item)
        
        # 添加股票子项目
        if hasattr(self.analysis_results_obj, 'stocks'):
            stocks_data = self.analysis_results_obj.stocks
            # 按股票代码从小到大排序
            sorted_stocks = []
            for stock_code, stock_info in stocks_data.items():
                rtsi_value = 0
                if isinstance(stock_info, dict):
                    rtsi_value = stock_info.get('rtsi', 0)
                    # 处理RTSI值也是字典的情况
                    if isinstance(rtsi_value, dict):
                        rtsi_value = rtsi_value.get('rtsi', 0)
                # 确保rtsi_value是数字
                if not isinstance(rtsi_value, (int, float)):
                    rtsi_value = 0
                sorted_stocks.append((stock_code, float(rtsi_value), stock_info.get('name', stock_code)))
            
            # 按股票代码排序（从小到大）
            sorted_stocks.sort(key=lambda x: x[0])
            
            for stock_code, rtsi_value, stock_name in sorted_stocks:  # 显示所有股票
                child_item = QTreeWidgetItem([f" {stock_code} {stock_name} (RTSI: {rtsi_value:.1f})"])
                child_item.setData(0, Qt.UserRole, f"stock_{stock_code}")
                child_item.setData(0, Qt.UserRole + 1, stock_code)  # 存储纯股票代码供搜索使用
                self.stock_item.addChild(child_item)
        
        # 展开树形控件
        self.tree_widget.expandAll()
        
    def update_ai_suggestions(self):
        """更新AI建议 - 改用WebView显示HTML报告"""
        if not self.analysis_results:
            return

        # 首先尝试显示HTML报告
        html_report_path = self.analysis_results.get('html_report_path', '')

        if html_report_path and Path(html_report_path).exists():
            try:
                # 保存当前HTML路径供保存按钮使用
                self.current_html_path = html_report_path
                
                # 启用保存HTML按钮
                if hasattr(self, 'save_html_btn'):
                    self.save_html_btn.setEnabled(True)
                
                # 使用WebView显示HTML报告
                if hasattr(self, 'ai_webview'):
                    file_url = QUrl.fromLocalFile(str(Path(html_report_path).absolute()))
                    self.ai_webview.load(file_url)
                    return
                else:
                    # 回退到文本显示
                    with open(html_report_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    self.ai_browser.setHtml(html_content)
                    return
            except Exception as e:
                print(f"加载HTML报告失败: {str(e)}")

        # 如果没有HTML报告，尝试生成基础HTML报告
        if 'analysis_results' in self.analysis_results:
            try:
                print("没有HTML报告，正在生成基础分析报告...")
                html_report_path = self.generate_html_report(self.analysis_results)
                if html_report_path and Path(html_report_path).exists():
                    # 更新报告路径
                    self.analysis_results['html_report_path'] = html_report_path
                    self.current_html_path = html_report_path
                    
                    # 启用保存HTML按钮
                    if hasattr(self, 'save_html_btn'):
                        self.save_html_btn.setEnabled(True)
                    
                    # 显示生成的报告
                    if hasattr(self, 'ai_webview'):
                        file_url = QUrl.fromLocalFile(str(Path(html_report_path).absolute()))
                        self.ai_webview.load(file_url)
                        return
                    else:
                        with open(html_report_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        self.ai_browser.setHtml(html_content)
                        return
            except Exception as e:
                print(f"生成基础HTML报告失败: {str(e)}")

        # 如果所有尝试都失败，显示提示信息
        no_report_html = """
        <html>
        <head>
            <meta charset="utf-8">
            <title>智能分析报告</title>
            <style>
                body { 
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; 
                    padding: 20px; 
                    text-align: center;
                    background: #f8f9fa;
                }
                .container {
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 30px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .icon { font-size: 48px; margin-bottom: 20px; }
                .title { color: #dc3545; font-size: 18px; margin-bottom: 15px; }
                .description { color: #868e96; font-size: 14px; line-height: 1.6; }
                .note { 
                    background: #fff3cd; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-top: 20px;
                    border-left: 4px solid #ffc107;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon"></div>
                <div class="title">智能分析报告</div>
                <div class="description">
                    未生成HTML分析报告，可能的原因：<br/>
                    • 分析尚未完成<br/>
                    • AI分析配置有误<br/>
                    • 系统错误
                </div>
                <div class="note">
                    <strong>解决方案：</strong><br/>
                    1. 检查 llm-api/config/user_settings.json 配置<br/>
                    2. 确保网络连接正常<br/>
                    3. 重新进行数据分析
                </div>
            </div>
        </body>
        </html>
        """
        
        if hasattr(self, 'ai_webview'):
            self.ai_webview.setHtml(no_report_html)
        else:
            self.ai_browser.setPlainText(t_gui("AI功能未执行，请检查配置"))
            
    def update_market_analysis(self):
        """更新大盘分析 - HTML富文本版本"""
        if not self.analysis_results_obj:
            self.set_market_html("<p style='color: #dc3545;'>暂无大盘分析数据</p>")
            return
            
        # 使用HTML格式的generate_market_analysis_report逻辑
        market_data = self.analysis_results_obj.market
        
        # Tab 1: 详细分析（原有内容）
        content = self.generate_market_analysis_report(market_data)
        self.set_market_html(content)
        

        
    def generate_market_analysis_report(self, market_data):
        """生成市场分析报告 - HTML富文本版本，包含多空力量对比、风险评估、市场展望"""
        try:
            # MSCI指数信息
            msci_value = market_data.get('current_msci', 0)
            
            # 市场状态判断和颜色编码（红涨绿跌，红高绿低）
            if msci_value >= 70:
                market_mood = t_gui("极度乐观")
                mood_color = "#28a745"  # 绿色-乐观/高位风险
                risk_warning = t_gui("高风险_市场可能过热_建议谨慎")
            elif msci_value >= 60:
                market_mood = t_gui("乐观")
                mood_color = "#ff6600"  # 橙色-偏乐观
                risk_warning = t_gui("⚡_中高风险_市场情绪偏乐观")
            elif msci_value >= 40:
                market_mood = t_gui("中性")
                mood_color = "#6c757d"  # 灰色-中性
                risk_warning = t_gui("中等风险_市场相对理性")
            elif msci_value >= 30:
                market_mood = t_gui("悲观")
                mood_color = "#009900"  # 深绿色-偏悲观
                risk_warning = t_gui("机会信号_市场可能接近底部")
            else:
                market_mood = t_gui("极度悲观")
                mood_color = "#dc3545"  # 红色-悲观/低位机会
                risk_warning = t_gui("重大机会_市场严重超跌")
            
            # 技术指标
            volatility = market_data.get('volatility', 0)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            trend_5d = market_data.get('trend_5d', 0)
            
            # 生成HTML格式的市场分析报告
            from datetime import datetime
            
            market_html = f"""
            <div style="font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 5px;">
                     {t_gui('market_sentiment_analysis_report')}
                </h2>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🌐 {t_gui('core_indicators')}</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('msci_market_sentiment_index')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {mood_color};"><strong>{msci_value:.2f}</strong></td></tr>
                    <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('market_sentiment')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {mood_color};"><strong>{market_mood}</strong></td></tr>
                    <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('risk_warning')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{risk_warning}</td></tr>
                </table>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('technical_indicator_analysis')}</h3>
                <ul style="margin-left: 20px;">
                    <li><strong>{t_gui('market_volatility')}:</strong> <span style="color: {'#dc3545' if volatility > 3 else '#ffc107' if volatility > 1.5 else '#28a745'};">{volatility:.2f}%</span></li>
                    <li><strong>{t_gui('volume_ratio')}:</strong> <span style="color: {'#dc3545' if volume_ratio > 1.2 else '#ffc107' if volume_ratio > 0.8 else '#28a745'};">{volume_ratio:.2f}</span></li>
                    <li><strong>{t_gui('5_day_trend')}:</strong> <span style="color: {'#dc3545' if trend_5d > 0 else '#28a745' if trend_5d < 0 else '#6c757d'};">{trend_5d:+.2f}%</span></li>
                </ul>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">⚖️ {t_gui('bull_bear_balance')}</h3>
                <ul style="margin-left: 20px;">
                    <li><strong>{t_gui('power_analysis')}:</strong> {self.analyze_bull_bear_balance(market_data)}</li>
                    <li><strong>{t_gui('historical_trend')}:</strong> {self.analyze_historical_trend(market_data)}</li>
                </ul>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('risk_assessment')}</h3>
                <ul style="margin-left: 20px;">
                    <li><strong>{t_gui('comprehensive_assessment')}:</strong> {self.assess_market_risk(msci_value, market_data.get('risk_level', t_gui('moderate_level')))}</li>
                    <li><strong>{t_gui('systemic_risk')}:</strong> {self.get_systemic_risk(msci_value)}</li>
                    <li><strong>{t_gui('liquidity_risk')}:</strong> {self.get_liquidity_risk(volume_ratio)}</li>
                </ul>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🔮 {t_gui('market_outlook')}</h3>
                <ul style="margin-left: 20px;">
                    <li><strong>{t_gui('short_term_outlook')}:</strong> {self.forecast_market_outlook(msci_value, trend_5d)}</li>
                    <li><strong>{t_gui('medium_term_trend')}:</strong> {self.get_medium_term_outlook(msci_value)}</li>
                    <li><strong>{t_gui('long_term_prospects')}:</strong> {self.get_long_term_prospect(msci_value)}</li>
                </ul>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('investment_strategy_advice')}</h3>
                <div style="background-color: #e3f2fd; border: 1px solid #2196f3; border-radius: 6px; padding: 15px; margin: 10px 0;">
                    <p style="margin: 0; line-height: 1.8;">{self.suggest_investment_strategy(msci_value, market_mood)}</p>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-top: 25px;">
                    <h4 style="color: #856404; margin-top: 0;"> {t_gui('risk_warning')}</h4>
                    <p style="color: #856404; margin-bottom: 0; font-size: 12px;">
                        {t_gui('market_analysis_reference_only')}
                    </p>
                </div>
                
                <p style="text-align: right; color: #6c757d; font-size: 12px; margin-top: 20px;">
                    {t_gui('generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
            """
            
            return market_html
            
        except Exception as e:
            return f"<p style='color: #dc3545;'>生成市场分析报告失败: {str(e)}</p>"
    

        
    # 事件处理方法已简化，因为移除了表格
        
    def show_industry_detail(self, industry_name):
        """显示行业详细信息 - HTML富文本版本"""
        if not self.analysis_results_obj:
            return
        
        # 设置当前行业名称，供AI分析使用
        self.current_industry_name = industry_name
        
        # 自动切换到Tab1（详细分析）
        if hasattr(self, 'industry_tab_widget'):
            self.industry_tab_widget.setCurrentIndex(0)  # 切换到第一个Tab（详细分析）
        
        # 更新行业AI分析Tab状态（根据内存中的缓存）
        self.update_industry_ai_tab_status(industry_name)
        
        # 显示趋势图表tab（行业评级TAB已删除）
        if hasattr(self, 'industry_chart_tab_index'):
            self.industry_tab_widget.setTabVisible(self.industry_chart_tab_index, True)
        
        # 趋势图表改为点击tab表头时才计算
        # self.update_industry_chart(industry_name)
            
        industries_data = self.analysis_results_obj.industries
        industry_info = industries_data.get(industry_name, {})
        
        if not industry_info:
            self.set_industry_detail_html(f"<p style='color: #dc3545;'>未找到行业 {industry_name} 的详细信息</p>")
            return
            
        # 基本信息处理
        tma_value = industry_info.get('irsi', 0)
        # 处理TMA值也是字典的情况
        if isinstance(tma_value, dict):
            tma_value = tma_value.get('irsi', 0)
        # 确保tma_value是数字
        if not isinstance(tma_value, (int, float)):
            tma_value = 0
        tma_value = float(tma_value)
        
        stock_count = industry_info.get('stock_count', 0)
        risk_level = self.get_industry_risk_level(tma_value)
        
        # 判断强度等级和颜色（红涨绿跌）
        if tma_value > 20:
            strength = t_gui("强势")
            strength_color = "#dc3545"  # 强势用红色（上涨）
            color_desc = "🔴"
        elif tma_value > 5:
            strength = t_gui("中性偏强")
            strength_color = "#ff6600"  # 中性偏强用橙色
            color_desc = "🟠"
        elif tma_value > -5:
            strength = t_gui("中性")
            strength_color = "#6c757d"  # 中性用灰色
            color_desc = "⚪"
        elif tma_value > -20:
            strength = t_gui("中性偏弱")
            strength_color = "#009900"  # 偏弱用深绿色
            color_desc = "🟢"
        else:
            strength = t_gui("弱势")
            strength_color = "#28a745"  # 弱势用绿色（下跌）
            color_desc = "🟢"
        
        # 获取行业龙头股票
        top_stocks = self.get_top_stocks_in_industry(industry_name, 5)
        top_stocks_html = ""
        if top_stocks:
            for i, (code, name, rtsi) in enumerate(top_stocks, 1):
                stock_color = "#dc3545" if rtsi > 60 else "#ffc107" if rtsi > 40 else "#28a745"  # 红高绿低（红涨绿跌）
                top_stocks_html += f'<tr><td style="padding: 3px 8px; border-bottom: 1px solid #eee;">{i}</td><td style="padding: 3px 8px; border-bottom: 1px solid #eee;">{code}</td><td style="padding: 3px 8px; border-bottom: 1px solid #eee;">{name}</td><td style="padding: 3px 8px; border-bottom: 1px solid #eee; color: {stock_color}; font-weight: bold;">{rtsi:.2f}</td></tr>'
        
        # 投资建议内容
        if tma_value > 20:
            advice_items = [
                t_gui("行业处于强势状态"),
                t_gui("可重点关注该行业股票"), 
                t_gui("适合积极配置")
            ]
        elif tma_value > 5:
            advice_items = [
                t_gui("行业表现较好"),
                t_gui("可适度配置"),
                t_gui("关注个股选择")
            ]
        elif tma_value > -5:
            advice_items = [
                t_gui("行业表现中性"), 
                t_gui("维持现有配置"),
                t_gui("等待明确信号")
            ]
        else:
            advice_items = [
                t_gui("行业表现较弱"),
                t_gui("建议谨慎投资"),
                t_gui("可考虑减少配置")
            ]
        
        # 生成HTML格式的详细分析
        from datetime import datetime
        
        industry_html = f"""
        <div style="font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 5px;">
                🏭 {industry_name} 详细分析
            </h2>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('core_indicators')}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('industry_name')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{industry_name}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('tma_index')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {strength_color};"><strong>{tma_value:.2f}</strong></td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('stock_count')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{stock_count}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('risk_level')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{risk_level}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('strength_level')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {strength_color};"><strong>{color_desc} {strength}</strong></td></tr>
            </table>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('industry_leading_stocks')} ({t_gui('top_5_stocks')})</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">{t_gui('ranking')}</th>
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">{t_gui('code')}</th>
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">{t_gui('name')}</th>
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">RTSI</th>
                </tr>
                {top_stocks_html if top_stocks_html else f'<tr><td colspan="4" style="padding: 8px; text-align: center; color: #6c757d;">{t_gui("no_data")}</td></tr>'}
            </table>
            

            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('technical_analysis')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('trend_status')}:</strong> {self.get_industry_trend_status(tma_value)}</li>
                <li><strong>{t_gui('market_position')}:</strong> {self.get_industry_market_position(tma_value)}</li>
                <li><strong>{t_gui('allocation_value')}:</strong> {self.get_industry_allocation_value(tma_value)}</li>
            </ul>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-top: 25px;">
                <h4 style="color: #856404; margin-top: 0;"> {t_gui('risk_warning')}</h4>
                <p style="color: #856404; margin-bottom: 0; font-size: 12px;">
                    {t_gui('analysis_for_reference_only')}
                </p>
            </div>
            
            <p style="text-align: right; color: #6c757d; font-size: 12px; margin-top: 20px;">
                {t_gui('generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        """
        
        self.set_industry_detail_html(industry_html)
        
    def show_stock_detail(self, stock_code):
        """显示股票详细信息"""
        if not self.analysis_results_obj:
            return
            
        stocks_data = self.analysis_results_obj.stocks
        stock_info = stocks_data.get(stock_code, {})
        
        if not stock_info:
            error_html = f"""
            <div style="text-align: center; margin-top: 50px; color: #dc3545; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
                <h3>[ERROR] 数据错误</h3>
                <p>{t_gui("未找到股票_stock_code_的详细信息", stock_code=stock_code)}</p>
            </div>
            """
            self.set_stock_detail_html(error_html)
            return
            
        # 生成详细信息
        detail_lines = []
        stock_name = stock_info.get('name', stock_code)
        detail_lines.append(f" {stock_name} ({stock_code}) 详细分析")
        detail_lines.append("=" * 50)
        detail_lines.append("")
        
        # 获取分析结果信息
        rtsi_data = stock_info.get('rtsi', {})
        if isinstance(rtsi_data, dict):
            # 检查是否是ARTS算法结果
            algorithm = rtsi_data.get('algorithm', 'unknown')
            if algorithm == 'ARTS_v1.0' or algorithm == 'ARTS_v1.0_backup':
                # ARTS算法结果（主算法或后备算法）
                score = rtsi_data.get('rtsi', 0)
                rating_level = rtsi_data.get('rating_level', 'unknown')
                pattern = rtsi_data.get('pattern', 'unknown') 
                confidence = rtsi_data.get('confidence', 'unknown')
                recommendation = rtsi_data.get('recommendation', '')
                trend_direction = rtsi_data.get('trend', 'unknown')
                
                industry = stock_info.get('industry', t_gui('uncategorized'))
                
                detail_lines.append(f"🏢 所属行业: {industry}")
                detail_lines.append(f" ARTS分数: {score:.2f}")
                detail_lines.append(f" 评级等级: {rating_level}")
                detail_lines.append(f" 趋势模式: {pattern}")
                detail_lines.append(f" 置信度: {confidence}")
                detail_lines.append(f" 趋势方向: {trend_direction}")
                detail_lines.append("")
                
                # ARTS评级对应的风险等级
                if '7级' in rating_level or '6级' in rating_level:
                    risk_desc = t_gui("🟢_低风险")
                elif '5级' in rating_level or '4级' in rating_level:
                    risk_desc = t_gui("🟡_中等风险")
                elif '3级' in rating_level or '2级' in rating_level:
                    risk_desc = t_gui("🟠_中高风险")
                else:
                    risk_desc = t_gui("🔴_高风险")
                
                detail_lines.append(f" 风险等级: {risk_desc}")
                detail_lines.append("")
                

                
                # 根据评级等级给出详细建议
                if '7级' in rating_level or '6级' in rating_level:
                    detail_lines.append("  • ⭐ 强烈推荐：ARTS评级优秀")
                    detail_lines.append("  •  操作策略：可积极配置")
                    detail_lines.append("  •  目标：中长期持有")
                elif '5级' in rating_level or '4级' in rating_level:
                    detail_lines.append("  •  适度关注：ARTS评级良好")
                    detail_lines.append("  •  操作策略：可适量配置")
                    detail_lines.append("  •  目标：观察后续表现")
                elif '3级' in rating_level or '2级' in rating_level:
                    detail_lines.append("  •  谨慎观望：ARTS评级一般")
                    detail_lines.append("  •  操作策略：减少配置")
                    detail_lines.append("  •  目标：等待改善信号")
                else:
                    detail_lines.append("  •  建议回避：ARTS评级较低")
                    detail_lines.append("  •  操作策略：避免新增")
                    detail_lines.append("  •  目标：择机减仓")
                
                if confidence in ['极低', '低']:
                    detail_lines.append("  •  注意：当前分析置信度较低，建议谨慎决策")
                
                detail_lines.append("")
                detail_lines.append(" ARTS算法特点:")
                detail_lines.append("  • 动态时间加权，对近期变化敏感")
                detail_lines.append("  • 智能模式识别，捕捉复杂趋势")
                detail_lines.append("  • 置信度评估，提供可靠性参考")
                detail_lines.append("  • 自适应调整，适应不同股票特性")
            else:
                # RTSI算法结果（兼容旧版）
                rtsi_value = rtsi_data.get('rtsi', 0)
                if not isinstance(rtsi_value, (int, float)):
                    rtsi_value = 0
                rtsi_value = float(rtsi_value)
                
                industry = stock_info.get('industry', t_gui('uncategorized'))
                
                detail_lines.append(f"🏢 所属行业: {industry}")
                detail_lines.append(f" RTSI指数: {rtsi_value:.2f}")
                
                # 判断趋势强度
                if rtsi_value > 80:
                    trend = "极强上升"
                    risk_desc = "🟢 低风险"
                elif rtsi_value > 60:
                    trend = "强势上升"
                    risk_desc = "🟢 较低风险"
                elif rtsi_value > 40:
                    trend = t_gui("温和上升")
                    risk_desc = t_gui("🟡_中等风险")
                elif rtsi_value > 20:
                    trend = t_gui("震荡整理")
                    risk_desc = t_gui("🟡_中高风险")
                else:
                    trend = "下降趋势"
                    risk_desc = "🔴 高风险"
                    
                detail_lines.append(f" 趋势判断: {trend}")
                detail_lines.append(f" 风险等级: {risk_desc}")
                detail_lines.append("")
                





                    
                detail_lines.append("")
                detail_lines.append(" 重要提示:")
                detail_lines.append("  • RTSI指数反映短期技术趋势强度")
                detail_lines.append("  • 投资决策还需结合基本面分析")
                detail_lines.append("  • 市场有风险，投资需谨慎")
        else:
            # 简单数值结果（兼容性处理）
            rtsi_value = float(rtsi_data) if isinstance(rtsi_data, (int, float)) else 0
            industry = stock_info.get('industry', t_gui('uncategorized'))
            
            detail_lines.append(f"🏢 所属行业: {industry}")
            detail_lines.append(f" 分析分数: {rtsi_value:.2f}")
            detail_lines.append(" 注意：使用简化显示模式")
        
        # 将文本转换为HTML格式
        detail_html = f"""
        <div style="font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; padding: 20px; line-height: 1.6;">
            <pre style="white-space: pre-wrap; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">{"<br>".join(detail_lines)}</pre>
        </div>
        """
        self.set_stock_detail_html(detail_html)
    
    # 按钮事件处理方法已删除，因为移除了按钮
        
    def analyze_selected_stock_complete(self, stock_code):
        """完整分析选中的股票 - 移植原界面的analyze_selected_stock功能"""
        if not self.analysis_results_obj:
            return
            
        stocks_data = self.analysis_results_obj.stocks
        if stock_code not in stocks_data:
            self.clear_stock_analysis()
            return
            
        stock_info = stocks_data[stock_code]
        stock_name = stock_info.get('name', stock_code)
        
        # 保存当前股票信息供AI分析使用
        self.current_stock_code = stock_code
        self.current_stock_info = stock_info
        
        # 不再在这里预取量价数据，改为延迟加载
        # 清除之前的量价数据缓存，强制重新获取
        self.current_volume_price_data = None
        
        # 更新详细分析Tab（包含核心指标）- 这个不需要量价数据
        self.update_detailed_stock_analysis(stock_code, stock_name, stock_info)
        
        # 更新AI分析Tab状态 - 新结构中包含技术AI和投资大师AI
        self.update_technical_ai_tab(stock_code, stock_name)
        self.update_master_ai_tab(stock_code, stock_name)
        
        # 更新迷你投资大师Tab状态
        self.update_mini_master_tab(stock_code, stock_name)
        
        # 趋势图表Tab延迟加载 - 只有在用户点击Tab2时才加载
    
    def _load_stock_chart_data(self, stock_code):
        """延迟加载股票趋势图表数据 - 只在用户点击趋势图表Tab时执行"""
        try:
            if not hasattr(self, 'current_stock_info') or not self.current_stock_info:
                print(f"  无法加载趋势图表：缺少股票信息 {stock_code}")
                return
            
            print(f" 开始延迟加载趋势图表数据: {stock_code}")
            
            # 预取量价数据并缓存
            self._prefetch_volume_price_data(stock_code)
            
            # 更新趋势图表Tab
            self.update_stock_chart(stock_code, self.current_stock_info)
            
            print(f" 趋势图表数据加载完成: {stock_code}")
            
        except Exception as e:
            print(f"[ERROR] 延迟加载趋势图表数据失败: {stock_code} - {e}")
    
    def auto_trigger_mini_master_analysis(self, stock_code, stock_name):
        """自动触发迷你投资大师分析 - 无需用户点击按钮"""
        try:
            # 检查是否已有缓存，如果有则直接返回，避免重复分析
            if hasattr(self, 'mini_master_cache') and stock_code in self.mini_master_cache:
                print(f"[自动分析] {stock_code} 已有迷你投资大师分析缓存，跳过重复分析")
                return
            
            # 检查是否正在分析中
            if hasattr(self, 'mini_master_analysis_in_progress') and self.mini_master_analysis_in_progress:
                print(f"[自动分析] 迷你投资大师分析正在进行中，跳过 {stock_code}")
                return
            
            # 检查基础条件
            if not self.analysis_results_obj:
                print(f"[自动分析] 缺少分析结果数据，跳过 {stock_code} 的迷你投资大师分析")
                return
            
            print(f"[自动分析] 开始为 {stock_code}({stock_name}) 执行迷你投资大师分析")
            
            # 执行分析（使用与手动分析相同的逻辑）
            self.perform_mini_master_analysis(stock_code)
            
        except Exception as e:
            print(f"[自动分析] 自动触发迷你投资大师分析失败: {stock_code} - {e}")
    
    def _prefetch_volume_price_data(self, stock_code):
        """预取量价数据并缓存"""
        try:
            # 导入缓存管理器
            from cache import get_cache_manager
            
            # 获取市场类型 - 使用多种检测方案
            preferred_market = self._get_preferred_market_with_multiple_fallbacks(stock_code)
            if not preferred_market:
                print(f"  无法确定市场类型，跳过量价数据预取: {stock_code}")
                return
            
            # 获取缓存管理器
            cache_manager = get_cache_manager(verbose=False)
            
            # 异步预取数据（38天用于趋势图，5天用于AI分析）
            print(f" 开始预取量价数据: {stock_code} ({preferred_market.upper()}市场)")
            
            # 预取38天数据（趋势图用）
            volume_price_data_38 = cache_manager.get_volume_price_data(stock_code, preferred_market, 38)
            if volume_price_data_38:
                print(f" 成功缓存38天量价数据: {volume_price_data_38['stock_name']} - {volume_price_data_38['total_days']}天")
            
            # 预取5天数据（AI分析用）
            volume_price_data_5 = cache_manager.get_volume_price_data(stock_code, preferred_market, 5)
            if volume_price_data_5:
                print(f" 成功缓存5天量价数据: {volume_price_data_5['stock_name']} - {volume_price_data_5['total_days']}天")
            
            # 保存到实例变量供其他方法使用
            self.current_volume_price_data = {
                '38_days': volume_price_data_38,
                '5_days': volume_price_data_5,
                'market': preferred_market
            }
            
        except Exception as e:
            print(f"[ERROR] 预取量价数据失败: {stock_code} - {e}")
            self.current_volume_price_data = None
    
    def get_cached_volume_price_data(self, stock_code: str = None, days: int = 38) -> dict:
        """
        获取缓存的量价数据（统一接口）- 优化版：直接使用全局市场，不尝试其他市场
        
        Args:
            stock_code: 股票代码，None表示使用当前选中股票
            days: 天数，支持5和38天
            
        Returns:
            dict: 量价数据，如果没有返回None
        """
        try:
            # 使用当前选中股票代码
            if stock_code is None:
                stock_code = getattr(self, 'current_stock_code', None)
            
            if not stock_code:
                return None
            
            # 导入缓存管理器
            from cache import get_cache_manager
            
            # 直接使用全局市场类型，不进行多重检测
            current_market = self._get_current_market_type()
            
            # 从缓存获取数据
            cache_manager = get_cache_manager(verbose=False)
            result = cache_manager.get_volume_price_data(stock_code, current_market, days)
            
            # 如果找不到数据，直接返回None，不尝试其他市场
            if not result:
                # 静默失败，减少日志输出
                pass
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 获取缓存量价数据失败: {stock_code} - {e}")
            return None
        
    def clear_stock_analysis(self):
        """清空股票分析"""
        # 清空图表 - 支持WebView和TextEdit
        if hasattr(self, 'chart_webview'):
            default_html = """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>等待选择股票</title>
                <style>
                    body {
                        font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                        margin: 0;
                        padding: 40px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    
                    .placeholder {
                        background: white;
                        border-radius: 15px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                        padding: 60px;
                        text-align: center;
                        max-width: 500px;
                    }
                    
                    .icon {
                        font-size: 48px;
                        margin-bottom: 20px;
                    }
                    
                    .title {
                        color: #2c3e50;
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 15px;
                    }
                    
                    .description {
                        color: #6c757d;
                        font-size: 16px;
                        line-height: 1.6;
                    }
                </style>
            </head>
            <body>
                <div class="placeholder">
                    <div class="icon"></div>
                    <div class="title">请选择股票查看趋势图表</div>
                    <div class="description">
                        选择股票后，将显示：<br/>
                        • 量价走势图<br/>
                        • 评级趋势分析<br/>
                        • 技术指标分析<br/>
                        • 投资建议
                    </div>
                </div>
            </body>
            </html>
            """
            self.chart_webview.setHtml(default_html)
        elif hasattr(self, 'chart_text'):
            chart_html = f"""
            <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
                <h3 style="color: #007bff;"> 趋势图表</h3>
                <p>{t_gui("请选择股票查看趋势图表...")}</p>
            </div>
            """
            self.set_html_content(self.chart_text, chart_html)
            
        # 清空详细分析
        if hasattr(self, 'stock_detail_text'):
            detail_html = f"""
            <div style="text-align: center; margin-top: 50px; color: #666; font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;">
                <h3 style="color: #007bff;"> 个股详细分析</h3>
                <p>{t_gui("请从左侧股票列表中选择一只股票查看详细分析")}</p>
            </div>
            """
            self.set_stock_detail_html(detail_html)
        
        # 重置当前股票信息
        self.current_stock_code = None
        self.current_stock_info = None
        
        # 重置AI分析状态
        if hasattr(self, 'ai_stacked_widget'):
            # 重置到第1页（分析按钮页）
            self.ai_stacked_widget.setCurrentIndex(0)
        if hasattr(self, 'ai_status_label'):
            self.ai_status_label.setText("")
        if hasattr(self, 'stock_ai_analyze_btn'):
            self.stock_ai_analyze_btn.setEnabled(True)
            self.stock_ai_analyze_btn.setText(t_gui("开始AI分析"))
            

            
    def classify_trend(self, rtsi_value):
        """分类趋势 - 移植原界面逻辑"""
        if rtsi_value >= 80:
            return "强势上升"
        elif rtsi_value >= 60:
            return "温和上升"
        elif rtsi_value >= 40:
            return "震荡整理"
        elif rtsi_value >= 20:
            return "弱势下降"
        else:
            return "强势下降"
            
    def calculate_risk_level(self, rtsi_value, confidence):
        """计算风险等级 - 移植原界面逻辑"""
        if rtsi_value >= 80 and confidence >= 0.8:
            return "低风险"
        elif rtsi_value >= 60 and confidence >= 0.6:
            return "较低风险"
        elif rtsi_value >= 40:
            return "中等风险"
        elif rtsi_value >= 20:
            return "较高风险"
        else:
            return "高风险"
            
    def update_stock_chart(self, stock_code, stock_info):
        """更新趋势图表 - 使用新的增强图表生成器，集成38天量价走势"""
        # 提取RTSI数据
        rtsi_data = stock_info.get('rtsi', {})
        if isinstance(rtsi_data, dict):
            rtsi_value = rtsi_data.get('rtsi', 0)
        else:
            rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
            
        stock_name = stock_info.get('name', stock_code)
        
        try:
            # 获取当前数据文件路径，用于指定评级数据文件
            current_rating_file = self._get_current_rating_file()
            
            # 初始化增强图表生成器 V3 (重新设计，避免内容重复)
            from visualization.enhanced_stock_charts import EnhancedStockChartGeneratorV3
            chart_generator = EnhancedStockChartGeneratorV3(verbose=False, specific_rating_file=current_rating_file)
            
            # 根据当前加载的数据文件推断优先市场 - 使用增强检测
            preferred_market = self._get_preferred_market_with_multiple_fallbacks(stock_code)
            
            # 验证市场参数
            if not preferred_market:
                print(f"[ERROR] 无法确定股票市场，使用默认CN市场")
                preferred_market = 'cn'
            
            # 从统一缓存接口获取38天量价数据
            self.log(f"正在获取股票 {stock_code} 的38天量价数据（{preferred_market.upper()}市场）...")
            volume_price_data = self.get_cached_volume_price_data(stock_code, days=38)
            
            # 获取真实的评级历史数据（不使用模拟数据）
            rating_data = self.get_real_historical_data(stock_code)
            if not rating_data:
                print(f" 股票 {stock_code} 没有真实评级数据，将不显示评级图表")
                rating_data = []
            
            # 调试：打印量价数据获取结果
            print(f" 量价数据获取结果: {stock_code}")
            print(f"  - 数据对象: {type(volume_price_data)}")
            if volume_price_data:
                print(f"  - 数据键: {list(volume_price_data.keys()) if isinstance(volume_price_data, dict) else 'Not dict'}")
                if isinstance(volume_price_data, dict) and 'data' in volume_price_data:
                    print(f"  - 数据长度: {len(volume_price_data['data']) if volume_price_data['data'] else 0}")
            
            if volume_price_data and volume_price_data.get('data'):
                # 生成增强HTML图表
                enhanced_html = chart_generator.generate_enhanced_html_chart(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    volume_price_data=volume_price_data['data'],
                    rating_data=rating_data,
                    current_rtsi=rtsi_value,
                    market=preferred_market  # 传递市场信息
                )
                
                # 在WebView中显示
                if hasattr(self, 'chart_webview'):
                    self.chart_webview.setHtml(enhanced_html)
                    self.log(f" 成功生成增强图表：{stock_name} ({stock_code})")
                elif hasattr(self, 'chart_text'):
                    # 回退到简化HTML版本
                    self.chart_text.setHtml(self.generate_fallback_chart(stock_code, stock_name, rtsi_value, rating_data))
                    
            else:
                # 无量价数据时，尝试强制获取数据
                self.log(f" 第一次获取失败，尝试强制获取 {stock_code} 的量价数据")
                
                # 尝试直接使用图表生成器获取数据
                try:
                    direct_data = chart_generator.get_volume_price_data(stock_code, 38, preferred_market)
                    if direct_data and direct_data.get('data'):
                        print(f" 直接获取成功，数据长度: {len(direct_data['data'])}")
                        enhanced_html = chart_generator.generate_enhanced_html_chart(
                            stock_code=stock_code,
                            stock_name=stock_name,
                            volume_price_data=direct_data['data'],
                            rating_data=rating_data,
                            current_rtsi=rtsi_value,
                            market=preferred_market
                        )
                        
                        if hasattr(self, 'chart_webview'):
                            self.chart_webview.setHtml(enhanced_html)
                            self.log(f" 成功生成增强图表（直接获取）：{stock_name} ({stock_code})")
                            return
                        elif hasattr(self, 'chart_text'):
                            self.chart_text.setHtml(enhanced_html)
                            return
                except Exception as direct_e:
                    print(f"[ERROR] 直接获取也失败: {direct_e}")
                
                # 最后回退到基础图表
                self.log(f" 无法获取 {stock_code} 的量价数据，仅显示评级趋势")
                fallback_html = self.generate_fallback_chart(stock_code, stock_name, rtsi_value, rating_data)
                
                if hasattr(self, 'chart_webview'):
                    self.chart_webview.setHtml(fallback_html)
                elif hasattr(self, 'chart_text'):
                    self.chart_text.setHtml(fallback_html)
                    
        except Exception as e:
            self.log(f"[ERROR] 生成增强图表失败: {str(e)}")
            print(f"[ERROR] 异常详情: {e}")
            import traceback
            traceback.print_exc()
            # 使用原有的图表生成方法作为备用
            self.update_stock_chart_fallback(stock_code, stock_info)
    
    def generate_fallback_chart(self, stock_code, stock_name, rtsi_value, rating_data):
        """生成备用图表HTML"""
        from datetime import datetime
        
        chart_html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{stock_name} - 评级趋势分析</title>
            <style>
                body {{
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                
                .chart-container {{
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    padding: 30px;
                    margin-bottom: 20px;
                }}
                
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #4CAF50;
                }}
                
                .header h1 {{
                    color: #2c3e50;
                    margin: 0;
                    font-size: 24px;
                    font-weight: bold;
                }}
                
                .stock-info {{
                    display: flex;
                    justify-content: space-around;
                    background: #f8f9fa;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 30px;
                }}
                
                .info-item {{
                    text-align: center;
                }}
                
                .info-label {{
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}
                
                .info-value {{
                    color: #2c3e50;
                    font-size: 18px;
                    font-weight: bold;
                }}
                
                .chart-area {{
                    background: #f1f3f4;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                
                .chart-title {{
                    color: #2c5aa0;
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    text-align: center;
                }}
                
                .ascii-chart {{
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                    line-height: 1.2;
                    white-space: pre;
                    overflow-x: auto;
                    background: white;
                    padding: 15px;
                    border-radius: 5px;
                }}
                
                .analysis-panel {{
                    background: #e3f2fd;
                    border: 1px solid #2196f3;
                    border-radius: 10px;
                    padding: 20px;
                    margin-top: 20px;
                }}
                
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                    color: #856404;
                }}
            </style>
        </head>
        <body>
            <div class="chart-container">
                <div class="header">
                    <h1> {stock_name} ({stock_code})</h1>
                    <div style="color: #7f8c8d; font-size: 16px;">评级趋势分析</div>
                </div>
                
                <div class="stock-info">
                    <div class="info-item">
                        <div class="info-label">股票代码</div>
                        <div class="info-value">{stock_code}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">股票名称</div>
                        <div class="info-value">{stock_name}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">当前RTSI评级</div>
                        <div class="info-value" style="color: {'#28a745' if rtsi_value > 60 else '#ffc107' if rtsi_value > 40 else '#dc3545'}">{rtsi_value:.2f}</div>
                    </div>
                </div>
                
                <div class="warning">
                     <strong>数据说明：</strong> 无法获取该股票的量价数据，仅显示评级趋势分析。建议选择有完整数据的股票以获得最佳分析体验。
                </div>
                
                <div class="chart-area">
                    <div class="chart-title"> 评级趋势图（近期数据）</div>
                    <div class="ascii-chart">{self.generate_ascii_chart(rating_data) if rating_data else "暂无评级数据"}</div>
                </div>
                
                <div class="analysis-panel">
                    <h4 style="color: #1976d2; margin-top: 0;"> 技术分析</h4>
                    <ul style="margin-left: 20px;">
                        <li><strong>趋势方向:</strong> <span style="color: {'#28a745' if rtsi_value > 60 else '#ffc107' if rtsi_value > 40 else '#dc3545'};">{self.get_detailed_trend(rtsi_value) if hasattr(self, 'get_detailed_trend') else '分析中'}</span></li>
                        <li><strong>RTSI区间:</strong> {self.get_rtsi_zone(rtsi_value) if hasattr(self, 'get_rtsi_zone') else '计算中'}</li>
                        <li><strong>操作建议:</strong> {self.get_operation_suggestion(rtsi_value) if hasattr(self, 'get_operation_suggestion') else '评估中'}</li>
                    </ul>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #6c757d; font-size: 12px;">
                🕒 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                 数据来源: AI股票分析系统 | 
                 仅供参考，投资有风险
            </div>
        </body>
        </html>
        """
        
        return chart_html
    
    def update_stock_chart_fallback(self, stock_code, stock_info):
        """原有的图表更新方法作为备用"""
        if not (hasattr(self, 'chart_text') or hasattr(self, 'chart_webview')):
            return
            
        rtsi_data = stock_info.get('rtsi', {})
        if isinstance(rtsi_data, dict):
            rtsi_value = rtsi_data.get('rtsi', 0)
        else:
            rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
            
        stock_name = stock_info.get('name', stock_code)
        chart_data = self.generate_realistic_chart_data(stock_code, rtsi_value)
        fallback_html = self.generate_fallback_chart(stock_code, stock_name, rtsi_value, chart_data)
        
        if hasattr(self, 'chart_webview'):
            self.chart_webview.setHtml(fallback_html)
        elif hasattr(self, 'chart_text'):
            self.chart_text.setHtml(fallback_html)
    
    def update_industry_chart(self, industry_name):
        """更新行业趋势图表 - 基于行业内个股的平均值数据"""
        try:
            print(f" 开始更新行业趋势图表: {industry_name}")
            
            if not self.analysis_results_obj:
                print("[ERROR] 暂无分析数据")
                self.set_industry_chart_html("<p style='color: #dc3545;'>暂无分析数据</p>")
                return
            
            # 特殊处理指数行业 - 指数不需要交易数据，直接使用权重和评级数据
            if industry_name == "指数":
                print(" 检测到指数行业，使用权重模式（不要求交易数据）")
                # 指数行业使用权重和评级数据，不需要真实交易数据验证
                # 直接跳过数据验证，继续处理
            
            # 获取行业内的股票数据
            industry_stocks = self.get_industry_stocks_data(industry_name)
            print(f" 获取到 {len(industry_stocks)} 只行业股票")
            
            if not industry_stocks:
                print(f"[ERROR] 行业 {industry_name} 暂无股票数据")
                self.set_industry_chart_html(f"<p style='color: #dc3545;'>行业 {industry_name} 暂无股票数据</p>")
                return
            
            # 根据市场类型验证行业数据的完整性
            current_market = self._get_current_market_type()
            if current_market == 'hk' and self._is_hk_industry(industry_name, industry_stocks):
                validated_stocks = self._validate_hk_industry_data(industry_stocks)
                if not validated_stocks:
                    print(f"[ERROR] 港股行业 {industry_name} 数据验证失败")
                    self.set_industry_chart_html(f"<p style='color: #dc3545;'>港股行业 {industry_name} 数据验证失败，请检查数据源</p>")
                    return
                industry_stocks = validated_stocks
            elif current_market == 'us':
                # 美股数据验证（简化版，主要检查数据完整性）
                validated_stocks = self._validate_us_industry_data(industry_stocks)
                if not validated_stocks:
                    print(f"[ERROR] 美股行业 {industry_name} 数据验证失败")
                    self.set_industry_chart_html(f"<p style='color: #dc3545;'>美股行业 {industry_name} 数据验证失败，请检查数据源</p>")
                    return
                industry_stocks = validated_stocks
            # CN市场数据通常不需要特殊验证，直接使用
            
            # 计算行业平均值
            industry_avg_data = self.calculate_industry_averages(industry_stocks)
            print(f" 计算得到行业平均RTSI: {industry_avg_data.get('avg_rtsi', 0):.2f}")
            
            # 生成行业趋势图表HTML
            chart_html = self.generate_industry_chart_html(industry_name, industry_avg_data)
            
            # 更新显示
            self.set_industry_chart_html(chart_html)
            print(f" 行业趋势图表更新完成: {industry_name}")
            
        except Exception as e:
            print(f"[ERROR] 更新行业趋势图表失败: {industry_name} - {e}")
            import traceback
            traceback.print_exc()
            self.set_industry_chart_html(f"<p style='color: #dc3545;'>生成行业图表失败: {str(e)}</p>")
    
    def get_industry_stocks_data(self, industry_name):
        """获取行业内股票的数据 - 按当天成交金额排序，选择前10个"""
        try:
            if not self.analysis_results_obj:
                return []
            
            print(f" 开始获取行业 {industry_name} 的股票数据...")
            
            # 特殊处理指数行业
            if industry_name == "指数":
                print(" 检测到指数行业，使用特殊处理逻辑")
                return self._get_index_industry_data()
            
            # 首先尝试从行业数据中获取股票列表
            industry_stocks_raw = []
            
            if hasattr(self.analysis_results_obj, 'industries') and industry_name in self.analysis_results_obj.industries:
                industry_info = self.analysis_results_obj.industries[industry_name]
                
                # 检查行业数据中是否已经包含股票信息
                if 'stocks' in industry_info and industry_info['stocks']:
                    industry_stocks_raw = industry_info['stocks']
                    print(f" 从行业数据中获取到 {len(industry_stocks_raw)} 只股票")
            
            # 如果行业数据中没有股票信息，则遍历所有股票查找
            if not industry_stocks_raw and hasattr(self.analysis_results_obj, 'stocks'):
                print(" 从全部股票中筛选行业股票...")
                
                for stock_code, stock_data in self.analysis_results_obj.stocks.items():
                    # 检查股票是否属于该行业
                    stock_industry = stock_data.get('industry', '')
                    if stock_industry == industry_name:
                        industry_stocks_raw.append({
                            'code': stock_code,
                            'name': stock_data.get('name', stock_code),
                            'rtsi': stock_data.get('rtsi', {}),
                            'data': stock_data
                        })
                
                print(f" 筛选得到 {len(industry_stocks_raw)} 只行业股票")
            
            if not industry_stocks_raw:
                print(f"[ERROR] 行业 {industry_name} 没有找到股票数据")
                return []
            
            # 获取每只股票的当天成交金额并排序
            stocks_with_volume = []
            
            for stock in industry_stocks_raw:
                # 【修复】处理 stock 可能是字典的情况
                if isinstance(stock, dict):
                    stock_code = stock.get('code', '')
                    stock_name = stock.get('name', stock_code)
                    stock_rtsi = stock.get('rtsi', {})
                    stock_data = stock.get('data', {})
                else:
                    # 如果不是字典，尝试作为其他格式处理（兜底）
                    print(f"[WARNING] 股票数据格式异常，类型为 {type(stock)}")
                    continue
                
                # 尝试获取当天成交金额
                current_volume = self.get_stock_current_volume(stock_code)
                
                stocks_with_volume.append({
                    'code': stock_code,
                    'name': stock_name,
                    'rtsi': stock_rtsi,
                    'data': stock_data,
                    'current_volume': current_volume
                })
                
                print(f"  股票 {stock_code}({stock_name}): 成交金额 {current_volume:,.0f}")
            
            # 按成交金额降序排序
            stocks_with_volume.sort(key=lambda x: x['current_volume'], reverse=True)
            
            # 选择前10个（如果不足10个则全部选择）
            selected_count = min(10, len(stocks_with_volume))
            selected_stocks = stocks_with_volume[:selected_count]
            
            print(f" 按成交金额排序，选择前 {selected_count} 只股票参与计算")
            for i, stock in enumerate(selected_stocks, 1):
                print(f"  {i}. {stock['code']}({stock['name']}): {stock['current_volume']:,.0f}")
            
            return selected_stocks
            
        except Exception as e:
            print(f"[ERROR] 获取行业股票数据失败: {industry_name} - {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_stock_current_volume(self, stock_code):
        """获取股票的当天成交金额"""
        try:
            print(f"   开始获取 {stock_code} 的成交金额...")
            
            # 特殊处理指数：指数没有成交金额概念，使用权重或重要性排序
            if self._is_index_code(stock_code):
                index_weight = self._get_index_weight(stock_code)
                print(f"   指数 {stock_code} 使用权重排序: {index_weight:,.0f}")
                return float(index_weight)
            
            # 尝试从多个数据源获取成交金额
            
            # 方法1: 优先从LJ数据读取器获取交易数据（.dat.gz文件包含成交金额等交易数据）
            try:
                from utils.lj_data_reader import LJDataReader
                lj_reader = LJDataReader()
                
                # 检测市场类型
                current_market = self._get_current_market_type()
                market = self._detect_stock_market(stock_code)
                print(f"  🌍 当前市场类型: {current_market.upper()}, 股票市场: {market.upper()}")
                
                # 检查对应市场的数据文件是否存在（使用智能路径查找）
                market_data_files = {
                    'cn': 'cn-lj.dat.gz',
                    'hk': 'hk-lj.dat.gz', 
                    'us': 'us-lj.dat.gz'
                }
                
                # 使用智能路径查找（优先EXE目录）
                if market in market_data_files:
                    data_file_path = get_data_file_path(market_data_files[market])
                    if data_file_path.exists():
                        print(f"✓ 使用lj-read.py数据读取器，数据文件: {data_file_path}")
                        
                        # 获取最近1天的数据（移除data_type参数）
                        volume_data = lj_reader.get_volume_price_data(stock_code, days=1, market=market)
                        if volume_data and 'data' in volume_data and volume_data['data']:
                            latest_data = volume_data['data'][-1]  # 最新一天的数据
                            amount = latest_data.get('amount', 0)  # 成交金额
                            if amount > 0:
                                print(f"   从LJ数据获取 {stock_code} 成交金额: {amount:,.0f}")
                                return float(amount)
                            else:
                                # 如果没有成交金额，尝试计算：成交金额 = 成交量 × 收盘价
                                volume = latest_data.get('volume', 0)  # 成交量
                                close_price = latest_data.get('close_price', 0)  # 收盘价
                                if volume > 0 and close_price > 0:
                                    calculated_amount = volume * close_price
                                    print(f"  🧮 计算 {stock_code} 成交金额: {volume:,.0f} × {close_price} = {calculated_amount:,.0f}")
                                    return float(calculated_amount)
                    else:
                        print(f"    {market.upper()}市场数据文件不存在: {data_file_path}")
                    
            except Exception as e:
                print(f"    LJ数据获取失败 {stock_code}: {e}")
            
            # 方法2: 备用 - 尝试从主数据文件获取成交金额（.json.gz只有评级数据，通常没有交易数据）
            try:
                current_market = self._get_current_market_type()
                
                # 从主数据文件获取成交金额
                amount_from_main = self._get_amount_from_main_data(stock_code)
                if amount_from_main and amount_from_main > 0:
                    print(f"   从主数据文件获取 {stock_code} 成交金额: {amount_from_main:,.0f}")
                    return float(amount_from_main)
            except Exception as e:
                print(f"    主数据文件获取失败 {stock_code}: {e}")
            
            # 方法3: 尝试从股票搜索工具获取
            try:
                if hasattr(self, 'search_tool') and self.search_tool:
                    # 检测市场类型
                    market = self._detect_stock_market(stock_code)
                    results = self.search_tool.search_stock_by_code(stock_code, market, 1)
                    
                    if results:
                        for market_key, market_data in results.items():
                            trade_data = market_data.get('数据', {}).get('交易数据', {})
                            if trade_data:
                                # 获取最新日期的数据
                                latest_date = max(trade_data.keys())
                                latest_trade = trade_data[latest_date]
                                volume = latest_trade.get('成交额', 0)
                                if volume > 0:
                                    print(f"   从搜索工具获取 {stock_code} 成交金额: {volume:,.0f}")
                                    return float(volume)
            except Exception as e:
                print(f"    搜索工具获取失败 {stock_code}: {e}")
            
            # 如果无法获取真实成交金额，返回0表示数据不可用
            print(f"  [ERROR] 无法获取 {stock_code} 的真实成交金额数据")
            return 0.0
            
        except Exception as e:
            print(f"[ERROR] 获取股票成交金额失败 {stock_code}: {e}")
            return 50000000.0  # 默认5000万
    
    def _load_industries_from_file(self):
        """直接从数据文件加载行业数据"""
        try:
            import json
            import gzip
            import os
            from collections import defaultdict
            
            # 声明全局变量
            global DECOMPRESSED_FILES_THIS_RUN
            
            print("📁 正在从数据文件加载行业数据...")
            print(f"📋 本次运行已解压文件: {list(DECOMPRESSED_FILES_THIS_RUN) if DECOMPRESSED_FILES_THIS_RUN else '无'}")
            
            # 获取当前主文件路径
            current_file = self._get_current_rating_file()
            if current_file:
                print(f" 使用当前主文件: {current_file}")
                # 基于当前文件生成候选文件列表
                base_name = os.path.splitext(os.path.basename(current_file))[0]
                if base_name.endswith('.json'):
                    base_name = base_name[:-5]  # 移除 .json 后缀
                
                # 只包含真正的未压缩文件（.json 结尾，不是 .json.gz）
                uncompressed_files = []
                if not current_file.endswith('.gz'):
                    uncompressed_files.append(current_file)
                uncompressed_files.extend([
                    f"{base_name}.json",
                    f"{base_name.upper()}.json"
                ])
                compressed_files = [
                    current_file if current_file.endswith('.gz') else f"{current_file}.gz",
                    f"{base_name}.json.gz",
                    f"{base_name.upper()}.json.gz"
                ]
            else:
                print(" 未获取到当前主文件，使用默认CN数据")
                # 回退到默认文件
                uncompressed_files = ['cn_data5000.json', 'CN_Data5000.json']
                compressed_files = ['cn_data5000.json.gz', 'CN_Data5000.json.gz']
            
            data = None
            
            # 第一步：检查是否需要强制解压
            current_compressed_file = None
            
            # 找到对应的压缩文件
            for file_path in compressed_files:
                if os.path.exists(file_path):
                    current_compressed_file = file_path
                    break
            
            force_decompress = current_compressed_file and current_compressed_file not in DECOMPRESSED_FILES_THIS_RUN
            
            # 如果需要强制解压，跳过未压缩文件检查
            if not force_decompress:
                # 尝试未压缩文件（更快）
                for file_path in uncompressed_files:
                    if os.path.exists(file_path):
                        try:
                            print(f" 发现未压缩文件 {file_path}，使用快速加载...")
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            print(f" 快速加载完成: {file_path}")
                            break
                        except Exception as e:
                            print(f"  快速加载 {file_path} 失败: {e}")
                            continue
            else:
                print(f"🔄 本次运行首次加载，强制从压缩文件解压: {current_compressed_file}")
                data = None
            
            # 第二步：如果没有未压缩文件，使用压缩文件
            if not data:
                print("🔄 未找到解压文件，使用压缩文件...")
                loaded_from_compressed = None
                for file_path in compressed_files:
                    try:
                        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                            data = json.load(f)
                        print(f" 成功从压缩文件加载: {file_path}")
                        loaded_from_compressed = file_path
                        break
                    except Exception as e:
                        print(f"  加载 {file_path} 失败: {e}")
                        continue
                
                # 如果成功从压缩文件加载，创建未压缩版本供下次使用
                if data and loaded_from_compressed:
                    try:
                        uncompressed_name = loaded_from_compressed.replace('.gz', '')
                        
                        # 记录已解压的文件
                        DECOMPRESSED_FILES_THIS_RUN.add(loaded_from_compressed)
                        
                        # 强制覆盖旧的未压缩文件
                        if os.path.exists(uncompressed_name):
                            print(f"[DEL]  删除旧的未压缩文件: {uncompressed_name}")
                            os.remove(uncompressed_name)
                        
                        print(f"💾 创建未压缩版本 {uncompressed_name} 以供下次快速加载...")
                        with open(uncompressed_name, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                        print(f" 未压缩版本创建完成: {uncompressed_name}")
                        print(f"📝 已记录解压状态: {os.path.basename(loaded_from_compressed)}")
                    except Exception as e:
                        print(f"  创建未压缩版本失败: {e}")  # 不影响主流程
            
            if not data or 'data' not in data:
                print("[ERROR] 无法加载数据文件或数据格式错误")
                return None
            
            # 按行业分组股票
            industries = defaultdict(lambda: {'stocks': {}})
            
            for record in data['data']:
                industry = record.get('行业')
                stock_code = record.get('股票代码')
                stock_name = record.get('股票名称')
                
                if not industry or not stock_code:
                    continue
                
                # 将股票添加到对应行业
                industries[industry]['stocks'][stock_code] = {
                    'name': stock_name,
                    'industry': industry
                }
                
                # 添加评级数据（直接从record复制所有日期字段）
                for key, value in record.items():
                    if isinstance(key, str) and len(key) == 8 and key.isdigit():  # 日期字段
                        industries[industry]['stocks'][stock_code][key] = value
            
            # 转换为普通字典
            result = {}
            for industry_name, industry_info in industries.items():
                result[industry_name] = dict(industry_info)
                result[industry_name]['stocks'] = dict(industry_info['stocks'])
            
            print(f" 成功加载 {len(result)} 个行业，共 {sum(len(info['stocks']) for info in result.values())} 只股票")
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 从文件加载行业数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _detect_stock_market(self, stock_code):
        """检测股票所属市场"""
        try:
            if not stock_code:
                return 'cn'
            
            # 清理股票代码
            clean_code = str(stock_code).strip().upper()
            if clean_code.startswith('="') and clean_code.endswith('"'):
                clean_code = clean_code[2:-1]
            
            # 根据代码格式判断市场
            # A股：6位数字，以00、30、60、68、30开头
            if clean_code.isdigit() and len(clean_code) == 6:
                if clean_code.startswith(('00', '30', '60', '68')):
                    return 'cn'
            
            # 港股：通常是4-5位数字，或包含HK标识
            if clean_code.startswith(('HK', '.HK')) or (clean_code.isdigit() and 4 <= len(clean_code) <= 5):
                return 'hk'
            
            # 美股：通常是1-5位字母
            if clean_code.isalpha() and 1 <= len(clean_code) <= 5:
                return 'us'
            
            # 默认返回cn
            return 'cn'
                
        except Exception:
            return 'cn'
    
    def _is_hk_industry(self, industry_name, industry_stocks):
        """判断是否为港股行业"""
        try:
            # 首先检查当前数据的市场类型
            current_market = self._get_current_market_type()
            print(f"🌍 检测到当前市场类型: {current_market.upper()}")
            
            # 如果当前数据明确不是港股，直接返回False
            if current_market != 'hk':
                print(f" 当前为{current_market.upper()}市场数据，跳过港股验证")
                return False
            
            # 只有在港股市场时才进行港股特征检查
            # 检查行业名称是否包含港股特征
            hk_keywords = ['电讯', '地产', '银行', '保险', '公用', '综合', '能源', '原材料']
            if any(keyword in industry_name for keyword in hk_keywords):
                return True
            
            # 检查股票代码是否为港股格式
            hk_stock_count = 0
            for stock in industry_stocks[:5]:  # 检查前5只股票
                code = stock.get('code', '')
                if self._detect_stock_market(code) == 'hk':
                    hk_stock_count += 1
            
            # 如果超过一半是港股代码，认为是港股行业
            return hk_stock_count > len(industry_stocks[:5]) / 2
            
        except Exception as e:
            print(f"[ERROR] 港股行业判断异常: {e}")
            return False
    
    def _validate_hk_industry_data(self, industry_stocks):
        """验证港股行业数据的完整性"""
        try:
            validated_stocks = []
            
            for stock in industry_stocks:
                code = stock.get('code', '')
                name = stock.get('name', '')
                
                # 验证港股代码格式
                if not code or not name:
                    continue
                
                # 港股代码应该是4-5位数字
                clean_code = str(code).strip()
                if not (clean_code.isdigit() and 4 <= len(clean_code) <= 5):
                    print(f" 跳过无效港股代码: {code}")
                    continue
                
                # 验证是否能获取到数据
                try:
                    from utils.lj_data_reader import LJDataReader
                    lj_reader = LJDataReader()
                    test_data = lj_reader.get_volume_price_data(code, days=1, market='hk')
                    if test_data and test_data.get('data'):
                        validated_stocks.append(stock)
                        print(f" 港股 {code}({name}) 数据验证通过")
                    else:
                        print(f" 港股 {code}({name}) 无法获取数据")
                except Exception as e:
                    print(f" 港股 {code}({name}) 数据验证失败: {e}")
                    continue
            
            print(f" 港股行业数据验证完成: {len(validated_stocks)}/{len(industry_stocks)} 只股票通过验证")
            return validated_stocks
            
        except Exception as e:
            print(f"[ERROR] 港股行业数据验证异常: {e}")
            return []
    
    def _validate_us_industry_data(self, industry_stocks):
        """验证美股行业数据的完整性"""
        try:
            validated_stocks = []
            
            for stock in industry_stocks:
                code = stock.get('code', '')
                name = stock.get('name', '')
                
                # 验证美股代码格式
                if not code or not name:
                    continue
                
                # 美股代码应该是字母组合，通常1-5个字符
                clean_code = str(code).strip().upper()
                if not (clean_code.isalpha() and 1 <= len(clean_code) <= 5):
                    print(f" 跳过无效美股代码: {code}")
                    continue
                
                # 检查是否有基本的股票数据（成交金额等）
                amount = stock.get('amount', 0)
                
                # 如果没有amount字段，优先从LJ数据获取，再从主数据文件获取
                if not amount or amount <= 0:
                    # 方法1: 从LJ数据获取成交金额
                    amount = self._get_stock_amount(code)
                    
                    # 方法2: 如果LJ数据获取失败，尝试从主数据文件获取
                    if not amount or amount <= 0:
                        amount = self._get_amount_from_main_data(code)
                
                if amount and amount > 0:
                    # 更新stock数据中的amount字段
                    stock['amount'] = amount
                    validated_stocks.append(stock)
                    print(f" 美股 {code}({name}) 数据验证通过，成交金额: {amount:,.0f}")
                else:
                    print(f" 美股 {code}({name}) 缺少成交数据")
            
            print(f" 美股行业数据验证完成: {len(validated_stocks)}/{len(industry_stocks)} 只股票通过验证")
            return validated_stocks
            
        except Exception as e:
            print(f"[ERROR] 美股行业数据验证异常: {e}")
            return []
    
    def _is_index_code(self, stock_code):
        """判断是否为指数代码 - 使用精确的指数代码列表"""
        try:
            if not stock_code:
                return False
            
            # 清理股票代码
            clean_code = stock_code.strip()
            if clean_code.startswith('="') and clean_code.endswith('"'):
                clean_code = clean_code[2:-1]
            
            # 精确的指数代码列表（避免误判）
            exact_index_codes = {
                # A股主要指数 - 包含用户提供的特殊格式
                '000001',  # 上证指数（标准代码）
                '999999',  # 上证指数（用户提供的格式）
                '399001',  # 深证成指
                '399006',  # 创业板指
                '000300',  # 沪深300（标准代码）
                '600001',  # 沪深300（用户提供的格式）
                '000016',  # 上证50
                '000905',  # 中证500
                '000852',  # 中证1000
                '399005',  # 中小板指数
                '000009',  # 上证380
                '000010',  # 上证180
                '000688',  # 科创50（标准代码）
                '999688',  # 科创50（用户提供的格式）
                
                # 港股指数
                'HSI',     # 恒生指数
                'HSCEI',   # 恒生国企指数
                'HSCCI',   # 恒生中国企业指数
                'CESA80',  # 中华A80指数
                'HSTECH',  # 恒生科技指数
                'HSHKI',   # 恒生港股通指数
                
                # 美股指数
                'SPX',     # 标准普尔500
                'IXIC',    # 纳斯达克综合指数
                'DJI',     # 道琼斯工业平均指数
                
                # 中华指数系列
                'CES120',  # 中华120指数
                'CES280',  # 中华280指数
                'CES300',  # 中华300指数
            }
            
            # 精确匹配指数代码
            if clean_code in exact_index_codes:
                    return True
            
            # 检查CES系列指数（支持CES开头的其他指数）
            if clean_code.startswith('CES') and len(clean_code) > 3:
                # 确保CES后面跟的是数字
                suffix = clean_code[3:]
                if suffix.isdigit():
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _get_index_industry_data(self):
        """专门处理指数行业的数据获取 - 只保留真正的指数"""
        try:
            print(" 执行指数行业专用数据获取逻辑...")
            
            # 指数代码到名称的映射（根据用户提供的信息更新）
            index_code_to_name = {
                # A股指数 - 用户提供的示例
                '600001': '沪深300',    # 用户示例：600001(沪深300)
                '999999': '上证指数',   # 用户示例：999999(上证指数)
                '999688': '科创50',     # 用户示例：999688(科创50)
                
                # 其他常见指数
                '399001': '深证成指',
                '399006': '创业板指', 
                '000300': '沪深300',   # 标准代码
                '000001': '上证指数',   # 标准代码
                '000016': '上证50',
                '000905': '中证500',
                '000852': '中证1000',
                '000688': '科创50',    # 标准代码
                '399005': '中小板指数',
                
                # 港股指数
                'HSI': '恒生指数',
                'HSCEI': '恒生国企指数',
                'HSCCI': '恒生中国企业指数',
                'CESA80': '中华A80指数',
                'HSTECH': '恒生科技指数',
                'HSHKI': '恒生港股通指数',
                
                # 美股指数
                'SPX': '标普500',
                'IXIC': '纳斯达克', 
                'DJI': '道琼斯'
            }
            
            # 从指数行业数据中获取所有股票代码
            industry_stocks_raw = []
            if hasattr(self.analysis_results_obj, 'industries') and "指数" in self.analysis_results_obj.industries:
                industry_info = self.analysis_results_obj.industries["指数"]
                if 'stocks' in industry_info and industry_info['stocks']:
                    industry_stocks_raw = industry_info['stocks']
                    print(f" 从指数行业数据中获取到 {len(industry_stocks_raw)} 只潜在指数")
            
            # 过滤：只保留真正的指数代码
            valid_indices = []
            for stock in industry_stocks_raw:
                if isinstance(stock, dict):
                    stock_code = stock.get('code', '')
                    stock_name = stock.get('name', stock_code)
                else:
                    stock_code = str(stock)
                    stock_name = stock_code
                
                # 严格验证是否为指数代码
                if self._is_index_code(stock_code):
                    # 获取指数权重
                    weight = self._get_index_weight(stock_code)
                    
                    # 使用映射获取正确的指数名称
                    display_name = index_code_to_name.get(stock_code, stock_name)
                    print(f"   保留指数: {stock_code}({display_name}) - 权重: {weight:,.0f}")
                    
                    valid_indices.append({
                        'code': stock_code,
                        'name': display_name,  # 使用映射的名称
                        'amount': weight,  # 使用权重作为"成交金额"
                        'weight': weight,
                        'is_index': True,
                        'rtsi': stock.get('rtsi', {}) if isinstance(stock, dict) else {}
                    })
                else:
                    print(f"  [ERROR] 过滤非指数: {stock_code}({stock_name})")
            
            print(f" 指数过滤完成: 保留 {len(valid_indices)} 个真正的指数")
            
            # 按权重排序（主要指数在前）
            valid_indices.sort(key=lambda x: x['weight'], reverse=True)
            
            # 只取前10个指数进行计算
            final_indices = valid_indices[:10]
            print(f" 按权重排序，选择前 {len(final_indices)} 个指数参与计算:")
            for i, index in enumerate(final_indices, 1):
                is_major = index['weight'] >= 500000000
                status = "主要" if is_major else "非主要"
                print(f"  {i}. {index['code']}({index['name']}): {index['weight']:,.0f} ({status})")
            
            return final_indices
            
        except Exception as e:
            print(f"[ERROR] 指数行业数据获取失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_index_weight(self, stock_code):
        """获取指数的权重（用于排序）"""
        try:
            # 清理股票代码
            clean_code = stock_code.strip()
            if clean_code.startswith('="') and clean_code.endswith('"'):
                clean_code = clean_code[2:-1]
            
            # 根据指数重要性分配权重 - 区分主要指数和非主要指数
            # 主要指数（权重>500M）- 包含用户提供的特殊格式
            major_index_weights = {
                '000001': 1000000000,  # 上证指数（标准代码）- 最高权重（主要）
                '999999': 1000000000,  # 上证指数（用户格式）- 最高权重（主要）
                'SPX': 980000000,      # 标普500（主要）
                'IXIC': 970000000,     # 纳斯达克（主要）
                'DJI': 960000000,      # 道琼斯（主要）
                'HSI': 950000000,      # 恒生指数（主要）
                '399001': 900000000,   # 深证成指（主要）
                'HSCEI': 850000000,    # 恒生国企指数（主要）
                '000300': 800000000,   # 沪深300（标准代码）（主要）
                '600001': 800000000,   # 沪深300（用户格式）（主要）
                'CES120': 750000000,   # 中华120指数（主要）
                '399006': 700000000,   # 创业板指（主要）
                'CES280': 680000000,   # 中华280指数（主要）
                'CES300': 650000000,   # 中华300指数（主要）
                '000016': 600000000,   # 上证50（主要）
                '000905': 500000000,   # 中证500（主要）
            }
            
            # 非主要指数（权重<500M）- 包含用户提供的特殊格式
            minor_index_weights = {
                '000852': 400000000,   # 中证1000（非主要）
                '399005': 380000000,   # 中小板指数（非主要）
                '000009': 360000000,   # 上证380（非主要）
                '000010': 340000000,   # 上证180（非主要）
                '000688': 320000000,   # 科创50（标准代码）（非主要）
                '999688': 320000000,   # 科创50（用户格式）（非主要）
                'HSCCI': 300000000,    # 恒生中国企业指数（非主要）
            }
            
            # 合并权重字典
            index_weights = {**major_index_weights, **minor_index_weights}
            
            # 查找匹配的指数权重
            for index_code, weight in index_weights.items():
                if clean_code == index_code or clean_code.startswith(index_code):
                    return weight
            
            # 如果没有找到匹配的，基于RTSI值生成权重
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                stock_data = self.analysis_results_obj.stocks.get(stock_code, {})
                rtsi_data = stock_data.get('rtsi', {})
                
                if isinstance(rtsi_data, dict):
                    rtsi_value = rtsi_data.get('rtsi', 0)
                else:
                    rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
                
                # 指数权重基于RTSI值，但基础权重更高
                base_weight = 300000000  # 3亿基础权重
                rtsi_factor = max(0.5, rtsi_value / 100)
                calculated_weight = base_weight * rtsi_factor
                
                print(f"   基于RTSI({rtsi_value:.2f})计算指数权重: {calculated_weight:,.0f}")
                return calculated_weight
            
            # 默认指数权重
            return 300000000.0
            
        except Exception as e:
            print(f"    计算指数权重失败 {stock_code}: {e}")
            return 300000000.0
    
    def _get_real_industry_rating_data(self, industry_stocks):
        """获取行业真实评级数据（基于个股评级平均值）"""
        try:
            from datetime import datetime, timedelta
            
            print(f" 开始获取 {len(industry_stocks)} 只股票的真实评级数据...")
            
            # 收集所有股票的评级数据
            all_stock_ratings = {}
            
            for stock in industry_stocks:
                stock_code = stock.get('code', '')
                stock_name = stock.get('name', stock_code)
                
                # 获取该股票的评级数据
                stock_ratings = self._get_stock_rating_data(stock_code)
                if stock_ratings:
                    all_stock_ratings[stock_code] = stock_ratings
                    print(f"   {stock_code}({stock_name}): 获取到 {len(stock_ratings)} 天评级数据")
                else:
                    print(f"    {stock_code}({stock_name}): 无评级数据")
            
            if not all_stock_ratings:
                print("[ERROR] 所有股票都没有评级数据")
                return []
            
            # 计算行业平均评级
            return self._calculate_industry_average_ratings(all_stock_ratings)
            
        except Exception as e:
            print(f"[ERROR] 获取行业真实评级数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_stock_rating_data(self, stock_code):
        """获取单只股票的评级数据（只使用CN_Data5000.json.gz文件）"""
        try:
            # 方法1: 从CN_Data5000.json.gz文件中获取数据
            try:
                rating_files = self._get_rating_files()
                for file_path in rating_files:
                    ratings = self._load_rating_from_file(stock_code, file_path)
                    if ratings:
                        print(f"     从文件 {file_path} 获取到 {len(ratings)} 条评级")
                        return ratings
            except Exception as e:
                print(f"      从文件获取评级失败: {e}")
            
            # 方法2: 从数据集中获取评级数据（备用）
            try:
                if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                    rating_data = []
                    # 尝试从原始数据中获取评级
                    stock_data = self.analysis_results_obj.stocks.get(stock_code, {})
                    
                    # 查找日期格式的评级数据
                    for key, value in stock_data.items():
                        if isinstance(key, str) and len(key) == 8 and key.isdigit():  # YYYYMMDD格式
                            if value and str(value).strip() not in ['-', 'nan', '']:
                                rating_data.append((key, str(value).strip()))
                    
                    if rating_data:
                        # 按日期排序，取最近38天
                        rating_data.sort(key=lambda x: x[0])
                        recent_ratings = rating_data[-38:]
                        
                        # 转换为(date, numeric_rating)格式
                        converted_ratings = []
                        for date_str, rating_str in recent_ratings:
                            # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
                            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            numeric_rating = self._convert_rating_to_numeric(rating_str)
                            converted_ratings.append((formatted_date, numeric_rating))
                        
                        print(f"     从分析结果获取到 {len(converted_ratings)} 条评级")
                        return converted_ratings
            except Exception as e:
                print(f"      从分析结果获取评级失败: {e}")
            
            # 方法3: 直接从数据文件获取评级数据
            try:
                # 使用已有的文件加载方法
                rating_files = self._get_rating_files()
                for file_path in rating_files:
                    ratings = self._load_rating_from_file(stock_code, file_path)
                    if ratings:
                        print(f"     从文件 {file_path} 获取到 {len(ratings)} 条评级（备用方法）")
                        return ratings
            except Exception as e:
                print(f"      从文件获取评级失败（备用方法）: {e}")
            
            return []
            
        except Exception as e:
            print(f"[ERROR] 获取股票 {stock_code} 评级数据失败: {e}")
            return []
    
    def _convert_rating_to_numeric(self, rating_str):
        """将评级字符串转换为数值 - 使用0-7系统（7=大多最高，0=大空最低）"""
        try:
            # 评级映射表 - 使用0-7系统
            rating_map = {
                '大多': 7, '7': 7,
                '中多': 6, '6': 6,
                '小多': 5, '5': 5,
                '微多': 4, '4': 4,
                '微空': 3, '3': 3,
                '小空': 2, '2': 2,
                '中空': 1, '1': 1,
                '大空': 0, '0': 0,  # 大空为0（最低级）
                # 其他常见评级
                '强烈推荐': 7, '推荐': 6, '买入': 5, '增持': 4,
                '中性': 3, '持有': 3, '减持': 2, '卖出': 1, '强烈不推荐': 0,
                # 处理"-"和空值
                '-': 3, '': 3, 'None': 3, 'null': 3
            }
            
            rating_str = str(rating_str).strip()
            
            # 直接映射
            if rating_str in rating_map:
                return float(rating_map[rating_str])
            
            # 尝试数值转换
            try:
                num_val = float(rating_str)
                if num_val < 0:
                    return 0.0  # 负数映射到0
                elif num_val <= 7:
                    return num_val  # 保留小数
                else:
                    return 7.0  # 超过7的映射到7
            except ValueError:
                pass
            
            # 默认中性评级
            return 3.0
            
        except Exception:
            return 3.0
    
    def _get_rating_files(self):
        """获取评级文件列表"""
        try:
            import os
            import glob
            
            # 查找可能的评级文件
            rating_files = []
            
            # 查找当前目录下的评级文件
            patterns = [
                "*.json.gz",
                "*Data*.json.gz", 
                "CN_Data*.json.gz",
                "HK_Data*.json.gz",
                "US_Data*.json.gz"
            ]
            
            for pattern in patterns:
                files = glob.glob(pattern)
                rating_files.extend(files)
            
            return rating_files[:3]  # 最多检查3个文件
            
        except Exception as e:
            print(f"[ERROR] 获取评级文件列表失败: {e}")
            return []
    
    def _load_rating_from_file(self, stock_code, file_path):
        """从文件中加载股票评级数据"""
        try:
            import json
            import gzip
            from datetime import datetime, timedelta
            
            # 读取压缩JSON文件
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'data' not in data:
                return []
            
            # 查找股票数据
            for record in data['data']:
                if record.get('股票代码') == stock_code:
                    # 提取评级数据
                    rating_data = []
                    for key, value in record.items():
                        if isinstance(key, str) and len(key) == 8 and key.isdigit():  # YYYYMMDD格式
                            if value and str(value).strip() not in ['-', 'nan', '']:
                                # 转换日期格式
                                formatted_date = f"{key[:4]}-{key[4:6]}-{key[6:8]}"
                                numeric_rating = self._convert_rating_to_numeric(str(value).strip())
                                rating_data.append((formatted_date, numeric_rating))
                    
                    if rating_data:
                        # 按日期排序，取最近38天
                        rating_data.sort(key=lambda x: x[0])
                        return rating_data[-38:]
            
            return []
            
        except Exception as e:
            print(f"[ERROR] 从文件 {file_path} 加载评级失败: {e}")
            return []
    
    def _calculate_industry_average_ratings(self, all_stock_ratings):
        """计算行业平均评级"""
        try:
            from datetime import datetime, timedelta
            from collections import defaultdict
            
            print(f" 开始计算行业平均评级，包含 {len(all_stock_ratings)} 只股票")
            
            # 按日期收集所有股票的评级
            daily_ratings = defaultdict(list)
            
            for stock_code, ratings in all_stock_ratings.items():
                for date_str, rating in ratings:
                    daily_ratings[date_str].append(rating)
            
            # 计算每日平均评级
            industry_ratings = []
            for date_str in sorted(daily_ratings.keys())[-38:]:  # 最近38天
                ratings_for_date = daily_ratings[date_str]
                if ratings_for_date:
                    # 计算平均值，保留2位小数
                    avg_rating = sum(ratings_for_date) / len(ratings_for_date)
                    # 保留2位小数，不再四舍五入到整数
                    final_rating = round(avg_rating, 2)
                    # 确保评级在1-7范围内
                    final_rating = max(1.0, min(7.0, final_rating))
                    industry_ratings.append((date_str, final_rating))
                    
                    print(f"  📅 {date_str}: {len(ratings_for_date)}只股票，平均评级 {avg_rating:.2f} -> {final_rating}")
            
            print(f" 计算完成，获得 {len(industry_ratings)} 天的行业平均评级")
            return industry_ratings
            
        except Exception as e:
            print(f"[ERROR] 计算行业平均评级失败: {e}")
            return []
    

    
    def calculate_industry_averages(self, industry_stocks):
        """计算行业加权平均值数据（按成交金额加权）"""
        try:
            if not industry_stocks:
                print("[ERROR] 行业股票列表为空")
                return {}
            
            print(f" 开始计算 {len(industry_stocks)} 只股票的加权平均值")
            
            # 获取每只股票的成交金额作为权重
            stock_weights = []
            total_weight = 0
            weighted_rtsi_sum = 0
            
            for i, stock in enumerate(industry_stocks):
                stock_code = stock.get('code', '')
                rtsi_data = stock.get('rtsi', {})
                if isinstance(rtsi_data, dict):
                    rtsi_value = rtsi_data.get('rtsi', 0)
                else:
                    rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
                
                # 获取成交金额作为权重
                weight = self.get_stock_current_volume(stock_code)
                if weight <= 0:
                    # 基于RTSI计算默认权重，避免所有权重都相同
                    weight = max(1000000, rtsi_value * 50000)  # RTSI越高权重越大
                
                stock_weights.append({
                    'stock': stock,
                    'rtsi': rtsi_value,
                    'weight': weight,
                    'code': stock_code,
                    'is_index': stock.get('is_index', False),  # 保留指数标识
                    'name': stock.get('name', stock_code)      # 保留名称
                })
                
                if rtsi_value > 0:
                    weighted_rtsi_sum += rtsi_value * weight
                    total_weight += weight
                
                print(f"  股票 {i+1}: {stock_code} RTSI={rtsi_value} 权重={weight:,.0f}")
            
            # 计算加权平均RTSI
            avg_rtsi = weighted_rtsi_sum / total_weight if total_weight > 0 else 0
            print(f" 加权平均RTSI: {avg_rtsi:.2f} (总权重: {total_weight:,.0f})")
            
            # 生成基于真实数据的加权平均量价数据
            volume_price_data = self._calculate_weighted_volume_price_data(stock_weights)
            
            # 生成评级数据（基于真实个股评级数据，不使用插值）
            rating_data = self._get_real_industry_rating_data(industry_stocks)
            
            if not rating_data:
                print("  无法获取真实评级数据，返回空数据")
                # 如果无法获取真实数据，直接返回空数据
                return []
            
            print(f" 获取了{len(rating_data)}天的真实评级数据")
            
            return {
                'avg_rtsi': avg_rtsi,
                'stock_count': len(industry_stocks),
                'volume_price_data': volume_price_data,
                'rating_data': rating_data,
                'stocks': industry_stocks
            }
            
        except Exception as e:
            print(f"[ERROR] 计算行业平均值失败: {e}")
            return {}
    
    def _calculate_weighted_volume_price_data(self, stock_weights):
        """计算加权平均量价数据"""
        try:
            print(" 开始计算加权平均量价数据...")
            
            # 收集所有股票的历史数据
            all_stock_data = {}
            date_set = set()
            
            for stock_info in stock_weights:
                stock_code = stock_info['code']
                weight = stock_info['weight']
                
                print(f"   获取 {stock_code} 的历史数据...")
                
                # 尝试从LJ数据读取器获取历史数据
                try:
                    from utils.lj_data_reader import LJDataReader
                    lj_reader = LJDataReader()
                    
                    # 使用全局市场类型，不进行自动推测
                    market = self._get_current_market_type()
                    print(f"    🌍 使用全局市场类型: {market.upper()}")
                    
                    # 对于指数，尝试使用名称查找
                    search_key = stock_code
                    if stock_info.get('is_index', False) and 'name' in stock_info:
                        index_name = stock_info['name']
                        print(f"     指数数据查找: 代码 {stock_code} -> 名称 {index_name}")
                        search_key = index_name
                    
                    # 根据数据类型选择查找方式
                    if stock_info.get('is_index', False):
                        # 指数：严格使用名称向.dat.gz获取数据
                        print(f"     指数使用名称查找: {search_key}")
                        volume_data = lj_reader.get_volume_price_data(search_key, days=38, market=market)
                    else:
                        # 个股：使用代码向.dat.gz获取数据
                        print(f"     个股使用代码查找: {stock_code}")
                        volume_data = lj_reader.get_volume_price_data(stock_code, days=38, market=market)
                    
                    if volume_data and 'data' in volume_data and volume_data['data']:
                        stock_history = {}
                        for day_data in volume_data['data']:
                            date = day_data.get('date', '')
                            if date:
                                stock_history[date] = {
                                    'close': day_data.get('close_price', 0),  # 修正字段名
                                    'open': day_data.get('open_price', 0),    # 修正字段名
                                    'high': day_data.get('high_price', 0),    # 修正字段名
                                    'low': day_data.get('low_price', 0),      # 修正字段名
                                    'volume': day_data.get('volume', 0),
                                    'amount': day_data.get('amount', 0),
                                    'weight': weight
                                }
                                date_set.add(date)
                        
                        all_stock_data[stock_code] = stock_history
                        print(f"     获取到 {len(stock_history)} 天数据")
                    else:
                        print(f"    [ERROR] 未获取到 {stock_code} 的历史数据")
                        
                except Exception as e:
                    print(f"      获取 {stock_code} 历史数据失败: {e}")
            
            if not date_set:
                print("[ERROR] 未获取到任何历史数据，返回空数据")
                return []
            
            # 按日期排序
            sorted_dates = sorted(date_set)
            print(f"📅 共获取到 {len(sorted_dates)} 个交易日的数据")
            
            # 计算每日加权平均值和涨跌幅
            volume_price_data = []
            first_day_prices = {}  # 存储每只股票第一天的价格，用于计算涨跌幅
            
            # 先获取第一天的价格作为基准
            first_date = sorted_dates[0] if sorted_dates else None
            if first_date:
                for stock_code, stock_history in all_stock_data.items():
                    if first_date in stock_history:
                        first_day_prices[stock_code] = stock_history[first_date]['close']
                        print(f"     {stock_code} 基准价格: {first_day_prices[stock_code]}")
            
            for date in sorted_dates:
                daily_data = {
                    'date': date,
                    'close_price': 0,
                    'change_rate': 0,  # 涨跌幅
                    'volume': 0,
                    'amount': 0
                }
                
                total_weight = 0
                weighted_close = 0
                weighted_change_rate = 0
                total_volume = 0
                total_amount = 0
                
                # 计算当日所有股票的加权平均
                for stock_code, stock_history in all_stock_data.items():
                    if date in stock_history:
                        day_info = stock_history[date]
                        weight = day_info['weight']
                        current_price = day_info['close']
                        
                        # 计算涨跌幅
                        if stock_code in first_day_prices and first_day_prices[stock_code] > 0:
                            change_rate = ((current_price - first_day_prices[stock_code]) / first_day_prices[stock_code]) * 100
                        else:
                            change_rate = 0
                        
                        weighted_close += current_price * weight
                        weighted_change_rate += change_rate * weight
                        total_volume += day_info['volume']
                        total_amount += day_info['amount']
                        total_weight += weight
                
                if total_weight > 0:
                    daily_data['close_price'] = round(weighted_close / total_weight, 2)
                    daily_data['change_rate'] = round(weighted_change_rate / total_weight, 2)
                    daily_data['volume'] = int(total_volume)
                    daily_data['amount'] = int(total_amount)
                
                volume_price_data.append(daily_data)
            
            print(f" 生成了 {len(volume_price_data)} 天的加权平均量价数据")
            return volume_price_data
            
        except Exception as e:
            print(f"[ERROR] 计算加权量价数据失败: {e}")
            return []
    

    
    def _process_rating_data(self, rating_data):
        """处理评级数据，转换格式并排序"""
        try:
            processed_ratings = []
            
            for date_str, rating_str in rating_data:
                # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
                if len(date_str) == 8 and date_str.isdigit():
                    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                else:
                    formatted_date = date_str
                
                # 转换评级为数值
                numeric_rating = self._convert_rating_to_numeric(rating_str)
                if numeric_rating > 0:
                    processed_ratings.append((formatted_date, numeric_rating))
            
            # 按日期排序，取最近38天
            processed_ratings.sort(key=lambda x: x[0])
            recent_ratings = processed_ratings[-38:] if len(processed_ratings) > 38 else processed_ratings
            
            print(f"   处理后获得 {len(recent_ratings)} 条有效评级数据")
            return recent_ratings
            
        except Exception as e:
            print(f"[ERROR] 处理评级数据失败: {e}")
            return []
    

    
    def generate_industry_chart_html(self, industry_name, industry_data):
        """生成行业趋势图表HTML"""
        try:
            from datetime import datetime
            
            avg_rtsi = industry_data.get('avg_rtsi', 0)
            stock_count = industry_data.get('stock_count', 0)
            volume_price_data = industry_data.get('volume_price_data', [])
            rating_data = industry_data.get('rating_data', [])
            
            # 准备图表数据
            dates = [f"'{item['date']}'" for item in volume_price_data]
            change_rates = [item.get('change_rate', 0) for item in volume_price_data]  # 涨跌幅数据
            volumes = [item['volume'] for item in volume_price_data]
            
            rating_dates = [f"'{item[0]}'" for item in rating_data]
            ratings = [item[1] for item in rating_data]
            
            # 转换为JSON格式字符串
            import json
            dates_json = json.dumps([item['date'] for item in volume_price_data])
            change_rates_json = json.dumps(change_rates)  # 涨跌幅JSON数据
            volumes_json = json.dumps(volumes)
            rating_dates_json = json.dumps([item[0] for item in rating_data])
            ratings_json = json.dumps(ratings)
            
            # 生成HTML
            html_content = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{industry_name} - 行业趋势分析</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
                <script>
                    // 备用CDN加载
                    if (typeof Chart === 'undefined') {{
                        console.log('主CDN失败，尝试备用CDN...');
                        const script = document.createElement('script');
                        script.src = 'https://unpkg.com/chart.js@3.9.1/dist/chart.min.js';
                        script.onload = function() {{
                            console.log('备用CDN加载成功');
                            if (typeof initCharts === 'function') initCharts();
                        }};
                        script.onerror = function() {{
                            console.error('所有CDN都加载失败');
                            document.body.innerHTML = '<div style="text-align:center;padding:50px;color:#dc3545;"><h3>图表加载失败</h3><p>无法加载Chart.js库，请检查网络连接</p></div>';
                        }};
                        document.head.appendChild(script);
                    }} else {{
                        console.log('Chart.js加载成功');
                        if (typeof initCharts === 'function') initCharts();
                    }}
                </script>
                <style>
                    body {{
                        font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f8f9fa;
                        color: #333;
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                        padding: 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border-radius: 10px;
                    }}
                    .info-grid {{
                        display: grid;
                        grid-template-columns: repeat(4, 1fr);
                        gap: 10px;
                        margin-bottom: 30px;
                    }}
                    .info-card {{
                        background: white;
                        padding: 10px 8px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        text-align: center;
                    }}
                    .info-label {{
                        font-size: 11px;
                        color: #666;
                        margin-bottom: 3px;
                    }}
                    .info-value {{
                        font-size: 16px;
                        font-weight: bold;
                        color: #0078d4;
                    }}
                    .chart-container {{
                        background: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        margin-bottom: 20px;
                    }}
                    .chart-title {{
                        font-size: 16px;
                        font-weight: bold;
                        margin-bottom: 15px;
                        color: #333;
                        text-align: center;
                    }}
                    canvas {{
                        max-height: 300px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1> {industry_name} 行业趋势分析</h1>
                    <p>基于行业内 {stock_count} 只股票的平均数据</p>
                </div>
                
                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-label">行业平均RTSI</div>
                        <div class="info-value" style="color: {'#28a745' if avg_rtsi > 60 else '#dc3545' if avg_rtsi < 40 else '#ffc107'};">{avg_rtsi:.2f}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">包含股票数量</div>
                        <div class="info-value">{stock_count} 只</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">数据周期</div>
                        <div class="info-value">38 天</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">更新时间</div>
                        <div class="info-value">{datetime.now().strftime('%m-%d %H:%M')}</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">⭐ 行业平均评级趋势</div>
                    <canvas id="ratingChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title"> 行业加权涨跌幅走势</div>
                    <canvas id="changeRateChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title"> 行业平均成交量</div>
                    <canvas id="volumeChart"></canvas>
                </div>
                
                <script>
                    function initCharts() {{
                        try {{
                            console.log('开始初始化图表...');
                            
                            // 检查数据
                            const dates = {dates_json};
                            const changeRates = {change_rates_json};
                            const volumes = {volumes_json};
                            const ratingDates = {rating_dates_json};
                            const ratings = {ratings_json};
                            
                            console.log('数据检查:', {{
                                dates: dates.length,
                                changeRates: changeRates.length,
                                volumes: volumes.length,
                                ratingDates: ratingDates.length,
                                ratings: ratings.length
                            }});
                            
                            // 涨跌幅走势图
                            const changeRateCtx = document.getElementById('changeRateChart').getContext('2d');
                            const changeRateChart = new Chart(changeRateCtx, {{
                                type: 'line',
                                data: {{
                                    labels: dates,
                                    datasets: [{{
                                        label: '加权涨跌幅(%)',
                                        data: changeRates,
                                        borderColor: '#ff6b6b',
                                        backgroundColor: 'rgba(255, 107, 107, 0.1)',
                                        borderWidth: 2,
                                        fill: true,
                                        tension: 0.4
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    scales: {{
                                        y: {{
                                            beginAtZero: true,
                                            title: {{
                                                display: true,
                                                text: '涨跌幅 (%)'
                                            }},
                                            ticks: {{
                                                callback: function(value) {{
                                                    return value.toFixed(2) + '%';
                                                }}
                                            }}
                                        }},
                                        x: {{
                                            title: {{
                                                display: true,
                                                text: '日期'
                                            }}
                                        }}
                                    }},
                                    plugins: {{
                                        legend: {{
                                            display: true
                                        }}
                                    }}
                                }}
                            }});
                            console.log('价格图表创建成功');
                            
                            // 成交量图
                            const volumeCtx = document.getElementById('volumeChart').getContext('2d');
                            const volumeChart = new Chart(volumeCtx, {{
                                type: 'bar',
                                data: {{
                                    labels: dates,
                                    datasets: [{{
                                        label: '平均成交量',
                                        data: volumes,
                                        backgroundColor: 'rgba(40, 167, 69, 0.6)',
                                        borderColor: '#28a745',
                                        borderWidth: 1
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    scales: {{
                                        y: {{
                                            beginAtZero: true,
                                            title: {{
                                                display: true,
                                                text: '成交量'
                                            }}
                                        }},
                                        x: {{
                                            title: {{
                                                display: true,
                                                text: '日期'
                                            }}
                                        }}
                                    }},
                                    plugins: {{
                                        legend: {{
                                            display: true
                                        }}
                                    }}
                                }}
                            }});
                            console.log('成交量图表创建成功');
                            
                            // 评级趋势图
                            const ratingCtx = document.getElementById('ratingChart').getContext('2d');
                            const ratingChart = new Chart(ratingCtx, {{
                                type: 'line',
                                data: {{
                                    labels: ratingDates,
                                    datasets: [{{
                                        label: '平均评级',
                                        data: ratings,
                                        borderColor: '#ff6b6b',
                                        backgroundColor: 'rgba(255, 107, 107, 0.1)',
                                        borderWidth: 2,
                                        fill: true,
                                        tension: 0,  // 不使用插值平滑，显示真实的离散数据点
                                        stepped: false  // 不使用阶梯线，但保持直线连接
                                    }}]
                                }},
                                options: {{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    scales: {{
                                        y: {{
                                            beginAtZero: true,
                                            min: 0,
                                            max: 7,
                                            reverse: false,
                                            title: {{
                                                display: true,
                                                text: '评级 (7=大多, 0=大空)'
                                            }}
                                        }},
                                        x: {{
                                            title: {{
                                                display: true,
                                                text: '日期'
                                            }}
                                        }}
                                    }},
                                    plugins: {{
                                        legend: {{
                                            display: true
                                        }}
                                    }}
                                }}
                            }});
                            console.log('评级图表创建成功');
                            
                        }} catch (error) {{
                            console.error('图表创建失败:', error);
                            document.body.innerHTML = '<div style="text-align:center;padding:50px;color:#dc3545;"><h3>图表创建失败</h3><p>' + error.message + '</p></div>';
                        }}
                    }}
                    
                    // 页面加载完成后初始化图表
                    document.addEventListener('DOMContentLoaded', function() {{
                        console.log('DOM加载完成');
                        if (typeof Chart !== 'undefined') {{
                            initCharts();
                        }} else {{
                            console.log('等待Chart.js加载...');
                        }}
                    }});
                </script>
                
                <!-- 风险警告 -->
                {self.get_risk_warning_html()}
            </body>
            </html>
            """
            
            return html_content
            
        except Exception as e:
            print(f"[ERROR] 生成行业图表HTML失败: {e}")
            return f"<p style='color: #dc3545;'>生成行业图表失败: {str(e)}</p>"
    
    def set_industry_chart_html(self, html_content):
        """设置行业趋势图表HTML内容"""
        try:
            # 停止等待动画并切换到结果页面
            self.stop_industry_loading_animation()  # 停止等待动画
            if hasattr(self, 'industry_chart_stacked_widget'):
                self.industry_chart_stacked_widget.setCurrentIndex(2)  # 切换到结果页面
            
            if hasattr(self, 'industry_chart_webview'):
                self.industry_chart_webview.setHtml(html_content)
            elif hasattr(self, 'industry_chart_text'):
                self.industry_chart_text.setHtml(html_content)
        except Exception as e:
            print(f"[ERROR] 设置行业图表HTML失败: {e}")
    
    def log(self, message: str, level: str = "INFO"):
        """日志输出方法"""
        if hasattr(self, 'verbose') and self.verbose:
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level}: {message}")
        
    def get_rtsi_zone(self, rtsi_value):
        """获取RTSI区间描述"""
        if rtsi_value >= 80:
            return "强势上升区间"
        elif rtsi_value >= 60:
            return "温和上升区间"
        elif rtsi_value >= 40:
            return "震荡整理区间"
        elif rtsi_value >= 20:
            return "弱势下降区间"
        else:
            return "强势下降区间"
            
    def get_trend_strength(self, rtsi_value):
        """获取趋势强度描述"""
        if rtsi_value >= 80:
            return "极强"
        elif rtsi_value >= 60:
            return "较强"
        elif rtsi_value >= 40:
            return "中等"
        elif rtsi_value >= 20:
            return "较弱"
        else:
            return "极弱"
            
    def get_operation_suggestion(self, rtsi_value):
        """获取操作建议"""
        if rtsi_value >= 80:
            return "积极持有，注意高位风险"
        elif rtsi_value >= 60:
            return "适合持有，可逢低加仓"
        elif rtsi_value >= 40:
            return "观望为主，等待明确信号"
        elif rtsi_value >= 20:
            return "谨慎持有，考虑减仓"
        else:
            return "避免新增，建议止损"
            
    def update_detailed_stock_analysis(self, stock_code, stock_name, stock_info):
        """更新详细股票分析 - 完全按照旧版8个部分格式"""
        if not hasattr(self, 'stock_detail_text'):
            return
            
        # 提取数据 - 支持ARTS和RTSI算法
        rtsi_data = stock_info.get('rtsi', {})
        
        # 检测算法类型
        algorithm_type = "RTSI"
        if isinstance(rtsi_data, dict):
            algorithm = rtsi_data.get('algorithm', 'unknown')
            if algorithm == 'ARTS_v1.0':
                algorithm_type = "ARTS"
                score = rtsi_data.get('rtsi', 0)
                rating_level = rtsi_data.get('rating_level', 'unknown')
                pattern = rtsi_data.get('pattern', 'unknown')
                confidence_str = rtsi_data.get('confidence', 'unknown')
                recommendation = rtsi_data.get('recommendation', '')
                trend_direction = rtsi_data.get('trend', 'unknown')
                
                # 兼容性：将ARTS数据映射到RTSI格式用于旧方法
                rtsi_value = score
                confidence = 0.7 if confidence_str in ['高', '极高'] else 0.5 if confidence_str == '中等' else 0.3
                slope = 0.1 if 'upward' in trend_direction or '上升' in trend_direction else -0.1 if 'downward' in trend_direction or '下降' in trend_direction else 0
            elif algorithm == 'ARTS_v1.0_backup':
                algorithm_type = "ARTS(后备)"
                score = rtsi_data.get('rtsi', 0)
                rating_level = rtsi_data.get('rating_level', 'unknown')
                pattern = rtsi_data.get('pattern', 'unknown')
                confidence_str = rtsi_data.get('confidence', 'unknown')
                recommendation = rtsi_data.get('recommendation', '')
                trend_direction = rtsi_data.get('trend', 'unknown')
                
                # 兼容性：将ARTS数据映射到RTSI格式用于旧方法
                rtsi_value = score
                confidence = 0.7 if confidence_str in ['高', '极高'] else 0.5 if confidence_str == '中等' else 0.3
                slope = 0.1 if 'upward' in trend_direction or '上升' in trend_direction else -0.1 if 'downward' in trend_direction or '下降' in trend_direction else 0
            elif algorithm == '优化标准RTSI':
                algorithm_type = "优化标准RTSI"
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
            elif algorithm == '优化增强RTSI':
                algorithm_type = "优化增强RTSI"
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
            elif algorithm == '增强RTSI':
                algorithm_type = "增强RTSI"
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
            elif algorithm == 'ai_enhanced':
                algorithm_type = "AI增强RTSI"
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
            elif algorithm == 'ai_enhanced_best':
                algorithm_type = "AI增强RTSI(最佳)"
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
            elif algorithm == 'RTSI':
                algorithm_type = "RTSI"
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
            else:
                rtsi_value = rtsi_data.get('rtsi', 0)
                confidence = rtsi_data.get('confidence', 0.5)
                slope = rtsi_data.get('slope', 0)
                # 设置默认值以避免错误
                rating_level = ""
                pattern = ""
                confidence_str = ""
                recommendation = ""
                trend_direction = ""
        else:
            rtsi_value = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
            confidence = 0.5
            slope = 0
            # 设置默认值
            rating_level = ""
            pattern = ""
            confidence_str = ""
            recommendation = ""
            trend_direction = ""
            
        industry = stock_info.get('industry', t_gui('uncategorized'))
        
        # 计算更多指标 - 移植自旧版
        volatility = self.calculate_volatility(stock_info)
        market_cap_level = self.estimate_market_cap_level(stock_code)
        sector_performance = self.get_sector_performance(industry)
        
                # 生成完整分析报告 - 优化排版，使用HTML格式支持粗体标题
        from datetime import datetime
        
        # 构建HTML格式的分析报告
        analysis_html = f"""
        <div style="font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 5px;">
                {stock_name} ({stock_code}) {t_gui('comprehensive_analysis_report')}
            </h2>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('core_indicators')}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('stock_code')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{stock_code}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('stock_name')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{stock_name}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('industry_sector')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{industry}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('analysis_algorithm')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: #2c5aa0;"><strong> {algorithm_type}</strong></td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('arts_score') if algorithm_type == 'ARTS' else t_gui('rtsi_index')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {'#dc3545' if rtsi_value > 50 else '#28a745'};"><strong>{rtsi_value:.2f}/90</strong></td></tr>
                {"<tr><td style='padding: 5px; border-bottom: 1px solid #eee;'><strong>" + t_gui('rating_level') + ":</strong></td><td style='padding: 5px; border-bottom: 1px solid #eee;'>" + rating_level + "</td></tr>" if algorithm_type == 'ARTS' and rating_level else ""}
                {"<tr><td style='padding: 5px; border-bottom: 1px solid #eee;'><strong>" + t_gui('trend_pattern') + ":</strong></td><td style='padding: 5px; border-bottom: 1px solid #eee;'>" + pattern + "</td></tr>" if algorithm_type == 'ARTS' and pattern else ""}
                {"<tr><td style='padding: 5px; border-bottom: 1px solid #eee;'><strong>" + t_gui('confidence_level') + ":</strong></td><td style='padding: 5px; border-bottom: 1px solid #eee;'>" + confidence_str + "</td></tr>" if algorithm_type == 'ARTS' and confidence_str else ""}

            </table>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('technical_analysis')}</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #0078d4;">
                    <h4 style="color: #0078d4; margin-top: 0;"> 技术面核心指标</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>{t_gui('trend_direction')}:</strong> {self.get_detailed_trend(rtsi_value)}</li>
                        <li><strong>{t_gui('technical_strength')}:</strong> {self.get_tech_strength(rtsi_value)}</li>
                        <li><strong>{t_gui('volatility_level')}:</strong> {self.get_volatility_display(volatility)}</li>
                        <li><strong>动量指标:</strong> {self.get_momentum_indicator(rtsi_value)}</li>
                    </ul>
                </div>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                    <h4 style="color: #28a745; margin-top: 0;"> 相对强弱分析</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>{t_gui('relative_strength')}:</strong> {self.get_relative_position(rtsi_value)}</li>
                        <li><strong>行业排名:</strong> {self.get_industry_ranking_detail(rtsi_value)}</li>
                        <li><strong>市场表现:</strong> {self.get_market_performance(rtsi_value)}</li>
                        <li><strong>资金流向:</strong> {self.get_fund_flow_indicator(rtsi_value)}</li>
                    </ul>
                </div>
            </div>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🏭 {t_gui('industry_comparison')}</h3>
            <div style="background: linear-gradient(135deg, #e8f4fd 0%, #f0f8ff 100%); padding: 20px; border-radius: 10px; border: 1px solid #0078d4;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <h4 style="color: #0078d4; margin-top: 0; margin-bottom: 10px;"> 行业地位分析</h4>
                        <ul style="margin: 0; padding-left: 20px;">
                            <li><strong>{t_gui('行业表现')}:</strong> {sector_performance}</li>
                            <li><strong>{t_gui('industry_position')}:</strong> {self.get_industry_position(rtsi_value)}</li>
                            <li><strong>行业估值:</strong> {self.get_industry_valuation(industry)}</li>
                        </ul>
                    </div>
                    <div>
                        <h4 style="color: #0078d4; margin-top: 0; margin-bottom: 10px;">🔄 轮动机会分析</h4>
                        <ul style="margin: 0; padding-left: 20px;">
                            <li><strong>{t_gui('rotation_signal')}:</strong> {self.get_rotation_signal(rtsi_value)}</li>
                            <li><strong>{t_gui('industry_ranking')}:</strong> {self.get_industry_ranking(rtsi_value)}</li>
                            <li><strong>催化因素:</strong> {self.get_industry_catalysts(industry)}</li>
                        </ul>
                    </div>
                </div>
            </div>
            

            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('risk_assessment')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('risk_level')}:</strong> <span style="color: {'#28a745' if rtsi_value < 30 else '#ffc107' if rtsi_value < 60 else '#dc3545'};">{self.calculate_risk_level(rtsi_value, confidence)}</span></li>
                <li><strong>{t_gui('technical_risk')}:</strong> {t_gui('based_on_rtsi_assessment')}</li>
                <li><strong>{t_gui('liquidity_risk')}:</strong> {self.get_liquidity_level_display(market_cap_level)}</li>
                <li><strong>{t_gui('market_risk')}:</strong> {t_gui('pay_attention_to_systemic_risk')}</li>
            </ul>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;"> {t_gui('operation_advice')}</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <h4 style="color: #856404; margin-top: 0;">📍 进场策略</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{t_gui('best_entry_point')}:</strong> {self.suggest_entry_point(rtsi_value)}</li>
                        <li><strong>分批建仓:</strong> {self.suggest_position_building(rtsi_value)}</li>
                        <li><strong>最佳时机:</strong> {self.suggest_timing(rtsi_value)}</li>
                    </ul>
                </div>
                <div style="background: #f8d7da; padding: 15px; border-radius: 8px; border-left: 4px solid #dc3545;">
                    <h4 style="color: #721c24; margin-top: 0;">🛡️ 风险控制</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{t_gui('stop_loss_position')}:</strong> {self.suggest_stop_loss(rtsi_value)}</li>
                        <li><strong>仓位管理:</strong> {self.suggest_position_size(rtsi_value)}</li>
                        <li><strong>风险预警:</strong> {self.get_risk_warning(rtsi_value)}</li>
                    </ul>
                </div>
                <div style="background: #d4edda; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                    <h4 style="color: #155724; margin-top: 0;"> 盈利目标</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li><strong>{t_gui('target_price')}:</strong> {self.suggest_target_price(rtsi_value)}</li>
                        <li><strong>{t_gui('holding_period')}:</strong> {self.suggest_holding_period(rtsi_value)}</li>
                        <li><strong>止盈策略:</strong> {self.suggest_profit_taking(rtsi_value)}</li>
                    </ul>
                </div>
            </div>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🔮 {t_gui('future_outlook')}</h3>
            <p style="margin-left: 20px; line-height: 1.8;">{self.generate_outlook_display(rtsi_value, industry)}</p>
            
            {"<h3 style='color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;'> " + t_gui('arts_algorithm_advantages') + "</h3><ul style='margin-left: 20px;'><li><strong>" + t_gui('dynamic_weighting') + ":</strong> " + t_gui('recent_data_higher_weight') + "</li><li><strong>" + t_gui('pattern_recognition') + ":</strong> " + t_gui('can_identify_complex_patterns', pattern=pattern) + "</li><li><strong>" + t_gui('confidence_assessment') + ":</strong> " + t_gui('provides_reliability_assessment', confidence=confidence_str) + "</li><li><strong>" + t_gui('adaptive_adjustment') + ":</strong> " + t_gui('dynamically_optimize_based_on_characteristics') + "</li><li><strong>" + t_gui('eight_level_rating') + ":</strong> " + t_gui('more_scientific_grading_system') + "</li></ul>" if algorithm_type == 'ARTS' else ""}
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-top: 25px;">
                <h4 style="color: #856404; margin-top: 0;"> {t_gui('disclaimer')}</h4>
                <p style="color: #856404; margin-bottom: 0; font-size: 12px;">
                    {t_gui('disclaimer_text', algorithm_type=algorithm_type, algorithm_desc=t_gui('arts_algorithm_desc') if algorithm_type == 'ARTS' else '')}
                </p>
            </div>
            
            <p style="text-align: right; color: #6c757d; font-size: 12px; margin-top: 20px;">
                {t_gui('generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        """
        
        # 显示HTML格式的分析结果
        self.set_stock_detail_html(analysis_html)
    
    # 以下方法移植自旧版main_window.py，用于支持详细分析
    def get_trend_description(self, rtsi_value):
        """获取趋势描述"""
        if rtsi_value >= 80:
            return "强势上升"
        elif rtsi_value >= 60:
            return "强势上升"
        elif rtsi_value >= 40:
            return "震荡整理"
        elif rtsi_value >= 20:
            return "弱势下降"
        else:
            return "深度调整"
    
    def get_momentum_indicator(self, rtsi_value):
        """获取动量指标"""
        if rtsi_value > 65:
            return '<span style="color: #dc3545; font-weight: bold;"> 强劲上涨动量</span>'
        elif rtsi_value > 50:
            return '<span style="color: #fd7e14; font-weight: bold;"> 积极上涨动量</span>'
        elif rtsi_value > 35:
            return '<span style="color: #6c757d;"> 震荡整理</span>'
        else:
            return '<span style="color: #28a745; font-weight: bold;">📉 下跌动量</span>'
    
    def get_industry_ranking_detail(self, rtsi_value):
        """获取详细行业排名"""
        if rtsi_value > 60:
            return '<span style="color: #dc3545; font-weight: bold;">行业前20%</span>'
        elif rtsi_value > 45:
            return '<span style="color: #fd7e14;">行业前50%</span>'
        elif rtsi_value > 30:
            return '<span style="color: #6c757d;">行业中游</span>'
        else:
            return '<span style="color: #28a745;">行业后30%</span>'
    
    def get_market_performance(self, rtsi_value):
        """获取市场表现"""
        if rtsi_value > 55:
            return '<span style="color: #dc3545; font-weight: bold;">跑赢大盘</span>'
        elif rtsi_value > 40:
            return '<span style="color: #6c757d;">与大盘同步</span>'
        else:
            return '<span style="color: #28a745;">跑输大盘</span>'
    
    def get_fund_flow_indicator(self, rtsi_value):
        """获取资金流向指标"""
        if rtsi_value > 60:
            return '<span style="color: #dc3545; font-weight: bold;"> 资金净流入</span>'
        elif rtsi_value > 40:
            return '<span style="color: #6c757d;">💧 资金平衡</span>'
        else:
            return '<span style="color: #28a745;">💸 资金净流出</span>'
    
    def get_industry_valuation(self, industry):
        """获取行业估值"""
        # 简化实现，实际应该基于真实数据
        return '<span style="color: #0078d4;">相对合理</span>'
    
    def get_industry_catalysts(self, industry):
        """获取行业催化因素"""
        catalysts_map = {
            '银行': '货币政策、利率环境',
            '医药': '政策支持、创新药审批',
            '科技': '技术突破、政策扶持',
            '房地产': '政策调控、利率变化',
            '消费': '消费升级、政策刺激'
        }
        return catalysts_map.get(industry, '政策变化、行业周期')
    
    def suggest_position_building(self, rtsi_value):
        """建议分批建仓策略"""
        if rtsi_value > 60:
            return '谨慎分批，控制节奏'
        elif rtsi_value > 45:
            return '均匀分批，3-5次建仓'
        elif rtsi_value > 30:
            return '逢低分批，等待机会'
        else:
            return '暂缓建仓，观望为主'
    
    def suggest_timing(self, rtsi_value):
        """建议最佳时机"""
        if rtsi_value > 65:
            return '高位谨慎，等待回调'
        elif rtsi_value > 50:
            return '趋势向好，适时介入'
        elif rtsi_value > 35:
            return '震荡区间，波段操作'
        else:
            return '底部区域，耐心等待'
    
    def suggest_position_size(self, rtsi_value):
        """建议仓位大小"""
        if rtsi_value > 60:
            return '轻仓试探（10-20%）'
        elif rtsi_value > 45:
            return '标准仓位（20-40%）'
        elif rtsi_value > 30:
            return '适度仓位（15-30%）'
        else:
            return '观望为主（0-10%）'
    
    def get_risk_warning(self, rtsi_value):
        """获取风险预警"""
        if rtsi_value > 70:
            return '<span style="color: #dc3545; font-weight: bold;"> 高位风险</span>'
        elif rtsi_value > 55:
            return '<span style="color: #fd7e14;"> 适度风险</span>'
        elif rtsi_value > 35:
            return '<span style="color: #6c757d;"> 关注风险</span>'
        else:
            return '<span style="color: #28a745;"> 风险较低</span>'
    
    def suggest_profit_taking(self, rtsi_value):
        """建议止盈策略"""
        if rtsi_value > 65:
            return '分批止盈，保护利润'
        elif rtsi_value > 50:
            return '设置移动止盈'
        elif rtsi_value > 35:
            return '耐心持有，等待突破'
        else:
            return '暂无止盈压力'

    def get_tech_strength(self, rtsi_value):
        """获取技术强度 - 支持红涨绿跌颜色"""
        if rtsi_value > 60:
            return '<span style="color: #dc3545; font-weight: bold;">强势</span>'
        elif rtsi_value > 40:
            return '<span style="color: #6c757d;">中性</span>'
        else:
            return '<span style="color: #28a745;">弱势</span>'
    
    def get_detailed_trend(self, rtsi_value):
        """获取详细趋势分析 - 统一标准版本，支持红涨绿跌颜色"""
        if rtsi_value >= 75:
            return '<span style="color: #dc3545; font-weight: bold;">强势多头趋势</span>'
        elif rtsi_value >= 60:
            return '<span style="color: #dc3545;">温和多头趋势</span>'
        elif rtsi_value >= 50:
            return '<span style="color: #fd7e14;">弱势多头形态</span>'
        elif rtsi_value >= 40:
            return '<span style="color: #6c757d;">横盘整理</span>'
        elif rtsi_value >= 30:
            return '<span style="color: #20c997;">弱势空头形态</span>'
        elif rtsi_value >= 20:
            return '<span style="color: #28a745;">温和空头趋势</span>'
        else:
            return '<span style="color: #28a745; font-weight: bold;">强势空头趋势</span>'
    
    def calculate_volatility(self, stock_data):
        """计算波动程度"""
        return "中等波动"
    
    def get_volatility_display(self, volatility):
        """获取波动程度的国际化显示"""
        return t_gui('moderate_volatility')
    
    def estimate_market_cap_level(self, stock_code):
        """估算市值等级"""
        if stock_code.startswith('00'):
            return "大盘股"
        elif stock_code.startswith('60'):
            return "大盘股"
        elif stock_code.startswith('30'):
            return "成长股"
        else:
            return "中盘股"
    
    def get_sector_performance(self, industry):
        """获取行业表现"""
        return f"{industry} 行业表现中性"
    
    def get_relative_position(self, rtsi_value):
        """获取相对位置 - 支持红涨绿跌颜色"""
        if rtsi_value > 50:
            return '<span style="color: #dc3545;">领先</span>'
        else:
            return '<span style="color: #28a745;">滞后</span>'
    
    def get_industry_position(self, rtsi_value):
        """获取行业位置 - 支持红涨绿跌颜色"""
        if rtsi_value > 70:
            return '<span style="color: #dc3545; font-weight: bold;">蓝筹股</span>'
        elif rtsi_value > 40:
            return '<span style="color: #6c757d;">平均水平</span>'
        else:
            return '<span style="color: #28a745;">滞后股</span>'
    
    def get_rotation_signal(self, rtsi_value):
        """获取轮动信号 - 支持红涨绿跌颜色"""
        if rtsi_value > 60:
            return '<span style="color: #dc3545;">活跃</span>'
        elif rtsi_value > 30:
            return '<span style="color: #6c757d;">观望</span>'
        else:
            return '<span style="color: #28a745;">谨慎</span>'
    
    def get_short_term_advice(self, rtsi_value):
        """短线建议"""
        if rtsi_value >= 60:
            return "适度参与，关注量价配合"
        elif rtsi_value >= 40:
            return "观望为主，等待明确信号"
        else:
            return "避免抄底，等待反转"
    
    def get_medium_term_advice(self, rtsi_value, industry):
        """中线建议"""
        if rtsi_value >= 50:
            return f"可配置 {industry} 优质标的"
        else:
            return "等待更好配置机会"
    
    def get_risk_warning(self, rtsi_value):
        """风险提示"""
        if rtsi_value < 30:
            return "相对安全，关注回调风险"
        elif rtsi_value < 50:
            return "中等风险，控制仓位"
        else:
            return "相对安全，关注回调风险"
    
    def get_liquidity_level(self, market_cap_level):
        """获取流动性水平"""
        if market_cap_level != "中盘股":
            return "良好"
        else:
            return "一般"
    
    def get_liquidity_level_display(self, market_cap_level):
        """获取流动性水平的国际化显示"""
        if market_cap_level != "中盘股":
            return t_gui('good_liquidity')
        else:
            return t_gui('average_liquidity')
    
    def suggest_entry_point(self, rtsi_value):
        """建议入场点 - 支持红涨绿跌颜色和国际化"""
        if rtsi_value >= 60:
            return f'<span style="color: #dc3545;">{t_gui("pullback_to_support")}</span>'
        elif rtsi_value >= 40:
            return f'<span style="color: #fd7e14;">{t_gui("breakout_above_resistance")}</span>'
        else:
            return f'<span style="color: #28a745;">{t_gui("wait_for_reversal_signal")}</span>'
    
    def suggest_stop_loss(self, rtsi_value):
        """建议止损位 - 支持国际化"""
        if rtsi_value >= 50:
            return t_gui('below_recent_support')
        else:
            return t_gui('set_8_10_percent_stop_loss')
    
    def suggest_target_price(self, rtsi_value):
        """建议目标价 - 支持红涨绿跌颜色"""
        if rtsi_value >= 60:
            return '<span style="color: #dc3545; font-weight: bold;">目标前高或创新高</span>'
        elif rtsi_value >= 40:
            return '<span style="color: #fd7e14;">短期阻力位附近</span>'
        else:
            return '<span style="color: #28a745;">上涨空间有限</span>'
    
    def suggest_holding_period(self, rtsi_value):
        """建议持仓周期 - 支持红涨绿跌颜色 - 修复编码错误"""
        try:
            if rtsi_value >= 60:
                return '<span style="color: #dc3545;">Medium-Long Term 1-3 months</span>'
            elif rtsi_value >= 40:
                return '<span style="color: #fd7e14;">Short Term 1-2 weeks</span>'
            else:
                return '<span style="color: #28a745;">Not Recommended</span>'
        except Exception as e:
            print(f"Holding period suggestion error: {e}")
            return '<span style="color: #666;">Period suggestion unavailable</span>'
    
    def generate_outlook(self, rtsi_value, industry):
        """生成后市展望"""
        if rtsi_value >= 60:
            return f"技术分析显示 {industry} 行业及个股具备上涨潜力，建议关注基本面变化"
        elif rtsi_value >= 40:
            return f"股价处于整理期，需观察 {industry} 行业催化剂及成交量变化"
        else:
            return f"技术面分析偏弱，建议等待 {industry} 行业整体企稳后再配置"
    
    def generate_outlook_display(self, rtsi_value, industry):
        """生成后市展望的国际化显示"""
        if rtsi_value >= 60:
            return t_gui('technical_analysis_shows_upward_potential', industry=industry)
        elif rtsi_value >= 40:
            return t_gui('price_in_consolidation_phase', industry=industry)
        else:
            return t_gui('technical_analysis_weak', industry=industry)
    
    # 图表生成相关方法 - 移植自旧版
    def generate_realistic_chart_data(self, stock_code, rtsi_value):
        """获取真实历史数据用于图表展示"""
        from datetime import datetime, timedelta
        
        # 尝试获取真实历史数据
        real_data = self.get_real_historical_data(stock_code)
        
        if real_data and len(real_data) > 0:
            # 如果有真实数据，限制在90天内
            days = min(len(real_data), 90)
            print(f" 使用真实历史数据天数: {days}天 (限制90天内)")
        else:
            # 如果没有真实数据，返回空列表
            print(f" 无真实历史数据，跳过图表生成")
            return []
        
        # 直接使用真实数据，不需要生成日期和评级
        # 将真实数据格式化为(日期, 评级)元组列表
        formatted_data = []
        
        # 限制显示最近的days天数据
        real_data_limited = real_data[-days:] if len(real_data) > days else real_data
        
        for data_point in real_data_limited:
            if isinstance(data_point, (tuple, list)) and len(data_point) >= 2:
                date_str, rating = data_point[0], data_point[1]
                formatted_data.append((str(date_str), float(rating)))
            else:
                # 如果数据格式不正确，跳过
                continue
        
        print(f" 处理真实历史数据: {len(formatted_data)}个数据点")
        return formatted_data
        

    
    def get_real_historical_data(self, stock_code):
        """获取真实的历史评级数据 - 从原始数据集中提取"""
        try:
            # 尝试从多个数据源获取真实历史数据
            print(f" 正在查找股票 {stock_code} 的历史数据...")
            
            # 方法1：从analysis_results中的data_source获取（StockDataSet对象）
            if self.analysis_results and 'data_source' in self.analysis_results:
                data_source = self.analysis_results['data_source']
                if data_source and hasattr(data_source, 'get_stock_ratings'):
                    print(f" 尝试从data_source获取股票评级数据...")
                    try:
                        stock_ratings = data_source.get_stock_ratings(stock_code, use_interpolation=True)
                        if stock_ratings is not None and not stock_ratings.empty:
                            print(f"📋 股票评级数据长度: {len(stock_ratings)}")
                            
                            # 转换为历史数据格式 [(日期, 评级数字), ...]
                            historical_data = []
                            total_data_points = len(stock_ratings)
                            valid_data_points = 0
                            
                            for date_col, rating_value in stock_ratings.items():
                                if rating_value is not None and str(rating_value) not in ['nan', 'NaN', '', 'None', '-']:
                                    # 将文字评级转换为数字
                                    rating_num = self.convert_rating_to_number(rating_value)
                                    if rating_num is not None:
                                        historical_data.append((str(date_col), rating_num))
                                        valid_data_points += 1
                            
                            if historical_data:
                                print(f" 从data_source提取到 {len(historical_data)} 个历史评级点")
                                return historical_data
                            else:
                                print(f" 股票 {stock_code} 在 {total_data_points} 天数据中无有效评级（全为'-'或空值）")
                    except Exception as e:
                        print(f" 从data_source获取失败: {e}")
            
            # 方法2：从analysis_results_obj中的data_source获取
            if self.analysis_results_obj and hasattr(self.analysis_results_obj, 'data_source'):
                data_source = self.analysis_results_obj.data_source
                if data_source and hasattr(data_source, 'get_stock_ratings'):
                    print(f" 尝试从analysis_results_obj.data_source获取股票评级数据...")
                    try:
                        stock_ratings = data_source.get_stock_ratings(stock_code, use_interpolation=True)
                        if stock_ratings is not None and not stock_ratings.empty:
                            print(f"📋 股票评级数据长度: {len(stock_ratings)}")
                            
                            historical_data = []
                            total_data_points = len(stock_ratings)
                            
                            for date_col, rating_value in stock_ratings.items():
                                if rating_value is not None and str(rating_value) not in ['nan', 'NaN', '', 'None', '-']:
                                    rating_num = self.convert_rating_to_number(rating_value)
                                    if rating_num is not None:
                                        historical_data.append((str(date_col), rating_num))
                            
                            if historical_data:
                                print(f" 从analysis_results_obj.data_source提取到 {len(historical_data)} 个历史评级点")
                                return historical_data
                            else:
                                print(f" 股票 {stock_code} 在 {total_data_points} 天数据中无有效评级（全为'-'或空值）")
                    except Exception as e:
                        print(f" 从analysis_results_obj.data_source获取失败: {e}")
            
            # 方法3：尝试直接从原始数据获取（作为备用方案）
            if self.analysis_results and 'data_source' in self.analysis_results:
                data_source = self.analysis_results['data_source']
                if hasattr(data_source, 'data') and hasattr(data_source, '_metadata'):
                    print(f" 尝试从原始DataFrame直接获取...")
                    try:
                        # 直接访问原始数据
                        stock_code_str = str(stock_code)
                        stock_data = data_source.data
                        
                        # 尝试多种股票代码匹配方式
                        import pandas as pd
                        stock_row = pd.DataFrame()
                        
                        # 方法1：直接匹配
                        stock_row = stock_data[stock_data['股票代码'].astype(str) == stock_code_str]
                        
                        # 方法2：补零后匹配（兼容旧代码）
                        if stock_row.empty:
                            stock_code_padded = stock_code_str.zfill(6)
                            stock_row = stock_data[stock_data['股票代码'].astype(str) == stock_code_padded]
                        
                        # 方法3：去除前导零后匹配
                        if stock_row.empty:
                            stock_code_cleaned = stock_code_str.lstrip('0')
                            if stock_code_cleaned:  # 避免空字符串
                                stock_row = stock_data[stock_data['股票代码'].astype(str) == stock_code_cleaned]
                        
                        print(f" 股票代码匹配结果: {stock_code_str} -> 找到{len(stock_row)}条记录")
                        
                        if not stock_row.empty:
                            date_columns = data_source._metadata.get('date_columns', [])
                            print(f"📅 找到日期列: {len(date_columns)} 个")
                            
                            if date_columns:
                                stock_row = stock_row.iloc[0]
                                historical_data = []
                                
                                for date_col in sorted(date_columns):
                                    rating_value = stock_row.get(date_col)
                                    if rating_value is not None and str(rating_value) not in ['nan', 'NaN', '', 'None', '-']:
                                        rating_num = self.convert_rating_to_number(rating_value)
                                        if rating_num is not None:
                                            historical_data.append((str(date_col), rating_num))
                                
                                if historical_data:
                                    print(f" 从原始DataFrame提取到 {len(historical_data)} 个历史评级点")
                                    return historical_data
                    except Exception as e:
                        print(f" 从原始DataFrame获取失败: {e}")
            
            # 如果没有找到真实数据，返回None
            print(f" 未找到股票 {stock_code} 的真实历史数据")
            return None
            
        except Exception as e:
            print(f"[ERROR] 获取真实历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def convert_rating_to_number(self, rating_str):
        """将文字评级转换为数字评级 - 使用0-7系统（7=大多最高，0=大空最低）"""
        rating_map = {
            '大多': 7, '7': 7,
            '中多': 6, '6': 6,
            '小多': 5, '5': 5,
            '微多': 4, '4': 4,
            '微空': 3, '3': 3,
            '小空': 2, '2': 2,
            '中空': 1, '1': 1,
            '大空': 0, '0': 0  # 大空为0（最低级）
        }
        
        rating_str = str(rating_str).strip()
        return rating_map.get(rating_str, None)
    
    def apply_chart_display_completion(self, chart_data):
        """为ASCII图表应用显示补全功能"""
        if not chart_data:
            return chart_data
        
        from datetime import datetime, timedelta
        
        # 获取最后一个有效的评级
        last_valid_rating = None
        for date, rating in reversed(chart_data):
            if rating not in ['-', None, ''] and self.convert_rating_to_number(rating) is not None:
                last_valid_rating = rating
                break
        
        if last_valid_rating is None:
            return chart_data  # 没有有效评级，无法补全
        
        # 获取最后一个日期
        if not chart_data:
            return chart_data
        
        last_date_str = str(chart_data[-1][0])
        
        # 解析最后日期
        try:
            if len(last_date_str) == 8 and last_date_str.isdigit():
                # 20250820 格式
                last_year = int(last_date_str[:4])
                last_month = int(last_date_str[4:6])
                last_day = int(last_date_str[6:8])
                last_date = datetime(last_year, last_month, last_day)
            else:
                # 其他格式，不补全
                return chart_data
        except:
            return chart_data
        
        # 补全到今天
        today = datetime.now()
        current_date = last_date
        completed_data = list(chart_data)
        
        while current_date < today:
            current_date += timedelta(days=1)
            
            # 只添加工作日
            if current_date.weekday() < 5:  # 0-4 是周一到周五
                date_str = current_date.strftime('%Y%m%d')
                completed_data.append((date_str, last_valid_rating))
        
        return completed_data
    
    def get_original_chart_data(self, chart_data):
        """获取原始图表数据（不包含补全部分）"""
        if not chart_data:
            return chart_data
        
        from datetime import datetime
        
        # 找到第一个补全数据的位置
        today = datetime.now()
        for i, (date_str, rating) in enumerate(chart_data):
            try:
                if len(str(date_str)) == 8 and str(date_str).isdigit():
                    year = int(str(date_str)[:4])
                    month = int(str(date_str)[4:6])
                    day = int(str(date_str)[6:8])
                    date_obj = datetime(year, month, day)
                    
                    # 如果这个日期是今天或之后，说明可能是补全数据
                    if date_obj >= today.replace(hour=0, minute=0, second=0, microsecond=0):
                        return chart_data[:i]
            except:
                continue
        
        return chart_data
    
    def generate_ascii_chart(self, chart_data, enable_completion=True):
        """生成ASCII图表 - 增强版支持显示补全功能"""
        from datetime import datetime
        
        if not chart_data:
            return " 暂无历史评级数据\n\n     此股票在数据期间内所有评级均为空（显示为'-'）\n    📅 可能原因：\n        • 新上市股票，评级机构尚未覆盖\n        • 停牌或特殊情况期间无评级\n        • 数据源暂未包含该股票的评级信息\n     建议选择其他有评级数据的股票查看趋势图表"
        
        # 应用显示补全功能
        if enable_completion:
            chart_data = self.apply_chart_display_completion(chart_data)
        
        # 检查是否为无数据的特殊情况
        if len(chart_data) == 1 and isinstance(chart_data[0], tuple):
            first_item = chart_data[0]
            if len(first_item) >= 2 and isinstance(first_item[1], str) and "无历史评级数据" in first_item[1]:
                return " 暂无历史评级数据\n\n     此股票尚无足够的历史评级记录\n    📅 请稍后查看或选择其他股票"
        
        dates, ratings = zip(*chart_data)
        
        # 验证评级数据是否为数字类型
        numeric_ratings = []
        for rating in ratings:
            if isinstance(rating, (int, float)):
                numeric_ratings.append(rating)
            elif isinstance(rating, str):
                # 尝试转换字符串评级为数字
                converted = self.convert_rating_to_number(rating)
                if converted is not None:
                    numeric_ratings.append(converted)
                else:
                    # 如果转换失败，跳过该数据点
                    continue
            else:
                continue
        
        # 如果没有有效的数字评级，返回无数据提示
        if not numeric_ratings:
            return " 暂无有效的历史评级数据\n\n     评级数据格式异常或无法解析\n    📅 请稍后查看或选择其他股票"
        
        # 重新构建有效的数据对
        valid_data = [(dates[i], ratings[i]) for i, rating in enumerate(ratings) 
                     if isinstance(rating, (int, float)) or 
                     (isinstance(rating, str) and self.convert_rating_to_number(rating) is not None)]
        
        if not valid_data:
            return " 暂无有效的历史评级数据\n\n     评级数据格式异常或无法解析\n    📅 请稍后查看或选择其他股票"
        
        # 重新解包有效数据
        dates, ratings = zip(*valid_data)
        numeric_ratings = [rating if isinstance(rating, (int, float)) else self.convert_rating_to_number(rating) 
                          for rating in ratings]
        
        chart_lines = []
        
        # 分析原始数据长度（用于标识补全数据）
        if enable_completion:
            # 计算补全前的有效数据长度
            original_valid_count = 0
            today = datetime.now()
            for date_str, rating in valid_data:
                try:
                    if len(str(date_str)) == 8 and str(date_str).isdigit():
                        year = int(str(date_str)[:4])
                        month = int(str(date_str)[4:6])
                        day = int(str(date_str)[6:8])
                        date_obj = datetime(year, month, day)
                        
                        # 如果这个日期是今天之前的，算作原始数据
                        if date_obj < today.replace(hour=0, minute=0, second=0, microsecond=0):
                            original_valid_count += 1
                        else:
                            break
                except:
                    original_valid_count += 1
            original_length = original_valid_count
        else:
            original_length = len(dates)
        
        # 图表高度为8级（0-7）
        for level in range(7, -1, -1):
            line = f"{level}级 |"
            for i, rating in enumerate(numeric_ratings):
                if abs(rating - level) < 0.5:
                    # 判断是否为补全数据，使用不同标记
                    if enable_completion and i >= original_length:
                        line += "△"  # 橙色三角的替代符号
                    else:
                        line += "●"
                elif rating > level:
                    line += "│"
                else:
                    line += " "
            chart_lines.append(line)
        
        # 添加底部时间轴 - 显示年/月/日信息，特别是最左和最右处
        time_line = "     +"
        date_line = "     "
        
        # 解析日期格式并提取年月日信息
        for i, date in enumerate(dates):
            date_str = str(date)
            year = ""
            month = ""
            day = ""
            
            # 标准化日期解析
            if len(date_str) == 8 and date_str.isdigit():
                # YYYYMMDD 格式（如 20250630）
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
            elif '-' in date_str:
                # YYYY-MM-DD 格式
                parts = date_str.split('-')
                if len(parts) == 3:
                    year, month, day = parts[0], parts[1], parts[2]
            elif '/' in date_str:
                # YYYY/MM/DD 格式
                parts = date_str.split('/')
                if len(parts) == 3:
                    year, month, day = parts[0], parts[1], parts[2]
            
            # 在时间轴上显示标记
            if i % 10 == 0:  # 每10天显示一个标记点
                time_line += "+"
            elif i % 5 == 0:  # 每5天显示一个点
                time_line += "·"
            else:
                time_line += "─"
            
            # 显示日期信息，重点显示最左和最右处
            if i == 0:  # 最左边 - 显示完整的年/月/日
                if year and month and day:
                    # 去掉前导0并格式化
                    formatted_date = f"{year[-2:]}/{int(month)}/{int(day)}"
                    date_line += formatted_date
                    # 补齐剩余空间
                    date_line += " " * max(0, 10 - len(formatted_date))
                else:
                    date_line += " " * 10
            elif i == len(dates) - 1:  # 最右边 - 显示完整的年/月/日
                if year and month and day:
                    # 先补充到合适位置
                    target_position = len(time_line) - 10
                    while len(date_line) < target_position:
                        date_line += " "
                    # 去掉前导0并格式化
                    formatted_date = f"{year[-2:]}/{int(month)}/{int(day)}"
                    date_line += formatted_date
                else:
                    date_line += " "
            elif i % 15 == 0 and month and day:  # 中间关键点 - 显示月/日
                formatted_date = f"{int(month)}/{int(day)}"
                date_line += formatted_date
                date_line += " " * max(0, 5 - len(formatted_date))
            else:
                date_line += " "
        
        chart_lines.append(time_line)
        chart_lines.append(date_line)
        
        # 添加图表说明和图例
        completion_count = len(dates) - original_length if enable_completion else 0
        
        if completion_count > 0:
            chart_lines.append("")
            chart_lines.append(" 图例: ● 原始数据  △ 显示补全(用最近信号延续)  │ 评级上方区间")
            chart_lines.append(f" 最近{completion_count}天为显示补全数据，仅用于图表完整性，不用于分析")
        else:
            chart_lines.append("")
            chart_lines.append(f" {t_gui('chart_legend')}: {t_gui('legend_rating_points')}  {t_gui('legend_above_rating')}  {t_gui('legend_below_rating')}")
        
        return "\n".join(chart_lines)
    
    # ================ AI分析相关方法 ================
    
    def start_technical_analysis(self):
        """开始技术面分析"""
        if not self.analysis_results_obj:
            QMessageBox.warning(self, t_gui('warning'), "请先加载股票数据并选择要分析的股票")
            return
        
        if not hasattr(self, 'current_stock_code') or not self.current_stock_code:
            QMessageBox.warning(self, t_gui('warning'), "请先选择要分析的股票")
            return
        
        # 防止重复分析
        if hasattr(self, 'technical_analysis_in_progress') and self.technical_analysis_in_progress:
            QMessageBox.information(self, t_gui('info'), "技术面分析正在进行中，请稍候...")
            return
        
        # 检查缓存，如果有缓存直接显示结果页
        cache_key = f"technical_{self.current_stock_code}"
        if hasattr(self, 'stock_ai_cache') and cache_key in self.stock_ai_cache:
            self.show_cached_technical_result(self.current_stock_code)
            return
        
        # 开始分析
        self.perform_technical_analysis(self.current_stock_code)
    
    def start_master_analysis(self):
        """开始投资大师分析"""
        if not self.analysis_results_obj:
            QMessageBox.warning(self, t_gui('warning'), "请先加载股票数据并选择要分析的股票")
            return
        
        if not hasattr(self, 'current_stock_code') or not self.current_stock_code:
            QMessageBox.warning(self, t_gui('warning'), "请先选择要分析的股票")
            return
        
        # 防止重复分析
        if hasattr(self, 'master_analysis_in_progress') and self.master_analysis_in_progress:
            QMessageBox.information(self, t_gui('info'), "投资大师分析正在进行中，请稍候...")
            return
        
        # 检查缓存，如果有缓存直接显示结果页
        cache_key = f"master_{self.current_stock_code}"
        if hasattr(self, 'stock_ai_cache') and cache_key in self.stock_ai_cache:
            self.show_cached_master_result(self.current_stock_code)
            return
        
        # 开始分析
        self.perform_master_analysis(self.current_stock_code)
    
    def perform_technical_analysis(self, stock_code):
        """执行技术面分析"""
        try:
            # 设置分析状态
            self.technical_analysis_in_progress = True
            if hasattr(self, 'technical_ai_analyze_btn'):
                self.technical_ai_analyze_btn.setEnabled(False)
                self.technical_ai_analyze_btn.setText("🔄 分析中")
            if hasattr(self, 'technical_ai_status_label'):
                self.technical_ai_status_label.setText("🔄 技术面分析师正在分析，请稍候...")
            
            # 收集分析数据
            analysis_data = self.collect_stock_analysis_data(stock_code)
            
            # 生成技术面分析提示词
            prompt = self.generate_technical_analysis_prompt(analysis_data)
            
            # 使用单线程直接调用，避免PyQt5多线程崩溃
            QTimer.singleShot(100, lambda: self._perform_technical_analysis_sync(prompt, stock_code))
            
        except Exception as e:
            self.on_technical_analysis_error(str(e))
    
    def perform_master_analysis(self, stock_code):
        """执行投资大师分析"""
        try:
            # 设置分析状态
            self.master_analysis_in_progress = True
            if hasattr(self, 'master_ai_analyze_btn'):
                self.master_ai_analyze_btn.setEnabled(False)
                self.master_ai_analyze_btn.setText("🔄 分析中")
            if hasattr(self, 'master_ai_status_label'):
                self.master_ai_status_label.setText("🔄 投资大师正在分析，请稍候...")
            
            # 收集分析数据 - 包含迷你投资大师的数据
            analysis_data = self.collect_master_analysis_data(stock_code)
            
            # 生成投资大师分析提示词
            prompt = self.generate_master_analysis_prompt(analysis_data)
            
            # 使用单线程直接调用，避免PyQt5多线程崩溃
            QTimer.singleShot(100, lambda: self._perform_master_analysis_sync(prompt, stock_code))
            
        except Exception as e:
            self.on_master_analysis_error(str(e))
    
    def _perform_technical_analysis_sync(self, prompt, stock_code):
        """同步执行技术面分析"""
        analysis_type = "技术面分析"
        
        try:
            # ===== 执行前检查 =====
            can_proceed, config = self._ai_analysis_before(analysis_type)
            if not can_proceed:
                self.on_technical_analysis_error("执行前检查未通过")
                return
            
            # 执行分析
            result = self._call_llm_for_analysis(prompt, "技术面分析师")
            
            # 检查是否是API Key错误信息（用户取消配置或没有输入API Key）
            if result and isinstance(result, str) and ("需要配置API Key" in result or "API Key configuration required" in result):
                print(f"[{analysis_type}] API Key配置取消，终止分析")
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_technical_analysis_error(result)
                return
            
            # ===== 执行后处理 =====
            if result:
                self._ai_analysis_after(success=True, analysis_type=analysis_type)
                self.on_technical_analysis_finished(result, stock_code)
            else:
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_technical_analysis_error("AI分析未返回结果")
                
        except Exception as e:
            self._ai_analysis_after(success=False, analysis_type=analysis_type)
            self.on_technical_analysis_error(str(e))
    
    def _perform_master_analysis_sync(self, prompt, stock_code):
        """同步执行投资大师分析"""
        analysis_type = "投资大师分析"
        
        try:
            # ===== 执行前检查 =====
            can_proceed, config = self._ai_analysis_before(analysis_type)
            if not can_proceed:
                self.on_master_analysis_error("执行前检查未通过")
                return
            
            # 执行分析
            result = self._call_llm_for_analysis(prompt, "投资大师")
            
            # 检查是否是API Key错误信息（用户取消配置或没有输入API Key）
            if result and isinstance(result, str) and ("需要配置API Key" in result or "API Key configuration required" in result):
                print(f"[{analysis_type}] API Key配置取消，终止分析")
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_master_analysis_error(result)
                return
            
            # ===== 执行后处理 =====
            if result:
                self._ai_analysis_after(success=True, analysis_type=analysis_type)
                self.on_master_analysis_finished(result, stock_code)
            else:
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_master_analysis_error("AI分析未返回结果")
                
        except Exception as e:
            self._ai_analysis_after(success=False, analysis_type=analysis_type)
            self.on_master_analysis_error(str(e))
    
    def on_technical_analysis_finished(self, result, stock_code):
        """技术面分析完成"""
        try:
            # 生成HTML报告
            html_report = self.generate_technical_analysis_html(result, stock_code)
            
            # 缓存结果
            cache_key = f"technical_{stock_code}"
            from datetime import datetime
            if not hasattr(self, 'technical_ai_cache'):
                self.technical_ai_cache = {}
            self.technical_ai_cache[stock_code] = {
                'html': html_report,
                'result': result,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 显示结果 - 适配新的技术AI Tab结构
            if hasattr(self, 'technical_ai_result_browser'):
                self.technical_ai_result_browser.setHtml(html_report)
            elif hasattr(self, 'technical_ai_result_text'):
                self.technical_ai_result_text.setHtml(html_report)
            
            # 切换到结果页面
            if hasattr(self, 'technical_ai_stacked_widget'):
                self.technical_ai_stacked_widget.setCurrentIndex(1)
            
            # 重置按钮状态 - 适配新的按钮名称
            if hasattr(self, 'technical_ai_analyze_btn'):
                self.technical_ai_analyze_btn.setEnabled(True)
                self.technical_ai_analyze_btn.setText(" 开始技术面AI分析")
            if hasattr(self, 'technical_ai_status_label'):
                self.technical_ai_status_label.setText(" 技术面分析完成")
            self.technical_analysis_in_progress = False
            
        except Exception as e:
            self.on_technical_analysis_error(str(e))
    
    def on_master_analysis_finished(self, result, stock_code):
        """投资大师分析完成"""
        try:
            # 生成HTML报告
            html_report = self.generate_master_analysis_html(result, stock_code)
            
            # 缓存结果
            cache_key = f"master_{stock_code}"
            from datetime import datetime
            if not hasattr(self, 'master_ai_cache'):
                self.master_ai_cache = {}
            self.master_ai_cache[stock_code] = {
                'html': html_report,
                'result': result,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 显示结果 - 适配新的投资大师AI Tab结构
            if hasattr(self, 'master_ai_result_browser'):
                self.master_ai_result_browser.setHtml(html_report)
            elif hasattr(self, 'master_ai_result_text'):
                self.master_ai_result_text.setHtml(html_report)
            
            # 切换到结果页面
            if hasattr(self, 'master_ai_stacked_widget'):
                self.master_ai_stacked_widget.setCurrentIndex(1)
            
            # 重置按钮状态 - 适配新的按钮名称
            if hasattr(self, 'master_ai_analyze_btn'):
                self.master_ai_analyze_btn.setEnabled(True)
                self.master_ai_analyze_btn.setText(" 开始投资大师AI分析")
            if hasattr(self, 'master_ai_status_label'):
                self.master_ai_status_label.setText(" 投资大师分析完成")
            self.master_analysis_in_progress = False
            
        except Exception as e:
            self.on_master_analysis_error(str(e))
    
    def on_technical_analysis_error(self, error_msg):
        """技术面分析出错"""
        print(f"技术面分析失败: {error_msg}")
        if hasattr(self, 'technical_ai_analyze_btn'):
            self.technical_ai_analyze_btn.setEnabled(True)
            self.technical_ai_analyze_btn.setText(" 开始技术面AI分析")
        if hasattr(self, 'technical_ai_status_label'):
            self.technical_ai_status_label.setText(f"[ERROR] 分析失败: {error_msg}")
        self.technical_analysis_in_progress = False
        
        QMessageBox.critical(self, "技术面分析失败", f"分析过程中出现错误：\n{error_msg}")
    
    def on_master_analysis_error(self, error_msg):
        """投资大师分析出错"""
        print(f"投资大师分析失败: {error_msg}")
        if hasattr(self, 'master_ai_analyze_btn'):
            self.master_ai_analyze_btn.setEnabled(True)
            self.master_ai_analyze_btn.setText(" 开始投资大师AI分析")
        if hasattr(self, 'master_ai_status_label'):
            self.master_ai_status_label.setText(f"[ERROR] 分析失败: {error_msg}")
        self.master_analysis_in_progress = False
        
        QMessageBox.critical(self, "投资大师分析失败", f"分析过程中出现错误：\n{error_msg}")
    
    def generate_technical_analysis_prompt(self, analysis_data):
        """生成技术面分析提示词"""
        stock_code = analysis_data.get('stock_code', '')
        stock_name = analysis_data.get('stock_name', '')
        rtsi_score = analysis_data.get('rtsi', 0)  # 修复：使用正确的键名'rtsi'
        algorithm = analysis_data.get('algorithm', 'RTSI')
        industry = analysis_data.get('industry', '')
        rating_trend = analysis_data.get('rating_trend', [])
        volume_price_data = analysis_data.get('volume_price_data', [])
        
        prompt = f"""你是一位专业的技术面分析师，请基于以下数据对股票 {stock_code}({stock_name}) 进行专业的技术分析：

**基础数据：**
- 股票代码：{stock_code}
- 股票名称：{stock_name}
- 所属行业：{industry}
- RTSI评分：{rtsi_score:.2f} (范围：0-90，优化增强RTSI v2.3算法)
- 分析算法：{algorithm}

**RTSI评分解读标准（严格执行，最高分90）：**
 重要提醒：RTSI v2.3算法最高分约为90分（极少数优质股票），请准确理解评分含义
- 80-90：顶级强势区间（接近满分），技术面卓越，优先配置（仓位≤25%）
- 70-79：极强势区间，技术面极其强劲，积极关注（仓位≤20%）
- 60-69：高分强势区间，技术面表现优秀，积极配置（仓位≤15%）
- 50-59：中等偏上区间，技术面相对稳健，适度关注（仓位≤10%）
- 40-49：中性区间，技术面平衡，谨慎分析（仓位≤8%）
- 30-39：偏弱区间，技术面较弱，建议观望（仓位≤5%）
- 30以下：弱势区间，技术面疲弱，建议规避（仓位≤2%）

**当前评分{rtsi_score:.2f}的详细解读：**
{self._get_detailed_rtsi_interpretation(rtsi_score)}

**风险匹配的操作建议框架：**
{self._get_rtsi_operation_framework(rtsi_score)}

**评级趋势数据：**
{self._format_rating_trend_for_prompt(rating_trend)}

**量价数据：**
{self._format_volume_price_for_prompt(volume_price_data)}

**分析要求：**
1. **RTSI评分精准解读（强制要求）**：
   •  特别注意：{rtsi_score:.2f}分属于60-69高分强势区间，必须按此标准解读
   • 禁止将60-69分错误归类为"中性平衡"或"中等"，这是高分区间
   • 必须明确说明当前技术面表现优秀，具备较强投资价值
   • 分析建议必须与高分强势区间相匹配，采用积极配置策略

2. **数据驱动分析（强制要求）**：
   • 【必须引用】分析中必须明确引用具体的评级趋势数据和量价数据，不得忽略
   • 【数据验证】必须引用具体日期和数值，如"2025年X月X日评级变化"、"成交量XXX万股"、"价格X.XX元"
   • 【禁止空洞】禁止使用"数据显示"、"根据趋势"等模糊表述，必须使用具体数据
   • 【分析深度】每个关键数据点都必须给出具体的技术面解读和投资含义
   • 【量价配合】必须分析成交量与价格变化的配合情况，判断资金流向
   • 【趋势确认】必须基于评级趋势数据判断技术面是改善还是恶化
   • 【时间维度】必须分析短期（1-3天）、中期（1-2周）、长期（1-3个月）的技术变化

3. **操作建议精准化（风险控制）**：
   • 【仓位限制】单只股票的仓位建议不得超过20%，违反此规定的建议将被认为不合格
   • 【具体建议】必须给出明确的买入/持有/卖出建议百分比
   • 【价位设定】必须设置具体的目标价位和止损位，避免过于宽泛的范围
   • 【风险匹配】仓位建议必须与RTSI评分区间相匹配（中性区间建议更低仓位）

4. **客观性要求**：
   • 客观评估技术面，不得夸大上涨潜力
   • 对于中性或偏弱的RTSI评分，应给出相应的谨慎建议
   • 重视风险控制，避免盲目推荐

**重要约束：**
- 严格基于提供的RTSI评分和数据进行分析，不得编造数据
- 建议必须与RTSI评分等级相匹配
- 本分析针对大盘股，操作建议应体现稳健投资特点
- 避免推荐其他股票，专注于当前分析标的

【技术分析完整性检查清单】
完成分析前，请逐项确认以下要求：
 RTSI解读：已准确解读RTSI {rtsi_score:.2f}分的技术面含义，使用正确的区间描述
 数据引用：已引用具体的评级趋势和量价数据，包含具体日期和数值
 量价分析：已分析成交量与价格变化的配合情况
 趋势判断：已基于数据判断短期、中期、长期技术变化
 仓位控制：仓位建议严格控制在对应区间内（当前应≤{20 if rtsi_score >= 70 else 15 if rtsi_score >= 60 else 12 if rtsi_score >= 50 else 10 if rtsi_score >= 40 else 8 if rtsi_score >= 30 else 5}%）
 风险匹配：建议与RTSI评分区间完全匹配
 客观性：未夸大中性或偏弱评分的上涨潜力
 具体性：提供了明确的目标价位和止损位
 专业性：使用了专业的技术分析术语和逻辑

[ERROR] 如任一项未完成，请重新完善分析内容

请以专业技术分析师的口吻，用中文回复，结构清晰，观点明确。"""

        return prompt
    
    def _get_detailed_rtsi_interpretation(self, rtsi_score):
        """根据RTSI分数生成详细解读（基于最高90分的实际情况 - RTSI v2.3）"""
        if rtsi_score >= 80:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于顶级强势区间（80-90），技术面表现卓越。
注意：RTSI v2.3最高分约为90分，当前评分已接近满分，技术面优势极其显著。
这表明股票具有卓越的技术优势和极强的上涨动能，属于市场中的顶级标的。
操作建议：优先配置，可重点增配，建议仓位不超过20-25%。
当前技术信号：极其积极，适合各类投资者优先配置。"""
        elif rtsi_score >= 70:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于极强势区间（70-79），技术面表现极其强劲。
注意：RTSI v2.3最高分约90分，70+属于高分区间，技术面优势显著。
这表明股票具有卓越的技术优势，短期内有很强的上涨动能。
操作建议：积极关注，可适度增配，建议仓位不超过15-20%。
当前技术信号：非常积极，适合稳健投资者重点配置。"""
        elif rtsi_score >= 60:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于高分强势区间（60-69），技术面表现强劲。
技术指标显示良好的上涨趋势，具备较强的投资价值和上涨潜力。
操作建议：积极关注，可适度配置，建议仓位不超过12-15%。
当前技术信号：积极乐观，适合稳健投资者重点关注。"""
        elif rtsi_score >= 50:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于中等偏上区间（50-59），技术面较好。
技术指标显示一定的上涨潜力，整体趋势相对稳健。
操作建议：可适度关注，控制仓位在10%以内，重视风险管理。
当前技术信号：中性偏好，适合保守型投资者小幅配置。"""
        elif rtsi_score >= 40:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于中性区间（40-49），技术面平衡。
既无明显的强势信号，也无明显的弱势特征，技术面中性平衡。
操作建议：需要谨慎，仅建议极小仓位试探（≤8%），重点关注风险控制。
当前技术信号：中性平衡，不强不弱，需要更多确认信号。"""
        elif rtsi_score >= 30:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于偏弱区间（30-39），技术面较弱。
技术指标显示一定的弱势特征，上涨动能不足。
操作建议：建议观望为主，如配置仅限极小仓位（≤5%），严控风险。
当前技术信号：偏向谨慎，不适合主动配置。"""
        else:
            return f"""
该股票RTSI评分{rtsi_score:.2f}分处于弱势区间（30分以下），技术面疲弱。
技术指标显示明显的弱势特征，缺乏上涨动能。
操作建议：强烈建议规避，如特殊情况配置仅限最小仓位（≤2%）。
当前技术信号：明显偏弱，不建议投资配置。"""
    
    def _get_rtsi_operation_framework(self, rtsi_score):
        """根据RTSI分数生成操作建议框架（基于最高90分实际情况 - RTSI v2.3）"""
        if rtsi_score >= 80:
            return f"""
【顶级强势操作框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：接近满分的顶级表现，市场中的优质标的
▪ 推荐仓位：18-25%（可重点增配的顶级标的）
▪ 买入策略：优先配置，可在适当时机积极建仓
▪ 持有策略：长期持有为主，适度动态调整
▪ 止盈策略：目标涨幅25-35%，分批止盈
▪ 止损策略：跌破重要支撑位或RTSI跌破65时考虑减仓
▪ 风险提示：注意高位回调风险，不宜追高"""
        elif rtsi_score >= 70:
            return f"""
【极强势操作框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：接近满分的极强势表现
▪ 推荐仓位：12-18%（可适度增配的优质标的）
▪ 买入策略：积极配置，可在回调时分批建仓
▪ 持有策略：积极持有，重点关注量价配合
▪ 卖出信号：RTSI跌破65或出现明显技术破位
▪ 止损位：建议设置在当前价格下方8-10%
▪ 目标收益：短期15-25%，中期25-40%
▪ 风险提示：即使接近满分也需严控仓位，防范市场系统性风险"""
        elif rtsi_score >= 60:
            return f"""
【高分强势操作框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：高分区间，技术面表现优秀
▪ 推荐仓位：10-15%（积极配置的优质标的）
▪ 买入策略：积极配置，可在技术调整时适度加仓
▪ 持有策略：积极持有，密切关注技术变化
▪ 卖出信号：RTSI跌破55或技术形态破坏
▪ 止损位：建议设置在当前价格下方10-12%
▪ 目标收益：短期10-20%，中期20-35%
▪ 风险提示：高分股票具备较强投资价值，但仍需控制仓位风险"""
        elif rtsi_score >= 50:
            return f"""
【中等偏上操作框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：中等偏上水平，技术面相对稳健
▪ 推荐仓位：6-10%（适度配置）
▪ 买入策略：稳健配置，等待更好买点
▪ 持有策略：谨慎持有，随时准备调整
▪ 卖出信号：RTSI跌破45或出现技术疲软
▪ 止损位：建议设置在当前价格下方12-15%
▪ 目标收益：短期5-15%，中期10-20%
▪ 风险提示：中等水平股票波动性较大，需密切监控"""
        elif rtsi_score >= 40:
            return f"""
【中性平衡操作框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：中性平衡，技术面无明显强弱信号
▪ 推荐仓位：3-8%（极度谨慎，试探性配置）
▪ 买入策略：非常谨慎，等待明确向上信号
▪ 持有策略：密切监控，随时准备退出
▪ 卖出信号：RTSI跌破35或任何技术恶化信号
▪ 止损位：严格设置在当前价格下方8-10%
▪ 目标收益：短期3-8%，中期5-12%
▪ 风险提示：中性股票方向不明，以风控为首要原则"""
        elif rtsi_score >= 30:
            return f"""
【偏弱观望框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：偏弱水平，技术面表现不佳
▪ 推荐仓位：1-5%（仅限特殊情况的最小配置）
▪ 买入策略：强烈建议观望，等待技术改善
▪ 持有策略：如有持仓建议减仓或清仓
▪ 卖出信号：任何进一步的技术恶化
▪ 止损位：非常严格，当前价格下方5-8%
▪ 目标收益：以保本为主，期望收益很低
▪ 风险提示：偏弱股票下跌风险大，强烈建议规避"""
        else:
            return f"""
【弱势规避框架】(RTSI: {rtsi_score:.2f}/90)
▪ 评级说明：弱势表现，技术面严重不佳
▪ 推荐仓位：0-2%（强烈建议完全规避）
▪ 买入策略：不建议买入，等待基本面重大改善
▪ 持有策略：如有持仓建议尽快清仓
▪ 卖出信号：立即卖出或等待反弹卖出
▪ 止损位：不适用（建议直接规避）
▪ 目标收益：无收益预期，以减损为目标
▪ 风险提示：弱势股票风险极大，强烈建议完全规避"""
    
    def generate_master_analysis_prompt(self, analysis_data):
        """生成投资大师分析提示词 - 基于迷你投资大师的策略"""
        stock_code = analysis_data.get('stock_code', '')
        stock_name = analysis_data.get('stock_name', '')
        rtsi_score = analysis_data.get('rtsi', 0)  # 修复：使用正确的键名'rtsi'
        industry = analysis_data.get('industry', '')
        
        # 获取迷你投资大师数据
        mini_master_data = analysis_data.get('mini_master_data', {})
        master_scores = mini_master_data.get('strategy_breakdown', {})
        overall_score = mini_master_data.get('overall_score', 0)
        best_strategy = mini_master_data.get('best_strategy', '综合策略')
        indicators = mini_master_data.get('indicators', {})
        
        prompt = f"""你现在要扮演五位世界著名的投资大师，为股票 {stock_code}({stock_name}) 提供投资分析和建议。

**股票基础信息：**
- 股票代码：{stock_code}
- 股票名称：{stock_name}
- 所属行业：{industry}
- RTSI技术评分：{rtsi_score:.2f} (范围：0-90，优化增强RTSI v2.3算法)

**RTSI评分解读标准（v2.3算法，最高约90分）：**
- 80-90：顶级强势区间，技术面卓越，优先配置的顶级标的
- 70-79：极强势区间，技术面极其强劲，重点关注和配置
- 60-69：强势区间，技术面非常强劲，适合成长投资和趋势投资
- 50-59：中强势区间，技术面较好，适合价值成长结合策略
- 40-49：中性区间，技术面平衡，需结合基本面深度分析
- 30-39：偏弱区间，技术面较弱，适合逆向投资或等待时机
- 10-29：弱势区间，技术面疲弱，需谨慎评估风险

**投资大师策略评分（基于量化算法）：**
- 巴菲特价值投资策略：{master_scores.get('buffett', 0):.1f}分
- 彼得林奇成长投资策略：{master_scores.get('lynch', 0):.1f}分  
- 格雷厄姆价值投资策略：{master_scores.get('graham', 0):.1f}分
- 德鲁肯米勒趋势投资策略：{master_scores.get('druckenmiller', 0):.1f}分
- 迈克尔·伯里逆向投资策略：{master_scores.get('burry', 0):.1f}分
- **综合评分：{overall_score:.1f}分**
- **最适合策略：{best_strategy}**

**技术指标数据：**
{self._format_indicators_for_prompt(indicators)}

**分析要求：**
请分别以五位投资大师的口吻和投资理念进行分析：

1. **🏛️ 巴菲特 (价值投资之父)**：
   - 关注长期价值、护城河、管理层质量
   - 基于评分{master_scores.get('buffett', 0):.1f}分，分析是否符合价值投资标准
   - 给出长期持有建议

2. ** 彼得林奇 (成长投资大师)**：
   - 关注成长潜力、行业前景、动量特征
   - 基于评分{master_scores.get('lynch', 0):.1f}分，分析成长投资机会
   - 给出成长投资建议

3. ** 格雷厄姆 (证券分析之父)**：
   - 关注安全边际、低估值、风险控制
   - 基于评分{master_scores.get('graham', 0):.1f}分，分析价值低估机会
   - 给出价值挖掘建议

4. **⚡ 德鲁肯米勒 (趋势投资专家)**：
   - 关注趋势强度、动量确认、宏观环境
   - 基于评分{master_scores.get('druckenmiller', 0):.1f}分，分析趋势投资机会
   - 给出趋势跟随建议

5. **🔄 迈克尔·伯里 (逆向投资先锋)**：
   - 关注市场情绪、逆向思维、危机中的机会
   - 基于评分{master_scores.get('burry', 0):.1f}分，分析逆向投资机会
   - 给出逆向投资建议

**最终综合建议：**
基于综合评分{overall_score:.1f}分和最适合策略"{best_strategy}"，给出：
- 投资建议（买入/卖出/持有）
- 建议持有期限
- 风险等级评估
- 仓位建议

**重要提示：**
- 本分析针对大盘股，请在投资建议中体现大盘股稳健、流动性好的特点
- 风险评估应考虑大盘股相对较低的流动性风险和较高的基本面稳定性
- 如需推荐其他股票，请优先推荐同类型的大盘股和蓝筹股

请用中文回复，每位大师的分析要体现其独特的投资风格和语言特点。"""

        return prompt
    
    def collect_master_analysis_data(self, stock_code):
        """收集投资大师分析所需的数据 - 包含迷你投资大师数据"""
        # 先获取基础分析数据
        analysis_data = self.collect_stock_analysis_data(stock_code)
        
        try:
            # 调用迷你投资大师进行分析
            from mini import MiniInvestmentMasterGUI
            mini_master = MiniInvestmentMasterGUI()
            mini_result = mini_master.analyze_stock_for_gui(stock_code)
            
            if mini_result['status'] == 'success':
                analysis_result = mini_result['analysis_result']
                # 提取关键数据
                analysis_data['mini_master_data'] = {
                    'strategy_breakdown': analysis_result.get('master_analysis', {}).get('strategy_breakdown', {}),
                    'overall_score': analysis_result.get('master_analysis', {}).get('overall_score', 0),
                    'best_strategy': analysis_result.get('master_analysis', {}).get('best_strategy', '综合策略'),
                    'indicators': analysis_result.get('indicators', {}),
                    'investment_advice': analysis_result.get('investment_advice', {})
                }
            else:
                # 如果迷你投资大师分析失败，使用默认数据
                analysis_data['mini_master_data'] = {
                    'strategy_breakdown': {},
                    'overall_score': 50,
                    'best_strategy': '综合策略',
                    'indicators': {},
                    'investment_advice': {}
                }
                print(f"迷你投资大师分析失败: {mini_result.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"调用迷你投资大师失败: {e}")
            # 使用默认数据
            analysis_data['mini_master_data'] = {
                'strategy_breakdown': {},
                'overall_score': 50,
                'best_strategy': '综合策略',
                'indicators': {},
                'investment_advice': {}
            }
        
        return analysis_data
    
    def _format_rating_trend_for_prompt(self, rating_trend):
        """格式化评级趋势数据用于提示词 - 修复编码错误"""
        try:
            if not rating_trend:
                return "No rating trend data available"
            
            trend_text = "Recent rating changes:\n"
            
            # 处理不同数据格式
            if isinstance(rating_trend, list):
                # 如果是列表，直接处理
                recent_trends = rating_trend[-10:] if len(rating_trend) > 10 else rating_trend
                for i, item in enumerate(recent_trends):
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        date, rating = item[0], item[1]
                        trend_text += f"  {date}: {rating:.2f}\n"
                    elif isinstance(item, dict):
                        date = item.get('date', f'Day{i+1}')
                        rating = item.get('rating', 0)
                        trend_text += f"  {date}: {rating:.2f}\n"
            elif isinstance(rating_trend, dict):
                # 如果是字典，取最近的10个键值对
                items = list(rating_trend.items())[-10:]
                for date, rating in items:
                    trend_text += f"  {date}: {rating:.2f}\n"
            else:
                trend_text += f"  Data format: {type(rating_trend).__name__}\n"
            
            return trend_text
        except Exception as e:
            print(f"Rating trend formatting error: {e}")
            return "Rating trend data formatting failed"
    
    def _format_volume_price_for_prompt(self, volume_price_data):
        """格式化量价数据用于提示词 - 修复编码错误"""
        try:
            if not volume_price_data:
                return "No volume price data available"
            
            vp_text = "Recent volume price data:\n"
            
            # 处理不同数据格式
            if isinstance(volume_price_data, list):
                # 如果是列表，取最近5个元素
                recent_data = volume_price_data[-5:] if len(volume_price_data) > 5 else volume_price_data
                for i, data in enumerate(recent_data):
                    if isinstance(data, dict):
                        date = data.get('date', f'Day{i+1}')
                        price = data.get('close', 0)
                        volume = data.get('volume', 0)
                        vp_text += f"  {date}: Close {price:.2f}, Volume {volume}\n"
                    else:
                        vp_text += f"  Day{i+1}: {data}\n"
            elif isinstance(volume_price_data, dict):
                # 如果是字典，展示键值对
                for key, value in list(volume_price_data.items())[-5:]:
                    vp_text += f"  {key}: {value}\n"
            else:
                vp_text += f"  Data format: {type(volume_price_data).__name__}\n"
            
            return vp_text
        except Exception as e:
            print(f"Volume price formatting error: {e}")
            return "Volume price data formatting failed"
    
    def _format_indicators_for_prompt(self, indicators):
        """格式化技术指标数据用于提示词 - 修复编码错误"""
        try:
            if not indicators:
                return "No technical indicators data available"
            
            indicator_text = ""
            if 'current_price' in indicators:
                indicator_text += f"- Current Price: {indicators['current_price']:.2f}\n"
            if 'price_change_pct' in indicators:
                indicator_text += f"- Price Change: {indicators['price_change_pct']:.2f}%\n"
            if 'volatility' in indicators:
                indicator_text += f"- Volatility: {indicators['volatility']:.2f}%\n"
            if 'rsi' in indicators:
                indicator_text += f"- RSI: {indicators['rsi']:.1f}\n"
            if 'volume_ratio' in indicators:
                indicator_text += f"- Volume Ratio: {indicators['volume_ratio']:.2f}\n"
            if 'ma5' in indicators:
                indicator_text += f"- MA5: {indicators['ma5']:.2f}\n"
            if 'ma20' in indicators:
                indicator_text += f"- MA20: {indicators['ma20']:.2f}\n"
                
            return indicator_text if indicator_text else "No technical indicators data available"
        except Exception as e:
            print(f"Indicators formatting error: {e}")
            return "Technical indicators data formatting failed"
    
    def _call_llm_for_analysis(self, prompt, analyst_type):
        """调用LLM进行分析"""
        try:
            # 这里使用现有的LLM调用方法
            return self._call_llm_api_for_analysis(prompt)
        except Exception as e:
            raise Exception(f"{analyst_type}调用LLM失败: {str(e)}")
    
    def _check_api_key_for_stock_analysis(self, config, provider, use_english, base_path):
        """
        在执行个股AI分析前检查API Key
        
        Args:
            config: 配置字典
            provider: 供应商名称
            use_english: 是否使用英文
            base_path: 基础路径
            
        Returns:
            None: 检查通过，继续执行
            str: 错误信息，终止执行
        """
        try:
            # 如果是Ollama或LMStudio，跳过API Key检查
            if provider.lower() in ['ollama', 'lmstudio']:
                print(f"[API Key检查] {provider} 不需要API Key，跳过检查")
                return None
            
            # 检查是否有API Key配置
            has_api_key = False
            
            # 检查各个供应商的API Key
            provider_keys = {
                'openai': 'OPENAI_API_KEY',
                'deepseek': 'DEEPSEEK_API_KEY',
                'siliconflow': 'SILICONFLOW_API_KEY',
                'anthropic': 'ANTHROPIC_API_KEY',
                'google': 'GOOGLE_API_KEY',
                'zhipu': 'ZHIPU_API_KEY',
                'moonshot': 'MOONSHOT_API_KEY',
            }
            
            # 获取当前供应商对应的API Key字段名
            key_field = provider_keys.get(provider.lower())
            if key_field:
                api_key = config.get(key_field, '').strip()
                if api_key and api_key != '':
                    has_api_key = True
                    print(f"[API Key检查] 检测到 {provider} 的 API Key")
            
            # 如果没有API Key，弹出设置窗口
            if not has_api_key:
                print(f"[API Key检查] 未检测到 {provider} 的 API Key，需要配置")
                
                # 根据系统语言决定弹出哪个窗口
                from config.gui_i18n import get_system_language
                system_language = get_system_language()
                
                if system_language == 'zh':
                    # 中文系统：弹出新的API配置对话框
                    print("[API Key检查] 中文系统，弹出API配置对话框")
                    try:
                        from api_key_dialog import APIKeyDialog
                        
                        # 在主线程中显示对话框
                        dialog = APIKeyDialog(self)
                        dialog.exec_()
                        
                        # 对话框关闭后，返回提示信息
                        if use_english:
                            return "API Key configuration required. Please configure your API Key and try again."
                        else:
                            return "需要配置API Key。请配置您的API Key后重试。"
                    except Exception as e:
                        print(f"[API Key检查] 显示API配置对话框失败: {e}")
                        if use_english:
                            return f"Failed to show API configuration dialog: {str(e)}"
                        else:
                            return f"显示API配置对话框失败：{str(e)}"
                else:
                    # 非中文系统：运行 setting.exe
                    print("[API Key检查] 非中文系统，运行 setting.exe")
                    try:
                        import subprocess
                        
                        setting_exe = base_path / "llm-api" / "setting.exe"
                        if setting_exe.exists():
                            subprocess.Popen([str(setting_exe)], cwd=str(setting_exe.parent))
                            if use_english:
                                return "API Key configuration required. Please configure your API Key in the settings window and try again."
                            else:
                                return "需要配置API Key。请在设置窗口中配置您的API Key后重试。"
                        else:
                            if use_english:
                                return f"Settings program not found: {setting_exe}"
                            else:
                                return f"设置程序未找到：{setting_exe}"
                    except Exception as e:
                        print(f"[API Key检查] 运行 setting.exe 失败: {e}")
                        if use_english:
                            return f"Failed to run settings program: {str(e)}"
                        else:
                            return f"运行设置程序失败：{str(e)}"
            
            # 检查通过
            return None
            
        except Exception as e:
            print(f"[API Key检查] 检查过程出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错时不阻止执行，让后续的API调用自己处理错误
            return None
    
    def _call_llm_api_for_analysis(self, prompt):
        """实际调用LLM API - 使用与行业分析相同的LLMClient方式"""
        try:
            import sys
            import time
            from pathlib import Path
            
            # 检测当前系统语言
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            
            # 添加llm-api到路径（使用path_helper确保打包环境正确）
            from utils.path_helper import get_base_path
            base_path = get_base_path()  # 打包环境下返回EXE所在目录
            llm_api_path = base_path / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # ===== 新增：强制重新加载配置文件 =====
            import json
            config_path = llm_api_path / "config" / "user_settings.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[个股AI分析] 已强制重新加载AI配置")
            else:
                config = {}
                print("[个股AI分析] 未找到配置文件，使用默认设置")
            
            default_provider = config.get('default_provider', 'OpenAI')
            print(f"[个股AI分析] 当前配置的LLM供应商: {default_provider}")
            
            # ===== 新增：试用模式检查（必须在API Key检查之前）=====
            is_trial_mode = False
            try:
                from utils.ai_usage_counter import get_ai_usage_count
                
                provider = config.get('default_provider', '').lower()
                api_key = config.get('SILICONFLOW_API_KEY', '').strip()
                current_count = get_ai_usage_count()
                
                # 检查是否符合试用条件：SiliconFlow + 无API Key + 计数<20
                if provider == 'siliconflow' and not api_key and current_count < 20:
                    print(f"[个股AI分析-试用模式] 符合试用条件（{current_count}/20次）")
                    print(f"[个股AI分析-试用模式] 使用预设试用配置")
                    
                    # 使用硬编码的试用配置
                    trial_config = {
                        "default_provider": "SiliconFlow",
                        "default_chat_model": "Qwen/Qwen3-8B",
                        "default_structured_model": "Qwen/Qwen3-8B",
                        "request_timeout": 600,
                        "agent_role": "不使用",
                        "SILICONFLOW_API_KEY": "sk-zbzzqzrcjyemnxlgcwiznrkuxrpdkrnpbneurezszujaqfjg",
                        "SILICONFLOW_BASE_URL": "https://api.siliconflow.cn/v1",
                        "dont_show_api_dialog": True
                    }
                    
                    # 使用试用配置
                    config = trial_config
                    is_trial_mode = True
                    default_provider = "SiliconFlow"
                    
                    print(f"[个股AI分析-试用模式] 配置已切换为试用模式，剩余 {20 - current_count} 次试用机会")
                else:
                    if provider == 'siliconflow' and not api_key and current_count >= 20:
                        print(f"[个股AI分析-试用模式] 试用次数已用完（{current_count}/20），请配置API Key")
                        
            except Exception as e:
                print(f"[个股AI分析] 试用检查出错: {e}")
            
            # ===== 新增：检查API Key（如果不是试用模式才检查）=====
            if not is_trial_mode:
                # 注意：这里在AnalysisPage中，不是AnalysisWorker，所以需要直接调用检查逻辑
                api_key_check_result = self._check_api_key_for_stock_analysis(config, default_provider, use_english, base_path)
                if api_key_check_result is not None:
                    # 返回错误信息，终止AI执行
                    return api_key_check_result
            else:
                print(f"[个股AI分析] 试用模式，跳过API Key检查")
            
            # 如果使用Ollama，先检查并启动服务
            if default_provider.lower() == 'ollama':
                print("[个股AI分析] 检测到Ollama供应商，正在检查服务状态...")
                
                # 导入Ollama工具
                try:
                    from ollama_utils import ensure_ollama_and_model
                    model_name = config.get('default_chat_model', 'gemma3:1b')
                    base_url = config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
                    
                    print(f"[个股AI分析] 正在启动Ollama服务并确保模型可用: {model_name}")
                    if not ensure_ollama_and_model(model_name, base_url):
                        return f"无法启动Ollama服务或模型不可用。\n\n 解决方案：\n1. 请确保Ollama已正确安装\n2. 手动运行命令: ollama serve\n3. 检查端口11434是否被占用\n4. 检查防火墙设置"
                    
                    print("[个股AI分析] Ollama服务检查完成，准备进行AI分析")
                    
                except ImportError as e:
                    print(f"[个股AI分析] 无法导入Ollama工具: {e}")
                    return f"Ollama工具模块导入失败: {e}"
            
            # 根据配置的提供商选择合适的LLM客户端
            if default_provider.lower() == 'ollama':
                # Ollama使用SimpleLLMClient
                try:
                    from simple_client import SimpleLLMClient as LLMClient
                    print("[个股AI分析] 使用SimpleLLMClient（Ollama专用）")
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                    client_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(client_module)
                    LLMClient = client_module.SimpleLLMClient
                    print("[个股AI分析] 使用绝对路径导入SimpleLLMClient")
            else:
                # 其他提供商使用完整的LLMClient
                try:
                    from client import LLMClient
                    print(f"[个股AI分析] 使用LLMClient（支持{default_provider}）")
                except ImportError:
                    # 如果无法导入，回退到SimpleLLMClient
                    try:
                        from simple_client import SimpleLLMClient as LLMClient
                        print("[个股AI分析] 回退到SimpleLLMClient")
                    except ImportError:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                        client_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(client_module)
                        LLMClient = client_module.SimpleLLMClient
                        print("[个股AI分析] 使用绝对路径导入SimpleLLMClient作为回退")
            
            # 创建LLM客户端（试用模式下传递临时配置）
            if is_trial_mode:
                print(f"[个股AI分析] 使用试用配置创建客户端")
                client = LLMClient(temp_config=config)
            else:
                client = LLMClient()
            
            start_time = time.time()
            
            # 检测当前系统语言并选择对应的指令
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            
            # 根据系统语言选择指令
            if use_english:
                system_msg = "You are a professional financial analyst with expertise in technical analysis, investment strategies, and stock market analysis. Please respond in English and provide professional investment advice."
                user_msg = "Please analyze the following stock data and provide investment advice:\n\n" + prompt
            else:
                system_msg = "你是一位专业的中文金融分析师，精通技术分析、投资策略和股市分析。请用中文回复，提供专业的投资建议。"
                user_msg = "请用中文分析以下股票数据并提供投资建议：\n\n" + prompt
            
            # 使用SimpleLLMClient统一调用方式（合并system_message到用户消息）
            combined_message = f"{system_msg}\n\n{user_msg}"
            response = client.chat(message=combined_message)
            print(f"[个股AI分析] LLM调用成功，耗时 {time.time() - start_time:.1f}s")
            
            return response
                    
        except Exception as e:
            raise Exception(f"LLM API调用出错: {str(e)}")
    
    def get_stock_basic_info(self, stock_code):
        """获取股票基本信息 - 修复编码错误"""
        try:
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                stocks_data = getattr(self.analysis_results_obj, 'stocks', {})
                if stock_code in stocks_data:
                    stock_info = stocks_data[stock_code]
                    return {
                        'stock_name': stock_info.get('name', stock_code),
                        'industry': stock_info.get('industry', 'Unknown Industry'),
                        'rtsi': stock_info.get('rtsi', {}).get('rtsi', 0) if isinstance(stock_info.get('rtsi'), dict) else stock_info.get('rtsi', 0)
                    }
        except Exception as e:
            print(f"Get stock basic info failed: {e}")
        
        # 返回默认信息
        return {
            'stock_name': stock_code,
            'industry': 'Unknown Industry',
            'rtsi': 0
        }

    def generate_technical_analysis_html(self, ai_result, stock_code):
        """生成技术面分析HTML报告"""
        from datetime import datetime
        
        # 获取股票基本信息
        stock_info = self.get_stock_basic_info(stock_code)
        stock_name = stock_info.get('stock_name', stock_code)
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="{self._get_html_lang()}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{t_gui('technical_analysis_report_title')} - {stock_name}({stock_code})</title>
            <style>
                body {{
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif, 'SimHei', sans-serif;
                    line-height: 1.8;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                }}
                .container {{
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: bold;
                }}
                .header .subtitle {{
                    margin-top: 10px;
                    font-size: 16px;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px;
                }}
                .analysis-content {{
                    background: #f8f9fa;
                    border-left: 4px solid #007bff;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    white-space: pre-wrap;
                    font-size: 14px;
                    line-height: 1.8;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-top: 1px solid #dee2e6;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .analyst-badge {{
                    display: inline-block;
                    background: #007bff;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 12px;
                    margin-bottom: 15px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔧 技术面分析报告</h1>
                    <div class="subtitle">{stock_name} ({stock_code})</div>
                    <div class="subtitle">Analysis Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
                    <div class="subtitle" style="font-size: 14px; margin-top: 10px; opacity: 0.8;">作者：267278466@qq.com</div>
                </div>
                <div class="content">
                    <div class="analyst-badge">🔧 技术面分析师 (本地数据)</div>
                    <div class="analysis-content">{ai_result}</div>
                </div>
                <div class="footer">
                    <p>🔧 本报告由AI技术面分析师生成，基于RTSI指数、评级趋势和本地量价数据分析</p>
                    <p> 数据源：cn-lj.dat.gz 本地数据库，无需联网查询</p>
                    <p> 投资有风险，决策需谨慎。本报告仅供参考，不构成投资建议。</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content
    
    def generate_master_analysis_html(self, ai_result, stock_code):
        """生成投资大师分析HTML报告"""
        from datetime import datetime
        
        # 获取股票基本信息
        stock_info = self.get_stock_basic_info(stock_code)
        stock_name = stock_info.get('stock_name', stock_code)
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>投资大师分析报告 - {stock_name}({stock_code})</title>
            <style>
                body {{
                    font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif, 'SimHei', sans-serif;
                    line-height: 1.8;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%);
                    color: #333;
                }}
                .container {{
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: bold;
                }}
                .header .subtitle {{
                    margin-top: 10px;
                    font-size: 16px;
                    opacity: 0.9;
                }}
                .content {{
                    padding: 30px;
                }}
                .analysis-content {{
                    background: #f8f9fa;
                    border-left: 4px solid #dc3545;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    white-space: pre-wrap;
                    font-size: 14px;
                    line-height: 1.8;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    border-top: 1px solid #dee2e6;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .analyst-badge {{
                    display: inline-block;
                    background: #dc3545;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 12px;
                    margin-bottom: 15px;
                }}
                .masters-row {{
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin-bottom: 15px;
                    flex-wrap: wrap;
                }}
                .master-badge {{
                    background: #6c757d;
                    color: white;
                    padding: 3px 10px;
                    border-radius: 15px;
                    font-size: 11px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1> 投资大师分析报告</h1>
                    <div class="subtitle">{stock_name} ({stock_code})</div>
                    <div class="subtitle">Analysis Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
                    <div class="subtitle" style="font-size: 14px; margin-top: 10px; opacity: 0.8;">作者：267278466@qq.com</div>
                </div>
                <div class="content">
                    <div class="analyst-badge"> 投资大师分析</div>
                    <div class="masters-row">
                        <span class="master-badge">🏛️ 巴菲特</span>
                        <span class="master-badge"> 彼得林奇</span>
                        <span class="master-badge"> 格雷厄姆</span>
                        <span class="master-badge">⚡ 德鲁肯米勒</span>
                        <span class="master-badge">🔄 迈克尔·伯里</span>
                    </div>
                    <div class="analysis-content">{ai_result}</div>
                </div>
                <div class="footer">
                    <p> 本报告由AI模拟五位投资大师生成，融合巴菲特、彼得林奇、格雷厄姆、德鲁肯米勒、迈克尔·伯里的投资理念</p>
                    <p> 投资有风险，决策需谨慎。本报告仅供参考，不构成投资建议。</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content

    def show_cached_technical_result(self, stock_code):
        """显示缓存的技术面分析结果并切换到结果页"""
        cache_key = f"technical_{stock_code}"
        cached_result = self.stock_ai_cache[cache_key]
        self.set_technical_html(cached_result['html'])
        
        # 切换到结果页面（第2页）
        if hasattr(self, 'technical_stacked_widget'):
            self.technical_stacked_widget.setCurrentIndex(1)
    
    def show_cached_master_result(self, stock_code):
        """显示缓存的投资大师分析结果并切换到结果页"""
        cache_key = f"master_{stock_code}"
        cached_result = self.stock_ai_cache[cache_key]
        self.set_master_html(cached_result['html'])
        
        # 切换到结果页面（第2页）
        if hasattr(self, 'master_stacked_widget'):
            self.master_stacked_widget.setCurrentIndex(1)
    
    def set_technical_html(self, html_content):
        """设置技术面分析HTML内容"""
        try:
            if hasattr(self, 'technical_result_browser'):
                if hasattr(self.technical_result_browser, 'setHtml'):
                    self.technical_result_browser.setHtml(html_content)
                else:
                    # QTextEdit 回退方案
                    self.technical_result_browser.setHtml(html_content)
        except Exception as e:
            print(f"设置技术面分析HTML失败: {e}")
    
    def set_master_html(self, html_content):
        """设置投资大师分析HTML内容"""
        try:
            if hasattr(self, 'master_result_browser'):
                if hasattr(self.master_result_browser, 'setHtml'):
                    self.master_result_browser.setHtml(html_content)
                else:
                    # QTextEdit 回退方案
                    self.master_result_browser.setHtml(html_content)
        except Exception as e:
            print(f"设置投资大师分析HTML失败: {e}")
    
    def start_stock_ai_analysis(self):
        """开始个股AI分析"""
        if not self.analysis_results_obj:
            QMessageBox.warning(self, t_gui('warning'), "请先加载股票数据并选择要分析的股票")
            return
        
        if not hasattr(self, 'current_stock_code') or not self.current_stock_code:
            QMessageBox.warning(self, t_gui('warning'), "请先选择要分析的股票")
            return
        
        # 防止重复分析
        if self.ai_analysis_in_progress:
            QMessageBox.information(self, t_gui('info'), "AI分析正在进行中，请稍候...")
            return
        
        # 检查缓存，如果有缓存直接显示结果页
        if self.current_stock_code in self.stock_ai_cache:
            self.show_cached_ai_result(self.current_stock_code)
            return
        
        # 开始分析
        self.perform_stock_ai_analysis(self.current_stock_code)
    
    def show_cached_ai_result(self, stock_code):
        """显示缓存的AI分析结果并切换到结果页"""
        cached_result = self.stock_ai_cache[stock_code]
        self.set_stock_ai_html(cached_result['html'])
        
        # 切换到结果页面（第2页）
        if hasattr(self, 'ai_stacked_widget'):
            self.ai_stacked_widget.setCurrentIndex(1)
    
    def update_ai_buttons_state(self):
        """更新AI分析按钮的状态"""
        if not hasattr(self, 'ai_analysis_btn') or not hasattr(self, 'save_html_btn'):
            return
            
        if self.ai_analysis_executed:
            # 已执行AI分析：隐藏AI分析按钮，显示另存为按钮
            self.ai_analysis_btn.setVisible(False)
            self.save_html_btn.setVisible(True)
        else:
            # 未执行AI分析：显示AI分析按钮，隐藏另存为按钮
            self.ai_analysis_btn.setVisible(True)
            self.save_html_btn.setVisible(False)
    
    def start_ai_analysis(self):
        """执行AI智能分析 - 直接使用已有分析结果
        
        注意：这是主AI分析功能，与行业分析和个股分析的AI功能不同
        主分析会综合大盘、行业、个股三个层面提供全面的投资分析报告
        """
        if not self.analysis_results:
            QMessageBox.warning(self, t_gui("警告"), t_gui("请先完成基础分析"))
            return
            
        # 设置按键为分析中状态
        if hasattr(self, 'ai_analysis_btn'):
            self.ai_analysis_btn.setEnabled(False)
            self.ai_analysis_btn.setText("🔄 分析中...")
            self.ai_analysis_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
            """)
            # 强制刷新UI显示
            self.ai_analysis_btn.repaint()
            self.ai_analysis_btn.update()
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
        # 防止重复分析
        if self.ai_analysis_in_progress:
            QMessageBox.information(self, t_gui("提示"), t_gui("AI分析正在进行中，请稍候..."))
            return
        
        try:
            self.ai_analysis_in_progress = True
            # 按键状态已在上面设置，这里不重复设置
            
            # 【修复方案】直接使用已有分析结果，不重新运行worker
            print(f"🚨 [主AI分析调试] 开始AI分析，使用已有分析结果")
            print(f"🚨 [主AI分析调试] analysis_results 类型: {type(self.analysis_results)}")
            
            if isinstance(self.analysis_results, dict) and 'analysis_results' in self.analysis_results:
                # 如果存储在字典中
                actual_analysis_results = self.analysis_results['analysis_results']
                print(f"🚨 [主AI分析调试] 从字典中获取 analysis_results: {type(actual_analysis_results)}")
            else:
                # 直接使用
                actual_analysis_results = self.analysis_results
                print(f"🚨 [主AI分析调试] 直接使用 analysis_results: {type(actual_analysis_results)}")
            
            # 创建临时Worker仅用于AI分析
            # 确保使用正确的数据文件路径
            data_file_path = getattr(self, 'data_file_path', 'CN_Data5000.json.gz')
            temp_worker = AnalysisWorker(data_file_path, enable_ai_analysis=True)
            ai_result = temp_worker.run_ai_analysis(actual_analysis_results)
            
            if ai_result:
                print(f"🚨 [主AI分析调试] AI分析成功，结果长度: {len(ai_result) if ai_result else 0}")
                
                # 生成完整的HTML报告（包含基础分析+AI分析）
                try:
                    from datetime import datetime
                    import os
                    
                    # 确保reports目录存在（使用正确的路径）
                    reports_dir = get_reports_dir()
                    
                    # 生成HTML文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    html_filename = str(reports_dir / f"analysis_report_{timestamp}.html")
                    
                    print(f"🚨 [主AI分析调试] 开始生成完整HTML报告，包含基础分析+AI分析")
                    
                    # 生成完整的HTML报告，包含基础分析数据
                    # 使用临时worker的generate_html_report方法（返回文件路径）
                    html_file_path = temp_worker.generate_html_report(actual_analysis_results)
                    
                    # 读取生成的HTML文件内容
                    if html_file_path and os.path.exists(html_file_path):
                        with open(html_file_path, 'r', encoding='utf-8') as f:
                            full_html_content = f.read()
                        print(f"🚨 [HTML调试] 成功读取基础HTML文件: {html_file_path}")
                        print(f"🚨 [HTML调试] 基础HTML长度: {len(full_html_content)}")
                        print(f"🚨 [HTML调试] 基础HTML前200字符: {full_html_content[:200]}")
                        print(f"🚨 [HTML调试] 基础HTML是否包含</body>: {'</body>' in full_html_content}")
                    else:
                        print(f"[ERROR] [HTML调试] 无法读取基础HTML文件: {html_file_path}")
                        full_html_content = ""
                    
                    # 在HTML报告中添加AI分析部分
                    ai_section_html = f"""
<!-- AI智能分析部分 -->
<div class="section ai-analysis-section" style="border-top: 3px solid #007bff; margin-top: 30px;">
    <h2 style="color: #007bff; display: flex; align-items: center;">
        <span style="margin-right: 10px;"></span> AI智能分析
    </h2>
    <div class="ai-content" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
        <div style="white-space: pre-wrap; line-height: 1.6;">{ai_result}</div>
    </div>
</div>

</body>
</html>
"""
                    
                    # 首先删除基础HTML中的AI占位符部分
                    # 查找并删除旧的AI分析占位符（包含"AI功能未执行"的部分）
                    import re
                    ai_placeholder_pattern = r'<div class="section">\s*<h2>[^<]*AI智能分析</h2>.*?</div>\s*</div>'
                    clean_html_content = re.sub(ai_placeholder_pattern, '', full_html_content, flags=re.DOTALL)
                    
                    # 更新标题为"AI智能分析报告"
                    clean_html_content = clean_html_content.replace('<title>智能分析报告</title>', '<title>AI智能分析报告</title>')
                    
                    # 更新页面主标题（H1）
                    clean_html_content = clean_html_content.replace('<h1>智能分析报告</h1>', '<h1>AI智能分析报告</h1>')
                    
                    # 更新header背景色为金黄色
                    clean_html_content = clean_html_content.replace(
                        '.header { background: #f4f4f4;',
                        '.header { background: linear-gradient(135deg, #ffd700, #ffed4e);'
                    )
                    
                    print(f"🚨 [HTML清理调试] 删除AI占位符后的HTML长度: {len(clean_html_content)}")
                    print(f"🚨 [HTML样式调试] 已更新标题和header背景色为金黄色")
                    
                    # 将新的AI分析部分插入到清理后的HTML末尾（在</body></html>之前）
                    if clean_html_content.endswith('</body>\n</html>'):
                        complete_html = clean_html_content.replace('</body>\n</html>', ai_section_html)
                    elif clean_html_content.endswith('</body></html>'):
                        complete_html = clean_html_content.replace('</body></html>', ai_section_html)
                    else:
                        # 如果没有找到结束标签，直接添加到末尾
                        complete_html = clean_html_content + ai_section_html
                    
                    # 保存完整的HTML文件
                    with open(html_filename, 'w', encoding='utf-8') as f:
                        f.write(complete_html)
                    
                    print(f"🚨 [主AI分析调试] 完整HTML报告已生成: {html_filename}")
                    print(f"🚨 [主AI分析调试] 报告包含基础分析 + AI分析，总长度: {len(complete_html)}")
                    
                    # 调用完成处理
                    self._on_ai_analysis_completed({
                        'ai_analysis': ai_result,
                        'html_report_path': html_filename
                    })
                    
                except Exception as html_error:
                    print(f"🚨 [主AI分析调试] 生成完整HTML失败: {html_error}")
                    import traceback
                    traceback.print_exc()
                    # 即使HTML生成失败，也要处理AI结果
                    self._on_ai_analysis_completed({'ai_analysis': ai_result})
                    
            else:
                print(f"🚨 [主AI分析调试] AI分析失败")
                self._on_ai_analysis_failed("AI分析返回空结果")
            
        except Exception as e:
            print(f"🚨 [主AI分析调试] AI分析异常: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, t_gui("错误"), f"{t_gui('启动AI分析失败')}{str(e)}")
            self._reset_ai_analysis_state()
    
    def _run_ai_analysis_with_worker(self):
        """使用AnalysisWorker运行AI分析"""
        try:
            # 【修复数据路径获取逻辑】
            data_file_path = ""
            print(f"🚨 [AI分析路径调试] self.analysis_results 结构: {type(self.analysis_results)}")
            print(f"🚨 [AI分析路径调试] self.analysis_results 内容: {self.analysis_results.keys() if isinstance(self.analysis_results, dict) else '非字典类型'}")
            
            if isinstance(self.analysis_results, dict) and 'data_source' in self.analysis_results:
                data_source = self.analysis_results['data_source']
                print(f"🚨 [AI分析路径调试] data_source 类型: {type(data_source)}")
                if hasattr(data_source, 'file_path'):
                    data_file_path = data_source.file_path
                    print(f"🚨 [AI分析路径调试] 获取到数据文件路径: {data_file_path}")
                else:
                    print(f"🚨 [AI分析路径调试] data_source 没有 file_path 属性")
            else:
                print(f"🚨 [AI分析路径调试] analysis_results 中没有 data_source 或类型错误")
                
            # 回退方案：尝试从实例变量获取数据文件路径
            if not data_file_path and hasattr(self, 'data_file_path'):
                data_file_path = self.data_file_path
                print(f"🚨 [AI分析路径调试] 使用回退路径: {data_file_path}")
                
            # 最后的回退方案：使用中国数据文件
            if not data_file_path:
                data_file_path = "CN_Data5000.json.gz"
                print(f"🚨 [AI分析路径调试] 使用默认中国数据文件: {data_file_path}")
            
            print(f"🚨 [AI分析路径调试] 最终使用的数据文件路径: {data_file_path}")
            
            # 创建启用AI的AnalysisWorker
            self.ai_worker = AnalysisWorker(data_file_path, enable_ai_analysis=True)
            
            # 连接信号
            self.ai_worker.progress_updated.connect(self._on_ai_progress_updated)
            self.ai_worker.analysis_completed.connect(self._on_ai_analysis_completed)
            self.ai_worker.analysis_failed.connect(self._on_ai_analysis_failed)
            
            # 启动AI分析
            self.ai_worker.start()
            
        except Exception as e:
            self._show_ai_analysis_error(f"启动AI分析Worker失败：{str(e)}")
    
    def _on_ai_progress_updated(self, value, text):
        """AI分析进度更新"""
        # 更新按钮显示进度 - 只显示数字，不显示文字
        if value >= 70:  # AI分析阶段
            self.ai_analysis_btn.setText(f"{value}")
    
    def _on_ai_analysis_completed(self, results):
        """AI分析完成"""
        try:
            print(f"🚨 [AI完成处理调试] 收到结果: {type(results)}")
            print(f"🚨 [AI完成处理调试] 结果内容键: {results.keys() if isinstance(results, dict) else '非字典'}")
            
            # 更新分析结果
            self.analysis_results.update(results)
            self.ai_analysis_executed = True
            
            # 重新加载HTML报告
            html_path = results.get('html_report_path')
            print(f"🚨 [AI完成处理调试] HTML路径: {html_path}")
            
            if html_path:
                import os
                file_exists = os.path.exists(html_path)
                print(f"🚨 [AI完成处理调试] HTML文件是否存在: {file_exists}")
                
                if file_exists:
                    self.analysis_results['html_report_path'] = html_path
                    # 保存AI分析HTML路径供另存为按钮使用
                    self.current_html_path = html_path
                    print(f"💾 [另存为调试] 已更新current_html_path为: {html_path}")
                    
                    # 启用另存为按钮
                    if hasattr(self, 'save_html_btn'):
                        self.save_html_btn.setEnabled(True)
                        print(f" [另存为调试] 已启用另存为按钮")
                    
                    self._reload_ai_html(html_path)
                else:
                    print(f"[ERROR] [AI完成处理调试] HTML文件不存在: {html_path}")
            else:
                print(f" [AI完成处理调试] 没有HTML路径，尝试生成完整报告并直接显示")
                # 如果没有HTML路径，生成完整的HTML报告并直接显示
                ai_content = results.get('ai_analysis', '')
                if ai_content and hasattr(self, 'ai_webview'):
                    try:
                        # 尝试获取基础分析数据
                        if isinstance(self.analysis_results, dict) and 'analysis_results' in self.analysis_results:
                            base_analysis_results = self.analysis_results['analysis_results']
                        else:
                            base_analysis_results = self.analysis_results
                            
                        # 生成完整的HTML报告
                        print(f"[DOC] [AI完成处理调试] 生成包含基础分析的完整HTML")
                        # 创建临时worker来生成HTML报告
                        data_file_path_for_html = getattr(self, 'data_file_path', 'CN_Data5000.json.gz')
                        temp_worker_for_html = AnalysisWorker(data_file_path_for_html, enable_ai_analysis=False)
                        html_file_path_backup = temp_worker_for_html.generate_html_report(base_analysis_results)
                        
                        # 读取生成的HTML文件内容
                        if html_file_path_backup and os.path.exists(html_file_path_backup):
                            with open(html_file_path_backup, 'r', encoding='utf-8') as f:
                                full_html = f.read()
                            print(f"[DOC] [AI完成处理调试] 成功读取备用HTML文件: {html_file_path_backup}")
                        else:
                            print(f"[ERROR] [AI完成处理调试] 无法读取备用HTML文件: {html_file_path_backup}")
                            full_html = ""
                        
                        # 添加AI分析部分
                        ai_section = f"""
<!-- AI智能分析部分 -->
<div class="section ai-analysis-section" style="border-top: 3px solid #007bff; margin-top: 30px;">
    <h2 style="color: #007bff; display: flex; align-items: center;">
        <span style="margin-right: 10px;"></span> AI智能分析
    </h2>
    <div class="ai-content" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
        <div style="white-space: pre-wrap; line-height: 1.6;">{ai_content}</div>
    </div>
</div>

</body>
</html>
"""
                        
                        # 首先删除基础HTML中的AI占位符部分
                        import re
                        ai_placeholder_pattern = r'<div class="section">\s*<h2>[^<]*AI智能分析</h2>.*?</div>\s*</div>'
                        clean_html = re.sub(ai_placeholder_pattern, '', full_html, flags=re.DOTALL)
                        
                        # 更新标题为"AI智能分析报告"
                        clean_html = clean_html.replace('<title>智能分析报告</title>', '<title>AI智能分析报告</title>')
                        
                        # 更新页面主标题（H1）
                        clean_html = clean_html.replace('<h1>智能分析报告</h1>', '<h1>AI智能分析报告</h1>')
                        
                        # 更新header背景色为金黄色
                        clean_html = clean_html.replace(
                            '.header { background: #f4f4f4;',
                            '.header { background: linear-gradient(135deg, #ffd700, #ffed4e);'
                        )
                        
                        # 插入AI分析到清理后的HTML
                        if clean_html.endswith('</body>\n</html>'):
                            complete_html = clean_html.replace('</body>\n</html>', ai_section)
                        elif clean_html.endswith('</body></html>'):
                            complete_html = clean_html.replace('</body></html>', ai_section)
                        else:
                            complete_html = clean_html + ai_section
                            
                        self.ai_webview.setHtml(complete_html)
                        print(f"[DOC] [AI完成处理调试] 已设置完整HTML到WebView，包含基础分析+AI分析")
                        
                    except Exception as e:
                        print(f"[ERROR] [AI完成处理调试] 生成完整HTML失败: {e}")
                        # 回退到简单显示
                        simple_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI分析结果</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .content {{ white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="header">
        <h1> AI智能分析报告</h1>
        <p> 无法加载完整分析报告，仅显示AI分析内容</p>
    </div>
    <div class="content">{ai_content}</div>
</body>
</html>
"""
                        self.ai_webview.setHtml(simple_html)
                        print(f"[DOC] [AI完成处理调试] 回退到简单HTML显示")
            
            # 更新按钮状态 - 隐藏AI分析按钮，显示另存为按钮
            self.update_ai_buttons_state()
            
            # 恢复并设置AI分析按钮状态
            if hasattr(self, 'ai_analysis_btn'):
                self.ai_analysis_btn.setEnabled(True)
                self.ai_analysis_btn.setText(" AI分析")
                # 恢复原来的蓝色样式
                self.ai_analysis_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 15px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                    QPushButton:pressed {
                        background-color: #004085;
                    }
                    QPushButton:disabled {
                        background-color: #6c757d;
                        color: #f8f9fa;
                    }
                """)
            
            # 重置分析状态
            self._reset_ai_analysis_state()
            
            print("🎉 AI分析完成，HTML已更新")
            
        except Exception as e:
            print(f"[ERROR] [AI完成处理调试] 处理AI分析结果失败: {str(e)}")
            import traceback
            traceback.print_exc()
            self._show_ai_analysis_error(f"处理AI分析结果失败：{str(e)}")
    
    def _on_ai_analysis_failed(self, error_msg):
        """AI分析失败"""
        self._show_ai_analysis_error(f"AI分析失败：{error_msg}")
    
    def _reload_ai_html(self, html_path):
        """重新加载AI分析HTML"""
        try:
            from PyQt5.QtCore import QUrl
            from pathlib import Path
            
            if hasattr(self, 'ai_webview'):
                # 使用WebEngine浏览器加载
                file_url = QUrl.fromLocalFile(str(Path(html_path).absolute()))
                self.ai_webview.load(file_url)
                print(f"[DOC] AI分析HTML已重新加载到WebView：{html_path}")
            elif hasattr(self, 'ai_browser'):
                # 使用文本浏览器加载
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.ai_browser.setHtml(html_content)
                print(f"[DOC] AI分析HTML已重新加载到TextBrowser：{html_path}")
            else:
                print(" 找不到AI显示组件")
            
        except Exception as e:
            print(f"[ERROR] 重新加载HTML失败：{str(e)}")
    
    def _reset_ai_analysis_state(self):
        """重置AI分析状态"""
        self.ai_analysis_in_progress = False
        self.ai_analysis_btn.setEnabled(True)
        self.ai_analysis_btn.setText("AI分析")
    
    def _run_ai_analysis_thread(self):
        """在后台线程中运行AI分析 - 保留旧方法以防兼容性问题"""
        try:
            # 准备分析数据
            analysis_data = self._prepare_analysis_data_for_ai()
            
            # 调用LLM API
            ai_response = self._call_llm_api_for_ai(analysis_data)
            
            # 使用QTimer延迟在主线程中更新UI
            QTimer.singleShot(0, lambda: self._update_ai_analysis_result(ai_response))
            
        except Exception as e:
            # 使用QTimer延迟在主线程中显示错误
            QTimer.singleShot(0, lambda: self._show_ai_analysis_error(str(e)))
    
    def _prepare_analysis_data_for_ai(self):
        """为AI分析准备数据"""
        # 这里可以复用AnalysisWorker中的逻辑
        # 简化版本
        return {
            'analysis_results': self.analysis_results,
            'market_data': self.analysis_dict
        }
    
    def _call_llm_api_for_ai(self, data):
        """调用LLM API进行AI分析"""
        # 这里需要实现LLM API调用逻辑
        # 可以复用AnalysisWorker中的实现
        return "AI分析结果示例"
    
    def _update_ai_analysis_result(self, ai_result):
        """更新AI分析结果到UI"""
        try:
            # 在主线程中更新
            if ai_result:
                self.analysis_results['ai_analysis'] = ai_result
                self.ai_analysis_executed = True
                
                # 重新生成HTML报告
                self._regenerate_html_with_ai()
                
                # 更新按钮状态
                self.update_ai_buttons_state()
                
                QMessageBox.information(self, t_gui("成功"), t_gui("AI分析完成！"))
            else:
                QMessageBox.warning(self, t_gui("失败"), "AI分析未能生成有效结果")
                
        except Exception as e:
            QMessageBox.critical(self, t_gui("错误"), f"{t_gui('更新AI分析结果失败')}{str(e)}")
        finally:
            self.ai_analysis_in_progress = False
            self.ai_analysis_btn.setEnabled(True)
            self.ai_analysis_btn.setText("AI分析")
    
    def _show_ai_analysis_error(self, error_msg):
        """显示AI分析错误"""
        print(f"[ERROR] AI分析错误：{error_msg}")
        # 不弹出错误对话框，只在控制台输出错误信息
        # QMessageBox.critical(self, "AI分析失败", f"AI分析过程中出现错误：\n{error_msg}")
        self._reset_ai_analysis_state()
    
    def _regenerate_html_with_ai(self):
        """重新生成包含AI分析的HTML报告"""
        try:
            # 生成新的HTML报告
            analysis_worker = AnalysisWorker("", True)  # 临时实例用于生成HTML
            html_path = analysis_worker.generate_html_report(self.analysis_results)
            
            if html_path:
                self.analysis_results['html_report_path'] = html_path
                # 更新AI页面显示
                self.update_ai_suggestions()
                print(f"HTML报告已更新：{html_path}")
            
        except Exception as e:
            print(f"重新生成HTML失败：{str(e)}")
    
    def _check_llm_config(self):
        """检查LLM配置文件"""
        try:
            from pathlib import Path
            config_file = Path("llm-api/config.json")
            return config_file.exists()
        except:
            return False
    
    def perform_stock_ai_analysis(self, stock_code):
        """执行股票AI分析 - 改为单线程避免崩溃"""
        try:
            # 设置分析状态
            self.ai_analysis_in_progress = True
            self.current_ai_stock = stock_code
            self.stock_ai_analyze_btn.setEnabled(False)
            self.stock_ai_analyze_btn.setText(t_gui("分析中"))
            self.ai_status_label.setText(t_gui("🔄_AI正在分析_请稍候"))
            
            # 收集分析数据
            analysis_data = self.collect_stock_analysis_data(stock_code)
            
            # 保存当前分析数据，用于结果显示
            self.current_analysis_data = analysis_data
            
            # 生成AI分析提示词
            prompt = self.generate_ai_analysis_prompt(analysis_data)
            
            # 使用单线程直接调用，避免PyQt5多线程崩溃
            QTimer.singleShot(100, lambda: self._perform_ai_analysis_sync(prompt))
            
        except Exception as e:
            self.on_ai_analysis_error(str(e))
    
    def _perform_ai_analysis_sync(self, prompt):
        """同步执行AI分析，避免多线程问题"""
        analysis_type = "股票AI分析"
        
        try:
            # ===== 执行前检查 =====
            can_proceed, config = self._ai_analysis_before(analysis_type)
            if not can_proceed:
                self.on_ai_analysis_error("执行前检查未通过")
                return
            
            # 执行分析
            result = self._call_llm_for_stock_analysis(prompt)
            
            # ===== 执行后处理 =====
            if result:
                self._ai_analysis_after(success=True, analysis_type=analysis_type)
                self.on_ai_analysis_finished(result)
            else:
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_ai_analysis_error("AI分析未返回结果")
                
        except Exception as e:
            self._ai_analysis_after(success=False, analysis_type=analysis_type)
            self.on_ai_analysis_error(str(e))
    
    def _call_llm_for_stock_analysis(self, prompt):
        """同步调用LLM进行个股分析"""
        try:
            import sys
            import time
            from pathlib import Path
            
            # 添加llm-api到路径（使用path_helper确保打包环境正确）
            from utils.path_helper import get_base_path
            base_path = get_base_path()  # 打包环境下返回EXE所在目录
            llm_api_path = base_path / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # 读取配置文件获取提供商信息（使用缓存）
            config = {}
            try:
                import json
                
                # 检查缓存是否有效（使用AnalysisWorker的缓存）
                current_time = time.time()
                if (AnalysisWorker._ai_config_cache is not None and 
                    current_time - AnalysisWorker._ai_config_cache_time < AnalysisWorker._ai_config_cache_ttl):
                    config = AnalysisWorker._ai_config_cache
                    print(f"[个股AI分析] 使用缓存的AI配置")
                else:
                    # 从文件加载配置
                    config_path = llm_api_path / "config" / "user_settings.json"
                    if config_path.exists():
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            # 更新缓存
                            AnalysisWorker._ai_config_cache = config
                            AnalysisWorker._ai_config_cache_time = current_time
                            default_provider = config.get('default_provider', 'OpenAI')
                            print(f"[个股AI分析] 已加载并缓存AI配置，供应商: {default_provider}")
                    else:
                        print("[个股AI分析] 未找到配置文件，使用默认设置")
            except Exception as e:
                print(f"[个股AI分析] 读取配置文件时出错: {e}")
            
            # 根据配置的提供商选择合适的LLM客户端
            default_provider = config.get('default_provider', 'OpenAI')
            
            if default_provider.lower() == 'ollama':
                # Ollama使用SimpleLLMClient
                try:
                    from simple_client import SimpleLLMClient as LLMClient
                    print("[个股AI分析] 使用SimpleLLMClient（Ollama专用）")
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                    client_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(client_module)
                    LLMClient = client_module.SimpleLLMClient
                    print("[个股AI分析] 使用绝对路径导入SimpleLLMClient")
            else:
                # 其他提供商使用完整的LLMClient
                try:
                    from client import LLMClient
                    print(f"[个股AI分析] 使用LLMClient（支持{default_provider}）")
                except ImportError:
                    # 如果无法导入，回退到SimpleLLMClient
                    try:
                        from simple_client import SimpleLLMClient as LLMClient
                        print("[个股AI分析] 回退到SimpleLLMClient")
                    except ImportError:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                        client_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(client_module)
                        LLMClient = client_module.SimpleLLMClient
                        print("[个股AI分析] 使用绝对路径导入SimpleLLMClient作为回退")
            
            # 创建LLM客户端
            client = LLMClient()
            
            start_time = time.time()
            
            # 检测当前系统语言并选择对应的指令
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            
            # 根据系统语言选择指令
            if use_english:
                system_msg = "You are a professional financial analyst with expertise in stock analysis, technical analysis, and fundamental analysis. Please respond in English and provide professional investment advice."
                user_msg = "Please analyze the following stock data and provide investment advice:\n\n" + prompt
            else:
                system_msg = "你是一位专业的中文金融分析师，精通股票分析、技术分析和基本面分析。请用中文回复，提供专业的投资建议。"
                user_msg = "请用中文分析以下股票数据并提供投资建议：\n\n" + prompt
            
            # 使用SimpleLLMClient统一调用方式（合并system_message到用户消息）
            combined_message = f"{system_msg}\n\n{user_msg}"
            response = client.chat(message=combined_message)
            print(f"[个股AI分析] LLM调用成功，耗时 {time.time() - start_time:.1f}s")
            
            return response
            
        except Exception as e:
            return f"AI分析失败：{str(e)}\n\n请检查LLM配置是否正确。"
    
    def collect_stock_analysis_data(self, stock_code):
        """收集股票分析数据"""
        from datetime import datetime
        
        data = {
            'stock_code': stock_code,
            'stock_name': '',
            'rtsi': 0,
            'industry': '',
            'industry_tma': 0,
            'market_msci': 0,
            'market_sentiment': '',
            'recent_ratings': [],
            'volume_price_data': None,
            'has_real_volume_price_data': False,
            'data_source_info': ''
        }
        
        try:
            # 获取股票基本信息
            if hasattr(self, 'current_stock_info') and self.current_stock_info:
                data['stock_name'] = self.current_stock_info.get('name', stock_code)
                data['rtsi'] = self.current_stock_info.get('rtsi', {}).get('rtsi', 0)
                data['industry'] = self.current_stock_info.get('industry', t_gui('unknown'))
            
            # 获取行业TMA信息
            if self.analysis_results_obj and hasattr(self.analysis_results_obj, 'industries'):
                industry_info = self.analysis_results_obj.industries.get(data['industry'], {})
                if 'irsi' in industry_info:
                    irsi_data = industry_info['irsi']
                    if isinstance(irsi_data, dict):
                        data['industry_tma'] = irsi_data.get('enhanced_tma_score', irsi_data.get('irsi', 0))
                    else:
                        data['industry_tma'] = irsi_data
            
            # 获取大盘信息
            if self.analysis_results_obj and hasattr(self.analysis_results_obj, 'market'):
                market_info = self.analysis_results_obj.market
                data['market_msci'] = market_info.get('current_msci', 0)
                data['market_sentiment'] = market_info.get('market_state', t_gui('unknown'))
            
            # 获取最近30天评级趋势（真实数据）
            data['recent_ratings'] = self.get_recent_rating_trend(stock_code)
            
            # 优化：优先使用本地lj-read数据，避免联网查询
            volume_price_result = self.get_cached_volume_price_data(stock_code, days=30)
            if volume_price_result:
                data['volume_price_data'] = {
                    'success': True,
                    'data': volume_price_result,
                    'source': 'local_lj_data',
                    'market': self._get_preferred_market_from_current_data() or 'cn'
                }
                data['has_real_volume_price_data'] = True
                data['data_source_info'] = f"采用本地量价数据 (cn-lj.dat.gz)"
            else:
                # 回退到联网查询
                volume_price_result = self.get_volume_price_data(stock_code)
            if volume_price_result:
                data['volume_price_data'] = volume_price_result
                data['has_real_volume_price_data'] = volume_price_result.get('success', False)
                if data['has_real_volume_price_data']:
                        data['data_source_info'] = f"采用联网量价数据 ({volume_price_result.get('market', '').upper()}市场)"
                else:
                    data['data_source_info'] = f"量价数据获取失败: {volume_price_result.get('error', '未知错误') if volume_price_result else '未知错误'}"
            
        except Exception as e:
            print(f"收集分析数据失败: {e}")
        
        return data
    
    def get_volume_price_data(self, stock_code):
        """获取量价数据 - 使用统一缓存接口"""
        try:
            # 清理股票代码格式
            if stock_code.startswith('="') and stock_code.endswith('"'):
                clean_code = stock_code[2:-1]
            else:
                clean_code = stock_code
            
            # 从统一缓存接口获取5天量价数据（AI分析用）
            volume_price_data = self.get_cached_volume_price_data(clean_code, days=5)
            
            if not volume_price_data:
                # 根据当前加载的数据文件推断优先市场
                preferred_market = self._get_preferred_market_from_current_data()
                return {
                    'success': False,
                    'error': f'无法获取量价数据 ({preferred_market or "未知"}市场)',
                    'data_source': 'cache_miss',
                    'market': preferred_market or 'unknown'
                }
            
            # 转换为与原有接口兼容的格式
            result = {
                'success': True,
                'data_source': 'cached_data',
                'market': volume_price_data.get('market', 'unknown'),
                'stock_code': volume_price_data['stock_code'],
                'stock_name': volume_price_data['stock_name'],
                'volume_price_data': {},
                'summary': {
                    'total_days': volume_price_data['total_days'],
                    'date_range': {
                        'start': volume_price_data['data'][0]['date'] if volume_price_data['data'] else '',
                        'end': volume_price_data['data'][-1]['date'] if volume_price_data['data'] else ''
                    },
                    'data_completeness': 1.0,
                    'price_stats': {},
                    'volume_stats': {}
                }
            }
            
            # 转换数据格式并计算统计信息
            trade_data = {}
            prices = []
            volumes = []
            
            for day_data in volume_price_data['data']:
                date = day_data['date']
                trade_data[date] = {
                    '收盘价': day_data['close_price'],
                    '成交金额': day_data['volume'],
                    '开盘价': day_data.get('open_price', day_data['close_price']),
                    '最高价': day_data.get('high_price', day_data['close_price']),
                    '最低价': day_data.get('low_price', day_data['close_price'])
                }
                prices.append(day_data['close_price'])
                volumes.append(day_data['volume'])
            
            result['volume_price_data'] = trade_data
            
            # 计算价格统计
            if prices:
                import statistics
                result['summary']['price_stats'] = {
                    'count': len(prices),
                    'min': min(prices),
                    'max': max(prices),
                    'avg': statistics.mean(prices),
                    'latest': prices[-1],
                    'change_rate': (prices[-1] - prices[0]) / prices[0] * 100 if len(prices) > 1 else 0
                }
            
            # 计算成交量统计
            if volumes:
                import statistics
                result['summary']['volume_stats'] = {
                    'count': len(volumes),
                    'min': min(volumes),
                    'max': max(volumes),
                    'avg': statistics.mean(volumes),
                    'total': sum(volumes)
                }
            
            return result
            
        except Exception as e:
            print(f"获取量价数据失败: {e}")
            return {
                'success': False,
                'error': f'获取股票{stock_code}量价数据时出错: {str(e)}',
                'data_source': 'error'
                }
    
    def _infer_market_from_stock_code(self, stock_code: str) -> str:
        """根据股票代码推断市场类型"""
        try:
            if not stock_code:
                return None
                
            stock_code = str(stock_code).strip()
            
            # 中国股票代码特征
            if stock_code.isdigit() and len(stock_code) == 6:
                if stock_code.startswith(('000', '001', '002', '003', '300', '301')):  # 深圳主板/中小板/创业板
                    return 'cn'
                elif stock_code.startswith(('600', '601', '603', '605', '688')):  # 上海主板/科创板
                    return 'cn'
            
            # 香港股票代码特征 (通常以00开头且长度<=5)
            if stock_code.isdigit() and len(stock_code) <= 5:
                if stock_code.startswith('00') or len(stock_code) <= 4:
                    return 'hk'
            
            # 美国股票代码特征 (字母代码)
            if stock_code.isalpha() or any(c.isalpha() for c in stock_code):
                return 'us'
            
            return None
            
        except Exception as e:
            print(f"股票代码市场推断失败: {e}")
            return None
    
    def _detect_market_from_data_content(self) -> str:
        """通过分析已加载的数据内容来检测市场"""
        try:
            if not hasattr(self, 'analysis_results') or not self.analysis_results:
                return None
                
            # 检查是否有股票数据
            stock_data = self.analysis_results.get('stocks', {})
            if not stock_data:
                return None
            
            # 取前几个股票代码进行分析
            sample_codes = list(stock_data.keys())[:5]
            cn_count = 0
            hk_count = 0
            us_count = 0
            
            for code in sample_codes:
                inferred = self._infer_market_from_stock_code(code)
                if inferred == 'cn':
                    cn_count += 1
                elif inferred == 'hk':
                    hk_count += 1
                elif inferred == 'us':
                    us_count += 1
            
            # 返回数量最多的市场类型
            if cn_count > hk_count and cn_count > us_count:
                return 'cn'
            elif hk_count > us_count:
                return 'hk'
            elif us_count > 0:
                return 'us'
                
            return None
            
        except Exception as e:
            print(f"数据内容市场检测失败: {e}")
            return None
    
    def _get_preferred_market_with_multiple_fallbacks(self, stock_code: str = None) -> str:
        """使用多种方案检测市场类型"""
        try:
            print(f" 开始多重市场检测，股票代码: {stock_code}")
            
            # 方案1: 股票代码推断（最直接可靠）
            if stock_code:
                market_from_code = self._infer_market_from_stock_code(stock_code)
                if market_from_code:
                    print(f" 方案1成功: 根据股票代码{stock_code}检测为{market_from_code.upper()}市场")
                    return market_from_code
            
            # 方案2: 分析数据内容
            market_from_content = self._detect_market_from_data_content()
            if market_from_content:
                print(f" 方案2成功: 根据数据内容检测为{market_from_content.upper()}市场")
                return market_from_content
            
            # 方案3: 原有的检测逻辑
            market_from_original = self._get_preferred_market_from_current_data()
            if market_from_original:
                print(f" 方案3成功: 原有方法检测为{market_from_original.upper()}市场")
                return market_from_original
            
            # 方案4: 主窗口全局搜索
            market_from_global = self._find_main_window_global_search()
            if market_from_global:
                print(f" 方案4成功: 全局搜索检测为{market_from_global.upper()}市场")
                return market_from_global
            
            # 方案5: 强制默认CN（中国股票代码特征最明显）
            print(f" 所有方案均失败，默认使用CN市场")
            return 'cn'
            
        except Exception as e:
            print(f"多重市场检测失败: {e}，默认使用CN市场")
            return 'cn'
    
    def _find_main_window_global_search(self) -> str:
        """全局搜索主窗口的市场设置"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'detected_market') and widget.detected_market:
                        return widget.detected_market
                    if hasattr(widget, 'current_data_file_path') and widget.current_data_file_path:
                        import os
                        file_name = os.path.basename(widget.current_data_file_path).lower()
                        if file_name.startswith('cn') or 'cn_data' in file_name:
                            return 'cn'
                        elif file_name.startswith('hk') or 'hk_data' in file_name:
                            return 'hk'
                        elif file_name.startswith('us') or 'us_data' in file_name:
                            return 'us'
            return None
        except Exception as e:
            print(f"全局搜索失败: {e}")
            return None
    
    def _get_current_market_type(self) -> str:
        """检测当前数据的市场类型"""
        try:
            current_file = self._get_current_rating_file()
            if current_file:
                filename = os.path.basename(current_file).lower()
                if 'us_' in filename or 'us.' in filename:
                    return 'us'
                elif 'hk_' in filename or 'hk.' in filename:
                    return 'hk'
                elif 'cn_' in filename or 'cn.' in filename:
                    return 'cn'
            
            # 如果无法从文件名判断，尝试从数据内容判断
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                # 检查前几个股票代码的格式
                for industry_name, industry_info in list(self.analysis_results_obj.items())[:3]:
                    if isinstance(industry_info, dict) and 'stocks' in industry_info:
                        stocks = industry_info['stocks']
                        if isinstance(stocks, list) and len(stocks) > 0:
                            for stock in stocks[:3]:
                                code = stock.get('code', '').strip().upper()
                                if code:
                                    # 美股：字母代码（如AAPL, MSFT）
                                    if code.isalpha() and len(code) <= 5:
                                        return 'us'
                                    # 港股：5位数字或字母数字组合
                                    elif (code.isdigit() and len(code) == 5) or (len(code) <= 5 and any(c.isalpha() for c in code)):
                                        return 'hk'
                                    # 中国股：6位数字
                                    elif code.isdigit() and len(code) == 6:
                                        return 'cn'
            
            return 'cn'  # 默认中国市场
        except Exception as e:
            print(f"[ERROR] 检测市场类型失败: {e}")
            return 'cn'
    
    def _get_amount_from_main_data(self, stock_code: str) -> float:
        """从主数据文件获取股票的成交金额"""
        try:
            # 首先尝试从analysis_results_obj获取
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                # 使用industries属性而不是items()方法
                if hasattr(self.analysis_results_obj, 'industries'):
                    for industry_name, industry_info in self.analysis_results_obj.industries.items():
                        if isinstance(industry_info, dict) and 'stocks' in industry_info:
                            stocks = industry_info['stocks']
                            if isinstance(stocks, dict):
                                # stocks是字典格式
                                for code, stock_data in stocks.items():
                                    if str(code).strip().upper() == str(stock_code).strip().upper():
                                        amount = stock_data.get('amount', 0)
                                        if amount and amount > 0:
                                            return float(amount)
                            elif isinstance(stocks, list):
                                # stocks是列表格式
                                for stock in stocks:
                                    if isinstance(stock, dict):
                                        code = stock.get('code', '').strip().upper()
                                        if code == str(stock_code).strip().upper():
                                            amount = stock.get('amount', 0)
                                            if amount and amount > 0:
                                                return float(amount)
            
            # 如果analysis_results_obj中没找到，尝试直接从文件加载
            current_file = self._get_current_rating_file()
            if current_file and os.path.exists(current_file):
                import json
                import gzip
                
                # 读取数据文件
                if current_file.endswith('.gz'):
                    with gzip.open(current_file, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    with open(current_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                # 搜索股票数据
                for industry_name, industry_info in data.items():
                    if isinstance(industry_info, dict) and 'stocks' in industry_info:
                        stocks = industry_info['stocks']
                        if isinstance(stocks, dict):
                            # stocks是字典格式
                            for code, stock_data in stocks.items():
                                if str(code).strip().upper() == str(stock_code).strip().upper():
                                    amount = stock_data.get('amount', 0)
                                    if amount and amount > 0:
                                        return float(amount)
                        elif isinstance(stocks, list):
                            # stocks是列表格式
                            for stock in stocks:
                                if isinstance(stock, dict):
                                    code = stock.get('code', '').strip().upper()
                                    if code == str(stock_code).strip().upper():
                                        amount = stock.get('amount', 0)
                                        if amount and amount > 0:
                                            return float(amount)
            
            return 0.0
            
        except Exception as e:
            print(f"  [ERROR] 从主数据文件获取成交金额失败 {stock_code}: {e}")
            return 0.0
    
    def _get_current_rating_file(self) -> str:
        """获取当前加载的评级数据文件路径"""
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'current_data_file_path') and widget.current_data_file_path:
                        current_file = widget.current_data_file_path
                        print(f" 当前数据文件: {current_file}")
                        
                        # 检查文件是否存在
                        if os.path.exists(current_file):
                            print(f" 指定评级数据文件: {current_file}")
                            return current_file
                        else:
                            print(f"[ERROR] 文件不存在: {current_file}")
            
            print(" 未找到当前数据文件，将搜索所有评级文件")
            return None
        except Exception as e:
            print(f"获取当前评级文件失败: {e}")
            return None
    
    def _get_reliable_market_info(self) -> str:
        """获取可靠的市场信息 - 优先从主界面检测结果获取"""
        try:
            # 方法1：优先使用主界面检测到的市场类型
            if hasattr(self.parent(), 'detected_market') and self.parent().detected_market:
                detected_market = self.parent().detected_market
                print(f"[市场检测] 使用主界面检测的市场类型: {detected_market.upper()}")
                return detected_market
            
            # 方法2：从全局应用中查找主窗口的检测结果
            try:
                from PyQt5.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, 'detected_market') and widget.detected_market:
                            print(f"[市场检测] 从主窗口获取市场类型: {widget.detected_market.upper()}")
                            return widget.detected_market
                        if hasattr(widget, 'current_data_file_path') and widget.current_data_file_path:
                            import os
                            file_name = os.path.basename(widget.current_data_file_path).lower()
                            if file_name.startswith('cn') or 'cn_data' in file_name:
                                print(f"[市场检测] 从文件路径推断: CN市场 ({file_name})")
                                return 'cn'
                            elif file_name.startswith('hk') or 'hk_data' in file_name:
                                print(f"[市场检测] 从文件路径推断: HK市场 ({file_name})")
                                return 'hk'
                            elif file_name.startswith('us') or 'us_data' in file_name:
                                print(f"[市场检测] 从文件路径推断: US市场 ({file_name})")
                                return 'us'
            except Exception as e:
                print(f"[市场检测] 全局搜索失败: {e}")
            
            # 方法3：回退到原有逻辑
            return self._get_preferred_market_from_current_data()
            
        except Exception as e:
            print(f"[市场检测] 获取可靠市场信息失败: {e}，默认使用CN市场")
            return 'cn'
    
    def _get_preferred_market_from_current_data(self) -> str:
        """根据当前加载的数据文件推断优先市场"""
        try:
            # 优先使用主界面检测到的市场类型（新增）
            if hasattr(self.parent(), 'detected_market') and self.parent().detected_market:
                detected_market = self.parent().detected_market
                print(f"使用主界面检测的市场类型: {detected_market.upper()}")
                return detected_market
            
            # 检查是否有分析结果，从中获取数据源信息
            if hasattr(self, 'analysis_results') and self.analysis_results:
                if 'data_source' in self.analysis_results:
                    data_source = self.analysis_results['data_source']
                    # 修复：检查 file_path 而不是 data_file
                    if hasattr(data_source, 'file_path'):
                        data_file = data_source.file_path.lower()
                        if 'hk' in data_file:
                            return 'hk'
                        elif 'us' in data_file:
                            return 'us'
                        elif 'cn' in data_file:
                            return 'cn'
                    elif hasattr(data_source, 'data_file'):  # 保持向后兼容
                        data_file = data_source.data_file.lower()
                        if 'hk' in data_file:
                            return 'hk'
                        elif 'us' in data_file:
                            return 'us'
                        elif 'cn' in data_file:
                            return 'cn'
            
            # 检查当前文件名属性
            if hasattr(self, 'current_file_name') and self.current_file_name:
                file_name = self.current_file_name.lower()
                if 'hk' in file_name:
                    return 'hk'
                elif 'us' in file_name:
                    return 'us'
                elif 'cn' in file_name:
                    return 'cn'
            
            # 检查分析结果对象的数据文件路径
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                if hasattr(self.analysis_results_obj, 'dataset') and self.analysis_results_obj.dataset:
                    dataset = self.analysis_results_obj.dataset
                    # 修复：使用 file_path 而不是 data_file
                    if hasattr(dataset, 'file_path'):
                        data_file = str(dataset.file_path).lower()
                        if 'hk' in data_file:
                            return 'hk'
                        elif 'us' in data_file:
                            return 'us'
                        elif 'cn' in data_file:
                            return 'cn'
            
            # 默认返回cn市场（而不是None）
            print("无法确定具体市场，默认使用CN市场")
            return 'cn'
            
        except Exception as e:
            print(f"推断优先市场失败: {e}，默认使用CN市场")
            return 'cn'
    
    def get_recent_rating_trend(self, stock_code):
        """获取最近30天评级趋势 - 只使用真实数据"""
        # 从真实数据中获取评级趋势
        real_data = self.get_real_historical_data(stock_code)
        if not real_data:
            return []
        
        # 提取最近30天的评级
        recent_data = real_data[-30:] if len(real_data) > 30 else real_data
        ratings = [item[1] if len(item) > 1 else '-' for item in recent_data]
        
        return ratings
    
    def generate_ai_analysis_prompt(self, data):
        """生成AI分析提示词 - 优化版（减少40% token消耗）"""
        
        # 检测当前界面语言
        from config.i18n import is_english
        use_english = is_english()
        
        # 获取当前市场类型 - 优先从主界面检测结果获取
        current_market = self._get_reliable_market_info()
        market_names_short = {'cn': 'A股', 'hk': '港股', 'us': '美股'}
        market_name = market_names_short.get(current_market, '股市')
        
        # 调试信息：确保市场名称正确传递给LLM
        print(f"[市场检测] 个股分析AI - 检测到市场: {current_market}, 市场名称: {market_name}")
        
        # 构建量价数据
        volume_price_info = ""
        
        # 添加量价数据部分
        if data.get('has_real_volume_price_data', False) and data.get('volume_price_data'):
            try:
                from utils.volume_price_fetcher import VolumePriceFetcher
                fetcher = VolumePriceFetcher(verbose=False)
                volume_price_info = fetcher.format_volume_price_data_for_ai(data['volume_price_data'])
            except Exception as e:
                volume_price_info = f"量价数据格式化失败: {str(e)}"
        else:
            volume_price_info = f"量价数据不可用"
        
        # 根据语言生成不同的提示词（精简版）
        if use_english:
            prompt = f"""Develop trading strategy for {data['stock_code']} {data['stock_name']} ({market_name}):

## Core Data
- Stock: {data['stock_code']} {data['stock_name']} ({data['industry']})
- RTSI Rating: {data['rtsi']:.2f}/90
- Industry TMA: {data['industry_tma']:.2f}
- Market MSCI: {data['market_msci']:.2f}
- Market Sentiment: {data['market_sentiment']}
- Rating Trend: {' → '.join(data['recent_ratings'][-5:])}

## Volume-Price Data
{volume_price_info}

## Analysis Requirements
Provide:
1. **Action Recommendations**: Buy/Hold/Reduce/Sell percentages (0-100%, specific values)
2. **Entry Timing**: Specific buy conditions and position-adding strategy
3. **Profit/Loss Targets**: Target price range and stop-loss price
4. **Risk Assessment**: Upside probability, expected return, downside risk, holding period (weeks)
5. **Volume-Price Analysis**: Price-volume coordination, volume trend, key support levels, divergence signals

Note: Provide specific values and prices, avoid theoretical explanations. For China A-share market analysis, use Shanghai Composite Index (上证指数) as the market benchmark.

**IMPORTANT: Please respond in Chinese only.**
"""
        else:
            prompt = f"""为{data['stock_code']} {data['stock_name']}制定操作策略（{market_name}）：

## 核心数据
- 股票：{data['stock_code']} {data['stock_name']} ({data['industry']})
- RTSI评级：{data['rtsi']:.2f}/90
- 行业TMA：{data['industry_tma']:.2f}
- 市场MSCI：{data['market_msci']:.2f}
- 市场情绪：{data['market_sentiment']}
- 评级趋势：{' → '.join(data['recent_ratings'][-5:])}

## 量价数据
{volume_price_info}

## 分析要求
请提供：
1. **操作建议**：买入/持有/减仓/卖出的百分比建议（0-100%，具体数值）
2. **入场时机**：具体买入条件和加仓策略
3. **止盈止损**：目标价位区间和止损价位
4. **风险评估**：上涨概率、预期涨幅、下跌风险、持有周期（周）
5. **量价分析**：价量配合、成交量趋势、关键支撑位、背离信号

注意：给出具体数值和价位，避免理论解释。分析A股市场时，请以上证指数为基准。
"""
        
        return prompt
    
    def on_ai_analysis_finished(self, result):
        """AI分析完成回调"""
        try:
            # 生成HTML格式的结果
            html_result = self.format_ai_analysis_result(result)
            
            # 显示结果
            self.set_stock_ai_html(html_result)
            
            # 缓存结果
            from datetime import datetime
            self.stock_ai_cache[self.current_ai_stock] = {
                'html': html_result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'raw_result': result
            }
            
            # 切换到结果页面（第2页）
            if hasattr(self, 'ai_stacked_widget'):
                self.ai_stacked_widget.setCurrentIndex(1)
            
        except Exception as e:
            self.on_ai_analysis_error(f"结果处理失败: {str(e)}")
        finally:
            # 重置状态
            self.ai_analysis_in_progress = False
            self.current_ai_stock = None
            self.stock_ai_analyze_btn.setEnabled(True)
            self.stock_ai_analyze_btn.setText(t_gui("开始AI分析"))
            self.ai_status_label.setText("")
    
    def on_ai_analysis_error(self, error_message):
        """AI分析错误回调"""
        error_html = f"""
        <div style="text-align: center; color: #dc3545; margin-top: 50px;">
            <h3>[ERROR] AI分析失败</h3>
            <p>{error_message}</p>
            <p style="font-size: 12px; color: #666;">请检查网络连接和AI配置，然后重试</p>
        </div>
        """
        
        self.set_stock_ai_html(error_html)
        
        # 切换到结果页面显示错误
        if hasattr(self, 'ai_stacked_widget'):
            self.ai_stacked_widget.setCurrentIndex(1)
        
        # 重置状态
        self.ai_analysis_in_progress = False
        self.current_ai_stock = None
        self.stock_ai_analyze_btn.setEnabled(True)
        self.stock_ai_analyze_btn.setText(t_gui("开始AI分析"))
        self.ai_status_label.setText("")
    
    def start_mini_master_analysis(self):
        """开始迷你投资大师分析"""
        if not self.analysis_results_obj:
            QMessageBox.warning(self, t_gui('warning'), "请先加载股票数据并选择要分析的股票")
            return
        
        if not hasattr(self, 'current_stock_code') or not self.current_stock_code:
            QMessageBox.warning(self, t_gui('warning'), "请先选择要分析的股票")
            return
        
        # 防止重复分析
        if hasattr(self, 'mini_master_analysis_in_progress') and self.mini_master_analysis_in_progress:
            QMessageBox.information(self, t_gui('info'), "迷你投资大师分析正在进行中，请稍候...")
            return
        
        # 检查缓存，如果有缓存直接显示结果页
        if hasattr(self, 'mini_master_cache') and self.current_stock_code in self.mini_master_cache:
            self.show_cached_mini_master_result(self.current_stock_code)
            return
        
        # 开始分析
        self.perform_mini_master_analysis(self.current_stock_code)
    
    def show_cached_mini_master_result(self, stock_code):
        """显示缓存的迷你投资大师分析结果并切换到结果页"""
        if not hasattr(self, 'mini_master_cache'):
            self.mini_master_cache = {}
            return
        
        cached_result = self.mini_master_cache[stock_code]
        
        # 根据浏览器类型设置内容
        if hasattr(self.mini_master_result_browser, 'setHtml'):
            self.mini_master_result_browser.setHtml(cached_result['html'])
        elif hasattr(self.mini_master_result_browser, 'load'):
            # QWebEngineView
            from PyQt5.QtCore import QUrl
            import tempfile
            import os
            
            # 创建临时HTML文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(cached_result['html'])
            temp_file.close()
            
            # 加载临时文件
            file_url = QUrl.fromLocalFile(os.path.abspath(temp_file.name))
            self.mini_master_result_browser.load(file_url)
        
        # 切换到结果页面（第2页）
        if hasattr(self, 'mini_master_stacked_widget'):
            self.mini_master_stacked_widget.setCurrentIndex(1)
    
    def perform_mini_master_analysis(self, stock_code):
        """执行迷你投资大师分析"""
        try:
            # 设置分析状态
            self.mini_master_analysis_in_progress = True
            self.current_mini_master_stock = stock_code
            self.mini_master_analyze_btn.setEnabled(False)
            self.mini_master_analyze_btn.setText(t_gui("分析中"))
            self.mini_master_status_label.setText(t_gui("🔄_投资大师正在分析_请稍候"))
            
            # 使用单线程直接调用，避免PyQt5多线程崩溃
            QTimer.singleShot(100, lambda: self._perform_mini_master_analysis_sync(stock_code))
            
        except Exception as e:
            self.on_mini_master_analysis_error(str(e))
    
    def _perform_mini_master_analysis_sync(self, stock_code):
        """同步执行迷你投资大师分析"""
        try:
            # 使用mini.py中的MiniInvestmentMasterGUI进行分析
            from mini import MiniInvestmentMasterGUI
            
            # 创建迷你投资大师实例
            mini_master = MiniInvestmentMasterGUI()
            
            # 执行分析并获取HTML报告
            result = mini_master.analyze_stock_for_gui(stock_code)
            
            if result['status'] == 'success':
                self.on_mini_master_analysis_finished(result['html_report'])
            else:
                self.on_mini_master_analysis_error(result['error'])
                
        except Exception as e:
            self.on_mini_master_analysis_error(str(e))
    
    def on_mini_master_analysis_finished(self, html_result):
        """迷你投资大师分析完成回调"""
        try:
            # 显示结果
            if hasattr(self.mini_master_result_browser, 'setHtml'):
                self.mini_master_result_browser.setHtml(html_result)
            elif hasattr(self.mini_master_result_browser, 'load'):
                # QWebEngineView
                from PyQt5.QtCore import QUrl
                import tempfile
                import os
                
                # 创建临时HTML文件
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
                temp_file.write(html_result)
                temp_file.close()
                
                # 加载临时文件
                file_url = QUrl.fromLocalFile(os.path.abspath(temp_file.name))
                self.mini_master_result_browser.load(file_url)
            
            # 缓存结果
            from datetime import datetime
            self.mini_master_cache[self.current_mini_master_stock] = {
                'html': html_result,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 切换到结果页面（第2页）
            if hasattr(self, 'mini_master_stacked_widget'):
                self.mini_master_stacked_widget.setCurrentIndex(1)
            
        except Exception as e:
            self.on_mini_master_analysis_error(f"结果处理失败: {str(e)}")
        finally:
            # 重置状态
            self.mini_master_analysis_in_progress = False
            self.current_mini_master_stock = None
            self.mini_master_analyze_btn.setEnabled(True)
            self.mini_master_analyze_btn.setText(t_gui("开始分析"))
            self.mini_master_status_label.setText("")
    
    def on_mini_master_analysis_error(self, error_message):
        """迷你投资大师分析错误回调"""
        error_html = f"""
        <div style="text-align: center; color: #dc3545; margin-top: 50px;">
            <h3>[ERROR] 迷你投资大师分析失败</h3>
            <p>{error_message}</p>
            <p style="font-size: 12px; color: #666;">请检查股票代码和数据源，然后重试</p>
        </div>
        """
        
        # 显示错误信息
        if hasattr(self.mini_master_result_browser, 'setHtml'):
            self.mini_master_result_browser.setHtml(error_html)
        elif hasattr(self.mini_master_result_browser, 'load'):
            # QWebEngineView
            from PyQt5.QtCore import QUrl
            import tempfile
            import os
            
            # 创建临时HTML文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            temp_file.write(error_html)
            temp_file.close()
            
            # 加载临时文件
            file_url = QUrl.fromLocalFile(os.path.abspath(temp_file.name))
            self.mini_master_result_browser.load(file_url)
        
        # 切换到结果页面显示错误
        if hasattr(self, 'mini_master_stacked_widget'):
            self.mini_master_stacked_widget.setCurrentIndex(1)
        
        # 重置状态
        self.mini_master_analysis_in_progress = False
        self.current_mini_master_stock = None
        self.mini_master_analyze_btn.setEnabled(True)
        self.mini_master_analyze_btn.setText(t_gui("开始分析"))
        self.mini_master_status_label.setText("")
    
    def format_ai_analysis_result(self, result):
        """格式化AI分析结果为HTML - 采用迷你投资大师样式"""
        try:
            from datetime import datetime
            
            # 获取当前股票信息
            stock_info = f"{self.current_stock_code}"
            if hasattr(self, 'current_stock_info') and self.current_stock_info:
                stock_name = self.current_stock_info.get('name', '')
                if stock_name:
                    stock_info = f"{self.current_stock_code} ({stock_name})"
            
            # 获取数据源标志
            data_source_badge = ""
            if hasattr(self, 'current_analysis_data') and self.current_analysis_data:
                if self.current_analysis_data.get('has_real_volume_price_data', False):
                    data_source_info = self.current_analysis_data.get('data_source_info', '采用真实量价数据')
                    data_source_badge = f"""
                    <div class="section">
                        <div style="background: #e8f5e8; border: 1px solid #28a745; color: #155724; padding: 15px; border-radius: 8px; text-align: center;">
                        <strong> {data_source_info}</strong>
                        </div>
                    </div>
                    """
                else:
                    error_info = self.current_analysis_data.get('data_source_info', '量价数据不可用')
                    data_source_badge = f"""
                    <div class="section">
                        <div style="background: #ffeaea; border: 1px solid #e74c3c; color: #721c24; padding: 15px; border-radius: 8px; text-align: center;">
                        <strong> 量价数据获取失败：{error_info}</strong>
                        </div>
                    </div>
                    """
            
            # 使用迷你投资大师的CSS样式
            html = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AI股票分析报告 - {stock_info}</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif, 'Segoe UI', Tahoma, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    
                    .container {{
                        max-width: 1000px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 15px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }}
                    
                    .header {{
                        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }}
                    
                    .header h1 {{
                        font-size: 2.2em;
                        margin-bottom: 10px;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                    }}
                    
                    .header .subtitle {{
                        font-size: 1.1em;
                        opacity: 0.9;
                        margin-bottom: 5px;
                    }}
                    
                    .section {{
                        padding: 25px;
                        border-bottom: 1px solid #eee;
                    }}
                    
                    .section:last-child {{
                        border-bottom: none;
                    }}
                    
                    .section h2 {{
                        color: #2c3e50;
                        margin-bottom: 20px;
                        font-size: 1.5em;
                        border-left: 4px solid #3498db;
                        padding-left: 15px;
                    }}
                    
                    .analysis-content {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 15px 0;
                        border-left: 4px solid #3498db;
                    }}
                    
                    .price-up {{
                        color: #dc3545 !important;
                        font-weight: bold;
                    }}
                    
                    .price-down {{
                        color: #28a745 !important;
                        font-weight: bold;
                    }}
                    
                    .price-neutral {{
                        color: #6c757d !important;
                        font-weight: bold;
                    }}
                    
                    .warning {{
                        background: linear-gradient(135deg, #fff8e1 0%, #fffbf0 100%);
                        border: 2px solid #f39c12;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                    }}
                    
                    .warning h3 {{
                        margin-bottom: 10px;
                        font-size: 1.3em;
                        color: #e67e22;
                    }}
                    
                    .footer {{
                        background: #2c3e50;
                        color: white;
                        text-align: center;
                        padding: 20px;
                        font-size: 0.9em;
                    }}
                    
                    .timestamp {{
                        font-size: 0.9em;
                        opacity: 0.8;
                    }}
                    
                    @media (max-width: 768px) {{
                        .container {{
                            margin: 10px;
                            border-radius: 10px;
                        }}
                        
                        .header {{
                            padding: 20px;
                        }}
                        
                        .header h1 {{
                            font-size: 1.8em;
                        }}
                        
                        .section {{
                            padding: 15px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                <div class="header">
                    <h1> AI股票分析报告</h1>
                        <div class="subtitle">{stock_info} - 智能投资建议</div>
                        <div class="timestamp">Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                        <div class="timestamp" style="font-size: 14px; margin-top: 8px; opacity: 0.8;">作者：267278466@qq.com</div>
                </div>
                
                {data_source_badge}
                
                    <div class="section">
                        <h2> AI智能分析</h2>
                <div class="analysis-content">
                    {self._format_analysis_text(result)}
                        </div>
                </div>
                
                <div class="warning">
                        <h3> 风险提示</h3>
                        <p>本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。请结合自身情况和市场变化做出投资决策。</p>
                    </div>
                    
                    <div class="footer">
                        AI股票大师 © 2025 - 专业的股票分析工具
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            return f"<p>格式化结果失败: {str(e)}</p><pre>{result}</pre>"
    
    def _format_analysis_text(self, text):
        """格式化分析文本 - 符合红涨绿跌规范"""
        try:
            # 简单的文本格式化
            formatted = text.replace('\n\n', '</p><p>')
            formatted = formatted.replace('\n', '<br/>')
            formatted = f"<p>{formatted}</p>"
            
            # 突出显示关键词 - 符合红涨绿跌规范
            # 买入相关 - 红色（机会）
            buy_keywords = ['买入', '建议买入', '强烈买入', '增持', '建仓', '机会']
            for keyword in buy_keywords:
                formatted = formatted.replace(keyword, f"<span class='price-up'>{keyword}</span>")
            
            # 卖出相关 - 绿色（风险）
            sell_keywords = ['卖出', '建议卖出', '减仓', '清仓', '风险', '下跌', '看空']
            for keyword in sell_keywords:
                formatted = formatted.replace(keyword, f"<span class='price-down'>{keyword}</span>")
            
            # 中性关键词 - 灰色
            neutral_keywords = ['持有', '观望', '等待', '谨慎']
            for keyword in neutral_keywords:
                formatted = formatted.replace(keyword, f"<span class='price-neutral'>{keyword}</span>")
            
            # 涨跌相关词汇
            formatted = formatted.replace('上涨', "<span class='price-up'>上涨</span>")
            formatted = formatted.replace('涨幅', "<span class='price-up'>涨幅</span>")
            formatted = formatted.replace('看涨', "<span class='price-up'>看涨</span>")
            formatted = formatted.replace('看跌', "<span class='price-down'>看跌</span>")
            formatted = formatted.replace('跌幅', "<span class='price-down'>跌幅</span>")
            
            return formatted
            
        except Exception:
            return f"<pre>{text}</pre>"
    
    def update_technical_ai_tab(self, stock_code, stock_name):
        """更新技术AI分析Tab状态"""
        if not hasattr(self, 'technical_ai_stacked_widget'):
            return
            
        # 检查是否有技术分析缓存
        if hasattr(self, 'technical_ai_cache') and stock_code in self.technical_ai_cache:
            # 有缓存，显示结果页
            cached_data = self.technical_ai_cache[stock_code]
            if hasattr(self, 'technical_ai_result_browser'):
                self.technical_ai_result_browser.setHtml(cached_data['html'])
            elif hasattr(self, 'technical_ai_result_text'):
                self.technical_ai_result_text.setHtml(cached_data['html'])
            self.technical_ai_stacked_widget.setCurrentIndex(1)
        else:
            # 无缓存，重置到分析按钮页
            self.technical_ai_stacked_widget.setCurrentIndex(0)
            if hasattr(self, 'technical_ai_analyze_btn'):
                self.technical_ai_analyze_btn.setText(" 开始技术面AI分析")
                self.technical_ai_analyze_btn.setEnabled(True)
            if hasattr(self, 'technical_ai_status_label'):
                self.technical_ai_status_label.setText("")
    
    def update_master_ai_tab(self, stock_code, stock_name):
        """更新投资大师AI分析Tab状态"""
        if not hasattr(self, 'master_ai_stacked_widget'):
            return
            
        # 检查是否有投资大师分析缓存
        if hasattr(self, 'master_ai_cache') and stock_code in self.master_ai_cache:
            # 有缓存，显示结果页
            cached_data = self.master_ai_cache[stock_code]
            if hasattr(self, 'master_ai_result_browser'):
                self.master_ai_result_browser.setHtml(cached_data['html'])
            elif hasattr(self, 'master_ai_result_text'):
                self.master_ai_result_text.setHtml(cached_data['html'])
            self.master_ai_stacked_widget.setCurrentIndex(1)
        else:
            # 无缓存，重置到分析按钮页
            self.master_ai_stacked_widget.setCurrentIndex(0)
            if hasattr(self, 'master_ai_analyze_btn'):
                self.master_ai_analyze_btn.setText(" 开始投资大师AI分析")
                self.master_ai_analyze_btn.setEnabled(True)
            if hasattr(self, 'master_ai_status_label'):
                self.master_ai_status_label.setText("")
    
    def update_mini_master_tab(self, stock_code, stock_name):
        """更新迷你投资大师Tab状态"""
        if not hasattr(self, 'mini_master_stacked_widget'):
            return
            
        # 检查当前是否在迷你投资大师Tab
        current_tab_index = self.stock_tab_widget.currentIndex()
        
        if hasattr(self, 'mini_master_cache') and stock_code in self.mini_master_cache:
            # 有缓存
            if current_tab_index == 2:  # 如果当前就在迷你投资大师Tab（索引为2）
                # 直接显示结果页
                self.show_cached_mini_master_result(stock_code)
            # 如果不在迷你投资大师Tab，等待用户切换到该Tab时自动显示
        else:
            # 无缓存，重置到分析按钮页
            self.mini_master_stacked_widget.setCurrentIndex(0)
            self.mini_master_analyze_btn.setText(t_gui("开始分析"))
            self.mini_master_analyze_btn.setEnabled(True)
            self.mini_master_status_label.setText("")
    
    def on_industry_tab_changed(self, index):
        """行业Tab切换事件处理 - 当切换到趋势图表、行业评级或AI分析Tab时处理"""
        try:
            # 检查是否切换到趋势图表Tab（第2个Tab，索引为1）
            if index == 1 and hasattr(self, 'current_industry_name') and self.current_industry_name:
                # 点击趋势图表tab时，先显示等待画面，然后延迟开始计算
                print(f" 用户点击趋势图表tab，显示等待画面: {self.current_industry_name}")
                
                # 立即切换到等待页面并启动动画
                if hasattr(self, 'industry_chart_stacked_widget'):
                    self.industry_chart_stacked_widget.setCurrentIndex(1)  # 显示等待页面
                    self.start_industry_loading_animation()  # 启动等待动画
                
                # 使用QTimer延迟启动计算，让用户看到等待效果
                from PyQt5.QtCore import QTimer
                if not hasattr(self, 'industry_chart_timer'):
                    self.industry_chart_timer = QTimer()
                    self.industry_chart_timer.setSingleShot(True)
                    self.industry_chart_timer.timeout.connect(self.start_industry_chart_calculation)
                
                # 保存当前行业名，供计算时使用
                self.pending_industry_name = self.current_industry_name
                
                # 延迟500毫秒开始计算，让用户看到等待动画
                self.industry_chart_timer.start(500)
                
            # 检查是否切换到AI分析Tab（第3个Tab，索引为2）
            elif index == 2 and hasattr(self, 'current_industry_name') and self.current_industry_name:
                # 如果有当前行业且有缓存，自动显示缓存结果
                cached_result = self.industry_ai_cache.get(self.current_industry_name)
                if cached_result:
                    # 切换到结果页面并显示缓存的结果（格式化为HTML）
                    self.industry_ai_stacked_widget.setCurrentIndex(1)
                    html_result = self.format_industry_ai_analysis_result(cached_result, self.current_industry_name)
                    self.set_industry_ai_html(html_result)
                else:
                    # 没有缓存，显示分析按钮页面
                    self.industry_ai_stacked_widget.setCurrentIndex(0)
                    # 更新按钮状态
                    if hasattr(self, 'industry_ai_analyze_btn'):
                        self.industry_ai_analyze_btn.setText(t_gui("开始AI分析"))
                        self.industry_ai_analyze_btn.setEnabled(True)
                    if hasattr(self, 'industry_ai_status_label'):
                        self.industry_ai_status_label.setText("")
        except Exception as e:
            print(f"行业Tab切换处理失败: {str(e)}")
    


    

    

    
    def _calculate_real_industry_ratings_threaded(self, worker):
        """计算真实的行业评级数据 - 基于最新一天的数据（工作线程版本）"""
        try:
            # 强制从文件加载数据，确保数据结构正确
            industries = None
            print("🔄 强制从文件加载行业数据以确保数据结构正确...")
            
            # 如果没有现有数据，尝试直接从文件加载
            if not industries:
                print("  没有现有分析结果，尝试直接从数据文件加载行业数据...")
                worker.progress_updated.emit(0, 1, "加载行业数据...")
                industries = self._load_industries_from_file()
                
            if not industries:
                print("[ERROR] 无法获取行业数据")
                return None
                
            # 根据配置选择计算模式
            if INDUSTRY_RATING_CONFIG['enable_multithreading']:
                print(f" 开始多线程计算 {len(industries)} 个行业的最新评级（最大{INDUSTRY_RATING_CONFIG['max_workers']}线程）")
                return self._calculate_with_parallel_workers(industries, worker)
            else:
                print(f" 开始单线程计算 {len(industries)} 个行业的最新评级")
                return self._calculate_with_single_thread(industries, worker)
            
        except Exception as e:
            print(f"[ERROR] 计算真实行业评级失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_with_parallel_workers(self, industries, main_worker):
        """使用多线程并行计算行业评级（优化版）"""
        try:
            import threading
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            print(f" 启动并行计算模式，处理 {len(industries)} 个行业")
            
            # 优化1: 根据配置决定是否预加载股票成交金额数据
            if INDUSTRY_RATING_CONFIG['enable_preloading']:
                main_worker.progress_updated.emit(0, 100, "预加载股票成交金额数据...")
                all_stock_codes = self._collect_all_stock_codes(industries)
                self._preload_stock_amounts(all_stock_codes, main_worker)
            else:
                print("  预加载已禁用，将使用运行时获取模式")
            
            # 评级等级定义（0-7分制，8个等级，7级最高，0级最低）
            # 注意：评级数值7=大多（最高），0=大空（最低）
            # 按大多在上面，大空在底下排列
            rating_levels = {
                "7级": {"min": 6.5, "max": 7.1, "color": "#dc3545"},    # 深红色 - 大多（最高）
                "6级": {"min": 5.5, "max": 6.5, "color": "#ffc107"},    # 橙黄色 - 中多（原5级色）
                "5级": {"min": 4.5, "max": 5.5, "color": "#ff6b6b"},    # 浅红色 - 小多（原4级色）
                "4级": {"min": 3.5, "max": 4.5, "color": "#fd7e14"},    # 橙红色 - 微多（原6级色）
                "3级": {"min": 2.5, "max": 3.5, "color": "#6f42c1"},    # 紫色 - 微空
                "2级": {"min": 1.5, "max": 2.5, "color": "#6c757d"},    # 灰色 - 小空
                "1级": {"min": 0.5, "max": 1.5, "color": "#28a745"},    # 绿色 - 中空
                "0级": {"min": 0.0, "max": 0.5, "color": "#198754"}     # 深绿色 - 大空（最低）
            }
            
            # 按评级等级分类行业
            classified_industries = {level: {"color": info["color"], "industries": []} 
                                   for level, info in rating_levels.items()}
            
            industry_list = list(industries.items())
            total_industries = len(industry_list)
            
            # 并行计算配置（使用全局配置）
            max_workers = min(INDUSTRY_RATING_CONFIG['max_workers'], len(industry_list))
            completed_count = 0
            lock = threading.Lock()
            
            def process_single_industry(industry_item):
                """处理单个行业的评级计算"""
                industry_name, industry_info = industry_item
                try:
                    rating = self._get_industry_latest_rating(industry_name, industry_info)
                    return industry_name, rating
                except Exception as e:
                    print(f"  [ERROR] 计算行业 {industry_name} 失败: {e}")
                    return industry_name, None
            
            # 使用线程池并行处理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                print(f"💼 使用 {max_workers} 个线程并行计算")
                
                # 提交所有任务
                future_to_industry = {
                    executor.submit(process_single_industry, industry_item): industry_item[0] 
                    for industry_item in industry_list
                }
                
                # 收集结果
                for future in as_completed(future_to_industry):
                    with lock:
                        completed_count += 1
                        # 优化2: 更准确的进度显示（20-90%用于行业计算）
                        progress = 20 + int((completed_count / total_industries) * 70)
                        main_worker.progress_updated.emit(progress, 100, f"计算行业评级 {completed_count}/{total_industries}")
                    
                    try:
                        industry_name, rating = future.result()
                        
                        if rating is None:
                            print(f"    行业 {industry_name} 无评级数据，跳过")
                            continue
                        
                        # 分类到相应等级
                        classified = False
                        for level_name, level_info in rating_levels.items():
                            if level_info["min"] <= rating < level_info["max"]:
                                classified_industries[level_name]["industries"].append(industry_name)
                                print(f"   行业 {industry_name}: 评级 {rating:.2f} -> {level_name}")
                                classified = True
                                break
                        
                        if not classified:
                            # 处理边界情况
                            if rating >= 6.5:
                                classified_industries["7级"]["industries"].append(industry_name)
                                print(f"   行业 {industry_name}: 评级 {rating:.2f} -> 7级 (>=6.5)")
                            elif rating < 0.5:
                                classified_industries["0级"]["industries"].append(industry_name)
                                print(f"   行业 {industry_name}: 评级 {rating:.2f} -> 0级 (<0.5)")
                            else:
                                classified_industries["4级"]["industries"].append(industry_name)
                                print(f"   行业 {industry_name}: 评级 {rating:.2f} -> 4级 (默认)")
                        
                    except Exception as e:
                        print(f"  [ERROR] 处理行业结果失败: {e}")
            
            print(f" 并行计算完成，共分类 {sum(len(level['industries']) for level in classified_industries.values())} 个行业")
            
            # 优化3: 显示资源清理阶段
            main_worker.progress_updated.emit(90, 100, "整理计算结果...")
            
            # 确保至少有一些数据
            total_classified = sum(len(level['industries']) for level in classified_industries.values())
            if not classified_industries or total_classified == 0:
                print("  没有行业被成功分类，返回默认分类")
                return {
                    "4级": {
                        "color": "#ff6b6b",
                        "industries": ["数据加载中..."]
                    }
                }
            
            # 优化4: 异步清理资源，不阻塞主界面
            main_worker.progress_updated.emit(95, 100, "准备输出结果...")
            self._schedule_async_cleanup()
            
            return classified_industries
            
        except Exception as e:
            print(f"[ERROR] 并行计算失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _calculate_with_single_thread(self, industries, main_worker):
        """使用单线程计算行业评级（配置选项）"""
        try:
            print(f"🔄 启动单线程计算模式，处理 {len(industries)} 个行业")
            
            # 根据配置决定是否预加载
            if INDUSTRY_RATING_CONFIG['enable_preloading']:
                main_worker.progress_updated.emit(0, 100, "预加载股票成交金额数据...")
                all_stock_codes = self._collect_all_stock_codes(industries)
                self._preload_stock_amounts(all_stock_codes, main_worker)
            else:
                print("  预加载已禁用，将使用运行时获取模式")
            
            # 评级等级定义
            rating_levels = {
                "7级": {"min": 6.5, "max": 7.1, "color": "#dc3545"},
                "6级": {"min": 5.5, "max": 6.5, "color": "#ffc107"},
                "5级": {"min": 4.5, "max": 5.5, "color": "#ff6b6b"},
                "4级": {"min": 3.5, "max": 4.5, "color": "#fd7e14"},
                "3级": {"min": 2.5, "max": 3.5, "color": "#6f42c1"},
                "2级": {"min": 1.5, "max": 2.5, "color": "#6c757d"},
                "1级": {"min": 0.5, "max": 1.5, "color": "#28a745"},
                "0级": {"min": 0.0, "max": 0.5, "color": "#198754"}
            }
            
            classified_industries = {level: {"color": info["color"], "industries": []} 
                                   for level, info in rating_levels.items()}
            
            industry_list = list(industries.items())
            total_industries = len(industry_list)
            
            # 单线程顺序处理
            for i, (industry_name, industry_info) in enumerate(industry_list):
                # 更新进度
                progress = 20 + int((i / total_industries) * 70)
                main_worker.progress_updated.emit(progress, 100, f"单线程计算 {i+1}/{total_industries}")
                
                try:
                    rating = self._get_industry_latest_rating(industry_name, industry_info)
                    
                    if rating is None:
                        print(f"    行业 {industry_name} 无评级数据，跳过")
                        continue
                    
                    # 分类到相应等级
                    classified = False
                    for level_name, level_info in rating_levels.items():
                        if level_info["min"] <= rating < level_info["max"]:
                            classified_industries[level_name]["industries"].append(industry_name)
                            print(f"   行业 {industry_name}: 评级 {rating:.2f} -> {level_name}")
                            classified = True
                            break
                    
                    if not classified:
                        # 处理边界情况
                        if rating >= 6.5:
                            classified_industries["7级"]["industries"].append(industry_name)
                        elif rating < 0.5:
                            classified_industries["0级"]["industries"].append(industry_name)
                        else:
                            classified_industries["4级"]["industries"].append(industry_name)
                    
                except Exception as e:
                    print(f"  [ERROR] 计算行业 {industry_name} 失败: {e}")
                    continue
            
            print(f" 单线程计算完成，共分类 {sum(len(level['industries']) for level in classified_industries.values())} 个行业")
            
            # 显示资源清理阶段
            main_worker.progress_updated.emit(90, 100, "整理计算结果...")
            
            # 确保至少有一些数据
            total_classified = sum(len(level['industries']) for level in classified_industries.values())
            if not classified_industries or total_classified == 0:
                print("  没有行业被成功分类，返回默认分类")
                return {
                    "4级": {
                        "color": "#ff6b6b",
                        "industries": ["数据加载中..."]
                    }
                }
            
            # 异步清理资源
            main_worker.progress_updated.emit(95, 100, "准备输出结果...")
            self._schedule_async_cleanup()
            
            return classified_industries
            
        except Exception as e:
            print(f"[ERROR] 单线程计算失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _collect_all_stock_codes(self, industries):
        """收集所有行业中的股票代码"""
        all_stock_codes = set()
        for industry_name, industry_info in industries.items():
            try:
                if isinstance(industry_info, dict) and 'stocks' in industry_info:
                    stocks = industry_info['stocks']
                    if isinstance(stocks, list):
                        for stock in stocks:
                            if isinstance(stock, dict) and 'code' in stock:
                                all_stock_codes.add(stock['code'])
                            elif isinstance(stock, str):
                                all_stock_codes.add(stock)
                    elif isinstance(stocks, dict):
                        all_stock_codes.update(stocks.keys())
            except Exception as e:
                print(f"      [ERROR] 收集行业 {industry_name} 股票代码失败: {e}")
                continue
        
        print(f" 总共收集到 {len(all_stock_codes)} 只股票代码")
        return list(all_stock_codes)
    
    def _preload_stock_amounts(self, stock_codes, main_worker):
        """预加载所有股票的成交金额数据（优化版）"""
        try:
            # 初始化缓存
            if not hasattr(self, '_stock_amount_cache'):
                self._stock_amount_cache = {}
            
            # 初始化LJDataReader（只初始化一次）
            if not hasattr(self, '_lj_reader'):
                from utils.lj_data_reader import LJDataReader
                self._lj_reader = LJDataReader(verbose=False)
                print(f"🔧 初始化LJDataReader成功")
            
            current_market = self._get_current_market_type()
            print(f"🌍 当前市场: {current_market}")
            
            # 检查数据文件可用性
            market_data_files = {
                'cn': 'cn-lj.dat.gz',
                'hk': 'hk-lj.dat.gz', 
                'us': 'us-lj.dat.gz'
            }
            
            target_file = market_data_files.get(current_market)
            if not target_file or not os.path.exists(target_file):
                print(f"  市场数据文件不存在: {target_file}")
                print(f"  将跳过预加载，使用运行时获取模式")
                # 设置空缓存，让运行时方法处理
                for stock_code in stock_codes:
                    self._stock_amount_cache[stock_code] = None
                return
            
            # 批量加载成交金额数据（使用全局配置）
            total_stocks = len(stock_codes)
            batch_size = INDUSTRY_RATING_CONFIG['preload_batch_size']
            total_success = 0
            total_failed = 0
            
            print(f" 开始预加载 {total_stocks} 只股票的成交金额数据...")
            
            for i in range(0, total_stocks, batch_size):
                batch_codes = stock_codes[i:i + batch_size]
                batch_end = min(i + batch_size, total_stocks)
                
                # 更新进度
                progress = int((i / total_stocks) * 20)  # 预加载占总进度的20%
                main_worker.progress_updated.emit(progress, 100, f"预加载数据 {batch_end}/{total_stocks}")
                
                # 记录批处理前的缓存大小
                before_count = len([v for v in self._stock_amount_cache.values() if v is not None and v > 0])
                
                # 批量获取数据
                self._batch_load_stock_amounts(batch_codes, current_market)
                
                # 统计本批次成功数量
                after_count = len([v for v in self._stock_amount_cache.values() if v is not None and v > 0])
                batch_success = after_count - before_count
                batch_failed = len(batch_codes) - batch_success
                
                total_success += batch_success
                total_failed += batch_failed
            
            # 最终统计
            overall_coverage = (total_success / total_stocks * 100) if total_stocks > 0 else 0
            print(f" 预加载完成: 成功{total_success}只, 失败{total_failed}只, 总覆盖率{overall_coverage:.1f}%")
            
            # 根据配置的阈值发出警告
            if overall_coverage < INDUSTRY_RATING_CONFIG['coverage_warning_threshold']:
                print(f"  数据覆盖率较低({overall_coverage:.1f}%), 可能影响计算准确性")
            
        except Exception as e:
            print(f"[ERROR] 预加载股票成交金额失败: {e}")
            # 即使预加载失败，也要确保缓存存在
            if not hasattr(self, '_stock_amount_cache'):
                self._stock_amount_cache = {}
            import traceback
            traceback.print_exc()
    
    def _batch_load_stock_amounts(self, stock_codes, market):
        """批量加载一批股票的成交金额（优化版）"""
        market_data_files = {
            'cn': 'cn-lj.dat.gz',
            'hk': 'hk-lj.dat.gz', 
            'us': 'us-lj.dat.gz'
        }
        
        target_file = market_data_files.get(market)
        if not target_file or not os.path.exists(target_file):
            print(f"      [ERROR] 市场数据文件不存在: {target_file}")
            # 为所有股票设置默认值
            for stock_code in stock_codes:
                self._stock_amount_cache[stock_code] = 0.0
            return
        
        try:
            success_count = 0
            failed_count = 0
            
            # 根据配置设置LJDataReader的日志输出
            original_verbose = getattr(self._lj_reader, 'verbose', True)
            if hasattr(self._lj_reader, 'verbose'):
                self._lj_reader.verbose = INDUSTRY_RATING_CONFIG['enable_verbose_logging']
            
            for stock_code in stock_codes:
                try:
                    volume_data = self._lj_reader.get_volume_price_data(stock_code, days=1, market=market)
                    if volume_data and 'data' in volume_data and volume_data['data']:
                        latest_data = volume_data['data'][-1]
                        raw_amount = latest_data.get('amount', 0)
                        amount = raw_amount * 10  # 修正单位
                        
                        if amount <= 0:
                            # 计算成交金额
                            volume = latest_data.get('volume', 0)
                            close_price = latest_data.get('close_price', latest_data.get('收盘价', 0))
                            if volume > 0 and close_price > 0:
                                amount = volume * close_price
                        
                        # 缓存结果
                        self._stock_amount_cache[stock_code] = float(amount) if amount > 0 else 0.0
                        if amount > 0:
                            success_count += 1
                        else:
                            failed_count += 1
                    else:
                        self._stock_amount_cache[stock_code] = 0.0
                        failed_count += 1
                        
                except Exception:
                    # 单个股票获取失败不影响其他股票，静默处理
                    self._stock_amount_cache[stock_code] = 0.0
                    failed_count += 1
                    continue
            
            # 恢复原有的日志设置
            if hasattr(self._lj_reader, 'verbose'):
                self._lj_reader.verbose = original_verbose
            
            # 批量汇总日志，避免过多输出
            total_processed = success_count + failed_count
            coverage_rate = (success_count / total_processed * 100) if total_processed > 0 else 0
            print(f" 批量预加载完成: 成功{success_count}只, 失败{failed_count}只, 覆盖率{coverage_rate:.1f}%")
                    
        except Exception as e:
            print(f"[ERROR] 批量加载股票成交金额失败: {e}")
            # 为所有股票设置默认值
            for stock_code in stock_codes:
                if stock_code not in self._stock_amount_cache:
                    self._stock_amount_cache[stock_code] = 0.0
    
    def _schedule_async_cleanup(self):
        """安排异步资源清理，不阻塞主界面"""
        try:
            import threading
            
            def cleanup_resources():
                """后台清理资源"""
                try:
                    print("🧹 开始异步清理资源...")
                    
                    # 清理缓存数据
                    if hasattr(self, '_stock_amount_cache'):
                        cache_size = len(self._stock_amount_cache)
                        self._stock_amount_cache.clear()
                        print(f" 清理了 {cache_size} 个股票成交金额缓存")
                    
                    # 清理LJDataReader实例
                    if hasattr(self, '_lj_reader'):
                        del self._lj_reader
                        print(" 清理了LJDataReader实例")
                    
                    # 触发垃圾回收
                    import gc
                    collected = gc.collect()
                    print(f" 垃圾回收释放了 {collected} 个对象")
                    
                    print("🎉 异步资源清理完成")
                    
                except Exception as e:
                    print(f"[ERROR] 异步资源清理失败: {e}")
            
            # 在后台线程中执行清理
            cleanup_thread = threading.Thread(target=cleanup_resources, daemon=True)
            cleanup_thread.start()
            
        except Exception as e:
            print(f"[ERROR] 安排异步清理失败: {e}")
    
    def _get_industry_latest_rating(self, industry_name, industry_info):
        """获取行业最新一天的加权平均评级 - 按成交金额选择前10个股票"""
        try:
            print(f"     处理行业 {industry_name}, industry_info类型: {type(industry_info)}")
            
            # 检查数据结构
            if not isinstance(industry_info, dict):
                print(f"    [ERROR] industry_info不是字典，是 {type(industry_info)}: {industry_info}")
                return None
            
            # 获取行业内的股票
            stocks = industry_info.get('stocks', {})
            print(f"     行业 {industry_name} stocks类型: {type(stocks)}, 数量: {len(stocks) if hasattr(stocks, '__len__') else 'unknown'}")
            
            if isinstance(stocks, list):
                print(f"    📋 stocks是列表类型，共{len(stocks)}只股票，转换为字典格式处理")
                # 处理列表类型的股票数据
                stock_data = []
                for stock_item in stocks:
                    try:
                        # 列表中每个元素应该包含股票代码
                        if isinstance(stock_item, dict):
                            stock_code = stock_item.get('code', stock_item.get('symbol', ''))
                        elif isinstance(stock_item, str):
                            stock_code = stock_item
                        else:
                            continue
                        
                        if not stock_code:
                            continue
                        
                        # 获取股票的评级数据
                        stock_ratings = self._get_stock_rating_data(stock_code)
                        if not stock_ratings:
                            continue
                        
                        # 获取最新一天的评级
                        latest_date = max(stock_ratings, key=lambda x: x[0])
                        latest_rating = latest_date[1]
                        
                        # 获取股票的成交金额（用于加权）
                        amount = self._get_stock_amount(stock_code)
                        
                        stock_data.append({
                            'code': stock_code,
                            'rating': latest_rating,
                            'amount': amount
                        })
                        print(f"       股票 {stock_code}: 评级 {latest_rating}, 成交金额 {amount:.0f}")
                        
                    except Exception as e:
                        print(f"        处理列表中股票失败: {e}")
                        continue
                        
            elif isinstance(stocks, dict):
                print(f"    📋 stocks是字典类型，共{len(stocks)}只股票")
                # 收集所有股票的评级和成交金额数据
                stock_data = []
                
                for stock_code, stock_info in stocks.items():
                    try:
                        # 获取股票的评级数据
                        stock_ratings = self._get_stock_rating_data(stock_code)
                        if not stock_ratings:
                            continue
                        
                        # 获取最新一天的评级
                        latest_date = max(stock_ratings, key=lambda x: x[0])
                        latest_rating = latest_date[1]
                        
                        # 获取股票的成交金额（用于加权）
                        amount = self._get_stock_amount(stock_code)
                        
                        stock_data.append({
                            'code': stock_code,
                            'rating': latest_rating,
                            'amount': amount
                        })
                        print(f"       股票 {stock_code}: 评级 {latest_rating}, 成交金额 {amount:.0f}")
                        
                    except Exception as e:
                        print(f"        获取股票 {stock_code} 数据失败: {e}")
                        continue
            else:
                print(f"    [ERROR] stocks不是列表也不是字典类型，是 {type(stocks)}！跳过此行业")
                return None
            
            if not stock_data:
                print(f"    [ERROR] 行业 {industry_name} 没有有效的股票数据")
                return None
            
            # 按成交金额排序，选择前10个
            stock_data.sort(key=lambda x: x['amount'], reverse=True)
            top_10_stocks = stock_data[:10]
            
            print(f"     行业 {industry_name}: 从{len(stock_data)}只股票中选择成交金额最大的{len(top_10_stocks)}只")
            
            # 计算加权平均评级
            total_weighted_rating = 0
            total_weight = 0
            
            for stock in top_10_stocks:
                weight = stock['amount']
                rating = stock['rating']
                total_weighted_rating += rating * weight
                total_weight += weight
                print(f"       {stock['code']}: 评级{rating} × 权重{weight:.0f}")
            
            if total_weight == 0:
                print(f"    [ERROR] 行业 {industry_name} 总权重为0")
                return None
            
            # 加权平均评级
            weighted_avg_rating = total_weighted_rating / total_weight
            # 保留原始精度，不进行四舍五入，只限制范围
            final_rating = max(0.0, min(7.0, weighted_avg_rating))
            
            print(f"     行业 {industry_name}: 加权平均评级 {weighted_avg_rating:.4f} -> 保留精度 {final_rating:.4f}")
            return float(final_rating)
            
        except Exception as e:
            print(f"    [ERROR] 获取行业 {industry_name} 最新评级失败: {e}")
            return None
    
    def _get_stock_amount(self, stock_code):
        """获取股票的成交金额（用于加权计算）- 优化版使用缓存"""
        try:
            # 优化5: 优先使用预加载的缓存数据
            if hasattr(self, '_stock_amount_cache') and stock_code in self._stock_amount_cache:
                cached_amount = self._stock_amount_cache[stock_code]
                if cached_amount is not None and cached_amount > 0:
                    return cached_amount
                elif cached_amount == 0:
                    # 如果缓存中明确记录为0，说明数据文件中确实没有此股票
                    return 0.0
                    
            # 如果缓存中没有数据或值为None，回退到原有方法
            try:
                # 使用类级别的LJDataReader实例，避免重复初始化
                if not hasattr(self, '_lj_reader'):
                    from utils.lj_data_reader import LJDataReader
                    self._lj_reader = LJDataReader(verbose=False)  # 静默模式，避免重复日志
                    print(f"      🔧 初始化LJDataReader成功")
                
                lj_reader = self._lj_reader
                
                # 使用当前市场类型，避免市场检测
                current_market = self._get_current_market_type()
                print(f"      🌍 当前市场: {current_market}")
                
                # 检查对应市场的数据文件是否存在
                market_data_files = {
                    'cn': 'cn-lj.dat.gz',
                    'hk': 'hk-lj.dat.gz', 
                    'us': 'us-lj.dat.gz'
                }
                
                target_file = market_data_files[current_market]
                file_exists = os.path.exists(target_file)
                print(f"      📁 目标文件: {target_file}, 存在: {file_exists}")
                
                if current_market in market_data_files and file_exists:
                    # 获取最近1天的数据
                    print(f"       正在从LJDataReader获取 {stock_code} 数据...")
                    volume_data = lj_reader.get_volume_price_data(stock_code, days=1, market=current_market)
                    if volume_data and 'data' in volume_data and volume_data['data']:
                        latest_data = volume_data['data'][-1]  # 最新一天的数据
                        raw_amount = latest_data.get('amount', 0)  # 原始成交金额
                        # LJDataReader返回的成交额单位需要修正（约为实际值的1/10）
                        amount = raw_amount * 10  # 修正单位为元
                        print(f"       获取到原始成交金额: {raw_amount} -> 修正后: {amount}")
                        if amount > 0:
                            # 缓存结果供后续使用
                            if hasattr(self, '_stock_amount_cache'):
                                self._stock_amount_cache[stock_code] = float(amount)
                            return float(amount)
                        else:
                            # 如果没有成交金额，尝试计算：成交金额 = 成交量 × 收盘价
                            volume = latest_data.get('volume', 0)  # 成交量
                            close_price = latest_data.get('close_price', latest_data.get('收盘价', 0))  # 收盘价
                            if volume > 0 and close_price > 0:
                                calculated_amount = volume * close_price
                                print(f"      🧮 计算成交金额: {volume} × {close_price} = {calculated_amount}")
                                # 缓存结果供后续使用
                                if hasattr(self, '_stock_amount_cache'):
                                    self._stock_amount_cache[stock_code] = float(calculated_amount)
                                return float(calculated_amount)
                    else:
                        print(f"      [ERROR] LJDataReader返回空数据: {volume_data}")
                else:
                    print(f"      [ERROR] 市场文件检查失败: market={current_market}, file={market_data_files.get(current_market, 'unknown')}, exists={file_exists}")
            except Exception as e:
                print(f"      [ERROR] LJDataReader获取 {stock_code} 成交金额失败: {e}")
                # 检查具体错误原因
                if "lj-read模块不可用" in str(e):
                    print(f"        lj-read模块问题，检查 {current_market}-lj.dat.gz 文件")
                elif "文件不存在" in str(e):
                    print(f"        数据文件不存在: {market_data_files.get(current_market, 'unknown')}")
                else:
                    print(f"       具体错误: {str(e)[:100]}")  # 只显示前100字符避免日志过长
            
            # 如果.dat.gz文件中没有数据，返回0（不使用模拟数据）
            return 0.0
            
        except Exception as e:
            return 0.0  # 找不到数据时返回0，不使用模拟数据
    
    def _get_rating_description(self, rating_level):
        """获取评级等级的详细描述"""
        descriptions = {
            "7级": "🔥 极强 - 大多 (最高评级)",
            "6级": " 强势 - 中多 (高评级)", 
            "5级": "🟢 偏强 - 小多 (较好)",
            "4级": "⚪ 中性 - 微多 (中性偏好)",
            "3级": "🟡 偏弱 - 微空 (中性偏差)",
            "2级": "🔸 弱势 - 小空 (较差)",
            "1级": "🔻 很弱 - 中空 (低评级)",
            "0级": "❄️ 极弱 - 大空 (最低评级)"
        }
        return descriptions.get(rating_level, "未知等级")
    
    def _get_rating_level_from_score(self, rating_score):
        """根据精确评级分数确定等级和颜色"""
        # 评级等级定义（与计算时使用的一致）
        rating_levels = {
            "7级": {"min": 6.5, "max": 7.1, "color": "#dc3545"},    # 深红色 - 大多（最高）
            "6级": {"min": 5.5, "max": 6.5, "color": "#ffc107"},    # 橙黄色 - 中多（原5级色）
            "5级": {"min": 4.5, "max": 5.5, "color": "#ff6b6b"},    # 浅红色 - 小多（原4级色）
            "4级": {"min": 3.5, "max": 4.5, "color": "#fd7e14"},    # 橙红色 - 微多（原6级色）
            "3级": {"min": 2.5, "max": 3.5, "color": "#6f42c1"},    # 紫色 - 微空
            "2级": {"min": 1.5, "max": 2.5, "color": "#6c757d"},    # 灰色 - 小空
            "1级": {"min": 0.5, "max": 1.5, "color": "#28a745"},    # 绿色 - 中空
            "0级": {"min": 0.0, "max": 0.5, "color": "#198754"}     # 深绿色 - 大空（最低）
        }
        
        # 根据评级分数确定等级
        for level_name, level_info in rating_levels.items():
            if level_info["min"] <= rating_score < level_info["max"]:
                return level_name, level_info["color"]
        
        # 处理边界情况
        if rating_score >= 6.5:
            return "7级", "#dc3545"
        elif rating_score < 0.5:
            return "0级", "#198754"
        else:
            return "4级", "#fd7e14"  # 默认中性
    

    



    
    def _get_industry_detailed_score(self, industry_name):
        """获取行业的详细评分信息"""
        try:
            print(f" 获取行业详细评分: {industry_name}")
            
            # 优先从 analysis_results_obj 获取数据 (这是TAB1详细分析的数据源)
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                if hasattr(self.analysis_results_obj, 'industries'):
                    industry_info = self.analysis_results_obj.industries.get(industry_name, {})
                    print(f"   找到行业信息: {industry_name} -> {type(industry_info)}")
                    
                    # 与TreeView完全一致的TMA分数获取方式
                    tma_value = 0
                    if isinstance(industry_info, dict):
                        tma_value = industry_info.get('irsi', 0)
                        # 处理TMA值也是字典的情况
                        if isinstance(tma_value, dict):
                            tma_value = tma_value.get('irsi', 0)
                    
                    # 确保tma_value是数字
                    if not isinstance(tma_value, (int, float)):
                        tma_value = 0
                    
                    tma_score = float(tma_value)
                    stock_count = industry_info.get('stock_count', 0)
                    
                    print(f"   与TreeView一致的TMA分数: {tma_score:.2f}")
                    
                    # 评级分的获取
                    if 'irsi' in industry_info:
                        irsi_data = industry_info['irsi']
                        if isinstance(irsi_data, dict):
                            # 使用正确的个股评级加权平均计算
                            rating_score = self._get_industry_latest_rating(industry_name, industry_info)
                            if rating_score is None:
                                rating_score = 4.0  # 默认中性评级
                            
                            print(f"   行业加权评级分: {rating_score:.2f}, TMA分数: {tma_score:.2f}")
                            
                            return {
                                'rating_score': rating_score,  # 评级分（用于排序和显示）
                                'tma_score': tma_score,  # 与TreeView一致的TMA分数
                                'stock_count': int(stock_count)
                            }
                        else:
                            # irsi_data 是数值类型，使用个股评级加权平均计算
                            rating_score = self._get_industry_latest_rating(industry_name, industry_info)
                            if rating_score is None:
                                rating_score = 4.0  # 默认中性评级
                            
                            print(f"   行业加权评级分: {rating_score:.2f}")
                            
                            return {
                                'rating_score': rating_score,  # 评级分（用于排序和显示）
                                'tma_score': tma_score,  # 与TreeView一致的TMA分数
                                'stock_count': int(stock_count)
                            }
                    else:
                        # 没有irsi数据，使用个股评级加权平均计算
                        rating_score = self._get_industry_latest_rating(industry_name, industry_info)
                        if rating_score is None:
                            rating_score = 4.0  # 默认中性评级
                        
                        return {
                            'rating_score': rating_score,  # 评级分（用于排序和显示）
                            'tma_score': tma_score,  # 与TreeView一致的TMA分数
                            'stock_count': int(stock_count)
                        }
            
            # 备用：从 analysis_results 字典获取数据
            if hasattr(self, 'analysis_results') and self.analysis_results:
                industries_data = self.analysis_results.get('industries', {})
                if industry_name in industries_data:
                    industry_info = industries_data[industry_name]
                    irsi_data = industry_info.get('irsi', {})
                    
                    # 备用数据也使用个股评级加权平均计算
                    rating_score = self._get_industry_latest_rating(industry_name, industry_info)
                    if rating_score is None:
                        rating_score = 4.0  # 默认中性评级
                    
                    # 获取TMA分数用于显示
                    if isinstance(irsi_data, dict):
                        tma_score = irsi_data.get('enhanced_tma_score', irsi_data.get('irsi', 0))
                    else:
                        tma_score = float(irsi_data) if irsi_data else 50.0
                    
                    return {
                        'rating_score': rating_score,  # 评级分（用于排序和显示）
                        'tma_score': tma_score,
                        'stock_count': industry_info.get('stock_count', 0)
                    }
            
            print(f"   未找到行业数据: {industry_name}")
            # 如果没有找到详细数据，返回默认值
            return {
                'rating_score': 4.0,  # 默认评级分（中性）
                'tma_score': 0.0,
                'stock_count': 0
            }
            
        except Exception as e:
            print(f"[ERROR] 获取行业详细评分失败 {industry_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'rating_score': 4.0,  # 默认评级分（中性）
                'tma_score': 0.0,
                'stock_count': 0
            }
    

    
    def _generate_enhanced_html_template(self, all_industries, rating_data):
        """生成增强版的HTML模板"""
        try:
            from datetime import datetime
            
            # 统计信息
            total_industries = len(all_industries)
            top_industries = sorted(all_industries, key=lambda x: x.get('rating_score', 0), reverse=True)[:5]
            
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>行业评级分析报告</title>
    <style>
        body {{
            font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f8f9fa;
        }}
        .header h1 {{
            color: #2c3e50;
            font-size: 32px;
            margin: 0;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .header .subtitle {{
            color: #6c757d;
            font-size: 16px;
            margin: 10px 0;
        }}
        .stats-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-left: 5px solid #007bff;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 14px;
            color: #6c757d;
        }}
        .industries-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .industries-table th {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
            font-size: 14px;
        }}
        .industries-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            vertical-align: middle;
        }}
        .industries-table tr:hover {{
            background: #f8f9fa;
        }}
        .rating-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            font-size: 12px;
            text-align: center;
            min-width: 60px;
            display: inline-block;
        }}

        .tma-score {{
            font-weight: bold;
            color: #007bff;
        }}
        .stock-count {{
            color: #6c757d;
            font-size: 12px;
        }}
        .top-performers {{
            background: linear-gradient(135deg, #e8f5e8, #f0f8f0);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 2px solid #28a745;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #dee2e6;
            color: #6c757d;
            font-size: 13px;
        }}
        .cache-info {{
            background: #e3f2fd;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2196f3;
            font-size: 13px;
            color: #1565c0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> 行业评级分析报告</h1>
            <div class="subtitle">基于AI智能分析的增强版8级行业评级体系</div>
            <div class="subtitle">数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        

        
        <div class="stats-overview">
            <div class="stat-card">
                <div class="stat-value">{total_industries}</div>
                <div class="stat-label">总行业数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{max((i.get('rating_score', 0) for i in all_industries), default=0):.2f}</div>
                <div class="stat-label">最高等级</div>
            </div>
        </div>
        
        <div class="top-performers">
            <h3 style="margin-top: 0; color: #155724;">🌟 表现最佳前5行业</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
            """
            
            for i, industry in enumerate(top_industries, 1):
                # 评级分颜色：红涨绿跌
                rating_score = industry.get('rating_score', 0)
                if rating_score >= 5.0:
                    rating_color = "#dc3545"  # 红色
                elif rating_score >= 3.0:
                    rating_color = "#ffc107"  # 黄色
                else:
                    rating_color = "#28a745"  # 绿色
                
                # TMA分数颜色：红涨绿跌
                if industry['tma_score'] > 0:
                    tma_color = "#dc3545"  # 正值红色
                elif industry['tma_score'] < 0:
                    tma_color = "#28a745"  # 负值绿色
                else:
                    tma_color = "#6c757d"  # 中性灰色
                
                html_content += f"""
                <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {industry['color']};">
                    <div style="font-weight: bold; color: #2c3e50;">#{i} {industry['name']}</div>
                    <div style="font-size: 12px; margin-top: 5px;">
                        评级: <span style="color: {rating_color}; font-weight: bold;">{rating_score:.2f}</span> | 
                        TMA: <span style="color: {tma_color}; font-weight: bold;">{industry['tma_score']:.2f}</span>
                    </div>
                </div>
                """
            
            html_content += """
            </div>
        </div>
        
        <table class="industries-table">
            <thead>
                <tr>
                    <th>排名</th>
                    <th>行业名称</th>
                    <th>评级等级</th>
                    <th>TMA分数</th>
                    <th>股票数量</th>
                </tr>
            </thead>
            <tbody>
            """
            
            # 按评级分排序显示所有行业（从大到小）
            sorted_industries = sorted(all_industries, key=lambda x: x.get('rating_score', 0), reverse=True)
            for i, industry in enumerate(sorted_industries, 1):
                
                # TMA分数的颜色也采用红涨绿跌
                if industry['tma_score'] > 0:
                    tma_color = "#dc3545"  # 正值红色（涨）
                elif industry['tma_score'] < 0:
                    tma_color = "#28a745"  # 负值绿色（跌）
                else:
                    tma_color = "#6c757d"  # 中性灰色
                
                html_content += f"""
                <tr>
                    <td style="font-weight: bold; color: #2c3e50;">#{i}</td>
                    <td style="font-weight: 500;">{industry['name']}</td>
                    <td>
                        <span class="rating-badge" style="background: {industry['color']};">
                            {industry['rating_level']}
                        </span>
                    </td>
                    <td style="font-weight: bold; color: {tma_color};">{industry['tma_score']:.2f}</td>
                    <td class="stock-count">{industry['stock_count']} 只</td>
                </tr>
                """
            
            html_content += """
            </tbody>
        </table>
        
        <div class="footer">
            <p> 数据来源: AI股票分析系统 |  智能算法: RTSI + IRSI + TMA 多重评估</p>
            <p> 投资有风险，本报告仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>
            """
            
            return html_content
            
        except Exception as e:
            print(f"[ERROR] 生成增强版HTML模板失败: {e}")
            import traceback
            traceback.print_exc()
            return f"""
            <div style="text-align: center; padding: 50px; color: #dc3545;">
                <h3>[ERROR] 生成HTML模板失败</h3>
                <p>错误信息: {str(e)}</p>
            </div>
            """
    
    def start_industry_chart_calculation(self):
        """开始行业趋势图表计算 - 由定时器触发"""
        try:
            if hasattr(self, 'pending_industry_name') and self.pending_industry_name:
                print(f"🔄 开始计算行业趋势图表: {self.pending_industry_name}")
                self.update_industry_chart(self.pending_industry_name)
                # 清除待处理的行业名
                self.pending_industry_name = None
        except Exception as e:
            print(f"[ERROR] 行业趋势图表计算失败: {e}")
            import traceback
            traceback.print_exc()
            # 发生错误时停止动画并显示错误信息
            self.stop_industry_loading_animation()  # 停止等待动画
            if hasattr(self, 'industry_chart_stacked_widget'):
                self.industry_chart_stacked_widget.setCurrentIndex(2)  # 切换到结果页面
            if hasattr(self, 'industry_chart_webview'):
                self.industry_chart_webview.setHtml(f"<p style='color: #dc3545;'>计算失败: {str(e)}</p>")
            elif hasattr(self, 'industry_chart_text'):
                self.industry_chart_text.setHtml(f"<p style='color: #dc3545;'>计算失败: {str(e)}</p>")

    def on_market_tab_changed(self, index):
        """市场分析Tab切换事件处理 - 延迟加载HTML内容"""
        try:
            print(f"[市场Tab切换] 切换到Tab索引: {index}")
            
            # 处理市场HTML Tab
            if hasattr(self, 'market_html_tabs'):
                for tab_index, view, html_path in self.market_html_tabs:
                    if tab_index == index and html_path.exists():
                        print(f"[市场Tab切换] 加载HTML文件: {html_path.name}")
                        if WEBENGINE_AVAILABLE and isinstance(view, QWebEngineView):
                            url = QUrl.fromLocalFile(str(html_path))
                            print(f"[市场Tab切换] 加载URL: {url.toString()}")
                            view.load(url)
                        else:
                            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                                html = f.read()
                                if hasattr(view, 'setHtml'):
                                    view.setHtml(html)
                                else:
                                    view.setPlainText(html)
                        return  # 已处理，直接返回
        except Exception as e:
            print(f"[市场Tab切换] 处理Tab切换失败: {e}")

    def on_stock_tab_changed(self, index):
        """股票Tab切换事件处理 - 延迟加载量价数据和其他Tab内容"""
        try:
            # 调试信息
            print(f"[Tab切换] 切换到Tab索引: {index}")
            print(f"[Tab切换] 是否有current_stock_code: {hasattr(self, 'current_stock_code')}")
            if hasattr(self, 'current_stock_code'):
                print(f"[Tab切换] current_stock_code值: {self.current_stock_code}")
            print(f"[Tab切换] 是否有stock_extra_tabs: {hasattr(self, 'stock_extra_tabs')}")
            if hasattr(self, 'stock_extra_tabs'):
                print(f"[Tab切换] stock_extra_tabs数量: {len(self.stock_extra_tabs)}")
                print(f"[Tab切换] stock_extra_tabs索引: {[idx for idx, _, _ in self.stock_extra_tabs]}")
            
            if not hasattr(self, 'current_stock_code') or not self.current_stock_code:
                print("[Tab切换] 没有股票代码，退出")
                return
            
            # 获取当前Tab的标题来判断是哪个Tab
            current_tab_text = self.stock_tab_widget.tabText(index)
            print(f"[Tab切换] 当前Tab标题: {current_tab_text}")
            
            # 处理额外HTML Tab - 传递股票代码参数（优先处理）
            if hasattr(self, 'stock_extra_tabs'):
                for extra_index, view, html_path in self.stock_extra_tabs:
                    if extra_index == index and html_path.exists():
                        print(f"[Tab切换] 切换到额外HTML Tab: {html_path.name}，加载股票代码: {self.current_stock_code}")
                        if WEBENGINE_AVAILABLE and isinstance(view, QWebEngineView):
                            # 先清空占位内容
                            view.setHtml("")
                            
                            # 构建完整URL
                            base_url = QUrl.fromLocalFile(str(html_path))
                            full_url = base_url.toString()
                            full_url_with_code = f"{full_url}##{self.current_stock_code}##"
                            print(f"[Tab切换] 加载URL: {full_url_with_code}")
                            
                            # 添加加载完成回调
                            def on_load_finished(ok):
                                if ok:
                                    print(f"[Tab切换] HTML加载成功: {html_path.name}")
                                    # 调试：检查JavaScript中实际接收到的hash
                                    view.page().runJavaScript(
                                        "window.location.hash",
                                        lambda result: print(f"[Tab切换] JavaScript接收到的hash: {result}")
                                    )
                                    # 调试：执行getUrlParams并查看结果
                                    view.page().runJavaScript(
                                        """
                                        (function() {
                                            if (typeof getUrlParams === 'function') {
                                                var params = getUrlParams();
                                                return JSON.stringify(params);
                                            }
                                            return 'getUrlParams函数不存在';
                                        })()
                                        """,
                                        lambda result: print(f"[Tab切换] getUrlParams返回: {result}")
                                    )
                                else:
                                    print(f"[Tab切换] HTML加载失败: {html_path.name}")
                            
                            # 断开之前的信号连接
                            try:
                                view.loadFinished.disconnect()
                            except:
                                pass
                            view.loadFinished.connect(on_load_finished)
                            
                            # 加载URL
                            view.load(QUrl(full_url_with_code))
                        else:
                            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                                html = f.read().replace('##CODE##', f"##{self.current_stock_code}##")
                                if hasattr(view, 'setHtml'):
                                    view.setHtml(html)
                                else:
                                    view.setPlainText(html)
                        return  # 已处理，直接返回
            
            # 检查是否切换到趋势图表Tab
            if "趋势图表" in current_tab_text:
                print(f"[Tab切换] 切换到趋势图表Tab，开始加载量价数据: {self.current_stock_code}")
                self._load_stock_chart_data(self.current_stock_code)
            
            # 检查是否切换到迷你投资大师Tab
            elif "迷你投资大师" in current_tab_text:
                if hasattr(self, 'mini_master_cache') and self.current_stock_code in self.mini_master_cache:
                    print(f"[Tab切换] 自动显示{self.current_stock_code}的缓存迷你投资大师分析")
                    self.show_cached_mini_master_result(self.current_stock_code)
                else:
                    print(f"[Tab切换] {self.current_stock_code}未分析过，自动触发迷你投资大师分析")
                    current_stock_name = getattr(self, 'current_stock_name', '')
                    self.auto_trigger_mini_master_analysis(self.current_stock_code, current_stock_name)
            
            # 检查是否切换到AI技术分析师Tab
            elif "AI技术分析" in current_tab_text:
                if hasattr(self, 'stock_ai_cache') and self.current_stock_code in self.stock_ai_cache:
                    print(f"[Tab切换] 自动显示{self.current_stock_code}的缓存AI分析")
                    self.show_cached_ai_result(self.current_stock_code)
                    
        except Exception as e:
            print(f"[Tab切换] 处理Tab切换失败: {e}")
    
    def ensure_stock_server_running(self):
        """确保本地股票服务器正在运行（仅中文+CN市场）"""
        if self.server_started:
            print(f"[服务器管理] 服务器已标记为启动，跳过检查 (server_started_by_us={self.server_started_by_us})")
            return
        
        # 检查语言和市场条件
        current_lang = get_system_language() if callable(get_system_language) else 'zh'
        main_window = getattr(self, 'main_window', None)
        detected_market = getattr(main_window, 'detected_market', 'cn') if main_window else 'cn'
        
        if not current_lang.startswith('zh') or detected_market.lower() != 'cn':
            print("[服务器管理] 跳过服务器启动: 非中文A股市场")
            return
        
        print("[服务器管理] 开始检查服务器状态...")
        server_names = ["stockhost.exe", "大师服务器.exe"]
        server_running = False
        detected_pid = None
        
        # 使用psutil检查进程
        if psutil:
            print("[服务器管理] 使用psutil检查运行中的服务器进程...")
            for proc in psutil.process_iter(["name", "exe", "pid"]):
                try:
                    proc_name = proc.info['name']
                    proc_exe = proc.info['exe']
                    for name in server_names:
                        if name.lower() == proc_name.lower() or (proc_exe and name.lower() in proc_exe.lower()):
                            detected_pid = proc.info['pid']
                            print(f"[服务器管理] ✓ 检测到服务器 {name} 已在运行 (PID: {detected_pid})")
                            server_running = True
                            break
                    if server_running:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not server_running:
                print("[服务器管理] 未检测到运行中的服务器进程")
        else:
            print("[服务器管理] ⚠️ psutil模块不可用，无法检测运行中的进程")
        
        if server_running:
            self.server_started = True
            self.server_started_by_us = False  # 不是本软件启动的（可能是托盘启动或用户手动启动）
            print(f"[服务器管理] 服务器状态: server_started=True, server_started_by_us=False")
            print(f"[服务器管理] → 此服务器不是本软件启动，退出时将不会自动关闭")
            return
        
        # 尝试启动服务器
        print("[服务器管理] 未检测到运行中的服务器，尝试启动新服务器...")
        from utils.path_helper import get_base_path
        base_path = Path(get_base_path())
        candidate_dirs = [base_path, project_root]
        
        for exe_name in server_names:
            for directory in candidate_dirs:
                exe_path = directory / exe_name
                if exe_path.exists():
                    try:
                        print(f"[服务器管理] 正在启动服务器: {exe_name}")
                        print(f"[服务器管理]   路径: {exe_path}")
                        print(f"[服务器管理]   工作目录: {directory}")
                        import subprocess
                        subprocess.Popen([str(exe_path), "--server"], cwd=str(directory))
                        self.server_started = True
                        self.server_started_by_us = True  # 是本软件启动的
                        print(f"[服务器管理] ✓ 服务器启动成功: {exe_name}")
                        print(f"[服务器管理] 服务器状态: server_started=True, server_started_by_us=True")
                        print(f"[服务器管理] → 此服务器由本软件启动，退出时将自动关闭")
                        return
                    except Exception as e:
                        print(f"[服务器管理] ✗ 启动服务器 {exe_name} 失败: {e}")
        
        print("[服务器管理] ✗ 未能找到并启动任何服务器可执行文件")
    
    def get_current_rating_level(self, rtsi_value):
        """根据RTSI值获取当前评级等级"""
        if rtsi_value >= 85:
            return "7级 (大多)"
        elif rtsi_value >= 70:
            return "6级 (中多)"
        elif rtsi_value >= 55:
            return "5级 (小多)"
        elif rtsi_value >= 45:
            return "4级 (微多)"
        elif rtsi_value >= 35:
            return "3级 (微空)"
        elif rtsi_value >= 20:
            return "2级 (小空)"
        elif rtsi_value >= 10:
            return "1级 (中空)"
        else:
            return "0级 (大空)"
    
    def get_trend_strength_desc(self, rtsi_value):
        """获取趋势强度描述"""
        if rtsi_value >= 80:
            return "极强"
        elif rtsi_value >= 60:
            return "较强"
        elif rtsi_value >= 40:
            return "中等"
        elif rtsi_value >= 20:
            return "较弱"
        else:
            return "极弱"
    
    def get_trend_strength_desc_display(self, rtsi_value):
        """获取趋势强度描述的国际化显示"""
        if rtsi_value >= 80:
            return t_gui("extremely_strong")
        elif rtsi_value >= 60:
            return t_gui("strong")
        elif rtsi_value >= 40:
            return t_gui("neutral")
        elif rtsi_value >= 20:
            return t_gui("weak")
        else:
            return t_gui("extremely_weak")
    
    def get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 核心指标相关的新方法
    def get_investment_recommendation(self, rtsi_value):
        """获取投资建议"""
        if rtsi_value >= 70:
            return "强烈推荐"
        elif rtsi_value >= 50:
            return "推荐"
        elif rtsi_value >= 30:
            return "谨慎关注"
        else:
            return "不推荐"
    
    def get_suitable_investors(self, rtsi_value):
        """获取适合人群"""
        if rtsi_value >= 70:
            return "激进型投资者"
        elif rtsi_value >= 50:
            return "成长型投资者"
        elif rtsi_value >= 30:
            return "稳健型投资者"
        else:
            return "保守型投资者"
    
    def get_operation_difficulty(self, rtsi_value):
        """获取操作难度"""
        if rtsi_value >= 70:
            return "容易 (趋势明确)"
        elif rtsi_value >= 50:
            return "中等 (需要技巧)"
        elif rtsi_value >= 30:
            return "困难 (震荡频繁)"
        else:
            return "极难 (下跌趋势)"
    
    def get_short_term_performance(self, rtsi_value):
        """获取短期表现"""
        if rtsi_value >= 70:
            return "优秀"
        elif rtsi_value >= 50:
            return "良好"
        elif rtsi_value >= 30:
            return "一般"
        else:
            return "较差"
    
    def get_medium_term_performance(self, rtsi_value):
        """获取中期表现"""
        if rtsi_value >= 60:
            return "强势上升"
        elif rtsi_value >= 40:
            return "震荡上行"
        elif rtsi_value >= 20:
            return "震荡下行"
        else:
            return "弱势下跌"
    
    def get_long_term_potential(self, rtsi_value):
        """获取长期潜力"""
        if rtsi_value >= 60:
            return "潜力巨大"
        elif rtsi_value >= 40:
            return "有一定潜力"
        elif rtsi_value >= 20:
            return "潜力有限"
        else:
            return "风险较大"
    
    def get_industry_ranking(self, rtsi_value):
        """获取行业排名 - 支持红涨绿跌颜色"""
        if rtsi_value >= 70:
            return '<span style="color: #dc3545; font-weight: bold;">行业领先</span>'
        elif rtsi_value >= 50:
            return '<span style="color: #dc3545;">行业中上</span>'
        elif rtsi_value >= 30:
            return '<span style="color: #6c757d;">行业中等</span>'
        else:
            return '<span style="color: #28a745;">行业落后</span>'
    
    # 行业分析相关方法
    def get_industry_risk_level(self, tma_value):
        """获取行业风险等级"""
        if tma_value > 20:
            return "低风险"
        elif tma_value > 5:
            return "较低风险"
        elif tma_value > -5:
            return "中等风险"
        elif tma_value > -20:
            return "较高风险"
        else:
            return "高风险"
    
    def get_top_stocks_in_industry(self, industry_name, count=5):
        """获取指定行业中前N个RTSI最大的股票（仅大盘股）"""
        if not self.analysis_results_obj:
            return []
            
        stocks_data = self.analysis_results_obj.stocks
        industry_stocks = []
        
        for stock_code, stock_info in stocks_data.items():
            stock_industry = stock_info.get('industry', '')
            if stock_industry == industry_name:
                # 大盘股筛选：指数行业例外，允许所有指数通过
                if industry_name != "指数" and not self._is_large_cap_stock(stock_code):
                    continue
                
                rtsi_value = stock_info.get('rtsi', 0)
                if isinstance(rtsi_value, dict):
                    rtsi_value = rtsi_value.get('rtsi', 0)
                if not isinstance(rtsi_value, (int, float)):
                    rtsi_value = 0
                    
                stock_name = stock_info.get('name', stock_code)
                industry_stocks.append((stock_code, stock_name, float(rtsi_value)))
        
        # 按RTSI值排序
        industry_stocks.sort(key=lambda x: x[2], reverse=True)
        return industry_stocks[:count]
    
    def _is_large_cap_stock(self, stock_code: str) -> bool:
        """判断是否为大盘股（与algorithms模块中的逻辑保持一致）"""
        code = str(stock_code).strip()
        
        # A股大盘股判断
        if len(code) == 6 and code.isdigit():
            # 主板股票通常是大盘股
            if code.startswith('00') or code.startswith('60'):
                return True
            # 部分深市主板大盘股（001、002开头的部分股票）
            if code.startswith('001') or code.startswith('002'):
                return True
        
        # 港股大盘股判断（5位数字）
        elif len(code) == 5 and code.isdigit():
            # 知名港股大盘股代码
            large_cap_hk_codes = {
                '00700', '00939', '00388', '00005', '00001', '00002', '00003', '00004',
                '00011', '00012', '00016', '00017', '00019', '00023', '00027', '00066',
                '00083', '00101', '00135', '00144', '00151', '00175', '00267', '00288',
                '00386', '00688', '00762', '00823', '00857', '00883', '00941', '00992',
                '01038', '01044', '01088', '01093', '01109', '01113', '01171', '01177',
                '01299', '01398', '01818', '01928', '01997', '02007', '02018', '02020',
                '02202', '02318', '02319', '02382', '02388', '02628', '03328', '03988'
            }
            return code in large_cap_hk_codes
        
        # 美股大盘股判断（字母代码）
        elif code.isalpha():
            # 知名美股大盘股代码
            large_cap_us_codes = {
                'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA',
                'BRK.A', 'BRK.B', 'UNH', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'PFE',
                'ABBV', 'BAC', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'DIS', 'ABT',
                'MRK', 'ACN', 'VZ', 'CRM', 'DHR', 'ADBE', 'NKE', 'TXN', 'LIN',
                'WMT', 'NEE', 'AMD', 'BMY', 'PM', 'RTX', 'QCOM', 'HON', 'T',
                'UPS', 'ORCL', 'COP', 'MS', 'SCHW', 'LOW', 'CAT', 'GS', 'IBM',
                'AXP', 'BLK', 'DE', 'ELV', 'LMT', 'SYK', 'TJX', 'MDT', 'ADP',
                'GE', 'C', 'MDLZ', 'ISRG', 'REGN', 'CB', 'MMC', 'SO', 'PLD',
                'NOW', 'ZTS', 'ICE', 'DUK', 'SHW', 'CMG', 'WM', 'GD', 'TGT',
                'BDX', 'ITW', 'EOG', 'FIS', 'NSC', 'SRE', 'MU', 'BSX', 'FCX'
            }
            return code.upper() in large_cap_us_codes
        
        # 默认不是大盘股
        return False
    
    def get_industry_trend_status(self, tma_value):
        """获取行业趋势状态"""
        if tma_value > 15:
            return "强势上升"
        elif tma_value > 5:
            return "温和上升"
        elif tma_value > -5:
            return "震荡整理"
        elif tma_value > -15:
            return "温和下降"
        else:
            return "弱势下降"
    
    def get_industry_market_position(self, tma_value):
        """获取行业市场地位"""
        if tma_value > 20:
            return "市场领先"
        elif tma_value > 5:
            return "市场主流"
        elif tma_value > -5:
            return "市场平均"
        elif tma_value > -20:
            return "市场落后"
        else:
            return "市场垫底"
    
    def get_industry_allocation_value(self, tma_value):
        """获取行业配置价值"""
        if tma_value > 15:
            return "高配置价值"
        elif tma_value > 5:
            return "中等配置价值"
        elif tma_value > -5:
            return "观望配置价值"
        elif tma_value > -15:
            return "低配置价值"
        else:
            return "避免配置"
    
    # 大盘分析相关方法 - 移植自旧版main_window.py
    def analyze_bull_bear_balance(self, market_data):
        """分析多空力量对比"""
        # 从市场数据中提取多空力量信息
        latest_analysis = market_data.get('latest_analysis', {})
        bull_bear_ratio = latest_analysis.get('bull_bear_ratio', 1.0)
        
        if bull_bear_ratio > 2.0:
            return f"多头绝对优势 (多空比: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 1.5:
            return f"多头力量强劲 (多空比: {bull_bear_ratio:.2f}:1)"
        elif bull_bear_ratio > 0.8:
            return t_gui("多空力量平衡_(多空比:_{bull_bear_ratio:.2f}:1)", bull_bear_ratio=bull_bear_ratio)
        elif bull_bear_ratio > 0.5:
            return f"空头力量强劲 (多空比: {bull_bear_ratio:.2f}:1)"
        else:
            return f"空头绝对优势 (多空比: {bull_bear_ratio:.2f}:1)"
    
    def analyze_historical_trend(self, market_data):
        """分析历史趋势"""
        history = market_data.get('history', [])
        if len(history) >= 10:
            recent_avg = sum(h.get('msci', 50) for h in history[-5:]) / 5
            earlier_avg = sum(h.get('msci', 50) for h in history[-10:-5]) / 5
            change = recent_avg - earlier_avg
            
            if change > 5:
                return f"近期情绪显著改善 (+{change:.1f})"
            elif change > 2:
                return f"近期情绪温和改善 (+{change:.1f})"
            elif change > -2:
                return f"近期情绪基本稳定 ({change:+.1f})"
            elif change > -5:
                return f"近期情绪温和恶化 ({change:.1f})"
            else:
                return f"近期情绪显著恶化 ({change:.1f})"
        else:
            return "历史数据不足，无法对比"
    
    def assess_market_risk(self, msci_value, risk_level):
        """评估市场风险"""
        if msci_value > 70:
            return "高风险：市场过热，建议减仓"
        elif msci_value > 50:
            return t_gui("中等风险：保持谨慎，控制仓位")
        elif msci_value > 30:
            return "低风险：适度配置，分批建仓"
        else:
            return "机会大于风险：考虑逆向布局"
    
    def get_systemic_risk(self, msci_value):
        """获取系统性风险"""
        if msci_value > 75:
            return "极高 (泡沫风险)"
        elif msci_value > 60:
            return "较高 (过热风险)"
        elif msci_value > 40:
            return "中等 (正常范围)"
        elif msci_value > 25:
            return "较低 (底部区域)"
        else:
            return "极低 (极度超跌)"
    
    def get_liquidity_risk(self, volume_ratio):
        """获取流动性风险"""
        if volume_ratio > 1.5:
            return "低 (成交活跃)"
        elif volume_ratio > 1.0:
            return "较低 (成交正常)"
        elif volume_ratio > 0.7:
            return "中等 (成交偏淡)"
        else:
            return "较高 (成交清淡)"
    
    def forecast_market_outlook(self, msci_value, trend_5d):
        """预测市场展望"""
        if trend_5d > 3:
            return "短期情绪有望继续改善，但需防范过热"
        elif trend_5d > 0:
            return "短期情绪保持稳定，维持当前策略"
        elif trend_5d > -3:
            return "短期情绪继续偏弱，谨慎操作"
        else:
            return "短期情绪进一步恶化，保持观望"
    
    def get_medium_term_outlook(self, msci_value):
        """获取中期展望"""
        if msci_value > 65:
            return "回调压力较大，注意风险"
        elif msci_value > 45:
            return "震荡整理为主，结构性机会"
        elif msci_value > 25:
            return "筑底过程延续，耐心等待"
        else:
            return "底部区域确认，布局良机"
    
    def get_long_term_prospect(self, msci_value):
        """获取长期前景"""
        if msci_value > 60:
            return "长期向好，但估值偏高"
        elif msci_value > 40:
            return "长期稳健，估值合理"
        else:
            return "长期机会，估值偏低"
    
    def suggest_investment_strategy(self, msci_value, market_state):
        """建议投资策略"""
        if msci_value > 70:
            return """• 策略: 防守为主
• 仓位: 建议减至30%以下
• 操作: 高抛锁定收益
• 选股: 关注防守型股票"""
        elif msci_value > 50:
            return """• 策略: 稳健参与
• 仓位: 建议保持50-70%
• 操作: 精选个股，波段操作
• 选股: 优质蓝筹+成长股"""
        elif msci_value > 30:
            return """• 策略: 谨慎建仓
• 仓位: 建议控制30-50%
• 操作: 分批布局，不急满仓
• 选股: 基本面扎实的优质股"""
        else:
            return """• 策略: 逆向布局
• 仓位: 逐步增至70%以上
• 操作: 分批买入，长期持有
• 选股: 被低估的优质成长股"""
    
    # ==================== 行业AI分析功能 ====================
    
    def perform_industry_ai_analysis(self):
        """执行行业AI分析 - 单线程避免崩溃"""
        try:
            # 检查是否有当前行业
            if not hasattr(self, 'current_industry_name') or not self.current_industry_name:
                self.on_industry_ai_analysis_error("请先选择一个行业进行分析")
                return
            
            # 防止重复分析
            if self.industry_ai_analysis_in_progress:
                return
            
            # 设置分析状态
            self.industry_ai_analysis_in_progress = True
            self.industry_ai_analyze_btn.setEnabled(False)
            self.industry_ai_analyze_btn.setText(t_gui("分析中"))
            self.industry_ai_status_label.setText(t_gui("🔄_AI正在分析_请稍候"))
            
            # 收集行业分析数据
            analysis_data = self.collect_industry_analysis_data(self.current_industry_name)
            
            # 生成行业AI分析提示词
            prompt = self.generate_industry_ai_analysis_prompt(analysis_data)
            
            # 使用单线程直接调用，避免PyQt5多线程崩溃
            QTimer.singleShot(100, lambda: self._perform_industry_ai_analysis_sync(prompt))
            
        except Exception as e:
            self.on_industry_ai_analysis_error(str(e))
    
    def _perform_industry_ai_analysis_sync(self, prompt):
        """同步执行行业AI分析，避免多线程问题"""
        analysis_type = "行业AI分析"
        
        try:
            # ===== 执行前检查 =====
            can_proceed, config = self._ai_analysis_before(analysis_type)
            if not can_proceed:
                self.on_industry_ai_analysis_error("执行前检查未通过")
                return
            
            # 执行分析
            result = self._call_llm_for_industry_analysis(prompt)
            
            # 检查是否是API Key错误信息（用户取消配置或没有输入API Key）
            if result and isinstance(result, str) and ("需要配置API Key" in result or "API Key configuration required" in result):
                print(f"[{analysis_type}] API Key配置取消，终止分析")
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_industry_ai_analysis_error(result)
                return
            
            # ===== 执行后处理 =====
            if result:
                self._ai_analysis_after(success=True, analysis_type=analysis_type)
                self.on_industry_ai_analysis_finished(result)
            else:
                self._ai_analysis_after(success=False, analysis_type=analysis_type)
                self.on_industry_ai_analysis_error("AI分析未返回结果")
                
        except Exception as e:
            self._ai_analysis_after(success=False, analysis_type=analysis_type)
            self.on_industry_ai_analysis_error(str(e))
    
    def _call_llm_for_industry_analysis(self, prompt):
        """同步调用LLM进行行业分析"""
        try:
            import sys
            import time
            from pathlib import Path
            
            # 检测当前系统语言
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            
            # 添加llm-api到路径（使用path_helper确保打包环境正确）
            from utils.path_helper import get_base_path
            base_path = get_base_path()  # 打包环境下返回EXE所在目录
            llm_api_path = base_path / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # ===== 新增：强制重新加载配置文件 =====
            import json
            config_path = llm_api_path / "config" / "user_settings.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"[行业AI分析] 已强制重新加载AI配置")
            else:
                config = {}
                print("[行业AI分析] 未找到配置文件，使用默认设置")
            
            default_provider = config.get('default_provider', 'OpenAI')
            print(f"[行业AI分析] 当前配置的LLM供应商: {default_provider}")
            
            # ===== 新增：试用模式检查（必须在API Key检查之前）=====
            is_trial_mode = False
            try:
                from utils.ai_usage_counter import get_ai_usage_count
                
                provider = config.get('default_provider', '').lower()
                api_key = config.get('SILICONFLOW_API_KEY', '').strip()
                current_count = get_ai_usage_count()
                
                # 检查是否符合试用条件：SiliconFlow + 无API Key + 计数<20
                if provider == 'siliconflow' and not api_key and current_count < 20:
                    print(f"[行业AI分析-试用模式] 符合试用条件（{current_count}/20次）")
                    print(f"[行业AI分析-试用模式] 使用预设试用配置")
                    
                    # 使用硬编码的试用配置
                    trial_config = {
                        "default_provider": "SiliconFlow",
                        "default_chat_model": "Qwen/Qwen3-8B",
                        "default_structured_model": "Qwen/Qwen3-8B",
                        "request_timeout": 600,
                        "agent_role": "不使用",
                        "SILICONFLOW_API_KEY": "sk-zbzzqzrcjyemnxlgcwiznrkuxrpdkrnpbneurezszujaqfjg",
                        "SILICONFLOW_BASE_URL": "https://api.siliconflow.cn/v1",
                        "dont_show_api_dialog": True
                    }
                    
                    # 使用试用配置
                    config = trial_config
                    is_trial_mode = True
                    default_provider = "SiliconFlow"
                    
                    print(f"[行业AI分析-试用模式] 配置已切换为试用模式，剩余 {20 - current_count} 次试用机会")
                else:
                    if provider == 'siliconflow' and not api_key and current_count >= 20:
                        print(f"[行业AI分析-试用模式] 试用次数已用完（{current_count}/20），请配置API Key")
                        
            except Exception as e:
                print(f"[行业AI分析] 试用检查出错: {e}")
            
            # ===== 新增：检查API Key（如果不是试用模式才检查）=====
            if not is_trial_mode:
                api_key_check_result = self._check_api_key_for_stock_analysis(config, default_provider, use_english, base_path)
                if api_key_check_result is not None:
                    # 返回错误信息，终止AI执行
                    return api_key_check_result
            else:
                print(f"[行业AI分析] 试用模式，跳过API Key检查")
            
            # 如果使用Ollama，先检查并启动服务
            if default_provider.lower() == 'ollama':
                print("[行业AI分析] 检测到Ollama供应商，正在检查服务状态...")
                
                # 导入Ollama工具
                try:
                    from ollama_utils import ensure_ollama_and_model
                    model_name = config.get('default_chat_model', 'gemma3:1b')
                    base_url = config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
                    
                    print(f"[行业AI分析] 正在启动Ollama服务并确保模型可用: {model_name}")
                    if not ensure_ollama_and_model(model_name, base_url):
                        return f"无法启动Ollama服务或模型不可用。\n\n 解决方案：\n1. 请确保Ollama已正确安装\n2. 手动运行命令: ollama serve\n3. 检查端口11434是否被占用\n4. 检查防火墙设置"
                    
                    print("[行业AI分析] Ollama服务检查完成，准备进行AI分析")
                    
                except ImportError as e:
                    print(f"[行业AI分析] 无法导入Ollama工具: {e}")
                    return f"Ollama工具模块导入失败: {e}"
            
            # 根据配置的提供商选择合适的LLM客户端
            if default_provider.lower() == 'ollama':
                # Ollama使用SimpleLLMClient
                try:
                    from simple_client import SimpleLLMClient as LLMClient
                    print("[行业AI分析] 使用SimpleLLMClient（Ollama专用）")
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                    client_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(client_module)
                    LLMClient = client_module.SimpleLLMClient
                    print("[行业AI分析] 使用绝对路径导入SimpleLLMClient")
            elif default_provider.lower() == 'deepseek':
                # DeepSeek使用简化客户端（避免LangChain依赖）
                try:
                    from simple_deepseek_client import SimpleDeepSeekClient as LLMClient
                    print("[行业AI分析] 使用SimpleDeepSeekClient（DeepSeek专用）")
                except ImportError:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("simple_deepseek_client", llm_api_path / "simple_deepseek_client.py")
                    client_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(client_module)
                    LLMClient = client_module.SimpleDeepSeekClient
                    print("[行业AI分析] 使用绝对路径导入SimpleDeepSeekClient")
            else:
                # 其他提供商使用完整的LLMClient
                try:
                    from client import LLMClient
                    print(f"[行业AI分析] 使用LLMClient（支持{default_provider}）")
                except ImportError:
                    # 如果无法导入，回退到SimpleLLMClient
                    try:
                        from simple_client import SimpleLLMClient as LLMClient
                        print("[行业AI分析] 回退到SimpleLLMClient")
                    except ImportError:
                        import importlib.util
                        spec = importlib.util.spec_from_file_location("simple_client", llm_api_path / "simple_client.py")
                        client_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(client_module)
                        LLMClient = client_module.SimpleLLMClient
                        print("[行业AI分析] 使用绝对路径导入SimpleLLMClient作为回退")
            
            # 创建LLM客户端（试用模式下传递临时配置）
            if is_trial_mode:
                print(f"[行业AI分析] 使用试用配置创建客户端")
                client = LLMClient(temp_config=config)
            else:
                client = LLMClient()
            
            start_time = time.time()
            
            # 检测当前系统语言并选择对应的指令
            from config.gui_i18n import get_system_language
            is_english = lambda: get_system_language() == 'en'
            use_english = is_english()
            
            # 根据系统语言选择指令
            if use_english:
                system_msg = "You are a professional financial analyst with expertise in industry analysis, technical analysis, and macroeconomic analysis. Please respond in English and provide professional industry investment advice."
                user_msg = "Please analyze the following industry data and provide investment advice:\n\n" + prompt
            else:
                system_msg = "你是一位专业的中文金融分析师，精通行业分析、技术分析和宏观经济分析。请用中文回复，提供专业的行业投资建议。"
                user_msg = "请用中文分析以下行业数据并提供投资建议：\n\n" + prompt
            
            # 检查客户端类型并适配调用方式
            client_class_name = client.__class__.__name__
            if client_class_name == 'SimpleLLMClient':
                # SimpleLLMClient不支持system_message，将其合并到用户消息中
                combined_message = f"{system_msg}\n\n{user_msg}"
                response = client.chat(message=combined_message)
                print(f"[行业AI分析] SimpleLLMClient调用成功，耗时 {time.time() - start_time:.1f}s")
            else:
                # LLMClient支持system_message
                response = client.chat(
                    message=user_msg,
                    system_message=system_msg
                )
                print(f"[行业AI分析] LLMClient调用成功，耗时 {time.time() - start_time:.1f}s")
            
            return response
            
        except Exception as e:
            return f"行业AI分析失败：{str(e)}\n\n请检查LLM配置是否正确。"
    
    def collect_industry_analysis_data(self, industry_name):
        """收集行业分析数据"""
        from datetime import datetime
        
        data = {
            'industry_name': industry_name,
            'tma_index': 0,
            'irsi_value': 0,
            'stock_count': 0,
            'market_msci': 0,
            'market_sentiment': '',
            'top_stocks': [],
            'analysis_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # 从分析结果中获取行业数据
            if hasattr(self, 'analysis_results_obj') and self.analysis_results_obj:
                industries = getattr(self.analysis_results_obj, 'industries', {})
                if industry_name in industries:
                    industry_info = industries[industry_name]
                    
                    # 获取TMA/IRSI指数
                    tma_data = industry_info.get('irsi', {})
                    if isinstance(tma_data, dict):
                        data['tma_index'] = tma_data.get('irsi', 0)
                        data['irsi_value'] = tma_data.get('irsi', 0)
                    else:
                        data['tma_index'] = float(tma_data) if tma_data else 0
                        data['irsi_value'] = float(tma_data) if tma_data else 0
                    
                    # 获取股票数量
                    data['stock_count'] = industry_info.get('stock_count', 0)
                    
                    # 获取行业内股票信息
                    stocks = industry_info.get('stocks', {})
                    if isinstance(stocks, dict):
                        # 按RTSI排序获取行业龙头股票，放宽筛选条件确保有足够数据传递给AI
                        stock_list = []
                        for code, stock_info in stocks.items():
                            rtsi_data = stock_info.get('rtsi', {})
                            rtsi_value = rtsi_data.get('rtsi', 0) if isinstance(rtsi_data, dict) else float(rtsi_data) if rtsi_data else 0
                            
                            # 行业AI分析优化：放宽筛选条件，优先基于RTSI分数筛选
                            # 指数行业：直接通过
                            # 其他行业：RTSI >= 30 或者是大盘股
                            if industry_name == "指数":
                                pass  # 指数股票直接通过
                            else:
                                # 放宽筛选：RTSI >= 30 或者是大盘股，确保有足够股票供AI分析
                                if rtsi_value < 30 and not self._is_large_cap_stock(code):
                                    continue
                            
                            # 收集有效的股票数据（RTSI > 0）
                            if rtsi_value > 0:
                                stock_list.append({
                                    'code': code,
                                    'name': stock_info.get('name', code),
                                    'rtsi': rtsi_value
                                })
                        
                        # 排序并取前8只股票（增加数量确保AI有足够分析对象）
                        stock_list.sort(key=lambda x: x['rtsi'], reverse=True)
                        data['top_stocks'] = stock_list[:8]
                        
                        # 添加调试日志：确认传递给AI的股票数量
                        print(f"[行业AI数据收集] 行业: {industry_name}")
                        print(f"[行业AI数据收集] 原始股票总数: {len(stocks)}")
                        print(f"[行业AI数据收集] 筛选后股票数量: {len(stock_list)}")
                        print(f"[行业AI数据收集] 传递给AI的股票数量: {len(data['top_stocks'])}")
                        for i, stock in enumerate(data['top_stocks'][:5]):  # 只显示前5只
                            print(f"  {i+1}. {stock['code']} {stock['name']}: RTSI {stock['rtsi']:.2f}")
                        if len(data['top_stocks']) > 5:
                            print(f"  ... 还有{len(data['top_stocks']) - 5}只股票")
                        
                        # 数据质量验证
                        if len(data['top_stocks']) == 0:
                            print(f" [行业AI警告] 没有股票数据传递给LLM，AI可能无法进行具体股票分析")
                        elif len(data['top_stocks']) < 3:
                            print(f" [行业AI警告] 传递给LLM的股票数量较少({len(data['top_stocks'])}只)，可能影响分析质量")
                
                # 获取市场数据
                market = getattr(self.analysis_results_obj, 'market', {})
                if market:
                    data['market_msci'] = market.get('current_msci', 0)
                    
                    # 计算市场情绪
                    msci_value = data['market_msci']
                    if msci_value >= 70:
                        data['market_sentiment'] = t_gui('extremely_optimistic')
                    elif msci_value >= 60:
                        data['market_sentiment'] = t_gui('optimistic')
                    elif msci_value >= 40:
                        data['market_sentiment'] = t_gui('neutral')
                    elif msci_value >= 30:
                        data['market_sentiment'] = t_gui('pessimistic')
                    else:
                        data['market_sentiment'] = t_gui('extremely_pessimistic')
            
        except Exception as e:
            print(f"收集行业分析数据失败: {str(e)}")
        
        return data
    
    def generate_industry_ai_analysis_prompt(self, analysis_data):
        """生成行业AI分析提示词 - 专门针对行业分析，指数分析特别处理"""
        
        # 检测当前界面语言
        from config.i18n import is_english
        use_english = is_english()
        
        # 检测是否为指数分析
        industry_name = analysis_data['industry_name']
        is_index_analysis = industry_name == "指数"
        
        # 获取当前市场类型 - 优先从主界面检测结果获取
        current_market = self._get_reliable_market_info()
        market_names = {'cn': '中国A股市场', 'hk': '香港股票市场', 'us': '美国股票市场'}
        market_name = market_names.get(current_market, '股票市场')
        
        # 调试信息：确保市场名称正确传递给LLM
        print(f"[市场检测] 行业分析AI - 检测到市场: {current_market}, 市场名称: {market_name}")
        
        # 构建市场特色说明
        if current_market == 'cn':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：中国A股市场
▪ 股票代码格式：6位数字（如：000001 平安银行，600036 招商银行）
▪ 推荐股票要求：必须使用真实存在的A股股票代码和名称
▪ 价格单位：人民币元
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: China A-Share Market
▪ Stock Code Format: 6-digit numbers (e.g., 000001 Ping An Bank, 600036 China Merchants Bank)
▪ Stock Recommendation Requirement: Must use real existing A-share stock codes and names
▪ Currency Unit: Chinese Yuan (RMB)
"""
        elif current_market == 'hk':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：香港股票市场（港股）
▪ 股票代码格式：5位数字（如：00700 腾讯控股，00388 香港交易所）
▪ 推荐股票要求：必须使用真实存在的港股股票代码和名称
▪ 价格单位：港币元
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: Hong Kong Stock Market (HKEX)
▪ Stock Code Format: 5-digit numbers (e.g., 00700 Tencent Holdings, 00388 HKEX)
▪ Stock Recommendation Requirement: Must use real existing Hong Kong stock codes and names
▪ Currency Unit: Hong Kong Dollar (HKD)
"""
        elif current_market == 'us':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：美国股票市场（美股）
▪ 股票代码格式：英文字母代码（如：AAPL 苹果公司，MSFT 微软公司）
▪ 推荐股票要求：必须使用真实存在的美股股票代码和名称
▪ 价格单位：美元
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: US Stock Market (US Market)
▪ Stock Code Format: Letter codes (e.g., AAPL Apple Inc., MSFT Microsoft Corp.)
▪ Stock Recommendation Requirement: Must use real existing US stock codes and names
▪ Currency Unit: US Dollar (USD)
"""
        else:
            market_context_zh = ""
            market_context_en = ""
        
        industry_name = analysis_data['industry_name']
        tma_index = analysis_data['tma_index']
        stock_count = analysis_data['stock_count']
        market_msci = analysis_data['market_msci']
        market_sentiment = analysis_data['market_sentiment']
        top_stocks = analysis_data['top_stocks']
        analysis_time = analysis_data['analysis_time']
        
        # 根据语言生成不同的提示词
        if use_english:
            # 构建顶级股票信息 - 英文版（明确标识为行业龙头股票）
            top_stocks_info = ""
            if top_stocks:
                top_stocks_info = f"\n===== Industry Leading Stocks ({len(top_stocks)} stocks, sorted by RTSI) =====\n"
                for i, stock in enumerate(top_stocks, 1):
                    top_stocks_info += f"{i}. {stock['code']} {stock['name']} - RTSI: {stock['rtsi']:.2f}\n"
                top_stocks_info += f"\n【Data Integrity Confirmation】\n"
                top_stocks_info += f"▪ Actual number of leading stocks passed: {len(top_stocks)} stocks\n"
                top_stocks_info += f"▪ Total stocks requiring individual analysis: {len(top_stocks)} stocks\n"
                if len(top_stocks) == 0:
                    top_stocks_info += f"▪  Warning: No qualified stock data available, provide industry analysis based on this situation\n"
            else:
                top_stocks_info = f"\n===== Industry Leading Stocks (0 stocks) =====\n"
                top_stocks_info += f"▪  No analyzable leading stock data available for current industry\n"
                top_stocks_info += f"▪ AI should focus on overall industry trends without specific stock recommendations\n"
            
            # 判断TMA强度级别 - 英文版
            if tma_index > 20:
                tma_level = "Strong Uptrend"
                investment_tendency = "Active Allocation"
            elif tma_index > 5:
                tma_level = "Moderately Strong"
                investment_tendency = "Moderate Attention"
            elif tma_index > -5:
                tma_level = "Sideways Consolidation"
                investment_tendency = "Cautious Watch"
            else:
                tma_level = "Weak Decline"
                investment_tendency = "Risk Avoidance"
            
            prompt = f"""
【Industry AI Intelligent Analysis】

🚨【MANDATORY CONSTRAINTS - Violation will result in UNQUALIFIED report】🚨

【1. Stock Analysis Mandatory Requirements (Highest Priority)】
▪ 【MANDATORY COMPLETION】Must individually analyze every stock listed in "Industry Leading Stocks" section below
▪ 【MANDATORY FORMAT】Each stock must use format: "Stock_Code Stock_Name: RTSI XX.XX → [Rating Analysis] → [Investment Advice]"
▪ 【COMPLETENESS VERIFICATION】Report must confirm at end: analyzed all {len(top_stocks) if top_stocks else 0} leading stocks
▪ 【ABSOLUTE PROHIBITION】No use of "hypothetical XXX company" or "key companies may include" vague statements
▪ 【DATA CONSTRAINT】All stock codes, names, RTSI ratings must strictly follow data below, no fabrication

【2. Content Focus Requirements (Mandatory)】
▪ 【MAIN CONTENT】80% content must focus on specific stock investment value and operational advice
▪ 【THEORY LIMIT】Macroeconomic theoretical analysis must not exceed 20%
▪ 【PRACTICAL ORIENTED】Every analysis point must correspond to specific investment operations

Analysis Target: {industry_name}
Analysis Time: {analysis_time}
{market_context_en}
===== Core Data =====
• Industry TMA Index: {tma_index:.2f} ({tma_level})
• Number of Industry Stocks: {stock_count}
• Market MSCI Index: {market_msci:.2f}
• Market Sentiment: {market_sentiment}
• Preliminary Investment Recommendation: {investment_tendency}

{top_stocks_info}

===== Analysis Requirements =====
Please focus on analyzing the overall investment value and development trends of the {industry_name} industry:

1. 【In-depth Industry Analysis】(Key Focus)
   - Analyze current development stage and trend characteristics of the {industry_name} industry
   - Evaluate industry fundamentals, policy support, and market environment
   - Analyze overall competitive landscape and development prospects of major companies in the industry
   - Identify key driving factors and risk points affecting industry development

2. 【Industry Trend Analysis】(New Key Focus)
   - Analyze long-term development trends of the {industry_name} industry based on historical data
   - Evaluate the industry's life cycle stage (introduction, growth, maturity, decline)
   - Analyze factors affecting industry trends including macroeconomic, policy, and technological innovation
   - Predict the industry's development trajectory and key turning points for the next 1-3 years
   - Compare correlation and independence between industry trends and overall market trends

3. 【Industry Rotation Analysis】(New Key Focus)
   - Analyze historical performance and cyclical characteristics of the {industry_name} industry in market rotation
   - Judge the industry's position in the rotation cycle based on current TMA Index {tma_index:.2f}
   - Evaluate fund flow trends and institutional allocation preference changes in the industry
   - Identify catalysts and time windows that may trigger industry rotation
   - Analyze rotation relationships and substitution effects with other industries

4. 【Industry Investment Logic Analysis】(Key Focus)
   - Analyze industry relative strength based on TMA Index {tma_index:.2f}
   - Evaluate industry valuation levels and investment cost-effectiveness
   - Analyze allocation value of the industry in current market environment
   - Judge development trends of the industry for the next 3-6 months

5. 【Industry Risk Assessment】(Key Focus)
   - Identify main risk factors facing the {industry_name} industry
   - Analyze industry volatility and cyclical characteristics
   - Evaluate impact of policy changes, market competition on the industry
   - Provide risk control recommendations for industry investment

6. 【Industry Allocation Recommendations】(Key Focus)
   - Provide allocation recommendations and timing judgments based on industry analysis
   - Analyze allocation weight of the industry in investment portfolios
   - Evaluate possibility and timing of industry rotation
   - Provide strategic recommendations for industry investment

Note: Focus on overall investment value and development trends of the {industry_name} industry to provide professional analysis support for industry allocation decisions.
Please provide investment recommendations and risk alerts based on industry fundamentals.

**IMPORTANT: Please respond in English only.**
"""
        else:
            # 构建顶级股票信息 - 中文版（明确标识为行业龙头股票）
            top_stocks_info = ""
            if top_stocks:
                top_stocks_info = f"\n===== 行业龙头股票（{len(top_stocks)}只，按RTSI排序） =====\n"
                for i, stock in enumerate(top_stocks, 1):
                    top_stocks_info += f"{i}. {stock['code']} {stock['name']} - RTSI: {stock['rtsi']:.2f}分\n"
                top_stocks_info += f"\n【数据完整性确认】\n"
                top_stocks_info += f"▪ 实际传递的龙头股票数量: {len(top_stocks)}只\n"
                top_stocks_info += f"▪ 需要逐一分析的股票总数: {len(top_stocks)}只\n"
                if len(top_stocks) == 0:
                    top_stocks_info += f"▪  警告：当前没有符合条件的股票数据，请基于此情况给出相应的行业分析\n"
            else:
                top_stocks_info = f"\n===== 行业龙头股票（0只） =====\n"
                top_stocks_info += f"▪  当前行业没有可分析的龙头股票数据\n"
                top_stocks_info += f"▪ AI应重点分析行业整体趋势，无需进行具体股票推荐\n"
            
            # 判断TMA强度级别 - 中文版
            if tma_index > 20:
                tma_level = "强势上涨"
                investment_tendency = "积极配置"
            elif tma_index > 5:
                tma_level = "中性偏强"
                investment_tendency = "适度关注"
            elif tma_index > -5:
                tma_level = "震荡整理"
                investment_tendency = "谨慎观察"
            else:
                tma_level = "弱势下跌"
                investment_tendency = "规避风险"
            
            prompt = f"""
{t_gui("【行业AI智能分析】")}

🚨【强制执行约束条件 - 违反将被认定为不合格报告】🚨

【1. 股票分析强制要求（最高优先级）】
▪ 【强制完成】必须逐一分析下方"行业龙头股票"部分列出的每一只股票
▪ 【强制格式】每只股票必须使用格式："股票代码 股票名称: RTSI XX.XX分 → [评分解读] → [投资建议]"
▪ 【完整性验证】报告结尾必须确认已分析完所有{len(top_stocks) if top_stocks else 0}只龙头股票
▪ 【绝对禁止】不得使用"假设选择XXX企业"、"重点企业可能包括"等虚构表述
▪ 【数据约束】所有股票代码、名称、RTSI评分必须严格按照下方数据，不得编造

【2. 内容聚焦要求（强制执行）】
▪ 【主要内容】80%内容必须围绕具体股票的投资价值和操作建议
▪ 【理论限制】宏观理论分析不得超过20%
▪ 【实用导向】每个分析点必须对应具体投资操作

{t_gui("分析对象")}：{industry_name}
{t_gui("分析时间：")} {analysis_time}
{market_context_zh}
===== 核心数据 =====
• 行业TMA指数：{tma_index:.2f} ({tma_level})
• 行业股票数量：{stock_count}只
• 大盘MSCI指数：{market_msci:.2f}
• 市场情绪：{market_sentiment}
• 初步投资建议：{investment_tendency}

【数据完整性确认】
▪ 市场MSCI指数: {market_msci:.2f} {f" (数据异常，可能存在传递问题)" if market_msci == 0 else " (数据正常)"}
▪ 行业股票数量: {stock_count}只 {f" (无可分析股票)" if stock_count == 0 else " (数据充足)"}
▪ 龙头股票数量: {len(top_stocks) if top_stocks else 0}只 {f" (缺乏龙头股票数据)" if not top_stocks or len(top_stocks) == 0 else " (数据充足)"}

{top_stocks_info}

===== 分析要求 =====
请重点分析{industry_name}行业的整体投资价值和发展趋势：

1. 【行业深度分析】（重点）
   - 深入分析{industry_name}行业当前发展阶段和趋势特征
   - 评估行业的基本面状况、政策支持和市场环境
   - 分析行业内主要企业的整体竞争格局和发展前景
   - 识别影响行业发展的关键驱动因素和风险点

2. 【行业趋势分析】（新增重点）
   - 基于历史数据分析{industry_name}行业的长期发展趋势
   - 评估行业所处的生命周期阶段（导入期、成长期、成熟期、衰退期）
   - 分析影响行业趋势的宏观经济、政策导向、技术创新等因素
   - 预测行业未来1-3年的发展轨迹和关键转折点
   - 对比行业趋势与大盘走势的相关性和独立性

3. 【行业轮动分析】（新增重点）
   - 分析{industry_name}行业在市场轮动中的历史表现和周期特征
   - 基于当前TMA指数{tma_index:.2f}判断行业在轮动周期中的位置
   - 评估行业资金流入流出趋势和机构配置偏好变化
   - 识别可能引发行业轮动的催化因素和时间窗口
   - 分析与其他行业的轮动关系和替代效应

4. 【行业投资逻辑分析】（重点）
   - 基于TMA指数{tma_index:.2f}分析行业相对强弱
   - 评估行业估值水平和投资性价比
   - 分析行业在当前市场环境下的配置价值
   - 研判行业未来3-6个月的发展趋势

5. 【行业风险评估】（重点）
   - 识别{industry_name}行业面临的主要风险因素
   - 分析行业波动性和周期性特征
   - 评估政策变化、市场竞争等对行业的影响
   - 提供行业投资的风险控制建议

6. 【国际对标行业比较分析】（新增重点）
   - 对比{industry_name}行业与海外同类行业的发展水平和竞争力
   - 分析全球行业发展趋势对国内行业的影响和启示
   - 评估国内行业在全球价值链中的地位和发展空间
   - 识别国际先进经验和技术对行业的推动作用
   - 分析汇率、贸易政策等国际因素对行业的影响

7. 【行业配置建议】（重点）
   - 基于行业分析给出配置建议和时机判断
   - 分析行业在投资组合中的配置权重
   - 评估行业轮动的可能性和时机
   - 提供行业投资的策略性建议
   - 结合国际对标分析，提供全球视野下的配置建议

===== 国际对标分析要求 =====
请特别关注以下国际对标维度：

1. **全球行业地位对比**：
   - 对比国内外同行业的市场规模、技术水平、盈利能力
   - 分析国内行业的全球竞争优势和劣势
   - 评估国内行业在全球供应链中的地位

2. **国际发展趋势借鉴**：
   - 分析海外同行业的发展模式和成功经验
   - 识别可借鉴的技术创新和商业模式
   - 评估国际趋势对国内行业的指导意义

3. **跨境投资机会**：
   - 分析相关海外资产的投资价值
   - 评估汇率变动对行业投资的影响
   - 识别全球化背景下的投资机会和风险

注：重点关注{industry_name}行业的整体投资价值和发展趋势，结合国际视野为行业配置决策提供专业分析支持。
请提供基于行业基本面和国际对标的投资建议和风险提示。

🔥【最终强制检查 - 报告提交前必须完成以下所有项目】🔥

【强制性股票分析检查清单】
每只股票必须包含以下四个要素，缺一不可：
 股票代码（必须与上方数据完全一致）
 股票名称（必须与上方数据完全一致） 
 RTSI评分解读（必须引用上方具体数值）
 具体投资建议（买入/持有/观望，含仓位建议）

【报告结构强制要求】
 必须有专门的"行业龙头股票分析"章节
 逐一分析上方列出的所有{len(top_stocks) if top_stocks else 0}只股票
 每只股票使用统一格式："股票代码 股票名称: RTSI XX.XX分 → [评分解读] → [投资建议]"
 报告末尾确认："已完成所有{len(top_stocks) if top_stocks else 0}只龙头股票的分析"

【内容质量强制标准】
 具体股票投资建议占比≥80%，理论分析≤20%
 每个投资建议必须包含具体仓位或配置权重
 禁止使用任何虚构、假设或泛化表述
 所有数据引用必须与上方提供的数据完全一致

【不合格判定标准】
如出现以下任一情况，报告将被认定为不合格：
[ERROR] 遗漏任何一只上方列出的龙头股票分析
[ERROR] 使用虚构的股票代码或公司名称
[ERROR] 编造不存在的RTSI评分数据
[ERROR] 过多理论化内容（>20%），缺乏具体投资指导
[ERROR] 使用"假设"、"可能包括"等模糊表述替代具体分析

**重要：请用中文回复所有内容。**
"""
        
        # 如果是指数分析，生成专用的指数分析提示词
        if is_index_analysis:
            return self._generate_index_analysis_prompt(analysis_data, use_english, current_market, market_name)
        
        return prompt.strip()
    
    def _generate_index_analysis_prompt(self, analysis_data, use_english, current_market, market_name):
        """生成指数专用的AI分析提示词"""
        
        # 构建市场特色说明
        if current_market == 'cn':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：中国A股市场指数
▪ 指数代码格式：上证指数(000001)、深证成指(399001)、创业板指(399006)等
▪ 分析重点：指数趋势分析和相互关系研究
▪ 价格单位：指数点位
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: China A-Share Market Indices
▪ Index Code Format: Shanghai Composite (000001), Shenzhen Component (399001), ChiNext (399006), etc.
▪ Analysis Focus: Index trend analysis and inter-relationship study
▪ Unit: Index Points
"""
        elif current_market == 'hk':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：香港股票市场指数
▪ 指数代码格式：恒生指数(HSI)、国企指数(HSCEI)、恒生科技指数(HSTECH)等
▪ 分析重点：指数趋势分析和相互关系研究
▪ 价格单位：指数点位
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: Hong Kong Stock Market Indices
▪ Index Code Format: Hang Seng Index (HSI), H-Shares Index (HSCEI), Hang Seng TECH Index (HSTECH), etc.
▪ Analysis Focus: Index trend analysis and inter-relationship study
▪ Unit: Index Points
"""
        elif current_market == 'us':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：美国股票市场指数
▪ 指数代码格式：标普500(SPX)、纳斯达克(IXIC)、道琼斯(DJI)等
▪ 分析重点：指数趋势分析和相互关系研究
▪ 价格单位：指数点位
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: US Stock Market Indices
▪ Index Code Format: S&P 500 (SPX), NASDAQ (IXIC), Dow Jones (DJI), etc.
▪ Analysis Focus: Index trend analysis and inter-relationship study
▪ Unit: Index Points
"""
        else:
            market_context_zh = ""
            market_context_en = ""
        
        tma_index = analysis_data['tma_index']
        stock_count = analysis_data['stock_count']
        market_msci = analysis_data['market_msci']
        market_sentiment = analysis_data['market_sentiment']
        top_stocks = analysis_data['top_stocks']  # 对于指数，这实际上是各个指数
        analysis_time = analysis_data['analysis_time']
        
        # 根据语言生成不同的提示词
        if use_english:
            # 构建指数信息 - 英文版
            indices_info = ""
            if top_stocks:
                indices_info = "\nMajor indices performance (sorted by RTSI):\n"
                for i, index in enumerate(top_stocks, 1):
                    indices_info += f"{i}. {index['name']}({index['code']}) - RTSI: {index['rtsi']:.2f}\n"
            
            # 判断TMA强度级别 - 英文版
            if tma_index > 20:
                tma_level = "Strong Uptrend"
                investment_tendency = "Active Allocation"
            elif tma_index > 5:
                tma_level = "Moderately Strong"
                investment_tendency = "Moderate Attention"
            elif tma_index > -5:
                tma_level = "Sideways Consolidation"
                investment_tendency = "Cautious Watch"
            else:
                tma_level = "Weak Decline"
                investment_tendency = "Risk Avoidance"
            
            prompt = f"""
【Index AI Intelligent Analysis】

Analysis Target: Market Indices
Analysis Time: {analysis_time}
{market_context_en}
===== Core Data =====
• Index Cluster TMA: {tma_index:.2f} ({tma_level})
• Number of Indices: {stock_count}
• Market MSCI Index: {market_msci:.2f}
• Market Sentiment: {market_sentiment}
• Preliminary Investment Recommendation: {investment_tendency}

{indices_info}

===== Analysis Requirements =====
Please focus on analyzing index trends and their inter-relationships:

1. 【Index Trend Analysis】(Key Focus)
   - Analyze current trend characteristics and strength of each major index
   - Compare performance differences between indices and identify divergences
   - Evaluate technical patterns and momentum indicators for each index
   - Assess sustainability of current index trends

2. 【Inter-Index Relationship Analysis】(Key Focus)
   - Analyze correlation and divergence patterns between different indices
   - Identify lead-lag relationships among indices
   - Evaluate rotation patterns between different market segments
   - Assess risk-on vs risk-off sentiment through index performance

3. 【Market Structure Analysis】(Key Focus)
   - Analyze breadth and depth of market movements through index behavior
   - Evaluate sector rotation signals from index performance differences
   - Assess market leadership changes through index relative performance
   - Identify potential market regime changes

4. 【Strategic Implications】(Key Focus)
   - Provide strategic insights based on index trend analysis
   - Suggest portfolio allocation adjustments based on index signals
   - Identify timing opportunities from index divergences
   - Assess market risk levels through index behavior patterns

Note: Focus on index trend analysis and inter-index relationships to provide strategic market insights.
Please provide professional analysis based on index technical patterns and relative performance.

**IMPORTANT: Please respond in Chinese only.**
"""
        else:
            # 构建指数信息 - 中文版
            indices_info = ""
            if top_stocks:
                indices_info = "\n主要指数表现（按RTSI排序）：\n"
                for i, index in enumerate(top_stocks, 1):
                    indices_info += f"{i}. {index['name']}({index['code']}) - RTSI: {index['rtsi']:.2f}\n"
            
            # 判断TMA强度级别 - 中文版
            if tma_index > 20:
                tma_level = "强势上涨"
                investment_tendency = "积极配置"
            elif tma_index > 5:
                tma_level = "中性偏强"
                investment_tendency = "适度关注"
            elif tma_index > -5:
                tma_level = "震荡整理"
                investment_tendency = "谨慎观察"
            else:
                tma_level = "弱势下跌"
                investment_tendency = "规避风险"
            
            prompt = f"""
【指数AI智能分析】

分析对象：市场指数群组
分析时间：{analysis_time}
{market_context_zh}
===== 核心数据 =====
• 指数群组TMA：{tma_index:.2f} ({tma_level})
• 指数数量：{stock_count}个
• 大盘MSCI指数：{market_msci:.2f}
• 市场情绪：{market_sentiment}
• 初步投资建议：{investment_tendency}

{indices_info}

===== 分析要求 =====
请重点分析各指数的趋势特征和相互走势差异：

1. 【指数趋势分析】（重点）
   - 深入分析各主要指数的当前趋势特征和强弱程度
   - 对比各指数表现差异，识别背离现象和轮动信号
   - 评估各指数的技术形态和动能指标表现
   - 研判当前指数趋势的可持续性和转折可能

2. 【指数相互关系分析】（重点）
   - 分析不同指数间的相关性和背离规律
   - 识别指数间的领先滞后关系和传导机制
   - 评估不同市场板块间的轮动模式和资金流向
   - 通过指数表现判断市场风险偏好变化

3. 【市场结构分析】（重点）
   - 通过指数行为分析市场广度和深度特征
   - 评估指数表现差异反映的板块轮动信号
   - 识别市场领导力变化和风格切换特征
   - 判断潜在的市场制度性变化信号

4. 【策略性启示】（重点）
   - 基于指数趋势分析提供策略性见解
   - 根据指数信号建议组合配置调整方向
   - 识别指数背离中的择时机会
   - 通过指数行为评估市场风险水平

注：重点关注指数趋势分析和指数间相互关系，为市场策略决策提供专业洞察。
请基于指数技术形态和相对表现提供专业分析。

**重要：请用中文回复所有内容。**
"""
        
        return prompt.strip()
    
    def set_html_content(self, widget, html_content):
        """通用HTML设置方法 - 兼容QWebEngineView和QTextEdit"""
        try:
            if hasattr(widget, 'setHtml'):
                # QTextEdit方式
                widget.setHtml(html_content)
            elif hasattr(widget, 'load'):
                # QWebEngineView方式
                from PyQt5.QtCore import QUrl
                import tempfile
                import os
                
                # 创建临时HTML文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_file = f.name
                
                # 加载临时文件
                widget.load(QUrl.fromLocalFile(os.path.abspath(temp_file)))
            else:
                print(f"[ERROR] 无法识别组件类型: {type(widget)}")
        except Exception as e:
            print(f"[ERROR] 设置HTML内容失败: {e}")
    
    def set_industry_ai_html(self, html_content):
        """设置行业AI分析HTML内容"""
        self.set_html_content(self.industry_ai_result_browser, html_content)
    
    def set_stock_ai_html(self, html_content):
        """设置个股AI分析HTML内容"""
        self.set_html_content(self.stock_ai_result_browser, html_content)
    
    def set_market_html(self, html_content):
        """设置市场情绪分析HTML内容"""
        self.set_html_content(self.market_text, html_content)
    

    
    def set_industry_detail_html(self, html_content):
        """设置行业详细分析HTML内容"""
        self.set_html_content(self.industry_detail_text, html_content)
    
    def set_stock_detail_html(self, html_content):
        """设置个股详细分析HTML内容"""
        self.set_html_content(self.stock_detail_text, html_content)
    
    def format_industry_ai_analysis_result(self, result, industry_name):
        """格式化行业AI分析结果为HTML"""
        try:
            from datetime import datetime
            
            # 获取当前时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            

            
            # 格式化AI分析文本
            formatted_text = self.format_ai_text_to_html(result)
            
            html = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{ 
                        font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif, 'Segoe UI', Tahoma, sans-serif;
                        line-height: 1.6; 
                        color: #333;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    
                    .container {{
                        max-width: 1000px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 15px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }}
                    
                    .header {{ 
                        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                        color: white;
                        padding: 30px;
                        text-align: center; 
                    }}
                    
                    .header h1 {{
                        font-size: 2.2em;
                        margin-bottom: 10px;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                        color: white;
                    }}
                    
                    .header .subtitle {{
                        font-size: 1.1em;
                        opacity: 0.9;
                        margin-bottom: 5px;
                        color: white;
                    }}
                    
                    .section {{
                        padding: 25px;
                        border-bottom: 1px solid #eee;
                    }}
                    
                    .section:last-child {{
                        border-bottom: none;
                    }}
                    
                    .section h2 {{
                        color: #2c3e50;
                        margin-bottom: 20px;
                        font-size: 1.5em;
                        border-left: 4px solid #3498db;
                        padding-left: 15px;
                    }}
                    
                    .section h3 {{
                        color: #2c3e50;
                        margin-bottom: 15px;
                        font-size: 1.3em;
                    }}
                    
                    .industry-info {{ 
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px; 
                        border-left: 4px solid #3498db;
                        margin-bottom: 20px; 
                    }}
                    
                    .analysis-content {{
                        background: white;
                        padding: 25px;
                        border-radius: 10px;
                        margin-bottom: 20px;
                    }}
                    
                    .metrics-grid {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 15px;
                        margin-bottom: 20px;
                    }}
                    
                    .metric-card {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        border-left: 4px solid #3498db;
                    }}
                    
                    .metric-label {{
                        font-size: 0.9em;
                        color: #666;
                        margin-bottom: 5px;
                    }}
                    
                    .metric-value {{
                        font-size: 1.3em;
                        font-weight: bold;
                        color: #2c3e50;
                    }}
                    
                    .recommendation {{ 
                        background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
                        padding: 20px;
                        border-radius: 10px;
                        border: 2px solid #27ae60;
                        margin: 20px 0;
                    }}
                    
                    .recommendation.sell {{
                        background: linear-gradient(135deg, #ffeaea 0%, #fff0f0 100%);
                        border-color: #e74c3c;
                    }}
                    
                    .recommendation.hold {{
                        background: linear-gradient(135deg, #fff8e1 0%, #fffbf0 100%);
                        border-color: #f39c12;
                    }}
                    
                    .risk-warning {{ 
                        background: linear-gradient(135deg, #ffeaea 0%, #fff0f0 100%);
                        border: 2px solid #e74c3c;
                        border-radius: 10px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    
                    .highlight {{
                        background-color: #fff3cd;
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-weight: bold;
                    }}
                    
                    strong {{
                        color: #e74c3c;
                        font-weight: bold;
                    }}
                    
                    .price-up {{
                        color: #dc3545 !important;
                        font-weight: bold;
                    }}
                    
                    .price-down {{
                        color: #28a745 !important;
                        font-weight: bold;
                    }}
                    
                    .price-neutral {{
                        color: #6c757d !important;
                        font-weight: bold;
                    }}
                    
                    .insights {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        margin-top: 15px;
                    }}
                    
                    .insights ul {{
                        list-style-type: none;
                        padding-left: 0;
                    }}
                    
                    .insights li {{
                        padding: 5px 0;
                        padding-left: 20px;
                        position: relative;
                    }}
                    
                    .insights li:before {{
                        content: "";
                        position: absolute;
                        left: 0;
                    }}
                    
                    .footer {{
                        background: #2c3e50;
                        color: white;
                        text-align: center;
                        padding: 20px;
                        font-size: 0.9em;
                    }}
                    
                    .error {{
                        background: #ffeaea;
                        color: #e74c3c;
                        padding: 20px;
                        border-radius: 8px;
                        border: 1px solid #e74c3c;
                        margin: 20px 0;
                        text-align: center;
                    }}
                    
                    @media (max-width: 768px) {{
                        .container {{
                            margin: 10px;
                            border-radius: 10px;
                        }}
                        
                        .header {{
                            padding: 20px;
                        }}
                        
                        .header h1 {{
                            font-size: 1.8em;
                        }}
                        
                        .section {{
                            padding: 15px;
                        }}
                        
                        .metrics-grid {{
                            grid-template-columns: 1fr;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                <div class="header">
                        <h1> {industry_name} 行业AI智能分析报告</h1>
                        <div class="subtitle">分析时间：{current_time}</div>
                        <div class="subtitle" style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">作者：267278466@qq.com</div>
                </div>
                
                    <div class="section">
                <div class="industry-info">
                            <h3> 分析说明</h3>
                            <p>本报告基于行业TMA指数、市场情绪和优质股票数据，运用AI技术进行深度分析，为您提供专业的行业投资建议。</p>
                </div>
                
                <div class="analysis-content">
                    {formatted_text}
                        </div>
                </div>
                
                <div class="footer">
                        <p><strong>免责声明：</strong>本分析报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
                        <p>报告生成时间：{current_time} | AI股票大师系统</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            return f"<p style='color: #dc3545;'>格式化AI分析结果失败: {str(e)}</p>"
    
    def format_ai_text_to_html(self, text):
        """将AI分析文本格式化为HTML"""
        try:
            # 将换行符转换为HTML换行
            formatted = text.replace('\n', '<br/>')
            
            # 格式化标题（以【】包围的内容）
            import re
            formatted = re.sub(r'【([^】]+)】', r'<h2>📌 \1</h2>', formatted)
            
            # 格式化子标题（以数字开头的行）
            formatted = re.sub(r'^(\d+\.\s*【[^】]+】)', r'<h3>\1</h3>', formatted, flags=re.MULTILINE)
            
            # 格式化列表项（以•或-开头的行）
            formatted = re.sub(r'^[•\-]\s*(.+)$', r'<li>\1</li>', formatted, flags=re.MULTILINE)
            
            # 包装连续的li标签为ul
            formatted = re.sub(r'(<li>.*?</li>)(?:\s*<br/>)*', r'\1', formatted, flags=re.DOTALL)
            formatted = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', formatted, flags=re.DOTALL)
            
            # 突出显示关键词
            keywords = ['增持', '持有', '减持', '买入', '卖出', '建议', '风险', '机会', '强势', '弱势', '上涨', '下跌']
            for keyword in keywords:
                formatted = formatted.replace(keyword, f"<span class='highlight'><strong>{keyword}</strong></span>")
            
            # 格式化投资建议
            formatted = re.sub(r'(投资建议：[^<]+)', r'<div class="recommendation">\1</div>', formatted)
            formatted = re.sub(r'(风险提示：[^<]+)', r'<div class="risk-warning">\1</div>', formatted)
            
            return formatted
            
        except Exception:
            return f"<pre>{text}</pre>"
    
    def on_industry_ai_analysis_finished(self, result):
        """行业AI分析完成回调"""
        try:
            # 缓存结果（原始文本）
            if hasattr(self, 'current_industry_name') and self.current_industry_name:
                self.industry_ai_cache[self.current_industry_name] = result
            
            # 格式化并显示HTML结果
            html_result = self.format_industry_ai_analysis_result(result, self.current_industry_name)
            self.set_industry_ai_html(html_result)
            self.industry_ai_stacked_widget.setCurrentIndex(1)  # 切换到结果页面
            
            # 重置按钮状态
            self.industry_ai_analysis_in_progress = False
            self.industry_ai_analyze_btn.setEnabled(True)
            self.industry_ai_analyze_btn.setText(t_gui("开始AI分析"))
            self.industry_ai_status_label.setText(t_gui("分析完成"))
            
            print(f"[行业AI分析] {self.current_industry_name} 分析完成")
            
        except Exception as e:
            self.on_industry_ai_analysis_error(f"处理分析结果失败：{str(e)}")
    
    def on_industry_ai_analysis_error(self, error_message):
        """行业AI分析错误回调"""
        error_html = f"""
        <div style="text-align: center; color: #dc3545; margin-top: 50px;">
            <h3> 行业AI分析失败</h3>
            <p style="margin: 20px 0; font-size: 14px; color: #666;">{error_message}</p>
            <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; margin: 20px; text-align: left;">
                <h4 style="color: #721c24; margin-top: 0;">请检查以下项目：</h4>
                <ul style="color: #721c24;">
                    <li>LLM配置是否正确</li>
                    <li>网络连接是否正常</li>
                    <li>API密钥是否有效</li>
                    <li>是否已选择有效的行业</li>
                </ul>
                <p style="color: #721c24; margin-bottom: 0;"><strong>建议：</strong>您可以尝试重新分析或检查配置后再试。</p>
            </div>
        </div>
        """
        
        # 显示错误并重置状态
        self.set_industry_ai_html(error_html)
        self.industry_ai_stacked_widget.setCurrentIndex(1)  # 切换到结果页面显示错误
        
        # 重置按钮状态
        self.industry_ai_analysis_in_progress = False
        self.industry_ai_analyze_btn.setEnabled(True)
        self.industry_ai_analyze_btn.setText(t_gui("开始AI分析"))
        self.industry_ai_status_label.setText("")
        
        print(f"[ERROR] 行业AI分析错误：{error_message}")
    
    def update_industry_ai_tab_status(self, industry_name):
        """更新行业AI分析Tab状态 - 根据内存缓存决定显示首页还是结果页"""
        try:
            if not hasattr(self, 'industry_ai_stacked_widget'):
                return
            
            # 检查当前是否在AI分析Tab
            if hasattr(self, 'industry_tab_widget'):
                current_tab_index = self.industry_tab_widget.currentIndex()
                
                # 检查是否有该行业的缓存
                cached_result = self.industry_ai_cache.get(industry_name)
                
                if cached_result:
                    # 有缓存：如果当前在AI分析Tab，则显示结果页；否则准备好，等待切换时显示
                    if current_tab_index == 1:  # AI分析Tab
                        html_result = self.format_industry_ai_analysis_result(cached_result, industry_name)
                        self.set_industry_ai_html(html_result)
                        self.industry_ai_stacked_widget.setCurrentIndex(1)  # 显示结果页
                    print(f"[行业AI分析] {industry_name} 已有缓存，准备显示结果")
                else:
                    # 无缓存：重置到首页（分析按钮页）
                    self.industry_ai_stacked_widget.setCurrentIndex(0)  # 显示分析按钮页
                    
                    # 重置按钮状态
                    if hasattr(self, 'industry_ai_analyze_btn'):
                        self.industry_ai_analyze_btn.setText(t_gui("开始AI分析"))
                        self.industry_ai_analyze_btn.setEnabled(True)
                    if hasattr(self, 'industry_ai_status_label'):
                        self.industry_ai_status_label.setText("")
                    
                    print(f"[行业AI分析] {industry_name} 无缓存，显示首页")
                    
        except Exception as e:
            print(f"更新行业AI分析Tab状态失败: {str(e)}")







class NewPyQt5Interface(QMainWindow):
    """新的PyQt5股票分析界面主窗口"""
    
    def __init__(self, no_update=False):
        super().__init__()
        
        self.analysis_worker = None
        self.no_update = no_update
        
        # ===== 初始化AI使用计数器 =====
        try:
            from utils.ai_usage_counter import get_ai_counter
            self.ai_counter = get_ai_counter()
            print(f"[AI计数器] 初始化完成，当前使用次数: {self.ai_counter.get_count()}")
        except Exception as e:
            print(f"[AI计数器] 初始化失败: {e}")
            self.ai_counter = None
        
        # 根据参数决定是否执行开机启动更新数据文件
        if not self.no_update:
            self.startup_update_data_files()
        else:
            print("🚫 跳过数据文件检查（--NoUpdate参数已启用）")
        
        self.setup_ui()
        
    def startup_update_data_files(self):
        """开机启动更新数据文件功能（PyQt5版本）"""
        try:
            print("正在检查数据文件更新...")
            
            # 使用PyQt5版本的更新器（打包环境和开发环境都支持）
            from utils.data_updater_pyqt5 import silent_update
            
            # 获取目标目录（EXE目录或项目根目录）
            target_dir = get_base_path()
            
            # 静默更新（不显示界面，后台下载）
            try:
                print(f"数据文件将更新到: {target_dir}")
                update_success = silent_update(target_dir=target_dir)
                
                if update_success:
                    print(" 数据文件更新成功")
                else:
                    print(" 部分数据文件更新失败，将使用现有数据")
                    
            except Exception as e:
                print(f" 数据更新失败: {e}")
                print("将继续使用现有数据文件")
            
            print("数据文件检查完成，继续启动程序...")
            
        except ImportError as e:
            # tkinter不可用（打包环境）
            print(f" 数据更新功能不可用: {e}")
            print("ℹ️ 打包版本请手动更新数据文件")
        except Exception as e:
            print(f"启动数据更新功能失败: {e}")
            print("将跳过数据更新，直接启动程序")
    
    def setup_ui(self):
        """设置UI"""
        # 获取版本号并设置窗口标题
        try:
            from config.constants import VERSION
            window_title = f"{t_gui('window_title')} v{VERSION}"
        except ImportError:
            window_title = f"{t_gui('window_title')}"
        
        self.setWindowTitle(window_title)
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumHeight(800)
        self.setMaximumHeight(800)
        
        # 设置窗口字体 - 与行业分析标题一致
        self.setFont(QFont(get_cross_platform_font(), 14))
        
        # 设置窗口图标（如果存在）
        icon_path = project_root / "mrcai.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建堆叠部件管理两个页面
        self.stacked_widget = QStackedWidget()
        
        # 创建首页（文件选择页面）
        self.file_page = FileSelectionPage()
        self.file_page.file_selected.connect(self.on_file_selected)
        
        # 创建分析页面
        self.analysis_page = AnalysisPage()
        self.analysis_page.set_main_window(self)
        
        # 添加到堆叠部件
        self.stacked_widget.addWidget(self.file_page)
        self.stacked_widget.addWidget(self.analysis_page)
        
        # 设置布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)
        central_widget.setLayout(layout)
        
        # 设置商务风格主窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f8f9fa, stop:0.3 #e9ecef, stop:0.7 #dee2e6, stop:1 #ced4da);
                color: #2c3e50;
                font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
            }
            
            QWidget {
                font-family: Arial, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'WenQuanYi Micro Hei', sans-serif;
            }
            
            /* 工具栏和菜单栏样式 */
            QMenuBar {
                background: rgba(255, 255, 255, 0.9);
                border-bottom: 2px solid #667eea;
                padding: 5px;
                color: #2c3e50;
                font-weight: bold;
            }
            
            QMenuBar::item {
                background: transparent;
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px;
            }
            
            QMenuBar::item:selected {
                background: rgba(102, 126, 234, 0.1);
                color: #667eea;
            }
            
            QStatusBar {
                background: rgba(255, 255, 255, 0.8);
                border-top: 1px solid rgba(102, 126, 234, 0.3);
                color: #2c3e50;
                font-size: 12px;
            }
            
            /* 滚动条样式 */
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.3);
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5a6fd8, stop:1 #6a4190);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
    def on_file_selected(self, file_path: str):
        """文件选择后的处理"""
        if not MODULES_AVAILABLE:
            QMessageBox.critical(self, t_gui("error"), 
                               t_gui("module_unavailable_message"))
            return
        
        # 根据文件名前缀识别市场类型
        import os
        file_name = os.path.basename(file_path).lower()
        detected_market = self._detect_market_from_filename(file_name)
        
        # 保存检测到的市场类型，供后续使用
        self.detected_market = detected_market
        self.current_data_file_path = file_path
        
        print(f"检测到数据文件市场类型: {detected_market.upper()}")
        
        # 立即更新中国市场专属Tab的可见性
        if hasattr(self, 'analysis_page'):
            self.analysis_page.update_cn_market_tabs_visibility()
            print(f"[市场切换] 已更新Tab可见性，当前市场: {detected_market.upper()}")
        
        # 获取AI分析启用状态
        enable_ai = self.file_page.get_ai_analysis_enabled()
        
        # 创建分析工作线程
        self.analysis_worker = AnalysisWorker(file_path, enable_ai)
        self.analysis_worker.progress_updated.connect(self.on_progress_updated)
        self.analysis_worker.analysis_completed.connect(self.on_analysis_completed)
        self.analysis_worker.analysis_failed.connect(self.on_analysis_failed)
        
        # 启动分析
        self.analysis_worker.start()
        
    def _detect_market_from_filename(self, file_name: str) -> str:
        """根据文件名前缀检测市场类型"""
        file_name = file_name.lower()
        
        # 根据文件名前2个字母识别市场
        if file_name.startswith('cn'):
            return 'cn'
        elif file_name.startswith('hk'):
            return 'hk'  
        elif file_name.startswith('us'):
            return 'us'
        else:
            # 如果没有明确前缀，尝试从文件名中寻找关键字
            if 'china' in file_name or 'cn_' in file_name:
                return 'cn'
            elif 'hongkong' in file_name or 'hk_' in file_name or 'hong' in file_name:
                return 'hk'
            elif 'america' in file_name or 'us_' in file_name or 'usa' in file_name:
                return 'us'
            else:
                # 默认返回cn市场
                print(f"无法从文件名识别市场类型: {file_name}，默认使用CN市场")
                return 'cn'
        
    def on_progress_updated(self, value: int, text: str):
        """进度更新"""
        # 更新首页的进度条
        self.file_page.update_loading_progress(value, text)
            
    def on_analysis_completed(self, results: Dict[str, Any]):
        """分析完成"""
        # 隐藏首页的进度条
        self.file_page.hide_loading_progress()
            
        # 更新分析页面的结果
        self.analysis_page.update_analysis_results(results)
        
        # 确保服务器运行（仅市场数据完成后且未启动过，且为中文系统+CN市场）
        try:
            self.analysis_page.ensure_stock_server_running()
        except Exception as e:
            print(f"启动服务器时出错: {e}")
        
        # 切换到分析页面
        self.stacked_widget.setCurrentWidget(self.analysis_page)
        
        # 检查是否需要显示 API Key 配置对话框
        self._check_and_show_api_dialog()
        
    def _check_and_show_api_dialog(self):
        """检查并显示 API Key 配置对话框"""
        try:
            from api_key_dialog import should_show_api_dialog, APIKeyDialog
            
            if should_show_api_dialog():
                print("[API配置] 检测到需要配置 API Key，显示配置对话框")
                dialog = APIKeyDialog(self)
                dialog.exec_()
            else:
                print("[API配置] 已有 API Key 配置或用户选择不再显示")
        except Exception as e:
            print(f"[API配置] 检查API对话框时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def on_analysis_failed(self, error_msg: str):
        """分析失败"""
        # 隐藏首页的进度条
        self.file_page.hide_loading_progress()
            
        # 显示错误消息
        QMessageBox.critical(self, "分析失败", f"分析过程中发生错误:\n{error_msg}")
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.analysis_worker and self.analysis_worker.isRunning():
            reply = QMessageBox.question(self, "确认退出", 
                                       "分析正在进行中，确定要退出吗？",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.analysis_worker.is_cancelled = True
                self.analysis_worker.terminate()
                self.analysis_worker.wait()
                self._cleanup_and_exit()
                event.accept()
            else:
                event.ignore()
        else:
            self._cleanup_and_exit()
            event.accept()
    
    def _cleanup_and_exit(self):
        """清理资源并准备退出"""
        try:
            # 清理主分析线程
            if hasattr(self, 'analysis_worker') and self.analysis_worker:
                if self.analysis_worker.isRunning():
                    self.analysis_worker.is_cancelled = True
                    self.analysis_worker.terminate()
                    self.analysis_worker.wait(1000)  # 等待最多1秒
            
            # 行业评级工作线程已删除
            
            # 关闭服务器（如果是本软件启动的）
            self._shutdown_server_if_started_by_us()
            
            # 清理临时文件
            self._cleanup_temporary_files()
            
            # 处理待处理事件
            QApplication.processEvents()
            
            # 退出应用
            QApplication.instance().quit()
            
        except Exception as e:
            print(f"清理退出时出错: {e}")
            # 强制退出
            import os
            os._exit(0)
    
    def _shutdown_server_if_started_by_us(self):
        """无条件关闭大师服务器 (http://localhost:16888) - 使用API+进程管理双保险"""
        try:
            print("[服务器管理] 准备关闭大师服务器...")
            
            # 方法1: 尝试通过API优雅关闭
            api_success = self._try_api_shutdown()
            
            # 等待并验证
            if api_success:
                import time
                time.sleep(1)  # 等待服务器关闭
                
                # 验证服务器是否真的关闭了
                if not self._check_server_running():
                    print("[服务器管理] ✅ 服务器已通过API成功关闭")
                    return
                else:
                    print("[服务器管理] ⚠️ API关闭后服务器仍在运行，尝试进程终止")
            
            # 方法2: 如果API失败，使用进程管理强制关闭
            print("[服务器管理] 使用进程管理强制关闭服务器...")
            process_success = self._try_process_shutdown()
            
            if process_success:
                print("[服务器管理] ✅ 服务器已通过进程管理成功关闭")
            else:
                print("[服务器管理] ⚠️ 无法关闭服务器，可能需要手动关闭")
                
        except Exception as e:
            print(f"[ERROR] 关闭大师服务器时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _try_api_shutdown(self):
        """方法1: 尝试通过API优雅关闭服务器"""
        try:
            import requests
            import time
            
            url = "http://localhost:16888/api/shutdown"
            timeout = 3
            
            print(f"[服务器管理] 方法1: 向 {url} 发送关闭指令")
            
            try:
                response = requests.post(url, timeout=timeout)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"[服务器管理] ✅ API关闭指令已发送")
                        print(f"[服务器管理]    消息: {result.get('message')}")
                        return True
                    else:
                        print(f"[服务器管理] ⚠️ API返回失败: {result.get('error', 'Unknown error')}")
                        return False
                else:
                    print(f"[服务器管理] ⚠️ HTTP 状态码: {response.status_code}")
                    return False
                    
            except requests.exceptions.Timeout:
                print("[服务器管理] ⚠️ API请求超时")
                return True  # 超时可能意味着服务器已开始关闭
                
            except requests.exceptions.ConnectionError:
                print("[服务器管理] ℹ️ 无法连接到服务器（可能已关闭）")
                return True  # 连接失败可能意味着已关闭
            
        except ImportError:
            print("[服务器管理] ⚠️ requests模块不可用")
            return False
        except Exception as e:
            print(f"[服务器管理] ⚠️ API关闭出错: {e}")
            return False
    
    def _try_process_shutdown(self):
        """方法2: 通过进程管理强制关闭服务器"""
        try:
            import psutil
            import time
            
            # 查找 stockhost.exe 进程
            found_processes = []
            target_port = 16888
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'stockhost' in proc.info['name'].lower():
                        # 检查端口
                        try:
                            connections = proc.connections()
                            for conn in connections:
                                if conn.status == 'LISTEN' and conn.laddr.port == target_port:
                                    found_processes.append(proc)
                                    print(f"[服务器管理] 找到进程: PID={proc.pid}, 名称={proc.info['name']}, 端口={target_port}")
                                    break
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            # 如果无法获取端口信息，但名称匹配，也加入列表
                            found_processes.append(proc)
                            print(f"[服务器管理] 找到进程: PID={proc.pid}, 名称={proc.info['name']} (无法确认端口)")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not found_processes:
                print("[服务器管理] 未找到 stockhost.exe 进程")
                return True  # 没有进程就认为成功
            
            # 终止所有找到的进程
            killed_count = 0
            for proc in found_processes:
                try:
                    print(f"[服务器管理] 尝试终止进程 PID={proc.pid}...")
                    
                    # 先尝试优雅终止
                    proc.terminate()
                    
                    # 等待最多3秒
                    try:
                        proc.wait(timeout=3)
                        print(f"[服务器管理] ✅ 进程 PID={proc.pid} 已优雅终止")
                        killed_count += 1
                    except psutil.TimeoutExpired:
                        # 如果3秒后还没退出，强制杀死
                        print(f"[服务器管理] ⚠️ 进程 PID={proc.pid} 未响应，强制终止...")
                        proc.kill()
                        proc.wait(timeout=3)
                        print(f"[服务器管理] ✅ 进程 PID={proc.pid} 已强制终止")
                        killed_count += 1
                        
                except psutil.NoSuchProcess:
                    print(f"[服务器管理] ℹ️ 进程 PID={proc.pid} 已不存在")
                    killed_count += 1
                except psutil.AccessDenied:
                    print(f"[服务器管理] ❌ 没有权限终止进程 PID={proc.pid} (需要管理员权限)")
                except Exception as e:
                    print(f"[服务器管理] ❌ 终止进程 PID={proc.pid} 失败: {e}")
            
            if killed_count > 0:
                print(f"[服务器管理] ✅ 成功终止 {killed_count} 个进程")
                return True
            else:
                print(f"[服务器管理] ❌ 未能终止任何进程")
                return False
                
        except ImportError:
            print("[服务器管理] ⚠️ psutil模块不可用，无法使用进程管理")
            return False
        except Exception as e:
            print(f"[服务器管理] ❌ 进程终止出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _check_server_running(self):
        """检查服务器是否仍在运行"""
        try:
            import requests
            response = requests.get("http://localhost:16888", timeout=2)
            return True  # 能连接就是在运行
        except:
            return False  # 连接失败就是已关闭
    
    def _cleanup_temporary_files(self):
        """清理临时文件"""
        import os
        
        # 需要删除的临时文件列表
        temp_files = [
            'cn_data5000.json',
            'hk_data1000.json', 
            'us_data1000.json',
            'cn-lj.dat',
            'hk-lj.dat',
            'us-lj.dat'
        ]
        
        deleted_count = 0
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[DEL] 已删除临时文件: {file_path}")
                    deleted_count += 1
            except Exception as e:
                print(f" 删除临时文件失败 {file_path}: {e}")
        
        if deleted_count > 0:
            print(f" 共清理了 {deleted_count} 个临时文件")
        else:
            print("📝 没有找到需要清理的临时文件")


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AI股票大师 - 智能股票分析工具')
    parser.add_argument('--NoUpdate', action='store_true', 
                       help='跳过启动时的数据文件检查和更新（cn_data5000等6个文件）')
    parser.add_argument('--no-upgrade-check', action='store_true',
                       help='跳过软件版本升级检查')
    parser.add_argument('--no-splash', action='store_true',
                       help='禁用启动画面（Splash Screen）')
    args = parser.parse_args()
    
    # 创建QApplication
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName(t_gui('app_name'))
    app.setApplicationVersion(t_gui('app_version'))
    app.setOrganizationName("AI Stock Master")
    
    # 设置全局字体
    font = QFont(get_cross_platform_font(), 9)
    app.setFont(font)
    
    # 显示启动画面（如果未禁用）
    splash = None
    splash_logger = None
    if not args.no_splash:
        try:
            from utils.splash_screen import create_splash_screen, SplashLogger
            splash = create_splash_screen(app)
            splash.showMessage("正在启动 AI 股票大师...")
            splash.showProgress(10)
            
            # 安装日志重定向
            splash_logger = SplashLogger(splash)
            splash_logger.install()
        except Exception as e:
            print(f"无法显示启动画面: {e}")
    
    # 软件升级检查 (在分析数据文件之前)
    if not args.no_upgrade_check:
        if splash:
            splash.showProgress(20, "正在检查软件更新...")
        try:
            from updater import check_for_updates
            
            # 检查软件更新
            result = check_for_updates()
            
            # 注意：如果是Windows系统且需要升级，updater会调用sys.exit()直接退出
            # 只有在无需升级或升级失败时才会到达这里
            if not result:
                print("Software upgrade check failed, continuing normal startup... | 软件升级检查失败，继续正常启动...")
            
        except SystemExit:
            # 升级程序调用了sys.exit()，正常退出
            raise
        except ImportError:
            print("Upgrade module unavailable, skipping upgrade check | 升级模块不可用，跳过升级检查")
        except Exception as e:
            print(f"Error during upgrade check: {e} | 升级检查时发生错误: {e}")
            print("Continuing normal startup... | 继续正常启动...")
    
    # 加载配置
    if splash:
        splash.showProgress(20, "正在检查软件更新...")
        splash.showDetail("Check Update...")
    
    # 初始化模块
    if splash:
        splash.showProgress(30, "正在检查数据文件...")
        splash.showDetail("Check DataBase...")
    
    # 创建主窗口
    if splash:
        splash.showProgress(50, "正在更新数据文件...")
    
    # 创建主窗口，传递NoUpdate参数
    window = NewPyQt5Interface(no_update=args.NoUpdate)
    
    # 完成加载
    if splash:
        splash.showProgress(100, "启动完成！")
        QTimer.singleShot(500, lambda: splash.finish(window))
    
    # 显示主窗口
    window.show()
    
    # 运行应用程序
    try:
        exit_code = app.exec_()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        if splash_logger:
            splash_logger.restore()
        # 确保应用程序完全退出
        app.quit()
        QApplication.processEvents()
    
    # 强制退出，确保终端也关闭
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
