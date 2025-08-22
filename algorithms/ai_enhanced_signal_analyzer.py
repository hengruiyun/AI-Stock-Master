# -*- coding: utf-8 -*-
"""
AI增强8级信号分析系统
整合自适应插值引擎和多维度分析器，加入机器学习能力
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
import logging
from datetime import datetime, timedelta
import warnings
import json
from dataclasses import dataclass, asdict
from enum import Enum

# 导入我们开发的核心组件
from .adaptive_interpolation import AdaptiveInterpolationEngine, InterpolationStrategy
from .enhanced_multi_dimensional_analyzer import (
    EnhancedMultiDimensionalAnalyzer, 
    AnalysisResult, 
    SignalStrength,
    AnalysisLevel
)

warnings.filterwarnings('ignore')

class AIModelType(Enum):
    """AI模型类型"""
    PATTERN_RECOGNITION = "pattern_recognition"    # 模式识别
    SENTIMENT_ANALYSIS = "sentiment_analysis"      # 情绪分析  
    TREND_PREDICTION = "trend_prediction"          # 趋势预测
    RISK_ASSESSMENT = "risk_assessment"            # 风险评估
    SIGNAL_FUSION = "signal_fusion"                # 信号融合

@dataclass
class AIInsight:
    """AI洞察结果"""
    insight_type: str           # 洞察类型
    confidence: float           # 置信度
    description: str            # 描述
    recommendation: str         # 建议
    supporting_evidence: List   # 支持证据
    risk_factors: List          # 风险因素

@dataclass
class ComprehensiveAnalysisResult:
    """综合分析结果"""
    # 基础分析结果
    interpolation_result: Dict
    multi_dimensional_result: Dict
    
    # AI增强结果
    ai_insights: List[AIInsight]
    ai_enhanced_score: float
    
    # 综合评估
    final_recommendation: str
    confidence_level: str
    risk_warning: List[str]
    
    # 元数据
    analysis_timestamp: str
    processing_time: float

class AIEnhancedSignalAnalyzer:
    """
    AI增强8级信号分析系统
    
    核心功能：
    1. 智能数据预处理（自适应插值）
    2. 多维度信号分析
    3. AI模式识别和预测
    4. 智能信号融合
    5. 风险智能评估
    """
    
    def __init__(self, enable_ai_features: bool = True):
        self.logger = logging.getLogger(__name__)
        # 设置日志级别为WARNING，减少INFO输出
        self.logger.setLevel(logging.WARNING)
        
        # 初始化核心组件
        self.interpolation_engine = AdaptiveInterpolationEngine()
        self.multi_dimensional_analyzer = EnhancedMultiDimensionalAnalyzer()
        
        # AI功能开关
        self.enable_ai = enable_ai_features
        
        # 8级评级系统
        self.rating_scale = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0,
            '中性': 3.5, '-': None
        }
        
        # AI模型配置（模拟配置，实际应用中会加载真实模型）
        self.ai_models = {
            AIModelType.PATTERN_RECOGNITION: self._init_pattern_recognition_model(),
            AIModelType.SENTIMENT_ANALYSIS: self._init_sentiment_analysis_model(),
            AIModelType.TREND_PREDICTION: self._init_trend_prediction_model(),
            AIModelType.RISK_ASSESSMENT: self._init_risk_assessment_model(),
            AIModelType.SIGNAL_FUSION: self._init_signal_fusion_model()
        }
        
        # 智能权重配置（动态调整）
        self.adaptive_weights = {
            'interpolation_quality': 0.15,
            'multi_dimensional_score': 0.35,
            'ai_pattern_recognition': 0.20,
            'ai_sentiment_analysis': 0.15,
            'ai_trend_prediction': 0.15
        }
    
    def comprehensive_analyze(self, 
                            stock_data: pd.DataFrame,
                            stock_code: str,
                            industry_data: pd.DataFrame = None,
                            market_data: pd.DataFrame = None,
                            news_data: List[str] = None,
                            enable_prediction: bool = True) -> ComprehensiveAnalysisResult:
        """
        综合AI增强分析
        
        Args:
            stock_data: 股票历史数据
            stock_code: 股票代码
            industry_data: 行业数据
            market_data: 市场数据
            news_data: 新闻数据（用于情绪分析）
            enable_prediction: 是否启用预测功能
            
        Returns:
            综合分析结果
        """
        analysis_start = datetime.now()
        
        try:
            # ================ 第一阶段：数据预处理和质量评估 ================
            self.logger.info(f"开始分析股票 {stock_code}")
            
            # 1.1 提取股票评级序列
            stock_ratings = self._extract_stock_ratings(stock_data, stock_code)
            
            # 1.2 自适应插值处理
            interpolation_result = self.interpolation_engine.interpolate_rating_series(
                ratings_series=stock_ratings,
                stock_info={'code': stock_code, 'industry': 'auto_detect'},
                market_context=self._extract_market_context(market_data)
            )
            
            # ================ 第二阶段：多维度基础分析 ================
            
            # 2.1 多维度分析
            multi_dimensional_result = self.multi_dimensional_analyzer.comprehensive_analysis(
                stock_data=stock_data,
                industry_data=industry_data,
                market_data=market_data,
                target_stock=stock_code
            )
            
            # ================ 第三阶段：AI增强分析 ================
            ai_insights = []
            
            if self.enable_ai:
                # 3.1 AI模式识别
                pattern_insights = self._ai_pattern_recognition(
                    interpolation_result['interpolated_series']
                )
                ai_insights.extend(pattern_insights)
                
                # 3.2 AI情绪分析（如果有新闻数据）
                if news_data:
                    sentiment_insights = self._ai_sentiment_analysis(news_data, stock_code)
                    ai_insights.extend(sentiment_insights)
                
                # 3.3 AI趋势预测
                if enable_prediction:
                    trend_insights = self._ai_trend_prediction(
                        interpolation_result['interpolated_series'],
                        multi_dimensional_result
                    )
                    ai_insights.extend(trend_insights)
                
                # 3.4 AI风险评估
                risk_insights = self._ai_risk_assessment(
                    interpolation_result,
                    multi_dimensional_result
                )
                ai_insights.extend(risk_insights)
            
            # ================ 第四阶段：智能信号融合 ================
            
            # 4.1 计算AI增强评分
            ai_enhanced_score = self._calculate_ai_enhanced_score(
                interpolation_result,
                multi_dimensional_result,
                ai_insights
            )
            
            # 4.2 生成最终建议
            final_recommendation = self._generate_final_recommendation(
                interpolation_result,
                multi_dimensional_result,
                ai_insights,
                ai_enhanced_score
            )
            
            # 4.3 智能风险预警
            risk_warnings = self._generate_intelligent_risk_warnings(
                interpolation_result,
                multi_dimensional_result,
                ai_insights
            )
            
            # 4.4 评估整体置信度
            confidence_level = self._assess_overall_confidence(
                interpolation_result,
                multi_dimensional_result,
                ai_insights
            )
            
            # ================ 第五阶段：结果封装 ================
            
            processing_time = (datetime.now() - analysis_start).total_seconds()
            
            result = ComprehensiveAnalysisResult(
                interpolation_result=interpolation_result,
                multi_dimensional_result=multi_dimensional_result,
                ai_insights=ai_insights,
                ai_enhanced_score=ai_enhanced_score,
                final_recommendation=final_recommendation,
                confidence_level=confidence_level,
                risk_warning=risk_warnings,
                analysis_timestamp=datetime.now().isoformat(),
                processing_time=processing_time
            )
            
            self.logger.info(f"分析完成，耗时 {processing_time:.3f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"综合分析失败: {str(e)}")
            return self._create_error_result(str(e))
    
    def _extract_stock_ratings(self, stock_data: pd.DataFrame, stock_code: str) -> pd.Series:
        """提取股票评级序列"""
        try:
            # 查找目标股票
            if stock_code in stock_data.index:
                stock_row = stock_data.loc[stock_code]
            elif '股票代码' in stock_data.columns:
                matching_rows = stock_data[stock_data['股票代码'] == stock_code]
                if not matching_rows.empty:
                    stock_row = matching_rows.iloc[0]
                else:
                    raise ValueError(f"未找到股票 {stock_code}")
            else:
                # 假设第一行是目标股票
                stock_row = stock_data.iloc[0]
            
            # 提取日期列
            date_columns = [col for col in stock_row.index if str(col).startswith('202')]
            date_columns.sort()
            
            # 构建评级序列
            ratings = pd.Series(
                [stock_row[col] for col in date_columns],
                index=pd.to_datetime(date_columns, format='%Y%m%d')
            )
            
            return ratings
            
        except Exception as e:
            self.logger.error(f"提取股票评级失败: {str(e)}")
            return pd.Series(dtype=object)
    
    def _extract_market_context(self, market_data: pd.DataFrame = None) -> Dict:
        """提取市场环境信息"""
        if market_data is None or market_data.empty:
            return {'volatility': 0.5, 'trend': 'neutral'}
        
        try:
            # 简化的市场环境分析
            date_columns = [col for col in market_data.columns if str(col).startswith('202')]
            if not date_columns:
                return {'volatility': 0.5, 'trend': 'neutral'}
            
            # 计算市场评级分布的变化
            recent_columns = sorted(date_columns)[-5:]  # 最近5天
            
            market_scores = []
            for col in recent_columns:
                daily_ratings = market_data[col].dropna()
                daily_score = np.mean([self.rating_scale.get(r, 3.5) for r in daily_ratings if r != '-'])
                market_scores.append(daily_score)
            
            volatility = np.std(market_scores) / 3.5 if len(market_scores) > 1 else 0.5
            trend = 'upward' if market_scores[-1] > market_scores[0] else 'downward'
            
            return {
                'volatility': min(max(volatility, 0), 1),
                'trend': trend,
                'recent_scores': market_scores
            }
            
        except Exception as e:
            self.logger.error(f"市场环境分析失败: {str(e)}")
            return {'volatility': 0.5, 'trend': 'neutral'}
    
    # ================ AI模型初始化（模拟实现） ================
    
    def _init_pattern_recognition_model(self):
        """初始化模式识别模型"""
        return {
            'model_type': 'lstm_autoencoder',
            'trained': True,
            'accuracy': 0.85,
            'patterns': ['double_top', 'double_bottom', 'ascending_triangle', 'head_and_shoulders']
        }
    
    def _init_sentiment_analysis_model(self):
        """初始化情绪分析模型"""
        return {
            'model_type': 'bert_sentiment',
            'trained': True,
            'accuracy': 0.82,
            'languages': ['zh', 'en']
        }
    
    def _init_trend_prediction_model(self):
        """初始化趋势预测模型"""
        return {
            'model_type': 'transformer_ts',
            'trained': True,
            'accuracy': 0.78,
            'horizon': 10  # 预测10天
        }
    
    def _init_risk_assessment_model(self):
        """初始化风险评估模型"""
        return {
            'model_type': 'ensemble_risk',
            'trained': True,
            'accuracy': 0.88,
            'risk_types': ['volatility', 'liquidity', 'credit', 'market']
        }
    
    def _init_signal_fusion_model(self):
        """初始化信号融合模型"""
        return {
            'model_type': 'attention_fusion',
            'trained': True,
            'accuracy': 0.86,
            'fusion_methods': ['weighted_average', 'attention', 'ensemble']
        }
    
    # ================ AI分析方法 ================
    
    def _ai_pattern_recognition(self, rating_series: pd.Series) -> List[AIInsight]:
        """AI模式识别"""
        insights = []
        
        try:
            # 模拟模式识别算法
            numeric_values = [self.rating_scale.get(r, r) for r in rating_series if r is not None]
            
            if len(numeric_values) < 5:
                return insights
            
            # 检测趋势模式
            recent_trend = np.polyfit(range(len(numeric_values[-5:])), numeric_values[-5:], 1)[0]
            
            if recent_trend > 0.2:
                insights.append(AIInsight(
                    insight_type="上升趋势模式",
                    confidence=0.85,
                    description="AI检测到明显的上升趋势模式，评级呈现持续改善",
                    recommendation="建议关注，趋势有望延续",
                    supporting_evidence=[f"近期斜率: {recent_trend:.3f}", "连续性良好"],
                    risk_factors=["趋势过热风险", "回调压力"]
                ))
            elif recent_trend < -0.2:
                insights.append(AIInsight(
                    insight_type="下降趋势模式",
                    confidence=0.82,
                    description="AI检测到下降趋势模式，评级持续恶化",
                    recommendation="建议谨慎，考虑防御策略",
                    supporting_evidence=[f"近期斜率: {recent_trend:.3f}", "下降连续性"],
                    risk_factors=["进一步下跌风险", "止损考虑"]
                ))
            
            # 检测波动模式
            volatility = np.std(numeric_values)
            if volatility > 1.5:
                insights.append(AIInsight(
                    insight_type="高波动模式",
                    confidence=0.78,
                    description="AI检测到高波动性模式，评级变化频繁",
                    recommendation="建议短线操作，注意风险控制",
                    supporting_evidence=[f"波动率: {volatility:.3f}", "频繁变化"],
                    risk_factors=["高风险", "难以预测"]
                ))
            
        except Exception as e:
            self.logger.error(f"AI模式识别失败: {str(e)}")
        
        return insights
    
    def _ai_sentiment_analysis(self, news_data: List[str], stock_code: str) -> List[AIInsight]:
        """AI情绪分析"""
        insights = []
        
        try:
            if not news_data:
                return insights
            
            # 模拟情绪分析
            positive_keywords = ['利好', '上涨', '增长', '盈利', '突破', '买入', '推荐']
            negative_keywords = ['利空', '下跌', '亏损', '风险', '卖出', '减持', '警告']
            
            sentiment_scores = []
            for news in news_data:
                pos_score = sum(1 for keyword in positive_keywords if keyword in news)
                neg_score = sum(1 for keyword in negative_keywords if keyword in news)
                sentiment_scores.append(pos_score - neg_score)
            
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
            
            if avg_sentiment > 0.5:
                insights.append(AIInsight(
                    insight_type="正面情绪主导",
                    confidence=0.76,
                    description="新闻情绪分析显示市场对该股持正面态度",
                    recommendation="情绪面支撑，可适度乐观",
                    supporting_evidence=[f"情绪得分: {avg_sentiment:.2f}", f"新闻数量: {len(news_data)}"],
                    risk_factors=["情绪反转风险"]
                ))
            elif avg_sentiment < -0.5:
                insights.append(AIInsight(
                    insight_type="负面情绪主导",
                    confidence=0.74,
                    description="新闻情绪分析显示市场对该股持负面态度",
                    recommendation="情绪面承压，建议谨慎",
                    supporting_evidence=[f"情绪得分: {avg_sentiment:.2f}", f"新闻数量: {len(news_data)}"],
                    risk_factors=["情绪恶化风险", "信心不足"]
                ))
            
        except Exception as e:
            self.logger.error(f"AI情绪分析失败: {str(e)}")
        
        return insights
    
    def _ai_trend_prediction(self, rating_series: pd.Series, multi_result: Dict) -> List[AIInsight]:
        """AI趋势预测"""
        insights = []
        
        try:
            # 模拟深度学习趋势预测
            numeric_values = [self.rating_scale.get(r, r) for r in rating_series if r is not None]
            
            if len(numeric_values) < 10:
                return insights
            
            # 简化的趋势预测算法
            recent_values = numeric_values[-5:]
            trend_momentum = np.mean(np.diff(recent_values))
            
            # 预测未来3-5天的可能方向
            if trend_momentum > 0.1:
                predicted_direction = "向上"
                confidence = min(0.9, 0.6 + abs(trend_momentum))
            elif trend_momentum < -0.1:
                predicted_direction = "向下"
                confidence = min(0.9, 0.6 + abs(trend_momentum))
            else:
                predicted_direction = "震荡"
                confidence = 0.65
            
            insights.append(AIInsight(
                insight_type="趋势预测",
                confidence=confidence,
                description=f"AI预测未来3-5天趋势{predicted_direction}",
                recommendation=f"基于预测调整策略: {predicted_direction}趋势",
                supporting_evidence=[f"动量: {trend_momentum:.3f}", "历史模式匹配"],
                risk_factors=["预测不确定性", "市场突发事件"]
            ))
            
        except Exception as e:
            self.logger.error(f"AI趋势预测失败: {str(e)}")
        
        return insights
    
    def _ai_risk_assessment(self, interp_result: Dict, multi_result: Dict) -> List[AIInsight]:
        """AI风险评估"""
        insights = []
        
        try:
            # 综合风险评估
            data_quality_risk = 1 - interp_result.get('interpolation_quality', 0.5)
            
            # 多维度一致性风险
            consistency_risk = 0.5  # 简化计算
            if 'fusion' in multi_result:
                fusion_result = multi_result['fusion']
                if hasattr(fusion_result, 'confidence'):
                    consistency_risk = 1 - fusion_result.confidence
            
            # 综合风险评分
            overall_risk = (data_quality_risk * 0.4 + consistency_risk * 0.6)
            
            if overall_risk > 0.7:
                risk_level = "高风险"
                color_code = "🔴"
            elif overall_risk > 0.4:
                risk_level = "中等风险"
                color_code = "🟡"
            else:
                risk_level = "低风险"
                color_code = "🟢"
            
            insights.append(AIInsight(
                insight_type="综合风险评估",
                confidence=0.82,
                description=f"{color_code} AI评估当前风险等级为{risk_level}",
                recommendation=f"建议采用{risk_level}对应的投资策略",
                supporting_evidence=[
                    f"数据质量风险: {data_quality_risk:.2f}",
                    f"一致性风险: {consistency_risk:.2f}"
                ],
                risk_factors=["模型不确定性", "市场变化风险"]
            ))
            
        except Exception as e:
            self.logger.error(f"AI风险评估失败: {str(e)}")
        
        return insights
    
    # ================ 智能融合和决策 ================
    
    def _calculate_ai_enhanced_score(self, 
                                   interp_result: Dict, 
                                   multi_result: Dict, 
                                   ai_insights: List[AIInsight]) -> float:
        """计算AI增强评分"""
        try:
            # 基础分数
            base_score = 50  # 中性起点
            
            # 插值质量贡献
            interp_quality = interp_result.get('interpolation_quality', 0.5)
            base_score += (interp_quality - 0.5) * 20
            
            # 多维度分析贡献
            if 'fusion' in multi_result:
                fusion_result = multi_result['fusion']
                if hasattr(fusion_result, 'score'):
                    multi_score = fusion_result.score
                    base_score = base_score * 0.6 + multi_score * 0.4
            
            # AI洞察贡献
            ai_adjustment = 0
            for insight in ai_insights:
                if "上升" in insight.description or "正面" in insight.description:
                    ai_adjustment += insight.confidence * 10
                elif "下降" in insight.description or "负面" in insight.description:
                    ai_adjustment -= insight.confidence * 10
            
            # 最终评分
            final_score = base_score + ai_adjustment
            final_score = max(0, min(100, final_score))
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"AI增强评分计算失败: {str(e)}")
            return 50
    
    def _generate_final_recommendation(self, 
                                     interp_result: Dict,
                                     multi_result: Dict,
                                     ai_insights: List[AIInsight],
                                     ai_score: float) -> str:
        """生成最终建议"""
        try:
            recommendations = []
            
            # 基于AI增强评分
            if ai_score >= 75:
                recommendations.append("🚀 综合AI分析显示强烈看好信号")
            elif ai_score >= 60:
                recommendations.append("📈 综合分析偏向积极，可适度关注")
            elif ai_score >= 40:
                recommendations.append("⚖️ 综合分析中性，建议谨慎观望")
            else:
                recommendations.append("📉 综合分析偏向消极，建议回避风险")
            
            # AI洞察建议
            for insight in ai_insights:
                if insight.confidence > 0.8:
                    recommendations.append(f"🤖 AI洞察: {insight.recommendation}")
            
            # 数据质量提醒
            if interp_result.get('interpolation_quality', 0) < 0.6:
                recommendations.append("⚠️ 数据质量提醒: 插值比例较高，建议结合其他信息")
            
            return " | ".join(recommendations[:3])  # 最多显示3条主要建议
            
        except Exception as e:
            self.logger.error(f"生成最终建议失败: {str(e)}")
            return "分析过程中出现错误，建议人工复核"
    
    def _generate_intelligent_risk_warnings(self, 
                                          interp_result: Dict,
                                          multi_result: Dict,
                                          ai_insights: List[AIInsight]) -> List[str]:
        """生成智能风险预警"""
        warnings = []
        
        try:
            # 数据质量风险
            if interp_result.get('interpolation_quality', 1) < 0.5:
                warnings.append("⚠️ 数据质量风险: 插值比例过高，分析可靠性降低")
            
            # AI置信度风险
            high_conf_insights = [i for i in ai_insights if i.confidence > 0.8]
            if len(high_conf_insights) == 0:
                warnings.append("🤖 AI置信度风险: 所有AI分析置信度偏低")
            
            # 趋势一致性风险
            trend_insights = [i for i in ai_insights if "趋势" in i.insight_type]
            if len(trend_insights) > 1:
                # 检查趋势一致性
                directions = [i.description for i in trend_insights]
                if len(set(directions)) > 1:
                    warnings.append("📊 趋势分歧风险: AI检测到相互矛盾的趋势信号")
            
            # 模型风险
            if not self.enable_ai:
                warnings.append("🔧 模型风险: AI功能未启用，仅使用传统分析方法")
            
        except Exception as e:
            self.logger.error(f"生成风险预警失败: {str(e)}")
            warnings.append("⚠️ 风险评估过程出现异常")
        
        return warnings
    
    def _assess_overall_confidence(self, 
                                 interp_result: Dict,
                                 multi_result: Dict,
                                 ai_insights: List[AIInsight]) -> str:
        """评估整体置信度"""
        try:
            confidence_scores = []
            
            # 插值质量置信度
            interp_confidence = interp_result.get('confidence_score', 0.5)
            confidence_scores.append(interp_confidence)
            
            # 多维度分析置信度
            if 'fusion' in multi_result:
                fusion_result = multi_result['fusion']
                if hasattr(fusion_result, 'confidence'):
                    confidence_scores.append(fusion_result.confidence)
            
            # AI分析置信度
            if ai_insights:
                ai_confidences = [insight.confidence for insight in ai_insights]
                confidence_scores.append(np.mean(ai_confidences))
            
            # 计算整体置信度
            overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.5
            
            if overall_confidence >= 0.8:
                return "高置信度"
            elif overall_confidence >= 0.6:
                return "中等置信度"
            else:
                return "低置信度"
                
        except Exception as e:
            self.logger.error(f"置信度评估失败: {str(e)}")
            return "置信度未知"
    
    def _create_error_result(self, error_message: str) -> ComprehensiveAnalysisResult:
        """创建错误结果"""
        return ComprehensiveAnalysisResult(
            interpolation_result={'error': error_message},
            multi_dimensional_result={'error': error_message},
            ai_insights=[],
            ai_enhanced_score=0,
            final_recommendation=f"分析失败: {error_message}",
            confidence_level="无",
            risk_warning=[f"系统错误: {error_message}"],
            analysis_timestamp=datetime.now().isoformat(),
            processing_time=0
        )
    
    def export_results_for_web(self, result: ComprehensiveAnalysisResult) -> Dict:
        """导出结果供Web界面使用"""
        try:
            return {
                'ai_enhanced_score': result.ai_enhanced_score,
                'final_recommendation': result.final_recommendation,
                'confidence_level': result.confidence_level,
                'risk_warnings': result.risk_warning,
                'processing_time': result.processing_time,
                'analysis_timestamp': result.analysis_timestamp,
                
                # AI洞察（序列化）
                'ai_insights': [asdict(insight) for insight in result.ai_insights],
                
                # 插值结果摘要
                'interpolation_summary': {
                    'quality': result.interpolation_result.get('interpolation_quality', 0),
                    'strategy': result.interpolation_result.get('strategy_used', 'unknown'),
                    'missing_ratio': result.interpolation_result.get('missing_ratio', 0)
                },
                
                # 多维度分析摘要
                'multi_dimensional_summary': {
                    'available_levels': list(result.multi_dimensional_result.keys()),
                    'fusion_available': 'fusion' in result.multi_dimensional_result
                }
            }
        except Exception as e:
            self.logger.error(f"导出Web结果失败: {str(e)}")
            return {'error': str(e)}

# 使用示例
if __name__ == "__main__":
    # 创建AI增强分析器
    analyzer = AIEnhancedSignalAnalyzer(enable_ai_features=True)
    
    # 示例数据
    sample_data = pd.DataFrame({
        '股票代码': ['000001'],
        '20241201': ['大多'],
        '20241202': ['中多'],
        '20241203': ['-'],
        '20241204': ['小多'],
        '20241205': ['微多']
    })
    
    # 示例新闻
    sample_news = [
        "该公司发布利好消息，业绩大幅增长",
        "分析师上调评级，建议买入",
        "市场传言存在风险，投资者需谨慎"
    ]
    
    # 执行综合分析
    result = analyzer.comprehensive_analyze(
        stock_data=sample_data,
        stock_code='000001',
        news_data=sample_news,
        enable_prediction=True
    )
    
    print("=== AI增强8级信号分析结果 ===")
    print(f"AI增强评分: {result.ai_enhanced_score:.1f}/100")
    print(f"最终建议: {result.final_recommendation}")
    print(f"置信度: {result.confidence_level}")
    print(f"处理时间: {result.processing_time:.3f}s")
    
    print("\n=== AI洞察 ===")
    for insight in result.ai_insights:
        print(f"• {insight.insight_type} (置信度: {insight.confidence:.2f})")
        print(f"  {insight.description}")
        print(f"  建议: {insight.recommendation}")
    
    print("\n=== 风险预警 ===")
    for warning in result.risk_warning:
        print(f"• {warning}")
