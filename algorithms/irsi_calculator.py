# -*- coding: utf-8 -*-
"""
核心强势分析器 - 替代IRSI模块
集成技术动量分析算法(TMA)和升级关注算法(UFA)
专门用于识别行业强势

核心功能：
1. 行业强势识别和排名
2. 技术动量分析
3. 评级升级关注分析
4. 投资建议生成

作者: 267278466@qq.com
创建时间：2025-08-14
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Union
import logging
import warnings
from datetime import datetime

# 导入国际化配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.i18n import t_msci, t_rtsi, t_irsi, t_engine, t_common, set_language
except ImportError:
    # 如果无法导入，使用备用函数
    def t_msci(key): return key
    def t_rtsi(key): return key
    def t_irsi(key): return key
    def t_engine(key): return key
    def t_common(key): return key
    def set_language(lang): pass

try:
    from config import RATING_SCORE_MAP
except ImportError:
    # 如果无法导入配置，使用默认映射
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }

warnings.filterwarnings('ignore', category=RuntimeWarning)

class CoreStrengthAnalyzer:
    """
    核心行业强势分析器
    整合最佳算法：技术动量分析(TMA) + 升级关注算法(UFA)
    """
    
    def __init__(self, rating_map: Dict = None, min_stocks_per_industry: int = 3, enable_cache: bool = True):
        self.logger = logging.getLogger(__name__)
        
        # 评级映射
        self.rating_map = rating_map or {
            '强烈推荐': 5, '推荐': 4, '买入': 4, '增持': 3, '中性': 2,
            '持有': 2, '减持': 1, '卖出': 0, '强烈卖出': 0,
            '中空': 1, '-': 2,  # 特殊处理
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '大空': 0
        }
        
        # 强势等级定义
        self.strength_levels = {
            (0.4, float('inf')): "强势",
            (0.2, 0.4): "轻微强势", 
            (-0.2, 0.2): "中性",
            (-0.4, -0.2): "轻微弱势",
            (float('-inf'), -0.4): "弱势"
        }
        
        # 配置参数
        self.min_stocks_per_industry = min_stocks_per_industry
        self.enable_cache = enable_cache
        self.cache = {} if enable_cache else None
        self.calculation_count = 0
        self.cache_hits = 0
    
    def technical_momentum_analysis(self, sector_data: pd.DataFrame, 
                                  industry_col: str, date_cols: List[str]) -> Dict[str, float]:
        """
        技术动量分析算法 (TMA)
        基于RSI、MACD等技术指标概念，适合识别技术面强势
        """
        results = {}
        
        for industry in sector_data[industry_col].unique():
            industry_data = sector_data[sector_data[industry_col] == industry]
            
            # 计算技术动量指标
            momentum_scores = []
            
            for _, stock in industry_data.iterrows():
                ratings = []
                for col in date_cols:
                    rating_str = str(stock[col]).strip()
                    if rating_str in self.rating_map:
                        ratings.append(self.rating_map[rating_str])
                
                if len(ratings) >= 3:
                    # RSI风格计算
                    changes = np.diff(ratings)
                    gains = np.where(changes > 0, changes, 0)
                    losses = np.where(changes < 0, -changes, 0)
                    
                    if len(gains) > 0 and len(losses) > 0:
                        avg_gain = np.mean(gains) if np.sum(gains) > 0 else 0.01
                        avg_loss = np.mean(losses) if np.sum(losses) > 0 else 0.01
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                        
                        # MACD风格趋势
                        short_ma = np.mean(ratings[-3:]) if len(ratings) >= 3 else np.mean(ratings)
                        long_ma = np.mean(ratings)
                        macd = short_ma - long_ma
                        
                        # 综合技术分数
                        tech_score = (rsi - 50) / 50 * 0.6 + macd * 0.4
                        momentum_scores.append(tech_score)
            
            # 行业技术动量
            if momentum_scores:
                industry_momentum = np.mean(momentum_scores)
                # 标准化到[-1, 1]区间
                results[industry] = np.tanh(industry_momentum)
            else:
                results[industry] = 0.0
        
        return results
    
    def upgrade_focus_analysis(self, sector_data: pd.DataFrame, 
                             industry_col: str, date_cols: List[str]) -> Dict[str, float]:
        """
        升级关注算法 (UFA)
        专注评级上调事件，放大积极变化信号
        """
        results = {}
        
        for industry in sector_data[industry_col].unique():
            industry_data = sector_data[sector_data[industry_col] == industry]
            
            upgrade_scores = []
            
            for _, stock in industry_data.iterrows():
                ratings = []
                for col in date_cols:
                    rating_str = str(stock[col]).strip()
                    if rating_str in self.rating_map:
                        ratings.append(self.rating_map[rating_str])
                
                if len(ratings) >= 2:
                    # 计算评级变化
                    changes = np.diff(ratings)
                    
                    # 重点关注上调
                    upgrades = np.where(changes > 0, changes, 0)
                    downgrades = np.where(changes < 0, changes, 0)
                    
                    # 上调权重更高
                    upgrade_weight = 2.0
                    downgrade_weight = 1.0
                    
                    weighted_change = (np.sum(upgrades) * upgrade_weight + 
                                     np.sum(downgrades) * downgrade_weight)
                    
                    # 最近变化权重更高
                    if len(changes) > 0:
                        recent_change = changes[-1] if len(changes) >= 1 else 0
                        weighted_change += recent_change * 1.5
                    
                    upgrade_scores.append(weighted_change)
            
            # 行业升级关注分数
            if upgrade_scores:
                industry_upgrade = np.mean(upgrade_scores)
                # 标准化处理
                results[industry] = np.tanh(industry_upgrade / 2.0)
            else:
                results[industry] = 0.0
        
        return results
    
    def calculate(self, industry_data: pd.DataFrame, market_data: pd.DataFrame = None, 
                 industry_name: str = None, language: str = 'zh_CN') -> Dict[str, Union[float, str, int]]:
        """
        计算单个行业的强势分析 (兼容原IRSI接口)
        
        Args:
            industry_data: 行业数据
            market_data: 市场数据 (保持兼容性，实际不使用)
            industry_name: 行业名称
            language: 语言设置
        
        Returns:
            分析结果字典
        """
        self.calculation_count += 1
        
        # 识别行业列
        industry_col = None
        for col in ['行业', 'Industry', 'Sector']:
            if col in industry_data.columns:
                industry_col = col
                break
        
        if industry_col is None:
            return self._get_insufficient_data_result(industry_name, 0)
        
        # 识别日期列
        date_cols = [col for col in industry_data.columns 
                    if col not in [industry_col, '股票代码', '股票名称', 'Code', 'Name']]
        
        if len(date_cols) < 2:
            return self._get_insufficient_data_result(industry_name, len(date_cols))
        
        # 按日期排序
        date_cols.sort()
        
        # 运行两个核心算法
        tma_results = self.technical_momentum_analysis(industry_data, industry_col, date_cols)
        ufa_results = self.upgrade_focus_analysis(industry_data, industry_col, date_cols)
        
        # 如果指定了行业名称，返回该行业结果
        if industry_name and industry_name in tma_results:
            tma_score = tma_results[industry_name]
            ufa_score = ufa_results.get(industry_name, 0.0)
            
            # 选择最佳算法分数
            best_score = max(tma_score, ufa_score)
            best_algorithm = "TMA" if tma_score >= ufa_score else "UFA"
            
            # 转换为IRSI兼容格式 (映射到-100到100)
            irsi_score = best_score * 100
            
            # 确定状态
            status = self._determine_status(best_score)
            
            return {
                'irsi': irsi_score,
                'status': status,
                'industry_name': industry_name,
                'stock_count': len(industry_data),
                'data_points': len(date_cols),
                'algorithm': best_algorithm,
                'tma_score': tma_score,
                'ufa_score': ufa_score,
                'strength_level': self._get_strength_level(best_score)
            }
        
        # 如果没有指定行业，返回第一个行业的结果
        if tma_results:
            first_industry = list(tma_results.keys())[0]
            return self.calculate(industry_data, market_data, first_industry, language)
        
        return self._get_insufficient_data_result(industry_name, 0)
    
    def batch_calculate(self, stock_data: pd.DataFrame, language: str = 'zh_CN') -> Dict[str, Dict]:
        """
        批量计算所有行业的强势分析 (兼容原IRSI接口)
        
        Args:
            stock_data: 股票数据
            language: 语言设置
        
        Returns:
            所有行业的分析结果
        """
        # 识别行业列
        industry_col = None
        for col in ['行业', 'Industry', 'Sector']:
            if col in stock_data.columns:
                industry_col = col
                break
        
        if industry_col is None:
            return {}
        
        # 识别日期列
        date_cols = [col for col in stock_data.columns 
                    if col not in [industry_col, '股票代码', '股票名称', 'Code', 'Name']]
        
        if len(date_cols) < 2:
            return {}
        
        # 按日期排序
        date_cols.sort()
        
        # 运行两个核心算法
        tma_results = self.technical_momentum_analysis(stock_data, industry_col, date_cols)
        ufa_results = self.upgrade_focus_analysis(stock_data, industry_col, date_cols)
        
        # 构建结果字典
        results = {}
        for industry in tma_results.keys():
            industry_data = stock_data[stock_data[industry_col] == industry]
            
            if len(industry_data) < self.min_stocks_per_industry:
                continue
            
            tma_score = tma_results[industry]
            ufa_score = ufa_results.get(industry, 0.0)
            
            # 选择最佳算法分数
            best_score = max(tma_score, ufa_score)
            best_algorithm = "TMA" if tma_score >= ufa_score else "UFA"
            
            # 转换为IRSI兼容格式
            irsi_score = best_score * 100
            
            results[industry] = {
                'irsi': irsi_score,
                'status': self._determine_status(best_score),
                'industry_name': industry,
                'stock_count': len(industry_data),
                'data_points': len(date_cols),
                'algorithm': best_algorithm,
                'tma_score': tma_score,
                'ufa_score': ufa_score,
                'strength_level': self._get_strength_level(best_score)
            }
        
        return results
    
    def detect_rotation_signals(self, irsi_results: Dict[str, Dict], 
                               threshold_strong: float = 30,
                               threshold_weak: float = 10) -> List[Dict]:
        """
        检测行业轮动信号 (兼容原IRSI接口)
        """
        signals = []
        
        for industry, result in irsi_results.items():
            irsi_score = result.get('irsi', 0)
            strength_level = result.get('strength_level', '中性')
            
            if irsi_score >= threshold_strong:
                signals.append({
                    'industry': industry,
                    'signal': '强势信号',
                    'irsi': irsi_score,
                    'strength': strength_level,
                    'recommendation': '积极关注'
                })
            elif irsi_score <= -threshold_weak:
                signals.append({
                    'industry': industry,
                    'signal': '弱势信号',
                    'irsi': irsi_score,
                    'strength': strength_level,
                    'recommendation': '谨慎观察'
                })
        
        return signals
    
    def get_strongest_industries(self, irsi_results: Dict[str, Dict], 
                               top_n: int = 10, direction: str = 'both') -> List[Tuple[str, float, str]]:
        """
        获取最强势行业列表 (兼容原IRSI接口)
        """
        industries = []
        
        for industry, result in irsi_results.items():
            irsi_score = result.get('irsi', 0)
            strength_level = result.get('strength_level', '中性')
            
            if direction == 'strong' and irsi_score > 0:
                industries.append((industry, irsi_score, strength_level))
            elif direction == 'weak' and irsi_score < 0:
                industries.append((industry, irsi_score, strength_level))
            elif direction == 'both':
                industries.append((industry, irsi_score, strength_level))
        
        # 按分数排序
        if direction == 'weak':
            industries.sort(key=lambda x: x[1])  # 升序
        else:
            industries.sort(key=lambda x: x[1], reverse=True)  # 降序
        
        return industries[:top_n]
    
    def get_market_summary(self, irsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float, str]]:
        """
        获取市场总结 (兼容原IRSI接口)
        """
        if not irsi_results:
            return {
                'total_industries': 0,
                'strong_industries': 0,
                'weak_industries': 0,
                'neutral_industries': 0,
                'average_irsi': 0.0,
                'market_sentiment': '中性'
            }
        
        irsi_scores = [result.get('irsi', 0) for result in irsi_results.values()]
        strong_count = len([score for score in irsi_scores if score >= 20])
        weak_count = len([score for score in irsi_scores if score <= -20])
        neutral_count = len(irsi_scores) - strong_count - weak_count
        
        avg_irsi = np.mean(irsi_scores)
        
        # 确定市场情绪
        if avg_irsi >= 20:
            sentiment = '乐观'
        elif avg_irsi <= -20:
            sentiment = '悲观'
        else:
            sentiment = '中性'
        
        return {
            'total_industries': len(irsi_results),
            'strong_industries': strong_count,
            'weak_industries': weak_count,
            'neutral_industries': neutral_count,
            'average_irsi': avg_irsi,
            'market_sentiment': sentiment
        }
    
    def _get_strength_level(self, score: float) -> str:
        """
        根据分数获取强势等级
        """
        for (min_val, max_val), level in self.strength_levels.items():
            if min_val <= score < max_val:
                return level
        return "中性"
    
    def _determine_status(self, score: float) -> str:
        """
        确定状态描述
        """
        if score >= 0.4:
            return "强势上涨"
        elif score >= 0.2:
            return "轻微强势"
        elif score >= -0.2:
            return "震荡整理"
        elif score >= -0.4:
            return "轻微弱势"
        else:
            return "弱势下跌"
    
    def _get_insufficient_data_result(self, industry_name: str = None, data_points: int = 0) -> Dict:
        """
        数据不足时的默认结果
        """
        return {
            'irsi': 0.0,
            'status': '数据不足',
            'industry_name': industry_name or '未知行业',
            'stock_count': 0,
            'data_points': data_points,
            'algorithm': 'N/A',
            'tma_score': 0.0,
            'ufa_score': 0.0,
            'strength_level': '中性'
        }
    
    def get_performance_stats(self) -> Dict[str, Union[int, float, str]]:
        """
        获取性能统计
        """
        cache_hit_rate = (self.cache_hits / max(self.calculation_count, 1)) * 100 if self.enable_cache else 0
        
        return {
            'calculation_count': self.calculation_count,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'cache_enabled': self.enable_cache,
            'min_stocks_per_industry': self.min_stocks_per_industry
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache is not None:
            self.cache.clear()
            self.cache_hits = 0
    
    def reset_counter(self):
        """重置计数器"""
        self.calculation_count = 0
        self.cache_hits = 0
    
    def __str__(self):
        cache_info = f", cache_hits={self.cache_hits}" if self.enable_cache else ""
        return f"CoreStrengthAnalyzer(calculations={self.calculation_count}, min_stocks={self.min_stocks_per_industry}{cache_info})"


# 兼容性函数 - 保持原IRSI接口
def calculate_industry_relative_strength(industry_data: pd.DataFrame, 
                                       market_data: pd.DataFrame, 
                                       industry_name: str = None,
                                       language: str = 'zh_CN') -> Dict[str, Union[float, str, int]]:
    """
    计算行业相对强度 (兼容原IRSI函数)
    """
    analyzer = CoreStrengthAnalyzer()
    return analyzer.calculate(industry_data, market_data, industry_name, language)


def batch_calculate_irsi(stock_data: pd.DataFrame, language: str = 'zh_CN') -> Dict[str, Dict]:
    """
    批量计算IRSI (兼容原IRSI函数)
    """
    analyzer = CoreStrengthAnalyzer()
    return analyzer.batch_calculate(stock_data, language)


def detect_industry_rotation_signals(irsi_results: Dict[str, Dict], 
                                   threshold_strong: float = 30,
                                   threshold_weak: float = 10) -> List[Dict]:
    """
    检测行业轮动信号 (兼容原IRSI函数)
    """
    analyzer = CoreStrengthAnalyzer()
    return analyzer.detect_rotation_signals(irsi_results, threshold_strong, threshold_weak)


def get_strongest_industries(irsi_results: Dict[str, Dict], 
                           top_n: int = 10, 
                           direction: str = 'both') -> List[Tuple[str, float, str]]:
    """
    获取最强势行业 (兼容原IRSI函数)
    """
    analyzer = CoreStrengthAnalyzer()
    return analyzer.get_strongest_industries(irsi_results, top_n, direction)


def get_irsi_market_summary(irsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float, str]]:
    """
    获取IRSI市场总结 (兼容原IRSI函数)
    """
    analyzer = CoreStrengthAnalyzer()
    return analyzer.get_market_summary(irsi_results)


# 兼容性类别名
class IRSICalculator(CoreStrengthAnalyzer):
    """
    IRSI计算器 (兼容性别名)
    """
    pass


def test_irsi_calculator():
    """
    测试核心强势分析器
    """
    print("测试核心强势分析器 (替代IRSI)...")
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '600000', '600036'],
        '股票名称': ['平安银行', '万科A', '浦发银行', '招商银行'],
        '行业': ['银行', '房地产', '银行', '银行'],
        '20250801': ['推荐', '中性', '买入', '推荐'],
        '20250802': ['推荐', '减持', '推荐', '强烈推荐'],
        '20250803': ['强烈推荐', '中性', '推荐', '推荐']
    })
    
    # 测试单个行业计算
    bank_data = test_data[test_data['行业'] == '银行']
    result = calculate_industry_relative_strength(bank_data, test_data, '银行')
    print(f"银行行业分析结果: {result}")
    
    # 测试批量计算
    batch_results = batch_calculate_irsi(test_data)
    print(f"批量分析结果: {batch_results}")
    
    # 测试轮动信号
    signals = detect_industry_rotation_signals(batch_results)
    print(f"轮动信号: {signals}")
    
    # 测试强势行业
    strongest = get_strongest_industries(batch_results, top_n=5)
    print(f"强势行业: {strongest}")
    
    print("测试完成！")


if __name__ == "__main__":
    test_irsi_calculator()