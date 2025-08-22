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

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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

# 可选导入 WebEngine
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    print("WebEngine组件不可用，将使用替代方案 (WebEngine component unavailable, using fallback)")
    QWebEngineView = None
    WEBENGINE_AVAILABLE = False

# 备用翻译函数（在导入失败时使用）
def t_gui_fallback(key, **kwargs):
    return key

def t_common_fallback(key, **kwargs):
    return key

# 项目模块导入
try:
    from data.stock_dataset import StockDataSet
    from algorithms.realtime_engine import RealtimeAnalysisEngine
    from utils.report_generator import ReportGenerator
    from config.i18n import t_common
    from config.gui_i18n import t_gui, set_language, get_system_language
    from config import get_config
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"模块导入失败 (Import modules failed): {e}")
    MODULES_AVAILABLE = False
    # 使用备用翻译函数
    t_gui = t_gui_fallback
    t_common = t_common_fallback


class AnalysisWorker(QThread):
    """分析工作线程"""
    progress_updated = pyqtSignal(int, str)  # 进度，状态文本
    analysis_completed = pyqtSignal(dict)    # 分析完成，结果数据
    analysis_failed = pyqtSignal(str)        # 分析失败，错误信息
    
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
            time.sleep(0.5)
            
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
            time.sleep(0.5)
            
            # 第3阶段：创建分析引擎 - 35%
            analysis_engine = RealtimeAnalysisEngine(current_dataset)
            self.progress_updated.emit(35, t_gui('executing_stock_analysis'))
            time.sleep(1.0)
            
            # 第4阶段：执行分析 - 55%
            analysis_results = analysis_engine.calculate_all_metrics()
            
            self.progress_updated.emit(55, t_gui('generating_basic_report'))
            time.sleep(0.8)
            
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
            
            # 第5阶段：AI智能分析 - 70% (仅在启用时执行)
            if self.enable_ai_analysis:
                self.progress_updated.emit(70, t_gui('ai_analysis'))
                time.sleep(0.5)
                
                ai_analysis_result = self.run_ai_analysis(analysis_results)
                if ai_analysis_result:
                    final_results['ai_analysis'] = ai_analysis_result
                    print(t_gui('ai_analysis_complete'))
                else:
                    print(t_gui('ai_analysis_failed'))
                
                # 第6阶段：AI分析完成 - 85%
                self.progress_updated.emit(85, t_gui('ai_analysis_complete_status'))
                time.sleep(0.3)
            else:
                # 跳过AI分析，直接进入下一阶段
                self.progress_updated.emit(85, t_gui("skip_ai_analysis"))
                print(t_gui("user_disabled_ai_analysis"))
                time.sleep(0.3)
            
            # 第7阶段：生成HTML报告 - 95%
            html_report_path = self.generate_html_report(final_results)
            if html_report_path:
                final_results['html_report_path'] = html_report_path
                print(t_gui('html_report_generated', path=html_report_path))
            
            self.progress_updated.emit(100, t_gui('analysis_complete'))
            time.sleep(0.3)
            
            self.analysis_completed.emit(final_results)
            
        except Exception as e:
            error_msg = t_gui('analysis_process_error', error=str(e))
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.analysis_failed.emit(error_msg)
    
    def run_ai_analysis(self, analysis_results):
        """运行AI智能分析 - 移植自旧版main_window.py
        
        注意：这是主AI分析的数据处理和调用逻辑
        与行业分析和个股分析的AI功能分离，提供综合性的投资分析
        """
        try:
            # 检查LLM配置文件是否存在
            if not self._check_llm_config():
                print(t_gui("ai_config_file_not_found"))
                return None
            
            # 准备分析数据
            analysis_data = self._prepare_analysis_data(analysis_results)
            
            # 调用LLM API
            ai_response = self._call_llm_api(analysis_data)
            
            return ai_response
            
        except Exception as e:
            print(f"{t_gui('ai_analysis_execution_failed')}: {str(e)}")
            return None
    
    def _check_llm_config(self) -> bool:
        """检查LLM配置文件是否存在"""
        try:
            import os
            import json
            project_root = Path(__file__).parent
            config_path = project_root / "llm-api" / "config" / "user_settings.json"
            
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
            
            # 提取市场数据
            if hasattr(analysis_results, 'market') and analysis_results.market:
                market = analysis_results.market
                msci_value = market.get('current_msci', 0)
                volatility = market.get('volatility', 0)
                volume_ratio = market.get('volume_ratio', 0)
                
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
            
            # 提取行业数据
            if hasattr(analysis_results, 'industries') and analysis_results.industries:
                industries_summary = {}
                sorted_industries = []
                
                for industry_name, industry_info in analysis_results.industries.items():
                    tma_value = industry_info.get('irsi', 0)
                    if isinstance(tma_value, dict):
                        tma_value = tma_value.get('irsi', 0)
                    sorted_industries.append((industry_name, float(tma_value)))
                
                sorted_industries.sort(key=lambda x: x[1], reverse=True)
                
                # 取前10个行业
                top_industries = sorted_industries[:10]
                industries_summary["top_performers"] = top_industries
                industries_summary["sector_count"] = len(analysis_results.industries)
                
                data["industry_data"] = industries_summary
            
            # 提取股票数据
            if hasattr(analysis_results, 'stocks') and analysis_results.stocks:
                stocks_summary = {}
                sorted_stocks = []
                
                for stock_code, stock_info in analysis_results.stocks.items():
                    rtsi_value = stock_info.get('rtsi', 0)
                    if isinstance(rtsi_value, dict):
                        rtsi_value = rtsi_value.get('rtsi', 0)
                    sorted_stocks.append((stock_code, stock_info.get('name', stock_code), float(rtsi_value)))
                
                sorted_stocks.sort(key=lambda x: x[2], reverse=True)
                
                # 取前20只股票
                top_stocks = sorted_stocks[:20]
                stocks_summary["top_performers"] = top_stocks
                stocks_summary["total_count"] = len(analysis_results.stocks)
                
                # 计算分布统计
                rtsi_values = [x[2] for x in sorted_stocks]
                stocks_summary["statistics"] = {
                    "average_rtsi": np.mean(rtsi_values) if rtsi_values else 0,
                    "strong_count": len([x for x in rtsi_values if x >= 60]),
                    "neutral_count": len([x for x in rtsi_values if 40 <= x < 60]),
                    "weak_count": len([x for x in rtsi_values if x < 40])
                }
                
                data["stock_data"] = stocks_summary
            
            return data
            
        except Exception as e:
            print(t_gui('prepare_ai_data_failed', error=str(e)))
            return {}
    
    def _call_llm_api(self, analysis_data):
        """调用LLM API进行分析 - 移植自旧版main_window.py，完全一致"""
        try:
            import sys
            import time
            
            # 检测当前系统语言
            from config.i18n import is_english
            use_english = is_english()
            
            # 添加llm-api到路径
            project_root = Path(__file__).parent
            llm_api_path = project_root / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # 导入LLM API模块
            from client import LLMClient
            
            # 创建LLM客户端
            client = LLMClient()
            
            # 准备提示词
            prompt = self._create_analysis_prompt(analysis_data)
            
            # 调用LLM - 与旧版本完全一致的方式
            start_time = time.time()
            
            # 根据系统语言选择指令和智能体
            if use_english:
                language_instruction = "Please respond in English."
                agent_id = "financial_analyst"
                system_msg = "You are a professional financial analyst with expertise in stock analysis, technical analysis, and fundamental analysis. Please respond in English and provide professional investment advice."
                user_msg = "Please analyze the following stock data and provide investment advice:\n\n" + prompt
            else:
                language_instruction = t_gui('chinese_response_instruction')
                agent_id = t_gui('financial_analyst_agent')
                system_msg = t_gui('chinese_financial_analyst')
                user_msg = t_gui('chinese_answer_request') + prompt
            
            # 尝试使用智能体模式
            try:
                response = client.chat(
                    message=language_instruction + prompt,
                    agent_id=agent_id
                )
                print(f"[LLM Debug] Agent call successful, took {time.time() - start_time:.1f}s")
            except Exception as agent_error:
                print(f"[LLM Debug] {t_gui('agent_failed_fallback_direct')}: {agent_error}")
                
                # 如果智能体不可用，回退到直接调用
                response = client.chat(
                    message=user_msg,
                    system_message=system_msg
                )
                print(f"[LLM Debug] Direct call successful, took {time.time() - start_time:.1f}s")
            
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
    
    def _create_analysis_prompt(self, analysis_data):
        """创建分析提示词 - 移植自旧版
        
        注意：这是主AI分析的提示词，与行业分析和个股分析的AI功能不同
        主分析需要综合讨论大盘、行业、个股三个层面的投资分析
        """
        market_data = analysis_data.get('market_data', {})
        industry_data = analysis_data.get('industry_data', {})
        stock_data = analysis_data.get('stock_data', {})
        
        # 获取当前市场类型 - 从文件路径检测
        current_market = self._detect_market_from_file_path()
        market_names = {'cn': '中国A股市场', 'hk': '香港股票市场', 'us': '美国股票市场'}
        market_name = market_names.get(current_market, '股票市场')
        
        # 构建市场特色说明
        market_context = ""
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
▪ 平均RTSI指数: {stock_data.get('statistics', {}).get('average_rtsi', 0):.2f}
▪ 强势股票数量: {stock_data.get('statistics', {}).get('strong_count', 0)}只 (RTSI≥60)
▪ 中性股票数量: {stock_data.get('statistics', {}).get('neutral_count', 0)}只 (40≤RTSI<60)
▪ 弱势股票数量: {stock_data.get('statistics', {}).get('weak_count', 0)}只 (RTSI<40)

▪ 优质个股推荐（按RTSI指数排序）:
"""
        
        # 添加股票信息
        top_stocks = stock_data.get('top_performers', [])
        for i, (code, name, rtsi) in enumerate(top_stocks[:10]):
            prompt += f"  {i+1}. {code} {name}: RTSI {rtsi:.2f}\n"
        
        prompt += """

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
• 回复语言：根据用户系统语言自动选择中文或英文回复

【重要：股票推荐真实性要求】
• 推荐的所有股票必须是{market_name}真实存在的股票
• 股票代码和名称必须准确无误，不得虚构或编造
• 推荐股票时务必遵循{current_market.upper()}市场的代码格式规范
• 可参考分析数据中提供的真实股票代码进行推荐

