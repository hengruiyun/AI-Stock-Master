# -*- coding: utf-8 -*-
"""
优化标准RTSI算法
- 规范化得分范围到0-100
- 根据数据质量进行分值调整
- 增强区分度和稳定性
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime

# 导入基础RTSI功能
try:
    from algorithms.rtsi_calculator import (
        calculate_rating_trend_strength_index_base,
        _get_insufficient_data_result,
        get_rating_score_map
    )
    from algorithms.adaptive_interpolation import AdaptiveInterpolationEngine
    from config.gui_i18n import t_gui as t_rtsi, set_language
except ImportError as e:
    print(f"导入依赖失败: {e}")
    # 提供备用函数
    def t_rtsi(key): return key
    def set_language(lang): pass

warnings.filterwarnings('ignore', category=RuntimeWarning)


class OptimizedStandardRTSI:
    """优化标准RTSI计算器"""
    
    def __init__(self):
        self.version = "1.0.0"
        self.algorithm_name = "优化标准RTSI"
        
        # 得分映射配置
        self.score_mapping = {
            # 基础分数段 (0-40): 低质量/弱趋势
            'base_low': (0, 40),
            # 中等分数段 (40-70): 中等质量/趋势
            'base_medium': (40, 70), 
            # 高分数段 (70-100): 高质量/强趋势
            'base_high': (70, 100)
        }
        
        # 质量折扣配置
        self.quality_discounts = {
            'excellent': (0.9, 1.0),    # 90%-100%: 优秀质量
            'good': (0.7, 0.9),         # 70%-90%: 良好质量
            'fair': (0.5, 0.7),         # 50%-70%: 一般质量
            'poor': (0.0, 0.5)          # 0%-50%: 较差质量
        }
        
    def calculate_optimized_rtsi(self, 
                               stock_ratings: pd.Series, 
                               stock_code: str = None,
                               stock_name: str = None,
                               language: str = 'zh_CN') -> Dict[str, Union[float, str, int, None]]:
        """
        计算优化标准RTSI
        
        Args:
            stock_ratings: 股票评级序列
            stock_code: 股票代码
            stock_name: 股票名称
            language: 语言设置
            
        Returns:
            优化后的RTSI结果字典
        """
        set_language(language)
        calculation_start = datetime.now()
        
        try:
            # 1. 应用自适应插值
            interpolation_result = self._apply_adaptive_interpolation(
                stock_ratings, stock_code, stock_name
            )
            
            processed_series = interpolation_result['processed_series']
            interpolation_quality = interpolation_result['quality']
            interpolation_strategy = interpolation_result['strategy']
            
            # 2. 计算基础RTSI
            base_result = calculate_rating_trend_strength_index_base(
                processed_series, language
            )
            
            if base_result.get('rtsi', 0) == 0:
                return self._get_insufficient_data_result(len(processed_series))
            
            # 3. 优化得分范围 (0-100)
            raw_rtsi = base_result.get('rtsi', 0)
            optimized_score = self._optimize_score_range(
                raw_rtsi, 
                base_result.get('r_squared', 0),
                base_result.get('confidence', 0),
                base_result.get('slope', 0)
            )
            
            # 4. 根据数据质量调整分值
            quality_adjusted_score = self._apply_quality_discount(
                optimized_score, interpolation_quality
            )
            
            # 5. 生成最终结果
            final_result = base_result.copy()
            final_result.update({
                'rtsi': round(quality_adjusted_score, 2),
                'raw_rtsi': round(raw_rtsi, 2),
                'optimized_rtsi': round(optimized_score, 2),
                'interpolation_quality': round(interpolation_quality, 3),
                'interpolation_strategy': interpolation_strategy,
                'quality_discount_applied': round(quality_adjusted_score / optimized_score if optimized_score > 0 else 1.0, 3),
                'algorithm': self.algorithm_name,
                'version': self.version,
                'calculation_time': f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
            })
            
            return final_result
            
        except Exception as e:
            return {
                'rtsi': 0,
                'trend': 'calculation_error',
                'confidence': 0,
                'error': str(e),
                'algorithm': self.algorithm_name,
                'calculation_time': f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
            }
    
    def _apply_adaptive_interpolation(self, 
                                    stock_ratings: pd.Series,
                                    stock_code: str = None,
                                    stock_name: str = None) -> Dict:
        """应用自适应插值"""
        try:
            adaptive_engine = AdaptiveInterpolationEngine()
            
            interpolation_result = adaptive_engine.interpolate_rating_series(
                ratings_series=stock_ratings,
                stock_info={'code': stock_code, 'name': stock_name} if stock_code else None,
                market_context=None
            )
            
            return {
                'processed_series': interpolation_result['interpolated_series'],
                'quality': interpolation_result.get('interpolation_quality', 0.5),
                'strategy': interpolation_result.get('strategy_used', 'adaptive')
            }
            
        except Exception as e:
            # 回退到原始数据
            return {
                'processed_series': stock_ratings.dropna(),
                'quality': 0.3,  # 低质量标记
                'strategy': 'fallback_dropna'
            }
    
    def _optimize_score_range(self, 
                            raw_rtsi: float,
                            r_squared: float,
                            confidence: float, 
                            slope: float) -> float:
        """
        优化得分范围到0-100
        
        Args:
            raw_rtsi: 原始RTSI得分
            r_squared: R²值 (趋势一致性)
            confidence: 置信度 (显著性)
            slope: 回归斜率 (趋势方向性)
            
        Returns:
            优化后的0-100范围得分
        """
        # 1. 非线性映射原始RTSI到基础得分
        if raw_rtsi <= 0:
            base_score = 0
        elif raw_rtsi >= 100:
            base_score = 85  # 原始满分映射到85分，留出提升空间
        else:
            # 使用S形曲线提升区分度
            normalized = raw_rtsi / 100.0
            # 应用sigmoid变换增强中间区域的区分度
            sigmoid_factor = 2 / (1 + np.exp(-6 * (normalized - 0.5)))
            base_score = sigmoid_factor * 85
        
        # 2. 根据统计指标进行奖励调整
        bonus_points = 0
        
        # R²奖励 (最多+8分)
        if r_squared > 0.8:
            bonus_points += 8
        elif r_squared > 0.6:
            bonus_points += 5
        elif r_squared > 0.4:
            bonus_points += 2
        
        # 置信度奖励 (最多+4分)
        if confidence > 0.8:
            bonus_points += 4
        elif confidence > 0.6:
            bonus_points += 2
        
        # 趋势强度奖励 (最多+3分)
        abs_slope = abs(slope)
        if abs_slope > 0.5:
            bonus_points += 3
        elif abs_slope > 0.2:
            bonus_points += 1
        
        # 3. 最终得分计算
        final_score = min(base_score + bonus_points, 100)
        
        return max(final_score, 0)
    
    def _apply_quality_discount(self, 
                              optimized_score: float,
                              interpolation_quality: float) -> float:
        """
        根据数据质量对分值进行折扣
        
        Args:
            optimized_score: 优化后的得分
            interpolation_quality: 插值质量 (0-1)
            
        Returns:
            质量调整后的得分
        """
        # 确定质量等级
        if interpolation_quality >= 0.9:
            quality_level = 'excellent'
            discount_factor = 1.0  # 无折扣
        elif interpolation_quality >= 0.7:
            quality_level = 'good'
            discount_factor = 0.95  # 5%折扣
        elif interpolation_quality >= 0.5:
            quality_level = 'fair' 
            discount_factor = 0.85  # 15%折扣
        else:
            quality_level = 'poor'
            discount_factor = 0.7   # 30%折扣
        
        # 应用质量折扣
        discounted_score = optimized_score * discount_factor
        
        # 确保最低分数不低于原始得分的50%
        min_score = optimized_score * 0.5
        final_score = max(discounted_score, min_score)
        
        return min(final_score, 100)
    
    def _get_insufficient_data_result(self, data_points: int) -> Dict:
        """数据不足时的结果"""
        return {
            'rtsi': 0,
            'trend': 'insufficient_data',
            'confidence': 0,
            'slope': 0,
            'r_squared': 0,
            'recent_score': None,
            'score_change_5d': None,
            'data_points': data_points,
            'interpolation_quality': 0,
            'interpolation_strategy': 'none',
            'algorithm': self.algorithm_name,
            'version': self.version,
            'error': f'数据点不足，需要至少3个有效数据点，当前只有{data_points}个'
        }


def calculate_optimized_standard_rtsi(stock_ratings: pd.Series,
                                    stock_code: str = None, 
                                    stock_name: str = None,
                                    language: str = 'zh_CN') -> Dict[str, Union[float, str, int, None]]:
    """
    优化标准RTSI计算入口函数
    
    Args:
        stock_ratings: 股票评级序列
        stock_code: 股票代码
        stock_name: 股票名称
        language: 语言设置
        
    Returns:
        优化标准RTSI结果
    """
    calculator = OptimizedStandardRTSI()
    return calculator.calculate_optimized_rtsi(
        stock_ratings, stock_code, stock_name, language
    )

