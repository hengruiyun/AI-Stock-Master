# -*- coding: utf-8 -*-
"""
图表模板系统

提供预设的图表配置和样式模板：
- StockTrendTemplate: 股票趋势图模板
- IndustryHeatmapTemplate: 行业热力图模板
- MarketSentimentTemplate: 市场情绪图模板
- PerformanceTemplate: 性能监控模板
"""

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    # 如果plotly不可用，创建一个备用的go模块
    class MockFigure:
        def __init__(self, *args, **kwargs):
            pass
    
    class MockGo:
        Figure = MockFigure
    
    go = MockGo()
    PLOTLY_AVAILABLE = False
    print("WARNING: Plotly未安装，图表模板功能受限")

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BaseTemplate:
    """图表模板基类"""
    
    def __init__(self, theme: str = 'professional'):
        self.theme = theme
        self.colors = self._get_theme_colors(theme)
        self.layout_config = self._get_layout_config(theme)
    
    def _get_theme_colors(self, theme: str) -> Dict[str, str]:
        """获取主题颜色配置"""
        themes = {
            'professional': {
                'primary': '#2E86AB',
                'secondary': '#A23B72',
                'accent': '#F18F01',
                'success': '#28A745',
                'warning': '#FFC107',
                'danger': '#DC3545',
                'info': '#17A2B8',
                'background': '#F8F9FA',
                'surface': '#FFFFFF',
                'text': '#2C3E50',
                'text_secondary': '#6C757D'
            },
            'dark': {
                'primary': '#00D4AA',
                'secondary': '#FF6B6B',
                'accent': '#FFE66D',
                'success': '#4ECDC4',
                'warning': '#FFE66D',
                'danger': '#FF6B6B',
                'info': '#45B7D1',
                'background': '#2C3E50',
                'surface': '#34495E',
                'text': '#ECF0F1',
                'text_secondary': '#BDC3C7'
            },
            'classic': {
                'primary': '#1f77b4',
                'secondary': '#ff7f0e',
                'accent': '#2ca02c',
                'success': '#2ca02c',
                'warning': '#ff7f0e',
                'danger': '#d62728',
                'info': '#17becf',
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'text': '#000000',
                'text_secondary': '#666666'
            }
        }
        return themes.get(theme, themes['professional'])
    
    def _get_layout_config(self, theme: str) -> Dict[str, Any]:
        """获取布局配置"""
        return {
            'template': 'plotly_white' if theme != 'dark' else 'plotly_dark',
            'font': {'family': 'Arial, sans-serif', 'size': 12, 'color': self.colors['text']},
            'title_font': {'family': 'Arial, sans-serif', 'size': 18, 'color': self.colors['text']},
            'paper_bgcolor': self.colors['background'],
            'plot_bgcolor': self.colors['surface'],
            'grid_color': self.colors['text_secondary'] + '30',  # 30% opacity
            'margin': {'l': 60, 'r': 60, 't': 80, 'b': 60}
        }

class StockTrendTemplate(BaseTemplate):
    """股票趋势图模板"""
    
    def __init__(self, theme: str = 'professional'):
        super().__init__(theme)
        self.default_config = {
            'show_volume': True,
            'show_ma_lines': True,
            'ma_periods': [5, 10, 20],
            'show_bollinger': False,
            'show_rsi': True,
            'chart_height': 800,
            'main_chart_ratio': 0.7,
            'volume_ratio': 0.15,
            'indicator_ratio': 0.15
        }
    
    def create_layout(self, **kwargs) -> Dict[str, Any]:
        """创建趋势图布局配置"""
        config = {**self.default_config, **kwargs}
        
        # 计算子图行数和规格
        rows = 1
        specs = [[{"secondary_y": True}]]
        subplot_titles = ["股票趋势图"]
        
        if config['show_volume']:
            rows += 1
            specs.append([{"secondary_y": False}])
            subplot_titles.append("成交量")
        
        if config['show_rsi']:
            rows += 1
            specs.append([{"secondary_y": False}])
            subplot_titles.append("RSI指标")
        
        # 计算行高比例
        row_heights = []
        if rows == 1:
            row_heights = None
        elif rows == 2:
            row_heights = [0.85, 0.15]
        elif rows == 3:
            row_heights = [0.7, 0.15, 0.15]
        
        layout = {
            'rows': rows,
            'cols': 1,
            'specs': specs,
            'subplot_titles': subplot_titles,
            'row_heights': row_heights,
            'vertical_spacing': 0.05,
            'shared_xaxes': True
        }
        
        return layout
    
    def get_line_styles(self) -> Dict[str, Dict[str, Any]]:
        """获取线条样式配置"""
        return {
            'price_line': {
                'color': self.colors['primary'],
                'width': 2
            },
            'ma5': {
                'color': self.colors['accent'],
                'width': 1,
                'dash': 'solid'
            },
            'ma10': {
                'color': self.colors['secondary'],
                'width': 1,
                'dash': 'dash'
            },
            'ma20': {
                'color': self.colors['info'],
                'width': 1,
                'dash': 'dot'
            },
            'bollinger_upper': {
                'color': self.colors['warning'],
                'width': 1,
                'dash': 'dash'
            },
            'bollinger_lower': {
                'color': self.colors['warning'],
                'width': 1,
                'dash': 'dash'
            },
            'volume_bar': {
                'color': self.colors['text_secondary'],
                'opacity': 0.6
            },
            'rsi_line': {
                'color': self.colors['primary'],
                'width': 2
            }
        }
    
    def get_annotation_config(self) -> Dict[str, Any]:
        """获取注释配置"""
        return {
            'font': {'size': 10, 'color': self.colors['text']},
            'bgcolor': self.colors['surface'],
            'bordercolor': self.colors['primary'],
            'borderwidth': 1,
            'showarrow': True,
            'arrowhead': 2,
            'arrowsize': 1,
            'arrowwidth': 2,
            'arrowcolor': self.colors['primary']
        }

