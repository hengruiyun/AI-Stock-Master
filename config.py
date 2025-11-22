#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
from config.gui_i18n import t_gui as _
AI股票大师 - 配置文件
集成行业速查系统和核心算法配置

配置管理模块 - 支持用户配置文件

提供系统配置、用户配置文件的管理功能
"""

import os
import json
import platform
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# =============================================================================
# 系统基础配置
# =============================================================================

# 版本信息
VERSION = "3.8.0"
APP_NAME = "AI股票大师"
from config.constants import AUTHOR, VERSION, HOMEPAGE

# 文件路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
INDUSTRY_GUIDES_DIR = os.path.join(RESOURCES_DIR, "industry_guides")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(INDUSTRY_GUIDES_DIR, exist_ok=True)

# =============================================================================
# 行业速查系统配置
# =============================================================================

# 多地区市场配置
MARKET_CONFIG = {
    'CN': {
        'name': '中国A股',
        'description': '中国A股市场',
        'code_pattern': r'^\d{6}$|^[0-9]{3}$|^[0-9]{4}$|^688\d{3}$|^300\d{3}$',
        'filename': '行业速查-中国A股.md',
        'currency': 'CNY',
        'timezone': 'Asia/Shanghai',
        'trading_hours': '09:30-15:00'
    },
    'HK': {
        'name': '香港股市',
        'description': '香港证券交易所',
        'code_pattern': r'^\d{4,5}\.HK$|^0\d{4}$',
        'filename': '行业速查-香港股市.md',
        'currency': 'HKD',
        'timezone': 'Asia/Hong_Kong',
        'trading_hours': '09:30-16:00'
    },
    'US': {
        'name': '美国股市',
        'description': '美国证券市场',
        'code_pattern': r'^[A-Z]{1,5}$',
        'filename': '行业速查-美国股市.md',
        'currency': 'USD',
        'timezone': 'America/New_York',
        'trading_hours': '09:30-16:00'
    }
}

# 默认市场
DEFAULT_MARKET = 'CN'

# 行业速查文件路径
def get_industry_guide_path(market_code: str = DEFAULT_MARKET) -> str:
    """获取行业速查文件路径"""
    filename = MARKET_CONFIG[market_code]['filename']
    return os.path.join(INDUSTRY_GUIDES_DIR, filename)

# =============================================================================
# 评级系统配置
# =============================================================================

# 评级映射表 (8级评级体系)
RATING_SCORE_MAP = {
    '大多': 7,   # 强烈看多
    '中多': 6,   # 看多  
    '小多': 5,   # 偏多
    '微多': 4,   # 微弱看多
    '微空': 3,   # 微弱看空
    '小空': 2,   # 偏空
    '中空': 1,   # 看空
    '大空': 0,   # 强烈看空
    # 兼容测试数据格式
    '看多': 6,   # 看多 (映射到中多)
    '看空': 1,   # 看空 (映射到中空)
    '中性': 4,   # 中性 (映射到微多)
    '-': None    # 无评级/停牌
}

# 评级颜色映射 (用于GUI显示)
RATING_COLORS = {
    '大多': '#FF0000',    # 大红色 (强烈看多)
    '中多': '#FF4444',    # 红色
    '小多': '#FF8844',    # 橙红
    '微多': '#FFAA44',    # 橙色
    '微空': '#DDDD44',    # 黄色
    '小空': '#44DD44',    # 绿色
    '中空': '#44AA44',    # 深绿
    '大空': '#006600',    # 深绿色 (强烈看空)
    '-': '#CCCCCC'        # 灰色
}

# =============================================================================
# 核心算法配置
# =============================================================================

# RTSI (个股评级趋势强度指数) 配置
RTSI_CONFIG = {
    'min_data_points': 5,           # 最少数据点
    'consistency_weight': 0.4,      # 一致性权重
    'significance_weight': 0.3,     # 显著性权重
    'amplitude_weight': 0.3,        # 幅度权重
    'strong_trend_threshold': 0.1,  # 强趋势阈值
    'weak_trend_threshold': 0.05,   # 弱趋势阈值
    'significance_threshold': 0.5,  # 显著性阈值
    'rating_scale_max': 7,          # 评级量表最大值 (大多=7, 大空=0)
    
    # 优化测试得出的最佳参数配置 (2025-08-20)
    'rtsi_threshold': 0.4,          # RTSI筛选阈值
    'volatility_threshold': 0.2,    # 波动性调整阈值
    'trend_strength_threshold': 0.6, # 趋势强度阈值
    
    # AI增强主算法配置 (2025-08-20 正式采用)
    'use_ai_enhancement': True,     # 启用AI增强作为主算法
    'ai_primary_algorithm': True,   # AI增强为主算法
    'ai_fallback_enabled': True,    # 启用基础RTSI作为容错方案
    'ai_weight': 0.7,              # AI增强权重
    'base_weight': 0.3,            # 基础RTSI权重
    'ai_min_score': 10,            # AI最小有效分数
    'ai_coverage_target': 100.0,   # AI覆盖率目标（%）
    
    'use_multi_dimensional': False, # 关闭多维度分析
    'time_window': 60              # 60天时间窗口
}

# IRSI (行业相对强度指数) 配置
IRSI_CONFIG = {
    'min_data_points': 5,           # 最少数据点
    'recent_days': 5,               # 近期天数
    'trend_multiplier': 10,         # 趋势乘数
    'score_multiplier': 20,         # 分数乘数
    'strong_outperform_threshold': 20,  # 强超越阈值
    'weak_outperform_threshold': 5,     # 弱超越阈值
    'strong_underperform_threshold': -20, # 强落后阈值
    'weak_underperform_threshold': -5    # 弱落后阈值
}

# MSCI (市场情绪综合指数) 配置
MSCI_CONFIG = {
    'sentiment_weight': 0.5,        # 情绪权重
    'ratio_weight': 0.3,            # 比例权重
    'participation_weight': 0.2,    # 参与度权重
    'max_bull_bear_ratio': 2.0,     # 最大多空比
    'max_participation_rate': 0.5,  # 最大参与率
    'extreme_bull_threshold': 0.02, # 极端看多阈值
    'extreme_bear_threshold': 0.25, # 极端看空阈值
    'euphoric_threshold': 70,       # 过度乐观阈值
    'optimistic_threshold': 50,     # 乐观阈值
    'neutral_threshold': 30,        # 中性阈值
    'pessimistic_threshold': 15     # 悲观阈值
}

# =============================================================================
# GUI界面配置
# =============================================================================

# 主窗口配置
GUI_CONFIG = {
    'main_window': {
        'title': f"{APP_NAME} v{VERSION}",
        'size': '1200x800',
        'min_size': '800x600',
        'bg_color': '#f0f0f0'
    },
    'colors': {
        'bg_primary': '#f0f0f0',     # 主背景色
        'bg_secondary': '#e0e0e0',   # 次背景色
        'text_primary': '#000000',   # 主文字色
        'text_secondary': '#666666', # 次文字色
        'accent': '#0078d4',         # 强调色
        'success': '#107c10',        # 成功色
        'warning': '#ff8c00',        # 警告色
        'error': '#d13438'           # 错误色
    },
    'fonts': {
        'default': ('微软雅黑', 10),
        'header': ('微软雅黑', 12, 'bold'),
        'mono': ('Consolas', 10)
    }
}

# 图表配置
CHART_CONFIG = {
    'figsize': (10, 6),
    'dpi': 100,
    'style': 'seaborn-v0_8',  # matplotlib样式
    'colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
    'grid': True,
    'legend': True
}

# =============================================================================
# 数据处理配置
# =============================================================================

# Excel文件配置
EXCEL_CONFIG = {
    'supported_extensions': ['.json'],
    'required_columns': ['行业', '股票代码', '股票名称'],
    'date_pattern': r'202\d{5}',  # 日期列格式
    'encoding': 'utf-8'
}

# 数据验证配置
VALIDATION_CONFIG = {
    'min_stocks': 100,           # 最少股票数
    'min_date_columns': 5,       # 最少日期列
    'max_missing_rate': 0.9,     # 最大缺失率
    'industry_column': '行业',
    'code_column': '股票代码',
    'name_column': '股票名称'
}

# =============================================================================
# 缓存配置
# =============================================================================

# 缓存设置
CACHE_CONFIG = {
    'enable_cache': True,        # 启用缓存
    'cache_timeout': 3600,       # 缓存超时(秒)
    'max_cache_size': 1000,      # 最大缓存条目
    'cache_dir': os.path.join(BASE_DIR, '.cache')
}

# =============================================================================
# 日志配置
# =============================================================================

# 日志设置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_path': os.path.join(BASE_DIR, 'logs', 'app.log'),
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5
}

# =============================================================================
# 工具函数
# =============================================================================

def get_config(section: str, key: str = None, default: Any = None) -> Any:
    """
    获取配置值
    
    Args:
        section: 配置段名
        key: 配置键名 (可选)
        default: 默认值
        
    Returns:
        配置值
    """
    config_map = {
        'market': MARKET_CONFIG,
        'rating': RATING_SCORE_MAP,
        'rtsi': RTSI_CONFIG,
        'irsi': IRSI_CONFIG,
        'msci': MSCI_CONFIG,
        'gui': GUI_CONFIG,
        'chart': CHART_CONFIG,
        'excel': EXCEL_CONFIG,
        'validation': VALIDATION_CONFIG,
        'cache': CACHE_CONFIG,
        'logging': LOGGING_CONFIG
    }
    
    section_config = config_map.get(section)
    if section_config is None:
        return default
    
    if key is None:
        return section_config
    
    return section_config.get(key, default)

def get_market_info(market_code: str = DEFAULT_MARKET) -> Dict[str, Any]:
    """获取市场信息"""
    return MARKET_CONFIG.get(market_code, MARKET_CONFIG[DEFAULT_MARKET])

def is_valid_market(market_code: str) -> bool:
    """检查市场代码是否有效"""
    return market_code in MARKET_CONFIG

# =============================================================================
# 配置验证
# =============================================================================

def validate_config() -> bool:
    """验证配置完整性"""
    try:
        # 检查必要目录
        if not os.path.exists(BASE_DIR):
            raise ValueError(f"基础目录不存在: {BASE_DIR}")
        
        # 检查市场配置
        for market_code, config in MARKET_CONFIG.items():
            required_keys = ['name', 'description', 'code_pattern', 'filename']
            for key in required_keys:
                if key not in config:
                    raise ValueError(f"市场配置缺失: {market_code}.{key}")
        
        # 检查评级配置
        if len(RATING_SCORE_MAP) < 7:
            raise ValueError("评级映射配置不完整")
        
        return True
        
    except Exception as e:
        print(f"配置验证失败: {e}")
        return False

# =============================================================================
# 高级配置功能
# =============================================================================

class ConfigManager:
    """配置管理器 - 动态配置管理"""
    
    def __init__(self):
        self.user_config_file = os.path.join(BASE_DIR, 'user_config.json')
        self.runtime_config = {}
        self.load_user_config()
    
    def load_user_config(self):
        """加载用户配置"""
        try:
            if os.path.exists(self.user_config_file):
                import json
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    self.runtime_config = json.load(f)
                print(f"用户配置加载成功: {len(self.runtime_config)}项")
            else:
                self.runtime_config = {}
                print("")
        except Exception as e:
            print(f"用户配置加载失败: {e}")
            self.runtime_config = {}
    
    def save_user_config(self):
        """保存用户配置"""
        try:
            import json
            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.runtime_config, f, ensure_ascii=False, indent=2)
            print("")
            return True
        except Exception as e:
            print(f"用户配置保存失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值 (优先用户配置)"""
        return self.runtime_config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        self.runtime_config[key] = value
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.runtime_config = {}
        print("")
    
    def export_config(self, file_path: str = None) -> str:
        """导出配置"""
        try:
            if file_path is None:
                file_path = f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            export_data = {
                'export_time': datetime.now().isoformat(),
                'app_version': VERSION,
                'user_config': self.runtime_config,
                'default_configs': {
                    'market': MARKET_CONFIG,
                    'rtsi': RTSI_CONFIG,
                    'irsi': IRSI_CONFIG,
                    'msci': MSCI_CONFIG,
                    'gui': GUI_CONFIG
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"配置导出成功: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"配置导出失败: {e}")
            return ""

# 全局配置管理器实例
config_manager = ConfigManager()

def get_user_config(key: str, default: Any = None) -> Any:
    """获取用户配置 (便捷函数)"""
    return config_manager.get(key, default)

def set_user_config(key: str, value: Any):
    """设置用户配置 (便捷函数)"""
    config_manager.set(key, value)

def save_config():
    """保存配置 (便捷函数)"""
    return config_manager.save_user_config()

# =============================================================================
# 配置预设
# =============================================================================

CONFIG_PRESETS = {
    'conservative': {
        'name': '保守分析',
        'description': '适合稳健投资者的保守配置',
        'rtsi': {
            'strong_trend_threshold': 0.15,
            'significance_threshold': 0.6
        },
        'irsi': {
            'strong_outperform_threshold': 25,
            'strong_underperform_threshold': -25
        },
        'msci': {
            'euphoric_threshold': 65,
            'pessimistic_threshold': 20
        }
    },
    'aggressive': {
        'name': '激进分析',
        'description': '适合激进投资者的敏感配置',
        'rtsi': {
            'strong_trend_threshold': 0.05,
            'significance_threshold': 0.3
        },
        'irsi': {
            'strong_outperform_threshold': 10,
            'strong_underperform_threshold': -10
        },
        'msci': {
            'euphoric_threshold': 75,
            'pessimistic_threshold': 10
        }
    },
    'balanced': {
        'name': '平衡分析',
        'description': '适合大多数用户的平衡配置',
        'rtsi': {
            'strong_trend_threshold': 0.1,
            'significance_threshold': 0.5
        },
        'irsi': {
            'strong_outperform_threshold': 20,
            'strong_underperform_threshold': -20
        },
        'msci': {
            'euphoric_threshold': 70,
            'pessimistic_threshold': 15
        }
    }
}

def apply_preset(preset_name: str) -> bool:
    """应用配置预设"""
    if preset_name not in CONFIG_PRESETS:
        print(f"配置预设不存在: {preset_name}")
        return False
    
    preset = CONFIG_PRESETS[preset_name]
    print(f"应用配置预设: {preset['name']} - {preset['description']}")
    
    try:
        # 更新全局配置
        if 'rtsi' in preset:
            RTSI_CONFIG.update(preset['rtsi'])
        if 'irsi' in preset:
            IRSI_CONFIG.update(preset['irsi'])
        if 'msci' in preset:
            MSCI_CONFIG.update(preset['msci'])
        
        # 保存到用户配置
        config_manager.set('active_preset', preset_name)
        config_manager.set('preset_configs', preset)
        
        print(f"配置预设应用成功: {preset_name}")
        return True
        
    except Exception as e:
        print(f"配置预设应用失败: {e}")
        return False

def get_available_presets() -> Dict[str, str]:
    """获取可用的配置预设"""
    return {name: config['description'] for name, config in CONFIG_PRESETS.items()}

# =============================================================================
# 配置监控和诊断
# =============================================================================

def diagnose_system() -> Dict[str, Any]:
    """系统配置诊断"""
    import sys
    import platform
    from datetime import datetime
    
    diagnosis = {
        'timestamp': datetime.now().isoformat(),
        'system_info': {
            'platform': platform.platform(),
            'python_version': sys.version,
            'architecture': platform.architecture(),
            'processor': platform.processor()
        },
        'app_info': {
            'name': APP_NAME,
            'version': VERSION,
            'base_dir': BASE_DIR,
            'data_dir': DATA_DIR
        },
        'config_status': {
            'validation_passed': validate_config(),
            'user_config_exists': os.path.exists(config_manager.user_config_file),
            'user_config_items': len(config_manager.runtime_config),
            'active_preset': config_manager.get('active_preset', 'default')
        },
        'directory_status': {
            'base_dir_exists': os.path.exists(BASE_DIR),
            'data_dir_exists': os.path.exists(DATA_DIR),
            'industry_guides_dir_exists': os.path.exists(INDUSTRY_GUIDES_DIR),
            'cache_dir_exists': os.path.exists(CACHE_CONFIG['cache_dir'])
        },
        'market_config': {
            'available_markets': list(MARKET_CONFIG.keys()),
            'default_market': DEFAULT_MARKET,
            'total_markets': len(MARKET_CONFIG)
        }
    }
    
    return diagnosis

def print_system_info():
    """打印系统信息"""
    diagnosis = diagnose_system()
    
    print("" * 60)
    print(f"{APP_NAME} v{VERSION} - 系统诊断报告")
    print("" * 60)
    
    print(f"\n🖥️  系统环境:")
    print(f"   平台: {diagnosis['system_info']['platform']}")
    print(f"   Python: {diagnosis['system_info']['python_version'].split()[0]}")
    
    print(f"\n文件 目录状态:")
    for name, exists in diagnosis['directory_status'].items():
        status = "成功" if exists else "错误"
        print(f"   {status} {name.replace('_', ' ').title()}")
    
    print(f"\n⚙️  配置状态:")
    print(f"   配置验证: {'成功 通过' if diagnosis['config_status']['validation_passed'] else '错误 失败'}")
    print(f"   用户配置: {'成功 存在' if diagnosis['config_status']['user_config_exists'] else '错误 不存在'}")
    print(f"   配置项数: {diagnosis['config_status']['user_config_items']}")
    print(f"   活动预设: {diagnosis['config_status']['active_preset']}")
    
    print(f"\n🌍 市场配置:")
    print(f"   支持市场: {', '.join(diagnosis['market_config']['available_markets'])}")
    print(f"   默认市场: {diagnosis['market_config']['default_market']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    print_system_info()
    
    # 配置功能测试
    print("\n测试 配置功能测试:")
    
    # 测试预设应用
    print("...")
    apply_preset('balanced')
    
    # 测试用户配置
    print("...")
    set_user_config('test_key', 'test_value')
    print(f"    设置值: {get_user_config('test_key')}")
    
    # 测试配置导出
    print("...")
    export_file = config_manager.export_config()
    if export_file:
        print(f"    导出成功: {export_file}")
    
    print("\n成功 配置系统测试完成")

# 用户配置文件路径
USER_CONFIG_PATH = Path.home() / '.stock_analyzer_config.json'

# 默认用户配置
DEFAULT_USER_CONFIG = {
    'window': {
        'theme': 'professional',
        'font_size': 11,
        'auto_center': True,
        'remember_size': True
    },
    'data': {
        'auto_load_last_file': False,
        'default_data_dir': '',
        'backup_enabled': True
    },
    'analysis': {
        'auto_refresh_interval': 300,  # 5分钟
        'cache_enabled': True,
        'detailed_logging': False
    },
    'reports': {
        'default_format': 'html',
        'auto_open_browser': True,
        'export_directory': 'reports'
    }
}

def load_user_config() -> Dict[str, Any]:
    """加载用户配置文件"""
    try:
        if USER_CONFIG_PATH.exists():
            with open(USER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return {**DEFAULT_USER_CONFIG, **config}
        else:
            # 首次运行，创建默认配置文件
            save_user_config(DEFAULT_USER_CONFIG)
            print("")
            return DEFAULT_USER_CONFIG.copy()
    except Exception as e:
        print(f"加载用户配置失败，使用默认配置: {e}")
        return DEFAULT_USER_CONFIG.copy()

def save_user_config(config: Dict[str, Any]) -> bool:
    """保存用户配置文件"""
    try:
        # 确保目录存在
        USER_CONFIG_PATH.parent.mkdir(exist_ok=True)
        
        with open(USER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存用户配置失败: {e}")
        return False

def get_config_value(key_path: str, default: Any = None) -> Any:
    """获取配置值"""
    config = load_user_config()
    keys = key_path.split('.')
    value = config
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

def set_config_value(key_path: str, value: Any) -> bool:
    """设置配置值"""
    config = load_user_config()
    keys = key_path.split('.')
    
    try:
        # 导航到父级字典
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 设置值
        current[keys[-1]] = value
        
        return save_user_config(config)
    except Exception as e:
        print(f"设置配置值失败: {e}")
        return False