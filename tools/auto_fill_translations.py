#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动补充翻译脚本

此脚本会根据键名和上下文自动补充缺少的翻译。
"""

import os
import re
import sys
import json
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent

# 智能翻译映射
SMART_TRANSLATIONS = {
    # 基础词汇
    "close": {"zh": "关闭", "en": "Close"},
    "good": {"zh": "良好", "en": "Good"},
    "error": {"zh": "错误", "en": "Error"},
    "success": {"zh": "成功", "en": "Success"},
    "failed": {"zh": "失败", "en": "Failed"},
    "loading": {"zh": "加载中", "en": "Loading"},
    "complete": {"zh": "完成", "en": "Complete"},
    "cancel": {"zh": "取消", "en": "Cancel"},
    "confirm": {"zh": "确认", "en": "Confirm"},
    "warning": {"zh": "警告", "en": "Warning"},
    "info": {"zh": "信息", "en": "Information"},
    "about": {"zh": "关于", "en": "About"},
    "help": {"zh": "帮助", "en": "Help"},
    "settings": {"zh": "设置", "en": "Settings"},
    "export": {"zh": "导出", "en": "Export"},
    "import": {"zh": "导入", "en": "Import"},
    "open": {"zh": "打开", "en": "Open"},
    "save": {"zh": "保存", "en": "Save"},
    "search": {"zh": "搜索", "en": "Search"},
    "filter": {"zh": "筛选", "en": "Filter"},
    "sort": {"zh": "排序", "en": "Sort"},
    "ranking": {"zh": "排名", "en": "Ranking"},
    "index": {"zh": "指数", "en": "Index"},
    "analysis": {"zh": "分析", "en": "Analysis"},
    "report": {"zh": "报告", "en": "Report"},
    "data": {"zh": "数据", "en": "Data"},
    "chart": {"zh": "图表", "en": "Chart"},
    "trend": {"zh": "趋势", "en": "Trend"},
    "market": {"zh": "市场", "en": "Market"},
    "stock": {"zh": "股票", "en": "Stock"},
    "industry": {"zh": "行业", "en": "Industry"},
    "performance": {"zh": "表现", "en": "Performance"},
    "risk": {"zh": "风险", "en": "Risk"},
    "quality": {"zh": "质量", "en": "Quality"},
    "version": {"zh": "版本", "en": "Version"},
    "title": {"zh": "标题", "en": "Title"},
    "name": {"zh": "名称", "en": "Name"},
    "code": {"zh": "代码", "en": "Code"},
    "value": {"zh": "值", "en": "Value"},
    "date": {"zh": "日期", "en": "Date"},
    "time": {"zh": "时间", "en": "Time"},
    "price": {"zh": "价格", "en": "Price"},
    "volume": {"zh": "成交量", "en": "Volume"},
    "change": {"zh": "变化", "en": "Change"},
    "percent": {"zh": "百分比", "en": "Percent"},
    "high": {"zh": "高", "en": "High"},
    "low": {"zh": "低", "en": "Low"},
    "medium": {"zh": "中等", "en": "Medium"},
    "strong": {"zh": "强", "en": "Strong"},
    "weak": {"zh": "弱", "en": "Weak"},
    "neutral": {"zh": "中性", "en": "Neutral"},
    "bull": {"zh": "牛市", "en": "Bull"},
    "bear": {"zh": "熊市", "en": "Bear"},
    "uptrend": {"zh": "上升趋势", "en": "Uptrend"},
    "downtrend": {"zh": "下降趋势", "en": "Downtrend"},
    "volatility": {"zh": "波动性", "en": "Volatility"},
    "optimistic": {"zh": "乐观", "en": "Optimistic"},
    "pessimistic": {"zh": "悲观", "en": "Pessimistic"},
    "balanced": {"zh": "平衡", "en": "Balanced"},
    "active": {"zh": "活跃", "en": "Active"},
    "inactive": {"zh": "不活跃", "en": "Inactive"},
    "enable": {"zh": "启用", "en": "Enable"},
    "disable": {"zh": "禁用", "en": "Disable"},
    "cache": {"zh": "缓存", "en": "Cache"},
    "multithreading": {"zh": "多线程", "en": "Multithreading"},
    "configuration": {"zh": "配置", "en": "Configuration"},
    "validation": {"zh": "验证", "en": "Validation"},
    "monitor": {"zh": "监控", "en": "Monitor"},
    "visualization": {"zh": "可视化", "en": "Visualization"},
    "advanced": {"zh": "高级", "en": "Advanced"},
    "professional": {"zh": "专业", "en": "Professional"},
    "intelligent": {"zh": "智能", "en": "Intelligent"},
    "comprehensive": {"zh": "综合", "en": "Comprehensive"},
    "historical": {"zh": "历史", "en": "Historical"},
    "realtime": {"zh": "实时", "en": "Realtime"},
    "algorithm": {"zh": "算法", "en": "Algorithm"},
    "engine": {"zh": "引擎", "en": "Engine"},
    "system": {"zh": "系统", "en": "System"},
    "platform": {"zh": "平台", "en": "Platform"},
    "interface": {"zh": "界面", "en": "Interface"},
    "classic": {"zh": "经典", "en": "Classic"},
    "modern": {"zh": "现代", "en": "Modern"},
    "dark": {"zh": "深色", "en": "Dark"},
    "light": {"zh": "浅色", "en": "Light"},
    "theme": {"zh": "主题", "en": "Theme"},
    "style": {"zh": "样式", "en": "Style"},
    "layout": {"zh": "布局", "en": "Layout"},
    "window": {"zh": "窗口", "en": "Window"},
    "dialog": {"zh": "对话框", "en": "Dialog"},
    "menu": {"zh": "菜单", "en": "Menu"},
    "button": {"zh": "按钮", "en": "Button"},
    "label": {"zh": "标签", "en": "Label"},
    "text": {"zh": "文本", "en": "Text"},
    "file": {"zh": "文件", "en": "File"},
    "folder": {"zh": "文件夹", "en": "Folder"},
    "path": {"zh": "路径", "en": "Path"},
    "directory": {"zh": "目录", "en": "Directory"},
    "excel": {"zh": "Excel", "en": "Excel"},
    "csv": {"zh": "CSV", "en": "CSV"},
    "json": {"zh": "JSON", "en": "JSON"},
    "html": {"zh": "HTML", "en": "HTML"},
    "pdf": {"zh": "PDF", "en": "PDF"},
    "format": {"zh": "格式", "en": "Format"},
    "type": {"zh": "类型", "en": "Type"},
    "category": {"zh": "类别", "en": "Category"},
    "group": {"zh": "组", "en": "Group"},
    "level": {"zh": "级别", "en": "Level"},
    "range": {"zh": "范围", "en": "Range"},
    "limit": {"zh": "限制", "en": "Limit"},
    "threshold": {"zh": "阈值", "en": "Threshold"},
    "weight": {"zh": "权重", "en": "Weight"},
    "factor": {"zh": "因子", "en": "Factor"},
    "parameter": {"zh": "参数", "en": "Parameter"},
    "option": {"zh": "选项", "en": "Option"},
    "preference": {"zh": "偏好", "en": "Preference"},
    "default": {"zh": "默认", "en": "Default"},
    "custom": {"zh": "自定义", "en": "Custom"},
    "auto": {"zh": "自动", "en": "Auto"},
    "manual": {"zh": "手动", "en": "Manual"},
    "update": {"zh": "更新", "en": "Update"},
    "refresh": {"zh": "刷新", "en": "Refresh"},
    "reload": {"zh": "重新加载", "en": "Reload"},
    "reset": {"zh": "重置", "en": "Reset"},
    "clear": {"zh": "清除", "en": "Clear"},
    "delete": {"zh": "删除", "en": "Delete"},
    "remove": {"zh": "移除", "en": "Remove"},
    "add": {"zh": "添加", "en": "Add"},
    "insert": {"zh": "插入", "en": "Insert"},
    "edit": {"zh": "编辑", "en": "Edit"},
    "modify": {"zh": "修改", "en": "Modify"},
    "copy": {"zh": "复制", "en": "Copy"},
    "paste": {"zh": "粘贴", "en": "Paste"},
    "cut": {"zh": "剪切", "en": "Cut"},
    "undo": {"zh": "撤销", "en": "Undo"},
    "redo": {"zh": "重做", "en": "Redo"},
    "select": {"zh": "选择", "en": "Select"},
    "choose": {"zh": "选择", "en": "Choose"},
    "pick": {"zh": "选取", "en": "Pick"},
    "apply": {"zh": "应用", "en": "Apply"},
    "submit": {"zh": "提交", "en": "Submit"},
    "send": {"zh": "发送", "en": "Send"},
    "receive": {"zh": "接收", "en": "Receive"},
    "download": {"zh": "下载", "en": "Download"},
    "upload": {"zh": "上传", "en": "Upload"},
    "sync": {"zh": "同步", "en": "Sync"},
    "backup": {"zh": "备份", "en": "Backup"},
    "restore": {"zh": "恢复", "en": "Restore"},
    "preview": {"zh": "预览", "en": "Preview"},
    "print": {"zh": "打印", "en": "Print"},
    "share": {"zh": "分享", "en": "Share"},
    "publish": {"zh": "发布", "en": "Publish"},
    "generate": {"zh": "生成", "en": "Generate"},
    "create": {"zh": "创建", "en": "Create"},
    "build": {"zh": "构建", "en": "Build"},
    "compile": {"zh": "编译", "en": "Compile"},
    "execute": {"zh": "执行", "en": "Execute"},
    "run": {"zh": "运行", "en": "Run"},
    "start": {"zh": "开始", "en": "Start"},
    "stop": {"zh": "停止", "en": "Stop"},
    "pause": {"zh": "暂停", "en": "Pause"},
    "resume": {"zh": "恢复", "en": "Resume"},
    "continue": {"zh": "继续", "en": "Continue"},
    "finish": {"zh": "完成", "en": "Finish"},
    "exit": {"zh": "退出", "en": "Exit"},
    "quit": {"zh": "退出", "en": "Quit"},
    "close": {"zh": "关闭", "en": "Close"},
    "minimize": {"zh": "最小化", "en": "Minimize"},
    "maximize": {"zh": "最大化", "en": "Maximize"},
    "restore": {"zh": "还原", "en": "Restore"},
    "resize": {"zh": "调整大小", "en": "Resize"},
    "move": {"zh": "移动", "en": "Move"},
    "position": {"zh": "位置", "en": "Position"},
    "size": {"zh": "大小", "en": "Size"},
    "width": {"zh": "宽度", "en": "Width"},
    "height": {"zh": "高度", "en": "Height"},
    "color": {"zh": "颜色", "en": "Color"},
    "font": {"zh": "字体", "en": "Font"},
    "size": {"zh": "大小", "en": "Size"},
    "bold": {"zh": "粗体", "en": "Bold"},
    "italic": {"zh": "斜体", "en": "Italic"},
    "underline": {"zh": "下划线", "en": "Underline"},
    "align": {"zh": "对齐", "en": "Align"},
    "left": {"zh": "左", "en": "Left"},
    "right": {"zh": "右", "en": "Right"},
    "center": {"zh": "中心", "en": "Center"},
    "top": {"zh": "顶部", "en": "Top"},
    "bottom": {"zh": "底部", "en": "Bottom"},
    "middle": {"zh": "中间", "en": "Middle"},
    "first": {"zh": "第一", "en": "First"},
    "last": {"zh": "最后", "en": "Last"},
    "next": {"zh": "下一个", "en": "Next"},
    "previous": {"zh": "上一个", "en": "Previous"},
    "back": {"zh": "返回", "en": "Back"},
    "forward": {"zh": "前进", "en": "Forward"},
    "up": {"zh": "向上", "en": "Up"},
    "down": {"zh": "向下", "en": "Down"},
    "yes": {"zh": "是", "en": "Yes"},
    "no": {"zh": "否", "en": "No"},
    "ok": {"zh": "确定", "en": "OK"},
    "cancel": {"zh": "取消", "en": "Cancel"},
    "retry": {"zh": "重试", "en": "Retry"},
    "ignore": {"zh": "忽略", "en": "Ignore"},
    "skip": {"zh": "跳过", "en": "Skip"},
    "wait": {"zh": "等待", "en": "Wait"},
    "ready": {"zh": "就绪", "en": "Ready"},
    "busy": {"zh": "忙碌", "en": "Busy"},
    "idle": {"zh": "空闲", "en": "Idle"},
    "online": {"zh": "在线", "en": "Online"},
    "offline": {"zh": "离线", "en": "Offline"},
    "connected": {"zh": "已连接", "en": "Connected"},
    "disconnected": {"zh": "已断开", "en": "Disconnected"},
    "available": {"zh": "可用", "en": "Available"},
    "unavailable": {"zh": "不可用", "en": "Unavailable"},
    "enabled": {"zh": "已启用", "en": "Enabled"},
    "disabled": {"zh": "已禁用", "en": "Disabled"},
    "visible": {"zh": "可见", "en": "Visible"},
    "hidden": {"zh": "隐藏", "en": "Hidden"},
    "show": {"zh": "显示", "en": "Show"},
    "hide": {"zh": "隐藏", "en": "Hide"},
    "expand": {"zh": "展开", "en": "Expand"},
    "collapse": {"zh": "折叠", "en": "Collapse"},
    "toggle": {"zh": "切换", "en": "Toggle"},
    "switch": {"zh": "切换", "en": "Switch"},
    "change": {"zh": "更改", "en": "Change"},
    "replace": {"zh": "替换", "en": "Replace"},
    "substitute": {"zh": "替代", "en": "Substitute"},
    "convert": {"zh": "转换", "en": "Convert"},
    "transform": {"zh": "转换", "en": "Transform"},
    "translate": {"zh": "翻译", "en": "Translate"},
    "language": {"zh": "语言", "en": "Language"},
    "locale": {"zh": "区域设置", "en": "Locale"},
    "region": {"zh": "地区", "en": "Region"},
    "country": {"zh": "国家", "en": "Country"},
    "timezone": {"zh": "时区", "en": "Timezone"},
    "currency": {"zh": "货币", "en": "Currency"},
    "unit": {"zh": "单位", "en": "Unit"},
    "measure": {"zh": "度量", "en": "Measure"},
    "scale": {"zh": "比例", "en": "Scale"},
    "ratio": {"zh": "比率", "en": "Ratio"},
    "rate": {"zh": "比率", "en": "Rate"},
    "speed": {"zh": "速度", "en": "Speed"},
    "frequency": {"zh": "频率", "en": "Frequency"},
    "interval": {"zh": "间隔", "en": "Interval"},
    "duration": {"zh": "持续时间", "en": "Duration"},
    "timeout": {"zh": "超时", "en": "Timeout"},
    "delay": {"zh": "延迟", "en": "Delay"},
    "latency": {"zh": "延迟", "en": "Latency"},
    "response": {"zh": "响应", "en": "Response"},
    "request": {"zh": "请求", "en": "Request"},
    "query": {"zh": "查询", "en": "Query"},
    "result": {"zh": "结果", "en": "Result"},
    "output": {"zh": "输出", "en": "Output"},
    "input": {"zh": "输入", "en": "Input"},
    "source": {"zh": "来源", "en": "Source"},
    "target": {"zh": "目标", "en": "Target"},
    "destination": {"zh": "目的地", "en": "Destination"},
    "origin": {"zh": "原点", "en": "Origin"},
    "reference": {"zh": "参考", "en": "Reference"},
    "link": {"zh": "链接", "en": "Link"},
    "url": {"zh": "网址", "en": "URL"},
    "address": {"zh": "地址", "en": "Address"},
    "location": {"zh": "位置", "en": "Location"},
    "place": {"zh": "地点", "en": "Place"},
    "site": {"zh": "站点", "en": "Site"},
    "page": {"zh": "页面", "en": "Page"},
    "section": {"zh": "部分", "en": "Section"},
    "chapter": {"zh": "章节", "en": "Chapter"},
    "part": {"zh": "部分", "en": "Part"},
    "component": {"zh": "组件", "en": "Component"},
    "module": {"zh": "模块", "en": "Module"},
    "plugin": {"zh": "插件", "en": "Plugin"},
    "extension": {"zh": "扩展", "en": "Extension"},
    "addon": {"zh": "附加组件", "en": "Addon"},
    "feature": {"zh": "功能", "en": "Feature"},
    "function": {"zh": "函数", "en": "Function"},
    "method": {"zh": "方法", "en": "Method"},
    "procedure": {"zh": "过程", "en": "Procedure"},
    "process": {"zh": "进程", "en": "Process"},
    "task": {"zh": "任务", "en": "Task"},
    "job": {"zh": "作业", "en": "Job"},
    "work": {"zh": "工作", "en": "Work"},
    "operation": {"zh": "操作", "en": "Operation"},
    "action": {"zh": "动作", "en": "Action"},
    "activity": {"zh": "活动", "en": "Activity"},
    "event": {"zh": "事件", "en": "Event"},
    "trigger": {"zh": "触发器", "en": "Trigger"},
    "handler": {"zh": "处理器", "en": "Handler"},
    "callback": {"zh": "回调", "en": "Callback"},
    "listener": {"zh": "监听器", "en": "Listener"},
    "observer": {"zh": "观察者", "en": "Observer"},
    "watcher": {"zh": "监视器", "en": "Watcher"},
    "tracker": {"zh": "跟踪器", "en": "Tracker"},
    "logger": {"zh": "日志记录器", "en": "Logger"},
    "debugger": {"zh": "调试器", "en": "Debugger"},
    "profiler": {"zh": "分析器", "en": "Profiler"},
    "optimizer": {"zh": "优化器", "en": "Optimizer"},
    "validator": {"zh": "验证器", "en": "Validator"},
    "parser": {"zh": "解析器", "en": "Parser"},
    "compiler": {"zh": "编译器", "en": "Compiler"},
    "interpreter": {"zh": "解释器", "en": "Interpreter"},
    "executor": {"zh": "执行器", "en": "Executor"},
    "scheduler": {"zh": "调度器", "en": "Scheduler"},
    "manager": {"zh": "管理器", "en": "Manager"},
    "controller": {"zh": "控制器", "en": "Controller"},
    "service": {"zh": "服务", "en": "Service"},
    "client": {"zh": "客户端", "en": "Client"},
    "server": {"zh": "服务器", "en": "Server"},
    "host": {"zh": "主机", "en": "Host"},
    "node": {"zh": "节点", "en": "Node"},
    "cluster": {"zh": "集群", "en": "Cluster"},
    "network": {"zh": "网络", "en": "Network"},
    "connection": {"zh": "连接", "en": "Connection"},
    "session": {"zh": "会话", "en": "Session"},
    "transaction": {"zh": "事务", "en": "Transaction"},
    "database": {"zh": "数据库", "en": "Database"},
    "table": {"zh": "表", "en": "Table"},
    "record": {"zh": "记录", "en": "Record"},
    "field": {"zh": "字段", "en": "Field"},
    "column": {"zh": "列", "en": "Column"},
    "row": {"zh": "行", "en": "Row"},
    "cell": {"zh": "单元格", "en": "Cell"},
    "grid": {"zh": "网格", "en": "Grid"},
    "list": {"zh": "列表", "en": "List"},
    "tree": {"zh": "树", "en": "Tree"},
    "graph": {"zh": "图", "en": "Graph"},
    "node": {"zh": "节点", "en": "Node"},
    "edge": {"zh": "边", "en": "Edge"},
    "vertex": {"zh": "顶点", "en": "Vertex"},
    "path": {"zh": "路径", "en": "Path"},
    "route": {"zh": "路由", "en": "Route"},
    "navigation": {"zh": "导航", "en": "Navigation"},
    "breadcrumb": {"zh": "面包屑", "en": "Breadcrumb"},
    "sidebar": {"zh": "侧边栏", "en": "Sidebar"},
    "toolbar": {"zh": "工具栏", "en": "Toolbar"},
    "statusbar": {"zh": "状态栏", "en": "Statusbar"},
    "menubar": {"zh": "菜单栏", "en": "Menubar"},
    "header": {"zh": "头部", "en": "Header"},
    "footer": {"zh": "底部", "en": "Footer"},
    "content": {"zh": "内容", "en": "Content"},
    "body": {"zh": "主体", "en": "Body"},
    "main": {"zh": "主要", "en": "Main"},
    "primary": {"zh": "主要", "en": "Primary"},
    "secondary": {"zh": "次要", "en": "Secondary"},
    "tertiary": {"zh": "第三", "en": "Tertiary"},
    "auxiliary": {"zh": "辅助", "en": "Auxiliary"},
    "optional": {"zh": "可选", "en": "Optional"},
    "required": {"zh": "必需", "en": "Required"},
    "mandatory": {"zh": "强制", "en": "Mandatory"},
    "forbidden": {"zh": "禁止", "en": "Forbidden"},
    "allowed": {"zh": "允许", "en": "Allowed"},
    "permitted": {"zh": "允许", "en": "Permitted"},
    "denied": {"zh": "拒绝", "en": "Denied"},
    "granted": {"zh": "授予", "en": "Granted"},
    "revoked": {"zh": "撤销", "en": "Revoked"},
    "suspended": {"zh": "暂停", "en": "Suspended"},
    "active": {"zh": "活跃", "en": "Active"},
    "inactive": {"zh": "不活跃", "en": "Inactive"},
    "pending": {"zh": "待处理", "en": "Pending"},
    "processing": {"zh": "处理中", "en": "Processing"},
    "completed": {"zh": "已完成", "en": "Completed"},
    "cancelled": {"zh": "已取消", "en": "Cancelled"},
    "failed": {"zh": "失败", "en": "Failed"},
    "successful": {"zh": "成功", "en": "Successful"},
    "partial": {"zh": "部分", "en": "Partial"},
    "full": {"zh": "完整", "en": "Full"},
    "empty": {"zh": "空", "en": "Empty"},
    "null": {"zh": "空值", "en": "Null"},
    "undefined": {"zh": "未定义", "en": "Undefined"},
    "unknown": {"zh": "未知", "en": "Unknown"},
    "invalid": {"zh": "无效", "en": "Invalid"},
    "valid": {"zh": "有效", "en": "Valid"},
    "correct": {"zh": "正确", "en": "Correct"},
    "incorrect": {"zh": "不正确", "en": "Incorrect"},
    "true": {"zh": "真", "en": "True"},
    "false": {"zh": "假", "en": "False"},
    "positive": {"zh": "正", "en": "Positive"},
    "negative": {"zh": "负", "en": "Negative"},
    "zero": {"zh": "零", "en": "Zero"},
    "one": {"zh": "一", "en": "One"},
    "two": {"zh": "二", "en": "Two"},
    "three": {"zh": "三", "en": "Three"},
    "four": {"zh": "四", "en": "Four"},
    "five": {"zh": "五", "en": "Five"},
    "six": {"zh": "六", "en": "Six"},
    "seven": {"zh": "七", "en": "Seven"},
    "eight": {"zh": "八", "en": "Eight"},
    "nine": {"zh": "九", "en": "Nine"},
    "ten": {"zh": "十", "en": "Ten"},
    "hundred": {"zh": "百", "en": "Hundred"},
    "thousand": {"zh": "千", "en": "Thousand"},
    "million": {"zh": "百万", "en": "Million"},
    "billion": {"zh": "十亿", "en": "Billion"},
    "trillion": {"zh": "万亿", "en": "Trillion"},
    "percent": {"zh": "百分比", "en": "Percent"},
    "percentage": {"zh": "百分比", "en": "Percentage"},
    "ratio": {"zh": "比率", "en": "Ratio"},
    "proportion": {"zh": "比例", "en": "Proportion"},
    "fraction": {"zh": "分数", "en": "Fraction"},
    "decimal": {"zh": "小数", "en": "Decimal"},
    "integer": {"zh": "整数", "en": "Integer"},
    "number": {"zh": "数字", "en": "Number"},
    "digit": {"zh": "数位", "en": "Digit"},
    "figure": {"zh": "数字", "en": "Figure"},
    "amount": {"zh": "数量", "en": "Amount"},
    "quantity": {"zh": "数量", "en": "Quantity"},
    "count": {"zh": "计数", "en": "Count"},
    "total": {"zh": "总计", "en": "Total"},
    "sum": {"zh": "总和", "en": "Sum"},
    "average": {"zh": "平均", "en": "Average"},
    "mean": {"zh": "平均值", "en": "Mean"},
    "median": {"zh": "中位数", "en": "Median"},
    "mode": {"zh": "众数", "en": "Mode"},
    "minimum": {"zh": "最小值", "en": "Minimum"},
    "maximum": {"zh": "最大值", "en": "Maximum"},
    "range": {"zh": "范围", "en": "Range"},
    "variance": {"zh": "方差", "en": "Variance"},
    "deviation": {"zh": "偏差", "en": "Deviation"},
    "standard": {"zh": "标准", "en": "Standard"},
    "normal": {"zh": "正常", "en": "Normal"},
    "abnormal": {"zh": "异常", "en": "Abnormal"},
    "unusual": {"zh": "不寻常", "en": "Unusual"},
    "typical": {"zh": "典型", "en": "Typical"},
    "atypical": {"zh": "非典型", "en": "Atypical"},
    "common": {"zh": "常见", "en": "Common"},
    "rare": {"zh": "罕见", "en": "Rare"},
    "frequent": {"zh": "频繁", "en": "Frequent"},
    "infrequent": {"zh": "不频繁", "en": "Infrequent"},
    "regular": {"zh": "规律", "en": "Regular"},
    "irregular": {"zh": "不规律", "en": "Irregular"},
    "consistent": {"zh": "一致", "en": "Consistent"},
    "inconsistent": {"zh": "不一致", "en": "Inconsistent"},
    "stable": {"zh": "稳定", "en": "Stable"},
    "unstable": {"zh": "不稳定", "en": "Unstable"},
    "volatile": {"zh": "波动", "en": "Volatile"},
    "steady": {"zh": "稳定", "en": "Steady"},
    "fluctuating": {"zh": "波动", "en": "Fluctuating"},
    "rising": {"zh": "上升", "en": "Rising"},
    "falling": {"zh": "下降", "en": "Falling"},
    "increasing": {"zh": "增加", "en": "Increasing"},
    "decreasing": {"zh": "减少", "en": "Decreasing"},
    "growing": {"zh": "增长", "en": "Growing"},
    "shrinking": {"zh": "收缩", "en": "Shrinking"},
    "expanding": {"zh": "扩张", "en": "Expanding"},
    "contracting": {"zh": "收缩", "en": "Contracting"},
    "improving": {"zh": "改善", "en": "Improving"},
    "deteriorating": {"zh": "恶化", "en": "Deteriorating"},
    "recovering": {"zh": "恢复", "en": "Recovering"},
    "declining": {"zh": "下降", "en": "Declining"},
    "accelerating": {"zh": "加速", "en": "Accelerating"},
    "decelerating": {"zh": "减速", "en": "Decelerating"},
    "momentum": {"zh": "动量", "en": "Momentum"},
    "velocity": {"zh": "速度", "en": "Velocity"},
    "acceleration": {"zh": "加速度", "en": "Acceleration"},
    "deceleration": {"zh": "减速度", "en": "Deceleration"},
    "direction": {"zh": "方向", "en": "Direction"},
    "orientation": {"zh": "方向", "en": "Orientation"},
    "angle": {"zh": "角度", "en": "Angle"},
    "rotation": {"zh": "旋转", "en": "Rotation"},
    "revolution": {"zh": "旋转", "en": "Revolution"},
    "cycle": {"zh": "周期", "en": "Cycle"},
    "period": {"zh": "周期", "en": "Period"},
    "phase": {"zh": "阶段", "en": "Phase"},
    "stage": {"zh": "阶段", "en": "Stage"},
    "step": {"zh": "步骤", "en": "Step"},
    "sequence": {"zh": "序列", "en": "Sequence"},
    "order": {"zh": "顺序", "en": "Order"},
    "arrangement": {"zh": "排列", "en": "Arrangement"},
    "organization": {"zh": "组织", "en": "Organization"},
    "structure": {"zh": "结构", "en": "Structure"},
    "framework": {"zh": "框架", "en": "Framework"},
    "architecture": {"zh": "架构", "en": "Architecture"},
    "design": {"zh": "设计", "en": "Design"},
    "pattern": {"zh": "模式", "en": "Pattern"},
    "template": {"zh": "模板", "en": "Template"},
    "model": {"zh": "模型", "en": "Model"},
    "prototype": {"zh": "原型", "en": "Prototype"},
    "sample": {"zh": "样本", "en": "Sample"},
    "example": {"zh": "示例", "en": "Example"},
    "instance": {"zh": "实例", "en": "Instance"},
    "case": {"zh": "案例", "en": "Case"},
    "scenario": {"zh": "场景", "en": "Scenario"},
    "situation": {"zh": "情况", "en": "Situation"},
    "condition": {"zh": "条件", "en": "Condition"},
    "state": {"zh": "状态", "en": "State"},
    "status": {"zh": "状态", "en": "Status"},
    "mode": {"zh": "模式", "en": "Mode"},
    "setting": {"zh": "设置", "en": "Setting"},
    "configuration": {"zh": "配置", "en": "Configuration"},
    "setup": {"zh": "设置", "en": "Setup"},
    "installation": {"zh": "安装", "en": "Installation"},
    "deployment": {"zh": "部署", "en": "Deployment"},
    "implementation": {"zh": "实现", "en": "Implementation"},
    "execution": {"zh": "执行", "en": "Execution"},
    "performance": {"zh": "性能", "en": "Performance"},
    "efficiency": {"zh": "效率", "en": "Efficiency"},
    "effectiveness": {"zh": "有效性", "en": "Effectiveness"},
    "productivity": {"zh": "生产力", "en": "Productivity"},
    "throughput": {"zh": "吞吐量", "en": "Throughput"},
    "bandwidth": {"zh": "带宽", "en": "Bandwidth"},
    "capacity": {"zh": "容量", "en": "Capacity"},
    "capability": {"zh": "能力", "en": "Capability"},
    "ability": {"zh": "能力", "en": "Ability"},
    "skill": {"zh": "技能", "en": "Skill"},
    "talent": {"zh": "天赋", "en": "Talent"},
    "expertise": {"zh": "专业知识", "en": "Expertise"},
    "knowledge": {"zh": "知识", "en": "Knowledge"},
    "information": {"zh": "信息", "en": "Information"},
    "data": {"zh": "数据", "en": "Data"},
    "content": {"zh": "内容", "en": "Content"},
    "material": {"zh": "材料", "en": "Material"},
    "resource": {"zh": "资源", "en": "Resource"},
    "asset": {"zh": "资产", "en": "Asset"},
    "property": {"zh": "属性", "en": "Property"},
    "attribute": {"zh": "属性", "en": "Attribute"},
    "characteristic": {"zh": "特征", "en": "Characteristic"},
    "feature": {"zh": "特性", "en": "Feature"},
    "trait": {"zh": "特质", "en": "Trait"},
    "quality": {"zh": "质量", "en": "Quality"},
    "grade": {"zh": "等级", "en": "Grade"},
    "rank": {"zh": "排名", "en": "Rank"},
    "score": {"zh": "分数", "en": "Score"},
    "rating": {"zh": "评级", "en": "Rating"},
    "evaluation": {"zh": "评估", "en": "Evaluation"},
    "assessment": {"zh": "评估", "en": "Assessment"},
    "review": {"zh": "审查", "en": "Review"},
    "audit": {"zh": "审计", "en": "Audit"},
    "inspection": {"zh": "检查", "en": "Inspection"},
    "examination": {"zh": "检查", "en": "Examination"},
    "test": {"zh": "测试", "en": "Test"},
    "trial": {"zh": "试验", "en": "Trial"},
    "experiment": {"zh": "实验", "en": "Experiment"},
    "research": {"zh": "研究", "en": "Research"},
    "study": {"zh": "研究", "en": "Study"},
    "investigation": {"zh": "调查", "en": "Investigation"},
    "survey": {"zh": "调查", "en": "Survey"},
    "poll": {"zh": "投票", "en": "Poll"},
    "vote": {"zh": "投票", "en": "Vote"},
    "election": {"zh": "选举", "en": "Election"},
    "selection": {"zh": "选择", "en": "Selection"},
    "choice": {"zh": "选择", "en": "Choice"},
    "option": {"zh": "选项", "en": "Option"},
    "alternative": {"zh": "替代", "en": "Alternative"},
    "possibility": {"zh": "可能性", "en": "Possibility"},
    "probability": {"zh": "概率", "en": "Probability"},
    "chance": {"zh": "机会", "en": "Chance"},
    "opportunity": {"zh": "机会", "en": "Opportunity"},
    "occasion": {"zh": "场合", "en": "Occasion"},
    "moment": {"zh": "时刻", "en": "Moment"},
    "instant": {"zh": "瞬间", "en": "Instant"},
    "second": {"zh": "秒", "en": "Second"},
    "minute": {"zh": "分钟", "en": "Minute"},
    "hour": {"zh": "小时", "en": "Hour"},
    "day": {"zh": "天", "en": "Day"},
    "week": {"zh": "周", "en": "Week"},
    "month": {"zh": "月", "en": "Month"},
    "year": {"zh": "年", "en": "Year"},
    "decade": {"zh": "十年", "en": "Decade"},
    "century": {"zh": "世纪", "en": "Century"},
    "millennium": {"zh": "千年", "en": "Millennium"},
    "era": {"zh": "时代", "en": "Era"},
    "age": {"zh": "时代", "en": "Age"},
    "epoch": {"zh": "时代", "en": "Epoch"},
    "period": {"zh": "时期", "en": "Period"},
    "term": {"zh": "期限", "en": "Term"},
    "deadline": {"zh": "截止日期", "en": "Deadline"},
    "schedule": {"zh": "计划", "en": "Schedule"},
    "plan": {"zh": "计划", "en": "Plan"},
    "strategy": {"zh": "策略", "en": "Strategy"},
    "tactic": {"zh": "战术", "en": "Tactic"},
    "approach": {"zh": "方法", "en": "Approach"},
    "method": {"zh": "方法", "en": "Method"},
    "technique": {"zh": "技术", "en": "Technique"},
    "technology": {"zh": "技术", "en": "Technology"},
    "tool": {"zh": "工具", "en": "Tool"},
    "instrument": {"zh": "仪器", "en": "Instrument"},
    "device": {"zh": "设备", "en": "Device"},
    "equipment": {"zh": "设备", "en": "Equipment"},
    "machine": {"zh": "机器", "en": "Machine"},
    "apparatus": {"zh": "装置", "en": "Apparatus"},
    "mechanism": {"zh": "机制", "en": "Mechanism"},
    "system": {"zh": "系统", "en": "System"},
    "platform": {"zh": "平台", "en": "Platform"},
    "framework": {"zh": "框架", "en": "Framework"},
    "infrastructure": {"zh": "基础设施", "en": "Infrastructure"},
    "foundation": {"zh": "基础", "en": "Foundation"},
    "base": {"zh": "基础", "en": "Base"},
    "basis": {"zh": "基础", "en": "Basis"},
    "ground": {"zh": "基础", "en": "Ground"},
    "root": {"zh": "根", "en": "Root"},
    "origin": {"zh": "起源", "en": "Origin"},
    "source": {"zh": "来源", "en": "Source"},
    "beginning": {"zh": "开始", "en": "Beginning"},
    "start": {"zh": "开始", "en": "Start"},
    "end": {"zh": "结束", "en": "End"},
    "finish": {"zh": "完成", "en": "Finish"},
    "conclusion": {"zh": "结论", "en": "Conclusion"},
    "result": {"zh": "结果", "en": "Result"},
    "outcome": {"zh": "结果", "en": "Outcome"},
    "consequence": {"zh": "后果", "en": "Consequence"},
    "effect": {"zh": "效果", "en": "Effect"},
    "impact": {"zh": "影响", "en": "Impact"},
    "influence": {"zh": "影响", "en": "Influence"},
    "factor": {"zh": "因素", "en": "Factor"},
    "element": {"zh": "元素", "en": "Element"},
    "component": {"zh": "组件", "en": "Component"},
    "part": {"zh": "部分", "en": "Part"},
    "piece": {"zh": "片段", "en": "Piece"},
    "fragment": {"zh": "片段", "en": "Fragment"},
    "segment": {"zh": "段", "en": "Segment"},
    "section": {"zh": "部分", "en": "Section"},
    "division": {"zh": "分割", "en": "Division"}
}

def smart_translate_key(key):
    """
    根据键名智能生成翻译
    """
    # 转换为小写并分割
    parts = re.split(r'[_\-\s]+', key.lower())
    
    zh_parts = []
    en_parts = []
    
    for part in parts:
        if part in SMART_TRANSLATIONS:
            zh_parts.append(SMART_TRANSLATIONS[part]["zh"])
            en_parts.append(SMART_TRANSLATIONS[part]["en"])
        else:
            # 如果找不到直接翻译，尝试部分匹配
            found = False
            for smart_key in SMART_TRANSLATIONS:
                if part in smart_key or smart_key in part:
                    zh_parts.append(SMART_TRANSLATIONS[smart_key]["zh"])
                    en_parts.append(SMART_TRANSLATIONS[smart_key]["en"])
                    found = True
                    break
            
            if not found:
                # 如果还是找不到，保持原样
                zh_parts.append(part)
                en_parts.append(part.title())
    
    # 组合翻译
    zh_translation = "".join(zh_parts) if len(zh_parts) <= 3 else "".join(zh_parts[:3]) + "等"
    en_translation = " ".join(en_parts)
    
    return {
        "zh": zh_translation,
        "en": en_translation
    }

def load_existing_translations():
    """
    加载现有翻译
    """
    try:
        # 尝试从unified_i18n_manager导入
        sys.path.insert(0, str(project_root / "tools"))
        from unified_i18n_manager import UnifiedI18nManager
        
        manager = UnifiedI18nManager()
        return manager.translations
    except Exception as e:
        print(f"无法加载现有翻译: {e}")
        return {}

def load_missing_keys():
    """
    从missing_translations_template.json加载缺失的键
    """
    template_file = project_root / "tools" / "missing_translations_template.json"
    if template_file.exists():
        with open(template_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def auto_fill_translations():
    """
    自动补充翻译
    """
    print("...")
    
    # 加载现有翻译
    existing_translations = load_existing_translations()
    print(f"已加载 {len(existing_translations)} 个现有翻译")
    
    # 加载缺失的键
    missing_keys = load_missing_keys()
    print(f"发现 {len(missing_keys)} 个缺失翻译的键")
    
    # 自动补充翻译
    filled_count = 0
    for key in missing_keys:
        if key not in existing_translations:
            # 智能生成翻译
            translation = smart_translate_key(key)
            existing_translations[key] = translation
            filled_count += 1
            print(f"已补充: {key} -> {translation}")
    
    # 保存更新后的翻译
    output_file = project_root / "tools" / "auto_filled_translations.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_translations, f, ensure_ascii=False, indent=2)
    
    print(f"\n自动补充完成!")
    print(f"- 总翻译条目: {len(existing_translations)}")
    print(f"- 新增翻译: {filled_count}")
    print(f"- 输出文件: {output_file}")
    
    # 生成报告
    report_file = project_root / "tools" / "auto_fill_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"自动翻译补充报告\n")
        f.write(f"生成时间: {__import__('datetime').datetime.now()}\n\n")
        f.write(f"总翻译条目: {len(existing_translations)}\n")
        f.write(f"新增翻译: {filled_count}\n\n")
        
        if filled_count > 0:
            f.write("新增翻译详情:\n")
            for key in missing_keys:
                if key in existing_translations:
                    translation = existing_translations[key]
                    f.write(f"  {key}:\n")
                    f.write(f"    中文: {translation.get('zh', '')}\n")
                    f.write(f"    英文: {translation.get('en', '')}\n\n")
    
    print(f"- 报告文件: {report_file}")
    
    return existing_translations

def update_unified_i18n_manager(translations):
    """
    更新unified_i18n_manager.py文件
    """
    try:
        manager_file = project_root / "tools" / "unified_i18n_manager.py"
        
        # 读取现有文件
        with open(manager_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找translations字典的位置
        pattern = r'(self\.translations\s*=\s*){[^}]*}'
        
        # 生成新的translations字典
        translations_str = json.dumps(translations, ensure_ascii=False, indent=8)
        replacement = f'\\1{translations_str}'
        
        # 替换
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 写回文件
        with open(manager_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"已更新 {manager_file}")
        return True
    except Exception as e:
        print(f"更新unified_i18n_manager.py失败: {e}")
        return False

if __name__ == "__main__":
    # 自动补充翻译
    translations = auto_fill_translations()
    
    # 询问是否更新unified_i18n_manager.py
    response = input("\n是否要更新unified_i18n_manager.py文件? (y/n): ")
    if response.lower() in ['y', 'yes', '是']:
        update_unified_i18n_manager(translations)
        print("!")
    else:
        print("跳过更新unified_i18n_manager.py")
    
    print("\n自动翻译补充完成!")