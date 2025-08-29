"""
from config.i18n import t_gui as _
Excel数据加载器 - 增强版数据加载和验证

功能特性：
1. 多种数据格式支持 (*.json.gz)
2. 自动文件日期检测
3. 数据结构验证
4. 8级评级系统支持
5. 智能编码检测（CSV文件）
6. 错误处理和日志记录

基于：xlsx_analyzer.py 功能扩展
作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime
import os
import logging
from pathlib import Path

# 导入配置
try:
    from config import RATING_SCORE_MAP, MARKET_CONFIG
except ImportError:
    # 默认配置
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }
    MARKET_CONFIG = {'CN': {'name': '中国A股'}}

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelDataLoader:
    """增强的数据加载器 - 支持Excel和CSV格式"""
    
    def __init__(self, file_path: str):
        """
        初始化加载器
        
        参数:
            file_path (str): Excel文件路径
        """
        self.file_path = file_path
        self.data = None
        self.validation_result = {}
        self.file_info = {}
        self.load_time = None
        
    def load_and_validate(self) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        加载并验证数据
        
        返回:
            tuple: (DataFrame对象, 验证结果字典)
        """
        load_start = datetime.now()
        
        try:
            logger.info(f"开始加载Excel文件: {self.file_path}")
            
            # 1. 文件检查
            file_check = self._check_file()
            if not file_check['is_valid']:
                return None, file_check
            
            # 2. 加载数据
            self.data = self._load_excel_data()
            if self.data is None:
                return None, {'is_valid': False, 'error': 'Excel文件加载失败'}
            
            # 3. 数据验证
            self.validation_result = self._validate_data_structure()
            
            # 4. 数据清洗
            if self.validation_result['is_valid']:
                self.data = self._clean_data()
            
            # 5. 记录加载时间
            self.load_time = (datetime.now() - load_start).total_seconds()
            self.validation_result['load_time'] = f"{self.load_time:.2f}s"
            self.validation_result['file_info'] = self.file_info
            
            logger.info(f"数据加载完成: {self.data.shape if self.data is not None else 'Failed'}")
            
            return self.data, self.validation_result
            
        except Exception as e:
            error_msg = f"数据加载异常: {str(e)}"
            logger.error(error_msg)
            return None, {'is_valid': False, 'error': error_msg}
    
    def detect_file_date(self) -> str:
        """
        从文件名自动检测数据日期
        
        返回:
            str: 检测到的日期 (YYYYMMDD格式)
        """
        filename = os.path.basename(self.file_path)
        
        # 匹配YYYYMMDD格式
        date_pattern = r'20\d{6}'
        match = re.search(date_pattern, filename)
        
        if match:
            return match.group()
        
        # 如果文件名中没有日期，尝试从修改时间获取
        try:
            file_mtime = os.path.getmtime(self.file_path)
            file_date = datetime.fromtimestamp(file_mtime)
            return file_date.strftime('%Y%m%d')
        except:
            return datetime.now().strftime('%Y%m%d')
    
    def get_data_summary(self) -> Dict:
        """
        获取数据概览
        
        返回:
            dict: 数据概览信息
        """
        if self.data is None:
            return {}
        
        date_columns = [col for col in self.data.columns if str(col).startswith('202')]
        
        # 评级分布统计
        rating_stats = {}
        if date_columns:
            latest_col = max(date_columns)
            rating_dist = self.data[latest_col].value_counts()
            total_rated = sum(count for rating, count in rating_dist.items() if rating != '-')
            
            for rating, count in rating_dist.items():
                percentage = count / len(self.data) * 100
                rating_stats[rating] = {
                    'count': count,
                    'percentage': round(percentage, 1)
                }
        
        # 行业分布
        industry_stats = {}
        if '行业' in self.data.columns:
            industry_dist = self.data['行业'].value_counts()
            for industry, count in industry_dist.head(10).items():
                percentage = count / len(self.data) * 100
                industry_stats[industry] = {
                    'count': count,
                    'percentage': round(percentage, 1)
                }
        
        return {
            'total_stocks': len(self.data),
            'total_columns': len(self.data.columns),
            'date_range': f"{min(date_columns)} ~ {max(date_columns)}" if date_columns else "无",
            'trading_days': len(date_columns),
            'industry_coverage': self.data['行业'].notna().sum() / len(self.data) * 100 if '行业' in self.data.columns else 0,
            'latest_rating_stats': rating_stats,
            'top_industries': industry_stats,
            'file_date': self.detect_file_date(),
            'load_time': self.load_time
        }
    
    # 私有方法
    
    def _check_file(self) -> Dict:
        """检查文件是否存在和可读"""
        if not os.path.exists(self.file_path):
            return {'is_valid': False, 'error': f'文件不存在: {self.file_path}'}
        
        if not os.path.isfile(self.file_path):
            return {'is_valid': False, 'error': f'不是有效文件: {self.file_path}'}
        
        # 检查文件扩展名
        _, ext = os.path.splitext(self.file_path)
        if ext.lower() not in ['.xlsx', '.xls', '.csv']:
            return {'is_valid': False, 'error': f'不支持的文件格式: {ext}'}
        
        # 获取文件信息
        file_stat = os.stat(self.file_path)
        self.file_info = {
            'file_name': os.path.basename(self.file_path),
            'file_size': file_stat.st_size,
            'file_size_mb': round(file_stat.st_size / 1024 / 1024, 2),
            'modified_time': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'detected_date': self.detect_file_date()
        }
        
        return {'is_valid': True}
    
    def _load_excel_data(self) -> Optional[pd.DataFrame]:
        """加载Excel或CSV数据"""
        try:
            # 检查文件扩展名
            _, ext = os.path.splitext(self.file_path)
            
            if ext.lower() == '.csv':
                # 加载CSV文件
                try:
                    # 尝试不同的编码
                    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']
                    for encoding in encodings:
                        try:
                            df = pd.read_csv(self.file_path, encoding=encoding)
                            logger.info(f"使用编码 {encoding} 成功加载CSV数据")
                            return df
                        except UnicodeDecodeError:
                            continue
                    
                    # 如果所有编码都失败，尝试默认方式
                    df = pd.read_csv(self.file_path)
                    logger.info("使用默认编码成功加载CSV数据")
                    return df
                    
                except Exception as e:
                    logger.error(f"CSV加载失败: {e}")
                    return None
            else:
                # 加载Excel文件
                # 尝试不同的引擎
                engines = ['openpyxl', 'xlrd']
                
                for engine in engines:
                    try:
                        df = pd.read_excel(self.file_path, engine=engine)
                        logger.info(f"使用引擎 {engine} 成功加载Excel数据")
                        return df
                    except Exception as e:
                        logger.warning(f"引擎 {engine} 加载失败: {e}")
                        continue
                
                # 如果所有引擎都失败，尝试默认方式
                return pd.read_excel(self.file_path)
            
        except Exception as e:
            logger.error(f"数据加载失败: {e}")
            return None
    
    def _validate_data_structure(self) -> Dict:
        """验证数据结构"""
        if self.data is None:
            return {'is_valid': False, 'error': '数据为空'}
        
        validation = {
            'is_valid': True,
            'missing_columns': [],
            'warnings': [],
            'data_quality': {}
        }
        
        # 检查必需列
        required_columns = ['行业', '股票代码', '股票名称']
        for col in required_columns:
            if col not in self.data.columns:
                validation['missing_columns'].append(col)
                validation['is_valid'] = False
        
        # 检查日期列
        date_columns = [col for col in self.data.columns if str(col).startswith('202')]
        
        if len(date_columns) == 0:
            validation['warnings'].append('未找到日期列')
            validation['is_valid'] = False
        elif len(date_columns) < 5:
            validation['warnings'].append('日期列过少，可能影响趋势分析准确性')
        
        # 数据质量检查
        if validation['is_valid']:
            validation['data_quality'] = {
                'total_rows': len(self.data),
                'total_columns': len(self.data.columns),
                'date_columns_count': len(date_columns),
                'date_range': f"{min(date_columns)} ~ {max(date_columns)}" if date_columns else "无",
                'industry_coverage': self.data['行业'].notna().sum() / len(self.data) * 100,
                'duplicate_codes': self.data['股票代码'].duplicated().sum(),
                'duplicate_names': self.data['股票名称'].duplicated().sum()
            }
            
            # 检查评级有效性
            rating_check = self._check_rating_validity(date_columns)
            validation['data_quality']['rating_validity'] = rating_check
        
        return validation
    
    def _check_rating_validity(self, date_columns: List[str]) -> Dict:
        """检查评级数据有效性"""
        valid_ratings = set(RATING_SCORE_MAP.keys())
        invalid_ratings = {}
        
        for col in date_columns[:5]:  # 检查前5列
            unique_ratings = set(self.data[col].dropna().unique())
            invalid = unique_ratings - valid_ratings
            if invalid:
                invalid_ratings[col] = list(invalid)
        
        total_ratings = 0
        valid_rating_count = 0
        
        for col in date_columns:
            col_ratings = self.data[col].dropna()
            total_ratings += len(col_ratings)
            valid_rating_count += col_ratings.isin(valid_ratings).sum()
        
        validity_rate = valid_rating_count / total_ratings * 100 if total_ratings > 0 else 0
        
        return {
            'validity_rate': round(validity_rate, 2),
            'total_ratings': total_ratings,
            'valid_ratings': valid_rating_count,
            'invalid_ratings': invalid_ratings
        }
    
    def _detect_market_type(self) -> str:
        """检测数据文件的市场类型"""
        if not self.file_path:
            return 'cn'  # 默认中国市场
        
        file_name = Path(self.file_path).name.lower()
        
        # 根据文件名前缀判断市场类型
        if file_name.startswith('us'):
            return 'us'
        elif file_name.startswith('hk'):
            return 'hk'
        elif file_name.startswith('cn'):
            return 'cn'
        else:
            # 根据文件名关键词判断
            if 'us' in file_name or 'america' in file_name or 'usa' in file_name:
                return 'us'
            elif 'hk' in file_name or 'hongkong' in file_name or 'hong' in file_name:
                return 'hk'
            elif 'cn' in file_name or 'china' in file_name:
                return 'cn'
            else:
                # 检查股票代码格式来推断市场类型
                if self.data is not None and '股票代码' in self.data.columns:
                    sample_codes = self.data['股票代码'].head(10).astype(str)
                    # 如果大部分代码包含字母，可能是US市场
                    alpha_count = sum(1 for code in sample_codes if any(c.isalpha() for c in str(code)))
                    if alpha_count > len(sample_codes) * 0.7:  # 70%以上包含字母
                        return 'us'
                
                logger.info(f"无法从文件名识别市场类型: {file_name}，默认使用CN市场")
                return 'cn'
    
    def _clean_data(self) -> pd.DataFrame:
        """数据清洗"""
        df = self.data.copy()
        
        # 检测市场类型
        market_type = self._detect_market_type()
        logger.info(f"检测到市场类型: {market_type.upper()}")
        
        # 1. 股票代码标准化 - 根据市场类型处理
        if '股票代码' in df.columns:
            if market_type == 'us':
                # US市场保持原始代码格式（字母代码如AAPL, MSFT）
                df['股票代码'] = df['股票代码'].astype(str).str.strip().str.upper()
                logger.info("US市场: 保持原始股票代码格式")
            else:
                # CN/HK市场使用6位数字填充
                df['股票代码'] = df['股票代码'].astype(str).str.zfill(6)
                logger.info(f"{market_type.upper()}市场: 使用6位数字填充格式")
        
        # 2. 行业信息处理
        if '行业' in df.columns:
            df['行业'] = df['行业'].fillna('未分类')
            # 去除空白字符
            df['行业'] = df['行业'].astype(str).str.strip()
        
        # 3. 股票名称处理
        if '股票名称' in df.columns:
            df['股票名称'] = df['股票名称'].astype(str).str.strip()
        
        # 4. 评级数据处理 - 确保符合8级评级系统
        date_columns = [col for col in df.columns if str(col).startswith('202')]
        for col in date_columns:
            # 将无效评级替换为'-'
            valid_ratings = set(RATING_SCORE_MAP.keys())
            mask = ~df[col].isin(valid_ratings)
            df.loc[mask, col] = '-'
        
        logger.info(f"数据清洗完成: {len(df)} 行数据")
        return df


