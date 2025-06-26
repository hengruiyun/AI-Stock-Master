"""Ollama工具函数模块"""

import platform
import subprocess
import requests
import time
import os
import re
from typing import List, Optional
from colorama import Fore, Style

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
    
    def is_installed(self) -> bool:
        """检查Ollama是否已安装"""
        system = platform.system().lower()
        
        if system in ["darwin", "linux"]:
            try:
                result = subprocess.run(
                    ["which", "ollama"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                return result.returncode == 0
            except Exception:
                return False
        elif system == "windows":
            try:
                result = subprocess.run(
                    ["where", "ollama"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    shell=True
                )
                return result.returncode == 0
            except Exception:
                return False
        else:
            return False
    
    def is_server_running(self) -> bool:
        """检查Ollama服务器是否正在运行"""
        try:
            response = requests.get(self.api_models_endpoint, timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_locally_available_models(self) -> List[str]:
        """获取本地已下载的模型列表"""
        if not self.is_server_running():
            return []
        
        try:
            response = requests.get(self.api_models_endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data["models"]] if "models" in data else []
            return []
        except requests.RequestException:
            return []
    
    def start_server(self) -> bool:
        """启动Ollama服务器"""
        if self.is_server_running():
            print(f"{Fore.GREEN}Ollama服务器已在运行。{Style.RESET_ALL}")
            return True
        
        system = platform.system().lower()
        
        try:
            if system in ["darwin", "linux"]:
                subprocess.Popen(
                    ["ollama", "serve"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
            elif system == "windows":
                subprocess.Popen(
                    ["ollama", "serve"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    shell=True
                )
            else:
                raise OllamaError(f"不支持的操作系统: {system}")
            
            # 等待服务器启动
            for _ in range(10):  # 尝试10秒
                if self.is_server_running():
                    print(f"{Fore.GREEN}Ollama服务器启动成功。{Style.RESET_ALL}")
                    return True
                time.sleep(1)
            
            raise OllamaError("启动Ollama服务器超时")
            
        except Exception as e:
            raise OllamaError(f"启动Ollama服务器时出错: {e}")
    
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
        
        # 检查Ollama是否已安装
        if not self.is_installed():
            raise OllamaError("Ollama未安装。请先安装Ollama。")
        
        # 确保服务器运行
        if not self.is_server_running():
            print(f"{Fore.YELLOW}启动Ollama服务器...{Style.RESET_ALL}")
            if not self.start_server():
                return False
        
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


def ensure_ollama_and_model(model_name: str) -> bool:
    """确保Ollama和指定模型可用"""
    try:
        manager = get_ollama_manager()
        
        # 检查Ollama是否安装
        if not manager.is_installed():
            print(f"{Fore.YELLOW}Ollama未安装，请先安装Ollama{Style.RESET_ALL}")
            return False
        
        # 检查服务器是否运行
        if not manager.is_server_running():
            print(f"{Fore.YELLOW}Ollama服务器未运行，尝试启动...{Style.RESET_ALL}")
            if not manager.start_server():
                return False
        
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