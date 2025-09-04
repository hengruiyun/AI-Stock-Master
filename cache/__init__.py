#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存模块

统一管理各种数据缓存，包括：
- 量价数据缓存
- 分析结果缓存  
- 图表数据缓存

作者: AI Assistant
版本: 1.0.0
"""

from .volume_price_cache import (
    VolumePriceCacheManager,
    get_cache_manager,
    get_volume_price_data,
    clear_volume_price_cache,
    get_cache_statistics
)

__all__ = [
    'VolumePriceCacheManager',
    'get_cache_manager', 
    'get_volume_price_data',
    'clear_volume_price_cache',
    'get_cache_statistics'
]

