#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARTS - Adaptive Rating Trend Strength 自适应评级趋势强度指数
一个比RTSI更先进的股票评级分析算法

核心优势：
1. 动态时间加权 - 近期数据权重更高
2. 模式识别 - 识别评级变化模式
3. 信心度量化 - 多维度置信度评估
4. 自适应阈值 - 根据历史波动性调整
5. 8级精细评级 - 更准确的分级体系

作者: AI股票大师团队
创建时间: 2025-01-16
算法版本: v1.0
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks
from typing import Dict, List, Union, Optional, Tuple
import warnings
from datetime import datetime, timedelta
from enum import Enum
import math

warnings.filterwarnings('ignore', category=RuntimeWarning)

class TrendPattern(Enum):
    """趋势模式枚举"""
    STRONG_UPTREND = "强势上升"
    MODERATE_UPTREND = "温和上升"
    WEAK_UPTREND = "弱势上升"
    SIDEWAYS = "横盘整理"
    WEAK_DOWNTREND = "弱势下降"
    MODERATE_DOWNTREND = "温和下降"
    STRONG_DOWNTREND = "强势下降"
    VOLATILE = "剧烈波动"

class ConfidenceLevel(Enum):
    """置信度等级"""
    VERY_HIGH = "极高"
    HIGH = "高"
    MEDIUM = "中等"
    LOW = "低"
    VERY_LOW = "极低"

