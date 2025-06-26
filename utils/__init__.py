"""
工具模块包

提供股票分析系统的通用工具功能，包括缓存管理、性能监控等。

模块列表:
- cache_manager: 缓存管理系统
- performance_monitor: 性能监控工具

作者: 267278466@qq.com
版本: 1.0.0
"""

from .cache_manager import (
    AnalysisCache,
    CacheEntry,
    get_global_cache,
    cache_analysis_result,
    get_cached_analysis,
    clear_analysis_cache
)

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    get_global_monitor,
    monitor_execution_time,
    memory_usage_tracker,
    generate_performance_report,
    reset_performance_metrics,
    get_performance_stats
)

from .report_generator import (
    ReportGenerator,
    ExcelReportGenerator,
    generate_report_quick,
    create_excel_report_quick
)

# 版本信息
__version__ = "2.0.0"
__author__ = "267278466@qq.com"

# 导出的公共接口
__all__ = [
    # 缓存管理
    'AnalysisCache',
    'CacheEntry', 
    'get_global_cache',
    'cache_analysis_result',
    'get_cached_analysis',
    'clear_analysis_cache',
    
    # 性能监控
    'PerformanceMonitor',
    'PerformanceMetrics',
    'get_global_monitor',
    'monitor_execution_time',
    'memory_usage_tracker',
    'generate_performance_report',
    'reset_performance_metrics',
    'get_performance_stats',
    
    # 报告生成
    'ReportGenerator',
    'ExcelReportGenerator',
    'generate_report_quick',
    'create_excel_report_quick'
]


def get_utils_info() -> dict:
    """获取工具模块信息"""
    return {
        'version': __version__,
        'author': __author__,
        'modules': {
            'cache_manager': '缓存管理系统 - 提供多层次缓存功能',
            'performance_monitor': '性能监控工具 - 提供执行时间和资源监控'
        },
        'features': [
            '内存缓存和文件缓存',
            '自动过期清理',
            'LRU淘汰策略',
            '函数执行时间监控',
            '系统资源监控',
            '性能报告生成'
        ]
    }


if __name__ == "__main__":
    # 工具模块导入
# 模块已加载
    
    info = get_utils_info()
    print(f"\n版本: {info['version']}")
    print(f"作者: {info['author']}")
    print("\n模块列表:")
    for module, desc in info['modules'].items():
        print(f"  - {module}: {desc}")
    
    print("\n主要功能:")
    for feature in info['features']:
        print(f"  - {feature}")
    
    print("\n成功 Utils模块包信息显示完成")