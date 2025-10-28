#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI使用次数统计模块

功能：
1. 记录AI分析的使用次数
2. 使用Windows注册表持久化存储
3. 跨平台支持（Windows使用注册表，其他系统使用文件）
"""

import sys
import os
from pathlib import Path


class AIUsageCounter:
    """AI使用次数计数器"""
    
    def __init__(self):
        """初始化计数器"""
        self.count = 0
        self.is_windows = sys.platform == 'win32'
        
        if self.is_windows:
            try:
                import winreg
                self.winreg = winreg
                self.reg_path = r"Software\AIStockMaster"
                self.reg_key_name = "AIUsageCount"
                print("[AI计数器] Windows系统，使用注册表存储")
            except ImportError:
                print("[AI计数器] 警告：无法导入winreg模块，回退到文件存储")
                self.is_windows = False
                self._init_file_storage()
        else:
            print("[AI计数器] 非Windows系统，使用文件存储")
            self._init_file_storage()
        
        # 启动时读取已有计数
        self._load_count()
    
    def _init_file_storage(self):
        """初始化文件存储（非Windows系统）"""
        self.storage_dir = Path.home() / ".ai_stock_master"
        self.storage_file = self.storage_dir / "ai_usage_count.txt"
        
        # 确保目录存在
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_count(self):
        """从存储中加载计数"""
        try:
            if self.is_windows:
                self.count = self._load_from_registry()
            else:
                self.count = self._load_from_file()
            
            print(f"[AI计数器] 已加载使用次数: {self.count}")
        except Exception as e:
            print(f"[AI计数器] 加载计数失败: {e}，从0开始")
            self.count = 0
    
    def _load_from_registry(self):
        """从Windows注册表加载计数"""
        try:
            # 尝试打开注册表键
            key = self.winreg.OpenKey(
                self.winreg.HKEY_CURRENT_USER,
                self.reg_path,
                0,
                self.winreg.KEY_READ
            )
            
            # 读取值
            value, _ = self.winreg.QueryValueEx(key, self.reg_key_name)
            self.winreg.CloseKey(key)
            
            return int(value)
        except FileNotFoundError:
            # 注册表键不存在，返回0
            print("[AI计数器] 注册表键不存在，首次使用")
            return 0
        except Exception as e:
            print(f"[AI计数器] 读取注册表失败: {e}")
            return 0
    
    def _load_from_file(self):
        """从文件加载计数"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    content = f.read().strip()
                    return int(content) if content else 0
            else:
                print("[AI计数器] 计数文件不存在，首次使用")
                return 0
        except Exception as e:
            print(f"[AI计数器] 读取文件失败: {e}")
            return 0
    
    def increment(self):
        """增加计数并保存"""
        self.count += 1
        print(f"[AI计数器] AI使用次数: {self.count}")
        
        # 立即保存到存储
        self._save_count()
        
        return self.count
    
    def _save_count(self):
        """保存计数到存储"""
        try:
            if self.is_windows:
                self._save_to_registry()
            else:
                self._save_to_file()
        except Exception as e:
            print(f"[AI计数器] 保存计数失败: {e}")
    
    def _save_to_registry(self):
        """保存计数到Windows注册表"""
        try:
            # 尝试创建或打开注册表键
            key = self.winreg.CreateKeyEx(
                self.winreg.HKEY_CURRENT_USER,
                self.reg_path,
                0,
                self.winreg.KEY_WRITE
            )
            
            # 设置值
            self.winreg.SetValueEx(
                key,
                self.reg_key_name,
                0,
                self.winreg.REG_DWORD,
                self.count
            )
            
            self.winreg.CloseKey(key)
            print(f"[AI计数器] 已保存到注册表: {self.count}")
        except Exception as e:
            print(f"[AI计数器] 保存到注册表失败: {e}")
            raise
    
    def _save_to_file(self):
        """保存计数到文件"""
        try:
            with open(self.storage_file, 'w') as f:
                f.write(str(self.count))
            print(f"[AI计数器] 已保存到文件: {self.count}")
        except Exception as e:
            print(f"[AI计数器] 保存到文件失败: {e}")
            raise
    
    def get_count(self):
        """获取当前计数"""
        return self.count
    
    def reset(self):
        """重置计数（仅用于测试）"""
        self.count = 0
        self._save_count()
        print("[AI计数器] 计数已重置为0")


# 全局单例
_ai_counter_instance = None


def get_ai_counter():
    """获取全局AI计数器实例"""
    global _ai_counter_instance
    if _ai_counter_instance is None:
        _ai_counter_instance = AIUsageCounter()
    return _ai_counter_instance


def increment_ai_usage():
    """增加AI使用次数（便捷函数）"""
    counter = get_ai_counter()
    return counter.increment()


def get_ai_usage_count():
    """获取AI使用次数（便捷函数）"""
    counter = get_ai_counter()
    return counter.get_count()


# 测试代码
if __name__ == "__main__":
    print("="*60)
    print("AI使用次数计数器测试")
    print("="*60)
    
    # 创建计数器
    counter = AIUsageCounter()
    
    # 显示当前计数
    print(f"\n当前计数: {counter.get_count()}")
    
    # 增加几次
    print("\n模拟AI使用...")
    for i in range(3):
        count = counter.increment()
        print(f"  第{i+1}次调用，当前总计: {count}")
    
    print(f"\n最终计数: {counter.get_count()}")
    
    # 测试重新加载
    print("\n重新创建计数器实例（模拟应用重启）...")
    counter2 = AIUsageCounter()
    print(f"新实例读取的计数: {counter2.get_count()}")
    
    print("\n"+"="*60)
    print("测试完成！")
    print("="*60)








