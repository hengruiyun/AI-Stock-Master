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
        
        self.version = "2.3.0"
        self.algorithm_name = "优化增强RTSI v2.3 (方案C)"
        
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
        
        #print(f"ertsi {self.algorithm_name}计算器初始化完成")
        #print(f"ertsi 配置参数: RTSI阈值={self.rtsi_threshold}, 波动性阈值={self.volatility_threshold}")
        #print(f"ertsi AI增强={self.use_ai_enhancement}, 多维度={self.use_multi_dimensional}, 时间窗口={self.time_window}天")
    
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
        """计算基础增强RTSI (保持0-1范围) - 方案C：55%评级强度权重"""
        try:
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
            
            # ===== 方案C核心：重新分配权重（评级强度55%）=====
            rating_strength = mean_rating / 5.0        # 评级强度，范围0-1
            consistency = r_value ** 2 if 'r_value' in locals() else 0
            volatility = min(std_rating / 2.5, 1.0)   # 标准化波动性
            
            # 新的权重分配：评级强度占主导（55%），移除trend_strength
            base_score = (
                rating_strength * 0.55 +    # 从25%提高到55%
                consistency * 0.25 +         # 保持25%
                (1 - volatility) * 0.20     # 保持20%
            )
            
            # AI增强（适度增强）
            if self.use_ai_enhancement:
                ai_factor = self._calculate_ai_enhancement_factor(ratings)
                base_score = base_score * ai_factor
            
            return min(max(base_score, 0), 1)
            
        except Exception as e:
            print(f"计算基础增强RTSI失败: {e}")
            return None
    
    def _calculate_ai_enhancement_factor(self, ratings: List[float]) -> float:
        """计算AI增强因子 - 方案C：适度增强"""
        try:
            ratings_array = np.array(ratings)
            pattern_score = 1.0
            
            # 上升趋势检测
            if len(ratings) >= 5:
                recent_trend = np.mean(ratings[-3:]) - np.mean(ratings[:3])
                if recent_trend > 0.5:
                    pattern_score += 0.15  # 从0.1提高到0.15
            
            # 稳定性检测
            volatility = np.std(ratings_array)
            if volatility < 0.5:
                pattern_score += 0.08  # 从0.05提高到0.08
            
            return min(pattern_score, 1.35)  # 从1.3提高到1.35，最多35%增强
            
        except:
            return 1.0
    
    def _optimize_enhanced_score_range(self, 
                                     base_enhanced_rtsi: float,
                                     processed_ratings: List[float]) -> float:
        """方案C：优化增强RTSI得分范围到0-100（放宽条件+提高基础分）"""
        
        # ===== 改进1: 基础分上限 85 → 88 =====
        base_score = base_enhanced_rtsi * 88
        
        bonus_points = 0
        
        # A. 数据丰富性奖励 (最多+8分)
        if len(processed_ratings) >= 30:
            bonus_points += 8
        elif len(processed_ratings) >= 20:
            bonus_points += 6
        elif len(processed_ratings) >= 15:
            bonus_points += 5
        elif len(processed_ratings) >= 10:
            bonus_points += 4
        elif len(processed_ratings) >= 7:
            bonus_points += 3
        elif len(processed_ratings) >= 5:
            bonus_points += 2
        
        # ===== 改进2: 评级质量奖励条件放宽 (最多+15分) =====
        avg_rating = np.mean(processed_ratings)
        if avg_rating >= 4.5:           # 从4.8放宽到4.5 ✓
            bonus_points += 15
        elif avg_rating >= 4.2:         # 从4.5放宽到4.2 ✓
            bonus_points += 13
        elif avg_rating >= 3.8:         # 从4.0放宽到3.8 ✓
            bonus_points += 11
        elif avg_rating >= 3.3:         # 从3.5放宽到3.3 ✓
            bonus_points += 8
        elif avg_rating >= 2.8:         # 从3.0放宽到2.8 ✓
            bonus_points += 5
        elif avg_rating >= 2.3:         # 从2.5放宽到2.3 ✓
            bonus_points += 2
        elif avg_rating >= 1.8:         # 从2.0放宽到1.8 ✓
            bonus_points += 0
        elif avg_rating < 1.5:
            bonus_points -= 5
        
        # ===== 改进3: 一致性奖励条件放宽 (最多+10分) =====
        rating_std = np.std(processed_ratings)
        if rating_std <= 0.15:          # 从0.1放宽到0.15 ✓
            bonus_points += 10
        elif rating_std <= 0.4:         # 从0.3放宽到0.4 ✓
            bonus_points += 8
        elif rating_std <= 0.7:         # 从0.6放宽到0.7 ✓
            bonus_points += 6
        elif rating_std <= 1.1:         # 从1.0放宽到1.1 ✓
            bonus_points += 4
        elif rating_std <= 1.6:         # 从1.5放宽到1.6 ✓
            bonus_points += 2
        elif rating_std >= 2.5:
            bonus_points -= 3
        
        # ===== 改进4: 趋势强度奖励条件放宽 (最多+10分) =====
        if len(processed_ratings) >= 5:
            x = np.arange(len(processed_ratings))
            try:
                from scipy.stats import linregress
                slope, _, r_value, _, _ = linregress(x, processed_ratings)
                
                # 使用绝对涨幅代替斜率
                total_change = processed_ratings[-1] - processed_ratings[0]
                trend_consistency = r_value ** 2
                
                if total_change > 0.8 and trend_consistency > 0.4:  # 从1.0/0.5放宽到0.8/0.4 ✓
                    bonus_points += 10
                elif total_change > 0.4 and trend_consistency > 0.3:  # 从0.5/0.4放宽到0.4/0.3 ✓
                    bonus_points += 7
                elif total_change > 0.15 and trend_consistency > 0.25:  # 从0.2/0.3放宽到0.15/0.25 ✓
                    bonus_points += 4
            except:
                pass
        
        # E. 极端情况奖励 (最多+5分)
        excellent_conditions = 0
        
        if avg_rating >= 4.3:           # 从4.5放宽到4.3 ✓
            excellent_conditions += 1
        if rating_std <= 0.5:           # 从0.4放宽到0.5 ✓
            excellent_conditions += 1
        if len(processed_ratings) >= 20:
            excellent_conditions += 1
        
        # 检查趋势
        if len(processed_ratings) >= 5:
            try:
                total_change = processed_ratings[-1] - processed_ratings[0]
                if total_change > 0.4:  # 从0.5放宽到0.4 ✓
                    excellent_conditions += 1
            except:
                pass
        
        if excellent_conditions >= 4:
            bonus_points += 5
        elif excellent_conditions >= 3:
            bonus_points += 3
        elif excellent_conditions >= 2:
            bonus_points += 1
        
        # 最终得分
        final_score = base_score + bonus_points
        
        return max(0, min(final_score, 100))
    
    def _apply_quality_adjustment(self, 
                                optimized_score: float,
                                interpolation_quality: float) -> float:
        """方案C：根据数据质量调整分值（进一步降低惩罚）"""
        
        # ===== 改进5: 进一步降低质量惩罚 =====
        if interpolation_quality >= 0.9:
            adjustment_factor = 1.0
        elif interpolation_quality >= 0.75:
            adjustment_factor = 0.98    # 从0.95提高到0.98 ✓
        elif interpolation_quality >= 0.6:
            adjustment_factor = 0.96    # 从0.9提高到0.96 ✓
        elif interpolation_quality >= 0.4:
            adjustment_factor = 0.94    # 从0.8提高到0.94 ✓
        else:
            adjustment_factor = 0.90    # 从0.7提高到0.90 ✓
        
        # 应用调整
        adjusted_score = optimized_score * adjustment_factor
        
        # 优化低分保障
        if interpolation_quality >= 0.6:
            min_score = max(optimized_score * 0.03, 0)  # 从5%降低到3% ✓
        else:
            min_score = 0
        
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
