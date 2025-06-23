"""
分析结果管理模块
管理RTSI、IRSI、MSCI等算法的分析结果
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class AnalysisResults:
    """分析结果容器类"""
    
    def __init__(self):
        self.stocks = {}       # 个股RTSI结果
        self.industries = {}   # 行业IRSI结果  
        self.market = {}       # 市场MSCI结果
        self.timestamp = None  # 分析时间戳
        self.metadata = {}     # 元数据
    
    def set_stock_result(self, stock_code: str, result: dict):
        """设置个股分析结果"""
        self.stocks[stock_code] = result
    
    def set_industry_result(self, industry: str, result: dict):
        """设置行业分析结果"""
        self.industries[industry] = result
    
    def set_market_result(self, result: dict):
        """设置市场分析结果"""
        self.market = result
    
    def get_stock_result(self, stock_code: str) -> dict:
        """获取个股分析结果"""
        return self.stocks.get(stock_code, {})
    
    def get_industry_result(self, industry: str) -> dict:
        """获取行业分析结果"""
        return self.industries.get(industry, {})
    
    def get_market_result(self) -> dict:
        """获取市场分析结果"""
        return self.market
    
    def get_top_stocks(self, metric: str = 'rtsi', limit: int = 10) -> List[tuple]:
        """获取排名前N的股票"""
        if metric == 'rtsi':
            sorted_stocks = sorted(
                self.stocks.items(),
                key=lambda x: x[1].get('rtsi', {}).get('rtsi', 0) if isinstance(x[1].get('rtsi'), dict) else x[1].get('rtsi', 0),
                reverse=True
            )
            # 返回 (code, name, rtsi_value) 格式
            result = []
            for code, data in sorted_stocks[:limit]:
                rtsi_value = data.get('rtsi', {})
                if isinstance(rtsi_value, dict):
                    rtsi_score = rtsi_value.get('rtsi', 0)
                else:
                    rtsi_score = rtsi_value if isinstance(rtsi_value, (int, float)) else 0
                stock_name = data.get('name', code)
                result.append((code, stock_name, rtsi_score))
            return result
        else:
            return []
    
    def get_top_industries(self, metric: str = 'irsi', limit: int = 10) -> List[tuple]:
        """获取排名前N的行业"""
        if metric == 'irsi':
            sorted_industries = sorted(
                self.industries.items(), 
                key=lambda x: x[1].get('irsi', 0) if isinstance(x[1], dict) else (x[1] if isinstance(x[1], (int, float)) else 0),
                reverse=True
            )
            # 返回 (industry, irsi_value) 格式
            result = []
            for industry, data in sorted_industries[:limit]:
                if isinstance(data, dict):
                    irsi_score = data.get('irsi', 0)
                elif isinstance(data, (int, float)):
                    irsi_score = data
                else:
                    irsi_score = 0
                result.append((industry, irsi_score))
            return result
        else:
            return []
    
    def is_empty(self) -> bool:
        """检查是否为空结果"""
        return not (self.stocks or self.industries or self.market)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'stocks': self.stocks,
            'industries': self.industries,
            'market': self.market,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }
    
    def from_dict(self, data: dict):
        """从字典格式加载"""
        self.stocks = data.get('stocks', {})
        self.industries = data.get('industries', {})
        self.market = data.get('market', {})
        self.timestamp = data.get('timestamp')
        self.metadata = data.get('metadata', {})
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存分析结果失败: {e}")
    
    def load_from_file(self, filepath: str):
        """从文件加载"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.from_dict(data)
        except Exception as e:
            print(f"加载分析结果失败: {e}")


def create_empty_results() -> AnalysisResults:
    """创建空的分析结果"""
    return AnalysisResults()


def merge_results(results_list: List[AnalysisResults]) -> AnalysisResults:
    """合并多个分析结果"""
    merged = AnalysisResults()
    
    for results in results_list:
        merged.stocks.update(results.stocks)
        merged.industries.update(results.industries)
        if results.market:
            merged.market = results.market
    
    merged.timestamp = datetime.now().isoformat()
    return merged 