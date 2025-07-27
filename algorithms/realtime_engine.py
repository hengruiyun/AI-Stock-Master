"""
from config.i18n import t_gui as _
实时分析引擎模块

提供高性能的股票分析计算引擎，整合RTSI、IRSI、MSCI三大核心算法。
支持多线程并行计算、结果缓存、性能监控等功能。

作者: 267278466@qq.com
版本: 1.0.0
"""

import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

from data.stock_dataset import StockDataSet
from algorithms.rtsi_calculator import calculate_rating_trend_strength_index
from algorithms.irsi_calculator import calculate_industry_relative_strength
from algorithms.msci_calculator import calculate_market_sentiment_composite_index
from config import get_config

# 配置日志

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisResults:
    """分析结果数据类"""
    
    def __init__(self):
        self.stocks: Dict[str, Dict] = {}
        self.industries: Dict[str, Dict] = {}
        self.market: Dict = {}
        self.metadata: Dict = {
            'calculation_time': None,
            'total_stocks': 0,
            'total_industries': 0,
            'cache_hit_rate': 0,
            'performance_metrics': {}
        }
        self.last_updated = datetime.now()
    
    def get_top_stocks(self, metric: str = 'rtsi', top_n: int = 50) -> List[Tuple[str, str, float]]:
        """获取指定指标的前N只股票"""
        try:
            stock_scores = []
            for code, data in self.stocks.items():
                if metric in data and data[metric] is not None:
                    # 修复：正确提取RTSI分数
                    if isinstance(data[metric], dict):
                        if metric == 'rtsi':
                            score = data[metric].get('rtsi', 0)  # RTSI存储在'rtsi'字段
                        else:
                            score = data[metric].get('value', 0)  # 其他指标可能存储在'value'字段
                    else:
                        score = data[metric]
                    
                    # 处理numpy类型
                    import numpy as np
                    if isinstance(score, (np.number, np.integer, np.floating)):
                        score = float(score)
                    elif not isinstance(score, (int, float)):
                        score = 0.0
                    
                    stock_scores.append((code, data.get('name', ''), score))
            
            stock_scores.sort(key=lambda x: x[2], reverse=True)
            return stock_scores[:top_n]
        except Exception as e:
            logger.error(f"获取top stocks失败: {e}")
            return []
    
    def get_top_industries(self, metric: str = 'irsi', top_n: int = 20) -> List[Tuple[str, float]]:
        """获取指定指标的前N个行业"""
        try:
            industry_scores = []
            for industry, data in self.industries.items():
                if metric in data and data[metric] is not None:
                    # 修复：正确提取IRSI分数
                    if isinstance(data[metric], dict):
                        if metric == 'irsi':
                            score = data[metric].get('irsi', 0)  # IRSI存储在'irsi'字段
                        else:
                            score = data[metric].get('value', 0)  # 其他指标可能存储在'value'字段
                    else:
                        score = data[metric]
                    
                    # 处理numpy类型
                    import numpy as np
                    if isinstance(score, (np.number, np.integer, np.floating)):
                        score = float(score)
                    elif not isinstance(score, (int, float)):
                        score = 0.0
                    
                    industry_scores.append((industry, score))
            
            industry_scores.sort(key=lambda x: x[1], reverse=True)
            return industry_scores[:top_n]
        except Exception as e:
            logger.error(f"获取top industries失败: {e}")
            return []
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'stocks': self.stocks,
            'industries': self.industries,
            'market': self.market,
            'metadata': self.metadata,
            'last_updated': self.last_updated.isoformat()
        }


