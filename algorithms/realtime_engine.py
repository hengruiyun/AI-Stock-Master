"""
from config.gui_i18n import t_gui as _
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
from algorithms.enhanced_rtsi_calculator import EnhancedRTSICalculator
from algorithms.irsi_calculator import calculate_industry_relative_strength
from algorithms.msci_calculator import calculate_market_sentiment_composite_index

# 导入增强版TMA分析器
try:
    from algorithms.enhanced_tma_analyzer import EnhancedTMAAnalyzer, enhanced_industry_analysis
    ENHANCED_TMA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"增强TMA分析器不可用，使用基础模式: {e}")
    ENHANCED_TMA_AVAILABLE = False
from config import get_config

# 配置日志

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
    
    def get_top_stocks(self, metric: str = 'rtsi', top_n: int = 50, large_cap_only: bool = True) -> List[Tuple[str, str, float]]:
        """获取指定指标的前N只股票
        
        Args:
            metric: 指标名称
            top_n: 返回数量
            large_cap_only: 是否只返回大盘股
        """
        try:
            stock_scores = []
            for code, data in self.stocks.items():
                if metric in data and data[metric] is not None:
                    # 大盘股筛选：只推荐大盘股
                    if large_cap_only and not self._is_large_cap_stock(code):
                        continue
                    
                    # 修复：正确提取RTSI分数
                    if isinstance(data[metric], dict):
                        if metric == 'rtsi':
                            # 使用国际化键名获取RTSI值
                            # t_rtsi 已在文件开头定义
                            score = data[metric].get(t_rtsi('rtsi'), data[metric].get('RTSI', data[metric].get('rtsi', 0)))
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
    
    def _is_large_cap_stock(self, stock_code: str) -> bool:
        """判断是否为大盘股
        
        基于股票代码前缀和已知的大盘股规律判断：
        - A股：以00、60开头的通常是大盘股
        - 港股：00700(腾讯)、00939(建设银行)等知名大盘股
        - 美股：AAPL、MSFT、GOOGL等知名大公司
        """
        code = str(stock_code).strip()
        
        # A股大盘股判断
        if len(code) == 6 and code.isdigit():
            # 主板股票通常是大盘股
            if code.startswith('00') or code.startswith('60'):
                return True
            # 部分深市主板大盘股（001、002开头的部分股票）
            if code.startswith('001') or code.startswith('002'):
                # 可以在这里添加更精确的判断逻辑
                return True
        
        # 港股大盘股判断（5位数字）
        elif len(code) == 5 and code.isdigit():
            # 知名港股大盘股代码
            large_cap_hk_codes = {
                '00700', '00939', '00388', '00005', '00001', '00002', '00003', '00004',
                '00011', '00012', '00016', '00017', '00019', '00023', '00027', '00066',
                '00083', '00101', '00135', '00144', '00151', '00175', '00267', '00288',
                '00386', '00688', '00762', '00823', '00857', '00883', '00941', '00992',
                '01038', '01044', '01088', '01093', '01109', '01113', '01171', '01177',
                '01299', '01398', '01818', '01928', '01997', '02007', '02018', '02020',
                '02202', '02318', '02319', '02382', '02388', '02628', '03328', '03988'
            }
            return code in large_cap_hk_codes
        
        # 美股大盘股判断（字母代码）
        elif code.isalpha():
            # 知名美股大盘股代码
            large_cap_us_codes = {
                'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA',
                'BRK.A', 'BRK.B', 'UNH', 'JNJ', 'JPM', 'V', 'PG', 'HD', 'MA', 'PFE',
                'ABBV', 'BAC', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'DIS', 'ABT',
                'MRK', 'ACN', 'VZ', 'CRM', 'DHR', 'ADBE', 'NKE', 'TXN', 'LIN',
                'WMT', 'NEE', 'AMD', 'BMY', 'PM', 'RTX', 'QCOM', 'HON', 'T',
                'UPS', 'ORCL', 'COP', 'MS', 'SCHW', 'LOW', 'CAT', 'GS', 'IBM',
                'AXP', 'BLK', 'DE', 'ELV', 'LMT', 'SYK', 'TJX', 'MDT', 'ADP',
                'GE', 'C', 'MDLZ', 'ISRG', 'REGN', 'CB', 'MMC', 'SO', 'PLD',
                'NOW', 'ZTS', 'ICE', 'DUK', 'SHW', 'CMG', 'WM', 'GD', 'TGT',
                'BDX', 'ITW', 'EOG', 'FIS', 'NSC', 'SRE', 'MU', 'BSX', 'FCX'
            }
            return code.upper() in large_cap_us_codes
        
        # 默认不是大盘股
        return False
    
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
    
    def __init__(self, data_source: StockDataSet, enable_multithreading: bool = True, enable_enhanced_tma: bool = True):
        """
        初始化实时分析引擎
        
        Args:
            data_source: 股票数据源
            enable_multithreading: 是否启用多线程计算
            enable_enhanced_tma: 是否启用增强TMA分析
        """
        self.data_source = data_source
        self.enable_multithreading = enable_multithreading
        self.enable_enhanced_tma = enable_enhanced_tma and ENHANCED_TMA_AVAILABLE
        self.results_cache: Optional[AnalysisResults] = None
        self.last_calculation_time: Optional[datetime] = None
        self.calculation_lock = threading.Lock()
        
        # 初始化增强TMA分析器（如果启用）
        if self.enable_enhanced_tma:
            try:
                self.enhanced_tma_analyzer = EnhancedTMAAnalyzer(
                    enable_ai_enhancement=False,  # 根据测试结果关闭AI增强
                    min_credibility=0.2,  # 最佳可信度阈值
                    max_interpolation_ratio=0.5,  # 最佳插值比例
                    min_stocks_per_industry=2  # 最小股票数
                )
                logger.info("增强TMA分析器已启用")
            except Exception as e:
                logger.warning(f"增强TMA分析器初始化失败，使用基础模式: {e}")
                self.enable_enhanced_tma = False
        
        # 初始化智能RTSI计算器
        # 先初始化所有属性为None
        self.smart_rtsi_calculator = None
        self.enhanced_rtsi_calculator = None
        
        try:
            from .smart_rtsi_algorithm import get_smart_rtsi_calculator
            # 在多线程模式下禁用缓存以避免AKShare延迟
            enable_cache = not enable_multithreading
            self.smart_rtsi_calculator = get_smart_rtsi_calculator(enable_cache=enable_cache, verbose=False)
            logger.info(f"智能RTSI计算器已启用 (缓存: {enable_cache})")
        except Exception as e:
            logger.warning(f"智能RTSI计算器初始化失败: {e}")
            
        # 总是初始化增强RTSI计算器，用于批量计算
        try:
            self.enhanced_rtsi_calculator = EnhancedRTSICalculator()
            logger.info("增强RTSI计算器已启用")
        except Exception as e2:
            logger.warning(f"增强RTSI计算器初始化失败，使用基础模式: {e2}")
        
        # 配置参数 - 优化性能设置
        try:
            self.config = get_config('engine', {
                'cache_ttl': 600,  # 增加缓存时间到10分钟
                'max_workers': 4,  # 适当增加线程数以提高并行度
                'chunk_size': 100, # 增加批处理大小
                'timeout': 180     # 适当的超时时间
            })
            # 如果get_config返回None，使用默认配置
            if self.config is None:
                self.config = {
                    'cache_ttl': 600,
                    'max_workers': 4,
                    'chunk_size': 100,
                    'timeout': 180
                }
        except Exception:
            # 如果配置获取失败，使用默认配置
            self.config = {
                'cache_ttl': 600,
                'max_workers': 4,
                'chunk_size': 100,
                'timeout': 180
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
    
    def _detect_market_type(self, stock_data: Dict[str, Any]) -> str:
        """检测股票所属市场类型"""
        try:
            # 优先从数据源的文件路径判断
            if hasattr(self.data_source, 'file_path') and self.data_source.file_path:
                file_name = os.path.basename(self.data_source.file_path).lower()
                if file_name.startswith('cn'):
                    return 'cn'
                elif file_name.startswith('hk'):
                    return 'hk'
                elif file_name.startswith('us'):
                    return 'us'
            
            # 从股票代码格式判断
            stock_code = str(stock_data.get('股票代码', ''))
            if stock_code:
                # 中国股票：6位数字
                if len(stock_code) == 6 and stock_code.isdigit():
                    return 'cn'
                # 香港股票：5位数字（通常前面补0到6位）
                elif len(stock_code) == 6 and stock_code.startswith('00') and stock_code[2:].isdigit():
                    return 'hk'
                # 美国股票：字母+数字组合
                elif not stock_code.isdigit():
                    return 'us'
            
            # 默认返回中国市场
            return 'cn'
            
        except Exception as e:
            logger.debug(f"市场类型检测失败: {e}")
            return 'cn'
    
    def calculate_all_metrics(self, force_refresh: bool = False, enable_emergency_timeout: bool = True) -> AnalysisResults:
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
                
                # 紧急超时检查
                if enable_emergency_timeout:
                    emergency_timeout = 180  # 3分钟紧急超时
                    logger.info(f"启用紧急超时机制: {emergency_timeout}秒")
                
                # 多线程或单线程计算
                calculation_start = time.time()
                if self.enable_multithreading:
                    results = self._calculate_multithreaded(raw_data, results)
                else:
                    results = self._calculate_single_threaded(raw_data, results)
                
                # 检查是否超过紧急超时
                if enable_emergency_timeout and (time.time() - calculation_start) > emergency_timeout:
                    logger.warning(f"计算超过紧急超时时间 {emergency_timeout}秒，可能存在问题")
                    # 不抛出异常，但记录警告
                
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
        """多线程并行计算个股RTSI（支持ARTS算法）"""
        stocks_results = {}
        date_columns = [col for col in raw_data.columns if str(col).startswith('202')]
        
        # 导入ARTS算法作为后备
        try:
            from algorithms.arts_calculator import ARTSCalculator
            arts_calculator = ARTSCalculator()
            arts_available = True
        except ImportError:
            logger.warning("⚠️ ARTS算法不可用")
            arts_available = False
            arts_calculator = None
        
        logger.info("📊 并行模式使用RTSI算法进行个股分析（主算法）")
        
        def calculate_single_stock(stock_data):
            try:
                stock_code = str(stock_data['股票代码'])
                stock_name = stock_data.get('股票名称', '')
                industry = stock_data.get('行业', '未分类')
                
                # 优先使用智能RTSI算法（主算法）
                rtsi_success = False
                
                # 计算RTSI - 使用智能RTSI计算器（如果可用）
                if hasattr(self, 'smart_rtsi_calculator') and self.smart_rtsi_calculator is not None:
                    try:
                        # 确定市场类型
                        market = self._detect_market_type(stock_data)
                        
                        # 使用智能RTSI计算器
                        rtsi_result = self.smart_rtsi_calculator.calculate_smart_rtsi(
                            stock_data, 
                            market=market, 
                            stock_code=stock_code
                        )
                        rtsi_success = True
                        logger.debug(f"智能RTSI计算成功 {stock_code}: {rtsi_result.get('algorithm', 'unknown')}")
                    except Exception as e:
                        # 静默处理智能RTSI计算失败，回退到增强RTSI
                        logger.debug(f"智能RTSI计算失败 {stock_code}: {e}")
                        rtsi_success = False
                
                # 如果智能RTSI失败，尝试增强RTSI
                if not rtsi_success and hasattr(self, 'enhanced_rtsi_calculator') and self.enhanced_rtsi_calculator is not None:
                    try:
                        # 使用增强RTSI计算器
                        rtsi_enhanced_result = self.enhanced_rtsi_calculator.batch_calculate_enhanced_rtsi(
                            pd.DataFrame([stock_data])
                        )
                        if stock_code in rtsi_enhanced_result:
                            rtsi_result = rtsi_enhanced_result[stock_code]
                            rtsi_success = True
                        else:
                            raise Exception("增强RTSI批量计算未返回结果")
                    except Exception as e:
                        # 静默处理增强RTSI计算失败，回退到标准RTSI
                        logger.debug(f"增强RTSI计算失败 {stock_code}: {e}")
                        rtsi_success = False
                
                # 如果智能RTSI和增强RTSI都失败，尝试标准RTSI
                if not rtsi_success:
                    try:
                        # 使用AI增强RTSI作为主算法（默认启用）
                        ratings = stock_data[date_columns]
                        rtsi_result = calculate_rating_trend_strength_index(
                            ratings, 
                            stock_code=stock_code,
                            stock_name=stock_name,
                            enable_ai=True  # 确保使用AI增强主算法
                        )
                        rtsi_success = True
                    except Exception as e:
                        logger.warning(f"标准RTSI计算失败 {stock_code}: {e}")
                        rtsi_success = False
                
                # 如果RTSI失败且ARTS可用，使用ARTS作为后备
                if not rtsi_success and arts_available:
                    try:
                        logger.info(f"🔄 {stock_code} 并行模式使用ARTS后备算法")
                        ratings = stock_data[date_columns]
                        arts_result = arts_calculator.calculate_arts(ratings, stock_code)
                        
                        # 将ARTS结果转换为兼容RTSI的格式
                        rtsi_result = {
                            'rtsi': arts_result.get('arts_score', 0),
                            'trend': arts_result.get('trend_direction', 'unknown'),
                            'confidence': arts_result.get('confidence_level', 'unknown'),
                            'pattern': arts_result.get('trend_pattern', 'unknown'),
                            'rating_level': arts_result.get('rating_level', 'unknown'),
                            'recommendation': arts_result.get('recommendation', ''),
                            'algorithm': 'ARTS_v1.0_backup',
                            'recent_score': arts_result.get('recent_rating'),
                            'data_points': arts_result.get('data_points', 0)
                        }
                        rtsi_success = True
                    except Exception as e:
                        logger.error(f"ARTS后备算法也失败 {stock_code}: {e}")
                
                # 如果所有算法都失败，使用默认结果
                if not rtsi_success:
                    rtsi_result = {
                        'rtsi': 0,
                        'trend': 'unknown',
                        'confidence': 0,
                        'algorithm': 'fallback',
                        'recent_score': None,
                        'data_points': 0
                    }
                
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
        
        # 多线程执行 - 增强错误处理和进度监控
        total_stocks = len(raw_data)
        max_workers = min(self.config['max_workers'], total_stocks, 6)  # 适当增加线程数上限
        logger.info(f"启动多线程计算: {total_stocks}只股票, {max_workers}个线程")
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                futures = []
                for _, stock_data in raw_data.iterrows():
                    future = executor.submit(calculate_single_stock, stock_data)
                    futures.append(future)
                
                logger.info(f"已提交 {len(futures)} 个计算任务")
                
                # 收集结果 - 使用更短的超时时间和适度的进度报告
                completed = 0
                failed = 0
                timeout_per_batch = min(45, self.config['timeout'] // 8)  # 每批次最多45秒，减少超时频率
                
                for i, future in enumerate(futures):
                    try:
                        # 使用适中的超时时间，平衡速度和稳定性
                        stock_code, result = future.result(timeout=timeout_per_batch)
                        if stock_code and result:
                            stocks_results[stock_code] = result
                            completed += 1
                        else:
                            failed += 1
                        
                        # 适度的进度报告，减少日志输出开销
                        if (i + 1) % 100 == 0 or (i + 1) == len(futures):
                            progress = ((i + 1) / len(futures)) * 100
                            logger.info(f"计算进度: {progress:.1f}% ({i + 1}/{len(futures)}) - 成功:{completed}, 失败:{failed}")
                            
                    except Exception as e:
                        failed += 1
                        if failed % 50 == 0:  # 只在失败数量达到一定程度时记录
                            logger.warning(f"任务失败数量: {failed}, 最新失败: {e}")
                        # 继续处理其他任务，不要因为单个任务失败而停止
                
                logger.info(f"多线程计算完成: 总计{len(futures)}只股票, 成功{completed}只, 失败{failed}只")
                
        except Exception as e:
            logger.error(f"多线程执行异常: {e}")
            # 如果多线程完全失败，回退到单线程模式
            logger.info("回退到单线程模式...")
            return self._calculate_stocks_rtsi_sequential(raw_data)
        
        return stocks_results
    
    def _calculate_stocks_rtsi_sequential(self, raw_data: pd.DataFrame) -> Dict[str, Dict]:
        """单线程顺序计算个股RTSI"""
        stocks_results = {}
        date_columns = [col for col in raw_data.columns if str(col).startswith('202')]
        
        # 导入ARTS算法作为后备
        try:
            from algorithms.arts_calculator import ARTSCalculator
            arts_calculator = ARTSCalculator()
            arts_available = True
        except ImportError:
            logger.warning("⚠️ ARTS算法不可用")
            arts_available = False
            arts_calculator = None
        
        # 如果有增强RTSI计算器，批量计算以提高效率
        if self.enhanced_rtsi_calculator is not None:
            logger.info("📊 开始批量计算增强RTSI...")
            enhanced_results = self.enhanced_rtsi_calculator.batch_calculate_enhanced_rtsi(raw_data)
            logger.info(f"📊 批量计算完成，成功计算 {len(enhanced_results)} 只股票")
            logger.info("📊 使用RTSI算法进行个股分析（主算法）")
        else:
            enhanced_results = {}
            logger.info("📊 使用RTSI算法进行个股分析（标准模式）")
        
        total_stocks = len(raw_data)
        logger.info(f"开始逐个股票计算: {total_stocks}只股票")
        
        for idx, stock_data in raw_data.iterrows():
            try:
                stock_code = str(stock_data['股票代码'])
                stock_name = stock_data.get('股票名称', '')
                industry = stock_data.get('行业', '未分类')
                
                # 进度报告
                if (idx + 1) % 100 == 0 or (idx + 1) == total_stocks:
                    progress = ((idx + 1) / total_stocks) * 100
                    logger.info(f"逐个股票计算进度: {progress:.1f}% ({idx + 1}/{total_stocks})")
                
                # 优先使用RTSI算法（主算法）
                rtsi_success = False
                
                # 计算RTSI - 优先使用增强结果
                if stock_code in enhanced_results:
                    rtsi_result = enhanced_results[stock_code]
                    rtsi_success = True
                else:
                    try:
                        # 使用AI增强RTSI作为主算法（默认启用）
                        ratings = stock_data[date_columns]
                        rtsi_result = calculate_rating_trend_strength_index(
                            ratings, 
                            stock_code=stock_code,
                            stock_name=stock_name,
                            enable_ai=True  # 确保使用AI增强主算法
                        )
                        rtsi_success = True
                    except Exception as e:
                        logger.debug(f"RTSI算法计算失败 {stock_code}: {e}")
                        rtsi_success = False
                
                # 如果RTSI失败且ARTS可用，使用ARTS作为后备
                if not rtsi_success and arts_available:
                    try:
                        logger.info(f"🔄 {stock_code} 使用ARTS后备算法")
                        ratings = stock_data[date_columns]
                        arts_result = arts_calculator.calculate_arts(ratings, stock_code)
                        
                        # 将ARTS结果转换为兼容RTSI的格式
                        rtsi_result = {
                            'rtsi': arts_result.get('arts_score', 0),
                            'trend': arts_result.get('trend_direction', 'unknown'),
                            'confidence': arts_result.get('confidence_level', 'unknown'),
                            'pattern': arts_result.get('trend_pattern', 'unknown'),
                            'rating_level': arts_result.get('rating_level', 'unknown'),
                            'recommendation': arts_result.get('recommendation', ''),
                            'algorithm': 'ARTS_v1.0_backup',
                            'recent_score': arts_result.get('recent_rating'),
                            'data_points': arts_result.get('data_points', 0)
                        }
                        rtsi_success = True
                    except Exception as e:
                        logger.error(f"ARTS后备算法也失败 {stock_code}: {e}")
                
                # 如果所有算法都失败，使用默认结果
                if not rtsi_success:
                    rtsi_result = {
                        'rtsi': 0,
                        'trend': 'unknown',
                        'confidence': 0,
                        'algorithm': 'fallback',
                        'recent_score': None,
                        'data_points': 0
                    }
                
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
        """计算行业IRSI（支持增强TMA）"""
        industries_results = {}
        
        # 按行业分组
        industries = raw_data['行业'].dropna().unique()
        
        # 选择分析方法
        if self.enable_enhanced_tma:
            logger.info("使用增强TMA分析行业强势")
            try:
                # 使用增强TMA分析器进行批量分析
                enhanced_results = self.enhanced_tma_analyzer.batch_analyze_industries_enhanced(raw_data)
                
                for industry in industries:
                    if industry in enhanced_results:
                        enhanced_result = enhanced_results[industry]
                        
                        # 统计行业内股票信息
                        industry_data = raw_data[raw_data['行业'] == industry]
                        industry_stocks = []
                        for _, stock in industry_data.iterrows():
                            stock_code = str(stock['股票代码'])
                            if stock_code in stocks_results:
                                industry_stocks.append({
                                    'code': stock_code,
                                    'name': stocks_results[stock_code]['name'],
                                    'rtsi': stocks_results[stock_code]['rtsi'].get('rtsi', 0)
                                })
                        
                        # 构建增强结果
                        industries_results[industry] = {
                            'irsi': enhanced_result,  # 包含所有增强信息
                            'stock_count': len(industry_stocks),
                            'stocks': industry_stocks,
                            'status': enhanced_result.get('enhanced_status', enhanced_result.get('status', 'unknown')),
                            'enhanced_tma': True,
                            'ai_enhanced': enhanced_result.get('ai_enhanced', False),
                            'credibility_info': enhanced_result.get('credibility_info', {}),
                            'risk_assessment': enhanced_result.get('risk_assessment', {})
                        }
                
                # 记录增强分析统计
                if hasattr(self.enhanced_tma_analyzer, 'get_analysis_statistics'):
                    enhancement_stats = self.enhanced_tma_analyzer.get_analysis_statistics()
                    logger.info(f"增强TMA分析统计: {enhancement_stats}")
                
            except Exception as e:
                logger.error(f"增强TMA分析失败，回退到基础模式: {e}")
                self.enable_enhanced_tma = False  # 临时关闭增强模式
        
        # 基础IRSI分析（作为回退或未启用增强TMA时使用）
        if not self.enable_enhanced_tma:
            logger.info("使用基础TMA分析行业强势")
            for industry in industries:
                try:
                    # 获取行业数据
                    industry_data = raw_data[raw_data['行业'] == industry]
                    
                    # 计算行业强势分析 (使用核心强势分析器)
                    irsi_result = calculate_industry_relative_strength(industry_data, raw_data, industry)
                    
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
                        'stocks': industry_stocks,  # 保存所有股票
                        'status': irsi_result.get('status', 'unknown'),
                        'enhanced_tma': False,
                        'ai_enhanced': False
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
def create_engine(data_source: StockDataSet, 
                  enable_multithreading: bool = True, 
                  enable_enhanced_tma: bool = True) -> RealtimeAnalysisEngine:
    """创建实时分析引擎实例"""
    return RealtimeAnalysisEngine(data_source, enable_multithreading, enable_enhanced_tma)


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