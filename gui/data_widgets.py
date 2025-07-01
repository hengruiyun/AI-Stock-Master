# -*- coding: utf-8 -*-
"""
数据展示组件模块 - Windows经典风格的数据展示控件

实现:
- StockListWidget: 股票列表显示组件
- AnalysisResultWidget: 分析结果显示组件
- RankingWidget: 排名显示组件

技术栈: tkinter.ttk
设计风格: Windows经典表格和列表
"""

import tkinter as tk
from tkinter import ttk
from localization.improved_language_manager import ImprovedLanguageManager

# 获取国际化函数
lang_manager = ImprovedLanguageManager()
_ = lang_manager.get_text
from typing import List, Dict, Any
import pandas as pd


class StockListWidget(ttk.Treeview):
    """股票列表显示组件 - 基于Treeview的表格控件"""
    
    def __init__(self, parent, **kwargs):
        # 定义列
        columns = ('code', 'name', 'industry', 'rtsi', 'trend', 'confidence')
        super().__init__(parent, columns=columns, show='headings', **kwargs)
        
        # 设置列标题
        self.heading('#1', text='股票代码', anchor=tk.W)
        self.heading('#2', text='股票名称', anchor=tk.W)
        self.heading('#3', text='所属行业', anchor=tk.W)
        self.heading('#4', text='RTSI指数', anchor=tk.E)
        self.heading('#5', text='趋势方向', anchor=tk.CENTER)
        self.heading('#6', text='数据可靠性', anchor=tk.E)
        
        # 设置列宽
        self.column('#1', width=80, minwidth=60)
        self.column('#2', width=120, minwidth=100)
        self.column('#3', width=100, minwidth=80)
        self.column('#4', width=80, minwidth=60)
        self.column('#5', width=80, minwidth=60)
        self.column('#6', width=80, minwidth=60)
        
        # 设置排序功能
        for col in columns:
            self.heading(col, command=lambda c=col: self.sort_by_column(c))
        
        # 添加滚动条
        self.setup_scrollbars()
        
        # 双击事件
        self.bind('<Double-1>', self.on_double_click)
        
        # 数据存储
        self.stock_data = {}
        self.sort_reverse = {}
    
    def setup_scrollbars(self):
        """设置滚动条"""
        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(self.master, orient=tk.VERTICAL, command=self.yview)
        self.configure(yscrollcommand=v_scrollbar.set)
        
        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(self.master, orient=tk.HORIZONTAL, command=self.xview)
        self.configure(xscrollcommand=h_scrollbar.set)
        
        # 布局
        self.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # 配置grid权重
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
    
    def load_stock_data(self, stocks_data: Dict[str, Any]):
        """加载股票数据"""
        # 清空现有数据
        for item in self.get_children():
            self.delete(item)
        
        self.stock_data = stocks_data
        
        # 填充数据
        for stock_code, stock_info in stocks_data.items():
            rtsi_data = stock_info.get('rtsi', {})
            
            # 趋势方向中文映射
            trend_mapping = {
                'strong_up': '强势上涨',
                'weak_up': '弱势上涨', 
                'sideways': '横盘整理',
                'weak_down': '弱势下跌',
                'strong_down': '强势下跌'
            }
            
            values = (
                stock_code,
                stock_info.get('name', '未知'),
                stock_info.get('industry', '未分类'),
                f"{rtsi_data.get('rtsi', 0):.2f}",
                trend_mapping.get(rtsi_data.get('trend', 'sideways'), '未知'),
                f"{rtsi_data.get('confidence', 0):.3f}"
            )
            
            # 插入数据项
            item = self.insert('', tk.END, values=values)
            
            # 根据RTSI值设置颜色
            rtsi_value = rtsi_data.get('rtsi', 0)
            if rtsi_value > 70:
                self.set(item, '#4', f"{rtsi_value:.2f}")
                self.item(item, tags=('high_rtsi',))
            elif rtsi_value < 30:
                self.item(item, tags=('low_rtsi',))
        
        # 设置标签样式
        self.tag_configure('high_rtsi', foreground='green')
        self.tag_configure('low_rtsi', foreground='red')
    
    def sort_by_column(self, col):
        """按列排序"""
        # 获取所有数据
        data = [(self.set(item, col), item) for item in self.get_children('')]
        
        # 数值列特殊处理
        if col in ['#4', '#6']:  # RTSI指数和数据可靠性
            try:
                data = [(float(val), item) for val, item in data]
            except ValueError:
                pass
        
        # 切换排序方向
        reverse = self.sort_reverse.get(col, False)
        data.sort(reverse=reverse)
        self.sort_reverse[col] = not reverse
        
        # 重新排列
        for index, (val, item) in enumerate(data):
            self.move(item, '', index)
    
    def on_double_click(self, event):
        """双击事件处理"""
        selection = self.selection()
        if selection:
            item = selection[0]
            stock_code = self.set(item, '#1')
            stock_name = self.set(item, '#2')
            
            # 显示详细信息对话框
            self.show_stock_detail(stock_code, stock_name)
    
    def show_stock_detail(self, stock_code, stock_name):
        """显示股票详细信息"""
        if stock_code in self.stock_data:
            stock_info = self.stock_data[stock_code]
            detail_window = StockDetailWindow(self.master, stock_code, stock_name, stock_info)
    
    def filter_stocks(self, filter_text: str = ""):
        """筛选股票"""
        # 清空显示
        for item in self.get_children():
            self.delete(item)
        
        # 重新加载符合筛选条件的数据
        filtered_data = {}
        for code, info in self.stock_data.items():
            if (filter_text.lower() in code.lower() or 
                filter_text.lower() in info.get('name', '').lower() or
                filter_text.lower() in info.get('industry', '').lower()):
                filtered_data[code] = info
        
        self.load_stock_data(filtered_data)
    
    def get_selected_stocks(self) -> List[str]:
        """获取选中的股票代码列表"""
        selection = self.selection()
        return [self.set(item, '#1') for item in selection]


