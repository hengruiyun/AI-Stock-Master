"""
from config.i18n import t_gui as _
性能监控模块

提供全面的性能监控功能，包括函数执行时间监控、内存使用追踪、
系统资源监控和性能报告生成。

作者: 267278466@qq.com
版本: 1.0.0
"""

import time
import psutil
import threading
import functools
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict, deque
import gc

from config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """性能指标数据类"""
    
    def __init__(self, name: str):
        self.name = name
        self.call_count = 0
        self.total_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0
        self.avg_time = 0.0
        self.last_execution_time = None
        self.error_count = 0
        self.memory_usage_history = deque(maxlen=100)  # 保存最近100次内存使用记录
        self.execution_history = deque(maxlen=50)  # 保存最近50次执行时间
    
    def add_execution(self, execution_time: float, memory_usage: float = None, error: bool = False):
        """添加执行记录"""
        self.call_count += 1
        self.last_execution_time = datetime.now()
        
        if error:
            self.error_count += 1
            return
        
        # 更新时间统计
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / (self.call_count - self.error_count)
        
        # 记录历史
        self.execution_history.append({
            'time': execution_time,
            'timestamp': datetime.now(),
            'memory': memory_usage
        })
        
        if memory_usage is not None:
            self.memory_usage_history.append({
                'usage': memory_usage,
                'timestamp': datetime.now()
            })
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.call_count == 0:
            return 0.0
        return (self.call_count - self.error_count) / self.call_count
    
    def get_trend(self, window: int = 10) -> str:
        """获取性能趋势"""
        if len(self.execution_history) < window:
            return "insufficient_data"
        
        recent = list(self.execution_history)[-window:]
        early = recent[:window//2]
        late = recent[window//2:]
        
        early_avg = sum(r['time'] for r in early) / len(early)
        late_avg = sum(r['time'] for r in late) / len(late)
        
        change_rate = (late_avg - early_avg) / early_avg
        
        if change_rate > 0.1:
            return "degrading"
        elif change_rate < -0.1:
            return "improving"
        else:
            return "stable"
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'name': self.name,
            'call_count': self.call_count,
            'error_count': self.error_count,
            'success_rate': self.get_success_rate(),
            'timing': {
                'total_time': round(self.total_time, 4),
                'avg_time': round(self.avg_time, 4),
                'min_time': round(self.min_time, 4),
                'max_time': round(self.max_time, 4)
            },
            'trend': self.get_trend(),
            'last_execution': self.last_execution_time.isoformat() if self.last_execution_time else None
        }


class PerformanceMonitor:
    """
    性能监控器
    
    功能特性:
    - 函数执行时间监控
    - 内存使用追踪
    - 系统资源监控
    - 性能趋势分析
    - 报告生成
    """
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.system_metrics = {
            'cpu_usage_history': deque(maxlen=100),
            'memory_usage_history': deque(maxlen=100),
            'disk_io_history': deque(maxlen=100)
        }
        self.monitoring_lock = threading.Lock()
        self.start_time = datetime.now()
        
        # 配置参数
        try:
            self.config = get_config('performance', {
                'enable_memory_tracking': True,
                'enable_system_monitoring': True,
                'monitoring_interval': 60,  # 系统监控间隔(秒)
                'alert_threshold': 5.0,     # 性能告警阈值(秒)
                'max_memory_mb': float('inf')  # 无内存使用限制
            })
            # 如果get_config返回None，使用默认配置
            if self.config is None:
                self.config = {
                    'enable_memory_tracking': True,
                    'enable_system_monitoring': True,
                    'monitoring_interval': 60,
                    'alert_threshold': 5.0,
                    'max_memory_mb': 500
                }
        except Exception:
            # 如果配置获取失败，使用默认配置
            self.config = {
                'enable_memory_tracking': True,
                'enable_system_monitoring': True,
                'monitoring_interval': 60,
                'alert_threshold': 5.0,
                'max_memory_mb': 500
            }
        
        # 启动系统监控
        if self.config['enable_system_monitoring']:
            self._start_system_monitoring()
        
        logger.info("性能监控器初始化完成")
    
    def _start_system_monitoring(self):
        """启动系统监控线程"""
        def system_monitor():
            while True:
                try:
                    # CPU使用率
                    cpu_percent = psutil.cpu_percent(interval=1)
                    
                    # 内存使用
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                    memory_mb = memory.used / 1024 / 1024
                    
                    # 磁盘IO (如果可用)
                    try:
                        disk_io = psutil.disk_io_counters()
                        disk_read_mb = disk_io.read_bytes / 1024 / 1024
                        disk_write_mb = disk_io.write_bytes / 1024 / 1024
                    except Exception:
                        disk_read_mb = disk_write_mb = 0
                    
                    timestamp = datetime.now()
                    
                    with self.monitoring_lock:
                        self.system_metrics['cpu_usage_history'].append({
                            'value': cpu_percent,
                            'timestamp': timestamp
                        })
                        
                        self.system_metrics['memory_usage_history'].append({
                            'percent': memory_percent,
                            'mb': memory_mb,
                            'timestamp': timestamp
                        })
                        
                        self.system_metrics['disk_io_history'].append({
                            'read_mb': disk_read_mb,
                            'write_mb': disk_write_mb,
                            'timestamp': timestamp
                        })
                    
                    # 检查告警 (如果有限制的话)
                    if self.config['max_memory_mb'] != float('inf') and memory_mb > self.config['max_memory_mb']:
                        logger.warning(f"内存使用过高: {memory_mb:.1f}MB > {self.config['max_memory_mb']}MB")
                    
                except Exception as e:
                    logger.error(f"系统监控错误: {e}")
                
                time.sleep(self.config['monitoring_interval'])
        
        monitor_thread = threading.Thread(target=system_monitor, daemon=True)
        monitor_thread.start()
    
    def get_memory_usage(self) -> float:
        """获取当前进程内存使用(MB)"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def record_execution(self, function_name: str, execution_time: float, 
                        memory_usage: float = None, error: bool = False):
        """记录函数执行信息"""
        with self.monitoring_lock:
            if function_name not in self.metrics:
                self.metrics[function_name] = PerformanceMetrics(function_name)
            
            if memory_usage is None and self.config['enable_memory_tracking']:
                memory_usage = self.get_memory_usage()
            
            self.metrics[function_name].add_execution(execution_time, memory_usage, error)
            
            # 性能告警
            if not error and execution_time > self.config['alert_threshold']:
                logger.warning(f"性能告警: {function_name} 执行时间 {execution_time:.2f}s 超过阈值 {self.config['alert_threshold']}s")
    
    def get_function_metrics(self, function_name: str) -> Optional[Dict]:
        """获取指定函数的性能指标"""
        with self.monitoring_lock:
            if function_name in self.metrics:
                return self.metrics[function_name].to_dict()
            return None
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        """获取所有函数的性能指标"""
        with self.monitoring_lock:
            return {name: metrics.to_dict() for name, metrics in self.metrics.items()}
    
    def get_system_metrics(self) -> Dict:
        """获取系统性能指标"""
        with self.monitoring_lock:
            current_memory = self.get_memory_usage()
            
            # 计算平均值
            cpu_history = list(self.system_metrics['cpu_usage_history'])
            memory_history = list(self.system_metrics['memory_usage_history'])
            
            avg_cpu = sum(h['value'] for h in cpu_history[-10:]) / min(10, len(cpu_history)) if cpu_history else 0
            avg_memory = sum(h['percent'] for h in memory_history[-10:]) / min(10, len(memory_history)) if memory_history else 0
            
            return {
                'current': {
                    'memory_mb': current_memory,
                    'cpu_percent': psutil.cpu_percent() if hasattr(psutil, 'cpu_percent') else 0,
                    'memory_percent': psutil.virtual_memory().percent if hasattr(psutil, 'virtual_memory') else 0
                },
                'averages': {
                    'cpu_percent': round(avg_cpu, 2),
                    'memory_percent': round(avg_memory, 2)
                },
                'history_length': {
                    'cpu': len(cpu_history),
                    'memory': len(memory_history)
                },
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
            }
    
    def get_top_functions(self, metric: str = 'avg_time', top_n: int = 10) -> List[Dict]:
        """获取性能排名"""
        with self.monitoring_lock:
            metrics_list = []
            for name, metrics in self.metrics.items():
                metric_dict = metrics.to_dict()
                if metric == 'avg_time':
                    sort_key = metric_dict['timing']['avg_time']
                elif metric == 'total_time':
                    sort_key = metric_dict['timing']['total_time']
                elif metric == 'call_count':
                    sort_key = metric_dict['call_count']
                elif metric == 'error_rate':
                    sort_key = 1 - metric_dict['success_rate']
                else:
                    sort_key = 0
                
                metrics_list.append({
                    'name': name,
                    'sort_key': sort_key,
                    'metrics': metric_dict
                })
            
            metrics_list.sort(key=lambda x: x['sort_key'], reverse=True)
            return [item['metrics'] for item in metrics_list[:top_n]]
    
    def reset_metrics(self, function_name: str = None):
        """重置性能指标"""
        with self.monitoring_lock:
            if function_name:
                if function_name in self.metrics:
                    del self.metrics[function_name]
                    logger.info(f"已重置 {function_name} 的性能指标")
            else:
                self.metrics.clear()
                self.system_metrics = {
                    'cpu_usage_history': deque(maxlen=100),
                    'memory_usage_history': deque(maxlen=100),
                    'disk_io_history': deque(maxlen=100)
                }
                self.start_time = datetime.now()
                logger.info("已重置所有性能指标")
    
    def generate_performance_report(self) -> str:
        """生成性能报告"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("AI股票大师 - 性能监控报告")
        report_lines.append("=" * 60)
        report_lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"系统运行时间: {(datetime.now() - self.start_time)}")
        report_lines.append("")
        
        # 系统概览
        system_metrics = self.get_system_metrics()
        report_lines.append("数据 系统资源概览")
        report_lines.append("-" * 30)
        report_lines.append(f"当前内存使用: {system_metrics['current']['memory_mb']:.1f}MB")
        report_lines.append(f"当前CPU使用: {system_metrics['current']['cpu_percent']:.1f}%")
        report_lines.append(f"平均CPU使用: {system_metrics['averages']['cpu_percent']:.1f}%")
        report_lines.append(f"平均内存使用: {system_metrics['averages']['memory_percent']:.1f}%")
        report_lines.append("")
        
        # 函数性能排名
        report_lines.append("快速 函数执行时间排名 (Top 10)")
        report_lines.append("-" * 50)
        top_functions = self.get_top_functions('avg_time', 10)
        for i, func in enumerate(top_functions, 1):
            timing = func['timing']
            report_lines.append(
                f"{i:2d}. {func['name']:<25} "
                f"平均: {timing['avg_time']:.3f}s "
                f"调用: {func['call_count']:>4}次 "
                f"趋势: {func['trend']}"
            )
        report_lines.append("")
        
        # 调用次数排名
        report_lines.append("上涨 函数调用次数排名 (Top 5)")
        report_lines.append("-" * 40)
        top_calls = self.get_top_functions('call_count', 5)
        for i, func in enumerate(top_calls, 1):
            report_lines.append(
                f"{i}. {func['name']:<25} {func['call_count']:>6}次调用 "
                f"成功率: {func['success_rate']:.1%}"
            )
        report_lines.append("")
        
        # 错误率统计
        error_functions = [f for f in self.get_all_metrics().values() if f['error_count'] > 0]
        if error_functions:
            report_lines.append("警告  错误统计")
            report_lines.append("-" * 20)
            for func in sorted(error_functions, key=lambda x: x['error_count'], reverse=True):
                error_rate = (1 - func['success_rate']) * 100
                report_lines.append(
                    f"{func['name']:<25} 错误: {func['error_count']:>3}次 "
                    f"错误率: {error_rate:.1f}%"
                )
            report_lines.append("")
        
        # 性能建议
        report_lines.append("提示 性能建议")
        report_lines.append("-" * 15)
        
        # 慢函数建议
        slow_functions = [f for f in self.get_all_metrics().values() 
                         if f['timing']['avg_time'] > self.config['alert_threshold']]
        if slow_functions:
            report_lines.append("• 以下函数执行时间较长，建议优化:")
            for func in slow_functions[:3]:
                report_lines.append(f"  - {func['name']}: {func['timing']['avg_time']:.3f}s")
        
        # 内存建议
        current_memory = system_metrics['current']['memory_mb']
        if current_memory > self.config['max_memory_mb']:
            report_lines.append(f"• 内存使用过高 ({current_memory:.1f}MB)，建议清理缓存或优化数据结构")
        
        # 趋势建议
        degrading_functions = [f for f in self.get_all_metrics().values() if f['trend'] == 'degrading']
        if degrading_functions:
            report_lines.append("• 以下函数性能呈下降趋势:")
            for func in degrading_functions[:3]:
                report_lines.append(f"  - {func['name']}")
        
        if not slow_functions and current_memory <= self.config['max_memory_mb'] and not degrading_functions:
            report_lines.append("• 系统性能良好，无明显瓶颈")
        
        report_lines.append("")
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)


