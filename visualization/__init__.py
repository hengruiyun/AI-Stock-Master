# -*- coding: utf-8 -*-
"""
AI股票大师 - 高级可视化模块

本模块提供专业级的数据可视化功能，包括：
- 交互式趋势图表
- 行业轮动热力图  
- 多维度散点图
- 性能监控仪表板
- 自定义图表样式
"""

from .advanced_charts import (
    InteractiveTrendChart,
    HeatmapChart, 
    ScatterPlotChart,
    PerformanceDashboard,
    ChartStyleManager
)

from .chart_templates import (
    StockTrendTemplate,
    IndustryHeatmapTemplate,
    MarketSentimentTemplate,
    PerformanceTemplate
)

from .export_manager import (
    ChartExporter,
    ReportImageGenerator,
    InteractiveHTMLExporter
)

__version__ = "2.0.0"
__author__ = "267278466@qq.com"

# 公共API导出
__all__ = [
    # 核心图表类
    'InteractiveTrendChart',
    'HeatmapChart', 
    'ScatterPlotChart',
    'PerformanceDashboard',
    
    # 样式管理
    'ChartStyleManager',
    
    # 模板系统
    'StockTrendTemplate',
    'IndustryHeatmapTemplate', 
    'MarketSentimentTemplate',
    'PerformanceTemplate',
    
    # 导出功能
    'ChartExporter',
    'ReportImageGenerator',
    'InteractiveHTMLExporter',
    
    # 便捷函数
    'create_stock_trend_chart',
    'create_industry_heatmap',
    'create_market_sentiment_chart',
    'create_performance_dashboard',
    'export_chart_collection'
]

# 便捷函数
def create_stock_trend_chart(stock_data, **kwargs):
    """创建股票趋势图的便捷函数"""
    chart = InteractiveTrendChart(**kwargs)
    return chart.create_stock_trend(stock_data)

def create_industry_heatmap(industry_data, **kwargs):
    """创建行业热力图的便捷函数"""
    chart = HeatmapChart(**kwargs)
    return chart.create_industry_heatmap(industry_data)

def create_market_sentiment_chart(market_data, **kwargs):
    """创建市场情绪图的便捷函数"""
    chart = ScatterPlotChart(**kwargs)
    return chart.create_sentiment_scatter(market_data)

def create_performance_dashboard(performance_data, **kwargs):
    """创建性能仪表板的便捷函数"""
    dashboard = PerformanceDashboard(**kwargs)
    return dashboard.create_dashboard(performance_data)

def export_chart_collection(charts, output_dir, formats=['png', 'pdf', 'html']):
    """批量导出图表集合的便捷函数"""
    exporter = ChartExporter()
    return exporter.export_collection(charts, output_dir, formats)

# 模块级配置
DEFAULT_STYLE = '专业版'
DEFAULT_DPI = 300
DEFAULT_FIGSIZE = (12, 8)

# 支持的导出格式
SUPPORTED_FORMATS = ['png', 'jpg', 'pdf', 'svg', 'html', 'json']

# 颜色主题
COLOR_THEMES = {
    '专业版': {
        '主色': '#2E86AB',
        '次色': '#A23B72', 
        '强调色': '#F18F01',
        '背景色': '#F8F9FA',
        '文本色': '#2C3E50'
    },
    '深色': {
        '主色': '#00D4AA',
        '次色': '#FF6B6B',
        '强调色': '#FFE66D', 
        '背景色': '#2C3E50',
        '文本色': '#ECF0F1'
    },
    '经典': {
        '主色': '#1f77b4',
        '次色': '#ff7f0e',
        '强调色': '#2ca02c',
        '背景色': '#ffffff', 
        '文本色': '#000000'
    }
}

print(f"AI股票大师可视化模块 v{__version__} 加载完成")
print(f"支持格式: {', '.join(SUPPORTED_FORMATS)}")
print(f"可用主题: {', '.join(COLOR_THEMES.keys())}")