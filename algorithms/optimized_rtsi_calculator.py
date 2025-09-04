#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的RTSI算法 - 基于数据分析结果优化
解决RTSI=0过多的问题，提高有效评级的股票数量

优化要点：
1. 降低最小数据点要求：从5个降到3个
2. 改进数据预处理：更好的缺失值处理和插值
3. 调整权重分配：更平衡的权重分布
4. 增加基础分数机制：避免过多的零分
5. 优化显著性判断：更灵活的p值阈值

分析结果：
- 当前5000只股票中41.1%(2057只)RTSI=0
- 其中数据不足导致的有1403只
- 目标：将RTSI>0比例提升到80%以上
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime

# 导入国际化配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.gui_i18n import t_gui as t_rtsi, set_language
except ImportError:
    def t_rtsi(key): return key
    def set_language(lang): pass

warnings.filterwarnings('ignore', category=RuntimeWarning)

class OptimizedRTSICalculator:
    """优化后的RTSI计算器"""
    
    def __init__(self, 
                 min_data_points: int = 3,           # 降低最小数据点要求
                 p_threshold: float = 0.1,           # 放宽显著性阈值
                 weights: List[float] = None,        # 权重分配
                 base_score_enabled: bool = True,    # 启用基础分数
                 interpolation_enabled: bool = True, # 启用智能插值
                 language: str = 'zh_CN'):
        
        self.min_data_points = min_data_points
        self.p_threshold = p_threshold
        self.weights = weights or [0.3, 0.3, 0.4]  # 一致性30% + 显著性30% + 幅度40%
        self.base_score_enabled = base_score_enabled
        self.interpolation_enabled = interpolation_enabled
        self.language = language
        
        # 评级映射表（基于实际数据中的评级值）
        self.rating_map = {
            # 原有的评级
            '大多': 7, '多': 6, '轻多': 5, '中性': 4, '持有': 4,
            '轻空': 3, '空': 2, '大空': 1, 
            # 实际数据中的评级
            '微多': 5, '中多': 6, '大多': 7,
            '微空': 3, '中空': 2, '大空': 1,
            '强买': 7, '买入': 6, '增持': 5, '减持': 3, '卖出': 2, '强卖': 1,
            # 缺失值
            '-': None, '': None, 'nan': None, 'NaN': None, None: None
        }
        
        set_language(language)
        
        # 统计信息
        self.stats = {
            'total_calculations': 0,
            'zero_rtsi_count': 0,
            'improved_count': 0,
            'interpolation_used': 0,
            'base_score_applied': 0
        }
    
    def calculate_optimized_rtsi(self, stock_ratings: pd.Series, 
                               stock_code: str = None) -> Dict[str, Union[float, str, int, None]]:
        """
        计算优化后的RTSI指数
        
        参数:
            stock_ratings (pd.Series): 股票评级序列
            stock_code (str): 股票代码（用于统计）
            
        返回:
            dict: 优化后的RTSI计算结果
        """
        calculation_start = datetime.now()
        self.stats['total_calculations'] += 1
        
        # 1. 数据预处理
        processed_ratings = self._preprocess_ratings(stock_ratings)
        
        if len(processed_ratings) < self.min_data_points:
            self.stats['zero_rtsi_count'] += 1
            return self._get_insufficient_data_result(len(processed_ratings))
        
        try:
            # 2. 线性回归分析
            x = np.arange(len(processed_ratings))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, processed_ratings)
            
            # 3. 三大核心指标计算
            consistency = r_value ** 2  # 一致性 (R²值)
            
            # 优化的显著性计算
            significance = max(0, 1 - p_value) if p_value < self.p_threshold else 0
            
            # 改进的幅度计算
            rating_scale_max = 7
            amplitude = abs(slope) * len(processed_ratings) / rating_scale_max
            amplitude = min(amplitude, 1.0)
            
            # 4. 优化的RTSI计算
            rtsi = (consistency * self.weights[0] + 
                   significance * self.weights[1] + 
                   amplitude * self.weights[2]) * 100
            
            # 5. 基础分数机制
            if self.base_score_enabled and rtsi < 5:
                # 如果有一定的一致性或幅度，给予基础分数
                if consistency > 0.1 or amplitude > 0.1:
                    rtsi = max(rtsi, 5)
                    self.stats['base_score_applied'] += 1
            
            # 6. 趋势方向判断
            trend_direction = self._determine_trend_direction(slope, significance)
            
            # 7. 计算附加指标
            recent_score = int(processed_ratings[-1]) if len(processed_ratings) > 0 else None
            score_change_5d = self._calculate_score_change(processed_ratings, 5)
            
            # 8. 数据质量评估
            original_length = len(stock_ratings)
            interpolation_ratio = (original_length - len(processed_ratings)) / original_length if original_length > 0 else 0
            
            calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
            
            if rtsi > 0:
                self.stats['improved_count'] += 1
            else:
                self.stats['zero_rtsi_count'] += 1
            
            return {
                t_rtsi('rtsi'): round(rtsi, 2),
                t_rtsi('trend'): trend_direction,
                t_rtsi('confidence'): round(significance, 3),
                t_rtsi('slope'): round(slope, 4),
                t_rtsi('r_squared'): round(consistency, 3),
                t_rtsi('recent_score'): recent_score,
                t_rtsi('score_change_5d'): score_change_5d,
                t_rtsi('data_points'): len(processed_ratings),
                t_rtsi('calculation_time'): calculation_time,
                'interpolation_ratio': round(interpolation_ratio, 3),
                'optimization_applied': True,
                'base_score_used': rtsi >= 5 and self.base_score_enabled,
                'algorithm_version': 'OptimizedRTSI_v1.0'
            }
            
        except Exception as e:
            self.stats['zero_rtsi_count'] += 1
            return {
                t_rtsi('rtsi'): 0,
                t_rtsi('trend'): 'calculation_error',
                t_rtsi('confidence'): 0,
                'error': str(e),
                t_rtsi('data_points'): len(processed_ratings),
                'optimization_applied': False
            }
    
    def _preprocess_ratings(self, stock_ratings: pd.Series) -> List[float]:
        """
        优化的数据预处理
        """
        valid_ratings = []
        missing_positions = []
        
        # 第一轮：收集有效数据和缺失位置
        for i, rating in enumerate(stock_ratings):
            if self._is_missing(rating):
                missing_positions.append(i)
            elif str(rating) in self.rating_map:
                score = self.rating_map[str(rating)]
                if score is not None:
                    valid_ratings.append((i, score))
        
        if len(valid_ratings) < self.min_data_points:
            return [item[1] for item in valid_ratings]  # 返回原始有效数据
        
        # 第二轮：智能插值（如果启用）
        if self.interpolation_enabled and missing_positions:
            interpolated_ratings = self._smart_interpolation(valid_ratings, missing_positions, len(stock_ratings))
            self.stats['interpolation_used'] += 1
            return interpolated_ratings
        
        return [item[1] for item in valid_ratings]
    
    def _smart_interpolation(self, valid_ratings: List[Tuple[int, float]], 
                           missing_positions: List[int], 
                           total_length: int) -> List[float]:
        """
        智能插值算法
        """
        if len(valid_ratings) < 2:
            return [item[1] for item in valid_ratings]
        
        # 创建完整序列
        full_sequence = [None] * total_length
        for pos, score in valid_ratings:
            full_sequence[pos] = score
        
        # 线性插值缺失值
        for i in missing_positions:
            # 寻找前后最近的有效值
            left_val, left_pos = None, -1
            right_val, right_pos = None, total_length
            
            # 向左查找
            for j in range(i-1, -1, -1):
                if full_sequence[j] is not None:
                    left_val, left_pos = full_sequence[j], j
                    break
            
            # 向右查找
            for j in range(i+1, total_length):
                if full_sequence[j] is not None:
                    right_val, right_pos = full_sequence[j], j
                    break
            
            # 插值计算
            if left_val is not None and right_val is not None:
                # 线性插值
                weight = (i - left_pos) / (right_pos - left_pos)
                interpolated_value = left_val + weight * (right_val - left_val)
                full_sequence[i] = round(interpolated_value)
            elif left_val is not None:
                # 只有左值，使用左值
                full_sequence[i] = left_val
            elif right_val is not None:
                # 只有右值，使用右值
                full_sequence[i] = right_val
        
        # 过滤掉仍然为None的值
        return [val for val in full_sequence if val is not None]
    
    def _is_missing(self, rating) -> bool:
        """判断是否为缺失值"""
        try:
            return (rating == '-' or 
                   pd.isna(rating) or 
                   str(rating).lower() in ['nan', 'none', '', '<na>'])
        except:
            return True
    
    def _determine_trend_direction(self, slope: float, significance: float) -> str:
        """确定趋势方向"""
        if significance < 0.1:
            return t_rtsi('trend_unclear')
        
        if slope > 0.02:
            return t_rtsi('trend_upward')
        elif slope < -0.02:
            return t_rtsi('trend_downward')
        else:
            return t_rtsi('trend_sideways')
    
    def _calculate_score_change(self, scores: List[float], days: int) -> Optional[float]:
        """计算指定天数的分数变化"""
        if len(scores) < days + 1:
            return None
        
        recent_avg = np.mean(scores[-days:])
        older_avg = np.mean(scores[-days*2:-days]) if len(scores) >= days * 2 else scores[0]
        
        return round(recent_avg - older_avg, 2)
    
    def _get_insufficient_data_result(self, data_points: int = 0) -> Dict:
        """数据不足时的结果"""
        return {
            t_rtsi('rtsi'): 0,
            t_rtsi('trend'): t_rtsi('insufficient_data'),
            t_rtsi('confidence'): 0,
            t_rtsi('slope'): 0,
            t_rtsi('r_squared'): 0,
            t_rtsi('recent_score'): None,
            t_rtsi('score_change_5d'): None,
            t_rtsi('data_points'): data_points,
            'optimization_applied': False,
            'insufficient_data_reason': f'需要至少{self.min_data_points}个数据点，当前只有{data_points}个'
        }
    
    def batch_calculate_optimized(self, stock_data: pd.DataFrame) -> Dict[str, Dict]:
        """
        批量计算优化后的RTSI
        """
        results = {}
        date_columns = [col for col in stock_data.columns if str(col).startswith('202')]
        date_columns.sort()
        
        print(f"使用优化RTSI算法批量计算 {len(stock_data)} 只股票...")
        
        for idx, row in stock_data.iterrows():
            try:
                stock_code = str(row.get('股票代码', f'STOCK_{idx}'))
                stock_name = row.get('股票名称', '')
                ratings = row[date_columns]
                
                rtsi_result = self.calculate_optimized_rtsi(ratings, stock_code)
                
                results[stock_code] = {
                    'name': stock_name,
                    'rtsi_result': rtsi_result,
                    'rtsi_score': rtsi_result.get('rtsi', 0)
                }
                
                if (idx + 1) % 500 == 0:
                    print(f"已完成 {idx + 1}/{len(stock_data)} 只股票")
                    
            except Exception as e:
                print(f"计算股票 {stock_code} 失败: {e}")
        
        return results
    
    def get_optimization_stats(self) -> Dict:
        """获取优化统计信息"""
        total = self.stats['total_calculations']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'zero_rtsi_ratio': self.stats['zero_rtsi_count'] / total,
            'improvement_ratio': self.stats['improved_count'] / total,
            'interpolation_usage_ratio': self.stats['interpolation_used'] / total,
            'base_score_usage_ratio': self.stats['base_score_applied'] / total
        }
    
    def compare_with_original(self, stock_data: pd.DataFrame) -> Dict:
        """
        与原始算法对比测试
        """
        from algorithms.rtsi_calculator import calculate_rating_trend_strength_index
        
        date_columns = [col for col in stock_data.columns if str(col).startswith('202')]
        
        original_zero_count = 0
        optimized_zero_count = 0
        improvement_count = 0
        
        sample_size = min(1000, len(stock_data))  # 采样测试
        sample_data = stock_data.sample(n=sample_size, random_state=42)
        
        print(f"对比测试：采样 {sample_size} 只股票...")
        
        for idx, row in sample_data.iterrows():
            try:
                ratings = row[date_columns]
                
                # 原始算法
                original_result = calculate_rating_trend_strength_index(ratings)
                original_rtsi = original_result.get('rtsi', 0)
                if original_rtsi == 0:
                    original_zero_count += 1
                
                # 优化算法
                optimized_result = self.calculate_optimized_rtsi(ratings)
                optimized_rtsi = optimized_result.get('rtsi', 0)
                if optimized_rtsi == 0:
                    optimized_zero_count += 1
                
                # 改善检查
                if original_rtsi == 0 and optimized_rtsi > 0:
                    improvement_count += 1
                    
            except Exception:
                continue
        
        return {
            'sample_size': sample_size,
            'original_zero_count': original_zero_count,
            'original_zero_ratio': original_zero_count / sample_size,
            'optimized_zero_count': optimized_zero_count,
            'optimized_zero_ratio': optimized_zero_count / sample_size,
            'improvement_count': improvement_count,
            'improvement_ratio': improvement_count / sample_size,
            'relative_improvement': (original_zero_count - optimized_zero_count) / original_zero_count if original_zero_count > 0 else 0
        }