class AnalysisResultWidget(tk.Text):
    """分析结果显示组件 - 基于Text的多行文本显示"""
    
    def __init__(self, parent, **kwargs):
        # 设置默认样式
        default_kwargs = {
            'bg': 'white',
            'fg': 'black',
            'font': ('Consolas', 10),
            'wrap': tk.WORD,
            'state': tk.DISABLED,
            'padx': 10,
            'pady': 10
        }
        default_kwargs.update(kwargs)
        
        super().__init__(parent, **default_kwargs)
        
        # 添加滚动条
        self.setup_scrollbar()
        
        # 配置文本标签样式
        self.setup_text_tags()
    
    def setup_scrollbar(self):
        """设置滚动条"""
        self.scrollbar = tk.Scrollbar(self.master, orient=tk.VERTICAL, command=self.yview)
        self.configure(yscrollcommand=self.scrollbar.set)
        
        # 布局
        self.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_text_tags(self):
        """设置文本标签样式"""
        # 标题样式
        self.tag_configure('title', font=('Microsoft YaHei', 14, 'bold'), foreground='#0078d4')
        
        # 子标题样式
        self.tag_configure('subtitle', font=('Microsoft YaHei', 12, 'bold'), foreground='#333333')
        
        # 成功信息
        self.tag_configure('success', foreground='#008000')
        
        # 警告信息
        self.tag_configure('warning', foreground='#ff8c00')
        
        # 错误信息
        self.tag_configure('error', foreground='#cc0000')
        
        # 高亮信息
        self.tag_configure('highlight', background='#ffffcc', foreground='#333333')
        
        # 数值样式
        self.tag_configure('number', font=('Consolas', 10, 'bold'), foreground='#0078d4')
    
    def clear_content(self):
        """清空内容"""
        self.config(state=tk.NORMAL)
        self.delete(1.0, tk.END)
        self.config(state=tk.DISABLED)
    
    def append_text(self, text: str, tag: str = None):
        """追加文本"""
        self.config(state=tk.NORMAL)
        if tag:
            self.insert(tk.END, text, tag)
        else:
            self.insert(tk.END, text)
        self.config(state=tk.DISABLED)
        self.see(tk.END)
    
    def set_content(self, content: str, tag: str = None):
        """设置内容"""
        self.clear_content()
        self.append_text(content, tag)
    
    def display_analysis_result(self, analysis_data: Dict[str, Any]):
        """显示分析结果"""
        self.clear_content()
        
        # 标题
        self.append_text("核心 AI股票趋势分析结果\n\n", 'title')
        
        # 数据概览
        summary = analysis_data.get('summary', {})
        self.append_text("数据 数据概览\n", 'subtitle')
        self.append_text(f"• 总股票数: ")
        self.append_text(f"{summary.get('total_stocks', 0)}", 'number')
        self.append_text(" 只\n")
        
        self.append_text(f"• 行业分类: ")
        self.append_text(f"{summary.get('total_industries', 0)}", 'number')
        self.append_text(" 个\n")
        
        self.append_text(f"• 评级覆盖: ")
        self.append_text(f"{summary.get('rating_coverage', 0):.1f}%", 'number')
        self.append_text("\n\n")
        
        # 市场情绪
        market = analysis_data.get('market_sentiment', {})
        self.append_text("上涨 市场情绪分析\n", 'subtitle')
        self.append_text(f"• MSCI指数: ")
        self.append_text(f"{market.get('current_msci', 0):.2f}", 'number')
        self.append_text("\n")
        
        state = market.get('market_state', '未知')
        state_color = 'success' if state in ['optimistic', 'euphoric'] else 'warning' if state == 'neutral' else 'error'
        self.append_text(f"• 市场状态: ")
        self.append_text(f"{state}", state_color)
        self.append_text("\n\n")
        
        # 顶级股票
        top_stocks = analysis_data.get('top_stocks', [])[:10]
        if top_stocks:
            self.append_text("优秀 优质个股TOP10\n", 'subtitle')
            for i, stock in enumerate(top_stocks, 1):
                self.append_text(f"{i:2d}. {stock.get('name', '未知')} ")
                self.append_text(f"({stock.get('code', '')})", 'highlight')
                self.append_text(f" - RTSI: ")
                self.append_text(f"{stock.get('rtsi', 0):.2f}", 'number')
                self.append_text("\n")
        
        self.append_text("\n提示 详细数据请查看上方股票列表和排名表格")


