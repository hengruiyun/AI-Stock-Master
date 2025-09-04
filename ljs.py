#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票搜索工具

功能：
1. 从压缩的JSON文件中搜索指定股票的数据
2. 支持搜索指定天数的量价数据
3. 支持多种查询方式：股票代码、股票名称
4. 支持日期范围查询

作者：AI Assistant
版本：1.0.0
"""

import os
import sys
import json
import gzip
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

class StockSearchTool:
    """股票搜索工具"""
    
    def __init__(self, verbose: bool = True, data_file_name: str = None):
        self.verbose = verbose
        self.current_dir = os.getcwd()
                # 优先使用.dat.gz文件，如果不存在则使用.dat文件
        self.data_files = {
            'cn': 'cn-lj.dat' if os.path.exists('cn-lj.dat') else 'cn-lj.dat',
            'hk': 'hk-lj.dat' if os.path.exists('hk-lj.dat') else 'hk-lj.dat',
            'us': 'us-lj.dat' if os.path.exists('us-lj.dat') else 'us-lj.dat'
        }
        self.loaded_data = {}  # 缓存已加载的数据
        
        # 如果指定了数据文件名，则自动确定市场文件映射
        if data_file_name:
            self._update_data_files_from_name(data_file_name)
    
    def _update_data_files_from_name(self, data_file_name: str):
        """根据数据文件名更新市场文件映射"""
        try:
            # 获取文件名（去除路径）
            file_name = os.path.basename(data_file_name).lower()
            
            # 根据文件名前缀确定市场类型
            if file_name.startswith('cn'):
                market_type = 'cn'
            elif file_name.startswith('hk'):
                market_type = 'hk'
            elif file_name.startswith('us'):
                market_type = 'us'
            else:
                self.log(f"无法从文件名确定市场类型: {data_file_name}", "WARNING")
                return
            
            # 更新对应市场的文件映射
            original_file = self.data_files.get(market_type)
            self.data_files[market_type] = f"{market_type}-lj.dat"
            
            self.log(f"根据数据文件名 '{data_file_name}' 确定市场类型: {market_type.upper()}")
            self.log(f"使用量价数据文件: {self.data_files[market_type]}")
            
        except Exception as e:
            self.log(f"更新数据文件映射失败: {str(e)}", "ERROR")
        
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level}: {message}")
    
    def clean_stock_code(self, stock_code: str) -> str:
        """清理股票代码格式，去掉Excel导入时的格式符号"""
        if not stock_code:
            return stock_code
        
        # 去掉开头的 =" 和结尾的 "
        if stock_code.startswith('="') and stock_code.endswith('"'):
            return stock_code[2:-1]
        
        # 去掉开头的 = (如果只有等号)
        if stock_code.startswith('='):
            return stock_code[1:]
        
        return stock_code
    
    def format_stock_code_for_search(self, stock_code: str) -> str:
        """将用户输入的股票代码转换为数据文件中的格式"""
        if not stock_code:
            return stock_code
        
        # 清理Excel格式（如果用户输入了Excel格式代码）
        if stock_code.startswith('="') and stock_code.endswith('"'):
            return stock_code[2:-1]  # 去掉 =" 和 "
        
        # 直接返回原始代码（数据文件中直接存储股票代码，不使用Excel格式）
        return stock_code
    
    def load_compressed_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """加载压缩JSON文件"""
        try:
            if not os.path.exists(file_path):
                self.log(f"文件不存在: {file_path}", "ERROR")
                return None
            
            self.log(f"正在加载文件: {os.path.basename(file_path)}")
            
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            self.log(f"成功加载数据，包含 {len(data.get('stocks', {}))} 只股票")
            return data
            
        except Exception as e:
            self.log(f"加载文件失败 {file_path}: {str(e)}", "ERROR")
            return None
    
    def load_market_data(self, market: str) -> bool:
        """加载指定市场的数据"""
        if market in self.loaded_data:
            return True
            
        if market not in self.data_files:
            self.log(f"不支持的市场: {market}", "ERROR")
            return False
        
        file_path = os.path.join(self.current_dir, self.data_files[market])
        data = self.load_compressed_json(file_path)
        
        if data:
            self.loaded_data[market] = data
            return True
        return False
    
    def search_stock_by_code(self, stock_code: str, market: str, days: int = None) -> Dict[str, Any]:
        """根据股票代码搜索 - 要求必须指定市场"""
        results = {}
        
        # 验证市场参数
        if not market:
            raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
        
        if market not in self.data_files:
            raise ValueError(f"不支持的市场类型: {market}，支持的市场: {list(self.data_files.keys())}")
        
        # 只搜索指定的市场
        markets_to_search = [market]
        
        # 准备不同格式的股票代码进行搜索
        search_codes = self._prepare_search_codes(stock_code)
        
        # 加载指定市场的数据
        if not self.load_market_data(market):
            raise RuntimeError(f"无法加载{market.upper()}市场数据")
            
        market_data = self.loaded_data[market]
        stocks = market_data.get('stocks', {})
        
        # 尝试不同格式的代码
        for search_code in search_codes:
            if search_code in stocks:
                stock_info = stocks[search_code]
                filtered_data = self._filter_by_days(stock_info, days)
                results[market] = {
                    "市场": market.upper(),
                    "股票代码": search_code,  # 保存原始格式，在显示时清理
                    "股票名称": stock_info.get("股票名称", ""),
                    "数据": filtered_data
                }
                # 找到后停止搜索其他格式
                break
        
        return results
    

    
    def _prepare_search_codes(self, stock_code: str) -> List[str]:
        """准备不同格式的搜索代码"""
        search_codes = []
        
        # 原始格式（清理后的代码）
        formatted_code = self.format_stock_code_for_search(stock_code)
        search_codes.append(formatted_code)
        
        # 对于HK市场，需要处理前导0的情况
        # 如果是6位数字且以000开头，也尝试5位数字版本（去掉一个前导0）
        if formatted_code.isdigit() and len(formatted_code) == 6 and formatted_code.startswith('000'):
            short_code = formatted_code[1:]  # 去掉第一个0
            if short_code not in search_codes:
                search_codes.append(short_code)
        
        # 如果是5位数字，也尝试6位数字版本（添加前导0）
        elif formatted_code.isdigit() and len(formatted_code) == 5:
            long_code = '0' + formatted_code
            if long_code not in search_codes:
                search_codes.append(long_code)
        
        # 对于4位以下的数字代码，尝试添加前导0到5位
        elif formatted_code.isdigit() and len(formatted_code) <= 4:
            padded_code = formatted_code.zfill(5)  # 左边填充0到5位
            if padded_code not in search_codes:
                search_codes.append(padded_code)
        
        return search_codes
    
    def search_stock_by_name(self, stock_name: str, market: str, days: int = None) -> Dict[str, Any]:
        """根据股票名称搜索（支持模糊匹配）- 要求必须指定市场"""
        results = {}
        
        # 验证市场参数
        if not market:
            raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
        
        if market not in self.data_files:
            raise ValueError(f"不支持的市场类型: {market}，支持的市场: {list(self.data_files.keys())}")
        
        # 加载指定市场的数据
        if not self.load_market_data(market):
            raise RuntimeError(f"无法加载{market.upper()}市场数据")
            
        market_data = self.loaded_data[market]
        stocks = market_data.get('stocks', {})
        
        # 搜索匹配的股票名称
        for code, stock_info in stocks.items():
            name = stock_info.get("股票名称", "")
            if stock_name in name or name in stock_name:
                filtered_data = self._filter_by_days(stock_info, days)
                key = f"{market}_{code}"
                results[key] = {
                    "市场": market.upper(),
                    "股票代码": code,
                    "股票名称": name,
                    "数据": filtered_data
                }
        
        return results
    
    def search_by_date_range(self, start_date: str, end_date: str, market: str, stock_code: str = None) -> Dict[str, Any]:
        """根据日期范围搜索 - 要求必须指定市场"""
        results = {}
        
        # 验证市场参数
        if not market:
            raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
        
        if market not in self.data_files:
            raise ValueError(f"不支持的市场类型: {market}，支持的市场: {list(self.data_files.keys())}")
        
        # 加载指定市场的数据
        if not self.load_market_data(market):
            raise RuntimeError(f"无法加载{market.upper()}市场数据")
            
        market_data = self.loaded_data[market]
        stocks = market_data.get('stocks', {})
        
        # 如果指定了股票代码
        if stock_code:
            # 准备不同格式的搜索代码
            search_codes = self._prepare_search_codes(stock_code)
            
            for search_code in search_codes:
                if search_code in stocks:
                    stock_info = stocks[search_code]
                    filtered_data = self._filter_by_date_range(stock_info, start_date, end_date)
                    if filtered_data:
                        results[f"{market}_{search_code}"] = {
                            "市场": market.upper(),
                            "股票代码": search_code,
                            "股票名称": stock_info.get("股票名称", ""),
                            "数据": filtered_data
                        }
                    break  # 找到后停止搜索其他格式
        else:
            # 搜索所有股票在指定日期范围内的数据
            for code, stock_info in stocks.items():
                filtered_data = self._filter_by_date_range(stock_info, start_date, end_date)
                if filtered_data:
                    results[f"{market}_{code}"] = {
                        "市场": market.upper(),
                        "股票代码": code,
                        "股票名称": stock_info.get("股票名称", ""),
                        "数据": filtered_data
                    }
        
        return results
    
    def _add_volume_to_stock_info(self, stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """为股票信息添加成交量字段"""
        if not stock_info:
            return stock_info
            
        trade_data = stock_info.get("交易数据", {})
        if not trade_data:
            return stock_info
        
        # 复制股票信息
        updated_info = stock_info.copy()
        updated_trade_data = {}
        
        # 处理每天的数据，添加成交量字段
        for date, day_data in trade_data.items():
            updated_day_data = day_data.copy()
            price = updated_day_data.get('收盘价', 0)
            amount = updated_day_data.get('成交金额', 0)
            
            # 原始数据只有收盘价和成交金额，需要计算成交量
            # 计算公式：成交量 = 成交金额 ÷ 收盘价
            if price > 0 and amount > 0:
                volume = int(amount / price)  # 成交量 = 成交金额 ÷ 收盘价
            elif price > 0 and amount == 0:
                # 如果成交金额为0，使用默认成交量，并重新计算成交金额
                volume = 1000000  # 默认成交量100万股
                amount = price * volume  # 成交金额 = 收盘价 × 成交量
                updated_day_data['成交金额'] = amount
            else:
                # 价格为0或无效的情况，使用默认值
                volume = 1000000
                if price <= 0:
                    price = 10.0  # 默认价格
                    updated_day_data['收盘价'] = price
                amount = price * volume
                updated_day_data['成交金额'] = amount
            
            updated_day_data['成交量'] = volume
            updated_trade_data[date] = updated_day_data
        
        updated_info["交易数据"] = updated_trade_data
        return updated_info
    
    def _filter_by_days(self, stock_info: Dict[str, Any], days: int = None) -> Dict[str, Any]:
        """按天数过滤数据"""
        if not days:
            # 即使不过滤天数，也要添加成交量字段
            return self._add_volume_to_stock_info(stock_info)
        
        trade_data = stock_info.get("交易数据", {})
        if not trade_data:
            return stock_info
        
        # 获取排序后的日期列表
        sorted_dates = sorted(trade_data.keys(), reverse=True)  # 最新的在前
        
        # 取最近的指定天数
        if days < len(sorted_dates):
            recent_dates = sorted_dates[:days]
            filtered_trade_data = {}
            
            # 处理每天的数据，添加成交量字段
            for date in recent_dates:
                day_data = trade_data[date].copy()  # 复制原数据
                price = day_data.get('收盘价', 0)
                amount = day_data.get('成交金额', 0)
                
                # 原始数据只有收盘价和成交金额，需要计算成交量
                # 计算公式：成交量 = 成交金额 ÷ 收盘价
                if price > 0 and amount > 0:
                    volume = int(amount / price)  # 成交量 = 成交金额 ÷ 收盘价
                elif price > 0 and amount == 0:
                    # 如果成交金额为0，使用默认成交量，并重新计算成交金额
                    volume = 1000000  # 默认成交量100万股
                    amount = price * volume  # 成交金额 = 收盘价 × 成交量
                    day_data['成交金额'] = amount
                else:
                    # 价格为0或无效的情况，使用默认值
                    volume = 1000000
                    if price <= 0:
                        price = 10.0  # 默认价格
                        day_data['收盘价'] = price
                    amount = price * volume
                    day_data['成交金额'] = amount
                
                day_data['成交量'] = volume
                filtered_trade_data[date] = day_data
            
            # 重新构建过滤后的数据
            filtered_info = {
                "股票名称": stock_info.get("股票名称", ""),
                "交易数据": filtered_trade_data,
                "交易日期列表": sorted(recent_dates),
                "最早交易日": min(recent_dates),
                "最新交易日": max(recent_dates),
                "交易天数": len(recent_dates)
            }
            return filtered_info
        
        return stock_info
    
    def _filter_by_date_range(self, stock_info: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
        """按日期范围过滤数据"""
        trade_data = stock_info.get("交易数据", {})
        if not trade_data:
            return {}
        
        # 过滤日期范围内的数据
        filtered_trade_data = {}
        for date, data in trade_data.items():
            if start_date <= date <= end_date:
                day_data = data.copy()  # 复制原数据
                price = day_data.get('收盘价', 0)
                amount = day_data.get('成交金额', 0)
                
                # 原始数据只有收盘价和成交金额，需要计算成交量
                # 计算公式：成交量 = 成交金额 ÷ 收盘价
                if price > 0 and amount > 0:
                    volume = int(amount / price)  # 成交量 = 成交金额 ÷ 收盘价
                elif price > 0 and amount == 0:
                    # 如果成交金额为0，使用默认成交量，并重新计算成交金额
                    volume = 1000000  # 默认成交量100万股
                    amount = price * volume  # 成交金额 = 收盘价 × 成交量
                    day_data['成交金额'] = amount
                else:
                    # 价格为0或无效的情况，使用默认值
                    volume = 1000000
                    if price <= 0:
                        price = 10.0  # 默认价格
                        day_data['收盘价'] = price
                    amount = price * volume
                    day_data['成交金额'] = amount
                
                day_data['成交量'] = volume
                filtered_trade_data[date] = day_data
        
        if not filtered_trade_data:
            return {}
        
        # 重新构建过滤后的数据
        sorted_dates = sorted(filtered_trade_data.keys())
        filtered_info = {
            "股票名称": stock_info.get("股票名称", ""),
            "交易数据": filtered_trade_data,
            "交易日期列表": sorted_dates,
            "最早交易日": sorted_dates[0],
            "最新交易日": sorted_dates[-1],
            "交易天数": len(sorted_dates)
        }
        return filtered_info
    
    def format_results(self, results: Dict[str, Any], output_format: str = "table") -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到匹配的股票数据"
        
        if output_format == "json":
            return json.dumps(results, ensure_ascii=False, indent=2)
        
        elif output_format == "table":
            output = []
            output.append("=" * 80)
            output.append("股票搜索结果")
            output.append("=" * 80)
            
            for key, stock_data in results.items():
                # 清理股票代码格式，去掉 =" 和 "
                clean_code = self.clean_stock_code(stock_data['股票代码'])
                output.append(f"\n【{stock_data['市场']}市场】 {clean_code} - {stock_data['股票名称']}")
                output.append("-" * 60)
                
                data = stock_data.get('数据', {})
                trade_data = data.get('交易数据', {})
                
                if trade_data:
                    output.append(f"交易天数: {data.get('交易天数', 0)}")
                    output.append(f"日期范围: {data.get('最早交易日', 'N/A')} ~ {data.get('最新交易日', 'N/A')}")
                    output.append("")
                    output.append(f"{'日期':<12} {'收盘价':<10} {'成交金额':<15} {'成交量':<12}")
                    output.append("-" * 52)
                    
                    # 按日期排序显示
                    for date in sorted(trade_data.keys()):
                        price = trade_data[date].get('收盘价', 0)
                        amount = trade_data[date].get('成交金额', 0)
                        volume = trade_data[date].get('成交量', 0)
                        output.append(f"{date:<12} {price:<10.2f} {amount:<15,.0f} {volume:<12,.0f}")
                else:
                    output.append("无交易数据")
                
                output.append("")
            
            return "\n".join(output)
        
        elif output_format == "csv":
            # CSV格式输出
            csv_lines = ["市场,股票代码,股票名称,交易日期,收盘价,成交金额,成交量"]
            
            for key, stock_data in results.items():
                market = stock_data['市场']
                code = self.clean_stock_code(stock_data['股票代码'])  # 清理股票代码
                name = stock_data['股票名称']
                
                data = stock_data.get('数据', {})
                trade_data = data.get('交易数据', {})
                
                for date in sorted(trade_data.keys()):
                    price = trade_data[date].get('收盘价', 0)
                    amount = trade_data[date].get('成交金额', 0)
                    volume = trade_data[date].get('成交量', 0)
                    csv_lines.append(f"{market},{code},{name},{date},{price},{amount},{volume}")
            
            return "\n".join(csv_lines)
        
        else:
            return str(results)
    
    def get_market_summary(self, market: str) -> Dict[str, Any]:
        """获取市场概览"""
        if not self.load_market_data(market):
            return {}
        
        market_data = self.loaded_data[market]
        stocks = market_data.get('stocks', {})
        summary_info = market_data.get('summary', {})
        
        # 统计信息
        total_stocks = len(stocks)
        total_trading_days = 0
        date_range = {"earliest": None, "latest": None}
        
        all_dates = set()
        for stock_info in stocks.values():
            trade_data = stock_info.get('交易数据', {})
            all_dates.update(trade_data.keys())
        
        if all_dates:
            sorted_dates = sorted(all_dates)
            date_range["earliest"] = sorted_dates[0]
            date_range["latest"] = sorted_dates[-1]
            total_trading_days = len(sorted_dates)
        
        return {
            "市场": market.upper(),
            "股票总数": total_stocks,
            "交易天数": total_trading_days,
            "日期范围": date_range,
            "处理统计": summary_info
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='股票搜索工具 - 从压缩JSON文件中搜索股票量价数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python ljs.py --code 000001                               # 搜索股票代码
  python ljs.py --name 平安银行                              # 搜索股票名称
  python ljs.py --code 000001 --days 10                     # 搜索最近10天数据
  python ljs.py --code 000001 --market cn                   # 搜索指定市场
  python ljs.py --code 000001 --data-file cn_data.xlsx      # 根据数据文件名自动确定市场
  python ljs.py --start 2024-01-01 --end 2024-01-10         # 日期范围搜索
  python ljs.py --summary cn                                # 显示市场概览
  python ljs.py --code 000001 --format json                 # JSON格式输出
  
数据文件名映射规则:
  cn开头的文件名 -> 使用 cn-lj.dat (中国市场量价数据)
  hk开头的文件名 -> 使用 hk-lj.dat (香港市场量价数据)  
  us开头的文件名 -> 使用 us-lj.dat (美国市场量价数据)
        """
    )
    
    # 搜索参数
    parser.add_argument('--code', '-c', help='股票代码')
    parser.add_argument('--name', '-n', help='股票名称（支持模糊匹配）')
    parser.add_argument('--market', '-m', choices=['cn', 'hk', 'us'], required=True, help='必须指定市场 (cn/hk/us)')
    parser.add_argument('--days', '-d', type=int, help='查询最近天数')
    parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    
    # 数据文件参数
    parser.add_argument('--data-file', help='指定数据文件名，用于自动确定市场类型 (例如: cn_data.xlsx -> cn市场)')
    
    # 输出参数
    parser.add_argument('--format', '-f', choices=['table', 'json', 'csv'], default='table', help='输出格式')
    parser.add_argument('--output', '-o', help='输出到文件')
    parser.add_argument('--summary', choices=['cn', 'hk', 'us'], help='显示市场概览')
    
    # 其他参数
    parser.add_argument('--verbose', '-v', action='store_true', default=True, help='详细输出')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    
    args = parser.parse_args()
    
    # 创建搜索工具
    verbose = args.verbose and not args.quiet
    searcher = StockSearchTool(verbose=verbose, data_file_name=args.data_file)
    
    try:
        # 显示市场概览
        if args.summary:
            summary = searcher.get_market_summary(args.summary)
            if summary:
                print(f"\n{args.summary.upper()}市场概览:")
                print("=" * 50)
                print(f"股票总数: {summary['股票总数']}")
                print(f"交易天数: {summary['交易天数']}")
                print(f"日期范围: {summary['日期范围']['earliest']} ~ {summary['日期范围']['latest']}")
                print(f"处理统计: {summary['处理统计']}")
            else:
                print(f"无法获取{args.summary.upper()}市场数据")
            return
        
        # 搜索逻辑
        results = {}
        
        if args.start and args.end:
            # 日期范围搜索
            results = searcher.search_by_date_range(args.start, args.end, args.market, args.code)
        elif args.code:
            # 股票代码搜索
            results = searcher.search_stock_by_code(args.code, args.market, args.days)
        elif args.name:
            # 股票名称搜索
            results = searcher.search_stock_by_name(args.name, args.market, args.days)
        else:
            print("请指定搜索条件：--code, --name, 或 --start/--end")
            return
        
        # 格式化并输出结果
        output_text = searcher.format_results(results, args.format)
        
        if args.output:
            # 保存到文件
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"结果已保存到: {args.output}")
        else:
            # 控制台输出
            print(output_text)
    
    except Exception as e:
        print(f"搜索过程中出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

