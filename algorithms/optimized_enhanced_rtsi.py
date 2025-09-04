# -*- coding: utf-8 -*-
"""
优化增强RTSI算法
- 规范化得分范围到0-100
- 根据数据质量进行分值调整
- 保持AI增强特性
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime

# 导入基础功能
try:
    from algorithms.enhanced_rtsi_calculator import EnhancedRTSICalculator
    from algorithms.adaptive_interpolation import AdaptiveInterpolationEngine
    from config.gui_i18n import t_gui as t_rtsi
except ImportError as e:
    print(f"导入依赖失败: {e}")
    def t_rtsi(key): return key


class OptimizedEnhancedRTSI:
    """优化增强RTSI计算器"""
    
    def __init__(self, 
                 rtsi_threshold: float = None,
                 volatility_threshold: float = None,
                 trend_strength_threshold: float = None,
                 use_ai_enhancement: bool = None,
                 use_multi_dimensional: bool = None,
                 time_window: int = None):
        
        self.version = "1.0.0"
        self.algorithm_name = "优化增强RTSI"
        
        # 继承原有配置
        self.rtsi_threshold = rtsi_threshold or 0.4
        self.volatility_threshold = volatility_threshold or 0.2
        self.trend_strength_threshold = trend_strength_threshold or 0.3
        self.use_ai_enhancement = use_ai_enhancement if use_ai_enhancement is not None else True
        self.use_multi_dimensional = use_multi_dimensional if use_multi_dimensional is not None else False
        self.time_window = time_window or 60
        
        # 评级映射
        self.rating_map = {
            '大多': 5, '中多': 4, '小多': 3, '微多': 2,
            '微空': 2, '小空': 1, '中空': 1, '大空': 0,
            '强烈推荐': 5, '推荐': 4, '买入': 4, '强烈买入': 5,
            '减持': 1, '卖出': 0, '强烈卖出': 0
        }
        
        # 得分优化配置
        self.score_enhancement = {
            'base_multiplier': 2.5,      # 基础放大倍数
            'volatility_bonus': 15,      # 波动性奖励
            'consistency_bonus': 20,     # 一致性奖励  
            'trend_strength_bonus': 10,  # 趋势强度奖励
            'ai_enhancement_bonus': 5    # AI增强奖励
        }
        
        # 质量调整配置
        self.quality_adjustments = {
            'excellent': (0.95, 1.0),   # 95%-100%: 优秀质量
            'good': (0.85, 0.95),       # 85%-95%: 良好质量  
            'fair': (0.7, 0.85),        # 70%-85%: 一般质量
            'poor': (0.5, 0.7)          # 50%-70%: 较差质量
        }
        
        # 插值质量记录
        self.last_interpolation_quality = 0.0
        self.last_interpolation_strategy = 'unknown'
        
        print(f"🚀 {self.algorithm_name}计算器初始化完成")
        print(f"📊 配置参数: RTSI阈值={self.rtsi_threshold}, 波动性阈值={self.volatility_threshold}")
        print(f"🎯 AI增强={self.use_ai_enhancement}, 多维度={self.use_multi_dimensional}, 时间窗口={self.time_window}天")
    
    def calculate_optimized_enhanced_rtsi(self, 
                                        stock_data: pd.Series, 
                                        date_columns: List[str],
                                        stock_code: str = "",
                                        stock_name: str = "") -> Dict[str, Union[float, str, int, None]]:
        """
        计算优化增强RTSI
        
        Args:
            stock_data: 单只股票的数据行
            date_columns: 日期列名列表
            stock_code: 股票代码
            stock_name: 股票名称
            
        Returns:
            优化增强RTSI结果字典
        """
        calculation_start = datetime.now()
        
        try:
            # 1. 数据预处理（自适应插值）
            processed_ratings = self._preprocess_stock_ratings_optimized(
                stock_data, date_columns
            )
            
            if len(processed_ratings) < 3:
                return self._get_insufficient_data_result(len(processed_ratings))
            
            # 2. 计算基础增强RTSI (0-1范围)
            base_enhanced_rtsi = self._calculate_base_enhanced_rtsi(
                processed_ratings, stock_code, stock_name
            )
            
            if base_enhanced_rtsi is None:
                return self._get_calculation_failed_result()
            
            # 3. 优化得分范围到0-100
            optimized_score = self._optimize_enhanced_score_range(
                base_enhanced_rtsi, processed_ratings
            )
            
            # 4. 根据数据质量调整分值
            quality_adjusted_score = self._apply_quality_adjustment(
                optimized_score, self.last_interpolation_quality
            )
            
            # 5. 生成结果
            calculation_time = (datetime.now() - calculation_start).total_seconds()
            
            return {
                'rtsi': round(quality_adjusted_score, 2),
                'enhanced_rtsi': base_enhanced_rtsi,
                'optimized_rtsi': round(optimized_score, 2),
                'interpolation_quality': round(self.last_interpolation_quality, 3),
                'interpolation_strategy': self.last_interpolation_strategy,
                'quality_adjustment_factor': round(quality_adjusted_score / optimized_score if optimized_score > 0 else 1.0, 3),
                'data_points': len(processed_ratings),
                'algorithm': self.algorithm_name,
                'version': self.version,
                'calculation_time': f"{calculation_time:.3f}s",
                'ai_enhanced': self.use_ai_enhancement,
                'confidence': min(self.last_interpolation_quality + (quality_adjusted_score / 100) * 0.3, 1.0)
            }
            
        except Exception as e:
            return {
                'rtsi': 0,
                'trend': 'calculation_error',
                'confidence': 0,
                'error': str(e),
                'algorithm': self.algorithm_name,
                'version': self.version,
                'calculation_time': f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
            }
    
    def _preprocess_stock_ratings_optimized(self, 
                                           stock_data: pd.Series, 
                                           date_columns: List[str]) -> List[float]:
        """优化的股票评级数据预处理"""
        # 应用时间窗口限制
        limited_date_cols = date_columns
        if len(date_columns) > self.time_window:
            limited_date_cols = sorted(date_columns)[-self.time_window:]
        
        # 第一步：收集原始评级数据
        raw_ratings = []
        for col in limited_date_cols:
            rating_str = str(stock_data[col]).strip()
            if rating_str and rating_str != 'nan' and rating_str != '' and rating_str != '-':
                if rating_str in self.rating_map:
                    raw_ratings.append(self.rating_map[rating_str])
                else:
                    try:
                        rating_num = float(rating_str)
                        if 0 <= rating_num <= 5:
                            raw_ratings.append(rating_num)
                        else:
                            raw_ratings.append(None)
                    except:
                        raw_ratings.append(None)
            else:
                raw_ratings.append(None)
        
        # 第二步：应用自适应插值
        return self._apply_adaptive_interpolation_enhanced(raw_ratings, limited_date_cols)
    
    def _apply_adaptive_interpolation_enhanced(self, 
                                             raw_ratings: List[Optional[float]], 
                                             date_columns: List[str]) -> List[float]:
        """应用优化的自适应插值"""
        try:
            adaptive_engine = AdaptiveInterpolationEngine()
            
            # 创建pandas Series
            ratings_series = pd.Series(
                [r if r is not None else '-' for r in raw_ratings],
                index=date_columns[:len(raw_ratings)]
            )
            
            # 使用自适应插值引擎
            interpolation_result = adaptive_engine.interpolate_rating_series(
                ratings_series=ratings_series,
                stock_info={'code': 'enhanced_rtsi', 'type': 'optimized'},
                market_context=None
            )
            
            # 记录插值质量
            self.last_interpolation_quality = interpolation_result.get('interpolation_quality', 0)
            self.last_interpolation_strategy = interpolation_result.get('strategy_used', 'unknown')
            
            # 转换为数值列表
            interpolated_series = interpolation_result['interpolated_series']
            result = []
            for value in interpolated_series:
                try:
                    if isinstance(value, (int, float)):
                        result.append(float(value))
                    else:
                        if str(value) in self.rating_map:
                            result.append(self.rating_map[str(value)])
                        else:
                            result.append(3.0)  # 默认中性值
                except:
                    result.append(3.0)
            
            return result
            
        except Exception as e:
            print(f"⚠️ 自适应插值失败，回退到双向插值: {e}")
            # 回退到双向插值
            self.last_interpolation_quality = 0.3
            self.last_interpolation_strategy = 'bidirectional_fallback'
            return self._apply_bidirectional_interpolation(raw_ratings)
    
    def _apply_bidirectional_interpolation(self, raw_ratings: List[Optional[float]]) -> List[float]:
        """双向插值回退方案"""
        if len(raw_ratings) <= 2:
            return [r for r in raw_ratings if r is not None]
        
        # 前向填充
        forward_filled = []
        last_valid = 3.0
        for rating in raw_ratings:
            if rating is not None:
                last_valid = rating
                forward_filled.append(rating)
            else:
                forward_filled.append(last_valid)
        
        # 后向填充
        backward_filled = [None] * len(raw_ratings)
        next_valid = 3.0
        for i in range(len(raw_ratings) - 1, -1, -1):
            if raw_ratings[i] is not None:
                next_valid = raw_ratings[i]
                backward_filled[i] = raw_ratings[i]
            else:
                backward_filled[i] = next_valid
        
        # 双向插值
        result = []
        for i, original in enumerate(raw_ratings):
            if original is not None:
                result.append(original)
            else:
                interpolated = (forward_filled[i] + backward_filled[i]) / 2
                result.append(interpolated)
        
        return result
    
    def _calculate_base_enhanced_rtsi(self, 
                                    ratings: List[float], 
                                    stock_code: str = "", 
                                    stock_name: str = "") -> Optional[float]:
        """计算基础增强RTSI (保持0-1范围)"""
        try:
            # 使用原有的增强RTSI算法逻辑，但优化参数
            if len(ratings) < 3:
                return None
                
            # 计算基础统计指标
            ratings_array = np.array(ratings)
            mean_rating = np.mean(ratings_array)
            std_rating = np.std(ratings_array)
            
            # 趋势分析
            x = np.arange(len(ratings))
            if len(ratings) >= 2:
                from scipy.stats import linregress
                slope, intercept, r_value, p_value, std_err = linregress(x, ratings)
            else:
                slope, intercept, r_value, p_value, std_err = 0, 0, 0, 1, 0
            
            # 计算各个组件
            trend_strength = abs(slope) / 5.0  # 标准化到0-1
            consistency = r_value ** 2 if 'r_value' in locals() else 0
            volatility = min(std_rating / 2.5, 1.0)  # 标准化波动性
            
            # 平均评级强度
            rating_strength = mean_rating / 5.0
            
            # 综合计算 (保持0-1范围)
            base_score = (
                trend_strength * 0.3 +
                consistency * 0.25 +
                rating_strength * 0.25 +
                (1 - volatility) * 0.2  # 低波动性得高分
            )
            
            # AI增强 (如果启用)
            if self.use_ai_enhancement:
                ai_factor = self._calculate_ai_enhancement_factor(ratings)
                base_score = base_score * ai_factor
            
            return min(max(base_score, 0), 1)
            
        except Exception as e:
            print(f"计算基础增强RTSI失败: {e}")
            return None
    
    def _calculate_ai_enhancement_factor(self, ratings: List[float]) -> float:
        """计算AI增强因子"""
        try:
            # 简化的AI增强逻辑
            ratings_array = np.array(ratings)
            
            # 检测模式识别
            pattern_score = 1.0
            
            # 上升趋势检测
            if len(ratings) >= 5:
                recent_trend = np.mean(ratings[-3:]) - np.mean(ratings[:3])
                if recent_trend > 0.5:
                    pattern_score += 0.1
            
            # 稳定性检测
            volatility = np.std(ratings_array)
            if volatility < 0.5:
                pattern_score += 0.05
            
            return min(pattern_score, 1.3)  # 最多30%增强
            
        except:
            return 1.0
    
    def _optimize_enhanced_score_range(self, 
                                     base_enhanced_rtsi: float,
                                     processed_ratings: List[float]) -> float:
        """优化增强RTSI得分范围到0-100 (目标94+有效范围)"""
        
        # 1. 基础分数放大 (0-1 → 0-97) - 进一步提高基础上限
        base_score = base_enhanced_rtsi * 97
        
        # 2. 计算额外奖励 (总奖励提升到最多+50分)
        bonus_points = 0
        
        # 数据丰富性奖励 (最多+15分) - 再次提升奖励
        if len(processed_ratings) >= 20:
            bonus_points += 15
        elif len(processed_ratings) >= 15:
            bonus_points += 13
        elif len(processed_ratings) >= 10:
            bonus_points += 10
        elif len(processed_ratings) >= 7:
            bonus_points += 7
        elif len(processed_ratings) >= 5:
            bonus_points += 4
        
        # 评级质量奖励 (最多+30分) - 大幅提升质量奖励
        avg_rating = np.mean(processed_ratings)
        if avg_rating >= 4.8:
            bonus_points += 30  # 极优质量超高奖励
        elif avg_rating >= 4.5:
            bonus_points += 27
        elif avg_rating >= 4.0:
            bonus_points += 22
        elif avg_rating >= 3.5:
            bonus_points += 15
        elif avg_rating >= 3.0:
            bonus_points += 12  # 适度提升3.0分数奖励
        elif avg_rating >= 2.5:
            bonus_points += 8   # 为2.5-3.0增加奖励
        elif avg_rating >= 2.0:
            bonus_points += 4   # 为2.0-2.5增加奖励
        elif avg_rating < 1.5:
            bonus_points -= 8   # 极低评级重罚
        
        # 一致性奖励/惩罚 (最多+25分/-15分) - 进一步极化差异
        rating_std = np.std(processed_ratings)
        if rating_std <= 0.1:
            bonus_points += 25  # 极高一致性超高奖励
        elif rating_std <= 0.3:
            bonus_points += 20
        elif rating_std <= 0.6:
            bonus_points += 15
        elif rating_std <= 1.0:
            bonus_points += 8
        elif rating_std <= 1.5:
            bonus_points += 2
        elif rating_std >= 2.5:
            bonus_points -= 15  # 极高波动重罚
        
        # 趋势强度奖励 (最多+12分) - 新增趋势奖励
        if len(processed_ratings) >= 5:
            # 计算趋势斜率
            x = np.arange(len(processed_ratings))
            try:
                from scipy.stats import linregress
                slope, _, r_value, _, _ = linregress(x, processed_ratings)
                trend_strength = abs(slope) * (r_value ** 2)  # 趋势强度 × 一致性
                
                if trend_strength >= 0.5 and slope > 0:  # 强上升趋势
                    bonus_points += 12
                elif trend_strength >= 0.3 and slope > 0:  # 中等上升趋势
                    bonus_points += 8
                elif trend_strength >= 0.1 and slope > 0:  # 轻微上升趋势
                    bonus_points += 5
            except:
                pass
        
        # 3. 最终得分
        final_score = base_score + bonus_points
        
        return min(final_score, 100)
    
    def _apply_quality_adjustment(self, 
                                optimized_score: float,
                                interpolation_quality: float) -> float:
        """根据数据质量调整分值"""
        
        # 确定质量等级和调整因子
        if interpolation_quality >= 0.9:
            adjustment_factor = 1.0      # 无调整
        elif interpolation_quality >= 0.75:
            adjustment_factor = 0.95     # 5%调整
        elif interpolation_quality >= 0.6:
            adjustment_factor = 0.9      # 10%调整
        elif interpolation_quality >= 0.4:
            adjustment_factor = 0.8      # 20%调整
        else:
            adjustment_factor = 0.7      # 30%调整
        
        # 应用调整
        adjusted_score = optimized_score * adjustment_factor
        
        # 增强低分区间差异化 - 极致降低最低分数保障
        min_score = max(optimized_score * 0.05, 0)  # 降低至5%或0分，允许极低分数
        final_score = max(adjusted_score, min_score)
        
        return min(final_score, 100)
    
    def _get_insufficient_data_result(self, data_points: int) -> Dict:
        """数据不足结果"""
        return {
            'rtsi': 0,
            'trend': 'insufficient_data',
            'confidence': 0,
            'data_points': data_points,
            'algorithm': self.algorithm_name,
            'version': self.version,
            'error': f'数据点不足，需要至少3个有效数据点，当前只有{data_points}个'
        }
    
    def _get_calculation_failed_result(self) -> Dict:
        """计算失败结果"""
        return {
            'rtsi': 0,
            'trend': 'calculation_failed',
            'confidence': 0,
            'algorithm': self.algorithm_name,
            'version': self.version,
            'error': '增强RTSI计算失败'
        }


def calculate_optimized_enhanced_rtsi(stock_data: pd.Series,
                                    date_columns: List[str],
                                    stock_code: str = "",
                                    stock_name: str = "",
                                    **kwargs) -> Dict[str, Union[float, str, int, None]]:
    """
    优化增强RTSI计算入口函数
    
    Args:
        stock_data: 单只股票的数据行
        date_columns: 日期列名列表
        stock_code: 股票代码
        stock_name: 股票名称
        **kwargs: 其他配置参数
        
    Returns:
        优化增强RTSI结果
    """
    calculator = OptimizedEnhancedRTSI(**kwargs)
    return calculator.calculate_optimized_enhanced_rtsi(
        stock_data, date_columns, stock_code, stock_name
    )
