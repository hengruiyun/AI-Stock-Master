#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迷你投资大师 - 独立接口文件
包含数据获取、计算过程及结果、生成简易HTML报告的完整功能

作者: AI Fund Master
版本: 1.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入国际化支持
try:
    from config.gui_i18n import t_gui
except ImportError:
    # 如果无法导入，提供简单的回退函数
    def t_gui(key, **kwargs):
        return key

import akshare as ak
import time

# 设置akshare全局访问间隔为2秒
ak.set_token("")
# 注意：akshare没有内置的全局间隔设置，我们将在每次API调用后手动添加延迟


class MiniInvestmentMaster:
    """
    迷你投资大师 - 核心分析引擎
    融合多位投资大师的投资理念，提供智能投资分析
    """
    
    def __init__(self):
        """初始化迷你投资大师"""
        # 投资大师策略配置
        self.master_strategies = {
            'buffett': {
                'name': '巴菲特价值投资',
                'focus': ['长期趋势', '价格稳定性', '低波动率'],
                'weight': 0.3
            },
            'lynch': {
                'name': '彼得林奇成长投资',
                'focus': ['价格动量', '成交量确认', '短期趋势'],
                'weight': 0.25
            },
            'graham': {
                'name': '格雷厄姆价值投资',
                'focus': ['安全边际', '价格低估', '风险控制'],
                'weight': 0.2
            },
            'druckenmiller': {
                'name': '德鲁肯米勒趋势投资',
                'focus': ['趋势强度', '动量确认', '风险回报比'],
                'weight': 0.15
            },
            'burry': {
                'name': '迈克尔·伯里逆向投资',
                'focus': ['超卖反弹', '价值回归', '市场情绪'],
                'weight': 0.1
            }
        }
        
        # 分析方法配置
        self.analysis_methods = {
            'trend_analysis': '趋势分析',
            'momentum_analysis': '动量分析', 
            'support_resistance': '支撑阻力分析',
            'volume_analysis': '成交量分析',
            'price_action': '价格行为分析',
            'value_analysis': '价值分析',
            'growth_analysis': '成长分析',
            'contrarian_analysis': '逆向分析'
        }
    
    def detect_market_type(self, symbol: str) -> str:
        """
        根据股票代码判断市场类型
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场类型: 'A' (A股), 'HK' (港股), 'US' (美股)
        """
        symbol = symbol.upper().strip()
        
        # 港股判断：5位数字，前缀00-09
        if len(symbol) == 5 and symbol.isdigit() and symbol.startswith(('00', '01', '02', '03', '04', '05', '06', '07', '08', '09')):
            return 'HK'
        
        # 美股判断：包含字母的代码
        if any(c.isalpha() for c in symbol):
            return 'US'
        
        # A股判断：6位数字
        if len(symbol) == 6 and symbol.isdigit():
            return 'A'
        
        # 默认A股
        return 'A'
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票数据 - 支持A股、港股、美股
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            包含股票数据的DataFrame
        """
        try:
            market_type = self.detect_market_type(symbol)
            df = None
            
            # 格式化日期
            start_date_fmt = start_date.replace('-', '')
            end_date_fmt = end_date.replace('-', '')
            
            if market_type == 'A':
                # A股数据
                df = ak.stock_zh_a_hist(
                    symbol=symbol, 
                    period="daily", 
                    start_date=start_date_fmt, 
                    end_date=end_date_fmt, 
                    adjust="qfq"
                )
                # 添加2秒访问间隔
                time.sleep(2)
                # A股列名：日期、股票代码、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
                if not df.empty:
                    df.columns = ['date', 'stock_code', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
                    
            elif market_type == 'HK':
                # 港股数据
                df = ak.stock_hk_hist(
                    symbol=symbol, 
                    period="daily", 
                    start_date=start_date_fmt, 
                    end_date=end_date_fmt, 
                    adjust="qfq"
                )
                # 添加2秒访问间隔
                time.sleep(2)
                # 港股列名可能不同，需要统一格式
                if not df.empty:
                    # 根据实际返回的列名进行映射
                    if len(df.columns) >= 6:
                        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume'] + list(df.columns[6:])
                        # 添加缺失的列
                        if 'turnover' not in df.columns:
                            df['turnover'] = 0
                        if 'amplitude' not in df.columns:
                            df['amplitude'] = 0
                        if 'change_pct' not in df.columns:
                            df['change_pct'] = 0
                        if 'change_amount' not in df.columns:
                            df['change_amount'] = 0
                        if 'turnover_rate' not in df.columns:
                            df['turnover_rate'] = 0
                            
            elif market_type == 'US':
                # 美股数据 - 使用新接口: stock_us_daily
                try:
                    df = ak.stock_us_daily(symbol=symbol)
                    # 添加2秒访问间隔
                    time.sleep(2)
                    
                    if not df.empty:
                        # stock_us_daily返回的列名: ['date', 'open', 'high', 'low', 'close', 'volume']
                        print(f"获取到美股数据，列名: {list(df.columns)}")
                        
                        # 过滤日期范围（因为stock_us_daily返回所有历史数据）
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            start_dt = pd.to_datetime(start_date)
                            end_dt = pd.to_datetime(end_date)
                            df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
                        
                        # 添加缺失的列
                        if 'turnover' not in df.columns:
                            df['turnover'] = 0
                        if 'amplitude' not in df.columns:
                            df['amplitude'] = 0
                        if 'change_pct' not in df.columns:
                            df['change_pct'] = 0
                        if 'change_amount' not in df.columns:
                            df['change_amount'] = 0
                        if 'turnover_rate' not in df.columns:
                            df['turnover_rate'] = 0
                except Exception as e:
                    # 如果美股接口不可用，抛出异常
                    raise ValueError(f"美股数据接口暂不可用，股票代码: {symbol}, 错误: {e}")
            
            if df is None or df.empty:
                raise ValueError(f"未找到股票代码 {symbol} 的数据")
            
            # 统一数据格式
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 删除股票代码列（如果存在）
            if 'stock_code' in df.columns:
                df = df.drop('stock_code', axis=1)
            
            # 确保所有必需的列都存在
            required_columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'turnover', 'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = 0
            
            # 重新排列列顺序
            df = df[required_columns]
            
            return df
            
        except Exception as e:
            raise Exception(f"获取股票数据失败: {e}")
    

    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算技术指标
        
        Args:
            df: 股票数据DataFrame
            
        Returns:
            包含技术指标的字典
        """
        if df.empty or len(df) < 20:
            return {}
        
        indicators = {}
        
        try:
            # 基础价格信息
            indicators['current_price'] = float(df['close'].iloc[-1])
            indicators['price_change'] = float(df['close'].iloc[-1] - df['close'].iloc[-2]) if len(df) > 1 else 0
            indicators['price_change_pct'] = float((indicators['price_change'] / df['close'].iloc[-2] * 100)) if len(df) > 1 and df['close'].iloc[-2] != 0 else 0
            
            # 移动平均线
            if len(df) >= 5:
                indicators['ma5'] = float(df['close'].rolling(5).mean().iloc[-1])
            if len(df) >= 10:
                indicators['ma10'] = float(df['close'].rolling(10).mean().iloc[-1])
            if len(df) >= 20:
                indicators['ma20'] = float(df['close'].rolling(20).mean().iloc[-1])
            if len(df) >= 60:
                indicators['ma60'] = float(df['close'].rolling(60).mean().iloc[-1])
            
            # RSI指标
            if len(df) >= 14:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi'] = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
            
            # MACD指标
            if len(df) >= 26:
                exp1 = df['close'].ewm(span=12).mean()
                exp2 = df['close'].ewm(span=26).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9).mean()
                indicators['macd'] = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
                indicators['macd_signal'] = float(signal.iloc[-1]) if not pd.isna(signal.iloc[-1]) else 0
                indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
            
            # 布林带
            if len(df) >= 20:
                ma20 = df['close'].rolling(20).mean()
                std20 = df['close'].rolling(20).std()
                indicators['bollinger_upper'] = float(ma20.iloc[-1] + 2 * std20.iloc[-1])
                indicators['bollinger_lower'] = float(ma20.iloc[-1] - 2 * std20.iloc[-1])
                indicators['bollinger_middle'] = float(ma20.iloc[-1])
            
            # 成交量指标
            indicators['volume'] = float(df['volume'].iloc[-1])
            if len(df) >= 20:
                indicators['volume_ma20'] = float(df['volume'].rolling(20).mean().iloc[-1])
                indicators['volume_ratio'] = indicators['volume'] / indicators['volume_ma20']
            
            # 波动率
            if len(df) >= 20:
                returns = df['close'].pct_change().dropna()
                indicators['volatility'] = float(returns.rolling(20).std().iloc[-1] * np.sqrt(252) * 100)  # 年化波动率
            
        except Exception as e:
            print(f"计算技术指标失败: {e}")
        
        return indicators
    
    def analyze_master_strategies(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        综合投资大师策略分析
        基于11位投资大师的核心理念，不使用LLM
        """
        master_scores = {}
        
        if not indicators or df.empty:
            return {'overall_score': 50, 'master_insights': [], 'strategy_breakdown': {}}
        
        try:
            current_price = indicators.get('current_price', 0)
            volatility = indicators.get('volatility', 0)
            rsi = indicators.get('rsi', 50)
            volume_ratio = indicators.get('volume_ratio', 1)
            price_change_pct = indicators.get('price_change_pct', 0)
            
            # 巴菲特策略评分（价值投资）- 更激进的评分
            buffett_score = 40  # 降低基础分
            if volatility < 15:  # 低波动率
                buffett_score += 25
            elif volatility < 25:
                buffett_score += 15
            if abs(price_change_pct) < 1:  # 价格稳定
                buffett_score += 20
            elif abs(price_change_pct) < 3:
                buffett_score += 10
            if len(df) >= 60:  # 长期数据可用
                long_term_trend = df['close'].tail(60).mean() / df['close'].head(10).mean()
                if 1.1 < long_term_trend < 1.5:  # 稳健增长
                    buffett_score += 25
                elif 1.05 < long_term_trend < 1.1:
                    buffett_score += 15
            master_scores['buffett'] = min(100, max(0, buffett_score))
            
            # 彼得林奇策略评分（成长投资）- 更激进的评分
            lynch_score = 35
            if price_change_pct > 3:  # 强正向动量
                lynch_score += 35
            elif price_change_pct > 1:
                lynch_score += 25
            elif price_change_pct > 0:
                lynch_score += 15
            if volume_ratio > 1.5:  # 成交量确认
                lynch_score += 25
            elif volume_ratio > 1.2:
                lynch_score += 15
            if 50 < rsi < 70:  # 健康的上升趋势
                lynch_score += 20
            elif 40 < rsi < 80:
                lynch_score += 10
            master_scores['lynch'] = min(100, max(0, lynch_score))
            
            # 格雷厄姆策略评分（深度价值）- 更激进的评分
            graham_score = 35
            if rsi < 25:  # 严重超卖
                graham_score += 40
            elif rsi < 35:
                graham_score += 30
            elif rsi < 45:
                graham_score += 20
            if volatility > 25:  # 市场恐慌中的机会
                graham_score += 20
            elif volatility > 15:
                graham_score += 10
            if price_change_pct < -5:  # 大幅下跌创造价值机会
                graham_score += 25
            elif price_change_pct < -2:
                graham_score += 15
            master_scores['graham'] = min(100, max(0, graham_score))
            
            # 德鲁肯米勒策略评分（趋势投资）- 更激进的评分
            druckenmiller_score = 35
            ma5 = indicators.get('ma5')
            ma20 = indicators.get('ma20')
            if ma5 and ma20:
                trend_strength = abs((ma5 - ma20) / ma20 * 100)
                if trend_strength > 5:  # 强趋势
                    druckenmiller_score += 35
                elif trend_strength > 2:
                    druckenmiller_score += 25
                elif trend_strength > 1:
                    druckenmiller_score += 15
                if ma5 > ma20 and price_change_pct > 0:  # 上升趋势一致性
                    druckenmiller_score += 25
                elif ma5 < ma20 and price_change_pct < 0:  # 下降趋势一致性
                    druckenmiller_score += 20
            master_scores['druckenmiller'] = min(100, max(0, druckenmiller_score))
            
            # 迈克尔·伯里策略评分（逆向投资）- 更激进的评分
            burry_score = 30
            if rsi < 20:  # 极度超卖
                burry_score += 45
            elif rsi < 30:
                burry_score += 35
            elif rsi < 40:
                burry_score += 25
            if price_change_pct < -8:  # 大幅下跌
                burry_score += 30
            elif price_change_pct < -5:
                burry_score += 20
            elif price_change_pct < -2:
                burry_score += 10
            if volatility > 40:  # 高波动率中的机会
                burry_score += 20
            elif volatility > 25:
                burry_score += 10
            master_scores['burry'] = min(100, max(0, burry_score))
            
            # 计算加权综合得分
            overall_score = 0
            for strategy, score in master_scores.items():
                weight = self.master_strategies[strategy]['weight']
                overall_score += score * weight
            
            # 生成投资大师洞察
            master_insights = []
            best_strategy = max(master_scores.items(), key=lambda x: x[1])
            strategy_name = self.master_strategies[best_strategy[0]]['name']
            
            if best_strategy[1] > 70:
                master_insights.append(f"当前最适合{strategy_name}策略（得分：{best_strategy[1]:.0f}）")
            
            if overall_score > 70:
                master_insights.append("多位投资大师策略显示积极信号")
            elif overall_score < 40:
                master_insights.append("投资大师策略建议谨慎观望")
            else:
                master_insights.append("投资大师策略显示中性信号")
            
            # 添加具体策略建议
            if master_scores['buffett'] > 65:
                master_insights.append("巴菲特价值投资：适合长期持有")
            if master_scores['lynch'] > 65:
                master_insights.append("彼得林奇成长投资：关注成长潜力")
            if master_scores['graham'] > 65:
                master_insights.append("格雷厄姆价值投资：发现低估机会")
            if master_scores['druckenmiller'] > 65:
                master_insights.append("德鲁肯米勒趋势投资：跟随强势趋势")
            if master_scores['burry'] > 65:
                master_insights.append("迈克尔·伯里逆向投资：逆向思维机会")
            
            return {
                'overall_score': round(overall_score, 1),
                'master_insights': master_insights,
                'strategy_breakdown': master_scores,
                'best_strategy': strategy_name,
                'analysis_method': '多投资大师策略综合分析'
            }
            
        except Exception as e:
            print(f"投资大师策略分析失败: {e}")
            return {
                'overall_score': 50,
                'master_insights': ['分析数据不足，建议谨慎投资'],
                'strategy_breakdown': {},
                'analysis_method': '基础投资大师理论'
            }
    
    def generate_investment_advice(self, master_analysis: Dict[str, Any], indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成投资建议
        
        Args:
            master_analysis: 投资大师分析结果
            indicators: 技术指标
            
        Returns:
            投资建议字典
        """
        try:
            master_score = master_analysis.get('overall_score', 50)
            master_insights = master_analysis.get('master_insights', [])
            best_strategy = master_analysis.get('best_strategy', '综合策略')
            
            # 基础置信度计算
            base_confidence = min(85, max(50, 70 - abs(indicators.get('price_change_pct', 0)) * 2))
            
            # 根据投资大师综合得分调整建议 - 增加更多样化的建议类型
            if master_score >= 75:
                recommendation = "强烈买入"
                confidence = min(95, base_confidence + 20)
                risk_level = "低"
            elif master_score >= 65:
                recommendation = "买入"
                confidence = min(90, base_confidence + 15)
                risk_level = "中低"
            elif master_score >= 55:
                recommendation = "谨慎买入"
                confidence = min(80, base_confidence + 10)
                risk_level = "中等"
            elif master_score >= 45:
                recommendation = "持有"
                confidence = min(70, base_confidence + 5)
                risk_level = "中等"
            elif master_score >= 35:
                recommendation = "谨慎卖出"
                confidence = min(75, base_confidence + 5)
                risk_level = "中高"
            elif master_score >= 25:
                recommendation = "卖出"
                confidence = min(85, base_confidence + 10)
                risk_level = "高"
            else:
                recommendation = "强烈卖出"
                confidence = min(95, base_confidence + 20)
                risk_level = "很高"
            
            # 生成推理说明
            price_change_pct = indicators.get('price_change_pct', 0)
            trend_direction = "上涨" if price_change_pct > 0 else "下跌" if price_change_pct < 0 else "横盘"
            momentum_direction = "正向" if price_change_pct > 0 else "负向" if price_change_pct < 0 else "中性"
            
            # 根据不同建议类型生成更详细的推理说明
            if recommendation == "强烈买入":
                reasoning = f"基于{best_strategy}等多位投资大师策略高度一致，{trend_direction}趋势强劲，综合得分{master_score:.1f}，显示强烈买入信号"
            elif recommendation == "强烈卖出":
                reasoning = f"基于{best_strategy}等多位投资大师策略高度一致看空，{trend_direction}趋势疲弱，综合得分{master_score:.1f}，强烈建议卖出"
            elif "持有" in recommendation:
                reasoning = f"基于{best_strategy}等投资大师策略分歧，{trend_direction}趋势不明确，综合得分{master_score:.1f}，建议持有观望"
            else:
                reasoning = f"基于{best_strategy}等多位投资大师策略，{trend_direction}趋势配合{momentum_direction}动量，综合得分{master_score:.1f}"
            
            return {
                'recommendation': recommendation,
                'confidence': round(confidence, 1),
                'risk_level': risk_level,
                'reasoning': reasoning,
                'master_insights': master_insights if master_insights else [
                    "巴菲特价值投资视角：关注长期趋势的可持续性",
                    "彼得林奇成长投资理念：重视价格动量和市场情绪",
                    "风险管理：建议分批建仓，控制单次投资比例"
                ],
                'strategy_scores': master_analysis.get('strategy_breakdown', {}),
                'recommendation_level': recommendation  # 添加建议级别字段
            }
            
        except Exception as e:
            print(f"生成投资建议失败: {e}")
            return {
                'recommendation': '观望',
                'confidence': 50,
                'risk_level': '未知',
                'reasoning': '分析过程出错，建议谨慎投资',
                'master_insights': ['投资有风险，决策需谨慎'],
                'strategy_scores': {},
                'recommendation_level': '观望'
            }
    
    def analyze_stock(self, symbol: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        分析单只股票
        
        Args:
            symbol: 股票代码
            start_date: 开始日期，默认为60天前
            end_date: 结束日期，默认为今天
            
        Returns:
            完整的分析结果
        """
        # 设置默认日期
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
        
        result = {
            'status': 'success',
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_period': f"{start_date} 至 {end_date}",
            'data': {},
            'indicators': {},
            'master_analysis': {},
            'investment_advice': {},
            'summary': '',
            'disclaimer': '本分析仅供参考，投资有风险，决策需谨慎。'
        }
        
        try:
            # 1. 获取数据
            print(f"正在获取 {symbol} 的股票数据...")
            df = self.get_stock_data(symbol, start_date, end_date)
            
            if df.empty:
                result['status'] = 'error'
                result['error'] = '无法获取股票数据'
                return result
            
            result['data'] = {
                'total_days': len(df),
                'latest_price': float(df['close'].iloc[-1]),
                'price_range': {
                    'high': float(df['high'].max()),
                    'low': float(df['low'].min())
                }
            }
            
            # 2. 计算技术指标
            print("正在计算技术指标...")
            result['indicators'] = self.calculate_technical_indicators(df)
            
            # 3. 投资大师策略分析
            print("正在进行投资大师策略分析...")
            result['master_analysis'] = self.analyze_master_strategies(df, result['indicators'])
            
            # 4. 生成投资建议
            print("正在生成投资建议...")
            result['investment_advice'] = self.generate_investment_advice(
                result['master_analysis'], 
                result['indicators']
            )
            
            # 5. 生成总结
            current_price = result['indicators'].get('current_price', 0)
            recommendation = result['investment_advice'].get('recommendation', '观望')
            confidence = result['investment_advice'].get('confidence', 0)
            master_score = result['master_analysis'].get('overall_score', 0)
            
            result['summary'] = f"迷你投资大师分析：股票{symbol}当前价格{current_price:.2f}元，" + \
                              f"投资建议：{recommendation}（置信度{confidence:.0f}%）。" + \
                              f"综合评分{master_score:.1f}/100。"
            
            print(f"分析完成！")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f'分析过程出错: {str(e)}'
            print(f"分析失败: {e}")
        
        return result


class SimpleHTMLGenerator:
    """
    简易HTML报告生成器
    """
    
    def __init__(self):
        self.css_styles = self._get_css_styles()
    
    def _get_html_lang(self):
        """获取HTML语言标识"""
        try:
            from config.gui_i18n import get_system_language
            return "en" if get_system_language() == 'en' else "zh-CN"
        except:
            return "zh-CN"
    
    def _get_css_styles(self) -> str:
        """
        获取CSS样式
        """
        return """
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Microsoft YaHei', 'Segoe UI', Tahoma, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.2em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            
            .header .subtitle {
                font-size: 1.1em;
                opacity: 0.9;
                margin-bottom: 5px;
            }
            
            .section {
                padding: 25px;
                border-bottom: 1px solid #eee;
            }
            
            .section:last-child {
                border-bottom: none;
            }
            
            .section h2 {
                color: #2c3e50;
                margin-bottom: 20px;
                font-size: 1.5em;
                border-left: 4px solid #3498db;
                padding-left: 15px;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            
            .metric-card {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
            }
            
            .metric-label {
                font-size: 0.9em;
                color: #666;
                margin-bottom: 5px;
            }
            
            .metric-value {
                font-size: 1.3em;
                font-weight: bold;
                color: #2c3e50;
            }
            
            .recommendation {
                background: linear-gradient(135deg, #ffeaea 0%, #fff0f0 100%);
                padding: 20px;
                border-radius: 10px;
                border: 2px solid #e74c3c;
                margin: 20px 0;
            }
            
            .recommendation.sell {
                background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
                border-color: #27ae60;
            }
            
            .recommendation.hold {
                background: linear-gradient(135deg, #fff8e1 0%, #fffbf0 100%);
                border-color: #f39c12;
            }
            
            .recommendation h3 {
                margin-bottom: 10px;
                font-size: 1.3em;
            }
            
            /* 置信度长条样式已移除，只使用文字显示 */
            
            .strategy-scores {
                margin-top: 20px;
            }
            
            .strategy-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }
            
            .strategy-name {
                font-weight: 500;
            }
            
            .strategy-score {
                font-weight: bold;
                color: #3498db;
            }
            
            .price-up {
                color: #dc3545 !important;
                font-weight: bold;
            }
            
            .price-down {
                color: #28a745 !important;
                font-weight: bold;
            }
            
            .price-neutral {
                color: #6c757d !important;
                font-weight: bold;
            }
            
            .trend-up {
                background-color: rgba(220, 53, 69, 0.1);
                border-left: 4px solid #dc3545;
                padding-left: 10px;
            }
            
            .trend-down {
                background-color: rgba(40, 167, 69, 0.1);
                border-left: 4px solid #28a745;
                padding-left: 10px;
            }
            
            .stock-info {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }
            
            .stock-info.trend-up {
                background-color: rgba(220, 53, 69, 0.05);
                border-left: 4px solid #dc3545;
            }
            
            .stock-info.trend-down {
                background-color: rgba(40, 167, 69, 0.05);
                border-left: 4px solid #28a745;
            }
            
            .insights {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-top: 15px;
            }
            
            .insights ul {
                list-style-type: none;
                padding-left: 0;
            }
            
            .insights li {
                padding: 5px 0;
                padding-left: 20px;
                position: relative;
            }
            
            .insights li:before {
                content: "💡";
                position: absolute;
                left: 0;
            }
            
            .footer {
                background: #2c3e50;
                color: white;
                text-align: center;
                padding: 20px;
                font-size: 0.9em;
            }
            
            .error {
                background: #ffeaea;
                color: #e74c3c;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e74c3c;
                margin: 20px 0;
                text-align: center;
            }
            
            @media (max-width: 768px) {
                .container {
                    margin: 10px;
                    border-radius: 10px;
                }
                
                .header {
                    padding: 20px;
                }
                
                .header h1 {
                    font-size: 1.8em;
                }
                
                .section {
                    padding: 15px;
                }
                
                .metrics-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """
    
    def generate_html_report(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成HTML报告
        
        Args:
            analysis_result: 分析结果字典
            
        Returns:
            HTML报告字符串
        """
        if analysis_result.get('status') == 'error':
            return self._generate_error_html(analysis_result.get('error', '未知错误'))
        
        symbol = analysis_result.get('symbol', 'Unknown')
        analysis_date = analysis_result.get('analysis_date', '')
        data_period = analysis_result.get('data_period', '')
        
        # 生成各个部分
        header_html = self._generate_header(symbol, analysis_date)
        summary_html = self._generate_summary(analysis_result)
        indicators_html = self._generate_indicators_section(analysis_result.get('indicators', {}))
        recommendation_html = self._generate_recommendation_section(analysis_result.get('investment_advice', {}))
        master_analysis_html = self._generate_master_analysis_section(analysis_result.get('master_analysis', {}))
        footer_html = self._generate_footer()
        
        # 组装完整HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="{self._get_html_lang()}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{t_gui('迷你投资大师分析报告')} - {symbol}</title>
            {self.css_styles}
        </head>
        <body>
            <div class="container">
                {header_html}
                {summary_html}
                {recommendation_html}
                {indicators_html}
                {master_analysis_html}
                {footer_html}
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _generate_header(self, symbol: str, analysis_date: str) -> str:
        """
        生成报告头部
        """
        return f"""
        <div class="header">
            <h1>{t_gui('迷你投资大师分析报告')}</h1>
            <div class="subtitle">{t_gui('股票代码')}: {symbol}</div>
            <div class="subtitle">{t_gui('分析时间')}: {analysis_date}</div>
            <div class="subtitle">{t_gui('智能投资决策 · 多维度分析 · 风险控制')}</div>
        </div>
        """
    
    def _generate_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成摘要部分
        """
        summary = analysis_result.get('summary', t_gui('暂无摘要'))
        data_period = analysis_result.get('data_period', '')
        
        return f"""
        <div class="section">
            <h2>{t_gui('分析摘要')}</h2>
            <p><strong>{t_gui('分析周期')}:</strong> {data_period}</p>
            <p>{summary}</p>
        </div>
        """
    
    def _generate_recommendation_section(self, investment_advice: Dict[str, Any]) -> str:
        """
        生成投资建议部分
        """
        if not investment_advice:
            return f'<div class="section"><h2>{t_gui("投资建议")}</h2><p>{t_gui("暂无投资建议")}</p></div>'
        
        recommendation = investment_advice.get('recommendation', t_gui('观望'))
        confidence = investment_advice.get('confidence', 0)
        risk_level = investment_advice.get('risk_level', t_gui('中等'))
        reasoning = investment_advice.get('reasoning', t_gui('暂无分析理由'))
        master_insights = investment_advice.get('master_insights', [])
        
        # 确定推荐类型的CSS类
        rec_class = 'hold'
        buy_terms = [t_gui('强烈买入'), t_gui('买入'), t_gui('谨慎买入')]
        sell_terms = [t_gui('强烈卖出'), t_gui('卖出'), t_gui('谨慎卖出')]
        if recommendation in buy_terms:
            rec_class = 'buy'
        elif recommendation in sell_terms:
            rec_class = 'sell'
        elif recommendation == t_gui('持有'):
            rec_class = 'hold'
        
        # 生成投资洞察列表
        insights_html = ''
        if master_insights:
            insights_items = ''.join([f'<li>{insight}</li>' for insight in master_insights])
            insights_html = f"""
            <div class="insights">
                <h4>{t_gui('投资大师观点')}</h4>
                <ul>
                    {insights_items}
                </ul>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>{t_gui('投资建议')}</h2>
            <div class="recommendation {rec_class}">
                <h3>{t_gui('推荐操作')}: {recommendation}</h3>
                <p><strong>{t_gui('置信度')}:</strong> {confidence:.1f}%</p>
                <p><strong>{t_gui('风险等级')}:</strong> {risk_level}</p>
                <p><strong>{t_gui('分析理由')}:</strong> {reasoning}</p>
                {insights_html}
            </div>
        </div>
        """
    
    def _generate_indicators_section(self, indicators: Dict[str, Any]) -> str:
        """
        生成技术指标部分
        """
        if not indicators:
            return f'<div class="section"><h2>{t_gui("技术指标")}</h2><p>{t_gui("暂无技术指标数据")}</p></div>'
        
        # 生成指标卡片
        metrics_html = ''
        
        # 基础价格信息
        if 'current_price' in indicators:
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-label">{t_gui('当前价格')}</div>
                <div class="metric-value">{indicators['current_price']:.2f} 元</div>
            </div>
            """
        
        if 'price_change_pct' in indicators:
            # 红涨绿跌：上涨用红色，下跌用绿色
            change_color = '#e74c3c' if indicators['price_change_pct'] >= 0 else '#27ae60'
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-label">{t_gui('价格变化')}</div>
                <div class="metric-value" style="color: {change_color}">{indicators['price_change_pct']:+.2f}%</div>
            </div>
            """
        
        # 移动平均线
        for ma in ['ma5', 'ma10', 'ma20', 'ma60']:
            if ma in indicators:
                metrics_html += f"""
                <div class="metric-card">
                    <div class="metric-label">{ma.upper()}</div>
                    <div class="metric-value">{indicators[ma]:.2f}</div>
                </div>
                """
        
        # RSI
        if 'rsi' in indicators:
            rsi_color = '#e74c3c' if indicators['rsi'] > 70 else '#27ae60' if indicators['rsi'] < 30 else '#3498db'
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-label">RSI</div>
                <div class="metric-value" style="color: {rsi_color}">{indicators['rsi']:.1f}</div>
            </div>
            """
        
        # 波动率
        if 'volatility' in indicators:
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-label">年化波动率</div>
                <div class="metric-value">{indicators['volatility']:.1f}%</div>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>{t_gui('技术指标')}</h2>
            <div class="metrics-grid">
                {metrics_html}
            </div>
        </div>
        """
    
    def _generate_master_analysis_section(self, master_analysis: Dict[str, Any]) -> str:
        """
        生成投资大师分析部分
        """
        if not master_analysis:
            return f'<div class="section"><h2>{t_gui("投资大师评分")}</h2><p>{t_gui("暂无投资大师评分")}</p></div>'
        
        overall_score = master_analysis.get('overall_score', 0)
        best_strategy = master_analysis.get('best_strategy', '综合策略')
        strategy_breakdown = master_analysis.get('strategy_breakdown', {})
        
        # 生成策略评分
        strategy_html = ''
        strategy_names = {
            'buffett': t_gui('巴菲特价值投资'),
            'lynch': t_gui('林奇成长投资'),
            'graham': t_gui('格雷厄姆防御投资'),
            'druckenmiller': t_gui('索罗斯趋势投资'),
            'burry': t_gui('彼得·德鲁克管理投资')
        }
        
        for strategy_key, score in strategy_breakdown.items():
            strategy_name = strategy_names.get(strategy_key, strategy_key)
            strategy_html += f"""
            <div class="strategy-item">
                <span class="strategy-name">{strategy_name}</span>
                <span class="strategy-score">{score:.1f}分</span>
            </div>
            """
        
        return f"""
        <div class="section">
            <h2>{t_gui('投资大师评分')}</h2>
            <div class="metric-card">
                <div class="metric-label">{t_gui('总体评分')}</div>
                <div class="metric-value">{overall_score:.1f}/100</div>
            </div>
            <p><strong>最佳策略:</strong> {best_strategy}</p>
            <div class="strategy-scores">
                <h4>{t_gui('策略分解')}</h4>
                {strategy_html}
            </div>
        </div>
        """
    
    def _generate_footer(self) -> str:
        """
        生成页脚
        """
        return f"""
        <div class="footer">
            <p>{t_gui('迷你投资大师')} | {t_gui('智能投资决策 · 多维度分析 · 风险控制')}</p>
            <p style="margin-top: 10px; font-size: 0.8em; opacity: 0.8;">
                {t_gui('本系统所有内容均为测试数据，仅供学习和研究使用。所有分析结果、建议和推荐均不构成投资建议，不能用于真实投资决策。投资有风险，决策需谨慎。')}
            </p>
        </div>
        """
    
    def _generate_error_html(self, error_message: str) -> str:
        """
        生成错误页面
        """
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>分析报告 - 错误</title>
            {self.css_styles}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>迷你投资大师</h1>
                    <div class="subtitle">分析报告生成失败</div>
                </div>
                <div class="section">
                    <div class="error">
                        <h3>错误信息</h3>
                        <p>{error_message}</p>
                    </div>
                </div>
                {self._generate_footer()}
            </div>
        </body>
        </html>
        """
    
    def save_report(self, html_content: str, filename: str = None) -> str:
        """
        保存HTML报告到文件
        
        Args:
            html_content: HTML内容
            filename: 文件名，如果为None则自动生成
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'mini_investment_master_report_{timestamp}.html'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"报告已保存到: {filename}")
            return filename
        except Exception as e:
            print(f"保存报告失败: {e}")
            return ''


class MiniInvestmentMasterGUI:
    """
    迷你投资大师GUI接口类
    为GUI应用提供简化的调用接口
    """
    
    def __init__(self):
        self.analyzer = MiniInvestmentMaster()
        self.html_generator = SimpleHTMLGenerator()
    
    def analyze_stock_for_gui(self, symbol: str) -> Dict[str, Any]:
        """
        为GUI提供的股票分析接口
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含分析结果和HTML报告的字典
        """
        try:
            # 执行股票分析
            analysis_result = self.analyzer.analyze_stock(symbol)
            
            if analysis_result['status'] == 'error':
                return {
                    'status': 'error',
                    'error': analysis_result['error'],
                    'html_report': self.html_generator._generate_error_html(analysis_result['error'])
                }
            
            # 生成HTML报告
            html_report = self.html_generator.generate_html_report(analysis_result)
            
            return {
                'status': 'success',
                'analysis_result': analysis_result,
                'html_report': html_report,
                'summary': analysis_result.get('summary', ''),
                'recommendation': analysis_result.get('investment_advice', {}).get('recommendation', '观望'),
                'confidence': analysis_result.get('investment_advice', {}).get('confidence', 0),
                'risk_level': analysis_result.get('investment_advice', {}).get('risk_level', '中等')
            }
            
        except Exception as e:
            error_msg = f"分析过程中出现错误: {str(e)}"
            return {
                'status': 'error',
                'error': error_msg,
                'html_report': self.html_generator._generate_error_html(error_msg)
            }
    
    def get_analysis_summary(self, symbol: str) -> str:
        """
        获取股票分析摘要
        
        Args:
            symbol: 股票代码
            
        Returns:
            分析摘要字符串
        """
        result = self.analyze_stock_for_gui(symbol)
        if result['status'] == 'success':
            return result['summary']
        else:
            return f"分析失败: {result['error']}"


def main():
    """
    主函数 - 演示如何使用迷你投资大师
    """
    print("=" * 50)
    print("迷你投资大师 - 独立分析系统")
    print("=" * 50)
    
    # 创建GUI接口
    gui_interface = MiniInvestmentMasterGUI()
    
    # 获取用户输入
    while True:
        symbol = input("\n请输入股票代码 (例如: 000001, 600519，输入 'quit' 退出): ").strip()
        
        if symbol.lower() == 'quit':
            print("感谢使用迷你投资大师！")
            break
        
        if not symbol:
            print("请输入有效的股票代码")
            continue
        
        try:
            # 使用GUI接口分析股票
            print(f"\n开始分析股票 {symbol}...")
            result = gui_interface.analyze_stock_for_gui(symbol)
            
            if result['status'] == 'error':
                print(f"分析失败: {result['error']}")
                continue
            
            # 显示分析结果
            print("\n" + "=" * 30)
            print("分析结果")
            print("=" * 30)
            print(result['summary'])
            
            # 显示投资建议
            print(f"\n投资建议: {result['recommendation']}")
            print(f"置信度: {result['confidence']:.1f}%")
            print(f"风险等级: {result['risk_level']}")
            
            # 保存HTML报告
            filename = gui_interface.html_generator.save_report(result['html_report'], f'{symbol}_analysis_report.html')
            
            if filename:
                print(f"\n✅ 分析完成！HTML报告已保存为: {filename}")
                print("您可以用浏览器打开该文件查看详细报告。")
            
        except Exception as e:
            print(f"分析过程中出现错误: {e}")
        
        # 询问是否继续
        continue_analysis = input("\n是否继续分析其他股票？(y/n): ").strip().lower()
        if continue_analysis not in ['y', 'yes', '是']:
            print("感谢使用迷你投资大师！")
            break


if __name__ == "__main__":
    main()