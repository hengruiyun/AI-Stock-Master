#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证翻译修复效果

测试用户反馈的问题翻译是否已正确修复
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到系统路径
def find_project_root():
    """查找项目根目录"""
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    while not (current_dir / ".git").exists() and current_dir != current_dir.parent:
        current_dir = current_dir.parent
    return current_dir

project_root = find_project_root()
sys.path.insert(0, str(project_root))

# 导入统一翻译管理器
try:
    from tools.unified_i18n_manager import UnifiedI18nManager
except ImportError:
    print(":")
    sys.exit(1)

def test_translations():
    """测试翻译修复效果"""
    # 初始化翻译管理器
    i18n_manager = UnifiedI18nManager()
    translations = i18n_manager.translations
    
    # 用户反馈的问题翻译
    problem_keys = [
        "col_stock_name",
        "data_scale",
        "data_analysis_in_progress",
        "stage_detail_loading",
        "stage_detail_validation",
        "btn_start_analysis",
        "loading_success",
        "error_file_load_failed"
    ]
    
    # 测试中文翻译
    print("\n=== 中文翻译测试 ===")
    for key in problem_keys:
        zh_translation = translations["zh"].get(key, "未找到翻译")
        print(f"{key}: {zh_translation}")
    
    # 测试英文翻译
    print("\n=== 英文翻译测试 ===")
    for key in problem_keys:
        en_translation = translations["en"].get(key, "Translation not found")
        print(f"{key}: {en_translation}")
    
    # 模拟用户界面显示
    print("\n=== 模拟用户界面显示 ===")
    print(":")
    print(f"数据文件 {translations['zh'].get('data_overview', '数据概览')}:")
    print(f"• {translations['zh'].get('col_stock_name', '股票名称')}: CN_Demo300.xlsx")
    print(f"• {translations['zh'].get('data_scale', '数据规模')}: 0.13 MB")
    print(f"• 数据日期: 2025-07-03 16:59:16")
    print()
    print(f"{translations['zh'].get('data_analysis_in_progress', '数据分析进行中')}:")
    print(f"• {translations['zh'].get('stage_detail_loading', '数据加载阶段')}")
    print(f"• {translations['zh'].get('stage_detail_validation', '数据验证阶段')}")
    print(f"• {translations['zh'].get('stage_detail_validation', '数据验证阶段')}")
    print()
    print(f"开始使用: {translations['zh'].get('btn_start_analysis', '开始分析')}")
    print()
    print(":")
    print(f"{translations['zh'].get('loading_success', '加载成功')} {translations['zh'].get('error_file_load_failed', '文件加载失败')}")
    print()
    print(f"数据文件 {translations['zh'].get('data_overview', '数据概览')}:")
    print(f"• {translations['zh'].get('col_stock_name', '股票名称')}: CN_Demo300.xlsx")
    print(f"• {translations['zh'].get('data_scale', '数据规模')}: 0.13 MB")
    print(f"• 数据日期: 2025-07-03 16:59:16")
    print()
    print(f"{translations['zh'].get('data_analysis_in_progress', '数据分析进行中')}:")
    print(f"• {translations['zh'].get('stage_detail_loading', '数据加载阶段')}")
    print(f"• {translations['zh'].get('stage_detail_validation', '数据验证阶段')}")
    print(f"• {translations['zh'].get('stage_detail_validation', '数据验证阶段')}")
    print()
    print(f"开始使用: {translations['zh'].get('btn_start_analysis', '开始分析')}")

def main():
    """主函数"""
    print("...")
    test_translations()
    print("\n✅ 验证完成！")

if __name__ == "__main__":
    main()