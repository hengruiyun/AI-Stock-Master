#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新翻译管理器
将自动生成的翻译整合到unified_i18n_manager.py中
并检查和修正翻译中的语言错误
"""

import json
import re
import os
from pathlib import Path

project_root = Path(__file__).parent.parent

def load_auto_filled_translations():
    """加载自动生成的翻译"""
    auto_fill_file = project_root / "tools" / "auto_filled_translations.json"
    if auto_fill_file.exists():
        with open(auto_fill_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def is_chinese(text):
    """检查文本是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def is_english(text):
    """检查文本是否为纯英文"""
    return bool(re.match(r'^[a-zA-Z0-9\s\-_.,!?()\[\]{}:;"\'\/\\]+$', text))

def validate_and_fix_translations(translations):
    """验证和修正翻译中的语言错误"""
    fixed_translations = {}
    errors_found = []
    
    for key, value in translations.items():
        if isinstance(value, dict) and 'zh' in value and 'en' in value:
            zh_text = value['zh']
            en_text = value['en']
            
            # 检查中文翻译是否包含中文
            if not is_chinese(zh_text) and is_english(zh_text):
                # 中文区域有纯英文，需要修正
                if is_chinese(en_text):
                    # 如果英文区域有中文，交换它们
                    fixed_translations[key] = {'zh': en_text, 'en': zh_text}
                    errors_found.append(f"交换语言: {key} - 中文区域有英文，英文区域有中文")
                else:
                    # 尝试生成中文翻译
                    zh_translation = generate_chinese_translation(key, zh_text)
                    fixed_translations[key] = {'zh': zh_translation, 'en': en_text}
                    errors_found.append(f"生成中文翻译: {key} - 原中文区域为纯英文")
            elif not is_english(en_text) and is_chinese(en_text):
                # 英文区域有中文，需要修正
                if is_chinese(zh_text):
                    # 如果中文区域正常，生成英文翻译
                    en_translation = generate_english_translation(key, en_text)
                    fixed_translations[key] = {'zh': zh_text, 'en': en_translation}
                    errors_found.append(f"生成英文翻译: {key} - 原英文区域为中文")
                else:
                    # 交换它们
                    fixed_translations[key] = {'zh': en_text, 'en': zh_text}
                    errors_found.append(f"交换语言: {key} - 英文区域有中文，中文区域有英文")
            else:
                # 翻译正常
                fixed_translations[key] = value
        else:
            # 保持原样
            fixed_translations[key] = value
    
    return fixed_translations, errors_found

def generate_chinese_translation(key, english_text):
    """根据键名和英文文本生成中文翻译"""
    # 简单的翻译映射
    translation_map = {
        'error': '错误', 'warning': '警告', 'info': '信息', 'success': '成功',
        'loading': '加载中', 'saving': '保存中', 'processing': '处理中',
        'complete': '完成', 'failed': '失败', 'cancel': '取消',
        'ok': '确定', 'yes': '是', 'no': '否', 'close': '关闭',
        'open': '打开', 'save': '保存', 'delete': '删除', 'edit': '编辑',
        'view': '查看', 'copy': '复制', 'move': '移动', 'rename': '重命名',
        'file': '文件', 'folder': '文件夹', 'data': '数据', 'analysis': '分析',
        'report': '报告', 'chart': '图表', 'market': '市场', 'stock': '股票',
        'price': '价格', 'volume': '成交量', 'trend': '趋势', 'risk': '风险',
        'high': '高', 'low': '低', 'medium': '中等', 'good': '良好',
        'active': '活跃', 'ranking': '排名', 'date': '日期', 'time': '时间',
        'search': '搜索', 'label': '标签', 'button': '按钮', 'export': '导出',
        'import': '导入', 'update': '更新', 'refresh': '刷新', 'config': '配置',
        'settings': '设置', 'help': '帮助', 'about': '关于', 'version': '版本',
        'welcome': '欢迎', 'industry': '行业', 'count': '计数', 'query': '查询',
        'professional': '专业', 'algorithm': '算法', 'ai': '人工智能',
        'intelligent': '智能', 'demo': '演示', 'desc': '描述', 'title': '标题',
        'performance': '性能', 'strength': '强度', 'relative': '相对',
        'bear': '熊市', 'bull': '牛市', 'micro': '微', 'big': '大',
        'trading': '交易', 'days': '天', 'quality': '质量', 'top': '顶部',
        'progress': '进度', 'cancelled': '已取消', 'available': '可用',
        'module': '模块', 'core': '核心', 'decline': '下跌', 'sharp': '急剧',
        'strong': '强', 'up': '上涨', 'waiting': '等待', 'step': '步骤',
        'optimistic': '乐观', 'cautiously': '谨慎地', 'enable': '启用',
        'cache': '缓存', 'panic': '恐慌', 'selling': '抛售'
    }
    
    # 将键名转换为小写并分割
    key_parts = re.split(r'[_\-\s]+', key.lower())
    
    # 尝试翻译每个部分
    translated_parts = []
    for part in key_parts:
        if part in translation_map:
            translated_parts.append(translation_map[part])
        else:
            # 如果找不到翻译，保持原样
            translated_parts.append(part)
    
    # 组合翻译
    if len(translated_parts) <= 3:
        return ''.join(translated_parts)
    else:
        return ''.join(translated_parts[:3]) + '等'