class IndustryHeatmapTemplate(BaseTemplate):
    """行业热力图模板"""
    
    def __init__(self, theme: str = 'professional'):
        super().__init__(theme)
        self.default_config = {
            'colorscale_type': 'diverging',  # diverging, sequential, categorical
            'show_text': True,
            'text_size': 10,
            'aspect_ratio': 'auto',  # auto, equal
            'cluster_method': 'ward',  # ward, complete, average
            'distance_metric': 'euclidean',
            'show_dendrograms': False,
            'annotation_threshold': 0.5
        }
    
    def get_colorscales(self) -> Dict[str, List[List]]:
        """获取热力图颜色标度"""
        return {
            'diverging_red_blue': [
                [0, '#d73027'],      # 强烈看空 - 深红
                [0.1, '#f46d43'],    # 看空 - 红
                [0.2, '#fdae61'],    # 偏空 - 橙
                [0.3, '#fee08b'],    # 微空 - 浅橙
                [0.4, '#e6f598'],    # 接近中性 - 浅黄绿
                [0.5, '#ffffff'],    # 中性 - 白
                [0.6, '#d9f0a3'],    # 接近中性 - 浅绿
                [0.7, '#abdda4'],    # 微多 - 绿
                [0.8, '#74add1'],    # 偏多 - 蓝
                [0.9, '#4575b4'],    # 看多 - 深蓝
                [1, '#313695']       # 强烈看多 - 极深蓝
            ],
            'diverging_green_red': [
                [0, '#a50026'],
                [0.1, '#d73027'],
                [0.2, '#f46d43'],
                [0.3, '#fdae61'],
                [0.4, '#fee08b'],
                [0.5, '#ffffcc'],
                [0.6, '#d9f0a3'],
                [0.7, '#a6d96a'],
                [0.8, '#66bd63'],
                [0.9, '#1a9850'],
                [1, '#006837']
            ],
            'sequential_blues': [
                [0, '#f7fbff'],
                [0.125, '#deebf7'],
                [0.25, '#c6dbef'],
                [0.375, '#9ecae1'],
                [0.5, '#6baed6'],
                [0.625, '#4292c6'],
                [0.75, '#2171b5'],
                [0.875, '#08519c'],
                [1, '#08306b']
            ],
            'professional': [
                [0, '#FFE6E6'],      # 浅红
                [0.2, '#FFB3B3'],    # 红
                [0.4, '#FF8080'],    # 中红
                [0.5, '#FFFFFF'],    # 白色中性
                [0.6, '#B3D9FF'],    # 浅蓝
                [0.8, '#80C7FF'],    # 蓝
                [1, '#4DB8FF']       # 深蓝
            ]
        }
    
    def get_heatmap_config(self, data_range: Tuple[float, float] = (-50, 50)) -> Dict[str, Any]:
        """获取热力图配置"""
        colorscales = self.get_colorscales()
        
        return {
            'colorscale': colorscales['diverging_red_blue'],
            'zmid': 0,  # 中性值
            'zmin': data_range[0],
            'zmax': data_range[1],
            'colorbar': {
                'title': 'IRSI值',
                'titleside': 'right',
                'tickmode': 'linear',
                'tick0': data_range[0],
                'dtick': (data_range[1] - data_range[0]) / 10,
                'thickness': 15,
                'len': 0.8,
                'x': 1.02
            },
            'hovertemplate': "<b>%{y}</b><br>" +
                           "时间: %{x}<br>" +
                           "IRSI: %{z:.2f}<br>" +
                           "<extra></extra>",
            'showscale': True
        }
    
    def get_clustering_config(self) -> Dict[str, Any]:
        """获取聚类配置"""
        return {
            'linkage_method': self.default_config['cluster_method'],
            'distance_metric': self.default_config['distance_metric'],
            'dendrogram_colors': [self.colors['primary'], self.colors['secondary'], 
                                self.colors['accent'], self.colors['info']],
            'dendrogram_line_width': 2
        }

