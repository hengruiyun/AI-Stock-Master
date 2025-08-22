# -*- coding: utf-8 -*-
"""
from config.i18n import t_gui as _
基础图表组件模块 - matplotlib集成的图表控件

实现:
- TrendChart: 趋势图表组件
- IndustryChart: 行业对比图表
- MarketChart: 市场情绪图表

技术栈: matplotlib + tkinter
设计风格: 专业金融图表
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime, timedelta
import matplotlib.dates as mdates


class BaseChart:
    """图表基类"""
    
    def __init__(self, parent, figsize=(10, 6)):
        self.parent = parent
        self.figure = Figure(figsize=figsize, dpi=100, facecolor='white')
        
        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.figure, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 创建工具栏
        toolbar_frame = tk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 设置专业样式
        self.setup_style()
    
    def setup_style(self):
        """设置图表样式"""
        self.figure.patch.set_facecolor('white')
        
        # 定义颜色方案
        self.colors = {
            'primary': '#0078d4',
            'success': '#107c10',
            'warning': '#ff8c00',
            'danger': '#d13438',
            'info': '#00bcf2',
            'light': '#f3f2f1',
            'dark': '#323130'
        }
        
        # 设置默认字体大小
        self.font_sizes = {
            'title': 14,
            'label': 12,
            'tick': 10,
            'legend': 10
        }
    
    def clear_chart(self):
        """清空图表"""
        self.figure.clear()
        self.canvas.draw()
    
    def save_chart(self, filename):
        """保存图表"""
        self.figure.savefig(filename, dpi=300, bbox_inches='tight')


class TrendChart(BaseChart):
    """趋势图表组件 - 显示股票和行业趋势"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
    def plot_stock_trend(self, stock_data: Dict[str, Any], date_range: List[str] = None):
        """绘制个股趋势图"""
        self.clear_chart()
        
        # 创建子图
        ax = self.figure.add_subplot(111)
        
        if not date_range:
            # 生成示例日期
            end_date = datetime.now()
            date_range = [(end_date - timedelta(days=i)).strftime('%Y%m%d') 
                         for i in range(30, 0, -1)]
        
        # 提取RTSI历史数据 (模拟)
        rtsi_values = self._generate_trend_data(stock_data.get('rtsi', {}).get('rtsi', 50), len(date_range))
        
        # 转换日期格式
        dates = [datetime.strptime(d, '%Y%m%d') for d in date_range]
        
        # 绘制主趋势线
        ax.plot(dates, rtsi_values, 
               color=self.colors['primary'], linewidth=2.5, 
               label=f"RTSI趋势 - {stock_data.get('name', '未知股票')}")
        
        # 添加趋势线
        z = np.polyfit(range(len(rtsi_values)), rtsi_values, 1)
        trend_line = np.poly1d(z)
        trend_values = [trend_line(i) for i in range(len(rtsi_values))]
        
        trend_color = self.colors['success'] if z[0] > 0 else self.colors['danger']
        ax.plot(dates, trend_values, 
               color=trend_color, linestyle='--', alpha=0.7,
               label=f"趋势线 (斜率: {z[0]:.3f})")
        
        # 添加关键水平线
        ax.axhline(y=70, color=self.colors['success'], linestyle=':', alpha=0.5, label='强势线 (70)')
        ax.axhline(y=50, color=self.colors['info'], linestyle=':', alpha=0.5, label='中性线 (50)')
        ax.axhline(y=30, color=self.colors['danger'], linestyle=':', alpha=0.5, label='弱势线 (30)')
        
        # 高亮最新值
        if rtsi_values:
            ax.scatter(dates[-1], rtsi_values[-1], 
                      color=self.colors['warning'], s=100, zorder=5,
                      label=f"最新RTSI: {rtsi_values[-1]:.1f}")
        
        # 设置标题和标签
        ax.set_title(f"个股趋势分析 - {stock_data.get('name', '未知')} ({stock_data.get('code', '')})",
                    fontsize=self.font_sizes['title'], fontweight='bold')
        ax.set_xlabel('日期', fontsize=self.font_sizes['label'])
        ax.set_ylabel('RTSI指数', fontsize=self.font_sizes['label'])
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # 网格和图例
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=self.font_sizes['legend'])
        
        # 调整布局
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_multiple_stocks(self, stocks_data: Dict[str, Dict], top_n: int = 10):
        """绘制多个股票对比"""
        self.clear_chart()
        
        # 筛选前N只股票
        sorted_stocks = sorted(stocks_data.items(), 
                              key=lambda x: x[1].get('rtsi', {}).get('rtsi', 0), 
                              reverse=True)[:top_n]
        
        # 创建子图
        ax = self.figure.add_subplot(111)
        
        # 提取数据
        names = [stock[1].get('name', stock[0]) for stock in sorted_stocks]
        rtsi_values = [stock[1].get('rtsi', {}).get('rtsi', 0) for stock in sorted_stocks]
        
        # 颜色映射
        colors = [self.colors['success'] if v >= 70 else 
                 self.colors['warning'] if v >= 50 else 
                 self.colors['danger'] for v in rtsi_values]
        
        # 绘制水平条形图
        bars = ax.barh(range(len(names)), rtsi_values, color=colors, alpha=0.8)
        
        # 添加数值标签
        for i, (bar, value) in enumerate(zip(bars, rtsi_values)):
            ax.text(value + 1, i, f'{value:.1f}', 
                   va='center', fontsize=self.font_sizes['tick'])
        
        # 设置标签
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels([name[:8] + '...' if len(name) > 8 else name for name in names])
        ax.set_xlabel('RTSI指数', fontsize=self.font_sizes['label'])
        ax.set_title(f'股票RTSI排行榜 (TOP {top_n})', 
                    fontsize=self.font_sizes['title'], fontweight='bold')
        
        # 添加参考线
        ax.axvline(x=70, color=self.colors['success'], linestyle='--', alpha=0.5)
        ax.axvline(x=50, color=self.colors['info'], linestyle='--', alpha=0.5)
        ax.axvline(x=30, color=self.colors['danger'], linestyle='--', alpha=0.5)
        
        # 网格
        ax.grid(True, alpha=0.3, axis='x')
        ax.set_xlim(0, 100)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _generate_trend_data(self, current_value: float, length: int) -> List[float]:
        """生成趋势数据 (模拟历史数据)"""
        # 基于当前值生成历史趋势
        values = []
        base_value = current_value
        
        for i in range(length):
            # 添加随机波动
            noise = np.random.normal(0, 2)
            trend = (i - length/2) * 0.5  # 趋势成分
            value = max(0, min(100, base_value + trend + noise))
            values.append(value)
        
        return values


