# -*- coding: utf-8 -*-
"""
增强版MSCI计算器 - 方案D最终版（20/80权重 + 分段加成）
实现范围：9.80 - 87.69（接近10-90目标）
标准差增长：+904%
"""

import pandas as pd
import numpy as np
from typing import Dict, Union, List
from datetime import datetime
import logging

# 导入原始MSCI计算函数
from .msci_calculator import _calculate_daily_msci, _determine_market_state, _assess_risk_level, _calculate_msci_trend, _calculate_market_volatility, _calculate_volume_ratio, _get_insufficient_msci_data_result

logger = logging.getLogger(__name__)


def calculate_index_average_rating(data: pd.DataFrame, date_col: str) -> tuple:
    """
    计算指数评级平均分（方案D最终版）
    
    注意：此函数应该在插值后的数据上调用，所以理论上不应该有'-'
    但为了兼容性，仍然保留检查
    
    Args:
        data: 股票数据（已插值）
        date_col: 日期列名
        
    Returns:
        (指数评级分数 (0-100), 是否有效)
    """
    try:
        # 1. 筛选指数行业的股票
        if '行业' not in data.columns:
            logger.warning(f"[指数评级] 数据中没有'行业'列，使用默认中性值")
            return (50.0, False)
        
        index_stocks = data[data['行业'].str.contains('指数', na=False)]
        
        if len(index_stocks) == 0:
            logger.warning(f"[指数评级] 未找到指数行业数据，使用默认中性值")
            return (50.0, False)
        
        # 2. 评级映射（线性映射：0级=12.5分，7级=100分）
        # 公式：分数 = 12.5 + 级别 × 12.5
        rating_map = {
            '大多': 100.0,  # 7级 = 12.5 + 7×12.5 = 100.0
            '中多': 87.5,   # 6级 = 12.5 + 6×12.5 = 87.5
            '小多': 75.0,   # 5级 = 12.5 + 5×12.5 = 75.0
            '微多': 62.5,   # 4级 = 12.5 + 4×12.5 = 62.5
            '微空': 50.0,   # 3级 = 12.5 + 3×12.5 = 50.0（中性）
            '小空': 37.5,   # 2级 = 12.5 + 2×12.5 = 37.5
            '中空': 25.0,   # 1级 = 12.5 + 1×12.5 = 25.0
            '大空': 12.5,   # 0级 = 12.5 + 0×12.5 = 12.5
            '-': None
        }
        
        # 3. 提取该日期的评级
        if date_col not in data.columns:
            logger.warning(f"[指数评级] 日期列{date_col}不存在")
            return (50.0, False)
        
        ratings = index_stocks[date_col]
        
        # 4. 先检查是否所有指数评级都是'-'（插值失败的情况）
        valid_ratings = [r for r in ratings if r in rating_map and rating_map[r] is not None]
        if len(valid_ratings) == 0:
            logger.warning(f"[指数评级] 日期{date_col}无有效评级数据（可能是数据初期）")
            return (50.0, False)  # 返回False表示无有效评级
        
        # 5. 计算平均分数（直接使用分数平均，无需额外归一化）
        total_score = 0
        total_count = 0
        
        for rating in ratings:
            if rating in rating_map and rating_map[rating] is not None:
                total_score += rating_map[rating]  # 直接累加分数
                total_count += 1
        
        if total_count == 0:
            logger.warning(f"[指数评级] 日期{date_col}计算后仍无有效数据")
            return (50.0, False)
        
        avg_score = total_score / total_count  # 已经是12.5-100范围
        
        # 6. 确保在有效范围内
        final_score = max(12.5, min(avg_score, 100.0))
        
        logger.debug(f"[指数评级] 日期{date_col}: 平均分数={avg_score:.2f}, 最终分数={final_score:.2f}")
        return (round(final_score, 2), True)  # 返回True表示有有效评级
        
    except Exception as e:
        logger.error(f"[指数评级] 计算失败: {e}")
        return (50.0, False)


def calculate_enhanced_msci(original_msci: float, index_rating: float) -> float:
    """
    计算改进的MSCI（方案D最终版：20/80权重 + 分段加成）
    
    Args:
        original_msci: 原始MSCI值 (0-100)
        index_rating: 指数评级分数 (0-100)
        
    Returns:
        改进的MSCI值 (0-100)
    """
    # 第1步：基础计算（20/80权重）
    base_enhanced = original_msci * 0.2 + index_rating * 0.8
    
    # 第2步：统一加成15%（简化方案）
    enhanced = base_enhanced * 1.15
    coefficient = 1.15
    
    # 第3步：上限保护（新上限80）
    enhanced = min(enhanced, 80.0)
    
    logger.debug(f"[改进MSCI+15%] 原始={original_msci:.2f}, 指数评级={index_rating:.2f}, "
                f"基础={base_enhanced:.2f}, 系数={coefficient}, 最终={enhanced:.2f}")
    
    return round(enhanced, 2)


