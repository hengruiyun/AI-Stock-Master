"""
from config.i18n import t_gui as _
RTSI算法 - 评级趋势强度指数 (Rating Trend Strength Index)

核心功能：
1. 个股评级趋势强度计算
2. 趋势方向性、一致性、持续性、幅度综合分析
3. 批量计算和排名功能

算法原理：
- 方向性：线性回归斜率
- 一致性：R²值 
- 显著性：p值检验
- 幅度：标准化变化幅度
- RTSI指数：综合评分 (0-100)

作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional, Union
import warnings
from datetime import datetime

# 导入配置

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

def get_rating_score_map():
    """获取评级分数映射"""
    return {
        t_rtsi('rating_strong_buy'): 7, 
        t_rtsi('rating_buy'): 6, 
        t_rtsi('rating_moderate_buy'): 5, 
        t_rtsi('rating_slight_buy'): 4,
        t_rtsi('rating_slight_sell'): 3, 
        t_rtsi('rating_moderate_sell'): 2, 
        t_rtsi('rating_sell'): 1, 
        t_rtsi('rating_strong_sell'): 0, 
        '-': None
    }

try:
    from config import RATING_SCORE_MAP
except ImportError:
    # 如果无法导入配置，使用动态映射
    RATING_SCORE_MAP = get_rating_score_map()

# 抑制scipy的警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


def calculate_ai_enhanced_rtsi_optimized(stock_ratings, stock_code=None, stock_name=None):
    """AI增强RTSI算法 - 简化版"""
    try:
        # 数据质量检查
        valid_count = sum(1 for r in stock_ratings if str(r).strip() not in ['-', '', 'nan', 'None'])
        data_quality = valid_count / len(stock_ratings)
        
        if data_quality >= 0.3 and valid_count >= 3:
            try:
                from algorithms.ai_enhanced_signal_analyzer import AIEnhancedSignalAnalyzer
                
                ai_analyzer = AIEnhancedSignalAnalyzer(enable_ai_features=True)
                
                # 准备数据
                stock_df = pd.DataFrame({
                    '股票代码': [stock_code or 'UNKNOWN'],
                    '股票名称': [stock_name or 'UNKNOWN']
                })
                
                date_columns = [col for col in stock_ratings.index if str(col).startswith('202')]
                for col in date_columns:
                    stock_df[col] = [stock_ratings.get(col, '-')]
                
                # AI分析
                ai_result = ai_analyzer.comprehensive_analyze(
                    stock_data=stock_df,
                    stock_code=stock_code or 'UNKNOWN',
                    enable_prediction=True
                )
                
                ai_score = ai_result.ai_enhanced_score
                
                if ai_score >= 10:
                    # 获取基础RTSI
                    base_result = calculate_rating_trend_strength_index_base(stock_ratings)
                    base_rtsi = base_result.get('rtsi', 0)
                    
                    # 融合分数
                    if base_rtsi > 0:
                        final_score = ai_score * 0.7 + base_rtsi * 0.3
                    else:
                        final_score = ai_score * 0.8
                    
                    result = base_result.copy()
                    result['rtsi'] = round(final_score, 2)
                    result['algorithm'] = 'ai_enhanced'
                    return result
            except:
                pass
        
        # 回退到基础RTSI
        return calculate_rating_trend_strength_index_base(stock_ratings)
        
    except:
        return {'rtsi': 0, 'trend': 'error', 'confidence': 0}

def calculate_rating_trend_strength_index_base(stock_ratings: pd.Series, language: str = 'zh_CN') -> Dict[str, Union[float, str, int, None]]:
    """原始RTSI算法 - 作为AI增强的基础"""

def calculate_rating_trend_strength_index(stock_ratings: pd.Series, language: str = 'zh_CN', stock_code: str = None, stock_name: str = None, enable_ai: bool = True) -> Dict[str, Union[float, str, int, None]]:
    """
    评级趋势强度指数 (Rating Trend Strength Index) - AI增强版本
    综合考虑：方向性、一致性、持续性、幅度，并集成AI增强功能
    
    参数:
        stock_ratings (pd.Series): 股票评级序列，索引为日期，值为评级
        language (str): 语言设置
        stock_code (str): 股票代码
        stock_name (str): 股票名称  
        enable_ai (bool): 是否启用AI增强功能
        
    返回:
        dict: {
            t_rtsi('rtsi'): float,              # RTSI指数 (0-100)
            t_rtsi('trend'): str,               # 趋势方向
            'algorithm': str,                   # 使用的算法类型
            ...
        }
    """
    # 主算法：AI增强RTSI（优先使用）
    if enable_ai:
        try:
            ai_result = calculate_ai_enhanced_rtsi_optimized(stock_ratings, stock_code, stock_name)
            if ai_result.get('algorithm') == 'ai_enhanced':
                # AI增强成功，返回结果
                ai_result['primary_algorithm'] = 'ai_enhanced_rtsi'
                ai_result['fallback_used'] = False
                return ai_result
        except Exception as e:
            # AI增强失败，记录但继续使用基础算法
            print(f"⚠️ AI增强RTSI失败，使用基础算法: {str(e)}")
    
    # 容错方案：基础RTSI算法
    base_result = calculate_rating_trend_strength_index_base(stock_ratings, language)
    base_result['primary_algorithm'] = 'basic_rtsi'
    base_result['fallback_used'] = not enable_ai
    if enable_ai:
        base_result['fallback_reason'] = 'ai_enhancement_failed'
    
    return base_result

def calculate_rating_trend_strength_index_base(stock_ratings: pd.Series, language: str = 'zh_CN') -> Dict[str, Union[float, str, int, None]]:
    """
    原始RTSI算法 - 作为AI增强的基础
    评级趋势强度指数 (Rating Trend Strength Index)
    综合考虑：方向性、一致性、持续性、幅度
    
    参数:
        stock_ratings (pd.Series): 股票评级序列，索引为日期，值为评级
            t_rtsi('confidence'): float,        # 置信度 (0-1)
            t_rtsi('slope'): float,             # 回归斜率
            t_rtsi('r_squared'): float,         # R²值
            t_rtsi('recent_score'): int,        # 最新评级分数
            t_rtsi('score_change_5d'): float,   # 5日变化
            t_rtsi('data_points'): int,         # 有效数据点数
            'calculation_time': str     # 计算时间
        }
    """
    # 设置语言
    set_language(language)
    calculation_start = datetime.now()
    
    # 1. 数据预处理和插值比例计算
    if stock_ratings is None or len(stock_ratings) == 0:
        return _get_insufficient_data_result()
    
    # 计算插值比例
    total_data_points = len(stock_ratings)
    def is_missing(rating):
        try:
            return rating == '-' or pd.isna(rating)
        except:
            return str(rating) in ['-', 'nan', 'None', '<NA>']
    
    missing_count = sum(1 for rating in stock_ratings if is_missing(rating))
    interpolation_ratio = missing_count / total_data_points if total_data_points > 0 else 0
    
    # 获取动态评级映射表
    try:
        extended_rating_map = RATING_SCORE_MAP.copy()
    except:
        extended_rating_map = get_rating_score_map()
    
    # 添加可能缺失的评级映射（兼容旧数据）
    additional_mappings = {
        # 数字评级映射
        7: 7, 6: 6, 5: 5, 4: 4, 3: 3, 2: 2, 1: 1, 0: 0,
        # 中文评级映射
        '看多': 6, '看空': 1, '中性': 4,
        '强烈买入': 7, '买入': 6, '谨慎买入': 5,
        '谨慎卖出': 3, '卖出': 2, '强烈卖出': 1,
        # 英文评级映射
        'Strong Buy': 7, 'Buy': 6, 'Moderate Buy': 5, 'Slight Buy': 4,
        'Slight Sell': 3, 'Moderate Sell': 2, 'Sell': 1, 'Strong Sell': 0,
        'Hold': 4
    }
    for rating, score in additional_mappings.items():
        if rating not in extended_rating_map:
            extended_rating_map[rating] = score
    
    # 将评级转换为分数
    scores = stock_ratings.map(extended_rating_map).dropna()
    
    # 优化：降低最小数据点要求从5到3
    if len(scores) < 3:
        return _get_insufficient_data_result(len(scores))
    
    try:
        # 2. 线性回归分析 - 趋势方向性
        x = np.arange(len(scores))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, scores)
        
        # 3. 趋势一致性 (R²值)
        consistency = r_value ** 2
        
        # 4. 趋势显著性 (p值检验) - 优化：放宽p值阈值到0.1
        significance = max(0, 1 - p_value) if p_value < 0.1 else 0
        
        # 5. 变化幅度 (标准化到8级评级范围: 0-7)
        rating_scale_max = 7  # 8级评级系统：大多=7到大空=0
        amplitude = abs(slope) * len(scores) / rating_scale_max
        amplitude = min(amplitude, 1.0)  # 限制在[0,1]范围
        
        # 6. 综合RTSI指数计算 (0-100)
        # 优化权重分配：一致性45% + 显著性25% + 幅度30%
        rtsi = (consistency * 0.45 + significance * 0.25 + amplitude * 0.30) * 100
        
        # 6.5. 基础分数保障机制 - 优化：避免过多零分
        if rtsi < 3 and (consistency > 0.1 or amplitude > 0.1):
            rtsi = 3  # 最低给3分
        
        # 7. 趋势方向判断
        trend_direction = _determine_trend_direction(slope, significance)
        
        # 8. 计算附加指标
        recent_score = int(scores.iloc[-1]) if len(scores) > 0 else None
        score_change_5d = _calculate_score_change(scores, 5)
        
        # 9. 数据质量评估和警告
        data_quality_warnings = []
        if interpolation_ratio > 0.3:  # 插值比例超过30%
            data_quality_warnings.append(f"⚠️ 数据质量警告：插值比例过高 ({interpolation_ratio:.1%})")
        if interpolation_ratio > 0.5:  # 插值比例超过50%
            data_quality_warnings.append("🚨 严重警告：超过一半数据需要插值，RTSI结果可靠性较低")
        
        # 10. 计算时间
        calculation_time = f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        
        return {
            t_rtsi('rtsi'): round(rtsi, 2),
            t_rtsi('trend'): trend_direction,
            t_rtsi('confidence'): round(significance, 3),
            t_rtsi('slope'): round(slope, 4),
            t_rtsi('r_squared'): round(consistency, 3),
            t_rtsi('recent_score'): recent_score,
            t_rtsi('score_change_5d'): score_change_5d,
            t_rtsi('data_points'): len(scores),
            t_rtsi('calculation_time'): calculation_time,
            'interpolation_ratio': round(interpolation_ratio, 3),
            'data_quality_warnings': data_quality_warnings,
            'total_data_points': total_data_points,
            'missing_count': missing_count
        }
        
    except Exception as e:
        return {
            t_rtsi('rtsi'): 0,
            t_rtsi('trend'): t_rtsi('calculation_error'),
            t_rtsi('confidence'): 0,
            'error': str(e),
            t_rtsi('data_points'): len(scores),
            t_rtsi('calculation_time'): f"{(datetime.now() - calculation_start).total_seconds():.3f}s"
        }


def batch_calculate_rtsi(stock_data: pd.DataFrame, language: str = 'zh_CN') -> Dict[str, Dict]:
    """
    批量计算所有股票的RTSI指数
    
    参数:
        stock_data (pd.DataFrame): 股票数据，列包含股票代码、名称和各日期评级
        
    返回:
        dict: {stock_code: rtsi_result, ...}
    """
    # 设置语言
    set_language(language)
    
    if stock_data is None or len(stock_data) == 0:
        return {}
    
    batch_start = datetime.now()
    results = {}
    
    # 识别日期列
    date_columns = [col for col in stock_data.columns if str(col).startswith('202')]
    date_columns.sort()  # 确保日期排序
    
    if len(date_columns) == 0:
        print("")
        return {}
    
    print(f"数据 开始批量计算RTSI指数...")
    print(f"   数据规模: {len(stock_data)} 只股票 × {len(date_columns)} 个交易日")
    
    # 批量处理
    for idx, row in stock_data.iterrows():
        stock_code = str(row.get('股票代码', f'STOCK_{idx}'))
        stock_name = row.get('股票名称', '未知股票')
        
        # 提取该股票的评级序列
        stock_ratings = row[date_columns]
        
        # 计算RTSI
        rtsi_result = calculate_rating_trend_strength_index(stock_ratings)
        
        # 添加股票基本信息
        rtsi_result.update({
            t_rtsi('stock_code'): stock_code,
            t_rtsi('stock_name'): stock_name,
            t_rtsi('industry'): row.get('行业', '未分类')
        })
        
        results[stock_code] = rtsi_result
        
        # 进度提示
        if (idx + 1) % 1000 == 0:
            print(f"   已处理: {idx + 1:,} / {len(stock_data):,} 只股票")
    
    batch_time = (datetime.now() - batch_start).total_seconds()
    print(f"成功 批量计算完成: {len(results)} 只股票，耗时 {batch_time:.2f} 秒")
    print(f"   平均速度: {len(results) / batch_time:.1f} 只/秒")
    
    return results


def get_rtsi_ranking(rtsi_results: Dict[str, Dict], top_n: int = 50, 
                    trend_filter: Optional[str] = None) -> List[Tuple[str, str, float, str]]:
    """
    获取RTSI指数排名
    
    参数:
        rtsi_results (dict): 批量计算的RTSI结果
        top_n (int): 返回前N名，默认50
        trend_filter (str): 趋势过滤器，可选值: 'up', 'down', t_rtsi('strong_up'), t_rtsi('strong_down')
        
    返回:
        list: [(stock_code, stock_name, rtsi, trend), ...] 按RTSI降序排列
    """
    if not rtsi_results:
        return []
    
    # 过滤有效结果
    valid_results = []
    for stock_code, result in rtsi_results.items():
        if result.get(t_rtsi('rtsi'), 0) > 0:  # 排除计算失败的结果
            # 趋势过滤
            if trend_filter:
                trend = result.get(t_rtsi('trend'), '')
                if trend_filter == 'up' and 'up' not in trend:
                    continue
                elif trend_filter == 'down' and 'down' not in trend:
                    continue
                elif trend_filter == t_rtsi('strong_up') and trend != t_rtsi('strong_up'):
                    continue
                elif trend_filter == t_rtsi('strong_down') and trend != t_rtsi('strong_down'):
                    continue
            
            valid_results.append((
                stock_code,
                result.get(t_rtsi('stock_name'), '未知'),
                result.get(t_rtsi('rtsi'), 0),
                result.get(t_rtsi('trend'), 'unknown'),
                result.get(t_rtsi('confidence'), 0),
                result.get(t_rtsi('recent_score'), 0)
            ))
    
    # 按RTSI指数降序排序
    valid_results.sort(key=lambda x: x[2], reverse=True)
    
    # 返回前N名
    return [(code, name, rtsi, trend) for code, name, rtsi, trend, conf, score in valid_results[:top_n]]


def get_rtsi_statistics(rtsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float]]:
    """
    获取RTSI计算的统计信息
    
    参数:
        rtsi_results (dict): 批量计算的RTSI结果
        
    返回:
        dict: 统计信息
    """
    if not rtsi_results:
        return {}
    
    valid_rtsi = [result[t_rtsi('rtsi')] for result in rtsi_results.values() 
                  if result.get(t_rtsi('rtsi'), 0) > 0]
    
    if not valid_rtsi:
        return {'total_stocks': len(rtsi_results), 'valid_calculations': 0}
    
    # 趋势分布统计
    trend_counts = {}
    for result in rtsi_results.values():
        trend = result.get(t_rtsi('trend'), 'unknown')
        trend_counts[trend] = trend_counts.get(trend, 0) + 1
    
    return {
        'total_stocks': len(rtsi_results),
        'valid_calculations': len(valid_rtsi),
        'success_rate': len(valid_rtsi) / len(rtsi_results) * 100,
        'rtsi_mean': np.mean(valid_rtsi),
        'rtsi_median': np.median(valid_rtsi),
        'rtsi_std': np.std(valid_rtsi),
        'rtsi_max': max(valid_rtsi),
        'rtsi_min': min(valid_rtsi),
        'trend_distribution': trend_counts
    }


# 私有辅助函数

def _get_insufficient_data_result(data_points: int = 0) -> Dict:
    """返回数据不足的结果"""
    return {
        t_rtsi('rtsi'): 0,
        t_rtsi('trend'): t_rtsi('insufficient_data'),
        t_rtsi('confidence'): 0,
        t_rtsi('slope'): 0,
        t_rtsi('r_squared'): 0,
        t_rtsi('recent_score'): None,
        t_rtsi('score_change_5d'): None,
        t_rtsi('data_points'): data_points,
        t_rtsi('calculation_time'): '0.001s'
    }


def _determine_trend_direction(slope: float, significance: float) -> str:
    """
    根据斜率和显著性确定趋势方向 - 优化版本
    采用统一的7级分类标准，基于统计学原理
    
    参数:
        slope (float): 回归斜率
        significance (float): 显著性水平
        
    返回:
        str: 趋势方向描述（统一标准）
    """
    # 先计算基础RTSI分数用于分类
    if significance < 0.3:  # 显著性太低，归为横盘
        return t_rtsi('neutral')
    
    # 基于斜率强度和显著性的组合判断
    if slope > 0.15 and significance > 0.7:
        return t_rtsi('strong_bull')      # 强势多头趋势
    elif slope > 0.08 and significance > 0.5:
        return t_rtsi('moderate_bull')    # 温和多头趋势
    elif slope > 0.03:
        return t_rtsi('weak_bull')        # 弱势多头格局
    elif slope < -0.15 and significance > 0.7:
        return t_rtsi('strong_bear')      # 强势空头趋势
    elif slope < -0.08 and significance > 0.5:
        return t_rtsi('moderate_bear')    # 温和空头趋势
    elif slope < -0.03:
        return t_rtsi('weak_bear')        # 弱势空头格局
    else:
        return t_rtsi('neutral')          # 横盘整理格局


def classify_rtsi_by_value(rtsi_value: float) -> str:
    """
    根据RTSI数值进行统一分类 - 新增函数
    采用基于统计学分析的7级分类标准
    
    参数:
        rtsi_value (float): RTSI指数值 (0-100)
        
    返回:
        str: 统一的趋势分类
    """
    if rtsi_value >= 75:
        return t_rtsi('strong_bull')      # 强势多头：统计学上位数(90%+)
    elif rtsi_value >= 60:
        return t_rtsi('moderate_bull')    # 温和多头：上四分位数(75%+)
    elif rtsi_value >= 50:
        return t_rtsi('weak_bull')        # 弱势多头：中位数以上
    elif rtsi_value >= 40:
        return t_rtsi('neutral')          # 横盘整理：中性区间
    elif rtsi_value >= 30:
        return t_rtsi('weak_bear')        # 弱势空头：下四分位数(25%+)
    elif rtsi_value >= 20:
        return t_rtsi('moderate_bear')    # 温和空头：较低分位数
    else:
        return t_rtsi('strong_bear')      # 强势空头：最低分位数


def get_professional_terminology(trend_category: str) -> dict:
    """
    获取专业术语描述 - 新增函数
    
    参数:
        trend_category (str): 趋势分类
        
    返回:
        dict: 包含简短和详细描述的专业术语
    """
    terminology = {
        t_rtsi('strong_bull'): {
            'short': '强势多头',
            'detailed': '强势多头趋势，技术面极度乐观，建议积极配置',
            'english': 'Strong Bullish Trend',
            'confidence_required': 0.7
        },
        t_rtsi('moderate_bull'): {
            'short': '温和多头', 
            'detailed': '温和多头趋势，上升动能充足，适合中线持有',
            'english': 'Moderate Bullish Trend',
            'confidence_required': 0.5
        },
        t_rtsi('weak_bull'): {
            'short': '弱势多头',
            'detailed': '弱势多头格局，上升空间有限，谨慎乐观',
            'english': 'Weak Bullish Bias',
            'confidence_required': 0.4
        },
        t_rtsi('neutral'): {
            'short': '横盘整理',
            'detailed': '横盘整理格局，方向选择待定，观望为主',
            'english': 'Sideways Consolidation',
            'confidence_required': 0.3
        },
        t_rtsi('weak_bear'): {
            'short': '弱势空头',
            'detailed': '弱势空头格局，下跌空间有限，适度防御',
            'english': 'Weak Bearish Bias', 
            'confidence_required': 0.4
        },
        t_rtsi('moderate_bear'): {
            'short': '温和空头',
            'detailed': '温和空头趋势，下跌动能充足，建议减仓',
            'english': 'Moderate Bearish Trend',
            'confidence_required': 0.5
        },
        t_rtsi('strong_bear'): {
            'short': '强势空头',
            'detailed': '强势空头趋势，技术面极度悲观，严格风控',
            'english': 'Strong Bearish Trend',
            'confidence_required': 0.7
        }
    }
    
    return terminology.get(trend_category, {
        'short': '未知趋势',
        'detailed': '趋势方向不明确，建议谨慎操作',
        'english': 'Unknown Trend',
        'confidence_required': 0.5
    })


def calculate_risk_level_unified(rtsi_value: float, confidence: float) -> str:
    """
    统一的风险等级评估 - 新增函数
    基于RTSI值和置信度的综合评估
    
    参数:
        rtsi_value (float): RTSI指数值
        confidence (float): 置信度
        
    返回:
        str: 风险等级描述
    """
    # 基于RTSI值和置信度的矩阵评估
    if rtsi_value >= 75 and confidence >= 0.7:
        return '🟢 极低风险（强势确认）'
    elif rtsi_value >= 75 and confidence >= 0.4:
        return '🟡 中等风险（强势待确认）'
    elif rtsi_value >= 60 and confidence >= 0.5:
        return '🟢 低风险（温和上升）'
    elif rtsi_value >= 50 and confidence >= 0.4:
        return '🟡 中等风险（弱势多头）'
    elif rtsi_value >= 40:
        return '🟡 中等风险（中性区间）'
    elif rtsi_value >= 30:
        return '🟠 较高风险（弱势空头）'
    elif rtsi_value >= 20 and confidence >= 0.5:
        return '🔴 高风险（温和下跌）'
    elif rtsi_value < 20 and confidence >= 0.7:
        return '🔴 极高风险（强势下跌确认）'
    else:
        return '🔴 高风险'


def _calculate_score_change(scores: pd.Series, days: int) -> Optional[float]:
    """
    计算指定天数的评级分数变化
    
    参数:
        scores (pd.Series): 评级分数序列
        days (int): 计算天数
        
    返回:
        float: 分数变化，如果数据不足返回None
    """
    if len(scores) < days + 1:
        return None
    
    return float(scores.iloc[-1] - scores.iloc[-(days + 1)])


# 模块测试函数
def test_rtsi_calculator():
    """测试RTSI计算器功能"""
    print("RTSI...")
    
    # 构造测试数据
    test_ratings = pd.Series([
        '中空', '小空', '微空', '微多', '小多', '中多', '大多'
    ])
    
    # 测试单个计算
    result = calculate_rating_trend_strength_index(test_ratings)
    print(f"   测试结果: RTSI={result[t_rtsi('rtsi')]}, 趋势={result[t_rtsi('trend')]}")
    
    # 构造批量测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '000003'],
        '股票名称': ['测试股票A', '测试股票B', '测试股票C'],
        '行业': ['银行', '地产', '科技'],
        '20250601': ['中空', '微多', '大多'],
        '20250602': ['小空', '小多', '中多'],
        '20250603': ['微空', '中多', '小多'],
        '20250604': ['微多', '大多', '微多'],
        '20250605': ['小多', '中多', '微空']
    })
    
    # 测试批量计算
    batch_results = batch_calculate_rtsi(test_data)
    print(f"   批量测试: 处理 {len(batch_results)} 只股票")
    
    # 测试排名
    ranking = get_rtsi_ranking(batch_results, top_n=3)
    print(f"   排名测试: 前3名获取成功")
    
    # 测试统计
    stats = get_rtsi_statistics(batch_results)
    print(f"   统计测试: 成功率 {stats.get('success_rate', 0):.1f}%")
    
    print("RTSI")
    return True


if __name__ == "__main__":
    test_rtsi_calculator()


class RTSICalculator:
    """
    RTSI算法计算器类
    
    提供面向对象的RTSI计算接口，便于实例化和配置管理
    """
    
    def __init__(self, rating_map: Dict = None, min_data_points: int = 5, enable_cache: bool = True):
        """
        初始化RTSI计算器
        
        参数:
            rating_map (dict): 评级映射表，默认使用RATING_SCORE_MAP
            min_data_points (int): 最少数据点要求，默认5个
            enable_cache (bool): 是否启用结果缓存，默认启用
        """
        self.rating_map = rating_map or RATING_SCORE_MAP
        self.min_data_points = min_data_points
        self.calculation_count = 0
        self.enable_cache = enable_cache
        self._cache = {} if enable_cache else None
        
        # 性能统计
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_time_per_stock': 0.0
        }
    
    def calculate(self, stock_ratings: pd.Series, stock_code: str = None, language: str = 'zh_CN') -> Dict[str, Union[float, str, int, None]]:
        """
        计算单只股票的RTSI指数
        
        参数:
            stock_ratings (pd.Series): 股票评级序列
            stock_code (str): 股票代码，用于缓存键
            language (str): 语言设置
            
        返回:
            dict: RTSI计算结果
        """
        self.calculation_count += 1
        start_time = datetime.now()
        
        # 缓存检查
        if self.enable_cache and stock_code:
            cache_key = self._generate_cache_key(stock_ratings, stock_code)
            if cache_key in self._cache:
                self.stats['cache_hits'] += 1
                return self._cache[cache_key]
        
        # 执行计算
        result = calculate_rating_trend_strength_index(stock_ratings, language=language)
        
        # 更新统计
        calc_time = (datetime.now() - start_time).total_seconds()
        self.stats['total_calculations'] += 1
        self.stats['total_time'] += calc_time
        self.stats['avg_time_per_stock'] = self.stats['total_time'] / self.stats['total_calculations']
        
        # 存储缓存
        if self.enable_cache and stock_code:
            self._cache[cache_key] = result
        
        return result
    
    def batch_calculate_optimized(self, stock_data: pd.DataFrame, parallel: bool = False, language: str = 'zh_CN') -> Dict[str, Dict]:
        """
        优化的批量计算RTSI指数
        
        参数:
            stock_data (pd.DataFrame): 股票数据
            parallel (bool): 是否使用并行计算（大数据集推荐）
            language (str): 语言设置
            
        返回:
            dict: 批量计算结果
        """
        if parallel and len(stock_data) > 1000:
            return self._parallel_batch_calculate(stock_data, language=language)
        else:
            return batch_calculate_rtsi(stock_data, language=language)
    
    def _parallel_batch_calculate(self, stock_data: pd.DataFrame, language: str = 'zh_CN') -> Dict[str, Dict]:
        """
        并行批量计算（预留接口）
        """
        # 当前使用标准批量计算，后续可集成multiprocessing
        print("...")
        return batch_calculate_rtsi(stock_data, language=language)
    
    def _generate_cache_key(self, stock_ratings: pd.Series, stock_code: str) -> str:
        """生成缓存键"""
        ratings_hash = hash(tuple(stock_ratings.dropna().values))
        return f"{stock_code}_{ratings_hash}"
    
    def get_performance_stats(self) -> Dict[str, Union[int, float, str]]:
        """获取性能统计信息"""
        cache_hit_rate = (self.stats['cache_hits'] / max(1, self.stats['total_calculations'])) * 100
        
        return {
            'total_calculations': self.stats['total_calculations'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'total_time': f"{self.stats['total_time']:.3f}s",
            'avg_time_per_stock': f"{self.stats['avg_time_per_stock']*1000:.2f}ms",
            'cache_enabled': self.enable_cache,
            'cache_size': len(self._cache) if self._cache else 0
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
            print("RTSI")
    
    def batch_calculate(self, stock_data: pd.DataFrame, language: str = 'zh_CN') -> Dict[str, Dict]:
        """
        批量计算RTSI指数
        
        参数:
            stock_data (pd.DataFrame): 股票数据
            language (str): 语言设置
            
        返回:
            dict: 批量计算结果
        """
        return self.batch_calculate_optimized(stock_data, parallel=False, language=language)
    
    def get_ranking(self, rtsi_results: Dict[str, Dict], top_n: int = 50, 
                   trend_filter: Optional[str] = None) -> List[Tuple[str, str, float, str]]:
        """
        获取RTSI排名
        
        参数:
            rtsi_results (dict): RTSI计算结果
            top_n (int): 返回前N名
            trend_filter (str): 趋势过滤器
            
        返回:
            list: 排名结果
        """
        return get_rtsi_ranking(rtsi_results, top_n, trend_filter)
    
    def get_statistics(self, rtsi_results: Dict[str, Dict]) -> Dict[str, Union[int, float]]:
        """
        获取RTSI统计信息
        
        参数:
            rtsi_results (dict): RTSI计算结果
            
        返回:
            dict: 统计信息
        """
        return get_rtsi_statistics(rtsi_results)
    
    def reset_counter(self):
        """重置计算计数器"""
        self.calculation_count = 0
        self.stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'total_time': 0.0,
            'avg_time_per_stock': 0.0
        }
    
    def __str__(self):
        cache_info = f", cache={len(self._cache) if self._cache else 0}" if self.enable_cache else ""
        return f"RTSICalculator(calculations={self.calculation_count}, min_points={self.min_data_points}{cache_info})"

# ========== AI增强RTSI算法集成 ==========

# AI增强RTSI算法 - 最佳配置集成
from algorithms.ai_enhanced_signal_analyzer import AIEnhancedSignalAnalyzer

# 全局AI分析器实例
_ai_analyzer = None

def get_ai_analyzer():
    global _ai_analyzer
    if _ai_analyzer is None:
        _ai_analyzer = AIEnhancedSignalAnalyzer(enable_ai_features=True)
    return _ai_analyzer

def calculate_ai_enhanced_rtsi_best(stock_ratings: pd.Series, 
                                   stock_code: str = None,
                                   stock_name: str = None) -> Dict[str, Union[float, str, int, None]]:
    """
    AI增强RTSI算法 - 最佳配置版本
    
    最佳参数:
    - AI权重: 0.7
    - 数据质量阈值: 0.2
    - 最小AI分数: 15
    """
    try:
        # 计算数据质量
        total_points = len(stock_ratings)
        valid_points = sum(1 for rating in stock_ratings 
                          if str(rating).strip() not in ['-', '', 'nan', 'None'])
        data_quality = valid_points / total_points if total_points > 0 else 0
        
        # AI增强条件
        use_ai = (data_quality >= 0.2 and valid_points >= 3)
        
        if use_ai:
            try:
                ai_analyzer = get_ai_analyzer()
                
                # 准备数据
                stock_df = pd.DataFrame({
                    '股票代码': [stock_code or 'UNKNOWN'],
                    '股票名称': [stock_name or 'UNKNOWN']
                })
                
                # 添加评级数据
                for col in stock_ratings.index:
                    if str(col).startswith('202'):
                        stock_df[col] = [stock_ratings.get(col, '-')]
                
                # AI分析
                ai_result = ai_analyzer.comprehensive_analyze(
                    stock_data=stock_df,
                    stock_code=stock_code or 'UNKNOWN',
                    enable_prediction=True
                )
                
                ai_score = ai_result.ai_enhanced_score
                
                if ai_score >= 15:
                    # 获取基础RTSI
                    base_result = calculate_rating_trend_strength_index(stock_ratings)
                    base_rtsi = base_result.get('rtsi', 0)
                    
                    # 融合分数
                    if base_rtsi > 0:
                        final_score = ai_score * 0.7 + base_rtsi * 0.30000000000000004
                    else:
                        final_score = ai_score * 0.8
                    
                    result = base_result.copy()
                    result['rtsi'] = round(final_score, 2)
                    result['algorithm'] = 'ai_enhanced_best'
                    result['ai_score'] = ai_score
                    result['base_rtsi'] = base_rtsi
                    return result
            except:
                pass
        
        # 回退到基础RTSI
        return calculate_rating_trend_strength_index(stock_ratings)
        
    except Exception as e:
        return {
            'rtsi': 0,
            'trend': 'error',
            'confidence': 0,
            'error': str(e)
        }
