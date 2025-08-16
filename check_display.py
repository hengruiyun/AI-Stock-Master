#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Display Adapter Checker and Ollama Installer
显卡检测器和Ollama安装器

功能:
1. 检测当前显卡供应商及型号
2. 如果是NVIDIA 2000以上显卡且缺少CUDA支持文件，则自动下载安装Ollama
3. 下载过程显示进度条和百分比
4. 记录下载历史，避免重复下载

使用方法:
python check_display.py
"""

import os
import sys
import subprocess
import requests
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import re

class DisplayChecker:
    def __init__(self):
        self.cuda_dll_files = [
            os.path.expanduser("~\\AppData\\Local\\Programs\\Ollama\\lib\\ollama\\ggml-cuda.dll"),
            None  # 将在find_ollama_exe后设置
        ]
        self.ollama_exe_path = None
        self.ollama_download_url = "https://ollama.com/download/OllamaSetup.exe"
        self.download_record_file = "check_display.json"
        
    def print_header(self):
        """打印程序头部信息 / Print program header"""
        print("="*70)
        print("Display Adapter Checker and Ollama Installer")
        print("显卡检测器和Ollama安装器")
        print("="*70)
    
    def print_bilingual(self, en_text: str, zh_text: str):
        """双语输出 / Print in both languages"""
        print(f"{en_text} / {zh_text}")
    
    def load_download_record(self) -> Dict:
        """
        加载下载记录 / Load download record
        """
        if os.path.exists(self.download_record_file):
            try:
                with open(self.download_record_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.print_bilingual(
                    f"Error loading download record: {e}",
                    f"加载下载记录时出错: {e}"
                )
        return {}
    
    def save_download_record(self, record: Dict):
        """
        保存下载记录 / Save download record
        """
        try:
            with open(self.download_record_file, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.print_bilingual(
                f"Error saving download record: {e}",
                f"保存下载记录时出错: {e}"
            )
    
    def check_download_history(self) -> bool:
        """
        检查是否已有下载记录 / Check if there's already a download record
        返回 True 表示已有下载记录，False 表示无记录
        """
        record = self.load_download_record()
        if "ollama_downloads" in record and record["ollama_downloads"]:
            last_download = record["ollama_downloads"][-1]
            download_time = last_download.get("download_time", "Unknown")
            self.print_bilingual(
                f"Found previous download record: {download_time}",
                f"发现先前的下载记录: {download_time}"
            )
            return True
        return False
    
    def record_download(self):
        """
        记录本次下载信息 / Record current download info
        """
        record = self.load_download_record()
        if "ollama_downloads" not in record:
            record["ollama_downloads"] = []
        
        download_info = {
            "download_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "download_url": self.ollama_download_url,
            "system_info": {
                "os": os.name,
                "platform": sys.platform
            }
        }
        
        record["ollama_downloads"].append(download_info)
        self.save_download_record(record)
        
    def get_gpu_info(self) -> List[Tuple[str, str, int]]:
        """
        获取显卡信息 / Get GPU information
        返回: [(供应商, 型号, 系列号), ...]
        """
        self.print_bilingual("[1] Detecting GPU information...", "[1] 检测显卡信息...")
        gpu_info = []
        
        try:
            # 使用wmic获取显卡信息
            result = subprocess.run([
                "wmic", "path", "win32_VideoController", 
                "get", "name,AdapterCompatibility", "/format:csv"
            ], capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # 跳过标题行
                    if line.strip() and ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 3:
                            vendor = parts[1].strip() if parts[1] else ""
                            name = parts[2].strip() if parts[2] else ""
                            
                            if vendor and name:
                                # 提取NVIDIA显卡型号中的数字
                                series_num = self.extract_nvidia_series(vendor, name)
                                gpu_info.append((vendor, name, series_num))
                                self.print_bilingual(f"  Found GPU: {vendor} - {name}", f"  发现显卡: {vendor} - {name}")
                                if series_num > 0:
                                    self.print_bilingual(f"    NVIDIA Series: {series_num}", f"    NVIDIA系列: {series_num}")
            
            # 如果wmic失败，尝试使用dxdiag
            if not gpu_info:
                self.print_bilingual("  wmic method failed, trying dxdiag...", "  wmic方法失败，尝试使用dxdiag...")
                gpu_info = self.get_gpu_info_dxdiag()
                
        except Exception as e:
            self.print_bilingual(f"  Error detecting GPU info: {e}", f"  检测显卡信息时出错: {e}")
            self.print_bilingual("  Trying dxdiag...", "  尝试使用dxdiag...")
            gpu_info = self.get_gpu_info_dxdiag()
            
        if not gpu_info:
            self.print_bilingual("  ✗ Cannot detect GPU information", "  ✗ 无法检测到显卡信息")
        else:
            self.print_bilingual(f"  ✓ Detected {len(gpu_info)} GPU(s)", f"  ✓ 检测到 {len(gpu_info)} 个显卡")
            
        return gpu_info
    
    def get_gpu_info_dxdiag(self) -> List[Tuple[str, str, int]]:
        """使用dxdiag获取显卡信息 / Get GPU info using dxdiag"""
        gpu_info = []
        try:
            # 创建临时文件
            temp_file = "dxdiag_temp.txt"
            
            # 运行dxdiag
            result = subprocess.run([
                "dxdiag", "/t", temp_file
            ], capture_output=True, timeout=30)
            
            # 等待文件生成
            time.sleep(2)
            
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # 查找显卡信息
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if "Card name:" in line:
                        name = line.split("Card name:")[-1].strip()
                        vendor = "Unknown"
                        
                        # 判断供应商
                        name_lower = name.lower()
                        if "nvidia" in name_lower or "geforce" in name_lower:
                            vendor = "NVIDIA"
                        elif "amd" in name_lower or "radeon" in name_lower:
                            vendor = "AMD"
                        elif "intel" in name_lower:
                            vendor = "Intel"
                        
                        series_num = self.extract_nvidia_series(vendor, name)
                        gpu_info.append((vendor, name, series_num))
                        self.print_bilingual(f"  Found GPU: {vendor} - {name}", f"  发现显卡: {vendor} - {name}")
                        if series_num > 0:
                            self.print_bilingual(f"    NVIDIA Series: {series_num}", f"    NVIDIA系列: {series_num}")
                
                # 清理临时文件
                os.remove(temp_file)
                
        except Exception as e:
            self.print_bilingual(f"  dxdiag method failed: {e}", f"  dxdiag方法失败: {e}")
            # 清理临时文件
            try:
                if os.path.exists("dxdiag_temp.txt"):
                    os.remove("dxdiag_temp.txt")
            except:
                pass
                
        return gpu_info
    
    def extract_nvidia_series(self, vendor: str, name: str) -> int:
        """
        从NVIDIA显卡名称中提取系列号
        例如: "GeForce RTX 3080" -> 3080, "GTX 1660" -> 1660
        """
        if vendor.upper() != "NVIDIA":
            return 0
            
        # 匹配NVIDIA显卡型号中的数字
        patterns = [
            r'RTX\s*(\d{4})',  # RTX 3080, RTX 4090等
            r'GTX\s*(\d{4})',  # GTX 1660, GTX 1080等
            r'(\d{4})\s*Ti',   # 2080 Ti等
            r'(\d{4})',        # 通用4位数字
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                series_num = int(match.group(1))
                return series_num
                
        return 0
    
    def find_ollama_exe(self) -> Optional[str]:
        """
        查找Ollama.exe路径 / Find Ollama.exe path (reference check_ollama_env.py implementation)
        """
        self.print_bilingual("\n[2] Searching for Ollama.exe...", "\n[2] 查找Ollama.exe...")
        
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
                self.print_bilingual(f"  ✓ Found Ollama.exe: {path}", f"  ✓ 找到Ollama.exe: {path}")
                # 设置第二个CUDA DLL路径
                exe_dir = os.path.dirname(path)
                self.cuda_dll_files[1] = os.path.join(exe_dir, "lib", "ollama", "ggml-cuda.dll")
                return path
        
        # 在PATH环境变量中搜索
        try:
            result = subprocess.run(["where", "ollama"], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                self.ollama_exe_path = result.stdout.strip().split('\n')[0]
                self.print_bilingual(f"  ✓ Found Ollama.exe in PATH: {self.ollama_exe_path}", f"  ✓ 在PATH中找到Ollama.exe: {self.ollama_exe_path}")
                # 设置第二个CUDA DLL路径
                exe_dir = os.path.dirname(self.ollama_exe_path)
                self.cuda_dll_files[1] = os.path.join(exe_dir, "lib", "ollama", "ggml-cuda.dll")
                return self.ollama_exe_path
        except Exception:
            pass
            
        self.print_bilingual("  ✗ Ollama.exe not found", "  ✗ 未找到Ollama.exe")
        return None
    
    def check_cuda_support(self) -> bool:
        """检查CUDA支持文件是否存在 / Check if CUDA support files exist"""
        self.print_bilingual("\n[3] Checking CUDA support files...", "\n[3] 检查CUDA支持文件...")
        
        for i, cuda_file in enumerate(self.cuda_dll_files):
            if cuda_file is None:
                continue
                
            location_en = "User directory" if i == 0 else "Ollama installation directory"
            location_zh = "用户目录" if i == 0 else "Ollama安装目录"
            self.print_bilingual(f"  Checking {location_en}: {cuda_file}", f"  检查 {location_zh}: {cuda_file}")
            
            if os.path.exists(cuda_file):
                self.print_bilingual(f"  ✓ Found CUDA support file: {cuda_file}", f"  ✓ 找到CUDA支持文件: {cuda_file}")
                return True
            else:
                self.print_bilingual(f"  ✗ CUDA support file not found: {cuda_file}", f"  ✗ 未找到CUDA支持文件: {cuda_file}")
        
        self.print_bilingual("  ✗ All CUDA support files are missing", "  ✗ 所有CUDA支持文件都不存在")
        return False
    
    def download_file_with_progress(self, url: str, filename: str) -> bool:
        """
        下载文件并显示进度条 / Download file with progress bar [[memory:4721131]]
        """
        self.print_bilingual(f"\n[4] Downloading {filename}...", f"\n[4] 下载 {filename}...")
        self.print_bilingual(f"  Download URL: {url}", f"  下载地址: {url}")
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0:
                self.print_bilingual("  Cannot get file size, using simple download mode...", "  无法获取文件大小，使用简单下载模式...")
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            print(".", end="", flush=True)
                print()
                self.print_bilingual("  ✓ Download completed", "  ✓ 下载完成")
                return True
            
            downloaded_size = 0
            chunk_size = 8192
            
            self.print_bilingual(f"  File size: {total_size / (1024*1024):.1f} MB", f"  文件大小: {total_size / (1024*1024):.1f} MB")
            print("  Download progress: / 下载进度: ", end="", flush=True)
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 计算进度百分比（整数显示）
                        percentage = int((downloaded_size / total_size) * 100)
                        
                        # 每10%显示一次进度
                        if percentage % 10 == 0 and percentage > 0:
                            print(f" {percentage}%", end="", flush=True)
                        elif downloaded_size % (chunk_size * 10) == 0:
                            print(".", end="", flush=True)
            
            print(f" 100%")
            self.print_bilingual(f"  ✓ Download completed: {filename}", f"  ✓ 下载完成: {filename}")
            return True
            
        except requests.RequestException as e:
            self.print_bilingual(f"  ✗ Download failed: {e}", f"  ✗ 下载失败: {e}")
            return False
        except Exception as e:
            self.print_bilingual(f"  ✗ Error during download: {e}", f"  ✗ 下载时出错: {e}")
            return False
    
    def install_ollama(self, exe_file: str) -> bool:
        """安装Ollama / Install Ollama"""
        self.print_bilingual(f"\n[5] Installing Ollama...", f"\n[5] 安装Ollama...")
        self.print_bilingual(f"  Installation file: {exe_file}", f"  安装文件: {exe_file}")
        
        try:
            # 运行安装程序
            self.print_bilingual("  Starting installer, please complete installation in the interface...", "  正在启动安装程序，请在安装界面中完成安装...")
            result = subprocess.run([exe_file], check=True)
            
            self.print_bilingual("  ✓ Ollama installation completed", "  ✓ Ollama安装完成")
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_bilingual(f"  ✗ Installation failed: {e}", f"  ✗ 安装失败: {e}")
            return False
        except Exception as e:
            self.print_bilingual(f"  ✗ Error during installation: {e}", f"  ✗ 安装时出错: {e}")
            return False
    
    def cleanup_temp_files(self, filename: str):
        """清理临时文件 / Clean up temporary files"""
        try:
            if os.path.exists(filename):
                os.remove(filename)
                self.print_bilingual(f"  ✓ Cleaned up temporary file: {filename}", f"  ✓ 已清理临时文件: {filename}")
        except Exception as e:
            self.print_bilingual(f"  ⚠ Failed to clean up temporary file: {e}", f"  ⚠ 清理临时文件失败: {e}")
    
    def run_check(self) -> bool:
        """运行完整的检查流程 / Run complete check process"""
        self.print_header()
        
        # 1. 检测显卡信息
        gpu_info = self.get_gpu_info()
        if not gpu_info:
            self.print_bilingual("\n✗ Cannot detect GPU information, program terminated", "\n✗ 无法检测到显卡信息，程序终止")
            return False
        
        # 2. 检查是否有NVIDIA 2000以上系列显卡
        has_high_end_nvidia = False
        for vendor, name, series_num in gpu_info:
            if vendor.upper() == "NVIDIA" and series_num >= 2000:
                self.print_bilingual(f"\n✓ Detected high-end NVIDIA GPU: {name} (Series: {series_num})", f"\n✓ 检测到NVIDIA高端显卡: {name} (系列: {series_num})")
                has_high_end_nvidia = True
                break
        
        if not has_high_end_nvidia:
            nvidia_cards = [info for info in gpu_info if info[0].upper() == "NVIDIA"]
            if nvidia_cards:
                self.print_bilingual("\n• Detected NVIDIA GPU(s), but not 2000 series or above:", "\n• 检测到NVIDIA显卡，但不是2000系列以上:")
                for vendor, name, series_num in nvidia_cards:
                    series_text = str(series_num) if series_num > 0 else "Unknown/未知"
                    self.print_bilingual(f"  - {name} (Series: {series_text})", f"  - {name} (系列: {series_text})")
            else:
                self.print_bilingual("\n• No NVIDIA GPU detected", "\n• 未检测到NVIDIA显卡")
            self.print_bilingual("  No need to install CUDA version of Ollama", "  不需要安装CUDA版本的Ollama")
            return True
        
        # 3. 查找现有的Ollama安装
        self.find_ollama_exe()
        
        # 4. 检查CUDA支持文件
        if self.check_cuda_support():
            self.print_bilingual("\n✓ CUDA support files already exist, no need to reinstall Ollama", "\n✓ CUDA支持文件已存在，无需重新安装Ollama")
            return True
        
        # 5. 检查下载历史
        if self.check_download_history():
            self.print_bilingual("\nSkipping download due to existing download record.", "\n由于存在下载记录，跳过下载。")
            self.print_bilingual("If you need to reinstall, please delete check_display.json first.", "如需重新安装，请先删除 check_display.json 文件。")
            return True
        
        # 6. 下载并安装Ollama
        self.print_bilingual("\n• Need to install CUDA-enabled Ollama version", "\n• 需要安装支持CUDA的Ollama版本")
        
        download_filename = "OllamaSetup.exe"
        
        # 下载Ollama安装程序
        if not self.download_file_with_progress(self.ollama_download_url, download_filename):
            return False
        
        # 记录下载信息
        self.record_download()
        
        # 安装Ollama
        install_success = self.install_ollama(download_filename)
        
        # 清理临时文件
        self.cleanup_temp_files(download_filename)
        
        if install_success:
            print("\n" + "="*70)
            self.print_bilingual("✓ All operations completed!", "✓ 所有操作已完成!")
            self.print_bilingual("✓ CUDA-enabled Ollama has been installed", "✓ 支持CUDA的Ollama已安装")
            self.print_bilingual("  Note: Please restart command line window to use the newly installed Ollama", "  注意: 请重启命令行窗口以使用新安装的Ollama")
            print("="*70)
        
        return install_success

def main():
    """主函数 / Main function"""
    # 检查帮助参数
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', '/h', '/?']:
        print("Display Adapter Checker and Ollama Installer")
        print("显卡检测器和Ollama安装器")
        print()
        print("Functions / 功能:")
        print("  1. Detect current GPU vendor and model / 检测当前显卡供应商及型号")
        print("  2. Check if it's NVIDIA 2000 series or above / 判断是否为NVIDIA 2000系列以上显卡")
        print("  3. Check if CUDA support files exist / 检查CUDA支持文件是否存在")
        print("  4. Check download history to avoid duplicate downloads / 检查下载历史避免重复下载")
        print("  5. Auto download and install CUDA-enabled Ollama (if needed) / 自动下载并安装支持CUDA的Ollama (如需要)")
        print()
        print("Usage / 使用方法:")
        print("  python check_display.py")
        print()
        print("Download Record / 下载记录:")
        print("  check_display.json - stores download history / 存储下载历史")
        sys.exit(0)
    
    # 创建检查器并运行
    checker = DisplayChecker()
    success = checker.run_check()
    
    # 退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()