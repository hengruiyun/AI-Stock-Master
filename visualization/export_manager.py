# -*- coding: utf-8 -*-
"""
图表导出管理模块

提供多种格式的图表导出功能：
- ChartExporter: 基础图表导出器
- ReportImageGenerator: 报告图像生成器
- InteractiveHTMLExporter: 交互式HTML导出器
"""

import os
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

# 添加项目根目录到Python路径以导入配置
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
import sys
sys.path.insert(0, project_root)

# 导入国际化翻译
from config.gui_i18n import t_gui

try:
    import plotly.graph_objects as go
    import plotly.io as pio
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    # 如果plotly不可用，创建一个备用的go模块
    class MockFigure:
        def __init__(self, *args, **kwargs):
            pass
        
        def write_image(self, *args, **kwargs):
            raise ImportError(t_gui('plotly_not_installed_error'))
        
        def to_json(self):
            return t_gui('plotly_not_installed_json')
    
    class MockGo:
        Figure = MockFigure
    
    class MockPio:
        @staticmethod
        def to_html(*args, **kwargs):
            return t_gui('plotly_not_installed_div')
    
    go = MockGo()
    pio = MockPio()
    pyo = None
    PLOTLY_AVAILABLE = False
    print(": Plotly")

import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("ReportLab未安装，PDF导出功能不可用")

logger = logging.getLogger(__name__)

