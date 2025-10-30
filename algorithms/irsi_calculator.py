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
    from config.gui_i18n import t_gui as t_msci, t_gui as t_rtsi, t_gui as t_irsi, t_gui as t_engine, t_gui as t_common, set_language
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
    支持基于量价数据的增强TMA
    """
    
    def __init__(self, rating_map: Dict = None, min_stocks_per_industry: int = 3, 
                 enable_cache: bool = True, top_n_leading_stocks: int = 5):
        self.logger = logging.getLogger(__name__)
        
        # 评级映射
        self.rating_map = rating_map or {
            '强烈推荐': 5, '推荐': 4, '买入': 4, '增持': 3, '中性': 2,
            '持有': 2, '减持': 1, '卖出': 0, '强烈卖出': 0,
            '中空': 1, '-': 2,  # 特殊处理
            '大多': 7, '中多': 6, '小多': 5, '微多': 4,
            '微空': 3, '小空': 2, '大空': 0
        }
        
        # 强势等级定义（TMA分数范围-100到100，显示时×100）
        # >=70为强（红色），<=40为弱（绿色），其它为中（黄色）
        self.strength_levels = {
            (0.7, float('inf')): "强势",      # >=70分
            (0.4, 0.7): "中性",                # 40-70分
            (float('-inf'), 0.4): "弱势"       # <=40分
        }
        
        # 配置参数
        self.min_stocks_per_industry = min_stocks_per_industry
        self.enable_cache = enable_cache
        self.cache = {} if enable_cache else None
        self.calculation_count = 0
        self.cache_hits = 0
        
        # 新TMA算法配置：原始TMA × 60% + 前N龙头股RTSI平均 × 40%
        self.top_n_leading_stocks = top_n_leading_stocks
        self.logger.info(f"✅ [CoreStrengthAnalyzer] 新TMA算法：原始TMA×60% + 前{top_n_leading_stocks}龙头股RTSI平均×40%")
    
    def technical_momentum_analysis(self, sector_data: pd.DataFrame, 
                                  industry_col: str, date_cols: List[str],
                                  market: str = "CN", 
                                  industry_stocks_map: Dict[str, List[Dict]] = None) -> Dict[str, float]:
        """
        技术动量分析算法 (TMA) - 新公式
        
        新TMA = 原始TMA × 60% + 前N龙头股RTSI平均分 × 40%
        
        Args:
            sector_data: 行业数据DataFrame
            industry_col: 行业列名
            date_cols: 日期列
            market: 市场代码（CN/HK/US）
            industry_stocks_map: 行业股票映射 {行业名: [{'code': '600000', 'rtsi': 0.8}]}
        """
        # 1. 计算原始TMA（基于评级数据）
        traditional_tma = self._traditional_tma_analysis(sector_data, industry_col, date_cols)
        
        # 2. 如果有龙头股RTSI数据，则增强TMA
        if industry_stocks_map:
            enhanced_tma = self._enhance_tma_with_leading_stocks(traditional_tma, industry_stocks_map)
            self.logger.info(f"[TMA] ✅ 使用增强TMA：原始TMA×60% + 前{self.top_n_leading_stocks}龙头股RTSI×40%（{len(enhanced_tma)}个行业）")
            return enhanced_tma
        else:
            # 没有龙头股数据，只用原始TMA
            self.logger.info(f"[TMA] 使用原始TMA（无龙头股数据，{len(traditional_tma)}个行业）")
            return traditional_tma
    
    def _enhance_tma_with_leading_stocks(self, traditional_tma: Dict[str, float],
                                         industry_stocks_map: Dict[str, List[Dict]]) -> Dict[str, float]:
        """
        使用龙头股RTSI增强TMA
        
        新TMA = 原始TMA × 60% + 前N龙头股RTSI平均分 × 40%
        
        Args:
            traditional_tma: 原始TMA评分 {行业名: 评分(-1到1)}
            industry_stocks_map: 行业股票映射 {行业名: [{'code': '600000', 'rtsi': 85.5, 'name': '浦发银行'}]}
        
        Returns:
            增强后的TMA评分 {行业名: 评分(-1到1)}
        """
        enhanced_results = {}
        
        for industry_name, original_tma in traditional_tma.items():
            # 获取该行业的股票列表
            stocks = industry_stocks_map.get(industry_name, [])
            
            if not stocks:
                # 无股票数据，使用原始TMA
                self.logger.warning(f"[TMA增强] {industry_name}: industry_stocks_map中无股票数据")
                enhanced_results[industry_name] = original_tma
                continue
            
            # 调试：打印stocks的前3个
            self.logger.debug(f"[TMA增强] {industry_name}: stocks数量={len(stocks)}, 前3个={stocks[:3] if len(stocks) >= 3 else stocks}")
            
            # 按RTSI排序，选择前N个龙头股
            sorted_stocks = sorted(
                stocks,
                key=lambda x: self._get_rtsi_value(x),
                reverse=True
            )
            top_stocks = sorted_stocks[:self.top_n_leading_stocks]
            
            # 计算龙头股RTSI平均分
            rtsi_values = []
            for stock in top_stocks:
                rtsi = self._get_rtsi_value(stock)
                if rtsi > 0:  # 只计算有效的RTSI
                    rtsi_values.append(rtsi)
                else:
                    self.logger.debug(f"[TMA增强] {industry_name}: 股票{stock}的RTSI=0或无效")
            
            if rtsi_values:
                # 将RTSI (0-100) 转换到 (-1, 1) 范围
                avg_rtsi = np.mean(rtsi_values)
                rtsi_normalized = (avg_rtsi - 50) / 50.0  # 50分 → 0，100分 → 1，0分 → -1
                
                # 新TMA = 原始TMA × 60% + 龙头股RTSI × 40%
                enhanced_tma = original_tma * 0.6 + rtsi_normalized * 0.4
                
                self.logger.info(
                    f"[TMA增强] {industry_name}: "
                    f"原始TMA={original_tma:.3f}×0.6={original_tma*0.6:.3f}, "
                    f"前{len(rtsi_values)}股RTSI均值={avg_rtsi:.1f}→归一化={rtsi_normalized:.3f}×0.4={rtsi_normalized*0.4:.3f}, "
                    f"增强TMA={enhanced_tma:.3f}, 显示={enhanced_tma*100:.1f}分"
                )
            else:
                # 没有有效RTSI，使用原始TMA
                enhanced_tma = original_tma
                self.logger.info(f"[TMA增强] {industry_name}: 无有效RTSI，使用原始TMA={original_tma:.3f}, 显示={original_tma*100:.1f}分")
            
            enhanced_results[industry_name] = enhanced_tma
        
        return enhanced_results
    
    def _get_rtsi_value(self, stock_item) -> float:
        """安全获取RTSI值"""
        if isinstance(stock_item, dict):
            rtsi = stock_item.get('rtsi', 0)
            if isinstance(rtsi, dict):
                return float(rtsi.get('rtsi', 0))
            return float(rtsi) if rtsi else 0
        return 0
    
    def _traditional_tma_analysis(self, sector_data: pd.DataFrame, 
                                  industry_col: str, date_cols: List[str]) -> Dict[str, float]:
        """传统TMA算法（原有实现，保留作为后备）"""
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
                
                # 降低最低评级要求从3个到2个，处理数据稀疏问题
                if len(ratings) >= 2:
                    # 对于只有2个评级的情况，使用简化计算
                    if len(ratings) == 2:
                        # 简单趋势计算
                        trend = ratings[-1] - ratings[0]
                        # 标准化到[-1, 1]区间
                        tech_score = np.tanh(trend / 4.0)  # 4是评级范围的估计值
                        momentum_scores.append(tech_score)
                    else:
                        # 原有的RSI风格计算（3个或以上评级）
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
                            # RSI归一化到[-1, 1]
                            rsi_normalized = (rsi - 50) / 50
                            # MACD归一化到[-1, 1]（假设评级范围0-7，最大差值为7）
                            macd_normalized = np.tanh(macd / 2.0)  # 除以2使其更敏感，tanh限制到[-1,1]
                            
                            tech_score = rsi_normalized * 0.6 + macd_normalized * 0.4
                            momentum_scores.append(tech_score)
            
            # 行业技术动量
            if momentum_scores:
                industry_momentum = np.mean(momentum_scores)
                # tech_score已经在[-1, 1]范围内，直接使用平均值
                # 不再使用tanh压缩，避免单行业计算时过度饱和
                final_score = np.clip(industry_momentum, -1.0, 1.0)
                results[industry] = final_score
                
                # 调试输出：查看原始TMA的实际范围
                if len(results) == 1:  # 只在单行业模式下输出
                    self.logger.debug(f"[原始TMA] {industry}: momentum_scores数量={len(momentum_scores)}, "
                                    f"平均={industry_momentum:.3f}, 最终={final_score:.3f}")
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
                # 标准化处理 - 使用更激进的除数避免饱和
                # weighted_change的范围可能很大，需要更大的除数
                normalized_score = np.tanh(industry_upgrade / 5.0)  # 从2.0改为5.0，降低饱和
                results[industry] = normalized_score
                
                # 调试输出
                if len(results) == 1:
                    self.logger.debug(f"[UFA] {industry}: upgrade_scores数量={len(upgrade_scores)}, "
                                    f"平均={industry_upgrade:.3f}, 归一化={normalized_score:.3f}")
            else:
                results[industry] = 0.0
        
        return results
    
    def calculate(self, industry_data: pd.DataFrame, market_data: pd.DataFrame = None, 
                 industry_name: str = None, language: str = 'zh_CN',
                 stocks_results: Dict = None) -> Dict[str, Union[float, str, int]]:
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
        
        # 识别日期列（限制最近30天）
        date_cols = [col for col in industry_data.columns 
                    if col not in [industry_col, '股票代码', '股票名称', 'Code', 'Name']]
        
        # 限制行业分析只使用最近30天的数据（根据优化测试结果）
        if len(date_cols) > 30:
            date_cols = sorted(date_cols)[-30:]
        
        if len(date_cols) < 2:
            return self._get_insufficient_data_result(industry_name, len(date_cols))
        
        # 按日期排序
        date_cols.sort()
        
        # 准备行业股票映射（用于TMA增强）
        if stocks_results:
            # ✅ 使用已计算的RTSI数据
            industry_stocks_map = {}
            for _, row in industry_data.iterrows():
                stock_code = str(row.get('股票代码', row.get('Code', '')))
                if stock_code in stocks_results:
                    stock_info = stocks_results[stock_code]
                    if industry_name not in industry_stocks_map:
                        industry_stocks_map[industry_name] = []
                    industry_stocks_map[industry_name].append({
                        'code': stock_code,
                        'name': stock_info.get('name', stock_code),
                        'rtsi': stock_info.get('rtsi', {}).get('rtsi', 0) if isinstance(stock_info.get('rtsi'), dict) else stock_info.get('rtsi', 0)
                    })
            self.logger.debug(f"[TMA准备] {industry_name}: 从stocks_results构建industry_stocks_map, 股票数={len(industry_stocks_map.get(industry_name, []))}")
        else:
            # 回退：从DataFrame提取（没有RTSI）
            industry_stocks_map = self._prepare_industry_stocks_map(industry_data, industry_col)
            self.logger.warning(f"[TMA准备] {industry_name}: stocks_results为空，回退到DataFrame提取（无RTSI）")
        
        # 推断市场代码
        market = self._infer_market_from_data(industry_data)
        
        # 运行两个核心算法
        tma_results = self.technical_momentum_analysis(
            industry_data, industry_col, date_cols,
            market=market,
            industry_stocks_map=industry_stocks_map  # ✅ 现在有RTSI了
        )
        ufa_results = self.upgrade_focus_analysis(industry_data, industry_col, date_cols)
        
        # 如果指定了行业名称，返回该行业结果
        if industry_name and industry_name in tma_results:
            tma_score = tma_results[industry_name]
            ufa_score = ufa_results.get(industry_name, 0.0)
            
            # 新算法：（UFA×60% + 前5龙头股RTSI×40%）× 1.2
            # 计算龙头股RTSI部分
            stocks = industry_stocks_map.get(industry_name, []) if industry_stocks_map else []
            
            if stocks:
                # 按RTSI排序，选择前5个龙头股
                sorted_stocks = sorted(
                    stocks,
                    key=lambda x: self._get_rtsi_value(x),
                    reverse=True
                )
                top_stocks = sorted_stocks[:5]
                
                # 计算龙头股RTSI平均分
                rtsi_values = []
                for stock in top_stocks:
                    rtsi = self._get_rtsi_value(stock)
                    if rtsi > 0:
                        rtsi_values.append(rtsi)
                
                if rtsi_values:
                    # 将RTSI (0-100) 转换到 (-1, 1) 范围
                    avg_rtsi = np.mean(rtsi_values)
                    rtsi_normalized = (avg_rtsi - 50) / 50.0
                    
                    # 新算法：（UFA×70% + 龙头股RTSI×30%）× 1.2
                    combined_score = (ufa_score * 0.7 + rtsi_normalized * 0.3) * 1.2
                    
                    # 确保不超过1.0
                    combined_score = min(combined_score, 1.0)
                    
                    self.logger.info(
                        f"[新算法] {industry_name}: "
                        f"UFA={ufa_score:.3f}×0.6={ufa_score*0.6:.3f}, "
                        f"前{len(rtsi_values)}股RTSI均值={avg_rtsi:.1f}→归一化={rtsi_normalized:.3f}×0.4={rtsi_normalized*0.4:.3f}, "
                        f"合计={(ufa_score*0.6 + rtsi_normalized*0.4):.3f}×1.1={combined_score:.3f}, "
                        f"显示={combined_score*100:.1f}分"
                    )
                    
                    best_score = combined_score
                else:
                    # 没有有效RTSI，只用UFA × 1.1
                    best_score = min(ufa_score * 1.1, 1.0)
                    self.logger.info(f"[新算法] {industry_name}: 无有效RTSI，UFA={ufa_score:.3f}×1.1={best_score:.3f}, 显示={best_score*100:.1f}分")
            else:
                # 没有股票数据，只用UFA × 1.1
                best_score = min(ufa_score * 1.1, 1.0)
                self.logger.info(f"[新算法] {industry_name}: 无股票数据，UFA={ufa_score:.3f}×1.1={best_score:.3f}, 显示={best_score*100:.1f}分")
            
            best_algorithm = "UFA+RTSI×1.1"
            
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
        
        # 识别日期列（限制最近30天）
        date_cols = [col for col in stock_data.columns 
                    if col not in [industry_col, '股票代码', '股票名称', 'Code', 'Name']]
        
        # 限制行业分析只使用最近30天的数据（根据优化测试结果）
        if len(date_cols) > 30:
            date_cols = sorted(date_cols)[-30:]
        
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
            
            # 取消最小股票数限制，处理所有行业
            # 原限制: if len(industry_data) < self.min_stocks_per_industry: continue
            
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
        确定状态描述（TMA分数×100后的范围）
        >=70为强，<=40为弱，其它为中
        """
        if score >= 0.7:
            return "强势上涨"
        elif score > 0.4:
            return "震荡整理"
        else:
            return "弱势下跌"
    
    def _prepare_industry_stocks_map(self, industry_data: pd.DataFrame, 
                                     industry_col: str) -> Dict[str, List[Dict]]:
        """
        准备行业股票映射（用于量价TMA）
        
        Returns:
            {行业名: [{'code': '600000', 'name': '浦发银行', 'rtsi': 0.8}]}
        """
        industry_stocks_map = {}
        
        for industry in industry_data[industry_col].unique():
            if not industry or industry == '未分类':
                continue
            
            industry_stocks = industry_data[industry_data[industry_col] == industry]
            stocks_list = []
            
            for _, row in industry_stocks.iterrows():
                stock_code = str(row.get('股票代码', row.get('Code', '')))
                stock_name = str(row.get('股票名称', row.get('Name', stock_code)))
                
                # 尝试获取RTSI值（如果有）
                rtsi_value = 0
                for col in industry_stocks.columns:
                    if 'rtsi' in col.lower() or 'RTSI' in col:
                        rtsi_value = row.get(col, 0)
                        break
                
                if stock_code:
                    stocks_list.append({
                        'code': stock_code,
                        'name': stock_name,
                        'rtsi': rtsi_value
                    })
            
            if stocks_list:
                industry_stocks_map[industry] = stocks_list
        
        return industry_stocks_map
    
    def _infer_market_from_data(self, industry_data: pd.DataFrame) -> str:
        """
        从数据推断市场代码
        
        Returns:
            'CN', 'HK', 或 'US'
        """
        # 尝试从股票代码推断
        if '股票代码' in industry_data.columns:
            codes = industry_data['股票代码'].dropna().astype(str)
            
            for code in codes[:10]:  # 检查前10个
                if code.isdigit() and len(code) == 6:
                    return 'CN'  # 中国A股
                elif code.startswith(('0', '3', '6')):
                    return 'CN'
                elif code.endswith('.HK') or (code.isdigit() and len(code) <= 5):
                    return 'HK'  # 香港
                elif len(code) <= 4 and code.isalpha():
                    return 'US'  # 美股
        
        # 默认返回CN
        return 'CN'
    
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