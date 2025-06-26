"""
数据验证器 - 数据质量检测和报告

功能特性：
1. 评级数据验证 - 8级评级系统完整性检查
2. 行业数据验证 - 行业分类正确性检查
3. 数据完整性检查 - 缺失值和异常值检测
4. 质量报告生成 - 详细的数据质量分析报告

作者: 267278466@qq.com
创建时间：2025-06-07
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import warnings

# 导入配置
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


class DataValidator:
    """数据验证器 - 提供全面的数据质量检测"""
    
    def __init__(self, enable_industry_check: bool = True):
        """
        初始化验证器
        
        参数:
            enable_industry_check (bool): 是否启用行业数据验证
        """
        self.enable_industry_check = enable_industry_check
        self.validation_results = {}
        self.quality_score = 0.0
    
    def validate_complete_dataset(self, dataset) -> Dict:
        """
        完整数据集验证
        
        参数:
            dataset: StockDataSet对象或DataFrame
            
        返回:
            dict: 完整验证结果
        """
        if hasattr(dataset, 'data'):
            df = dataset.data
            file_path = dataset.file_path
        else:
            df = dataset
            file_path = "unknown"
        
        validation_start = datetime.now()
        
        # 1. 基础结构验证
        structure_result = self.validate_data_structure(df)
        
        # 2. 评级数据验证
        rating_result = self.validate_rating_data(df)
        
        # 3. 行业数据验证
        industry_result = self.validate_industry_data(df) if self.enable_industry_check else {}
        
        # 4. 数据完整性验证
        completeness_result = self.check_data_completeness(df)
        
        # 5. 数据一致性验证
        consistency_result = self.check_data_consistency(df)
        
        # 6. 计算质量分数
        quality_score = self.calculate_quality_score(
            structure_result, rating_result, industry_result, 
            completeness_result, consistency_result
        )
        
        validation_time = (datetime.now() - validation_start).total_seconds()
        
        # 整合结果
        complete_result = {
            'is_valid': all([
                structure_result.get('is_valid', False),
                rating_result.get('is_valid', False),
                completeness_result.get('is_valid', False)
            ]),
            'quality_score': round(quality_score, 2),
            'validation_time': f"{validation_time:.2f}s",
            'file_path': file_path,
            'validation_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'structure': structure_result,
            'rating_data': rating_result,
            'industry_data': industry_result,
            'completeness': completeness_result,
            'consistency': consistency_result,
            'recommendations': self._generate_recommendations(
                structure_result, rating_result, industry_result, completeness_result
            )
        }
        
        self.validation_results = complete_result
        self.quality_score = quality_score
        
        return complete_result
    
    def validate_data_structure(self, df: pd.DataFrame) -> Dict:
        """验证数据基础结构"""
        result = {
            'is_valid': True,
            'missing_columns': [],
            'warnings': [],
            'data_quality': {}
        }
        
        # 检查必需列
        required_columns = ['行业', '股票代码', '股票名称']
        for col in required_columns:
            if col not in df.columns:
                result['missing_columns'].append(col)
                result['is_valid'] = False
        
        # 检查日期列
        date_columns = [col for col in df.columns if str(col).startswith('202')]
        
        if len(date_columns) == 0:
            result['warnings'].append('未找到日期列')
            result['is_valid'] = False
        elif len(date_columns) < 5:
            result['warnings'].append('日期列过少，可能影响趋势分析准确性')
        
        # 数据质量检查
        if result['is_valid']:
            result['data_quality'] = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'date_columns_count': len(date_columns),
                'date_range': f"{min(date_columns)} ~ {max(date_columns)}" if date_columns else "无",
                'industry_coverage': df['行业'].notna().sum() / len(df) * 100 if '行业' in df.columns else 0,
                'duplicate_codes': df['股票代码'].duplicated().sum() if '股票代码' in df.columns else 0,
                'duplicate_names': df['股票名称'].duplicated().sum() if '股票名称' in df.columns else 0
            }
        
        return result
    
    def validate_rating_data(self, df: pd.DataFrame) -> Dict:
        """验证评级数据"""
        date_columns = [col for col in df.columns if str(col).startswith('202')]
        
        if not date_columns:
            return {
                'is_valid': False,
                'error': '未找到评级日期列',
                'details': {}
            }
        
        valid_ratings = set(RATING_SCORE_MAP.keys())
        result = {
            'is_valid': True,
            'total_date_columns': len(date_columns),
            'date_range': f"{min(date_columns)} ~ {max(date_columns)}",
            'rating_distribution': {},
            'invalid_ratings': {},
            'missing_data_stats': {},
            'quality_metrics': {}
        }
        
        total_cells = 0
        valid_cells = 0
        missing_cells = 0
        
        # 验证每个日期列
        for col in date_columns:
            col_data = df[col]
            total_cells += len(col_data)
            
            # 评级分布
            rating_dist = col_data.value_counts()
            result['rating_distribution'][col] = rating_dist.to_dict()
            
            # 无效评级检测
            unique_ratings = set(col_data.dropna().unique())
            invalid = unique_ratings - valid_ratings
            if invalid:
                result['invalid_ratings'][col] = list(invalid)
                result['is_valid'] = False
            
            # 缺失数据统计
            missing_count = col_data.isna().sum() + (col_data == '-').sum()
            missing_rate = missing_count / len(col_data) * 100
            missing_cells += missing_count
            
            result['missing_data_stats'][col] = {
                'missing_count': missing_count,
                'missing_rate': round(missing_rate, 2),
                'valid_count': len(col_data) - missing_count
            }
            
            # 有效数据统计
            valid_ratings_count = col_data.isin([r for r in valid_ratings if r != '-']).sum()
            valid_cells += valid_ratings_count
        
        # 整体质量指标
        overall_validity_rate = valid_cells / total_cells * 100 if total_cells > 0 else 0
        overall_missing_rate = missing_cells / total_cells * 100 if total_cells > 0 else 0
        
        result['quality_metrics'] = {
            'total_cells': total_cells,
            'valid_cells': valid_cells,
            'missing_cells': missing_cells,
            'validity_rate': round(overall_validity_rate, 2),
            'missing_rate': round(overall_missing_rate, 2),
            'data_coverage': round(100 - overall_missing_rate, 2)
        }
        
        return result
    
    def validate_industry_data(self, df: pd.DataFrame) -> Dict:
        """验证行业数据"""
        if '行业' not in df.columns:
            return {
                'is_valid': False,
                'error': '未找到行业列',
                'details': {}
            }
        
        industry_col = df['行业']
        result = {
            'is_valid': True,
            'industry_coverage': 0,
            'industry_distribution': {},
            'missing_industry_stats': {},
            'quality_metrics': {}
        }
        
        # 行业覆盖率
        non_missing = industry_col.notna() & (industry_col != '') & (industry_col != '未分类')
        coverage_rate = non_missing.sum() / len(industry_col) * 100
        result['industry_coverage'] = round(coverage_rate, 2)
        
        # 行业分布
        industry_dist = industry_col.value_counts()
        result['industry_distribution'] = industry_dist.head(20).to_dict()
        
        # 缺失统计
        missing_count = industry_col.isna().sum() + (industry_col == '').sum()
        unclassified_count = (industry_col == '未分类').sum()
        
        result['missing_industry_stats'] = {
            'missing_count': missing_count,
            'unclassified_count': unclassified_count,
            'total_missing': missing_count + unclassified_count,
            'missing_rate': round((missing_count + unclassified_count) / len(industry_col) * 100, 2)
        }
        
        # 质量指标
        result['quality_metrics'] = {
            'total_stocks': len(df),
            'classified_stocks': non_missing.sum(),
            'unique_industries': len(industry_dist),
            'largest_industry': industry_dist.index[0] if len(industry_dist) > 0 else None,
            'largest_industry_count': industry_dist.iloc[0] if len(industry_dist) > 0 else 0
        }
        
        return result
    
    def check_data_completeness(self, df: pd.DataFrame) -> Dict:
        """检查数据完整性"""
        result = {
            'is_valid': True,
            'overall_completeness': 0,
            'column_completeness': {},
            'row_completeness': {},
            'critical_missing': [],
            'quality_metrics': {}
        }
        
        # 列完整性
        for col in df.columns:
            missing_count = df[col].isna().sum()
            completeness = (len(df) - missing_count) / len(df) * 100
            
            result['column_completeness'][col] = {
                'missing_count': missing_count,
                'completeness_rate': round(completeness, 2),
                'is_critical': col in ['股票代码', '股票名称']
            }
            
            # 关键列缺失检查
            if col in ['股票代码', '股票名称'] and missing_count > 0:
                result['critical_missing'].append(col)
                result['is_valid'] = False
        
        # 行完整性（评级数据行）
        date_columns = [col for col in df.columns if str(col).startswith('202')]
        if date_columns:
            row_stats = []
            for idx, row in df.iterrows():
                rating_data = row[date_columns]
                non_missing = rating_data.notna().sum()
                completeness = non_missing / len(date_columns) * 100
                row_stats.append(completeness)
            
            result['row_completeness'] = {
                'avg_completeness': round(np.mean(row_stats), 2),
                'min_completeness': round(np.min(row_stats), 2),
                'max_completeness': round(np.max(row_stats), 2),
                'stocks_with_full_data': sum(1 for x in row_stats if x == 100),
                'stocks_with_no_data': sum(1 for x in row_stats if x == 0)
            }
        
        # 整体完整性
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        overall_completeness = (total_cells - missing_cells) / total_cells * 100
        result['overall_completeness'] = round(overall_completeness, 2)
        
        # 质量指标
        result['quality_metrics'] = {
            'total_cells': total_cells,
            'missing_cells': missing_cells,
            'data_density': round(overall_completeness, 2),
            'critical_columns_ok': len(result['critical_missing']) == 0
        }
        
        return result
    
    def check_data_consistency(self, df: pd.DataFrame) -> Dict:
        """检查数据一致性"""
        result = {
            'is_valid': True,
            'duplicate_checks': {},
            'format_consistency': {},
            'value_consistency': {}
        }
        
        # 重复数据检查
        if '股票代码' in df.columns:
            duplicate_codes = df['股票代码'].duplicated().sum()
            result['duplicate_checks']['duplicate_stock_codes'] = duplicate_codes
            if duplicate_codes > 0:
                result['is_valid'] = False
        
        if '股票名称' in df.columns:
            duplicate_names = df['股票名称'].duplicated().sum()
            result['duplicate_checks']['duplicate_stock_names'] = duplicate_names
        
        return result
    
    def calculate_quality_score(self, structure: Dict, rating: Dict, 
                              industry: Dict, completeness: Dict, 
                              consistency: Dict) -> float:
        """计算数据质量分数 (0-100)"""
        score = 0.0
        
        # 结构分数 (20%)
        if structure.get('is_valid', False):
            score += 20
        
        # 评级数据分数 (40%)
        if rating.get('is_valid', False):
            validity_rate = rating.get('quality_metrics', {}).get('validity_rate', 0)
            score += 40 * (validity_rate / 100)
        
        # 完整性分数 (25%)
        if completeness.get('is_valid', False):
            completeness_rate = completeness.get('overall_completeness', 0)
            score += 25 * (completeness_rate / 100)
        
        # 一致性分数 (10%)
        if consistency.get('is_valid', False):
            score += 10
        
        # 行业数据分数 (5%)
        if industry.get('is_valid', True):
            coverage = industry.get('industry_coverage', 0)
            score += 5 * (coverage / 100)
        
        return min(100.0, score)
    
    def generate_quality_report(self) -> str:
        """生成数据质量报告"""
        if not self.validation_results:
            return "错误 未进行数据验证，请先调用validate_complete_dataset方法"
        
        results = self.validation_results
        
        report = []
        report.append("=" * 80)
        report.append("数据 数据质量验证报告")
        report.append("=" * 80)
        
        # 基础信息
        report.append(f"📂 文件路径: {results.get('file_path', 'unknown')}")
        report.append(f"🕒 验证时间: {results.get('validation_timestamp', 'unknown')}")
        report.append(f"⏱️ 验证耗时: {results.get('validation_time', 'unknown')}")
        report.append(f"核心 质量分数: {results.get('quality_score', 0)}/100")
        report.append("")
        
        # 验证状态
        status_emoji = "成功" if results.get('is_valid', False) else "错误"
        report.append(f"{status_emoji} 整体验证状态: {'通过' if results.get('is_valid', False) else '失败'}")
        report.append("")
        
        # 结构验证
        structure = results.get('structure', {})
        if structure:
            report.append("列表 数据结构验证:")
            dq = structure.get('data_quality', {})
            report.append(f"   📏 数据规模: {dq.get('total_rows', 0)} 行 × {dq.get('total_columns', 0)} 列")
            report.append(f"   时间 日期范围: {dq.get('date_range', '无')}")
            report.append(f"   行业 行业覆盖: {dq.get('industry_coverage', 0):.1f}%")
            report.append("")
        
        # 推荐建议
        recommendations = results.get('recommendations', [])
        if recommendations:
            report.append("提示 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                report.append(f"   {i}. {rec}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _generate_recommendations(self, structure: Dict, rating: Dict, 
                                industry: Dict, completeness: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 结构问题
        if not structure.get('is_valid', False):
            recommendations.append("修复数据结构问题，确保包含必需的列")
        
        # 评级问题
        if rating.get('quality_metrics', {}).get('validity_rate', 0) < 90:
            recommendations.append("清理无效评级数据，确保符合8级评级系统")
        
        # 行业问题
        if industry.get('industry_coverage', 0) < 80:
            recommendations.append("完善行业分类信息，提高行业覆盖率")
        
        # 完整性问题
        if completeness.get('overall_completeness', 0) < 70:
            recommendations.append("补充缺失数据，提高数据完整性")
        
        return recommendations


# 便捷函数
def validate_stock_data(data: pd.DataFrame, enable_industry_check: bool = True) -> Dict:
    """便捷函数：验证股票数据"""
    validator = DataValidator(enable_industry_check)
    return validator.validate_complete_dataset(data)


def generate_quick_report(data: pd.DataFrame) -> str:
    """便捷函数：生成快速数据质量报告"""
    validator = DataValidator()
    validator.validate_complete_dataset(data)
    return validator.generate_quality_report()


# 测试函数
def test_data_validator():
    """测试数据验证器"""
    print("测试 测试数据验证器...")
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '行业': ['软件开发', '半导体', '银行', None, '未分类'],
        '股票代码': ['000001', '000002', '000003', '000004', '000005'],
        '股票名称': ['测试股票1', '测试股票2', '测试股票3', '测试股票4', '测试股票5'],
        '20250601': ['大多', '中多', '小多', '-', '微空'],
        '20250602': ['中多', '小多', '微多', '-', '小空'],
        '20250603': ['小多', '微多', '微多', '微多', '-']
    })
    
    # 测试验证
    validator = DataValidator(enable_industry_check=False)
    result = validator.validate_complete_dataset(test_data)
    
    print(f"   成功 验证完成，质量分数: {result['quality_score']}")
    print(f"   数据 验证状态: {'通过' if result['is_valid'] else '失败'}")
    
    # 生成报告
    report = validator.generate_quality_report()
    print("   列表 质量报告已生成")
    
    print("成功 数据验证器测试完成")
    return True


if __name__ == "__main__":
    test_data_validator() 