class ChartExporter:
    """基础图表导出器"""
    
    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 支持的导出格式
        self.supported_formats = {
            'html': self._export_html,
            'png': self._export_png,
            'jpg': self._export_jpg,
            'pdf': self._export_pdf,
            'svg': self._export_svg,
            'json': self._export_json
        }
        
        # 默认配置
        self.default_config = {
            'width': 1200,
            'height': 800,
            'scale': 2,  # 高分辨率
            'engine': 'kaleido'  # plotly图像导出引擎
        }
    
    def export_chart(self, fig: go.Figure, filename: str, 
                    format: str = 'html', **kwargs) -> str:
        """
        导出单个图表
        
        Args:
            fig: plotly图表对象
            filename: 输出文件名(不含扩展名)
            format: 导出格式
            **kwargs: 导出配置参数
            
        Returns:
            导出文件的完整路径
        """
        if format not in self.supported_formats:
            raise ValueError(f"不支持的导出格式: {format}")
        
        config = {**self.default_config, **kwargs}
        export_func = self.supported_formats[format]
        
        return export_func(fig, filename, config)
    
    def export_collection(self, charts: Dict[str, go.Figure], 
                         output_prefix: str = "chart_collection",
                         formats: List[str] = ['html', 'png']) -> Dict[str, List[str]]:
        """
        批量导出图表集合
        
        Args:
            charts: 图表字典 {名称: 图表对象}
            output_prefix: 输出文件前缀
            formats: 导出格式列表
            
        Returns:
            导出文件路径字典 {格式: [文件路径列表]}
        """
        exported_files = {fmt: [] for fmt in formats}
        
        for chart_name, fig in charts.items():
            filename = f"{output_prefix}_{chart_name}"
            
            for fmt in formats:
                try:
                    filepath = self.export_chart(fig, filename, fmt)
                    exported_files[fmt].append(filepath)
                    logger.info(f"导出成功: {filepath}")
                except Exception as e:
                    logger.error(f"导出失败 {chart_name}.{fmt}: {e}")
        
        return exported_files
    
    def _export_html(self, fig: go.Figure, filename: str, config: Dict[str, Any]) -> str:
        """导出HTML格式"""
        output_path = self.output_dir / f"{filename}.html"
        
        # 创建完整的HTML页面
        html_content = self._create_html_page(fig, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_path)
    
    def _export_png(self, fig: go.Figure, filename: str, config: Dict[str, Any]) -> str:
        """导出PNG格式"""
        output_path = self.output_dir / f"{filename}.png"
        
        fig.write_image(
            str(output_path),
            format='png',
            width=config['width'],
            height=config['height'],
            scale=config['scale'],
            engine=config['engine']
        )
        
        return str(output_path)
    
    def _export_jpg(self, fig: go.Figure, filename: str, config: Dict[str, Any]) -> str:
        """导出JPG格式"""
        output_path = self.output_dir / f"{filename}.jpg"
        
        fig.write_image(
            str(output_path),
            format='jpg',
            width=config['width'],
            height=config['height'],
            scale=config['scale'],
            engine=config['engine']
        )
        
        return str(output_path)
    
    def _export_pdf(self, fig: go.Figure, filename: str, config: Dict[str, Any]) -> str:
        """导出PDF格式"""
        output_path = self.output_dir / f"{filename}.pdf"
        
        fig.write_image(
            str(output_path),
            format='pdf',
            width=config['width'],
            height=config['height'],
            scale=config['scale'],
            engine=config['engine']
        )
        
        return str(output_path)
    
    def _export_svg(self, fig: go.Figure, filename: str, config: Dict[str, Any]) -> str:
        """导出SVG格式"""
        output_path = self.output_dir / f"{filename}.svg"
        
        fig.write_image(
            str(output_path),
            format='svg',
            width=config['width'],
            height=config['height'],
            engine=config['engine']
        )
        
        return str(output_path)
    
    def _export_json(self, fig: go.Figure, filename: str, config: Dict[str, Any]) -> str:
        """导出JSON格式"""
        output_path = self.output_dir / f"{filename}.json"
        
        fig_json = fig.to_json()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fig_json)
        
        return str(output_path)
    
    def _create_html_page(self, fig: go.Figure, title: str) -> str:
        """创建完整的HTML页面"""
        
        # 获取图表的HTML代码
        chart_html = pio.to_html(fig, include_plotlyjs='cdn', div_id=f"chart_{title}")
        
        # 创建完整的HTML页面
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI股票大师 - {title}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #6c757d;
            font-size: 12px;
        }}
        .export-info {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .export-info strong {{
            color: #2E86AB;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI股票大师</h1>
        <p>图表报告 - {title}</p>
    </div>
    
    <div class="export-info">
        <strong>导出时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <strong>图表类型:</strong> {title}<br>
        <strong>数据来源:</strong> AI股票大师
    </div>
    
    <div class="chart-container">
        {chart_html}
    </div>
    
    <div class="footer">
        <p>© 2025 AI股票大师 | 本报告仅供参考，投资有风险，决策需谨慎</p>
    </div>
</body>
</html>
        """
        
        return html_template

class ReportImageGenerator:
    """报告图像生成器"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 尝试加载字体
        self.font_paths = [
            'C:/Windows/Fonts/msyh.ttc',  # 微软雅黑
            'C:/Windows/Fonts/simhei.ttf',  # 黑体
            'C:/Windows/Fonts/arial.ttf'   # Arial
        ]
        self.font = self._load_font()
    
    def _load_font(self, size: int = 20) -> ImageFont.FreeTypeFont:
        """加载字体"""
        for font_path in self.font_paths:
            try:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
            except:
                continue
        
        # 如果都加载失败，使用默认字体
        try:
            return ImageFont.load_default()
        except:
            return None
    
    def create_summary_image(self, charts_data: Dict[str, Any], 
                           title: str = "AI股票分析报告") -> str:
        """
        创建汇总图像
        
        Args:
            charts_data: 图表数据字典
            title: 报告标题
            
        Returns:
            生成的图像文件路径
        """
        # 创建画布
        width, height = 1200, 1600
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # 绘制标题
        title_font = self._load_font(36)
        if title_font:
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            draw.text((title_x, 30), title, fill='#2E86AB', font=title_font)
        
        # 绘制时间戳
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_font = self._load_font(14)
        if time_font:
            time_text = f"生成时间: {timestamp}"
            time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
            time_width = time_bbox[2] - time_bbox[0]
            time_x = (width - time_width) // 2
            draw.text((time_x, 80), time_text, fill='#6c757d', font=time_font)
        
        # 绘制分割线
        draw.line([(50, 120), (width-50, 120)], fill='#dee2e6', width=2)
        
        # 绘制内容区域
        content_y = 150
        section_font = self._load_font(18)
        text_font = self._load_font(14)
        
        # 示例数据展示
        sections = [
            "数据 数据概览",
            "上涨 趋势分析", 
            "行业 行业轮动",
            "💹 市场情绪",
            "快速 系统性能"
        ]
        
        for i, section in enumerate(sections):
            # 绘制区域标题
            if section_font:
                draw.text((60, content_y), section, fill='#2E86AB', font=section_font)
            
            # 绘制区域内容框
            box_y = content_y + 35
            box_height = 180
            
            # 绘制边框
            draw.rectangle(
                [(60, box_y), (width-60, box_y + box_height)], 
                outline='#dee2e6', 
                width=1
            )
            
            # 绘制渐变背景效果 (简化版)
            for j in range(box_height):
                alpha = int(255 * (1 - j / box_height * 0.1))
                color = (248, 249, 250, alpha)
                try:
                    draw.line(
                        [(61, box_y + j), (width-61, box_y + j)], 
                        fill=color
                    )
                except:
                    pass
            
            # 添加示例文本
            if text_font:
                status_texts = [
                    "数据加载成功",
                    "算法计算完成", 
                    "图表生成成功",
                    "详细信息请查看完整报告"
                ]
                
                for k, text in enumerate(status_texts):
                    draw.text(
                        (80, box_y + 20 + k * 25), 
                        text, 
                        fill='#495057', 
                        font=text_font
                    )
            
            content_y += box_height + 80
        
        # 绘制页脚
        footer_y = height - 100
        draw.line([(50, footer_y), (width-50, footer_y)], fill='#dee2e6', width=1)
        
        if text_font:
            footer_text = "2025 AI"
            footer_bbox = draw.textbbox((0, 0), footer_text, font=text_font)
            footer_width = footer_bbox[2] - footer_bbox[0]
            footer_x = (width - footer_width) // 2
            draw.text((footer_x, footer_y + 20), footer_text, fill='#6c757d', font=text_font)
        
        # 保存图像
        output_path = self.output_dir / f"summary_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(output_path, 'PNG', quality=95)
        
        logger.info(f"汇总图像已生成: {output_path}")
        return str(output_path)
    
    def create_chart_thumbnail(self, chart_path: str, 
                             size: Tuple[int, int] = (300, 200)) -> str:
        """
        创建图表缩略图
        
        Args:
            chart_path: 原图表文件路径
            size: 缩略图尺寸
            
        Returns:
            缩略图文件路径
        """
        try:
            # 打开原图像
            original = Image.open(chart_path)
            
            # 创建缩略图
            thumbnail = original.copy()
            thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 创建白色背景
            background = Image.new('RGB', size, 'white')
            
            # 居中放置缩略图
            thumb_width, thumb_height = thumbnail.size
            x = (size[0] - thumb_width) // 2
            y = (size[1] - thumb_height) // 2
            
            background.paste(thumbnail, (x, y))
            
            # 保存缩略图
            path = Path(chart_path)
            thumbnail_path = path.parent / f"{path.stem}_thumb{path.suffix}"
            background.save(thumbnail_path, 'PNG', quality=90)
            
            return str(thumbnail_path)
            
        except Exception as e:
            logger.error(f"创建缩略图失败: {e}")
            return chart_path

class InteractiveHTMLExporter:
    """交互式HTML导出器"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 创建静态资源目录
        self.assets_dir = self.output_dir / "assets"
        self.assets_dir.mkdir(exist_ok=True)
    
    def _get_html_lang(self):
        """获取HTML语言标识"""
        try:
            from config.gui_i18n import get_system_language
            return "en" if get_system_language() == 'en' else "zh-CN"
        except:
            return "zh-CN"
    
    def export_dashboard(self, charts: Dict[str, go.Figure], 
                        title: str = "AI股票分析仪表板",
                        template: str = "professional") -> str:
        """
        导出交互式仪表板
        
        Args:
            charts: 图表字典
            title: 仪表板标题
            template: 样式模板
            
        Returns:
            HTML文件路径
        """
        
        # 生成HTML内容
        html_content = self._create_dashboard_html(charts, title, template)
        
        # 保存文件
        output_path = self.output_dir / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"交互式仪表板已生成: {output_path}")
        return str(output_path)
    
    def _create_dashboard_html(self, charts: Dict[str, go.Figure], 
                              title: str, template: str) -> str:
        """创建仪表板HTML"""
        
        # 获取图表HTML代码
        chart_htmls = {}
        for name, fig in charts.items():
            chart_htmls[name] = pio.to_html(
                fig, 
                include_plotlyjs=False, 
                div_id=f"chart_{name}",
                config={'displayModeBar': True}
            )
        
        # 选择样式模板
        if template == "dark":
            css_theme = self._get_dark_theme_css()
        elif template == "classic":
            css_theme = self._get_classic_theme_css()
        else:
            css_theme = self._get_professional_theme_css()
        
        # 创建完整HTML
        html_template = f"""
<!DOCTYPE html>
<html lang="{self._get_html_lang()}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        {css_theme}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <header class="dashboard-header">
            <h1>{title}</h1>
            <div class="header-info">
                <span class="timestamp">更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                <button class="refresh-btn" onclick="refreshDashboard()">刷新 刷新</button>
            </div>
        </header>
        
        <nav class="dashboard-nav">
            <ul>
                {self._generate_nav_items(chart_htmls.keys())}
            </ul>
        </nav>
        
        <main class="dashboard-main">
            <div class="chart-grid">
                {self._generate_chart_grid(chart_htmls)}
            </div>
        </main>
        
        <footer class="dashboard-footer">
            <p>© 2025 AI股票大师 | 数据更新频率: 实时 | 建议使用Chrome浏览器获得最佳体验</p>
        </footer>
    </div>
    
    <script>
        {self._generate_dashboard_js()}
    </script>
</body>
</html>
        """
        
        return html_template
    
    def _generate_nav_items(self, chart_names: List[str]) -> str:
        """生成导航项目"""
        nav_mapping = {
            'trend': ('上涨', '趋势分析'),
            'heatmap': ('热门', '行业热力图'), 
            'scatter': ('💹', '市场情绪'),
            'dashboard': ('快速', '性能监控')
        }
        
        nav_html = ""
        for name in chart_names:
            icon, label = nav_mapping.get(name, ('数据', name.title()))
            nav_html += f'<li><a href="#chart_{name}" onclick="showChart(\'{name}\')">{icon} {label}</a></li>\n'
        
        return nav_html
    
    def _generate_chart_grid(self, chart_htmls: Dict[str, str]) -> str:
        """生成图表网格"""
        grid_html = ""
        
        for name, html in chart_htmls.items():
            grid_html += f"""
            <div class="chart-panel" id="panel_{name}">
                <div class="chart-header">
                    <h3>{name.title()}</h3>
                    <div class="chart-controls">
                        <button onclick="fullscreenChart('{name}')">⛶ 全屏</button>
                        <button onclick="exportChart('{name}')">保存 导出</button>
                    </div>
                </div>
                <div class="chart-content">
                    {html}
                </div>
            </div>
            """
        
        return grid_html
    
    def _generate_dashboard_js(self) -> str:
        """生成仪表板JavaScript"""
        return """
        function showChart(chartName) {
            // 隐藏所有图表面板
            const panels = document.querySelectorAll('.chart-panel');
            panels.forEach(panel => {
                panel.style.display = 'none';
            });
            
            // 显示选中的图表面板
            const targetPanel = document.getElementById('panel_' + chartName);
            if (targetPanel) {
                targetPanel.style.display = 'block';
            }
            
            // 更新导航状态
            const navLinks = document.querySelectorAll('.dashboard-nav a');
            navLinks.forEach(link => {
                link.classList.remove('active');
            });
            event.target.classList.add('active');
        }
        
        function fullscreenChart(chartName) {
            const chartDiv = document.getElementById('chart_' + chartName);
            if (chartDiv) {
                if (chartDiv.requestFullscreen) {
                    chartDiv.requestFullscreen();
                } else if (chartDiv.webkitRequestFullscreen) {
                    chartDiv.webkitRequestFullscreen();
                } else if (chartDiv.msRequestFullscreen) {
                    chartDiv.msRequestFullscreen();
                }
            }
        }
        
        function exportChart(chartName) {
            const chartDiv = document.getElementById('chart_' + chartName);
            if (chartDiv && window.Plotly) {
                Plotly.downloadImage(chartDiv, {
                    format: 'png',
                    width: 1200,
                    height: 800,
                    filename: 'chart_' + chartName + '_' + new Date().getTime()
                });
            }
        }
        
        function refreshDashboard() {
            location.reload();
        }
        
        // 初始化显示第一个图表
        document.addEventListener('DOMContentLoaded', function() {
            const firstChart = document.querySelector('.chart-panel');
            if (firstChart) {
                const chartName = firstChart.id.replace('panel_', '');
                showChart(chartName);
            }
        });
        """
    
    def _get_professional_theme_css(self) -> str:
        """获取专业主题CSS"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Microsoft YaHei', 'Segoe UI', 'Arial', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #2c3e50;
            min-height: 100vh;
        }
        
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .dashboard-header {
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .dashboard-header h1 {
            font-size: 2.5em;
            font-weight: 300;
            margin: 0;
        }
        
        .header-info {
            text-align: right;
        }
        
        .timestamp {
            display: block;
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }
        
        .refresh-btn {
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .refresh-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .dashboard-nav {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .dashboard-nav ul {
            list-style: none;
            display: flex;
            flex-wrap: wrap;
        }
        
        .dashboard-nav li {
            flex: 1;
        }
        
        .dashboard-nav a {
            display: block;
            padding: 15px 20px;
            text-decoration: none;
            color: #2c3e50;
            transition: all 0.3s;
            text-align: center;
            border-right: 1px solid #f1f3f4;
        }
        
        .dashboard-nav a:hover,
        .dashboard-nav a.active {
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
        }
        
        .dashboard-main {
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            padding: 30px;
            margin-bottom: 20px;
            min-height: 600px;
        }
        
        .chart-panel {
            display: none;
        }
        
        .chart-panel:first-child {
            display: block;
        }
        
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f1f3f4;
        }
        
        .chart-header h3 {
            color: #2E86AB;
            font-size: 1.5em;
            font-weight: 400;
        }
        
        .chart-controls button {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            color: #495057;
            padding: 8px 12px;
            margin-left: 10px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .chart-controls button:hover {
            background: #2E86AB;
            color: white;
            border-color: #2E86AB;
        }
        
        .chart-content {
            min-height: 500px;
        }
        
        .dashboard-footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .dashboard-header {
                flex-direction: column;
                text-align: center;
            }
            
            .dashboard-nav ul {
                flex-direction: column;
            }
            
            .dashboard-nav a {
                border-right: none;
                border-bottom: 1px solid #f1f3f4;
            }
            
            .chart-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .chart-controls {
                margin-top: 10px;
            }
        }
        """
    
    def _get_dark_theme_css(self) -> str:
        """获取深色主题CSS"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Microsoft YaHei', 'Segoe UI', 'Arial', sans-serif;
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: #ecf0f1;
            min-height: 100vh;
        }
        
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .dashboard-header {
            background: linear-gradient(135deg, #00D4AA 0%, #FF6B6B 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        
        .dashboard-nav {
            background: #34495e;
            border-radius: 10px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }
        
        .dashboard-nav a {
            color: #ecf0f1;
            border-right: 1px solid #2c3e50;
        }
        
        .dashboard-nav a:hover,
        .dashboard-nav a.active {
            background: linear-gradient(135deg, #00D4AA 0%, #FF6B6B 100%);
        }
        
        .dashboard-main {
            background: #34495e;
            border-radius: 15px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            padding: 30px;
            margin-bottom: 20px;
        }
        
        .chart-header h3 {
            color: #00D4AA;
        }
        
        .chart-controls button {
            background: #2c3e50;
            border: 1px solid #34495e;
            color: #ecf0f1;
        }
        
        .chart-controls button:hover {
            background: #00D4AA;
            border-color: #00D4AA;
        }
        """
    
    def _get_classic_theme_css(self) -> str:
        """获取经典主题CSS"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Times New Roman', serif;
            background: #ffffff;
            color: #000000;
            min-height: 100vh;
        }
        
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .dashboard-header {
            background: #1f77b4;
            color: white;
            padding: 30px;
            border: 2px solid #333;
            margin-bottom: 20px;
        }
        
        .dashboard-nav {
            background: #f8f9fa;
            border: 2px solid #333;
            margin-bottom: 20px;
        }
        
        .dashboard-nav a {
            color: #000;
            border-right: 1px solid #333;
        }
        
        .dashboard-nav a:hover,
        .dashboard-nav a.active {
            background: #1f77b4;
            color: white;
        }
        
        .dashboard-main {
            background: white;
            border: 2px solid #333;
            padding: 30px;
            margin-bottom: 20px;
        }
        """

# 便捷函数
def export_chart_quick(fig: go.Figure, filename: str, format: str = 'html') -> str:
    """快速导出图表的便捷函数"""
    exporter = ChartExporter()
    return exporter.export_chart(fig, filename, format)

def export_dashboard_quick(charts: Dict[str, go.Figure], 
                          title: str = "AI股票分析仪表板") -> str:
    """快速导出仪表板的便捷函数"""
    exporter = InteractiveHTMLExporter()
    return exporter.export_dashboard(charts, title)

def create_report_summary(charts_data: Dict[str, Any]) -> str:
    """快速创建报告汇总的便捷函数"""
    generator = ReportImageGenerator()
    return generator.create_summary_image(charts_data)