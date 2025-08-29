#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商务风格样式配置

作者：267278466@qq.com
版本：v1.0
创建时间：2025-01-19
"""

# 商务风格配色方案
BUSINESS_COLORS = {
    # 主色调 - 蓝紫渐变
    'primary_gradient': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:0.5 #764ba2, stop:1 #667eea)',
    'primary_blue': '#667eea',
    'primary_purple': '#764ba2',
    
    # 背景色
    'bg_main': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f8f9fa, stop:0.3 #e9ecef, stop:0.7 #dee2e6, stop:1 #ced4da)',
    'bg_card': 'rgba(255, 255, 255, 0.8)',
    'bg_loading': 'rgba(255, 255, 255, 0.6)',
    
    # 文字色
    'text_primary': '#2c3e50',
    'text_secondary': '#34495e',
    'text_light': '#7f8c8d',
    'text_white': 'white',
    
    # 市场专用渐变色
    'cn_market': 'stop:0 #e74c3c, stop:1 #c0392b',  # A股 - 红色渐变
    'hk_market': 'stop:0 #9b59b6, stop:1 #8e44ad',  # 港股 - 紫色渐变
    'us_market': 'stop:0 #4facfe, stop:1 #00f2fe',  # 美股 - 蓝青渐变
    
    # 状态色
    'success': '#27ae60',
    'warning': '#f39c12',
    'error': '#e74c3c',
    'info': '#3498db',
}

# 字体配置
BUSINESS_FONTS = {
    'family': "'Microsoft YaHei', 'Segoe UI', Arial, sans-serif",
    'title_size': 32,
    'subtitle_size': 18,
    'header_size': 20,
    'body_size': 14,
    'small_size': 11,
    'caption_size': 10,
}

# 首页样式
HOMEPAGE_STYLES = {
    'container': f"""
        QWidget {{
            background: {BUSINESS_COLORS['bg_main']};
            font-family: {BUSINESS_FONTS['family']};
        }}
    """,
    
    'top_bar': f"""
        background: {BUSINESS_COLORS['primary_gradient']};
        border-radius: 3px;
    """,
    
    'title_container': f"""
        QWidget {{
            background: {BUSINESS_COLORS['bg_card']};
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
    """,
    
    'main_title': f"""
        color: {BUSINESS_COLORS['text_primary']};
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0px;
        letter-spacing: 2px;
    """,
    
    'subtitle': f"""
        color: {BUSINESS_COLORS['text_secondary']};
        margin-bottom: 15px;
        letter-spacing: 1px;
    """,
    
    'slogan_left': f"""
        color: {BUSINESS_COLORS['primary_blue']};
        background: rgba(102, 126, 234, 0.1);
        padding: 12px 20px;
        border-radius: 25px;
        border: 2px solid rgba(102, 126, 234, 0.2);
    """,
    
    'slogan_right': f"""
        color: {BUSINESS_COLORS['primary_purple']};
        background: rgba(118, 75, 162, 0.1);
        padding: 12px 20px;
        border-radius: 25px;
        border: 2px solid rgba(118, 75, 162, 0.2);
    """,
}

# 市场卡片样式
def get_market_card_style(market_type):
    """获取市场卡片样式"""
    gradient_colors = BUSINESS_COLORS.get(f'{market_type}_market', BUSINESS_COLORS['cn_market'])
    
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {gradient_colors});
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {gradient_colors});
            border: 2px solid rgba(255, 255, 255, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {gradient_colors});
            border: 2px solid rgba(255, 255, 255, 0.6);
            transform: translateY(0px);
        }}
    """

# 加载进度样式
LOADING_STYLES = {
    'container': f"""
        QWidget {{
            background: {BUSINESS_COLORS['bg_loading']};
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
    """,
    
    'label': f"""
        color: {BUSINESS_COLORS['text_primary']};
        background: rgba(255, 255, 255, 0.9);
        padding: 15px 25px;
        border-radius: 25px;
        border: 2px solid rgba(102, 126, 234, 0.2);
    """,
    
    'progress_bar': f"""
        QProgressBar {{
            border: none;
            border-radius: 6px;
            text-align: center;
            background: rgba(255, 255, 255, 0.3);
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: {BUSINESS_COLORS['primary_gradient']};
            border-radius: 6px;
            margin: 0px;
        }}
    """,
    
    'hint': f"""
        color: {BUSINESS_COLORS['text_light']};
        background: transparent;
        padding: 5px;
    """,
}

# 主窗口样式
MAIN_WINDOW_STYLES = f"""
    QMainWindow {{
        background: {BUSINESS_COLORS['bg_main']};
        color: {BUSINESS_COLORS['text_primary']};
        font-family: {BUSINESS_FONTS['family']};
    }}
    
    QWidget {{
        font-family: {BUSINESS_FONTS['family']};
    }}
    
    /* 工具栏和菜单栏样式 */
    QMenuBar {{
        background: rgba(255, 255, 255, 0.9);
        border-bottom: 2px solid {BUSINESS_COLORS['primary_blue']};
        padding: 5px;
        color: {BUSINESS_COLORS['text_primary']};
        font-weight: bold;
    }}
    
    QMenuBar::item {{
        background: transparent;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 2px;
    }}
    
    QMenuBar::item:selected {{
        background: rgba(102, 126, 234, 0.1);
        color: {BUSINESS_COLORS['primary_blue']};
    }}
    
    QStatusBar {{
        background: rgba(255, 255, 255, 0.8);
        border-top: 1px solid rgba(102, 126, 234, 0.3);
        color: {BUSINESS_COLORS['text_primary']};
        font-size: 12px;
    }}
    
    /* 滚动条样式 */
    QScrollBar:vertical {{
        background: rgba(255, 255, 255, 0.3);
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background: {BUSINESS_COLORS['primary_gradient']};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #5a6fd8, stop:1 #6a4190);
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}
"""

# 市场图标配置
MARKET_ICONS = {
    'cn': '中国',
    'hk': '中国', 
    'us': '美国',
}

# 动态加载消息
LOADING_MESSAGES = {
    'initial': [
        "正在启动智能分析引擎...",
        "正在加载市场数据...",
        "正在执行AI增强分析...",
        "正在优化计算结果...",
        "正在生成分析报告..."
    ],
    'market_specific': {
        'cn': "正在分析A股市场数据...",
        'hk': "正在分析港股市场数据...",
        'us': "正在分析美股市场数据...",
    },
    'progress_hints': {
        'early': "系统正在智能分析海量数据，预计还需要几秒钟...",
        'middle': "分析即将完成，正在优化结果展示...",
        'late': "分析完成，准备为您呈现专业投资建议...",
    }
}

def get_progress_icon(progress_value):
    """根据进度值获取对应文字（不使用emoji）"""
    if progress_value <= 25:
        return "启动"
    elif progress_value <= 50:
        return "加载"
    elif progress_value <= 75:
        return "分析"
    else:
        return "完成"

def get_market_gradient(market_type):
    """获取市场对应的渐变色"""
    return BUSINESS_COLORS.get(f'{market_type}_market', BUSINESS_COLORS['cn_market'])

def apply_business_theme():
    """应用商务主题的便捷函数"""
    return {
        'colors': BUSINESS_COLORS,
        'fonts': BUSINESS_FONTS,
        'homepage': HOMEPAGE_STYLES,
        'loading': LOADING_STYLES,
        'main_window': MAIN_WINDOW_STYLES,
        'icons': MARKET_ICONS,
        'messages': LOADING_MESSAGES,
    }
