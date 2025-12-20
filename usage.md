# AI股票大师使用教程

演示: [TTfox.com](https://master.ttfox.com)


<img width="1298" height="973" alt="aismc-10" src="https://github.com/user-attachments/assets/3b4a2147-1f58-4fad-af7e-29dcd6e21981" />

---

## 🚀 下载安装

### 📥 获取安装包
访问官方发布页面下载最新版本：
**https://github.com/hengruiyun/AI-Stock-Master/releases**

### 💻 Windows 10/11 安装
1. **下载安装包**：选择 `AI-Stock-Master-Windows-Setup.exe`
2. **运行安装程序**
3. **安装选项**：
   - ✅ **强烈推荐**：勾选"安装AI模型"选项

### 🍎 macOS 安装
1. **下载DMG文件**：选择 `AI-Stock-Master--macOS-x86_64.dmg`
2. **挂载镜像**：双击DMG文件
3. **拖拽安装**：将 `AI-Stock-Master` 文件夹拖到 `Applications` 文件夹
4. **权限设置**：首次运行时，在"系统偏好设置 > 安全性与隐私"中允许运行

### 🐧 Ubuntu/Linux 安装
1. **下载源码包**：选择 `Source code.zip`
2. **解压缩**：
   ```bash
   unzip Source code.zip
   cd AI-Stock-Master
   ```
3. **设置权限**：
   ```bash
   chmod +x *.sh
   ```
---

## 🎯 第一次使用

### Windows 首次启动流程

#### 启动主程序
1. **双击**："AI股票大师"桌面图标
2. **耐心等待**：整个过程可能需要1-2分钟


### macOS 首次启动流程

#### 方法1：使用图形界面
1. **双击**：`安装AI大模型.command`
2. **双击**：`启动AI股票大师.command`
3. **允许执行**：系统可能会询问权限，选择"允许"
4. **等待完成**：安装过程会在终端中显示进度

#### 方法2：使用命令行
```bash
cd /Applications/AI-Stock-Master
./InstallOllama.sh
./AI-Stock-Master.sh
```

### Linux 首次启动流程

```bash
# 安装AI模型
./InstallOllama.sh

# 启动程序
./AI-Stock-Master.sh
```

---
<img width="1298" height="973" alt="aismc-11" src="https://github.com/user-attachments/assets/4fbff212-5f85-48b2-bff1-a7ba716939b9" />


## 🔧 核心功能介绍

### 📊 主要分析模块

#### 1. 个股分析系统
- **RTSI指数**：个股趋势强度指数，量化个股趋势力度
- **置信度分析**：评估分析结果的可靠性

#### 2. 行业分析系统
- **TMA算法**：技术动量分析，专门用于行业轮动识别
- **轮动信号**：识别行业轮动机会

#### 3. 市场情绪分析
- **MSCI指数**：市场情绪综合指数
- **恐慌贪婪指标**：量化市场情绪状态
- **波动率分析**：市场风险评估

#### 4. AI智能分析
- **AI报告生成**：自动生成专业分析报告
- **风险评估**：AI驱动的风险识别
- **投资建议**：基于多维度数据的投资建议

---

## 🤖 AI模型配置

### 本地AI模型（推荐）

#### Ollama管理
```bash
# 启动Ollama
ollama serv

# 查看已安装模型
ollama list

# 安装新模型
ollama pull qwen3:4b

# 删除模型
ollama rm gemma3:1b
```
#### 推荐模型配置

| 配置等级 | 推荐模型 | 内存需求 | 分析质量 | 适用场景 |
|---------|---------|---------|---------|---------|
| 入门级 | qwen3:1.7b | 1.4GB | ⭐⭐⭐ | 基础分析 |
| 标准级 | qwen3:8b | 6GB | ⭐⭐⭐⭐ | 日常使用 |
| 专业级 | qwen3:12b | 8GB | ⭐⭐⭐⭐⭐ | 专业分析 |
| 企业级 | llama3.1:70b | 32GB+ | ⭐⭐⭐⭐⭐ | 机构使用 |

### 云端AI模型（高级）

#### siliconflow配置
1. **注册账号**：访问 https://cloud.siliconflow.cn/i/GvCcTpzt
2. **获取API密钥**：在控制台创建API密钥
3. **配置软件**：在设置中输入API密钥
4. **选择模型**：推荐使用 `Qwen/Qwen3-8B`


---

## 📈 日常使用指南

### 启动流程
1. **数据检查**：软件启动时自动检查数据更新
2. **市场选择**：选择要分析的市场（A股/港股/美股）
3. **功能导航**：根据需求选择相应分析功能


### AI功能说明
- **AI功能**：标题包含"AI"字样
- **传统功能**：纯数学算法分析，不依赖AI
- **软件默认不开启AI**：需要AI时手动运行，运行前必须保证已经正确安装AI大模型。
- **AI模型的大小影响了AI的智力**：当你看到AI分析结果有异常，则表示当前AI模型不能满足你的要求，需要更换更强大的，甚至是商业版本的DeepSeek，这需要你自己支付AI的费用。
  
<img width="1298" height="973" alt="aismc-15" src="https://github.com/user-attachments/assets/20093fdb-514c-44a1-a029-2c4ed8f1f44f" />



### 评级系统说明（核心）
- **8级评级系统**：此评级为本软件最重要的数据，一切算法和功能都以此展开，与传统交易数据绝然不同。
- **评级应用范围**：是所有分析功能的基础数据，评级数据最直接体现在行业分析的趋势图表中，它可以和股价走势不一致。

<img width="1298" height="973" alt="aismc-12" src="https://github.com/user-attachments/assets/1243c9a0-3207-4788-bd54-09e2fbff5f69" />

---

## 📊 数据来源说明

### 数据更新机制
- **数据来源**：分两部分数据，交易数据和评级数据，数据格式为本软件自制
- **更新频率**：每日定时更新（通常在晚上8点半后）
- **自动检测**：软件启动时自动检查更新

---

## ❓ 常见问题解答

### Q1：数据下载失败
**A1**：
1. 检查软件是否为最新版本
2. 尝试安装git 客户端
3. 首次使用git clone https://github.com/hengruiyun/AI-Stock-Master.git
    日后使用git pull 命令更新

### Q2：如何提高AI分析质量？
**A2**：
1. 使用更大参数的AI模型
2. 结合多个AI模型的结果
3. 定期更新软件版本

---


### 投资建议

#### 风险提示
⚠️ **重要声明**：
- 本软件仅供学习和研究使用
- 所有分析结果不构成投资建议
- 投资有风险，决策需谨慎
- 请根据自身风险承受能力做出投资决定

#### 使用原则
1. **多重验证**：不要依赖单一工具或指标
2. **风险分散**：不要将所有资金投入单一股票
3. **止损设置**：设定合理的止损点
4. **持续学习**：不断学习和改进投资策略

---

## 📞 技术支持

### 联系方式
- **邮箱**：267278466@qq.com
- **项目地址**：https://github.com/hengruiyun/AI-Stock-Master