class RankingWidget(ttk.Treeview):
    """排名显示组件 - 显示各种排名信息"""
    
    def __init__(self, parent, ranking_type="stock", **kwargs):
        self.ranking_type = ranking_type
        
        # 根据类型设置列
        if ranking_type == "stock":
            columns = ('rank', 'code', 'name', 'rtsi', 'trend')
            self.column_headers = [_("column_rank", "排名"), _("column_code", "代码"), _("column_name", "名称"), 'RTSI', _("column_trend", "趋势")]
        elif ranking_type == "industry":
            columns = ('rank', 'industry', 'irsi', 'status', 'stocks')
            self.column_headers = [_("column_rank", "排名"), _("column_industry", "行业"), 'IRSI', _("column_status", "状态"), _("column_stock_count", "股票数")]
        else:
            columns = ('rank', 'item', 'value', 'status')
            self.column_headers = [_("column_rank", "排名"), _("column_item", "项目"), _("column_value", "数值"), _("column_status", "状态")]
        
        super().__init__(parent, columns=columns, show='headings', **kwargs)
        
        # 设置列标题
        for i, (col, header) in enumerate(zip(columns, self.column_headers)):
            self.heading(col, text=header, anchor=tk.W if i < 2 else tk.CENTER)
        
        # 设置列宽
        self.setup_column_widths()
        
        # 添加滚动条
        self.setup_scrollbar()
        
        # 样式配置
        self.setup_styles()
    
    def setup_column_widths(self):
        """设置列宽"""
        if self.ranking_type == "stock":
            widths = [50, 80, 120, 80, 80]
        elif self.ranking_type == "industry":
            widths = [50, 120, 80, 80, 80]
        else:
            widths = [50, 150, 100, 100]
        
        for i, width in enumerate(widths):
            col = f"#{i+1}"
            self.column(col, width=width, minwidth=width-20)
    
    def setup_scrollbar(self):
        """设置滚动条"""
        scrollbar = ttk.Scrollbar(self.master, orient=tk.VERTICAL, command=self.yview)
        self.configure(yscrollcommand=scrollbar.set)
        
        self.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_styles(self):
        """设置样式"""
        # 顶部3名金银铜配色
        self.tag_configure('rank1', background='#FFD700', foreground='#8B4513')  # 金色
        self.tag_configure('rank2', background='#C0C0C0', foreground='#000000')  # 银色
        self.tag_configure('rank3', background='#CD7F32', foreground='#FFFFFF')  # 铜色
        
        # 正面和负面指标
        self.tag_configure('positive', foreground='#008000')
        self.tag_configure('negative', foreground='#cc0000')
        self.tag_configure('neutral', foreground='#666666')
    
    def load_stock_ranking(self, stocks_data: List[Dict[str, Any]]):
        """加载股票排名数据"""
        if self.ranking_type != "stock":
            return
        
        # 清空现有数据
        for item in self.get_children():
            self.delete(item)
        
        # 按RTSI排序
        sorted_stocks = sorted(stocks_data, 
                             key=lambda x: x.get('rtsi', {}).get('rtsi', 0), 
                             reverse=True)
        
        # 趋势映射
        trend_mapping = {
            'strong_up': '强势上涨',
            'weak_up': '弱势上涨',
            'sideways': '横盘整理',
            'weak_down': '弱势下跌',
            'strong_down': '强势下跌'
        }
        
        # 填充数据
        for i, stock in enumerate(sorted_stocks[:50], 1):  # 只显示前50名
            rtsi_data = stock.get('rtsi', {})
            values = (
                i,
                stock.get('code', ''),
                stock.get('name', '未知'),
                f"{rtsi_data.get('rtsi', 0):.2f}",
                trend_mapping.get(rtsi_data.get('trend', 'sideways'), '未知')
            )
            
            item = self.insert('', tk.END, values=values)
            
            # 设置排名样式
            if i == 1:
                self.item(item, tags=('rank1',))
            elif i == 2:
                self.item(item, tags=('rank2',))
            elif i == 3:
                self.item(item, tags=('rank3',))
            
            # 设置趋势颜色
            trend = rtsi_data.get('trend', 'sideways')
            if 'up' in trend:
                self.set(item, '#5', f"{trend_mapping.get(trend, '未知')}")
                self.item(item, tags=self.item(item, 'tags') + ('positive',))
            elif 'down' in trend:
                self.set(item, '#5', f"{trend_mapping.get(trend, '未知')}")
                self.item(item, tags=self.item(item, 'tags') + ('negative',))
    
    def load_industry_ranking(self, industries_data: List[Dict[str, Any]]):
        """加载行业排名数据"""
        if self.ranking_type != "industry":
            return
        
        # 清空现有数据
        for item in self.get_children():
            self.delete(item)
        
        # 按IRSI排序
        sorted_industries = sorted(industries_data,
                                 key=lambda x: x.get('irsi', 0),
                                 reverse=True)
        
        # 状态映射
        status_mapping = {
            'strong_outperform': '强势领先',
            'weak_outperform': '弱势领先',
            'neutral': '中性',
            'weak_underperform': '弱势落后',
            'strong_underperform': '强势落后'
        }
        
        # 填充数据
        for i, industry in enumerate(sorted_industries, 1):
            values = (
                i,
                industry.get('name', '未知'),
                f"{industry.get('irsi', 0):.2f}",
                status_mapping.get(industry.get('status', 'neutral'), '未知'),
                industry.get('stock_count', 0)
            )
            
            item = self.insert('', tk.END, values=values)
            
            # 设置排名样式
            if i <= 3:
                self.item(item, tags=(f'rank{i}',))
            
            # 设置状态颜色
            status = industry.get('status', 'neutral')
            if 'outperform' in status:
                self.item(item, tags=self.item(item, 'tags') + ('positive',))
            elif 'underperform' in status:
                self.item(item, tags=self.item(item, 'tags') + ('negative',))
            else:
                self.item(item, tags=self.item(item, 'tags') + ('neutral',))


