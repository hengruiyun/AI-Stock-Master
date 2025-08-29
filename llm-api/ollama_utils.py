"""Ollama工具函数模块"""

import platform
import subprocess
import requests
import time
import os
import re
import shutil
import psutil
from typing import List, Optional, Tuple
from colorama import Fore, Style
# from tools.unified_i18n_manager import _

try:
    from exceptions import OllamaError
    from config_manager import get_config
except ImportError:
    from exceptions import OllamaError
    from config_manager import get_config

# 常量
OLLAMA_SERVER_URL = "http://localhost:11434"
OLLAMA_API_MODELS_ENDPOINT = f"{OLLAMA_SERVER_URL}/api/tags"
OLLAMA_DOWNLOAD_URL = {
    "darwin": "https://ollama.com/download/darwin",  # macOS
    "windows": "https://ollama.com/download/windows",  # Windows
    "linux": "https://ollama.com/download/linux"  # Linux
}


class OllamaManager:
    """Ollama管理器类"""
    
    def __init__(self, base_url: Optional[str] = None):
        if base_url is None:
            # 从配置管理器获取Ollama配置
            config = get_config()
            host = config.get("OLLAMA_HOST", "localhost")
            port = config.get("OLLAMA_PORT", 11434, int)
            base_url = config.get("OLLAMA_BASE_URL", f"http://{host}:{port}")
        
        self.base_url = base_url
        self.api_models_endpoint = f"{self.base_url}/api/tags"
        self.ollama_executable_path = None
        
    def find_ollama_executable(self) -> Optional[str]:
        """查找Ollama可执行文件路径"""
        if self.ollama_executable_path:
            return self.ollama_executable_path
            
        # 首先检查PATH中是否有ollama
        ollama_in_path = shutil.which("ollama")
        if ollama_in_path:
            self.ollama_executable_path = ollama_in_path
            print(f"[LLM Debug] 在PATH中找到Ollama: {ollama_in_path}")
            return ollama_in_path
        
        # Windows系统下的常见安装路径
        if platform.system().lower() == "windows":
            # 获取当前用户名
            username = os.getenv("USERNAME", "")
            
            possible_paths = [
                # 用户特定路径
                f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Ollama\\ollama.exe",
                f"C:\\Users\\{username}\\AppData\\Local\\ollama\\ollama.exe",
                # 系统路径
                "C:\\Program Files\\Ollama\\ollama.exe",
                "C:\\Program Files (x86)\\Ollama\\ollama.exe",
                # 其他可能路径
                "C:\\Ollama\\ollama.exe",
                "D:\\Program Files\\Ollama\\ollama.exe",
                "D:\\Ollama\\ollama.exe",
            ]
            
            print(f"[LLM Debug] 搜索Ollama可执行文件，用户名: {username}")
            for path in possible_paths:
                print(f"[LLM Debug] 检查路径: {path}")
                if os.path.exists(path):
                    self.ollama_executable_path = path
                    print(f"[LLM Debug] 找到Ollama可执行文件: {path}")
                    return path
        
        # macOS和Linux路径
        elif platform.system().lower() in ["darwin", "linux"]:
            possible_paths = [
                "/usr/local/bin/ollama",
                "/usr/bin/ollama",
                "/opt/ollama/bin/ollama",
                os.path.expanduser("~/ollama"),
                os.path.expanduser("~/.local/bin/ollama"),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.ollama_executable_path = path
                    print(f"[LLM Debug] 找到Ollama可执行文件: {path}")
                    return path
        
        print(f"[LLM Debug] 未找到Ollama可执行文件")
        return None
    
    def is_ollama_process_running(self) -> bool:
        """检查Ollama进程是否正在运行"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # 检查进程名或命令行参数
                    if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                        print(f"[LLM Debug] 找到Ollama进程: {proc.info['name']} (PID: {proc.info['pid']})")
                        return True
                    
                    # 检查命令行参数
                    if proc.info['cmdline']:
                        cmdline_str = ' '.join(proc.info['cmdline']).lower()
                        if 'ollama' in cmdline_str and ('serve' in cmdline_str or 'server' in cmdline_str):
                            print(f"[LLM Debug] 找到Ollama服务进程: {proc.info['cmdline']} (PID: {proc.info['pid']})")
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"[LLM Debug] 检查Ollama进程时出错: {e}")
        
        return False
    
    def start_ollama_service(self) -> Tuple[bool, str]:
        """启动Ollama服务"""
        # 检查服务是否已经在运行
        if self.is_server_running():
            return True, "Ollama服务已在运行"
        
        # 查找Ollama可执行文件
        ollama_path = self.find_ollama_executable()
        if not ollama_path:
            return False, "未找到Ollama可执行文件。请确保Ollama已安装。"
        
        try:
            print(f"[LLM Debug] 使用路径启动Ollama服务: {ollama_path}")
            
            # 启动Ollama服务
            if platform.system().lower() == "windows":
                # Windows下使用完整路径启动
                process = subprocess.Popen(
                    [ollama_path, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                # macOS和Linux
                process = subprocess.Popen(
                    [ollama_path, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print(f"[LLM Debug] Ollama服务启动中，PID: {process.pid}")
            
            # 等待服务启动
            max_wait_time = 15  # 增加等待时间
            for i in range(max_wait_time):
                time.sleep(1)
                if self.is_server_running():
                    print(f"[LLM Debug] Ollama服务启动成功，等待时间: {i+1}秒")
                    return True, f"Ollama服务启动成功 (等待{i+1}秒)"
                print(f"[LLM Debug] 等待Ollama服务启动... ({i+1}/{max_wait_time})")
            
            return False, f"Ollama服务启动超时（等待{max_wait_time}秒）"
            
        except Exception as e:
            error_msg = f"启动Ollama服务时出错: {str(e)}"
            print(f"[LLM Debug] {error_msg}")
            return False, error_msg
    
    def is_installed(self) -> bool:
        """检查Ollama是否已安装并运行中"""
        try:
            # 直接访问 base_url 检查 Ollama 是否运行
            response = requests.get(self.base_url, timeout=3)
            if response.status_code == 200:
                response_text = response.text.strip()
                # 检查返回内容是否包含 "Ollama is running"
                if "Ollama is running" in response_text:
                    print(f"[LLM Debug] Ollama is running at {self.base_url}")
                    return True
                else:
                    print(f"[LLM Debug] Unexpected response from {self.base_url}: {response_text}")
                    return False
            else:
                print(f"[LLM Debug] Ollama not responding at {self.base_url}, status: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"[LLM Debug] Failed to connect to Ollama at {self.base_url}: {str(e)}")
            return False
    
    def is_server_running(self) -> bool:
        """检查Ollama服务器是否正在运行"""
        try:
            print(f"[LLM Debug] Checking Ollama server at: {self.api_models_endpoint}")
            response = requests.get(self.api_models_endpoint, timeout=2)
            is_running = response.status_code == 200
            print(f"[LLM Debug] Ollama server running: {is_running}")
            return is_running
        except requests.RequestException as e:
            print(f"[LLM Debug] Ollama server check failed: {str(e)}")
            return False
    
    def get_locally_available_models(self) -> List[str]:
        """获取本地已下载的模型列表"""
        if not self.is_server_running():
            print("[LLM Debug] Ollama server not running, returning empty model list")
            return []
        
        try:
            print(f"[LLM Debug] Fetching Ollama models from: {self.api_models_endpoint}")
            response = requests.get(self.api_models_endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data["models"]] if "models" in data else []
                print(f"[LLM Debug] Found {len(models)} Ollama models: {models}")
                return models
            else:
                print(f"[LLM Debug] Failed to get Ollama models, status: {response.status_code}")
            return []
        except requests.RequestException as e:
            print(f"[LLM Debug] Error fetching Ollama models: {str(e)}")
            return []
    
    def start_server(self) -> bool:
        """启动Ollama服务器（兼容旧接口）"""
        success, message = self.start_ollama_service()
        if success:
            print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{message}{Style.RESET_ALL}")
            raise OllamaError(message)
        return success
    
    def download_model(self, model_name: str) -> bool:
        """下载Ollama模型"""
        if not self.is_server_running():
            if not self.start_server():
                return False
        
        print(f"{Fore.YELLOW}正在下载模型 {model_name}...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}这可能需要一些时间，取决于您的网络速度和模型大小。{Style.RESET_ALL}")
        
        try:
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            # 显示进度
            print(f"{Fore.CYAN}下载进度:{Style.RESET_ALL}")
            
            last_percentage = 0
            last_phase = ""
            bar_length = 40
            
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    output = output.strip()
                    percentage = None
                    current_phase = None
                    
                    # 提取百分比信息
                    percentage_match = re.search(r"(\d+(\.\d+)?)%", output)
                    if percentage_match:
                        try:
                            percentage = float(percentage_match.group(1))
                        except ValueError:
                            percentage = None
                    
                    # 确定当前阶段
                    phase_match = re.search(r"^([a-zA-Z\s]+):", output)
                    if phase_match:
                        current_phase = phase_match.group(1).strip()
                    
                    # 显示进度条
                    if percentage is not None:
                        if abs(percentage - last_percentage) >= 1 or (current_phase and current_phase != last_phase):
                            last_percentage = percentage
                            if current_phase:
                                last_phase = current_phase
                            
                            filled_length = int(bar_length * percentage / 100)
                            bar = "█" * filled_length + "░" * (bar_length - filled_length)
                            
                            phase_display = f"{Fore.CYAN}{last_phase.capitalize()}{Style.RESET_ALL}: " if last_phase else ""
                            status_line = f"\r{phase_display}{Fore.GREEN}{bar}{Style.RESET_ALL} {Fore.YELLOW}{percentage:.1f}%{Style.RESET_ALL}"
                            
                            print(status_line, end="", flush=True)
            
            return_code = process.wait()
            print()  # 换行
            
            if return_code == 0:
                print(f"{Fore.GREEN}模型 {model_name} 下载成功！{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}下载模型 {model_name} 失败。请检查网络连接并重试。{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"\n{Fore.RED}下载模型 {model_name} 时出错: {e}{Style.RESET_ALL}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除本地下载的Ollama模型"""
        if not self.is_server_running():
            if not self.start_server():
                return False
        
        print(f"{Fore.YELLOW}正在删除模型 {model_name}...{Style.RESET_ALL}")
        
        try:
            process = subprocess.run(
                ["ollama", "rm", model_name], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            if process.returncode == 0:
                print(f"{Fore.GREEN}模型 {model_name} 删除成功。{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}删除模型 {model_name} 失败。错误: {process.stderr}{Style.RESET_ALL}")
                return False
                
        except Exception as e:
            print(f"{Fore.RED}删除模型 {model_name} 时出错: {e}{Style.RESET_ALL}")
            return False
    
    def ensure_model_available(self, model_name: str) -> bool:
        """确保模型可用（如果不存在则下载）"""
        # 检查Docker环境
        in_docker = (
            os.environ.get("OLLAMA_BASE_URL", "").startswith("http://ollama:") or 
            os.environ.get("OLLAMA_BASE_URL", "").startswith("http://host.docker.internal:")
        )
        
        if in_docker:
            # Docker环境下的处理逻辑
            print(f"{Fore.YELLOW}检测到Docker环境，使用容器化Ollama服务{Style.RESET_ALL}")
            return True  # 假设Docker环境已正确配置
        
        # 检查是否为远程Ollama服务
        is_remote_service = (
            self.base_url != "http://localhost:11434" and 
            not self.base_url.startswith("http://127.0.0.1") and
            not self.base_url.startswith("http://localhost")
        )
        
        # 检查Ollama是否运行（新的检测逻辑：直接访问base_url）
        if not self.is_installed():
            raise OllamaError("Ollama未安装。请先安装Ollama。")
        
        # 检查模型是否已下载
        available_models = self.get_locally_available_models()
        
        # 改进模型匹配逻辑：支持模糊匹配
        model_found = False
        matched_model = None
        
        # 首先尝试精确匹配
        if model_name in available_models:
            model_found = True
            matched_model = model_name
        else:
            # 尝试模糊匹配：检查是否有以model_name开头的模型
            for available_model in available_models:
                if available_model.startswith(model_name + ":") or available_model == model_name:
                    model_found = True
                    matched_model = available_model
                    break
            
            # 如果还没找到，尝试更宽松的匹配（去掉版本标签）
            if not model_found:
                base_model_name = model_name.split(":")[0]  # 去掉可能的标签
                for available_model in available_models:
                    available_base_name = available_model.split(":")[0]
                    if available_base_name == base_model_name:
                        model_found = True
                        matched_model = available_model
                        break
        
        if not model_found:
            # 如果模型名称没有标签，尝试添加:latest
            download_model_name = model_name if ":" in model_name else f"{model_name}:latest"
            print(f"{Fore.YELLOW}模型 {model_name} 在本地不可用。{Style.RESET_ALL}")
            return self.download_model(download_model_name)
        else:
            print(f"{Fore.GREEN}找到匹配的模型: {matched_model}{Style.RESET_ALL}")
            return True


# 全局实例
_ollama_manager = None


def get_ollama_manager(base_url: Optional[str] = None) -> OllamaManager:
    """获取Ollama管理器实例"""
    global _ollama_manager
    if _ollama_manager is None or (base_url and base_url != _ollama_manager.base_url):
        _ollama_manager = OllamaManager(base_url)
    return _ollama_manager


# 便捷函数
def is_ollama_installed() -> bool:
    """检查Ollama是否已安装"""
    return get_ollama_manager().is_installed()


def is_ollama_server_running() -> bool:
    """检查Ollama服务器是否正在运行"""
    return get_ollama_manager().is_server_running()


def get_locally_available_models() -> List[str]:
    """获取本地已下载的模型列表"""
    return get_ollama_manager().get_locally_available_models()


def start_ollama_server() -> bool:
    """启动Ollama服务器"""
    return get_ollama_manager().start_server()


def download_model(model_name: str) -> bool:
    """下载Ollama模型"""
    return get_ollama_manager().download_model(model_name)


def ensure_ollama_and_model(model_name: str, base_url: Optional[str] = None) -> bool:
    """确保Ollama和指定模型可用"""
    try:
        manager = get_ollama_manager(base_url)
        
        # 检查是否为远程Ollama服务
        is_remote_service = (
            manager.base_url != "http://localhost:11434" and 
            not manager.base_url.startswith("http://127.0.0.1") and
            not manager.base_url.startswith("http://localhost")
        )
        
        print(f"[LLM Debug] Ollama service type: {'Remote' if is_remote_service else 'Local'}")
        print(f"[LLM Debug] Ollama base URL: {manager.base_url}")
        
        # 检查Ollama是否运行，如果没有运行则尝试自动启动
        if not manager.is_server_running():
            print(f"[LLM Debug] {Fore.YELLOW}Ollama服务未运行，尝试自动启动...{Style.RESET_ALL}")
            
            # 尝试自动启动Ollama服务
            success, message = manager.start_ollama_service()
            if not success:
                print(f"[LLM Debug] {Fore.RED}自动启动Ollama失败: {message}{Style.RESET_ALL}")
                return False
            else:
                print(f"[LLM Debug] {Fore.GREEN}Ollama服务自动启动成功: {message}{Style.RESET_ALL}")
        
        # 再次检查服务是否正常运行
        if not manager.is_installed():
            print(f"[LLM Debug] {Fore.YELLOW}Ollama服务仍然无法访问{Style.RESET_ALL}")
            return False
        
        print(f"[LLM Debug] Ollama is running and accessible at {manager.base_url}")
        
        # 检查模型是否可用
        local_models = manager.get_locally_available_models()
        
        # 改进模型匹配逻辑：支持模糊匹配
        model_found = False
        matched_model = None
        
        # 首先尝试精确匹配
        if model_name in local_models:
            model_found = True
            matched_model = model_name
        else:
            # 尝试模糊匹配：检查是否有以model_name开头的模型
            for local_model in local_models:
                if local_model.startswith(model_name + ":") or local_model == model_name:
                    model_found = True
                    matched_model = local_model
                    break
            
            # 如果还没找到，尝试更宽松的匹配（去掉版本标签）
            if not model_found:
                base_model_name = model_name.split(":")[0]  # 去掉可能的标签
                for local_model in local_models:
                    local_base_name = local_model.split(":")[0]
                    if local_base_name == base_model_name:
                        model_found = True
                        matched_model = local_model
                        break
        
        if not model_found:
            # 如果模型名称没有标签，尝试添加:latest
            download_model_name = model_name if ":" in model_name else f"{model_name}:latest"
            print(f"{Fore.YELLOW}模型 {model_name} 未找到，尝试下载...{Style.RESET_ALL}")
            return manager.download_model(download_model_name)
        else:
            print(f"{Fore.GREEN}找到匹配的模型: {matched_model}{Style.RESET_ALL}")
            return True
        
    except Exception as e:
        print(f"{Fore.RED}确保Ollama和模型可用时出错: {e}{Style.RESET_ALL}")
        return False