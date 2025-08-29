#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强股票图表生成器
用于生成美观的HTML图表，包含量价走势和评级趋势图

作者：AI Assistant
版本：1.0.0
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from ljs import StockSearchTool

# 添加国际化支持 - 支持中英文动态切换
def is_english_system():
    """检测系统语言是否为英文"""
    import locale
    import os
    import sys
    
    try:
        # 尝试导入系统的语言检测
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from config.i18n import is_english
        return is_english()
    except ImportError:
        pass
    
    # 备用检测方法：通过环境变量和locale
    # 检查环境变量
    lang = os.getenv('LANG', '').lower()
    if 'en' in lang:
        return True
    
    # 检查系统locale
    try:
        system_locale = locale.getdefaultlocale()[0]
        if system_locale and 'en' in system_locale.lower():
            return True
    except:
        pass
    
    # Windows系统检查
    if os.name == 'nt':
        try:
            import ctypes
            windll = ctypes.windll.kernel32
            lang_id = windll.GetUserDefaultUILanguage()
            # 英文语言ID (1033=en-US, 2057=en-GB等)
            return lang_id in [1033, 2057, 3081, 4105, 5129, 6153, 7177, 8201, 9225, 10249, 11273, 12297]
        except:
            pass
            
    return False  # 默认中文

def t_common(key, **kwargs):
    """图表专用国际化函数"""
    is_english = is_english_system()
    
    # 中文翻译
    chinese_fallbacks = {
        'enhanced_chart_title': '综合走势分析',
        'days_volume_price_chart': '天量价走势图',
        'rtsi_detailed_trend': 'RTSI评级详细趋势',
        'closing_price': '收盘价',
        'volume': '成交量',
        'rtsi_rating': 'RTSI评级 (0-100)',
        'strong_uptrend': '强势上升',
        'mild_uptrend': '温和上升', 
        'sideways': '震荡整理',
        'mild_downtrend': '弱势下降',
        'strong_downtrend': '强势下降',
        'price_trend': '价格趋势',
        'volume_analysis': '成交量分析',
        'rating_trend': '评级走势',
        'investment_advice': '投资建议',
        'technical_analysis_summary': '技术分析摘要',
        'data_source': '数据来源',
        'real_volume_price_data': '真实量价数据',
        'market': '市场',
        'stock_code': '股票代码',
        'stock_name': '股票名称',
        'current_rtsi_rating': '当前RTSI评级',
        'data_days': '数据天数',
        'date': '日期',
        'days': '天',
        'data_update_time': '数据更新时间',
        'data_from': '数据来源',
        'investment_risk_warning': '仅供参考，投资有风险',
        'ai_stock_analysis_system': 'AI股票分析系统',
        'bullish_zone': '看涨区间',
        'neutral_zone': '中性区间', 
        'bearish_zone': '看跌区间'
    }
    
    # 英文翻译
    english_fallbacks = {
        'enhanced_chart_title': 'Comprehensive Trend Analysis',
        'days_volume_price_chart': 'Days Volume & Price Chart',
        'rtsi_detailed_trend': 'RTSI Rating Detailed Trend',
        'closing_price': 'Closing Price',
        'volume': 'Volume',
        'rtsi_rating': 'RTSI Rating (0-100)',
        'strong_uptrend': 'Strong Uptrend',
        'mild_uptrend': 'Mild Uptrend', 
        'sideways': 'Sideways',
        'mild_downtrend': 'Mild Downtrend',
        'strong_downtrend': 'Strong Downtrend',
        'price_trend': 'Price Trend',
        'volume_analysis': 'Volume Analysis',
        'rating_trend': 'Rating Trend',
        'investment_advice': 'Investment Advice',
        'technical_analysis_summary': 'Technical Analysis Summary',
        'data_source': 'Data Source',
        'real_volume_price_data': 'Real Volume & Price Data',
        'market': ' Market',
        'stock_code': 'Stock Code',
        'stock_name': 'Stock Name',
        'current_rtsi_rating': 'Current RTSI Rating',
        'data_days': 'Data Days',
        'date': 'Date',
        'days': ' Days',
        'data_update_time': 'Data Update Time',
        'data_from': 'Data From',
        'investment_risk_warning': 'For reference only, investment involves risks',
        'ai_stock_analysis_system': 'AI Stock Analysis System',
        'bullish_zone': 'Bullish Zone',
        'neutral_zone': 'Neutral Zone', 
        'bearish_zone': 'Bearish Zone'
    }
    
    fallbacks = english_fallbacks if is_english else chinese_fallbacks
    return fallbacks.get(key, key).format(**kwargs)