def test_optimized_rtsi():
    """测试优化后的RTSI算法"""
    import gzip
    import json
    
    print("🧪 测试优化后的RTSI算法...")
    
    # 加载测试数据
    try:
        with gzip.open('CN_Data5000.json.gz', 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        stock_data = pd.DataFrame(data['data'])
        print(f"✅ 加载数据成功: {len(stock_data)} 只股票")
        
        # 创建优化计算器
        calculator = OptimizedRTSICalculator()
        
        # 对比测试
        comparison_result = calculator.compare_with_original(stock_data)
        
        print(f"\n📊 对比测试结果:")
        print(f"   采样数量: {comparison_result['sample_size']}")
        print(f"   原始算法RTSI=0: {comparison_result['original_zero_count']} ({comparison_result['original_zero_ratio']:.1%})")
        print(f"   优化算法RTSI=0: {comparison_result['optimized_zero_count']} ({comparison_result['optimized_zero_ratio']:.1%})")
        print(f"   改善股票数量: {comparison_result['improvement_count']}")
        print(f"   相对改善率: {comparison_result['relative_improvement']:.1%}")
        
        # 获取优化统计
        stats = calculator.get_optimization_stats()
        print(f"\n📈 优化统计:")
        print(f"   插值使用率: {stats.get('interpolation_usage_ratio', 0):.1%}")
        print(f"   基础分数应用率: {stats.get('base_score_usage_ratio', 0):.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    test_optimized_rtsi()
