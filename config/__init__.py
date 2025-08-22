# -*- coding: utf-8 -*-
"""
Config package for AI Stock Analysis
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入配置常量
try:
    import importlib.util
    config_path = os.path.join(project_root, 'config.py')
    spec = importlib.util.spec_from_file_location("config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    # 导出配置常量
    RTSI_CONFIG = config_module.RTSI_CONFIG
    IRSI_CONFIG = config_module.IRSI_CONFIG
    MSCI_CONFIG = config_module.MSCI_CONFIG
    RATING_SCORE_MAP = config_module.RATING_SCORE_MAP
    
except Exception as e:
    # 如果导入失败，使用默认配置
    RTSI_CONFIG = {
        'rtsi_threshold': 0.4,
        'volatility_threshold': 0.2,
        'trend_strength_threshold': 0.6,
        'use_ai_enhancement': True,
        'use_multi_dimensional': False,
        'time_window': 60
    }

# 延迟导入以避免循环导入
def get_config(*args, **kwargs):
    """获取配置值"""
    # 直接导入根目录下的 config.py 文件
    import importlib.util
    config_path = os.path.join(project_root, 'config.py')
    spec = importlib.util.spec_from_file_location("config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    return config_module.get_config(*args, **kwargs)

def load_user_config(*args, **kwargs):
    """加载用户配置"""
    # 直接导入根目录下的 config.py 文件
    import importlib.util
    config_path = os.path.join(project_root, 'config.py')
    spec = importlib.util.spec_from_file_location("config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    return config_module.load_user_config(*args, **kwargs)

# 评级分数映射表
RATING_SCORE_MAP = {
    '大多': 7, '中多': 6, '小多': 5, '微多': 4,
    '微空': 3, '小空': 2, '中空': 1, '大空': 0, 
    '-': None
}

# 导出的函数和变量
__all__ = ['get_config', 'load_user_config', 'RATING_SCORE_MAP']