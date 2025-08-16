"""
from config.i18n import t_gui as _
股票数据集 - 统一数据接口

功能特性：
1. 标准化数据访问接口
2. 缓存机制提升查询性能
3. 数据变换和计算支持
4. 与现有模块无缝集成

作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import warnings

# 导入其他模块
try:
    from config import RATING_SCORE_MAP, MARKET_CONFIG
    from industry_lookup import get_industry_stocks, get_stock_industry
except ImportError:
    # 默认配置
    RATING_SCORE_MAP = {
        '大多': 7, '中多': 6, '小多': 5, '微多': 4,
        '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
        '-': None
    }
    MARKET_CONFIG = {'CN': {'name': '中国A股'}}
    
    def get_industry_stocks(industry): return []
    def get_stock_industry(code): return "未分类"


class StockDataSet:
    """
    股票数据集统一接口
    
    提供标准化的数据访问、查询和计算功能
    """
    
    def __init__(self, data_source, file_path: str = ""):
        """
        初始化数据集
        
        参数:
            data_source: 股票数据(pd.DataFrame)或文件路径(str)
            file_path (str): 数据文件路径(当data_source为DataFrame时使用)
        """
        # 支持从文件路径直接创建
        if isinstance(data_source, str):
            from .excel_loader import ExcelDataLoader
            loader = ExcelDataLoader(data_source)
            loaded_data, validation = loader.load_and_validate()
            if not validation.get('is_valid', False):
                raise ValueError(f"无法加载数据文件: {validation.get('error', '未知错误')}")
            self.data = loaded_data
            self.file_path = data_source
        else:
            self.data = data_source.copy()
            self.file_path = file_path
        
        self._cache = {}
        self._metadata = {}
        
        # 初始化元数据 - 动态计算
        self._initialize_metadata()
        
        # 创建评级分数数据
        self._create_rating_scores()
    
    def _initialize_metadata(self):
        """初始化数据集元数据"""
        # 检测日期列 - 支持多种格式
        date_columns = []
        for col in self.data.columns:
            col_str = str(col)
            # 检测各种日期格式：202X年份开头、MMDD格式等
            if (col_str.startswith('202') or  # 2023、2024等
                (len(col_str) == 4 and col_str.isdigit()) or  # 0410等4位数字
                col_str.replace('.', '').replace('-', '').replace('/', '').isdigit()):
                date_columns.append(col)
        
        self._metadata = {
            'total_stocks': len(self.data),
            'date_columns': sorted(date_columns),
            'date_range': (min(date_columns), max(date_columns)) if date_columns else (None, None),
            'trading_days': len(date_columns),
            'industries': self.data['行业'].unique().tolist() if '行业' in self.data.columns else [],
            'has_industry_data': '行业' in self.data.columns,
            'has_rating_data': len(date_columns) > 0,
            'last_update': datetime.now()
        }
    
    def _create_rating_scores(self):
        """创建评级分数数据"""
        if not self._metadata['has_rating_data']:
            return
        
        # 创建评级分数DataFrame
        score_data = self.data[['股票代码', '股票名称', '行业']].copy() if '行业' in self.data.columns else self.data[['股票代码', '股票名称']].copy()
        
        for col in self._metadata['date_columns']:
            score_data[f"{col}_score"] = self.data[col].map(RATING_SCORE_MAP)
        
        self._cache['rating_scores'] = score_data
    
    # 基础查询接口
    
    def get_stock_ratings(self, stock_code: str, use_interpolation: bool = True) -> pd.Series:
        """
        获取指定股票的评级序列
        
        参数:
            stock_code (str): 股票代码
            use_interpolation (bool): 是否使用插值填充缺失数据
            
        返回:
            pd.Series: 评级序列，按时间顺序排列
        """
        stock_code = str(stock_code).zfill(6)  # 标准化代码格式
        
        try:
            stock_row = self.data[self.data['股票代码'] == stock_code].iloc[0]
            ratings = stock_row[self._metadata['date_columns']]
            
            # 根据参数决定是否进行前向填充
            if use_interpolation:
                ratings = self._forward_fill_series(ratings, stock_code)
            
            return ratings
        except (IndexError, KeyError):
            return pd.Series(dtype=object)
    
    def _forward_fill_series(self, ratings: pd.Series, stock_code: str = "") -> pd.Series:
        """前向填充评级序列中的"-"值，严格按日期顺序，只允许低日期向高日期补充"""
        if ratings.empty:
            return ratings
        
        # 创建副本以避免修改原数据
        filled_ratings = ratings.copy()
        fill_count = 0
        
        # 第一步：找到第一个有效评级
        first_valid_rating = None
        first_valid_index = None
        
        for i, rating in enumerate(filled_ratings):
            if rating != '-' and not pd.isna(rating) and rating != '':
                first_valid_rating = rating
                first_valid_index = i
                break
        
        # 如果没有找到任何有效评级，返回原序列（全部为空）
        if first_valid_rating is None:
            print(f"警告 StockDataSet {stock_code}: 所有日期都是'-'，无法填充")
            return filled_ratings
        
        # 第二步：从第一个有效评级开始，只向后填充
        # 将前面的无效值设为NaN（不填充）
        for i in range(first_valid_index):
            if filled_ratings.iloc[i] == '-' or pd.isna(filled_ratings.iloc[i]) or filled_ratings.iloc[i] == '':
                filled_ratings.iloc[i] = pd.NA  # 明确设置为NaN，不填充
                print(f"跳过 StockDataSet {stock_code} 早期索引 {i}: 在首个有效数据之前")
        
        # 第三步：从第一个有效评级开始前向填充
        last_valid_rating = first_valid_rating
        for i in range(first_valid_index, len(filled_ratings)):
            rating = filled_ratings.iloc[i]
            if rating == '-' or pd.isna(rating) or rating == '':
                # 使用上一个有效评级填充
                filled_ratings.iloc[i] = last_valid_rating
                fill_count += 1
            else:
                # 更新最后有效评级
                last_valid_rating = rating
        
        if fill_count > 0:
            print(f"StockDataSet严格前向填充 {stock_code}: 填充了 {fill_count} 个'-'值 (从索引 {first_valid_index} 开始)")
        
        return filled_ratings
    
    def get_stock_rating_scores(self, stock_code: str) -> pd.Series:
        """
        获取指定股票的评级分数序列
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            pd.Series: 评级分数序列
        """
        ratings = self.get_stock_ratings(stock_code)
        return ratings.map(RATING_SCORE_MAP)
    
    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票基本信息
        
        参数:
            stock_code (str): 股票代码
            
        返回:
            dict: 股票信息
        """
        stock_code = str(stock_code).zfill(6)
        
        try:
            stock_row = self.data[self.data['股票代码'] == stock_code].iloc[0]
            return {
                'code': stock_row['股票代码'],
                'name': stock_row['股票名称'],
                'industry': stock_row.get('行业', '未分类'),
                'has_ratings': not self.get_stock_ratings(stock_code).empty
            }
        except (IndexError, KeyError):
            return {}
    
    def get_industry_stocks(self, industry: str) -> List[Tuple[str, str]]:
        """
        获取指定行业的股票列表
        
        参数:
            industry (str): 行业名称
            
        返回:
            list: [(股票代码, 股票名称), ...]
        """
        if not self._metadata['has_industry_data']:
            return []
        
        industry_data = self.data[self.data['行业'] == industry]
        return [(row['股票代码'], row['股票名称']) for _, row in industry_data.iterrows()]
    
    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取数据日期范围
        
        返回:
            tuple: (开始日期, 结束日期)
        """
        return self._metadata['date_range']
    
    def get_all_industries(self) -> List[str]:
        """
        获取所有行业列表
        
        返回:
            list: 行业名称列表
        """
        return self._metadata['industries'].copy()
    
    def get_raw_data(self) -> pd.DataFrame:
        """
        获取原始数据
        
        返回:
            pd.DataFrame: 原始股票数据
        """
        return self.data.copy()
    
    # 高级查询接口
    
    def filter_stocks_by_industry(self, industries: Union[str, List[str]]) -> 'StockDataSet':
        """
        按行业筛选股票
        
        参数:
            industries: 行业名称或行业列表
            
        返回:
            StockDataSet: 筛选后的数据集
        """
        if isinstance(industries, str):
            industries = [industries]
        
        filtered_data = self.data[self.data['行业'].isin(industries)] if self._metadata['has_industry_data'] else self.data.iloc[0:0]
        return StockDataSet(filtered_data, self.file_path)
    
    def filter_stocks_by_codes(self, codes: List[str]) -> 'StockDataSet':
        """
        按股票代码筛选
        
        参数:
            codes: 股票代码列表
            
        返回:
            StockDataSet: 筛选后的数据集
        """
        codes = [str(code).zfill(6) for code in codes]  # 标准化格式
        filtered_data = self.data[self.data['股票代码'].isin(codes)]
        return StockDataSet(filtered_data, self.file_path)
    
    def get_stocks_with_ratings(self, min_rating_days: int = 5) -> 'StockDataSet':
        """
        获取有足够评级数据的股票
        
        参数:
            min_rating_days: 最少评级天数
            
        返回:
            StockDataSet: 筛选后的数据集
        """
        if not self._metadata['has_rating_data']:
            return StockDataSet(self.data.iloc[0:0], self.file_path)
        
        # 计算每只股票的有效评级天数
        valid_ratings_count = []
        for _, row in self.data.iterrows():
            ratings = row[self._metadata['date_columns']]
            valid_count = ratings.notna().sum() - (ratings == '-').sum()
            valid_ratings_count.append(valid_count >= min_rating_days)
        
        filtered_data = self.data[valid_ratings_count]
        return StockDataSet(filtered_data, self.file_path)
    
    # 数据统计和分析
    
    def get_rating_distribution(self, date: str = None) -> Dict[str, int]:
        """
        获取评级分布统计
        
        参数:
            date: 指定日期，None表示最新日期
            
        返回:
            dict: 评级分布
        """
        if not self._metadata['has_rating_data']:
            return {}
        
        if date is None:
            date = self._metadata['date_columns'][-1]  # 最新日期
        
        if date not in self._metadata['date_columns']:
            return {}
        
        return self.data[date].value_counts().to_dict()
    
    def get_industry_statistics(self) -> Dict[str, Any]:
        """
        获取行业统计信息
        
        返回:
            dict: 行业统计
        """
        if not self._metadata['has_industry_data']:
            return {}
        
        industry_dist = self.data['行业'].value_counts()
        
        return {
            'total_industries': len(industry_dist),
            'largest_industry': industry_dist.index[0] if len(industry_dist) > 0 else None,
            'largest_industry_count': industry_dist.iloc[0] if len(industry_dist) > 0 else 0,
            'industry_distribution': industry_dist.head(20).to_dict(),
            'industry_coverage': self.data['行业'].notna().sum() / len(self.data) * 100
        }
    
    def get_data_quality_summary(self) -> Dict[str, Any]:
        """
        获取数据质量概要
        
        返回:
            dict: 数据质量信息
        """
        summary = {
            'total_stocks': self._metadata['total_stocks'],
            'trading_days': self._metadata['trading_days'],
            'date_range': f"{self._metadata['date_range'][0]} ~ {self._metadata['date_range'][1]}" if self._metadata['date_range'][0] else "无",
            'has_industry_data': self._metadata['has_industry_data'],
            'has_rating_data': self._metadata['has_rating_data']
        }
        
        if self._metadata['has_rating_data']:
            # 评级数据质量
            latest_date = self._metadata['date_columns'][-1]
            latest_ratings = self.data[latest_date]
            
            total_ratings = len(latest_ratings)
            valid_ratings = (latest_ratings.notna() & (latest_ratings != '-')).sum()
            
            summary.update({
                'latest_date': latest_date,
                'latest_rating_coverage': valid_ratings / total_ratings * 100,
                'latest_rating_distribution': latest_ratings.value_counts().head(5).to_dict()
            })
        
        if self._metadata['has_industry_data']:
            # 行业数据质量
            industry_coverage = self.data['行业'].notna().sum() / len(self.data) * 100
            summary['industry_coverage'] = industry_coverage
        
        return summary
    
    def validate_data(self) -> Dict[str, Any]:
        """
        数据验证功能
        
        返回:
            dict: 验证结果
        """
        validation_result = {
            'passed': 0,
            'failed': 0,
            'warnings': [],
            'summary': '',
            'details': []
        }
        
        # 检查必需列
        required_columns = ['股票代码', '股票名称']
        for col in required_columns:
            if col in self.data.columns:
                validation_result['passed'] += 1
                validation_result['details'].append(f"成功 必需列 '{col}' 存在")
            else:
                validation_result['failed'] += 1
                validation_result['details'].append(f"错误 缺少必需列 '{col}'")
        
        # 检查行业列
        if '行业' in self.data.columns:
            validation_result['passed'] += 1
            validation_result['details'].append("成功 行业分类列存在")
            
            # 检查行业覆盖率
            industry_coverage = self.data['行业'].notna().sum() / len(self.data) * 100
            if industry_coverage < 30:
                validation_result['warnings'].append(f"行业覆盖率较低: {industry_coverage:.1f}%")
        else:
            validation_result['warnings'].append("行业分类列不存在")
        
        # 检查日期列
        date_columns = self._metadata['date_columns']
        if len(date_columns) >= 5:
            validation_result['passed'] += 1
            validation_result['details'].append(f"成功 日期列充足: {len(date_columns)}个")
        else:
            validation_result['failed'] += 1
            validation_result['details'].append(f"错误 日期列不足: 仅{len(date_columns)}个")
        
        # 检查股票代码格式
        try:
            if '股票代码' in self.data.columns:
                code_format_valid = self.data['股票代码'].astype(str).str.match(r'^\d{6}$|^\d{3}$').sum()
                if code_format_valid > len(self.data) * 0.9:
                    validation_result['passed'] += 1
                    validation_result['details'].append("成功 股票代码格式正确")
                else:
                    validation_result['warnings'].append("部分股票代码格式异常")
        except:
            validation_result['warnings'].append("股票代码格式检查失败")
        
        # 检查评级数据
        if date_columns:
            valid_ratings = set(['大多', '中多', '小多', '微多', '微空', '小空', '中空', '大空', '-'])
            for col in date_columns[:3]:  # 检查前3个日期列
                try:
                    unique_values = set(self.data[col].unique())
                    invalid_values = unique_values - valid_ratings
                    if not invalid_values:
                        validation_result['passed'] += 1
                        validation_result['details'].append(f"成功 {col} 评级值格式正确")
                    else:
                        validation_result['warnings'].append(f"{col} 包含无效评级值: {list(invalid_values)[:5]}")
                except:
                    validation_result['warnings'].append(f"{col} 评级数据检查失败")
        
        # 生成摘要
        total_checks = validation_result['passed'] + validation_result['failed']
        if total_checks > 0:
            success_rate = validation_result['passed'] / total_checks * 100
            validation_result['summary'] = f"验证完成: {success_rate:.1f}% 通过率 ({validation_result['passed']}/{total_checks})"
        else:
            validation_result['summary'] = "验证完成: 无可验证项目"
        
        return validation_result
    
    # 数据导出和转换
    
    def to_dataframe(self, include_scores: bool = False) -> pd.DataFrame:
        """
        转换为DataFrame
        
        参数:
            include_scores: 是否包含评级分数
            
        返回:
            pd.DataFrame: 数据框
        """
        if include_scores and 'rating_scores' in self._cache:
            return self._cache['rating_scores'].copy()
        else:
            return self.data.copy()
    
    def get_rating_matrix(self, fill_na: Any = None) -> pd.DataFrame:
        """
        获取评级矩阵 (股票×日期)
        
        参数:
            fill_na: 缺失值填充方式
            
        返回:
            pd.DataFrame: 评级矩阵
        """
        if not self._metadata['has_rating_data']:
            return pd.DataFrame()
        
        # 创建评级矩阵
        rating_matrix = self.data.set_index('股票代码')[self._metadata['date_columns']]
        
        if fill_na is not None:
            rating_matrix = rating_matrix.fillna(fill_na)
        
        return rating_matrix
    
    def get_score_matrix(self, fill_na: Any = None) -> pd.DataFrame:
        """
        获取评级分数矩阵 (股票×日期)
        
        参数:
            fill_na: 缺失值填充方式
            
        返回:
            pd.DataFrame: 分数矩阵
        """
        if not self._metadata['has_rating_data']:
            return pd.DataFrame()
        
        # 创建分数矩阵
        rating_matrix = self.get_rating_matrix()
        score_matrix = rating_matrix.map(RATING_SCORE_MAP)
        
        if fill_na is not None:
            score_matrix = score_matrix.fillna(fill_na)
        
        return score_matrix
    
    # 元数据和缓存管理
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取数据集元数据"""
        return self._metadata.copy()
    
    def refresh_cache(self):
        """刷新内部缓存"""
        self._cache.clear()
        self._create_rating_scores()
    
    def clear_cache(self):
        """清理缓存"""
        self._cache.clear()
    
    # 魔术方法
    
    def __len__(self) -> int:
        """返回股票数量"""
        return len(self.data)
    
    def __getitem__(self, key: str) -> pd.Series:
        """支持直接访问列"""
        return self.data[key]
    
    def __contains__(self, stock_code: str) -> bool:
        """检查是否包含指定股票"""
        stock_code = str(stock_code).zfill(6)
        return stock_code in self.data['股票代码'].values
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"StockDataSet(stocks={len(self.data)}, dates={self._metadata['trading_days']}, file='{self.file_path}')"
    
    def __str__(self) -> str:
        """可读字符串表示"""
        info = []
        info.append(f"股票数据集")
        info.append(f"  股票数量: {self._metadata['total_stocks']:,}")
        info.append(f"  交易日数: {self._metadata['trading_days']}")
        if self._metadata['date_range'][0]:
            info.append(f"  日期范围: {self._metadata['date_range'][0]} ~ {self._metadata['date_range'][1]}")
        info.append(f"  行业数据: {'有' if self._metadata['has_industry_data'] else '无'}")
        info.append(f"  评级数据: {'有' if self._metadata['has_rating_data'] else '无'}")
        if self.file_path:
            info.append(f"  数据文件: {self.file_path}")
        
        return "\n".join(info)


