#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票量价数据读取接口 V2
支持个股和指数的区分查询，包含行业信息
提供便捷的数据查询和访问功能
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import argparse
import os
import gzip
import tempfile
import shutil
import json

class StockDataReaderV2:
    """股票数据读取器 V2 - 支持SQLite、压缩SQLite和JSON格式"""
    
    def __init__(self, db_path: str = "data-lj.dat"):
        self.original_path = db_path
        self.db_path = db_path
        self.temp_dir = None
        self.data_format = self._detect_format()
        self._prepare_database()
    
    def __del__(self):
        """清理临时文件"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _detect_format(self) -> str:
        """检测数据文件格式"""
        if not os.path.exists(self.original_path):
            raise FileNotFoundError(f"数据文件不存在: {self.original_path}")
        
        if self.original_path.endswith('.gz'):
            # 检查是否是压缩的SQLite或JSON
            try:
                with gzip.open(self.original_path, 'rb') as f:
                    header = f.read(16)
                    if header.startswith(b'SQLite format 3'):
                        return 'sqlite_gz'
                    else:
                        return 'json_gz'
            except:
                raise ValueError(f"无法读取压缩文件: {self.original_path}")
        
        elif self.original_path.endswith('.json'):
            return 'json'
        
        else:
            # 检查是否是SQLite文件
            try:
                with open(self.original_path, 'rb') as f:
                    header = f.read(16)
                    if header.startswith(b'SQLite format 3'):
                        return 'sqlite'
                    else:
                        raise ValueError(f"未知的数据文件格式: {self.original_path}")
            except:
                raise ValueError(f"无法读取数据文件: {self.original_path}")
    
    def _prepare_database(self):
        """准备数据库文件（解压缩或转换格式）"""
        if self.data_format == 'sqlite':
            # 直接使用SQLite文件
            self._check_database()
            
        elif self.data_format == 'sqlite_gz':
            # 解压缩SQLite文件到临时目录
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = os.path.join(self.temp_dir, 'temp_db.dat')
            
            with gzip.open(self.original_path, 'rb') as f_in:
                with open(self.db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            self._check_database()
            
        elif self.data_format in ['json', 'json_gz']:
            # 将JSON转换为临时SQLite数据库
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = os.path.join(self.temp_dir, 'temp_db.dat')
            self._convert_json_to_sqlite()
    
    def _convert_json_to_sqlite(self):
        """将JSON数据转换为SQLite数据库"""
        try:
            # 读取JSON数据
            if self.data_format == 'json_gz':
                with gzip.open(self.original_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(self.original_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # 创建SQLite数据库
            conn = sqlite3.connect(self.db_path)
            
            # 创建表结构
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    market TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    industry TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE volume_price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            ''')
            
            # 导入数据
            if 'stock_info' in data:
                stock_info_df = pd.DataFrame(data['stock_info'])
                stock_info_df.to_sql('stock_info', conn, if_exists='append', index=False)
            
            if 'volume_price_data' in data:
                volume_price_df = pd.DataFrame(data['volume_price_data'])
                volume_price_df.to_sql('volume_price_data', conn, if_exists='append', index=False)
            
            # 创建索引
            cursor.execute('CREATE INDEX idx_symbol_date ON volume_price_data(symbol, date)')
            cursor.execute('CREATE INDEX idx_market ON volume_price_data(market)')
            cursor.execute('CREATE INDEX idx_data_type ON volume_price_data(data_type)')
            cursor.execute('CREATE INDEX idx_date ON volume_price_data(date)')
            cursor.execute('CREATE INDEX idx_industry ON stock_info(industry)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            raise ValueError(f"JSON数据转换失败: {e}")
    
    def _check_database(self):
        """检查数据库是否存在且有效"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            if not tables:
                raise FileNotFoundError(f"数据库文件 {self.db_path} 不存在或为空")
                
        except Exception as e:
            raise FileNotFoundError(f"无法访问数据库文件 {self.db_path}: {e}")
    
    def get_file_info(self) -> Dict:
        """获取文件信息"""
        info = {
            'original_path': self.original_path,
            'format': self.data_format,
            'size': os.path.getsize(self.original_path),
            'readable': True
        }
        
        if self.data_format.endswith('_gz'):
            info['compressed'] = True
            if self.data_format == 'sqlite_gz':
                info['uncompressed_size'] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        else:
            info['compressed'] = False
        
        return info
    
    def get_stock_list(self, market: Optional[str] = None, data_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票/指数列表
        
        Args:
            market: 市场代码 ('CN', 'HK', 'US')，None表示所有市场
            data_type: 数据类型 ('stock', 'index')，None表示所有类型
            
        Returns:
            包含股票信息的DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        conditions = []
        params = []
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        if data_type:
            conditions.append("data_type = ?")
            params.append(data_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM stock_info WHERE {where_clause} ORDER BY market, data_type, symbol"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def get_stocks_only(self, market: Optional[str] = None) -> pd.DataFrame:
        """获取个股列表（不包含指数）"""
        return self.get_stock_list(market=market, data_type='stock')
    
    def get_indices_only(self, market: Optional[str] = None) -> pd.DataFrame:
        """获取指数列表（不包含个股）"""
        return self.get_stock_list(market=market, data_type='index')
    
    def get_stock_data(self, symbol: str, market: Optional[str] = None, 
                      start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取指定股票/指数的量价数据
        
        Args:
            symbol: 股票代码
            market: 市场代码，如果不指定会自动查找
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            包含量价数据的DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        # 构建查询条件
        conditions = ["symbol = ?"]
        params = [symbol]
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT symbol, market, data_type, date, open, high, low, close, volume, amount
            FROM volume_price_data 
            WHERE {where_clause}
            ORDER BY date
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if df.empty:
            print(f"未找到股票/指数 {symbol} 的数据")
        
        return df
    
    def get_market_data(self, market: str, data_type: Optional[str] = None,
                       start_date: Optional[str] = None, end_date: Optional[str] = None, 
                       limit: Optional[int] = None) -> pd.DataFrame:
        """
        获取指定市场的数据
        
        Args:
            market: 市场代码 ('CN', 'HK', 'US')
            data_type: 数据类型 ('stock', 'index')，None表示所有类型
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 限制返回的记录数
            
        Returns:
            包含市场数据的DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        conditions = ["market = ?"]
        params = [market]
        
        if data_type:
            conditions.append("data_type = ?")
            params.append(data_type)
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT symbol, market, data_type, date, open, high, low, close, volume, amount
            FROM volume_price_data 
            WHERE {where_clause}
            ORDER BY symbol, date
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_latest_data(self, symbol: Optional[str] = None, market: Optional[str] = None, 
                       data_type: Optional[str] = None, days: int = 1) -> pd.DataFrame:
        """
        获取最新的数据
        
        Args:
            symbol: 股票代码，None表示所有股票
            market: 市场代码，None表示所有市场
            data_type: 数据类型，None表示所有类型
            days: 最近几天的数据
            
        Returns:
            包含最新数据的DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        # 获取最新日期
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM volume_price_data")
        latest_date = cursor.fetchone()[0]
        
        if not latest_date:
            conn.close()
            return pd.DataFrame()
        
        # 计算开始日期
        latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
        start_dt = latest_dt - timedelta(days=days-1)
        start_date = start_dt.strftime('%Y-%m-%d')
        
        # 构建查询条件
        conditions = ["date >= ?"]
        params = [start_date]
        
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        if data_type:
            conditions.append("data_type = ?")
            params.append(data_type)
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT symbol, market, data_type, date, open, high, low, close, volume, amount
            FROM volume_price_data 
            WHERE {where_clause}
            ORDER BY date DESC, symbol
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def search_stocks(self, keyword: str, market: Optional[str] = None, 
                     data_type: Optional[str] = None) -> pd.DataFrame:
        """
        搜索股票/指数（按名称或代码）
        
        Args:
            keyword: 搜索关键词
            market: 市场代码，None表示所有市场
            data_type: 数据类型，None表示所有类型
            
        Returns:
            匹配的股票列表
        """
        conn = sqlite3.connect(self.db_path)
        
        conditions = ["(symbol LIKE ? OR name LIKE ?)"]
        params = [f"%{keyword}%", f"%{keyword}%"]
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        if data_type:
            conditions.append("data_type = ?")
            params.append(data_type)
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT * FROM stock_info 
            WHERE {where_clause}
            ORDER BY market, data_type, symbol
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_industry_stocks(self, industry: str, market: Optional[str] = None) -> pd.DataFrame:
        """
        获取指定行业的股票
        
        Args:
            industry: 行业名称
            market: 市场代码，None表示所有市场
            
        Returns:
            指定行业的股票列表
        """
        conn = sqlite3.connect(self.db_path)
        
        conditions = ["industry = ?", "data_type = 'stock'"]
        params = [industry]
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT * FROM stock_info 
            WHERE {where_clause}
            ORDER BY market, symbol
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_statistics(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 按市场和数据类型统计股票数量
        cursor.execute("SELECT market, data_type, COUNT(*) FROM stock_info GROUP BY market, data_type")
        stock_counts = cursor.fetchall()
        stats['stock_counts'] = {}
        for market, dtype, count in stock_counts:
            if market not in stats['stock_counts']:
                stats['stock_counts'][market] = {}
            stats['stock_counts'][market][dtype] = count
        
        # 按市场和数据类型统计数据记录
        cursor.execute("SELECT market, data_type, COUNT(*) FROM volume_price_data GROUP BY market, data_type")
        data_counts = cursor.fetchall()
        stats['data_counts'] = {}
        for market, dtype, count in data_counts:
            if market not in stats['data_counts']:
                stats['data_counts'][market] = {}
            stats['data_counts'][market][dtype] = count
        
        # 日期范围
        cursor.execute("SELECT MIN(date), MAX(date) FROM volume_price_data")
        date_range = cursor.fetchone()
        stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
        
        # 行业统计
        cursor.execute("SELECT industry, COUNT(*) FROM stock_info WHERE data_type='stock' GROUP BY industry ORDER BY COUNT(*) DESC")
        industry_counts = cursor.fetchall()
        stats['industry_counts'] = {industry: count for industry, count in industry_counts}
        
        # 总计
        cursor.execute("SELECT COUNT(*) FROM stock_info")
        stats['total_stocks'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM volume_price_data")
        stats['total_records'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def get_top_volume_stocks(self, market: str, data_type: str = 'stock', 
                             date: Optional[str] = None, top_n: int = 10) -> pd.DataFrame:
        """
        获取成交量最大的股票/指数
        
        Args:
            market: 市场代码
            data_type: 数据类型 ('stock' 或 'index')
            date: 指定日期，None表示最新日期
            top_n: 返回前N只股票
            
        Returns:
            成交量排序的数据
        """
        conn = sqlite3.connect(self.db_path)
        
        if date is None:
            # 获取最新日期
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM volume_price_data WHERE market = ? AND data_type = ?", 
                          (market, data_type))
            date = cursor.fetchone()[0]
        
        query = """
            SELECT v.*, s.name, s.industry
            FROM volume_price_data v
            LEFT JOIN stock_info s ON v.symbol = s.symbol AND v.market = s.market
            WHERE v.market = ? AND v.data_type = ? AND v.date = ?
            ORDER BY v.volume DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(market, data_type, date, top_n))
        conn.close()
        
        return df

def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='股票数据读取器 V2')
    parser.add_argument('--db', help='数据库文件路径 (默认自动检测cn-lj.dat.gz, hk-lj.dat.gz, us-lj.dat.gz)')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 股票列表命令
    list_parser = subparsers.add_parser('list', help='获取股票/指数列表')
    list_parser.add_argument('--market', choices=['CN', 'HK', 'US'], help='指定市场')
    list_parser.add_argument('--type', choices=['stock', 'index'], help='指定类型')
    
    # 个股列表命令
    subparsers.add_parser('stocks', help='获取个股列表')
    
    # 指数列表命令
    subparsers.add_parser('indices', help='获取指数列表')
    
    # 股票数据命令
    data_parser = subparsers.add_parser('data', help='获取股票/指数数据')
    data_parser.add_argument('symbol', help='股票代码')
    data_parser.add_argument('--market', choices=['CN', 'HK', 'US'], help='指定市场')
    data_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    data_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    
    # 搜索命令
    search_parser = subparsers.add_parser('search', help='搜索股票/指数')
    search_parser.add_argument('keyword', help='搜索关键词')
    search_parser.add_argument('--market', choices=['CN', 'HK', 'US'], help='指定市场')
    search_parser.add_argument('--type', choices=['stock', 'index'], help='指定类型')
    
    # 行业命令
    industry_parser = subparsers.add_parser('industry', help='获取行业股票')
    industry_parser.add_argument('industry_name', help='行业名称')
    industry_parser.add_argument('--market', choices=['CN', 'HK', 'US'], help='指定市场')
    
    # 统计命令
    subparsers.add_parser('stats', help='显示统计信息')
    
    # 文件信息命令
    subparsers.add_parser('info', help='显示文件信息')
    
    # 最新数据命令
    latest_parser = subparsers.add_parser('latest', help='获取最新数据')
    latest_parser.add_argument('--symbol', help='股票代码')
    latest_parser.add_argument('--market', choices=['CN', 'HK', 'US'], help='指定市场')
    latest_parser.add_argument('--type', choices=['stock', 'index'], help='指定类型')
    latest_parser.add_argument('--days', type=int, default=1, help='最近几天')
    
    # 成交量排行命令
    volume_parser = subparsers.add_parser('volume', help='成交量排行')
    volume_parser.add_argument('market', choices=['CN', 'HK', 'US'], help='市场')
    volume_parser.add_argument('--type', choices=['stock', 'index'], default='stock', help='数据类型')
    volume_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    volume_parser.add_argument('--top', type=int, default=10, help='前N只股票')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 自动检测数据库文件
    db_path = args.db
    if not db_path:
        # 按优先级检测数据库文件
        possible_files = [
            'cn-lj.dat.gz', 'hk-lj.dat.gz', 'us-lj.dat.gz',
            'cn-lj.dat', 'hk-lj.dat', 'us-lj.dat',
            'data-lj.dat.gz', 'data-lj.dat'
        ]
        
        for filename in possible_files:
            if os.path.exists(filename):
                db_path = filename
                print(f"自动检测到数据文件: {filename}")
                break
        
        if not db_path:
            print("错误: 未找到数据文件，请使用 --db 参数指定文件路径")
            print("支持的文件格式:")
            print("  - cn-lj.dat.gz / cn-lj.dat (中国市场)")
            print("  - hk-lj.dat.gz / hk-lj.dat (香港市场)")
            print("  - us-lj.dat.gz / us-lj.dat (美国市场)")
            print("  - data-lj.dat.gz / data-lj.dat (旧格式)")
            return
    
    try:
        reader = StockDataReaderV2(db_path)
        
        if args.command == 'list':
            df = reader.get_stock_list(args.market, getattr(args, 'type', None))
            print(f"\n股票/指数列表 ({len(df)}只):")
            print(df.to_string(index=False))
            
        elif args.command == 'stocks':
            df = reader.get_stocks_only()
            print(f"\n个股列表 ({len(df)}只):")
            print(df.to_string(index=False))
            
        elif args.command == 'indices':
            df = reader.get_indices_only()
            print(f"\n指数列表 ({len(df)}个):")
            print(df.to_string(index=False))
            
        elif args.command == 'data':
            df = reader.get_stock_data(args.symbol, args.market, args.start, args.end)
            if not df.empty:
                data_type_name = "个股" if df.iloc[0]['data_type'] == 'stock' else "指数"
                print(f"\n{args.symbol} {data_type_name}数据:")
                print(df.to_string(index=False))
            
        elif args.command == 'search':
            df = reader.search_stocks(args.keyword, args.market, getattr(args, 'type', None))
            print(f"\n搜索结果 ({len(df)}只):")
            print(df.to_string(index=False))
            
        elif args.command == 'industry':
            df = reader.get_industry_stocks(args.industry_name, args.market)
            print(f"\n{args.industry_name}行业股票 ({len(df)}只):")
            print(df.to_string(index=False))
            
        elif args.command == 'info':
            info = reader.get_file_info()
            print("\n=== 数据文件信息 ===")
            print(f"文件路径: {info['original_path']}")
            print(f"文件格式: {info['format']}")
            print(f"文件大小: {info['size']:,} bytes ({info['size']/1024/1024:.2f} MB)")
            print(f"是否压缩: {'是' if info['compressed'] else '否'}")
            
            if 'uncompressed_size' in info:
                compression_ratio = (1 - info['size'] / info['uncompressed_size']) * 100
                print(f"解压大小: {info['uncompressed_size']:,} bytes ({info['uncompressed_size']/1024/1024:.2f} MB)")
                print(f"压缩率: {compression_ratio:.2f}%")
            
            print(f"可访问性: {'正常' if info['readable'] else '异常'}")
            
        elif args.command == 'stats':
            stats = reader.get_statistics()
            print("\n=== 数据库统计信息 ===")
            print("股票/指数数量:")
            for market, types in stats['stock_counts'].items():
                for dtype, count in types.items():
                    type_name = "个股" if dtype == "stock" else "指数"
                    print(f"  {market}市场{type_name}: {count}只")
            print("\n数据记录:")
            for market, types in stats['data_counts'].items():
                for dtype, count in types.items():
                    type_name = "个股" if dtype == "stock" else "指数"
                    print(f"  {market}市场{type_name}: {count}条")
            print(f"\n总计: {stats['total_stocks']}只股票/指数, {stats['total_records']}条记录")
            if stats['date_range']['start']:
                print(f"数据日期范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
            
            if stats['industry_counts']:
                print("\n主要行业分布:")
                for industry, count in list(stats['industry_counts'].items())[:10]:
                    print(f"  {industry}: {count}只")
                
        elif args.command == 'latest':
            df = reader.get_latest_data(args.symbol, args.market, getattr(args, 'type', None), args.days)
            print(f"\n最新数据 (最近{args.days}天):")
            print(df.to_string(index=False))
            
        elif args.command == 'volume':
            df = reader.get_top_volume_stocks(args.market, args.type, args.date, args.top)
            type_name = "个股" if args.type == "stock" else "指数"
            print(f"\n{args.market}市场{type_name}成交量排行 (前{args.top}名):")
            if args.date:
                print(f"日期: {args.date}")
            print(df.to_string(index=False))
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
