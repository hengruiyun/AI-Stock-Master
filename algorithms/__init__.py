"""
AI股票趋势分析系统 - 核心算法模块

本模块包含三大核心分析算法：
1. RTSI - 评级趋势强度指数 (Rating Trend Strength Index)
2. IRSI - 行业相对强度指数 (Industry Relative Strength Index)  
3. MSCI - 市场情绪综合指数 (Market Sentiment Composite Index)

作者: 267278466@qq.com
版本：v1.0
创建时间：2025-06-07
"""

from .rtsi_calculator import calculate_rating_trend_strength_index, batch_calculate_rtsi, get_rtsi_ranking, RTSICalculator
from .irsi_calculator import calculate_industry_relative_strength, detect_industry_rotation_signals, get_strongest_industries
from .msci_calculator import calculate_market_sentiment_composite_index, analyze_market_extremes, generate_risk_warnings

__version__ = "1.0.0"
__author__ = "267278466@qq.com"

__all__ = [
    # RTSI算法
    'calculate_rating_trend_strength_index',
    'batch_calculate_rtsi', 
    'get_rtsi_ranking',
    'RTSICalculator',
    
    # IRSI算法
    'calculate_industry_relative_strength',
    'detect_industry_rotation_signals',
    'get_strongest_industries',
    
    # MSCI算法
    'calculate_market_sentiment_composite_index',
    'analyze_market_extremes',
    'generate_risk_warnings'
] 