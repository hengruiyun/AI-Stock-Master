#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强股票图表生成器 - 统一版本
基于cn-lj.dat.gz量价数据和评级数据，设计用户真正需要的图表
合并了V1、V2、V3的最佳特性，保留最稳定和高效的实现

作者：AI Assistant
版本：4.0.0 (统一版本)
"""

import os
import sys
import json
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 导入数据读取模块
try:
    from utils.lj_data_reader import StockSearchTool
except ImportError:
    print("警告: 无法导入lj数据读取模块，图表功能将不可用")
    StockSearchTool = None

# 添加国际化支持
try:
    from config.gui_i18n import t_gui
    USE_I18N = True
except ImportError:
    USE_I18N = False
    def t_gui(key, **kwargs):
        return key

def is_english_system():
    """检测系统语言是否为英文"""
    try:
        from config.gui_i18n import get_system_language
        return get_system_language() == 'en'
    except:
        import locale
        try:
            lang = locale.getdefaultlocale()[0]
            return lang and lang.lower().startswith('en')
        except:
            return False

def t_common(key, **kwargs):
    """图表专用国际化函数"""
    if not USE_I18N:
        return key
    
    is_english = is_english_system()
    
    # 中文翻译
    chinese_fallbacks = {
        'enhanced_chart_title': '智能投资分析图表',
        'volume_price_analysis': '量价分析',
        'rating_trend_analysis': '评级趋势分析',
        'performance_comparison': '表现对比分析',
        'technical_indicators': '技术指标',
        'market_sentiment': '市场情绪',
        'risk_assessment': '风险评估',
        'closing_price': '收盘价',
        'volume': '成交量',
        'rating': '评级',
        'stock_code': '股票代码',
        'stock_name': '股票名称',
        'current_rtsi_rating': '当前RTSI评级',
        'data_days': '数据天数',
        'data_source': '数据来源',
        'real_volume_price_data': '真实量价数据',
        'market': '市场',
        'days': '天',
        'data_update_time': '数据更新时间',
        'data_from': '数据来源',
        'ai_stock_analysis_system': 'AI股票分析系统',
        'investment_risk_warning': '本系统所有内容均为测试数据，仅供学习和研究使用。投资有风险，决策需谨慎。',
        'date': '日期',
        'price_yuan': '价格(元)',
        'volume_unit': '成交量',
        'rating_score': '评级分数',
        'bullish_zone': '看涨区间',
        'neutral_zone': '中性区间', 
        'bearish_zone': '看跌区间',
        'price_change_rate': '价格变化率',
        'volume_change_rate': '成交量变化率',
        'rating_stability': '评级稳定性',
        'trend_strength': '趋势强度',
        'support_resistance': '支撑阻力',
        'momentum_indicator': '动量指标'
    }
    
    # 英文翻译
    english_fallbacks = {
        'enhanced_chart_title': 'Smart Investment Analysis Charts',
        'volume_price_analysis': 'Volume & Price Analysis',
        'rating_trend_analysis': 'Rating Trend Analysis',
        'performance_comparison': 'Performance Comparison',
        'technical_indicators': 'Technical Indicators',
        'market_sentiment': 'Market Sentiment',
        'risk_assessment': 'Risk Assessment',
        'closing_price': 'Closing Price',
        'volume': 'Volume',
        'rating': 'Rating',
        'stock_code': 'Stock Code',
        'stock_name': 'Stock Name',
        'current_rtsi_rating': 'Current RTSI Rating',
        'data_days': 'Data Days',
        'data_source': 'Data Source',
        'real_volume_price_data': 'Real Volume & Price Data',
        'market': ' Market',
        'days': ' Days',
        'data_update_time': 'Data Update Time',
        'data_from': 'Data From',
        'ai_stock_analysis_system': 'AI Stock Analysis System',
        'investment_risk_warning': 'All content in this system is test data for learning and research purposes only. Investment involves risks, please make decisions carefully.',
        'date': 'Date',
        'price_yuan': 'Price (Yuan)',
        'volume_unit': 'Volume',
        'rating_score': 'Rating Score',
        'bullish_zone': 'Bullish Zone',
        'neutral_zone': 'Neutral Zone', 
        'bearish_zone': 'Bearish Zone',
        'price_change_rate': 'Price Change Rate',
        'volume_change_rate': 'Volume Change Rate',
        'rating_stability': 'Rating Stability',
        'trend_strength': 'Trend Strength',
        'support_resistance': 'Support & Resistance',
        'momentum_indicator': 'Momentum Indicator'
    }
    
    fallbacks = english_fallbacks if is_english else chinese_fallbacks
    return fallbacks.get(key, key).format(**kwargs)

class EnhancedStockChartGeneratorV3:
    """增强股票图表生成器 - 统一版本的图表系统"""
    
    def __init__(self, verbose: bool = True, specific_rating_file: str = None):
        self.verbose = verbose
        self.search_tool = StockSearchTool(verbose=verbose) if StockSearchTool else None
        self.specific_rating_file = specific_rating_file  # 指定使用的评级数据文件
        
        # 本地Chart.js文件路径
        self.chartjs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'js', 'chart.min.js')
        self.date_adapter_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'js', 'chartjs-adapter-date-fns.bundle.min.js')
        
        # 评级映射
        self.rating_map = {
            '中多': 80, '小多': 70, '微多': 60,
            '-': 50,
            '微空': 40, '小空': 30, '中空': 20
        }
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level}: {message}")
    
    def _get_local_chartjs_content(self) -> str:
        """获取本地Chart.js文件内容"""
        try:
            if os.path.exists(self.chartjs_path):
                with open(self.chartjs_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.log(f"本地Chart.js文件不存在: {self.chartjs_path}", "WARNING")
                return "console.error('本地Chart.js文件未找到');"
        except Exception as e:
            self.log(f"读取本地Chart.js文件失败: {e}", "ERROR")
            return "console.error('读取本地Chart.js文件失败');"
    
    def _get_local_date_adapter_content(self) -> str:
        """获取本地日期适配器文件内容"""
        try:
            if os.path.exists(self.date_adapter_path):
                with open(self.date_adapter_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.log(f"本地日期适配器文件不存在: {self.date_adapter_path}", "WARNING")
                return "console.error('本地日期适配器文件未找到');"
        except Exception as e:
            self.log(f"读取本地日期适配器文件失败: {e}", "ERROR")
            return "console.error('读取本地日期适配器文件失败');"
    
    def _load_rating_data(self, stock_code: str) -> List[Tuple[str, str]]:
        """从评级数据文件中加载指定股票的评级数据"""
        try:
            # 确定要使用的评级数据文件
            if self.specific_rating_file and os.path.exists(self.specific_rating_file):
                rating_files = [self.specific_rating_file]
                self.log(f"使用指定的评级数据文件: {self.specific_rating_file}", "INFO")
            else:
                # 查找评级数据文件
                import glob
                rating_files = glob.glob('*Data*.json.gz')
                self.log(f"未指定评级文件，搜索所有评级文件: {rating_files}", "INFO")
            
            for file in rating_files:
                try:
                    self.log(f"尝试从{file}加载股票{stock_code}的评级数据", "DEBUG")
                    with gzip.open(file, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if 'data' in data:
                        for record in data['data']:
                            if record.get('股票代码') == stock_code:
                                # 提取评级数据
                                rating_data = []
                                for key, value in record.items():
                                    if key.isdigit() and len(key) == 8:  # 日期格式YYYYMMDD
                                        if value and value != '-':
                                            rating_data.append((key, value))
                                
                                if rating_data:
                                    # 按日期排序并返回最近的数据
                                    rating_data.sort(key=lambda x: x[0])
                                    self.log(f"从{file}找到股票{stock_code}的{len(rating_data)}条评级数据，日期范围: {rating_data[0][0]} - {rating_data[-1][0]}", "INFO")
                                    return rating_data[-60:]  # 返回最近60天的数据
                                else:
                                    self.log(f"股票{stock_code}在{file}中没有有效评级数据", "DEBUG")
                                
                except Exception as e:
                    self.log(f"读取评级文件{file}失败: {e}", "WARNING")
                    continue
            
            self.log(f"未找到股票{stock_code}的评级数据", "WARNING")
            return []
            
        except Exception as e:
            self.log(f"加载评级数据失败: {e}", "ERROR")
            return []
    
    def _calculate_technical_indicators(self, volume_price_data: List[Dict]) -> Dict:
        """计算技术指标"""
        if len(volume_price_data) < 5:
            return {}
        
        prices = [item['close_price'] for item in volume_price_data]
        volumes = [item['volume'] for item in volume_price_data]
        
        # 计算移动平均线
        ma5 = []
        ma10 = []
        ma20 = []
        
        for i in range(len(prices)):
            if i >= 4:
                ma5.append(sum(prices[i-4:i+1]) / 5)
            else:
                ma5.append(prices[i])
                
            if i >= 9:
                ma10.append(sum(prices[i-9:i+1]) / 10)
            else:
                ma10.append(prices[i])
                
            if i >= 19:
                ma20.append(sum(prices[i-19:i+1]) / 20)
            else:
                ma20.append(prices[i])
        
        # 计算价格变化率
        price_changes = []
        for i in range(1, len(prices)):
            change_rate = (prices[i] - prices[i-1]) / prices[i-1] * 100
            price_changes.append(change_rate)
        price_changes.insert(0, 0)  # 第一天变化率为0
        
        # 计算成交量变化率
        volume_changes = []
        for i in range(1, len(volumes)):
            if volumes[i-1] > 0:
                change_rate = (volumes[i] - volumes[i-1]) / volumes[i-1] * 100
                volume_changes.append(change_rate)
            else:
                volume_changes.append(0)
        volume_changes.insert(0, 0)  # 第一天变化率为0
        
        return {
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'price_changes': price_changes,
            'volume_changes': volume_changes
        }
    
    def generate_enhanced_html_chart(self, stock_code: str, stock_name: str, 
                                   volume_price_data: List[Dict], 
                                   rating_data: List[Tuple], 
                                   current_rtsi: float = 0,
                                   market: str = None) -> str:
        """生成重新设计的HTML图表"""
        
        # 准备国际化文本
        i18n_texts = {
            'enhanced_chart_title': t_common('enhanced_chart_title'),
            'volume_price_analysis': t_common('volume_price_analysis'),
            'rating_trend_analysis': t_common('rating_trend_analysis'),
            'performance_comparison': t_common('performance_comparison'),
            'technical_indicators': t_common('technical_indicators'),
            'stock_code': t_common('stock_code'),
            'stock_name': t_common('stock_name'),
            'current_rtsi_rating': t_common('current_rtsi_rating'),
            'data_days': t_common('data_days'),
            'data_source': t_common('data_source'),
            'real_volume_price_data': t_common('real_volume_price_data'),
            'market': t_common('market'),
            'days': t_common('days'),
            'closing_price': t_common('closing_price'),
            'volume': t_common('volume'),
            'rating': t_common('rating'),
            'data_update_time': t_common('data_update_time'),
            'data_from': t_common('data_from'),
            'ai_stock_analysis_system': t_common('ai_stock_analysis_system'),
            'investment_risk_warning': t_common('investment_risk_warning'),
            'date': t_common('date'),
            'price_yuan': t_common('price_yuan'),
            'volume_unit': t_common('volume_unit'),
            'rating_score': t_common('rating_score'),
            'price_change_rate': t_common('price_change_rate'),
            'volume_change_rate': t_common('volume_change_rate'),
            'trend_strength': t_common('trend_strength'),
            'momentum_indicator': t_common('momentum_indicator')
        }
        
        # 处理市场信息显示
        market_display = ""
        if market:
            market_name_map = {
                'cn': 'CN', 'hk': 'HK', 'us': 'US',
                'china': 'CN', 'hongkong': 'HK', 'america': 'US'
            }
            market_code = market_name_map.get(market.lower(), market.upper())
            market_display = f"""
            <div class="info-item">
                <div class="info-label">{i18n_texts['data_source']}</div>
                <div class="info-value" style="color: #28a745;">📊 {i18n_texts['real_volume_price_data']} ({market_code}{i18n_texts['market']})</div>
            </div>"""
        
        # 加载更多评级数据
        extended_rating_data = self._load_rating_data(stock_code)
        if extended_rating_data:
            rating_data = extended_rating_data
        
        # 计算技术指标
        technical_indicators = self._calculate_technical_indicators(volume_price_data)
        
        # 转换评级数据为数值
        rating_data_numeric = [(item[0], self.rating_map.get(item[1], 50)) for item in rating_data] if rating_data else []
        
        # 获取本地Chart.js内容
        chartjs_content = self._get_local_chartjs_content()
        date_adapter_content = self._get_local_date_adapter_content()
        
        # 生成HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{stock_name} - {i18n_texts['enhanced_chart_title']}</title>
    
    <!-- 本地Chart.js -->
    <script>
        {chartjs_content}
    </script>
    
    <!-- 本地日期适配器 -->
    <script>
        {date_adapter_content}
    </script>
    
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
            font-size: 28px;
            font-weight: bold;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 16px;
            margin-top: 10px;
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
        
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}
        
        .chart-wrapper {{
            background: #ffffff;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .chart-wrapper.full-width {{
            grid-column: 1 / -1;
        }}
        
        .chart-title {{
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}
        
        .chart-canvas {{
            max-height: 350px;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            margin-top: 15px;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 4px;
            border-radius: 2px;
        }}
        
        .analysis-summary {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        
        .summary-title {{
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .summary-content {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .summary-item {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }}
        
        .summary-item-title {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .summary-item-value {{
            color: #6c757d;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <div class="header">
            <h1>{stock_name} ({stock_code})</h1>
            <div class="subtitle">{i18n_texts['enhanced_chart_title']}</div>
        </div>
        
        <div class="stock-info">
            <div class="info-item">
                <div class="info-label">{i18n_texts['stock_code']}</div>
                <div class="info-value">{stock_code}</div>
            </div>
            <div class="info-item">
                <div class="info-label">{i18n_texts['stock_name']}</div>
                <div class="info-value">{stock_name}</div>
            </div>
            <div class="info-item">
                <div class="info-label">{i18n_texts['current_rtsi_rating']}</div>
                <div class="info-value" style="color: #e74c3c;">{current_rtsi:.1f}</div>
            </div>
            <div class="info-item">
                <div class="info-label">{i18n_texts['data_days']}</div>
                <div class="info-value">{len(volume_price_data)}{i18n_texts['days']}</div>
            </div>{market_display}
        </div>
        
        <div class="charts-grid">
            <!-- 图表1：量价关系分析 -->
            <div class="chart-wrapper">
                <div class="chart-title">📊 {i18n_texts['volume_price_analysis']}</div>
                <canvas id="volumePriceChart" class="chart-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: #3498db;"></div>
                        <span>{i18n_texts['closing_price']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: rgba(52, 152, 219, 0.3);"></div>
                        <span>{i18n_texts['volume']}</span>
                    </div>
                </div>
            </div>
            
            <!-- 图表2：评级趋势与稳定性 -->
            <div class="chart-wrapper">
                <div class="chart-title">📈 {i18n_texts['rating_trend_analysis']}</div>
                <canvas id="ratingTrendChart" class="chart-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: #e74c3c;"></div>
                        <span>{i18n_texts['rating_score']}</span>
                    </div>
                    </div>
                    </div>
            
            <!-- 图表3：技术指标综合分析 -->
            <div class="chart-wrapper full-width">
                <div class="chart-title">📊 {i18n_texts['technical_indicators']}</div>
                <canvas id="technicalChart" class="chart-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: #3498db;"></div>
                        <span>{i18n_texts['closing_price']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #f39c12;"></div>
                        <span>MA5</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #e74c3c;"></div>
                        <span>MA10</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #9b59b6;"></div>
                        <span>MA20</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 分析总结 -->
        <div class="analysis-summary">
            <div class="summary-title">📋 智能分析总结</div>
            <div class="summary-content">
                <div class="summary-item">
                    <div class="summary-item-title">价格趋势</div>
                    <div class="summary-item-value" id="priceTrendSummary">分析中...</div>
                </div>
                <div class="summary-item">
                    <div class="summary-item-title">成交量状态</div>
                    <div class="summary-item-value" id="volumeStatusSummary">分析中...</div>
                </div>
                <div class="summary-item">
                    <div class="summary-item-title">评级稳定性</div>
                    <div class="summary-item-value" id="ratingStabilitySummary">分析中...</div>
                </div>
                <div class="summary-item">
                    <div class="summary-item-title">技术面强度</div>
                    <div class="summary-item-value" id="technicalStrengthSummary">分析中...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 等待DOM加载完成
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('DOM加载完成，开始初始化图表');
            
            // 检查Chart.js是否可用
            if (typeof Chart === 'undefined') {{
                console.error('Chart.js未加载');
                document.body.innerHTML = '<div style="text-align: center; padding: 50px;"><h2>Chart.js加载失败</h2><p>请检查网络连接或刷新页面</p></div>';
                return;
            }}
            
            console.log('Chart.js已加载，开始创建图表');
            initializeAllCharts();
        }});
        
        function initializeAllCharts() {{
            try {{
                // 准备数据
                const volumePriceData = {json.dumps(volume_price_data)};
                const ratingData = {json.dumps(rating_data_numeric)};
                const technicalData = {json.dumps(technical_indicators)};
                
                // 图表1：量价关系分析
                createVolumePriceChart(volumePriceData);
                
                // 图表2：评级趋势分析
                createRatingTrendChart(ratingData);
                
                // 图表3：技术指标分析
                createTechnicalChart(volumePriceData, technicalData);
                
                // 生成分析总结
                generateAnalysisSummary(volumePriceData, ratingData, technicalData);
                
                console.log('所有图表创建完成');
                
            }} catch (error) {{
                console.error('图表创建失败:', error);
                document.body.innerHTML = '<div style="text-align: center; padding: 50px;"><h2>图表创建失败</h2><p>错误: ' + error.message + '</p><button onclick="location.reload()">刷新页面</button></div>';
            }}
        }}
        
        function createVolumePriceChart(data) {{
            const ctx = document.getElementById('volumePriceChart').getContext('2d');
            new Chart(ctx, {{
            type: 'line',
            data: {{
                    labels: data.map(item => item.date),
                datasets: [{{
                        label: '{i18n_texts['closing_price']}',
                        data: data.map(item => item.close_price),
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y',
                    tension: 0.4,
                        fill: true
                }}, {{
                        label: '{i18n_texts['volume']}',
                        data: data.map(item => item.volume),
                        borderColor: 'rgba(52, 152, 219, 0.3)',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y1',
                    tension: 0.4,
                        fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                            title: {{ display: true, text: '{i18n_texts['price_yuan']}' }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                            title: {{ display: true, text: '{i18n_texts['volume_unit']}' }},
                            grid: {{ drawOnChartArea: false }}
                    }}
                }},
                plugins: {{
                        legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            title: function(tooltipItems) {{
                                return '日期: ' + tooltipItems[0].label;
                            }},
                            label: function(context) {{
                                if (context.datasetIndex === 0) {{
                                    return '收盘价: ¥' + context.parsed.y.toFixed(2);
                                }} else {{
                                    return '成交量: ' + context.parsed.y.toLocaleString();
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }});
        }}
        
        function createRatingTrendChart(data) {{
            const ctx = document.getElementById('ratingTrendChart').getContext('2d');
            
            // 检查数据是否为空
            if (!data || data.length === 0) {{
                // 显示"无评级数据"提示
                ctx.canvas.parentNode.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;"><h3>📊 暂无评级数据</h3><p>该股票暂无有效的评级历史数据</p></div>';
                return;
            }}
            
            new Chart(ctx, {{
            type: 'line',
            data: {{
                    labels: data.map(item => item[0]),
                datasets: [{{
                        label: '{i18n_texts['rating_score']}',
                        data: data.map(item => item[1]),
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    pointBackgroundColor: function(context) {{
                            // 安全检查context.parsed
                            if (!context.parsed || context.parsed.y === undefined) return '#666';
                            const value = context.parsed.y;
                            if (value >= 60) return '#dc3545';
                            else if (value >= 40) return '#ffc107';
                            else return '#28a745';
                        }},
                    tension: 0.4,
                        fill: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                        y: {{
                        min: 0,
                        max: 100,
                            title: {{ display: true, text: '{i18n_texts['rating_score']}' }}
                    }}
                }},
                plugins: {{
                        legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                    // 安全检查context.parsed
                                    if (!context.parsed || context.parsed.y === undefined) return '无数据';
                                    const rating = context.parsed.y;
                                    let zone = '';
                                    if (rating >= 60) zone = '看涨区间';
                                    else if (rating >= 40) zone = '中性区间';
                                    else zone = '看跌区间';
                                    return '评级: ' + rating + ' - ' + zone;
                            }}
                        }}
                    }}
                }}
            }}
                }});
            }}
        
        function createTechnicalChart(priceData, techData) {{
            const ctx = document.getElementById('technicalChart').getContext('2d');
            new Chart(ctx, {{
            type: 'line',
            data: {{
                    labels: priceData.map(item => item.date),
                datasets: [{{
                        label: '{i18n_texts['closing_price']}',
                        data: priceData.map(item => item.close_price),
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4
                    }}, {{
                        label: 'MA5',
                        data: techData.ma5 || [],
                        borderColor: '#f39c12',
                        backgroundColor: 'transparent',
                        tension: 0.4
                    }}, {{
                        label: 'MA10',
                        data: techData.ma10 || [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'transparent',
                        tension: 0.4
                    }}, {{
                        label: 'MA20',
                        data: techData.ma20 || [],
                        borderColor: '#9b59b6',
                        backgroundColor: 'transparent',
                        tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                        y: {{
                            title: {{ display: true, text: '{i18n_texts['price_yuan']}' }}
                    }}
                }},
                plugins: {{
                        legend: {{ display: false }}
                }}
            }}
        }});
        }}
        
        function generateAnalysisSummary(priceData, ratingData, techData) {{
            // 价格趋势分析
            const prices = priceData.map(item => item.close_price);
            const priceChange = ((prices[prices.length-1] - prices[0]) / prices[0] * 100).toFixed(2);
            const priceTrend = priceChange > 5 ? '强势上涨' : priceChange > 0 ? '温和上涨' : priceChange > -5 ? '震荡整理' : '下跌趋势';
            document.getElementById('priceTrendSummary').textContent = priceTrend + ' (' + priceChange + '%)';
            
            // 成交量状态
            const volumes = priceData.map(item => item.volume);
            const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;
            const recentVolume = volumes.slice(-5).reduce((a, b) => a + b, 0) / 5;
            const volumeStatus = recentVolume > avgVolume * 1.2 ? '放量' : recentVolume < avgVolume * 0.8 ? '缩量' : '正常';
            document.getElementById('volumeStatusSummary').textContent = volumeStatus;
            
            // 评级稳定性
            if (ratingData && ratingData.length > 0) {{
                const ratings = ratingData.map(item => item[1]);
                const ratingStd = Math.sqrt(ratings.reduce((sum, rating) => sum + Math.pow(rating - ratings.reduce((a, b) => a + b, 0) / ratings.length, 2), 0) / ratings.length);
                const stability = ratingStd < 10 ? '非常稳定' : ratingStd < 20 ? '较稳定' : '波动较大';
                document.getElementById('ratingStabilitySummary').textContent = stability;
            }} else {{
                document.getElementById('ratingStabilitySummary').textContent = '无评级数据';
            }}
            
            // 技术面强度
            const currentPrice = prices[prices.length-1];
            const ma5Current = techData.ma5 ? techData.ma5[techData.ma5.length-1] : currentPrice;
            const ma20Current = techData.ma20 ? techData.ma20[techData.ma20.length-1] : currentPrice;
            const strength = currentPrice > ma5Current && ma5Current > ma20Current ? '强势' : 
                           currentPrice > ma20Current ? '中性偏强' : '偏弱';
            document.getElementById('technicalStrengthSummary').textContent = strength;
        }}
    </script>
    
    <div style="text-align: center; margin-top: 30px; color: white; font-size: 12px;">
        🕒 {i18n_texts['data_update_time']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        📊 {i18n_texts['data_from']}: {i18n_texts['ai_stock_analysis_system']} | 
        ⚠️ {i18n_texts['investment_risk_warning']}
    </div>
</body>
</html>
        """
        
        return html_content

def main():
    """测试主函数"""
    generator = EnhancedStockChartGeneratorV3()
    
    # 注意：不再生成随机数据，使用固定示例数据
    from datetime import datetime, timedelta
    
    example_volume_price_data = [
        {'date': '20250115', 'close_price': 12.0, 'volume': 1500000000, 'open_price': 11.9, 'high_price': 12.1, 'low_price': 11.8},
        {'date': '20250116', 'close_price': 12.1, 'volume': 1600000000, 'open_price': 12.0, 'high_price': 12.2, 'low_price': 11.9}
    ]
    example_rating_data = [
        ('20250115', '中多'),
        ('20250116', '小多')
    ]
    
    # 生成HTML图表
    html_content = generator.generate_enhanced_html_chart(
        "00001",
        "长和",
        example_volume_price_data,
        example_rating_data,
        66.5,
        'hk'
    )
    
    # 保存到文件
    output_file = "enhanced_chart_v3_redesigned.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"重新设计的图表已保存到: {output_file}")
    print("请在浏览器中打开查看效果")

if __name__ == "__main__":
    main()
