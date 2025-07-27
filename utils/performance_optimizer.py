# -*- coding: utf-8 -*-
"""
from config.i18n import t_gui as _
性能优化器 - 第六期测试与优化

功能：
1. 系统性能监控
2. 自动优化建议
3. 内存管理优化
4. 缓存策略优化
5. 算法性能分析

作者：267278466@qq.com
版本：1.0.0
"""

import sys
import os
import time
import gc
from pathlib import Path
from typing import Dict, List, Any
import warnings

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.metrics = {}
        self.optimization_results = []
        print("")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        metrics = {}
        
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics['cpu_usage'] = {
                'value': cpu_percent,
                'unit': '%',
                'status': 'good' if cpu_percent < 50 else 'warning' if cpu_percent < 80 else 'critical'
            }
            
            # 内存使用
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = {
                'value': memory.percent,
                'unit': '%',
                'absolute_mb': memory.used / 1024 / 1024,
                'status': 'good'  # 无内存限制约束
            }
            
        except ImportError:
            # 使用基础内存检测
            import resource
            memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_mb = memory_usage / 1024 if sys.platform != 'darwin' else memory_usage / 1024 / 1024
            
            metrics['memory_simple'] = {
                'value': memory_mb,
                'unit': 'MB',
                'status': 'good'  # 无内存限制，总是显示为良好
            }
        
        except Exception as e:
            print(f"警告 获取系统指标失败: {e}")
        
        return metrics
    
    def analyze_performance(self) -> Dict[str, Any]:
        """性能分析"""
        print("...")
        
        # 获取系统指标
        system_metrics = self.get_system_metrics()
        
        # 分析缓存性能
        cache_metrics = self.analyze_cache_performance()
        
        # 合并指标
        all_metrics = {**system_metrics, **cache_metrics}
        
        # 计算健康度
        status_counts = {'good': 0, 'warning': 0, 'critical': 0}
        for metric in all_metrics.values():
            status = metric.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
        
        total = sum(status_counts.values())
        health_score = (status_counts['good'] / total * 100) if total > 0 else 0
        
        # 生成建议
        recommendations = self.generate_recommendations(all_metrics)
        
        result = {
            'metrics': all_metrics,
            'health_score': health_score,
            'status_counts': status_counts,
            'recommendations': recommendations
        }
        
        self.metrics = all_metrics
        print(f"成功 性能分析完成，健康度: {health_score:.1f}%")
        
        return result
    
    def analyze_cache_performance(self) -> Dict[str, Any]:
        """分析缓存性能"""
        cache_metrics = {}
        
        try:
            from utils.cache_manager import get_global_cache
            cache = get_global_cache()
            
            if cache:
                stats = cache.get_cache_stats()
                
                # 缓存命中率
                hit_rate = stats.get('performance_stats', {}).get('hit_rate', 0)
                cache_metrics['cache_hit_rate'] = {
                    'value': hit_rate * 100,
                    'unit': '%',
                    'status': 'good' if hit_rate > 0.7 else 'warning' if hit_rate > 0.4 else 'critical'
                }
                
                # 缓存内存使用
                memory_usage = stats.get('memory_stats', {}).get('memory_usage_mb', 0)
                cache_metrics['cache_memory'] = {
                    'value': memory_usage,
                    'unit': 'MB',
                    'status': 'good' if memory_usage < 50 else 'warning' if memory_usage < 100 else 'critical'
                }
        
        except Exception as e:
            print(f"警告 缓存性能分析失败: {e}")
        
        return cache_metrics
    
    def generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 检查关键指标
        critical_items = [name for name, metric in metrics.items() if metric.get('status') == 'critical']
        warning_items = [name for name, metric in metrics.items() if metric.get('status') == 'warning']
        
        if critical_items:
            recommendations.append("🚨 关键性能问题：")
            for item in critical_items:
                if 'memory' in item:
                    recommendations.append("  • 内存使用过高，建议释放不必要的数据")
                elif 'cpu' in item:
                    recommendations.append("  • CPU使用率过高，建议优化计算密集型操作")
                elif 'cache' in item:
                    recommendations.append("  • 缓存性能不佳，建议调整缓存策略")
        
        if warning_items:
            recommendations.append("警告 性能警告：")
            for item in warning_items:
                if 'memory' in item:
                    recommendations.append("  • 考虑进行内存清理和优化")
                elif 'cache' in item:
                    recommendations.append("  • 考虑优化缓存配置")
        
        # 通用建议
        if not critical_items and not warning_items:
            recommendations.append("🎉 系统性能良好")
        else:
            recommendations.extend([
                "提示 通用优化建议：",
                "  • 定期执行垃圾回收",
                "  • 优化数据处理流程",
                "  • 使用更高效的算法",
                "  • 考虑增加缓存使用"
            ])
        
        return recommendations
    
    def apply_optimizations(self) -> List[Dict[str, Any]]:
        """应用自动优化"""
        print("...")
        
        results = []
        
        # 1. 内存优化
        memory_before = self.get_memory_usage()
        try:
            gc.collect()  # 强制垃圾回收
            
            # 清理缓存
            try:
                from utils.cache_manager import get_global_cache
                cache = get_global_cache()
                if cache:
                    cleared = cache.clear_expired_cache()
                    print(f"   清理过期缓存: {cleared}项")
            except Exception:
                pass
            
            memory_after = self.get_memory_usage()
            memory_saved = memory_before - memory_after
            
            results.append({
                'type': '内存优化',
                'before': memory_before,
                'after': memory_after,
                'improvement': memory_saved,
                'success': memory_saved > 0
            })
            
        except Exception as e:
            print(f"   内存优化失败: {e}")
        
        # 2. 系统优化
        try:
            # 调整垃圾回收阈值
            gc.set_threshold(700, 10, 10)
            
            # 抑制警告
            warnings.filterwarnings('ignore', category=UserWarning)
            
            results.append({
                'type': '系统调优',
                'description': '调整垃圾回收参数和警告设置',
                'success': True
            })
            
        except Exception as e:
            print(f"   系统优化失败: {e}")
        
        self.optimization_results = results
        print(f"成功 优化完成，应用了{len(results)}项优化")
        
        return results
    
    def get_memory_usage(self) -> float:
        """获取内存使用量(MB)"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / 1024 / 1024
        except ImportError:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return usage / 1024 / 1024 if sys.platform == 'darwin' else usage / 1024
        except Exception:
            return 0
    
    def generate_report(self) -> str:
        """生成优化报告"""
        if not self.metrics:
            return "暂无性能数据"
        
        lines = []
        lines.append("数据 性能优化报告")
        lines.append("=" * 40)
        
        # 性能指标
        good_count = len([m for m in self.metrics.values() if m.get('status') == 'good'])
        warning_count = len([m for m in self.metrics.values() if m.get('status') == 'warning'])
        critical_count = len([m for m in self.metrics.values() if m.get('status') == 'critical'])
        total = len(self.metrics)
        
        lines.append(f"\n核心 性能指标:")
        lines.append(f"  总指标: {total}")
        lines.append(f"  良好: {good_count} ({good_count/total*100:.1f}%)")
        lines.append(f"  警告: {warning_count} ({warning_count/total*100:.1f}%)")
        lines.append(f"  关键: {critical_count} ({critical_count/total*100:.1f}%)")
        
        # 详细指标
        lines.append(f"\n上涨 详细指标:")
        for name, metric in self.metrics.items():
            status_icon = "成功" if metric['status'] == 'good' else "警告" if metric['status'] == 'warning' else "🚨"
            lines.append(f"  {status_icon} {name}: {metric['value']:.2f}{metric['unit']}")
        
        # 优化结果
        if self.optimization_results:
            lines.append(f"\n配置 优化结果:")
            for result in self.optimization_results:
                if result['success']:
                    lines.append(f"  成功 {result['type']}: 成功")
                    if 'improvement' in result and result['improvement'] > 0:
                        lines.append(f"     改进: {result['improvement']:.1f}MB")
        
        return "\n".join(lines)
    
    def run_full_optimization(self) -> Dict[str, Any]:
        """运行完整优化流程"""
        print("")
        print("" * 50)
        
        # 1. 性能分析
        analysis = self.analyze_performance()
        
        # 2. 应用优化
        optimizations = self.apply_optimizations()
        
        # 3. 生成报告
        report = self.generate_report()
        
        return {
            'analysis': analysis,
            'optimizations': optimizations,
            'report': report
        }

def main():
    """主函数"""
    print("-")
    
    optimizer = PerformanceOptimizer()
    result = optimizer.run_full_optimization()
    
    print(f"\n{result['report']}")
    
    return result

if __name__ == "__main__":
    main()