class IndustryChart(BaseChart):
    """行业对比图表组件"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
    
    def plot_industry_comparison(self, industries_data: Dict[str, Dict]):
        """绘制行业对比图"""
        self.clear_chart()
        
        if not industries_data:
            return
        
        # 按IRSI排序
        sorted_industries = sorted(industries_data.items(),
                                 key=lambda x: x[1].get('irsi', 0),
                                 reverse=True)
        
        # 提取数据
        industry_names = [item[0] for item in sorted_industries]
        irsi_values = [item[1].get('irsi', 0) for item in sorted_industries]
        
        # 创建子图
        ax = self.figure.add_subplot(111)
        
        # 颜色映射
        colors = []
        for value in irsi_values:
            if value > 20:
                colors.append(self.colors['success'])
            elif value > 5:
                colors.append(self.colors['info'])
            elif value > -5:
                colors.append(self.colors['warning'])
            else:
                colors.append(self.colors['danger'])
        
        # 绘制条形图
        bars = ax.bar(range(len(industry_names)), irsi_values, 
                     color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
        
        # 添加数值标签
        for bar, value in zip(bars, irsi_values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -3),
                   f'{value:.1f}', ha='center', va='bottom' if height >= 0 else 'top',
                   fontsize=self.font_sizes['tick'])
        
        # 设置标签
        ax.set_xticks(range(len(industry_names)))
        ax.set_xticklabels([name[:6] + '..' if len(name) > 6 else name 
                           for name in industry_names], rotation=45, ha='right')
        ax.set_ylabel('IRSI指数', fontsize=self.font_sizes['label'])
        ax.set_title('行业相对强度指数 (IRSI) 排行', 
                    fontsize=self.font_sizes['title'], fontweight='bold')
        
        # 添加零轴线
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax.axhline(y=20, color=self.colors['success'], linestyle='--', alpha=0.5, label='强势线 (+20)')
        ax.axhline(y=-20, color=self.colors['danger'], linestyle='--', alpha=0.5, label='弱势线 (-20)')
        
        # 网格和图例
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend(fontsize=self.font_sizes['legend'])
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_industry_heatmap(self, industries_data: Dict[str, Dict]):
        """绘制行业热力图"""
        self.clear_chart()
        
        if not industries_data:
            return
        
        # 创建数据矩阵 (简化版)
        industry_names = list(industries_data.keys())[:20]  # 限制显示数量
        irsi_values = [industries_data[name].get('irsi', 0) for name in industry_names]
        
        # 创建矩阵 (这里简化为1维)
        data_matrix = np.array(irsi_values).reshape(-1, 1)
        
        # 创建子图
        ax = self.figure.add_subplot(111)
        
        # 绘制热力图
        im = ax.imshow(data_matrix, cmap='RdYlGn', aspect='auto', interpolation='nearest')
        
        # 设置标签
        ax.set_yticks(range(len(industry_names)))
        ax.set_yticklabels(industry_names, fontsize=self.font_sizes['tick'])
        ax.set_xticks([])
        ax.set_title('行业热力图', fontsize=self.font_sizes['title'], fontweight='bold')
        
        # 添加颜色条
        cbar = self.figure.colorbar(im, ax=ax)
        cbar.set_label('IRSI指数', fontsize=self.font_sizes['label'])
        
        # 添加数值标注
        for i, value in enumerate(irsi_values):
            ax.text(0, i, f'{value:.1f}', ha='center', va='center',
                   color='white' if abs(value) > 15 else 'black',
                   fontweight='bold')
        
        self.figure.tight_layout()
        self.canvas.draw()


class MarketChart(BaseChart):
    """市场情绪图表组件"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
    
    def plot_market_sentiment(self, market_data: Dict[str, Any]):
        """绘制市场情绪分析图"""
        self.clear_chart()
        
        # 创建子图
        fig = self.figure
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. MSCI仪表盘
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_gauge(ax1, market_data.get('current_msci', 50), 
                        'MSCI指数', 0, 100)
        
        # 2. 市场状态饼图
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_market_state_pie(ax2, market_data)
        
        # 3. 情绪历史趋势
        ax3 = fig.add_subplot(gs[1, :])
        self._plot_sentiment_history(ax3, market_data.get('history', []))
        
        self.canvas.draw()
    
    def _plot_gauge(self, ax, value: float, title: str, min_val: float = 0, max_val: float = 100):
        """绘制仪表盘"""
        # 创建半圆仪表盘
        theta = np.linspace(0, np.pi, 100)
        
        # 背景扇形
        ax.fill_between(theta, 0, 1, alpha=0.3, color=self.colors['light'])
        
        # 值指示扇形
        value_ratio = (value - min_val) / (max_val - min_val)
        value_theta = value_ratio * np.pi
        
        # 颜色映射
        if value >= 70:
            color = self.colors['success']
            zone = "乐观"
        elif value >= 50:
            color = self.colors['info']
            zone = "中性"
        elif value >= 30:
            color = self.colors['warning']
            zone = "谨慎"
        else:
            color = self.colors['danger']
            zone = "悲观"
        
        # 绘制扇形
        theta_fill = np.linspace(0, value_theta, 50)
        ax.fill_between(theta_fill, 0, 1, alpha=0.8, color=color)
        
        # 指针
        ax.arrow(value_theta, 0, 0, 0.8, head_width=0.05, head_length=0.1, 
                fc=self.colors['dark'], ec=self.colors['dark'])
        
        # 设置样式
        ax.set_xlim(0, np.pi)
        ax.set_ylim(0, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        
        # 添加标签
        ax.text(np.pi/2, 1.1, title, ha='center', va='bottom', 
               fontsize=self.font_sizes['label'], fontweight='bold')
        ax.text(np.pi/2, 0.5, f'{value:.1f}', ha='center', va='center',
               fontsize=20, fontweight='bold', color=color)
        ax.text(np.pi/2, 0.3, zone, ha='center', va='center',
               fontsize=self.font_sizes['tick'], color=color)
    
    def _plot_market_state_pie(self, ax, market_data: Dict[str, Any]):
        """绘制市场状态饼图"""
        states = ['看多', '中性', '看空', '无评级']
        sizes = [8.8, 15.7, 14.7, 60.8]  # 示例数据
        colors = [self.colors['success'], self.colors['info'], 
                 self.colors['danger'], self.colors['light']]
        
        # 绘制饼图
        wedges, texts, autotexts = ax.pie(sizes, labels=states, colors=colors,
                                          autopct='%1.1f%%', startangle=90)
        
        # 设置文本样式
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('市场情绪分布', fontsize=self.font_sizes['label'], fontweight='bold')
    
    def _plot_sentiment_history(self, ax, history_data: List[Dict]):
        """绘制情绪历史趋势"""
        if not history_data:
            # 生成示例数据
            dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') 
                    for i in range(20, 0, -1)]
            msci_values = [45 + 10*np.sin(i/3) + np.random.normal(0, 3) 
                          for i in range(20)]
        else:
            dates = [item.get('date', '') for item in history_data]
            msci_values = [item.get('msci', 50) for item in history_data]
        
        # 绘制趋势线
        ax.plot(dates, msci_values, color=self.colors['primary'], 
               linewidth=2, marker='o', markersize=4)
        
        # 添加区域填充
        ax.fill_between(dates, msci_values, alpha=0.3, color=self.colors['primary'])
        
        # 添加参考线
        ax.axhline(y=70, color=self.colors['success'], linestyle='--', alpha=0.5, label='')
        ax.axhline(y=50, color=self.colors['info'], linestyle='--', alpha=0.5, label='')
        ax.axhline(y=30, color=self.colors['danger'], linestyle='--', alpha=0.5, label='')
        
        # 设置标签
        ax.set_xlabel('日期', fontsize=self.font_sizes['label'])
        ax.set_ylabel('MSCI指数', fontsize=self.font_sizes['label'])
        ax.set_title('市场情绪历史趋势', fontsize=self.font_sizes['label'], fontweight='bold')
        
        # 设置x轴标签旋转
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=self.font_sizes['legend'])
    
    def plot_risk_analysis(self, risk_data: Dict[str, Any]):
        """绘制风险分析图"""
        self.clear_chart()
        
        # 创建雷达图
        ax = self.figure.add_subplot(111, projection='polar')
        
        # 风险指标
        categories = ['流动性风险', '信用风险', '市场风险', '操作风险', '政策风险', '系统风险']
        values = [risk_data.get(cat, 50) for cat in categories]  # 默认值50
        
        # 添加第一个点到末尾，形成闭合图形
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, values, color=self.colors['danger'], linewidth=2, label='')
        ax.fill(angles, values, color=self.colors['danger'], alpha=0.25)
        
        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        
        # 添加网格线
        ax.grid(True)
        
        # 添加标题
        ax.set_title('风险分析雷达图', y=1.08, fontsize=self.font_sizes['title'], fontweight='bold')
        
        self.canvas.draw()


