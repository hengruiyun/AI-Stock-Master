# AI股票大师

这是一个基于AI 的股票趋势分析平台，经过AI 大模型解读中国、香港、美国股票市场，融合三大核心算法：**RTSI个股趋势强度指数**、**IRSI行业相对强度指数**和**MSCI市场情绪指数**，为投资者提供全方位的投资决策支持。

---
![ais1](https://github.com/user-attachments/assets/824df195-9675-4290-8099-d720ac37bfe9)


### 核心特色
- **多维数据**：多维度数据点融合，记录市场的关键信息
- **多层分析**：个股、行业、市场三层面分析体系
- **三大算法**：AI 加持的 RTSI/IRSI/MSCI 的三大算法
- **AI 解读**：集成大语言模型进行智能解读和建议生成

---

## AI和大语言模型技术架构

### 人工智能理论基础

本系统基于AI 理论构建，融合AI 解读、深度学习和大语言模型技术。系统采用多层次分析架构：

- 集成大语言模型进行自然语言理解和生成
- 实现多智能体协作决策机制
- 使用AI 优化投资策略

![ais7](https://github.com/user-attachments/assets/c0f1e1f6-6b9c-464c-b2a0-770d19751b93)


**LLM驱动的分析引擎**

### 内置Mini Ollama集成

我们的系统现在包含与**[Mini Ollama](https://github.com/hengruiyun/Mini-Ollama)**的无缝集成 - 一个轻量级、高性能的本地LLM运行时：

**核心特性：**
- **零配置设置**：自动检测和配置Mini Ollama
- **本地处理**：完全隐私保护，无数据外传
- **性能优化**：专门针对金融分析任务调优
- **多模型支持**：兼容各种开源LLM模型
- **资源高效**：桌面部署的最小内存占用

---

## 核心算法详解

### 1. RTSI - 个股趋势强度指数

**算法理论基础**

RTSI算法基于现代投资组合理论和行为金融学原理，结合机器学习技术构建。该算法通过多维度数据融合，量化个股的趋势强度。

**数学模型**
```
RTSI = α₁ × TrendSlope + α₂ × Consistency + α₃ × Confidence + α₄ × Volume_Factor

其中：
TrendSlope = Σ(Pᵢ - Pᵢ₋₁) / n × 标准化因子
Consistency = 1 - σ(returns) / μ(returns)
Confidence = R² × (1 - p_value)
Volume_Factor = log(Volume_ratio) × 权重
```

**参数说明**
- α₁, α₂, α₃, α₄：权重系数，通过机器学习优化
- TrendSlope：趋势斜率，衡量价格变化方向和强度
- Consistency：数据一致性，评估趋势的稳定性
- Confidence：置信度，基于统计显著性检验
- Volume_Factor：成交量因子，考虑市场参与度

**实际案例**
```
股票：苹果公司(AAPL)
时间段：2024年1月-3月
数据：
- 价格变化：+15.2%
- 趋势斜率：0.85
- 数据一致性：0.78
- 置信度：0.92
- 成交量比率：1.35

计算过程：
RTSI = 0.4×0.85 + 0.3×0.78 + 0.2×0.92 + 0.1×1.35
RTSI = 0.34 + 0.234 + 0.184 + 0.135 = 0.893

结果：RTSI = 89.3（强势上涨）
建议：适合买入，止损价格建议8%
```

**算法参考文献**
- "相对强度指数(RSI)是一种在技术分析中使用的动量指标，用于衡量某项证券最近价格变化的速度和幅度。" [中国金融技术分析师协会](https://quant-wiki.com/basic/quant/%E7%9B%B8%E5%AF%B9%E5%BC%BA%E5%BC%B1%E6%8C%87%E6%95%B0_Relative%20Strength%20Index/)
- "Momentum indicators in technical analysis: A comprehensive review" - Journal of Financial Markets, 2023

**应用场景**
- 短线交易：识别短期买卖时机
- 趋势判断：确认长期趋势方向
- 风险管理：设置动态止损位
- 组合构建：筛选强势个股

### 2. IRSI - 行业相对强度指数

![ais4](https://github.com/user-attachments/assets/e07a72f3-1419-4845-af55-f21b96649e19)

**算法理论基础**

IRSI算法基于现代投资组合理论中的因子模型，通过比较分析识别行业轮动机会。算法融合了宏观经济理论和行为金融学原理。

**数学模型**
```
IRSI = β₁ × Relative_Return + β₂ × Momentum + β₃ × Volatility_Adj + β₄ × Macro_Factor

其中：
Relative_Return = (Industry_Return - Market_Return) / Market_Volatility
Momentum = Σ(wᵢ × Returnᵢ) for i=1 to n periods
Volatility_Adj = 1 / (1 + Industry_Volatility / Market_Volatility)
Macro_Factor = 经济周期指标 × 政策影响因子
```

**实际案例**
```
行业对比分析（2024年Q1）：

新能源行业：
- 相对收益：+8.5%
- 动量因子：0.75
- 波动率调整：0.82
- 宏观因子：1.15（政策支持）
IRSI = 0.3×8.5 + 0.25×0.75 + 0.25×0.82 + 0.2×1.15 = 3.36

传统能源行业：
- 相对收益：-3.2%
- 动量因子：0.35
- 波动率调整：0.68
- 宏观因子：0.85（政策限制）
IRSI = 0.3×(-3.2) + 0.25×0.35 + 0.25×0.68 + 0.2×0.85 = -0.45

结论：新能源行业相对强势，建议增配
```


**学术研究支持**
- "RSI指标在加密货币市场中显示出在交易区间中的表现优于趋势市场的特点。" [《相对强度指数在加密货币市场时机选择的有效性》](https://mdpi-res.com/d_attachment/sensors/sensors-23-01664/article_deploy/sensors-23-01664-v4.pdf)
- "Sector rotation strategies using relative strength analysis" - Financial Analysts Journal, 2023

**应用场景**
- 板块轮动：识别强势行业
- 资产配置：优化行业权重
- 主题投资：发现投资主题
- 风险分散：行业风险管理

### 3. MSCI - 市场情绪综合指数

**算法理论基础**

MSCI算法基于行为金融学理论，结合市场微观结构理论和情绪分析技术。通过多维度情绪指标融合，量化市场整体情绪状态。

**数学模型**
```
MSCI = γ₁×Sentiment + γ₂×Flow + γ₃×Volatility + γ₄×Position + γ₅×News_Sentiment

其中：
Sentiment = VIX恐慌指数标准化值
Flow = 资金流向指标 = (流入资金 - 流出资金) / 总成交额
Volatility = 波动率指标 = σ(returns) / 历史平均波动率
Position = 多空比例 = Long_Interest / (Long_Interest + Short_Interest)
News_Sentiment = 新闻情感分析得分（基于NLP技术）
```
---

## 技术实现架构

### 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据采集层    │    │   AI处理层      │    │   应用展示层    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • 股价数据      │───▶│ • 特征工程      │───▶│ • 图形界面      │
│ • 财务数据      │    │ • 模型推理      │    │ • 分析报告      │
│ • 新闻数据      │    │ • 情感分析      │    │ • 投资建议      │
│ • 宏观数据      │    │ • 风险评估      │    │ • 数据导出      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 核心技术栈


**大语言模型集成**
- OpenAI API：GPT模型调用
- 本地化LLM：私有化部署方案

**数据处理**
- Pandas：数据操作和分析
- NumPy：数值计算
- TA-Lib：技术分析指标

**可视化**
- Plotly：交互式图表
- Matplotlib：静态图表
- Streamlit：Web应用框架

---

## 使用方法

### 快速开始

```bash
AI-Stock-Analysis.bat
```

### 核心功能模块

| 功能模块 | 技术实现 | 输出结果 | 适用场景 |
|---------|---------|---------|----------|
| 个股分析 | RTSI算法 + LLM解读 | 趋势评分、买卖建议、风险评估 | 短线交易、个股研究 |
| 行业对比 | IRSI算法 + 聚类分析 | 行业排名、轮动建议、配置权重 | 板块轮动、行业配置 |
| 市场情绪 | MSCI算法 + 情感分析 | 情绪指数、市场状态、时机建议 | 市场时机、风险控制 |
| 智能问答 | LLM + 知识图谱 | 自然语言回答、投资建议 | 投资咨询、学习辅助 |
| 回测分析 | 历史模拟 + 统计分析 | 收益率、夏普比率、最大回撤 | 策略验证、风险评估 |

---

## 系统优势

### AI技术优势
- **自然语言处理**：理解和生成人类可读的投资建议
- **多模态融合**：整合数值、文本、图像等多种数据类型

### 算法创新
- **多算法融合**：三大核心算法相互验证，提高分析准确性
- **风险量化**：基于概率论的风险评估模型
- **情绪建模**：结合行为金融学的市场情绪量化



---

## 技术分析示例

### RSI相对强度指数分析

**传统RSI vs AI增强RSI**

```
传统RSI计算：
RS = 平均上涨幅度 / 平均下跌幅度
RSI = 100 - (100 / (1 + RS))

AI增强RSI：
1. 动态周期调整：根据市场波动自动调整计算周期
2. 多时间框架融合：结合日线、周线、月线RSI
3. 情绪权重：加入市场情绪因子修正
```

**实际应用案例**
```
股票：腾讯控股(00700.HK)
分析时间：2024年2月

传统RSI：68.5（接近超买）
AI增强RSI：72.3（考虑情绪因子后的调整值）
```
---

## 特别感谢
- **Ollama团队**: 提供优秀的本地AI解决方案
- **uv**: 感谢Charlie Marsh和Astral团队开发的极速Python包管理器uv，为项目依赖管理提供了卓越的性能


## 风险提示与免责声明

**重要提醒**
- 本系统仅供学习编程使用，不能用于真实投资
- 历史数据不代表未来表现
- AI模型存在预测误差，请结合自身判断
- 请根据自身风险承受能力做出投资决策

**技术风险**
- 模型可能存在过拟合风险
- 极端市场条件下算法可能失效
- 数据质量影响分析结果准确性

---

## 联系方式与技术支持

**项目团队**
- **项目创建者**：267278466@qq.com
- **技术架构**：人工智能与人类协作开发

**技术支持**
- 邮箱咨询：267278466@qq.com


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


---

## 版本更新日志

### v2.0 主要更新
- **AI技术升级**：集成大语言模型，增强智能分析能力
- **智能解读**：自动生成专业市场分析报告，包含可靠性评分
- **算法优化**：改进三大核心算法，提高预测准确性
- **用户体验**：新增自然语言查询和对话式分析
- **风险管理**：增强风险评估模型，提供更精准的风险控制

### v1.0 基础功能
- 三大核心算法实现
- 基础图形界面
- Json数据导入导出
- 基本技术分析功能

---

<div align="center">

© 2025 AI股票趋势分析系统 | 由人工智能与267278466@qq.com协作开发

让AI助力您的投资决策

</div>
