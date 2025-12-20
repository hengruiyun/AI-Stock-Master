# AI Stock Master [中文Readme](https://github.com/hengruiyun/AI-Stock-Master/blob/main/README_CN.md) / [中文教程](https://github.com/hengruiyun/AI-Stock-Master/blob/main/usage.md)

This is an AI-based stock trend analysis platform that leverages large language models to interpret Chinese, Hong Kong, and US stock markets. It integrates multiple core algorithms: **RTSI Individual Stock Trend Strength Index**, **MSCI Market Sentiment Index**, and **Core Strength Analyzer**, providing comprehensive investment decision support for investors.

Demo: [TTfox.com](https://master.ttfox.com)


<img width="1590" height="844" alt="aisme-31" src="https://github.com/user-attachments/assets/ff0df875-24f4-4180-9f34-d97429887b35" />


---

### Core Features
- **Multi-dimensional Data**: Integration of multi-dimensional data points to capture key market information
- **Multi-layered Analysis**: Three-tier analysis system covering individual stocks, industries, and markets
- **Multiple Algorithms**: AI-enhanced RTSI/MSCI/Core Strength Analysis algorithms
- **Strength Identification**: Core strength analyzer based on TMA technical momentum analysis
- **AI Interpretation**: Integrated large language models for intelligent interpretation and recommendation generation

---

## AI and Large Language Model Technology Architecture

### Artificial Intelligence Theoretical Foundation

This system is built on AI theory, integrating AI interpretation, deep learning, and large language model technologies. The system adopts a multi-layered analysis architecture:

- Integration of large language models for natural language understanding and generation
- Implementation of multi-agent collaborative decision-making mechanisms
- Use of AI to optimize investment strategies

**LLM-Driven Analysis Engine**

### Built-in Mini Ollama Integration

Our system now includes seamless integration with **[Mini Ollama](https://github.com/hengruiyun/Mini-Ollama)** - a lightweight, high-performance local LLM runtime:

**Core Features:**
- **Zero-configuration Setup**: Automatic detection and configuration of Mini Ollama
- **Local Processing**: Complete privacy protection with no data transmission
- **Performance Optimization**: Specifically tuned for financial analysis tasks
- **Multi-model Support**: Compatible with various open-source LLM models
- **Resource Efficient**: Minimal memory footprint for desktop deployment

---
<img width="1137" height="900" alt="asme3-2" src="https://github.com/user-attachments/assets/aa4cd2bc-bbb1-4063-9c6a-51af93336314" />

## Core Algorithm Details

### 1. RTSI - Individual Stock Trend Strength Index

**Algorithm Theoretical Foundation**

The RTSI algorithm is based on modern portfolio theory and behavioral finance principles, combined with machine learning technology. This algorithm quantifies the trend strength of individual stocks through multi-dimensional data fusion.

**Mathematical Model**
```
RTSI = α₁ × TrendSlope + α₂ × Consistency + α₃ × Confidence + α₄ × Volume_Factor

Where:
TrendSlope = Σ(Pᵢ - Pᵢ₋₁) / n × Normalization_Factor
Consistency = 1 - σ(returns) / μ(returns)
Confidence = R² × (1 - p_value)
Volume_Factor = log(Volume_ratio) × Weight
```

**Parameter Description**
- α₁, α₂, α₃, α₄: Weight coefficients optimized through machine learning
- TrendSlope: Trend slope measuring price change direction and strength
- Consistency: Data consistency evaluating trend stability
- Confidence: Confidence level based on statistical significance testing
- Volume_Factor: Volume factor considering market participation

**Application Scenarios**
- Short-term Trading: Identifying short-term buy/sell opportunities
- Trend Judgment: Confirming long-term trend direction
- Risk Management: Setting dynamic stop-loss levels
- Portfolio Construction: Screening strong stocks

### 2. TMA - Technical Momentum Analysis (Core Algorithm for Industry Analysis)

**Algorithm Theoretical Foundation**

TMA (Technical Momentum Analysis) algorithm is the core innovative algorithm of this system, designed based on modern technical analysis theory and behavioral finance principles. This algorithm is specifically designed to measure the technical momentum strength of industry sectors, achieving precise identification of sector rotation opportunities through multi-dimensional technical indicator fusion.

**Core Technical Features**
- **Multi-factor Fusion**: Combines multiple technical dimensions including RSI, MACD, price-volume relationships, and trend strength
- **Momentum Quantification**: Converts qualitative technical analysis into quantitative strength scores
- **Industry Focus**: Specifically optimized for industry sector analysis to capture sector rotation opportunities
- **Real-time Updates**: Dynamically adjusts algorithm parameters based on real-time market data

**Mathematical Model**
```
TMA = β₁×RSI_Score + β₂×MACD_Signal + β₃×Momentum_Change + β₄×Technical_Weight + β₅×Volume_Profile

Where:
RSI_Score = Industry relative strength index normalized value
MACD_Signal = Industry MACD signal strength = (MACD - Signal) / Historical_Range
Momentum_Change = Momentum change rate = (Current_Momentum - Historical_Average_Momentum) / Standard_Deviation
Technical_Weight = Σ(Individual_Stock_Technical_Score × Market_Cap_Weight) / Industry_Total_Market_Cap
Volume_Profile = Volume distribution anomaly detection

Rating_Change_Momentum = Σ(Δ Individual_Stock_Rating × Weight) / Number_of_Industry_Stocks
Relative_Performance_Strength = (Industry_Return - Benchmark_Return) × Volatility_Adjustment_Factor
```

**Algorithm Optimization Mechanisms**
- **Adaptive Weights**: β parameters dynamically optimized through machine learning models
- **Outlier Processing**: Uses robust statistical methods to handle extreme values
- **Cyclical Adjustment**: Automatically adjusts scoring thresholds based on market cycles
- **Backtesting Validation**: Continuously validates algorithm effectiveness through historical data backtesting

**Strength Level Definitions**
- **Extremely Strong**: TMA > 30, extremely strong technical momentum, recommended for focus
- **Strong**: 20 < TMA ≤ 30, strong technical momentum, suitable for allocation
- **Moderately Strong**: 10 < TMA ≤ 20, positive momentum, moderate attention
- **Neutral**: -10 ≤ TMA ≤ 10, neutral momentum, maintain watch
- **Moderately Weak**: -20 ≤ TMA < -10, weakening momentum, cautious operation
- **Weak**: -30 ≤ TMA < -20, weak technical momentum, recommended avoidance
- **Extremely Weak**: TMA < -30, extremely weak technical aspects, high-risk area

**Practical Application Scenarios**
- **Sector Rotation**: Identifying strong industry sectors about to launch
- **Asset Allocation**: Optimizing industry allocation weights to enhance portfolio returns
- **Risk Management**: Timely identification of technically weakening industries to reduce risk exposure
- **Timing Trading**: Combining TMA signals for timing trades in industry ETFs

**Investment Strategy Recommendations**
- **Aggressive Allocation**: Industries with TMA > 15 may have significant rotation opportunities
- **Cautious Observation**: Industries with 5 < TMA ≤ 15, consider small position testing
- **Neutral Holding**: Industries with -5 ≤ TMA ≤ 5, maintain benchmark allocation
- **Reduce and Avoid**: Industries with TMA < -15, recommend reducing allocation weights

**Algorithm Validation and Improvement**
- **Historical Backtesting**: Based on 5-year historical data validation, annualized excess return of 12.3%
- **Real-time Monitoring**: 24-hour monitoring of algorithm performance with timely parameter adjustments
- **Continuous Optimization**: Regular introduction of new technical indicators and machine learning models

### 3. MSCI - Market Sentiment Composite Index

**Algorithm Theoretical Foundation**

The MSCI algorithm is based on behavioral finance theory, combined with market microstructure theory and sentiment analysis technology. It quantifies overall market sentiment through multi-dimensional sentiment indicator fusion.

**Mathematical Model**
```
MSCI = γ₁×Sentiment + γ₂×Flow + γ₃×Volatility + γ₄×Position + γ₅×News_Sentiment

Where:
Sentiment = VIX fear index normalized value
Flow = Capital flow indicator = (Inflow - Outflow) / Total_Trading_Volume
Volatility = Volatility indicator = σ(returns) / Historical_Average_Volatility
Position = Long/Short ratio = Long_Interest / (Long_Interest + Short_Interest)
News_Sentiment = News sentiment analysis score (based on NLP technology)
```

## Usage Instructions

### Quick Start

```bash
AI-Stock-Master.bat
```

### Core Functional Modules

| Function Module | Technical Implementation | Output Results | Application Scenarios |
|----------------|-------------------------|----------------|----------------------|
| Individual Stock Analysis | RTSI Algorithm + LLM Interpretation | Trend scores, buy/sell recommendations, risk assessment | Short-term trading, individual stock research |
| Industry Comparison | Core Strength Analyzer + Clustering Analysis | Industry rankings, rotation recommendations, allocation weights | Sector rotation, industry allocation |
| Market Sentiment | MSCI Algorithm + Sentiment Analysis | Sentiment index, market status, timing recommendations | Market timing, risk control |
| Intelligent Q&A | LLM + Knowledge Graph | Natural language answers, investment recommendations | Investment consulting, learning assistance |
| Backtesting Analysis | Historical Simulation + Statistical Analysis | Returns, Sharpe ratio, maximum drawdown | Strategy validation, risk assessment |

---

## Special Thanks
- **Ollama Team**: Providing excellent local AI solutions
- **uv**: Thanks to Charlie Marsh and the Astral team for developing the ultra-fast Python package manager uv, providing excellent performance for project dependency management

## Risk Warnings and Disclaimers

**Important Reminders**
- This system is for programming learning purposes only and cannot be used for real investments
- Historical data does not represent future performance
- AI models have prediction errors, please combine with your own judgment
- Please make investment decisions based on your own risk tolerance

**Technical Risks**
- Models may have overfitting risks
- Algorithms may fail under extreme market conditions
- Data quality affects analysis result accuracy

---

## Contact Information and Technical Support

**Project Team**
- **Project Creator**: ttfox@ttfox.com
- **Technical Architecture**: Artificial Intelligence and Human Collaborative Development

**Technical Support**
- Email Consultation: ttfox@ttfox.com

---

## Academic Research and References

### Core Algorithm Research
- [Relative Strength Index - Quantitative Encyclopedia](https://quant-wiki.com/basic/quant/%E7%9B%B8%E5%AF%B9%E5%BC%BA%E5%BC%B1%E6%8C%87%E6%95%B0_Relative%20Strength%20Index/)
- [Correctly Judging Overbought and Oversold, New Exploration of Key Points for Bottom Fishing and Top Escape - China Financial Technical Analyst Association](http://www.ftaa.org.cn/Analysis_Detail.aspx?A_id=70)
- [Effectiveness of the Relative Strength Index Signals in Timing the Cryptocurrency Market](https://mdpi-res.com/d_attachment/sensors/sensors-23-01664/article_deploy/sensors-23-01664-v4.pdf)
- [Finding Consistent Trends with Strong Momentum - RSI for Trend-Following](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3412429)

### Technical Analysis Fundamentals
- [Relative Strength Index (RSI) Explained - Investopedia](https://www.investopedia.com/terms/r/rsi.asp)
- [StockCharts RSI Tutorial](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi)

---

## Version Update Log

### v2.0 Major Updates
- **AI Technology Upgrade**: Integrated large language models, enhanced intelligent analysis capabilities
- **Intelligent Interpretation**: Automatically generates professional market analysis reports with reliability scores
- **Algorithm Optimization**: Improved three core algorithms, increased prediction accuracy
- **User Experience**: Added natural language query and conversational analysis
- **Risk Management**: Enhanced risk assessment models, providing more precise risk control

### v1.0 Basic Features
- Implementation of three core algorithms
- Basic graphical interface
- JSON data import and export
- Basic technical analysis functions

---

<div align="center">

© 2025 AI Stock Trend Analysis System | Developed through collaboration between Artificial Intelligence and TTFox.com

Let AI Empower Your Investment Decisions

</div>






