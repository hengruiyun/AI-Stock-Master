#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径辅助工具 - 解决PyInstaller打包后的路径问题

当程序被PyInstaller打包成EXE后：
1. sys._MEIPASS: 临时解压目录（只读，包含打包的资源文件）
2. sys.executable: EXE文件所在目录
3. os.getcwd(): 用户运行EXE时的工作目录

本模块提供统一的路径获取方法，确保：
- 读取资源文件时使用正确的打包路径
- 保存用户数据时使用EXE所在目录或用户指定目录
"""

import os
import sys
from pathlib import Path
from typing import Optional


def get_base_path() -> Path:
    """
    获取应用程序基础路径
    
    返回:
        Path: 
            - 开发环境: 项目根目录
            - 打包环境: EXE所在目录（而非临时解压目录）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的环境
        # 使用EXE文件所在目录，而不是_MEIPASS临时目录
        return Path(sys.executable).parent
    else:
        # 开发环境
        return Path(__file__).parent.parent


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件路径（只读资源，如配置文件、图标等）
    
    参数:
        relative_path: 相对路径
        
    返回:
        Path: 资源文件的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境：从临时解压目录读取资源
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境：从项目根目录读取
        base_path = Path(__file__).parent.parent
    
    return base_path / relative_path


def get_data_file_path(filename: str) -> Path:
    """
    获取数据文件路径（智能查找，优先EXE目录）
    
    对于数据文件（*.json.gz, *.dat.gz），优先从EXE所在目录读取，
    如果不存在才从打包的临时目录读取。
    
    参数:
        filename: 文件名（如 'CN_Data5000.json.gz'）
        
    返回:
        Path: 数据文件的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包环境：优先从EXE目录读取
        exe_dir_file = get_base_path() / filename
        if exe_dir_file.exists():
            print(f"✓ 使用EXE目录的数据文件: {exe_dir_file}")
            return exe_dir_file
        
        # 如果EXE目录没有，使用打包的文件
        packed_file = Path(sys._MEIPASS) / filename
        if packed_file.exists():
            print(f"ℹ 使用打包的数据文件: {packed_file}")
            return packed_file
        
        # 都不存在，返回EXE目录路径（让调用者处理文件不存在的情况）
        print(f"⚠ 数据文件不存在: {filename}")
        return exe_dir_file
    else:
        # 开发环境：从项目根目录读取
        dev_file = Path(__file__).parent.parent / filename
        return dev_file


def get_data_path(relative_path: str = '') -> Path:
    """
    获取数据文件路径（用户数据，如分析报告、缓存等）
    
    这些文件应该保存在EXE所在目录，而不是临时目录
    
    参数:
        relative_path: 相对路径
        
    返回:
        Path: 数据文件的绝对路径
    """
    base_path = get_base_path()
    
    if relative_path:
        data_path = base_path / relative_path
    else:
        data_path = base_path
    
    # 确保目录存在
    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
    
    return data_path


def get_reports_dir() -> Path:
    """
    获取报告输出目录
    
    返回:
        Path: 报告目录路径（EXE所在目录下的analysis_reports）
    """
    reports_dir = get_data_path('analysis_reports')
    return reports_dir


def get_cache_dir() -> Path:
    """
    获取缓存目录
    
    返回:
        Path: 缓存目录路径（EXE所在目录下的cache）
    """
    cache_dir = get_data_path('cache')
    return cache_dir


def get_logs_dir() -> Path:
    """
    获取日志目录
    
    返回:
        Path: 日志目录路径（EXE所在目录下的logs）
    """
    logs_dir = get_data_path('logs')
    return logs_dir


def get_temp_dir() -> Path:
    """
    获取临时文件目录
    
    返回:
        Path: 临时目录路径（EXE所在目录下的temp）
    """
    temp_dir = get_data_path('temp')
    return temp_dir


def is_frozen() -> bool:
    """
    检查是否运行在打包环境
    
    返回:
        bool: True表示是打包后的EXE，False表示开发环境
    """
    return getattr(sys, 'frozen', False)


def get_executable_dir() -> Path:
    """
    获取可执行文件所在目录
    
    返回:
        Path: 
            - 打包环境: EXE文件所在目录
            - 开发环境: 脚本文件所在目录
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def get_user_data_dir() -> Path:
    """
    获取用户数据目录（用于存储用户配置等）
    
    返回:
        Path: 用户数据目录
            - Windows: %APPDATA%/AI股票大师
            - macOS: ~/Library/Application Support/AI股票大师
            - Linux: ~/.config/AI股票大师
    """
    import platform
    system = platform.system()
    
    if system == 'Windows':
        appdata = os.getenv('APPDATA', '')
        if appdata:
            user_dir = Path(appdata) / 'AI股票大师'
        else:
            user_dir = Path.home() / 'AppData' / 'Roaming' / 'AI股票大师'
    elif system == 'Darwin':  # macOS
        user_dir = Path.home() / 'Library' / 'Application Support' / 'AI股票大师'
    else:  # Linux
        user_dir = Path.home() / '.config' / 'AI股票大师'
    
    # 确保目录存在
    user_dir.mkdir(parents=True, exist_ok=True)
    
    return user_dir