请用专业、系统的分析方法，确保分析逻辑清晰、结论明确、建议具体可操作。分析应当平衡风险与收益，避免极端观点。
"""
        
        return prompt
    
    def generate_html_report(self, results_data):
        """生成HTML报告 - 移植自旧版main_window.py"""
        try:
            from datetime import datetime
            
            # 提取AnalysisResults对象
            if isinstance(results_data, dict) and 'analysis_results' in results_data:
                analysis_results = results_data['analysis_results']
            else:
                analysis_results = results_data
            
            # 创建报告目录
            reports_dir = Path("analysis_reports")
            reports_dir.mkdir(exist_ok=True)
            
            html_file = reports_dir / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            # 获取分析数据 - 修复数据传递问题
            if isinstance(analysis_results, dict) and 'analysis_results' in analysis_results:
                # 从字典格式的final_results中获取真正的分析结果对象
                real_analysis_results = analysis_results['analysis_results']
                
                if hasattr(real_analysis_results, 'metadata'):
                    total_stocks = real_analysis_results.metadata.get('total_stocks', 0)
                    total_industries = real_analysis_results.metadata.get('total_industries', 0)
                    
                    # 获取top股票推荐
                    top_stocks = real_analysis_results.get_top_stocks('rtsi', 5)
                    
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
                    
                    # 获取top股票
                    top_stocks = []
                    if hasattr(real_analysis_results, 'stocks'):
                        stocks_list = []
                        for code, info in real_analysis_results.stocks.items():
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
                    top_stocks = analysis_results.get_top_stocks('rtsi', 5)
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
                        recommendation = t_gui('strongly_recommend') if rtsi_value > 70 else t_gui('moderate_attention') if rtsi_value > 50 else t_gui('cautious_observation')
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
            
            if ai_analysis:
                ai_analysis_section = f"""
    <div class="section">
        <h2>🤖 {t_gui('ai_intelligent_analysis')}</h2>
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
        <h2>🤖 {t_gui('ai_intelligent_analysis')}</h2>
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; text-align: center;">
            <h3 style="color: #856404;">{t_gui('ai_function_not_executed')}</h3>
            <p style="color: #856404; margin: 10px 0;">{t_gui('please_check_ai_settings')}</p>
            <p style="color: #6c757d; font-size: 12px;">{t_gui('click_ai_settings_button_to_configure')}</p>
        </div>
    </div>"""
            
            # 生成市场情绪分析HTML
            sentiment_risk_color = "red" if msci_value > 70 else "green" if msci_value < 30 else "orange"  # 高位风险用红色，低位机会用绿色
            trend_color = "red" if trend_5d > 0 else "green"  # 上涨用红色，下跌用绿色（红涨绿跌）
            
            # 生成HTML内容
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{t_gui('ai_stock_trend_analysis_report')}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; line-height: 1.6; }}
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
        .risk-high {{ color: green; font-weight: bold; }}  /* 高风险用绿色（危险信号） */
        .risk-medium {{ color: orange; font-weight: bold; }}
        .risk-low {{ color: red; font-weight: bold; }}  /* 低风险用红色（机会信号） */
        .trend-up {{ color: red; }}  /* 上涨用红色（红涨绿跌） */
        .trend-down {{ color: green; }}  /* 下跌用绿色（红涨绿跌） */
    </style>
</head>
<body>
    <div class="header">
        <h1>{t_gui('ai_stock_trend_analysis_report')}</h1>
        <p>{t_gui('generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <div class="author">{t_gui('author')}: 267278466@qq.com</div>
    </div>
    
    <div class="section">
        <h2>{t_gui('analysis_overview')}</h2>
        <div class="metric">{t_gui('analyzed_stocks_count')}: <span class="highlight">{total_stocks:,}</span></div>
        <div class="metric">{t_gui('industry_classification')}: <span class="highlight">{total_industries}</span>{t_gui('industries_unit')}</div>
        <div class="metric">{t_gui('analysis_algorithm')}: <span class="highlight">RTSI + TMA + MSCI</span></div>
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
    """首页 - 文件选择页面"""
    file_selected = pyqtSignal(str)  # 文件选择信号
    
    def __init__(self):
        super().__init__()
        self.enable_ai_analysis = False  # AI分析标志
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(30)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # 标题
        title_label = QLabel(t_gui('main_title'))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin: 20px;")
        
        # 副标题
        subtitle_label = QLabel(t_gui('subtitle'))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setFont(QFont("Microsoft YaHei", 16))
        subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 40px;")
        
        # 说明文本
        desc_label = QLabel(t_gui('file_selection_desc'))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setFont(QFont("Microsoft YaHei", 12))
        desc_label.setStyleSheet("color: #34495e; margin-bottom: 30px;")
        
        # 文件选择按钮
        self.select_button = QPushButton("📂 " + t_gui('select_file_button'))
        self.select_button.setFont(QFont("Microsoft YaHei", 14))
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.select_button.clicked.connect(self.select_file)
        
        # 文件信息显示
        self.file_info_label = QLabel(t_gui('file_not_selected'))
        self.file_info_label.setAlignment(Qt.AlignCenter)
        self.file_info_label.setFont(QFont("Microsoft YaHei", 10))
        self.file_info_label.setStyleSheet("color: #95a5a6; margin-top: 20px;")
        
        # AI智能分析复选框 - 默认不选择且不可见
        self.ai_analysis_checkbox = QCheckBox(t_gui("execute_ai_analysis"))
        self.ai_analysis_checkbox.setFont(QFont("Microsoft YaHei", 12))
        self.ai_analysis_checkbox.setStyleSheet("""
            QCheckBox {
                color: #2c3e50;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #bdc3c7;
                background-color: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3498db;
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        self.ai_analysis_checkbox.setChecked(False)  # 默认不选择
        self.ai_analysis_checkbox.setVisible(False)  # 默认不可见
        self.ai_analysis_checkbox.stateChanged.connect(self.on_ai_checkbox_changed)
        
        # 布局
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(desc_label)
        layout.addWidget(self.select_button, alignment=Qt.AlignCenter)
        layout.addWidget(self.ai_analysis_checkbox, alignment=Qt.AlignCenter)
        layout.addWidget(self.file_info_label)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            t_gui('select_stock_data_file'),
            str(project_root),
            f"{t_gui('data_files')};;{t_gui('all_files_pattern')}"
        )
        
        if file_path:
            file_name = Path(file_path).name
            self.file_info_label.setText(t_gui('file_selected', filename=file_name))
            self.file_info_label.setStyleSheet("color: #27ae60; margin-top: 20px;")
            
            # 发射文件选择信号
            self.file_selected.emit(file_path)
    
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
        
        # 行业AI分析相关
        self.industry_ai_cache = {}  # 缓存行业AI分析结果
        self.industry_ai_analysis_in_progress = False  # 防止重复分析
        self.current_industry_name = None  # 当前分析的行业
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧树形导航 - 增大字体与行业分析标题一致
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel(t_gui('analysis_items_header'))
        self.tree_widget.setMaximumWidth(350)
        self.tree_widget.setMinimumWidth(300)
        self.tree_widget.setFont(QFont("Microsoft YaHei", 14))  # 增大字体与行业分析标题一致
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: 'Microsoft YaHei';
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
        
    def setup_tree_structure(self):
        """设置树形结构 - 带子项目"""
        # AI建议
        ai_item = QTreeWidgetItem([t_gui('ai_suggestions')])
        ai_item.setData(0, Qt.UserRole, "ai_suggestions")
        self.tree_widget.addTopLevelItem(ai_item)
        
        # 大盘分析
        market_item = QTreeWidgetItem([t_gui('market_analysis')])
        market_item.setData(0, Qt.UserRole, "market_analysis")
        self.tree_widget.addTopLevelItem(market_item)
        
        # 行业列表 - 动态添加子项目
        self.industry_item = QTreeWidgetItem([t_gui('industry_list')])
        self.industry_item.setData(0, Qt.UserRole, "industry_list")
        self.tree_widget.addTopLevelItem(self.industry_item)
        
        # 个股列表 - 动态添加子项目  
        self.stock_item = QTreeWidgetItem([t_gui('stock_list')])
        self.stock_item.setData(0, Qt.UserRole, "stock_list")
        self.tree_widget.addTopLevelItem(self.stock_item)
        
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
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # 顶部区域：标题和按钮
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        self.ai_title_label = QLabel(t_gui('ai_intelligent_analysis'))
        self.ai_title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        self.ai_title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        header_layout.addWidget(self.ai_title_label)
        
        # 添加弹性空间
        header_layout.addStretch()
        
        # AI设置按钮
        self.ai_settings_btn = QPushButton(t_gui('ai_settings_btn'))
        self.ai_settings_btn.setFont(QFont("Microsoft YaHei", 10))
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
        
        # AI分析按钮 - 插入在AI设置和另存为之间
        self.ai_analysis_btn = QPushButton(t_gui("ai_analysis"))
        self.ai_analysis_btn.setFont(QFont("Microsoft YaHei", 10))
        self.ai_analysis_btn.setFixedSize(100, 35)
        self.ai_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-weight: bold;
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
        self.ai_analysis_btn.clicked.connect(self.start_ai_analysis)
        header_layout.addWidget(self.ai_analysis_btn)
        
        # 保存HTML按钮
        self.save_html_btn = QPushButton(t_gui('save_html_btn'))
        self.save_html_btn.setFont(QFont("Microsoft YaHei", 10))
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
                        font-family: 'Microsoft YaHei', sans-serif; 
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
                    <div class="icon">📊</div>
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
            self.ai_browser.setFont(QFont("Microsoft YaHei", 10))
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
        """打开AI设置界面"""
        try:
            import subprocess
            import sys
            import os
            
            # 获取llm-api目录的设置文件路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            llm_api_dir = os.path.join(current_dir, "llm-api")
            
            # 优先使用无控制台窗口版本
            run_settings_no_console_path = os.path.join(llm_api_dir, "run_settings_no_console.pyw")
            run_settings_path = os.path.join(llm_api_dir, "run_settings.py")
            
            if os.path.exists(run_settings_no_console_path):
                # 使用.pyw文件启动，自动隐藏控制台窗口
                if os.name == 'nt':  # Windows系统
                    pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                    if os.path.exists(pythonw_path):
                        subprocess.Popen([pythonw_path, run_settings_no_console_path], 
                                       cwd=llm_api_dir)
                    else:
                        subprocess.Popen([sys.executable, run_settings_no_console_path], 
                                       cwd=llm_api_dir,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen([sys.executable, run_settings_no_console_path], 
                                   cwd=llm_api_dir)
            elif os.path.exists(run_settings_path):
                # 备用方案：使用原始的.py文件
                if os.name == 'nt':  # Windows系统
                    pythonw_path = sys.executable.replace('python.exe', 'pythonw.exe')
                    if os.path.exists(pythonw_path):
                        subprocess.Popen([pythonw_path, run_settings_path], 
                                       cwd=llm_api_dir)
                    else:
                        subprocess.Popen([sys.executable, run_settings_path], 
                                       cwd=llm_api_dir,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen([sys.executable, run_settings_path], 
                                   cwd=llm_api_dir)
                
                print(t_gui("ai_settings_interface_started"))
            else:
                QMessageBox.warning(self, t_gui('error'), t_gui('ai_config_not_found', path1=run_settings_no_console_path, path2=run_settings_path))
                
        except Exception as e:
            QMessageBox.critical(self, t_gui('error'), t_gui('ai_settings_open_failed', error=str(e)))
    
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
        """创建大盘分析页面 - 简化版本，去掉按钮"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        self.market_title_label = QLabel(t_gui('market_sentiment_analysis'))
        self.market_title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))  # 统一为16号字体
        self.market_title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        
        # 内容区域 - 移植原界面的文本显示
        self.market_text = QTextEdit()
        self.market_text.setFont(QFont("Microsoft YaHei", 11))
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
        
        layout.addWidget(self.market_title_label)
        layout.addWidget(self.market_text)
        widget.setLayout(layout)
        return widget
        
    def create_industry_analysis_page(self):
        """创建行业分析页面 - 增加Tab结构，包含AI分析"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        self.industry_title_label = QLabel(t_gui('industry_analysis'))
        self.industry_title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))  # 统一为16号字体
        self.industry_title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        
        # Tab控件 - 类似个股分析的结构
        from PyQt5.QtWidgets import QTabWidget
        self.industry_tab_widget = QTabWidget()
        self.industry_tab_widget.setFont(QFont("Microsoft YaHei", 10))
        
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
        
        # Tab 2: 行业AI分析 - 新增AI分析功能
        self.industry_ai_analysis_tab = self.create_industry_ai_analysis_tab()
        self.industry_tab_widget.addTab(self.industry_ai_analysis_tab, t_gui("🤖_AI分析"))
        
        main_layout.addWidget(self.industry_title_label)
        main_layout.addWidget(self.industry_tab_widget)
        widget.setLayout(main_layout)
        return widget
    
    def create_industry_detail_tab(self):
        """创建行业详细分析Tab - 原有的显示区域"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 详细信息显示区域
        self.industry_detail_text = QTextEdit()
        self.industry_detail_text.setFont(QFont("Microsoft YaHei", 11))
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
        self.industry_detail_text.setPlainText(t_gui("select_industry_from_left_panel"))
        
        layout.addWidget(self.industry_detail_text)
        widget.setLayout(layout)
        return widget
    
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
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加少量顶部空间
        layout.addStretch(1)
        
        # 主标题
        title_label = QLabel(t_gui("🤖_行业AI智能分析"))
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #007bff; margin-bottom: 15px;")
        
        # 描述文字
        desc_label = QLabel(t_gui("industry_ai_analysis_desc"))
        desc_label.setFont(QFont("Microsoft YaHei", 11))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        
        # 分析按钮
        self.industry_ai_analyze_btn = QPushButton(t_gui("🚀_开始AI分析"))
        self.industry_ai_analyze_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
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
        self.industry_ai_status_label.setFont(QFont("Microsoft YaHei", 10))
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
        layout.setContentsMargins(10, 10, 10, 10)
        
        # AI分析结果显示区域 - 使用HTML富文本显示
        self.industry_ai_result_browser = QTextEdit()
        self.industry_ai_result_browser.setFont(QFont("Microsoft YaHei", 11))
        self.industry_ai_result_browser.setReadOnly(True)
        self.industry_ai_result_browser.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 15px;
                line-height: 1.6;
            }
        """)
        # 设置初始HTML内容
        initial_html = f"""
        <div style="text-align: center; margin-top: 50px; color: #666;">
            <h3 style="color: #007bff;">{t_gui("🤖 行业AI分析")}</h3>
            <p>{t_gui("AI分析结果将在这里显示...")}</p>
            <p style="font-size: 12px; color: #999;">{t_gui("click_start_ai_analysis_button")}</p>
        </div>
        """
        self.industry_ai_result_browser.setHtml(initial_html)
        
        layout.addWidget(self.industry_ai_result_browser)
        widget.setLayout(layout)
        return widget
        
    def create_stock_analysis_page(self):
        """创建个股分析页面 - 添加搜索功能，美化样式"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题 - 增大字体与行业分析一致
        self.stock_title_label = QLabel(t_gui('stock_trend_analysis'))
        self.stock_title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))  # 与行业分析标题字体一致
        self.stock_title_label.setStyleSheet("color: #0078d4; padding: 10px;")
        
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
        search_layout.setContentsMargins(10, 8, 10, 8)
        
        # 查询标签 - 增大字体
        search_label = QLabel(t_gui('stock_query_label'))
        search_label.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))  # 增大字体
        search_label.setStyleSheet("color: #495057; background: transparent; border: none; padding: 0;")
        
        # 输入框 - 增大字体
        from PyQt5.QtWidgets import QLineEdit
        self.stock_search_input = QLineEdit()
        self.stock_search_input.setPlaceholderText(t_gui('stock_search_placeholder'))
        self.stock_search_input.setFont(QFont("Microsoft YaHei", 12))  # 增大字体
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
        self.stock_search_btn.setFont(QFont("Microsoft YaHei", 12))
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
        self.stock_tab_widget.setFont(QFont("Microsoft YaHei", 10))
        
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

        # Tab 1: 详细分析（含核心指标） - 前移并合并核心指标内容
        self.detail_tab = self.create_detail_tab()
        self.stock_tab_widget.addTab(self.detail_tab, t_gui("📋_详细分析"))

        # Tab 2: 趋势图表 - 移植原界面的趋势图表区
        self.chart_tab = self.create_chart_tab()
        self.stock_tab_widget.addTab(self.chart_tab, t_gui("📈_趋势图表"))
        
        # Tab 3: 个股AI分析 - 新增AI分析功能
        self.ai_analysis_tab = self.create_ai_analysis_tab()
        self.stock_tab_widget.addTab(self.ai_analysis_tab, t_gui("🤖_AI分析"))
        
        main_layout.addWidget(self.stock_title_label)
        main_layout.addWidget(search_frame)
        main_layout.addWidget(self.stock_tab_widget)
        widget.setLayout(main_layout)
        return widget
        

        
    def create_chart_tab(self):
        """创建趋势图表Tab - 使用WebView显示HTML图表，集成38天量价走势"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
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
            default_html = """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>等待选择股票</title>
                <style>
                    body {
                        font-family: 'Microsoft YaHei', sans-serif;
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
                    <div class="icon">📊</div>
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
            layout.addWidget(self.chart_webview)
            
        except ImportError:
            # 如果WebView不可用，回退到QTextEdit
            self.chart_text = QTextEdit()
            self.chart_text.setFont(QFont("Microsoft YaHei", 12))
            self.chart_text.setReadOnly(True)
            self.chart_text.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    padding: 15px;
                    line-height: 1.6;
                    font-family: 'Microsoft YaHei';
                }
            """)
            self.chart_text.setPlainText(t_gui("请选择股票查看趋势图表"))
            layout.addWidget(self.chart_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_ai_analysis_tab(self):
        """创建个股AI分析Tab - 采用2页方式"""
        # 创建堆叠窗口实现页面切换
        from PyQt5.QtWidgets import QStackedWidget
        
        self.ai_stacked_widget = QStackedWidget()
        
        # 第1页：分析按钮页面
        self.ai_button_page = self.create_ai_button_page()
        self.ai_stacked_widget.addWidget(self.ai_button_page)
        
        # 第2页：分析结果页面
        self.ai_result_page = self.create_ai_result_page()
        self.ai_stacked_widget.addWidget(self.ai_result_page)
        
        # 默认显示第1页
        self.ai_stacked_widget.setCurrentIndex(0)
        
        return self.ai_stacked_widget
    
    def create_ai_button_page(self):
        """创建AI分析按钮页面（第1页）"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
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
        icon_label = QLabel("🤖")
        icon_label.setFont(QFont("Microsoft YaHei", 28))  # 进一步减小字体大小
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: #0078d4; margin-bottom: 10px;")
        
        title_label = QLabel(t_gui("AI智能股票分析"))
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))  # 减小字体大小
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #0078d4; margin-bottom: 10px;")
        
        # 分析说明
        desc_label = QLabel(t_gui("基于RTSI指数_30天评级趋势_行业TMA状况和大盘情绪_为您提供专业的投资操作建议"))
        desc_label.setFont(QFont("Microsoft YaHei", 11))  # 减小字体大小
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 20px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        
        # 分析按钮
        self.stock_ai_analyze_btn = QPushButton(t_gui("🚀_开始AI分析"))
        self.stock_ai_analyze_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))  # 减小字体
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
        self.ai_status_label.setFont(QFont("Microsoft YaHei", 10))  # 减小字体
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
        layout.setContentsMargins(10, 10, 10, 10)
        
        # AI分析结果显示区域
        self.stock_ai_result_browser = QTextEdit()
        self.stock_ai_result_browser.setFont(QFont("Microsoft YaHei", 11))
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
        
    def create_detail_tab(self):
        """创建详细分析Tab - 合并核心指标和详细分析，美化样式"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 详细分析文本区域（包含核心指标） - 美化样式，增大字体
        self.stock_detail_text = QTextEdit()
        self.stock_detail_text.setFont(QFont("Microsoft YaHei", 12))  # 增大字体提升可读性
        self.stock_detail_text.setReadOnly(True)
        self.stock_detail_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: #333333;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 15px;
                line-height: 1.6;
                font-family: 'Microsoft YaHei';
            }
        """)
        self.stock_detail_text.setPlainText(t_gui('select_stock_prompt'))
        
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
            
            # 模拟点击事件，触发正常的点击处理逻辑
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
            self.industry_detail_text.setPlainText(t_gui("select_industry_from_left_panel"))
        elif item_type == "stock_list":
            # 主项目：显示个股分析页面
            self.content_area.setCurrentWidget(self.stock_page)
            # 切换到Tab1（详细分析）
            if hasattr(self, 'stock_tab_widget'):
                self.stock_tab_widget.setCurrentIndex(0)
            # 显示默认提示信息
            if hasattr(self, 'stock_detail_text'):
                self.stock_detail_text.setPlainText(t_gui("请从左侧个股列表中选择一只股票查看详细分析"))
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
        self.analysis_results = results
        
        # 提取不同格式的结果
        self.analysis_results_obj = results.get('analysis_results')  # AnalysisResults对象
        self.analysis_dict = results.get('analysis_dict', {})        # 字典格式
        
        # 检查是否包含AI分析结果
        self.ai_analysis_executed = 'ai_analysis' in results and results['ai_analysis'] is not None
        
        # 获取数据日期范围
        self.date_range_text = self.get_data_date_range()
        
        # 更新所有页面标题（添加日期范围）
        self.update_page_titles_with_date_range()
        
        # 填充树形控件的子项目
        self.populate_tree_items()
        
        # 更新内容页面
        self.update_ai_suggestions()
        self.update_market_analysis()
        
        # 更新AI按钮状态
        self.update_ai_buttons_state()
        
    def get_data_date_range(self) -> str:
        """获取数据文件的日期范围 - 参考main_window.py实现"""
        try:
            # 定义日期格式化函数
            def format_date(date_str):
                date_str = str(date_str)
                if len(date_str) == 8:  # YYYYMMDD格式
                    year = date_str[:4]
                    month = date_str[4:6].lstrip('0') or '0'
                    day = date_str[6:8].lstrip('0') or '0'
                    return f"{year}年{month}月{day}日"
                return date_str
            
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
                        print(f"[Debug] 从直接数据源获取日期范围: {start_date} ~ {end_date}")
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
                        print(f"[Debug] 从分析对象数据源获取日期范围: {start_date} ~ {end_date}")
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
                        print(f"[Debug] 通过metadata获取日期范围: {start_date} ~ {end_date}")
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
                        print(f"[Debug] 从分析字典获取日期范围: {start} ~ {end}")
                        return f"（{start}至{end}）"
            
            print("[Debug] 无法获取日期范围，使用默认值")
            return t_gui('date_range_unknown')
        except Exception as e:
            print(f"[Debug] 获取日期范围失败: {e}")
            import traceback
            traceback.print_exc()
            return t_gui('date_range_unknown')
    
    def update_page_titles_with_date_range(self):
        """更新所有页面标题，添加日期范围"""
        try:
            # 生成带样式的HTML标题（主标题 + 小号黑色日期范围）
            def format_title_with_date(main_title, date_range):
                return f"""
                <span style="color: #0078d4; font-size: 16px; font-weight: bold;">{main_title}</span>
                <span style="color: black; font-size: 12px; font-weight: normal; margin-left: 10px;">{date_range}</span>
                """
            
            # 更新AI分析页面标题
            if hasattr(self, 'ai_title_label'):
                html_title = format_title_with_date(t_gui('📊_智能分析报告'), self.date_range_text)
                self.ai_title_label.setText(html_title)
                self.ai_title_label.setStyleSheet("padding: 10px;")  # 移除颜色设置，使用HTML样式
            
            # 更新大盘分析页面标题
            if hasattr(self, 'market_title_label'):
                html_title = format_title_with_date(t_gui('📊_市场情绪分析'), self.date_range_text)
                self.market_title_label.setText(html_title)
                self.market_title_label.setStyleSheet("padding: 10px;")
            
            # 更新行业分析页面标题
            if hasattr(self, 'industry_title_label'):
                html_title = format_title_with_date(t_gui('🏭_行业分析'), self.date_range_text)
                self.industry_title_label.setText(html_title)
                self.industry_title_label.setStyleSheet("padding: 10px;")
            
            # 更新个股分析页面标题
            if hasattr(self, 'stock_title_label'):
                html_title = format_title_with_date(t_gui('📈_个股趋势分析'), self.date_range_text)
                self.stock_title_label.setText(html_title)
                self.stock_title_label.setStyleSheet("padding: 10px;")
                
        except Exception as e:
            print(f"更新页面标题失败: {e}")
        
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
            # 按TMA排序，但指数固定第一位
            sorted_industries = []
            index_industry = None
            
            for industry_name, industry_info in industries_data.items():
                tma_value = 0
                if isinstance(industry_info, dict):
                    tma_value = industry_info.get('irsi', 0)
                    # 处理TMA值也是字典的情况
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
            
            # 按TMA排序其他行业
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
                child_item = QTreeWidgetItem([f"📊 {stock_code} {stock_name} (RTSI: {rtsi_value:.1f})"])
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
            <style>
                body { 
                    font-family: 'Microsoft YaHei', sans-serif; 
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
                <div class="icon">⚠️</div>
                <div class="title">AI功能未执行</div>
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
            self.market_text.setHtml("<p style='color: #dc3545;'>暂无大盘分析数据</p>")
            return
            
        # 使用HTML格式的generate_market_analysis_report逻辑
        market_data = self.analysis_results_obj.market
        content = self.generate_market_analysis_report(market_data)
        self.market_text.setHtml(content)
        
    def generate_market_analysis_report(self, market_data):
        """生成市场分析报告 - HTML富文本版本，包含多空力量对比、风险评估、市场展望"""
        try:
            # MSCI指数信息
            msci_value = market_data.get('current_msci', 0)
            
            # 市场状态判断和颜色编码（红涨绿跌，红高绿低）
            if msci_value >= 70:
                market_mood = t_gui("极度乐观")
                mood_color = "#dc3545"  # 红色-乐观/高位
                risk_warning = t_gui("⚠️_高风险_市场可能过热_建议谨慎")
            elif msci_value >= 60:
                market_mood = t_gui("乐观")
                mood_color = "#ff6600"  # 橙色-偏乐观
                risk_warning = t_gui("⚡_中高风险_市场情绪偏乐观")
            elif msci_value >= 40:
                market_mood = t_gui("中性")
                mood_color = "#6c757d"  # 灰色-中性
                risk_warning = t_gui("✅_中等风险_市场相对理性")
            elif msci_value >= 30:
                market_mood = t_gui("悲观")
                mood_color = "#009900"  # 深绿色-偏悲观
                risk_warning = t_gui("📈_机会信号_市场可能接近底部")
            else:
                market_mood = t_gui("极度悲观")
                mood_color = "#28a745"  # 绿色-悲观/低位
                risk_warning = t_gui("🚀_重大机会_市场严重超跌")
            
            # 技术指标
            volatility = market_data.get('volatility', 0)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            trend_5d = market_data.get('trend_5d', 0)
            
            # 生成HTML格式的市场分析报告
            from datetime import datetime
            
            market_html = f"""
            <div style="font-family: 'Microsoft YaHei'; line-height: 1.6; color: #333;">
                <h2 style="color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 5px;">
                    📊 {t_gui('market_sentiment_analysis_report')}
                </h2>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🌐 {t_gui('core_indicators')}</h3>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('msci_market_sentiment_index')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {mood_color};"><strong>{msci_value:.2f}</strong></td></tr>
                    <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('market_sentiment')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {mood_color};"><strong>{market_mood}</strong></td></tr>
                    <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('risk_warning')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{risk_warning}</td></tr>
                </table>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">📊 {t_gui('technical_indicator_analysis')}</h3>
                <ul style="margin-left: 20px;">
                    <li><strong>{t_gui('market_volatility')}:</strong> <span style="color: {'#28a745' if volatility > 3 else '#ffc107' if volatility > 1.5 else '#dc3545'};">{volatility:.2f}%</span></li>
                    <li><strong>{t_gui('volume_ratio')}:</strong> <span style="color: {'#dc3545' if volume_ratio > 1.2 else '#ffc107' if volume_ratio > 0.8 else '#28a745'};">{volume_ratio:.2f}</span></li>
                    <li><strong>{t_gui('5_day_trend')}:</strong> <span style="color: {'#dc3545' if trend_5d > 0 else '#28a745' if trend_5d < 0 else '#6c757d'};">{trend_5d:+.2f}%</span></li>
                </ul>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">⚖️ {t_gui('bull_bear_balance')}</h3>
                <ul style="margin-left: 20px;">
                    <li><strong>{t_gui('power_analysis')}:</strong> {self.analyze_bull_bear_balance(market_data)}</li>
                    <li><strong>{t_gui('historical_trend')}:</strong> {self.analyze_historical_trend(market_data)}</li>
                </ul>
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">⚠️ {t_gui('risk_assessment')}</h3>
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
                
                <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">💡 {t_gui('investment_strategy_advice')}</h3>
                <div style="background-color: #e3f2fd; border: 1px solid #2196f3; border-radius: 6px; padding: 15px; margin: 10px 0;">
                    <p style="margin: 0; line-height: 1.8;">{self.suggest_investment_strategy(msci_value, market_mood)}</p>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-top: 25px;">
                    <h4 style="color: #856404; margin-top: 0;">🔍 {t_gui('risk_warning')}</h4>
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
            
        industries_data = self.analysis_results_obj.industries
        industry_info = industries_data.get(industry_name, {})
        
        if not industry_info:
            self.industry_detail_text.setHtml(f"<p style='color: #dc3545;'>未找到行业 {industry_name} 的详细信息</p>")
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
            strength_color = "#dc3545"  # 强势用红色
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
            strength_color = "#28a745"  # 弱势用绿色
            color_desc = "🟢"
        
        # 获取行业龙头股票
        top_stocks = self.get_top_stocks_in_industry(industry_name, 5)
        top_stocks_html = ""
        if top_stocks:
            for i, (code, name, rtsi) in enumerate(top_stocks, 1):
                stock_color = "#dc3545" if rtsi > 60 else "#ffc107" if rtsi > 40 else "#28a745"  # 红高绿低
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
        <div style="font-family: 'Microsoft YaHei'; line-height: 1.6; color: #333;">
            <h2 style="color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 5px;">
                🏭 {industry_name} 详细分析
            </h2>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">📊 {t_gui('core_indicators')}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('industry_name')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{industry_name}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('tma_index')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {strength_color};"><strong>{tma_value:.2f}</strong></td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('stock_count')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{stock_count}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('risk_level')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{risk_level}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('strength_level')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {strength_color};"><strong>{color_desc} {strength}</strong></td></tr>
            </table>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🎯 {t_gui('industry_leading_stocks')} ({t_gui('top_5_stocks')})</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #f8f9fa;">
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">{t_gui('ranking')}</th>
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">{t_gui('code')}</th>
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">{t_gui('name')}</th>
                    <th style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: left;">RTSI</th>
                </tr>
                {top_stocks_html if top_stocks_html else f'<tr><td colspan="4" style="padding: 8px; text-align: center; color: #6c757d;">{t_gui("no_data")}</td></tr>'}
            </table>
            

            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">📈 {t_gui('technical_analysis')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('trend_status')}:</strong> {self.get_industry_trend_status(tma_value)}</li>
                <li><strong>{t_gui('market_position')}:</strong> {self.get_industry_market_position(tma_value)}</li>
                <li><strong>{t_gui('allocation_value')}:</strong> {self.get_industry_allocation_value(tma_value)}</li>
            </ul>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-top: 25px;">
                <h4 style="color: #856404; margin-top: 0;">⚠️ {t_gui('risk_warning')}</h4>
                <p style="color: #856404; margin-bottom: 0; font-size: 12px;">
                    {t_gui('analysis_for_reference_only')}
                </p>
            </div>
            
            <p style="text-align: right; color: #6c757d; font-size: 12px; margin-top: 20px;">
                {t_gui('generation_time')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
        """
        
        self.industry_detail_text.setHtml(industry_html)
        
    def show_stock_detail(self, stock_code):
        """显示股票详细信息"""
        if not self.analysis_results_obj:
            return
            
        stocks_data = self.analysis_results_obj.stocks
        stock_info = stocks_data.get(stock_code, {})
        
        if not stock_info:
            self.stock_detail_text.setPlainText(t_gui("未找到股票_stock_code_的详细信息", stock_code=stock_code))
            return
            
        # 生成详细信息
        detail_lines = []
        stock_name = stock_info.get('name', stock_code)
        detail_lines.append(f"📊 {stock_name} ({stock_code}) 详细分析")
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
                detail_lines.append(f"🚀 ARTS分数: {score:.2f}")
                detail_lines.append(f"🎯 评级等级: {rating_level}")
                detail_lines.append(f"📊 趋势模式: {pattern}")
                detail_lines.append(f"🔍 置信度: {confidence}")
                detail_lines.append(f"📈 趋势方向: {trend_direction}")
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
                
                detail_lines.append(f"⚠️ 风险等级: {risk_desc}")
                detail_lines.append("")
                

                
                # 根据评级等级给出详细建议
                if '7级' in rating_level or '6级' in rating_level:
                    detail_lines.append("  • ⭐ 强烈推荐：ARTS评级优秀")
                    detail_lines.append("  • 🎯 操作策略：可积极配置")
                    detail_lines.append("  • 📈 目标：中长期持有")
                elif '5级' in rating_level or '4级' in rating_level:
                    detail_lines.append("  • ✅ 适度关注：ARTS评级良好")
                    detail_lines.append("  • 🎯 操作策略：可适量配置")
                    detail_lines.append("  • 📈 目标：观察后续表现")
                elif '3级' in rating_level or '2级' in rating_level:
                    detail_lines.append("  • 🔍 谨慎观望：ARTS评级一般")
                    detail_lines.append("  • 🎯 操作策略：减少配置")
                    detail_lines.append("  • 📈 目标：等待改善信号")
                else:
                    detail_lines.append("  • ⚠️ 建议回避：ARTS评级较低")
                    detail_lines.append("  • 🎯 操作策略：避免新增")
                    detail_lines.append("  • 📈 目标：择机减仓")
                
                if confidence in ['极低', '低']:
                    detail_lines.append("  • ⚠️ 注意：当前分析置信度较低，建议谨慎决策")
                
                detail_lines.append("")
                detail_lines.append("🔍 ARTS算法特点:")
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
                detail_lines.append(f"📈 RTSI指数: {rtsi_value:.2f}")
                
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
                    
                detail_lines.append(f"📊 趋势判断: {trend}")
                detail_lines.append(f"⚠️ 风险等级: {risk_desc}")
                detail_lines.append("")
                





                    
                detail_lines.append("")
                detail_lines.append("🔍 重要提示:")
                detail_lines.append("  • RTSI指数反映短期技术趋势强度")
                detail_lines.append("  • 投资决策还需结合基本面分析")
                detail_lines.append("  • 市场有风险，投资需谨慎")
        else:
            # 简单数值结果（兼容性处理）
            rtsi_value = float(rtsi_data) if isinstance(rtsi_data, (int, float)) else 0
            industry = stock_info.get('industry', t_gui('uncategorized'))
            
            detail_lines.append(f"🏢 所属行业: {industry}")
            detail_lines.append(f"📈 分析分数: {rtsi_value:.2f}")
            detail_lines.append("⚠️ 注意：使用简化显示模式")
        
        self.stock_detail_text.setPlainText("\n".join(detail_lines))
    
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
        
        # 即时获取并缓存量价数据
        self._prefetch_volume_price_data(stock_code)
        
        # 更新趋势图表Tab
        self.update_stock_chart(stock_code, stock_info)
        
        # 更新详细分析Tab（包含核心指标）
        self.update_detailed_stock_analysis(stock_code, stock_name, stock_info)
        
        # 更新AI分析Tab状态
        self.update_ai_analysis_tab(stock_code, stock_name)
    
    def _prefetch_volume_price_data(self, stock_code):
        """预取量价数据并缓存"""
        try:
            # 导入缓存管理器
            from cache import get_cache_manager
            
            # 获取市场类型
            preferred_market = self._get_preferred_market_from_current_data()
            if not preferred_market:
                print(f"⚠️  无法确定市场类型，跳过量价数据预取: {stock_code}")
                return
            
            # 获取缓存管理器
            cache_manager = get_cache_manager(verbose=False)
            
            # 异步预取数据（38天用于趋势图，5天用于AI分析）
            print(f"📊 开始预取量价数据: {stock_code} ({preferred_market.upper()}市场)")
            
            # 预取38天数据（趋势图用）
            volume_price_data_38 = cache_manager.get_volume_price_data(stock_code, preferred_market, 38)
            if volume_price_data_38:
                print(f"✅ 成功缓存38天量价数据: {volume_price_data_38['stock_name']} - {volume_price_data_38['total_days']}天")
            
            # 预取5天数据（AI分析用）
            volume_price_data_5 = cache_manager.get_volume_price_data(stock_code, preferred_market, 5)
            if volume_price_data_5:
                print(f"✅ 成功缓存5天量价数据: {volume_price_data_5['stock_name']} - {volume_price_data_5['total_days']}天")
            
            # 保存到实例变量供其他方法使用
            self.current_volume_price_data = {
                '38_days': volume_price_data_38,
                '5_days': volume_price_data_5,
                'market': preferred_market
            }
            
        except Exception as e:
            print(f"❌ 预取量价数据失败: {stock_code} - {e}")
            self.current_volume_price_data = None
    
    def get_cached_volume_price_data(self, stock_code: str = None, days: int = 38) -> dict:
        """
        获取缓存的量价数据（统一接口）
        
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
                print(f"🔍 [调试] 无股票代码，无法获取量价数据")
                return None
            
            # 保存当前股票代码供其他方法使用
            self.current_stock_code = stock_code
            
            # 导入缓存管理器
            from cache import get_cache_manager
            
            # 获取市场类型
            preferred_market = self._get_preferred_market_from_current_data()
            
            # 如果无法确定市场，尝试根据股票代码推断
            if not preferred_market:
                preferred_market = self._infer_market_from_stock_code(stock_code)
                if preferred_market:
                    print(f"🔍 [调试] 使用股票代码推断的市场: {preferred_market}")
                else:
                    print(f"🔍 [调试] 无法确定市场类型，尝试所有市场")
                    # 尝试所有市场
                    for market in ['cn', 'hk', 'us']:
                        try:
                            cache_manager = get_cache_manager(verbose=False)
                            result = cache_manager.get_volume_price_data(stock_code, market, days)
                            if result:
                                print(f"🔍 [调试] 在{market.upper()}市场找到数据")
                                return result
                        except:
                            continue
                    return None
            
            # 从缓存获取数据
            cache_manager = get_cache_manager(verbose=False)
            result = cache_manager.get_volume_price_data(stock_code, preferred_market, days)
            print(f"🔍 [调试] 缓存获取结果: {result is not None}, 市场: {preferred_market}")
            return result
            
        except Exception as e:
            print(f"❌ 获取缓存量价数据失败: {stock_code} - {e}")
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
                        font-family: 'Microsoft YaHei', sans-serif;
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
                    <div class="icon">📊</div>
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
            self.chart_text.setPlainText(t_gui("请选择股票查看趋势图表..."))
            
        # 清空详细分析
        if hasattr(self, 'stock_detail_text'):
            self.stock_detail_text.setPlainText(t_gui("请从左侧股票列表中选择一只股票查看详细分析"))
        
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
            self.stock_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
            

            
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
            # 初始化增强图表生成器
            try:
                from visualization.enhanced_stock_charts import EnhancedStockChartGenerator
                chart_generator = EnhancedStockChartGenerator(verbose=False)
                print(f"🔍 [调试] 成功加载EnhancedStockChartGenerator")
            except Exception as chart_import_error:
                print(f"🔍 [调试] EnhancedStockChartGenerator加载失败: {chart_import_error}")
                # 直接使用fallback方法
                self.update_stock_chart_fallback(stock_code, stock_info)
                return
            
            # 根据当前加载的数据文件推断优先市场
            preferred_market = self._get_preferred_market_from_current_data()
            print(f"🔍 [调试] update_stock_chart - preferred_market: {preferred_market}")
            
            # 验证市场参数
            if not preferred_market:
                print(f"🔍 [调试] 无法确定股票市场，将尝试默认使用cn市场")
                preferred_market = 'cn'  # 默认使用cn市场而不是抛出异常
            
            # 从统一缓存接口获取38天量价数据
            self.log(f"正在获取股票 {stock_code} 的38天量价数据（{preferred_market.upper()}市场）...")
            volume_price_data = self.get_cached_volume_price_data(stock_code, days=38)
            print(f"🔍 [调试] volume_price_data结果: {volume_price_data is not None}")
            
            # 获取评级历史数据（使用RTSI值生成，保持与TreeView一致）
            rating_data = self.generate_rtsi_based_chart_data(stock_code, rtsi_value)
            
            if volume_price_data and volume_price_data['data']:
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
                    self.log(f"✅ 成功生成增强图表：{stock_name} ({stock_code})")
                elif hasattr(self, 'chart_text'):
                    # 回退到简化HTML版本
                    self.chart_text.setHtml(self.generate_fallback_chart(stock_code, stock_name, rtsi_value, rating_data))
                    
            else:
                # 无量价数据时，显示评级趋势图
                self.log(f"⚠️ 无法获取 {stock_code} 的量价数据，仅显示评级趋势")
                fallback_html = self.generate_fallback_chart(stock_code, stock_name, rtsi_value, rating_data)
                
                if hasattr(self, 'chart_webview'):
                    self.chart_webview.setHtml(fallback_html)
                elif hasattr(self, 'chart_text'):
                    self.chart_text.setHtml(fallback_html)
                    
        except Exception as e:
            self.log(f"❌ 生成增强图表失败: {str(e)}")
            # 使用原有的图表生成方法作为备用
            self.update_stock_chart_fallback(stock_code, stock_info)
    
    def generate_fallback_chart(self, stock_code, stock_name, rtsi_value, rating_data):
        """生成备用图表HTML - 尝试获取量价数据"""
        from datetime import datetime
        
        # 尝试获取量价数据
        volume_price_available = False
        volume_price_info = ""
        try:
            # 获取市场类型
            preferred_market = self._get_preferred_market_from_current_data()
            if preferred_market:
                volume_price_data = self.get_cached_volume_price_data(stock_code, days=38)
                if volume_price_data and volume_price_data.get('data'):
                    volume_price_available = True
                    data_count = len(volume_price_data.get('data', []))
                    volume_price_info = f"已获取 {data_count} 天量价数据"
                    print(f"🔍 [调试] fallback图表中成功获取量价数据: {data_count}天")
                else:
                    print(f"🔍 [调试] fallback图表中无法获取量价数据")
            else:
                print(f"🔍 [调试] fallback图表中无法确定市场类型")
        except Exception as e:
            print(f"🔍 [调试] fallback图表获取量价数据失败: {e}")
            volume_price_available = False
        
        chart_html = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{stock_name} - 评级趋势分析</title>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', sans-serif;
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
                    <h1>📈 {stock_name} ({stock_code})</h1>
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
                
                <div class="{'warning' if not volume_price_available else 'info'}" style="{'background: #fff3cd; border: 1px solid #ffeaa7; color: #856404;' if not volume_price_available else 'background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460;'} border-radius: 8px; padding: 15px; margin: 15px 0;">
                    {('⚠️ <strong>数据说明：</strong> 无法获取该股票的量价数据，仅显示评级趋势分析。建议选择有完整数据的股票以获得最佳分析体验。') if not volume_price_available else ('📊 <strong>数据说明：</strong> ' + volume_price_info + '，显示技术指标和评级趋势分析。')}
                </div>
                
                <div class="chart-area">
                    <div class="chart-title">📊 评级趋势图（近期数据）</div>
                    <div class="ascii-chart">{self.generate_ascii_chart(rating_data) if rating_data else "暂无评级数据"}</div>
                </div>
                
                <div class="analysis-panel">
                    <h4 style="color: #1976d2; margin-top: 0;">🔍 技术分析</h4>
                    <ul style="margin-left: 20px;">
                        <li><strong>趋势方向:</strong> <span style="color: {'#28a745' if rtsi_value > 60 else '#ffc107' if rtsi_value > 40 else '#dc3545'};">{self.get_detailed_trend(rtsi_value) if hasattr(self, 'get_detailed_trend') else '分析中'}</span></li>
                        <li><strong>RTSI区间:</strong> {self.get_rtsi_zone(rtsi_value) if hasattr(self, 'get_rtsi_zone') else '计算中'}</li>
                        <li><strong>操作建议:</strong> {self.get_operation_suggestion(rtsi_value) if hasattr(self, 'get_operation_suggestion') else '评估中'}</li>
                    </ul>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 30px; color: #6c757d; font-size: 12px;">
                🕒 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                📊 数据来源: AI股票分析系统 | 
                ⚠️ 仅供参考，投资有风险
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
        <div style="font-family: 'Microsoft YaHei'; line-height: 1.6; color: #333;">
            <h2 style="color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 5px;">
                {stock_name} ({stock_code}) {t_gui('comprehensive_analysis_report')}
            </h2>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">📊 {t_gui('core_indicators')}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('stock_code')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{stock_code}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('stock_name')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{stock_name}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('industry_sector')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee;">{industry}</td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('analysis_algorithm')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {'#dc3545' if algorithm_type == 'ARTS' else '#28a745'};"><strong>🚀 {algorithm_type}</strong></td></tr>
                <tr><td style="padding: 5px; border-bottom: 1px solid #eee;"><strong>{t_gui('arts_score') if algorithm_type == 'ARTS' else t_gui('rtsi_index')}:</strong></td><td style="padding: 5px; border-bottom: 1px solid #eee; color: {'#dc3545' if rtsi_value > 50 else '#28a745'};"><strong>{rtsi_value:.2f}/100</strong></td></tr>
                {"<tr><td style='padding: 5px; border-bottom: 1px solid #eee;'><strong>" + t_gui('rating_level') + ":</strong></td><td style='padding: 5px; border-bottom: 1px solid #eee;'>" + rating_level + "</td></tr>" if algorithm_type == 'ARTS' and rating_level else ""}
                {"<tr><td style='padding: 5px; border-bottom: 1px solid #eee;'><strong>" + t_gui('trend_pattern') + ":</strong></td><td style='padding: 5px; border-bottom: 1px solid #eee;'>" + pattern + "</td></tr>" if algorithm_type == 'ARTS' and pattern else ""}
                {"<tr><td style='padding: 5px; border-bottom: 1px solid #eee;'><strong>" + t_gui('confidence_level') + ":</strong></td><td style='padding: 5px; border-bottom: 1px solid #eee;'>" + confidence_str + "</td></tr>" if algorithm_type == 'ARTS' and confidence_str else ""}

            </table>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">📈 {t_gui('technical_analysis')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('trend_direction')}:</strong> {self.get_detailed_trend(rtsi_value)}</li>
                <li><strong>{t_gui('technical_strength')}:</strong> {self.get_tech_strength(rtsi_value)}</li>
                <li><strong>{t_gui('volatility_level')}:</strong> {self.get_volatility_display(volatility)}</li>
                <li><strong>{t_gui('relative_strength')}:</strong> {t_gui('in_industry', industry=industry)}{self.get_relative_position(rtsi_value)}</li>
            </ul>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🏭 {t_gui('industry_comparison')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('行业表现')}:</strong> {sector_performance}</li>
                <li><strong>{t_gui('industry_position')}:</strong> {self.get_industry_position(rtsi_value)}</li>
                <li><strong>{t_gui('rotation_signal')}:</strong> {self.get_rotation_signal(rtsi_value)}</li>
                <li><strong>{t_gui('industry_ranking')}:</strong> {self.get_industry_ranking(rtsi_value)}</li>
            </ul>
            

            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">⚠️ {t_gui('risk_assessment')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('risk_level')}:</strong> <span style="color: {'#28a745' if rtsi_value < 30 else '#ffc107' if rtsi_value < 60 else '#dc3545'};">{self.calculate_risk_level(rtsi_value, confidence)}</span></li>
                <li><strong>{t_gui('technical_risk')}:</strong> {t_gui('based_on_rtsi_assessment')}</li>
                <li><strong>{t_gui('liquidity_risk')}:</strong> {self.get_liquidity_level_display(market_cap_level)}</li>
                <li><strong>{t_gui('market_risk')}:</strong> {t_gui('pay_attention_to_systemic_risk')}</li>
            </ul>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🎯 {t_gui('operation_advice')}</h3>
            <ul style="margin-left: 20px;">
                <li><strong>{t_gui('best_entry_point')}:</strong> {self.suggest_entry_point(rtsi_value)}</li>
                <li><strong>{t_gui('stop_loss_position')}:</strong> {self.suggest_stop_loss(rtsi_value)}</li>
                <li><strong>{t_gui('target_price')}:</strong> {self.suggest_target_price(rtsi_value)}</li>
                <li><strong>{t_gui('holding_period')}:</strong> {self.suggest_holding_period(rtsi_value)}</li>
            </ul>
            
            <h3 style="color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;">🔮 {t_gui('future_outlook')}</h3>
            <p style="margin-left: 20px; line-height: 1.8;">{self.generate_outlook_display(rtsi_value, industry)}</p>
            
            {"<h3 style='color: #2c5aa0; margin-top: 25px; margin-bottom: 15px;'>🚀 " + t_gui('arts_algorithm_advantages') + "</h3><ul style='margin-left: 20px;'><li><strong>" + t_gui('dynamic_weighting') + ":</strong> " + t_gui('recent_data_higher_weight') + "</li><li><strong>" + t_gui('pattern_recognition') + ":</strong> " + t_gui('can_identify_complex_patterns', pattern=pattern) + "</li><li><strong>" + t_gui('confidence_assessment') + ":</strong> " + t_gui('provides_reliability_assessment', confidence=confidence_str) + "</li><li><strong>" + t_gui('adaptive_adjustment') + ":</strong> " + t_gui('dynamically_optimize_based_on_characteristics') + "</li><li><strong>" + t_gui('eight_level_rating') + ":</strong> " + t_gui('more_scientific_grading_system') + "</li></ul>" if algorithm_type == 'ARTS' else ""}
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-top: 25px;">
                <h4 style="color: #856404; margin-top: 0;">⚠️ {t_gui('disclaimer')}</h4>
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
        self.stock_detail_text.setHtml(analysis_html)
    
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
        """建议持仓周期 - 支持红涨绿跌颜色"""
        if rtsi_value >= 60:
            return '<span style="color: #dc3545;">中长期1-3个月</span>'
        elif rtsi_value >= 40:
            return '<span style="color: #fd7e14;">短期1-2周</span>'
        else:
            return '<span style="color: #28a745;">不建议持有</span>'
    
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
        """基于真实RTSI生成合理的历史数据用于图表展示 - 支持90天限制"""
        import random
        import numpy as np
        from datetime import datetime, timedelta
        
        # 使用股票代码作为随机种子，确保每次生成相同的数据
        random.seed(hash(stock_code) % 2**32)
        np.random.seed(hash(stock_code) % 2**32)
        
        # 尝试获取真实历史数据
        real_data = self.get_real_historical_data(stock_code)
        
        if real_data and len(real_data) > 0:
            # 如果有数据（包括模拟数据），限制在90天内
            days = min(len(real_data), 90)
            print(f"✅ 使用历史数据天数: {days}天 (限制90天内)")
            use_real_data = True
        else:
            # 如果没有数据，返回空列表让调用方处理
            print(f"⚠️ 无历史数据，跳过图表生成")
            return []
            use_real_data = False
        
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
        
        print(f"📊 处理真实历史数据: {len(formatted_data)}个数据点")
        return formatted_data
        
    def generate_rtsi_based_chart_data(self, stock_code, current_rtsi_value):
        """基于当前RTSI值生成一致的历史评级数据（0-100范围）"""
        import random
        import numpy as np
        from datetime import datetime, timedelta
        
        # 使用股票代码作为随机种子，确保每次生成相同的数据
        random.seed(hash(stock_code) % 2**32)
        np.random.seed(hash(stock_code) % 2**32)
        
        # 生成38天的历史数据
        days = 38
        formatted_data = []
        
        # 生成日期序列（最近38天）
        end_date = datetime.now()
        for i in range(days):
            date = end_date - timedelta(days=days-1-i)
            date_str = date.strftime('%Y-%m-%d')
            
            # 基于当前RTSI值生成历史波动
            if i == days - 1:
                # 最后一天使用当前RTSI值
                rtsi_value = current_rtsi_value
            else:
                # 历史数据在当前值附近波动
                variation_range = min(20, max(5, current_rtsi_value * 0.3))  # 波动范围
                variation = random.uniform(-variation_range, variation_range)
                rtsi_value = max(0, min(100, current_rtsi_value + variation))
                
                # 添加一些趋势性：越接近当前日期，越接近当前值
                trend_factor = i / (days - 1)  # 0到1的权重
                rtsi_value = rtsi_value * (1 - trend_factor) + current_rtsi_value * trend_factor
            
            formatted_data.append((date_str, round(rtsi_value, 1)))
        
        self.log(f"📊 生成RTSI历史数据: {len(formatted_data)}个数据点，当前值: {current_rtsi_value:.1f}")
        return formatted_data
    
    def get_real_historical_data(self, stock_code):
        """获取真实的历史评级数据 - 从原始数据集中提取"""
        try:
            # 尝试从多个数据源获取真实历史数据
            print(f"🔍 正在查找股票 {stock_code} 的历史数据...")
            
            # 方法1：从analysis_results中的data_source获取（StockDataSet对象）
            if self.analysis_results and 'data_source' in self.analysis_results:
                data_source = self.analysis_results['data_source']
                if data_source and hasattr(data_source, 'get_stock_ratings'):
                    print(f"📊 尝试从data_source获取股票评级数据...")
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
                                print(f"✅ 从data_source提取到 {len(historical_data)} 个历史评级点")
                                return historical_data
                            else:
                                print(f"📊 股票 {stock_code} 在 {total_data_points} 天数据中无有效评级（全为'-'或空值）")
                    except Exception as e:
                        print(f"📊 从data_source获取失败: {e}")
            
            # 方法2：从analysis_results_obj中的data_source获取
            if self.analysis_results_obj and hasattr(self.analysis_results_obj, 'data_source'):
                data_source = self.analysis_results_obj.data_source
                if data_source and hasattr(data_source, 'get_stock_ratings'):
                    print(f"📊 尝试从analysis_results_obj.data_source获取股票评级数据...")
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
                                print(f"✅ 从analysis_results_obj.data_source提取到 {len(historical_data)} 个历史评级点")
                                return historical_data
                            else:
                                print(f"📊 股票 {stock_code} 在 {total_data_points} 天数据中无有效评级（全为'-'或空值）")
                    except Exception as e:
                        print(f"📊 从analysis_results_obj.data_source获取失败: {e}")
            
            # 方法3：尝试直接从原始数据获取（作为备用方案）
            if self.analysis_results and 'data_source' in self.analysis_results:
                data_source = self.analysis_results['data_source']
                if hasattr(data_source, 'data') and hasattr(data_source, '_metadata'):
                    print(f"📊 尝试从原始DataFrame直接获取...")
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
                        
                        print(f"📊 股票代码匹配结果: {stock_code_str} -> 找到{len(stock_row)}条记录")
                        
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
                                    print(f"✅ 从原始DataFrame提取到 {len(historical_data)} 个历史评级点")
                                    return historical_data
                    except Exception as e:
                        print(f"📊 从原始DataFrame获取失败: {e}")
            
            # 如果没有找到真实数据，返回None
            print(f"🔍 未找到股票 {stock_code} 的真实历史数据")
            return None
            
        except Exception as e:
            print(f"❌ 获取真实历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def convert_rating_to_number(self, rating_str):
        """将文字评级转换为数字评级"""
        rating_map = {
            '大多': 7, '7': 7,
            '中多': 6, '6': 6,
            '小多': 5, '5': 5,
            '微多': 4, '4': 4,
            '微空': 3, '3': 3,
            '小空': 2, '2': 2,
            '中空': 1, '1': 1,
            '大空': 0, '0': 0
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
            return "📊 暂无历史评级数据\n\n    💡 此股票在数据期间内所有评级均为空（显示为'-'）\n    📅 可能原因：\n        • 新上市股票，评级机构尚未覆盖\n        • 停牌或特殊情况期间无评级\n        • 数据源暂未包含该股票的评级信息\n    🔍 建议选择其他有评级数据的股票查看趋势图表"
        
        # 应用显示补全功能
        if enable_completion:
            chart_data = self.apply_chart_display_completion(chart_data)
        
        # 检查是否为无数据的特殊情况
        if len(chart_data) == 1 and isinstance(chart_data[0], tuple):
            first_item = chart_data[0]
            if len(first_item) >= 2 and isinstance(first_item[1], str) and "无历史评级数据" in first_item[1]:
                return "📊 暂无历史评级数据\n\n    💡 此股票尚无足够的历史评级记录\n    📅 请稍后查看或选择其他股票"
        
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
            return "📊 暂无有效的历史评级数据\n\n    💡 评级数据格式异常或无法解析\n    📅 请稍后查看或选择其他股票"
        
        # 重新构建有效的数据对
        valid_data = [(dates[i], ratings[i]) for i, rating in enumerate(ratings) 
                     if isinstance(rating, (int, float)) or 
                     (isinstance(rating, str) and self.convert_rating_to_number(rating) is not None)]
        
        if not valid_data:
            return "📊 暂无有效的历史评级数据\n\n    💡 评级数据格式异常或无法解析\n    📅 请稍后查看或选择其他股票"
        
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
            chart_lines.append("💡 图例: ● 原始数据  △ 显示补全(用最近信号延续)  │ 评级上方区间")
            chart_lines.append(f"⚠️ 最近{completion_count}天为显示补全数据，仅用于图表完整性，不用于分析")
        else:
            chart_lines.append("")
            chart_lines.append(f"💡 {t_gui('chart_legend')}: {t_gui('legend_rating_points')}  {t_gui('legend_above_rating')}  {t_gui('legend_below_rating')}")
        
        return "\n".join(chart_lines)
    
    # ================ AI分析相关方法 ================
    
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
        self.stock_ai_result_browser.setHtml(cached_result['html'])
        
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
        """执行AI智能分析 - 直接执行，无需配置检查
        
        注意：这是主AI分析功能，与行业分析和个股分析的AI功能不同
        主分析会综合大盘、行业、个股三个层面提供全面的投资分析报告
        """
        if not self.analysis_results:
            QMessageBox.warning(self, "警告", "请先完成基础分析")
            return
            
        # 防止重复分析
        if self.ai_analysis_in_progress:
            QMessageBox.information(self, "提示", "AI分析正在进行中，请稍候...")
            return
        
        try:
            self.ai_analysis_in_progress = True
            self.ai_analysis_btn.setEnabled(False)
            self.ai_analysis_btn.setText("分析中...")
            
            # 直接使用AnalysisWorker进行AI分析
            self._run_ai_analysis_with_worker()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动AI分析失败：{str(e)}")
            self._reset_ai_analysis_state()
    
    def _run_ai_analysis_with_worker(self):
        """使用AnalysisWorker运行AI分析"""
        try:
            # 获取数据文件路径
            data_file_path = ""
            if 'data_source' in self.analysis_results:
                data_source = self.analysis_results['data_source']
                if hasattr(data_source, 'file_path'):
                    data_file_path = data_source.file_path
            
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
        # 更新按钮显示进度
        if value >= 70:  # AI分析阶段
            self.ai_analysis_btn.setText(f"AI分析中...{value}%")
    
    def _on_ai_analysis_completed(self, results):
        """AI分析完成"""
        try:
            # 更新分析结果
            self.analysis_results.update(results)
            self.ai_analysis_executed = True
            
            # 重新加载HTML报告
            html_path = results.get('html_report_path')
            if html_path:
                self.analysis_results['html_report_path'] = html_path
                self._reload_ai_html(html_path)
            
            # 更新按钮状态
            self.update_ai_buttons_state()
            
            # 重置分析状态
            self._reset_ai_analysis_state()
            
            print("🎉 AI分析完成，HTML已更新")
            
        except Exception as e:
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
                print(f"📄 AI分析HTML已重新加载到WebView：{html_path}")
            elif hasattr(self, 'ai_browser'):
                # 使用文本浏览器加载
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.ai_browser.setHtml(html_content)
                print(f"📄 AI分析HTML已重新加载到TextBrowser：{html_path}")
            else:
                print("⚠️ 找不到AI显示组件")
            
        except Exception as e:
            print(f"❌ 重新加载HTML失败：{str(e)}")
    
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
                
                QMessageBox.information(self, "成功", "AI分析完成！")
            else:
                QMessageBox.warning(self, "分析失败", "AI分析未能生成有效结果")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新AI分析结果失败：{str(e)}")
        finally:
            self.ai_analysis_in_progress = False
            self.ai_analysis_btn.setEnabled(True)
            self.ai_analysis_btn.setText("AI分析")
    
    def _show_ai_analysis_error(self, error_msg):
        """显示AI分析错误"""
        print(f"❌ AI分析错误：{error_msg}")
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
            self.stock_ai_analyze_btn.setText(t_gui("🤖_分析中"))
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
        try:
            result = self._call_llm_for_stock_analysis(prompt)
            self.on_ai_analysis_finished(result)
        except Exception as e:
            self.on_ai_analysis_error(str(e))
    
    def _call_llm_for_stock_analysis(self, prompt):
        """同步调用LLM进行个股分析"""
        try:
            import sys
            import time
            from pathlib import Path
            
            # 添加llm-api到路径
            project_root = Path(__file__).parent
            llm_api_path = project_root / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # 导入LLM客户端
            from client import LLMClient
            
            # 创建LLM客户端
            client = LLMClient()
            
            start_time = time.time()
            
            # 检测当前系统语言并选择对应的指令
            from config.i18n import is_english
            use_english = is_english()
            
            # 根据系统语言选择指令
            if use_english:
                language_instruction = "Please respond in English."
                agent_id = "financial_analyst"
                system_msg = "You are a professional financial analyst with expertise in stock analysis, technical analysis, and fundamental analysis. Please respond in English and provide professional investment advice."
                user_msg = "Please analyze the following stock data and provide investment advice:\n\n" + prompt
            else:
                language_instruction = "请用中文回复。"
                agent_id = "financial_analyst"
                system_msg = "你是一位专业的中文金融分析师，精通股票分析、技术分析和基本面分析。请用中文回复，提供专业的投资建议。"
                user_msg = "请用中文分析以下股票数据并提供投资建议：\n\n" + prompt
            
            # 尝试使用智能体模式
            try:
                response = client.chat(
                    message=language_instruction + prompt,
                    agent_id=agent_id
                )
                print(f"[个股AI分析] 智能体调用成功，耗时 {time.time() - start_time:.1f}s")
            except Exception as agent_error:
                print(f"[个股AI分析] 使用智能体失败，尝试直接调用: {agent_error}")
                
                # 回退到直接调用
                response = client.chat(
                    message=user_msg,
                    system_message=system_msg
                )
                print(f"[个股AI分析] 直接调用成功，耗时 {time.time() - start_time:.1f}s")
            
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
            
            # 获取最近30天评级趋势（模拟数据）
            data['recent_ratings'] = self.get_recent_rating_trend(stock_code)
            
            # 新增：获取30天真实量价数据
            volume_price_result = self.get_volume_price_data(stock_code)
            if volume_price_result:
                data['volume_price_data'] = volume_price_result
                data['has_real_volume_price_data'] = volume_price_result.get('success', False)
                if data['has_real_volume_price_data']:
                    data['data_source_info'] = f"采用真实量价数据 ({volume_price_result.get('market', '').upper()}市场)"
                else:
                    data['data_source_info'] = f"量价数据获取失败: {volume_price_result.get('error', '未知错误')}"
            
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
    
    def _find_main_window(self):
        """查找真正的主窗口对象"""
        try:
            # 从当前widget向上查找主窗口
            widget = self
            while widget is not None:
                if hasattr(widget, 'detected_market'):
                    print(f"🔍 [调试] 找到主窗口: {type(widget).__name__}")
                    return widget
                widget = widget.parent()
            
            # 如果向上查找失败，尝试从QApplication获取主窗口
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'detected_market'):
                        print(f"🔍 [调试] 从QApplication找到主窗口: {type(widget).__name__}")
                        return widget
            
            print(f"🔍 [调试] 未找到主窗口")
            return None
        except Exception as e:
            print(f"🔍 [调试] 查找主窗口失败: {e}")
            return None
    
    def _infer_market_from_stock_code(self, stock_code: str) -> str:
        """根据股票代码推断市场类型"""
        try:
            if not stock_code:
                return None
                
            stock_code = str(stock_code).strip()
            
            # 中国股票代码特征
            if (stock_code.isdigit() and len(stock_code) == 6):
                if stock_code.startswith(('000', '001', '002', '003')):  # 深圳主板/中小板/创业板
                    return 'cn'
                elif stock_code.startswith('600') or stock_code.startswith('601') or stock_code.startswith('603') or stock_code.startswith('605'):  # 上海主板
                    return 'cn'
                elif stock_code.startswith('688'):  # 科创板
                    return 'cn'
            
            # 香港股票代码特征 (通常以00开头)
            if stock_code.isdigit() and len(stock_code) <= 5:
                if stock_code.startswith('00') or len(stock_code) <= 4:
                    return 'hk'
            
            # 美国股票代码特征 (字母代码)
            if stock_code.isalpha() or any(c.isalpha() for c in stock_code):
                return 'us'
            
            print(f"🔍 [调试] 无法从股票代码推断市场: {stock_code}")
            return None
            
        except Exception as e:
            print(f"🔍 [调试] 股票代码市场推断失败: {e}")
            return None
    
    def _get_preferred_market_from_current_data(self) -> str:
        """根据当前加载的数据文件推断优先市场"""
        try:
            # 1. 优先使用主界面检测到的市场类型（需要找到真正的主窗口）
            main_window = self._find_main_window()
            if main_window and hasattr(main_window, 'detected_market') and main_window.detected_market:
                detected_market = main_window.detected_market
                print(f"🔍 [调试] 使用主界面检测的市场类型: {detected_market.upper()}")
                return detected_market
            else:
                print(f"🔍 [调试] 主界面market检测失败: main_window={main_window}, detected_market={getattr(main_window, 'detected_market', None) if main_window else None}")
                
            # 2. 从数据文件名推断市场类型（新增强化逻辑）
            if main_window and hasattr(main_window, 'current_data_file_path') and main_window.current_data_file_path:
                file_path = main_window.current_data_file_path
                import os
                file_name = os.path.basename(file_path).lower()
                print(f"🔍 [调试] 从文件路径推断市场: {file_name}")
                
                if file_name.startswith('cn') or 'cn_data' in file_name:
                    print(f"🔍 [调试] 从文件名识别为CN市场: {file_name}")
                    return 'cn'
                elif file_name.startswith('hk') or 'hk_data' in file_name:
                    print(f"🔍 [调试] 从文件名识别为HK市场: {file_name}")
                    return 'hk'
                elif file_name.startswith('us') or 'us_data' in file_name:
                    print(f"🔍 [调试] 从文件名识别为US市场: {file_name}")
                    return 'us'
            
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
            
            # 最后尝试根据当前股票代码推断市场
            if hasattr(self, 'current_stock_code') and self.current_stock_code:
                stock_code = self.current_stock_code
                inferred_market = self._infer_market_from_stock_code(stock_code)
                if inferred_market:
                    print(f"🔍 [调试] 根据股票代码{stock_code}推断市场: {inferred_market}")
                    return inferred_market
            
            # 默认返回cn市场（而不是None）
            print("🔍 [调试] 无法确定具体市场，默认使用CN市场")
            return 'cn'
            
        except Exception as e:
            print(f"推断优先市场失败: {e}，默认使用CN市场")
            return 'cn'
    
    def get_recent_rating_trend(self, stock_code):
        """获取最近30天评级趋势"""
        # 这里应该从真实数据中获取，目前使用模拟数据
        import random
        random.seed(hash(stock_code) % 2**32)
        
        ratings = []
        rating_levels = ['大多', '中多', '小多', '微多', '微空', '小空', '中空', '大空']
        
        for i in range(30):
            if random.random() < 0.1:  # 10%概率无评级
                ratings.append('-')
            else:
                ratings.append(random.choice(rating_levels))
        
        return ratings
    
    def generate_ai_analysis_prompt(self, data):
        """生成AI分析提示词"""
        
        # 检测当前界面语言
        from config.i18n import is_english
        use_english = is_english()
        
        # 获取当前市场类型
        current_market = self._get_preferred_market_from_current_data()
        market_names = {'cn': '中国A股市场', 'hk': '香港股票市场', 'us': '美国股票市场'}
        market_name = market_names.get(current_market, '股票市场')
        
        # 构建市场特色说明
        if current_market == 'cn':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：中国A股市场
▪ 股票代码格式：6位数字（如：000001 平安银行，600036 招商银行）
▪ 推荐相关股票要求：必须使用真实存在的A股股票代码和名称
▪ 价格单位：人民币元
▪ 市场特点：T+1交易，涨跌停限制（主板±10%，创业板/科创板±20%）
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: China A-Share Market
▪ Stock Code Format: 6-digit numbers (e.g., 000001 Ping An Bank, 600036 China Merchants Bank)
▪ Related Stock Recommendation Requirement: Must use real existing A-share stock codes and names
▪ Currency Unit: Chinese Yuan (RMB)
▪ Market Features: T+1 trading, price limit (Main Board ±10%, ChiNext/STAR ±20%)
"""
        elif current_market == 'hk':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：香港股票市场（港股）
▪ 股票代码格式：5位数字（如：00700 腾讯控股，00388 香港交易所）
▪ 推荐相关股票要求：必须使用真实存在的港股股票代码和名称
▪ 价格单位：港币元
▪ 市场特点：T+0交易，无涨跌停限制
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: Hong Kong Stock Market (HKEX)
▪ Stock Code Format: 5-digit numbers (e.g., 00700 Tencent Holdings, 00388 HKEX)
▪ Related Stock Recommendation Requirement: Must use real existing Hong Kong stock codes and names
▪ Currency Unit: Hong Kong Dollar (HKD)
▪ Market Features: T+0 trading, no price limit
"""
        elif current_market == 'us':
            market_context_zh = """
【市场特色提醒】
▪ 当前分析对象：美国股票市场（美股）
▪ 股票代码格式：英文字母代码（如：AAPL 苹果公司，MSFT 微软公司）
▪ 推荐相关股票要求：必须使用真实存在的美股股票代码和名称
▪ 价格单位：美元
▪ 市场特点：T+0交易，无涨跌停限制，盘前盘后交易
"""
            market_context_en = """
【Market Context Reminder】
▪ Current Analysis Target: US Stock Market (US Market)
▪ Stock Code Format: Letter codes (e.g., AAPL Apple Inc., MSFT Microsoft Corp.)
▪ Related Stock Recommendation Requirement: Must use real existing US stock codes and names
▪ Currency Unit: US Dollar (USD)
▪ Market Features: T+0 trading, no price limit, pre/after-market trading
"""
        else:
            market_context_zh = ""
            market_context_en = ""
        
        # 构建基础提示词
        volume_price_info = ""
        data_source_note = ""
        
        # 添加量价数据部分
        if data.get('has_real_volume_price_data', False) and data.get('volume_price_data'):
            try:
                from utils.volume_price_fetcher import VolumePriceFetcher
                fetcher = VolumePriceFetcher(verbose=False)
                volume_price_info = fetcher.format_volume_price_data_for_ai(data['volume_price_data'])
                data_source_note = f"\n\n**{data.get('data_source_info', '采用真实量价数据')}**"
            except Exception as e:
                volume_price_info = f"量价数据格式化失败: {str(e)}"
        else:
            volume_price_info = f"量价数据获取失败: {data.get('data_source_info', '数据不可用')}"
        
        # 根据语言生成不同的提示词
        if use_english:
            prompt = f"""
Based on the following data, develop specific operational strategies for {data['stock_code']} {data['stock_name']}:
{market_context_en}
## Core Data
- Stock: {data['stock_code']} {data['stock_name']} ({data['industry']})
- RTSI Technical Rating: {data['rtsi']:.2f}/100
- Industry TMA Index: {data['industry_tma']:.2f}
- Market MSCI Index: {data['market_msci']:.2f}
- Market Sentiment: {data['market_sentiment']}
- Recent Rating Trend: {' → '.join(data['recent_ratings'][-5:])}

## 30-Day Volume-Price Data Analysis
{volume_price_info}

## Operational Strategy Analysis Requirements

### 1. Immediate Operational Recommendations (Percentages):
- Buy Recommendation: __% (0-100%, specific value)
- Hold Recommendation: __% (0-100%, specific value)
- Reduce Position Recommendation: __% (0-100%, specific value)
- Sell Recommendation: __% (0-100%, specific value)
*Recommendations can be adjusted flexibly based on actual conditions, not required to total 100%*

### 2. Practical Trading Guidance:
- **Entry Timing**: Specific conditions for buying and how to add positions
- **Profit-Taking Strategy**: Target price range and staged profit-taking points
- **Stop-Loss Setting**: Specific stop-loss price and response strategy
- **Position Management**: Recommended position size, suitability for heavy positions

### 3. Risk-Return Assessment:
- **Upside Probability**: Probability of rise in next 1-3 months ___%
- **Expected Returns**: Target return rate ___% to ___%
- **Downside Risk**: Maximum possible loss ___%
- **Investment Cycle**: Recommended holding period __ to __ weeks

### 4. Key Signal Monitoring:
- **Buy Signal Confirmation**: What specific indicator changes to observe
- **Sell Warning Signals**: What conditions trigger immediate position reduction or exit
- **Position Addition Opportunities**: What conditions allow for additional investment

### 5. Volume-Price Relationship Analysis (Focus):
- **Price-Volume Coordination**: Analyze recent price trends and volume matching
- **Volume Trend**: Judge volume changes' indication for future trends
- **Key Price Support**: Combine volume analysis for important support and resistance levels
- **Volume-Price Divergence Signals**: Identify divergence between price and volume

Notes:
- All recommendations must be specific and executable with clear values and steps
- Focus on practical operations, avoid theoretical explanations
- Must provide specific percentage and price recommendations (use "yuan" as currency unit)
- Give more precise technical analysis based on volume-price data
- Fully utilize 30-day real trading data for in-depth analysis
- Recommendation percentages can be adjusted flexibly based on actual conditions, not required to total 100%

**IMPORTANT: Please respond in Chinese only.**{data_source_note}
"""
        else:
            prompt = f"""
基于以下数据为{data['stock_code']} {data['stock_name']}制定具体操作策略：
{market_context_zh}
## 核心数据
- 股票：{data['stock_code']} {data['stock_name']} ({data['industry']})
- RTSI技术评级：{data['rtsi']:.2f}/100
- 行业TMA指数：{data['industry_tma']:.2f}
- 市场MSCI指数：{data['market_msci']:.2f}
- 市场情绪：{data['market_sentiment']}
- 近期评级趋势：{' → '.join(data['recent_ratings'][-5:])}

## 30天量价数据分析
{volume_price_info}

## 操作策略分析要求

### 1. 立即给出操作建议百分比：
- 买入建议：___%（0-100%，具体数值）
- 持有建议：___%（0-100%，具体数值）
- 减仓建议：___%（0-100%，具体数值）
- 卖出建议：___%（0-100%，具体数值）
*各项建议可以根据实际情况灵活调整，不要求合计为100%*

### 2. 实战操作指导：
- **入场时机**：具体什么情况下买入，买入后如何加仓
- **止盈策略**：目标价位区间，分批止盈点位
- **止损设置**：具体止损价位，止损后的应对策略
- **持仓管理**：建议仓位比例，是否适合重仓

### 3. 风险收益评估：
- **上涨概率**：未来1-3个月上涨概率___%
- **预期涨幅**：目标收益率___%至___%
- **下跌风险**：最大可能亏损___%
- **投资周期**：建议持有时间__周至__周

### 4. 关键信号监控：
- **买入信号确认**：需要观察哪些具体指标变化
- **卖出预警信号**：出现什么情况立即减仓或清仓
- **加仓机会**：什么条件下可以追加投资

### 5. 量价关系分析（重点）：
- **价量配合度**：分析最近价格走势与成交量的匹配关系
- **成交量趋势**：判断成交量变化对后续走势的指示作用
- **关键价位支撑**：结合成交量分析重要的支撑和阻力位
- **量价背离信号**：识别价格与成交量的背离现象

注意：
- 所有建议必须具体可执行，给出明确数值和操作步骤
- 重点关注实战操作，避免理论解释
- 必须给出具体的百分比和价位建议（价格单位统一使用"元"）
- 基于量价数据给出更精准的技术分析
- 充分利用30天真实交易数据进行深度分析
- 各项操作建议比例可以根据实际情况灵活调整，不要求加起来等于100%

**重要：请用中文回复所有内容。**{data_source_note}
"""
        
        return prompt
    
    def on_ai_analysis_finished(self, result):
        """AI分析完成回调"""
        try:
            # 生成HTML格式的结果
            html_result = self.format_ai_analysis_result(result)
            
            # 显示结果
            self.stock_ai_result_browser.setHtml(html_result)
            
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
            self.stock_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
            self.ai_status_label.setText("")
    
    def on_ai_analysis_error(self, error_message):
        """AI分析错误回调"""
        error_html = f"""
        <div style="text-align: center; color: #dc3545; margin-top: 50px;">
            <h3>❌ AI分析失败</h3>
            <p>{error_message}</p>
            <p style="font-size: 12px; color: #666;">请检查网络连接和AI配置，然后重试</p>
        </div>
        """
        
        self.stock_ai_result_browser.setHtml(error_html)
        
        # 切换到结果页面显示错误
        if hasattr(self, 'ai_stacked_widget'):
            self.ai_stacked_widget.setCurrentIndex(1)
        
        # 重置状态
        self.ai_analysis_in_progress = False
        self.current_ai_stock = None
        self.stock_ai_analyze_btn.setEnabled(True)
        self.stock_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
        self.ai_status_label.setText("")
    
    def format_ai_analysis_result(self, result):
        """格式化AI分析结果为HTML"""
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
                    <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 5px; margin-bottom: 15px; text-align: center;">
                        <strong>📊 {data_source_info}</strong>
                    </div>
                    """
                else:
                    error_info = self.current_analysis_data.get('data_source_info', '量价数据不可用')
                    data_source_badge = f"""
                    <div style="background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 10px; border-radius: 5px; margin-bottom: 15px; text-align: center;">
                        <strong>⚠️ 量价数据获取失败：{error_info}</strong>
                    </div>
                    """
            
            html = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; margin: 20px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .stock-info {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                    .analysis-content {{ background: white; padding: 20px; border-radius: 8px; }}
                    .recommendation {{ background: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; margin-top: 20px; }}
                    .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-top: 20px; }}
                    h1 {{ color: #0078d4; }}
                    h2 {{ color: #2c5aa0; }}
                    .timestamp {{ font-size: 12px; color: #666; text-align: right; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🤖 AI股票分析报告</h1>
                    <div class="stock-info">
                        <h2>{stock_info} - 智能投资建议</h2>
                        <div class="timestamp">{t_gui("分析时间:")}: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</div>
                    </div>
                </div>
                
                {data_source_badge}
                
                <div class="analysis-content">
                    {self._format_analysis_text(result)}
                </div>
                
                <div class="warning">
                    <strong>⚠️ 风险提示：</strong>本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。请结合自身情况和市场变化做出投资决策。
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            return f"<p>格式化结果失败: {str(e)}</p><pre>{result}</pre>"
    
    def _format_analysis_text(self, text):
        """格式化分析文本"""
        try:
            # 简单的文本格式化
            formatted = text.replace('\n\n', '</p><p>')
            formatted = formatted.replace('\n', '<br/>')
            formatted = f"<p>{formatted}</p>"
            
            # 突出显示关键词
            keywords = ['买入', '卖出', '持有', '减仓', '建议', '风险', '机会']
            for keyword in keywords:
                formatted = formatted.replace(keyword, f"<strong style='color: #dc3545;'>{keyword}</strong>")
            
            return formatted
            
        except Exception:
            return f"<pre>{text}</pre>"
    
    def update_ai_analysis_tab(self, stock_code, stock_name):
        """更新AI分析Tab状态"""
        if not hasattr(self, 'ai_stacked_widget'):
            return
            
        # 检查当前是否在AI分析Tab
        current_tab_index = self.stock_tab_widget.currentIndex()
        
        if stock_code in self.stock_ai_cache:
            # 有缓存
            if current_tab_index == 2:  # 如果当前就在AI分析Tab
                # 直接显示结果页
                self.show_cached_ai_result(stock_code)
            # 如果不在AI分析Tab，等待用户切换到该Tab时自动显示
        else:
            # 无缓存，重置到分析按钮页
            self.ai_stacked_widget.setCurrentIndex(0)
            self.stock_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
            self.stock_ai_analyze_btn.setEnabled(True)
            self.ai_status_label.setText("")
    
    def on_industry_tab_changed(self, index):
        """行业Tab切换事件处理 - 当切换到AI分析Tab时自动显示缓存"""
        try:
            # 检查是否切换到AI分析Tab（第2个Tab，索引为1）
            if index == 1 and hasattr(self, 'current_industry_name') and self.current_industry_name:
                # 如果有当前行业且有缓存，自动显示缓存结果
                cached_result = self.industry_ai_cache.get(self.current_industry_name)
                if cached_result:
                    # 切换到结果页面并显示缓存的结果（格式化为HTML）
                    self.industry_ai_stacked_widget.setCurrentIndex(1)
                    html_result = self.format_industry_ai_analysis_result(cached_result, self.current_industry_name)
                    self.industry_ai_result_browser.setHtml(html_result)
                else:
                    # 没有缓存，显示分析按钮页面
                    self.industry_ai_stacked_widget.setCurrentIndex(0)
                    # 更新按钮状态
                    if hasattr(self, 'industry_ai_analyze_btn'):
                        self.industry_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
                        self.industry_ai_analyze_btn.setEnabled(True)
                    if hasattr(self, 'industry_ai_status_label'):
                        self.industry_ai_status_label.setText("")
        except Exception as e:
            print(f"行业Tab切换处理失败: {str(e)}")

    def on_stock_tab_changed(self, index):
        """股票Tab切换事件处理 - 当切换到AI分析Tab时自动显示缓存"""
        try:
            # 检查是否切换到AI分析Tab（第3个Tab，索引为2）
            if index == 2 and hasattr(self, 'current_stock_code') and self.current_stock_code:
                # 如果有当前股票且有缓存，自动显示缓存结果
                if self.current_stock_code in self.stock_ai_cache:
                    print(f"[Tab切换] 自动显示{self.current_stock_code}的缓存AI分析")
                    self.show_cached_ai_result(self.current_stock_code)
                    
        except Exception as e:
            print(f"[Tab切换] 处理AI分析Tab切换失败: {e}")
    
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
        """获取指定行业中前N个RTSI最大的股票"""
        if not self.analysis_results_obj:
            return []
            
        stocks_data = self.analysis_results_obj.stocks
        industry_stocks = []
        
        for stock_code, stock_info in stocks_data.items():
            stock_industry = stock_info.get('industry', '')
            if stock_industry == industry_name:
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
            self.industry_ai_analyze_btn.setText(t_gui("🤖_分析中"))
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
        try:
            result = self._call_llm_for_industry_analysis(prompt)
            self.on_industry_ai_analysis_finished(result)
        except Exception as e:
            self.on_industry_ai_analysis_error(str(e))
    
    def _call_llm_for_industry_analysis(self, prompt):
        """同步调用LLM进行行业分析"""
        try:
            import sys
            import time
            from pathlib import Path
            
            # 添加llm-api到路径
            project_root = Path(__file__).parent
            llm_api_path = project_root / "llm-api"
            if str(llm_api_path) not in sys.path:
                sys.path.insert(0, str(llm_api_path))
            
            # 导入LLM客户端
            from client import LLMClient
            
            # 创建LLM客户端
            client = LLMClient()
            
            start_time = time.time()
            
            # 检测当前系统语言并选择对应的指令
            from config.i18n import is_english
            use_english = is_english()
            
            # 根据系统语言选择指令
            if use_english:
                language_instruction = "Please respond in English."
                agent_id = "financial_analyst"
                system_msg = "You are a professional financial analyst with expertise in industry analysis, technical analysis, and macroeconomic analysis. Please respond in English and provide professional industry investment advice."
                user_msg = "Please analyze the following industry data and provide investment advice:\n\n" + prompt
            else:
                language_instruction = "请用中文回复。"
                agent_id = "financial_analyst"
                system_msg = "你是一位专业的中文金融分析师，精通行业分析、技术分析和宏观经济分析。请用中文回复，提供专业的行业投资建议。"
                user_msg = "请用中文分析以下行业数据并提供投资建议：\n\n" + prompt
            
            # 尝试使用智能体模式
            try:
                response = client.chat(
                    message=language_instruction + prompt,
                    agent_id=agent_id
                )
                print(f"[行业AI分析] 智能体调用成功，耗时 {time.time() - start_time:.1f}s")
            except Exception as agent_error:
                print(f"[行业AI分析] 使用智能体失败，尝试直接调用: {agent_error}")
                
                # 回退到直接调用
                response = client.chat(
                    message=user_msg,
                    system_message=system_msg
                )
                print(f"[行业AI分析] 直接调用成功，耗时 {time.time() - start_time:.1f}s")
            
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
                        # 按RTSI排序获取前5只股票，只包含RTSI > 0的股票
                        stock_list = []
                        for code, stock_info in stocks.items():
                            rtsi_data = stock_info.get('rtsi', {})
                            rtsi_value = rtsi_data.get('rtsi', 0) if isinstance(rtsi_data, dict) else float(rtsi_data) if rtsi_data else 0
                            
                            # 只收集RTSI > 5的个股
                            if rtsi_value > 5:
                                stock_list.append({
                                    'code': code,
                                    'name': stock_info.get('name', code),
                                    'rtsi': rtsi_value
                                })
                        
                        # 排序并取前5只
                        stock_list.sort(key=lambda x: x['rtsi'], reverse=True)
                        data['top_stocks'] = stock_list[:5]
                
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
        """生成行业AI分析提示词 - 专门针对行业分析"""
        
        # 检测当前界面语言
        from config.i18n import is_english
        use_english = is_english()
        
        # 获取当前市场类型
        current_market = self._get_preferred_market_from_current_data()
        market_names = {'cn': '中国A股市场', 'hk': '香港股票市场', 'us': '美国股票市场'}
        market_name = market_names.get(current_market, '股票市场')
        
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
            # 构建顶级股票信息 - 英文版
            top_stocks_info = ""
            if top_stocks:
                top_stocks_info = "\nQuality stocks in the industry (sorted by RTSI):\n"
                for i, stock in enumerate(top_stocks, 1):
                    top_stocks_info += f"{i}. {stock['name']}({stock['code']}) - RTSI: {stock['rtsi']:.2f}\n"
            
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
Please focus on analyzing quality individual stock investment opportunities within the {industry_name} industry:

1. 【In-depth Analysis of Industry Leading Stocks】(Key Focus)
   - Detailed analysis of investment value and buying timing for the above recommended stocks
   - Evaluate competitive position and moats of each stock in the {industry_name} industry
   - Analyze technical indicators, fundamental advantages, and growth potential of individual stocks
   - Provide specific operational recommendations for individual stocks (buy price, profit-taking, stop-loss, etc.)

2. 【Individual Stock Portfolio Construction】(Key Focus)
   - Build a {industry_name} industry investment portfolio based on the above stocks
   - Analyze risk-return characteristics and correlation of different stocks
   - Provide weight recommendations and staged position building strategies for individual stocks
   - Set risk control measures and dynamic adjustment plans for the portfolio

3. 【Industry Background Brief】(Brief)
   - Briefly analyze current trends in the {industry_name} industry (TMA Index {tma_index:.2f})
   - Outline main driving factors and investment logic of the industry

4. 【Individual Stock Selection Strategy】(Key Focus)
   - Screen 3-5 stocks with the highest investment value from recommended stocks
   - Analyze short-term and medium-term investment opportunities for each stock
   - Provide specific investment timeframes and expected returns for individual stocks
   - Develop stock rotation and switching strategies

Note: Focus on investment opportunities for individual stocks within the {industry_name} industry, with industry macro analysis as background support.
Please provide specific actionable individual stock investment recommendations, including buying timing, target prices, and risk control measures.

【Important: Stock Recommendation Authenticity Requirements】
• All recommended stocks must be real existing stocks in {market_name}
• Stock codes and names must be accurate and correct, not fabricated or invented
• When recommending stocks, must follow {current_market.upper()} market code format standards

**IMPORTANT: Please respond in Chinese only.**
"""
        else:
            # 构建顶级股票信息 - 中文版
            top_stocks_info = ""
            if top_stocks:
                top_stocks_info = "\n行业内优质股票（按RTSI排序）：\n"
                for i, stock in enumerate(top_stocks, 1):
                    top_stocks_info += f"{i}. {stock['name']}({stock['code']}) - RTSI: {stock['rtsi']:.2f}\n"
            
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

{t_gui("分析对象")}：{industry_name}
{t_gui("分析时间：")} {analysis_time}
{market_context_zh}
===== 核心数据 =====
• 行业TMA指数：{tma_index:.2f} ({tma_level})
• 行业股票数量：{stock_count}只
• 大盘MSCI指数：{market_msci:.2f}
• 市场情绪：{market_sentiment}
• 初步投资建议：{investment_tendency}

{top_stocks_info}

===== 分析要求 =====
请重点分析{industry_name}行业内的优质个股投资机会：

1. 【行业龙头股票深度分析】（重点）
   - 详细分析上述推荐个股的投资价值和买入时机
   - 评估各个股在{industry_name}行业中的竞争地位和护城河
   - 分析个股的技术指标、基本面优势和成长潜力
   - 提供具体的个股操作建议（买入价位、止盈止损等）

2. 【个股投资组合构建】（重点）
   - 基于上述个股构建{industry_name}行业投资组合
   - 分析不同个股的风险收益特征和相关性
   - 提供个股配置权重建议和分批建仓策略
   - 设定组合的风险控制措施和动态调整方案

3. 【行业背景简析】（简要）
   - 简要分析{industry_name}行业当前趋势（TMA指数{tma_index:.2f}）
   - 概述行业主要驱动因素和投资逻辑

4. 【个股精选策略】（重点）
   - 从推荐个股中筛选出最具投资价值的3-5只
   - 分析各个股的短期、中期投资机会
   - 提供具体的个股投资时间框架和预期收益
   - 制定个股轮动和换股策略

注：重点关注{industry_name}行业内个股的投资机会，行业宏观分析作为背景支撑。
请提供具体可操作的个股投资建议，包括买入时机、目标价位（价格统一使用"元"作为单位）和风险控制措施。

【重要：股票推荐真实性要求】
• 推荐的所有股票必须是{market_name}真实存在的股票
• 股票代码和名称必须准确无误，不得虚构或编造
• 推荐股票时务必遵循{current_market.upper()}市场的代码格式规范

**重要：请用中文回复所有内容。**
"""
        
        return prompt.strip()
    
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
                <style>
                    body {{ 
                        font-family: 'Microsoft YaHei', sans-serif; 
                        line-height: 1.6; 
                        margin: 20px; 
                        background-color: #f9f9f9;
                    }}
                    .header {{ 
                        text-align: center; 
                        margin-bottom: 30px; 
                        background: linear-gradient(135deg, #007bff, #0056b3);
                        color: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    }}
                    .industry-info {{ 
                        background: #e3f2fd; 
                        padding: 15px; 
                        border-radius: 8px; 
                        margin-bottom: 20px; 
                        border-left: 4px solid #007bff;
                    }}
                    .analysis-content {{
                        background: white;
                        padding: 25px;
                        border-radius: 10px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        margin-bottom: 20px;
                    }}
                    .footer {{ 
                        text-align: center; 
                        font-size: 12px; 
                        color: #666; 
                        margin-top: 30px; 
                        padding: 15px;
                        background: #f8f9fa;
                        border-radius: 8px;
                    }}
                    h1 {{ color: white; margin: 0; font-size: 24px; }}
                    h2 {{ color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
                    h3 {{ color: #0056b3; }}
                    strong {{ color: #dc3545; }}
                    .highlight {{ background-color: #fff3cd; padding: 2px 4px; border-radius: 3px; }}
                    .recommendation {{ 
                        background: #d4edda; 
                        border: 1px solid #c3e6cb; 
                        border-radius: 5px; 
                        padding: 10px; 
                        margin: 10px 0; 
                    }}
                    .risk-warning {{ 
                        background: #f8d7da; 
                        border: 1px solid #f5c6cb; 
                        border-radius: 5px; 
                        padding: 10px; 
                        margin: 10px 0; 
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{t_gui("🤖_行业AI智能分析报告", industry_name=industry_name)}</h1>
                    <p style="margin: 5px 0;">{t_gui("分析时间：")} {current_time}</p>
                </div>
                
                <div class="industry-info">
                    <h3>{t_gui("📊 分析说明")}</h3>
                    <p>{t_gui("本报告基于行业TMA指数、市场情绪和优质股票数据，运用AI技术进行深度分析，为您提供专业的行业投资建议。")}</p>
                </div>
                
                <div class="analysis-content">
                    {formatted_text}
                </div>
                
                <div class="footer">
                    <p><strong>{t_gui("免责声明：")}</strong>{t_gui("本分析报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。")}</p>
                    <p>{t_gui("报告生成时间：")} {current_time} | {t_gui("AI股票大师系统")}</p>
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
            self.industry_ai_result_browser.setHtml(html_result)
            self.industry_ai_stacked_widget.setCurrentIndex(1)  # 切换到结果页面
            
            # 重置按钮状态
            self.industry_ai_analysis_in_progress = False
            self.industry_ai_analyze_btn.setEnabled(True)
            self.industry_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
            self.industry_ai_status_label.setText(t_gui("✅_分析完成"))
            
            print(f"[行业AI分析] {self.current_industry_name} 分析完成")
            
        except Exception as e:
            self.on_industry_ai_analysis_error(f"处理分析结果失败：{str(e)}")
    
    def on_industry_ai_analysis_error(self, error_message):
        """行业AI分析错误回调"""
        error_html = f"""
        <div style="text-align: center; color: #dc3545; margin-top: 50px;">
            <h3>🔍 行业AI分析失败</h3>
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
        self.industry_ai_result_browser.setHtml(error_html)
        self.industry_ai_stacked_widget.setCurrentIndex(1)  # 切换到结果页面显示错误
        
        # 重置按钮状态
        self.industry_ai_analysis_in_progress = False
        self.industry_ai_analyze_btn.setEnabled(True)
        self.industry_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
        self.industry_ai_status_label.setText("")
        
        print(f"❌ 行业AI分析错误：{error_message}")
    
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
                        self.industry_ai_result_browser.setHtml(html_result)
                        self.industry_ai_stacked_widget.setCurrentIndex(1)  # 显示结果页
                    print(f"[行业AI分析] {industry_name} 已有缓存，准备显示结果")
                else:
                    # 无缓存：重置到首页（分析按钮页）
                    self.industry_ai_stacked_widget.setCurrentIndex(0)  # 显示分析按钮页
                    
                    # 重置按钮状态
                    if hasattr(self, 'industry_ai_analyze_btn'):
                        self.industry_ai_analyze_btn.setText(t_gui("🚀_开始AI分析"))
                        self.industry_ai_analyze_btn.setEnabled(True)
                    if hasattr(self, 'industry_ai_status_label'):
                        self.industry_ai_status_label.setText("")
                    
                    print(f"[行业AI分析] {industry_name} 无缓存，显示首页")
                    
        except Exception as e:
            print(f"更新行业AI分析Tab状态失败: {str(e)}")


class LoadingDialog(QWidget):
    """加载对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("正在分析...")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self.setWindowModality(Qt.ApplicationModal)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 状态标签
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 12))
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        # 居中显示
        self.center_window()
        
    def center_window(self):
        """窗口居中"""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
        
    def update_progress(self, value: int, text: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(text)


class NewPyQt5Interface(QMainWindow):
    """新的PyQt5股票分析界面主窗口"""
    
    def __init__(self, no_update=False):
        super().__init__()
        
        self.analysis_worker = None
        self.loading_dialog = None
        self.no_update = no_update
        
        # 根据参数决定是否执行开机启动更新数据文件
        if not self.no_update:
            self.startup_update_data_files()
        else:
            print("🚫 跳过数据文件检查（--NoUpdate参数已启用）")
        
        self.setup_ui()
        
    def startup_update_data_files(self):
        """开机启动更新数据文件功能"""
        try:
            print("正在检查数据文件更新...")
            from utils.data_updater import auto_update_data_files
            
            # 同步执行更新，等待检查更新结束
            try:
                # 检查并更新数据文件（cn_data5000/hk_data1000/us_data1000）
                update_success = auto_update_data_files(parent=None, show_progress=False)
                if update_success:
                    print("✅ 数据文件更新成功")
                else:
                    print("ℹ️ 数据文件已是最新版本")
            except Exception as e:
                print(f"⚠️ 数据更新失败: {e}")
                print("将继续使用现有数据文件")
            
            print("数据文件检查完成，继续启动程序...")
            
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
        self.setGeometry(100, 100, 1280, 720)  # 减小高度到780
        
        # 设置窗口字体 - 与行业分析标题一致
        self.setFont(QFont("Microsoft YaHei", 14))
        
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
        
        # 添加到堆叠部件
        self.stacked_widget.addWidget(self.file_page)
        self.stacked_widget.addWidget(self.analysis_page)
        
        # 设置布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)
        central_widget.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)
        
    def on_file_selected(self, file_path: str):
        """文件选择后的处理"""
        if not MODULES_AVAILABLE:
            QMessageBox.critical(self, "错误", 
                               "项目模块不可用，请检查Python环境和依赖包安装。")
            return
        
        # 根据文件名前缀识别市场类型
        import os
        file_name = os.path.basename(file_path).lower()
        detected_market = self._detect_market_from_filename(file_name)
        
        # 保存检测到的市场类型，供后续使用
        self.detected_market = detected_market
        self.current_data_file_path = file_path
        
        print(f"检测到数据文件市场类型: {detected_market.upper()}")
            
        # 创建并显示加载对话框
        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()
        
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
        if self.loading_dialog:
            self.loading_dialog.update_progress(value, text)
            
    def on_analysis_completed(self, results: Dict[str, Any]):
        """分析完成"""
        # 关闭加载对话框
        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None
            
        # 更新分析页面的结果
        self.analysis_page.update_analysis_results(results)
        
        # 切换到分析页面
        self.stacked_widget.setCurrentWidget(self.analysis_page)
        
    def on_analysis_failed(self, error_msg: str):
        """分析失败"""
        # 关闭加载对话框
        if self.loading_dialog:
            self.loading_dialog.close()
            self.loading_dialog = None
            
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
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AI股票大师 - 智能股票分析工具')
    parser.add_argument('--NoUpdate', action='store_true', 
                       help='跳过启动时的数据文件检查和更新（cn_data5000等6个文件）')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName(t_gui('app_name'))
    app.setApplicationVersion(t_gui('app_version'))
    app.setOrganizationName("AI Stock Master")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 创建主窗口，传递NoUpdate参数
    window = NewPyQt5Interface(no_update=args.NoUpdate)
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
