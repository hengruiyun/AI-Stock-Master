#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统语言检测器
自动检测系统语言并设置应用程序界面语言
"""

import os
import locale
import platform
import ctypes
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LanguageDetector')

class LanguageDetector:
    """系统语言检测器"""
    
    def __init__(self):
        self.system = platform.system()
        self.detected_language = None
        self.supported_languages = ['zh', 'en']
        self.default_language = 'en'
    
    def detect_system_language(self):
        """检测系统语言"""
        try:
            if self.system == 'Windows':
                return self._detect_windows_language()
            elif self.system == 'Darwin':  # macOS
                return self._detect_macos_language()
            elif self.system == 'Linux':
                return self._detect_linux_language()
            else:
                logger.warning(f"未知操作系统: {self.system}，使用默认语言")
                return self.default_language
        except Exception as e:
            logger.error(f"检测系统语言时出错: {e}")
            return self.default_language
    
    def _detect_windows_language(self):
        """检测Windows系统语言"""
        try:
            # 使用GetUserDefaultUILanguage获取用户界面语言
            windll = ctypes.windll.kernel32
            lang_id = windll.GetUserDefaultUILanguage()
            
            # 提取主要语言ID
            primary_lang_id = lang_id & 0x3FF
            
            # 中文语言ID: 简体中文(2052)、繁体中文(1028、3076、4100、5124)
            if primary_lang_id == 4:  # 中文
                return 'zh'
            else:
                # 获取locale信息作为备选
                loc = locale.getdefaultlocale()
                if loc and loc[0]:
                    if loc[0].startswith('zh'):
                        return 'zh'
                return 'en'
        except Exception as e:
            logger.error(f"检测Windows语言时出错: {e}")
            return self.default_language
    
    def _detect_macos_language(self):
        """检测macOS系统语言"""
        try:
            # 使用locale获取系统语言
            loc = locale.getdefaultlocale()
            if loc and loc[0]:
                if loc[0].startswith('zh'):
                    return 'zh'
            return 'en'
        except Exception as e:
            logger.error(f"检测macOS语言时出错: {e}")
            return self.default_language
    
    def _detect_linux_language(self):
        """检测Linux系统语言"""
        try:
            # 尝试从环境变量获取
            for env_var in ['LANG', 'LC_ALL', 'LC_MESSAGES']:
                lang = os.environ.get(env_var, '')
                if lang:
                    if lang.startswith('zh'):
                        return 'zh'
                    break
            
            # 使用locale作为备选
            loc = locale.getdefaultlocale()
            if loc and loc[0]:
                if loc[0].startswith('zh'):
                    return 'zh'
            
            return 'en'
        except Exception as e:
            logger.error(f"检测Linux语言时出错: {e}")
            return self.default_language
    
    def get_language(self):
        """获取检测到的语言"""
        if not self.detected_language:
            self.detected_language = self.detect_system_language()
            logger.info(f"检测到系统语言: {self.detected_language}")
        
        return self.detected_language

# 单例模式
_language_detector = None

def get_language_detector():
    """获取语言检测器实例"""
    global _language_detector
    if _language_detector is None:
        _language_detector = LanguageDetector()
    return _language_detector

def get_system_language():
    """获取系统语言"""
    detector = get_language_detector()
    return detector.get_language()

# 测试代码
if __name__ == "__main__":
    language = get_system_language()
    print(f"检测到的系统语言: {language}")