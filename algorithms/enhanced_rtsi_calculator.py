#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强RTSI计算器模块
基于优化测试结果，集成最佳参数配置的高性能RTSI计算器

作者: 267278466@qq.com
创建时间: 2025-08-20
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime

# 导入基础RTSI计算器
from .rtsi_calculator import calculate_rating_trend_strength_index
from config import RTSI_CONFIG

# 导入国际化配置
try:
    from config.i18n import t_rtsi, t_common
except ImportError:
    def t_rtsi(key): return key
    def t_common(key): return key


class EnhancedRTSICalculator:
    """
    增强RTSI计算器
    使用优化测试得出的最佳参数配置
    """
    
    def __init__(self, 
                 rtsi_threshold: float = None,
                 volatility_threshold: float = None,
                 trend_strength_threshold: float = None,
                 use_ai_enhancement: bool = None,
                 use_multi_dimensional: bool = None,
                 time_window: int = None):
        """
        初始化增强RTSI计算器
        
        Args:
            rtsi_threshold: RTSI筛选阈值，默认使用配置文件中的最佳值
            volatility_threshold: 波动性调整阈值
            trend_strength_threshold: 趋势强度阈值
            use_ai_enhancement: 是否启用AI增强
            use_multi_dimensional: 是否启用多维度分析
            time_window: 时间窗口大小（天数）
        """
        # 使用配置文件中的最佳参数或传入参数
        self.rtsi_threshold = rtsi_threshold if rtsi_threshold is not None else RTSI_CONFIG.get('rtsi_threshold', 0.4)
        self.volatility_threshold = volatility_threshold if volatility_threshold is not None else RTSI_CONFIG.get('volatility_threshold', 0.2)
        self.trend_strength_threshold = trend_strength_threshold if trend_strength_threshold is not None else RTSI_CONFIG.get('trend_strength_threshold', 0.6)
        self.use_ai_enhancement = use_ai_enhancement if use_ai_enhancement is not None else RTSI_CONFIG.get('use_ai_enhancement', True)
        self.use_multi_dimensional = use_multi_dimensional if use_multi_dimensional is not None else RTSI_CONFIG.get('use_multi_dimensional', False)
        self.time_window = time_window if time_window is not None else RTSI_CONFIG.get('time_window', 60)
        
        # 中文评级映射（根据实际数据格式）
        self.rating_map = {
            '大多': 5, '中多': 4, '小多': 3, '微多': 2,
            '中性': 2.5, '观望': 2.5, '持有': 2.5,
            '微空': 2, '小空': 1, '中空': 1, '大空': 0,
            '强烈推荐': 5, '推荐': 4, '买入': 4, '强烈买入': 5,
            '减持': 1, '卖出': 0, '强烈卖出': 0
        }
        
        # 插值质量记录
        self.last_interpolation_quality = 0.0
        self.last_interpolation_strategy = 'unknown'
        
        print(f"🚀 增强RTSI计算器初始化完成")
        print(f"📊 配置参数: RTSI阈值={self.rtsi_threshold}, 波动性阈值={self.volatility_threshold}")
        print(f"🎯 AI增强={self.use_ai_enhancement}, 多维度={self.use_multi_dimensional}, 时间窗口={self.time_window}天")
    
    def preprocess_stock_ratings(self, stock_data: pd.Series, date_columns: List[str]) -> List[float]:
        """
        预处理股票评级数据（支持双向插值）
        
        Args:
            stock_data: 单只股票的数据行
            date_columns: 日期列名列表
            
        Returns:
            处理后的评级数值列表
        """
        # 应用时间窗口限制
        limited_date_cols = date_columns
        if len(date_columns) > self.time_window:
            limited_date_cols = sorted(date_columns)[-self.time_window:]
        
        # 第一步：收集原始评级数据（保持None表示缺失）
        raw_ratings = []
        for col in limited_date_cols:
            rating_str = str(stock_data[col]).strip()
            if rating_str and rating_str != 'nan' and rating_str != '' and rating_str != '-':
                # 使用评级映射转换
                if rating_str in self.rating_map:
                    raw_ratings.append(self.rating_map[rating_str])
                else:
                    # 尝试数字转换
                    try:
                        rating_num = float(rating_str)
                        if 0 <= rating_num <= 5:
                            raw_ratings.append(rating_num)
                        else:
                            raw_ratings.append(None)  # 无效数字，标记为缺失
                    except:
                        raw_ratings.append(None)  # 转换失败，标记为缺失
            else:
                raw_ratings.append(None)  # 缺失值
        
        # 第二步：应用自适应插值
        return self._apply_adaptive_interpolation(raw_ratings, date_columns)
    
    def _apply_bidirectional_interpolation(self, raw_ratings: List[Optional[float]]) -> List[float]:
        """
        对评级数据应用双向插值
        
        Args:
            raw_ratings: 原始评级列表（包含None表示缺失）
            
        Returns:
            插值后的评级列表
        """
        if len(raw_ratings) <= 2:
            # 数据太少，只返回有效值
            return [r for r in raw_ratings if r is not None]
        
        # 前向填充
        forward_filled = []
        last_valid = 3.0  # 默认中性评级
        for rating in raw_ratings:
            if rating is not None:
                last_valid = rating
                forward_filled.append(rating)
            else:
                forward_filled.append(last_valid)
        
        # 后向填充
        backward_filled = [None] * len(raw_ratings)
        next_valid = 3.0  # 默认中性评级
        for i in range(len(raw_ratings) - 1, -1, -1):
            if raw_ratings[i] is not None:
                next_valid = raw_ratings[i]
                backward_filled[i] = raw_ratings[i]
            else:
                backward_filled[i] = next_valid
        
        # 双向插值：取前向和后向的平均值
        result = []
        for i, original in enumerate(raw_ratings):
            if original is not None:
                result.append(original)
            else:
                # 取前向和后向插值的平均
                interpolated = (forward_filled[i] + backward_filled[i]) / 2
                result.append(interpolated)
        
        return result
    
    def _apply_adaptive_interpolation(self, raw_ratings: List[Optional[float]], date_columns: List[str]) -> List[float]:
        """
        对评级数据应用自适应插值
        
        Args:
            raw_ratings: 原始评级列表（包含None表示缺失）
            date_columns: 日期列名列表
            
        Returns:
            插值后的评级列表
        """
        try:
            from algorithms.adaptive_interpolation import AdaptiveInterpolationEngine
            
            # 创建pandas Series用于自适应插值
            ratings_series = pd.Series(
                [r if r is not None else '-' for r in raw_ratings],
                index=date_columns[:len(raw_ratings)]
            )
            
            # 使用自适应插值引擎
            adaptive_engine = AdaptiveInterpolationEngine()
            interpolation_result = adaptive_engine.interpolate_rating_series(
                ratings_series=ratings_series,
                stock_info={'code': 'enhanced_rtsi', 'type': 'enhanced'},
                market_context=None
            )
            
            # 提取插值结果
            interpolated_series = interpolation_result['interpolated_series']
            self.last_interpolation_quality = interpolation_result.get('interpolation_quality', 0)
            self.last_interpolation_strategy = interpolation_result.get('strategy_used', 'unknown')
            
            # 转换为数值列表
            result = []
            for value in interpolated_series:
                try:
                    if isinstance(value, (int, float)):
                        result.append(float(value))
                    else:
                        # 处理字符串评级
                        if str(value) in self.rating_map:
                            result.append(self.rating_map[str(value)])
                        else:
                            result.append(3.0)  # 默认中性值
                except:
                    result.append(3.0)  # 默认中性值
            
            return result
            
        except Exception as e:
            print(f"⚠️ 自适应插值失败，回退到双向插值: {e}")
            # 回退到双向插值
            return self._apply_bidirectional_interpolation(raw_ratings)
    
    def calculate_enhanced_rtsi(self, ratings: List[float], stock_code: str = "", stock_name: str = "") -> Optional[float]:
        """
        计算增强版RTSI
        
        Args:
            ratings: 评级数值列表
            stock_code: 股票代码（用于日志）
            stock_name: 股票名称（用于日志）
            
        Returns:
            增强后的RTSI分数（0-1范围），失败时返回None
        """
        try:
            if len(ratings) < 10:  # 需要足够的数据点
                return None
            
            # 基础RTSI计算
            ratings_series = pd.Series(ratings)
            rtsi_result = calculate_rating_trend_strength_index(ratings_series)
            base_rtsi = rtsi_result.get('rtsi', 0) if rtsi_result else 0
            
            if base_rtsi is None or base_rtsi == 0:
                return None
            
            # 将RTSI分数归一化到0-1范围
            enhanced_rtsi = base_rtsi / 100.0
            
            # 应用多维度分析增强
            if self.use_multi_dimensional:
                try:
                    # 计算波动性调整
                    volatility = np.std(ratings) / np.mean(ratings) if np.mean(ratings) > 0 else 0
                    volatility_factor = 1.0
                    
                    if volatility > self.volatility_threshold:
                        volatility_factor = 0.8  # 高波动性降权
                    elif volatility < self.volatility_threshold / 2:
                        volatility_factor = 1.2  # 低波动性增权
                    
                    enhanced_rtsi *= volatility_factor
                    
                    # 计算趋势强度调整
                    if len(ratings) >= 20:
                        recent_trend = np.polyfit(range(len(ratings[-20:])), ratings[-20:], 1)[0]
                        trend_strength = abs(recent_trend)
                        
                        if trend_strength > self.trend_strength_threshold:
                            trend_factor = 1.1  # 强趋势增权
                        else:
                            trend_factor = 0.95  # 弱趋势略降权
                        
                        enhanced_rtsi *= trend_factor
                
                except Exception as e:
                    pass  # 如果多维度分析失败，使用基础RTSI
            
            # 应用AI增强
            if self.use_ai_enhancement:
                try:
                    # 简化的AI增强逻辑
                    rating_changes = np.diff(ratings)
                    if len(rating_changes) > 0:
                        momentum = np.mean(rating_changes[-10:]) if len(rating_changes) >= 10 else np.mean(rating_changes)
                        consistency = 1 / (1 + np.std(rating_changes))
                        
                        ai_factor = 1 + (momentum * consistency * 0.1)
                        enhanced_rtsi *= ai_factor
                
                except Exception as e:
                    pass  # 如果AI增强失败，使用多维度增强或基础RTSI
            
            # 应用阈值过滤
            if enhanced_rtsi < self.rtsi_threshold:
                enhanced_rtsi *= 0.8  # 低于阈值的RTSI降权
            
            return min(enhanced_rtsi, 1.0)  # 限制最大值为1.0
            
        except Exception as e:
            return None
    
    def batch_calculate_enhanced_rtsi(self, stock_data: pd.DataFrame, use_optimized: bool = True) -> Dict[str, Dict]:
        """
        批量计算增强RTSI
        
        Args:
            stock_data: 股票数据DataFrame
            
        Returns:
            股票代码到RTSI结果的映射字典
        """
        results = {}
        
        # 获取日期列
        date_cols = [col for col in stock_data.columns if str(col).startswith('202')]
        if not date_cols:
            return results
        
        successful_count = 0
        failed_count = 0
        
        for idx, stock in stock_data.iterrows():
            try:
                stock_code = str(stock.get('股票代码', ''))
                stock_name = str(stock.get('股票名称', ''))
                
                if not stock_code:
                    continue
                
                # 优先使用优化增强RTSI
                if use_optimized:
                    try:
                        from algorithms.optimized_enhanced_rtsi import calculate_optimized_enhanced_rtsi
                        optimized_result = calculate_optimized_enhanced_rtsi(
                            stock, date_cols, stock_code, stock_name
                        )
                        if optimized_result and optimized_result.get('rtsi', 0) > 0:
                            results[stock_code] = optimized_result
                            successful_count += 1
                            continue
                    except Exception as e:
                        # 优化算法失败，回退到原版
                        pass
                
                # 回退到原始增强RTSI
                # 预处理评级数据
                ratings = self.preprocess_stock_ratings(stock, date_cols)
                
                if len(ratings) < 10:
                    failed_count += 1
                    continue
                
                # 计算增强RTSI
                enhanced_rtsi = self.calculate_enhanced_rtsi(ratings, stock_code, stock_name)
                
                if enhanced_rtsi is not None:
                    # 获取基础RTSI结果用于详细信息
                    ratings_series = pd.Series(ratings)
                    base_result = calculate_rating_trend_strength_index(ratings_series)
                    
                    # 构建结果
                    results[stock_code] = {
                        'rtsi': enhanced_rtsi * 100,  # 转换为0-100范围以兼容显示
                        'enhanced_rtsi': enhanced_rtsi,
                        'base_rtsi': base_result.get('rtsi', 0) if base_result else 0,
                        'trend': base_result.get('trend', 'unknown') if base_result else 'unknown',
                        'confidence': base_result.get('confidence', 0) if base_result else 0,
                        'algorithm': '增强RTSI',  # 添加算法标识
                        'data_points': len(ratings),
                        'stock_name': stock_name,
                        'rating_range': [min(ratings), max(ratings)],
                        'calculation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    successful_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                continue
        
        # 记录统计信息
        total_count = successful_count + failed_count
        success_rate = successful_count / total_count if total_count > 0 else 0
        
        # 移除终端输出，避免干扰用户界面
        # print(f"📊 批量RTSI计算完成: 成功 {successful_count}, 失败 {failed_count}, 成功率 {success_rate:.1%}")
        
        return results
    
    def get_config_summary(self) -> Dict[str, Union[str, float, bool, int]]:
        """获取当前配置摘要"""
        return {
            'rtsi_threshold': self.rtsi_threshold,
            'volatility_threshold': self.volatility_threshold,
            'trend_strength_threshold': self.trend_strength_threshold,
            'use_ai_enhancement': self.use_ai_enhancement,
            'use_multi_dimensional': self.use_multi_dimensional,
            'time_window': self.time_window,
            'config_version': '2025-08-20_optimized'
        }


def create_enhanced_rtsi_calculator(**kwargs) -> EnhancedRTSICalculator:
    """
    创建增强RTSI计算器实例的便捷函数
    
    Returns:
        配置好的增强RTSI计算器实例
    """
    return EnhancedRTSICalculator(**kwargs)


def calculate_enhanced_rtsi_for_stock(stock_data: pd.Series, date_columns: List[str], **config) -> Optional[Dict]:
    """
    为单只股票计算增强RTSI的便捷函数
    
    Args:
        stock_data: 股票数据行
        date_columns: 日期列名列表
        **config: 可选的配置参数
        
    Returns:
        RTSI计算结果字典，失败时返回None
    """
    calculator = EnhancedRTSICalculator(**config)
    
    stock_code = str(stock_data.get('股票代码', ''))
    stock_name = str(stock_data.get('股票名称', ''))
    
    ratings = calculator.preprocess_stock_ratings(stock_data, date_columns)
    if len(ratings) < 10:
        return None
    
    enhanced_rtsi = calculator.calculate_enhanced_rtsi(ratings, stock_code, stock_name)
    if enhanced_rtsi is None:
        return None
    
    # 获取基础RTSI结果
    ratings_series = pd.Series(ratings)
    base_result = calculate_rating_trend_strength_index(ratings_series)
    
    return {
        'enhanced_rtsi': enhanced_rtsi,
        'base_rtsi': base_result.get('rtsi', 0) if base_result else 0,
        'trend': base_result.get('trend', 'unknown') if base_result else 'unknown',
        'confidence': base_result.get('confidence', 0) if base_result else 0,
        'data_points': len(ratings),
        'stock_code': stock_code,
        'stock_name': stock_name,
        'rating_range': [min(ratings), max(ratings)],
        'calculation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == "__main__":
    # 测试代码
    print("🧪 增强RTSI计算器测试")
    
    # 创建测试数据
    test_ratings = [2, 2, 2, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 5, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2]
    
    # 创建计算器
    calculator = create_enhanced_rtsi_calculator()
    
    # 测试计算
    result = calculator.calculate_enhanced_rtsi(test_ratings, "000001", "测试股票")
    
    print(f"测试结果: {result}")
    print(f"配置摘要: {calculator.get_config_summary()}")