class MarketSentimentTemplate(BaseTemplate):
    """市场情绪图模板"""
    
    def __init__(self, theme: str = 'professional'):
        super().__init__(theme)
        self.default_config = {
            'scatter_size_range': (5, 20),
            'opacity': 0.7,
            'show_regression_line': True,
            'show_confidence_interval': False,
            'show_quadrant_lines': True,
            'quadrant_line_style': 'dash',
            'bubble_scale': 'sqrt',  # linear, sqrt, log
            'color_scale': 'viridis'  # viridis, plasma, RdYlGn
        }
    
    def get_scatter_config(self) -> Dict[str, Any]:
        """获取散点图配置"""
        return {
            'mode': 'markers',
            'marker': {
                'opacity': self.default_config['opacity'],
                'line': {'width': 1, 'color': self.colors['text_secondary']},
                'colorscale': self.default_config['color_scale'],
                'showscale': True,
                'sizemode': 'diameter',
                'sizeref': 1,
                'sizemin': self.default_config['scatter_size_range'][0]
            },
            'hovertemplate': "<b>%{text}</b><br>" +
                           "X轴: %{x:.2f}<br>" +
                           "Y轴: %{y:.2f}<br>" +
                           "<extra></extra>"
        }
    
    def get_quadrant_config(self) -> Dict[str, Any]:
        """获取象限配置"""
        return {
            'line_color': self.colors['text_secondary'],
            'line_width': 1,
            'line_dash': self.default_config['quadrant_line_style'],
            'opacity': 0.5,
            'quadrant_colors': {
                'high_return_low_risk': self.colors['success'],    # 优质股 - 绿色
                'high_return_high_risk': self.colors['warning'],   # 激进股 - 橙色
                'low_return_low_risk': self.colors['info'],        # 稳健股 - 蓝色
                'low_return_high_risk': self.colors['danger']      # 风险股 - 红色
            },
            'quadrant_labels': {
                'high_return_low_risk': '优质股',
                'high_return_high_risk': '激进股',
                'low_return_low_risk': '稳健股',
                'low_return_high_risk': '风险股'
            }
        }
    
    def get_regression_config(self) -> Dict[str, Any]:
        """获取回归线配置"""
        return {
            'line': {
                'color': self.colors['primary'],
                'width': 2,
                'dash': 'solid'
            },
            'confidence_interval': {
                'color': self.colors['primary'],
                'opacity': 0.2,
                'fill': 'tonexty'
            }
        }

