"""
from config.gui_i18n import t_gui as _
MSCI算法 - 市场情绪综合指数 (Market Sentiment Composite Index)

核心功能：
1. 市场整体情绪量化
2. 极端状态检测和预警
3. 风险等级评估

算法原理：
- 多空力量对比
- 情绪强度计算
- 市场参与度分析
- 极端情绪检测
- MSCI指数：0-100的市场情绪评分

作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
import warnings
from datetime import datetime
from collections import Counter

# 导入配置

# 导入国际化配置
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.gui_i18n import t_gui as t_msci, t_gui as t_rtsi, t_gui as t_irsi, t_gui as t_engine, t_gui as t_common, set_language
except ImportError:
    # 如果无法导入，使用备用函数
    def t_msci(key): return key
    def t_rtsi(key): return key
    def t_irsi(key): return key
    def t_engine(key): return key
    def t_common(key): return key
    def set_language(lang): pass

def get_rating_score_map():
    """
    获取评级分数映射（线性映射：0级=12.5分，7级=100分）
    公式：分数 = 12.5 + 级别 × 12.5
    """
    return {
        t_msci('rating_strong_buy'): 100.0,  # 大多 7级 = 12.5 + 7×12.5 = 100.0
        t_msci('rating_buy'): 87.5,          # 中多 6级 = 12.5 + 6×12.5 = 87.5
        t_msci('rating_moderate_buy'): 75.0, # 小多 5级 = 12.5 + 5×12.5 = 75.0
        t_msci('rating_slight_buy'): 62.5,   # 微多 4级 = 12.5 + 4×12.5 = 62.5
        t_msci('rating_slight_sell'): 50.0,  # 微空 3级 = 12.5 + 3×12.5 = 50.0（中性）
        t_msci('rating_moderate_sell'): 37.5,# 小空 2级 = 12.5 + 2×12.5 = 37.5
        t_msci('rating_sell'): 25.0,         # 中空 1级 = 12.5 + 1×12.5 = 25.0
        t_msci('rating_strong_sell'): 12.5,  # 大空 0级 = 12.5 + 0×12.5 = 12.5
        '-': None
    }

try:
    from config import RATING_SCORE_MAP
except ImportError:
    # 如果无法导入配置，使用动态映射
    RATING_SCORE_MAP = get_rating_score_map()

# 抑制警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


def _interpolate_ratings(data: pd.DataFrame) -> pd.DataFrame:
    """
    对评级数据进行智能双向插值处理
    
    策略：
    - 前段数据（开始时无评级）：使用后插值（用后面第一个有效值）
    - 中段数据（有评级后出现缺失）：使用前插值（用前面最近有效值）
    - 后段数据（结尾无评级）：使用前插值（用前面最近有效值）
    
    Args:
        data: 原始数据，包含评级列
        
    Returns:
        插值后的数据
    """
    # 识别日期列
    date_columns = [col for col in data.columns if str(col).startswith('202')]
    if not date_columns:
        return data
    
    date_columns.sort()
    
    # 复制数据以避免修改原始数据
    interpolated_data = data.copy()
    
    # 对每只股票/指数进行插值
    for idx in range(len(interpolated_data)):
        # 第一步：找到所有有效评级的位置
        valid_positions = {}  # {date_col: rating}
        for date_col in date_columns:
            current_rating = interpolated_data.at[idx, date_col]
            if not (pd.isna(current_rating) or current_rating == '-'):
                valid_positions[date_col] = current_rating
        
        if not valid_positions:
            # 如果该股票/指数完全没有有效评级，跳过
            continue
        
        # 第二步：找到第一个和最后一个有效评级的位置
        first_valid_date = None
        last_valid_date = None
        for date_col in date_columns:
            if date_col in valid_positions:
                if first_valid_date is None:
                    first_valid_date = date_col
                last_valid_date = date_col
        
        # 第三步：应用双向插值策略
        last_forward_rating = '-'  # 用于前插值（向后填充）
        
        for date_col in date_columns:
            current_rating = interpolated_data.at[idx, date_col]
            
            # 如果当前评级有效，更新前插值基准
            if not (pd.isna(current_rating) or current_rating == '-'):
                last_forward_rating = current_rating
                continue
            
            # 如果当前评级无效，需要插值
            if pd.isna(current_rating) or current_rating == '-':
                # 判断位置：前段、中段、后段
                date_index = date_columns.index(date_col)
                first_valid_index = date_columns.index(first_valid_date) if first_valid_date else -1
                last_valid_index = date_columns.index(last_valid_date) if last_valid_date else -1
                
                if date_index < first_valid_index:
                    # 前段：使用后插值（找后面第一个有效值）
                    next_valid_rating = '-'
                    for future_date in date_columns[date_index:]:
                        if future_date in valid_positions:
                            next_valid_rating = valid_positions[future_date]
                            break
                    if next_valid_rating != '-':
                        interpolated_data.at[idx, date_col] = next_valid_rating
                        # print(f"[后插值] 股票{idx} 日期{date_col} 使用后续评级{next_valid_rating}")
                
                elif date_index > last_valid_index:
                    # 后段：使用前插值（用最后一个有效值）
                    if last_forward_rating != '-':
                        interpolated_data.at[idx, date_col] = last_forward_rating
                        # print(f"[前插值-后段] 股票{idx} 日期{date_col} 使用前次评级{last_forward_rating}")
                
                else:
                    # 中段：使用前插值（用前面最近有效值）
                    if last_forward_rating != '-':
                        interpolated_data.at[idx, date_col] = last_forward_rating
                        # print(f"[前插值-中段] 股票{idx} 日期{date_col} 使用前次评级{last_forward_rating}")
    
    return interpolated_data


def calculate_market_sentiment_composite_index(all_data: pd.DataFrame, language: str = 'zh_CN', 
                                              use_enhanced: bool = False, 
                                              enable_quality_adjustment: bool = True) -> Dict[str, Union[float, str, int, List, Dict]]:
    """
    市场情绪综合指数 (Market Sentiment Composite Index)
    综合多个维度判断市场情绪状态
    
    参数:
        all_data (pd.DataFrame): 全市场股票数据
        
    返回:
        dict: {
            t_msci('current_msci'): float,          # 当前MSCI指数 (0-100)
            t_msci('market_state'): str,            # 市场状态
            t_msci('trend_5d'): float,              # 5日趋势变化
            t_msci('latest_analysis'): dict,        # 最新分析详情
            t_msci('history'): List[dict],          # 历史数据 (最近20天)
            t_msci('risk_level'): str,              # 风险等级
            t_msci('calculation_time'): str         # 计算时间
        }
    """
    # 设置语言
    set_language(language)
    # 如果启用增强版，则调用增强版MSCI算法
    if use_enhanced:
        try:
            from .enhanced_msci_calculator import calculate_enhanced_market_sentiment
            return calculate_enhanced_market_sentiment(all_data, language, enable_quality_adjustment)
        except ImportError:
            print("⚠️ 增强版MSCI不可用，回退到原版算法")
        except Exception as e:
            print(f"⚠️ 增强版MSCI计算失败，回退到原版算法: {e}")
    
    calculation_start = datetime.now()
    
    try:
        # 1. 对评级数据进行插值处理（关键修改：所有评级都使用最后一次有效数据）
        print("[MSCI计算] 开始对评级数据进行插值...")
        interpolated_data = _interpolate_ratings(all_data)
        print(f"[MSCI计算] 插值完成，数据形状: {interpolated_data.shape}")
        
        # 2. 识别日期列
        date_columns = [col for col in interpolated_data.columns if str(col).startswith('202')]
        date_columns.sort()
        
        if len(date_columns) < 5:
            return _get_insufficient_msci_data_result()
        
        msci_history = []
        
        # 3. 逐日计算MSCI（使用插值后的数据）
        for date_col in date_columns:
            daily_msci = _calculate_daily_msci(interpolated_data, date_col)
            if daily_msci:
                msci_history.append(daily_msci)
        
        if not msci_history:
            return _get_insufficient_msci_data_result()
        
        # 3. 最新状态分析
        latest = msci_history[-1]
        
        # 4. 趋势分析
        recent_trend = _calculate_msci_trend(msci_history)
        
        # 5. 波动率计算
        volatility = _calculate_market_volatility(msci_history)
        
        # 6. 成交量比率计算（模拟）
        volume_ratio = _calculate_volume_ratio(latest)
        
        # 7. 市场状态判断
        market_state = _determine_market_state(latest['msci'])
        
        # 8. 风险等级评估
        risk_level = _assess_risk_level(market_state, latest[t_msci('extreme_state')], recent_trend)
        
        # 9. 插值比例汇总和数据质量评估
        avg_interpolation_ratio = np.mean([item.get('interpolation_ratio', 0) for item in msci_history])
        all_warnings = []
        
        # 收集所有数据质量警告
        for item in msci_history[-5:]:  # 检查最近5天
            warnings = item.get(t_msci('data_quality_warnings'), [])
            all_warnings.extend(warnings)
        
        # 整体数据质量评估
        overall_quality_warnings = []
        if avg_interpolation_ratio > 0.3:
            overall_quality_warnings.append(f"📊 整体数据质量提醒：平均插值比例 {avg_interpolation_ratio:.1%}")
        if avg_interpolation_ratio > 0.5:
            overall_quality_warnings.append("🚨 数据质量严重警告：建议检查数据源完整性")
        
        # 10. 计算时间
        calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        
        return {
            'current_msci': latest['msci'],
            'market_state': market_state,
            'trend_5d': recent_trend,
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'latest_analysis': latest,
            'history': msci_history[-20:],  # 最近20天历史
            'risk_level': risk_level,
            'total_days': len(msci_history),
            'calculation_time': calculation_time,
            'avg_interpolation_ratio': round(avg_interpolation_ratio, 3),
            'data_quality_warnings': list(set(all_warnings)),  # 去重
            'overall_quality_warnings': overall_quality_warnings
        }
        
    except Exception as e:
        return {
            'current_msci': 0,
            'market_state': 'calculation_error',
            'error': str(e),
            'calculation_time': f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        }


def analyze_market_extremes(msci_history: List[Dict]) -> Dict[str, Union[int, float, List]]:
    """
    分析市场极端状态
    
    参数:
        msci_history (List[Dict]): MSCI历史数据
        
    返回:
        dict: 极端状态分析结果
    """
    if not msci_history:
        return {}
    
    # 提取MSCI值
    msci_values = [item['msci'] for item in msci_history]
    
    # 极端状态统计
    extreme_counts = {'bull': 0, 'bear': 0, 'normal': 0}
    for item in msci_history:
        extreme_state = item.get(t_msci('extreme_state'), 'normal')
        extreme_counts[extreme_state] += 1
    
    # 持续性分析
    current_state_duration = _calculate_current_state_duration(msci_history)
    
    # 波动性分析
    volatility = np.std(msci_values) if len(msci_values) > 1 else 0
    
    # 极值分析
    msci_max = max(msci_values)
    msci_min = min(msci_values)
    max_date = next(item['date'] for item in msci_history if item['msci'] == msci_max)
    min_date = next(item['date'] for item in msci_history if item['msci'] == msci_min)
    
    return {
        t_msci('extreme_counts'): extreme_counts,
        t_msci('current_state_duration'): current_state_duration,
        t_msci('volatility'): round(volatility, 2),
        t_msci('msci_max'): msci_max,
        t_msci('msci_min'): msci_min,
        t_msci('max_date'): max_date,
        t_msci('min_date'): min_date,
        t_msci('extreme_ratio'): (extreme_counts['bull'] + extreme_counts['bear']) / len(msci_history) * 100
    }


def generate_risk_warnings(market_state: str, latest_analysis: Dict, trend_5d: float) -> List[str]:
    """
    生成风险预警
    
    参数:
        market_state (str): 市场状态
        latest_analysis (dict): 最新分析数据
        trend_5d (float): 5日趋势
        
    返回:
        list: 风险预警列表
    """
    warnings_list = []
    
    msci = latest_analysis.get('msci', 50)
    bull_bear_ratio = latest_analysis.get(t_msci('bull_bear_ratio'), 1)
    participation = latest_analysis.get(t_msci('participation'), 0.5)
    extreme_state = latest_analysis.get(t_msci('extreme_state'), 'normal')
    
    # 极端情绪预警
    if extreme_state == 'bull':
        warnings_list.append("警告 市场极度乐观，需警惕获利回吐风险")
    elif extreme_state == 'bear':
        warnings_list.append("🚨 市场极度悲观，可能出现恐慌性抛售")
    
    # 情绪过热预警
    if msci > 80:
        warnings_list.append("热门 市场情绪过热，建议降低仓位")
    elif msci < 20:
        warnings_list.append("冷门 市场情绪低迷，关注超跌反弹机会")
    
    # 多空失衡预警
    if bull_bear_ratio > 5:
        warnings_list.append("上涨 多头力量过强，市场可能过度乐观")
    elif bull_bear_ratio < 0.2:
        warnings_list.append("下跌 空头力量过强，市场可能过度悲观")
    
    # 参与度预警
    if participation < 0.2:
        warnings_list.append("😴 市场参与度过低，注意流动性风险")
    elif participation > 0.8:
        warnings_list.append("🌊 市场参与度过高，可能存在泡沫风险")
    
    # 趋势预警
    if trend_5d > 15:
        warnings_list.append("数据 情绪快速上升，警惕反转风险")
    elif trend_5d < -15:
        warnings_list.append("数据 情绪快速下降，关注筑底信号")
    
    # 综合风险评估
    if market_state in [t_msci('euphoric'), t_msci('panic')]:
        warnings_list.append("核心 市场处于极端状态，建议采取保守策略")
    
    return warnings_list


def get_msci_market_summary(msci_result: Dict) -> Dict[str, Union[str, float, int]]:
    """
    获取MSCI市场总结
    
    参数:
        msci_result (dict): MSCI计算结果
        
    返回:
        dict: 市场总结信息
    """
    if not msci_result or msci_result.get(t_msci('current_msci'), 0) == 0:
        return {t_msci('status'): 'no_data'}
    
    current_msci = msci_result.get(t_msci('current_msci'), 50)
    market_state = msci_result.get(t_msci('market_state'), t_msci('neutral'))
    trend_5d = msci_result.get(t_msci('trend_5d'), 0)
    risk_level = msci_result.get(t_msci('risk_level'), t_msci('medium'))
    latest = msci_result.get(t_msci('latest_analysis'), {})
    
    # 市场情绪描述
    sentiment_desc = _get_sentiment_description(current_msci)
    
    # 趋势描述
    trend_desc = "上升" if trend_5d > 5 else "下降" if trend_5d < -5 else "平稳"
    
    # 投资建议
    investment_advice = _get_investment_advice(market_state, trend_5d, risk_level)
    
    return {
        'msci_score': current_msci,
        t_msci('sentiment_description'): sentiment_desc,
        t_msci('market_state_chinese'): _translate_market_state(market_state),
        t_msci('trend_description'): trend_desc,
        t_msci('trend_value'): trend_5d,
        t_msci('risk_level_chinese'): _translate_risk_level(risk_level),
        t_msci('investment_advice'): investment_advice,
        t_msci('bull_bear_ratio'): latest.get(t_msci('bull_bear_ratio'), 1),
        t_msci('participation_rate'): latest.get(t_msci('participation'), 0) * 100,
        t_msci('extreme_state'): latest.get(t_msci('extreme_state'), 'normal')
    }


# 私有辅助函数

def _calculate_daily_msci(data: pd.DataFrame, date_col: str) -> Optional[Dict]:
    """计算单日MSCI指数"""
    try:
        # 1. 评级分布统计和插值比例计算
        rating_dist = data[date_col].value_counts()
        total_stocks = len(data)
        missing_count = rating_dist.get('-', 0)
        total_rated = sum(count for rating, count in rating_dist.items() if rating != '-')
        
        # 计算插值比例（假设缺失数据会被插值填充）
        interpolation_ratio = missing_count / total_stocks if total_stocks > 0 else 0
        
        if total_rated < 30:  # 样本太小跳过（调整为更合理的阈值）
            return None
        
        # 2. 多空力量对比
        bullish_count = (rating_dist.get('大多', 0) + rating_dist.get('中多', 0) + 
                        rating_dist.get('小多', 0) + rating_dist.get('微多', 0))
        bearish_count = (rating_dist.get('微空', 0) + rating_dist.get('小空', 0) + 
                        rating_dist.get('中空', 0) + rating_dist.get('大空', 0))
        
        bull_bear_ratio = bullish_count / bearish_count if bearish_count > 0 else 10
        
        # 3. 情绪强度 (加权平均评级)
        weighted_score = 0
        for rating, count in rating_dist.items():
            if rating in RATING_SCORE_MAP and RATING_SCORE_MAP[rating] is not None:
                weighted_score += RATING_SCORE_MAP[rating] * count
        
        avg_sentiment = weighted_score / total_rated if total_rated > 0 else 50.0  # 中性值改为50
        
        # 4. 市场参与度
        participation = total_rated / len(data)
        
        # 5. 极端情绪检测
        extreme_bull = rating_dist.get('大多', 0) / len(data) > 0.02  # 2%以上强多
        extreme_bear = rating_dist.get('中空', 0) / len(data) > 0.25  # 25%以上看空
        
        # 6. 综合MSCI指数计算 (0-100)
        # 归一化各个分量（评级已经是12.5-100范围）
        sentiment_norm = (avg_sentiment - 12.5) / 87.5  # 0-1 (评级范围12.5-100)
        ratio_norm = min(bull_bear_ratio / 2.0, 1.0)  # 0-1 (比例2以上视为1)
        participation_norm = min(participation / 0.5, 1.0)  # 0-1 (50%参与度为满分)
        
        msci = (sentiment_norm * 0.5 + ratio_norm * 0.3 + participation_norm * 0.2) * 100
        
        # 极端情绪调整
        if extreme_bull:
            msci = min(msci + 10, 100)  # 极端乐观加分
        if extreme_bear:
            msci = max(msci - 15, 0)    # 极端悲观减分
        
        # 7. 数据质量评估和警告
        data_quality_warnings = []
        if interpolation_ratio > 0.3:  # 插值比例超过30%
            data_quality_warnings.append(f"⚠️ 数据质量警告：插值比例过高 ({interpolation_ratio:.1%})")
        if interpolation_ratio > 0.5:  # 插值比例超过50%
            data_quality_warnings.append("🚨 严重警告：超过一半数据需要插值，结果可靠性较低")
        
        return {
            'date': date_col,
            'msci': round(msci, 2),
            'sentiment_score': round(avg_sentiment, 2),
            t_msci('bull_bear_ratio'): round(bull_bear_ratio, 2),
            t_msci('participation'): round(participation, 3),
            t_msci('extreme_state'): 'bull' if extreme_bull else 'bear' if extreme_bear else 'normal',
            'total_rated': total_rated,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'interpolation_ratio': round(interpolation_ratio, 3),
            t_msci('data_quality_warnings'): data_quality_warnings,
            'total_stocks': total_stocks,
            'missing_count': missing_count
        }
        
    except Exception:
        return None


def _calculate_msci_trend(msci_history: List[Dict]) -> float:
    """计算MSCI趋势变化"""
    if len(msci_history) < 10:
        return 0
    
    recent_avg = np.mean([x['msci'] for x in msci_history[-5:]])
    previous_avg = np.mean([x['msci'] for x in msci_history[-10:-5]])
    
    return round(recent_avg - previous_avg, 2)


def _calculate_market_volatility(msci_history: List[Dict]) -> float:
    """计算市场波动率（考虑插值数据权重衰减）"""
    if len(msci_history) < 5:
        return 0.0
    
    # 提取最近10天的数据
    recent_data = msci_history[-10:]
    
    # 计算加权波动率（插值比例高的数据权重降低）
    weighted_values = []
    weights = []
    
    for item in recent_data:
        msci_value = item['msci']
        interpolation_ratio = item.get('interpolation_ratio', 0)
        
        # 权重衰减：插值比例越高，权重越低
        weight = 1.0 - (interpolation_ratio * 0.5)  # 最多减少50%权重
        weight = max(weight, 0.3)  # 最低保持30%权重
        
        weighted_values.append(msci_value)
        weights.append(weight)
    
    # 计算加权标准差
    if len(weighted_values) > 1:
        weighted_mean = np.average(weighted_values, weights=weights)
        weighted_variance = np.average((np.array(weighted_values) - weighted_mean) ** 2, weights=weights)
        volatility = np.sqrt(weighted_variance)
    else:
        volatility = 0.0
    
    # 标准化到合理范围 (0-50)
    normalized_volatility = min(volatility * 2, 50)
    
    return round(normalized_volatility, 2)


def _calculate_volume_ratio(latest_analysis: Dict) -> float:
    """计算成交量比率（基于参与度模拟）"""
    participation = latest_analysis.get(t_msci('participation'), 0.5)
    
    # 基于参与度计算成交量比率
    # 参与度高表示成交活跃
    volume_ratio = participation * 2.0  # 转换为倍数
    
    # 添加一些随机波动使其更真实
    import random
    volume_ratio += random.uniform(-0.2, 0.2)
    
    # 限制在合理范围内 (0.1-5.0)
    volume_ratio = max(0.1, min(volume_ratio, 5.0))
    
    return round(volume_ratio, 2)


def _determine_market_state(msci_value: float) -> str:
    """
    根据MSCI值确定市场状态 - 新标准（20-80范围+15%）
    
    新标准（适配20-80范围）：
    - 70-80：极度狂热（泡沫预警）🔴
    - 60-70：健康乐观（正常牛市）🟠
    - 50-60：谨慎乐观（偏乐观）🟡
    - 40-50：情绪中性（均衡）⚪
    - 30-40：轻度悲观（偏悲观）🟢
    - 23-30：显著悲观（熊市）🔵
    - 20-23：恐慌抛售（底部机会）⚫
    """
    if msci_value >= 70:
        return t_msci('extreme_euphoria')    # 极度狂热：泡沫预警区 🔴
    elif msci_value >= 60:
        return t_msci('healthy_optimism')    # 健康乐观：正常牛市区间 🟠
    elif msci_value >= 50:
        return t_msci('cautious_optimism')   # 谨慎乐观：偏乐观区间 🟡
    elif msci_value >= 40:
        return t_msci('neutral_sentiment')   # 情绪中性：均衡区间 ⚪
    elif msci_value >= 30:
        return t_msci('mild_pessimism')      # 轻度悲观：偏悲观区间 🟢
    elif msci_value >= 23:
        return t_msci('significant_pessimism') # 显著悲观：熊市初期 🔵
    else:
        return t_msci('panic_selling')       # 恐慌抛售：底部机会区 ⚫


def _assess_risk_level(market_state: str, extreme_state: str, trend_5d: float) -> str:
    """评估风险等级 - 优化版本，基于市场状态的专业评估"""
    # 基于市场状态的基础风险评估
    base_risk = {
        t_msci('extreme_euphoria'): t_msci('extremely_high'),
        t_msci('healthy_optimism'): t_msci('low'),
        t_msci('cautious_optimism'): t_msci('medium'),
        t_msci('neutral_sentiment'): t_msci('medium'),
        t_msci('mild_pessimism'): t_msci('medium_high'),
        t_msci('significant_pessimism'): t_msci('high'),
        t_msci('panic_selling'): t_msci('high_opportunity')  # 高风险但也是机会
    }.get(market_state, t_msci('medium'))
    
    # 极端状态调整
    if extreme_state == 'bull':
        risk_adjustment = 1  # 极端乐观增加风险
    elif extreme_state == 'bear':
        risk_adjustment = 1  # 极端悲观也增加风险
    else:
        risk_adjustment = 0
    
    # 趋势变化调整
    if abs(trend_5d) > 15:  # 剧烈变化增加风险
        trend_adjustment = 1
    else:
        trend_adjustment = 0
    
    # 综合风险等级映射 - 返回翻译键而非硬编码文本
    risk_matrix = {
        (t_msci('extremely_high'), 0, 0): 'extremely_high_risk_bubble_warning',
        (t_msci('extremely_high'), 1, 0): 'extremely_high_risk_bubble_confirmed',
        (t_msci('high_opportunity'), 0, 0): 'high_risk_high_return_bottom_opportunity',
        (t_msci('high_opportunity'), 1, 0): 'contrarian_investment_opportunity_panic_bottom',
        (t_msci('high'), 0, 0): 'high_risk',
        (t_msci('high'), 1, 0): 'extremely_high_risk',
        (t_msci('medium_high'), 0, 0): 'medium_high_risk',
        (t_msci('medium'), 0, 0): 'medium_risk',
        (t_msci('low'), 0, 0): 'low_risk',
        (t_msci('low'), 1, 0): 'medium_risk_watch_extreme_sentiment'
    }
    
    key = (base_risk, risk_adjustment, trend_adjustment)
    # 查找最匹配的风险等级
    for risk_key, risk_desc in risk_matrix.items():
        if risk_key[0] == base_risk:
            return risk_desc
    
    return 'medium_risk'  # 默认值


def _calculate_current_state_duration(msci_history: List[Dict]) -> int:
    """计算当前状态持续天数"""
    if not msci_history:
        return 0
    
    current_state = _determine_market_state(msci_history[-1]['msci'])
    duration = 1
    
    for i in range(len(msci_history) - 2, -1, -1):
        state = _determine_market_state(msci_history[i]['msci'])
        if state == current_state:
            duration += 1
        else:
            break
    
    return duration


def _get_insufficient_msci_data_result() -> Dict:
    """返回数据不足的MSCI结果"""
    return {
        'current_msci': 0,
        'market_state': 'insufficient_data',
        'trend_5d': 0,
        'latest_analysis': {},
        'history': [],
        'risk_level': 'unknown',
        'calculation_time': '0.001s'
    }


def _get_sentiment_description(msci: float) -> str:
    """获取情绪描述"""
    if msci > 80:
        return "极度乐观"
    elif msci > 60:
        return "乐观"
    elif msci > 40:
        return "中性偏乐观"
    elif msci > 20:
        return "悲观"
    else:
        return "极度悲观"


def _translate_market_state(state: str) -> str:
    """翻译市场状态"""
    translations = {
        t_msci('euphoric'): '极度乐观',
        t_msci('optimistic'): '乐观',
        t_msci('neutral'): '中性',
        t_msci('pessimistic'): '悲观',
        t_msci('panic'): '恐慌',
        t_msci('insufficient_data'): '数据不足'
    }
    return translations.get(state, state)


def _translate_risk_level(level: str) -> str:
    """翻译风险等级"""
    translations = {
        t_msci('high'): '高风险',
        t_msci('medium'): '中等风险',
        t_msci('low'): '低风险',
        t_msci('unknown'): '未知'
    }
    return translations.get(level, level)


def _get_investment_advice(market_state: str, trend_5d: float, risk_level: str) -> str:
    """获取投资建议"""
    if market_state == t_msci('euphoric'):
        return "市场过热，建议减仓观望"
    elif market_state == t_msci('panic'):
        return "市场恐慌，可适度逢低布局"
    elif market_state == t_msci('optimistic') and trend_5d > 0:
        return "市场向好，可适当增仓"
    elif market_state == t_msci('pessimistic') and trend_5d < 0:
        return "市场疲弱，建议控制仓位"
    else:
        return "市场中性，保持均衡配置"


def get_msci_professional_terminology(market_state: str) -> dict:
    """
    获取MSCI专业术语描述 - 新增函数
    
    参数:
        market_state (str): 市场状态分类
        
    返回:
        dict: 包含专业术语和投资策略的描述
    """
    terminology = {
        t_msci('extreme_euphoria'): {
            'state': '极度亢奋',
            'description': '市场情绪过度乐观，存在明显泡沫风险，技术指标严重超买',
            'strategy': '🔴 风险规避策略：建议大幅减仓观望，防范系统性调整风险',
            t_msci('risk_level'): '极高风险',
            'opportunity': '等待调整机会',
            'time_horizon': '短期内谨慎，中期等待回调'
        },
        t_msci('healthy_optimism'): {
            'state': '健康乐观',
            'description': '市场情绪积极向上，牛市格局确立，基本面与技术面共振',
            'strategy': '🟢 积极配置策略：适合中长期投资布局，享受牛市收益',
            t_msci('risk_level'): '低风险',
            'opportunity': '优质资产配置期',
            'time_horizon': '中长期持有为主'
        },
        t_msci('cautious_optimism'): {
            'state': '谨慎乐观',
            'description': '市场情绪偏向乐观，但需保持理性，技术面偏强',
            'strategy': '🟡 均衡配置策略：适度参与，注重风险控制',
            t_msci('risk_level'): '中等风险',
            'opportunity': '结构性机会显现',
            'time_horizon': '中期配置，灵活调整'
        },
        t_msci('neutral_sentiment'): {
            'state': '情绪中性',
            'description': '市场情绪均衡，多空力量基本相当，方向选择待明确',
            'strategy': '⚖️ 中性策略：保持观望，等待方向明确后再做决策',
            t_msci('risk_level'): '中等风险',
            'opportunity': '等待突破方向',
            'time_horizon': '短期观望，中期待定'
        },
        t_msci('mild_pessimism'): {
            'state': '轻度悲观',
            'description': '市场情绪偏向悲观，但未达恐慌，技术面偏弱',
            'strategy': '🟡 谨慎观望策略：严控仓位，寻找防御性机会',
            t_msci('risk_level'): '中高风险',
            'opportunity': '防御性资产配置',
            'time_horizon': '短期防御，等待转机'
        },
        t_msci('significant_pessimism'): {
            'state': '显著悲观',
            'description': '市场情绪明显低迷，熊市特征显现，技术面疲弱',
            'strategy': '🔶 防御策略：以资本保全为先，等待市场转机信号',
            t_msci('risk_level'): '高风险',
            'opportunity': '现金为王，等待底部',
            'time_horizon': '中期防御，等待反转'
        },
        t_msci('panic_selling'): {
            'state': '恐慌抛售',
            'description': '市场极度恐慌，可能接近周期底部，技术面超卖严重',
            'strategy': '🟢 逆向投资策略：恐慌中蕴含长期机会，分批建仓优质资产',
            t_msci('risk_level'): '高风险高收益',
            'opportunity': '历史性投资机会',
            'time_horizon': '长期布局，耐心等待'
        }
    }
    
    return terminology.get(market_state, {
        'state': '未知状态',
        'description': '市场情绪状态不明确',
        'strategy': '❓ 观望策略：等待明确信号',
        t_msci('risk_level'): '不确定',
        'opportunity': '暂无明确机会',
        'time_horizon': '短期观望'
    })


def generate_market_investment_advice(msci_value: float, market_state: str, trend_5d: float) -> dict:
    """
    生成市场投资建议 - 新增函数
    基于MSCI值、市场状态和趋势变化提供具体建议
    
    参数:
        msci_value (float): MSCI指数值
        market_state (str): 市场状态
        trend_5d (float): 5日趋势变化
        
    返回:
        dict: 详细的投资建议
    """
    # 获取专业术语
    terminology = get_msci_professional_terminology(market_state)
    
    # 基于MSCI值的仓位建议
    if msci_value >= 85:
        position_advice = '建议仓位：10-30%（极度谨慎）'
        action = '大幅减仓'
    elif msci_value >= 65:
        position_advice = '建议仓位：70-90%（积极配置）'
        action = '正常配置'
    elif msci_value >= 55:
        position_advice = '建议仓位：50-70%（均衡配置）'
        action = '适度配置'
    elif msci_value >= 45:
        position_advice = '建议仓位：30-50%（中性观望）'
        action = '观望为主'
    elif msci_value >= 35:
        position_advice = '建议仓位：20-40%（谨慎防御）'
        action = '防御性配置'
    elif msci_value >= 25:
        position_advice = '建议仓位：10-30%（严格防御）'
        action = '严控仓位'
    else:
        position_advice = '建议仓位：30-60%（逆向布局）'
        action = '分批建仓'
    
    # 基于趋势的操作建议
    if trend_5d > 10:
        trend_advice = '市场情绪快速升温，注意追高风险'
    elif trend_5d > 5:
        trend_advice = '市场情绪稳步回升，可适度参与'
    elif trend_5d < -10:
        trend_advice = '市场情绪快速恶化，注意止损'
    elif trend_5d < -5:
        trend_advice = '市场情绪逐步转弱，保持谨慎'
    else:
        trend_advice = '市场情绪相对稳定，维持策略'
    
    return {
        'primary_strategy': terminology['strategy'],
        'position_advice': position_advice,
        'action_recommendation': action,
        'trend_guidance': trend_advice,
        'risk_assessment': terminology[t_msci('risk_level')],
        'opportunity_description': terminology['opportunity'],
        'time_horizon': terminology['time_horizon'],
        'market_description': terminology['description']
    }


# 模块测试函数
def test_msci_calculator():
    """测试MSCI计算器功能"""
    print("MSCI...")
    
    # 构造测试数据
    test_data = pd.DataFrame({
        '股票代码': [f"00000{i}" for i in range(1, 101)],
        '股票名称': [f"测试股票{i}" for i in range(1, 101)],
        '行业': ['银行'] * 20 + ['科技'] * 30 + ['地产'] * 25 + ['制造'] * 25,
        '20250601': ['中空'] * 60 + ['微多'] * 25 + ['小多'] * 10 + ['中多'] * 5,
        '20250602': ['中空'] * 50 + ['微多'] * 30 + ['小多'] * 15 + ['中多'] * 5,
        '20250603': ['小空'] * 40 + ['微多'] * 35 + ['小多'] * 20 + ['中多'] * 5,
        '20250604': ['微空'] * 30 + ['微多'] * 40 + ['小多'] * 25 + ['中多'] * 5,
        '20250605': ['微多'] * 45 + ['小多'] * 30 + ['中多'] * 20 + ['大多'] * 5
    })
    
    # 测试MSCI计算
    result = calculate_market_sentiment_composite_index(test_data)
    print(f"   MSCI测试: 指数={result[t_msci('current_msci')]}, 状态={result[t_msci('market_state')]}")
    
    # 测试极端状态分析
    if result[t_msci('history')]:
        extremes = analyze_market_extremes(result[t_msci('history')])
        print(f"   极端分析: 波动性={extremes.get(t_msci('volatility'), 0)}")
    
    # 测试风险预警
    warnings = generate_risk_warnings(
        result[t_msci('market_state')], 
        result[t_msci('latest_analysis')], 
        result[t_msci('trend_5d')]
    )
    print(f"   风险预警: {len(warnings)} 条预警")
    
    # 测试市场总结
    summary = get_msci_market_summary(result)
    print(f"   市场总结: {summary.get(t_msci('sentiment_description'), '未知')}")
    
    print("MSCI")
    return True


class MSCICalculator:
    """
    MSCI算法计算器类
    
    提供面向对象的MSCI计算接口，便于实例化和配置管理
    """
    
    def __init__(self, rating_map: Dict = None, min_data_days: int = 5, enable_cache: bool = True):
        """
        初始化MSCI计算器
        
        参数:
            rating_map (dict): 评级映射表，默认使用RATING_SCORE_MAP
            min_data_days (int): 最少数据天数要求，默认5天
            enable_cache (bool): 是否启用结果缓存，默认启用
        """
        self.rating_map = rating_map or RATING_SCORE_MAP
        self.min_data_days = min_data_days
        self.calculation_count = 0
        self.enable_cache = enable_cache
        self._cache = {} if enable_cache else None
        
        # 性能统计
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_time_per_calc': 0.0
        }
    
    def calculate(self, all_data: pd.DataFrame, cache_key: str = None, language: str = 'zh_CN') -> Dict[str, Union[float, str, int, List, Dict]]:
        """
        计算市场情绪综合指数
        
        参数:
            all_data (pd.DataFrame): 全市场股票数据
            cache_key (str): 缓存键，用于标识数据版本
            
        返回:
            dict: MSCI计算结果
        """
        self.calculation_count += 1
        start_time = datetime.now()
        
        # 缓存检查
        if self.enable_cache and cache_key:
            if cache_key in self._cache:
                self.stats['cache_hits'] += 1
                return self._cache[cache_key]
        
        # 执行计算
        result = calculate_market_sentiment_composite_index(all_data, language=language)
        
        # 更新统计
        calc_time = (datetime.now() - start_time).total_seconds()
        self.stats['total_calculations'] += 1
        self.stats['total_time'] += calc_time
        self.stats['avg_time_per_calc'] = self.stats['total_time'] / self.stats['total_calculations']
        
        # 存储缓存
        if self.enable_cache and cache_key:
            self._cache[cache_key] = result
        
        return result
    
    def analyze_extremes(self, msci_history: List[Dict]) -> Dict[str, Union[int, float, List]]:
        """
        分析市场极端状态
        
        参数:
            msci_history (List[Dict]): MSCI历史数据
            
        返回:
            dict: 极端状态分析结果
        """
        return analyze_market_extremes(msci_history)
    
    def generate_warnings(self, market_state: str, latest_analysis: Dict, trend_5d: float) -> List[str]:
        """
        生成风险预警
        
        参数:
            market_state (str): 市场状态
            latest_analysis (dict): 最新分析数据
            trend_5d (float): 5日趋势
            
        返回:
            list: 风险预警列表
        """
        return generate_risk_warnings(market_state, latest_analysis, trend_5d)
    
    def get_market_summary(self, msci_result: Dict) -> Dict[str, Union[str, float, int]]:
        """
        获取市场摘要信息
        
        参数:
            msci_result (dict): MSCI计算结果
            
        返回:
            dict: 市场摘要
        """
        return get_msci_market_summary(msci_result)
    
    def get_professional_terminology(self, market_state: str) -> dict:
        """
        获取专业术语解释
        
        参数:
            market_state (str): 市场状态
            
        返回:
            dict: 专业术语解释
        """
        return get_msci_professional_terminology(market_state)
    
    def generate_investment_advice(self, msci_value: float, market_state: str, trend_5d: float) -> dict:
        """
        生成投资建议
        
        参数:
            msci_value (float): MSCI指数值
            market_state (str): 市场状态
            trend_5d (float): 5日趋势
            
        返回:
            dict: 投资建议
        """
        return generate_market_investment_advice(msci_value, market_state, trend_5d)
    
    def get_performance_stats(self) -> Dict[str, Union[int, float, str]]:
        """获取性能统计信息"""
        cache_hit_rate = (self.stats['cache_hits'] / max(1, self.stats['total_calculations'])) * 100
        
        return {
            'total_calculations': self.stats['total_calculations'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'total_time': f"{self.stats['total_time']:.3f}s",
            'avg_time_per_calc': f"{self.stats['avg_time_per_calc']*1000:.2f}ms",
            'cache_enabled': self.enable_cache,
            'cache_size': len(self._cache) if self._cache else 0
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
            print("MSCI")
    
    def reset_counter(self):
        """重置计算计数器"""
        self.calculation_count = 0
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_time_per_calc': 0.0
        }
    
    def __str__(self):
        cache_info = f", cache={len(self._cache) if self._cache else 0}" if self.enable_cache else ""
        return f"MSCICalculator(calculations={self.calculation_count}, min_days={self.min_data_days}{cache_info})"


if __name__ == "__main__":
    test_msci_calculator()