class StockDetailWindow:
    """股票详细信息窗口"""
    
    def __init__(self, parent, stock_code, stock_name, stock_info):
        self.window = tk.Toplevel(parent)
        self.window.title(f"股票详情 - {stock_name} ({stock_code})")
        self.window.geometry("500x400")
        self.window.configure(bg='#f0f0f0')
        
        # 模态窗口
        self.window.transient(parent)
        self.window.grab_set()
        
        self.setup_content(stock_code, stock_name, stock_info)
        
        # 居中显示
        self.center_window()
    
    def center_window(self):
        """窗口居中"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
    
    def setup_content(self, stock_code, stock_name, stock_info):
        """设置窗口内容"""
        # 标题区域
        title_frame = tk.Frame(self.window, bg='#0078d4', height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text=f"{stock_name} ({stock_code})",
                              bg='#0078d4', fg='white',
                              font=('Microsoft YaHei', 14, 'bold'))
        title_label.pack(expand=True)
        
        # 内容区域
        content_frame = tk.Frame(self.window, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 基本信息
        info_text = f"""基本信息:
• 股票代码: {stock_code}
• 股票名称: {stock_name}
• 所属行业: {stock_info.get('industry', '未分类')}

RTSI分析结果:"""
        
        rtsi_data = stock_info.get('rtsi', {})
        info_text += f"""
