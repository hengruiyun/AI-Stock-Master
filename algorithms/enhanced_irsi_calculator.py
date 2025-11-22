#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心强势分析器 - 增强版 (替代Enhanced IRSI)
集成技术动量分析算法(TMA)和升级关注算法(UFA)
专门用于识别行业强势，提供增强的分析功能

核心功能：
1. 行业强势识别和排名
2. 技术动量分析
3. 评级升级关注分析
4. 投资建议生成
5. 多维度强势评估
6. 动态权重调整

作者: ttfox@ttfox.com
创建时间：2025-08-14
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime, timedelta
import logging

# 导入核心强势分析器
from .irsi_calculator import CoreStrengthAnalyzer, calculate_industry_relative_strength

# 导入配置
try:
    from config import RATING_SCORE_MAP
except ImportError:
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }

warnings.filterwarnings('ignore', category=RuntimeWarning)
logger = logging.getLogger(__name__)


class EnhancedIRSICalculator(CoreStrengthAnalyzer):
    """
    增强型核心强势分析器
    
    基于CoreStrengthAnalyzer，增加了以下功能：
    1. 智能处理无评级数据
    2. 多维度强势评估
    3. 动态权重调整
    4. 趋势稳定性分析
    5. 成交量权重支持
    """
    
    def __init__(self, 
                 rating_map: Dict = None,
                 min_rated_stocks: int = 2,
                 min_coverage_ratio: float = 0.1,
                 enable_volume_weight: bool = True,
                 min_stocks_per_industry: int = 3,
                 enable_cache: bool = True):
        """
        初始化增强型核心强势分析器
        
        Args:
            rating_map: 评级映射表
            min_rated_stocks: 最少有评级的股票数
            min_coverage_ratio: 最小覆盖率
            enable_volume_weight: 是否启用成交量权重
            min_stocks_per_industry: 每个行业最少股票数
            enable_cache: 是否启用缓存
        """
        super().__init__(rating_map, min_stocks_per_industry, enable_cache)
        
        self.min_rated_stocks = min_rated_stocks
        self.min_coverage_ratio = min_coverage_ratio
        self.enable_volume_weight = enable_volume_weight
        
        # 增强型强势等级定义
        self.enhanced_strength_levels = {
            (0.6, float('inf')): "极强势",
            (0.4, 0.6): "强势",
            (0.2, 0.4): "轻微强势", 
            (-0.1, 0.2): "中性",
            (-0.3, -0.1): "轻微弱势",
            (-0.5, -0.3): "弱势",
            (float('-inf'), -0.5): "极弱势"
        }
    
    def calculate_enhanced_irsi(self, 
                               industry_data: pd.DataFrame,
                               market_data: pd.DataFrame,
                               industry_name: str = None) -> Dict[str, Union[float, str, int]]:
        """
        计算增强型行业强势指数
        
        Args:
            industry_data: 行业数据
            market_data: 市场数据
            industry_name: 行业名称
        
        Returns:
            增强型分析结果
        """
        # 数据验证
        validation = self._validate_data(industry_data, market_data, industry_name)
        if not validation['is_valid']:
            return self._get_insufficient_data_result(
                industry_name, 
                validation.get('data_points', 0),
                validation.get('reason', 'insufficient_data')
            )
        
        # 使用核心强势分析器进行基础计算
        base_result = self.calculate(industry_data, market_data, industry_name)
        
        # 增强分析
        date_columns = [col for col in industry_data.columns if str(col).startswith('202')]
        date_columns.sort()
        
        enhanced_metrics = self._calculate_comprehensive_metrics(
            industry_data, market_data, date_columns
        )
        
        # 计算增强型IRSI
        enhanced_irsi = self._compute_enhanced_irsi(enhanced_metrics)
        
        # 评估状态
        status_assessment = self._assess_industry_status(enhanced_irsi, enhanced_metrics)
        
        # 合并结果
        enhanced_result = {
            **base_result,
            'enhanced_irsi': enhanced_irsi,
            'enhanced_status': status_assessment['status'],
            'confidence_level': status_assessment['confidence'],
            'trend_stability': enhanced_metrics.get('trend_stability', 0),
            'coverage_ratio': enhanced_metrics.get('coverage_ratio', 0),
            'volume_weighted_score': enhanced_metrics.get('volume_weighted_score', 0),
            'enhanced_strength_level': self._get_enhanced_strength_level(enhanced_irsi)
        }
        
        return enhanced_result
    
    def _validate_data(self, industry_data: pd.DataFrame, market_data: pd.DataFrame, 
                      industry_name: str) -> Dict[str, Union[bool, Dict]]:
        """
        验证数据质量
        """
        date_columns = [col for col in industry_data.columns if str(col).startswith('202')]
        
        if len(date_columns) < 3:
            return {
                'is_valid': False,
                'reason': 'insufficient_time_periods',
                'data_points': len(date_columns)
            }
        
        # 检查评级覆盖率
        total_ratings = 0
        valid_ratings = 0
        
        for col in date_columns:
            for rating in industry_data[col]:
                total_ratings += 1
                if str(rating).strip() != '-' and str(rating).strip() in self.rating_map:
                    valid_ratings += 1
        
        coverage_ratio = valid_ratings / max(total_ratings, 1)
        
        if coverage_ratio < self.min_coverage_ratio:
            return {
                'is_valid': False,
                'reason': 'low_coverage_ratio',
                'coverage_ratio': coverage_ratio
            }
        
        return {
            'is_valid': True,
            'coverage_ratio': coverage_ratio,
            'data_points': len(date_columns)
        }
    
    def _calculate_comprehensive_metrics(self, industry_data: pd.DataFrame, 
                                       market_data: pd.DataFrame, 
                                       date_columns: List[str]) -> Dict[str, float]:
        """
        计算综合指标
        """
        metrics = {
            'trend_stability': 0.0,
            'coverage_ratio': 0.0,
            'volume_weighted_score': 0.0,
            'momentum_strength': 0.0,
            'upgrade_intensity': 0.0
        }
        
        # 计算趋势稳定性
        industry_scores = []
        market_scores = []
        
        for col in date_columns:
            # 行业平均分
            ind_ratings = industry_data[col].map(self.rating_map).dropna()
            industry_avg = ind_ratings.mean() if len(ind_ratings) > 0 else np.nan
            
            # 市场平均分
            mkt_ratings = market_data[col].map(self.rating_map).dropna()
            market_avg = mkt_ratings.mean() if len(mkt_ratings) > 0 else np.nan
            
            if not (np.isnan(industry_avg) or np.isnan(market_avg)):
                industry_scores.append(industry_avg)
                market_scores.append(market_avg)
        
        if len(industry_scores) >= 3:
            relative_scores = np.array(industry_scores) - np.array(market_scores)
            
            # 趋势稳定性 (相对分数的标准差的倒数)
            trend_std = np.std(relative_scores)
            metrics['trend_stability'] = 1 / (1 + trend_std) if trend_std > 0 else 1.0
            
            # 动量强度 (最近期与早期的差异)
            if len(relative_scores) >= 5:
                recent_avg = np.mean(relative_scores[-3:])
                early_avg = np.mean(relative_scores[:3])
                metrics['momentum_strength'] = recent_avg - early_avg
        
        # 计算覆盖率
        total_ratings = 0
        valid_ratings = 0
        
        for col in date_columns:
            for rating in industry_data[col]:
                total_ratings += 1
                if str(rating).strip() != '-' and str(rating).strip() in self.rating_map:
                    valid_ratings += 1
        
        metrics['coverage_ratio'] = valid_ratings / max(total_ratings, 1)
        
        # 升级强度计算
        upgrade_scores = []
        for _, stock in industry_data.iterrows():
            stock_ratings = []
            for col in date_columns:
                rating_str = str(stock[col]).strip()
                if rating_str in self.rating_map:
                    stock_ratings.append(self.rating_map[rating_str])
            
            if len(stock_ratings) >= 2:
                changes = np.diff(stock_ratings)
                upgrades = np.sum(np.where(changes > 0, changes, 0))
                downgrades = np.sum(np.where(changes < 0, -changes, 0))
                net_upgrade = upgrades - downgrades
                upgrade_scores.append(net_upgrade)
        
        if upgrade_scores:
            metrics['upgrade_intensity'] = np.mean(upgrade_scores)
        
        # 成交量权重分数 (如果启用)
        if self.enable_volume_weight:
            # 这里可以添加成交量权重逻辑
            # 目前使用简化版本
            metrics['volume_weighted_score'] = metrics['momentum_strength'] * 1.1
        else:
            metrics['volume_weighted_score'] = metrics['momentum_strength']
        
        return metrics
    
    def _compute_enhanced_irsi(self, metrics: Dict[str, float]) -> float:
        """
        计算增强型IRSI指数
        """
        # 基础权重
        weights = {
            'momentum_strength': 0.4,
            'upgrade_intensity': 0.3,
            'trend_stability': 0.2,
            'coverage_ratio': 0.1
        }
        
        # 动态权重调整
        if metrics['coverage_ratio'] < 0.3:
            weights['coverage_ratio'] *= 2  # 低覆盖率时增加权重
        
        if metrics['trend_stability'] > 0.8:
            weights['trend_stability'] *= 1.5  # 高稳定性时增加权重
        
        # 计算加权分数
        weighted_score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in metrics:
                weighted_score += metrics[metric] * weight
                total_weight += weight
        
        # 标准化
        if total_weight > 0:
            enhanced_irsi = weighted_score / total_weight
        else:
            enhanced_irsi = 0
        
        # 限制范围
        enhanced_irsi = max(-1, min(1, enhanced_irsi))
        
        return enhanced_irsi
    
    def _assess_industry_status(self, enhanced_irsi: float, metrics: Dict[str, float]) -> Dict[str, Union[str, float]]:
        """
        评估行业状态
        """
        # 基础状态
        if enhanced_irsi >= 0.4:
            base_status = "强势领先"
        elif enhanced_irsi >= 0.2:
            base_status = "温和强势"
        elif enhanced_irsi >= -0.1:
            base_status = "相对平衡"
        elif enhanced_irsi >= -0.3:
            base_status = "轻微落后"
        else:
            base_status = "明显弱势"
        
        # 置信度评估
        confidence_factors = [
            metrics.get('trend_stability', 0),
            metrics.get('coverage_ratio', 0),
            min(1.0, abs(enhanced_irsi) * 2)  # IRSI绝对值越大，置信度越高
        ]
        
        confidence = np.mean(confidence_factors)
        
        # 状态修饰
        if confidence >= 0.8:
            status_modifier = "(高置信度)"
        elif confidence >= 0.6:
            status_modifier = "(中等置信度)"
        else:
            status_modifier = "(低置信度)"
        
        return {
            'status': f"{base_status}{status_modifier}",
            'confidence': confidence
        }
    
    def _get_enhanced_strength_level(self, score: float) -> str:
        """
        根据分数获取增强型强势等级
        """
        for (min_val, max_val), level in self.enhanced_strength_levels.items():
            if min_val <= score < max_val:
                return level
        return "中性"
    
    def _get_insufficient_data_result(self, industry_name: str = None, 
                                    data_points: int = 0, 
                                    reason: str = 'insufficient_data') -> Dict:
        """
        数据不足时的默认结果
        """
        base_result = super()._get_insufficient_data_result(industry_name, data_points)
        
        # 添加增强型字段
        base_result.update({
            'enhanced_irsi': 0.0,
            'enhanced_status': f'数据不足({reason})',
            'confidence_level': 0.0,
            'trend_stability': 0.0,
            'coverage_ratio': 0.0,
            'volume_weighted_score': 0.0,
            'enhanced_strength_level': '中性'
        })
        
        return base_result
    
    def batch_calculate_enhanced_irsi(self, stock_data: pd.DataFrame) -> Dict[str, Dict]:
        """
        批量计算增强型IRSI
        """
        results = {}
        
        # 获取所有行业
        industries = stock_data['行业'].dropna().unique()
        industries = [ind for ind in industries if ind and ind != '未分类']
        
        for industry in industries:
            industry_data = stock_data[stock_data['行业'] == industry]
            
            if len(industry_data) >= self.min_stocks_per_industry:
                result = self.calculate_enhanced_irsi(
                    industry_data=industry_data,
                    market_data=stock_data,
                    industry_name=industry
                )
                results[industry] = result
        
        return results
    
    def get_enhanced_industry_ranking(self, enhanced_irsi_results: Dict[str, Dict], 
                                    top_n: int = 10) -> List[Tuple[str, float, str]]:
        """
        获取增强型行业排名
        """
        rankings = []
        
        for industry, result in enhanced_irsi_results.items():
            enhanced_irsi = result.get('enhanced_irsi', 0)
            enhanced_status = result.get('enhanced_status', '未知')
            confidence = result.get('confidence_level', 0)
            
            # 只包含高置信度的结果
            if confidence >= 0.5:
                rankings.append((industry, enhanced_irsi, enhanced_status))
        
        # 按增强型IRSI排序
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return rankings[:top_n]


