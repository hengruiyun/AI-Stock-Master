"""
from config.i18n import t_gui as _
高级图表可视化模块 - 修复版本

提供交互式图表、热力图、散点图等高级可视化功能。

主要功能:
- 交互式趋势图表
- 行业轮动热力图  
- 市场情绪散点图
- 性能仪表板

作者: 267278466@qq.com
版本: 1.0.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional, Union
import logging

# 图表库
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    logging.warning("Plotly未安装，将使用基础图表功能")
    # 创建占位符，避免在类定义中出现NameError
    class _PlotlyFigurePlaceholder:
        pass
    go = type('go', (), {'Figure': _PlotlyFigurePlaceholder})
    px = None

# 配置日志
logger = logging.getLogger(__name__)

class ChartStyleManager:
    """图表样式管理器"""
    
    def __init__(self):
        self.theme = _('professional_theme')
        self.color_palette = self._init_color_palette()
        self.font_settings = self._init_font_settings()
    
    def _init_color_palette(self) -> Dict[str, List[str]]:
        """初始化调色板"""
        return {
            _('professional_theme'): [
                '#2E86AB', '#A23B72', '#F18F01', '#C73E1D',
                '#6A994E', '#277DA1', '#F8961E', '#90E0EF',
                '#023047', '#8ECAE6', '#219EBC', '#FFB3BA'
            ],
            _('vivid_theme'): [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
                '#FFEAA7', '#DDA0DD', '#98D8C8', '#FFD93D',
                '#6C5CE7', '#A29BFE', '#FD79A8', '#E17055'
            ],
            _('monochrome_theme'): [
                '#2C3E50', '#34495E', '#7F8C8D', '#95A5A6',
                '#BDC3C7', '#ECF0F1', '#3498DB', '#2980B9',
                '#1ABC9C', '#16A085', '#E74C3C', '#C0392B'
            ]
        }
    
    def _init_font_settings(self) -> Dict[str, Any]:
        """初始化字体设置"""
        return {
            'family': 'Microsoft YaHei, Arial, sans-serif',
        'size': 12,
        'title_size': 18,
        'axis_size': 11
        }
    
    def apply_theme(self, theme_name: str = None):
        """应用主题"""
        if theme_name is None:
            theme_name = _('professional_theme')
        if theme_name in self.color_palette:
            self.theme = theme_name
        else:
            logger.warning(_('unknown_theme_use_default', theme=theme_name))
    
    def get_colors(self, n: int = None) -> List[str]:
        """获取颜色列表"""
        colors = self.color_palette[self.theme]
        if n is None:
            return colors
        return (colors * ((n // len(colors)) + 1))[:n]

class InteractiveTrendChart:
    """交互式趋势图表"""
    
    def __init__(self, figsize: Tuple[int, int] = (14, 10), style_manager: ChartStyleManager = None):
        self.figsize = figsize
        self.style_manager = style_manager or ChartStyleManager()
    
    def create_stock_trend(self, stock_data: Dict[str, Any], 
                          stock_codes: List[str] = None,
                          interactive: bool = True) -> go.Figure:
        """创建股票趋势图"""
        
        if not HAS_PLOTLY:
            logger.error("Plotly未安装，无法创建交互式图表")
            return None
        
        return self._create_plotly_trend(stock_data, stock_codes)
    
    def _create_plotly_trend(self, stock_data: Dict[str, Any], 
                           stock_codes: List[str] = None) -> go.Figure:
        """创建Plotly趋势图"""
        
        # 创建子图布局
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('RTSI趋势分析', '评级分布', 'RTSI排名', '市场指标'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"type": "indicator"}]],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        # 获取颜色
        colors = self.style_manager.get_colors(10)
        
        # 处理股票代码
        if stock_codes is None:
            stock_codes = list(stock_data.keys())[:5]  # 默认取前5只
        
        # 1. RTSI趋势图
        for i, stock_code in enumerate(stock_codes):
            if stock_code in stock_data:
                stock_info = stock_data[stock_code]
                
                # 使用真实数据或跳过
                rtsi_data = stock_info.get('rtsi', {})
                if isinstance(rtsi_data, dict) and 'rtsi' in rtsi_data:
                    rtsi_value = rtsi_data['rtsi']
                    # 生成简单的历史趋势数据用于展示
                    dates = pd.date_range(start='2025-04-10', periods=38, freq='D')
                    rtsi_values = [rtsi_value] * 38  # 使用实际RTSI值
                else:
                    continue  # 跳过没有RTSI数据的股票
                
                fig.add_trace(
                    go.Scatter(
                        x=dates,
                        y=rtsi_values,
                        mode='lines+markers',
                        name=f"{stock_code} ({stock_info.get('name', '')})",
                        line=dict(color=colors[i], width=2),
                        marker=dict(size=4),
                        hovertemplate="<b>%{fullData.name}</b><br>" +
                                    "日期: %{x}<br>" +
                                    "RTSI: %{y:.2f}<br>" +
                                    "<extra></extra>"
                    ),
                    row=1, col=1
                )
        
        # 2. 评级分布条形图
        rating_dist = self._calculate_rating_distribution(stock_data)
        fig.add_trace(
            go.Bar(
                x=list(rating_dist.keys()),
                y=list(rating_dist.values()),
                name="评级分布",
                marker_color=colors[:len(rating_dist)],
                text=[f"{v:.1f}%" for v in rating_dist.values()],
                textposition='auto'
            ),
            row=1, col=2
        )
        
        # 3. RTSI排名散点图
        rtsi_ranking = self._get_rtsi_ranking(stock_data, stock_codes)
        if rtsi_ranking:
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(rtsi_ranking))),
                    y=[item['rtsi'] for item in rtsi_ranking],
                    mode='markers+text',
                    marker=dict(
                        size=[15 + item['rtsi']/10 for item in rtsi_ranking],
                        color=[item['rtsi'] for item in rtsi_ranking],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="RTSI")
                    ),
                    text=[item['code'] for item in rtsi_ranking],
                    textposition="middle center",
                    name="RTSI排名",
                    hovertemplate="<b>%{text}</b><br>" +
                                "排名: %{x}<br>" +
                                "RTSI: %{y:.2f}<br>" +
                                "<extra></extra>"
                ),
                row=2, col=1
            )
            
            # 4. 关键指标仪表板
            avg_rtsi = np.mean([item['rtsi'] for item in rtsi_ranking])
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=avg_rtsi,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "平均RTSI"},
                    delta={'reference': 50},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "#2E86AB"},
                        'steps': [
                            {'range': [0, 30], 'color': "#FFE6E6"},
                            {'range': [30, 70], 'color': "#FFF4E6"},
                            {'range': [70, 100], 'color': "#E6F7E6"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 80
                        }
                    }
                ),
                row=2, col=2
            )
        
        # 更新布局
        fig.update_layout(
            title={
                'text': "AI股票趋势分析 - 交互式仪表板",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            showlegend=True,
            height=800,
            template="plotly_white"
        )
        
        # 更新各子图轴标签
        fig.update_xaxes(title_text="", row=1, col=1)
        fig.update_yaxes(title_text="RTSI", row=1, col=1)
        fig.update_xaxes(title_text="", row=1, col=2)
        fig.update_yaxes(title_text="", row=1, col=2)
        fig.update_xaxes(title_text="", row=2, col=1)
        fig.update_yaxes(title_text="RTSI", row=2, col=1)
        
        return fig
    
    def _calculate_rating_distribution(self, stock_data: Dict[str, Any]) -> Dict[str, float]:
        """计算评级分布"""
        ratings = []
        for stock_info in stock_data.values():
            # 从真实数据获取评级
            rating = stock_info.get('rating', '未评级')
            if rating not in ['大多', '中多', '小多', '微多', '微空', '小空', '中空']:
                rating = '未评级'
            ratings.append(rating)
        
        if not ratings:
            return {'无数据': 100.0}
        
        rating_counts = pd.Series(ratings).value_counts()
        total = len(ratings)
        
        return {rating: (count/total)*100 for rating, count in rating_counts.items()}
    
    def _get_rtsi_ranking(self, stock_data: Dict[str, Any], 
                         stock_codes: List[str]) -> List[Dict[str, Any]]:
        """获取RTSI排名"""
        ranking = []
        for code in stock_codes:
            if code in stock_data:
                # 从真实数据获取RTSI值
                rtsi_data = stock_data[code].get('rtsi', {})
                if isinstance(rtsi_data, dict):
                    rtsi = rtsi_data.get('rtsi', 0)
                else:
                    rtsi = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
                
                if rtsi > 0:  # 只包含有效的RTSI值
                    ranking.append({
                        'code': code,
                        'name': stock_data[code].get('name', ''),
                        'rtsi': rtsi
                    })
        
        return sorted(ranking, key=lambda x: x['rtsi'], reverse=True)

class HeatmapChart:
    """行业轮动热力图"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8), style_manager: ChartStyleManager = None):
        self.figsize = figsize
        self.style_manager = style_manager or ChartStyleManager()
    
    def create_industry_heatmap(self, industry_data: Dict[str, Any], 
                              metric: str = 'irsi') -> go.Figure:
        """创建行业轮动热力图"""
        
        if not HAS_PLOTLY:
            logger.error("Plotly未安装，无法创建热力图")
            return None
        
        # 准备数据
        industries = list(industry_data.keys())[:20]  # 取前20个行业
        dates = pd.date_range(start='2025-04-10', periods=38, freq='D')
        
        # 生成热力图数据矩阵
        heatmap_data = []
        for industry in industries:
            # 从真实数据获取IRSI值或使用默认值
            irsi_data = industry_data.get(industry, {})
            if isinstance(irsi_data, dict) and 'irsi' in irsi_data:
                base_irsi = irsi_data['irsi']
            else:
                base_irsi = 0
            
            # 生成历史序列用于展示
            irsi_series = [base_irsi] * len(dates)
            heatmap_data.append(irsi_series)
        
        if not heatmap_data:
            # 创建空图表
            fig = go.Figure()
            fig.add_annotation(
                text="",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                font=dict(size=20)
            )
            return fig
        
        heatmap_matrix = np.array(heatmap_data)
        
        # 创建plotly热力图
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_matrix,
            x=[d.strftime('%m-%d') for d in dates],
            y=industries,
            colorscale=[
                [0, '#d73027'],      # 强烈看空 - 深红
                [0.2, '#f46d43'],    # 看空 - 红
                [0.4, '#fdae61'],    # 偏空 - 橙
                [0.5, '#ffffff'],    # 中性 - 白
                [0.6, '#abd9e9'],    # 偏多 - 浅蓝
                [0.8, '#74add1'],    # 看多 - 蓝
                [1, '#4575b4']       # 强烈看多 - 深蓝
            ],
            zmid=0,
            colorbar=dict(
                title="IRSI",
                titleside="right",
                tickmode="linear",
                tick0=-50,
                dtick=10
            ),
            hovertemplate="<b>%{y}</b><br>" +
                         "日期: %{x}<br>" +
                         "IRSI: %{z:.2f}<br>" +
                         "<extra></extra>"
        ))
        
        fig.update_layout(
            title={
                'text': "行业轮动热力图 - IRSI指标",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18}
            },
            xaxis_title="",
            yaxis_title="",
            height=600,
            template="plotly_white"
        )
        
        return fig

