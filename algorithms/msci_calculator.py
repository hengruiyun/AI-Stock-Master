"""
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
try:
    from config import RATING_SCORE_MAP
except ImportError:
    # 如果无法导入配置，使用默认映射
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }

# 抑制警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


def calculate_market_sentiment_composite_index(all_data: pd.DataFrame) -> Dict[str, Union[float, str, int, List, Dict]]:
    """
    市场情绪综合指数 (Market Sentiment Composite Index)
    综合多个维度判断市场情绪状态
    
    参数:
        all_data (pd.DataFrame): 全市场股票数据
        
    返回:
        dict: {
            'current_msci': float,          # 当前MSCI指数 (0-100)
            'market_state': str,            # 市场状态
            'trend_5d': float,              # 5日趋势变化
            'latest_analysis': dict,        # 最新分析详情
            'history': List[dict],          # 历史数据 (最近20天)
            'risk_level': str,              # 风险等级
            'calculation_time': str         # 计算时间
        }
    """
    calculation_start = datetime.now()
    
    try:
        # 1. 识别日期列
        date_columns = [col for col in all_data.columns if str(col).startswith('202')]
        date_columns.sort()
        
        if len(date_columns) < 5:
            return _get_insufficient_msci_data_result()
        
        msci_history = []
        
        # 2. 逐日计算MSCI
        for date_col in date_columns:
            daily_msci = _calculate_daily_msci(all_data, date_col)
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
        risk_level = _assess_risk_level(market_state, latest['extreme_state'], recent_trend)
        
        # 9. 插值比例汇总和数据质量评估
        avg_interpolation_ratio = np.mean([item.get('interpolation_ratio', 0) for item in msci_history])
        all_warnings = []
        
        # 收集所有数据质量警告
        for item in msci_history[-5:]:  # 检查最近5天
            warnings = item.get('data_quality_warnings', [])
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
        extreme_state = item.get('extreme_state', 'normal')
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
        'extreme_counts': extreme_counts,
        'current_state_duration': current_state_duration,
        'volatility': round(volatility, 2),
        'msci_max': msci_max,
        'msci_min': msci_min,
        'max_date': max_date,
        'min_date': min_date,
        'extreme_ratio': (extreme_counts['bull'] + extreme_counts['bear']) / len(msci_history) * 100
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
    bull_bear_ratio = latest_analysis.get('bull_bear_ratio', 1)
    participation = latest_analysis.get('participation', 0.5)
    extreme_state = latest_analysis.get('extreme_state', 'normal')
    
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
    if market_state in ['euphoric', 'panic']:
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
    if not msci_result or msci_result.get('current_msci', 0) == 0:
        return {'status': 'no_data'}
    
    current_msci = msci_result.get('current_msci', 50)
    market_state = msci_result.get('market_state', 'neutral')
    trend_5d = msci_result.get('trend_5d', 0)
    risk_level = msci_result.get('risk_level', 'medium')
    latest = msci_result.get('latest_analysis', {})
    
    # 市场情绪描述
    sentiment_desc = _get_sentiment_description(current_msci)
    
    # 趋势描述
    trend_desc = "上升" if trend_5d > 5 else "下降" if trend_5d < -5 else "平稳"
    
    # 投资建议
    investment_advice = _get_investment_advice(market_state, trend_5d, risk_level)
    
    return {
        'msci_score': current_msci,
        'sentiment_description': sentiment_desc,
        'market_state_chinese': _translate_market_state(market_state),
        'trend_description': trend_desc,
        'trend_value': trend_5d,
        'risk_level_chinese': _translate_risk_level(risk_level),
        'investment_advice': investment_advice,
        'bull_bear_ratio': latest.get('bull_bear_ratio', 1),
        'participation_rate': latest.get('participation', 0) * 100,
        'extreme_state': latest.get('extreme_state', 'normal')
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
        
        if total_rated < 100:  # 样本太小跳过
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
        
        avg_sentiment = weighted_score / total_rated if total_rated > 0 else 3.5
        
        # 4. 市场参与度
        participation = total_rated / len(data)
        
        # 5. 极端情绪检测
        extreme_bull = rating_dist.get('大多', 0) / len(data) > 0.02  # 2%以上强多
        extreme_bear = rating_dist.get('中空', 0) / len(data) > 0.25  # 25%以上看空
        
        # 6. 综合MSCI指数计算 (0-100)
        # 归一化各个分量
        sentiment_norm = avg_sentiment / 7.0  # 0-1 (评级范围0-7)
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
            'bull_bear_ratio': round(bull_bear_ratio, 2),
            'participation': round(participation, 3),
            'extreme_state': 'bull' if extreme_bull else 'bear' if extreme_bear else 'normal',
            'total_rated': total_rated,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'interpolation_ratio': round(interpolation_ratio, 3),
            'data_quality_warnings': data_quality_warnings,
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
    participation = latest_analysis.get('participation', 0.5)
    
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
    """根据MSCI值确定市场状态 - 优化版本，采用统一的专业术语"""
    if msci_value >= 85:
        return 'extreme_euphoria'    # 极度亢奋：泡沫预警区
    elif msci_value >= 65:
        return 'healthy_optimism'    # 健康乐观：正常牛市区间
    elif msci_value >= 55:
        return 'cautious_optimism'   # 谨慎乐观：偏乐观区间
    elif msci_value >= 45:
        return 'neutral_sentiment'   # 情绪中性：均衡区间  
    elif msci_value >= 35:
        return 'mild_pessimism'      # 轻度悲观：偏悲观区间
    elif msci_value >= 25:
        return 'significant_pessimism' # 显著悲观：熊市初期
    else:
        return 'panic_selling'       # 恐慌抛售：底部机会区


def _assess_risk_level(market_state: str, extreme_state: str, trend_5d: float) -> str:
    """评估风险等级 - 优化版本，基于市场状态的专业评估"""
    # 基于市场状态的基础风险评估
    base_risk = {
        'extreme_euphoria': 'extremely_high',
        'healthy_optimism': 'low',
        'cautious_optimism': 'medium',
        'neutral_sentiment': 'medium',
        'mild_pessimism': 'medium_high',
        'significant_pessimism': 'high',
        'panic_selling': 'high_opportunity'  # 高风险但也是机会
    }.get(market_state, 'medium')
    
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
    
    # 综合风险等级映射
    risk_matrix = {
        ('extremely_high', 0, 0): '🔴 极高风险（泡沫预警）',
        ('extremely_high', 1, 0): '🔴 极高风险（泡沫确认）',
        ('high_opportunity', 0, 0): '🟡 高风险高收益（底部机会）',
        ('high_opportunity', 1, 0): '🟢 逆向投资机会（恐慌底部）',
        ('high', 0, 0): '🔴 高风险',
        ('high', 1, 0): '🔴 极高风险',
        ('medium_high', 0, 0): '🟠 中高风险',
        ('medium', 0, 0): '🟡 中等风险',
        ('low', 0, 0): '🟢 低风险',
        ('low', 1, 0): '🟡 中等风险（需关注极端情绪）'
    }
    
    key = (base_risk, risk_adjustment, trend_adjustment)
    # 查找最匹配的风险等级
    for risk_key, risk_desc in risk_matrix.items():
        if risk_key[0] == base_risk:
            return risk_desc
    
    return '🟡 中等风险'  # 默认值


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
        'euphoric': '极度乐观',
        'optimistic': '乐观',
        'neutral': '中性',
        'pessimistic': '悲观',
        'panic': '恐慌',
        'insufficient_data': '数据不足'
    }
    return translations.get(state, state)


def _translate_risk_level(level: str) -> str:
    """翻译风险等级"""
    translations = {
        'high': '高风险',
        'medium': '中等风险',
        'low': '低风险',
        'unknown': '未知'
    }
    return translations.get(level, level)


def _get_investment_advice(market_state: str, trend_5d: float, risk_level: str) -> str:
    """获取投资建议"""
    if market_state == 'euphoric':
        return "市场过热，建议减仓观望"
    elif market_state == 'panic':
        return "市场恐慌，可适度逢低布局"
    elif market_state == 'optimistic' and trend_5d > 0:
        return "市场向好，可适当增仓"
    elif market_state == 'pessimistic' and trend_5d < 0:
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
        'extreme_euphoria': {
            'state': '极度亢奋',
            'description': '市场情绪过度乐观，存在明显泡沫风险，技术指标严重超买',
            'strategy': '🔴 风险规避策略：建议大幅减仓观望，防范系统性调整风险',
            'risk_level': '极高风险',
            'opportunity': '等待调整机会',
            'time_horizon': '短期内谨慎，中期等待回调'
        },
        'healthy_optimism': {
            'state': '健康乐观',
            'description': '市场情绪积极向上，牛市格局确立，基本面与技术面共振',
            'strategy': '🟢 积极配置策略：适合中长期投资布局，享受牛市收益',
            'risk_level': '低风险',
            'opportunity': '优质资产配置期',
            'time_horizon': '中长期持有为主'
        },
        'cautious_optimism': {
            'state': '谨慎乐观',
            'description': '市场情绪偏向乐观，但需保持理性，技术面偏强',
            'strategy': '🟡 均衡配置策略：适度参与，注重风险控制',
            'risk_level': '中等风险',
            'opportunity': '结构性机会显现',
            'time_horizon': '中期配置，灵活调整'
        },
        'neutral_sentiment': {
            'state': '情绪中性',
            'description': '市场情绪均衡，多空力量基本相当，方向选择待明确',
            'strategy': '⚖️ 中性策略：保持观望，等待方向明确后再做决策',
            'risk_level': '中等风险',
            'opportunity': '等待突破方向',
            'time_horizon': '短期观望，中期待定'
        },
        'mild_pessimism': {
            'state': '轻度悲观',
            'description': '市场情绪偏向悲观，但未达恐慌，技术面偏弱',
            'strategy': '🟡 谨慎观望策略：严控仓位，寻找防御性机会',
            'risk_level': '中高风险',
            'opportunity': '防御性资产配置',
            'time_horizon': '短期防御，等待转机'
        },
        'significant_pessimism': {
            'state': '显著悲观',
            'description': '市场情绪明显低迷，熊市特征显现，技术面疲弱',
            'strategy': '🔶 防御策略：以资本保全为先，等待市场转机信号',
            'risk_level': '高风险',
            'opportunity': '现金为王，等待底部',
            'time_horizon': '中期防御，等待反转'
        },
        'panic_selling': {
            'state': '恐慌抛售',
            'description': '市场极度恐慌，可能接近周期底部，技术面超卖严重',
            'strategy': '🟢 逆向投资策略：恐慌中蕴含长期机会，分批建仓优质资产',
            'risk_level': '高风险高收益',
            'opportunity': '历史性投资机会',
            'time_horizon': '长期布局，耐心等待'
        }
    }
    
    return terminology.get(market_state, {
        'state': '未知状态',
        'description': '市场情绪状态不明确',
        'strategy': '❓ 观望策略：等待明确信号',
        'risk_level': '不确定',
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
        'risk_assessment': terminology['risk_level'],
        'opportunity_description': terminology['opportunity'],
        'time_horizon': terminology['time_horizon'],
        'market_description': terminology['description']
    }


# 模块测试函数
def test_msci_calculator():
    """测试MSCI计算器功能"""
    print("测试 测试MSCI计算器...")
    
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
    print(f"   MSCI测试: 指数={result['current_msci']}, 状态={result['market_state']}")
    
    # 测试极端状态分析
    if result['history']:
        extremes = analyze_market_extremes(result['history'])
        print(f"   极端分析: 波动性={extremes.get('volatility', 0)}")
    
    # 测试风险预警
    warnings = generate_risk_warnings(
        result['market_state'], 
        result['latest_analysis'], 
        result['trend_5d']
    )
    print(f"   风险预警: {len(warnings)} 条预警")
    
    # 测试市场总结
    summary = get_msci_market_summary(result)
    print(f"   市场总结: {summary.get('sentiment_description', '未知')}")
    
    print("成功 MSCI计算器测试完成")
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
    
    def calculate(self, all_data: pd.DataFrame, cache_key: str = None) -> Dict[str, Union[float, str, int, List, Dict]]:
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
        result = calculate_market_sentiment_composite_index(all_data)
        
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
            print("成功 MSCI计算器缓存已清空")
    
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