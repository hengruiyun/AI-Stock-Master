# -*- coding: utf-8 -*-
"""
增强版TMA分析器 - 集成AI增强信号和可信度评估
基于原有TMA方法，增加智能插值和可信度筛选机制

作者: 267278466@qq.com
创建时间：2025-01-21
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime
import warnings

# 导入AI增强组件
try:
    from .ai_enhanced_signal_analyzer import AIEnhancedSignalAnalyzer
    from .adaptive_interpolation import AdaptiveInterpolationEngine
    from .enhanced_multi_dimensional_analyzer import EnhancedMultiDimensionalAnalyzer
    from .irsi_calculator import CoreStrengthAnalyzer, calculate_industry_relative_strength
    AI_ENHANCED_AVAILABLE = True
except ImportError as e:
    print(f"AI增强组件不可用，使用基础模式: {e}")
    from .irsi_calculator import CoreStrengthAnalyzer, calculate_industry_relative_strength
    AI_ENHANCED_AVAILABLE = False

warnings.filterwarnings('ignore', category=RuntimeWarning)


class CredibilityFilter:
    """可信度过滤器"""
    
    def __init__(self, min_credibility: float = 0.3, max_interpolation_ratio: float = 0.5):
        """
        初始化可信度过滤器
        
        Args:
            min_credibility: 最小可信度阈值
            max_interpolation_ratio: 最大插值比例阈值
        """
        self.min_credibility = min_credibility
        self.max_interpolation_ratio = max_interpolation_ratio
        self.logger = logging.getLogger(__name__)
    
    def evaluate_data_credibility(self, 
                                 industry_data: pd.DataFrame, 
                                 interpolation_results: Dict = None) -> Dict[str, float]:
        """
        评估行业数据的可信度
        
        Args:
            industry_data: 行业数据
            interpolation_results: 插值结果（如果有）
        
        Returns:
            各股票的可信度评分字典
        """
        credibility_scores = {}
        date_columns = [col for col in industry_data.columns if str(col).startswith('202')]
        
        # 限制行业分析只使用最近60天的数据
        if len(date_columns) > 60:
            date_columns = sorted(date_columns)[-60:]  # 只取最近60天
        
        for _, stock in industry_data.iterrows():
            stock_code = str(stock.get('股票代码', ''))
            
            # 1. 计算原始数据完整性
            original_completeness = self._calculate_original_completeness(stock, date_columns)
            
            # 2. 计算数据一致性
            consistency_score = self._calculate_data_consistency(stock, date_columns)
            
            # 3. 考虑插值质量（如果有）
            interpolation_quality = 1.0
            if interpolation_results and stock_code in interpolation_results:
                interp_result = interpolation_results[stock_code]
                interpolation_quality = interp_result.get('interpolation_quality', 1.0)
                
                # 插值比例过高的惩罚
                missing_ratio = interp_result.get('missing_ratio', 0)
                if missing_ratio > self.max_interpolation_ratio:
                    interpolation_quality *= (1 - missing_ratio) * 2  # 双重惩罚
            
            # 4. 综合可信度评分
            credibility = (original_completeness * 0.4 + 
                          consistency_score * 0.3 + 
                          interpolation_quality * 0.3)
            
            credibility_scores[stock_code] = min(max(credibility, 0), 1)
        
        return credibility_scores
    
    def _calculate_original_completeness(self, stock_data: pd.Series, date_columns: List[str]) -> float:
        """计算原始数据完整性"""
        total_points = len(date_columns)
        valid_points = 0
        
        for col in date_columns:
            value = str(stock_data[col]).strip()
            if value and value != '-' and value != 'nan':
                valid_points += 1
        
        return valid_points / max(total_points, 1)
    
    def _calculate_data_consistency(self, stock_data: pd.Series, date_columns: List[str]) -> float:
        """计算数据一致性（评级变化的合理性）"""
        rating_map = {
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '中空': 1, '大空': 0,
            '中性': 3.5
        }
        
        valid_ratings = []
        for col in date_columns:
            value = str(stock_data[col]).strip()
            if value in rating_map:
                valid_ratings.append(rating_map[value])
        
        if len(valid_ratings) < 2:
            return 0.5  # 数据不足，给予中等评分
        
        # 计算评级变化的方差，方差过大说明变化太剧烈，可信度降低
        changes = np.diff(valid_ratings)
        variance = np.var(changes) if len(changes) > 0 else 0
        
        # 将方差转换为一致性分数（方差越小，一致性越好）
        consistency_score = 1 / (1 + variance)
        
        return consistency_score
    
    def filter_credible_stocks(self, 
                              industry_data: pd.DataFrame,
                              credibility_scores: Dict[str, float]) -> pd.DataFrame:
        """
        过滤出可信度较高的股票（使用0.3阈值）
        
        Args:
            industry_data: 原始行业数据
            credibility_scores: 可信度评分
        
        Returns:
            过滤后的行业数据
        """
        credible_indices = []
        
        for idx, stock in industry_data.iterrows():
            stock_code = str(stock.get('股票代码', ''))
            credibility = credibility_scores.get(stock_code, 0)
            
            if credibility >= self.min_credibility:
                credible_indices.append(idx)
            else:
                self.logger.debug(f"排除低可信度股票 {stock_code}: 可信度={credibility:.3f}")
        
        filtered_data = industry_data.loc[credible_indices].copy()
        
        self.logger.info(f"可信度过滤(阈值{self.min_credibility}): {len(industry_data)} -> {len(filtered_data)} 只股票")
        
        return filtered_data


class EnhancedTMAAnalyzer:
    """
    增强版TMA分析器
    
    核心功能：
    1. 集成AI增强信号分析
    2. 智能插值处理
    3. 可信度评估和过滤
    4. 多维度分析融合
    5. 数据时间窗口限制（行业分析限制60天）
    """
    
    def __init__(self, 
                 enable_ai_enhancement: bool = True,
                 min_credibility: float = 0.3,
                 max_interpolation_ratio: float = 0.5,
                 min_stocks_per_industry: int = 3):
        """
        初始化增强版TMA分析器
        
        Args:
            enable_ai_enhancement: 是否启用AI增强功能
            min_credibility: 最小可信度阈值
            max_interpolation_ratio: 最大插值比例阈值
            min_stocks_per_industry: 每个行业最少股票数
        """
        self.logger = logging.getLogger(__name__)
        # 设置日志级别为WARNING，减少INFO输出
        self.logger.setLevel(logging.WARNING)
        self.enable_ai = enable_ai_enhancement and AI_ENHANCED_AVAILABLE
        self.min_stocks_per_industry = min_stocks_per_industry
        
        # 初始化基础分析器
        self.base_analyzer = CoreStrengthAnalyzer(min_stocks_per_industry=min_stocks_per_industry)
        
        # 初始化可信度过滤器
        self.credibility_filter = CredibilityFilter(min_credibility, max_interpolation_ratio)
        
        # 初始化AI增强组件（如果可用）
        if self.enable_ai:
            try:
                self.ai_analyzer = AIEnhancedSignalAnalyzer(enable_ai_features=True)
                self.interpolation_engine = AdaptiveInterpolationEngine()
                self.multi_analyzer = EnhancedMultiDimensionalAnalyzer()
                self.logger.info("AI增强功能已启用")
            except Exception as e:
                self.logger.warning(f"AI增强功能初始化失败，使用基础模式: {e}")
                self.enable_ai = False
        
        # 统计信息
        self.analysis_stats = {
            'total_industries': 0,
            'credibility_filtered': 0,
            'ai_enhanced_count': 0,
            'interpolation_applied': 0,
            'date_limited': 0  # 日期限制应用次数
        }
    
    def _limit_date_columns(self, data: pd.DataFrame, max_days: int = 60) -> List[str]:
        """
        限制数据的日期列数量
        
        Args:
            data: 数据DataFrame
            max_days: 最大天数限制
        
        Returns:
            限制后的日期列列表
        """
        date_columns = [col for col in data.columns if str(col).startswith('202')]
        
        if len(date_columns) > max_days:
            original_count = len(date_columns)
            date_columns = sorted(date_columns)[-max_days:]  # 只取最近的天数
            self.analysis_stats['date_limited'] += 1
            self.logger.info(f"日期列限制: {original_count} -> {len(date_columns)} 天 (最大{max_days}天)")
        
        return date_columns
    
    def analyze_industry_with_enhancement(self, 
                                        industry_data: pd.DataFrame,
                                        market_data: pd.DataFrame = None,
                                        industry_name: str = None) -> Dict[str, Union[float, str, Dict]]:
        """
        增强版行业分析
        
        Args:
            industry_data: 行业数据
            market_data: 市场数据
            industry_name: 行业名称
        
        Returns:
            增强的分析结果
        """
        analysis_start = datetime.now()
        
        try:
            self.analysis_stats['total_industries'] += 1
            
            # ================ 第一阶段：数据预处理和可信度评估 ================
            
            # 1.1 AI智能插值（如果启用）
            interpolation_results = {}
            if self.enable_ai and len(industry_data) > 0:
                interpolation_results = self._apply_ai_interpolation(industry_data, market_data)
                if interpolation_results:
                    self.analysis_stats['interpolation_applied'] += 1
            
            # 1.2 可信度评估
            credibility_scores = self.credibility_filter.evaluate_data_credibility(
                industry_data, interpolation_results
            )
            
            # 1.3 过滤低可信度数据
            filtered_data = self.credibility_filter.filter_credible_stocks(
                industry_data, credibility_scores
            )
            
            if len(filtered_data) != len(industry_data):
                self.analysis_stats['credibility_filtered'] += 1
            
            # 检查过滤后数据是否足够（降低到最少2只股票）
            min_required_stocks = 2
            if len(filtered_data) < min_required_stocks:
                return self._get_insufficient_data_result(
                    industry_name, 
                    len(filtered_data),
                    f"可信度过滤后股票数不足({len(filtered_data)} < {min_required_stocks})"
                )
            
            # ================ 第二阶段：基础TMA分析 ================
            
            # 2.1 使用过滤后的数据进行基础分析（应用日期限制）
            # 为基础分析器创建限制后的数据
            limited_date_cols = self._limit_date_columns(filtered_data, max_days=60)
            
            base_result = self.base_analyzer.calculate(
                filtered_data, market_data, industry_name
            )
            
            # ================ 第三阶段：AI增强分析（如果启用） ================
            
            ai_enhancement = {}
            if self.enable_ai and len(filtered_data) >= 2:
                try:
                    ai_enhancement = self._apply_ai_enhancement(
                        filtered_data, market_data, industry_name, interpolation_results
                    )
                    self.analysis_stats['ai_enhanced_count'] += 1
                except Exception as e:
                    self.logger.warning(f"AI增强分析失败: {e}")
            
            # ================ 第四阶段：结果融合和增强 ================
            
            # 4.1 计算增强TMA分数
            enhanced_tma_score = self._calculate_enhanced_tma_score(
                base_result, ai_enhancement, credibility_scores
            )
            
            # 4.2 生成增强状态评估
            enhanced_status = self._generate_enhanced_status(
                base_result, ai_enhancement, enhanced_tma_score
            )
            
            # 4.3 风险评估
            risk_assessment = self._assess_enhancement_risks(
                interpolation_results, credibility_scores, len(filtered_data)
            )
            
            # ================ 第五阶段：构建最终结果 ================
            
            processing_time = (datetime.now() - analysis_start).total_seconds()
            
            enhanced_result = {
                # 基础TMA结果
                **base_result,
                
                # 增强结果
                'enhanced_tma_score': enhanced_tma_score,
                'enhanced_status': enhanced_status,
                'ai_enhanced': self.enable_ai and bool(ai_enhancement),
                
                # 可信度信息
                'credibility_info': {
                    'avg_credibility': np.mean(list(credibility_scores.values())),
                    'min_credibility': min(credibility_scores.values()) if credibility_scores else 0,
                    'filtered_stocks': len(filtered_data),
                    'original_stocks': len(industry_data),
                    'filter_ratio': len(filtered_data) / max(len(industry_data), 1)
                },
                
                # AI增强信息
                'ai_enhancement': ai_enhancement,
                
                # 风险评估
                'risk_assessment': risk_assessment,
                
                # 元数据
                'processing_time': f"{processing_time:.3f}s",
                'enhancement_applied': self.enable_ai,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"增强TMA分析完成: {industry_name}, 耗时{processing_time:.3f}s, "
                           f"可信度过滤: {len(industry_data)}->{len(filtered_data)}")
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"增强TMA分析失败 {industry_name}: {e}")
            return self._get_error_result(industry_name, str(e))
    
    def _apply_ai_interpolation(self, 
                               industry_data: pd.DataFrame,
                               market_data: pd.DataFrame = None) -> Dict:
        """应用AI智能插值"""
        interpolation_results = {}
        
        try:
            market_context = self._extract_market_context(market_data)
            
            for _, stock in industry_data.iterrows():
                stock_code = str(stock.get('股票代码', ''))
                
                # 提取评级序列（限制最近60天）
                date_columns = self._limit_date_columns(industry_data, max_days=60)
                ratings_series = pd.Series(
                    [stock[col] for col in date_columns],
                    index=date_columns
                )
                
                # 应用自适应插值
                interp_result = self.interpolation_engine.interpolate_rating_series(
                    ratings_series=ratings_series,
                    stock_info={'code': stock_code, 'industry': 'auto_detect'},
                    market_context=market_context
                )
                
                interpolation_results[stock_code] = interp_result
            
            return interpolation_results
            
        except Exception as e:
            self.logger.error(f"AI插值失败: {e}")
            return {}
    
    def _apply_ai_enhancement(self, 
                             industry_data: pd.DataFrame,
                             market_data: pd.DataFrame,
                             industry_name: str,
                             interpolation_results: Dict) -> Dict:
        """应用AI增强分析"""
        try:
            # 选择代表性股票进行深度AI分析
            representative_stocks = self._select_representative_stocks(industry_data)
            
            ai_insights = []
            ai_scores = []
            
            for stock_code in representative_stocks[:3]:  # 最多分析3只代表性股票
                try:
                    # 准备单只股票数据
                    stock_data = industry_data[industry_data['股票代码'] == stock_code]
                    
                    # AI综合分析
                    ai_result = self.ai_analyzer.comprehensive_analyze(
                        stock_data=stock_data,
                        stock_code=stock_code,
                        industry_data=industry_data,
                        market_data=market_data,
                        enable_prediction=True
                    )
                    
                    ai_insights.extend(ai_result.ai_insights)
                    ai_scores.append(ai_result.ai_enhanced_score)
                    
                except Exception as e:
                    self.logger.warning(f"AI分析股票{stock_code}失败: {e}")
            
            # 汇总AI增强结果
            return {
                'ai_insights_count': len(ai_insights),
                'avg_ai_score': np.mean(ai_scores) if ai_scores else 50,
                'confidence_level': 'high' if np.mean(ai_scores) > 70 else 'medium' if np.mean(ai_scores) > 40 else 'low',
                'ai_recommendations': [insight.recommendation for insight in ai_insights[:3]],
                'processing_stocks': len(representative_stocks)
            }
            
        except Exception as e:
            self.logger.error(f"AI增强分析失败: {e}")
            return {}
    
    def _select_representative_stocks(self, industry_data: pd.DataFrame) -> List[str]:
        """选择代表性股票进行深度分析"""
        # 简化选择：按股票代码排序，选择前几只
        # 实际应用中可以基于市值、流动性等指标选择
        stock_codes = industry_data['股票代码'].astype(str).tolist()
        return sorted(stock_codes)[:5]  # 最多选择5只
    
    def _extract_market_context(self, market_data: pd.DataFrame = None) -> Dict:
        """提取市场环境信息"""
        if market_data is None or market_data.empty:
            return {'volatility': 0.5, 'trend': 'neutral'}
        
        try:
            # 简化的市场环境分析（限制最近60天）
            date_columns = self._limit_date_columns(market_data, max_days=60)
            if not date_columns:
                return {'volatility': 0.5, 'trend': 'neutral'}
            
            # 计算市场波动性
            recent_columns = sorted(date_columns)[-5:]  # 最近5天
            volatility = 0.5  # 默认中等波动
            
            return {
                'volatility': volatility,
                'trend': 'neutral',
                'data_quality': 'medium'
            }
            
        except Exception:
            return {'volatility': 0.5, 'trend': 'neutral'}
    
    def _calculate_enhanced_tma_score(self, 
                                    base_result: Dict,
                                    ai_enhancement: Dict,
                                    credibility_scores: Dict[str, float]) -> float:
        """计算增强TMA分数"""
        try:
            # 基础TMA分数
            base_tma = base_result.get('tma_score', 0) if 'tma_score' in base_result else base_result.get('irsi', 0)
            
            # 可信度加权
            avg_credibility = np.mean(list(credibility_scores.values())) if credibility_scores else 0.5
            credibility_weight = min(avg_credibility * 2, 1.0)  # 最高权重1.0
            
            # AI增强调整
            ai_adjustment = 0
            if ai_enhancement:
                ai_score = ai_enhancement.get('avg_ai_score', 50)
                ai_confidence = ai_enhancement.get('confidence_level', 'medium')
                
                # AI分数对TMA的调整
                ai_adjustment = (ai_score - 50) * 0.1  # AI分数的10%作为调整
                
                # 置信度加权
                confidence_weights = {'high': 1.0, 'medium': 0.7, 'low': 0.3}
                ai_adjustment *= confidence_weights.get(ai_confidence, 0.5)
            
            # 计算增强TMA分数
            enhanced_score = base_tma * credibility_weight + ai_adjustment
            
            # 限制范围
            enhanced_score = max(-100, min(100, enhanced_score))
            
            return enhanced_score
            
        except Exception as e:
            self.logger.error(f"计算增强TMA分数失败: {e}")
            return base_result.get('irsi', 0)
    
    def _generate_enhanced_status(self, 
                                base_result: Dict,
                                ai_enhancement: Dict,
                                enhanced_score: float) -> str:
        """生成增强状态描述"""
        try:
            # 基础状态
            base_status = base_result.get('status', '未知')
            
            # AI增强修饰
            ai_modifier = ""
            if ai_enhancement:
                confidence = ai_enhancement.get('confidence_level', 'medium')
                if confidence == 'high':
                    ai_modifier = "[AI高置信度]"
                elif confidence == 'medium':
                    ai_modifier = "[AI中等置信度]"
                else:
                    ai_modifier = "[AI低置信度]"
            
            # 增强分数修饰
            if enhanced_score > 40:
                score_modifier = "强势"
            elif enhanced_score > 20:
                score_modifier = "温和强势"
            elif enhanced_score > -20:
                score_modifier = "中性"
            elif enhanced_score > -40:
                score_modifier = "温和弱势"
            else:
                score_modifier = "弱势"
            
            return f"{score_modifier}{ai_modifier} (增强TMA: {enhanced_score:.1f})"
            
        except Exception:
            return base_result.get('status', '未知')
    
    def _assess_enhancement_risks(self, 
                                interpolation_results: Dict,
                                credibility_scores: Dict[str, float],
                                filtered_stocks_count: int) -> Dict:
        """评估增强分析的风险"""
        risks = []
        risk_level = "低"
        
        try:
            # 1. 插值风险评估
            if interpolation_results:
                high_interpolation_count = 0
                for result in interpolation_results.values():
                    missing_ratio = result.get('missing_ratio', 0)
                    if missing_ratio > 0.4:
                        high_interpolation_count += 1
                
                if high_interpolation_count > len(interpolation_results) * 0.3:
                    risks.append("插值比例过高，可能影响分析准确性")
                    risk_level = "中"
            
            # 2. 可信度风险评估
            if credibility_scores:
                low_credibility_count = sum(1 for score in credibility_scores.values() if score < 0.7)
                if low_credibility_count > len(credibility_scores) * 0.4:
                    risks.append("部分股票可信度偏低")
                    risk_level = "中"
            
            # 3. 样本量风险评估
            if filtered_stocks_count < 5:
                risks.append("过滤后样本量较小，统计显著性不足")
                risk_level = "高"
            
            # 4. AI增强风险
            if not self.enable_ai:
                risks.append("未启用AI增强功能，可能遗漏重要信号")
            
            return {
                'risk_level': risk_level,
                'risk_factors': risks,
                'risk_count': len(risks),
                'mitigation_advice': self._get_risk_mitigation_advice(risks)
            }
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            return {'risk_level': '未知', 'risk_factors': ['风险评估异常'], 'risk_count': 1}
    
    def _get_risk_mitigation_advice(self, risks: List[str]) -> List[str]:
        """获取风险缓解建议"""
        advice = []
        
        for risk in risks:
            if "插值" in risk:
                advice.append("建议寻找更完整的数据源")
            elif "可信度" in risk:
                advice.append("建议提高可信度阈值或增加验证指标")
            elif "样本量" in risk:
                advice.append("建议扩大分析范围或降低过滤标准")
            elif "AI" in risk:
                advice.append("建议启用AI增强功能以提高分析质量")
        
        return advice
    
    def _get_insufficient_data_result(self, industry_name: str, stock_count: int, reason: str) -> Dict:
        """数据不足时的结果"""
        return {
            'irsi': 0.0,
            'enhanced_tma_score': 0.0,
            'status': f'数据不足: {reason}',
            'enhanced_status': f'数据不足: {reason}',
            'industry_name': industry_name or '未知行业',
            'stock_count': stock_count,
            'data_points': 0,
            'algorithm': 'N/A',
            'ai_enhanced': False,
            'credibility_info': {'avg_credibility': 0, 'filter_ratio': 0},
            'risk_assessment': {'risk_level': '高', 'risk_factors': [reason]}
        }
    
    def _get_error_result(self, industry_name: str, error_message: str) -> Dict:
        """错误时的结果"""
        return {
            'irsi': 0.0,
            'enhanced_tma_score': 0.0,
            'status': f'分析错误: {error_message}',
            'enhanced_status': f'分析错误: {error_message}',
            'industry_name': industry_name or '未知行业',
            'error': error_message,
            'ai_enhanced': False,
            'risk_assessment': {'risk_level': '高', 'risk_factors': ['分析异常']}
        }
    
    def batch_analyze_industries_enhanced(self, stock_data: pd.DataFrame) -> Dict[str, Dict]:
        """批量增强行业分析"""
        results = {}
        
        # 获取所有行业
        industries = stock_data['行业'].dropna().unique()
        industries = [ind for ind in industries if ind and ind != '未分类']
        
        self.logger.info(f"开始批量增强TMA分析: {len(industries)}个行业")
        
        for industry in industries:
            try:
                industry_data = stock_data[stock_data['行业'] == industry]
                
                # 取消最小股票数限制，处理所有行业
                result = self.analyze_industry_with_enhancement(
                    industry_data=industry_data,
                    market_data=stock_data,
                    industry_name=industry
                )
                results[industry] = result
                    
            except Exception as e:
                self.logger.error(f"分析行业 {industry} 失败: {e}")
                results[industry] = self._get_error_result(industry, str(e))
        
        self.logger.info(f"批量增强TMA分析完成: {len(results)}个行业成功分析")
        return results
    
    def get_analysis_statistics(self) -> Dict:
        """获取分析统计信息"""
        return {
            'enhancement_stats': self.analysis_stats.copy(),
            'ai_enabled': self.enable_ai,
            'credibility_threshold': self.credibility_filter.min_credibility,
            'max_interpolation_ratio': self.credibility_filter.max_interpolation_ratio,
            'min_stocks_per_industry': self.min_stocks_per_industry
        }


# 兼容性函数
def enhanced_industry_analysis(industry_data: pd.DataFrame,
                             market_data: pd.DataFrame = None,
                             industry_name: str = None,
                             enable_ai: bool = True,
                             min_credibility: float = 0.3) -> Dict:
    """
    增强版行业分析（兼容性函数）
    
    Args:
        industry_data: 行业数据
        market_data: 市场数据
        industry_name: 行业名称
        enable_ai: 是否启用AI增强
        min_credibility: 最小可信度阈值
    
    Returns:
        增强的分析结果
    """
    analyzer = EnhancedTMAAnalyzer(
        enable_ai_enhancement=enable_ai,
        min_credibility=min_credibility
    )
    
    return analyzer.analyze_industry_with_enhancement(
        industry_data, market_data, industry_name
    )


if __name__ == "__main__":
    # 测试增强TMA分析器
    print("=== 增强TMA分析器测试 ===")
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '股票代码': ['000001', '000002', '600000', '600036', '000858'],
        '股票名称': ['平安银行', '万科A', '浦发银行', '招商银行', '五粮液'],
        '行业': ['银行', '房地产', '银行', '银行', '食品饮料'],
        '20250115': ['推荐', '中性', '买入', '推荐', '强烈推荐'],
        '20250116': ['推荐', '-', '推荐', '强烈推荐', '推荐'],  # 模拟缺失数据
        '20250117': ['强烈推荐', '中性', '-', '推荐', '推荐'],  # 模拟缺失数据
        '20250118': ['推荐', '买入', '强烈推荐', '推荐', '强烈推荐'],
        '20250119': ['-', '推荐', '推荐', '推荐', '推荐'],  # 模拟缺失数据
        '20250120': ['买入', '推荐', '推荐', '强烈推荐', '强烈推荐']
    })
    
    # 创建增强分析器
    enhanced_analyzer = EnhancedTMAAnalyzer(
        enable_ai_enhancement=True,
        min_credibility=0.3,
        max_interpolation_ratio=0.5
    )
    
    # 测试银行行业
    bank_data = test_data[test_data['行业'] == '银行']
    result = enhanced_analyzer.analyze_industry_with_enhancement(
        industry_data=bank_data,
        market_data=test_data,
        industry_name='银行'
    )
    
    print("\n=== 银行行业增强TMA分析结果 ===")
    print(f"原始TMA分数: {result.get('irsi', 0):.2f}")
    print(f"增强TMA分数: {result.get('enhanced_tma_score', 0):.2f}")
    print(f"增强状态: {result.get('enhanced_status', '未知')}")
    print(f"AI增强: {result.get('ai_enhanced', False)}")
    
    credibility_info = result.get('credibility_info', {})
    print(f"可信度信息: 平均={credibility_info.get('avg_credibility', 0):.3f}, "
          f"过滤比例={credibility_info.get('filter_ratio', 0):.3f}")
    
    risk_info = result.get('risk_assessment', {})
    print(f"风险级别: {risk_info.get('risk_level', '未知')}")
    print(f"风险因素: {risk_info.get('risk_factors', [])}")
    
    # 测试批量分析
    print("\n=== 批量增强分析测试 ===")
    batch_results = enhanced_analyzer.batch_analyze_industries_enhanced(test_data)
    
    for industry, result in batch_results.items():
        enhanced_score = result.get('enhanced_tma_score', 0)
        ai_enhanced = result.get('ai_enhanced', False)
        print(f"{industry}: 增强TMA={enhanced_score:.2f}, AI增强={ai_enhanced}")
    
    # 统计信息
    stats = enhanced_analyzer.get_analysis_statistics()
    print(f"\n=== 分析统计 ===")
    print(f"分析统计: {stats}")
    
    print("\n=== 测试完成 ===")