class ScatterPlotChart:
    """市场情绪散点图"""
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8), style_manager: ChartStyleManager = None):
        self.figsize = figsize
        self.style_manager = style_manager or ChartStyleManager()
    
    def create_sentiment_scatter(self, market_data: Dict[str, Any]) -> go.Figure:
        """创建市场情绪散点图"""
        
        if not HAS_PLOTLY:
            logger.error("Plotly未安装，无法创建散点图")
            return None
        
        # 准备数据
        stocks = market_data.get('stocks', {})
        if not stocks:
            # 创建空图表
            fig = go.Figure()
            fig.add_annotation(
                text="",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                font=dict(size=20)
            )
            return fig
        
        rtsi_values = []
        sentiment_scores = []
        stock_codes = []
        stock_names = []
        industries = []
        
        for code, stock_info in stocks.items():
            # 获取RTSI值
            rtsi_data = stock_info.get('rtsi', {})
            if isinstance(rtsi_data, dict):
                rtsi = rtsi_data.get('rtsi', 0)
            else:
                rtsi = rtsi_data if isinstance(rtsi_data, (int, float)) else 0
            
            if rtsi > 0:  # 只包含有效数据
                rtsi_values.append(rtsi)
                sentiment_scores.append(stock_info.get('sentiment_score', rtsi))  # 使用RTSI作为情绪分数
                stock_codes.append(code)
                stock_names.append(stock_info.get('name', ''))
                industries.append(stock_info.get('industry', '未分类'))
        
        if not rtsi_values:
            # 创建空图表
            fig = go.Figure()
            fig.add_annotation(
                text="",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                font=dict(size=20)
            )
            return fig
        
        # 创建散点图
        fig = go.Figure(data=go.Scatter(
            x=rtsi_values,
            y=sentiment_scores,
            mode='markers',
            marker=dict(
                size=[max(8, rtsi/10) for rtsi in rtsi_values],
                color=rtsi_values,
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="RTSI"),
                opacity=0.7,
                line=dict(width=1, color='black')
            ),
            text=[f"{code}<br>{name}<br>{industry}" for code, name, industry in zip(stock_codes, stock_names, industries)],
            hovertemplate="<b>%{text}</b><br>" +
                         "RTSI: %{x:.2f}<br>" +
                         "情绪分数: %{y:.2f}<br>" +
                         "<extra></extra>"
        ))
        
        fig.update_layout(
            title={
                'text': "市场情绪分析 - RTSI vs 情绪分数",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18}
            },
            xaxis_title="RTSI",
            yaxis_title="",
            height=600,
            template="plotly_white"
        )
        
        return fig

