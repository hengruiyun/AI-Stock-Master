# -*- coding: utf-8 -*-
"""
LLM分析结果结构化输出模型
实现第一阶段改进：标准化LLM分析结果格式
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RiskLevel(str, Enum):
    """风险等级枚举"""
    VERY_LOW = "极低风险"
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    VERY_HIGH = "极高风险"


class TrendDirection(str, Enum):
    """趋势方向枚举"""
    STRONG_UP = "强势上涨"
    UP = "温和上涨"
    SIDEWAYS = "震荡整理"
    DOWN = "温和下跌"
    STRONG_DOWN = "快速下跌"


class InvestmentAction(str, Enum):
    """投资建议枚举"""
    STRONG_BUY = "强烈推荐"
    BUY = "推荐买入"
    HOLD = "持有观望"
    SELL = "建议卖出"
    STRONG_SELL = "强烈卖出"


class MarketSentiment(str, Enum):
    """市场情绪枚举"""
    EXTREMELY_BULLISH = "极度乐观"
    BULLISH = "乐观"
    NEUTRAL = "中性"
    BEARISH = "悲观"
    EXTREMELY_BEARISH = "极度悲观"


class MarketAnalysis(BaseModel):
    """市场分析结果"""
    msci_score: float = Field(..., description="市场情绪综合指数")
    sentiment: MarketSentiment = Field(..., description="市场情绪")
    trend_direction: TrendDirection = Field(..., description="趋势方向")
    volatility_level: str = Field(..., description="波动性水平")
    risk_assessment: RiskLevel = Field(..., description="风险评估")
    confidence_score: float = Field(..., ge=0, le=100, description="分析置信度(0-100)")
    key_factors: List[str] = Field(..., description="关键影响因素")


class SectorAnalysis(BaseModel):
    """板块分析结果"""
    sector_name: str = Field(..., description="板块名称")
    irsi_score: float = Field(..., description="行业相对强度指数")
    ranking: int = Field(..., description="排名")
    strength_level: str = Field(..., description="强度等级")
    outlook: str = Field(..., description="前景展望")
    key_drivers: List[str] = Field(..., description="关键驱动因素")


class StockRecommendation(BaseModel):
    """个股推荐结果"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    rtsi_score: float = Field(..., description="个股趋势强度指数")
    action: InvestmentAction = Field(..., description="投资建议")
    target_price: Optional[float] = Field(None, description="目标价格")
    stop_loss: Optional[float] = Field(None, description="止损价格")
    holding_period: str = Field(..., description="建议持有期")
    reasons: List[str] = Field(..., description="推荐理由")
    risks: List[str] = Field(..., description="风险提示")


class RiskManagement(BaseModel):
    """风险管理建议"""
    overall_risk: RiskLevel = Field(..., description="整体风险等级")
    position_sizing: str = Field(..., description="仓位建议")
    diversification: str = Field(..., description="分散化建议")
    stop_loss_strategy: str = Field(..., description="止损策略")
    monitoring_points: List[str] = Field(..., description="监控要点")


class TimeframeOutlook(BaseModel):
    """时间框架展望"""
    timeframe: str = Field(..., description="时间框架")
    outlook: str = Field(..., description="展望描述")
    key_events: List[str] = Field(..., description="关键事件")
    strategy: str = Field(..., description="策略建议")


class StructuredAnalysisResult(BaseModel):
    """结构化分析结果 - 主要输出模型"""
    
    # 分析元数据
    analysis_timestamp: str = Field(..., description="分析时间戳")
    data_period: str = Field(..., description="数据周期")
    analysis_version: str = Field(default="v1.0", description="分析版本")
    
    # 核心分析结果
    market_analysis: MarketAnalysis = Field(..., description="市场分析")
    sector_rankings: List[SectorAnalysis] = Field(..., description="板块排名分析")
    stock_recommendations: List[StockRecommendation] = Field(..., description="个股推荐")
    
    # 风险管理
    risk_management: RiskManagement = Field(..., description="风险管理建议")
    
    # 时间框架展望
    short_term_outlook: TimeframeOutlook = Field(..., description="短期展望(1-2周)")
    medium_term_outlook: TimeframeOutlook = Field(..., description="中期展望(1-3个月)")
    
    # 执行建议
    immediate_actions: List[str] = Field(..., description="立即执行建议")
    monitoring_schedule: str = Field(..., description="监控计划")
    
    # 分析师总结
    executive_summary: str = Field(..., description="执行摘要")
    confidence_level: float = Field(..., ge=0, le=100, description="整体分析置信度")
    
    # 免责声明
    disclaimer: str = Field(
        default="本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。",
        description="免责声明"
    )


# 简化版本 - 用于快速分析
class QuickAnalysisResult(BaseModel):
    """快速分析结果"""
    market_sentiment: MarketSentiment = Field(..., description="市场情绪")
    top_sectors: List[str] = Field(..., max_items=3, description="前3强势板块")
    top_stocks: List[str] = Field(..., max_items=5, description="前5推荐个股")
    risk_level: RiskLevel = Field(..., description="风险等级")
    key_message: str = Field(..., max_length=200, description="核心信息")
    confidence: float = Field(..., ge=0, le=100, description="置信度")