class EnhancedStockChartGenerator:
    """增强股票图表生成器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.search_tool = StockSearchTool(verbose=verbose)
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level}: {message}")
    
    def get_volume_price_data(self, stock_code: str, days: int = 38, market: str = None) -> Optional[Dict[str, Any]]:
        """获取指定天数的量价数据"""
        try:
            # 验证市场参数
            if not market:
                raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
            
            self.log(f"获取股票 {stock_code} 最近 {days} 天的量价数据（{market.upper()}市场）")
            
            # 确保股票代码是清理过的格式（不包含="符号）
            if stock_code.startswith('="') and stock_code.endswith('"'):
                clean_code = stock_code[2:-1]
            else:
                clean_code = stock_code
            
            # 使用ljs.py的搜索工具获取数据（新接口要求必须指定市场）
            results = self.search_tool.search_stock_by_code(clean_code, market, days)
            
            if not results:
                self.log(f"未找到股票 {stock_code} 的数据", "WARNING")
                return None
            
            # 获取第一个市场的数据
            first_market_data = list(results.values())[0]
            data = first_market_data.get('数据', {})
            trade_data = data.get('交易数据', {})
            
            if not trade_data:
                self.log(f"股票 {stock_code} 无交易数据", "WARNING")
                return None
            
            # 清理股票代码格式
            raw_code = first_market_data['股票代码']
            clean_stock_code = self.search_tool.clean_stock_code(raw_code)
            
            # 转换为便于处理的格式
            volume_price_data = []
            for date, day_data in sorted(trade_data.items()):
                volume_price_data.append({
                    'date': date,
                    'close_price': day_data.get('收盘价', 0),
                    'volume': day_data.get('成交金额', 0),
                    'open_price': day_data.get('开盘价', day_data.get('收盘价', 0)),
                    'high_price': day_data.get('最高价', day_data.get('收盘价', 0)),
                    'low_price': day_data.get('最低价', day_data.get('收盘价', 0))
                })
            
            result = {
                'market': first_market_data['市场'],
                'stock_code': clean_stock_code,  # 使用清理后的代码
                'stock_name': first_market_data['股票名称'],
                'total_days': len(volume_price_data),
                'data': volume_price_data
            }
            
            self.log(f"成功获取 {len(volume_price_data)} 天的量价数据")
            return result
            
        except Exception as e:
            self.log(f"获取量价数据失败: {str(e)}", "ERROR")
            return None
    
    def generate_enhanced_html_chart(self, stock_code: str, stock_name: str, 
                                   volume_price_data: List[Dict], 
                                   rating_data: List[Tuple], 
                                   current_rtsi: float = 0,
                                   market: str = None) -> str:
        """生成增强的HTML图表"""
        
        # 准备数据
        chart_data = self.prepare_chart_data(volume_price_data, rating_data)
        
        # 准备国际化文本 - 所有需要的文本都预先翻译
        i18n_texts = {
            'enhanced_chart_title': t_common('enhanced_chart_title'),
            'days': t_common('days'),
            'stock_code': t_common('stock_code'),
            'stock_name': t_common('stock_name'),
            'current_rtsi_rating': t_common('current_rtsi_rating'),
            'data_days': t_common('data_days'),
            'data_source': t_common('data_source'),
            'real_volume_price_data': t_common('real_volume_price_data'),
            'market': t_common('market'),
            'days_volume_price_chart': t_common('days_volume_price_chart'),
            'closing_price': t_common('closing_price'),
            'volume': t_common('volume'),
            'rtsi_detailed_trend': t_common('rtsi_detailed_trend'),
            'rtsi_rating': t_common('rtsi_rating'),
            'strong_uptrend': t_common('strong_uptrend'),
            'mild_uptrend': t_common('mild_uptrend'),
            'sideways': t_common('sideways'),
            'mild_downtrend': t_common('mild_downtrend'),
            'strong_downtrend': t_common('strong_downtrend'),
            'technical_analysis_summary': t_common('technical_analysis_summary'),
            'price_trend': t_common('price_trend'),
            'volume_analysis': t_common('volume_analysis'),
            'rating_trend': t_common('rating_trend'),
            'investment_advice': t_common('investment_advice'),
            'data_update_time': t_common('data_update_time'),
            'data_from': t_common('data_from'),
            'ai_stock_analysis_system': t_common('ai_stock_analysis_system'),
            'investment_risk_warning': t_common('investment_risk_warning'),
            'date': t_common('date'),
            'closing_price_yuan': f"{t_common('closing_price')} (元)",
            'bullish_zone': t_common('bullish_zone'),
            'neutral_zone': t_common('neutral_zone'),
            'bearish_zone': t_common('bearish_zone')
        }
        
        # 处理市场信息显示
        market_display = ""
        if market:
            market_name_map = {
                'cn': 'CN',
                'hk': 'HK', 
                'us': 'US',
                'china': 'CN',
                'hongkong': 'HK',
                'america': 'US'
            }
            market_code = market_name_map.get(market.lower(), market.upper())
            market_display = f"""
            <div class="info-item">
                <div class="info-label">{i18n_texts['data_source']}</div>
                <div class="info-value" style="color: #28a745;">📊 {i18n_texts['real_volume_price_data']} ({market_code}{i18n_texts['market']})</div>
            </div>"""
        
        # 生成HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{stock_name} - {i18n_texts['enhanced_chart_title']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
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
            grid-template-columns: 1fr;
            gap: 30px;
        }}
        
        .chart-wrapper {{
            background: #fefefe;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}
        
        .chart-title {{
            color: #2c3e50;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 20px;
            text-align: center;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .chart-canvas {{
            max-height: 400px;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }}
        
        .analysis-panel {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        
        .analysis-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            text-align: center;
        }}
        
        .analysis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .analysis-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 15px;
            backdrop-filter: blur(10px);
        }}
        
        .rating-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin: 2px;
        }}
        
        .rating-strong-buy {{ background: #dc3545; color: white; }}
        .rating-buy {{ background: #fd7e14; color: white; }}
        .rating-hold {{ background: #6c757d; color: white; }}
        .rating-sell {{ background: #28a745; color: white; }}
        .rating-strong-sell {{ background: #198754; color: white; }}
        
        @media (max-width: 768px) {{
            .stock-info {{
                flex-direction: column;
                gap: 15px;
            }}
            
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <div class="header">
            <h1>📈 {stock_name} ({stock_code})</h1>
            <div class="subtitle">{len(volume_price_data)}{i18n_texts['days']}{i18n_texts['enhanced_chart_title']}</div>
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
                <div class="info-value" style="color: {self.get_rtsi_color(current_rtsi)}">{current_rtsi:.2f}</div>
            </div>
            <div class="info-item">
                <div class="info-label">{i18n_texts['data_days']}</div>
                <div class="info-value">{len(volume_price_data)}{i18n_texts['days']}</div>
            </div>{market_display}
        </div>
        
        <div class="charts-grid">
            <!-- 量价走势图 -->
            <div class="chart-wrapper">
                <div class="chart-title">📊 {len(volume_price_data)}{i18n_texts['days_volume_price_chart']}</div>
                <canvas id="volumePriceChart" class="chart-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: #2196F3;"></div>
                        <span>{i18n_texts['closing_price']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #FF9800;"></div>
                        <span>{i18n_texts['volume']}</span>
                    </div>
                </div>
            </div>
            
            <!-- RTSI趋势详细图 -->
            <div class="chart-wrapper">
                <div class="chart-title">📊 {i18n_texts['rtsi_detailed_trend']}</div>
                <canvas id="gradeChart" class="chart-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background: linear-gradient(90deg, #dc3545 0%, #fd7e14 25%, #ffc107 50%, #6c757d 75%, #198754 100%);"></div>
                        <span>{i18n_texts['rtsi_rating']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #dc3545;"></div>
                        <span>80+ {i18n_texts['strong_uptrend']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #fd7e14;"></div>
                        <span>60-80 {i18n_texts['mild_uptrend']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #6c757d;"></div>
                        <span>40-60 {i18n_texts['sideways']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #28a745;"></div>
                        <span>20-40 {i18n_texts['mild_downtrend']}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #198754;"></div>
                        <span>0-20 {i18n_texts['strong_downtrend']}</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="analysis-panel">
            <div class="analysis-title">🔍 {i18n_texts['technical_analysis_summary']}</div>
            <div class="analysis-grid">
                <div class="analysis-card">
                    <h4>{i18n_texts['price_trend']}</h4>
                    <p>{self.analyze_price_trend(volume_price_data)}</p>
                </div>
                <div class="analysis-card">
                    <h4>{i18n_texts['volume_analysis']}</h4>
                    <p>{self.analyze_volume_trend(volume_price_data)}</p>
                </div>
                <div class="analysis-card">
                    <h4>{i18n_texts['rating_trend']}</h4>
                    <p>{self.analyze_rating_trend(rating_data)}</p>
                </div>
                <div class="analysis-card">
                    <h4>{i18n_texts['investment_advice']}</h4>
                    <p>{self.generate_investment_advice(current_rtsi)}</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 量价走势图
        const volumePriceCtx = document.getElementById('volumePriceChart').getContext('2d');
        const volumePriceChart = new Chart(volumePriceCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps([item['date'] for item in volume_price_data])},
                datasets: [{{
                    label: '收盘价',
                    data: {json.dumps([item['close_price'] for item in volume_price_data])},
                    borderColor: '#2196F3',
                    backgroundColor: 'rgba(33, 150, 243, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y'
                }}, {{
                    label: '成交量',
                    data: {json.dumps([item['volume'] for item in volume_price_data])},
                    borderColor: '#FF9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false,
                }},
                scales: {{
                    x: {{
                        display: true,
                        title: {{
                            display: true,
                            text: '{i18n_texts['date']}'
                        }}
                    }},
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: '{i18n_texts['closing_price_yuan']}'
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: '{i18n_texts['volume']}'
                        }},
                        grid: {{
                            drawOnChartArea: false,
                        }},
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
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

        // RTSI趋势详细图（与TreeView保持一致的0-100范围）
        const gradeCtx = document.getElementById('gradeChart').getContext('2d');
        
        // 获取RTSI评级数据（0-100范围）
        const rtsiDates = {json.dumps([item[0] for item in rating_data]) if rating_data else '[]'};
        const rtsiValues = {json.dumps([item[1] for item in rating_data]) if rating_data else '[]'};
        
        // 定义RTSI值的颜色映射（红涨绿跌体系）
        function getRtsiColor(rtsi) {{
            if (rtsi >= 80) return '#dc3545';      // 强势上升 - 深红色
            else if (rtsi >= 60) return '#fd7e14'; // 温和上升 - 橙色
            else if (rtsi >= 40) return '#6c757d'; // 震荡整理 - 灰色
            else if (rtsi >= 20) return '#28a745'; // 弱势下降 - 绿色
            else return '#198754';                 // 强势下降 - 深绿色
        }}
        
        function getRtsiLevel(rtsi) {{
            if (rtsi >= 80) return '{i18n_texts['strong_uptrend']}';
            else if (rtsi >= 60) return '{i18n_texts['mild_uptrend']}';
            else if (rtsi >= 40) return '{i18n_texts['sideways']}';
            else if (rtsi >= 20) return '{i18n_texts['mild_downtrend']}';
            else return '{i18n_texts['strong_downtrend']}';
        }}
        
        const gradeChart = new Chart(gradeCtx, {{
            type: 'line',
            data: {{
                labels: rtsiDates,
                datasets: [{{
                    label: 'RTSI评级',
                    data: rtsiValues,
                    borderColor: function(context) {{
                        if (context.dataIndex >= 0) {{
                            return getRtsiColor(rtsiValues[context.dataIndex]);
                        }}
                        return '#4CAF50';
                    }},
                    backgroundColor: function(context) {{
                        if (context.dataIndex >= 0) {{
                            const color = getRtsiColor(rtsiValues[context.dataIndex]);
                            return color + '20'; // 添加透明度
                        }}
                        return 'rgba(76, 175, 80, 0.1)';
                    }},
                    pointBackgroundColor: function(context) {{
                        if (context.dataIndex >= 0) {{
                            return getRtsiColor(rtsiValues[context.dataIndex]);
                        }}
                        return '#4CAF50';
                    }},
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    fill: true,
                    tension: 0.4,
                    segment: {{
                        borderColor: function(ctx) {{
                            const fromIndex = ctx.p0DataIndex;
                            const toIndex = ctx.p1DataIndex;
                            const fromRtsi = rtsiValues[fromIndex];
                            const toRtsi = rtsiValues[toIndex];
                            
                            // 根据趋势设置连线颜色：红涨绿跌
                            if (toRtsi > fromRtsi) {{
                                return '#dc3545'; // 上升趋势用红色
                            }} else if (toRtsi < fromRtsi) {{
                                return '#28a745'; // 下降趋势用绿色  
                            }} else {{
                                return '#6c757d'; // 平稳用灰色
                            }}
                        }}
                    }}
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                scales: {{
                    x: {{
                        display: true,
                        title: {{
                            display: true,
                            text: '{i18n_texts['date']}'
                        }}
                    }},
                    y: {{
                        display: true,
                        title: {{
                            display: true,
                            text: '{i18n_texts['rtsi_rating']}'
                        }},
                        min: 0,
                        max: 100,
                        ticks: {{
                            stepSize: 20,
                            callback: function(value) {{
                                if (value === 80) return value + ' ({i18n_texts['strong_uptrend']})';
                                else if (value === 60) return value + ' ({i18n_texts['mild_uptrend']})';
                                else if (value === 40) return value + ' ({i18n_texts['sideways']})';
                                else if (value === 20) return value + ' ({i18n_texts['mild_downtrend']})';
                                else if (value === 0) return value + ' ({i18n_texts['strong_downtrend']})';
                                else return value;
                            }}
                        }},
                        grid: {{
                            color: function(context) {{
                                // 关键分界线使用特殊颜色
                                const value = context.tick.value;
                                if (value === 50) return 'rgba(255, 193, 7, 0.8)'; // 中性线
                                else if (value === 80 || value === 60 || value === 40 || value === 20) {{
                                    return 'rgba(108, 117, 125, 0.5)'; // 等级分界线
                                }}
                                return 'rgba(0,0,0,0.1)';
                            }},
                            lineWidth: function(context) {{
                                if (context.tick.value === 50) return 2; // 中性线加粗
                                return 1;
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            title: function(tooltipItems) {{
                                return '日期: ' + tooltipItems[0].label;
                            }},
                            label: function(context) {{
                                const rtsi = context.parsed.y;
                                const level = getRtsiLevel(rtsi);
                                return `RTSI评级: ${{rtsi.toFixed(1)}} (${{level}})`;
                            }},
                            afterBody: function(tooltipItems) {{
                                const rtsi = tooltipItems[0].parsed.y;
                                if (rtsi >= 60) return '📈 {i18n_texts['bullish_zone']}';
                                else if (rtsi >= 40) return '➡️ {i18n_texts['neutral_zone']}';
                                else return '📉 {i18n_texts['bearish_zone']}';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // 自动调整图表大小，解决首次加载时的收缩问题
        function resizeCharts() {{
            if (window.volumePriceChart) {{
                window.volumePriceChart.resize();
            }}
            if (window.gradeChart) {{
                window.gradeChart.resize();
            }}
        }}
        
        // 保存图表实例到全局变量
        window.volumePriceChart = volumePriceChart;
        window.gradeChart = gradeChart;
        
        // 监听窗口大小变化
        window.addEventListener('resize', resizeCharts);
        
        // 在页面加载完成后强制调整图表大小
        window.addEventListener('load', function() {{
            setTimeout(resizeCharts, 100); // 延迟100ms确保DOM完全渲染
        }});
        
        // 在DOM内容加载完成后也调整一次
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(resizeCharts, 200); // 延迟200ms确保图表完全初始化
        }});
        
        // 使用MutationObserver监听DOM变化，处理动态显示的情况
        if (typeof MutationObserver !== 'undefined') {{
            const observer = new MutationObserver(function(mutations) {{
                mutations.forEach(function(mutation) {{
                    if (mutation.type === 'attributes' && 
                        (mutation.attributeName === 'style' || mutation.attributeName === 'class')) {{
                        setTimeout(resizeCharts, 50);
                    }}
                }});
            }});
            
            // 观察图表容器的变化
            const chartContainers = document.querySelectorAll('.chart-wrapper');
            chartContainers.forEach(function(container) {{
                observer.observe(container, {{
                    attributes: true,
                    attributeFilter: ['style', 'class']
                }});
            }});
        }}
    </script>
    
    <div style="text-align: center; margin-top: 30px; color: #6c757d; font-size: 12px;">
        🕒 {i18n_texts['data_update_time']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        📊 {i18n_texts['data_from']}: {i18n_texts['ai_stock_analysis_system']} | 
        ⚠️ {i18n_texts['investment_risk_warning']}
    </div>
</body>
</html>
        """
        
        return html_content
    
    def prepare_chart_data(self, volume_price_data: List[Dict], rating_data: List[Tuple]) -> Dict:
        """准备图表数据"""
        # 确保数据按日期排序
        volume_price_data.sort(key=lambda x: x['date'])
        if rating_data:
            rating_data.sort(key=lambda x: x[0])
        
        return {
            'volume_price': volume_price_data,
            'rating': rating_data
        }
    
    def get_rtsi_color(self, rtsi_value: float) -> str:
        """根据RTSI值获取颜色"""
        if rtsi_value >= 80:
            return "#dc3545"  # 红色 - 强势上升
        elif rtsi_value >= 60:
            return "#fd7e14"  # 橙色 - 温和上升
        elif rtsi_value >= 40:
            return "#6c757d"  # 灰色 - 震荡整理
        elif rtsi_value >= 20:
            return "#28a745"  # 绿色 - 弱势下降
        else:
            return "#198754"  # 深绿色 - 强势下降
    
    def analyze_price_trend(self, volume_price_data: List[Dict]) -> str:
        """分析价格趋势"""
        if len(volume_price_data) < 2:
            return "数据不足，无法分析趋势"
        
        first_price = volume_price_data[0]['close_price']
        last_price = volume_price_data[-1]['close_price']
        change_pct = ((last_price - first_price) / first_price) * 100
        
        if change_pct > 10:
            return f"强势上涨 +{change_pct:.2f}%，价格呈现明显上升趋势"
        elif change_pct > 3:
            return f"温和上涨 +{change_pct:.2f}%，价格稳步上升"
        elif change_pct > -3:
            return f"横盘震荡 {change_pct:+.2f}%，价格相对稳定"
        elif change_pct > -10:
            return f"温和下跌 {change_pct:.2f}%，价格有所回调"
        else:
            return f"明显下跌 {change_pct:.2f}%，价格承压下行"
    
    def analyze_volume_trend(self, volume_price_data: List[Dict]) -> str:
        """分析成交量趋势"""
        if len(volume_price_data) < 10:
            return "数据不足，无法分析成交量趋势"
        
        volumes = [item['volume'] for item in volume_price_data]
        avg_volume = sum(volumes) / len(volumes)
        recent_avg = sum(volumes[-5:]) / 5
        
        change_pct = ((recent_avg - avg_volume) / avg_volume) * 100
        
        if change_pct > 30:
            return f"成交活跃 +{change_pct:.1f}%，市场关注度显著提升"
        elif change_pct > 10:
            return f"成交增加 +{change_pct:.1f}%，市场参与度上升"
        elif change_pct > -10:
            return f"成交稳定 {change_pct:+.1f}%，市场情绪平稳"
        else:
            return f"成交萎缩 {change_pct:.1f}%，市场参与度下降"
    
    def analyze_rating_trend(self, rating_data: List[Tuple]) -> str:
        """分析评级趋势"""
        if not rating_data or len(rating_data) < 2:
            return "暂无评级数据或数据不足"
        
        first_rating = rating_data[0][1]
        last_rating = rating_data[-1][1]
        change = last_rating - first_rating
        
        if change > 20:
            return f"评级大幅提升 +{change:.1f}，投资价值显著改善"
        elif change > 5:
            return f"评级上升 +{change:.1f}，投资前景向好"
        elif change > -5:
            return f"评级稳定 {change:+.1f}，投资价值相对稳定"
        elif change > -20:
            return f"评级下降 {change:.1f}，需要谨慎关注"
        else:
            return f"评级大幅下降 {change:.1f}，投资风险增加"
    
    def generate_investment_advice(self, current_rtsi: float) -> str:
        """生成投资建议"""
        if current_rtsi >= 80:
            return "🔴 强烈买入信号，但注意高位风险控制"
        elif current_rtsi >= 60:
            return "🟠 买入信号，适合积极投资者"
        elif current_rtsi >= 40:
            return "⚪ 中性观望，等待明确信号"
        elif current_rtsi >= 20:
            return "🟢 谨慎卖出，考虑减仓"
        else:
            return "🟢🟢 强烈卖出信号，建议规避风险"


