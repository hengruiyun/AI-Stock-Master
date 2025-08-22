# -*- coding: utf-8 -*-
"""
自适应插值算法
根据缺失时长、市场环境、数据质量等因素智能选择插值策略
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
import logging
from datetime import datetime, timedelta
from enum import Enum

class InterpolationStrategy(Enum):
    """插值策略枚举"""
    FORWARD_FILL = "forward_fill"           # 前向填充
    NEUTRAL_FILL = "neutral_fill"           # 中性插值
    WEIGHTED_HYBRID = "weighted_hybrid"     # 加权混合
    ML_PREDICTION = "ml_prediction"         # 机器学习预测
    INDUSTRY_CORRELATION = "industry_correlation"  # 行业相关性插值

class AdaptiveInterpolationEngine:
    """
    自适应插值引擎
    
    核心功能：
    1. 智能评估缺失数据的特征
    2. 动态选择最优插值策略
    3. 提供插值质量评估
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 设置日志级别为WARNING，减少INFO输出
        self.logger.setLevel(logging.WARNING)
        
        # 8级评级系统配置
        self.rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0,
            '中性': 3.5, '-': None
        }
        
        # 中性值（8级系统的中间值）
        self.neutral_value = 3.5
        
        # 插值策略权重配置
        self.strategy_weights = {
            'data_quality': 0.3,      # 数据质量权重
            'temporal_distance': 0.25, # 时间距离权重  
            'market_volatility': 0.2,  # 市场波动性权重
            'trend_strength': 0.15,    # 趋势强度权重
            'industry_correlation': 0.1 # 行业相关性权重
        }
    
    def interpolate_rating_series(self, 
                                 ratings_series: pd.Series,
                                 stock_info: Dict = None,
                                 market_context: Dict = None) -> Dict[str, Union[pd.Series, float, str]]:
        """
        自适应插值主函数
        
        Args:
            ratings_series: 原始评级序列
            stock_info: 股票信息（代码、行业等）
            market_context: 市场环境信息
            
        Returns:
            插值结果字典：{
                'interpolated_series': 插值后序列,
                'interpolation_quality': 插值质量评分,
                'strategy_used': 使用的策略,
                'confidence_score': 置信度评分
            }
        """
        start_time = datetime.now()
        
        try:
            # 1. 数据预处理和质量评估
            missing_analysis = self._analyze_missing_pattern(ratings_series)
            
            # 2. 选择最优插值策略
            optimal_strategy = self._select_optimal_strategy(
                missing_analysis, stock_info, market_context
            )
            
            # 3. 执行插值
            interpolated_series = self._execute_interpolation(
                ratings_series, optimal_strategy, missing_analysis
            )
            
            # 4. 质量评估
            quality_assessment = self._assess_interpolation_quality(
                ratings_series, interpolated_series, missing_analysis
            )
            
            # 5. 生成结果
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'interpolated_series': interpolated_series,
                'interpolation_quality': quality_assessment['quality_score'],
                'strategy_used': optimal_strategy.value,
                'confidence_score': quality_assessment['confidence'],
                'missing_ratio': missing_analysis['missing_ratio'],
                'max_gap_days': missing_analysis['max_gap_days'],
                'processing_time': f"{processing_time:.3f}s",
                'recommendations': quality_assessment['recommendations']
            }
            
        except Exception as e:
            self.logger.error(f"插值处理失败: {str(e)}")
            return {
                'interpolated_series': ratings_series,
                'interpolation_quality': 0.0,
                'strategy_used': 'error',
                'confidence_score': 0.0,
                'error_message': str(e)
            }
    
    def _analyze_missing_pattern(self, ratings_series: pd.Series) -> Dict:
        """分析缺失数据模式"""
        missing_mask = ratings_series.isin(['-', None, np.nan])
        total_points = len(ratings_series)
        missing_count = missing_mask.sum()
        
        # 计算连续缺失的最大长度
        max_gap = 0
        current_gap = 0
        gap_positions = []
        
        for i, is_missing in enumerate(missing_mask):
            if is_missing:
                current_gap += 1
            else:
                if current_gap > 0:
                    gap_positions.append((i - current_gap, i - 1, current_gap))
                    max_gap = max(max_gap, current_gap)
                    current_gap = 0
        
        # 处理序列末尾的缺失
        if current_gap > 0:
            gap_positions.append((total_points - current_gap, total_points - 1, current_gap))
            max_gap = max(max_gap, current_gap)
        
        # 分析缺失模式类型
        if missing_count == 0:
            pattern_type = "complete"
        elif missing_count == total_points:
            pattern_type = "empty"
        elif missing_count / total_points > 0.7:
            pattern_type = "sparse"
        elif max_gap > 7:
            pattern_type = "long_gaps"
        elif len(gap_positions) > total_points / 3:
            pattern_type = "scattered"
        else:
            pattern_type = "normal"
        
        return {
            'missing_ratio': missing_count / total_points,
            'missing_count': missing_count,
            'total_points': total_points,
            'max_gap_days': max_gap,
            'gap_positions': gap_positions,
            'pattern_type': pattern_type,
            'data_density': 1 - (missing_count / total_points)
        }
    
    def _select_optimal_strategy(self, 
                               missing_analysis: Dict,
                               stock_info: Dict = None,
                               market_context: Dict = None) -> InterpolationStrategy:
        """选择最优插值策略"""
        
        # 基于缺失数据特征的策略选择
        missing_ratio = missing_analysis['missing_ratio']
        max_gap = missing_analysis['max_gap_days']
        pattern_type = missing_analysis['pattern_type']
        
        # 策略评分
        strategy_scores = {}
        
        # 1. 前向填充评分
        if missing_ratio < 0.3 and max_gap <= 5:
            strategy_scores[InterpolationStrategy.FORWARD_FILL] = 0.9
        elif missing_ratio < 0.5 and max_gap <= 3:
            strategy_scores[InterpolationStrategy.FORWARD_FILL] = 0.7
        else:
            strategy_scores[InterpolationStrategy.FORWARD_FILL] = 0.3
        
        # 2. 中性插值评分
        if missing_ratio > 0.5 or max_gap > 7:
            strategy_scores[InterpolationStrategy.NEUTRAL_FILL] = 0.9
        elif pattern_type in ['sparse', 'long_gaps']:
            strategy_scores[InterpolationStrategy.NEUTRAL_FILL] = 0.8
        else:
            strategy_scores[InterpolationStrategy.NEUTRAL_FILL] = 0.6
        
        # 3. 加权混合评分
        if 0.2 < missing_ratio < 0.6 and 3 < max_gap <= 7:
            strategy_scores[InterpolationStrategy.WEIGHTED_HYBRID] = 0.9
        elif pattern_type == 'normal':
            strategy_scores[InterpolationStrategy.WEIGHTED_HYBRID] = 0.7
        else:
            strategy_scores[InterpolationStrategy.WEIGHTED_HYBRID] = 0.5
        
        # 4. 考虑市场环境调整
        if market_context:
            volatility = market_context.get('volatility', 0.5)
            if volatility > 0.7:  # 高波动市场
                strategy_scores[InterpolationStrategy.NEUTRAL_FILL] *= 1.2
                strategy_scores[InterpolationStrategy.FORWARD_FILL] *= 0.8
        
        # 选择得分最高的策略
        optimal_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        
        self.logger.info(f"选择插值策略: {optimal_strategy.value}, 评分: {strategy_scores}")
        
        return optimal_strategy
    
    def _execute_interpolation(self, 
                             ratings_series: pd.Series,
                             strategy: InterpolationStrategy,
                             missing_analysis: Dict) -> pd.Series:
        """执行具体的插值操作"""
        
        if strategy == InterpolationStrategy.FORWARD_FILL:
            return self._forward_fill_interpolation(ratings_series)
        
        elif strategy == InterpolationStrategy.NEUTRAL_FILL:
            return self._neutral_fill_interpolation(ratings_series)
        
        elif strategy == InterpolationStrategy.WEIGHTED_HYBRID:
            return self._weighted_hybrid_interpolation(ratings_series, missing_analysis)
        
        else:
            # 默认使用前向填充
            self.logger.warning(f"未实现的策略 {strategy}, 使用前向填充")
            return self._forward_fill_interpolation(ratings_series)
    
    def _forward_fill_interpolation(self, ratings_series: pd.Series) -> pd.Series:
        """前向填充插值"""
        interpolated = ratings_series.copy()
        last_valid = None
        
        for i, rating in enumerate(interpolated):
            if rating not in ['-', None, np.nan]:
                # 转换为数值
                if rating in self.rating_map:
                    last_valid = self.rating_map[rating]
                    interpolated.iloc[i] = last_valid
                else:
                    try:
                        last_valid = float(rating)
                        interpolated.iloc[i] = last_valid
                    except:
                        if last_valid is not None:
                            interpolated.iloc[i] = last_valid
            else:
                if last_valid is not None:
                    interpolated.iloc[i] = last_valid
                else:
                    interpolated.iloc[i] = self.neutral_value
        
        return interpolated
    
    def _neutral_fill_interpolation(self, ratings_series: pd.Series) -> pd.Series:
        """中性插值"""
        interpolated = ratings_series.copy()
        
        for i, rating in enumerate(interpolated):
            if rating in ['-', None, np.nan]:
                interpolated.iloc[i] = self.neutral_value
            else:
                if rating in self.rating_map:
                    interpolated.iloc[i] = self.rating_map[rating]
                else:
                    try:
                        interpolated.iloc[i] = float(rating)
                    except:
                        interpolated.iloc[i] = self.neutral_value
        
        return interpolated
    
    def _weighted_hybrid_interpolation(self, 
                                     ratings_series: pd.Series,
                                     missing_analysis: Dict) -> pd.Series:
        """加权混合插值"""
        interpolated = ratings_series.copy()
        last_valid = None
        
        for i, rating in enumerate(interpolated):
            if rating not in ['-', None, np.nan]:
                if rating in self.rating_map:
                    last_valid = self.rating_map[rating]
                    interpolated.iloc[i] = last_valid
                else:
                    try:
                        last_valid = float(rating)
                        interpolated.iloc[i] = last_valid
                    except:
                        if last_valid is not None:
                            interpolated.iloc[i] = last_valid
            else:
                if last_valid is not None:
                    # 计算时间衰减权重
                    days_since_valid = self._calculate_days_since_valid(i, ratings_series)
                    time_weight = max(0, 1 - days_since_valid / 7)  # 7天内线性衰减
                    
                    # 加权插值：历史信号 + 中性值
                    interpolated_value = (time_weight * last_valid + 
                                        (1 - time_weight) * self.neutral_value)
                    interpolated.iloc[i] = interpolated_value
                else:
                    interpolated.iloc[i] = self.neutral_value
        
        return interpolated
    
    def _calculate_days_since_valid(self, current_index: int, ratings_series: pd.Series) -> int:
        """计算距离最近有效数据的天数"""
        days = 0
        for i in range(current_index - 1, -1, -1):
            if ratings_series.iloc[i] not in ['-', None, np.nan]:
                break
            days += 1
        return days
    
    def _assess_interpolation_quality(self, 
                                    original_series: pd.Series,
                                    interpolated_series: pd.Series,
                                    missing_analysis: Dict) -> Dict:
        """评估插值质量"""
        
        # 基础质量指标
        missing_ratio = missing_analysis['missing_ratio']
        max_gap = missing_analysis['max_gap_days']
        pattern_type = missing_analysis['pattern_type']
        
        # 质量评分计算
        quality_score = 1.0
        confidence = 1.0
        recommendations = []
        
        # 1. 基于缺失比例的质量调整
        if missing_ratio > 0.5:
            quality_score *= 0.6
            confidence *= 0.7
            recommendations.append("⚠️ 缺失数据过多，建议谨慎使用分析结果")
        elif missing_ratio > 0.3:
            quality_score *= 0.8
            confidence *= 0.85
            recommendations.append("📊 数据质量中等，建议结合其他指标")
        
        # 2. 基于最大缺失间隔的调整
        if max_gap > 10:
            quality_score *= 0.5
            confidence *= 0.6
            recommendations.append("🚨 存在长期数据缺失，结果可靠性降低")
        elif max_gap > 5:
            quality_score *= 0.8
            confidence *= 0.8
            recommendations.append("⚠️ 存在较长数据缺失间隔")
        
        # 3. 基于缺失模式的调整
        if pattern_type == 'sparse':
            quality_score *= 0.6
            recommendations.append("📉 数据稀疏，建议寻找替代数据源")
        elif pattern_type == 'scattered':
            quality_score *= 0.9
            recommendations.append("✅ 数据完整性良好")
        
        # 4. 计算数据一致性
        valid_data = original_series[original_series.notna()]
        if len(valid_data) > 1:
            data_variance = np.var([self.rating_map.get(x, x) for x in valid_data if x != '-'])
            if data_variance < 1:  # 低方差表示一致性好
                quality_score *= 1.1
                confidence *= 1.05
        
        return {
            'quality_score': min(quality_score, 1.0),
            'confidence': min(confidence, 1.0),
            'recommendations': recommendations,
            'missing_ratio': missing_ratio,
            'max_gap_days': max_gap,
            'pattern_type': pattern_type
        }

# 使用示例
if __name__ == "__main__":
    # 创建插值引擎
    engine = AdaptiveInterpolationEngine()
    
    # 示例数据
    test_ratings = pd.Series(['大多', '中多', '-', '-', '小多', '-', '微空', '小空'])
    
    # 执行插值
    result = engine.interpolate_rating_series(test_ratings)
    
    print("插值结果:")
    print(f"原始序列: {test_ratings.tolist()}")
    print(f"插值序列: {result['interpolated_series'].tolist()}")
    print(f"使用策略: {result['strategy_used']}")
    print(f"质量评分: {result['interpolation_quality']:.2f}")
    print(f"置信度: {result['confidence_score']:.2f}")
    for rec in result['recommendations']:
        print(f"建议: {rec}")
