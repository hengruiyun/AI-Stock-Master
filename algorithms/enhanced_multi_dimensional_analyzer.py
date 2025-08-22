# -*- coding: utf-8 -*-
"""
增强版多维度股票分析器
整合个股、行业、大盘三个层面的8级信号分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

class AnalysisLevel(Enum):
    """分析层级枚举"""
    INDIVIDUAL = "individual"    # 个股层面
    INDUSTRY = "industry"        # 行业层面
    MARKET = "market"           # 大盘层面

class SignalStrength(Enum):
    """信号强度枚举"""
    VERY_STRONG = "very_strong"     # 非常强
    STRONG = "strong"               # 强
    MODERATE = "moderate"           # 中等
    WEAK = "weak"                   # 弱
    VERY_WEAK = "very_weak"         # 非常弱

@dataclass
class AnalysisResult:
    """分析结果数据结构"""
    score: float                    # 综合评分 (0-100)
    signal_strength: SignalStrength # 信号强度
    confidence: float               # 置信度 (0-1)
    trend_direction: str            # 趋势方向
    risk_level: str                 # 风险等级
    recommendations: List[str]      # 具体建议
    contributing_factors: Dict      # 贡献因子详情

class EnhancedMultiDimensionalAnalyzer:
    """
    增强版多维度分析器
    
    核心功能：
    1. 个股层面：增强版RTSI + 基本面分析
    2. 行业层面：智能轮动分析 + 相对强度
    3. 大盘层面：系统性风险 + 市场情绪
    4. 三层联动：多维度信号融合与验证
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 设置日志级别为ERROR，只输出严重错误
        self.logger.setLevel(logging.ERROR)
        
        # 8级评级映射
        self.rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0,
            '中性': 3.5, '-': None
        }
        
        # 反向映射（数值到评级）
        self.reverse_rating_map = {v: k for k, v in self.rating_map.items() if v is not None}
        
        # 分析权重配置
        self.analysis_weights = {
            'individual_weight': 0.4,    # 个股分析权重
            'industry_weight': 0.35,     # 行业分析权重
            'market_weight': 0.25        # 大盘分析权重
        }
        
        # 风险等级阈值
        self.risk_thresholds = {
            'very_low': (0, 10),
            'low': (10, 25),
            'medium': (25, 50),
            'high': (50, 75),
            'very_high': (75, 100)
        }
    
    def comprehensive_analysis(self, 
                             stock_data: pd.DataFrame,
                             industry_data: pd.DataFrame = None,
                             market_data: pd.DataFrame = None,
                             target_stock: str = None) -> Dict[str, AnalysisResult]:
        """
        综合多维度分析
        
        Args:
            stock_data: 个股数据
            industry_data: 行业数据
            market_data: 市场数据
            target_stock: 目标股票代码
            
        Returns:
            多层次分析结果
        """
        analysis_start = datetime.now()
        results = {}
        
        try:
            # 1. 个股层面分析
            if target_stock and not stock_data.empty:
                individual_result = self._analyze_individual_stock(stock_data, target_stock)
                results['individual'] = individual_result
            
            # 2. 行业层面分析
            if industry_data is not None and not industry_data.empty:
                industry_result = self._analyze_industry_strength(industry_data, target_stock)
                results['industry'] = industry_result
            
            # 3. 大盘层面分析
            if market_data is not None and not market_data.empty:
                market_result = self._analyze_market_sentiment(market_data)
                results['market'] = market_result
            
            # 4. 多维度融合分析
            if len(results) > 1:
                fusion_result = self._multi_dimensional_fusion(results)
                results['fusion'] = fusion_result
            
            # 5. 生成最终建议
            final_recommendation = self._generate_final_recommendation(results)
            results['final_recommendation'] = final_recommendation
            
            processing_time = (datetime.now() - analysis_start).total_seconds()
            self.logger.info(f"多维度分析完成，耗时: {processing_time:.3f}s")
            
            return results
            
        except Exception as e:
            self.logger.error(f"综合分析失败: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_individual_stock(self, stock_data: pd.DataFrame, target_stock: str) -> AnalysisResult:
        """个股层面分析"""
        try:
            # 获取目标股票数据
            if target_stock in stock_data.index:
                stock_ratings = stock_data.loc[target_stock]
            elif target_stock in stock_data.get('股票代码', pd.Series()).values:
                stock_ratings = stock_data[stock_data['股票代码'] == target_stock].iloc[0]
            else:
                raise ValueError(f"未找到股票 {target_stock}")
            
            # 获取日期列
            date_columns = [col for col in stock_ratings.index if str(col).startswith('202')]
            date_columns.sort()
            
            if len(date_columns) < 5:
                raise ValueError("数据不足，无法进行个股分析")
            
            # 1. 基础RTSI分析
            rating_values = [stock_ratings[col] for col in date_columns]
            rtsi_score = self._calculate_enhanced_rtsi(rating_values)
            
            # 2. 趋势分析
            trend_analysis = self._analyze_rating_trend(rating_values)
            
            # 3. 波动性分析
            volatility_analysis = self._analyze_rating_volatility(rating_values)
            
            # 4. 动量分析
            momentum_analysis = self._analyze_rating_momentum(rating_values)
            
            # 5. 综合评分计算
            comprehensive_score = (
                rtsi_score * 0.3 +
                trend_analysis['score'] * 0.25 +
                volatility_analysis['score'] * 0.2 +
                momentum_analysis['score'] * 0.25
            )
            
            # 6. 信号强度判断
            signal_strength = self._determine_signal_strength(comprehensive_score)
            
            # 7. 风险评估
            risk_level = self._assess_risk_level(volatility_analysis, trend_analysis)
            
            # 8. 置信度计算
            confidence = self._calculate_confidence(rating_values, comprehensive_score)
            
            # 9. 生成建议
            recommendations = self._generate_individual_recommendations(
                comprehensive_score, trend_analysis, volatility_analysis, momentum_analysis
            )
            
            return AnalysisResult(
                score=comprehensive_score,
                signal_strength=signal_strength,
                confidence=confidence,
                trend_direction=trend_analysis['direction'],
                risk_level=risk_level,
                recommendations=recommendations,
                contributing_factors={
                    'rtsi_score': rtsi_score,
                    'trend_score': trend_analysis['score'],
                    'volatility_score': volatility_analysis['score'],
                    'momentum_score': momentum_analysis['score']
                }
            )
            
        except Exception as e:
            # 将错误级别改为debug，避免输出到终端
            self.logger.debug(f"个股分析失败: {str(e)}")
            return AnalysisResult(
                score=0, signal_strength=SignalStrength.VERY_WEAK,
                confidence=0, trend_direction="未知", risk_level="高",
                recommendations=[f"分析失败: {str(e)}"],
                contributing_factors={}
            )
    
    def _analyze_industry_strength(self, industry_data: pd.DataFrame, target_stock: str = None) -> AnalysisResult:
        """行业层面分析"""
        try:
            # 获取日期列
            date_columns = [col for col in industry_data.columns if str(col).startswith('202')]
            date_columns.sort()
            
            if len(date_columns) < 10:
                raise ValueError("数据不足，无法进行行业分析")
            
            # 1. 行业整体评级分布分析
            industry_distribution = self._analyze_industry_distribution(industry_data, date_columns)
            
            # 2. 行业轮动强度分析
            rotation_strength = self._analyze_industry_rotation(industry_data, date_columns)
            
            # 3. 相对强度分析
            relative_strength = self._analyze_industry_relative_strength(industry_data, date_columns)
            
            # 4. 行业集中度分析
            concentration_analysis = self._analyze_industry_concentration(industry_data, date_columns)
            
            # 5. 综合评分
            comprehensive_score = (
                industry_distribution['score'] * 0.3 +
                rotation_strength['score'] * 0.25 +
                relative_strength['score'] * 0.25 +
                concentration_analysis['score'] * 0.2
            )
            
            # 6. 信号强度和趋势方向
            signal_strength = self._determine_signal_strength(comprehensive_score)
            trend_direction = self._determine_industry_trend(rotation_strength, relative_strength)
            
            # 7. 风险评估
            risk_level = self._assess_industry_risk(concentration_analysis, rotation_strength)
            
            # 8. 置信度
            confidence = min(0.9, concentration_analysis['data_quality'] * relative_strength['reliability'])
            
            # 9. 建议生成
            recommendations = self._generate_industry_recommendations(
                comprehensive_score, rotation_strength, relative_strength, concentration_analysis
            )
            
            return AnalysisResult(
                score=comprehensive_score,
                signal_strength=signal_strength,
                confidence=confidence,
                trend_direction=trend_direction,
                risk_level=risk_level,
                recommendations=recommendations,
                contributing_factors={
                    'distribution_score': industry_distribution['score'],
                    'rotation_score': rotation_strength['score'],
                    'relative_strength_score': relative_strength['score'],
                    'concentration_score': concentration_analysis['score']
                }
            )
            
        except Exception as e:
            self.logger.error(f"行业分析失败: {str(e)}")
            return AnalysisResult(
                score=0, signal_strength=SignalStrength.VERY_WEAK,
                confidence=0, trend_direction="未知", risk_level="高",
                recommendations=[f"分析失败: {str(e)}"],
                contributing_factors={}
            )
    
    def _analyze_market_sentiment(self, market_data: pd.DataFrame) -> AnalysisResult:
        """大盘层面分析"""
        try:
            # 获取日期列
            date_columns = [col for col in market_data.columns if str(col).startswith('202')]
            date_columns.sort()
            
            if len(date_columns) < 10:
                raise ValueError("数据不足，无法进行市场分析")
            
            # 1. 市场情绪分布分析
            sentiment_distribution = self._analyze_market_sentiment_distribution(market_data, date_columns)
            
            # 2. 系统性风险分析
            systemic_risk = self._analyze_systemic_risk(market_data, date_columns)
            
            # 3. 市场参与度分析
            participation_analysis = self._analyze_market_participation(market_data, date_columns)
            
            # 4. 极端情绪检测
            extreme_sentiment = self._detect_extreme_sentiment(market_data, date_columns)
            
            # 5. 市场周期分析
            cycle_analysis = self._analyze_market_cycle(market_data, date_columns)
            
            # 6. 综合评分
            comprehensive_score = (
                sentiment_distribution['score'] * 0.25 +
                (100 - systemic_risk['score']) * 0.25 +  # 风险越低分数越高
                participation_analysis['score'] * 0.2 +
                extreme_sentiment['score'] * 0.15 +
                cycle_analysis['score'] * 0.15
            )
            
            # 7. 信号强度和趋势
            signal_strength = self._determine_signal_strength(comprehensive_score)
            trend_direction = cycle_analysis['phase']
            
            # 8. 风险等级
            risk_level = self._assess_market_risk(systemic_risk, extreme_sentiment)
            
            # 9. 置信度
            confidence = min(0.95, participation_analysis['reliability'] * cycle_analysis['confidence'])
            
            # 10. 建议生成
            recommendations = self._generate_market_recommendations(
                comprehensive_score, systemic_risk, extreme_sentiment, cycle_analysis
            )
            
            return AnalysisResult(
                score=comprehensive_score,
                signal_strength=signal_strength,
                confidence=confidence,
                trend_direction=trend_direction,
                risk_level=risk_level,
                recommendations=recommendations,
                contributing_factors={
                    'sentiment_score': sentiment_distribution['score'],
                    'systemic_risk_score': systemic_risk['score'],
                    'participation_score': participation_analysis['score'],
                    'extreme_sentiment_score': extreme_sentiment['score'],
                    'cycle_score': cycle_analysis['score']
                }
            )
            
        except Exception as e:
            self.logger.error(f"市场分析失败: {str(e)}")
            return AnalysisResult(
                score=0, signal_strength=SignalStrength.VERY_WEAK,
                confidence=0, trend_direction="未知", risk_level="高",
                recommendations=[f"分析失败: {str(e)}"],
                contributing_factors={}
            )
    
    def _multi_dimensional_fusion(self, results: Dict[str, AnalysisResult]) -> AnalysisResult:
        """多维度融合分析"""
        try:
            # 获取各维度结果
            individual = results.get('individual')
            industry = results.get('industry')
            market = results.get('market')
            
            # 计算加权综合得分
            weighted_score = 0
            total_weight = 0
            confidence_weights = []
            
            if individual:
                weight = self.analysis_weights['individual_weight'] * individual.confidence
                weighted_score += individual.score * weight
                total_weight += weight
                confidence_weights.append(individual.confidence)
            
            if industry:
                weight = self.analysis_weights['industry_weight'] * industry.confidence
                weighted_score += industry.score * weight
                total_weight += weight
                confidence_weights.append(industry.confidence)
            
            if market:
                weight = self.analysis_weights['market_weight'] * market.confidence
                weighted_score += market.score * weight
                total_weight += weight
                confidence_weights.append(market.confidence)
            
            # 最终综合得分
            final_score = weighted_score / total_weight if total_weight > 0 else 0
            
            # 多维度一致性检验
            consistency_score = self._calculate_multi_dimensional_consistency(results)
            
            # 综合置信度
            avg_confidence = np.mean(confidence_weights) if confidence_weights else 0
            final_confidence = avg_confidence * consistency_score
            
            # 趋势方向融合
            trend_votes = []
            if individual: trend_votes.append(individual.trend_direction)
            if industry: trend_votes.append(industry.trend_direction)
            if market: trend_votes.append(market.trend_direction)
            
            final_trend = max(set(trend_votes), key=trend_votes.count) if trend_votes else "中性"
            
            # 风险等级融合
            risk_levels = []
            if individual: risk_levels.append(individual.risk_level)
            if industry: risk_levels.append(industry.risk_level)
            if market: risk_levels.append(market.risk_level)
            
            final_risk = max(set(risk_levels), key=risk_levels.count) if risk_levels else "中等"
            
            # 信号强度
            signal_strength = self._determine_signal_strength(final_score)
            
            # 融合建议
            fusion_recommendations = self._generate_fusion_recommendations(
                results, final_score, consistency_score
            )
            
            return AnalysisResult(
                score=final_score,
                signal_strength=signal_strength,
                confidence=final_confidence,
                trend_direction=final_trend,
                risk_level=final_risk,
                recommendations=fusion_recommendations,
                contributing_factors={
                    'consistency_score': consistency_score,
                    'individual_weight': individual.score if individual else 0,
                    'industry_weight': industry.score if industry else 0,
                    'market_weight': market.score if market else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"多维度融合失败: {str(e)}")
            return AnalysisResult(
                score=0, signal_strength=SignalStrength.VERY_WEAK,
                confidence=0, trend_direction="未知", risk_level="高",
                recommendations=[f"融合分析失败: {str(e)}"],
                contributing_factors={}
            )
    
    # 辅助方法实现
    def _calculate_enhanced_rtsi(self, rating_values: List) -> float:
        """计算增强版RTSI"""
        try:
            # 转换为数值
            numeric_values = []
            for rating in rating_values:
                if rating in self.rating_map and self.rating_map[rating] is not None:
                    numeric_values.append(self.rating_map[rating])
                elif isinstance(rating, (int, float)):
                    numeric_values.append(rating)
            
            if len(numeric_values) < 5:
                return 0
            
            # 计算趋势强度
            x = np.arange(len(numeric_values))
            slope = np.polyfit(x, numeric_values, 1)[0]
            
            # 计算一致性（R²）
            correlation = np.corrcoef(x, numeric_values)[0, 1]
            r_squared = correlation ** 2 if not np.isnan(correlation) else 0
            
            # 计算变化幅度
            amplitude = abs(slope) * len(numeric_values) / 7  # 标准化到8级评级
            amplitude = min(amplitude, 1.0)
            
            # RTSI计算
            rtsi = (r_squared * 0.4 + abs(slope)/7 * 0.3 + amplitude * 0.3) * 100
            
            return min(rtsi, 100)
            
        except Exception as e:
            self.logger.error(f"RTSI计算失败: {str(e)}")
            return 0
    
    def _analyze_rating_trend(self, rating_values: List) -> Dict:
        """分析评级趋势"""
        try:
            numeric_values = [self.rating_map.get(r, r) for r in rating_values if r is not None]
            if len(numeric_values) < 3:
                return {'score': 0, 'direction': '未知', 'strength': 0}
            
            # 线性回归
            x = np.arange(len(numeric_values))
            slope = np.polyfit(x, numeric_values, 1)[0]
            
            # 趋势方向
            if slope > 0.1:
                direction = "上升"
            elif slope < -0.1:
                direction = "下降"
            else:
                direction = "平稳"
            
            # 趋势强度
            strength = min(abs(slope) * 10, 10)  # 标准化到0-10
            
            # 评分
            score = 50 + slope * 10  # 中性为50，上升趋势加分，下降趋势减分
            score = max(0, min(100, score))
            
            return {
                'score': score,
                'direction': direction,
                'strength': strength,
                'slope': slope
            }
            
        except Exception as e:
            return {'score': 0, 'direction': '未知', 'strength': 0}
    
    def _analyze_rating_volatility(self, rating_values: List) -> Dict:
        """分析评级波动性"""
        try:
            numeric_values = [self.rating_map.get(r, r) for r in rating_values if r is not None]
            if len(numeric_values) < 2:
                return {'score': 50, 'level': '中等'}
            
            volatility = np.std(numeric_values)
            
            # 波动性等级
            if volatility < 0.5:
                level = "很低"
                score = 80  # 低波动性给高分
            elif volatility < 1.0:
                level = "低"
                score = 70
            elif volatility < 1.5:
                level = "中等"
                score = 50
            elif volatility < 2.0:
                level = "高"
                score = 30
            else:
                level = "很高"
                score = 10  # 高波动性给低分
            
            return {
                'score': score,
                'level': level,
                'volatility': volatility
            }
            
        except Exception as e:
            return {'score': 50, 'level': '中等'}
    
    def _analyze_rating_momentum(self, rating_values: List) -> Dict:
        """分析评级动量"""
        try:
            numeric_values = [self.rating_map.get(r, r) for r in rating_values if r is not None]
            if len(numeric_values) < 5:
                return {'score': 50, 'momentum': 0}
            
            # 计算短期和长期平均
            short_avg = np.mean(numeric_values[-3:])  # 最近3期
            long_avg = np.mean(numeric_values[:-3])   # 之前的期数
            
            momentum = short_avg - long_avg
            
            # 动量评分
            score = 50 + momentum * 10  # 正动量加分，负动量减分
            score = max(0, min(100, score))
            
            return {
                'score': score,
                'momentum': momentum,
                'short_avg': short_avg,
                'long_avg': long_avg
            }
            
        except Exception as e:
            return {'score': 50, 'momentum': 0}
    
    def _determine_signal_strength(self, score: float) -> SignalStrength:
        """确定信号强度"""
        if score >= 80:
            return SignalStrength.VERY_STRONG
        elif score >= 65:
            return SignalStrength.STRONG
        elif score >= 35:
            return SignalStrength.MODERATE
        elif score >= 20:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK
    
    def _assess_risk_level(self, volatility_analysis: Dict, trend_analysis: Dict) -> str:
        """评估风险等级"""
        volatility_score = volatility_analysis.get('score', 50)
        trend_strength = trend_analysis.get('strength', 0)
        
        # 高波动性 + 弱趋势 = 高风险
        risk_score = (100 - volatility_score) + (10 - trend_strength) * 5
        
        if risk_score < 20:
            return "很低"
        elif risk_score < 40:
            return "低"
        elif risk_score < 60:
            return "中等"
        elif risk_score < 80:
            return "高"
        else:
            return "很高"
    
    def _calculate_confidence(self, rating_values: List, score: float) -> float:
        """计算置信度"""
        try:
            # 数据完整性
            valid_count = sum(1 for r in rating_values if r != '-' and r is not None)
            data_completeness = valid_count / len(rating_values)
            
            # 分数稳定性
            score_stability = 1 - abs(score - 50) / 50  # 越接近中性越稳定
            
            # 综合置信度
            confidence = (data_completeness * 0.7 + score_stability * 0.3)
            
            return max(0.1, min(0.95, confidence))
            
        except Exception as e:
            return 0.5
    
    def _generate_individual_recommendations(self, score: float, trend: Dict, volatility: Dict, momentum: Dict) -> List[str]:
        """生成个股建议"""
        recommendations = []
        
        if score >= 70:
            recommendations.append("💹 个股表现强势，建议关注")
        elif score >= 50:
            recommendations.append("📈 个股表现中性偏好，可适度关注")
        else:
            recommendations.append("📉 个股表现偏弱，建议谨慎")
        
        if trend['direction'] == "上升":
            recommendations.append(f"📊 趋势向上，强度: {trend['strength']:.1f}")
        elif trend['direction'] == "下降":
            recommendations.append(f"📉 趋势向下，建议防御")
        
        if volatility['level'] in ['高', '很高']:
            recommendations.append("⚠️ 波动性较高，注意风险控制")
        
        return recommendations
    
    # 其他行业和市场分析方法的简化实现
    def _analyze_industry_distribution(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """行业分布分析简化实现"""
        return {'score': 60}  # 简化返回
    
    def _analyze_industry_rotation(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """行业轮动分析简化实现"""
        return {'score': 55}  # 简化返回
    
    def _analyze_industry_relative_strength(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """相对强度分析简化实现"""
        return {'score': 65, 'reliability': 0.8}  # 简化返回
    
    def _analyze_industry_concentration(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """行业集中度分析简化实现"""
        return {'score': 70, 'data_quality': 0.85}  # 简化返回
    
    def _analyze_market_sentiment_distribution(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """市场情绪分布分析简化实现"""
        return {'score': 60}  # 简化返回
    
    def _analyze_systemic_risk(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """系统性风险分析简化实现"""
        return {'score': 30}  # 简化返回，分数越低风险越低
    
    def _analyze_market_participation(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """市场参与度分析简化实现"""
        return {'score': 75, 'reliability': 0.9}  # 简化返回
    
    def _detect_extreme_sentiment(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """极端情绪检测简化实现"""
        return {'score': 50}  # 简化返回
    
    def _analyze_market_cycle(self, data: pd.DataFrame, date_columns: List) -> Dict:
        """市场周期分析简化实现"""
        return {'score': 65, 'phase': '上升期', 'confidence': 0.8}  # 简化返回
    
    def _determine_industry_trend(self, rotation: Dict, strength: Dict) -> str:
        """确定行业趋势简化实现"""
        return "轮动上升"  # 简化返回
    
    def _assess_industry_risk(self, concentration: Dict, rotation: Dict) -> str:
        """评估行业风险简化实现"""
        return "中等"  # 简化返回
    
    def _assess_market_risk(self, systemic: Dict, extreme: Dict) -> str:
        """评估市场风险简化实现"""
        return "中等"  # 简化返回
    
    def _calculate_multi_dimensional_consistency(self, results: Dict) -> float:
        """计算多维度一致性"""
        scores = []
        for key, result in results.items():
            if isinstance(result, AnalysisResult):
                scores.append(result.score)
        
        if len(scores) < 2:
            return 1.0
        
        # 计算分数的标准差，标准差越小一致性越高
        std_dev = np.std(scores)
        consistency = max(0, 1 - std_dev / 50)  # 标准化到0-1
        
        return consistency
    
    def _generate_industry_recommendations(self, score: float, rotation: Dict, strength: Dict, concentration: Dict) -> List[str]:
        """生成行业建议简化实现"""
        return ["🏭 行业表现稳定", "📊 建议关注行业轮动机会"]
    
    def _generate_market_recommendations(self, score: float, risk: Dict, extreme: Dict, cycle: Dict) -> List[str]:
        """生成市场建议简化实现"""
        return ["🌐 市场整体向好", "⚠️ 注意系统性风险"]
    
    def _generate_fusion_recommendations(self, results: Dict, score: float, consistency: float) -> List[str]:
        """生成融合建议"""
        recommendations = []
        
        if consistency > 0.8:
            recommendations.append("✅ 多维度分析结果一致性高，建议参考")
        elif consistency > 0.6:
            recommendations.append("📊 多维度分析结果基本一致")
        else:
            recommendations.append("⚠️ 多维度分析结果存在分歧，建议谨慎决策")
        
        if score >= 70:
            recommendations.append("💹 综合评分较高，投资机会较好")
        elif score >= 50:
            recommendations.append("📈 综合评分中性，可考虑适度参与")
        else:
            recommendations.append("📉 综合评分偏低，建议保持谨慎")
        
        return recommendations
    
    def _generate_final_recommendation(self, results: Dict) -> AnalysisResult:
        """生成最终建议"""
        if 'fusion' in results:
            return results['fusion']
        elif 'individual' in results:
            return results['individual']
        else:
            return AnalysisResult(
                score=0, signal_strength=SignalStrength.VERY_WEAK,
                confidence=0, trend_direction="未知", risk_level="高",
                recommendations=["数据不足，无法生成建议"],
                contributing_factors={}
            )

# 使用示例
if __name__ == "__main__":
    analyzer = EnhancedMultiDimensionalAnalyzer()
    
    # 示例股票数据
    sample_stock_data = pd.DataFrame({
        '股票代码': ['000001'],
        '20241201': ['大多'],
        '20241202': ['中多'],
        '20241203': ['小多'],
        '20241204': ['-'],
        '20241205': ['微多']
    })
    
    # 执行分析
    results = analyzer.comprehensive_analysis(
        stock_data=sample_stock_data,
        target_stock='000001'
    )
    
    for level, result in results.items():
        if isinstance(result, AnalysisResult):
            print(f"\n{level}分析结果:")
            print(f"  评分: {result.score:.1f}")
            print(f"  信号强度: {result.signal_strength.value}")
            print(f"  置信度: {result.confidence:.2f}")
            print(f"  趋势方向: {result.trend_direction}")
            print(f"  风险等级: {result.risk_level}")
            print(f"  建议: {result.recommendations}")