class PerformanceTemplate(BaseTemplate):
    """性能监控模板"""
    
    def __init__(self, theme: str = 'professional'):
        super().__init__(theme)
        self.default_config = {
            'gauge_ranges': {
                'good': (0, 60),
                'warning': (60, 85),
                'critical': (85, 100)
            },
            'gauge_colors': {
                'good': '#E6F7E6',
                'warning': '#FFF4E6', 
                'critical': '#FFE6E6'
            },
            'threshold_color': '#DC3545',
            'bar_colors': {
                'excellent': '#28A745',
                'good': '#17A2B8',
                'warning': '#FFC107',
                'poor': '#DC3545'
            },
            'time_window': '1h',  # 1h, 6h, 24h, 7d
            'refresh_interval': 60  # seconds
        }
    
    def get_gauge_config(self, metric_name: str, value_range: Tuple[float, float] = (0, 100)) -> Dict[str, Any]:
        """获取仪表盘配置"""
        ranges = self.default_config['gauge_ranges']
        colors = self.default_config['gauge_colors']
        
        # 根据值域调整范围
        scale_factor = (value_range[1] - value_range[0]) / 100
        
        return {
            'mode': "gauge+number+delta",
            'domain': {'x': [0, 1], 'y': [0, 1]},
            'title': {'text': metric_name, 'font': {'size': 14}},
            'gauge': {
                'axis': {'range': [value_range[0], value_range[1]]},
                'bar': {'color': self.colors['primary']},
                'steps': [
                    {
                        'range': [value_range[0], value_range[0] + ranges['good'][1] * scale_factor],
                        'color': colors['good']
                    },
                    {
                        'range': [value_range[0] + ranges['good'][1] * scale_factor, 
                                value_range[0] + ranges['warning'][1] * scale_factor],
                        'color': colors['warning']
                    },
                    {
                        'range': [value_range[0] + ranges['warning'][1] * scale_factor, value_range[1]],
                        'color': colors['critical']
                    }
                ],
                'threshold': {
                    'line': {'color': self.default_config['threshold_color'], 'width': 4},
                    'thickness': 0.75,
                    'value': value_range[0] + ranges['warning'][1] * scale_factor
                }
            }
        }
    
    def get_performance_colors(self, values: List[float], thresholds: Dict[str, float] = None) -> List[str]:
        """根据性能值获取颜色"""
        if thresholds is None:
            thresholds = {'excellent': 90, 'good': 70, 'warning': 50}
        
        colors = []
        bar_colors = self.default_config['bar_colors']
        
        for value in values:
            if value >= thresholds['excellent']:
                colors.append(bar_colors['excellent'])
            elif value >= thresholds['good']:
                colors.append(bar_colors['good'])
            elif value >= thresholds['warning']:
                colors.append(bar_colors['warning'])
            else:
                colors.append(bar_colors['poor'])
        
        return colors
    
    def get_time_series_config(self) -> Dict[str, Any]:
        """获取时间序列图配置"""
        return {
            'line': {
                'color': self.colors['primary'],
                'width': 2
            },
            'fill': 'tonexty',
            'fillcolor': f"rgba({self.colors['primary'][1:]}, 0.2)",
            'hovertemplate': "时间: %{x}<br>" +
                           "数值: %{y:.2f}<br>" +
                           "<extra></extra>"
        }

class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self.templates = {
            'stock_trend': StockTrendTemplate,
            'industry_heatmap': IndustryHeatmapTemplate,
            'market_sentiment': MarketSentimentTemplate,
            'performance': PerformanceTemplate
        }
        self.theme = 'professional'
    
    def get_template(self, template_name: str, theme: str = None) -> BaseTemplate:
        """获取指定模板"""
        if template_name not in self.templates:
            raise ValueError(f"不支持的模板类型: {template_name}")
        
        current_theme = theme or self.theme
        return self.templates[template_name](current_theme)
    
    def set_global_theme(self, theme: str):
        """设置全局主题"""
        self.theme = theme
    
    def get_available_templates(self) -> List[str]:
        """获取可用模板列表"""
        return list(self.templates.keys())
    
    def get_available_themes(self) -> List[str]:
        """获取可用主题列表"""
        return ['professional', 'dark', 'classic']

# 全局模板管理器实例
template_manager = TemplateManager()

# 便捷函数
def get_template(template_name: str, theme: str = None) -> BaseTemplate:
    """获取模板的便捷函数"""
    return template_manager.get_template(template_name, theme)

def set_global_theme(theme: str):
    """设置全局主题的便捷函数"""
    template_manager.set_global_theme(theme)

def create_styled_figure(template_name: str, **kwargs) -> go.Figure:
    """创建带样式的图表"""
    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly未安装，无法创建高级图表")
        return None
    
    template = get_template(template_name)
    
    if template_name == 'stock_trend':
        layout_config = template.create_layout(**kwargs)
        fig = make_subplots(**layout_config)
    elif template_name == 'industry_heatmap':
        fig = go.Figure()
    elif template_name == 'market_sentiment':
        fig = make_subplots(rows=2, cols=2, 
                          subplot_titles=('散点图1', '散点图2', '分布图', '统计图'))
    elif template_name == 'performance':
        fig = make_subplots(rows=3, cols=3,
                          specs=[
                              [{"type": "indicator"}, {"type": "scatter"}, {"type": "indicator"}],
                              [{"type": "bar"}, {"type": "pie"}, {"type": "bar"}],
                              [{"type": "scatter"}, {"type": "bar"}, {"type": "indicator"}]
                          ])
    else:
        fig = go.Figure()
    
    # 应用模板样式
    fig.update_layout(
        template=template.layout_config['template'],
        font=template.layout_config['font'],
        paper_bgcolor=template.layout_config['paper_bgcolor'],
        plot_bgcolor=template.layout_config['plot_bgcolor'],
        margin=template.layout_config['margin']
    )
    
    return fig 