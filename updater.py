#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软件升级模块
提供自动检查版本并升级软件的功能

作者: AI Stock Master Team
"""

import os
import sys
import platform
import subprocess
import urllib.request
import urllib.error
import gzip
import tarfile
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import configparser

# 配置常量
EXTRACT_TARGET_DIR = "."  # gz文件解压目标目录，"." 表示当前文件夹


class SoftwareUpdater:
    """软件升级器"""
    
    def __init__(self, current_version: str, version_url: str = ""):
        """
        初始化升级器
        
        Args:
            current_version: 当前软件版本号
            version_url: 版本文件的URL地址
        """
        self.current_version = current_version
        self.version_url = version_url
        self.system_type = platform.system().lower()
        
    def parse_version(self, version_str: str) -> Tuple[int, ...]:
        """
        解析版本号字符串为可比较的元组
        
        Args:
            version_str: 版本号字符串，如 "3.6" 或 "3.8.5"
            
        Returns:
            版本号元组，如 (3, 3) 或 (3, 3, 1)
        """
        try:
            # 移除可能的 'v' 前缀
            if version_str.startswith('v'):
                version_str = version_str[1:]
            
            # 分割版本号并转换为整数
            parts = version_str.split('.')
            return tuple(int(part) for part in parts)
        except (ValueError, AttributeError):
            return (0, 0, 0)
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        比较两个版本号
        
        Args:
            version1: 版本号1
            version2: 版本号2
            
        Returns:
            -1: version1 < version2 (需要升级)
             0: version1 == version2 (无需升级)
             1: version1 > version2 (当前版本更新)
        """
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    
    def read_version_file(self) -> Optional[Dict[str, str]]:
        """
        读取远程版本文件
        
        Returns:
            版本信息字典，包含 version, exe, gz 字段，失败返回 None
        """
        if not self.version_url:
            print("Error: No version file URL provided | 错误：未提供版本文件URL")
            return None
        
        try:
            print(f"Checking version file: {self.version_url} | 正在检查版本文件: {self.version_url}")
            
            # 创建请求，设置用户代理和超时
            req = urllib.request.Request(
                self.version_url,
                headers={'User-Agent': 'AI-Stock-Master-Updater/1.0'}
            )
            
            # 下载版本文件内容
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8')
            
            # 解析配置文件格式
            config = configparser.ConfigParser()
            config.read_string(content)
            
            # 获取版本信息
            if 'AI-Stock-Master' in config:
                section = config['AI-Stock-Master']
            else:
                # 如果没有DEFAULT section，取第一个section
                sections = config.sections()
                if not sections:
                    print("错误：版本文件格式不正确，找不到有效的配置节")
                    return None
                section = config[sections[0]]
            
            version_info = {
                'version': section.get('version', ''),
                'exe': section.get('exe', ''),
                'gz': section.get('gz', '')
            }
            
            # 验证必需字段
            if not version_info['version']:
                print("Error: Missing version number in version file | 错误：版本文件中缺少版本号")
                return None
            
            print(f"Remote version: {version_info['version']} | 远程版本: {version_info['version']}")
            print(f"Current version: {self.current_version} | 当前版本: {self.current_version}")
            
            return version_info
            
        except urllib.error.URLError as e:
            print(f"Network error: Unable to access version file - {e} | 网络错误：无法访问版本文件 - {e}")
            return None
        except urllib.error.HTTPError as e:
            print(f"HTTP error: {e.code} - {e.reason} | HTTP错误：{e.code} - {e.reason}")
            return None
        except Exception as e:
            print(f"Error reading version file: {e} | 读取版本文件时发生错误: {e}")
            return None
    
    def download_file(self, url: str, filename: str) -> bool:
        """
        下载升级文件
        
        Args:
            url: 下载地址
            filename: 保存的文件名
            
        Returns:
            下载成功返回 True，失败返回 False
        """
        try:
            print(f"Downloading: {url} | 正在下载: {url}")
            
            # 创建请求
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'AI-Stock-Master-Updater/1.0'}
            )
            
            # 下载文件
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(filename, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 显示下载进度 (每1MB更新一次显示)
                        if downloaded % (1024 * 1024) < 8192:  # 每1MB更新一次
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                mb_downloaded = downloaded / (1024 * 1024)
                                mb_total = total_size / (1024 * 1024)
                                # 清除当前行并显示新的进度
                                print(f"\rProgress: {progress:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) | 进度: {progress:.1f}%", end="", flush=True)
                            else:
                                mb_downloaded = downloaded / (1024 * 1024)
                                print(f"\rDownloaded: {mb_downloaded:.1f}MB | 已下载: {mb_downloaded:.1f}MB", end="", flush=True)
            
            print(f"\nDownload completed: {filename} | 下载完成: {filename}")
            return True
            
        except Exception as e:
            print(f"Download failed: {e} | 下载失败: {e}")
            return False
    
    def extract_gz_file(self, gz_path: str, extract_path: str) -> bool:
        """
        解压缩 .gz 文件到指定目录
        
        Args:
            gz_path: .gz 文件路径
            extract_path: 解压目录
            
        Returns:
            解压成功返回 True，失败返回 False
        """
        try:
            print(f"Extracting: {gz_path} | 正在解压: {gz_path}")
            
            # 检查是否是 tar.gz 文件
            if gz_path.endswith('.tar.gz'):
                with tarfile.open(gz_path, 'r:gz') as tar:
                    tar.extractall(path=extract_path)
            else:
                # 普通的 .gz 文件
                output_filename = os.path.splitext(gz_path)[0]
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(output_filename, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            
            print(f"Extraction completed to: {extract_path} | 解压完成到: {extract_path}")
            return True
            
        except Exception as e:
            print(f"Extraction failed: {e} | 解压失败: {e}")
            return False
    
    def extract_and_overwrite(self, gz_path: str, target_dir: str) -> bool:
        """
        解压缩文件并自动覆盖到目标目录
        
        Args:
            gz_path: .gz 文件路径
            target_dir: 目标目录
            
        Returns:
            操作成功返回 True，失败返回 False
        """
        try:
            print(f"Extracting and overwriting to: {target_dir} | 正在解压并覆盖到: {target_dir}")
            
            # 确保目标目录存在
            if target_dir != "." and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # 创建临时目录进行解压
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压到临时目录
                if not self.extract_gz_file(gz_path, temp_dir):
                    return False
                
                # 查找解压后的文件
                extracted_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, temp_dir)
                        extracted_files.append((file_path, rel_path))
                
                print(f"Found {len(extracted_files)} files to copy | 找到 {len(extracted_files)} 个文件需要复制")
                
                # 复制文件到目标目录，自动覆盖
                copied_count = 0
                for src_path, rel_path in extracted_files:
                    # 跳过可能的顶级目录结构
                    # 如果解压后有一个顶级目录，跳过它
                    if '/' in rel_path or '\\' in rel_path:
                        parts = rel_path.replace('\\', '/').split('/')
                        if len(parts) > 1:
                            # 跳过第一级目录
                            rel_path = '/'.join(parts[1:])
                    
                    if not rel_path:  # 跳过空的相对路径
                        continue
                    
                    dst_path = os.path.join(target_dir, rel_path)
                    
                    # 创建目标目录
                    dst_dir = os.path.dirname(dst_path)
                    if dst_dir and not os.path.exists(dst_dir):
                        os.makedirs(dst_dir, exist_ok=True)
                    
                    # 复制文件（自动覆盖）
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    print(f"Copied: {rel_path} | 已复制: {rel_path}")
                
                print(f"Successfully copied {copied_count} files | 成功复制了 {copied_count} 个文件")
                return True
                
        except Exception as e:
            print(f"Extract and overwrite failed: {e} | 解压覆盖失败: {e}")
            return False
    
    def backup_current_files(self, backup_dir: str) -> bool:
        """
        备份当前文件
        
        Args:
            backup_dir: 备份目录
            
        Returns:
            备份成功返回 True，失败返回 False
        """
        try:
            current_dir = os.getcwd()
            
            # 创建备份目录
            os.makedirs(backup_dir, exist_ok=True)
            
            # 备份主要文件
            important_files = [
                'gui-pyqt5.py',
                'config.py',
                'app.ini',
                'requirements.txt'
            ]
            
            for file in important_files:
                src = os.path.join(current_dir, file)
                if os.path.exists(src):
                    dst = os.path.join(backup_dir, file)
                    shutil.copy2(src, dst)
                    print(f"备份文件: {file}")
            
            print(f"备份完成到: {backup_dir}")
            return True
            
        except Exception as e:
            print(f"备份失败: {e}")
            return False
    
    def update_files_from_archive(self, archive_path: str) -> bool:
        """
        从压缩包更新文件
        
        Args:
            archive_path: 压缩包路径
            
        Returns:
            更新成功返回 True，失败返回 False
        """
        try:
            current_dir = os.getcwd()
            
            # 创建临时解压目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 解压文件
                if not self.extract_gz_file(archive_path, temp_dir):
                    return False
                
                # 查找解压后的文件
                extracted_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, temp_dir)
                        extracted_files.append((file_path, rel_path))
                
                # 备份当前文件
                backup_dir = os.path.join(current_dir, f"backup_{int(time.time())}")
                self.backup_current_files(backup_dir)
                
                # 复制新文件
                for src_path, rel_path in extracted_files:
                    dst_path = os.path.join(current_dir, rel_path)
                    
                    # 创建目标目录
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(src_path, dst_path)
                    print(f"更新文件: {rel_path}")
                
                print("文件更新完成")
                return True
                
        except Exception as e:
            print(f"更新文件失败: {e}")
            return False
    
    def perform_windows_upgrade(self, exe_url: str) -> bool:
        """
        执行 Windows 系统升级（下载exe并执行）
        
        Args:
            exe_url: exe 文件下载地址
            
        Returns:
            升级启动成功返回 True，失败返回 False
        """
        try:
            # 下载exe文件到临时目录
            temp_dir = tempfile.gettempdir()
            exe_filename = os.path.join(temp_dir, "ai_stock_master_update.exe")
            
            if not self.download_file(exe_url, exe_filename):
                return False
            
            # 检查文件是否存在
            if not os.path.exists(exe_filename):
                print("Error: Downloaded upgrade file does not exist | 错误：下载的升级文件不存在")
                return False
            
            print("Starting upgrade program... | 正在启动升级程序...")
            print("Software will exit after upgrade program starts | 软件将在升级程序启动后立即退出")
            
            # 启动升级程序
            subprocess.Popen([exe_filename], shell=True)
            
            # 给升级程序一点时间启动
            time.sleep(1)
            
            # 标记需要退出程序
            print("Exiting current program... | 正在退出当前程序...")
            # 返回特殊值表示需要退出程序
            return "UPGRADE_EXIT"
            
        except Exception as e:
            print(f"Windows upgrade failed: {e} | Windows升级失败: {e}")
            return False
    
    def perform_unix_upgrade(self, gz_url: str) -> bool:
        """
        执行 Unix/Linux/Mac 系统升级（下载gz并解压覆盖）
        
        Args:
            gz_url: gz 文件下载地址
            
        Returns:
            升级成功返回 True，失败返回 False
        """
        try:
            # 下载gz文件
            gz_filename = "ai_stock_master_update.tar.gz"
            
            if not self.download_file(gz_url, gz_filename):
                return False
            
            # 自动解压到指定目录并覆盖
            if not self.extract_and_overwrite(gz_filename, EXTRACT_TARGET_DIR):
                return False
            
            # 清理下载的文件
            try:
                os.remove(gz_filename)
            except:
                pass
            
            print("Upgrade completed! Please restart the software | 升级完成！请重新启动软件")
            return True
            
        except Exception as e:
            print(f"Unix upgrade failed: {e} | Unix升级失败: {e}")
            return False
    
    def check_and_update(self) -> bool:
        """
        检查并执行软件升级
        
        Returns:
            升级成功或无需升级返回 True，失败返回 False
        """
        try:
            print("=" * 50)
            print("Checking for software updates... | 正在检查软件更新...")
            print("=" * 50)
            
            # 读取版本文件
            version_info = self.read_version_file()
            if not version_info:
                print("Skip upgrade: Unable to get version info | 跳过升级：无法获取版本信息")
                return True  # 不阻止程序继续运行
            
            # 比较版本
            comparison = self.compare_versions(self.current_version, version_info['version'])
            
            if comparison >= 0:
                print(f"Current version {self.current_version} is up to date | 当前版本 {self.current_version} 已是最新版本，无需升级")
                return True
            
            print(f"New version found! | 发现新版本！")
            print(f"Current version: {self.current_version} → New version: {version_info['version']} | 当前版本: {self.current_version} → 新版本: {version_info['version']}")
            print(f"Starting upgrade... | 开始升级...")
            
            # 根据系统类型选择升级方式
            if self.system_type == 'windows':
                # Windows 系统使用 exe 升级
                if not version_info['exe']:
                    print("Error: Missing Windows upgrade package URL in version file | 错误：版本文件中缺少 Windows 升级包地址")
                    return False
                
                result = self.perform_windows_upgrade(version_info['exe'])
                if result == "UPGRADE_EXIT":
                    # 需要退出程序
                    sys.exit(0)
                return result
            
            else:
                # 其他系统使用 gz 升级
                if not version_info['gz']:
                    print("Error: Missing Unix/Linux upgrade package URL in version file | 错误：版本文件中缺少 Unix/Linux 升级包地址")
                    return False
                
                return self.perform_unix_upgrade(version_info['gz'])
            
        except Exception as e:
            print(f"Error occurred during upgrade: {e} | 升级过程中发生错误: {e}")
            return False


