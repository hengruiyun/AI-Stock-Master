"""
IRSI算法 - 行业相对强度指数 (Industry Relative Strength Index)

核心功能：
1. 行业相对于大盘的表现分析
2. 行业轮动信号检测
3. 强势行业识别和排名

算法原理：
- 行业平均评级 vs 市场平均评级
- 相对强度趋势分析
- 轮动信号识别
- IRSI指数：-100到100的相对强度评分

作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime

# 导入配置和工具
try:
    from config import RATING_SCORE_MAP
    from industry_lookup import get_industry_stocks, get_stock_industry
except ImportError:
    # 如果无法导入配置，使用默认映射
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }
    # 定义备用函数
    def get_industry_stocks(industry_name: str) -> List[Tuple[str, str]]:
        return []
    def get_stock_industry(stock_code: str) -> str:
        return "未分类"

# 抑制警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


def calculate_industry_relative_strength(industry_data: pd.DataFrame, 
                                       market_data: pd.DataFrame, 
                                       industry_name: str = None) -> Dict[str, Union[float, str, int]]:
    """
    行业相对强度指数 (Industry Relative Strength Index)
    衡量行业相对于大盘的表现
    
    参数:
        industry_data (pd.DataFrame): 行业内股票数据
        market_data (pd.DataFrame): 全市场股票数据
        industry_name (str): 行业名称
        
    返回:
        dict: {
            'irsi': float,                  # IRSI指数 (-100到100)
            'status': str,                  # 相对状态
            'recent_relative': float,       # 近期相对表现
            'trend_slope': float,           # 趋势斜率
            'industry_avg': float,          # 行业平均分
            'market_avg': float,            # 市场平均分
            'data_points': int,             # 有效数据点数
            'industry_name': str,           # 行业名称
            'calculation_time': str         # 计算时间
        }
    """
    calculation_start = datetime.now()
    
    try:
        # 1. 识别日期列
        date_columns = [col for col in market_data.columns if str(col).startswith('202')]
        date_columns.sort()
        
        if len(date_columns) < 5:
            return _get_insufficient_irsi_data_result(industry_name)
        
        # 2. 计算行业和市场的平均评级
        industry_scores = []
        market_scores = []
        
        for date_col in date_columns:
            # 行业平均分 (等权重)
            if len(industry_data) > 0:
                ind_ratings = industry_data[date_col].map(RATING_SCORE_MAP).dropna()
                industry_avg = ind_ratings.mean() if len(ind_ratings) > 0 else np.nan
            else:
                industry_avg = np.nan
            
            # 市场平均分
            mkt_ratings = market_data[date_col].map(RATING_SCORE_MAP).dropna()
            market_avg = mkt_ratings.mean() if len(mkt_ratings) > 0 else np.nan
            
            if not (np.isnan(industry_avg) or np.isnan(market_avg)):
                industry_scores.append(industry_avg)
                market_scores.append(market_avg)
        
        if len(industry_scores) < 5:
            return _get_insufficient_irsi_data_result(industry_name, len(industry_scores))
        
        # 3. 相对强度计算
        relative_scores = np.array(industry_scores) - np.array(market_scores)
        
        # 4. 近期表现 (最近5天平均)
        recent_relative = np.mean(relative_scores[-5:]) if len(relative_scores) >= 5 else np.mean(relative_scores)
        
        # 5. 趋势强度 (线性拟合斜率)
        if len(relative_scores) >= 3:
            x = np.arange(len(relative_scores))
            trend_slope = np.polyfit(x, relative_scores, 1)[0]
        else:
            trend_slope = 0
        
        # 6. IRSI指数计算 (-100到100)
        # 基础分数：近期相对表现
        base_score = recent_relative * 20  # 放大到合适范围
        # 趋势调整：趋势斜率的贡献
        trend_adjustment = trend_slope * 50  # 趋势影响
        
        irsi = base_score + trend_adjustment
        irsi = max(-100, min(100, irsi))  # 限制在[-100, 100]
        
        # 7. 状态判断
        status = _determine_irsi_status(irsi, recent_relative, trend_slope)
        
        # 8. 计算时间
        calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        
        return {
            'irsi': round(irsi, 2),
            'status': status,
            'recent_relative': round(recent_relative, 3),
            'trend_slope': round(trend_slope, 4),
            'industry_avg': round(np.mean(industry_scores[-5:]), 2),
            'market_avg': round(np.mean(market_scores[-5:]), 2),
            'data_points': len(relative_scores),
            'industry_name': industry_name or '未知行业',
            'calculation_time': calculation_time
        }
        
    except Exception as e:
        return {
            'irsi': 0,
            'status': 'calculation_error',
            'error': str(e),
            'industry_name': industry_name or '未知行业',
            'calculation_time': f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        }


def batch_calculate_irsi(stock_data: pd.DataFrame) -> Dict[str, Dict]:
    """
    批量计算所有行业的IRSI指数
    
    参数:
        stock_data (pd.DataFrame): 股票数据，包含行业分类
        
    返回:
        dict: {industry_name: irsi_result, ...}
    """
    if stock_data is None or len(stock_data) == 0:
        return {}
    
    batch_start = datetime.now()
    results = {}
    
    # 获取所有行业
    industries = stock_data['行业'].dropna().unique()
    industries = [ind for ind in industries if ind and ind != '未分类']
    
    if len(industries) == 0:
        print("警告 警告：未找到有效的行业分类")
        return {}
    
    print(f"行业 开始批量计算IRSI指数...")
    print(f"   分析范围: {len(industries)} 个行业")
    
    for idx, industry in enumerate(industries):
        # 筛选行业数据
        industry_data = stock_data[stock_data['行业'] == industry]
        
        if len(industry_data) < 3:  # 行业股票太少跳过
            continue
        
        # 计算该行业的IRSI
        irsi_result = calculate_industry_relative_strength(
            industry_data=industry_data,
            market_data=stock_data,
            industry_name=industry
        )
        
        # 添加行业统计信息
        irsi_result.update({
            'stock_count': len(industry_data),
            'market_share': len(industry_data) / len(stock_data) * 100
        })
        
        results[industry] = irsi_result
        
        # 进度提示
        if (idx + 1) % 20 == 0:
            print(f"   已处理: {idx + 1} / {len(industries)} 个行业")
    
    batch_time = (datetime.now() - batch_start).total_seconds()
    print(f"成功 批量计算完成: {len(results)} 个行业，耗时 {batch_time:.2f} 秒")
    
    return results


def detect_industry_rotation_signals(irsi_results: Dict[str, Dict], 
                                   threshold_strong: float = 30,
                                   threshold_weak: float = 10) -> List[Dict]:
    """
    检测行业轮动信号
    
    参数:
        irsi_results (dict): 行业IRSI计算结果
        threshold_strong (float): 强信号阈值
        threshold_weak (float): 弱信号阈值
        
    返回:
        list: 轮动信号列表
    """
    signals = []
    
    for industry, result in irsi_results.items():
        irsi = result.get('irsi', 0)
        trend_slope = result.get('trend_slope', 0)
        status = result.get('status', 'neutral')
        
        signal_strength = 'none'
        signal_type = 'neutral'
        
        # 强势上升信号
        if irsi > threshold_strong and trend_slope > 0.01:
            signal_type = 'rotation_in'
            signal_strength = 'strong' if irsi > 50 else 'medium'
        
        # 强势下降信号
        elif irsi < -threshold_strong and trend_slope < -0.01:
            signal_type = 'rotation_out'
            signal_strength = 'strong' if irsi < -50 else 'medium'
        
        # 弱信号
        elif abs(irsi) > threshold_weak:
            signal_type = 'rotation_in' if irsi > 0 else 'rotation_out'
            signal_strength = 'weak'
        
        if signal_strength != 'none':
            signals.append({
                'industry': industry,
                'signal_type': signal_type,
                'signal_strength': signal_strength,
                'irsi': irsi,
                'trend_slope': trend_slope,
                'status': status,
                'stock_count': result.get('stock_count', 0)
            })
    
    # 按信号强度和IRSI排序
    signals.sort(key=lambda x: (
        {'strong': 3, 'medium': 2, 'weak': 1}[x['signal_strength']],
        abs(x['irsi'])
    ), reverse=True)
    
    return signals


def get_strongest_industries(irsi_results: Dict[str, Dict], 
                           top_n: int = 10, 
                           direction: str = 'both') -> List[Tuple[str, float, str]]:
    """
    获取最强行业排名
    
    参数:
        irsi_results (dict): 行业IRSI计算结果
        top_n (int): 返回前N名
        direction (str): 方向筛选 'up'(上升), 'down'(下降), 'both'(双向)
        
    返回:
        list: [(industry_name, irsi, status), ...] 按绝对IRSI值排序
    """
    if not irsi_results:
        return []
    
    # 过滤有效结果
    valid_results = []
    for industry, result in irsi_results.items():
        irsi = result.get('irsi', 0)
        status = result.get('status', 'neutral')
        
        # 方向过滤
        if direction == 'up' and irsi <= 0:
            continue
        elif direction == 'down' and irsi >= 0:
            continue
        
        if abs(irsi) > 1:  # 排除无意义的微小变化
            valid_results.append((
                industry,
                irsi,
                status,
                result.get('stock_count', 0),
                abs(irsi)  # 用于排序的绝对值
            ))
    
    # 按绝对IRSI值降序排序
    valid_results.sort(key=lambda x: x[4], reverse=True)
    
    # 返回前N名
    return [(industry, irsi, status) for industry, irsi, status, count, abs_irsi in valid_results[:top_n]]


def get_irsi_market_summary(irsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float, str]]:
    """
    获取IRSI市场概况
    
    参数:
        irsi_results (dict): 行业IRSI计算结果
        
    返回:
        dict: 市场概况统计
    """
    if not irsi_results:
        return {}
    
    valid_irsi = [result['irsi'] for result in irsi_results.values() 
                  if result.get('irsi', 0) != 0]
    
    if not valid_irsi:
        return {'total_industries': len(irsi_results), 'valid_calculations': 0}
    
    # 状态分布统计
    status_counts = {}
    for result in irsi_results.values():
        status = result.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # 强弱行业统计
    strong_up = len([x for x in valid_irsi if x > 20])
    weak_up = len([x for x in valid_irsi if 5 < x <= 20])
    neutral = len([x for x in valid_irsi if -5 <= x <= 5])
    weak_down = len([x for x in valid_irsi if -20 <= x < -5])
    strong_down = len([x for x in valid_irsi if x < -20])
    
    # 市场轮动活跃度
    rotation_activity = np.std(valid_irsi) if len(valid_irsi) > 1 else 0
    
    return {
        'total_industries': len(irsi_results),
        'valid_calculations': len(valid_irsi),
        'success_rate': len(valid_irsi) / len(irsi_results) * 100,
        'irsi_mean': np.mean(valid_irsi),
        'irsi_median': np.median(valid_irsi),
        'irsi_std': np.std(valid_irsi),
        'irsi_max': max(valid_irsi),
        'irsi_min': min(valid_irsi),
        'strong_up_count': strong_up,
        'weak_up_count': weak_up,
        'neutral_count': neutral,
        'weak_down_count': weak_down,
        'strong_down_count': strong_down,
        'rotation_activity': round(rotation_activity, 2),
        'status_distribution': status_counts
    }


# 私有辅助函数

def _get_insufficient_irsi_data_result(industry_name: str = None, data_points: int = 0) -> Dict:
    """返回数据不足的IRSI结果"""
    return {
        'irsi': 0,
        'status': 'insufficient_data',
        'recent_relative': 0,
        'trend_slope': 0,
        'industry_avg': 0,
        'market_avg': 0,
        'data_points': data_points,
        'industry_name': industry_name or '未知行业',
        'calculation_time': '0.001s'
    }


def _determine_irsi_status(irsi: float, recent_relative: float, trend_slope: float) -> str:
    """
    根据IRSI值确定行业相对强度状态 - 优化版本
    采用统一的专业术语和优化的阈值标准
    
    参数:
        irsi (float): IRSI指数值 (-100到100)
        recent_relative (float): 近期相对表现
        trend_slope (float): 趋势斜率
        
    返回:
        str: 统一的专业术语状态描述
    """
    # 基于优化后的阈值标准进行分类
    if irsi >= 25:
        return 'significant_outperform'     # 显著跑赢大盘
    elif irsi >= 15:
        return 'moderate_outperform'        # 温和跑赢大盘
    elif irsi >= 5:
        return 'slight_outperform'          # 轻微跑赢大盘
    elif irsi >= -5:
        return 'market_neutral'             # 与大盘同步
    elif irsi >= -15:
        return 'slight_underperform'        # 轻微跑输大盘
    elif irsi >= -25:
        return 'moderate_underperform'      # 温和跑输大盘
    else:
        return 'significant_underperform'   # 显著跑输大盘


def get_irsi_professional_terminology(status: str) -> dict:
    """
    获取IRSI专业术语描述 - 新增函数
    
    参数:
        status (str): IRSI状态分类
        
    返回:
        dict: 包含专业术语和投资建议的描述
    """
    terminology = {
        'significant_outperform': {
            'short': '显著跑赢',
            'detailed': '显著跑赢大盘，行业配置价值突出，技术面强势',
            'investment_signal': '🔥 重点配置',
            'recommendation': '建议重点配置，享受行业超额收益',
            'risk_note': '注意估值泡沫风险'
        },
        'moderate_outperform': {
            'short': '温和跑赢', 
            'detailed': '温和跑赢大盘，具备明确配置价值，趋势向好',
            'investment_signal': '✅ 适度配置',
            'recommendation': '适合中线配置，稳健获取超额收益',
            'risk_note': '关注行业轮动风险'
        },
        'slight_outperform': {
            'short': '轻微跑赢',
            'detailed': '轻微跑赢大盘，相对优势有限，可适当关注',
            'investment_signal': '👀 关注',
            'recommendation': '可适当关注，等待更明确信号',
            'risk_note': '优势可能不持续'
        },
        'market_neutral': {
            'short': '与市场同步',
            'detailed': '与大盘表现基本同步，无明显相对优势，中性配置',
            'investment_signal': '⚖️ 中性',
            'recommendation': '中性配置，跟随大盘表现',
            'risk_note': '缺乏超额收益机会'
        },
        'slight_underperform': {
            'short': '轻微跑输',
            'detailed': '轻微跑输大盘，相对劣势显现，配置价值有限',
            'investment_signal': '⚠️ 谨慎',
            'recommendation': '谨慎配置，关注改善信号',
            'risk_note': '可能持续跑输大盘'
        },
        'moderate_underperform': {
            'short': '温和跑输',
            'detailed': '温和跑输大盘，相对劣势明显，建议减配或规避',
            'investment_signal': '⬇️ 减配',
            'recommendation': '建议减配，寻找更优行业',
            'risk_note': '面临持续跑输风险'
        },
        'significant_underperform': {
            'short': '显著跑输',
            'detailed': '显著跑输大盘，相对劣势严重，建议规避配置',
            'investment_signal': '🚫 规避',
            'recommendation': '建议规避，等待行业反转',
            'risk_note': '存在显著超额损失风险'
        }
    }
    
    return terminology.get(status, {
        'short': '未知状态',
        'detailed': '行业相对强度状态不明确',
        'investment_signal': '❓ 观望',
        'recommendation': '建议观望，等待明确信号',
        'risk_note': '不确定性较高'
    })


def assess_industry_investment_value(irsi: float, stock_count: int, trend_slope: float) -> dict:
    """
    评估行业投资价值 - 新增函数
    综合IRSI值、股票数量、趋势斜率进行评估
    
    参数:
        irsi (float): IRSI指数值
        stock_count (int): 行业内股票数量
        trend_slope (float): 趋势斜率
        
    返回:
        dict: 投资价值评估结果
    """
    # 基础价值评分 (0-100)
    base_score = max(0, min(100, (irsi + 50) * 2))  # 将IRSI(-50到50)映射到(0-100)
    
    # 规模调整 (股票数量越多，代表性越强)
    size_factor = min(1.2, 1 + stock_count / 100)  # 最多20%的加成
    
    # 趋势调整 (趋势向好额外加分)
    trend_factor = 1 + max(-0.3, min(0.3, trend_slope * 10))  # ±30%的调整
    
    # 综合评分
    final_score = base_score * size_factor * trend_factor
    final_score = max(0, min(100, final_score))
    
    # 投资价值等级
    if final_score >= 80:
        value_level = '🌟 极高价值'
        recommendation = '强烈推荐配置'
    elif final_score >= 65:
        value_level = '⭐ 高价值'
        recommendation = '推荐配置'
    elif final_score >= 50:
        value_level = '📊 中等价值'
        recommendation = '可考虑配置'
    elif final_score >= 35:
        value_level = '⚡ 低价值'
        recommendation = '谨慎考虑'
    else:
        value_level = '🚫 无配置价值'
        recommendation = '建议规避'
    
    return {
        'investment_score': round(final_score, 1),
        'value_level': value_level,
        'recommendation': recommendation,
        'factors': {
            'base_score': round(base_score, 1),
            'size_factor': round(size_factor, 2),
            'trend_factor': round(trend_factor, 2)
        }
    }


# 模块测试函数
def test_irsi_calculator():
    """测试IRSI计算器功能"""
    print("测试 测试IRSI计算器...")
    
    # 构造测试市场数据
    market_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '000003', '000004', '000005'],
        '股票名称': ['股票A', '股票B', '股票C', '股票D', '股票E'],
        '行业': ['银行', '银行', '科技', '科技', '地产'],
        '20250601': ['中空', '小空', '微多', '小多', '中空'],
        '20250602': ['小空', '微空', '小多', '中多', '小空'],
        '20250603': ['微空', '微多', '中多', '大多', '微空'],
        '20250604': ['微多', '小多', '大多', '中多', '微多'],
        '20250605': ['小多', '中多', '中多', '小多', '小多']
    })
    
    # 测试单个行业计算
    tech_industry = market_data[market_data['行业'] == '科技']
    result = calculate_industry_relative_strength(
        industry_data=tech_industry,
        market_data=market_data,
        industry_name='科技'
    )
    print(f"   科技行业测试: IRSI={result['irsi']}, 状态={result['status']}")
    
    # 测试批量计算
    batch_results = batch_calculate_irsi(market_data)
    print(f"   批量测试: 处理 {len(batch_results)} 个行业")
    
    # 测试轮动信号
    signals = detect_industry_rotation_signals(batch_results)
    print(f"   轮动信号: 检测到 {len(signals)} 个信号")
    
    # 测试排名
    ranking = get_strongest_industries(batch_results, top_n=3)
    print(f"   排名测试: 前3强行业获取成功")
    
    # 测试市场概况
    summary = get_irsi_market_summary(batch_results)
    print(f"   概况测试: 成功率 {summary.get('success_rate', 0):.1f}%")
    
    print("成功 IRSI计算器测试完成")
    return True


class IRSICalculator:
    """
    IRSI算法计算器类
    
    提供面向对象的IRSI计算接口，便于实例化和配置管理
    """
    
    def __init__(self, rating_map: Dict = None, min_stocks_per_industry: int = 3, enable_cache: bool = True):
        """
        初始化IRSI计算器
        
        参数:
            rating_map (dict): 评级映射表，默认使用RATING_SCORE_MAP
            min_stocks_per_industry (int): 每个行业最少股票数要求，默认3个
            enable_cache (bool): 是否启用结果缓存，默认启用
        """
        self.rating_map = rating_map or RATING_SCORE_MAP
        self.min_stocks_per_industry = min_stocks_per_industry
        self.calculation_count = 0
        self.enable_cache = enable_cache
        self._cache = {} if enable_cache else None
        
        # 性能统计
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_time_per_industry': 0.0
        }
    
    def calculate(self, industry_data: pd.DataFrame, market_data: pd.DataFrame, 
                 industry_name: str = None) -> Dict[str, Union[float, str, int]]:
        """
        计算单个行业的IRSI指数
        
        参数:
            industry_data (pd.DataFrame): 行业内股票数据
            market_data (pd.DataFrame): 全市场股票数据
            industry_name (str): 行业名称
            
        返回:
            dict: IRSI计算结果
        """
        self.calculation_count += 1
        start_time = datetime.now()
        
        # 缓存检查
        if self.enable_cache and industry_name:
            cache_key = self._generate_cache_key(industry_data, industry_name)
            if cache_key in self._cache:
                self.stats['cache_hits'] += 1
                return self._cache[cache_key]
        
        # 执行计算
        result = calculate_industry_relative_strength(industry_data, market_data, industry_name)
        
        # 更新统计
        calc_time = (datetime.now() - start_time).total_seconds()
        self.stats['total_calculations'] += 1
        self.stats['total_time'] += calc_time
        self.stats['avg_time_per_industry'] = self.stats['total_time'] / self.stats['total_calculations']
        
        # 存储缓存
        if self.enable_cache and industry_name:
            self._cache[cache_key] = result
        
        return result
    
    def batch_calculate(self, stock_data: pd.DataFrame) -> Dict[str, Dict]:
        """
        批量计算所有行业的IRSI指数
        
        参数:
            stock_data (pd.DataFrame): 股票数据，包含行业分类
            
        返回:
            dict: 批量计算结果
        """
        return batch_calculate_irsi(stock_data)
    
    def detect_rotation_signals(self, irsi_results: Dict[str, Dict], 
                               threshold_strong: float = 30,
                               threshold_weak: float = 10) -> List[Dict]:
        """
        检测行业轮动信号
        
        参数:
            irsi_results (dict): IRSI计算结果
            threshold_strong (float): 强势阈值
            threshold_weak (float): 弱势阈值
            
        返回:
            list: 轮动信号列表
        """
        return detect_industry_rotation_signals(irsi_results, threshold_strong, threshold_weak)
    
    def get_strongest_industries(self, irsi_results: Dict[str, Dict], 
                               top_n: int = 10, direction: str = 'both') -> List[Tuple[str, float, str]]:
        """
        获取最强势行业
        
        参数:
            irsi_results (dict): IRSI计算结果
            top_n (int): 返回前N名
            direction (str): 方向过滤器 ('both', 'positive', 'negative')
            
        返回:
            list: 强势行业列表
        """
        return get_strongest_industries(irsi_results, top_n, direction)
    
    def get_market_summary(self, irsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float, str]]:
        """
        获取市场摘要信息
        
        参数:
            irsi_results (dict): IRSI计算结果
            
        返回:
            dict: 市场摘要
        """
        return get_irsi_market_summary(irsi_results)
    
    def _generate_cache_key(self, industry_data: pd.DataFrame, industry_name: str) -> str:
        """生成缓存键"""
        data_hash = hash(tuple(industry_data.values.flatten()))
        return f"{industry_name}_{data_hash}"
    
    def get_performance_stats(self) -> Dict[str, Union[int, float, str]]:
        """获取性能统计信息"""
        cache_hit_rate = (self.stats['cache_hits'] / max(1, self.stats['total_calculations'])) * 100
        
        return {
            'total_calculations': self.stats['total_calculations'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'total_time': f"{self.stats['total_time']:.3f}s",
            'avg_time_per_industry': f"{self.stats['avg_time_per_industry']*1000:.2f}ms",
            'cache_enabled': self.enable_cache,
            'cache_size': len(self._cache) if self._cache else 0
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
            print("成功 IRSI计算器缓存已清空")
    
    def reset_counter(self):
        """重置计算计数器"""
        self.calculation_count = 0
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_time_per_industry': 0.0
        }
    
    def __str__(self):
        cache_info = f", cache={len(self._cache) if self._cache else 0}" if self.enable_cache else ""
        return f"IRSICalculator(calculations={self.calculation_count}, min_stocks={self.min_stocks_per_industry}{cache_info})"


if __name__ == "__main__":
    test_irsi_calculator() 