class PerformanceDashboard:
    """性能仪表板"""
    
    def __init__(self, style_manager: ChartStyleManager = None):
        self.style_manager = style_manager or ChartStyleManager()
    
    def create_dashboard(self, performance_data: Dict[str, Any]) -> go.Figure:
        """创建性能仪表板"""
        
        if not HAS_PLOTLY:
            logger.error("Plotly未安装，无法创建仪表板")
            return None
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['分析性能', '数据质量', '系统状态', '用户活动'],
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}]
            ]
        )
        
        # 获取性能数据
        analysis_time = performance_data.get('analysis_time', 0)
        data_quality = performance_data.get('data_quality_score', 85)
        system_health = performance_data.get('system_health', 90)
        user_activity = performance_data.get('user_activity_score', 75)
        
        # 1. 分析性能指标
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=min(100, max(0, 100 - analysis_time * 10)),  # 转换为性能分数
                title={'text': "分析性能<br><span style='font-size:0.8em;color:gray'>基于分析时间</span>"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#2E86AB"},
                    'steps': [
                        {'range': [0, 60], 'color': "#FFE6E6"},
                        {'range': [60, 80], 'color': "#FFF4E6"},
                        {'range': [80, 100], 'color': "#E6F7E6"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ),
            row=1, col=1
        )
        
        # 2. 数据质量指标
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=data_quality,
                title={'text': "数据质量<br><span style='font-size:0.8em;color:gray'>评级覆盖率</span>"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#A23B72"},
                    'steps': [
                        {'range': [0, 50], 'color': "#FFE6E6"},
                        {'range': [50, 75], 'color': "#FFF4E6"},
                        {'range': [75, 100], 'color': "#E6F7E6"}
                    ]
                }
            ),
            row=1, col=2
        )
        
        # 3. 系统状态指标
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=system_health,
                title={'text': "系统状态<br><span style='font-size:0.8em;color:gray'>运行健康度</span>"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#F18F01"},
                    'steps': [
                        {'range': [0, 70], 'color': "#FFE6E6"},
                        {'range': [70, 85], 'color': "#FFF4E6"},
                        {'range': [85, 100], 'color': "#E6F7E6"}
                    ]
                }
            ),
            row=2, col=1
        )
        
        # 4. 用户活动指标
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=user_activity,
                title={'text': "用户活动<br><span style='font-size:0.8em;color:gray'>系统使用率</span>"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#6A994E"},
                    'steps': [
                        {'range': [0, 40], 'color': "#FFE6E6"},
                        {'range': [40, 70], 'color': "#FFF4E6"},
                        {'range': [70, 100], 'color': "#E6F7E6"}
                    ]
                }
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title={
                'text': "系统性能监控仪表板",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
            },
            height=600,
            template="plotly_white"
        )
        
        return fig

