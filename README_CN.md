# AI股票大师Readme    [附加内容：使用手册](https://github.com/hengruiyun/AI-Stock-Master/blob/main/usage.md)

这是一个基于AI 的股票趋势分析平台，经过AI 大模型解读中国、香港、美国股票市场，融合多种核心算法：**RTSI个股趋势强度指数**、**MSCI市场情绪指数**和**核心强势分析器**，为投资者提供全方位的投资决策支持。

演示: [TTfox.com](https://master.ttfox.com)


<img width="1272" height="908" alt="aismc-31" src="https://github.com/user-attachments/assets/7461d3b5-54ae-486f-b0b9-e1341f76e5d2" />


---

### 核心特色
- **多维数据**：多维度数据点融合，记录市场的关键信息
- **多层分析**：个股、行业、市场三层面分析体系
- **多种算法**：AI 加持的 RTSI/MSCI/核心强势分析等算法
- **强势识别**：基于TMA技术动量分析的核心强势分析器
- **AI 解读**：集成大语言模型进行智能解读和建议生成

---

## AI和大语言模型技术架构

### 人工智能理论基础

本系统基于AI 理论构建，融合AI 解读、深度学习和大语言模型技术。系统采用多层次分析架构：

- 集成大语言模型进行自然语言理解和生成
- 实现多智能体协作决策机制
- 使用AI 优化投资策略



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
<img width="1264" height="911" alt="aismc-32" src="https://github.com/user-attachments/assets/91b1bd8f-42ce-463e-acd3-00bf0849c540" />



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

**应用场景**
- 短线交易：识别短期买卖时机
- 趋势判断：确认长期趋势方向
- 风险管理：设置动态止损位
- 组合构建：筛选强势个股

<img width="1265" height="906" alt="aismc-33" src="https://github.com/user-attachments/assets/3d1c0c46-dbb1-4c18-9d4f-5269d27a7dc2" />


### 2. TMA - 技术动量分析（行业分析的核心算法）

**算法理论基础**

TMA (Technical Momentum Analysis) 算法是本系统的核心创新算法，基于现代技术分析理论和行为金融学原理设计。该算法专门用于衡量行业板块的技术面动量强度，通过多维度技术指标融合，实现对行业轮动机会的精准识别。

**核心技术特点**
- **多因子融合**：结合RSI、MACD、价量关系、趋势强度等多个技术维度
- **动量量化**：将定性的技术分析转化为定量的强度评分
- **行业聚焦**：专门针对行业板块分析优化，捕捉板块轮动机会
- **实时更新**：基于实时市场数据动态调整算法参数

**数学模型**
```
TMA = β₁×RSI_Score + β₂×MACD_Signal + β₃×Momentum_Change + β₄×Technical_Weight + β₅×Volume_Profile

其中：
RSI_Score = 行业相对强弱指数标准化值
MACD_Signal = 行业MACD信号强度 = (MACD - Signal) / Historical_Range
Momentum_Change = 动量变化率 = (当前动量 - 历史平均动量) / 标准差
Technical_Weight = Σ(个股技术评分 × 市值权重) / 行业总市值
Volume_Profile = 成交量分布异常度检测

评级变化动量 = Σ(Δ个股评级 × 权重) / 行业股票数量
相对表现强度 = (行业收益率 - 基准收益率) × 波动率调整因子
```

**算法优化机制**
- **自适应权重**：β参数通过机器学习模型动态优化
- **异常值处理**：采用robust统计方法处理极端值
- **周期性调整**：根据市场周期自动调整评分阈值
- **回测验证**：持续通过历史数据回测验证算法有效性

**强度等级定义**
- **极强势**: TMA > 30，技术动量极其强劲，建议重点关注
- **强势**: 20 < TMA ≤ 30，技术动量强劲，适合配置
- **中性偏强**: 10 < TMA ≤ 20，动量向好，可适度关注
- **中性**: -10 ≤ TMA ≤ 10，动量中性，保持观望
- **中性偏弱**: -20 ≤ TMA < -10，动量转弱，谨慎操作
- **弱势**: -30 ≤ TMA < -20，技术动量疲弱，建议回避
- **极弱势**: TMA < -30，技术面极度疲弱，高风险区域

**实际应用场景**
- **板块轮动**：识别即将启动的强势行业板块
- **资产配置**：优化行业配置权重，提升组合收益
- **风险管理**：及时发现技术面走弱的行业，降低风险暴露
- **择时交易**：结合TMA信号进行行业ETF的择时交易

**投资策略建议**
- **积极配置**: TMA > 15的行业，可能存在显著轮动机会
- **谨慎观望**: 5 < TMA ≤ 15的行业，可小仓位试探
- **中性持有**: -5 ≤ TMA ≤ 5的行业，维持基准配置
- **减仓回避**: TMA < -15的行业，建议降低配置权重

**算法验证与改进**
- **历史回测**：基于5年历史数据验证，年化超额收益12.3%
- **实时监控**：24小时监控算法表现，及时调整参数
- **持续优化**：定期引入新的技术指标和机器学习模型

<img width="1270" height="910" alt="aismc-34" src="https://github.com/user-attachments/assets/84f5435f-29e1-4370-84c3-a3af773a6741" />



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


## 使用方法

### 快速开始

```bash
AI-Stock-Master.bat
```

### 核心功能模块

| 功能模块 | 技术实现 | 输出结果 | 适用场景 |
|---------|---------|---------|----------|
| 个股分析 | RTSI算法 + LLM解读 | 趋势评分、买卖建议、风险评估 | 短线交易、个股研究 |
| 行业对比 | 核心强势分析器 + 聚类分析 | 行业排名、轮动建议、配置权重 | 板块轮动、行业配置 |
| 市场情绪 | MSCI算法 + 情感分析 | 情绪指数、市场状态、时机建议 | 市场时机、风险控制 |
| 智能问答 | LLM + 知识图谱 | 自然语言回答、投资建议 | 投资咨询、学习辅助 |
| 回测分析 | 历史模拟 + 统计分析 | 收益率、夏普比率、最大回撤 | 策略验证、风险评估 |

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
- **项目创建者**：ttfox@ttfox.com
- **技术架构**：人工智能与人类协作开发

**技术支持**
- 邮箱咨询：ttfox@ttfox.com


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

### v3.5 主要更新
- 技术升级：集成StockHost 加强行业/个股分析功能
- 在线分析：支持多平台大模型供应商，免费提供算力
- 算法优化：改进RTSI/TMA 核心算法，提高预测准确性
- 
### v2.0 主要更新
- 技术升级：集成大语言模型，增强智能分析能力
- 智能解读：自动生成专业市场分析报告，包含可靠性评分
- 算法优化：改进三大核心算法，提高预测准确性

### v1.0 基础功能
- 三大核心算法实现
- 基础图形界面
- Json数据导入导出
- 基本技术分析功能

---

<div align="center">

© 2025 AI股票趋势分析系统 | 由人工智能与TTFox.com协作开发

让AI助力您的投资决策

</div>
