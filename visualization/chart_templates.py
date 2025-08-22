# -*- coding: utf-8 -*-
"""
from config.i18n import t_gui as _
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
    print('Plotly不可用')  # 避免在导入前使用t_common

from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

# 导入国际化配置
try:
    from config.i18n import t_visualization, t_common, get_current_language
except ImportError:
    # 回退函数
    def t_visualization(key, default=None):
        return default or key
    def t_common(key, default=None):
        return default or key
    def get_current_language():
        return 'zh'

logger = logging.getLogger(__name__)

class BaseTemplate:
    """图表模板基类"""
    
    def __init__(self, theme: str = None):
        if theme is None:
            theme = t_visualization('theme_professional', '专业版')
        self.theme = theme
        self.colors = self._get_theme_colors(theme)
        self.layout_config = self._get_layout_config(theme)
    
    def _get_theme_colors(self, theme: str) -> Dict[str, str]:
        """获取主题颜色配置"""
        themes = {
            t_visualization('theme_professional', '专业版'): {
                t_visualization('color_primary', '主色'): '#2E86AB',
                t_visualization('color_secondary', '次色'): '#A23B72',
                t_visualization('color_accent', '强调色'): '#F18F01',
                t_visualization('color_success', '成功色'): '#28A745',
                t_visualization('color_warning', '警告色'): '#FFC107',
                t_visualization('color_danger', '危险色'): '#DC3545',
                t_visualization('color_info', '信息色'): '#17A2B8',
                t_visualization('color_background', '背景色'): '#F8F9FA',
                t_visualization('color_surface', '表面色'): '#FFFFFF',
                t_visualization('color_text', '文本色'): '#2C3E50',
                t_visualization('color_text_secondary', '次要文本色'): '#6C757D'
            },
            t_visualization('theme_dark', '深色版'): {
                t_visualization('color_primary', '主色'): '#00D4AA',
                t_visualization('color_secondary', '次色'): '#FF6B6B',
                t_visualization('color_accent', '强调色'): '#FFE66D',
                t_visualization('color_success', '成功色'): '#4ECDC4',
                t_visualization('color_warning', '警告色'): '#FFE66D',
                t_visualization('color_danger', '危险色'): '#FF6B6B',
                t_visualization('color_info', '信息色'): '#45B7D1',
                t_visualization('color_background', '背景色'): '#2C3E50',
                t_visualization('color_surface', '表面色'): '#34495E',
                t_visualization('color_text', '文本色'): '#ECF0F1',
                t_visualization('color_text_secondary', '次要文本色'): '#BDC3C7'
            },
            t_visualization('theme_classic', '经典版'): {
                t_visualization('color_primary', '主色'): '#1f77b4',
                t_visualization('color_secondary', '次色'): '#ff7f0e',
                t_visualization('color_accent', '强调色'): '#2ca02c',
                t_visualization('color_success', '成功色'): '#2ca02c',
                t_visualization('color_warning', '警告色'): '#ff7f0e',
                t_visualization('color_danger', '危险色'): '#d62728',
                t_visualization('color_info', '信息色'): '#17becf',
                t_visualization('color_background', '背景色'): '#ffffff',
                t_visualization('color_surface', '表面色'): '#f8f9fa',
                t_visualization('color_text', '文本色'): '#000000',
                t_visualization('color_text_secondary', '次要文本色'): '#666666'
            }
        }
        return themes.get(theme, themes[t_visualization('theme_professional', '专业版')])
    
    def _get_layout_config(self, theme: str) -> Dict[str, Any]:
        """获取布局配置"""
        return {
            t_visualization('template', '模板'): 'plotly_white' if theme != t_visualization('theme_dark', '深色版') else 'plotly_dark',
            t_visualization('font', '字体'): {'family': 'Microsoft YaHei, Arial, sans-serif', 'size': 12, 'color': self.colors[t_visualization('color_text', '文本色')]},
            t_visualization('title_font', '标题字体'): {'family': 'Microsoft YaHei, Arial, sans-serif', 'size': 18, 'color': self.colors[t_visualization('color_text', '文本色')]},
            t_visualization('paper_bgcolor', '纸张背景色'): self.colors[t_visualization('color_background', '背景色')],
            t_visualization('plot_bgcolor', '绘图背景色'): self.colors[t_visualization('color_surface', '表面色')],
            t_visualization('grid_color', '网格颜色'): self.colors[t_visualization('color_text_secondary', '次要文本色')] + '30',  # 30% 透明度
            t_visualization('margin', '边距'): {'l': 60, 'r': 60, 't': 80, 'b': 60}
        }

class StockTrendTemplate(BaseTemplate):
    """股票趋势图模板"""
    
    def __init__(self, theme: str = None):
        if theme is None:
            theme = t_visualization('theme_professional', '专业版')
        super().__init__(theme)
        self.default_config = {
            t_visualization('show_volume', '显示成交量'): True,
            t_visualization('show_ma', '显示均线'): True,
            t_visualization('ma_periods', '均线周期'): [5, 10, 20],
            t_visualization('show_bollinger', '显示布林带'): False,
            t_visualization('show_rsi', '显示RSI'): True,
            t_visualization('chart_height', '图表高度'): 800,
            t_visualization('main_ratio', '主图比例'): 0.7,
            t_visualization('volume_ratio', '成交量比例'): 0.15,
            t_visualization('indicator_ratio', '指标比例'): 0.15
        }
    
    def create_layout(self, **kwargs) -> Dict[str, Any]:
        """创建趋势图布局配置"""
        config = {**self.default_config, **kwargs}
        
        # 计算子图行数和规格
        rows = 1
        specs = [[{"secondary_y": True}]]
        subplot_titles = [t_visualization('stock_trend_chart', '股票趋势图')]
        
        if config[t_visualization('show_volume', '显示成交量')]:
            rows += 1
            specs.append([{"secondary_y": False}])
            subplot_titles.append(t_visualization('volume', '成交量'))
        
        if config[t_visualization('show_rsi', '显示RSI')]:
            rows += 1
            specs.append([{"secondary_y": False}])
            subplot_titles.append(t_visualization('rsi_indicator', 'RSI指标'))
        
        # 计算行高比例
        row_heights = []
        if rows == 1:
            row_heights = None
        elif rows == 2:
            row_heights = [0.85, 0.15]
        elif rows == 3:
            row_heights = [0.7, 0.15, 0.15]
        
        layout = {
            t_visualization('rows', '行数'): rows,
            t_visualization('cols', '列数'): 1,
            t_visualization('specs', '规格'): specs,
            t_visualization('subplot_titles', '子图标题'): subplot_titles,
            t_visualization('row_heights', '行高'): row_heights,
            t_visualization('vertical_spacing', '垂直间距'): 0.05,
            t_visualization('shared_xaxes', '共享X轴'): True
        }
        
        return layout
    
    def get_line_styles(self) -> Dict[str, Dict[str, Any]]:
        """获取线条样式配置"""
        return {
            t_visualization('price_line', '价格线'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_primary', '主色')],
                t_visualization('width', '宽度'): 2
            },
            t_visualization('ma5_line', '5日均线'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_accent', '强调色')],
                t_visualization('width', '宽度'): 1,
                t_visualization('dash', '线型'): 'solid'
            },
            t_visualization('ma10_line', '10日均线'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_secondary', '次色')],
                t_visualization('width', '宽度'): 1,
                t_visualization('dash', '线型'): 'dash'
            },
            t_visualization('ma20_line', '20日均线'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_info', '信息色')],
                t_visualization('width', '宽度'): 1,
                t_visualization('dash', '线型'): 'dot'
            },
            t_visualization('bollinger_upper', '布林带上轨'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_warning', '警告色')],
                t_visualization('width', '宽度'): 1,
                t_visualization('dash', '线型'): 'dash'
            },
            t_visualization('bollinger_lower', '布林带下轨'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_warning', '警告色')],
                t_visualization('width', '宽度'): 1,
                t_visualization('dash', '线型'): 'dash'
            },
            t_visualization('volume_bar', '成交量柱'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_text_secondary', '次要文本色')],
                t_visualization('opacity', '透明度'): 0.6
            },
            t_visualization('rsi_line', 'RSI线'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_primary', '主色')],
                t_visualization('width', '宽度'): 2
            }
        }
    
    def get_annotation_config(self) -> Dict[str, Any]:
        """获取注释配置"""
        return {
            t_visualization('font', '字体'): {'size': 10, 'color': self.colors[t_visualization('color_text', '文本色')]},
            t_visualization('bgcolor', '背景色'): self.colors[t_visualization('color_surface', '表面色')],
            t_visualization('bordercolor', '边框颜色'): self.colors[t_visualization('color_primary', '主色')],
            t_visualization('borderwidth', '边框宽度'): 1,
            t_visualization('showarrow', '显示箭头'): True,
            t_visualization('arrowhead', '箭头头部'): 2,
            t_visualization('arrowsize', '箭头大小'): 1,
            t_visualization('arrowwidth', '箭头宽度'): 2,
            t_visualization('arrowcolor', '箭头颜色'): self.colors[t_visualization('color_primary', '主色')]
        }

class IndustryHeatmapTemplate(BaseTemplate):
    """行业热力图模板"""
    
    def __init__(self, theme: str = None):
        if theme is None:
            theme = t_visualization('theme_professional', '专业版')
        super().__init__(theme)
        self.default_config = {
            t_visualization('colorscale_type', '颜色标度类型'): t_visualization('diverging', '发散型'),  # 发散型, 顺序型, 分类型
            t_visualization('show_text', '显示文本'): True,
            t_visualization('text_size', '文本大小'): 10,
            t_visualization('aspect_ratio', '纵横比'): t_visualization('auto', '自动'),  # 自动, 等比
            t_visualization('cluster_method', '聚类方法'): 'ward',  # ward, complete, average
            t_visualization('distance_metric', '距离度量'): 'euclidean',
            t_visualization('show_dendrogram', '显示树状图'): False,
            t_visualization('annotation_threshold', '注释阈值'): 0.5
        }
    
    def get_colorscales(self) -> Dict[str, List[List]]:
        """获取热力图颜色标度"""
        return {
            t_visualization('diverging_red_blue', '发散型红蓝'): [
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
            t_visualization('diverging_green_red', '发散型绿红'): [
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
            t_visualization('sequential_blue', '顺序型蓝色'): [
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
            t_visualization('theme_professional', '专业版'): [
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
            t_visualization('colorscale', '颜色标度'): colorscales[t_visualization('diverging_red_blue', '发散型红蓝')],
            t_visualization('neutral_value', '中性值'): 0,  # 中性值
            t_visualization('min_value', '最小值'): data_range[0],
            t_visualization('max_value', '最大值'): data_range[1],
            t_visualization('colorbar', '颜色条'): {
                t_visualization('title', '标题'): t_visualization('irsi_value', 'IRSI值'),
                t_visualization('title_side', '标题位置'): 'right',
                t_visualization('tick_mode', '刻度模式'): 'linear',
                t_visualization('tick0', '起始刻度'): data_range[0],
                t_visualization('dtick', '刻度间隔'): (data_range[1] - data_range[0]) / 10,
                t_visualization('thickness', '厚度'): 15,
                t_visualization('len', '长度'): 0.8,
                t_visualization('x', 'x位置'): 1.02
            },
            t_visualization('hovertemplate', '悬停模板'): "<b>%{y}</b><br>" +
                           t_visualization('time_label', '时间') + ": %{x}<br>" +
                           "IRSI: %{z:.2f}<br>" +
                           "<extra></extra>",
            t_visualization('showscale', '显示标度'): True
        }
    
    def get_clustering_config(self) -> Dict[str, Any]:
        """获取聚类配置"""
        return {
            t_visualization('linkage_method', '连接方法'): self.default_config[t_visualization('cluster_method', '聚类方法')],
            t_visualization('distance_metric', '距离度量'): self.default_config[t_visualization('distance_metric', '距离度量')],
            t_visualization('dendrogram_colors', '树状图颜色'): [self.colors[t_visualization('color_primary', '主色')], self.colors[t_visualization('color_secondary', '次色')],
                                self.colors[t_visualization('color_accent', '强调色')], self.colors[t_visualization('color_info', '信息色')]],
            t_visualization('dendrogram_linewidth', '树状图线宽'): 2
        }

class MarketSentimentTemplate(BaseTemplate):
    """市场情绪图模板"""
    
    def __init__(self, theme: str = None):
        if theme is None:
            theme = t_visualization('theme_professional', '专业版')
        super().__init__(theme)
        self.default_config = {
            t_visualization('scatter_size_range', '散点大小范围'): (5, 20),
            t_visualization('opacity', '透明度'): 0.7,
            t_visualization('show_regression', '显示回归线'): True,
            t_visualization('show_confidence', '显示置信区间'): False,
            t_visualization('show_quadrant', '显示象限线'): True,
            t_visualization('quadrant_style', '象限线样式'): 'dash',
            t_visualization('bubble_scaling', '气泡缩放'): 'sqrt',  # linear, sqrt, log
            t_visualization('colorscale', '颜色标度'): 'viridis'  # viridis, plasma, RdYlGn
        }
    
    def get_scatter_config(self) -> Dict[str, Any]:
        """获取散点图配置"""
        return {
            t_visualization('mode', '模式'): 'markers',
            t_visualization('marker', '标记'): {
                t_visualization('opacity', '透明度'): self.default_config[t_visualization('opacity', '透明度')],
                t_visualization('line', '线条'): {'width': 1, 'color': self.colors[t_visualization('color_text_secondary', '次要文本色')]},
                t_visualization('colorscale', '颜色标度'): self.default_config[t_visualization('colorscale', '颜色标度')],
                t_visualization('showscale', '显示标度'): True,
                t_visualization('sizemode', '大小模式'): 'diameter',
                t_visualization('sizeref', '大小参考'): 1,
                t_visualization('sizemin', '最小大小'): self.default_config[t_visualization('scatter_size_range', '散点大小范围')][0]
            },
            t_visualization('hovertemplate', '悬停模板'): "<b>%{text}</b><br>" +
                           t_visualization('x_axis_label', 'X轴') + ": %{x:.2f}<br>" +
                           t_visualization('y_axis_label', 'Y轴') + ": %{y:.2f}<br>" +
                           "<extra></extra>"
        }
    
    def get_quadrant_config(self) -> Dict[str, Any]:
        """获取象限配置"""
        return {
            t_visualization('line_color', '线条颜色'): self.colors[t_visualization('color_text_secondary', '次要文本色')],
            t_visualization('line_width', '线条宽度'): 1,
            t_visualization('line_dash', '线条样式'): self.default_config[t_visualization('quadrant_style', '象限线样式')],
            t_visualization('opacity', '透明度'): 0.5,
            t_visualization('quadrant_colors', '象限颜色'): {
                t_visualization('high_return_low_risk', '高收益低风险'): self.colors[t_visualization('color_success', '成功色')],    # 优质股 - 绿色
                t_visualization('high_return_high_risk', '高收益高风险'): self.colors[t_visualization('color_warning', '警告色')],   # 激进股 - 橙色
                t_visualization('low_return_low_risk', '低收益低风险'): self.colors[t_visualization('color_info', '信息色')],        # 稳健股 - 蓝色
                t_visualization('low_return_high_risk', '低收益高风险'): self.colors[t_visualization('color_danger', '危险色')]      # 风险股 - 红色
            },
            t_visualization('quadrant_labels', '象限标签'): {
                t_visualization('high_return_low_risk', '高收益低风险'): t_visualization('quality_stock', '优质股'),
                t_visualization('high_return_high_risk', '高收益高风险'): t_visualization('aggressive_stock', '激进股'),
                t_visualization('low_return_low_risk', '低收益低风险'): t_visualization('stable_stock', '稳健股'),
                t_visualization('low_return_high_risk', '低收益高风险'): t_visualization('risky_stock', '风险股')
            }
        }
    
    def get_regression_config(self) -> Dict[str, Any]:
        """获取回归线配置"""
        return {
            t_visualization('line', '线条'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_primary', '主色')],
                t_visualization('width', '宽度'): 2,
                t_visualization('dash', '样式'): 'solid'
            },
            t_visualization('confidence_interval', '置信区间'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_primary', '主色')],
                t_visualization('opacity', '透明度'): 0.2,
                t_visualization('fill', '填充'): 'tonexty'
            }
        }

class PerformanceTemplate(BaseTemplate):
    """性能监控模板"""
    
    def __init__(self, theme: str = None):
        if theme is None:
            theme = t_visualization('theme_professional', '专业版')
        super().__init__(theme)
        self.default_config = {
            t_visualization('gauge_ranges', '仪表盘范围'): {
                t_visualization('good', '良好'): (0, 60),
                t_visualization('warning', '警告'): (60, 85),
                t_visualization('critical', '严重'): (85, 100)
            },
            t_visualization('gauge_colors', '仪表盘颜色'): {
                t_visualization('good', '良好'): '#E6F7E6',
                t_visualization('warning', '警告'): '#FFF4E6',
                t_visualization('critical', '严重'): '#FFE6E6'
            },
            t_visualization('threshold_color', '阈值颜色'): '#DC3545',
            t_visualization('bar_colors', '柱状图颜色'): {
                t_visualization('excellent', '优秀'): '#28A745',
                t_visualization('good', '良好'): '#17A2B8',
                t_visualization('warning', '警告'): '#FFC107',
                t_visualization('poor', '差'): '#DC3545'
            },
            t_visualization('time_window', '时间窗口'): t_visualization('1_hour', '1小时'),  # Options: 1h, 6h, 24h, 7d
            t_visualization('refresh_interval', '刷新间隔'): 60  # seconds
        }
    
    def get_gauge_config(self, metric_name: str, value_range: Tuple[float, float] = (0, 100)) -> Dict[str, Any]:
        """获取仪表盘配置"""
        ranges = self.default_config[t_visualization('gauge_ranges', '仪表盘范围')]
        colors = self.default_config[t_visualization('gauge_colors', '仪表盘颜色')]
        
        # Adjust range based on value domain
        scale_factor = (value_range[1] - value_range[0]) / 100
        
        return {
            t_visualization('mode', '模式'): "gauge+number+delta",
            t_visualization('domain', '域'): {'x': [0, 1], 'y': [0, 1]},
            t_visualization('title', '标题'): {'text': metric_name, 'font': {'size': 14}},
            t_visualization('gauge', '仪表盘'): {
                t_visualization('axis', '轴'): {'range': [value_range[0], value_range[1]]},
                t_visualization('bar', '条'): {'color': self.colors[t_visualization('color_primary', '主色')]},
                t_visualization('steps', '步骤'): [
                    {
                        'range': [value_range[0], value_range[0] + ranges[t_visualization('good', '良好')][1] * scale_factor],
                        'color': colors[t_visualization('good', '良好')]
                    },
                    {
                        'range': [value_range[0] + ranges[t_visualization('good', '良好')][1] * scale_factor,
                                value_range[0] + ranges[t_visualization('warning', '警告')][1] * scale_factor],
                        'color': colors[t_visualization('warning', '警告')]
                    },
                    {
                        'range': [value_range[0] + ranges[t_visualization('warning', '警告')][1] * scale_factor, value_range[1]],
                        'color': colors[t_visualization('critical', '严重')]
                    }
                ],
                t_visualization('threshold', '阈值'): {
                    t_visualization('line', '线条'): {'color': self.default_config[t_visualization('threshold_color', '阈值颜色')], 'width': 4},
                    t_visualization('thickness', '厚度'): 0.75,
                    t_visualization('value', '值'): value_range[0] + ranges[t_visualization('warning', '警告')][1] * scale_factor
                }
            }
        }
    
    def get_bar_config(self, orientation: str = 'vertical') -> Dict[str, Any]:
        """获取柱状图配置"""
        colors = self.default_config[t_visualization('bar_colors', '柱状图颜色')]
        
        return {
            t_visualization('type', '类型'): 'bar',
            t_visualization('orientation', '方向'): orientation,
            t_visualization('marker', '标记'): {
                t_visualization('color', '颜色'): list(colors.values()),
                t_visualization('line', '线条'): {
                    t_visualization('color', '颜色'): self.colors[t_visualization('color_border', '边框色')],
                    t_visualization('width', '宽度'): 1
                },
                t_visualization('opacity', '透明度'): 0.8
            },
            t_visualization('text', '文本'): {
                t_visualization('position', '位置'): 'auto',
                t_visualization('font', '字体'): {
                    t_visualization('size', '大小'): 10,
                    t_visualization('color', '颜色'): self.colors[t_visualization('color_text', '文字色')]
                }
            },
            t_visualization('hovertemplate', '悬停模板'): '<b>%{x}</b><br>' + t_visualization('value', '值') + ': %{y}<extra></extra>'
        }
    
    def get_performance_colors(self, values: List[float], thresholds: Dict[str, float] = None) -> List[str]:
        """根据性能值获取颜色"""
        if thresholds is None:
            thresholds = {t_visualization('excellent', '优秀'): 90, t_visualization('good', '良好'): 70, t_visualization('warning', '警告'): 50}
        
        colors = []
        bar_colors = self.default_config[t_visualization('bar_colors', '柱状图颜色')]
        
        for value in values:
            if value >= thresholds[t_visualization('excellent', '优秀')]:
                colors.append(bar_colors[t_visualization('excellent', '优秀')])
            elif value >= thresholds[t_visualization('good', '良好')]:
                colors.append(bar_colors[t_visualization('good', '良好')])
            elif value >= thresholds[t_visualization('warning', '警告')]:
                colors.append(bar_colors[t_visualization('warning', '警告')])
            else:
                colors.append(bar_colors[t_visualization('poor', '差')])
        
        return colors
    
    def get_time_series_config(self) -> Dict[str, Any]:
        """获取时间序列图配置"""
        return {
            t_visualization('line', '线条'): {
                t_visualization('color', '颜色'): self.colors[t_visualization('color_primary', '主色')],
                t_visualization('width', '宽度'): 2
            },
            t_visualization('fill', '填充'): 'tonexty',
            t_visualization('fill_color', '填充颜色'): f"rgba({self.colors[t_visualization('color_primary', '主色')][1:]}, 0.2)",
            t_visualization('hovertemplate', '悬停模板'): t_visualization('time_label', '时间') + ": %{x}<br>" +
                           t_visualization('value_label', '数值') + ": %{y:.2f}<br>" +
                           "<extra></extra>"
        }

class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self.templates = {
            t_visualization('stock_trend', '股票趋势'): StockTrendTemplate,
            t_visualization('industry_heatmap', '行业热力图'): IndustryHeatmapTemplate,
            t_visualization('market_sentiment', '市场情绪'): MarketSentimentTemplate,
            t_visualization('performance_monitor', '性能监控'): PerformanceTemplate
        }
        self.theme = t_visualization('theme_professional', '专业版')
    
    def get_template(self, template_name: str, theme: str = None) -> BaseTemplate:
        """获取指定模板"""
        if template_name not in self.templates:
            raise ValueError(t_common('unsupported_template_type', '不支持的模板类型') + f": {template_name}")
        
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
        return [t_visualization('theme_professional', '专业版'), t_visualization('theme_dark', '深色版'), t_visualization('theme_classic', '经典版')]

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
        logger.warning(t_common('plotly_not_installed', 'Plotly未安装，无法创建高级图表'))
        return None
    
    template = get_template(template_name)
    
    if template_name == t_visualization('stock_trend', '股票趋势'):
        layout_config = template.create_layout(**kwargs)
        fig = make_subplots(**layout_config)
    elif template_name == t_visualization('industry_heatmap', '行业热力图'):
        fig = go.Figure()
    elif template_name == t_visualization('market_sentiment', '市场情绪'):
        fig = make_subplots(rows=2, cols=2, 
                          subplot_titles=(t_visualization('scatter_plot_1', '散点图1'), t_visualization('scatter_plot_2', '散点图2'), t_visualization('distribution_plot', '分布图'), t_visualization('statistics_plot', '统计图')))
    elif template_name == t_visualization('performance_monitor', '性能监控'):
        fig = make_subplots(rows=3, cols=3,
                          specs=[
                              [{"type": "indicator"}, {"type": "scatter"}, {"type": "indicator"}],
                              [{"type": "bar"}, {"type": "pie"}, {"type": "bar"}],
                              [{"type": "scatter"}, {"type": "bar"}, {"type": "indicator"}]
                          ])
    else:
        fig = go.Figure()
    
    # Apply template styles
    fig.update_layout(
        template=template.layout_config[t_visualization('template', '模板')],
        font=template.layout_config[t_visualization('font', '字体')],
        paper_bgcolor=template.layout_config[t_visualization('paper_bgcolor', '纸张背景色')],
        plot_bgcolor=template.layout_config[t_visualization('plot_bgcolor', '绘图背景色')],
        margin=template.layout_config[t_visualization('margin', '边距')]
    )
    
    return fig