def get_config_file(filename: str = 'config.json') -> Path:
    """
    获取配置文件路径
    
    参数:
        filename: 配置文件名
        
    返回:
        Path: 配置文件路径（保存在用户数据目录）
    """
    return get_user_data_dir() / filename


def ensure_dir_exists(path: Path) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    参数:
        path: 目录路径
        
    返回:
        Path: 目录路径
    """
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_path_info() -> dict:
    """
    获取所有路径信息（用于调试）
    
    返回:
        dict: 包含所有路径信息的字典
    """
    info = {
        'is_frozen': is_frozen(),
        'base_path': str(get_base_path()),
        'executable_dir': str(get_executable_dir()),
        'reports_dir': str(get_reports_dir()),
        'cache_dir': str(get_cache_dir()),
        'logs_dir': str(get_logs_dir()),
        'temp_dir': str(get_temp_dir()),
        'user_data_dir': str(get_user_data_dir()),
        'sys.executable': sys.executable,
        'os.getcwd()': os.getcwd(),
    }
    
    if is_frozen():
        info['sys._MEIPASS'] = sys._MEIPASS
    
    return info


def print_path_info():
    """打印路径信息（用于调试）"""
    info = get_path_info()
    
    print("=" * 60)
    print("路径信息 / Path Information")
    print("=" * 60)
    print(f"运行模式 / Mode: {'打包EXE / Frozen EXE' if info['is_frozen'] else '开发环境 / Development'}")
    print(f"基础路径 / Base Path: {info['base_path']}")
    print(f"可执行文件目录 / Executable Dir: {info['executable_dir']}")
    print(f"报告目录 / Reports Dir: {info['reports_dir']}")
    print(f"缓存目录 / Cache Dir: {info['cache_dir']}")
    print(f"日志目录 / Logs Dir: {info['logs_dir']}")
    print(f"临时目录 / Temp Dir: {info['temp_dir']}")
    print(f"用户数据目录 / User Data Dir: {info['user_data_dir']}")
    print(f"sys.executable: {info['sys.executable']}")
    print(f"os.getcwd(): {info['os.getcwd()']}")
    
    if info['is_frozen']:
        print(f"sys._MEIPASS (临时解压目录): {info['sys._MEIPASS']}")
    
    print("=" * 60)


if __name__ == '__main__':
    # 测试路径功能
    print_path_info()
    
    print("\n测试创建目录...")
    test_dirs = [
        get_reports_dir(),
        get_cache_dir(),
        get_logs_dir(),
        get_temp_dir(),
    ]
    
    for dir_path in test_dirs:
        print(f"✓ {dir_path} {'存在' if dir_path.exists() else '已创建'}")
    
    print("\n路径辅助工具测试完成！")