# 便捷函数

def create_stock_dataset(data: pd.DataFrame, file_path: str = "") -> StockDataSet:
    """
    便捷函数：创建股票数据集
    
    参数:
        data (pd.DataFrame): 股票数据
        file_path (str): 文件路径
        
    返回:
        StockDataSet: 数据集对象
    """
    return StockDataSet(data, file_path)


def merge_datasets(datasets: List[StockDataSet]) -> Optional[StockDataSet]:
    """
    合并多个数据集
    
    参数:
        datasets: 数据集列表
        
    返回:
        StockDataSet: 合并后的数据集，失败返回None
    """
    if not datasets:
        return None
    
    try:
        # 合并数据
        all_data = []
        for dataset in datasets:
            all_data.append(dataset.data)
        
        merged_data = pd.concat(all_data, ignore_index=True)
        
        # 去重
        if '股票代码' in merged_data.columns:
            merged_data = merged_data.drop_duplicates(subset=['股票代码'])
        
        # 创建新数据集
        file_paths = [ds.file_path for ds in datasets if ds.file_path]
        merged_file_path = "; ".join(file_paths) if file_paths else "merged"
        
        return StockDataSet(merged_data, merged_file_path)
        
    except Exception as e:
        warnings.warn(f"数据集合并失败: {e}")
        return None