# 便捷函数

def load_stock_data(file_path: str, auto_clean: bool = True) -> Tuple[Optional[pd.DataFrame], Dict]:
    """
    便捷函数：加载股票数据
    
    参数:
        file_path (str): Excel文件路径
        auto_clean (bool): 是否自动清洗数据
        
    返回:
        tuple: (DataFrame, 加载结果)
    """
    loader = ExcelDataLoader(file_path)
    return loader.load_and_validate()


def detect_market_region(data: pd.DataFrame) -> str:
    """
    检测市场地区
    
    参数:
        data (pd.DataFrame): 股票数据
        
    返回:
        str: 市场地区代码 (CN/HK/US)
    """
    if '股票代码' not in data.columns:
        return 'CN'  # 默认A股
    
    codes = data['股票代码'].astype(str).tolist()
    
    # 检查港股特征
    hk_pattern = re.compile(r'^\d{5}$|\.HK$')
    hk_count = sum(1 for code in codes if hk_pattern.match(code))
    
    # 检查美股特征
    us_pattern = re.compile(r'^[A-Z]{1,5}$')
    us_count = sum(1 for code in codes if us_pattern.match(code))
    
    # 检查A股特征
    cn_pattern = re.compile(r'^\d{6}$')
    cn_count = sum(1 for code in codes if cn_pattern.match(code))
    
    # 返回占比最高的市场
    total = len(codes)
    if cn_count / total > 0.7:
        return 'CN'
    elif hk_count / total > 0.7:
        return 'HK'
    elif us_count / total > 0.7:
        return 'US'
    else:
        return 'CN'  # 默认A股


# 测试函数
def test_excel_loader():
    """测试Excel加载器"""
    print("Excel...")
    
    test_file = "CN_Data.json.gz"
    if not os.path.exists(test_file):
        print(f"   警告 测试文件不存在: {test_file}")
        return False
    
    # 测试加载
    loader = ExcelDataLoader(test_file)
    data, result = loader.load_and_validate()
    
    if result.get('is_valid', False):
        print(f"   成功 加载成功: {data.shape}")
        print(f"   数据 数据概览: {loader.get_data_summary()}")
        
        # 测试市场检测
        region = detect_market_region(data)
        print(f"   🌏 检测市场: {region}")
        
    else:
        print(f"   错误 加载失败: {result.get('error', '未知错误')}")
        return False
    
    print("Excel")
    return True


if __name__ == "__main__":
    test_excel_loader()