"""
from config.gui_i18n import t_gui as _
缓存管理器模块

提供多层次的缓存管理功能，包括内存缓存、文件缓存和自动清理机制。
支持结果持久化、缓存过期检测、性能统计等功能。

作者: 267278466@qq.com
版本: 1.0.0
"""

import json
import pickle
import hashlib
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging

from config import get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目数据类"""
    
    def __init__(self, key: str, data: Any, ttl: int = 300):
        """
        初始化缓存条目
        
        Args:
            key: 缓存键
            data: 缓存数据
            ttl: 生存时间(秒)
        """
        self.key = key
        self.data = data
        self.created_time = datetime.now()
        self.last_accessed = datetime.now()
        self.ttl = ttl
        self.access_count = 0
        self.size = self._calculate_size(data)
    
    def _calculate_size(self, data: Any) -> int:
        """计算数据大小(字节)"""
        try:
            if isinstance(data, str):
                return len(data.encode('utf-8'))
            elif isinstance(data, (dict, list)):
                return len(str(data).encode('utf-8'))
            else:
                return len(pickle.dumps(data))
        except Exception:
            return 0
    
    def is_expired(self) -> bool:
        """检查是否已过期"""
        age = (datetime.now() - self.created_time).total_seconds()
        return age > self.ttl
    
    def access(self) -> Any:
        """访问缓存数据"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        return self.data
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'key': self.key,
            'created_time': self.created_time.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'ttl': self.ttl,
            'access_count': self.access_count,
            'size': self.size,
            'expired': self.is_expired()
        }