def get_current_version() -> str:
    """
    获取当前软件版本号
    从 config/gui_i18n.py 文件中读取版本信息
    
    Returns:
        当前版本号字符串
    """
    try:
        # 尝试从配置文件中获取版本号
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'gui_i18n.py')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 查找版本号
            import re
            version_match = re.search(r'"app_version":\s*"v?([^"]+)"', content)
            if version_match:
                return version_match.group(1)
        
        # 如果无法从文件读取，返回默认版本号
        return "3.8.5"
        
    except Exception as e:
        print(f"获取版本号时发生错误: {e}")
        return "3.8.5"


def load_upgrade_config() -> Dict[str, Any]:
    """
    加载升级配置
    
    Returns:
        配置字典
    """
    default_config = {
        'enable_auto_check': True,
        'version_url': '',
        'timeout': 10,
        'auto_backup': False,
        'continue_on_failure': True
    }
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'upgrade_config.ini')
        
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            if 'upgrade' in config:
                section = config['upgrade']
                return {
                    'enable_auto_check': section.getboolean('enable_auto_check', True),
                    'version_url': section.get('version_url', ''),
                    'timeout': section.getint('timeout', 10),
                    'auto_backup': section.getboolean('auto_backup', False),
                    'continue_on_failure': section.getboolean('continue_on_failure', True)
                }
        
        return default_config
        
    except Exception as e:
        print(f"加载升级配置时发生错误: {e}")
        return default_config


