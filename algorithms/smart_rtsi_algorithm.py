#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能RTSI算法
实现自动切换机制：有量价数据时使用"增强RTSI"，无量价数据时使用"RTSI"

功能特性：
1. 智能算法选择：根据数据可用性自动切换
2. 量价增强RTSI：结合评级数据和量价数据
3. 双向插值RTSI：高效的基础算法
4. 统一接口：对外提供一致的调用方式
5. 性能优化：缓存机制和快速处理

作者: AI Assistant
版本: 1.0.0
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from scipy import stats
import threading
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 导入量价数据缓存管理器
try:
    from cache.volume_price_cache import get_cache_manager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("Warning: Volume price cache not available")

logger = logging.getLogger(__name__)

class SmartRTSICalculator:
    """智能RTSI计算器"""
    
    def __init__(self, enable_cache: bool = True, verbose: bool = False):
        """
        初始化智能RTSI计算器
        
        Args:
            enable_cache: 是否启用缓存
            verbose: 是否输出详细日志
        """
        self.enable_cache = enable_cache
        self.verbose = verbose
        self._lock = threading.RLock()
        
        # 算法统计
        self.stats = {
            'total_calculations': 0,
            'enhanced_rtsi_used': 0,
            'basic_rtsi_used': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'volume_data_available': 0,
            'volume_data_unavailable': 0
        }
        
        # 评级映射
        self.rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '中性': 3, '-': 3,
            '微空': 2, '小空': 1, '中空': 1, '大空': 0,
            # 英文映射
            'strong_buy': 7, 'buy': 6, 'weak_buy': 5, 'slight_buy': 4,
            'neutral': 3, 'hold': 3,
            'slight_sell': 2, 'weak_sell': 1, 'sell': 1, 'strong_sell': 0
        }
        
        # 初始化量价数据管理器
        if CACHE_AVAILABLE and enable_cache:
            try:
                self.volume_cache = get_cache_manager(verbose=verbose)
            except Exception as e:
                logger.warning(f"量价缓存初始化失败: {e}")
                self.volume_cache = None
        else:
            self.volume_cache = None
    
    def calculate_smart_rtsi(self, stock_data: Dict[str, Any], 
                           market: str = 'cn', 
                           stock_code: str = None) -> Dict[str, Union[float, str, int]]:
        """
        智能RTSI计算主入口
        
        Args:
            stock_data: 股票数据，包含评级信息
            market: 市场类型 ('cn', 'hk', 'us')
            stock_code: 股票代码
            
        Returns:
            Dict: 计算结果
        """
        with self._lock:
            self.stats['total_calculations'] += 1
            calculation_start = datetime.now()
            
            try:
                # 提取基础信息
                if stock_code is None:
                    stock_code = stock_data.get('code', stock_data.get('股票代码', 'unknown'))
                
                stock_name = stock_data.get('name', stock_data.get('股票名称', ''))
                
                # 检查是否有量价数据
                volume_data = self._get_volume_price_data(stock_code, market)
                
                if volume_data is not None:
                    # 使用增强RTSI算法
                    self.stats['enhanced_rtsi_used'] += 1
                    self.stats['volume_data_available'] += 1
                    result = self._calculate_enhanced_rtsi(stock_data, volume_data, stock_code, stock_name)
                    result['algorithm'] = '增强RTSI'
                else:
                    # 使用基础RTSI算法
                    self.stats['basic_rtsi_used'] += 1
                    self.stats['volume_data_unavailable'] += 1
                    result = self._calculate_basic_rtsi(stock_data, stock_code, stock_name)
                    result['algorithm'] = 'RTSI'
                
                # 添加计算时间
                calc_time = (datetime.now() - calculation_start).total_seconds()
                result['calculation_time'] = f"{calc_time:.3f}s"
                
                return result
                
            except Exception as e:
                logger.error(f"智能RTSI计算失败 {stock_code}: {e}")
                return self._get_error_result(stock_code, str(e))
    
    def _get_volume_price_data(self, stock_code: str, market: str) -> Optional[Dict[str, Any]]:
        """获取量价数据"""
        if not self.volume_cache:
            return None
        
        try:
            # 尝试获取5天的量价数据
            volume_data = self.volume_cache.get_volume_price_data(stock_code, market, days=5)
            
            if volume_data and volume_data.get('total_days', 0) > 0:
                return volume_data
            else:
                return None
                
        except Exception as e:
            if self.verbose:
                logger.debug(f"获取量价数据失败 {stock_code}: {e}")
            return None
    
    def _calculate_enhanced_rtsi(self, stock_data: Dict[str, Any], 
                               volume_data: Dict[str, Any],
                               stock_code: str, 
                               stock_name: str) -> Dict[str, Union[float, str, int]]:
        """
        计算增强RTSI（量价增强版本）
        
        结合评级数据和量价数据，提供更准确的评估
        """
        try:
            # 1. 计算基础评级得分
            base_rtsi = self._calculate_rating_component(stock_data)
            
            # 2. 计算量价增强因子
            price_momentum = self._calculate_price_momentum(volume_data)
            volume_momentum = self._calculate_volume_momentum(volume_data)
            volatility_factor = self._calculate_volatility_factor(volume_data)
            
            # 3. 量价综合得分
            volume_price_score = (
                price_momentum * 0.50 +      # 价格动量权重50%
                volume_momentum * 0.35 +     # 成交量动量权重35%
                volatility_factor * 0.15     # 波动率因子权重15%
            )
            
            # 4. 综合RTSI计算
            # 基础评级权重70%，量价因子权重30%
            enhanced_rtsi = base_rtsi * 0.70 + volume_price_score * 0.30
            
            # 5. 范围限制
            enhanced_rtsi = max(0, min(100, enhanced_rtsi))
            
            # 6. 趋势判断
            trend = self._determine_enhanced_trend(base_rtsi, price_momentum, volume_momentum)
            
            # 7. 信心度计算
            confidence = self._calculate_enhanced_confidence(volume_data, stock_data)
            
            return {
                'rtsi': round(enhanced_rtsi, 2),
                'trend': trend,
                'confidence': round(confidence, 2),
                'base_rating_score': round(base_rtsi, 2),
                'price_momentum': round(price_momentum, 2),
                'volume_momentum': round(volume_momentum, 2),
                'volatility_factor': round(volatility_factor, 2),
                'volume_price_score': round(volume_price_score, 2),
                'stock_code': stock_code,
                'stock_name': stock_name,
                'data_source': '评级+量价数据',
                'volume_days': volume_data.get('total_days', 0)
            }
            
        except Exception as e:
            logger.error(f"增强RTSI计算失败 {stock_code}: {e}")
            # 回退到基础算法
            return self._calculate_basic_rtsi(stock_data, stock_code, stock_name)
    
    def _calculate_basic_rtsi(self, stock_data: Dict[str, Any],
                            stock_code: str, 
                            stock_name: str) -> Dict[str, Union[float, str, int]]:
        """
        计算基础RTSI（双向插值版本）
        
        基于评级数据，使用双向插值提供快速准确的评估
        """
        try:
            # 1. 提取评级数据
            ratings = self._extract_ratings(stock_data)
            
            if len(ratings) < 2:
                return self._get_insufficient_data_result(stock_code, stock_name, len(ratings))
            
            # 2. 转换为数值
            numeric_ratings = self._convert_ratings_to_numeric(ratings)
            
            # 3. 双向插值处理
            interpolated_ratings = self._bidirectional_interpolate(numeric_ratings)
            
            # 4. 计算RTSI
            rtsi = self._calculate_rtsi_from_ratings(interpolated_ratings)
            
            # 5. 趋势分析
            trend = self._determine_basic_trend(interpolated_ratings)
            
            # 6. 信心度计算
            confidence = self._calculate_basic_confidence(interpolated_ratings, ratings)
            
            return {
                'rtsi': round(rtsi, 2),
                'trend': trend,
                'confidence': round(confidence, 2),
                'stock_code': stock_code,
                'stock_name': stock_name,
                'data_source': '评级数据',
                'rating_count': len(ratings),
                'interpolated_count': len(interpolated_ratings)
            }
            
        except Exception as e:
            logger.error(f"基础RTSI计算失败 {stock_code}: {e}")
            return self._get_error_result(stock_code, str(e))
    
    def _extract_ratings(self, stock_data: Dict[str, Any]) -> List[str]:
        """从股票数据中提取评级"""
        ratings = []
        
        # 尝试不同的数据格式
        if 'ratings' in stock_data:
            # 已处理的评级列表
            ratings = stock_data['ratings']
        else:
            # 从日期字段提取
            for key, value in stock_data.items():
                if key.startswith('202') and len(key) == 8:  # 日期格式 YYYYMMDD
                    ratings.append(str(value))
        
        # 过滤空值和无效值
        valid_ratings = []
        for rating in ratings:
            if rating and rating.strip() and rating.strip() != 'nan':
                valid_ratings.append(rating.strip())
        
        return valid_ratings[:38]  # 最多取38天
    
    def _convert_ratings_to_numeric(self, ratings: List[str]) -> List[float]:
        """将评级转换为数值"""
        numeric_ratings = []
        
        for rating in ratings:
            rating_str = str(rating).strip()
            if rating_str in self.rating_map:
                numeric_ratings.append(float(self.rating_map[rating_str]))
            else:
                # 尝试直接转换为数字
                try:
                    num_val = float(rating_str)
                    if 0 <= num_val <= 7:
                        numeric_ratings.append(num_val)
                    else:
                        numeric_ratings.append(3.0)  # 默认中性
                except ValueError:
                    numeric_ratings.append(3.0)  # 默认中性
        
        return numeric_ratings
    
    def _bidirectional_interpolate(self, ratings: List[float]) -> List[float]:
        """双向插值算法"""
        if len(ratings) <= 2:
            return ratings
        
        # 前向填充
        forward_filled = self._forward_fill(ratings)
        
        # 后向填充
        backward_filled = self._backward_fill(ratings)
        
        # 结合两种插值结果
        result = []
        for i, original in enumerate(ratings):
            if original != 0 and not np.isnan(original):  # 有效评级
                result.append(original)
            else:
                # 取前向和后向插值的平均
                forward_val = forward_filled[i] if i < len(forward_filled) else 3.0
                backward_val = backward_filled[i] if i < len(backward_filled) else 3.0
                result.append((forward_val + backward_val) / 2)
        
        return result
    
    def _forward_fill(self, ratings: List[float]) -> List[float]:
        """前向填充"""
        result = ratings.copy()
        last_valid = 3.0  # 默认中性
        
        for i in range(len(result)):
            if result[i] != 0 and not np.isnan(result[i]):
                last_valid = result[i]
            else:
                result[i] = last_valid
        
        return result
    
    def _backward_fill(self, ratings: List[float]) -> List[float]:
        """后向填充"""
        result = ratings.copy()
        next_valid = 3.0  # 默认中性
        
        for i in range(len(result) - 1, -1, -1):
            if result[i] != 0 and not np.isnan(result[i]):
                next_valid = result[i]
            else:
                result[i] = next_valid
        
        return result
    
    def _calculate_rating_component(self, stock_data: Dict[str, Any]) -> float:
        """计算评级组件得分"""
        ratings = self._extract_ratings(stock_data)
        if not ratings:
            return 50.0
        
        numeric_ratings = self._convert_ratings_to_numeric(ratings)
        interpolated_ratings = self._bidirectional_interpolate(numeric_ratings)
        
        return self._calculate_rtsi_from_ratings(interpolated_ratings)
    
    def _calculate_rtsi_from_ratings(self, ratings: List[float]) -> float:
        """从评级列表计算RTSI"""
        if not ratings:
            return 0.0
        
        try:
            # 线性回归分析
            x = np.arange(len(ratings))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, ratings)
            
            # 计算核心指标
            consistency = r_value ** 2  # 一致性 (R²值)
            significance = max(0, 1 - p_value) if p_value < 0.1 else 0  # 显著性
            
            # 变化幅度
            rating_scale_max = 7
            amplitude = abs(slope) * len(ratings) / rating_scale_max
            amplitude = min(amplitude, 1.0)
            
            # 加权平均，近期权重更高
            weights = np.exp(np.linspace(-1, 0, len(ratings)))
            weighted_avg = np.average(ratings, weights=weights)
            
            # 综合RTSI计算
            rtsi = (
                consistency * 0.35 +      # 一致性权重35%
                significance * 0.25 +     # 显著性权重25%
                amplitude * 0.20 +        # 幅度权重20%
                (weighted_avg / 7) * 0.20 # 当前水平权重20%
            ) * 100
            
            # 基础分数保障
            if rtsi < 5 and (consistency > 0.1 or amplitude > 0.1):
                rtsi = 5
            
            return max(0, min(100, rtsi))
            
        except Exception as e:
            logger.warning(f"RTSI计算失败: {e}")
            return np.mean(ratings) / 7 * 100 if ratings else 0.0
    
    def _calculate_price_momentum(self, volume_data: Dict[str, Any]) -> float:
        """计算价格动量"""
        try:
            data_list = volume_data.get('data', [])
            if len(data_list) < 2:
                return 50.0
            
            prices = [day['close_price'] for day in data_list if day.get('close_price', 0) > 0]
            if len(prices) < 2:
                return 50.0
            
            # 计算价格变化率
            price_changes = []
            for i in range(len(prices) - 1):
                change_rate = (prices[i] - prices[i + 1]) / prices[i + 1] * 100
                price_changes.append(change_rate)
            
            if not price_changes:
                return 50.0
            
            # 动量得分
            avg_change = np.mean(price_changes)
            momentum_score = 50 + avg_change * 2  # 调整系数
            
            return max(0, min(100, momentum_score))
            
        except Exception:
            return 50.0
    
    def _calculate_volume_momentum(self, volume_data: Dict[str, Any]) -> float:
        """计算成交量动量"""
        try:
            data_list = volume_data.get('data', [])
            if len(data_list) < 2:
                return 50.0
            
            volumes = [day['volume'] for day in data_list if day.get('volume', 0) > 0]
            if len(volumes) < 2:
                return 50.0
            
            # 计算成交量变化率
            volume_changes = []
            for i in range(len(volumes) - 1):
                change_rate = (volumes[i] - volumes[i + 1]) / volumes[i + 1] * 100
                volume_changes.append(change_rate)
            
            if not volume_changes:
                return 50.0
            
            # 动量得分
            avg_change = np.mean(volume_changes)
            momentum_score = 50 + avg_change * 0.5  # 成交量变化较大，使用较小系数
            
            return max(0, min(100, momentum_score))
            
        except Exception:
            return 50.0
    
    def _calculate_volatility_factor(self, volume_data: Dict[str, Any]) -> float:
        """计算波动率因子"""
        try:
            data_list = volume_data.get('data', [])
            if len(data_list) < 3:
                return 50.0
            
            prices = [day['close_price'] for day in data_list if day.get('close_price', 0) > 0]
            if len(prices) < 3:
                return 50.0
            
            # 计算价格波动率
            returns = []
            for i in range(len(prices) - 1):
                return_rate = (prices[i] - prices[i + 1]) / prices[i + 1]
                returns.append(return_rate)
            
            if not returns:
                return 50.0
            
            volatility = np.std(returns) * 100
            
            # 波动率转换为得分（低波动率得分高）
            volatility_score = max(0, 100 - volatility * 10)
            return min(100, volatility_score)
            
        except Exception:
            return 50.0
    
    def _determine_enhanced_trend(self, base_rtsi: float, 
                                price_momentum: float, 
                                volume_momentum: float) -> str:
        """确定增强趋势"""
        combined_momentum = (price_momentum + volume_momentum) / 2
        
        if base_rtsi >= 70 and combined_momentum >= 60:
            return 'strong_upward'
        elif base_rtsi >= 60 and combined_momentum >= 55:
            return 'upward'
        elif base_rtsi <= 30 and combined_momentum <= 40:
            return 'strong_downward'
        elif base_rtsi <= 40 and combined_momentum <= 45:
            return 'downward'
        else:
            return 'sideways'
    
    def _determine_basic_trend(self, ratings: List[float]) -> str:
        """确定基础趋势"""
        if len(ratings) < 3:
            return 'unclear'
        
        try:
            x = np.arange(len(ratings))
            slope, _, _, p_value, _ = stats.linregress(x, ratings)
            
            if p_value > 0.1:
                return 'unclear'
            elif slope > 0.1:
                return 'upward'
            elif slope < -0.1:
                return 'downward'
            else:
                return 'sideways'
                
        except Exception:
            return 'unclear'
    
    def _calculate_enhanced_confidence(self, volume_data: Dict[str, Any], 
                                     stock_data: Dict[str, Any]) -> float:
        """计算增强信心度"""
        confidence = 60.0  # 基础信心度
        
        # 量价数据质量加分
        volume_days = volume_data.get('total_days', 0)
        if volume_days >= 5:
            confidence += 20
        elif volume_days >= 3:
            confidence += 10
        
        # 评级数据质量加分
        ratings = self._extract_ratings(stock_data)
        if len(ratings) >= 10:
            confidence += 15
        elif len(ratings) >= 5:
            confidence += 10
        
        # 数据一致性加分
        try:
            numeric_ratings = self._convert_ratings_to_numeric(ratings)
            if len(numeric_ratings) >= 3:
                x = np.arange(len(numeric_ratings))
                _, _, r_value, _, _ = stats.linregress(x, numeric_ratings)
                confidence += (r_value ** 2) * 10
        except Exception:
            pass
        
        return min(100, confidence)
    
    def _calculate_basic_confidence(self, ratings: List[float], 
                                  original_ratings: List[str]) -> float:
        """计算基础信心度"""
        confidence = 50.0  # 基础信心度
        
        # 数据数量加分
        if len(original_ratings) >= 15:
            confidence += 25
        elif len(original_ratings) >= 10:
            confidence += 20
        elif len(original_ratings) >= 5:
            confidence += 15
        
        # 数据质量加分
        try:
            if len(ratings) >= 3:
                x = np.arange(len(ratings))
                _, _, r_value, p_value, _ = stats.linregress(x, ratings)
                
                # R²值加分
                confidence += (r_value ** 2) * 15
                
                # 显著性加分
                if p_value < 0.05:
                    confidence += 10
                elif p_value < 0.1:
                    confidence += 5
        except Exception:
            pass
        
        return min(100, confidence)
    
    def _get_insufficient_data_result(self, stock_code: str, stock_name: str, 
                                    data_count: int) -> Dict[str, Union[float, str, int]]:
        """获取数据不足时的结果"""
        return {
            'rtsi': 0.0,
            'trend': 'insufficient_data',
            'confidence': 0.0,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'data_source': '数据不足',
            'rating_count': data_count,
            'error': f'评级数据不足: {data_count} < 2'
        }
    
    def _get_error_result(self, stock_code: str, error_msg: str) -> Dict[str, Union[float, str, int]]:
        """获取错误结果"""
        return {
            'rtsi': 0.0,
            'trend': 'error',
            'confidence': 0.0,
            'stock_code': stock_code,
            'stock_name': '',
            'data_source': '计算错误',
            'error': error_msg
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取算法统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        for key in self.stats:
            self.stats[key] = 0


# 全局智能RTSI计算器实例
_global_smart_calculator = None

def get_smart_rtsi_calculator(enable_cache: bool = True, verbose: bool = False) -> SmartRTSICalculator:
    """获取全局智能RTSI计算器实例（单例模式）"""
    global _global_smart_calculator
    if _global_smart_calculator is None:
        _global_smart_calculator = SmartRTSICalculator(enable_cache=enable_cache, verbose=verbose)
    return _global_smart_calculator


def calculate_smart_rtsi(stock_data: Dict[str, Any], 
                        market: str = 'cn', 
                        stock_code: str = None) -> Dict[str, Union[float, str, int]]:
    """
    智能RTSI计算函数 - 便捷入口
    
    Args:
        stock_data: 股票数据
        market: 市场类型
        stock_code: 股票代码
        
    Returns:
        Dict: RTSI计算结果
    """
    calculator = get_smart_rtsi_calculator()
    return calculator.calculate_smart_rtsi(stock_data, market, stock_code)


if __name__ == "__main__":
    # 测试代码
    print("=== 智能RTSI算法测试 ===\n")
    
    # 测试数据
    test_stock = {
        'code': '000001',
        'name': '平安银行',
        'ratings': ['买入', '优势', '中性', '弱势', '中性', '优势', '买入']
    }
    
    calculator = SmartRTSICalculator(verbose=True)
    result = calculator.calculate_smart_rtsi(test_stock, market='cn', stock_code='000001')
    
    print("计算结果:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    print(f"\n算法统计:")
    stats = calculator.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
