# -*- coding: utf-8 -*-
"""
LLM分析模型包
"""

# 导入分析模型
try:
    from analysis_models import *
except ImportError:
    pass

# 直接从父目录的models.py导入
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(__file__))
models_file = os.path.join(parent_dir, 'models.py')

# 使用exec动态导入避免循环导入
if os.path.exists(models_file):
    with open(models_file, 'r', encoding='utf-8') as f:
        models_code = f.read()
    
    # 创建一个新的命名空间来执行models.py的代码
    models_namespace = {
        '__file__': models_file,
        '__name__': 'models',
        '__builtins__': __builtins__
    }
    exec(models_code, models_namespace)
    
    # 提取需要的类和函数
    ModelProvider = models_namespace.get('ModelProvider')
    LLMModel = models_namespace.get('LLMModel')
    get_model_info = models_namespace.get('get_model_info')
    list_all_models = models_namespace.get('list_all_models')
else:
    # 如果无法导入，则定义基本的枚举
    from enum import Enum
    
    class ModelProvider(str, Enum):
        OPENAI = "OpenAI"
        ANTHROPIC = "Anthropic"
    
    class LLMModel:
        pass
    
    def get_model_info():
        pass
    
    def list_all_models():
        pass

__all__ = [
    'RiskLevel',
    'TrendDirection', 
    'InvestmentAdvice',
    'MarketSentiment',
    'MarketAnalysis',
    'SectorAnalysis',
    'StockRecommendation',
    'RiskManagement',
    'TimeframeOutlook',
    'StructuredAnalysisResult',
    'MultiPerspectiveAnalysis',
    'QuickAnalysisResult',
    'ModelProvider',
    'LLMModel',
    'get_model_info',
    'list_all_models'
]