#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器管理模块
Server Manager Module

提供stockhost.exe服务器的启动和管理功能
"""

import sys
import subprocess
from pathlib import Path

# 导入psutil（如果可用）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False


def ensure_server_running():
    """
    确保本地股票服务器正在运行
    
    功能：
    1. 检查服务器是否已经在运行
    2. 如果未运行，尝试启动服务器
    
    返回：
    tuple: (server_running, started_by_us)
        - server_running: 服务器是否在运行
        - started_by_us: 是否由本次调用启动
    """
    print("[服务器管理] 开始检查服务器状态...")
    server_names = ["stockhost.exe", "大师服务器.exe"]
    server_running = False
    detected_pid = None
    
    # 使用psutil检查进程
    if PSUTIL_AVAILABLE:
        print("[服务器管理] 使用psutil检查运行中的服务器进程...")
        for proc in psutil.process_iter(["name", "exe", "pid"]):
            try:
                proc_name = proc.info['name']
                proc_exe = proc.info['exe']
                for name in server_names:
                    if name.lower() == proc_name.lower() or (proc_exe and name.lower() in proc_exe.lower()):
                        detected_pid = proc.info['pid']
                        print(f"[服务器管理] ✓ 检测到服务器 {name} 已在运行 (PID: {detected_pid})")
                        server_running = True
                        break
                if server_running:
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not server_running:
            print("[服务器管理] 未检测到运行中的服务器进程")
    else:
        print("[服务器管理] ⚠️ psutil模块不可用，无法检测运行中的进程")
    
    if server_running:
        print(f"[服务器管理] 服务器已在运行，无需启动")
        return True, False  # 已运行，但不是本次启动的
    
    # 尝试启动服务器
    print("[服务器管理] 未检测到运行中的服务器，尝试启动新服务器...")
    
    # 确定项目根目录
    try:
        from utils.path_helper import get_base_path
        base_path = Path(get_base_path())
    except:
        # 如果无法导入，使用当前目录
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent
    
    # 尝试获取项目根目录
    try:
        project_root = Path(__file__).resolve().parent.parent
    except:
        project_root = base_path
    
    candidate_dirs = [base_path, project_root]
    
    for exe_name in server_names:
        for directory in candidate_dirs:
            exe_path = directory / exe_name
            if exe_path.exists():
                try:
                    print(f"[服务器管理] 正在启动服务器: {exe_name}")
                    print(f"[服务器管理]   路径: {exe_path}")
                    print(f"[服务器管理]   工作目录: {directory}")
                    subprocess.Popen([str(exe_path), "--server"], cwd=str(directory))
                    print(f"[服务器管理] ✓ 服务器启动成功: {exe_name}")
                    return True, True  # 运行中，由本次启动
                except Exception as e:
                    print(f"[服务器管理] ✗ 启动服务器 {exe_name} 失败: {e}")
    
    print("[服务器管理] ✗ 未能找到并启动任何服务器可执行文件")
    return False, False


if __name__ == "__main__":
    # 测试服务器启动
    running, started = ensure_server_running()
    if running:
        if started:
            print("✅ 服务器已成功启动")
        else:
            print("✅ 服务器已在运行")
    else:
        print("❌ 服务器未运行")