# 全局监控实例
_global_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_global_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    global _global_monitor
    
    if _global_monitor is None:
        with _monitor_lock:
            if _global_monitor is None:
                _global_monitor = PerformanceMonitor()
    
    return _global_monitor


def monitor_execution_time(function: Callable = None, *, name: str = None):
    """
    装饰器：监控函数执行时间
    
    Args:
        function: 被装饰的函数
        name: 自定义函数名称
    """
    def decorator(func):
        func_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_global_monitor()
            start_time = time.time()
            error_occurred = False
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error_occurred = True
                raise
            finally:
                execution_time = time.time() - start_time
                monitor.record_execution(func_name, execution_time, error=error_occurred)
        
        return wrapper
    
    if function is None:
        return decorator
    else:
        return decorator(function)


def memory_usage_tracker() -> Dict:
    """获取当前内存使用情况"""
    monitor = get_global_monitor()
    return {
        'process_memory_mb': monitor.get_memory_usage(),
        'system_memory_percent': psutil.virtual_memory().percent,
        'timestamp': datetime.now().isoformat()
    }


def generate_performance_report() -> str:
    """生成性能报告"""
    monitor = get_global_monitor()
    return monitor.generate_performance_report()


def reset_performance_metrics(function_name: str = None):
    """重置性能指标"""
    monitor = get_global_monitor()
    monitor.reset_metrics(function_name)


