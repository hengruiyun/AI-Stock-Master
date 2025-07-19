"""
AI股票趋势分析系统 - 数据处理模块

第一期核心功能：
1. Excel数据加载器 - 支持多种格式自动识别
2. 数据验证器 - 数据质量检测和报告
3. 统一数据接口 - 标准化数据访问

作者: 267278466@qq.com
版本：v1.0
创建时间：2025-06-07
"""

from .excel_loader import ExcelDataLoader, load_stock_data
from .data_validator import DataValidator, validate_stock_data
from .stock_dataset import StockDataSet

__version__ = "2.2.0"
__author__ = "267278466@qq.com"

__all__ = [
    # 数据加载
    'ExcelDataLoader',
    'load_stock_data',
    
    # 数据验证
    'DataValidator', 
    'validate_stock_data',
    
    # 数据集接口
    'StockDataSet'
]

# 便捷函数
def load_and_validate_data(file_path: str, auto_validate: bool = True):
    """
    便捷函数：加载并验证股票数据
    
    参数:
        file_path (str): Json文件路径
        auto_validate (bool): 是否自动验证数据
        
    返回:
        tuple: (StockDataSet, validation_result)
    """
    # 加载数据
    loader = ExcelDataLoader(file_path)
    data, load_result = loader.load_and_validate()
    
    if not load_result.get('is_valid', False):
        return None, load_result
    
    # 创建数据集对象
    dataset = StockDataSet(data, file_path)
    
    # 自动验证
    validation_result = None
    if auto_validate:
        validator = DataValidator()
        validation_result = validator.validate_complete_dataset(dataset)
    
    return dataset, validation_result or load_result