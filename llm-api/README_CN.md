# LLM API - 统一大语言模型接口

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/llm-api.svg)](https://badge.fury.io/py/llm-api)

一个统一的API接口，支持多个大语言模型提供商，包括OpenAI、Anthropic、Google、Groq、DeepSeek、Ollama和LM Studio。

[English](README_EN.md) | 中文

## 功能特性

- 🔄 **统一接口**: 一个API调用所有主流LLM提供商
- 🎯 **结构化输出**: 支持Pydantic模型的结构化响应
- 🔧 **自动重试**: 内置重试机制和错误处理
- 🏠 **本地模型**: 完整的Ollama和LM Studio支持，包含模型管理
- ⚡ **缓存机制**: 模型实例缓存，提升性能
- 🛡️ **类型安全**: 完整的类型提示支持
- 🌐 **多语言**: 支持中文和英文
- 💬 **Web界面**: 基于Streamlit的聊天Web界面，支持所有提供商

## 支持的提供商

| 提供商 | 示例模型 | 环境变量 |
|--------|----------|----------|
| OpenAI | gpt-4o, gpt-4.1 | `OPENAI_API_KEY` |
| Anthropic | claude-3-5-haiku-latest | `ANTHROPIC_API_KEY` |
| Google | gemini-2.5-flash-preview | `GOOGLE_API_KEY` |
| Groq | llama-4-scout-17b | `GROQ_API_KEY` |
| DeepSeek | deepseek-reasoner | `DEEPSEEK_API_KEY` |
| Ollama | llama3.1:latest | 无需API密钥 |
| LM Studio | llama3.1:latest | 无需API密钥 |

## 安装

### 从PyPI安装（推荐）

```bash
pip install llm-api
```

### 从源码安装

```bash
git clone https://github.com/ai-hedge-fund/llm-api.git
cd llm-api
pip install -e .
```

### 开发环境安装

```bash
git clone https://github.com/ai-hedge-fund/llm-api.git
cd llm-api
pip install -e ".[dev]"
```

## 快速开始

### 基本聊天

```python
from llm_api import LLMClient

# 创建客户端
client = LLMClient()

# 简单聊天
response = client.chat("你好，世界！")
print(response)

# 指定模型和提供商
response = client.chat(
    "解释一下机器学习",
    model="gpt-4o",
    provider="OpenAI"
)
print(response)
```

### 结构化输出

```python
from pydantic import BaseModel
from llm_api import LLMClient

class AnalysisResult(BaseModel):
    sentiment: str
    confidence: float
    summary: str

client = LLMClient()

result = client.chat_with_structured_output(
    "分析这段文本的情感：'今天天气真好，心情很愉快！'",
    pydantic_model=AnalysisResult,
    model="gpt-4o"
)

print(f"情感: {result.sentiment}")
print(f"置信度: {result.confidence}")
print(f"摘要: {result.summary}")
```

## Chat Web UI

LLM-API 提供了一个基于 Streamlit 的现代化聊天 Web 界面，支持所有集成的 LLM 提供商。

### 启动 Web 界面

```bash
# 在项目目录中运行
streamlit run chat-webui.py
```

访问 `http://localhost:8501` 即可使用聊天界面。

### Web 界面功能

- 🎨 **现代化UI**: 美观的聊天界面，支持深色/浅色主题
- 🔄 **实时切换**: 无需重启即可切换不同的模型和提供商
- 📊 **状态监控**: 实时显示本地服务器（Ollama/LM Studio）状态
- 🔧 **智能缓存**: 优化的模型配置加载，避免重复请求
- 💾 **对话历史**: 保持对话上下文，支持清空历史
- 🛠️ **调试信息**: 详细的错误信息和连接状态显示
- 🔍 **模型管理**: 查看可用模型列表，支持本地和云端模型

### 使用步骤

1. **选择提供商**: 从侧边栏选择 LLM 提供商
2. **选择模型**: 根据提供商选择具体模型
3. **连接测试**: 点击"连接模型"进行连接测试
4. **开始聊天**: 在聊天框中输入消息开始对话

### 本地服务器支持

- **Ollama**: 自动检测服务状态，显示可用模型列表
- **LM Studio**: 监控服务器状态，获取已加载模型
- **状态指示**: 实时显示服务器运行状态和连接信息
- **一键刷新**: 支持手动刷新服务器状态和模型列表

### 环境配置提示

Web 界面提供详细的环境配置指导：
- API 密钥设置说明
- 本地服务器启动方法
- 常见问题解决方案
- 调试信息显示

### 使用Ollama本地模型

```python
from llm_api import LLMClient

client = LLMClient()

# 使用本地Ollama模型
response = client.chat(
    "写一首关于春天的诗",
    model="llama3.1:latest",
    provider="Ollama"
)
print(response)
```

### 使用LM Studio本地模型

```python
from llm_api import LLMClient

client = LLMClient()

# 使用LM Studio模型
response = client.chat(
    "解释量子计算的原理",
    model="llama-3.2-1b-instruct",  # 替换为你加载的模型名称
    provider="LMStudio"
)
print(response)
```



### 兼容原有代码

```python
# 兼容原有的call_llm函数
from llm_api.utils import call_llm
from pydantic import BaseModel

class MyResponse(BaseModel):
    answer: str
    confidence: float

result = call_llm(
    prompt="什么是人工智能？",
    pydantic_model=MyResponse,
    model_name="gpt-4o",
    provider="OpenAI"
)
```

## 配置

### 环境变量

创建`.env`文件并设置相应的API密钥：

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1  # 可选

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Google
GOOGLE_API_KEY=your_google_api_key

# Groq
GROQ_API_KEY=your_groq_api_key

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key

# Ollama（本地）
OLLAMA_HOST=localhost  # 可选
OLLAMA_BASE_URL=http://localhost:11434  # 可选

# LM Studio（本地）
LMSTUDIO_HOST=localhost  # 可选
LMSTUDIO_PORT=1234  # 可选
LMSTUDIO_BASE_URL=http://localhost:1234  # 可选


```

### 模型配置

模型配置存储在 `config/` 目录中：

- `api_models.json`: API模型配置
- `ollama_models.json`: Ollama模型配置
- `lmstudio_models.json`: LM Studio模型配置

你可以修改这些配置文件来添加新模型或调整现有模型设置。

## API参考

### LLMClient类

#### 初始化

```python
client = LLMClient(
    default_model="gpt-4o",  # 默认模型
    default_provider="OpenAI"  # 默认提供商
)
```

#### 方法

- `chat()`: 基本聊天接口
- `chat_with_structured_output()`: 结构化输出接口
- `get_model()`: 获取模型实例
- `list_available_models()`: 列出可用模型
- `get_model_info()`: 获取模型信息
- `clear_cache()`: 清除模型缓存

### 工具函数

```python
from llm_api.utils import chat, call_llm, get_model, list_models

# 简单聊天
response = chat("你好")

# 结构化输出（兼容原有接口）
result = call_llm(prompt, MyModel)

# 获取模型实例
model = get_model("gpt-4o", "OpenAI")

# 列出所有模型
models = list_models()
```

## Ollama支持

LLM-API提供完整的Ollama支持，包括：

- 自动检测Ollama安装
- 自动启动Ollama服务
- 自动下载模型
- 模型管理（下载、删除）
- Docker环境支持





### LM Studio设置

1. **下载并安装LM Studio**: 从 [lmstudio.ai](https://lmstudio.ai) 下载
2. **加载模型**: 在LM Studio中下载并加载一个模型
3. **启动本地服务器**: 切换到"Local Server"标签页，点击"Start Server"
4. **配置端口**: 默认运行在 `http://localhost:1234`

### LM Studio模型管理

```python
from llm_api.lmstudio_utils import (
    ensure_lmstudio_server,
    list_lmstudio_models,
    get_lmstudio_info
)

# 检查LM Studio服务器状态
if ensure_lmstudio_server():
    print("LM Studio服务器正在运行")

# 获取可用模型列表
models = list_lmstudio_models()
print(f"可用模型: {models}")

# 获取服务器信息
info = get_lmstudio_info()
print(f"服务器信息: {info}")
```

### Ollama模型管理

```python
from llm_api.ollama_utils import (
    ensure_ollama_and_model,
    get_locally_available_models,
    download_model
)

# 确保模型可用（如果不存在会自动下载）
ensure_ollama_and_model("llama3.1:latest")

# 获取本地可用模型
models = get_locally_available_models()

# 手动下载模型
download_model("gemma3:4b")
```

## LM Studio支持

LLM-API提供完整的LM Studio支持，包括：

- 自动检测LM Studio服务器状态
- 获取已加载的模型列表
- 模型信息查询
- 兼容OpenAI API格式

### LM Studio设置

1. **下载并安装LM Studio**: 从 [lmstudio.ai](https://lmstudio.ai) 下载
2. **加载模型**: 在LM Studio中下载并加载一个模型
3. **启动本地服务器**: 切换到"Local Server"标签，点击"Start Server"
4. **配置端口**: 默认运行在 `http://localhost:1234`

### LM Studio模型管理

```python
from llm_api.lmstudio_utils import (
    ensure_lmstudio_server,
    list_lmstudio_models,
    get_lmstudio_info
)

# 检查LM Studio服务器状态
if ensure_lmstudio_server():
    print("LM Studio服务器正在运行")

# 获取可用模型列表
models = list_lmstudio_models()
print(f"可用模型: {models}")

# 获取服务器信息
info = get_lmstudio_info()
print(f"服务器信息: {info}")
```

## 错误处理

LLM-API提供了完整的错误处理机制：

```python
from llm_api.exceptions import (
    LLMAPIError,
    ModelNotFoundError,
    APIKeyError,
    ModelProviderError,
    OllamaError,
    LMStudioError
)

try:
    response = client.chat("Hello")
except APIKeyError as e:
    print(f"API密钥错误: {e}")
except LMStudioError as e:
    print(f"LM Studio错误: {e}")
except OllamaError as e:
    print(f"Ollama错误: {e}")
except LLMAPIError as e:
    print(f"API密钥错误: {e}")
except ModelNotFoundError as e:
    print(f"模型未找到: {e}")
except LLMAPIError as e:
    print(f"LLM API错误: {e}")
```

## 最佳实践

1. **环境变量管理**: 使用`.env`文件管理API密钥
2. **模型选择**: 根据任务需求选择合适的模型
3. **错误处理**: 始终包含适当的错误处理
4. **缓存利用**: 重复使用同一客户端实例以利用缓存
5. **结构化输出**: 使用Pydantic模型确保输出格式一致

## 开发工具

### 配置验证

使用配置验证脚本检查环境设置：

```bash
python validate_config.py
```

该脚本会检查：
- 依赖包安装状态
- 配置文件格式
- 环境变量设置
- Ollama安装状态
- 基本功能测试

### 性能测试

运行性能基准测试：

```bash
python benchmark.py
```

测试包括：
- 顺序请求测试
- 并发请求测试
- 结构化输出测试
- 响应时间统计

### 单元测试

运行完整的单元测试套件：

```bash
python test_llm_api.py
```

或使用pytest：

```bash
pip install pytest
pytest test_llm_api.py -v
```

### 包安装

安装为Python包：

```bash
pip install -e .
```

安装后可以使用命令行工具：

```bash
llm-api-test  # 运行测试套件
```

### 性能测试

运行性能基准测试：

```bash
python benchmark.py
```

测试包括：
- 顺序请求测试
- 并发请求测试
- 结构化输出测试
- 响应时间统计

### 单元测试

运行完整的单元测试套件：

```bash
python test_llm_api.py
```



## 项目结构

```
llm-api/
├── __init__.py              # 主入口文件
├── client.py                # 核心LLMClient类
├── models.py                # 模型定义和配置
├── exceptions.py            # 自定义异常类
├── utils.py                 # 兼容性工具函数
├── ollama_utils.py          # Ollama管理工具
├── lmstudio_utils.py        # LM Studio管理工具
├── config_manager.py        # 配置管理
├── langchain_lmstudio.py    # LangChain LM Studio适配器
├── setup.py                 # 包安装配置
├── requirements.txt         # 依赖列表
├── README.md               # 项目文档（中文）
├── README_EN.md            # 项目文档（英文）
├── example.py              # 使用示例
├── example_lmstudio.py     # LM Studio示例
├── test_llm_api.py         # 单元测试
├── test_lmstudio.py        # LM Studio测试
├── validate_config.py      # 配置验证脚本
├── benchmark.py            # 性能测试脚本
└── config/
    ├── __init__.py
    ├── api_models.json     # API模型配置
    ├── ollama_models.json  # Ollama模型配置
    └── lmstudio_models.json # LM Studio模型配置
```

## 贡献

我们欢迎贡献！请查看我们的[贡献指南](CONTRIBUTING.md)了解详情。

### 开发设置

1. Fork仓库
2. 克隆你的fork: `git clone https://github.com/yourusername/llm-api.git`
3. 创建虚拟环境: `python -m venv venv`
4. 激活虚拟环境: `source venv/bin/activate` (Linux/Mac) 或 `venv\Scripts\activate` (Windows)
5. 安装开发依赖: `pip install -e ".[dev]"`
6. 运行测试: `pytest`

### 代码风格

我们使用以下工具来保证代码质量：

- **Black**: 代码格式化
- **Flake8**: 代码检查
- **MyPy**: 类型检查
- **Pytest**: 测试

运行所有检查：

```bash
black .
flake8 .
mypy .
pytest
```

## 更新日志

查看[CHANGELOG.md](CHANGELOG.md)了解版本历史和变更。

## 许可证

本项目采用MIT许可证。详见 [LICENSE](LICENSE) 文件。

## 支持

如果你遇到任何问题或有疑问：

1. 查看[文档](README.md)
2. 搜索[现有问题](https://github.com/ai-hedge-fund/llm-api/issues)
3. 创建[新问题](https://github.com/ai-hedge-fund/llm-api/issues/new)

## 致谢

- [LangChain](https://github.com/langchain-ai/langchain) 提供了优秀的LLM框架
- [Pydantic](https://github.com/pydantic/pydantic) 提供了数据验证
- [Ollama](https://ollama.ai/) 提供了本地模型支持
- [LM Studio](https://lmstudio.ai/) 提供了本地模型管理
- 所有LLM提供商提供了出色的API