if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.title("图表组件测试")
    root.geometry("1000x700")
    
    # 创建笔记本控件测试多个图表
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 测试趋势图
    trend_frame = tk.Frame(notebook)
    notebook.add(trend_frame, text="")
    
    trend_chart = TrendChart(trend_frame)
    test_stock = {
        'code': '600036',
        'name': '招商银行',
        'rtsi': {'rtsi': 85.5, 'trend': 'strong_up'}
    }
    trend_chart.plot_stock_trend(test_stock)
    
    # 测试行业图
    industry_frame = tk.Frame(notebook)
    notebook.add(industry_frame, text="")
    
    industry_chart = IndustryChart(industry_frame)
    test_industries = {
        '半导体': {'irsi': 25.3},
        '软件开发': {'irsi': 18.7},
        '银行': {'irsi': -12.4},
        '房地产': {'irsi': -25.1}
    }
    industry_chart.plot_industry_comparison(test_industries)
    
    # 测试市场图
    market_frame = tk.Frame(notebook)
    notebook.add(market_frame, text="")
    
    market_chart = MarketChart(market_frame)
    test_market = {
        'current_msci': 45.6,
        'market_state': 'neutral',
        'history': []
    }
    market_chart.plot_market_sentiment(test_market)
    
    root.mainloop()