def main():
    """测试主函数"""
    generator = EnhancedStockChartGenerator()
    
    # 测试获取量价数据 - 使用实际存在的股票代码
    test_stock_code = "000001"  # 平安银行
    print(f"测试股票代码: {test_stock_code}")
    
    volume_price_data = generator.get_volume_price_data(test_stock_code, 38, market='cn')
    
    if volume_price_data:
        print("成功获取量价数据:")
        print(f"股票: {volume_price_data['stock_name']} ({volume_price_data['stock_code']})")
        print(f"数据天数: {volume_price_data['total_days']}")
        print(f"最近几天数据示例:")
        for i, day_data in enumerate(volume_price_data['data'][-3:]):
            print(f"  {day_data['date']}: 收盘价={day_data['close_price']}, 成交额={day_data['volume']:,}")
        
        # 生成对应天数的模拟评级数据
        from datetime import datetime, timedelta
        import random
        
        rating_data = []
        base_date = datetime.now() - timedelta(days=len(volume_price_data['data']))
        base_rating = 65.0
        
        for i, day_data in enumerate(volume_price_data['data']):
            # 根据价格变化调整评级
            rating_change = random.uniform(-5, 5)
            current_rating = max(0, min(100, base_rating + rating_change))
            rating_data.append((day_data['date'], current_rating))
            base_rating = current_rating
        
        print(f"生成评级数据: {len(rating_data)} 天")
        
        # 生成HTML图表
        html_content = generator.generate_enhanced_html_chart(
            volume_price_data['stock_code'],
            volume_price_data['stock_name'],
            volume_price_data['data'],
            rating_data,
            rating_data[-1][1] if rating_data else 65.5
        )
        
        # 保存到文件
        output_file = f"test_chart_{test_stock_code}_{volume_price_data['stock_name']}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"图表已保存到: {output_file}")
        print("请在浏览器中打开查看效果")
    else:
        print("无法获取数据，尝试生成示例图表...")
        
        # 生成示例数据用于演示
        from datetime import datetime, timedelta
        import random
        
        # 示例量价数据
        example_volume_price_data = []
        example_rating_data = []
        base_date = datetime.now() - timedelta(days=38)
        base_price = 12.0
        base_rating = 65.0
        
        for i in range(38):
            current_date = (base_date + timedelta(days=i)).strftime("%Y%m%d")
            price_change = random.uniform(-0.5, 0.5)
            volume = random.randint(1000000000, 3000000000)
            
            current_price = max(0.1, base_price + price_change)
            example_volume_price_data.append({
                'date': current_date,
                'close_price': current_price,
                'volume': volume,
                'open_price': current_price * random.uniform(0.95, 1.05),
                'high_price': current_price * random.uniform(1.0, 1.05),
                'low_price': current_price * random.uniform(0.95, 1.0)
            })
            
            rating_change = random.uniform(-3, 3)
            current_rating = max(0, min(100, base_rating + rating_change))
            example_rating_data.append((current_date, current_rating))
            
            base_price = current_price
            base_rating = current_rating
        
        # 生成示例HTML图表
        html_content = generator.generate_enhanced_html_chart(
            "DEMO001",
            "示例股票",
            example_volume_price_data,
            example_rating_data,
            example_rating_data[-1][1]
        )
        
        # 保存到文件
        output_file = "demo_enhanced_chart.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"示例图表已保存到: {output_file}")
        print("请在浏览器中打开查看效果")


if __name__ == "__main__":
    main()
