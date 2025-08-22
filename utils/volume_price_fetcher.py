#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量价数据获取模块

功能：
1. 集成ljs.py功能，获取30天量价数据
2. 根据股票代码自动识别市场
3. 处理数据格式，提供统一接口
4. 支持数据缓存和错误处理

作者：AI Assistant
版本：1.0.0
"""

import os
import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入ljs模块
try:
    from ljs import StockSearchTool
except ImportError:
    print("警告: 无法导入ljs模块，量价数据功能将不可用")
    StockSearchTool = None


class VolumePriceFetcher:
    """量价数据获取器"""
    
    def __init__(self, verbose: bool = False):
        """
        初始化量价数据获取器
        
        Args:
            verbose: 是否显示详细日志
        """
        self.verbose = verbose
        self.search_tool = None
        self.data_file_mapping = {
            'cn': 'cn-lj.json.gz',
            'hk': 'hk-lj.json.gz', 
            'us': 'us-lj.json.gz'
        }
        
        # 初始化搜索工具
        if StockSearchTool:
            self.search_tool = StockSearchTool(verbose=verbose)
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level}: {message}")
    
    def determine_market_from_data_file(self, data_file_name: str) -> Optional[str]:
        """
        根据数据文件名确定市场类型
        
        Args:
            data_file_name: 数据文件名
            
        Returns:
            市场类型 ('cn', 'hk', 'us') 或 None
        """
        if not data_file_name:
            return None
            
        data_file_name = data_file_name.lower()
        
        if data_file_name.startswith('cn'):
            return 'cn'
        elif data_file_name.startswith('hk'):
            return 'hk'
        elif data_file_name.startswith('us'):
            return 'us'
        else:
            return None
    
    def determine_market_from_code(self, stock_code: str) -> Optional[str]:
        """
        根据股票代码推断市场类型
        
        Args:
            stock_code: 股票代码
            
        Returns:
            市场类型 ('cn', 'hk', 'us') 或 None
        """
        if not stock_code:
            return None
            
        stock_code = stock_code.upper().strip()
        
        # 中国A股代码特征
        if (stock_code.startswith(('000', '001', '002', '003', '300', '301')) or  # 深交所
            stock_code.startswith(('600', '601', '602', '603', '605', '688', '689')) or  # 上交所
            stock_code.startswith(('430', '831', '832', '833', '834', '835', '836', '837', '838', '839'))):  # 新三板
            return 'cn'
        
        # 香港股票代码特征
        elif len(stock_code) <= 5 and stock_code.isdigit():
            return 'hk'
        
        # 美股代码特征（字母组合）
        elif stock_code.isalpha() and len(stock_code) >= 1:
            return 'us'
        
        return None
    
    def get_volume_price_data(self, stock_code: str, days: int = 30, 
                            market: Optional[str] = None, 
                            data_file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取股票30天量价数据
        
        Args:
            stock_code: 股票代码
            days: 获取天数，默认30天
            market: 指定市场 ('cn', 'hk', 'us')，如果不指定则自动推断
            data_file_name: 数据文件名，用于推断市场类型
            
        Returns:
            包含量价数据的字典，结构如下：
            {
                'success': bool,
                'data_source': str,  # 'real_data' 或 'fallback'
                'market': str,
                'stock_code': str,
                'stock_name': str,
                'volume_price_data': Dict,  # 30天的量价数据
                'summary': Dict,  # 数据摘要
                'error': str  # 错误信息（如果有）
            }
        """
        result = {
            'success': False,
            'data_source': 'fallback',
            'market': '',
            'stock_code': stock_code,
            'stock_name': '',
            'volume_price_data': {},
            'summary': {},
            'error': ''
        }
        
        # 检查搜索工具类是否可用
        if not StockSearchTool:
            result['error'] = 'ljs模块不可用'
            self.log(f"ljs模块不可用，无法获取股票{stock_code}的量价数据", "ERROR")
            return result
        
        try:
            # 1. 确定市场类型
            if not market:
                # 优先使用数据文件名推断
                if data_file_name:
                    market = self.determine_market_from_data_file(data_file_name)
                
                # 如果还是无法确定，使用股票代码推断
                if not market:
                    market = self.determine_market_from_code(stock_code)
            
            if not market:
                result['error'] = f'无法确定股票{stock_code}的市场类型'
                self.log(f"无法确定股票{stock_code}的市场类型", "ERROR")
                return result
            
            result['market'] = market
            self.log(f"尝试从{market.upper()}市场获取股票{stock_code}的{days}天量价数据")
            
            # 2. 创建专门的搜索工具实例（传入数据文件名以自动选择正确的量价数据文件）
            search_tool = StockSearchTool(verbose=self.verbose, data_file_name=data_file_name)
            
            # 3. 使用ljs搜索工具获取数据
            search_results = search_tool.search_stock_by_code(stock_code, market, days)
            
            # 如果直接搜索失败，尝试Excel格式的股票代码（="代码"）
            if not search_results or market not in search_results:
                excel_format_code = f'="{stock_code}"'
                self.log(f"尝试Excel格式代码: {excel_format_code}")
                search_results = search_tool.search_stock_by_code(excel_format_code, market, days)
            
            if not search_results or market not in search_results:
                result['error'] = f'在{market.upper()}市场未找到股票{stock_code}的数据'
                self.log(f"在{market.upper()}市场未找到股票{stock_code}的数据", "ERROR")
                return result
            
            # 3. 提取数据
            stock_data = search_results[market]
            data_info = stock_data.get('数据', {})
            trade_data = data_info.get('交易数据', {})
            
            if not trade_data:
                result['error'] = f'股票{stock_code}没有可用的交易数据'
                self.log(f"股票{stock_code}没有可用的交易数据", "ERROR")
                return result
            
            # 4. 填充结果数据
            result['success'] = True
            result['data_source'] = 'real_data'
            result['stock_name'] = stock_data.get('股票名称', stock_code)
            result['volume_price_data'] = trade_data
            
            # 5. 生成数据摘要
            result['summary'] = self._generate_data_summary(trade_data, data_info)
            
            self.log(f"成功获取股票{stock_code}的{len(trade_data)}天量价数据")
            
        except Exception as e:
            result['error'] = f'获取量价数据时发生错误: {str(e)}'
            self.log(f"获取股票{stock_code}量价数据失败: {str(e)}", "ERROR")
        
        return result
    
    def _generate_data_summary(self, trade_data: Dict[str, Any], data_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成数据摘要
        
        Args:
            trade_data: 交易数据
            data_info: 数据信息
            
        Returns:
            数据摘要字典
        """
        try:
            if not trade_data:
                return {}
            
            # 基本统计信息
            summary = {
                'total_days': len(trade_data),
                'date_range': {
                    'start': data_info.get('最早交易日', ''),
                    'end': data_info.get('最新交易日', '')
                },
                'data_completeness': 0.0,
                'price_stats': {},
                'volume_stats': {}
            }
            
            # 提取价格和成交量数据用于统计
            prices = []
            volumes = []
            
            for date, daily_data in trade_data.items():
                if isinstance(daily_data, dict):
                    # 尝试提取价格数据（可能的字段名）
                    for price_field in ['收盘价', 'close', '收盘', '价格']:
                        if price_field in daily_data and daily_data[price_field] is not None:
                            try:
                                price = float(daily_data[price_field])
                                prices.append(price)
                                break
                            except (ValueError, TypeError):
                                continue
                    
                    # 尝试提取成交量数据（可能的字段名）
                    for volume_field in ['成交量', 'volume', '成交额', 'amount']:
                        if volume_field in daily_data and daily_data[volume_field] is not None:
                            try:
                                volume = float(daily_data[volume_field])
                                volumes.append(volume)
                                break
                            except (ValueError, TypeError):
                                continue
            
            # 计算数据完整性
            expected_fields = 0
            available_fields = 0
            
            for daily_data in trade_data.values():
                if isinstance(daily_data, dict):
                    expected_fields += 2  # 价格和成交量
                    if any(field in daily_data for field in ['收盘价', 'close', '收盘', '价格']):
                        available_fields += 1
                    if any(field in daily_data for field in ['成交量', 'volume', '成交额', 'amount']):
                        available_fields += 1
            
            if expected_fields > 0:
                summary['data_completeness'] = available_fields / expected_fields
            
            # 价格统计
            if prices:
                import statistics
                summary['price_stats'] = {
                    'count': len(prices),
                    'min': min(prices),
                    'max': max(prices),
                    'avg': statistics.mean(prices),
                    'latest': prices[-1] if prices else 0
                }
                
                if len(prices) > 1:
                    summary['price_stats']['change_rate'] = (prices[-1] - prices[0]) / prices[0] * 100
            
            # 成交量统计
            if volumes:
                import statistics
                summary['volume_stats'] = {
                    'count': len(volumes),
                    'min': min(volumes),
                    'max': max(volumes),
                    'avg': statistics.mean(volumes),
                    'total': sum(volumes)
                }
            
            return summary
            
        except Exception as e:
            self.log(f"生成数据摘要失败: {str(e)}", "ERROR")
            return {}
    
    def format_volume_price_data_for_ai(self, volume_price_result: Dict[str, Any]) -> str:
        """
        将量价数据格式化为适合AI分析的文本
        
        Args:
            volume_price_result: get_volume_price_data返回的结果
            
        Returns:
            格式化后的文本
        """
        if not volume_price_result.get('success', False):
            return f"量价数据获取失败: {volume_price_result.get('error', '未知错误')}"
        
        try:
            data = volume_price_result['volume_price_data']
            summary = volume_price_result.get('summary', {})
            
            lines = [
                f"=== 30天真实量价数据 ({volume_price_result['market'].upper()}市场) ===",
                f"股票: {volume_price_result['stock_code']} {volume_price_result['stock_name']}",
                f"数据期间: {summary.get('date_range', {}).get('start', '')} 至 {summary.get('date_range', {}).get('end', '')}",
                f"交易天数: {summary.get('total_days', 0)}天",
                f"数据完整度: {summary.get('data_completeness', 0):.1%}",
                ""
            ]
            
            # 价格统计
            price_stats = summary.get('price_stats', {})
            if price_stats:
                lines.extend([
                    "价格分析:",
                    f"  最新价格: {price_stats.get('latest', 0):.2f}",
                    f"  价格区间: {price_stats.get('min', 0):.2f} - {price_stats.get('max', 0):.2f}",
                    f"  平均价格: {price_stats.get('avg', 0):.2f}",
                    f"  期间涨跌: {price_stats.get('change_rate', 0):+.2f}%",
                    ""
                ])
            
            # 成交量统计
            volume_stats = summary.get('volume_stats', {})
            if volume_stats:
                lines.extend([
                    "成交量分析:",
                    f"  平均成交量: {volume_stats.get('avg', 0):,.0f}",
                    f"  成交量区间: {volume_stats.get('min', 0):,.0f} - {volume_stats.get('max', 0):,.0f}",
                    f"  总成交量: {volume_stats.get('total', 0):,.0f}",
                    ""
                ])
            
            # 最近几天的详细数据
            if data:
                lines.append("最近5天详细数据:")
                sorted_dates = sorted(data.keys(), reverse=True)[:5]
                
                for date in sorted_dates:
                    daily_data = data[date]
                    if isinstance(daily_data, dict):
                        price = "N/A"
                        volume = "N/A"
                        
                        # 提取价格
                        for price_field in ['收盘价', 'close', '收盘', '价格']:
                            if price_field in daily_data and daily_data[price_field] is not None:
                                try:
                                    price = f"{float(daily_data[price_field]):.2f}"
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        # 提取成交量
                        for volume_field in ['成交量', 'volume', '成交额', 'amount']:
                            if volume_field in daily_data and daily_data[volume_field] is not None:
                                try:
                                    volume = f"{float(daily_data[volume_field]):,.0f}"
                                    break
                                except (ValueError, TypeError):
                                    continue
                        
                        lines.append(f"  {date}: 价格={price}, 成交量={volume}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"格式化量价数据失败: {str(e)}"


def test_volume_price_fetcher():
    """测试量价数据获取器"""
    print("测试量价数据获取器...")
    
    fetcher = VolumePriceFetcher(verbose=True)
    
    # 测试用例
    test_cases = [
        {"code": "000001", "market": "cn", "description": "中国平安 - 中国市场"},
        {"code": "00700", "market": "hk", "description": "腾讯控股 - 香港市场"},
        {"code": "AAPL", "market": "us", "description": "苹果公司 - 美国市场"},
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {test_case['description']}")
        print('='*60)
        
        result = fetcher.get_volume_price_data(
            stock_code=test_case['code'], 
            days=30, 
            market=test_case['market']
        )
        
        if result['success']:
            print("✓ 数据获取成功")
            print(f"数据源: {result['data_source']}")
            print(f"股票名称: {result['stock_name']}")
            print(f"数据天数: {result['summary'].get('total_days', 0)}")
            
            # 输出格式化的AI分析文本
            ai_text = fetcher.format_volume_price_data_for_ai(result)
            print("\nAI分析格式:")
            print(ai_text[:500] + "..." if len(ai_text) > 500 else ai_text)
        else:
            print(f"✗ 数据获取失败: {result['error']}")


if __name__ == "__main__":
    test_volume_price_fetcher()