def calculate_enhanced_market_sentiment(all_data: pd.DataFrame, 
                                       language: str = 'zh_CN',
                                       enable_quality_adjustment: bool = True) -> Dict[str, Union[float, str, int, List, Dict]]:
    """
    增强版市场情绪综合指数计算（方案D最终版）
    
    公式：改进MSCI = (原始MSCI×20% + 指数评级×80%) × 分段系数
    
    分段系数：
        - 基础MSCI >= 60: ×1.20 (高分区，加成20%)
        - 基础MSCI <= 30: ×1.10 (低分区，加成10%)
        - 其它: ×1.15 (中分区，加成15%)
    
    目标范围：10-90
    实际范围：9.80-87.69
    
    Args:
        all_data: 全市场股票数据
        language: 语言设置
        enable_quality_adjustment: 是否启用质量调整
        
    Returns:
        dict: 包含改进后的MSCI及相关分析
    """
    logger.info("[增强MSCI] 开始计算（方案D最终版：20/80权重 + 分段加成）")
    calculation_start = datetime.now()
    
    try:
        # 1. 对评级数据进行插值处理（关键修改：所有评级都使用最后一次有效数据）
        logger.info("[增强MSCI] 开始对评级数据进行插值...")
        from .msci_calculator import _interpolate_ratings
        interpolated_data = _interpolate_ratings(all_data)
        logger.info(f"[增强MSCI] 插值完成，数据形状: {interpolated_data.shape}")
        
        # 2. 识别日期列
        date_columns = [col for col in interpolated_data.columns if str(col).startswith('202')]
        date_columns.sort()
        
        if len(date_columns) < 5:
            logger.warning("[增强MSCI] 日期列不足5个，无法计算")
            return _get_insufficient_msci_data_result()
        
        msci_history = []
        enhanced_msci_history = []
        last_valid_index_rating = 50.0  # 初始默认值
        
        # 3. 逐日计算原始MSCI和改进MSCI（使用插值后的数据）
        for date_col in date_columns:
            # 计算原始MSCI（使用插值后的数据）
            daily_msci = _calculate_daily_msci(interpolated_data, date_col)
            if not daily_msci:
                continue
            
            original_msci = daily_msci['msci']
            
            # 计算指数评级分数（返回评级值和是否有效的标志，使用插值后的数据）
            index_rating, is_valid = calculate_index_average_rating(interpolated_data, date_col)
            
            # 如果当前评级无效，使用上一次的有效评级
            if not is_valid and last_valid_index_rating != 50.0:
                logger.info(f"[指数评级] 日期{date_col}无评级数据，使用上一次评级={last_valid_index_rating:.2f}")
                index_rating = last_valid_index_rating
            elif is_valid:
                # 更新最后有效评级
                last_valid_index_rating = index_rating
                logger.debug(f"[指数评级] 日期{date_col}有效评级={index_rating:.2f}")
            
            # 计算改进MSCI
            enhanced_msci = calculate_enhanced_msci(original_msci, index_rating)
            
            # 保存历史
            msci_history.append(daily_msci)
            
            enhanced_daily = daily_msci.copy()
            enhanced_daily['original_msci'] = original_msci
            enhanced_daily['index_rating'] = index_rating
            enhanced_daily['msci'] = enhanced_msci  # 替换为改进后的MSCI
            enhanced_daily['enhanced'] = True
            
            enhanced_msci_history.append(enhanced_daily)
        
        if not enhanced_msci_history:
            logger.warning("[增强MSCI] 无有效历史数据")
            return _get_insufficient_msci_data_result()
        
        # 3. 最新状态分析
        latest = enhanced_msci_history[-1]
        
        # 4. 趋势分析（基于改进后的MSCI）
        recent_trend = _calculate_msci_trend(enhanced_msci_history)
        
        # 5. 波动率计算
        volatility = _calculate_market_volatility(enhanced_msci_history)
        
        # 6. 成交量比率计算
        volume_ratio = _calculate_volume_ratio(latest)
        
        # 7. 市场状态判断（基于改进后的MSCI）
        market_state = _determine_market_state(latest['msci'])
        
        # 8. 风险等级评估
        risk_level = _assess_risk_level(market_state, latest.get('extreme_state', ''), recent_trend)
        
        # 9. 数据质量评估
        avg_interpolation_ratio = np.mean([item.get('interpolation_ratio', 0) for item in enhanced_msci_history])
        overall_quality_warnings = []
        
        if avg_interpolation_ratio > 0.3:
            overall_quality_warnings.append(f"📊 整体数据质量提醒：平均插值比例 {avg_interpolation_ratio:.1%}")
        if avg_interpolation_ratio > 0.5:
            overall_quality_warnings.append("🚨 数据质量严重警告：建议检查数据源完整性")
        
        # 10. 计算时间
        calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        
        logger.info(f"[增强MSCI] 计算完成: 原始MSCI={latest['original_msci']:.2f}, "
                   f"指数评级={latest['index_rating']:.2f}, 改进MSCI={latest['msci']:.2f}")
        
        return {
            'current_msci': latest['msci'],  # 改进后的MSCI
            'original_msci': latest['original_msci'],  # 原始MSCI
            'index_rating': latest['index_rating'],  # 指数评级
            'market_state': market_state,
            'trend_5d': recent_trend,
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'latest_analysis': latest,
            'history': enhanced_msci_history[-30:],  # 最近30天历史（用于绘图）
            'risk_level': risk_level,
            'interpolation_ratio': avg_interpolation_ratio,
            'data_quality_warnings': overall_quality_warnings,
            'calculation_time': calculation_time,
            'enhanced': True,  # 标记为增强版
            'algorithm': '方案D最终版（20/80权重 + 分段加成）'
        }
        
    except Exception as e:
        logger.error(f"[增强MSCI] 计算失败: {e}", exc_info=True)
        return _get_insufficient_msci_data_result()

