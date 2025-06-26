# -*- coding: utf-8 -*-
"""
GUI模块 - Windows桌面界面组件

第四期: GUI界面核心
基于软件界面样本.html设计，实现Windows经典风格的股票分析界面

主要组件:
- MainWindow: 主窗口框架
- DataWidgets: 数据展示组件
- BasicCharts: 基础图表组件
- AnalysisDialogs: 分析对话框
"""

from .main_window import StockAnalyzerMainWindow
from .data_widgets import StockListWidget, AnalysisResultWidget, RankingWidget
from .basic_charts import TrendChart, IndustryChart, MarketChart
from .analysis_dialogs import AnalysisProgressDialog, SettingsDialog, AboutDialog

__all__ = [
    'StockAnalyzerMainWindow',
    'StockListWidget', 'AnalysisResultWidget', 'RankingWidget',
    'TrendChart', 'IndustryChart', 'MarketChart',
    'AnalysisProgressDialog', 'SettingsDialog', 'AboutDialog'
]

__version__ = "2.0.0"
__author__ = "267278466@qq.com"