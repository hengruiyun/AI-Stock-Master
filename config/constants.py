#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全局常量配置文件

定义系统的全局常量，包括主页、作者、版本等信息
"""

# 系统信息常量
HOMEPAGE = "http://github/hengruiyun"
AUTHOR = "267278466@qq.com"
VERSION = "v2.4"

# 应用程序信息
APP_NAME = "AI股票大师"
APP_NAME_EN = "AI Stock Master"
APP_DESCRIPTION = "专业股票分析工具"
APP_DESCRIPTION_EN = "Professional Stock Analysis Tool"

# 联系信息
CONTACT_EMAIL = AUTHOR
SUPPORT_URL = HOMEPAGE

# 版权信息
COPYRIGHT = f"© 2025 {AUTHOR}"
LICENSE = "Apache 2.0 License"

# 系统配置
DEFAULT_LANGUAGE = "auto"  # 自动检测系统语言
SUPPORTED_LANGUAGES = ["zh_CN", "en_US"]

# 文件路径常量
DATA_DIR = "data"
CACHE_DIR = "cache"
LOGS_DIR = "logs"
OUTPUT_DIR = "output"
REPORTS_DIR = "reports"

# 窗口配置
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600

# 数据配置
MAX_CACHE_SIZE = 100  # MB
DATA_REFRESH_INTERVAL = 300  # 秒
AUTO_SAVE_INTERVAL = 60  # 秒

# UI配置
UI_THEME = "classic"  # Windows经典风格
FONT_FAMILY = "Microsoft YaHei UI"
FONT_SIZE = 9

# 分析配置
DEFAULT_ANALYSIS_THREADS = 4
MAX_ANALYSIS_THREADS = 8
ANALYSIS_TIMEOUT = 300  # 秒

# 导出配置
DEFAULT_EXPORT_FORMAT = "xlsx"
SUPPORTED_EXPORT_FORMATS = ["xlsx", "csv", "html", "pdf"]

# 网络配置
REQUEST_TIMEOUT = 120  # 秒
MAX_RETRIES = 3
RETRY_DELAY = 1  # 秒

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_LOG_SIZE = 10  # MB
LOG_BACKUP_COUNT = 5