def check_for_updates(force_check: bool = False) -> bool:
    """
    检查软件更新的便捷函数
    
    Args:
        force_check: 是否强制检查（忽略配置中的启用设置）
        
    Returns:
        检查和升级成功返回 True，失败或无需升级返回 False
    """
    try:
        # 加载配置
        config = load_upgrade_config()
        
        # 检查是否启用自动检查
        if not force_check and not config['enable_auto_check']:
            print("Automatic upgrade check is disabled | 自动升级检查已禁用")
            return True
        
        # 检查是否配置了版本URL
        if not config['version_url']:
            print("Version file URL not configured, skipping upgrade check | 未配置版本文件URL，跳过升级检查")
            return True
        
        # 获取当前版本
        current_version = get_current_version()
        
        # 创建升级器
        updater = SoftwareUpdater(current_version, config['version_url'])
        
        # 设置超时
        if hasattr(updater, 'timeout'):
            updater.timeout = config['timeout']
        
        # 执行升级检查
        result = updater.check_and_update()
        
        return result
        
    except Exception as e:
        print(f"Error occurred during upgrade check: {e} | 升级检查过程中发生错误: {e}")
        return False


# 导入时间模块（在函数内部使用）
import time

if __name__ == "__main__":
    # 测试升级功能
    current_version = get_current_version()
    version_url = "http://update.ttfox.com/update/version.ini"
    
    updater = SoftwareUpdater(current_version, version_url)
    result = updater.check_and_update()
    
    if result:
        print("升级检查完成")
    else:
        print("升级失败")
