#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一量价数据缓存管理器

功能：
1. 统一管理量价数据的获取和缓存
2. 自动剔除无数据的交易日，保持数据连续性
3. 为AI分析和趋势图表提供统一接口
4. 支持多市场(CN/HK/US)数据获取

作者: AI Assistant
版本: 1.0.0
"""

import os
import sys
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from ljs import StockSearchTool

logger = logging.getLogger(__name__)

class VolumePriceCacheManager:
    """统一量价数据缓存管理器"""
    
    def __init__(self, verbose: bool = False):
        """
        初始化缓存管理器
        
        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        self.search_tool = StockSearchTool(verbose=verbose)
        
        # 缓存存储 - 使用嵌套字典: {market: {stock_code: {days: data}}}
        self._cache = {}
        
        # 线程锁，确保缓存操作的线程安全
        self._lock = threading.RLock()
        
        # 缓存统计
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        
        # 市场检测映射
        self._market_mapping = {
            'cn': 'cn',
            'hk': 'hk', 
            'us': 'us',
            'china': 'cn',
            'hongkong': 'hk',
            'america': 'us'
        }
    
    def _log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
    
    def _generate_cache_key(self, stock_code: str, market: str, days: int) -> str:
        """生成缓存键"""
        return f"{market.lower()}_{stock_code.upper()}_{days}"
    
    def _clean_trading_data(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理交易数据，剔除无效交易日
        
        Args:
            trade_data: 原始交易数据字典 {date: day_data}
            
        Returns:
            Dict: 清理后的连续交易数据
        """
        if not trade_data:
            return {}
        
        cleaned_data = {}
        removed_dates = []
        
        for date, day_data in sorted(trade_data.items()):
            # 检查是否有有效的价格数据
            close_price = day_data.get('收盘价')
            open_price = day_data.get('开盘价')
            volume = day_data.get('成交金额', 0)
            
            # 数据有效性检查
            valid_data = True
            
            # 价格数据检查
            if close_price is None or close_price <= 0:
                valid_data = False
            
            # 成交量检查（允许为0，但不能为None或负数）
            if volume is None or volume < 0:
                valid_data = False
            
            if valid_data:
                cleaned_data[date] = day_data
            else:
                removed_dates.append(date)
        
        if removed_dates and self.verbose:
            self._log(f"剔除无效交易日: {removed_dates}", "DEBUG")
        
        return cleaned_data
    
    def _format_volume_price_data(self, stock_data: Dict[str, Any], requested_days: int) -> Optional[Dict[str, Any]]:
        """
        格式化量价数据为统一格式
        
        Args:
            stock_data: 原始股票数据
            requested_days: 请求的天数
            
        Returns:
            Dict: 格式化后的量价数据，包含连续的交易数据
        """
        try:
            # 提取基础信息
            stock_code = stock_data.get('股票代码', '')
            stock_name = stock_data.get('股票名称', stock_code)
            data = stock_data.get('数据', {})
            trade_data = data.get('交易数据', {})
            
            if not trade_data:
                self._log(f"股票 {stock_code} 无交易数据", "WARNING")
                return None
            
            # 清理无效交易日
            cleaned_trade_data = self._clean_trading_data(trade_data)
            
            if not cleaned_trade_data:
                self._log(f"股票 {stock_code} 清理后无有效交易数据", "WARNING")
                return None
            
            # 按日期排序并取最近的交易日
            sorted_dates = sorted(cleaned_trade_data.keys(), reverse=True)
            recent_dates = sorted_dates[:requested_days]
            recent_dates.reverse()  # 改为正序排列（从早到晚）
            
            # 转换为统一格式
            formatted_data = []
            for date in recent_dates:
                day_data = cleaned_trade_data[date]
                
                formatted_day = {
                    'date': date,
                    'close_price': day_data.get('收盘价', 0),
                    'open_price': day_data.get('开盘价', day_data.get('收盘价', 0)),
                    'high_price': day_data.get('最高价', day_data.get('收盘价', 0)),
                    'low_price': day_data.get('最低价', day_data.get('收盘价', 0)),
                    'volume': day_data.get('成交金额', 0),
                    'volume_shares': day_data.get('成交量', 0),  # 股数
                    # 保留原始数据
                    'raw_data': day_data
                }
                
                formatted_data.append(formatted_day)
            
            result = {
                'stock_code': stock_code,
                'stock_name': stock_name,
                'market': stock_data.get('市场', 'unknown'),  # 从股票数据根级获取市场信息
                'total_days': len(formatted_data),
                'requested_days': requested_days,
                'data_continuous': True,  # 已经清理过，保证连续性
                'data': formatted_data,
                'cache_time': datetime.now().isoformat(),
                'raw_trade_data_count': len(trade_data),
                'cleaned_trade_data_count': len(cleaned_trade_data)
            }
            
            self._log(f"格式化完成: {stock_name}({stock_code}) - 请求{requested_days}天，实际获得{len(formatted_data)}天连续数据")
            return result
            
        except Exception as e:
            self._log(f"格式化量价数据失败: {e}", "ERROR")
            return None
    
    def get_volume_price_data(self, stock_code: str, market: str, days: int = 38) -> Optional[Dict[str, Any]]:
        """
        获取股票量价数据（带缓存）
        
        Args:
            stock_code: 股票代码
            market: 市场类型 ('cn', 'hk', 'us')
            days: 获取天数，默认38天
            
        Returns:
            Dict: 格式化的量价数据，如果获取失败返回None
        """
        with self._lock:
            self._cache_stats['total_requests'] += 1
            
            # 标准化市场参数
            market = market.lower()
            if market not in ['cn', 'hk', 'us']:
                market = self._market_mapping.get(market, 'cn')
            
            # 生成缓存键
            cache_key = self._generate_cache_key(stock_code, market, days)
            
            # 检查缓存
            if market in self._cache and cache_key in self._cache[market]:
                self._cache_stats['hits'] += 1
                cached_data = self._cache[market][cache_key]
                self._log(f"缓存命中: {stock_code}({market.upper()}) - {days}天")
                return cached_data
            
            # 缓存未命中，从数据源获取
            self._cache_stats['misses'] += 1
            self._log(f"缓存未命中，获取数据: {stock_code}({market.upper()}) - {days}天")
            
            try:
                # 清理股票代码格式
                clean_code = self._clean_stock_code(stock_code)
                formatted_data = None
                
                # 优先使用本地数据源（cn-lj.dat/hk-lj.dat/us-lj.dat）
                try:
                    self._log(f"优先尝试本地数据源: {stock_code}({market.upper()}) - {days}天")
                    results = self.search_tool.search_stock_by_code(clean_code, market, days)
                    
                    if results:
                        # 获取第一个市场的数据（通常只有一个）
                        stock_data = list(results.values())[0]
                        formatted_data = self._format_volume_price_data(stock_data, days)
                        if formatted_data:
                            self._log(f"✅ 本地数据源获取成功: {stock_code}({market.upper()}) - {formatted_data['total_days']}天")
                except Exception as e:
                    self._log(f"本地数据源获取失败: {stock_code}({market}) - {e}", "WARNING")
                
                # 如果本地数据源失败，使用AKShare作为备用方案
                if not formatted_data:
                    try:
                        self._log(f"使用AKShare备用数据源: {stock_code}({market.upper()}) - {days}天")
                        formatted_data = self._get_data_from_akshare(clean_code, market, days)
                        if formatted_data:
                            self._log(f"✅ AKShare备用获取成功: {stock_code}({market.upper()}) - {formatted_data['total_days']}天")
                    except Exception as e:
                        self._log(f"AKShare备用获取失败: {stock_code}({market}) - {e}", "WARNING")
                
                if not formatted_data:
                    self._log(f"所有数据源均失败: {stock_code}({market})", "ERROR")
                    return None
                
                # 存入缓存
                if market not in self._cache:
                    self._cache[market] = {}
                
                self._cache[market][cache_key] = formatted_data
                self._log(f"数据已缓存: {stock_code}({market.upper()}) - 实际{formatted_data['total_days']}天")
                    
                return formatted_data
                
            except Exception as e:
                self._log(f"获取量价数据失败: {stock_code}({market}) - {e}", "ERROR")
                return None
    
    def _get_data_from_akshare(self, stock_code: str, market: str, days: int) -> Optional[Dict[str, Any]]:
        """
        从AKShare获取量价数据
        
        Args:
            stock_code: 股票代码
            market: 市场类型 ('cn', 'hk', 'us')
            days: 获取天数
            
        Returns:
            格式化的量价数据字典
        """
        try:
            import akshare as ak
            import pandas as pd
            from datetime import datetime, timedelta
            import time
            
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 10)  # 多获取一些天数以确保有足够数据
            
            df = None
            
            if market == 'cn':
                # A股数据
                df = ak.stock_zh_a_hist(
                    symbol=stock_code, 
                    period="daily", 
                    start_date=start_date.strftime('%Y%m%d'), 
                    end_date=end_date.strftime('%Y%m%d'), 
                    adjust="qfq"
                )
                time.sleep(0.1)  # 减少访问间隔到100ms
                
            elif market == 'hk':
                # 港股数据
                df = ak.stock_hk_hist(
                    symbol=stock_code, 
                    period="daily", 
                    start_date=start_date.strftime('%Y%m%d'), 
                    end_date=end_date.strftime('%Y%m%d'), 
                    adjust="qfq"
                )
                time.sleep(0.1)  # 减少访问间隔到100ms
                
            elif market == 'us':
                # 美股数据
                df = ak.stock_us_daily(symbol=stock_code)
                time.sleep(0.1)  # 减少访问间隔到100ms
                
                # 过滤日期范围
                if not df.empty and 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[df['date'] >= start_date]
            
            if df is None or df.empty:
                return None
            
            # 统一列名格式
            if market == 'cn':
                # A股列名：日期、股票代码、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
                if len(df.columns) >= 6:
                    df.columns = ['date', 'stock_code', 'open', 'close', 'high', 'low', 'volume', 'turnover'] + list(df.columns[8:])
            else:
                # 港股和美股：date, open, high, low, close, volume
                if len(df.columns) >= 6:
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume'] + list(df.columns[6:])
            
            # 确保date列是datetime类型
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').tail(days)  # 只取最近的指定天数
            
            # 转换为标准格式
            volume_price_data = []
            for _, row in df.iterrows():
                volume_price_data.append({
                    'date': row['date'].strftime('%Y%m%d'),
                    'close_price': float(row.get('close', 0)),
                    'volume': float(row.get('volume', 0)),
                    'open_price': float(row.get('open', row.get('close', 0))),
                    'high_price': float(row.get('high', row.get('close', 0))),
                    'low_price': float(row.get('low', row.get('close', 0)))
                })
            
            # 获取股票名称（简化处理）
            stock_name = f"{stock_code}"
            
            return {
                'market': market.upper(),
                'stock_code': stock_code,
                'stock_name': stock_name,
                'total_days': len(volume_price_data),
                'data': volume_price_data,
                'data_source': 'akshare'
            }
            
        except Exception as e:
            self._log(f"AKShare获取数据异常: {stock_code}({market}) - {e}", "ERROR")
            return None
    
    def _clean_stock_code(self, stock_code: str) -> str:
        """清理股票代码格式"""
        if not stock_code:
            return stock_code
        
        # 清理Excel格式（如果存在）
        if stock_code.startswith('="') and stock_code.endswith('"'):
            return stock_code[2:-1]
        
        return str(stock_code).strip()
    
    def prefetch_data(self, stock_codes: List[str], market: str, days: int = 38) -> Dict[str, bool]:
        """
        预取多只股票的量价数据
        
        Args:
            stock_codes: 股票代码列表
            market: 市场类型
            days: 获取天数
            
        Returns:
            Dict: {stock_code: success_bool} 预取结果
        """
        results = {}
        self._log(f"开始预取 {len(stock_codes)} 只股票的量价数据({market.upper()}市场)")
        
        for stock_code in stock_codes:
            try:
                data = self.get_volume_price_data(stock_code, market, days)
                results[stock_code] = data is not None
            except Exception as e:
                self._log(f"预取失败 {stock_code}: {e}", "ERROR")
                results[stock_code] = False
        
        success_count = sum(results.values())
        self._log(f"预取完成: {success_count}/{len(stock_codes)} 成功")
        return results
    
    def clear_cache(self, market: str = None, stock_code: str = None):
        """
        清理缓存
        
        Args:
            market: 指定市场清理，None表示清理所有
            stock_code: 指定股票清理，None表示清理该市场所有股票
        """
        with self._lock:
            if market is None:
                # 清理全部缓存
                self._cache.clear()
                self._log("已清理全部缓存")
            elif market in self._cache:
                if stock_code is None:
                    # 清理指定市场的所有缓存
                    del self._cache[market]
                    self._log(f"已清理{market.upper()}市场缓存")
                else:
                    # 清理指定股票的缓存
                    market_cache = self._cache[market]
                    keys_to_remove = [k for k in market_cache.keys() if stock_code.upper() in k]
                    for key in keys_to_remove:
                        del market_cache[key]
                    self._log(f"已清理股票{stock_code}在{market.upper()}市场的缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_cached_items = sum(len(market_cache) for market_cache in self._cache.values())
            hit_rate = (self._cache_stats['hits'] / max(1, self._cache_stats['total_requests'])) * 100
            
            return {
                'total_requests': self._cache_stats['total_requests'],
                'cache_hits': self._cache_stats['hits'],
                'cache_misses': self._cache_stats['misses'],
                'hit_rate_percent': round(hit_rate, 2),
                'total_cached_items': total_cached_items,
                'cached_markets': list(self._cache.keys()),
                'cache_details': {
                    market: len(cache) for market, cache in self._cache.items()
                }
            }
    
    def get_cached_stock_list(self, market: str = None) -> List[str]:
        """
        获取已缓存的股票列表
        
        Args:
            market: 指定市场，None返回所有市场的股票
            
        Returns:
            List: 股票代码列表
        """
        with self._lock:
            if market:
                market = market.lower()
                if market in self._cache:
                    # 从缓存键中提取股票代码
                    codes = set()
                    for cache_key in self._cache[market].keys():
                        # cache_key格式: market_stockcode_days
                        parts = cache_key.split('_')
                        if len(parts) >= 3:
                            stock_code = '_'.join(parts[1:-1])  # 处理包含下划线的代码
                            codes.add(stock_code)
                    return sorted(list(codes))
                return []
            else:
                # 返回所有市场的股票
                all_codes = set()
                for market_cache in self._cache.values():
                    for cache_key in market_cache.keys():
                        parts = cache_key.split('_')
                        if len(parts) >= 3:
                            stock_code = '_'.join(parts[1:-1])
                            all_codes.add(stock_code)
                return sorted(list(all_codes))


# 全局缓存管理器实例
_global_cache_manager = None

def get_cache_manager(verbose: bool = False) -> VolumePriceCacheManager:
    """获取全局缓存管理器实例（单例模式）"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = VolumePriceCacheManager(verbose=verbose)
    return _global_cache_manager

def get_volume_price_data(stock_code: str, market: str, days: int = 38) -> Optional[Dict[str, Any]]:
    """便捷函数：获取量价数据"""
    cache_manager = get_cache_manager()
    return cache_manager.get_volume_price_data(stock_code, market, days)

def clear_volume_price_cache(market: str = None, stock_code: str = None):
    """便捷函数：清理缓存"""
    cache_manager = get_cache_manager()
    cache_manager.clear_cache(market, stock_code)

def get_cache_statistics() -> Dict[str, Any]:
    """便捷函数：获取缓存统计"""
    cache_manager = get_cache_manager()
    return cache_manager.get_cache_stats()


if __name__ == "__main__":
    # 测试代码
    print("=== 测试统一量价数据缓存管理器 ===\n")
    
    # 创建缓存管理器
    cache_manager = VolumePriceCacheManager(verbose=True)
    
    # 测试数据获取
    test_cases = [
        ('AAPL', 'us', 5),
        ('000001', 'cn', 5),
        ('00700', 'hk', 5)
    ]
    
    for stock_code, market, days in test_cases:
        print(f"\n测试: {stock_code} ({market.upper()}市场) - {days}天")
        
        # 第一次获取（缓存未命中）
        data = cache_manager.get_volume_price_data(stock_code, market, days)
        if data:
            print(f"✓ 成功获取: {data['stock_name']} - {data['total_days']}天连续数据")
            print(f"  最新交易日: {data['data'][-1]['date']}, 收盘价: {data['data'][-1]['close_price']}")
        else:
            print(f"✗ 获取失败")
        
        # 第二次获取（缓存命中）
        print("再次获取相同数据...")
        data2 = cache_manager.get_volume_price_data(stock_code, market, days)
        if data2:
            print(f"✓ 缓存命中: {data2['stock_name']}")
    
    # 显示缓存统计
    print(f"\n=== 缓存统计 ===")
    stats = cache_manager.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")

