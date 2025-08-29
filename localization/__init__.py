#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言本地化包
支持中英文自动切换
"""

from .language_manager import _, language_manager, get_current_language, set_language

__all__ = ['_', 'language_manager', 'get_current_language', 'set_language'] 