class AnalysisCache:
    """
    分析结果缓存管理器
    
    功能特性:
    - 多层次缓存 (内存 + 文件)
    - 自动过期清理
    - LRU淘汰策略
    - 缓存统计和监控
    - 线程安全操作
    """
    
    def __init__(self, 
                 max_memory_size: int = None,  # 无内存限制
                 max_entries: int = None,     # 无条目限制
                 cache_dir: str = "./cache"):
        """
        初始化缓存管理器
        
        Args:
            max_memory_size: 最大内存使用(字节)
            max_entries: 最大缓存条目数
            cache_dir: 文件缓存目录
        """
        self.max_memory_size = max_memory_size or float('inf')  # 无内存限制
        self.max_entries = max_entries or float('inf')       # 无条目限制
        self.cache_dir = cache_dir
        
        # 内存缓存
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'memory_usage': 0,
            'file_cache_size': 0,
            'total_entries': 0,
            'evictions': 0,
            'expired_cleanups': 0
        }
        
        # 配置参数
        try:
            self.config = get_config('cache', {
                'enable_file_cache': True,
                'auto_cleanup_interval': 600,  # 10分钟
                'default_ttl': 300,            # 5分钟
                'compression': True
            })
            # 如果get_config返回None，使用默认配置
            if self.config is None:
                self.config = {
                    'enable_file_cache': True,
                    'auto_cleanup_interval': 600,
                    'default_ttl': 300,
                    'compression': True
                }
        except Exception:
            # 如果配置获取失败，使用默认配置
            self.config = {
                'enable_file_cache': True,
                'auto_cleanup_interval': 600,
                'default_ttl': 300,
                'compression': True
            }
        
        # 创建缓存目录
        self._ensure_cache_dir()
        
        # 启动后台清理线程
        self._start_cleanup_thread()
        
        memory_limit_str = "无限制" if max_memory_size is None else f"{max_memory_size//1024//1024}MB"
        logger.info(f"缓存管理器初始化完成 (内存限制: {memory_limit_str}, 目录: {cache_dir})")
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if self.config['enable_file_cache']:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _start_cleanup_thread(self):
        """启动后台清理线程"""
        def cleanup_worker():
            while True:
                time.sleep(self.config['auto_cleanup_interval'])
                self.clear_expired_cache()
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _generate_cache_key(self, base_key: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 组合所有参数
        key_parts = [base_key]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        # 生成哈希
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _get_file_cache_path(self, key: str) -> str:
        """获取文件缓存路径"""
        return os.path.join(self.cache_dir, f"{key}.cache")
    
    def _update_memory_usage(self):
        """更新内存使用统计"""
        with self.memory_lock:
            total_size = sum(entry.size for entry in self.memory_cache.values())
            self.stats['memory_usage'] = total_size
            self.stats['total_entries'] = len(self.memory_cache)
    
    def _evict_if_needed(self):
        """根据LRU策略淘汰缓存"""
        with self.memory_lock:
            # 检查条目数限制
            while len(self.memory_cache) >= self.max_entries:
                # 找到最少使用的条目
                lru_key = min(self.memory_cache.keys(), 
                             key=lambda k: self.memory_cache[k].last_accessed)
                self._remove_from_memory(lru_key)
                self.stats['evictions'] += 1
            
            # 检查内存大小限制
            while self.stats['memory_usage'] > self.max_memory_size:
                if not self.memory_cache:
                    break
                lru_key = min(self.memory_cache.keys(), 
                             key=lambda k: self.memory_cache[k].last_accessed)
                self._remove_from_memory(lru_key)
                self.stats['evictions'] += 1
    
    def _remove_from_memory(self, key: str):
        """从内存中移除缓存条目"""
        if key in self.memory_cache:
            del self.memory_cache[key]
            self._update_memory_usage()
    
    def store_results(self, key: str, data: Any, ttl: int = None) -> None:
        """
        存储分析结果
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            ttl: 生存时间(秒)，None使用默认值
        """
        if ttl is None:
            ttl = self.config['default_ttl']
        
        cache_key = self._generate_cache_key(key)
        
        try:
            with self.memory_lock:
                # 创建缓存条目
                entry = CacheEntry(cache_key, data, ttl)
                
                # 检查是否需要淘汰
                self._evict_if_needed()
                
                # 存储到内存
                self.memory_cache[cache_key] = entry
                self._update_memory_usage()
                
                # 可选：存储到文件
                if self.config['enable_file_cache']:
                    self._store_to_file(cache_key, entry)
                
                logger.debug(f"已缓存数据: {key} -> {cache_key} (TTL: {ttl}s)")
                
        except Exception as e:
            logger.error(f"存储缓存失败 {key}: {e}")
    
    def _store_to_file(self, cache_key: str, entry: CacheEntry):
        """存储到文件缓存"""
        try:
            file_path = self._get_file_cache_path(cache_key)
            cache_data = {
                'data': entry.data,
                'created_time': entry.created_time.isoformat(),
                'ttl': entry.ttl,
                'metadata': {
                    'size': entry.size,
                    'access_count': entry.access_count
                }
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            logger.warning(f"文件缓存存储失败 {cache_key}: {e}")
    
    def get_cached_results(self, key: str) -> Optional[Any]:
        """
        获取缓存的结果
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或已过期返回None
        """
        cache_key = self._generate_cache_key(key)
        
        # 1. 首先检查内存缓存
        with self.memory_lock:
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                
                if not entry.is_expired():
                    self.stats['hits'] += 1
                    return entry.access()
                else:
                    # 过期了，清理
                    self._remove_from_memory(cache_key)
        
        # 2. 检查文件缓存
        if self.config['enable_file_cache']:
            data = self._load_from_file(cache_key)
            if data is not None:
                # 重新加载到内存
                self.store_results(key, data)
                self.stats['hits'] += 1
                return data
        
        # 3. 缓存未命中
        self.stats['misses'] += 1
        return None
    
    def _load_from_file(self, cache_key: str) -> Optional[Any]:
        """从文件缓存加载"""
        try:
            file_path = self._get_file_cache_path(cache_key)
            
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 检查是否过期
            created_time = datetime.fromisoformat(cache_data['created_time'])
            age = (datetime.now() - created_time).total_seconds()
            
            if age > cache_data['ttl']:
                # 过期了，删除文件
                os.remove(file_path)
                return None
            
            return cache_data['data']
            
        except Exception as e:
            logger.warning(f"文件缓存加载失败 {cache_key}: {e}")
            return None
    
    def is_cache_valid(self, key: str, max_age: int = None) -> bool:
        """
        检查缓存是否有效
        
        Args:
            key: 缓存键
            max_age: 最大年龄(秒)，None使用TTL
            
        Returns:
            缓存是否有效
        """
        cache_key = self._generate_cache_key(key)
        
        with self.memory_lock:
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                
                if max_age is not None:
                    age = (datetime.now() - entry.created_time).total_seconds()
                    return age <= max_age
                else:
                    return not entry.is_expired()
        
        return False
    
    def clear_expired_cache(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的条目数
        """
        cleaned_count = 0
        
        # 清理内存缓存
        with self.memory_lock:
            expired_keys = [key for key, entry in self.memory_cache.items() 
                           if entry.is_expired()]
            
            for key in expired_keys:
                self._remove_from_memory(key)
                cleaned_count += 1
        
        # 清理文件缓存
        if self.config['enable_file_cache']:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.cache'):
                        file_path = os.path.join(self.cache_dir, filename)
                        cache_key = filename[:-6]  # 移除.cache后缀
                        
                        if self._load_from_file(cache_key) is None:
                            cleaned_count += 1
            except Exception as e:
                logger.warning(f"清理文件缓存失败: {e}")
        
        if cleaned_count > 0:
            self.stats['expired_cleanups'] += cleaned_count
            logger.info(f"清理了 {cleaned_count} 个过期缓存条目")
        
        return cleaned_count
    
    def clear_all_cache(self) -> None:
        """清空所有缓存"""
        with self.memory_lock:
            cleared_count = len(self.memory_cache)
            self.memory_cache.clear()
            self._update_memory_usage()
        
        # 清理文件缓存
        if self.config['enable_file_cache']:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.cache'):
                        os.remove(os.path.join(self.cache_dir, filename))
            except Exception as e:
                logger.warning(f"清理文件缓存失败: {e}")
        
        logger.info(f"已清空所有缓存 ({cleared_count} 个条目)")
    
    def remove_cache(self, key: str) -> bool:
        """
        移除指定缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功移除
        """
        cache_key = self._generate_cache_key(key)
        removed = False
        
        # 从内存移除
        with self.memory_lock:
            if cache_key in self.memory_cache:
                self._remove_from_memory(cache_key)
                removed = True
        
        # 从文件移除
        if self.config['enable_file_cache']:
            file_path = self._get_file_cache_path(cache_key)
            if os.path.exists(file_path):
                os.remove(file_path)
                removed = True
        
        return removed
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self.memory_lock:
            file_cache_size = 0
            if self.config['enable_file_cache'] and os.path.exists(self.cache_dir):
                try:
                    file_cache_size = sum(
                        os.path.getsize(os.path.join(self.cache_dir, f))
                        for f in os.listdir(self.cache_dir)
                        if f.endswith('.cache')
                    )
                except Exception:
                    pass
            
            hit_rate = 0
            total_requests = self.stats['hits'] + self.stats['misses']
            if total_requests > 0:
                hit_rate = self.stats['hits'] / total_requests
            
            return {
                'memory_stats': {
                    'entries': len(self.memory_cache),
                    'memory_usage_mb': self.stats['memory_usage'] / 1024 / 1024,
                    'max_memory_mb': self.max_memory_size / 1024 / 1024,
                    'memory_utilization': self.stats['memory_usage'] / self.max_memory_size
                },
                'file_stats': {
                    'enabled': self.config['enable_file_cache'],
                    'cache_dir': self.cache_dir,
                    'file_cache_size_mb': file_cache_size / 1024 / 1024
                },
                'performance_stats': {
                    'hits': self.stats['hits'],
                    'misses': self.stats['misses'],
                    'hit_rate': hit_rate,
                    'evictions': self.stats['evictions'],
                    'expired_cleanups': self.stats['expired_cleanups']
                },
                'config': self.config.copy()
            }
    
    def get_cache_entries_info(self) -> List[Dict]:
        """获取所有缓存条目信息"""
        with self.memory_lock:
            return [entry.to_dict() for entry in self.memory_cache.values()]
    
    def optimize_cache(self) -> Dict:
        """优化缓存性能"""
        start_time = time.time()
        
        # 清理过期条目
        expired_cleaned = self.clear_expired_cache()
        
        # 强制垃圾回收 (如果内存使用过高)
        if self.stats['memory_usage'] > self.max_memory_size * 0.8:
            with self.memory_lock:
                # 移除访问次数少的条目
                sorted_entries = sorted(
                    self.memory_cache.items(),
                    key=lambda x: (x[1].access_count, x[1].last_accessed)
                )
                
                target_size = self.max_memory_size * 0.6  # 清理到60%
                current_size = self.stats['memory_usage']
                
                for key, entry in sorted_entries:
                    if current_size <= target_size:
                        break
                    current_size -= entry.size
                    self._remove_from_memory(key)
                    self.stats['evictions'] += 1
        
        optimization_time = time.time() - start_time
        
        return {
            'expired_cleaned': expired_cleaned,
            'optimization_time': optimization_time,
            'memory_after_optimization_mb': self.stats['memory_usage'] / 1024 / 1024,
            'entries_after_optimization': len(self.memory_cache)
        }


# 全局缓存实例
_global_cache: Optional[AnalysisCache] = None
_cache_lock = threading.Lock()


def get_global_cache() -> AnalysisCache:
    """获取全局缓存实例"""
    global _global_cache
    
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = AnalysisCache()
    
    return _global_cache


# 便捷函数
def cache_analysis_result(key: str, data: Any, ttl: int = None) -> None:
    """缓存分析结果"""
    cache = get_global_cache()
    cache.store_results(key, data, ttl)


def get_cached_analysis(key: str) -> Optional[Any]:
    """获取缓存的分析结果"""
    cache = get_global_cache()
    return cache.get_cached_results(key)


def clear_analysis_cache() -> None:
    """清空分析缓存"""
    cache = get_global_cache()
    cache.clear_all_cache()


if __name__ == "__main__":
    # 测试代码
    print("-")
    
    try:
        # 创建测试缓存
        cache = AnalysisCache()  # 使用默认配置(无限制)
        
        # 测试基本功能
        print("\n=== 测试基本缓存功能 ===")
        test_data = {'stocks': ['600036', '000001'], 'result': 'test'}
        cache.store_results('test_key', test_data, ttl=60)
        
        cached_data = cache.get_cached_results('test_key')
        print(f"缓存测试: {cached_data == test_data}")
        
        # 测试过期
        print("\n=== 测试过期机制 ===")
        cache.store_results('expire_test', {'data': 'will_expire'}, ttl=1)
        time.sleep(2)
        expired_data = cache.get_cached_results('expire_test')
        print(f"过期测试: {expired_data is None}")
        
        # 测试批量操作
        print("\n=== 测试批量缓存 ===")
        for i in range(10):
            cache.store_results(f'batch_test_{i}', {'value': i}, ttl=300)
        
        stats = cache.get_cache_stats()
        print(f"缓存条目数: {stats['memory_stats']['entries']}")
        print(f"内存使用: {stats['memory_stats']['memory_usage_mb']:.2f}MB")
        print(f"命中率: {stats['performance_stats']['hit_rate']:.2%}")
        
        # 测试清理
        print("\n=== 测试缓存清理 ===")
        cleaned = cache.clear_expired_cache()
        print(f"清理条目数: {cleaned}")
        
        # 测试优化
        print("\n=== 测试缓存优化 ===")
        optimize_result = cache.optimize_cache()
        print(f"优化结果: {optimize_result}")
        
        print("\n成功 缓存管理器测试完成")
        
    except Exception as e:
        print(f"错误 测试失败: {e}")
        import traceback
        traceback.print_exc()