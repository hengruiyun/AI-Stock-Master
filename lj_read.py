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
        
        # 移除打印，改为返回空DataFrame（调用者会处理）
        # if df.empty:
        #     print(f"未找到股票/指数 {symbol} 的数据")
        
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
    
    def get_batch_latest_data(self, symbols: List[str], market: Optional[str] = None, 
                             fields: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        批量获取多个股票的最新数据（性能优化版本）
        
        Args:
            symbols: 股票代码列表
            market: 市场代码 (可选，如果不指定会自动查找)
            fields: 需要获取的字段列表，如 ['amount', 'volume', 'close']
                   None 表示获取所有字段
        
        Returns:
            字典: {stock_code: {field: value, ...}, ...}
            
        示例:
            reader = StockDataReaderV2('cn-lj.dat.gz')
            # 批量获取成交金额
            result = reader.get_batch_latest_data(
                ['000001', '600519', '600036'], 
                market='CN',
                fields=['amount', 'volume', 'close']
            )
            # 返回: {'000001': {'amount': 123456789, 'volume': 12345, 'close': 12.34}, ...}
        """
        if not symbols:
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建批量查询 - 使用 IN 子句
        placeholders = ','.join('?' * len(symbols))
        
        # 构建字段选择
        if fields:
            field_list = ', '.join(fields)
        else:
            field_list = '*'
        
        # 查询条件
        conditions = [f"symbol IN ({placeholders})"]
        params = list(symbols)
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        where_clause = " AND ".join(conditions)
        
        # 使用子查询获取每个股票的最新数据
        query = f"""
            SELECT symbol, {field_list}
            FROM volume_price_data
            WHERE {where_clause}
            AND date = (
                SELECT MAX(date) 
                FROM volume_price_data AS vpd2 
                WHERE vpd2.symbol = volume_price_data.symbol
                {f'AND vpd2.market = ?' if market else ''}
            )
        """
        
        if market:
            params.append(market)  # 为子查询添加market参数
        
        try:
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            # 构建结果字典
            result = {}
            for row in rows:
                stock_code = row[0]  # symbol是第一列
                stock_data = {}
                for i, col_name in enumerate(columns):
                    if col_name != 'symbol':  # 排除symbol字段
                        value = row[i]
                        # 自动计算成交金额（如果缺失）
                        if col_name == 'amount' and (value is None or value == 0):
                            # 尝试从 volume 和 close 计算
                            volume_idx = columns.index('volume') if 'volume' in columns else -1
                            close_idx = columns.index('close') if 'close' in columns else -1
                            if volume_idx >= 0 and close_idx >= 0:
                                volume = row[volume_idx]
                                close = row[close_idx]
                                if volume and close:
                                    value = float(volume) * float(close)
                        stock_data[col_name] = value
                result[stock_code] = stock_data
            
            conn.close()
            return result
            
        except Exception as e:
            conn.close()
            print(f"批量查询失败: {e}")
            return {}
    
    def get_batch_historical_data(self, symbols: List[str], market: Optional[str] = None,
                                  days: int = 38) -> Dict[str, List[Dict]]:
        """
        批量获取多个股票的历史数据（性能优化版本）
        
        Args:
            symbols: 股票代码列表
            market: 市场代码 (可选)
            days: 获取最近N天的数据
        
        Returns:
            字典: {
                stock_code: [
                    {'date': '2024-01-01', 'open': 10.0, 'close': 10.5, ...},
                    {'date': '2024-01-02', 'open': 10.5, 'close': 11.0, ...},
                    ...
                ],
                ...
            }
        
        示例:
            reader = StockDataReaderV2('cn-lj.dat.gz')
            result = reader.get_batch_historical_data(
                ['000001', '600519', '600036'],
                market='CN',
                days=38
            )
        """
        if not symbols:
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建批量查询
        placeholders = ','.join('?' * len(symbols))
        
        # 查询条件
        conditions = [f"symbol IN ({placeholders})"]
        params = list(symbols)
        
        if market:
            conditions.append("market = ?")
            params.append(market)
        
        where_clause = " AND ".join(conditions)
        
        # 查询最近N天的数据
        # 使用更简单的方法：先获取每个股票的最新日期，然后获取最近N天
        query = f"""
            WITH latest_dates AS (
                SELECT symbol, MAX(date) as max_date
            FROM volume_price_data
            WHERE {where_clause}
                GROUP BY symbol
            )
            SELECT v.symbol, v.date, v.open, v.high, v.low, v.close, v.volume, v.amount
            FROM volume_price_data v
            INNER JOIN latest_dates l ON v.symbol = l.symbol
            WHERE v.symbol IN ({placeholders})
            AND v.date >= date(l.max_date, '-' || ? || ' days')
            ORDER BY v.symbol, v.date DESC
        """
        
        # 添加 days 参数 - 注意：params已经包含symbols和market，只需追加days
        params_final = params + symbols + [days - 1]
        
        try:
            cursor.execute(query, params_final)
            rows = cursor.fetchall()
            
            # 按股票代码分组
            result = {}
            for row in rows:
                symbol = row[0]
                date = row[1]
                
                stock_data = {
                    'date': date,
                    'open': row[2] or 0,
                    'high': row[3] or 0,
                    'low': row[4] or 0,
                    'close': row[5] or 0,
                    'volume': row[6] or 0,
                    'amount': row[7] or 0
                }
                
                # 自动计算缺失的成交金额
                if stock_data['amount'] == 0 and stock_data['volume'] > 0 and stock_data['close'] > 0:
                    stock_data['amount'] = stock_data['volume'] * stock_data['close']
                
                if symbol not in result:
                    result[symbol] = []
                result[symbol].append(stock_data)
            
            # 按日期正序排列（最老的在前）
            for symbol in result:
                result[symbol].reverse()
            
            conn.close()
            return result
            
        except Exception as e:
            conn.close()
            print(f"批量查询历史数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
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
    
    def get_lhb_data(self, symbol: Optional[str] = None, 
                     start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜数据
        
        Args:
            symbol: 股票代码（6位），None表示获取所有股票
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            龙虎榜数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查龙虎榜表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lhb_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM lhb_data 
            WHERE {where_clause}
            ORDER BY trade_date DESC, net_amount DESC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_lhb_stats(self, symbol: Optional[str] = None) -> Dict:
        """
        获取龙虎榜统计信息
        
        Args:
            symbol: 股票代码，None表示全市场统计
            
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查龙虎榜表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lhb_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        
        stats = {}
        
        if symbol:
            # 单只股票的统计
            cursor.execute("""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date),
                       AVG(net_amount), SUM(net_amount)
                FROM lhb_data 
                WHERE symbol = ?
            """, (symbol,))
            
            result = cursor.fetchone()
            stats['count'] = result[0]
            stats['first_date'] = result[1]
            stats['last_date'] = result[2]
            stats['avg_net_amount'] = result[3]
            stats['total_net_amount'] = result[4]
            
            # 上榜原因分布
            cursor.execute("""
                SELECT reason, COUNT(*) as count
                FROM lhb_data 
                WHERE symbol = ?
                GROUP BY reason
                ORDER BY count DESC
            """, (symbol,))
            
            stats['reasons'] = {row[0]: row[1] for row in cursor.fetchall()}
            
        else:
            # 全市场统计
            cursor.execute("SELECT COUNT(*) FROM lhb_data")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM lhb_data")
            date_range = cursor.fetchone()
            stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
            
            # 上榜次数最多的股票
            cursor.execute("""
                SELECT symbol, name, COUNT(*) as count
                FROM lhb_data 
                GROUP BY symbol, name 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_stocks'] = [
                {'symbol': row[0], 'name': row[1], 'count': row[2]} 
                for row in cursor.fetchall()
            ]
            
            # 上榜原因分布
            cursor.execute("""
                SELECT reason, COUNT(*) as count
                FROM lhb_data 
                GROUP BY reason 
                ORDER BY count DESC
            """)
            stats['reasons'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        return stats
    
    def get_lhb_top_net_amount(self, date: Optional[str] = None, 
                               top_n: int = 10, 
                               net_type: str = 'all') -> pd.DataFrame:
        """
        获取龙虎榜净买入/净卖出排行
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，None表示最新日期
            top_n: 返回前N名
            net_type: 'all'=全部, 'buy'=净买入, 'sell'=净卖出
            
        Returns:
            排行数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查龙虎榜表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lhb_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        if date is None:
            # 获取最新日期
            cursor.execute("SELECT MAX(trade_date) FROM lhb_data")
            date = cursor.fetchone()[0]
        
        # 构建查询条件
        if net_type == 'buy':
            order_clause = "net_amount DESC"
            where_clause = "net_amount > 0"
        elif net_type == 'sell':
            order_clause = "net_amount ASC"
            where_clause = "net_amount < 0"
        else:
            order_clause = "ABS(net_amount) DESC"
            where_clause = "1=1"
        
        query = f"""
            SELECT * FROM lhb_data 
            WHERE trade_date = ? AND {where_clause}
            ORDER BY {order_clause}
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(date, top_n))
        conn.close()
        
        return df
    
    def get_money_flow_data(self, symbol: Optional[str] = None, 
                            start_date: Optional[str] = None, 
                            end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取个股资金流向数据
        
        Args:
            symbol: 股票代码（6位），None表示获取所有股票
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            资金流向数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查资金流向表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='money_flow_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM money_flow_data 
            WHERE {where_clause}
            ORDER BY trade_date DESC, net_mf_amount DESC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_money_flow_stats(self, symbol: Optional[str] = None) -> Dict:
        """
        获取资金流向统计信息
        
        Args:
            symbol: 股票代码，None表示全市场统计
            
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查资金流向表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='money_flow_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        
        stats = {}
        
        if symbol:
            # 单只股票的统计
            cursor.execute("""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date),
                       AVG(net_mf_amount), SUM(net_mf_amount)
                FROM money_flow_data 
                WHERE symbol = ?
            """, (symbol,))
            
            result = cursor.fetchone()
            stats['count'] = result[0]
            stats['first_date'] = result[1]
            stats['last_date'] = result[2]
            stats['avg_net_mf_amount'] = result[3]
            stats['total_net_mf_amount'] = result[4]
            
        else:
            # 全市场统计
            cursor.execute("SELECT COUNT(*) FROM money_flow_data")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM money_flow_data")
            date_range = cursor.fetchone()
            stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
            
            # 获取最近一天的净流入前10名
            cursor.execute("""
                SELECT trade_date FROM money_flow_data 
                ORDER BY trade_date DESC LIMIT 1
            """)
            latest_date_result = cursor.fetchone()
            
            if latest_date_result:
                latest_date = latest_date_result[0]
                cursor.execute("""
                    SELECT symbol, name, net_mf_amount, close, pct_change
                    FROM money_flow_data 
                    WHERE trade_date = ?
                    ORDER BY net_mf_amount DESC 
                    LIMIT 10
                """, (latest_date,))
                stats['top_inflow'] = [
                    {'symbol': row[0], 'name': row[1], 'net_mf_amount': row[2], 
                     'close': row[3], 'pct_change': row[4]} 
                    for row in cursor.fetchall()
                ]
                stats['latest_date'] = latest_date
        
        conn.close()
        return stats
    
    def get_money_flow_top(self, date: Optional[str] = None, 
                           top_n: int = 10, 
                           flow_type: str = 'inflow') -> pd.DataFrame:
        """
        获取资金流向净流入/净流出排行
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，None表示最新日期
            top_n: 返回前N名
            flow_type: 'inflow'=净流入, 'outflow'=净流出
            
        Returns:
            排行数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查资金流向表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='money_flow_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        if date is None:
            # 获取最新日期
            cursor.execute("SELECT MAX(trade_date) FROM money_flow_data")
            date = cursor.fetchone()[0]
        
        # 构建查询条件
        if flow_type == 'inflow':
            order_clause = "net_mf_amount DESC"
            where_clause = "net_mf_amount > 0"
        else:  # outflow
            order_clause = "net_mf_amount ASC"
            where_clause = "net_mf_amount < 0"
        
        query = f"""
            SELECT * FROM money_flow_data 
            WHERE trade_date = ? AND {where_clause}
            ORDER BY {order_clause}
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(date, top_n))
        conn.close()
        
        return df
    
    def get_ztb_data(self, symbol: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取涨停板数据
        
        Args:
            symbol: 股票代码（6位），None表示获取所有股票
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit_type: 涨跌停类型 (U=涨停, D=跌停, Z=炸板)
            
        Returns:
            涨停板数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查涨停板表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ztb_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        
        if limit_type:
            conditions.append("limit_type = ?")
            params.append(limit_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM ztb_data 
            WHERE {where_clause}
            ORDER BY trade_date DESC, limit_times DESC, pct_chg DESC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_ztb_stats(self, symbol: Optional[str] = None) -> Dict:
        """
        获取涨停板统计信息
        
        Args:
            symbol: 股票代码，None表示全市场统计
            
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查涨停板表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ztb_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        
        stats = {}
        
        if symbol:
            # 单只股票的统计
            cursor.execute("""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date),
                       MAX(limit_times)
                FROM ztb_data 
                WHERE symbol = ? AND limit_type = 'U'
            """, (symbol,))
            
            result = cursor.fetchone()
            stats['zt_count'] = result[0]
            stats['first_date'] = result[1]
            stats['last_date'] = result[2]
            stats['max_limit_times'] = result[3]
            
        else:
            # 全市场统计
            cursor.execute("SELECT COUNT(*) FROM ztb_data")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM ztb_data")
            date_range = cursor.fetchone()
            stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
            
            # 各类型统计
            cursor.execute("SELECT limit_type, COUNT(*) FROM ztb_data GROUP BY limit_type")
            stats['type_counts'] = dict(cursor.fetchall())
            
            # 获取最新涨停股票
            cursor.execute("""
                SELECT trade_date FROM ztb_data 
                ORDER BY trade_date DESC LIMIT 1
            """)
            latest_date_result = cursor.fetchone()
            
            if latest_date_result:
                latest_date = latest_date_result[0]
                cursor.execute("""
                    SELECT symbol, name, pct_chg, limit_times, open_times, up_stat
                    FROM ztb_data 
                    WHERE trade_date = ? AND limit_type = 'U'
                    ORDER BY limit_times DESC, pct_chg DESC
                    LIMIT 10
                """, (latest_date,))
                stats['latest_zt'] = [
                    {'symbol': row[0], 'name': row[1], 'pct_chg': row[2], 
                     'limit_times': row[3], 'open_times': row[4], 'up_stat': row[5]} 
                    for row in cursor.fetchall()
                ]
                stats['latest_date'] = latest_date
        
        conn.close()
        return stats
    
    def get_ztb_top(self, date: Optional[str] = None,
                    top_n: int = 10,
                    limit_type: str = 'U') -> pd.DataFrame:
        """
        获取涨停板排行榜
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，None表示最新日期
            top_n: 返回前N名
            limit_type: U=涨停, D=跌停, Z=炸板
            
        Returns:
            排行数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查涨停板表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ztb_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        if date is None:
            # 获取最新日期
            cursor.execute("SELECT MAX(trade_date) FROM ztb_data")
            date = cursor.fetchone()[0]
        
        query = f"""
            SELECT * FROM ztb_data 
            WHERE trade_date = ? AND limit_type = ?
            ORDER BY limit_times DESC, pct_chg DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(date, limit_type, top_n))
        conn.close()
        
        return df
    
    def get_sector_money_flow_data(self, sector_name: Optional[str] = None,
                                    start_date: Optional[str] = None,
                                    end_date: Optional[str] = None,
                                    content_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取行业/概念板块资金流向数据
        
        Args:
            sector_name: 板块名称，None表示获取所有板块
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            content_type: 板块类型 ('行业' 或 '概念')，None表示所有类型
            
        Returns:
            板块资金流向数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查板块资金流向表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sector_money_flow_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if sector_name:
            conditions.append("sector_name = ?")
            params.append(sector_name)
        
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        
        if content_type:
            conditions.append("content_type = ?")
            params.append(content_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM sector_money_flow_data 
            WHERE {where_clause}
            ORDER BY trade_date DESC, net_amount DESC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_sector_money_flow_stats(self, sector_name: Optional[str] = None, 
                                     content_type: Optional[str] = None) -> Dict:
        """
        获取板块资金流向统计信息
        
        Args:
            sector_name: 板块名称，None表示全市场统计
            content_type: 板块类型 ('行业' 或 '概念')，None表示所有类型
            
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查板块资金流向表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sector_money_flow_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        
        stats = {}
        
        if sector_name:
            # 单个板块的统计
            base_condition = "sector_name = ?"
            params = [sector_name]
            
            if content_type:
                base_condition += " AND content_type = ?"
                params.append(content_type)
            
            cursor.execute(f"""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date),
                       AVG(net_amount), SUM(net_amount)
                FROM sector_money_flow_data 
                WHERE {base_condition}
            """, params)
            
            result = cursor.fetchone()
            stats['count'] = result[0]
            stats['first_date'] = result[1]
            stats['last_date'] = result[2]
            stats['avg_net_amount'] = result[3]
            stats['total_net_amount'] = result[4]
            
        else:
            # 全市场统计
            cursor.execute("SELECT COUNT(*) FROM sector_money_flow_data")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM sector_money_flow_data")
            date_range = cursor.fetchone()
            stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
            
            # 各类型统计
            cursor.execute("SELECT content_type, COUNT(*) FROM sector_money_flow_data GROUP BY content_type")
            stats['type_counts'] = dict(cursor.fetchall())
            
            # 获取最近一天的净流入前10名
            cursor.execute("""
                SELECT trade_date FROM sector_money_flow_data 
                ORDER BY trade_date DESC LIMIT 1
            """)
            latest_date_result = cursor.fetchone()
            
            if latest_date_result:
                latest_date = latest_date_result[0]
                
                # 行业板块净流入 TOP10
                cursor.execute("""
                    SELECT sector_name, net_amount, change_pct
                    FROM sector_money_flow_data 
                    WHERE trade_date = ? AND content_type = '行业'
                    ORDER BY net_amount DESC 
                    LIMIT 10
                """, (latest_date,))
                stats['top_industry_inflow'] = [
                    {'sector_name': row[0], 'net_amount': row[1], 'change_pct': row[2]} 
                    for row in cursor.fetchall()
                ]
                
                # 概念板块净流入 TOP10
                cursor.execute("""
                    SELECT sector_name, net_amount, change_pct
                    FROM sector_money_flow_data 
                    WHERE trade_date = ? AND content_type = '概念'
                    ORDER BY net_amount DESC 
                    LIMIT 10
                """, (latest_date,))
                stats['top_concept_inflow'] = [
                    {'sector_name': row[0], 'net_amount': row[1], 'change_pct': row[2]} 
                    for row in cursor.fetchall()
                ]
                
                stats['latest_date'] = latest_date
        
        conn.close()
        return stats
    
    def get_sector_money_flow_top(self, date: Optional[str] = None,
                                   top_n: int = 10,
                                   content_type: str = '行业',
                                   flow_type: str = 'inflow') -> pd.DataFrame:
        """
        获取板块资金流向净流入/净流出排行
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，None表示最新日期
            top_n: 返回前N名
            content_type: 板块类型 ('行业' 或 '概念')
            flow_type: 'inflow'=净流入, 'outflow'=净流出
            
        Returns:
            排行数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查板块资金流向表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sector_money_flow_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        if date is None:
            # 获取最新日期
            cursor.execute("SELECT MAX(trade_date) FROM sector_money_flow_data")
            date = cursor.fetchone()[0]
        
        # 构建查询条件
        if flow_type == 'inflow':
            order_clause = "net_amount DESC"
            where_clause = "net_amount > 0"
        else:  # outflow
            order_clause = "net_amount ASC"
            where_clause = "net_amount < 0"
        
        query = f"""
            SELECT * FROM sector_money_flow_data 
            WHERE trade_date = ? AND content_type = ? AND {where_clause}
            ORDER BY {order_clause}
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(date, content_type, top_n))
        conn.close()
        
        return df
    
    def get_ztb_sector_data(self, sector_name: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取涨停板板块统计数据
        
        Args:
            sector_name: 板块名称，None表示获取所有板块
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            涨停板板块统计数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查涨停板板块统计表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ztb_sector_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if sector_name:
            conditions.append("sector_name = ?")
            params.append(sector_name)
        
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM ztb_sector_data 
            WHERE {where_clause}
            ORDER BY trade_date DESC, rank ASC
        """
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_ztb_sector_stats(self, sector_name: Optional[str] = None) -> Dict:
        """
        获取涨停板板块统计信息
        
        Args:
            sector_name: 板块名称，None表示全市场统计
            
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查涨停板板块统计表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ztb_sector_data'")
        if not cursor.fetchone():
            conn.close()
            return {}
        
        stats = {}
        
        if sector_name:
            # 单个板块的统计
            cursor.execute("""
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date),
                       AVG(up_nums), MAX(up_nums)
                FROM ztb_sector_data 
                WHERE sector_name = ?
            """, (sector_name,))
            
            result = cursor.fetchone()
            stats['record_count'] = result[0]
            stats['first_date'] = result[1]
            stats['last_date'] = result[2]
            stats['avg_up_nums'] = result[3]
            stats['max_up_nums'] = result[4]
            
        else:
            # 全市场统计
            cursor.execute("SELECT COUNT(*) FROM ztb_sector_data")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(trade_date), MAX(trade_date) FROM ztb_sector_data")
            date_range = cursor.fetchone()
            stats['date_range'] = {'start': date_range[0], 'end': date_range[1]}
            
            # 获取最新板块排名
            cursor.execute("""
                SELECT trade_date FROM ztb_sector_data 
                ORDER BY trade_date DESC LIMIT 1
            """)
            latest_date_result = cursor.fetchone()
            
            if latest_date_result:
                latest_date = latest_date_result[0]
                cursor.execute("""
                    SELECT sector_name, up_nums, cons_nums, pct_chg, up_stat, rank
                    FROM ztb_sector_data 
                    WHERE trade_date = ?
                    ORDER BY rank ASC
                    LIMIT 10
                """, (latest_date,))
                stats['top_sectors'] = [
                    {'sector_name': row[0], 'up_nums': row[1], 'cons_nums': row[2],
                     'pct_chg': row[3], 'up_stat': row[4], 'rank': row[5]} 
                    for row in cursor.fetchall()
                ]
                stats['latest_date'] = latest_date
        
        conn.close()
        return stats
    
    def get_ztb_sector_top(self, date: Optional[str] = None,
                          top_n: int = 10) -> pd.DataFrame:
        """
        获取涨停板板块排行榜
        
        Args:
            date: 指定日期 (YYYY-MM-DD)，None表示最新日期
            top_n: 返回前N名
            
        Returns:
            排行数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查涨停板板块统计表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ztb_sector_data'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()
        
        if date is None:
            # 获取最新日期
            cursor.execute("SELECT MAX(trade_date) FROM ztb_sector_data")
            date = cursor.fetchone()[0]
        
        query = f"""
            SELECT * FROM ztb_sector_data 
            WHERE trade_date = ?
            ORDER BY rank ASC
            LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(date, top_n))
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
    
    # 龙虎榜数据命令
    lhb_parser = subparsers.add_parser('lhb', help='获取龙虎榜数据')
    lhb_parser.add_argument('--symbol', help='股票代码（6位）')
    lhb_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    lhb_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    
    # 龙虎榜统计命令
    lhb_stats_parser = subparsers.add_parser('lhb-stats', help='龙虎榜统计信息')
    lhb_stats_parser.add_argument('--symbol', help='股票代码（6位），不指定则显示全市场统计')
    
    # 龙虎榜净买入排行命令
    lhb_top_parser = subparsers.add_parser('lhb-top', help='龙虎榜净买入/卖出排行')
    lhb_top_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    lhb_top_parser.add_argument('--top', type=int, default=10, help='前N名')
    lhb_top_parser.add_argument('--type', choices=['all', 'buy', 'sell'], default='all', 
                               help='all=全部, buy=净买入, sell=净卖出')
    
    # 资金流向数据命令
    money_parser = subparsers.add_parser('money', help='获取个股资金流向数据')
    money_parser.add_argument('--symbol', help='股票代码（6位）')
    money_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    money_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    
    # 资金流向统计命令
    money_stats_parser = subparsers.add_parser('money-stats', help='资金流向统计信息')
    money_stats_parser.add_argument('--symbol', help='股票代码（6位），不指定则显示全市场统计')
    
    # 资金流向排行命令
    money_top_parser = subparsers.add_parser('money-top', help='资金流向净流入/流出排行')
    money_top_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    money_top_parser.add_argument('--top', type=int, default=10, help='前N名')
    money_top_parser.add_argument('--type', choices=['inflow', 'outflow'], default='inflow', 
                                  help='inflow=净流入, outflow=净流出')
    
    # 涨停板数据命令
    ztb_parser = subparsers.add_parser('ztb', help='获取涨停板数据')
    ztb_parser.add_argument('--symbol', help='股票代码（6位）')
    ztb_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    ztb_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    ztb_parser.add_argument('--type', choices=['U', 'D', 'Z'], 
                           help='U=涨停, D=跌停, Z=炸板')
    
    # 涨停板统计命令
    ztb_stats_parser = subparsers.add_parser('ztb-stats', help='涨停板统计信息')
    ztb_stats_parser.add_argument('--symbol', help='股票代码（6位），不指定则显示全市场统计')
    
    # 涨停板排行命令
    ztb_top_parser = subparsers.add_parser('ztb-top', help='涨停板排行榜')
    ztb_top_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    ztb_top_parser.add_argument('--top', type=int, default=10, help='前N名')
    ztb_top_parser.add_argument('--type', choices=['U', 'D', 'Z'], default='U', 
                                help='U=涨停, D=跌停, Z=炸板')
    
    # 板块资金流向数据命令
    sector_parser = subparsers.add_parser('sector', help='获取行业/概念板块资金流向数据')
    sector_parser.add_argument('--name', help='板块名称')
    sector_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    sector_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    sector_parser.add_argument('--type', choices=['行业', '概念'], help='板块类型')
    
    # 板块资金流向统计命令
    sector_stats_parser = subparsers.add_parser('sector-stats', help='板块资金流向统计信息')
    sector_stats_parser.add_argument('--name', help='板块名称，不指定则显示全市场统计')
    sector_stats_parser.add_argument('--type', choices=['行业', '概念'], help='板块类型')
    
    # 板块资金流向排行命令
    sector_top_parser = subparsers.add_parser('sector-top', help='板块资金流向排行榜')
    sector_top_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    sector_top_parser.add_argument('--top', type=int, default=10, help='前N名')
    sector_top_parser.add_argument('--type', choices=['行业', '概念'], default='行业',
                                   help='板块类型')
    sector_top_parser.add_argument('--flow', choices=['inflow', 'outflow'], default='inflow',
                                   help='inflow=净流入, outflow=净流出')
    
    # 涨停板板块统计数据命令
    ztbbk_parser = subparsers.add_parser('ztbbk', help='获取涨停板板块统计数据')
    ztbbk_parser.add_argument('--name', help='板块名称')
    ztbbk_parser.add_argument('--start', help='开始日期 (YYYY-MM-DD)')
    ztbbk_parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)')
    
    # 涨停板板块统计信息命令
    ztbbk_stats_parser = subparsers.add_parser('ztbbk-stats', help='涨停板板块统计信息')
    ztbbk_stats_parser.add_argument('--name', help='板块名称，不指定则显示全市场统计')
    
    # 涨停板板块排行命令
    ztbbk_top_parser = subparsers.add_parser('ztbbk-top', help='涨停板板块排行榜')
    ztbbk_top_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    ztbbk_top_parser.add_argument('--top', type=int, default=10, help='前N名')
    
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
            
        elif args.command == 'lhb':
            df = reader.get_lhb_data(args.symbol, args.start, args.end)
            if not df.empty:
                if args.symbol:
                    print(f"\n{args.symbol} 龙虎榜数据 ({len(df)}条):")
                else:
                    print(f"\n龙虎榜数据 ({len(df)}条):")
                print(df.to_string(index=False))
            else:
                print("\n未找到龙虎榜数据")
                
        elif args.command == 'lhb-stats':
            stats = reader.get_lhb_stats(args.symbol)
            if not stats:
                print("\n未找到龙虎榜数据")
            elif args.symbol:
                # 单只股票统计
                print(f"\n=== {args.symbol} 龙虎榜统计 ===")
                print(f"上榜次数: {stats['count']}次")
                if stats['first_date']:
                    print(f"首次上榜: {stats['first_date']}")
                    print(f"最近上榜: {stats['last_date']}")
                if stats['avg_net_amount']:
                    print(f"平均净买入: {stats['avg_net_amount']:,.2f}元")
                if stats['total_net_amount']:
                    print(f"累计净买入: {stats['total_net_amount']:,.2f}元")
                if stats['reasons']:
                    print("\n上榜原因分布:")
                    for reason, count in stats['reasons'].items():
                        print(f"  {reason}: {count}次")
            else:
                # 全市场统计
                print("\n=== 龙虎榜全市场统计 ===")
                print(f"总记录数: {stats['total_records']:,}条")
                if stats['date_range']['start']:
                    print(f"数据日期范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
                
                if stats['top_stocks']:
                    print(f"\n上榜次数最多的股票 (前10名):")
                    for i, stock in enumerate(stats['top_stocks'], 1):
                        print(f"  {i}. {stock['symbol']} ({stock['name']}): {stock['count']}次")
                
                if stats['reasons']:
                    print(f"\n上榜原因分布:")
                    for i, (reason, count) in enumerate(list(stats['reasons'].items())[:10], 1):
                        print(f"  {i}. {reason}: {count}次")
                        
        elif args.command == 'lhb-top':
            df = reader.get_lhb_top_net_amount(args.date, args.top, args.type)
            if not df.empty:
                type_name = {'all': '全部', 'buy': '净买入', 'sell': '净卖出'}[args.type]
                date_str = df['trade_date'].iloc[0] if not df.empty else args.date
                print(f"\n龙虎榜{type_name}排行 (前{args.top}名) - {date_str}:")
                # 选择关键字段显示
                display_cols = ['symbol', 'name', 'close', 'pct_chg', 'net_amount', 'net_rate', 'reason']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到龙虎榜数据")
                
        elif args.command == 'money':
            df = reader.get_money_flow_data(args.symbol, args.start, args.end)
            if not df.empty:
                if args.symbol:
                    print(f"\n{args.symbol} 资金流向数据 ({len(df)}条):")
                else:
                    print(f"\n资金流向数据 ({len(df)}条):")
                # 选择关键字段显示
                display_cols = ['trade_date', 'symbol', 'name', 'close', 'pct_change', 
                               'net_mf_amount', 'buy_elg_amount', 'sell_elg_amount']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到资金流向数据")
                
        elif args.command == 'money-stats':
            stats = reader.get_money_flow_stats(args.symbol)
            if not stats:
                print("\n未找到资金流向数据")
            elif args.symbol:
                # 单只股票统计
                print(f"\n=== {args.symbol} 资金流向统计 ===")
                print(f"数据记录数: {stats['count']}条")
                if stats['first_date']:
                    print(f"首次记录: {stats['first_date']}")
                    print(f"最近记录: {stats['last_date']}")
                if stats['avg_net_mf_amount']:
                    print(f"平均净流入: {stats['avg_net_mf_amount']/10000:.2f}万元")
                if stats['total_net_mf_amount']:
                    print(f"累计净流入: {stats['total_net_mf_amount']/10000:.2f}万元")
            else:
                # 全市场统计
                print("\n=== 个股资金流向全市场统计 ===")
                print(f"总记录数: {stats['total_records']:,}条")
                if stats['date_range']['start']:
                    print(f"数据日期范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
                
                if 'top_inflow' in stats and stats['top_inflow']:
                    print(f"\n最新净流入前10名 ({stats['latest_date']}):")
                    for i, stock in enumerate(stats['top_inflow'], 1):
                        # 安全处理可能为 None 的数值
                        net_amount_str = f"{stock['net_mf_amount']/10000:.2f}万元" if stock['net_mf_amount'] is not None else "N/A"
                        close_str = f"{stock['close']:.2f}" if stock['close'] is not None else "N/A"
                        pct_str = f"{stock['pct_change']:+.2f}%" if stock['pct_change'] is not None else "N/A"
                        print(f"  {i}. {stock['symbol']} ({stock['name']}): "
                              f"净流入{net_amount_str} "
                              f"(收盘{close_str}, {pct_str})")
                        
        elif args.command == 'money-top':
            df = reader.get_money_flow_top(args.date, args.top, args.type)
            if not df.empty:
                type_name = {'inflow': '净流入', 'outflow': '净流出'}[args.type]
                date_str = df['trade_date'].iloc[0] if not df.empty else args.date
                print(f"\n资金流向{type_name}排行 (前{args.top}名) - {date_str}:")
                # 选择关键字段显示
                display_cols = ['symbol', 'name', 'close', 'pct_change', 'net_mf_amount', 
                               'buy_elg_amount', 'sell_elg_amount']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到资金流向数据")
        
        elif args.command == 'ztb':
            df = reader.get_ztb_data(args.symbol, args.start, args.end, args.type)
            if not df.empty:
                if args.symbol:
                    print(f"\n{args.symbol} 涨停板数据 ({len(df)}条):")
                else:
                    print(f"\n涨停板数据 ({len(df)}条):")
                # 选择关键字段显示
                display_cols = ['trade_date', 'symbol', 'name', 'close', 'pct_chg', 
                               'limit_times', 'open_times', 'up_stat', 'limit_type']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到涨停板数据")
        
        elif args.command == 'ztb-stats':
            stats = reader.get_ztb_stats(args.symbol)
            if not stats:
                print("\n未找到涨停板数据")
            elif args.symbol:
                # 单只股票统计
                print(f"\n=== {args.symbol} 涨停板统计 ===")
                print(f"涨停次数: {stats['zt_count']}次")
                if stats['first_date']:
                    print(f"首次涨停: {stats['first_date']}")
                    print(f"最近涨停: {stats['last_date']}")
                if stats['max_limit_times']:
                    print(f"最高连板: {stats['max_limit_times']}连板")
            else:
                # 全市场统计
                print("\n=== 涨停板全市场统计 ===")
                print(f"总记录数: {stats['total_records']:,}条")
                if stats['date_range']['start']:
                    print(f"数据日期范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
                
                if 'type_counts' in stats:
                    print(f"\n类型分布:")
                    type_names = {'U': '涨停', 'D': '跌停', 'Z': '炸板'}
                    for limit_type, count in stats['type_counts'].items():
                        print(f"  {type_names.get(limit_type, limit_type)}: {count:,}次")
                
                if 'latest_zt' in stats and stats['latest_zt']:
                    print(f"\n最新涨停股票 ({stats['latest_date']}, 前10名):")
                    for i, stock in enumerate(stats['latest_zt'], 1):
                        zt_info = f"{stock['limit_times']}连板" if stock['limit_times'] > 1 else "首板"
                        zb_info = f"炸板{stock['open_times']}次" if stock['open_times'] > 0 else "一字板"
                        print(f"  {i}. {stock['symbol']} ({stock['name']}): "
                              f"{stock['pct_chg']:+.2f}% | {zt_info} | {zb_info} | {stock['up_stat']}")
        
        elif args.command == 'ztb-top':
            df = reader.get_ztb_top(args.date, args.top, args.type)
            if not df.empty:
                type_names = {'U': '涨停', 'D': '跌停', 'Z': '炸板'}
                type_name = type_names.get(args.type, args.type)
                date_str = df['trade_date'].iloc[0] if not df.empty else args.date
                print(f"\n{type_name}排行 (前{args.top}名) - {date_str}:")
                # 选择关键字段显示
                display_cols = ['symbol', 'name', 'close', 'pct_chg', 'limit_times', 
                               'open_times', 'up_stat', 'fd_amount']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到涨停板数据")
        
        elif args.command == 'sector':
            df = reader.get_sector_money_flow_data(args.name, args.start, args.end, args.type)
            if not df.empty:
                if args.name:
                    print(f"\n{args.name} 板块资金流向数据 ({len(df)}条):")
                else:
                    type_str = args.type if args.type else "所有"
                    print(f"\n{type_str}板块资金流向数据 ({len(df)}条):")
                # 选择关键字段显示
                display_cols = ['trade_date', 'content_type', 'sector_name', 'change_pct', 
                               'net_amount', 'inflow_rate', 'rank']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到板块资金流向数据")
        
        elif args.command == 'sector-stats':
            stats = reader.get_sector_money_flow_stats(args.name, args.type)
            if not stats:
                print("\n未找到板块资金流向数据")
            elif args.name:
                # 单个板块统计
                print(f"\n=== {args.name} 板块资金流向统计 ===")
                print(f"数据记录数: {stats['count']}条")
                if stats['first_date']:
                    print(f"首次记录: {stats['first_date']}")
                    print(f"最近记录: {stats['last_date']}")
                if stats['avg_net_amount']:
                    print(f"平均净流入: {stats['avg_net_amount']/10000:.2f}万元")
                if stats['total_net_amount']:
                    print(f"累计净流入: {stats['total_net_amount']/10000:.2f}万元")
            else:
                # 全市场统计
                print("\n=== 板块资金流向全市场统计 ===")
                print(f"总记录数: {stats['total_records']:,}条")
                if stats['date_range']['start']:
                    print(f"数据日期范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
                
                if 'type_counts' in stats:
                    print(f"\n各类型记录数:")
                    for content_type, count in stats['type_counts'].items():
                        print(f"  {content_type}板块: {count:,}条")
                
                if 'top_industry_inflow' in stats and stats['top_industry_inflow']:
                    print(f"\n最新行业板块净流入前10名 ({stats['latest_date']}):")
                    for i, sector in enumerate(stats['top_industry_inflow'], 1):
                        net_str = f"{sector['net_amount']/10000:.2f}万元" if sector['net_amount'] is not None else "N/A"
                        pct_str = f"{sector['change_pct']:+.2f}%" if sector['change_pct'] is not None else "N/A"
                        print(f"  {i}. {sector['sector_name']}: 净流入{net_str} (涨跌{pct_str})")
                
                if 'top_concept_inflow' in stats and stats['top_concept_inflow']:
                    print(f"\n最新概念板块净流入前10名 ({stats['latest_date']}):")
                    for i, sector in enumerate(stats['top_concept_inflow'], 1):
                        net_str = f"{sector['net_amount']/10000:.2f}万元" if sector['net_amount'] is not None else "N/A"
                        pct_str = f"{sector['change_pct']:+.2f}%" if sector['change_pct'] is not None else "N/A"
                        print(f"  {i}. {sector['sector_name']}: 净流入{net_str} (涨跌{pct_str})")
        
        elif args.command == 'sector-top':
            df = reader.get_sector_money_flow_top(args.date, args.top, args.type, args.flow)
            if not df.empty:
                flow_name = {'inflow': '净流入', 'outflow': '净流出'}[args.flow]
                date_str = df['trade_date'].iloc[0] if not df.empty else args.date
                print(f"\n{args.type}板块{flow_name}排行 (前{args.top}名) - {date_str}:")
                # 选择关键字段显示
                display_cols = ['rank', 'sector_name', 'change_pct', 'net_amount', 
                               'inflow_rate', 'inflow', 'amount']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n未找到板块资金流向数据")
        
        elif args.command == 'ztbbk':
            df = reader.get_ztb_sector_data(args.name, args.start, args.end)
            if not df.empty:
                print(f"\n涨停板板块统计数据 ({len(df)}条记录):")
                # 选择关键字段显示
                display_cols = ['trade_date', 'sector_name', 'up_nums', 'cons_nums', 
                               'pct_chg', 'up_stat', 'rank', 'days']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n无数据")
        
        elif args.command == 'ztbbk-stats':
            stats = reader.get_ztb_sector_stats(args.name)
            if stats:
                print("\n=== 涨停板板块统计信息 ===")
                if args.name:
                    print(f"板块名称: {args.name}")
                    print(f"记录数量: {stats.get('record_count', 0)}")
                    print(f"日期范围: {stats.get('first_date', 'N/A')} 到 {stats.get('last_date', 'N/A')}")
                    print(f"平均涨停家数: {stats.get('avg_up_nums', 0):.1f}")
                    print(f"最大涨停家数: {stats.get('max_up_nums', 0)}")
                else:
                    print(f"总记录数: {stats.get('total_records', 0):,}")
                    if 'date_range' in stats:
                        print(f"日期范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
                    
                    if 'top_sectors' in stats and stats['top_sectors']:
                        print(f"\n最强板块排名 ({stats.get('latest_date')}, TOP10):")
                        print(f"{'排名':<6} {'板块名称':<20} {'涨停家数':<10} {'连板家数':<10} {'涨跌幅%':<10} {'连板高度':<15}")
                        print("-" * 85)
                        for s in stats['top_sectors']:
                            pct_str = f"{s['pct_chg']:.2f}" if s['pct_chg'] is not None else "N/A"
                            up_stat_str = s['up_stat'] if s['up_stat'] else "N/A"
                            print(f"{s['rank']:<6} {s['sector_name']:<20} {s['up_nums']:<10} {s['cons_nums']:<10} {pct_str:<10} {up_stat_str:<15}")
            else:
                print("\n无数据")
        
        elif args.command == 'ztbbk-top':
            df = reader.get_ztb_sector_top(args.date, args.top)
            if not df.empty:
                date_str = df['trade_date'].iloc[0] if not df.empty else args.date
                print(f"\n涨停板板块排行榜 (前{args.top}名) - {date_str}:")
                # 选择关键字段显示
                display_cols = ['rank', 'sector_name', 'up_nums', 'cons_nums', 
                               'pct_chg', 'up_stat', 'days']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].to_string(index=False))
            else:
                print("\n无数据")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