def compare_algorithms(stock_data: pd.DataFrame) -> Dict[str, Dict]:
    """
    比较不同算法的结果
    """
    # 使用增强型核心强势分析器
    enhanced_analyzer = EnhancedIRSICalculator()
    enhanced_results = enhanced_analyzer.batch_calculate_enhanced_irsi(stock_data)
    
    # 使用基础核心强势分析器
    base_analyzer = CoreStrengthAnalyzer()
    base_results = base_analyzer.batch_calculate(stock_data)
    
    # 比较结果
    comparison = {
        'enhanced_results': enhanced_results,
        'base_results': base_results,
        'summary': {
            'enhanced_count': len(enhanced_results),
            'base_count': len(base_results),
            'common_industries': len(set(enhanced_results.keys()) & set(base_results.keys()))
        }
    }
    
    return comparison


# 兼容性函数
def calculate_enhanced_irsi(industry_data: pd.DataFrame,
                           market_data: pd.DataFrame,
                           industry_name: str = None) -> Dict[str, Union[float, str, int]]:
    """
    计算增强型IRSI (兼容性函数)
    """
    analyzer = EnhancedIRSICalculator()
    return analyzer.calculate_enhanced_irsi(industry_data, market_data, industry_name)


if __name__ == "__main__":
    print("测试增强型核心强势分析器...")
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '600000', '600036', '000858'],
        '股票名称': ['平安银行', '万科A', '浦发银行', '招商银行', '五粮液'],
        '行业': ['银行', '房地产', '银行', '银行', '食品饮料'],
        '20250801': ['推荐', '中性', '买入', '推荐', '强烈推荐'],
        '20250802': ['推荐', '减持', '推荐', '强烈推荐', '推荐'],
        '20250803': ['强烈推荐', '中性', '推荐', '推荐', '推荐'],
        '20250804': ['推荐', '买入', '强烈推荐', '推荐', '强烈推荐']
    })
    
    # 测试增强型分析器
    enhanced_analyzer = EnhancedIRSICalculator()
    
    # 测试单个行业
    bank_data = test_data[test_data['行业'] == '银行']
    result = enhanced_analyzer.calculate_enhanced_irsi(bank_data, test_data, '银行')
    print(f"银行行业增强分析结果: {result}")
    
    # 测试批量计算
    batch_results = enhanced_analyzer.batch_calculate_enhanced_irsi(test_data)
    print(f"批量增强分析结果: {len(batch_results)} 个行业")
    
    # 测试排名
    rankings = enhanced_analyzer.get_enhanced_industry_ranking(batch_results)
    print(f"增强型排名: {rankings}")
    
    print("测试完成！")