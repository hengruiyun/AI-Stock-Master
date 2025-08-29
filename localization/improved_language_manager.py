# -*- coding: utf-8 -*-
"""
改进的语言管理器 - 完整的双语支持
支持中英文自动切换，覆盖所有硬编码文字
"""

import locale
import os
import sys
from typing import Dict, Any

class ImprovedLanguageManager:
    """改进的语言管理器"""
    
    def __init__(self):
        """初始化语言管理器"""
        self.current_language = self._detect_system_language()
        self.translations = self._load_complete_translations()
    
    def _detect_system_language(self) -> str:
        """检测系统语言"""
        try:
            # 检查强制语言环境变量
            force_lang = os.environ.get('FORCE_LANG', '').lower()
            if force_lang == 'en' or force_lang == 'english':
                print("FORCE_LANG")
                return 'en'
            elif force_lang == 'zh' or force_lang == 'chinese':
                print("FORCE_LANG")
                return 'zh'
            
            # 检查环境变量LANG（优先级高于系统检测）
            lang_env = os.environ.get('LANG', '')
            print(f"环境变量LANG: {lang_env}")
            if lang_env:
                if 'en' in lang_env.lower():
                    print("")
                    return 'en'
                elif 'zh' in lang_env.lower():
                    print("")
                    return 'zh'
            
            # 获取系统默认语言
            system_locale = locale.getdefaultlocale()[0]
            print(f"系统语言检测 - system_locale: {system_locale}")
            
            # Windows系统特殊处理
            windows_lang_id = None
            if os.name == 'nt':
                try:
                    import ctypes
                    windll = ctypes.windll.kernel32
                    windows_lang_id = windll.GetUserDefaultUILanguage()
                    print(f"Windows语言ID: {windows_lang_id}")
                except Exception as e:
                    print(f"Windows语言检测异常: {e}")
            
            # 检查Windows语言ID
            if windows_lang_id:
                # 中文语言ID范围
                if windows_lang_id in [2052, 1028, 3076, 5124]:  # 简体中文、繁体中文等
                    print("Windows API")
                    return 'zh'
                else:
                    print(f"Windows API检测到非中文语言ID {windows_lang_id}，使用英文")
                    return 'en'
            
            # 如果Windows API不可用，检查locale
            if system_locale and 'zh' in system_locale.lower():
                print("locale")
                return 'zh'
            
            print("")
            return 'en'
            
        except Exception as e:
            print(f"语言检测异常: {e}，默认使用英文")
            return 'en'
    
    def _load_complete_translations(self) -> Dict[str, Dict[str, str]]:
        """加载完整的翻译文本"""
        return {
            'zh': {
                # 主窗口和应用程序
                'app_title': 'AI股票大师',
                'app_version': 'v2.2',
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
                'menu_update_data_files': '更新数据文件',
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
                'btn_stock': '个股',
                'btn_industry': '行业',
                'btn_market': '市场',
                'btn_open_file': '打开文件',
                'btn_start_analysis': '开始分析',
                'btn_export_report': '导出报告',
                'btn_refresh': '刷新',
                'btn_export': '导出',
                'btn_add_watchlist': '关注',
                'btn_close': '关闭',
                'btn_cancel': '取消',
                'btn_complete': '完成',
                'btn_export_analysis': '导出分析',
                'btn_add_watch': '添加关注',
                'btn_refresh_data': '刷新数据',
                
                # 个股分析窗口
                'stock_selector_label': '股票选择:',
                'search_label': '搜索:',
                'core_metrics_label': '核心指标',
                
                # 行业分析窗口
                'industry_rotation_title': '行业轮动强度分析',
                'industry_irsi_ranking': '行业IRSI排名',
                'industry_detail_info': '行业详细信息',
                
                # 市场情绪分析窗口
                'market_sentiment_title': '市场情绪综合分析',
                'btn_msci_details': 'MSCI详情',
                'btn_market_alerts': '市场预警',
                
                # 状态信息
                'status_loading_industry': '正在加载行业数据...',
                'status_loading_data': '正在加载数据...',
                'status_generating_report': '生成分析报告...',
                'status_data_validation': '数据验证和预处理...',
                'status_calculating_rtsi': '计算RTSI个股趋势指数...',
                'status_calculating_irsi': '计算IRSI行业强度指数...',
                'status_calculating_msci': '计算MSCI市场情绪指数...',
                'status_analysis_complete': '分析完成!',
                'status_updating_data': '正在更新数据文件...',
                'status_data_update_complete': '数据文件更新完成',
                'status_data_update_failed': '数据文件更新失败',
                
                # 表格列标题
                'column_rank': '排名',
                'column_code': '代码',
                'column_name': '名称',
                'column_industry': '行业',
                'column_status': '状态',
                'column_stock_count': '股票数',
                'column_item': '项目',
                'column_value': '数值',
                'column_trend': '趋势',
                
                # 分析报告相关
                'analysis_report_title': '分析报告',
                'industry_analysis_report': '行业分析报告',
                'market_analysis_report': '市场情绪综合分析报告',
                'stock_analysis_report': '个股分析报告',
                'export_analysis_report': '导出个股分析报告',
                'report_export_success': '分析报告已导出到',
                'report_generation_failed': '分析报告生成失败',
                
                # 图表和分析界面
                'chart_select_stock': '请选择股票进行分析',
                'chart_time': '时间',
                'chart_rating_score': '评级分数',
                'chart_waiting_analysis': '等待分析...',
                'analysis_data_status': '数据状态',
                'analysis_completed': '已完成分析',
                'analysis_waiting': '等待分析',
                'generation_time': '生成时间',
                'core_indicators': '核心指标',
                'technical_analysis': '技术分析',
                'operation_suggestion': '操作建议',
                'risk_warning': '股市有风险，投资需谨慎。请结合基本面分析和风险承受能力。',
                'data_update_info': '数据更新：基于最新评级数据实时计算',
                'analysis_time': '分析时间',
                'historical_comparison': '历史对比',
                'deep_analysis_report': '深度分析报告',
                'trend_status': '趋势状态',
                'technical_strength': '技术强度',
                'industry_category': '所属行业',
                'market_cap_level': '市值等级',
                'trend_direction': '趋势方向',
                'volatility_level': '波动程度',
                'support_resistance': '支撑阻力',
                'relative_strength': '相对强度',
                'industry_comparison': '行业对比',
                'industry_performance': '行业表现',
                'industry_position': '行业地位',
                'rotation_signal': '轮动信号',
                'investment_advice': '投资建议',
                'short_term_strategy': '短线策略',
                'medium_term_strategy': '中线策略',
                'risk_assessment': '风险评估',
                'technical_risk': '技术风险',
                'industry_risk': '行业风险',
                'market_risk': '市场风险',
                'liquidity': '流动性',
                'operation_advice': '操作建议',
                'best_entry_point': '最佳买点',
                'stop_loss_position': '止损位置',
                'target_price': '目标价位',
                'holding_period': '持仓周期',
                'future_outlook': '后市展望',
                'disclaimer': '免责声明',
                'disclaimer_text': '本分析基于RTSI技术算法，仅供参考，不构成投资建议。',
                'data_source': '数据来源',
                'analysis_failed': '分析报告生成失败',
                'error_info': '错误信息',
                'check_data_integrity': '请检查数据完整性或联系技术支持。',
                'strong': '强势',
                'neutral': '中性',
                'weak': '弱势',
                'leading': '领先',
                'lagging': '落后',
                'blue_chip': '龙头股',
                'average': '一般',
                'active': '积极',
                'wait_and_see': '观望',
                'cautious': '谨慎',
                'good': '良好',
                'small_cap': '小盘股',
                'uncategorized': '未分类',
                'based_on_rating_analysis': '基于评级变化分析',
                'pay_attention_to_policy': '关注{industry}政策和周期变化',
                'pay_attention_to_market': '需关注大盘趋势和系统性风险',
                'super_strong_trend': '超强趋势',
                'strong_uptrend': '强势上涨',
                'consolidation': '震荡整理',
                'weak_downtrend': '弱势下跌',
                'deep_adjustment': '深度调整',
                'strong_bull_trend': '强势多头趋势，技术面极度乐观，建议积极配置',
                'moderate_bull_trend': '温和多头趋势，上升动能充足，适合中线持有',
                'weak_bull_pattern': '弱势多头格局，上升空间有限，谨慎乐观',
                'sideways_consolidation': '横盘整理格局，方向选择待定，观望为主',
                'index': '指数',
                'industry': '行业',
                
                # 窗口标题
                'stock_analysis_window_title': '个股趋势分析 - RTSI算法分析',
                'industry_analysis_window_title': '行业轮动分析',
                'market_analysis_window_title': '市场情绪综合分析',
                
                # 状态栏
                'status_ready': '就绪',
                'status_select_file': '请选择数据文件开始分析',
                'status_loading': '加载中...',
                'status_analyzing': '分析中...',
                'status_completed': '分析完成',
                'status_error': '错误',
                
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
                
                # 分析相关
                'analysis_progress_title': '数据分析进行中...',
                'analysis_initializing': '正在初始化分析引擎...',
                'analysis_loading_data': '正在加载数据...',
                'analysis_data_validation': '数据验证和预处理...',
                'analysis_calculating_rtsi': '计算RTSI个股趋势指数...',
                'analysis_calculating_irsi': '计算IRSI行业强度指数...',
                'analysis_calculating_msci': '计算MSCI市场情绪指数...',
                'analysis_generating_report': '生成分析报告...',
                'analysis_completed': '分析完成!',
                'analysis_failed': '分析失败',
                'analysis_cancelled': '分析已取消',
                
                # 分析阶段详细信息
                'stage_detail_loading': '读取Excel文件，解析股票和行业数据',
                'stage_detail_validation': '验证8级评级系统，清理无效数据',
                'stage_detail_rtsi': '使用线性回归分析个股评级趋势',
                'stage_detail_irsi': '计算行业相对市场表现强度',
                'stage_detail_msci': '综合分析市场整体情绪状态',
                'stage_detail_report': '整理分析结果，准备可视化数据',
                'stage_detail_complete': '所有分析任务已完成，准备展示结果',
                
                # 错误和警告消息
                'error_file_load_failed': '文件加载失败!',
                'error_analysis_failed': '数据分析失败!',
                'error_insufficient_data': '数据不足',
                'error_calculation_error': '计算错误',
                'warning_data_quality': '数据质量警告：插值比例过高',
                'warning_serious': '严重警告：超过一半数据需要插值，RTSI结果可靠性较低',
                
                # 数据更新相关
                'feature_unavailable': '功能不可用',
                'data_updater_not_found': '数据更新模块未找到，请检查系统配置',
                'update_failed': '更新失败',
                'data_update_error': '数据文件更新过程中出现错误',
                'data_update_failed': '数据文件更新失败',
                'data_update_success': '数据文件更新成功',
                'data_update_cancelled': '数据更新已取消',
                'data_update_skipped': '数据更新已跳过',
                'downloading_file': '正在下载文件',
                'download_progress': '下载进度',
                'download_complete': '下载完成',
                'download_failed': '下载失败',
                'checking_updates': '正在检查数据更新...',
                'no_updates_needed': '数据文件已是最新版本',
                'updates_available': '发现数据文件更新',
                'update_data_files_title': '更新数据文件',
                'update_data_files_message': '是否要下载最新的数据文件？',
                'btn_update': '更新',
                'btn_skip': '跳过',
                'btn_cancel_update': '取消',
                
                # 趋势描述
                'trend_strong_bull': '强势多头',
                'trend_moderate_bull': '温和多头',
                'trend_weak_bull': '弱势多头',
                'trend_neutral': '横盘整理',
                'trend_weak_bear': '弱势空头',
                'trend_moderate_bear': '温和空头',
                'trend_strong_bear': '强势空头',
                'trend_unknown': '未知趋势',
                'trend_insufficient_data': '数据不足',
                
                # 风险等级
                'risk_extremely_low': '极低风险（强势确认）',
                'risk_low': '低风险（温和上升）',
                'risk_medium': '中等风险',
                'risk_medium_unconfirmed': '中等风险（强势待确认）',
                'risk_medium_weak_bull': '中等风险（弱势多头）',
                'risk_medium_neutral': '中等风险（中性区间）',
                'risk_high': '较高风险（弱势空头）',
                'risk_very_high': '高风险（温和下跌）',
                'risk_extremely_high': '极高风险（强势下跌确认）',
                
                # 表格列标题
                'col_stock_code': '股票代码',
                'col_stock_name': '股票名称',
                'col_industry': '所属行业',
                'col_rtsi_index': 'RTSI指数',
                'col_trend_direction': '趋势方向',
                'col_data_reliability': '数据可靠性',
                'col_irsi_index': 'IRSI指数',
                'col_msci_index': 'MSCI指数',
                
                # 分析结果显示
                'result_data_overview': '数据概览',
                'result_total_stocks': '总股票数',
                'result_industry_count': '行业分类',
                'result_calculation_time': '计算耗时',
                'result_data_date': '数据日期',
                'result_top_stocks': '优质个股 TOP5 (按RTSI排序)',
                'result_top_industries': '强势行业 TOP5 (按IRSI排序)',
                'result_market_sentiment': '市场情绪分析',
                'result_no_data': '暂无数据',
                
                # AI分析相关
                'ai_intelligent_analysis': 'AI智能分析',
                'ai_analyst_opinion': 'AI分析师观点',
                'ai_analysis_disclaimer': 'AI分析基于当前市场数据和算法模型，仅供参考。',
                'ai_intelligent_analysis_in_progress': 'AI智能分析进行中...',
                
                # 设置对话框
                'settings_title': '系统设置',
                'settings_analysis': '分析设置',
                'settings_interface': '界面设置',
                'settings_performance': '性能设置',
                'settings_rtsi_params': 'RTSI算法参数',
                'settings_irsi_params': 'IRSI算法参数',
                'settings_msci_params': 'MSCI算法参数',
                'settings_min_data_points': '最小数据点数',
                'settings_consistency_weight': '一致性权重',
                'settings_historical_period': '历史周期',
                
                # 确认对话框
                'confirm_cancel_analysis': '确定要取消分析吗？',
                'confirm_title': '确认',
                'msg_analysis_complete': '数据分析已完成！',
                'msg_complete': '完成',
                
                # 评级等级
                'rating_big_bull': '大多',
                'rating_mid_bull': '中多',
                'rating_small_bull': '小多',
                'rating_micro_bull': '微多',
                'rating_micro_bear': '微空',
                'rating_small_bear': '小空',
                'rating_mid_bear': '中空',
                'rating_big_bear': '大空',
                
                # 其他常用词汇
                'unknown': '未知',
                'uncategorized': '未分类',
                'unknown_stock': '未知股票',
                'data_preparing': '数据准备中...',
                'system_generating': '系统正在基于RTSI指数生成30天趋势数据\n预计需要1-2秒完成\n\n请稍候或刷新重试',
                'loading_success': '语言管理器加载成功',
                'loading_failed': '语言管理器导入失败',
                'config_load_success': '用户配置文件加载成功',
                'config_load_failed': '加载用户配置失败，使用默认配置',
                'batch_calculation_start': '开始批量计算RTSI指数...',
                'batch_calculation_complete': '批量计算完成',
                'batch_processing': '已处理',
                'average_speed': '平均速度',
                'stocks_per_second': '只/秒',
                'data_scale': '数据规模',
                'trading_days': '个交易日',
                'warning_no_date_columns': '警告：未找到有效的日期列',
                'test_rtsi_calculator': '测试RTSI计算器...',
                'test_result': '测试结果',
                'data_analysis_in_progress': '正在分析数据，请稍候...',
                'data_analysis_ongoing': '数据分析进行中...',
                'data_loading_validation': '数据加载和验证',
                'rtsi_individual_trend_analysis': 'RTSI个股趋势分析',
                'analysis_error': '分析过程中发生错误',
                'analysis_failed_msg': '数据分析失败!',
                'tip_possible_reasons': '提示 可能的原因',
                'solution_suggestions': '解决建议',
                'analysis_complete': '分析完成',
                'found_stocks_industries': '发现 股票， 个行业分类',
                'analysis_result_empty': '分析结果为空',
                'total_stock_count': '总股票数',
                'industry_classification': '行业分类',
                'calculation_time': '计算耗时',
                'data_date': '数据日期',
                'top_quality_stocks': '优质个股 TOP5',
                'top_strong_industries': '强势行业 TOP5',
                'no_data_available': '暂无数据',
                'data_format_error': '数据格式错误',
                'sort_by_column': '按列排序',
                'double_click_event': '双击事件处理',
                'show_detail_dialog': '显示详细信息对话框',
                'show_stock_details': '显示股票详细信息',
                'filter_stocks': '筛选股票',
                'clear_display': '清空显示',
                'reload_filtered_data': '重新加载符合筛选条件的数据',
                'get_selected_stock_codes': '获取选中的股票代码列表',
                'analysis_result_component': '分析结果显示组件',
                'setup_scrollbar': '设置滚动条',
                'setup_text_styles': '设置文本标签样式',
                'title_style': '标题样式',
                'subtitle_style': '子标题样式',
                'success_info': '成功信息',
                'warning_info': '警告信息',
                'error_info': '错误信息',
                'highlight_info': '高亮信息',
                'number_style': '数值样式',
                'clear_content': '清空内容',
                'append_text': '追加文本',
                'set_content': '设置内容',
                'display_analysis_result': '显示分析结果',
                'core_ai_stock_trend_analysis': '核心 AI股票趋势分析结果',
                'market_sentiment_analysis': '市场情绪分析',
                'market_state': '市场状态',
                'top_10_quality_stocks': '优质个股TOP10',
                'rating_coverage': '评级覆盖',
                'units_stocks': '只',
                'units_industries': '个',
                'check_ai_stock_trend_analysis': '检查 AI股票趋势分析',
                'initializing_analysis_engine': '正在初始化分析引擎...',
                'reading_excel_parsing_data': '读取Excel文件，解析股票和行业数据',
                'validating_rating_system': '验证8级评级系统，清理无效数据',
                'calculating_rtsi_trend': '使用线性回归分析个股评级趋势',
                'calculating_irsi_strength': '计算行业相对市场表现强度',
                'calculating_msci_sentiment': '综合分析市场整体情绪状态',
                'generating_analysis_report': '整理分析结果，准备可视化数据',
                'all_tasks_completed': '所有分析任务已完成，准备展示结果',
                'confirm_cancel': '确认',
                'confirm_cancel_analysis_msg': '确定要取消分析吗？',
                'complete_msg': '完成',
                'analysis_completed_msg': '数据分析已完成！',
                'analysis_failed_title': '分析失败',
                'analysis_error_occurred': '分析过程中发生错误',
                
                # Main GUI startup messages
                'gui_import_success': '成功：GUI模块导入成功',
                'gui_import_failed': '错误：GUI模块导入失败',
                'gui_check_files': '请确保gui目录下的所有文件都正确创建',
                'core_modules_available': '成功：核心模块可用',
                'core_modules_warning': '警告：部分核心模块不可用',
                'gui_limited_functionality': 'GUI界面可以启动，但分析功能可能受限',
                'checking_environment': '检查：正在检查运行环境...',
                'python_version_low': '错误：Python版本过低',
                'python_version_recommend': '建议使用Python 3.10+',
                'python_version_ok': '成功：Python版本',
                'module_available': '成功',
                'available': '可用',
                'module_missing': '错误',
                'missing': '缺失',
                'missing_modules': '缺失模块',
                'install_command': '请运行：pip install pandas numpy matplotlib',
                'module_warning': '警告',
                'optional': '可选',
                'not_available': '不可用',
                'environment_check_complete': '成功：环境检查完成',
                'startup_title': '快速AI股票大师',
                'startup_features': '数据特色：',
                'windows_classic_ui': 'Windows经典风格界面',
                'realtime_analysis_engine': '实时数据分析引擎',
                'advanced_visualization': '高级可视化报告',
                'startup_data_support': '核心数据支持：',
                'excel_format': 'Excel格式',
                'stock_count': '股票数量',
                'stocks': '只',
                'categories': '个分类',
                'rating_system': '评级系统',
                'levels': '级',
                'rating_range': '强烈买入→强烈卖出',
                'startup_shortcuts': '快捷操作：',
                'open_file': '打开文件',
                'start_analysis': '开始分析',
                'export_report': '导出报告',
                
                # Additional hardcoded strings
                '突破阻力位时': '突破阻力位时',
                '等待止跌企稳信号': '等待止跌企稳信号',
                '跌破近期支撑位': '跌破近期支撑位',
                '设置8-10%止损位': '设置8-10%止损位',
                '上看前高或新高': '上看前高或新高',
                '看至前期阻力位': '看至前期阻力位',
                '暂不设定目标价': '暂不设定目标价',
                '中长线持有(1-3个月)': '中长线持有(1-3个月)',
                '短中线操作(2-4周)': '短中线操作(2-4周)',
                '超短线或暂不持有': '超短线或暂不持有',
                '提示': '提示',
                '请先选择并分析股票': '请先选择并分析股票',
                '文本文件': '文本文件',
                'Excel文件': 'Excel文件',
                '所有文件': '所有文件',
                '股票代码': '股票代码',
                '股票名称': '股票名称',
                '生成时间': '生成时间',
                '成功': '成功',
                '错误': '错误',
                '导出失败': '导出失败',
                '请先选择股票': '请先选择股票',
                '已在关注列表中': '已在关注列表中',
                '已将': '已将',
                '添加到关注列表': '添加到关注列表',
                '添加关注失败': '添加关注失败',
                '数据已刷新': '数据已刷新',
                '刷新数据失败': '刷新数据失败',
                '强势': '强势',
                '中性偏强': '中性偏强',
                '中性': '中性',
                '中性偏弱': '中性偏弱',
                '弱势': '弱势',
                '已加载': '已加载',
                '个行业的IRSI数据': '个行业的IRSI数据',
                '暂无行业分析数据': '暂无行业分析数据',
                '行业数据加载失败': '行业数据加载失败',
                '正在分析行业数据': '正在分析行业数据',
                '弱势空头格局，下跌空间有限，适度防御': '弱势空头格局，下跌空间有限，适度防御',
                '温和空头趋势，下跌动能充足，建议减仓': '温和空头趋势，下跌动能充足，建议减仓',
                '强势空头趋势，技术面极度悲观，严格风控': '强势空头趋势，技术面极度悲观，严格风控',
                '中等波动': '中等波动',
                '大盘股': '大盘股',
                '成长股': '成长股',
                '中盘股': '中盘股',
                '行业整体表现中性': '行业整体表现中性',
                '可适度参与，关注量价配合': '可适度参与，关注量价配合',
                '观望为主，等待明确信号': '观望为主，等待明确信号',
                '避免抄底，等待趋势反转': '避免抄底，等待趋势反转',
                '可配置': '可配置',
                '优质标的': '优质标的',
                '等待更好的配置时机': '等待更好的配置时机',
                '高风险，严格止损': '高风险，严格止损',
                '中等风险，控制仓位': '中等风险，控制仓位',
                '相对安全，注意回调风险': '相对安全，注意回调风险',
                '回调至支撑位时': '回调至支撑位时',
                '数据加载失败': '数据加载失败',
                '请检查数据源': '请检查数据源',
                '建议': '建议',
                '确认已加载数据文件': '确认已加载数据文件',
                '完成数据分析': '完成数据分析',
                '选择有效股票': '选择有效股票',
                '技术面显示': '技术面显示',
                '行业及该股仍有上涨空间，建议持续关注基本面变化': '行业及该股仍有上涨空间，建议持续关注基本面变化',
                '股价处于震荡期，需要观察': '股价处于震荡期，需要观察',
                '行业催化剂和量能变化': '行业催化剂和量能变化',
                '技术面偏弱，建议等待': '技术面偏弱，建议等待',
                '行业整体企稳后再考虑配置': '行业整体企稳后再考虑配置'
            },
            
            'en': {
                # Main Window and Application
                'app_title': 'AI Stock Trend Analysis System',
                'app_version': 'v2.2',
                'welcome_title': 'Welcome',
                'welcome_core_features': 'Core Features',
                'welcome_getting_started': 'Getting Started',
                'welcome_dynamic_analysis': 'Dynamic Data Analysis',
                'welcome_system_config': 'System Configuration',
                'welcome_note': 'Note',
                'welcome_step1': 'Click "Load" button in the top right to select data file',
                'welcome_step2': 'Supported formats: *.json.gz',
                'welcome_step3': 'Recommended file: A-Share Data YYYYMMDD.xlsx',
                'welcome_stock_count': 'Stock Count - Dynamically read from data file',
                'welcome_industry_count': 'Industry Count - Dynamically categorized',
                'welcome_industry_query': 'Industry Info - Real-time query, not saved',
                'welcome_tech_stack': 'Technology Stack',
                'welcome_classic_ui': 'Classic UI Style',
                'welcome_professional_algo': 'Professional Data Analysis Algorithms',
                'welcome_note_desc': 'System does not auto-load files, all data is dynamically read from user-selected files',
                
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
                'menu_update_data_files': 'Update Data Files',
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
                'btn_stock': 'Stock',
                'btn_industry': 'Industry',
                'btn_market': 'Market',
                'btn_open_file': 'Open File',
                'btn_start_analysis': 'Start Analysis',
                'btn_export_report': 'Export Report',
                'btn_refresh': 'Refresh',
                'btn_export': 'Export',
                'btn_add_watchlist': 'Watch',
                'btn_close': 'Close',
                'btn_cancel': 'Cancel',
                'btn_complete': 'Complete',
                'btn_export_analysis': 'Export Analysis',
                'btn_add_watch': 'Add to Watchlist',
                'btn_refresh_data': 'Refresh Data',
                
                # Stock Analysis Window
                'stock_selector_label': 'Stock Selection:',
                'search_label': 'Search:',
                'core_metrics_label': 'Core Metrics',
                
                # Industry Analysis Window
                'industry_rotation_title': 'Industry Rotation Strength Analysis',
                'industry_irsi_ranking': 'Industry IRSI Ranking',
                'industry_detail_info': 'Industry Detail Information',
                
                # Market Sentiment Analysis Window
                'market_sentiment_title': 'Market Sentiment Comprehensive Analysis',
                'btn_msci_details': 'MSCI Details',
                'btn_market_alerts': 'Market Alerts',
                
                # Status Information
                'status_loading_industry': 'Loading industry data...',
                'status_loading_data': 'Loading data...',
                'status_generating_report': 'Generating analysis report...',
                'status_data_validation': 'Data validation and preprocessing...',
                'status_calculating_rtsi': 'Calculating RTSI stock trend index...',
                'status_calculating_irsi': 'Calculating IRSI industry strength index...',
                'status_calculating_msci': 'Calculating MSCI market sentiment index...',
                'status_analysis_complete': 'Analysis complete!',
                'status_updating_data': 'Updating data files...',
                'status_data_update_complete': 'Data files update completed',
                'status_data_update_failed': 'Data files update failed',
                
                # Table Column Headers
                'column_rank': 'Rank',
                'column_code': 'Code',
                'column_name': 'Name',
                'column_industry': 'Industry',
                'column_status': 'Status',
                'column_stock_count': 'Stock Count',
                'column_item': 'Item',
                'column_value': 'Value',
                'column_trend': 'Trend',
                
                # Analysis Report Related
                'analysis_report_title': 'Analysis Report',
                'industry_analysis_report': 'Industry Analysis Report',
                'market_analysis_report': 'Market Sentiment Comprehensive Analysis Report',
                'stock_analysis_report': 'Stock Analysis Report',
                'export_analysis_report': 'Export Stock Analysis Report',
                'report_export_success': 'Analysis report exported to',
                'report_generation_failed': 'Analysis report generation failed',
                
                # Chart and Analysis Interface
                'chart_select_stock': 'Please select a stock for analysis',
                'chart_time': 'Time',
                'chart_rating_score': 'Rating Score',
                'chart_waiting_analysis': 'Waiting for analysis...',
                'analysis_data_status': 'Data Status',
                'analysis_completed': 'Analysis completed',
                'analysis_waiting': 'Waiting for analysis',
                'generation_time': 'Generation Time',
                'core_indicators': 'Core Indicators',
                'technical_analysis': 'Technical Analysis',
                'operation_suggestion': 'Operation Suggestion',
                'risk_warning': 'Stock market involves risks. Please combine fundamental analysis and risk tolerance.',
                'data_update_info': 'Data Update: Real-time calculation based on latest rating data',
                'analysis_time': 'Analysis Time',
                'historical_comparison': 'Historical Comparison',
                'deep_analysis_report': 'Deep Analysis Report',
                'trend_status': 'Trend Status',
                'technical_strength': 'Technical Strength',
                'industry_category': 'Industry Category',
                'market_cap_level': 'Market Cap Level',
                'trend_direction': 'Trend Direction',
                'volatility_level': 'Volatility Level',
                'support_resistance': 'Support & Resistance',
                'relative_strength': 'Relative Strength',
                'industry_comparison': 'Industry Comparison',
                'industry_performance': 'Industry Performance',
                'industry_position': 'Industry Position',
                'rotation_signal': 'Rotation Signal',
                'investment_advice': 'Investment Advice',
                'short_term_strategy': 'Short-term Strategy',
                'medium_term_strategy': 'Medium-term Strategy',
                'risk_assessment': 'Risk Assessment',
                'technical_risk': 'Technical Risk',
                'industry_risk': 'Industry Risk',
                'market_risk': 'Market Risk',
                'liquidity': 'Liquidity',
                'operation_advice': 'Operation Advice',
                'best_entry_point': 'Best Entry Point',
                'stop_loss_position': 'Stop Loss Position',
                'target_price': 'Target Price',
                'holding_period': 'Holding Period',
                'future_outlook': 'Future Outlook',
                'disclaimer': 'Disclaimer',
                'disclaimer_text': 'This analysis is based on RTSI technical algorithm, for reference only, does not constitute investment advice.',
                'data_source': 'Data Source',
                'analysis_failed': 'Analysis Report Generation Failed',
                'error_info': 'Error Information',
                'check_data_integrity': 'Please check data integrity or contact technical support.',
                'strong': 'Strong',
                'neutral': 'Neutral',
                'weak': 'Weak',
                'leading': 'Leading',
                'lagging': 'Lagging',
                'blue_chip': 'Blue Chip',
                'average': 'Average',
                'active': 'Active',
                'wait_and_see': 'Wait and See',
                'cautious': 'Cautious',
                'good': 'Good',
                'small_cap': 'Small Cap',
                'uncategorized': 'Uncategorized',
                'based_on_rating_analysis': 'Based on rating change analysis',
                'pay_attention_to_policy': 'Pay attention to {industry} policy and cycle changes',
                'pay_attention_to_market': 'Need to pay attention to market trends and systemic risks',
                'super_strong_trend': 'Super Strong Trend',
                'strong_uptrend': 'Strong Uptrend',
                'consolidation': 'Consolidation',
                'weak_downtrend': 'Weak Downtrend',
                'deep_adjustment': 'Deep Adjustment',
                'strong_bull_trend': 'Strong bullish trend, extremely optimistic technical outlook, recommend active allocation',
                'moderate_bull_trend': 'Moderate bullish trend, sufficient upward momentum, suitable for medium-term holding',
                'weak_bull_pattern': 'Weak bullish pattern, limited upside space, cautiously optimistic',
                'sideways_consolidation': 'Sideways consolidation pattern, direction pending, mainly wait and see',
                'index': 'Index',
                'industry': 'Industry',
                'core_metrics': 'Core Metrics',
                'irsi_index': 'IRSI Index',
                'relative_strength_performance': 'Relative Strength',
                'outperform_market': 'Outperform Market',
                'underperform_market': 'Underperform Market',
                'sync_with_market': 'Sync with Market',
                'strength_level': 'Strength Level',
                'performance_analysis': 'Performance Analysis',
                'short_term_trend': 'Short-term Trend',
                'investment_value': 'Investment Value',
                'risk_level': 'Risk Level',
                'analysis_description': 'Description',
                'irsi_description': 'IRSI index is calculated based on the performance of stocks within the industry relative to the overall market',
                'display_industry_detail_failed': 'Failed to display industry details',
                'cannot_find_industry_data': 'Cannot find industry',
                'detailed_data': 'detailed data',
                'msci_index': 'MSCI Index',
                'market_state': 'Market State',
                'trend_5d': '5-Day Trend',
                'sentiment_interpretation': 'Sentiment Interpretation',
                'bull_bear_balance': 'Bull-Bear Balance',
                'euphoric': 'Euphoric',
                'optimistic': 'Optimistic',
                'pessimistic': 'Pessimistic',
                'panic': 'Panic',
                'low_risk': 'Low Risk',
                'medium_risk': 'Medium Risk',
                'high_risk': 'High Risk',
                'core_metrics': '核心指标',
                'irsi_index': 'IRSI指数',
                'relative_strength_performance': '相对强度',
                'outperform_market': '跑赢大盘',
                'underperform_market': '跑输大盘',
                'sync_with_market': '与大盘同步',
                'strength_level': '强度等级',
                'performance_analysis': '表现分析',
                'short_term_trend': '短期趋势',
                'investment_value': '投资价值',
                'risk_level': '风险等级',
                'analysis_description': '说明',
                'irsi_description': 'IRSI指数基于行业内股票评级相对于整体市场的表现计算',
                'display_industry_detail_failed': '显示行业详细信息失败',
                'cannot_find_industry_data': '无法找到行业',
                'detailed_data': '的详细数据',
                'msci_index': 'MSCI指数',
                'market_state': '市场状态',
                'trend_5d': '5日趋势',
                'sentiment_interpretation': '情绪解读',
                'bull_bear_balance': '多空力量对比',
                'euphoric': '极度乐观',
                'optimistic': '乐观',
                'pessimistic': '悲观',
                'panic': '恐慌',
                'low_risk': '低风险',
                'medium_risk': '中等风险',
                'high_risk': '高风险',
                
                # Window Titles
                'stock_analysis_window_title': 'Stock Trend Analysis - RTSI Algorithm',
                'industry_analysis_window_title': 'Industry Rotation Analysis',
                'market_analysis_window_title': 'Market Sentiment Analysis',
                
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
                
                # Analysis Related
                'analysis_progress_title': 'Data Analysis in Progress...',
                'analysis_initializing': 'Initializing analysis engine...',
                'analysis_loading_data': 'Loading data...',
                'analysis_data_validation': 'Data validation and preprocessing...',
                'analysis_calculating_rtsi': 'Calculating RTSI stock trend index...',
                'analysis_calculating_irsi': 'Calculating IRSI industry strength index...',
                'analysis_calculating_msci': 'Calculating MSCI market sentiment index...',
                'analysis_generating_report': 'Generating analysis report...',
                'analysis_completed': 'Analysis completed!',
                'analysis_failed': 'Analysis failed',
                'analysis_cancelled': 'Analysis cancelled',
                
                # Analysis Stage Details
                'stage_detail_loading': 'Reading Excel file, parsing stock and industry data',
                'stage_detail_validation': 'Validating 8-level rating system, cleaning invalid data',
                'stage_detail_rtsi': 'Using linear regression to analyze stock rating trends',
                'stage_detail_irsi': 'Calculating industry relative market performance strength',
                'stage_detail_msci': 'Comprehensive analysis of overall market sentiment',
                'stage_detail_report': 'Organizing analysis results, preparing visualization data',
                'stage_detail_complete': 'All analysis tasks completed, preparing to display results',
                
                # Error and Warning Messages
                'error_file_load_failed': 'File loading failed!',
                'error_analysis_failed': 'Data analysis failed!',
                'error_insufficient_data': 'Insufficient data',
                'error_calculation_error': 'Calculation error',
                'warning_data_quality': 'Data quality warning: High interpolation ratio',
                'warning_serious': 'Serious warning: More than half of data requires interpolation, RTSI result reliability is low',
                
                # Data Update Feature
                'data_update_feature_unavailable': 'Data update feature is currently unavailable',
                'data_update_module_not_found': 'Data update module not found',
                'data_update_success': 'Data files updated successfully',
                'data_update_failed': 'Data update failed',
                'data_update_cancelled': 'Data update cancelled',
                'data_update_skipped': 'Data update skipped',
                'data_update_downloading': 'Downloading data files...',
                'data_update_progress': 'Download Progress',
                'data_update_cancel': 'Cancel',
                'data_update_skip': 'Skip Update',
                'data_update_checking': 'Checking for data updates...',
                'data_update_complete': 'Data update complete',
                
                # Trend Descriptions
                'trend_strong_bull': 'Strong Bullish',
                'trend_moderate_bull': 'Moderate Bullish',
                'trend_weak_bull': 'Weak Bullish',
                'trend_neutral': 'Sideways',
                'trend_weak_bear': 'Weak Bearish',
                'trend_moderate_bear': 'Moderate Bearish',
                'trend_strong_bear': 'Strong Bearish',
                'trend_unknown': 'Unknown Trend',
                'trend_insufficient_data': 'Insufficient Data',
                
                # Risk Levels
                'risk_extremely_low': 'Extremely Low Risk (Strong Confirmation)',
                'risk_low': 'Low Risk (Moderate Uptrend)',
                'risk_medium': 'Medium Risk',
                'risk_medium_unconfirmed': 'Medium Risk (Strong Unconfirmed)',
                'risk_medium_weak_bull': 'Medium Risk (Weak Bullish)',
                'risk_medium_neutral': 'Medium Risk (Neutral Zone)',
                'risk_high': 'High Risk (Weak Bearish)',
                'risk_very_high': 'Very High Risk (Moderate Decline)',
                'risk_extremely_high': 'Extremely High Risk (Strong Decline Confirmed)',
                
                # Table Column Headers
                'col_stock_code': 'Stock Code',
                'col_stock_name': 'Stock Name',
                'col_industry': 'Industry',
                'col_rtsi_index': 'RTSI Index',
                'col_trend_direction': 'Trend Direction',
                'col_data_reliability': 'Data Reliability',
                'col_irsi_index': 'IRSI Index',
                'col_msci_index': 'MSCI Index',
                
                # Analysis Results Display
                'result_data_overview': 'Data Overview',
                'result_total_stocks': 'Total Stocks',
                'result_industry_count': 'Industry Classification',
                'result_calculation_time': 'Calculation Time',
                'result_data_date': 'Data Date',
                'result_top_stocks': 'Top 5 Quality Stocks (by RTSI)',
                'result_top_industries': 'Top 5 Strong Industries (by IRSI)',
                'result_market_sentiment': 'Market Sentiment Analysis',
                'result_no_data': 'No data available',
                
                # AI Analysis Related
                'ai_intelligent_analysis': 'AI Intelligent Analysis',
                'ai_analyst_opinion': 'AI Analyst Opinion',
                'ai_analysis_disclaimer': 'AI analysis is based on current market data and algorithmic models, for reference only.',
                'ai_intelligent_analysis_in_progress': 'AI intelligent analysis in progress...',
                
                # Settings Dialog
                'settings_title': 'System Settings',
                'settings_analysis': 'Analysis Settings',
                'settings_interface': 'Interface Settings',
                'settings_performance': 'Performance Settings',
                'settings_rtsi_params': 'RTSI Algorithm Parameters',
                'settings_irsi_params': 'IRSI Algorithm Parameters',
                'settings_msci_params': 'MSCI Algorithm Parameters',
                'settings_min_data_points': 'Minimum Data Points',
                'settings_consistency_weight': 'Consistency Weight',
                'settings_historical_period': 'Historical Period',
                
                # Confirmation Dialogs
                'confirm_cancel_analysis': 'Are you sure you want to cancel the analysis?',
                'confirm_title': 'Confirm',
                'msg_analysis_complete': 'Data analysis completed!',
                'msg_complete': 'Complete',
                
                # Rating Levels
                'rating_big_bull': 'Strong Buy',
                'rating_mid_bull': 'Buy',
                'rating_small_bull': 'Weak Buy',
                'rating_micro_bull': 'Hold+',
                'rating_micro_bear': 'Hold-',
                'rating_small_bear': 'Weak Sell',
                'rating_mid_bear': 'Sell',
                'rating_big_bear': 'Strong Sell',
                
                # Other Common Vocabulary
                'unknown': 'Unknown',
                'uncategorized': 'Uncategorized',
                'unknown_stock': 'Unknown Stock',
                'data_preparing': 'Data preparing...',
                'system_generating': 'System is generating 30-day trend data based on RTSI index\nEstimated completion time: 1-2 seconds\n\nPlease wait or refresh',
                'loading_success': 'Language manager loaded successfully',
                'loading_failed': 'Language manager import failed',
                'config_load_success': 'User configuration file loaded successfully',
                'config_load_failed': 'Failed to load user configuration, using default settings',
                'batch_calculation_start': 'Starting batch RTSI index calculation...',
                'batch_calculation_complete': 'Batch calculation completed',
                'batch_processing': 'Processed',
                'average_speed': 'Average speed',
                'stocks_per_second': 'stocks/sec',
                'data_scale': 'Data scale',
                'trading_days': 'trading days',
                'warning_no_date_columns': 'Warning: No valid date columns found',
                'test_rtsi_calculator': 'Testing RTSI calculator...',
                'test_result': 'Test result',
                'data_analysis_in_progress': 'Data analysis in progress, please wait...',
                'data_analysis_ongoing': 'Data analysis in progress...',
                'data_loading_validation': 'Data loading and validation',
                'rtsi_individual_trend_analysis': 'RTSI individual stock trend analysis',
                'analysis_error': 'Error occurred during analysis',
                'analysis_failed_msg': 'Data analysis failed!',
                'tip_possible_reasons': 'Tip: Possible reasons',
                'solution_suggestions': 'Solution suggestions',
                'analysis_complete': 'Analysis complete',
                'found_stocks_industries': 'Found stocks, industry classifications',
                'analysis_result_empty': 'Analysis result is empty',
                'total_stock_count': 'Total stock count',
                'industry_classification': 'Industry classification',
                'calculation_time': 'Calculation time',
                'data_date': 'Data date',
                'top_quality_stocks': 'Top 5 quality stocks',
                'top_strong_industries': 'Top 5 strong industries',
                'no_data_available': 'No data available',
                'data_format_error': 'Data format error',
                'sort_by_column': 'Sort by column',
                'double_click_event': 'Double-click event handling',
                'show_detail_dialog': 'Show detailed information dialog',
                'show_stock_details': 'Show stock details',
                'filter_stocks': 'Filter stocks',
                'clear_display': 'Clear display',
                'reload_filtered_data': 'Reload data matching filter criteria',
                'get_selected_stock_codes': 'Get selected stock codes list',
                'analysis_result_component': 'Analysis result display component',
                'setup_scrollbar': 'Setup scrollbar',
                'setup_text_styles': 'Setup text tag styles',
                'title_style': 'Title style',
                'subtitle_style': 'Subtitle style',
                'success_info': 'Success message',
                'warning_info': 'Warning message',
                'error_info': 'Error message',
                'highlight_info': 'Highlight message',
                'number_style': 'Number style',
                'clear_content': 'Clear content',
                'append_text': 'Append text',
                'set_content': 'Set content',
                'display_analysis_result': 'Display analysis result',
                'core_ai_stock_trend_analysis': 'Core AI stock trend analysis results',
                'market_sentiment_analysis': 'Market sentiment analysis',
                'market_state': 'Market state',
                'top_10_quality_stocks': 'Top 10 quality stocks',
                'rating_coverage': 'Rating coverage',
                'units_stocks': 'stocks',
                'units_industries': 'industries',
                'check_ai_stock_trend_analysis': 'Check AI Stock Trend Analysis',
                'initializing_analysis_engine': 'Initializing analysis engine...',
                'reading_excel_parsing_data': 'Reading Excel file, parsing stock and industry data',
                'validating_rating_system': 'Validating 8-level rating system, cleaning invalid data',
                'calculating_rtsi_trend': 'Using linear regression to analyze stock rating trends',
                'calculating_irsi_strength': 'Calculating industry relative market performance strength',
                'calculating_msci_sentiment': 'Comprehensive analysis of overall market sentiment',
                'generating_analysis_report': 'Organizing analysis results, preparing visualization data',
                'all_tasks_completed': 'All analysis tasks completed, preparing to display results',
                'confirm_cancel': 'Confirm',
                'confirm_cancel_analysis_msg': 'Are you sure you want to cancel the analysis?',
                'complete_msg': 'Complete',
                'analysis_completed_msg': 'Data analysis completed!',
                'analysis_failed_title': 'Analysis Failed',
                'analysis_error_occurred': 'Error occurred during analysis',
                
                # Main GUI startup messages
                'gui_import_success': 'Success: GUI module imported successfully',
                'gui_import_failed': 'Error: GUI module import failed',
                'gui_check_files': 'Please ensure all files in the gui directory are correctly created',
                'core_modules_available': 'Success: Core modules available',
                'core_modules_warning': 'Warning: Some core modules unavailable',
                'gui_limited_functionality': 'GUI interface can start, but analysis functionality may be limited',
                'checking_environment': 'Checking: Checking runtime environment...',
                'python_version_low': 'Error: Python version too low',
                'python_version_recommend': 'Recommend using Python 3.10+',
                'python_version_ok': 'Success: Python version',
                'module_available': 'Success',
                'available': 'available',
                'module_missing': 'Error',
                'missing': 'missing',
                'missing_modules': 'Missing modules',
                'install_command': 'Please run: pip install pandas numpy matplotlib',
                'module_warning': 'Warning',
                'optional': 'optional',
                'not_available': 'not available',
                'environment_check_complete': 'Success: Environment check complete',
                'startup_title': 'Quick AI Stock Trend Analysis System',
                'startup_features': 'Data Features:',
                'windows_classic_ui': 'Windows classic style interface',
                'realtime_analysis_engine': 'Real-time data analysis engine',
                'advanced_visualization': 'Advanced visualization reports',
                'startup_data_support': 'Core Data Support:',
                'excel_format': 'Excel format',
                'stock_count': 'Stock count',
                'stocks': 'stocks',
                'categories': 'categories',
                'rating_system': 'Rating system',
                'levels': 'levels',
                'rating_range': 'Strong Buy→Strong Sell',
                'startup_shortcuts': 'Quick Shortcuts:',
                'open_file': 'Open file',
                'start_analysis': 'Start analysis',
                'export_report': 'Export report',
                
                # Additional hardcoded strings
                '突破阻力位时': 'When breaking resistance level',
                '等待止跌企稳信号': 'Wait for stabilization signal',
                '跌破近期支撑位': 'Below recent support level',
                '设置8-10%止损位': 'Set 8-10% stop loss',
                '上看前高或新高': 'Target previous high or new high',
                '看至前期阻力位': 'Target previous resistance level',
                '暂不设定目标价': 'No target price set',
                '中长线持有(1-3个月)': 'Medium to long-term holding (1-3 months)',
                '短中线操作(2-4周)': 'Short to medium-term operation (2-4 weeks)',
                '超短线或暂不持有': 'Ultra-short term or no holding',
                '提示': 'Tip',
                '请先选择并分析股票': 'Please select and analyze a stock first',
                '文本文件': 'Text files',
                'Excel文件': 'Excel files',
                '所有文件': 'All files',
                '股票代码': 'Stock Code',
                '股票名称': 'Stock Name',
                '生成时间': 'Generation Time',
                '成功': 'Success',
                '错误': 'Error',
                '导出失败': 'Export failed',
                '请先选择股票': 'Please select a stock first',
                '已在关注列表中': 'Already in watchlist',
                '已将': 'Added',
                '添加到关注列表': 'to watchlist',
                '添加关注失败': 'Failed to add to watchlist',
                '数据已刷新': 'Data refreshed',
                '刷新数据失败': 'Failed to refresh data',
                '强势': 'Strong',
                '中性偏强': 'Neutral-Strong',
                '中性': 'Neutral',
                '中性偏弱': 'Neutral-Weak',
                '弱势': 'Weak',
                '已加载': 'Loaded',
                '个行业的IRSI数据': 'industries IRSI data',
                '暂无行业分析数据': 'No industry analysis data available',
                '行业数据加载失败': 'Failed to load industry data',
                '正在分析行业数据': 'Analyzing industry data...',
                '弱势空头格局，下跌空间有限，适度防御': 'Weak bearish pattern, limited downside, moderate defense',
                '温和空头趋势，下跌动能充足，建议减仓': 'Moderate bearish trend, sufficient downward momentum, suggest reducing positions',
                '强势空头趋势，技术面极度悲观，严格风控': 'Strong bearish trend, extremely pessimistic technicals, strict risk control',
                '中等波动': 'Medium volatility',
                '大盘股': 'Large cap',
                '成长股': 'Growth stock',
                '中盘股': 'Mid cap',
                '行业整体表现中性': 'Industry overall performance neutral',
                '可适度参与，关注量价配合': 'Can participate moderately, watch volume-price coordination',
                '观望为主，等待明确信号': 'Mainly wait and see, await clear signals',
                '避免抄底，等待趋势反转': 'Avoid bottom fishing, wait for trend reversal',
                '可配置': 'Can allocate',
                '优质标的': 'quality targets',
                '等待更好的配置时机': 'Wait for better allocation opportunities',
                '高风险，严格止损': 'High risk, strict stop loss',
                '中等风险，控制仓位': 'Medium risk, control position size',
                '相对安全，注意回调风险': 'Relatively safe, watch pullback risk',
                '回调至支撑位时': 'When pulling back to support level',
                '数据加载失败': 'Data loading failed',
                '请检查数据源': 'Please check data source',
                '建议': 'Suggestions',
                '确认已加载数据文件': 'Confirm data file is loaded',
                '完成数据分析': 'Complete data analysis',
                '选择有效股票': 'Select valid stocks',
                '技术面显示': 'Technical analysis shows',
                '行业及该股仍有上涨空间，建议持续关注基本面变化': 'industry and this stock still have upside potential, suggest continuous attention to fundamental changes',
                '股价处于震荡期，需要观察': 'Stock price is in consolidation period, need to observe',
                '行业催化剂和量能变化': 'industry catalysts and volume changes',
                '技术面偏弱，建议等待': 'Technical side is weak, suggest waiting for',
                '行业整体企稳后再考虑配置': 'industry overall stabilization before considering allocation'
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
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        return list(self.translations.keys())
    
    def is_chinese(self) -> bool:
        """判断当前是否为中文"""
        return self.current_language == 'zh'
    
    def is_english(self) -> bool:
        """判断当前是否为英文"""
        return self.current_language == 'en'

# 全局语言管理器实例
improved_language_manager = ImprovedLanguageManager()

# 便捷函数
def _(key: str, default: str = None) -> str:
    """获取翻译文本的便捷函数"""
    return improved_language_manager.get_text(key, default)

def get_current_language() -> str:
    """获取当前语言"""
    return improved_language_manager.get_language()

def set_language(language: str):
    """设置语言"""
    improved_language_manager.set_language(language)

def is_chinese() -> bool:
    """判断当前是否为中文"""
    return improved_language_manager.is_chinese()

def is_english() -> bool:
    """判断当前是否为英文"""
    return improved_language_manager.is_english()

# 兼容性函数，用于替换现有的语言管理器
language_manager = improved_language_manager