• RTSI指数: {rtsi_data.get('rtsi', 0):.2f}
• 趋势方向: {rtsi_data.get('trend', '未知')}
• 数据可靠性: {rtsi_data.get('confidence', 0):.3f}
• 斜率: {rtsi_data.get('slope', 0):.4f}
• R²值: {rtsi_data.get('r_squared', 0):.3f}

最近评级:
• 最新评级: {rtsi_data.get('recent_score', '未知')}
• 5日变化: {rtsi_data.get('score_change_5d', 'N/A')}
"""
        
        text_widget = tk.Text(content_frame, 
                             font=('Microsoft YaHei', 10),
                             bg='white', fg='black',
                             wrap=tk.WORD, state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 插入内容
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, info_text)
        text_widget.config(state=tk.DISABLED)
        
        # 关闭按钮
        close_btn = tk.Button(content_frame, text="关闭", 
                             command=self.window.destroy,
                             bg='#f0f0f0', relief=tk.RAISED, bd=2)
        close_btn.pack(pady=(10, 0))


if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.title("数据组件测试")
    root.geometry("800x600")
    
    # 创建测试数据
    test_stocks = {
        '600036': {
            'name': '招商银行',
            'industry': '银行',
            'rtsi': {'rtsi': 85.5, 'trend': 'strong_up', 'confidence': 0.89}
        },
        '000001': {
            'name': '平安银行', 
            'industry': '银行',
            'rtsi': {'rtsi': 42.3, 'trend': 'sideways', 'confidence': 0.65}
        }
    }
    
    # 测试股票列表组件
    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    stock_list = StockListWidget(frame)
    stock_list.load_stock_data(test_stocks)
    
    root.mainloop()