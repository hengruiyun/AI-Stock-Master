# AI Stock Trend Analysis System [中文](https://github.com/hengruiyun/AI-Stock-Analysis/blob/main/README_CN.md)

## Development Statement

This project demonstrates the perfect combination of artificial intelligence and human creativity, developing this intelligent investment analysis system through deep collaboration.

---

![ais1](https://github.com/user-attachments/assets/bf7467e2-1ac2-446d-a379-649043a422fa)

## System Overview

This system is an AI-based stock trend analysis platform that integrates three core algorithms: **RTSI Individual Stock Trend Strength Index**, **IRSI Industry Relative Strength Index**, and **MSCI Market Sentiment Composite Index** to provide comprehensive investment decision support for investors.

### Core Features
- **Intelligent Analysis**: Multi-dimensional data fusion for precise trend prediction
- **Global Market Support**: Supports Chinese A-shares, Hong Kong stock market, and US stock market
- **Deep Analysis**: Three-level analysis system for individual stocks, industries, and markets

---

## Core Algorithm Introduction

### 1. RTSI - Individual Stock Trend Strength Index


![ais3](https://github.com/user-attachments/assets/8e745112-9522-405f-9d61-c224620d3f93)



> **This is test data**

**Simple Understanding:** Like scoring the "development momentum" of stocks, higher scores indicate stronger upward trends.

**Real Case:**
- Apple Inc. (AAPL): Rating upgraded from B+ to A- for 5 consecutive days, RTSI = 75 (strong upward trend)
- Recommendation: Suitable for buying, suggested stop-loss at 10%

**Calculation Formula:**
```
RTSI = (Trend Slope × 50 + Data Consistency × 30 + Confidence × 20) × 100
```

**Algorithm Reference:** "The Relative Strength Index (RSI) is a momentum indicator used in technical analysis to measure the speed and magnitude of recent price changes of a security."  
**Source:** [China Financial Technical Analysts Association](https://quant-wiki.com/basic/quant/%E7%9B%B8%E5%AF%B9%E5%BC%BA%E5%BC%B1%E6%8C%87%E6%95%B0_Relative%20Strength%20Index/)

**Application Scenarios:** Short-term trading, trend judgment, buy/sell timing

### 2. IRSI - Industry Relative Strength Index

![ais5](https://github.com/user-attachments/assets/18fe92c2-ea7a-488e-a99d-23b878d39c70)


> **This is test data**

**Simple Understanding:** Compares performance of different industries to find currently hottest sectors.

**Real Case:**
- New Energy Industry IRSI = 65 (relatively strong)
- Traditional Energy Industry IRSI = 35 (relatively weak)
- Recommendation: Increase allocation to new energy, reduce traditional energy

**Calculation Formula:**
```
IRSI = (Industry Average Return - Market Average Return) × Time Weight × 100
```

**Academic Research:** "RSI indicators show better performance in trading ranges than in trending markets in cryptocurrency markets."  
**Source:** [Effectiveness of the Relative Strength Index Signals in Timing the Cryptocurrency Market](https://mdpi-res.com/d_attachment/sensors/sensors-23-01664/article_deploy/sensors-23-01664-v4.pdf)

**Application Scenarios:** Sector rotation, industry allocation, long-term investment strategies

### 3. MSCI - Market Sentiment Composite Index

![ais6](https://github.com/user-attachments/assets/73639f5a-e565-45c9-bea7-d01cd6b418ed)

> **This is test data**

**Simple Understanding:** Measures the overall market "mood" to determine whether people are optimistic or pessimistic.

**Real Case:**
- March 2024 Market Condition: MSCI = 1.2 (moderately optimistic)
- Investor Sentiment: Positive
- Recommendation: Moderately increase risk asset allocation

**Calculation Formula:**
```
MSCI = Sentiment Index×30% + Capital Flow×25% + Volatility×25% + Long/Short Ratio×20%
```

**Trend Research:** "RSI can effectively identify consistent uptrends with strong momentum, particularly suitable for trend-following and momentum strategies."  
**Source:** [Finding Consistent Trends with Strong Momentum](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3412429)

**Application Scenarios:** Market timing, risk control, position management

---

## Usage Instructions

### Quick Start
```bash
AI-Stock-Analysis-267278466
```

![ais7](https://github.com/user-attachments/assets/65c1edeb-237c-4a56-b67b-7f81a2d78b3c)

### Core Functions

| Function Module | Description | Application Scenarios |
|----------------|-------------|----------------------|
| Individual Stock Analysis | Trend analysis and buy/sell recommendations for single stocks | Short-term trading, individual stock research |
| Industry Comparison | Relative strength comparison of different industries | Sector rotation, industry allocation |
| Market Sentiment | Overall market sentiment analysis | Market timing, risk control |
| Data Export | Export analysis results to Excel/HTML formats | Report generation, record keeping |

---

## System Advantages

- **Multi-Algorithm Fusion:** Three core algorithms verify each other, improving analysis accuracy
- **Real-time Updates:** Supports real-time data acquisition and dynamic analysis
- **User-Friendly:** Intuitive graphical interface, easy to operate
- **Professional Reports:** Generate detailed investment analysis reports
- **Risk Control:** Built-in risk assessment and stop-loss recommendations

---

## Technical Analysis Examples

### RSI Relative Strength Index - Classic Technical Analysis Indicator

**RSI Indicator Chart Explanation:**
- RSI > 70: Overbought zone, possible pullback
- RSI < 30: Oversold zone, possible rebound
- RSI = 50: Neutral zone, unclear trend

---

## Risk Warning

**Important Reminder:**
- This system is for investment reference only and does not constitute investment advice
- Stock market carries risks, invest cautiously
- Historical data does not represent future performance
- Please make investment decisions based on your own risk tolerance

---

## Contact Information

If you have any questions or suggestions about this system, please contact:
- **Project Creator:** 267278466@qq.com
- **Technical Support:** Contact via QQ email

---

## Academic Research & References

### Core Algorithm Research
- [Relative Strength Index - Quantitative Wiki](https://quant-wiki.com/basic/quant/%E7%9B%B8%E5%AF%B9%E5%BC%BA%E5%BC%B1%E6%8C%87%E6%95%B0_Relative%20Strength%20Index/)
- [Correct Judgment of Overbought and Oversold - China Financial Technical Analysts Association](http://www.ftaa.org.cn/Analysis_Detail.aspx?A_id=70)
- [Effectiveness of the Relative Strength Index Signals in Timing the Cryptocurrency Market](https://mdpi-res.com/d_attachment/sensors/sensors-23-01664/article_deploy/sensors-23-01664-v4.pdf)
- [Finding Consistent Trends with Strong Momentum - RSI for Trend-Following](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3412429)

### Technical Analysis Fundamentals
- [Relative Strength Index (RSI) Explained - Investopedia](https://www.investopedia.com/terms/r/rsi.asp)
- [StockCharts RSI Tutorial](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi)
- [International Federation of Technical Analysts (IFTA)](https://www.ifta.org/)

### Development Tools & Libraries
- [Pandas Data Analysis Library](https://pandas.pydata.org/)
- [NumPy Scientific Computing Library](https://numpy.org/)
- [Matplotlib Visualization Library](https://matplotlib.org/)
- [Plotly Interactive Charts](https://plotly.com/python/)

---

<div align="center">

© 2025 AI Stock Trend Analysis System | Developed through AI- 267278466@qq.com Collaboration

*Let AI Empower Your Investment Decisions*

</div> 