def generate_english_translation(key, chinese_text):
    """根据键名和中文文本生成英文翻译"""
    # 简单的反向翻译映射
    reverse_translation_map = {
        '错误': 'Error', '警告': 'Warning', '信息': 'Info', '成功': 'Success',
        '加载中': 'Loading', '保存中': 'Saving', '处理中': 'Processing',
        '完成': 'Complete', '失败': 'Failed', '取消': 'Cancel',
        '确定': 'OK', '是': 'Yes', '否': 'No', '关闭': 'Close',
        '打开': 'Open', '保存': 'Save', '删除': 'Delete', '编辑': 'Edit',
        '查看': 'View', '复制': 'Copy', '移动': 'Move', '重命名': 'Rename',
        '文件': 'File', '文件夹': 'Folder', '数据': 'Data', '分析': 'Analysis',
        '报告': 'Report', '图表': 'Chart', '市场': 'Market', '股票': 'Stock',
        '价格': 'Price', '成交量': 'Volume', '趋势': 'Trend', '风险': 'Risk',
        '高': 'High', '低': 'Low', '中等': 'Medium', '良好': 'Good',
        '活跃': 'Active', '排名': 'Ranking', '日期': 'Date', '时间': 'Time',
        '搜索': 'Search', '标签': 'Label', '按钮': 'Button', '导出': 'Export',
        '导入': 'Import', '更新': 'Update', '刷新': 'Refresh', '配置': 'Config',
        '设置': 'Settings', '帮助': 'Help', '关于': 'About', '版本': 'Version',
        '欢迎': 'Welcome', '行业': 'Industry', '计数': 'Count', '查询': 'Query',
        '专业': 'Professional', '算法': 'Algorithm', '人工智能': 'AI',
        '智能': 'Intelligent', '演示': 'Demo', '描述': 'Description', '标题': 'Title'
    }
    
    # 尝试直接翻译
    if chinese_text in reverse_translation_map:
        return reverse_translation_map[chinese_text]
    
    # 如果找不到直接翻译，使用键名生成英文
    key_parts = re.split(r'[_\-\s]+', key.lower())
    english_parts = [part.title() for part in key_parts]
    return ' '.join(english_parts)

def convert_to_new_format(translations):
    """将翻译转换为新的格式，按键名组织"""
    new_format = {}
    
    for key, value in translations.items():
        if isinstance(value, dict) and 'zh' in value and 'en' in value:
            new_format[key] = value
        else:
            # 如果不是标准格式，尝试转换
            new_format[key] = {'zh': str(value), 'en': str(value)}
    
    return new_format

def update_unified_i18n_manager(translations):
    """更新unified_i18n_manager.py文件"""
    manager_file = project_root / "tools" / "unified_i18n_manager.py"
    
    # 读取现有文件
    with open(manager_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 生成新的翻译字典代码
    translations_code = generate_translations_code(translations)
    
    # 替换_init_base_translations方法
    pattern = r'(def _init_base_translations\(self\):[\s\S]*?)(?=\n    def |\n\nclass |\Z)'
    replacement = f"""def _init_base_translations(self):
        \"\"\"初始化基础翻译数据\"\"\"
        # 自动生成的翻译数据
{translations_code}
"""
    
    new_content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(manager_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"已更新 {manager_file}")

def generate_translations_code(translations):
    """生成翻译字典的Python代码"""
    code_lines = []
    code_lines.append("        self.translations = {")
    
    # 生成中文翻译
    zh_translations = {}
    en_translations = {}
    
    for key, value in translations.items():
        if isinstance(value, dict) and 'zh' in value and 'en' in value:
            zh_translations[key] = value['zh']
            en_translations[key] = value['en']
    
    # 中文翻译
    code_lines.append('            "zh": {')
    for key, zh_text in sorted(zh_translations.items()):
        escaped_key = key.replace('"', '\\"')
        escaped_zh = zh_text.replace('"', '\\"')
        code_lines.append(f'                "{escaped_key}": "{escaped_zh}",')
    code_lines.append('            },')  
    
    # 英文翻译
    code_lines.append('            "en": {')
    for key, en_text in sorted(en_translations.items()):
        escaped_key = key.replace('"', '\\"')
        escaped_en = en_text.replace('"', '\\"')
        code_lines.append(f'                "{escaped_key}": "{escaped_en}",')
    code_lines.append('            }')
    
    code_lines.append('        }')
    
    return '\n'.join(code_lines)

def main():
    """主函数"""
    print("...")
    
    # 加载自动生成的翻译
    auto_translations = load_auto_filled_translations()
    print(f"加载了 {len(auto_translations)} 个自动生成的翻译")
    
    # 转换为新格式
    formatted_translations = convert_to_new_format(auto_translations)
    
    # 验证和修正翻译
    fixed_translations, errors = validate_and_fix_translations(formatted_translations)
    
    if errors:
        print(f"\n发现并修正了 {len(errors)} 个翻译错误:")
        for error in errors:
            print(f"  - {error}")
    
    # 更新unified_i18n_manager.py
    update_unified_i18n_manager(fixed_translations)
    
    # 生成报告
    report_file = project_root / "tools" / "translation_update_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"翻译更新报告\n")
        f.write(f"生成时间: {__import__('datetime').datetime.now()}\n\n")
        f.write(f"总翻译条目: {len(fixed_translations)}\n")
        f.write(f"修正错误数: {len(errors)}\n\n")
        
        if errors:
            f.write("修正的错误详情:\n")
            for error in errors:
                f.write(f"  - {error}\n")
    
    print(f"\n更新完成!")
    print(f"- 总翻译条目: {len(fixed_translations)}")
    print(f"- 修正错误数: {len(errors)}")
    print(f"- 报告文件: {report_file}")

if __name__ == "__main__":
    main()