def get_performance_stats() -> Dict:
    """获取完整的性能统计信息"""
    monitor = get_global_monitor()
    return {
        'function_metrics': monitor.get_all_metrics(),
        'system_metrics': monitor.get_system_metrics(),
        'top_functions': {
            'by_avg_time': monitor.get_top_functions('avg_time', 5),
            'by_total_time': monitor.get_top_functions('total_time', 5),
            'by_call_count': monitor.get_top_functions('call_count', 5)
        }
    }


if __name__ == "__main__":
    # 测试代码
    print("-")
    
    try:
        # 创建测试监控器
        monitor = PerformanceMonitor()
        
        # 测试函数装饰器
        @monitor_execution_time
        def test_function(delay: float = 0.1):
            """测试函数"""
            time.sleep(delay)
            return f"执行完成 (延迟: {delay}s)"
        
        @monitor_execution_time(name="custom_test_function")
        def test_function_with_error():
            """会出错的测试函数"""
            if time.time() % 2 < 1:  # 随机出错
                raise ValueError("测试错误")
            return "成功执行"
        
        # 执行测试
        print("\n=== 测试函数执行监控 ===")
        for i in range(5):
            result = test_function(0.05 + i * 0.01)
            print(f"执行 {i+1}: {result}")
        
        # 测试错误处理
        print("\n=== 测试错误监控 ===")
        for i in range(3):
            try:
                test_function_with_error()
                print(f"执行 {i+1}: 成功")
            except ValueError:
                print(f"执行 {i+1}: 出错")
        
        # 等待一段时间让系统监控收集数据
        print("\n等待系统监控数据...")
        time.sleep(2)
        
        # 获取性能指标
        print("\n=== 性能指标 ===")
        all_metrics = monitor.get_all_metrics()
        for name, metrics in all_metrics.items():
            print(f"{name}:")
            print(f"  调用次数: {metrics['call_count']}")
            print(f"  平均时间: {metrics['timing']['avg_time']:.4f}s")
            print(f"  成功率: {metrics['success_rate']:.1%}")
            print(f"  趋势: {metrics['trend']}")
        
        # 系统指标
        print("\n=== 系统指标 ===")
        system_metrics = monitor.get_system_metrics()
        print(f"当前内存: {system_metrics['current']['memory_mb']:.1f}MB")
        print(f"CPU使用: {system_metrics['current']['cpu_percent']:.1f}%")
        
        # 生成报告
        print("\n=== 性能报告 ===")
        report = monitor.generate_performance_report()
        print(report)
        
        print("\n成功 性能监控器测试完成")
        
    except Exception as e:
        print(f"错误 测试失败: {e}")
        import traceback
        traceback.print_exc()