# 测试函数
def test_stock_dataset():
    """测试股票数据集"""
    print("...")
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '行业': ['软件开发', '半导体', '银行', '未分类', '汽车'],
        '股票代码': ['000001', '000002', '000003', '000004', '000005'],
        '股票名称': ['测试股票1', '测试股票2', '测试股票3', '测试股票4', '测试股票5'],
        '20250601': ['大多', '中多', '小多', '-', '微空'],
        '20250602': ['中多', '小多', '微多', '-', '小空'],
        '20250603': ['小多', '微多', '微多', '微多', '-']
    })
    
    # 创建数据集
    dataset = StockDataSet(test_data, "test_data.xlsx")
    
    print(f"   成功 数据集创建成功: {dataset}")
    
    # 测试基础查询
    stock_ratings = dataset.get_stock_ratings('000001')
    print(f"   数据 获取评级: {len(stock_ratings)} 个")
    
    stock_info = dataset.get_stock_info('000001')
    print(f"   ℹ️ 股票信息: {stock_info}")
    
    # 测试行业查询
    industry_stocks = dataset.get_industry_stocks('软件开发')
    print(f"   行业 行业股票: {len(industry_stocks)} 只")
    
    # 测试筛选
    filtered_dataset = dataset.filter_stocks_by_industry(['软件开发', '半导体'])
    print(f"   检查 筛选结果: {len(filtered_dataset)} 只股票")
    
    # 测试统计
    quality_summary = dataset.get_data_quality_summary()
    print(f"   上涨 数据质量: 覆盖率 {quality_summary.get('latest_rating_coverage', 0):.1f}%")
    
    print("")
    return True


if __name__ == "__main__":
    test_stock_dataset()