#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama Environment Checker
Ollama环境检测工具

功能:
1. 检查Windows系统中是否安装了Ollama.exe
2. 检查Ollama服务是否运行，未运行则启动
3. 检查指定模型是否存在，不存在则下载

使用方法:
python check_ollama_env.py [model_name]

示例:
python check_ollama_env.py qwen3:0.6b
"""

import os
import sys
import subprocess
import time
import json
import psutil
import requests
import threading
from pathlib import Path
from typing import Optional, List

class OllamaChecker:
    def __init__(self, model_name: str = "qwen3:0.6b"):
        self.model_name = model_name
        self.ollama_exe_path = None
        
        # 从环境变量读取OLLAMA_HOST和OLLAMA_PORT
        ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
        ollama_port = os.getenv('OLLAMA_PORT', '11434')
        self.ollama_url = f"http://{ollama_host}:{ollama_port}"
        
    def print_header(self):
        """打印程序头部信息"""
        print("="*60)
        print("Ollama Environment Checker / Ollama环境检测工具")
        print("="*60)
        print(f"Target Model / 目标模型: {self.model_name}")
        print("-"*60)
    
    def parse_download_progress(self, line):
        """解析下载进度信息"""
        import re
        
        # 匹配各种可能的进度格式
        # 例如: "downloading sha256:abc123... 50%"
        # 或者: "pulling manifest... 100%"
        # 或者: "downloading 123MB/456MB (27%)"
        
        # 匹配百分比
        percent_match = re.search(r'(\d+(?:\.\d+)?)%', line)
        if percent_match:
            percent = float(percent_match.group(1))
            
            # 匹配文件大小信息 (支持更多格式)
            size_match = re.search(r'(\d+(?:\.\d+)?\s*[KMGT]?B)/(\d+(?:\.\d+)?\s*[KMGT]?B)', line)
            if size_match:
                downloaded = size_match.group(1)
                total = size_match.group(2)
                return f"Downloading: {downloaded}/{total} ({percent:.1f}%) / 下载中: {downloaded}/{total} ({percent:.1f}%)"
            
            # 匹配操作类型
            if "pulling" in line.lower():
                return f"Pulling manifest: {percent:.1f}% / 拉取清单: {percent:.1f}%"
            elif "downloading" in line.lower():
                return f"Downloading: {percent:.1f}% / 下载中: {percent:.1f}%"
            elif "verifying" in line.lower():
                return f"Verifying: {percent:.1f}% / 验证中: {percent:.1f}%"
            else:
                return f"Progress: {percent:.1f}% / 进度: {percent:.1f}%"
        
        # 特殊处理没有百分比的常见状态
        line_lower = line.lower()
        if "pulling manifest" in line_lower:
            return f"Pulling manifest... / 拉取清单中..."
        elif "downloading" in line_lower and "sha256" in line_lower:
            return f"Downloading model data... / 下载模型数据中..."
        elif "writing manifest" in line_lower:
            return f"Writing manifest... / 写入清单中..."
        elif "verifying" in line_lower:
            return f"Verifying model... / 验证模型中..."
        elif any(keyword in line_lower for keyword in ['pulling', 'downloading', 'verifying', 'writing']):
            return f"Status: {line} / 状态: {line}"
        
        return None
        
    def find_ollama_exe(self) -> bool:
        """查找Windows系统中的Ollama.exe"""
        print("[1] Searching for Ollama.exe... / 正在搜索Ollama.exe...")
        
        # 常见的安装路径
        common_paths = [
            os.path.expanduser("~\\AppData\\Local\\Programs\\Ollama\\ollama.exe"),
            "C:\\Program Files\\Ollama\\ollama.exe",
            "C:\\Program Files (x86)\\Ollama\\ollama.exe",
            os.path.expanduser("~\\AppData\\Roaming\\Ollama\\ollama.exe"),
            ".\\Ollama\\ollama.exe",
        ]
        
        # 检查常见路径
        for path in common_paths:
            if os.path.exists(path):
                self.ollama_exe_path = path
                print(f"✓ Found Ollama.exe at / 找到Ollama.exe: {path}")
                return True
        
        # 在PATH环境变量中搜索
        try:
            result = subprocess.run(["where", "ollama"], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                self.ollama_exe_path = result.stdout.strip().split('\n')[0]
                print(f"✓ Found Ollama.exe in PATH / 在PATH中找到Ollama.exe: {self.ollama_exe_path}")
                return True
        except Exception as e:
            print(f"Error searching in PATH: {e}")
            
        # 在整个系统中搜索（可能很慢）
        print("Searching in system drives... / 在系统驱动器中搜索... (this may take a while / 可能需要一些时间)")
        
        for drive in ['C:\\', 'D:\\', 'E:\\']:
            if os.path.exists(drive):
                for root, dirs, files in os.walk(drive):
                    if 'ollama.exe' in files:
                        self.ollama_exe_path = os.path.join(root, 'ollama.exe')
                        print(f"✓ Found Ollama.exe at / 找到Ollama.exe: {self.ollama_exe_path}")
                        return True
                    # 跳过一些系统目录以加快搜索
                    dirs[:] = [d for d in dirs if not d.startswith(('Windows', 'System', '$'))]
        
        print("✗ Ollama.exe not found! / 未找到Ollama.exe!")
        print("Please install Ollama from / 请从以下地址安装Ollama: https://ollama.ai/")
        return False
    
    def check_ollama_process(self) -> bool:
        """检查Ollama进程是否在运行"""
        print("\n[2] Checking Ollama process... / 检查Ollama进程...")
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    print(f"✓ Ollama process found / 找到Ollama进程: PID {proc.info['pid']}")
                    if proc.info['exe']:
                        print(f"  Executable / 可执行文件: {proc.info['exe']}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        print("✗ Ollama process not running / Ollama进程未运行")
        return False
    
    def start_ollama_serve(self) -> bool:
        """启动Ollama服务"""
        if not self.ollama_exe_path:
            print("Cannot start Ollama: executable not found / 无法启动Ollama: 未找到可执行文件")
            return False
            
        print("\n[3] Starting Ollama serve... / 启动Ollama服务...")
        
        try:
            # 方法1: 直接启动 ollama serve (不等待返回)
            print("Trying method 1: Direct service start... / 尝试方法1: 直接启动服务...")
            try:
                subprocess.Popen(
                    [self.ollama_exe_path, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            except Exception as e1:
                print(f"Method 1 failed / 方法1失败: {e1}")
                
                # 方法2: 使用start命令在新窗口中启动
                print("Trying method 2: Start in new window... / 尝试方法2: 在新窗口中启动...")
                try:
                    subprocess.Popen(
                        f'start "Ollama Service" /min "{self.ollama_exe_path}" serve',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e2:
                    print(f"Method 2 failed / 方法2失败: {e2}")
                    
                    # 方法3: 尝试通过服务形式启动
                    print("Trying method 3: Start as service... / 尝试方法3: 通过服务形式启动...")
                    try:
                        subprocess.Popen(
                            ["sc", "start", "ollama"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        )
                    except Exception as e3:
                        print(f"Method 3 failed / 方法3失败: {e3}")
            
            # 等待4秒后检查进程是否在内存中
            print("Waiting 4 seconds to check service status... / 等待4秒后检查服务状态...")
            time.sleep(4)
            
            # 检查Ollama进程是否在运行
            ollama_running = False
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                        if proc.info['exe'] and 'ollama.exe' in proc.info['exe'].lower():
                            print(f"✓ Found Ollama process / 发现Ollama进程 (PID: {proc.info['pid']})")
                            ollama_running = True
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if ollama_running:
                # 再检查服务是否可访问
                if self.check_ollama_service():
                    print("✓ Ollama service started successfully and accessible / Ollama服务启动成功并可访问")
                    return True
                else:
                    print("⚠ Ollama process started but service temporarily inaccessible / Ollama进程已启动但服务暂时不可访问，可能正在初始化...")
                    return True  # 进程存在就认为启动成功
            else:
                print("✗ Failed to start Ollama service / 未能启动Ollama服务")
                print("\nTroubleshooting suggestions / 故障排除建议:")
                print("1. Check firewall settings / 检查防火墙设置")
                print("2. Check if port 11434 is in use / 检查端口11434是否被占用")
                print("3. Run this script as administrator / 以管理员身份运行此脚本")
                print("4. Manually run: ollama serve / 手动运行: ollama serve")
                print("5. Check if Ollama is properly installed / 检查Ollama是否正确安装")
                return False
                
        except Exception as e:
            print(f"✗ Error starting Ollama service / 启动Ollama服务时出错: {e}")
            return False
    
    def check_ollama_service(self) -> bool:
        """检查Ollama服务是否可访问"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def list_models(self) -> List[str]:
        """获取已安装的模型列表"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            print(f"Error getting model list / 获取模型列表错误: {e}")
        return []
    
    def check_model_exists(self) -> bool:
        """检查指定模型是否存在"""
        print(f"\n[4] Checking if model '{self.model_name}' exists... / 检查模型 '{self.model_name}' 是否存在...")
        
        models = self.list_models()
        if not models:
            print("✗ Failed to get model list / 获取模型列表失败")
            return False
        
        print(f"Available models / 可用模型: {', '.join(models)}")
        
        # 检查完全匹配或部分匹配
        for model in models:
            if model == self.model_name or model.startswith(self.model_name.split(':')[0]):
                print(f"✓ Model '{model}' found / 找到模型 '{model}'")
                return True
        
        print(f"✗ Model '{self.model_name}' not found / 未找到模型 '{self.model_name}'")
        return False
    
    def download_model(self) -> bool:
        """下载指定模型"""
        print(f"\n[5] Downloading model '{self.model_name}'... / 下载模型 '{self.model_name}'...")
        print("This may take a while depending on model size and network speed. / 根据模型大小和网络速度，这可能需要一些时间。")
        
        try:
            # 启动下载进程
            process = subprocess.Popen(
                [self.ollama_exe_path, "pull", self.model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=0
            )
            
            # 实时显示下载进度
            last_progress = ""
            output_lines = []
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.strip()
                    output_lines.append(line)
                    
                    # 解析进度信息
                    progress_info = self.parse_download_progress(line)
                    if progress_info and progress_info != last_progress:
                        print(f"\r{progress_info}", end='', flush=True)
                        last_progress = progress_info
                    elif any(keyword in line.lower() for keyword in ['pulling', 'downloading', 'verifying']):
                        print(f"\r{line}", end='', flush=True)
            
            # 等待进程完成
            return_code = process.wait()
            print("\r" + " " * 80 + "\r", end='')  # 清除进度行
            
            if return_code == 0:
                print(f"✓ Model '{self.model_name}' downloaded successfully / 模型 '{self.model_name}' 下载成功")
                return True
            else:
                # 显示错误信息
                error_lines = [line for line in output_lines if 'error' in line.lower()]
                if error_lines:
                    print(f"✗ Error downloading model / 下载模型错误: {error_lines[-1]}")
                else:
                    print(f"✗ Error downloading model / 下载模型错误 (exit code: {return_code})")
                return False
                
        except Exception as e:
            print(f"\r" + " " * 80 + "\r", end='')  # 清除进度行
            print(f"✗ Error downloading model / 下载模型错误: {e}")
            return False
    
    def run_check(self) -> bool:
        """运行完整的检查流程"""
        self.print_header()
        
        # 1. 查找Ollama.exe
        if not self.find_ollama_exe():
            return False
        
        # 2. 检查进程是否运行
        process_running = self.check_ollama_process()
        
        # 3. 检查服务是否可访问
        service_ready = self.check_ollama_service()
        
        # 优化逻辑：如果Ollama已在内存中且服务可访问，则不重启
        if process_running and service_ready:
            print("\n✓ Ollama service is already running and accessible / Ollama服务已运行且可访问")
        elif process_running and not service_ready:
            print("\nOllama process is running but service is not accessible / Ollama进程正在运行但服务不可访问")
            print("Waiting for service to become ready... / 等待服务就绪...")
            
            # 等待一段时间让服务自行就绪，避免不必要的重启
            for i in range(4):
                time.sleep(2)
                if self.check_ollama_service():
                    print("✓ Service is now accessible / 服务现在可访问")
                    service_ready = True
                    break
                print(f"  Waiting... / 等待中... ({i+1}/10)")
            
            # 如果等待后仍不可访问，则重启服务
            if not service_ready:
                print("Service still not accessible, attempting restart... / 服务仍不可访问，尝试重启...")
                
                # 尝试终止现有进程
                try:
                    for proc in psutil.process_iter(['pid', 'name']):
                        if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                            print(f"Terminating process / 终止进程 PID {proc.info['pid']}")
                            proc.terminate()
                            proc.wait(timeout=5)
                    time.sleep(2)
                except Exception as e:
                    print(f"Warning: Failed to terminate existing process / 警告: 终止现有进程失败: {e}")
                
                # 重新启动服务
                if not self.start_ollama_serve():
                    return False
        else:
            # 进程未运行，直接启动服务
            if not self.start_ollama_serve():
                return False
        
        # 4. 检查模型是否存在
        if not self.check_model_exists():
            # 5. 下载模型
            if not self.download_model():
                return False
        
        print("\n" + "="*60)
        print("✓ All checks completed successfully! / 所有检查已成功完成!")
        print(f"✓ Ollama is ready with model '{self.model_name}' / Ollama已就绪，模型 '{self.model_name}' 可用")
        print("="*60)
        
        return True

def main():
    """主函数"""
    # 检查帮助参数
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', '/h', '/?']:
        print("Ollama Environment Checker / Ollama环境检测工具")
        print()
        print("Arguments:")
        print("  model_name    Target model to check/download (default: qwen3:0.6b)")
        print("Examples:")
        print("  python check_ollama_env.py")
        print("  python check_ollama_env.py qwen3:0.6b")
        print("Functions:")
        print("  1. Find Ollama.exe in Windows system / 查找Windows系统中的Ollama.exe")
        print("  2. Check if Ollama service is running / 检查Ollama服务是否运行")
        print("  3. Start Ollama service if not running / 如果未运行则启动Ollama服务")
        print("  4. Check if target model exists / 检查目标模型是否存在")
        print("  5. Download model if not exists / 如果不存在则下载模型")
        sys.exit(0)
    
    # 获取命令行参数
    model_name = "qwen3:0.6b"  # 默认模型
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
    
    # 创建检查器并运行
    checker = OllamaChecker(model_name)
    success = checker.run_check()
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
