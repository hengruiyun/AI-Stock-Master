# AI股票趋势分析系统

## 开发声明

本项目展示了人工智能与人类创意的完美结合，通过深度协作开发出这一智能投资分析系统。

---

## 系统概述

本系统是一个基于人工智能的股票趋势分析平台，通过融合三大核心算法：**RTSI个股趋势强度指数**、**IRSI行业相对强度指数**和**MSCI市场情绪指数**，为投资者提供全方位的投资决策支持。

### 核心特色
- **智能分析**：多维度数据融合，提供精准的趋势预测
- **全市场支持**：支持中国A股、香港股市、美国股市
- **深度分析**：个股、行业、市场三层面分析体系

---

## 核心算法简介

### 1. RTSI - 个股趋势强度指数

> **这是测试数据**

**简单理解：** 就像给股票的"发展势头"打分，分数越高表示上涨趋势越强。

**实际案例：**
- 苹果公司(AAPL)：连续5天评级从B+升至A-，RTSI = 75（强势上涨）
- 建议：适合买入，止损价格建议10%

**计算公式：**
```
RTSI = (趋势斜率 × 50 + 数据一致性 × 30 + 置信度 × 20) × 100
```

**算法参考：** "相对强度指数(RSI)是一种在技术分析中使用的动量指标，用于衡量某项证券最近价格变化的速度和幅度。"  
**来源：** [中国金融技术分析师协会](https://quant-wiki.com/basic/quant/%E7%9B%B8%E5%AF%B9%E5%BC%BA%E5%BC%B1%E6%8C%87%E6%95%B0_Relative%20Strength%20Index/)

**应用场景：** 短线交易、趋势判断、买卖时机选择

### 2. IRSI - 行业相对强度指数

> **这是测试数据**

**简单理解：** 比较不同行业的表现，找出当前最热门的板块。

**实际案例：**
- 新能源行业 IRSI = 65（相对强势）
- 传统能源行业 IRSI = 35（相对弱势）
- 建议：增配新能源，减配传统能源

**计算公式：**
```
IRSI = (行业平均收益 - 市场平均收益) × 时间权重 × 100
```

**学术研究：** "RSI指标在加密货币市场中显示出在交易区间中的表现优于趋势市场的特点。"  
**来源：** [《相对强度指数在加密货币市场时机选择的有效性》](https://mdpi-res.com/d_attachment/sensors/sensors-23-01664/article_deploy/sensors-23-01664-v4.pdf)

**应用场景：** 板块轮动、行业配置、长期投资策略

### 3. MSCI - 市场情绪综合指数

> **这是测试数据**

**简单理解：** 测量整个市场的"心情"，判断大家是乐观还是悲观。

**实际案例：**
- 2024年3月市场状况：MSCI = 1.2（偏乐观）
- 投资者情绪：积极
- 建议：适度增加风险资产配置

**计算公式：**
```
MSCI = 情绪指数×30% + 资金流向×25% + 波动率×25% + 多空比例×20%
```

**趋势研究：** "RSI能够有效识别持续上升趋势和强劲动量，特别适用于趋势跟踪和动量策略。"  
**来源：** [《寻找一致趋势与强劲动量》](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3412429)

**应用场景：** 市场时机选择、风险控制、仓位管理

---

## 使用方法

### 快速开始
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行系统
python main_gui.py

# 3. 选择数据文件
# 支持格式：Excel (.xlsx)
# 包含：股票代码、股票名称、行业、历史评级数据
```

### 核心功能

| 功能模块 | 说明 | 适用场景 |
|---------|------|----------|
| 个股分析 | 单只股票的趋势分析和买卖建议 | 短线交易、个股研究 |
| 行业对比 | 不同行业的相对强弱比较 | 板块轮动、行业配置 |
| 市场情绪 | 整体市场的情绪状况分析 | 市场时机、风险控制 |
| 数据导出 | 分析结果导出为Excel/HTML格式 | 报告生成、记录保存 |

---

## 系统优势

- **多算法融合：** 三大核心算法相互验证，提高分析准确性
- **实时更新：** 支持实时数据获取和动态分析
- **用户友好：** 直观的图形界面，易于操作
- **专业报告：** 生成详细的投资分析报告
- **风险控制：** 内置风险评估和止损建议

---

## 技术分析示例

### RSI相对强度指数 - 经典技术分析指标

**RSI指标图表说明：**
- RSI > 70：超买区域，可能出现回调
- RSI < 30：超卖区域，可能出现反弹
- RSI = 50：中性区域，趋势不明确

---

## 风险提示

**重要提醒：**
- 本系统仅供投资参考，不构成投资建议
- 股市有风险，投资需谨慎
- 历史数据不代表未来表现
- 请结合自身风险承受能力做出投资决策

---

## 联系方式

如果您对本系统有任何问题或建议，请联系：
- **项目创建者：** 267278466@qq.com
- **技术支持：** 通过QQ邮箱联系

---

## 学术研究与参考文献

### 核心算法研究
- [相对强弱指数 - 量化百科](https://quant-wiki.com/basic/quant/%E7%9B%B8%E5%AF%B9%E5%BC%BA%E5%BC%B1%E6%8C%87%E6%95%B0_Relative%20Strength%20Index/)
- [正确判断超买超卖，抄底逃顶关键点新探 - 中国金融技术分析师协会](http://www.ftaa.org.cn/Analysis_Detail.aspx?A_id=70)
- [Effectiveness of the Relative Strength Index Signals in Timing the Cryptocurrency Market](https://mdpi-res.com/d_attachment/sensors/sensors-23-01664/article_deploy/sensors-23-01664-v4.pdf)
- [Finding Consistent Trends with Strong Momentum - RSI for Trend-Following](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3412429)

### 技术分析基础
- [相对强度指数(RSI)详解 - Investopedia](https://www.investopedia.com/terms/r/rsi.asp)
- [StockCharts RSI教程](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi)
- [国际技术分析师协会 (IFTA)](https://www.ifta.org/)

### 开发工具与库
- [Pandas数据分析库](https://pandas.pydata.org/)
- [NumPy科学计算库](https://numpy.org/)
- [Matplotlib可视化库](https://matplotlib.org/)
- [Plotly交互式图表](https://plotly.com/python/)

---

<div align="center">

© 2024 AI股票趋势分析系统 | 由人工智能与人类协作开发

*让AI助力您的投资决策*

</div> 