class RealtimeAnalysisEngine:
    """
    实时分析引擎
    
    功能特性:
    - 整合RTSI、IRSI、MSCI三大算法
    - 支持多线程并行计算 (可配置开关)
    - 智能缓存机制
    - 实时性能监控
    - 增量计算支持
    """
    
    def __init__(self, data_source: StockDataSet, enable_multithreading: bool = True):
        """
        初始化实时分析引擎
        
        Args:
            data_source: 股票数据源
            enable_multithreading: 是否启用多线程计算
        """
        self.data_source = data_source
        self.enable_multithreading = enable_multithreading
        self.results_cache: Optional[AnalysisResults] = None
        self.last_calculation_time: Optional[datetime] = None
        self.calculation_lock = threading.Lock()
        
        # 配置参数
        try:
            self.config = get_config('engine', {
                'cache_ttl': 300,  # 缓存5分钟
                'max_workers': 4,  # 最大线程数
                'chunk_size': 100, # 批处理大小
                'timeout': 300     # 计算超时时间
            })
            # 如果get_config返回None，使用默认配置
            if self.config is None:
                self.config = {
                    'cache_ttl': 300,
                    'max_workers': 4,
                    'chunk_size': 100,
                    'timeout': 300
                }
        except Exception:
            # 如果配置获取失败，使用默认配置
            self.config = {
                'cache_ttl': 300,
                'max_workers': 4,
                'chunk_size': 100,
                'timeout': 300
            }
        
        # 性能统计
        self.performance_stats = {
            'total_calculations': 0,
            'avg_calculation_time': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
        
        logger.info(f"实时分析引擎初始化完成 (多线程: {enable_multithreading})")
    
    def calculate_all_metrics(self, force_refresh: bool = False) -> AnalysisResults:
        """
        计算所有指标
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            完整的分析结果
        """
        start_time = time.time()
        
        with self.calculation_lock:
            # 检查缓存
            if not force_refresh and self._is_cache_valid():
                self.performance_stats['cache_hits'] += 1
                logger.info("使用缓存结果")
                return self.results_cache
            
            self.performance_stats['cache_misses'] += 1
            logger.info("开始完整计算...")
            
            try:
                # 获取数据
                raw_data = self.data_source.get_raw_data()
                if raw_data is None or raw_data.empty:
                    raise ValueError("数据源为空")
                
                # 创建结果对象
                results = AnalysisResults()
                
                # 多线程或单线程计算
                if self.enable_multithreading:
                    results = self._calculate_multithreaded(raw_data, results)
                else:
                    results = self._calculate_single_threaded(raw_data, results)
                
                # 更新缓存和统计
                self.results_cache = results
                self.last_calculation_time = datetime.now()
                self.performance_stats['total_calculations'] += 1
                
                # 计算性能指标
                calculation_time = time.time() - start_time
                self._update_performance_stats(calculation_time)
                
                results.metadata['calculation_time'] = calculation_time
                results.metadata['total_stocks'] = len(results.stocks)
                results.metadata['total_industries'] = len(results.industries)
                results.metadata['cache_hit_rate'] = self._get_cache_hit_rate()
                results.metadata['performance_metrics'] = self.performance_stats.copy()
                
                logger.info(f"计算完成: {len(results.stocks)}只股票, {len(results.industries)}个行业, 耗时{calculation_time:.2f}秒")
                
                return results
                
            except Exception as e:
                self.performance_stats['errors'] += 1
                logger.error(f"计算失败: {e}")
                raise
    
    def _calculate_multithreaded(self, raw_data: pd.DataFrame, results: AnalysisResults) -> AnalysisResults:
        """多线程计算模式"""
        logger.info("使用多线程计算模式")
        
        # 1. 多线程计算个股RTSI
        results.stocks = self._calculate_stocks_rtsi_parallel(raw_data)
        
        # 2. 计算行业IRSI (基于已计算的个股结果)
        results.industries = self._calculate_industries_irsi(raw_data, results.stocks)
        
        # 3. 计算市场MSCI
        results.market = self._calculate_market_msci(raw_data)
        
        return results
    
    def _calculate_single_threaded(self, raw_data: pd.DataFrame, results: AnalysisResults) -> AnalysisResults:
        """单线程计算模式"""
        logger.info("使用单线程计算模式")
        
        # 1. 计算个股RTSI
        results.stocks = self._calculate_stocks_rtsi_sequential(raw_data)
        
        # 2. 计算行业IRSI
        results.industries = self._calculate_industries_irsi(raw_data, results.stocks)
        
        # 3. 计算市场MSCI
        results.market = self._calculate_market_msci(raw_data)
        
        return results
    
    def _calculate_stocks_rtsi_parallel(self, raw_data: pd.DataFrame) -> Dict[str, Dict]:
        """多线程并行计算个股RTSI"""
        stocks_results = {}
        date_columns = [col for col in raw_data.columns if str(col).startswith('202')]
        
        def calculate_single_stock(stock_data):
            try:
                stock_code = str(stock_data['股票代码'])
                stock_name = stock_data.get('股票名称', '')
                industry = stock_data.get('行业', '未分类')
                
                # 获取评级序列
                ratings = stock_data[date_columns]
                
                # 计算RTSI
                rtsi_result = calculate_rating_trend_strength_index(ratings)
                
                return stock_code, {
                    'name': stock_name,
                    'industry': industry,
                    'rtsi': rtsi_result,
                    'last_score': rtsi_result.get('recent_score'),
                    'trend': rtsi_result.get('trend', 'unknown')
                }
            except Exception as e:
                logger.warning(f"计算股票RTSI失败 {stock_data.get('股票代码', 'unknown')}: {e}")
                return None, None
        
        # 多线程执行
        max_workers = min(self.config['max_workers'], len(raw_data))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            futures = []
            for _, stock_data in raw_data.iterrows():
                future = executor.submit(calculate_single_stock, stock_data)
                futures.append(future)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures, timeout=self.config['timeout']):
                try:
                    stock_code, result = future.result()
                    if stock_code and result:
                        stocks_results[stock_code] = result
                    completed += 1
                    
                    if completed % 100 == 0:
                        logger.info(f"已完成 {completed}/{len(futures)} 只股票计算")
                        
                except Exception as e:
                    logger.warning(f"获取任务结果失败: {e}")
        
        return stocks_results
    
    def _calculate_stocks_rtsi_sequential(self, raw_data: pd.DataFrame) -> Dict[str, Dict]:
        """单线程顺序计算个股RTSI"""
        stocks_results = {}
        date_columns = [col for col in raw_data.columns if str(col).startswith('202')]
        
        for idx, stock_data in raw_data.iterrows():
            try:
                stock_code = str(stock_data['股票代码'])
                stock_name = stock_data.get('股票名称', '')
                industry = stock_data.get('行业', '未分类')
                
                # 获取评级序列
                ratings = stock_data[date_columns]
                
                # 计算RTSI
                rtsi_result = calculate_rating_trend_strength_index(ratings)
                
                stocks_results[stock_code] = {
                    'name': stock_name,
                    'industry': industry,
                    'rtsi': rtsi_result,
                    'last_score': rtsi_result.get('recent_score'),
                    'trend': rtsi_result.get('trend', 'unknown')
                }
                
                if (idx + 1) % 100 == 0:
                    logger.info(f"已完成 {idx + 1}/{len(raw_data)} 只股票计算")
                    
            except Exception as e:
                logger.warning(f"计算股票RTSI失败 {stock_data.get('股票代码', 'unknown')}: {e}")
        
        return stocks_results
    
    def _calculate_industries_irsi(self, raw_data: pd.DataFrame, stocks_results: Dict) -> Dict[str, Dict]:
        """计算行业IRSI"""
        industries_results = {}
        
        # 按行业分组
        industries = raw_data['行业'].dropna().unique()
        
        for industry in industries:
            try:
                # 获取行业数据
                industry_data = raw_data[raw_data['行业'] == industry]
                
                # 计算行业IRSI
                irsi_result = calculate_industry_relative_strength(industry_data, raw_data)
                
                # 统计行业内股票信息
                industry_stocks = []
                for _, stock in industry_data.iterrows():
                    stock_code = str(stock['股票代码'])
                    if stock_code in stocks_results:
                        industry_stocks.append({
                            'code': stock_code,
                            'name': stocks_results[stock_code]['name'],
                            'rtsi': stocks_results[stock_code]['rtsi'].get('rtsi', 0)
                        })
                
                industries_results[industry] = {
                    'irsi': irsi_result,
                    'stock_count': len(industry_stocks),
                    'stocks': industry_stocks[:10],  # 只保存前10只代表股票
                    'status': irsi_result.get('status', 'unknown')
                }
                
            except Exception as e:
                logger.warning(f"计算行业IRSI失败 {industry}: {e}")
        
        return industries_results
    
    def _calculate_market_msci(self, raw_data: pd.DataFrame) -> Dict:
        """计算市场MSCI"""
        try:
            msci_result = calculate_market_sentiment_composite_index(raw_data)
            return msci_result
        except Exception as e:
            logger.error(f"计算市场MSCI失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.results_cache or not self.last_calculation_time:
            return False
        
        cache_age = (datetime.now() - self.last_calculation_time).total_seconds()
        return cache_age < self.config.get('cache_ttl', 300)
    
    def _update_performance_stats(self, calculation_time: float):
        """更新性能统计"""
        total = self.performance_stats['total_calculations']
        current_avg = self.performance_stats['avg_calculation_time']
        
        # 计算新的平均时间
        new_avg = (current_avg * (total - 1) + calculation_time) / total
        self.performance_stats['avg_calculation_time'] = new_avg
    
    def _get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total_requests = self.performance_stats['cache_hits'] + self.performance_stats['cache_misses']
        if total_requests == 0:
            return 0
        return self.performance_stats['cache_hits'] / total_requests
    
    def update_analysis(self, new_data: pd.DataFrame) -> Dict:
        """
        增量更新分析结果
        
        Args:
            new_data: 新的数据
            
        Returns:
            更新状态信息
        """
        try:
            logger.info("开始增量更新分析...")
            
            # 更新数据源
            self.data_source.update_data(new_data)
            
            # 强制重新计算
            results = self.calculate_all_metrics(force_refresh=True)
            
            return {
                'status': 'success',
                'updated_stocks': len(results.stocks),
                'updated_industries': len(results.industries),
                'update_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"增量更新失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'update_time': datetime.now().isoformat()
            }
    
    def get_real_time_rankings(self) -> Dict:
        """获取实时排名"""
        if not self.results_cache:
            logger.warning("没有可用的分析结果")
            return {}
        
        return {
            'top_stocks_by_rtsi': self.results_cache.get_top_stocks('rtsi', 20),
            'top_industries_by_irsi': self.results_cache.get_top_industries('irsi', 10),
            'market_sentiment': self.results_cache.market.get('current_msci', 0),
            'market_state': self.results_cache.market.get('market_state', 'unknown'),
            'last_updated': self.results_cache.last_updated.isoformat()
        }
    
    def detect_trend_changes(self) -> List[Dict]:
        """检测趋势变化信号"""
        if not self.results_cache:
            return []
        
        signals = []
        
        try:
            # 检测个股强势反转信号
            for stock_code, data in self.results_cache.stocks.items():
                rtsi_data = data.get('rtsi', {})
                rtsi_value = rtsi_data.get('rtsi', 0)
                trend = rtsi_data.get('trend', '')
                confidence = rtsi_data.get('confidence', 0)
                
                # 强势反转信号
                if rtsi_value > 70 and trend in ['strong_up', 'weak_up'] and confidence > 0.7:
                    signals.append({
                        'type': 'stock_bullish',
                        'target': stock_code,
                        'name': data.get('name', ''),
                        'signal': f"强势上涨信号 (RTSI: {rtsi_value:.2f})",
                        'confidence': confidence,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # 风险预警信号
                elif rtsi_value < 20 and trend in ['strong_down', 'weak_down'] and confidence > 0.7:
                    signals.append({
                        'type': 'stock_bearish',
                        'target': stock_code,
                        'name': data.get('name', ''),
                        'signal': f"下跌风险预警 (RTSI: {rtsi_value:.2f})",
                        'confidence': confidence,
                        'timestamp': datetime.now().isoformat()
                    })
            
            # 检测行业轮动信号
            for industry, data in self.results_cache.industries.items():
                irsi_data = data.get('irsi', {})
                irsi_value = irsi_data.get('irsi', 0)
                status = irsi_data.get('status', '')
                
                if irsi_value > 30 and status == 'strong_outperform':
                    signals.append({
                        'type': 'industry_rotation',
                        'target': industry,
                        'signal': f"行业轮动信号 (IRSI: {irsi_value:.2f})",
                        'stock_count': data.get('stock_count', 0),
                        'timestamp': datetime.now().isoformat()
                    })
            
            # 检测市场情绪极端信号
            market_state = self.results_cache.market.get('market_state', '')
            msci_value = self.results_cache.market.get('current_msci', 0)
            
            if market_state in ['euphoric', 'panic']:
                signals.append({
                    'type': 'market_extreme',
                    'target': 'market',
                    'signal': f"市场情绪极端: {market_state} (MSCI: {msci_value:.2f})",
                    'risk_level': self.results_cache.market.get('risk_level', 'unknown'),
                    'timestamp': datetime.now().isoformat()
                })
            
            logger.info(f"检测到 {len(signals)} 个趋势信号")
            return signals[:50]  # 限制返回数量
            
        except Exception as e:
            logger.error(f"趋势检测失败: {e}")
            return []
    
    def cache_results(self) -> None:
        """手动缓存当前结果"""
        if self.results_cache:
            # 可以在这里实现持久化缓存逻辑
            logger.info("结果已缓存")
    
    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        return {
            'engine_config': {
                'multithreading_enabled': self.enable_multithreading,
                'max_workers': self.config.get('max_workers', 4),
                'cache_ttl': self.config.get('cache_ttl', 300)
            },
            'performance_stats': self.performance_stats.copy(),
            'cache_status': {
                'is_cached': self.results_cache is not None,
                'cache_age': (datetime.now() - self.last_calculation_time).total_seconds() 
                            if self.last_calculation_time else None,
                'hit_rate': self._get_cache_hit_rate()
            },
            'last_calculation': self.last_calculation_time.isoformat() 
                              if self.last_calculation_time else None
        }


# 便捷函数
def create_engine(data_source: StockDataSet, enable_multithreading: bool = True) -> RealtimeAnalysisEngine:
    """创建实时分析引擎实例"""
    return RealtimeAnalysisEngine(data_source, enable_multithreading)


if __name__ == "__main__":
    # 测试代码
    print("-")
    
    # 这里可以添加简单的测试逻辑
    try:
        from data.stock_dataset import StockDataset
        
        # 创建测试数据源
        dataset = StockDataset("A股数据20250606.xlsx")
        
        # 测试多线程引擎
        print("\n=== 测试多线程引擎 ===")
        engine_mt = create_engine(dataset, enable_multithreading=True)
        start_time = time.time()
        results_mt = engine_mt.calculate_all_metrics()
        mt_time = time.time() - start_time
        print(f"多线程计算耗时: {mt_time:.2f}秒")
        print(f"计算股票数: {len(results_mt.stocks)}")
        print(f"计算行业数: {len(results_mt.industries)}")
        
        # 测试单线程引擎
        print("\n=== 测试单线程引擎 ===")
        engine_st = create_engine(dataset, enable_multithreading=False)
        start_time = time.time()
        results_st = engine_st.calculate_all_metrics()
        st_time = time.time() - start_time
        print(f"单线程计算耗时: {st_time:.2f}秒")
        print(f"计算股票数: {len(results_st.stocks)}")
        print(f"计算行业数: {len(results_st.industries)}")
        
        # 性能对比
        print(f"\n=== 性能对比 ===")
        print(f"多线程 vs 单线程加速比: {st_time/mt_time:.2f}x")
        
        # 测试缓存
        print("\n=== 测试缓存 ===")
        start_time = time.time()
        results_cached = engine_mt.calculate_all_metrics()  # 应该使用缓存
        cached_time = time.time() - start_time
        print(f"缓存查询耗时: {cached_time:.4f}秒")
        
        # 测试排名功能
        rankings = engine_mt.get_real_time_rankings()
        print(f"\n=== 实时排名 ===")
        print(f"Top 5 RTSI股票:")
        for i, (code, name, score) in enumerate(rankings['top_stocks_by_rtsi'][:5], 1):
            print(f"  {i}. {code} {name}: {score:.2f}")
        
        # 测试信号检测
        signals = engine_mt.detect_trend_changes()
        print(f"\n=== 趋势信号 ===")
        print(f"检测到 {len(signals)} 个信号")
        for signal in signals[:3]:
            print(f"  {signal['type']}: {signal['signal']}")
        
        print("\n成功 实时分析引擎测试完成")
        
    except Exception as e:
        print(f"错误 测试失败: {e}")
        import traceback
        traceback.print_exc()