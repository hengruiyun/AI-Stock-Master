#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于lj_read.py的量价数据获取器
替代ljs.py，使用.gz压缩数据文件

功能：
1. 使用lj_read.py的StockDataReaderV2读取.gz数据文件
2. 提供与原ljs.py兼容的接口
3. 支持多市场数据获取
4. 缓存和错误处理

作者：AI Assistant
版本：2.0.0
"""

import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入lj_read模块
try:
    # 尝试从当前目录导入
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # 检查是否在打包环境中
    if getattr(sys, 'frozen', False):
        # 打包环境：从sys._MEIPASS或sys.executable目录查找
        import importlib.util
        from pathlib import Path
        
        # 尝试多个可能的路径
        possible_paths = [
            Path(sys._MEIPASS) / "lj_read.py",  # PyInstaller临时目录
            Path(sys.executable).parent / "lj_read.py",  # EXE同级目录
        ]
        
        StockDataReaderV2 = None
        for lj_read_path in possible_paths:
            if lj_read_path.exists():
                try:
                    spec = importlib.util.spec_from_file_location("lj_read", str(lj_read_path))
                    if spec and spec.loader:
                        lj_read_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(lj_read_module)
                        StockDataReaderV2 = lj_read_module.StockDataReaderV2
                        print(f"✅ 成功从打包环境加载lj_read模块: {lj_read_path}")
                        break
                except Exception as e:
                    print(f"⚠️ 从 {lj_read_path} 加载失败: {e}")
                    continue
        
        if not StockDataReaderV2:
            print("警告: 打包环境中无法导入lj_read模块，将使用备用实现")
    else:
        # 开发环境：使用原有逻辑
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        # 尝试多种导入方式
        StockDataReaderV2 = None
        try:
            import lj_read
            StockDataReaderV2 = lj_read.StockDataReaderV2
        except ImportError as ie:
            print(f"调试: 直接导入lj_read失败: {ie}")
            try:
                import importlib.util
                module_path = os.path.join(project_root, "lj_read.py")
                spec = importlib.util.spec_from_file_location("lj_read", module_path)
                if spec and spec.loader:
                    lj_read_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(lj_read_module)
                    StockDataReaderV2 = lj_read_module.StockDataReaderV2
                print(f"✅ 通过spec加载lj_read模块: {module_path}")
            except Exception as ex:
                print(f"调试: 通过spec导入lj_read时发生异常: {ex}")
        
        if not StockDataReaderV2:
            print("警告: 无法导入lj_read模块，将使用备用实现")
            print(f"调试信息: project_root={project_root}, 当前目录={os.getcwd()}")
            print(f"lj_read.py存在: {os.path.exists(os.path.join(project_root, 'lj_read.py'))}")
            print(f"lj_read.py路径: {os.path.join(project_root, 'lj_read.py')}")
        
except Exception as e:
    print(f"导入lj_read模块时出错: {e}")
    StockDataReaderV2 = None

class LJDataReader:
    """基于lj_read.py的数据读取器"""
    
    def __init__(self, verbose: bool = False):
        """
        初始化数据读取器
        
        Args:
            verbose: 是否显示详细日志
        """
        self.verbose = verbose
        self.readers = {}  # 缓存不同市场的读取器
        self.use_ljs_for_markets = set()  # 需要使用ljs.py的市场
        self.ljs_readers = {}  # ljs.py读取器缓存
        
        # 数据文件映射 - 优先使用.dat.gz文件（已修复编码问题）
        self.data_files = {
            'cn': 'cn-lj.dat.gz',
            'hk': 'hk-lj.dat.gz', 
            'us': 'us-lj.dat.gz'
        }
        
        # 备用数据文件映射（如果.gz文件不存在则使用.dat文件）
        self.fallback_data_files = {
            'cn': 'cn-lj.dat',
            'hk': 'hk-lj.dat', 
            'us': 'us-lj.dat'
        }
        
        # 检查数据文件可用性并确定使用的文件
        self._determine_data_files()
        
        # 检查StockDataReaderV2是否可用，如果不可用或数据格式不兼容则使用备用实现
        if not StockDataReaderV2:
            print("警告: lj_read模块不可用，使用备用实现")
            self.use_fallback = True
        else:
            # 测试是否能读取数据文件（不显示具体文件名，避免误导）
            try:
                test_file = self.data_files['cn']
                if os.path.exists(test_file):
                    test_reader = StockDataReaderV2(test_file)
                    self.use_fallback = False
                    print(f"✅ lj_read.py数据读取器初始化成功")
                else:
                    self.use_fallback = True
                    print("⚠️ 数据文件不存在，使用备用实现")
            except Exception as e:
                print(f"⚠️ lj_read.py与数据格式不兼容({e})，使用备用实现")
                print(f"调试: 测试文件路径: {test_file}")
                print(f"调试: 测试文件存在: {os.path.exists(test_file)}")
                import traceback
                traceback.print_exc()
                self.use_fallback = True
    
    def _determine_data_files(self):
        """确定要使用的数据文件（只处理.gz文件，.dat文件交给ljs.py）"""
        # 优先从EXE目录查找数据文件
        from pathlib import Path
        try:
            from utils.path_helper import get_data_file_path
        except ImportError:
            # 如果path_helper不可用，回退到原方式
            def get_data_file_path(filename):
                return Path(filename)
        
        for market in self.data_files:
            gz_file = str(get_data_file_path(self.data_files[market]))
            dat_file = str(get_data_file_path(self.fallback_data_files[market]))
            
            # 更新映射为绝对路径
            self.data_files[market] = gz_file
            self.fallback_data_files[market] = dat_file
            
            if os.path.exists(gz_file):
                # .gz文件存在，使用lj_data_reader处理
                if self.verbose:
                    print(f"✅ 使用{market.upper()}市场.gz数据文件: {gz_file}")
            elif os.path.exists(dat_file):
                # .gz文件不存在但.dat文件存在，标记使用ljs.py处理
                self.use_ljs_for_markets.add(market)
                if self.verbose:
                    print(f"⚠️ .gz文件不存在，{market.upper()}市场.dat文件将由ljs.py处理: {dat_file}")
            else:
                # 两个文件都不存在
                if self.verbose:
                    print(f"❌ {market.upper()}市场数据文件都不存在: {gz_file}, {dat_file}")
        
        # 初始化ljs.py实例（如果需要的话）
        if self.use_ljs_for_markets:
            self._init_ljs_readers()
    
    def _init_ljs_readers(self):
        """初始化ljs.py读取器"""
        try:
            # 导入ljs模块
            from ljs import StockSearchTool
            self.ljs_readers = {}
            
            for market in self.use_ljs_for_markets:
                dat_file = self.fallback_data_files[market]
                if os.path.exists(dat_file):
                    # 为每个市场创建StockSearchTool实例
                    self.ljs_readers[market] = StockSearchTool(
                        verbose=self.verbose, 
                        data_file_name=dat_file
                    )
                    if self.verbose:
                        print(f"✅ 初始化{market.upper()}市场ljs.py读取器: {dat_file}")
                        
        except ImportError as e:
            print(f"❌ 无法导入ljs模块: {e}")
            self.ljs_readers = {}
        except Exception as e:
            print(f"❌ 初始化ljs.py读取器失败: {e}")
            self.ljs_readers = {}
    
    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        if self.verbose:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {level}: {message}")
    
    def _get_reader(self, market: str):
        """获取指定市场的数据读取器"""
        if market not in self.data_files and market not in self.use_ljs_for_markets:
            self.log(f"不支持的市场类型: {market}", "ERROR")
            return None
        
        # 如果该市场需要使用ljs.py处理
        if hasattr(self, 'use_ljs_for_markets') and market in self.use_ljs_for_markets:
            if hasattr(self, 'ljs_readers') and market in self.ljs_readers:
                return self.ljs_readers[market]
            else:
                self.log(f"ljs.py读取器未初始化: {market}", "ERROR")
                return None
        
        # 检查缓存
        if market in self.readers:
            return self.readers[market]
        
        # 检查.gz数据文件是否存在
        data_file = self.data_files[market]
        if not os.path.exists(data_file):
            self.log(f"数据文件不存在: {data_file}", "ERROR")
            return None
        
        try:
            if self.use_fallback:
                # 使用备用实现：直接使用ljs.py
                from ljs import StockSearchTool
                reader = StockSearchTool(verbose=self.verbose)
                self.readers[market] = reader
                self.log(f"成功加载{market.upper()}市场数据(备用): {data_file}")
                return reader
            else:
                # 使用lj_read.py，为每个市场创建独立的读取器
                reader = StockDataReaderV2(data_file)
                reader.data_file = data_file  # 记录数据文件路径
                self.readers[market] = reader
                print(f"使用lj_read.py数据读取器，数据文件: {os.path.basename(data_file)}")
                self.log(f"成功加载{market.upper()}市场数据: {data_file}")
                return reader
            
        except Exception as e:
            self.log(f"加载{market.upper()}市场数据失败: {e}", "ERROR")
            return None
    
    def search_stock_by_code(self, stock_code: str, market: str, days: int = None) -> Dict[str, Any]:
        """
        根据股票代码搜索数据 - 兼容ljs.py接口
        
        Args:
            stock_code: 股票代码
            market: 市场类型 ('cn', 'hk', 'us')
            days: 获取天数
            
        Returns:
            与ljs.py兼容的数据格式
        """
        results = {}
        
        # 验证市场参数
        if not market:
            raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
        
        market = market.lower()
        if market not in self.data_files and market not in self.use_ljs_for_markets:
            raise ValueError(f"不支持的市场类型: {market}，支持的市场: {list(self.data_files.keys())}")
        
        # 获取读取器
        reader = self._get_reader(market)
        if not reader:
            return results
        
        try:
            # 清理股票代码
            clean_code = self._clean_stock_code(stock_code)
            
            # 检查是否需要使用ljs.py处理该市场
            if hasattr(self, 'use_ljs_for_markets') and market in self.use_ljs_for_markets:
                # 使用ljs.py处理.dat文件
                results = reader.search_stock_by_code(clean_code, market, days)
                self.log(f"成功获取股票 {stock_code} 的数据（ljs.py处理.dat文件）")
                return results
            elif self.use_fallback:
                # 使用ljs.py备用实现
                results = reader.search_stock_by_code(clean_code, market, days)
                self.log(f"成功获取股票 {stock_code} 的数据（备用实现）")
                return results
            else:
                # 使用lj_read.py实现
                # 计算日期范围 - 获取最新的几天数据
                end_date = None
                start_date = None
                if days and days > 0:
                    # 不指定具体日期，让数据库返回最新的数据
                    # 我们将在后面限制返回的记录数
                    pass
                
                # 确保使用正确的市场数据文件
                expected_file = self.data_files[market]
                if not os.path.exists(expected_file):
                    self.log(f"市场数据文件不存在: {expected_file}", "ERROR")
                    return None
                
                # 如果当前reader使用的不是正确的市场文件，重新创建reader
                if hasattr(reader, 'data_file') and reader.data_file != expected_file:
                    self.log(f"切换数据文件: {reader.data_file} -> {expected_file}")
                    reader = StockDataReaderV2(expected_file)
                    self.readers[market] = reader
                
                # 获取股票数据
                df = reader.get_stock_data(clean_code, market.upper(), start_date, end_date)
                
                # 调试信息（可选）
                if self.verbose:
                    print(f"DEBUG: 搜索 {clean_code}, 市场 {market.upper()}, 获取到 {df.shape[0]} 条记录")
                
                if df.empty:
                    self.log(f"未找到股票/指数 {stock_code} 的数据", "WARNING")
                    return results
                
                # 如果指定了天数，只取最新的几天数据
                if days and days > 0:
                    df = df.tail(days)
                
                # 获取股票信息
                stock_info_df = reader.search_stocks(clean_code, market.upper())
                stock_name = ""
                if not stock_info_df.empty:
                    stock_name = stock_info_df.iloc[0]['name']
                
                # 转换为ljs.py兼容的格式
                trade_data = {}
                for _, row in df.iterrows():
                    date_str = row['date']
                    trade_data[date_str] = {
                        '开盘价': row['open'] if pd.notna(row['open']) else row['close'],
                        '最高价': row['high'] if pd.notna(row['high']) else row['close'],
                        '最低价': row['low'] if pd.notna(row['low']) else row['close'],
                        '收盘价': row['close'],
                        '成交量': int(row['volume']) if pd.notna(row['volume']) else 0,
                        '成交额': row['amount'] if pd.notna(row['amount']) else 0
                    }
                
                results[market] = {
                    "市场": market.upper(),
                    "股票代码": stock_code,
                    "股票名称": stock_name,
                    "数据": {
                        "交易数据": trade_data,
                        "基本信息": {
                            "股票名称": stock_name,
                            "市场": market.upper()
                        }
                    }
                }
                
                self.log(f"成功获取股票 {stock_code} 的数据，共 {len(trade_data)} 天")
            
        except Exception as e:
            self.log(f"搜索股票 {stock_code} 失败: {e}", "ERROR")
            
        return results
    
    def _clean_stock_code(self, stock_code: str) -> str:
        """清理股票代码格式"""
        if not stock_code:
            return ""
        
        # 移除Excel格式的引号
        if stock_code.startswith('="') and stock_code.endswith('"'):
            return stock_code[2:-1]
        
        # 移除普通引号
        if stock_code.startswith('"') and stock_code.endswith('"'):
            return stock_code[1:-1]
        
        return stock_code.strip()
    
    def _is_likely_index(self, code_or_name: str) -> bool:
        """检测是否可能是指数（基于名称特征）"""
        if not code_or_name:
            return False
        
        # 包含指数关键词
        index_keywords = ['指数', '指標', 'INDEX', 'index', '综指', '成指']
        for keyword in index_keywords:
            if keyword in code_or_name:
                return True
        
        # 常见指数名称
        common_indices = [
            '上证指数', '深证成指', '创业板指', '沪深300', '科创50', '上证50', 
            '中证500', '中证1000', '恒生指数', '恒生科技指数', '恒生国企指数',
            '恒生港股通指数', '中华A80指数', '标普500', '纳斯达克', '道琼斯'
        ]
        
        for index_name in common_indices:
            if code_or_name == index_name or index_name in code_or_name:
                return True
        
        return False
    
    def _get_index_code_mapping(self) -> Dict[str, str]:
        """获取指数名称到代码的映射"""
        return {
            # CN市场指数（基于数据文件中实际存在的指数）
            '上证指数': '000001',
            '深证成指': '399001', 
            '创业板指': '399006',
            '沪深300': '000300',
            '中证500': '000905',
            '上证50': '000016',
            '中小板指': '399005',
            '科创50': '000688',
            '中证800': '000932',
            
            # HK市场指数（基于hk-lj.dat.gz中实际存在的指数）
            '恒生指数': 'HSI',
            '恒生中国企业指数': 'HSCEI',
            '恒生科技指数': 'HSTECH', 
            '中华A80指数': 'CESA80',
            '中华120指数': 'CES120',
            '中华280指数': 'CES280',
            '中华沪深港300': 'CES300',
            
            # US市场指数
            '标普500': 'SPX',
            '纳斯达克': 'IXIC',
            '道琼斯': 'DJI'
        }

    def search_stock_by_name(self, stock_name: str, market: str, days: int = None) -> Dict[str, Any]:
        """
        根据股票/指数名称搜索数据
        
        Args:
            stock_name: 股票或指数名称
            market: 市场类型 ('cn', 'hk', 'us')
            days: 获取天数
            
        Returns:
            与ljs.py兼容的数据格式
        """
        results = {}
        
        # 验证市场参数
        if not market:
            raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
        
        market = market.lower()
        if market not in self.data_files and market not in self.use_ljs_for_markets:
            raise ValueError(f"不支持的市场类型: {market}，支持的市场: {list(self.data_files.keys())}")
        
        # 获取读取器
        reader = self._get_reader(market)
        if not reader:
            return results
        
        try:
            # 首先检查是否为已知指数，使用指数映射
            index_mapping = self._get_index_code_mapping()
            if stock_name in index_mapping:
                index_code = index_mapping[stock_name]
                self.log(f"指数名称映射: {stock_name} -> {index_code}")
                
                # 直接用指数代码获取数据，但指定只获取index类型的数据
                if not self.use_fallback:
                    # 使用lj_read.py直接获取指数数据
                    volume_df = reader.get_stock_data(index_code, market.upper())
                    
                    # 只保留index类型的数据
                    if not volume_df.empty:
                        index_df = volume_df[volume_df['data_type'] == 'index']
                        
                        if not index_df.empty:
                            # 调试信息
                            if self.verbose:
                                print(f"DEBUG: 指数名称搜索 {stock_name}({index_code}), 市场 {market.upper()}, 获取到 {index_df.shape[0]} 条index记录")
                            
                            # 如果指定了天数，只取最新的几天数据
                            if days and days > 0:
                                index_df = index_df.tail(days)
                            
                            # 转换为ljs.py兼容的格式
                            trade_data = {}
                            for _, row in index_df.iterrows():
                                date_str = row['date']
                                trade_data[date_str] = {
                                    '开盘价': row['open'] if pd.notna(row['open']) else row['close'],
                                    '最高价': row['high'] if pd.notna(row['high']) else row['close'],
                                    '最低价': row['low'] if pd.notna(row['low']) else row['close'],
                                    '收盘价': row['close'],
                                    '成交量': int(row['volume']) if pd.notna(row['volume']) else 0,
                                    '成交额': row['amount'] if pd.notna(row['amount']) else 0
                                }
                            
                            results[market] = {
                                "市场": market.upper(),
                                "股票代码": index_code,  # 使用实际的指数代码
                                "股票名称": stock_name,  # 使用用户输入的指数名称
                                "数据": {
                                    "交易数据": trade_data,
                                    "基本信息": {
                                        "股票名称": stock_name,
                                        "市场": market.upper()
                                    }
                                }
                            }
                            
                            self.log(f"成功获取指数 {stock_name} 的数据，共 {len(trade_data)} 天")
                            return results
                
            # 如果不是已知指数，或者指数映射失败，则回退到原有的搜索逻辑
            if hasattr(self, 'use_ljs_for_markets') and market in self.use_ljs_for_markets:
                # 使用ljs.py处理.dat文件
                results = reader.search_stock_by_name(stock_name, market, days)
                self.log(f"成功获取股票 {stock_name} 的数据（ljs.py处理.dat文件）")
                return results
            elif self.use_fallback:
                # 使用ljs.py备用实现
                results = reader.search_stock_by_name(stock_name, market, days)
                self.log(f"成功获取股票 {stock_name} 的数据（备用实现）")
                return results
            else:
                # 使用lj_read.py：通过名称搜索股票列表
                df = reader.search_stocks(stock_name, market.upper())
                
                if df.empty:
                    self.log(f"未找到股票/指数 {stock_name} 的数据", "WARNING")
                    return results
                
                # 找到匹配的股票，使用第一个匹配项的代码
                symbol = df.iloc[0]['symbol']
                stock_name_result = df.iloc[0]['name']
                volume_df = reader.get_stock_data(symbol, market.upper())
                
                # 调试信息（可选）
                if self.verbose:
                    print(f"DEBUG: 股票名称搜索 {stock_name}, 市场 {market.upper()}, 获取到 {volume_df.shape[0]} 条记录")
                
                if volume_df.empty:
                    self.log(f"未找到股票/指数 {stock_name} 的数据", "WARNING")
                    return results
                
                # 如果指定了天数，只取最新的几天数据
                if days and days > 0:
                    volume_df = volume_df.tail(days)
                
                # 转换为ljs.py兼容的格式
                trade_data = {}
                for _, row in volume_df.iterrows():
                    date_str = row['date']
                    trade_data[date_str] = {
                        '开盘价': row['open'] if pd.notna(row['open']) else row['close'],
                        '最高价': row['high'] if pd.notna(row['high']) else row['close'],
                        '最低价': row['low'] if pd.notna(row['low']) else row['close'],
                        '收盘价': row['close'],
                        '成交量': int(row['volume']) if pd.notna(row['volume']) else 0,
                        '成交额': row['amount'] if pd.notna(row['amount']) else 0
                    }
                
                results[market] = {
                    "市场": market.upper(),
                    "股票代码": symbol,
                    "股票名称": stock_name_result,
                    "数据": {
                        "交易数据": trade_data,
                        "基本信息": {
                            "股票名称": stock_name_result,
                            "市场": market.upper()
                        }
                    }
                }
                
                self.log(f"成功获取股票 {stock_name} 的数据，共 {len(trade_data)} 天")
            
        except Exception as e:
            self.log(f"搜索指数 {stock_name} 失败: {e}", "ERROR")
            
        return results
    
    def clean_stock_code(self, stock_code: str) -> str:
        """公开的股票代码清理方法 - 兼容ljs.py接口"""
        return self._clean_stock_code(stock_code)
    
    def get_volume_price_data(self, stock_code: str, days: int = 38, market: str = None) -> Optional[Dict[str, Any]]:
        """
        获取量价数据 - 兼容EnhancedStockChartGenerator接口
        
        Args:
            stock_code: 股票代码或名称
            days: 获取天数
            market: 市场类型
            
        Returns:
            格式化的量价数据
        """
        if not market:
            raise ValueError("必须指定市场参数: 'cn', 'hk', 或 'us'")
        
        try:
            # 检查是否为指数名称，如果是则使用名称搜索
            index_mapping = self._get_index_code_mapping()
            if stock_code in index_mapping:
                # 是指数名称，使用名称搜索
                results = self.search_stock_by_name(stock_code, market, days)
            else:
                # 不是指数名称，使用代码搜索
                results = self.search_stock_by_code(stock_code, market, days)
            
            if not results:
                return None
            
            # 获取第一个市场的数据
            first_market_data = list(results.values())[0]
            data = first_market_data.get('数据', {})
            trade_data = data.get('交易数据', {})
            
            if not trade_data:
                return None
            
            # 转换为图表生成器需要的格式
            formatted_data = []
            for date_str, day_data in sorted(trade_data.items()):
                formatted_data.append({
                    'date': date_str,
                    'open_price': day_data.get('开盘价', 0),
                    'high_price': day_data.get('最高价', 0),
                    'low_price': day_data.get('最低价', 0),
                    'close_price': day_data.get('收盘价', 0),
                    'volume': day_data.get('成交量', 0),  # 成交量
                    'amount': day_data.get('成交额', 0)   # 成交金额
                })
            
            return {
                'stock_code': first_market_data['股票代码'],
                'stock_name': first_market_data['股票名称'],
                'market': market.upper(),
                'total_days': len(formatted_data),
                'data': formatted_data
            }
            
        except Exception as e:
            self.log(f"获取量价数据失败: {stock_code} - {e}", "ERROR")
            return None
    
    def get_stock_list(self, market: str = None) -> List[Dict[str, str]]:
        """
        获取股票列表
        
        Args:
            market: 市场类型，None表示所有市场
            
        Returns:
            股票列表
        """
        stock_list = []
        
        markets_to_check = [market] if market else ['cn', 'hk', 'us']
        
        for mkt in markets_to_check:
            reader = self._get_reader(mkt)
            if not reader:
                continue
                
            try:
                df = reader.get_stocks_only(mkt.upper())
                for _, row in df.iterrows():
                    stock_list.append({
                        'code': row['symbol'],
                        'name': row['name'],
                        'market': row['market'],
                        'industry': row.get('industry', '')
                    })
            except Exception as e:
                self.log(f"获取{mkt.upper()}市场股票列表失败: {e}", "ERROR")
        
        return stock_list
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        stats = {
            'markets': {},
            'total_stocks': 0,
            'total_records': 0
        }
        
        for market in ['cn', 'hk', 'us']:
            reader = self._get_reader(market)
            if reader:
                try:
                    market_stats = reader.get_statistics()
                    stats['markets'][market] = market_stats
                    if 'total_stocks' in market_stats:
                        stats['total_stocks'] += market_stats['total_stocks']
                    if 'total_records' in market_stats:
                        stats['total_records'] += market_stats['total_records']
                except Exception as e:
                    self.log(f"获取{market.upper()}市场统计失败: {e}", "ERROR")
        
        return stats

# 为了兼容性，创建一个StockSearchTool别名
class StockSearchTool(LJDataReader):
    """兼容ljs.py的StockSearchTool接口"""
    
    def __init__(self, verbose: bool = True, data_file_name: str = None):
        super().__init__(verbose=verbose)
        # data_file_name参数保留兼容性，但不使用
        
    def load_market_data(self, market: str) -> bool:
        """加载市场数据 - 兼容接口"""
        reader = self._get_reader(market)
        return reader is not None

def main():
    """测试函数"""
    print("测试LJ数据读取器...")
    
    try:
        reader = LJDataReader(verbose=True)
        
        # 测试获取股票数据
        print("\n=== 测试股票数据获取 ===")
        results = reader.search_stock_by_code("000001", "cn", 5)
        if results:
            print(f"成功获取数据: {results}")
        else:
            print("未获取到数据")
        
        # 测试量价数据
        print("\n=== 测试量价数据 ===")
        volume_data = reader.get_volume_price_data("000001", 5, "cn")
        if volume_data:
            print(f"量价数据: {len(volume_data['data'])} 天")
        else:
            print("未获取到量价数据")
        
        # 测试统计信息
        print("\n=== 测试统计信息 ===")
        stats = reader.get_statistics()
        print(f"统计信息: {stats}")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()
