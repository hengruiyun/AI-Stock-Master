#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
语言管理器 - 支持中英文自动切换
"""

import locale
import os
import sys
from typing import Dict, Any

class LanguageManager:
    """语言管理器"""
    
    def __init__(self):
        """初始化语言管理器"""
        self.current_language = self._detect_system_language()
        self.translations = self._load_translations()
    
    def _detect_system_language(self) -> str:
        """检测系统语言"""
        try:
            # 获取系统语言
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                if system_locale.startswith('zh'):
                    return 'zh'
                elif system_locale.startswith('en'):
                    return 'en'
            
            # 备用检测方法
            if os.environ.get('LANG', '').startswith('zh'):
                return 'zh'
            elif os.environ.get('LANG', '').startswith('en'):
                return 'en'
            
            # 默认使用中文
            return 'zh'
            
        except Exception:
            return 'zh'  # 默认中文
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """加载翻译文本"""
        return {
            'zh': {
                # 主窗口
                'app_title': 'AI股票趋势分析系统',
                'app_version': 'v1.0',
                'app_title': 'AI股票趋势分析系统',
                'welcome_title': '欢迎使用',
                'welcome_core_features': '核心功能特点',
                'welcome_getting_started': '开始使用',
                'welcome_dynamic_analysis': '动态数据分析',
                'welcome_system_config': '系统配置',
                'welcome_note': '注意',
                'welcome_step1': '点击右上角\'加载\'按钮选择数据文件',
                'welcome_step2': '支持格式: *.json.gz',
                'welcome_step3': '建议文件: CN_Data.json.gz',
                'welcome_stock_count': '股票总数 - 动态读取自数据文件',
                'welcome_industry_count': '行业数量 - 动态统计分类信息',
                'welcome_industry_query': '所属行业 - 实时查询不保存',
                'welcome_tech_stack': '技术栈',
                'welcome_classic_ui': '经典界面风格',
                'welcome_professional_algo': '专业级数据分析算法',
                'welcome_note_desc': '系统不会自动加载文件，所有数据均从用户选择的文件中动态读取',
                'welcome_message': '请点击"打开文件"按钮选择.json.gz数据文件开始分析。\n\n支持格式：*.json.gz\n包含股票代码、名称、行业、历史评级数据',
                
                # 菜单栏
                'menu_file': '文件',
                'menu_open_file': '打开数据文件',
                'menu_export_report': '导出分析报告',
                'menu_export_html': '导出HTML报告',
                'menu_exit': '退出',
                'menu_analysis': '分析',
                'menu_start_analysis': '开始分析',
                'menu_stock_analysis': '个股趋势分析',
                'menu_industry_analysis': '行业对比分析',
                'menu_market_analysis': '市场情绪分析',
                'menu_tools': '工具',
                'menu_data_validation': '数据验证',
                'menu_performance_monitor': '性能监控',
                'menu_settings': '系统设置',
                'menu_help': '帮助',
                'menu_user_guide': '使用说明',
                'menu_about': '关于',
                'help_title': '帮助',
                'help_developing': '使用说明功能开发中...',
                
                # 按钮
                'btn_load': '加载',
                'btn_analyze': '分析',
                'btn_report': '报告',
                'btn_ai_model': 'AI模型',
                'btn_open_file': '打开文件',
                'btn_start_analysis': '开始分析',
                'btn_export_report': '导出报告',
                'btn_stock_analysis': '个股分析',
                'btn_industry_analysis': '行业分析',
                'btn_market_analysis': '市场分析',
                'btn_refresh': '刷新',
                'btn_export': '导出',
                'btn_add_watchlist': '关注',
                'btn_close': '关闭',
                
                # 状态栏
                'status_ready': '就绪',
                'status_select_file': '请选择数据文件开始分析',
                'status_loading': '加载中...',
                'status_analyzing': '分析中...',
                'status_completed': '分析完成',
                'status_error': '错误',
                
                # 个股分析
                'stock_analysis_title': '个股分析',
                'stock_list': '股票列表',
                'search_placeholder': '搜索股票代码或名称...',
                'core_metrics': '核心指标',
                'trend_chart': '趋势图表',
                'detailed_analysis': '详细分析',
                'rtsi_index': 'RTSI指数',
                'trend_status': '趋势状态',
                'confidence': '置信度',
                'risk_level': '风险等级',
                
                # 行业分析
                'industry_analysis_title': '行业轮动强度分析',
                'industry_list': '行业列表',
                'irsi_index': 'IRSI指数',
                'strength_level': '强度等级',
                'investment_value': '投资价值',
                'risk_warning': '风险提示',
                
                # 市场分析
                'market_sentiment_title': '市场情绪分析',
                'msci_index': 'MSCI指数',
                'market_sentiment': '市场情绪',
                'bull_bear_ratio': '多空比例',
                'investment_advice': '投资建议',
                
                # 文件类型和对话框
                'filetype_data': '数据文件',
                'filetype_excel': 'Excel文件',
                'filetype_csv': 'CSV文件',
                'filetype_all': '所有文件',
                'dialog_select_file': '选择股票数据文件',
                
                # 算法描述
                'rtsi_desc': '个股评级趋势强度指数',
                'irsi_desc': '行业相对强度指数',
                'msci_desc': '市场情绪综合指数',
                'rtsi_description': '个股评级趋势强度指数',
                'irsi_description': '行业相对强度指数',
                'msci_description': '市场情绪综合指数',
                
                # 趋势描述
                'trend_strong_up': '强势上涨',
                'trend_moderate_up': '温和上涨',
                'trend_weak_up': '弱势上涨',
                'trend_sideways': '震荡整理',
                'trend_weak_down': '弱势下跌',
                'trend_moderate_down': '温和下跌',
                'trend_strong_down': '强势下跌',
                
                # 风险等级
                'risk_low': '低风险',
                'risk_medium': '中风险',
                'risk_high': '高风险',
                
                # 提示信息
                'msg_select_file': '请选择Excel文件',
                'msg_analysis_success': '分析完成',
                'msg_analysis_failed': '分析失败',
                'msg_export_success': '导出成功',
                'msg_export_failed': '导出失败',
                'msg_no_data': '暂无数据',
                'msg_loading_data': '数据加载中...',
                'msg_select_stock': '请先选择股票',
                
                # 图表相关
                'chart_rating_trend': '评级趋势分析',
                'chart_real_data': '真实数据',
                'chart_generated_data': '基于RTSI={:.1f}生成',
                'chart_data_preparing': '数据准备中...',
                'chart_time': '时间',
                'chart_rating_score': '评级分数',
                
                # 评级等级
                'rating_big_bull': '大多',
                'rating_mid_bull': '中多',
                'rating_small_bull': '小多',
                'rating_micro_bull': '微多',
                'rating_micro_bear': '微空',
                'rating_small_bear': '小空',
                'rating_mid_bear': '中空',
                'rating_big_bear': '大空',
                
                # 详细分析报告
                'analysis_report_title': '深度分析报告',
                'analysis_core_metrics': '【核心指标】',
                'analysis_technical': '【技术分析】',
                'analysis_industry': '【行业对比】',
                'analysis_investment': '【投资建议】',
                'analysis_risk': '【风险评估】',
                'analysis_operation': '【操作建议】',
                'analysis_outlook': '【后市展望】',
                'analysis_disclaimer': '【免责声明】',
                
                # 文件操作
                'file_formats': [("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
                'report_formats': [("HTML文件", "*.html"), ("Excel文件", "*.xlsx"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
                
                # 系统信息
                'features': [
                    'RTSI - 个股评级趋势强度指数',
                    'IRSI - 行业相对强度指数', 
                    'MSCI - 市场情绪综合指数',
                    'Windows经典风格界面',
                    '实时数据分析引擎',
                    '高级可视化报告'
                ],
                'supported_data': [
                    'Json 格式: *.json.gz',
                    '股票数量: 5,000+ 只',
                    '行业分类: 85 个',
                    '评级系统: 8级 (大多→大空)'
                ],
                'shortcuts': [
                    'Ctrl+O: 打开文件',
                    'F5: 开始分析',
                    'Ctrl+S: 导出报告'
                ],
                'chart_system_generating': '系统正在基于RTSI指数生成30天趋势数据\n预计需要1-2秒完成\n\n请稍候或刷新重试'
            },
            
            'en': {
                # Main Window
                'app_title': 'AI Stock Trend Analysis System',
                'app_version': 'v1.0',
                'welcome_title': 'Welcome',
                'welcome_core_features': 'Core Features',
                'welcome_getting_started': 'Getting Started',
                'welcome_dynamic_analysis': 'Dynamic Data Analysis',
                'welcome_system_config': 'System Configuration',
                'welcome_note': 'Note',
                'welcome_step1': 'Click "Load" button in the top right to select data file',
                'welcome_step2': 'Supported formats: *.json.gz',
                'welcome_step3': 'Recommended file: US_Data.json.gz',
                'welcome_stock_count': 'Stock Count - Dynamically read from data file',
                'welcome_industry_count': 'Industry Count - Dynamically categorized',
                'welcome_industry_query': 'Industry Info - Real-time query, not saved',
                'welcome_tech_stack': 'Technology Stack',
                'welcome_classic_ui': 'Classic UI Style',
                'welcome_professional_algo': 'Professional Data Analysis Algorithms',
                'welcome_note_desc': 'System does not auto-load files, all data is dynamically read from user-selected files',
                'welcome_message': 'Click "Open File" to select .json.gz file to start analysis.\n\nSupported formats: *.json.gz\nContains: stock code, name, industry, historical rating data',
                
                # Menu Bar
                'menu_file': 'File',
                'menu_open_file': 'Open Data File',
                'menu_export_report': 'Export Analysis Report',
                'menu_export_html': 'Export HTML Report',
                'menu_exit': 'Exit',
                'menu_analysis': 'Analysis',
                'menu_start_analysis': 'Start Analysis',
                'menu_stock_analysis': 'Stock Trend Analysis',
                'menu_industry_analysis': 'Industry Comparison Analysis',
                'menu_market_analysis': 'Market Sentiment Analysis',
                'menu_tools': 'Tools',
                'menu_data_validation': 'Data Validation',
                'menu_performance_monitor': 'Performance Monitor',
                'menu_settings': 'System Settings',
                'menu_help': 'Help',
                'menu_user_guide': 'User Guide',
                'menu_about': 'About',
                'help_title': 'Help',
                'help_developing': 'User guide feature is under development...',
                
                # Buttons
                'btn_load': 'Load',
                'btn_analyze': 'Analyze',
                'btn_report': 'Report',
                'btn_ai_model': 'AI Model',
                'btn_open_file': 'Open File',
                'btn_start_analysis': 'Start Analysis',
                'btn_export_report': 'Export Report',
                'btn_stock_analysis': 'Stock Analysis',
                'btn_industry_analysis': 'Industry Analysis',
                'btn_market_analysis': 'Market Analysis',
                'btn_refresh': 'Refresh',
                'btn_export': 'Export',
                'btn_add_watchlist': 'Watch',
                'btn_close': 'Close',
                
                # Status Bar
                'status_ready': 'Ready',
                'status_select_file': 'Please select a data file to start analysis',
                'status_loading': 'Loading...',
                'status_analyzing': 'Analyzing...',
                'status_completed': 'Analysis Completed',
                'status_error': 'Error',
                
                # File Types and Dialogs
                'filetype_data': 'Data Files',
                'filetype_excel': 'Excel Files',
                'filetype_csv': 'CSV Files',
                'filetype_all': 'All Files',
                'dialog_select_file': 'Select Stock Data File',
                
                # Algorithm Descriptions
                'rtsi_desc': 'Rating Trend Strength Index',
                'irsi_desc': 'Industry Relative Strength Index',
                'msci_desc': 'Market Sentiment Composite Index',
                
                # Stock Analysis
                'stock_analysis_title': 'Stock Analysis',
                'stock_list': 'Stock List',
                'search_placeholder': 'Search stock code or name...',
                'core_metrics': 'Core Metrics',
                'trend_chart': 'Trend Chart',
                'detailed_analysis': 'Detailed Analysis',
                'rtsi_index': 'RTSI Index',
                'trend_status': 'Trend Status',
                'confidence': 'Confidence',
                'risk_level': 'Risk Level',
                
                # Industry Analysis
                'industry_analysis_title': 'Industry Rotation Analysis',
                'industry_list': 'Industry List',
                'irsi_index': 'IRSI Index',
                'strength_level': 'Strength Level',
                'investment_value': 'Investment Value',
                'risk_warning': 'Risk Warning',
                
                # Market Analysis
                'market_sentiment_title': 'Market Sentiment Analysis',
                'msci_index': 'MSCI Index',
                'market_sentiment': 'Market Sentiment',
                'bull_bear_ratio': 'Bull/Bear Ratio',
                'investment_advice': 'Investment Advice',
                
                # Algorithm Descriptions
                'rtsi_description': 'Rating Trend Strength Index',
                'irsi_description': 'Industry Relative Strength Index',
                'msci_description': 'Market Sentiment Composite Index',
                
                # Trend Descriptions
                'trend_strong_up': 'Strong Uptrend',
                'trend_moderate_up': 'Moderate Uptrend',
                'trend_weak_up': 'Weak Uptrend',
                'trend_sideways': 'Sideways',
                'trend_weak_down': 'Weak Downtrend',
                'trend_moderate_down': 'Moderate Downtrend',
                'trend_strong_down': 'Strong Downtrend',
                
                # Risk Levels
                'risk_low': 'Low Risk',
                'risk_medium': 'Medium Risk',
                'risk_high': 'High Risk',
                
                # Messages
                'msg_select_file': 'Please select Excel file',
                'msg_analysis_success': 'Analysis completed',
                'msg_analysis_failed': 'Analysis failed',
                'msg_export_success': 'Export successful',
                'msg_export_failed': 'Export failed',
                'msg_no_data': 'No data available',
                'msg_loading_data': 'Loading data...',
                'msg_select_stock': 'Please select a stock first',
                
                # Chart Related
                'chart_rating_trend': 'Rating Trend Analysis',
                'chart_real_data': 'Real Data',
                'chart_generated_data': 'Generated based on RTSI={:.1f}',
                'chart_data_preparing': 'Data preparing...',
                'chart_time': 'Time',
                'chart_rating_score': 'Rating Score',
                
                # Rating Levels
                'rating_big_bull': 'Strong Buy',
                'rating_mid_bull': 'Buy',
                'rating_small_bull': 'Weak Buy',
                'rating_micro_bull': 'Hold+',
                'rating_micro_bear': 'Hold-',
                'rating_small_bear': 'Weak Sell',
                'rating_mid_bear': 'Sell',
                'rating_big_bear': 'Strong Sell',
                
                # Detailed Analysis Report
                'analysis_report_title': 'In-depth Analysis Report',
                'analysis_core_metrics': '[Core Metrics]',
                'analysis_technical': '[Technical Analysis]',
                'analysis_industry': '[Industry Comparison]',
                'analysis_investment': '[Investment Advice]',
                'analysis_risk': '[Risk Assessment]',
                'analysis_operation': '[Operation Suggestions]',
                'analysis_outlook': '[Market Outlook]',
                'analysis_disclaimer': '[Disclaimer]',
                
                # File Operations
                'file_formats': [("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                'report_formats': [("HTML Files", "*.html"), ("Excel Files", "*.xlsx"), ("Text Files", "*.txt"), ("All Files", "*.*")],
                
                # System Information
                'features': [
                    'RTSI - Rating Trend Strength Index',
                    'IRSI - Industry Relative Strength Index', 
                    'MSCI - Market Sentiment Composite Index',
                    'Windows Classic Style Interface',
                    'Real-time Data Analysis Engine',
                    'Advanced Visualization Reports'
                ],
                'supported_data': [
                    'Json formats: *.json.gz',
                    'Stock count: 5,000+ stocks',
                    'Industry classification: 85 sectors',
                    'Rating system: 8 levels (Strong Buy→Strong Sell)'
                ],
                'shortcuts': [
                    'Ctrl+O: Open File',
                    'F5: Start Analysis',
                    'Ctrl+S: Export Report'
                ],
                'chart_system_generating': 'System is generating 30-day trend data based on RTSI index\nEstimated completion time: 1-2 seconds\n\nPlease wait or refresh'
            }
        }
    
    def get_text(self, key: str, default: str = None) -> str:
        """获取翻译文本"""
        return self.translations[self.current_language].get(key, default or key)
    
    def get_language(self) -> str:
        """获取当前语言"""
        return self.current_language
    
    def set_language(self, language: str):
        """设置语言"""
        if language in self.translations:
            self.current_language = language

# 全局语言管理器实例
language_manager = LanguageManager()

# 便捷函数
def _(key: str, default: str = None) -> str:
    """获取翻译文本的便捷函数"""
    return language_manager.get_text(key, default)

def get_current_language() -> str:
    """获取当前语言"""
    return language_manager.get_language()

def set_language(language: str):
    """设置语言"""
    language_manager.set_language(language)