# 便捷函数
def save_chart(fig, filename: str, format: str = 'html', **kwargs):
    """保存图表"""
    if not HAS_PLOTLY:
        logger.error("Plotly未安装，无法保存图表")
        return False
    
    try:
        if format == 'html':
            fig.write_html(filename, **kwargs)
        elif format == 'png':
            fig.write_image(filename, **kwargs)
        elif format == 'pdf':
            fig.write_image(filename, **kwargs)
        else:
            logger.error(f"不支持的格式: {format}")
            return False
        return True
    except Exception as e:
        logger.error(f"保存图表失败: {e}")
        return False

def create_chart_collection(data: Dict[str, Any]) -> Dict[str, go.Figure]:
    """创建图表集合"""
    charts = {}
    
    try:
        # 创建样式管理器
        style_manager = ChartStyleManager()
        
        # 1. 趋势图
        trend_chart = InteractiveTrendChart(style_manager=style_manager)
        charts['trend'] = trend_chart.create_stock_trend(data.get('stocks', {}))
        
        # 2. 热力图
        heatmap_chart = HeatmapChart(style_manager=style_manager)
        charts['heatmap'] = heatmap_chart.create_industry_heatmap(data.get('industries', {}))
        
        # 3. 散点图
        scatter_chart = ScatterPlotChart(style_manager=style_manager)
        charts['scatter'] = scatter_chart.create_sentiment_scatter(data)
        
        # 4. 性能仪表板
        dashboard = PerformanceDashboard(style_manager=style_manager)
        charts['dashboard'] = dashboard.create_dashboard(data.get('performance', {}))
        
        logger.info(f"成功创建 {len(charts)} 个图表")
        
    except Exception as e:
        logger.error(f"创建图表集合失败: {e}")
    
    return charts

if __name__ == "__main__":
    print("-")
    
    # 测试数据
    test_data = {
        'stocks': {
            '600036': {'name': '招商银行', 'industry': '银行', 'rtsi': {'rtsi': 85.2}},
            '000001': {'name': '平安银行', 'industry': '银行', 'rtsi': {'rtsi': 72.1}}
        },
        'industries': {
            '银行': {'irsi': 15.5},
            '科技': {'irsi': -8.2}
        },
        'performance': {
            'analysis_time': 2.5,
            'data_quality_score': 87,
            'system_health': 92,
            'user_activity_score': 78
        }
    }
    
    if HAS_PLOTLY:
        # 创建图表集合
        charts = create_chart_collection(test_data)
        print(f"创建了 {len(charts)} 个图表")
    else:
        print("Plotly")