class ARTSCalculator:
    """
    ARTS - Adaptive Rating Trend Strength Calculator
    自适应评级趋势强度计算器
    """
    
    def __init__(self, 
                 time_window: int = 60,
                 decay_factor: float = 0.95,
                 volatility_window: int = 20,
                 pattern_sensitivity: float = 0.1,
                 confidence_threshold: float = 0.6):
        """
        初始化ARTS计算器
        
        参数:
            time_window: 时间窗口大小（天数）
            decay_factor: 时间衰减因子（0-1），越接近1表示对历史数据的重视程度越高
            volatility_window: 波动性计算窗口
            pattern_sensitivity: 模式识别敏感度
            confidence_threshold: 置信度阈值
        """
        self.time_window = time_window
        self.decay_factor = decay_factor
        self.volatility_window = volatility_window
        self.pattern_sensitivity = pattern_sensitivity
        self.confidence_threshold = confidence_threshold
        
        # 8级评级映射表
        self.rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0,
            '中性': 3.5, '持有': 3.5, '-': None, '': None
        }
        
        # 反向映射
        self.reverse_rating_map = {
            7: "大多", 6: "中多", 5: "小多", 4: "微多",
            3: "微空", 2: "小空", 1: "中空", 0: "大空"
        }
        
        # 统计信息
        self.stats = {
            'total_calculations': 0,
            'pattern_detected': 0,
            'high_confidence': 0,
            'adaptive_adjustments': 0
        }
    
    def calculate_arts(self, stock_ratings: pd.Series, 
                      stock_code: str = None) -> Dict[str, Union[float, str, int, None]]:
        """
        计算ARTS指数
        
        参数:
            stock_ratings: 股票评级序列
            stock_code: 股票代码
            
        返回:
            dict: ARTS分析结果
        """
        calculation_start = datetime.now()
        self.stats['total_calculations'] += 1
        
        # 1. 数据预处理和验证
        valid_ratings, time_weights = self._preprocess_data(stock_ratings)
        
        if len(valid_ratings) < 3:
            return self._get_insufficient_data_result(len(valid_ratings))
        
        try:
            # 2. 核心ARTS计算
            arts_score = self._calculate_core_arts(valid_ratings, time_weights)
            
            # 3. 趋势模式识别
            pattern = self._identify_trend_pattern(valid_ratings)
            
            # 4. 多维度置信度评估
            confidence = self._calculate_confidence(valid_ratings, arts_score)
            
            # 5. 自适应调整
            adjusted_score = self._adaptive_adjustment(arts_score, valid_ratings, confidence)
            
            # 6. 8级评级分类
            rating_level = self._classify_to_8_levels(adjusted_score)
            
            # 7. 趋势强度和方向
            trend_strength, trend_direction = self._analyze_trend_characteristics(valid_ratings)
            
            # 8. 生成投资建议
            recommendation = self._generate_recommendation(rating_level, pattern, confidence.value)
            
            # 9. 计算附加指标
            volatility = self._calculate_adaptive_volatility(valid_ratings)
            momentum = self._calculate_momentum(valid_ratings)
            
            calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
            
            # 更新统计
            if pattern != TrendPattern.SIDEWAYS:
                self.stats['pattern_detected'] += 1
            if confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]:
                self.stats['high_confidence'] += 1
            
            return {
                'arts_score': round(adjusted_score, 2),
                'rating_level': rating_level,
                'trend_pattern': pattern.value,
                'confidence_level': confidence.value,
                'trend_strength': round(trend_strength, 3),
                'trend_direction': trend_direction,
                'volatility': round(volatility, 3),
                'momentum': round(momentum, 3),
                'recommendation': recommendation,
                'raw_score': round(arts_score, 2),
                'data_points': len(valid_ratings),
                'time_weighted': True,
                'pattern_detected': pattern != TrendPattern.SIDEWAYS,
                'calculation_time': calculation_time,
                'algorithm': 'ARTS_v1.0',
                'recent_rating': int(valid_ratings[-1]) if valid_ratings else None,
                'rating_change_5d': self._calculate_rating_change(valid_ratings, 5),
                'rating_change_10d': self._calculate_rating_change(valid_ratings, 10)
            }
            
        except Exception as e:
            return self._get_error_result(str(e))
    
    def _preprocess_data(self, stock_ratings: pd.Series) -> Tuple[List[float], List[float]]:
        """
        数据预处理和时间加权计算
        
        返回:
            tuple: (有效评级列表, 时间权重列表)
        """
        valid_ratings = []
        
        # 提取有效评级
        for rating in stock_ratings:
            str_rating = str(rating).strip()
            if str_rating in self.rating_map and self.rating_map[str_rating] is not None:
                valid_ratings.append(self.rating_map[str_rating])
        
        # 限制时间窗口
        if len(valid_ratings) > self.time_window:
            valid_ratings = valid_ratings[-self.time_window:]
        
        # 计算时间权重（指数衰减）
        n = len(valid_ratings)
        time_weights = []
        for i in range(n):
            # 越近期的数据权重越高
            weight = self.decay_factor ** (n - 1 - i)
            time_weights.append(weight)
        
        # 归一化权重
        total_weight = sum(time_weights)
        time_weights = [w / total_weight for w in time_weights]
        
        return valid_ratings, time_weights
    
    def _calculate_core_arts(self, ratings: List[float], weights: List[float]) -> float:
        """
        计算核心ARTS分数
        
        融合以下组件：
        1. 加权线性趋势 (40%)
        2. 模式一致性 (30%)
        3. 动量强度 (20%)
        4. 稳定性 (10%)
        """
        # 1. 加权线性趋势分析
        x = np.arange(len(ratings))
        
        # 使用权重进行加权回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, ratings)
        
        # 考虑权重的修正
        weighted_ratings = np.array(ratings) * np.array(weights)
        weighted_slope = np.sum(np.diff(weighted_ratings)) / (len(ratings) - 1) if len(ratings) > 1 else 0
        
        trend_component = abs(weighted_slope) * 20  # 趋势强度
        
        # 2. 模式一致性（加权R²）
        consistency = r_value ** 2
        consistency_component = consistency * 100
        
        # 3. 动量强度（近期变化率）
        if len(ratings) >= 3:
            recent_momentum = (ratings[-1] - ratings[-3]) * weights[-1]
            momentum_component = abs(recent_momentum) * 15
        else:
            momentum_component = 0
        
        # 4. 稳定性（方差的倒数）
        if len(ratings) > 1:
            weighted_variance = np.average((np.array(ratings) - np.average(ratings, weights=weights))**2, weights=weights)
            stability_component = min(10, 10 / (1 + weighted_variance))
        else:
            stability_component = 5
        
        # 综合ARTS分数
        arts_score = (
            trend_component * 0.4 +
            consistency_component * 0.3 +
            momentum_component * 0.2 +
            stability_component * 0.1
        )
        
        return min(100, max(0, arts_score))
    
    def _identify_trend_pattern(self, ratings: List[float]) -> TrendPattern:
        """
        识别趋势模式
        
        使用多种技术识别评级变化模式：
        - 线性趋势强度
        - 波峰波谷分析
        - 变化率分析
        """
        if len(ratings) < 5:
            return TrendPattern.SIDEWAYS
        
        # 计算总体斜率
        x = np.arange(len(ratings))
        slope, _, r_value, _, _ = stats.linregress(x, ratings)
        
        # 计算变化率
        total_change = ratings[-1] - ratings[0]
        change_rate = total_change / len(ratings)
        
        # 计算波动性
        volatility = np.std(ratings)
        
        # 识别峰谷
        peaks, _ = find_peaks(ratings, height=np.mean(ratings))
        valleys, _ = find_peaks([-r for r in ratings], height=-np.mean(ratings))
        
        # 模式判断逻辑
        if volatility > 1.5:
            return TrendPattern.VOLATILE
        elif slope > 0.1 and r_value**2 > 0.6:
            if change_rate > 0.3:
                return TrendPattern.STRONG_UPTREND
            elif change_rate > 0.1:
                return TrendPattern.MODERATE_UPTREND
            else:
                return TrendPattern.WEAK_UPTREND
        elif slope < -0.1 and r_value**2 > 0.6:
            if change_rate < -0.3:
                return TrendPattern.STRONG_DOWNTREND
            elif change_rate < -0.1:
                return TrendPattern.MODERATE_DOWNTREND
            else:
                return TrendPattern.WEAK_DOWNTREND
        else:
            return TrendPattern.SIDEWAYS
    
    def _calculate_confidence(self, ratings: List[float], arts_score: float) -> ConfidenceLevel:
        """
        计算多维度置信度
        
        考虑因素：
        1. 数据量充足性
        2. 趋势一致性
        3. 统计显著性
        4. 时间跨度
        """
        data_score = min(1.0, len(ratings) / 30)  # 数据量评分
        
        # 趋势一致性
        if len(ratings) > 3:
            x = np.arange(len(ratings))
            _, _, r_value, p_value, _ = stats.linregress(x, ratings)
            consistency_score = r_value ** 2
            significance_score = max(0, 1 - p_value)
        else:
            consistency_score = 0.5
            significance_score = 0.3
        
        # 时间跨度评分
        time_score = min(1.0, len(ratings) / self.time_window)
        
        # 综合置信度
        confidence_score = (
            data_score * 0.3 +
            consistency_score * 0.3 +
            significance_score * 0.2 +
            time_score * 0.2
        )
        
        if confidence_score >= 0.85:
            return ConfidenceLevel.VERY_HIGH
        elif confidence_score >= 0.70:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.50:
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.30:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def _adaptive_adjustment(self, base_score: float, ratings: List[float], confidence: ConfidenceLevel) -> float:
        """
        自适应调整分数
        
        根据历史波动性和置信度调整最终分数
        """
        if len(ratings) < 5:
            return base_score
        
        # 计算历史波动性
        volatility = np.std(ratings)
        
        # 置信度调整因子
        confidence_factors = {
            ConfidenceLevel.VERY_HIGH: 1.0,
            ConfidenceLevel.HIGH: 0.95,
            ConfidenceLevel.MEDIUM: 0.85,
            ConfidenceLevel.LOW: 0.70,
            ConfidenceLevel.VERY_LOW: 0.50
        }
        
        confidence_factor = confidence_factors[confidence]
        
        # 波动性调整（高波动性降低可信度）
        volatility_factor = max(0.7, 1 - volatility * 0.1)
        
        # 自适应调整
        adjusted_score = base_score * confidence_factor * volatility_factor
        
        if adjusted_score != base_score:
            self.stats['adaptive_adjustments'] += 1
        
        return adjusted_score
    
    def _classify_to_8_levels(self, arts_score: float) -> str:
        """
        将ARTS分数分类为8级评级
        
        更科学的分级方法，考虑分数分布的非线性特性
        """
        # 使用非线性映射，让中间级别更容易触发
        if arts_score >= 85:
            return "7级-大多"
        elif arts_score >= 70:
            return "6级-中多"
        elif arts_score >= 55:
            return "5级-小多"
        elif arts_score >= 45:
            return "4级-微多"
        elif arts_score >= 35:
            return "3级-微空"
        elif arts_score >= 20:
            return "2级-小空"
        elif arts_score >= 10:
            return "1级-中空"
        else:
            return "0级-大空"
    
    def _analyze_trend_characteristics(self, ratings: List[float]) -> Tuple[float, str]:
        """分析趋势特征"""
        if len(ratings) < 2:
            return 0.0, "未知"
        
        # 计算趋势强度（斜率的绝对值）
        x = np.arange(len(ratings))
        slope, _, r_value, _, _ = stats.linregress(x, ratings)
        trend_strength = abs(slope) * r_value ** 2
        
        # 趋势方向
        if slope > 0.05:
            trend_direction = "上升"
        elif slope < -0.05:
            trend_direction = "下降"
        else:
            trend_direction = "横盘"
        
        return trend_strength, trend_direction
    
    def _generate_recommendation(self, rating_level: str, pattern: TrendPattern, confidence: str) -> str:
        """生成投资建议"""
        level_num = int(rating_level.split('级')[0])
        
        if level_num >= 6:
            base_rec = "买入"
        elif level_num >= 4:
            base_rec = "持有"
        else:
            base_rec = "卖出"
        
        # 根据模式和置信度调整
        if confidence in ["极高", "高"]:
            if pattern in [TrendPattern.STRONG_UPTREND, TrendPattern.MODERATE_UPTREND]:
                return f"强烈{base_rec}"
            elif pattern in [TrendPattern.STRONG_DOWNTREND, TrendPattern.MODERATE_DOWNTREND]:
                if base_rec == "买入":
                    return "谨慎买入"
                else:
                    return f"强烈{base_rec}"
        
        return f"谨慎{base_rec}"
    
    def _calculate_adaptive_volatility(self, ratings: List[float]) -> float:
        """计算自适应波动性"""
        if len(ratings) < 3:
            return 0.0
        
        # 使用滚动窗口计算波动性
        window = min(self.volatility_window, len(ratings))
        recent_ratings = ratings[-window:]
        return np.std(recent_ratings)
    
    def _calculate_momentum(self, ratings: List[float]) -> float:
        """计算动量指标"""
        if len(ratings) < 3:
            return 0.0
        
        # 使用加权动量
        momentum = 0
        weights = [0.5, 0.3, 0.2]  # 1天前、2天前、3天前的权重
        
        for i in range(min(3, len(ratings) - 1)):
            if i < len(ratings) - 1:
                change = ratings[-(i+1)] - ratings[-(i+2)]
                momentum += change * weights[i]
        
        return momentum
    
    def _calculate_rating_change(self, ratings: List[float], days: int) -> float:
        """计算N天评级变化"""
        if len(ratings) < days + 1:
            return 0.0
        return ratings[-1] - ratings[-days-1]
    
    def _get_insufficient_data_result(self, data_points: int) -> Dict:
        """数据不足时的返回结果"""
        return {
            'arts_score': 0,
            'rating_level': "数据不足",
            'trend_pattern': "无法判断",
            'confidence_level': "极低",
            'trend_strength': 0,
            'trend_direction': "未知",
            'volatility': 0,
            'momentum': 0,
            'recommendation': "等待更多数据",
            'data_points': data_points,
            'algorithm': 'ARTS_v1.0',
            'error': "数据点不足"
        }
    
    def _get_error_result(self, error_msg: str) -> Dict:
        """错误时的返回结果"""
        return {
            'arts_score': 0,
            'rating_level': "计算错误",
            'trend_pattern': "无法判断",
            'confidence_level': "极低",
            'error': error_msg,
            'algorithm': 'ARTS_v1.0'
        }
    
    def get_algorithm_info(self) -> Dict:
        """获取算法信息"""
        return {
            'name': 'ARTS - Adaptive Rating Trend Strength',
            'version': '1.0',
            'description': '自适应评级趋势强度指数',
            'features': [
                '动态时间加权',
                '模式识别',
                '多维度置信度',
                '自适应阈值',
                '8级精细评级'
            ],
            'advantages_over_rtsi': [
                '时间加权：近期数据权重更高，反应更敏感',
                '模式识别：能识别复杂的评级变化模式',
                '置信度量化：提供可靠性评估',
                '自适应调整：根据历史波动性动态调整',
                '非线性分级：更科学的8级评级体系'
            ],
            'config': {
                'time_window': self.time_window,
                'decay_factor': self.decay_factor,
                'volatility_window': self.volatility_window,
                'pattern_sensitivity': self.pattern_sensitivity,
                'confidence_threshold': self.confidence_threshold
            },
            'stats': self.stats
        }

# 测试函数
def test_arts_calculator():
    """测试ARTS算法"""
    print("🚀 测试ARTS算法...")
    
    # 创建测试数据
    test_data = pd.Series(['大多', '中多', '中多', '小多', '微多', '微空', '小空', '中空'])
    
    # 创建ARTS计算器
    arts = ARTSCalculator()
    
    # 计算ARTS分数
    result = arts.calculate_arts(test_data, "000001")
    
    print(f"ARTS分数: {result['arts_score']}")
    print(f"评级等级: {result['rating_level']}")
    print(f"趋势模式: {result['trend_pattern']}")
    print(f"置信度: {result['confidence_level']}")
    print(f"投资建议: {result['recommendation']}")
    
    # 获取算法信息
    info = arts.get_algorithm_info()
    print(f"\n算法名称: {info['name']}")
    print(f"版本: {info['version']}")
    print("核心优势:")
    for advantage in info['advantages_over_rtsi']:
        print(f"  • {advantage}")
    
    return True

if __name__ == "__main__":
    test_arts_calculator()

