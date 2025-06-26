# LLM-API 接口使用指南 (AI专用)

## 概述

LLM-API 是一个统一的大语言模型接口系统，支持多个LLM提供商，包括OpenAI、Ollama、LM Studio等。本指南专为AI系统设计，提供详细的技术实现和使用方法。

## 核心架构

### 1. 主要组件

- **Client (`client.py`)**: 统一的LLM客户端接口
- **Models (`models.py`)**: 模型配置和管理
- **Config Manager (`config_manager.py`)**: 配置文件管理
- **Prompt Manager (`prompt_manager.py`)**: 智能体和提示词管理
- **I18n (`i18n.py`)**: 国际化支持
- **Utils**: 各种工具函数

### 2. 支持的提供商

```python
# 支持的提供商类型
PROVIDERS = {
    "OpenAI": "openai",
    "Ollama": "ollama", 
    "LMStudio": "lmstudio"
}
```

## 基本使用方法

### 1. 初始化客户端

```python
from client import LLMClient
from models import ModelConfig

# 创建模型配置
config = ModelConfig(
    provider="openai",
    model="gpt-3.5-turbo",
    api_key="your-api-key",
    temperature=0.7,
    max_tokens=1000
)

# 初始化客户端
client = LLMClient(config)
```

### 2. 发送消息

```python
# 简单对话
response = await client.send_message("Hello, how are you?")
print(response)

# 带系统提示词的对话
response = await client.send_message(
    message="Explain quantum computing",
    system_prompt="You are a physics professor"
)
```

### 3. 使用智能体

```python
from prompt_manager import PromptManager

# 初始化提示词管理器
prompt_manager = PromptManager()

# 获取可用智能体
agents = prompt_manager.list_agents()
print(f"Available agents: {agents}")

# 加载特定智能体
agent_config = prompt_manager.load_agent("doctor")
client.set_system_prompt(agent_config["system_prompt"])

# 使用智能体进行对话
response = await client.send_message("I have a headache")
```

## 智能体系统

### 1. 智能体配置格式

```json
{
  "name": "医生",
  "role": "doctor",
  "system_prompt": "你是一位专业的医生...",
  "temperature": 0.6,
  "max_tokens": 2000,
  "model": null,
  "provider": null,
  "description": "专业医生，提供医疗咨询",
  "custom_parameters": {}
}
```

### 2. 可用智能体列表

- `default`: 默认助手 - 通用AI助手
- `coder`: 程序员 - 编程和技术支持
- `doctor`: 医生 - 医疗健康咨询
- `translator`: 翻译员 - 多语言翻译
- `musician`: 音乐家 - 音乐相关咨询
- `painter`: 画家 - 艺术和绘画指导
- `computer_expert`: 电脑专家 - 计算机技术支持
- `psychologist`: 心理医生 - 心理健康咨询

## 配置管理

### 1. 环境变量配置

```bash
# OpenAI配置
OPENAI_API_KEY=your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1

# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434

# LM Studio配置
LMSTUDIO_BASE_URL=http://localhost:1234
```

### 2. 配置文件管理

```python
from config_manager import ConfigManager

# 初始化配置管理器
config_manager = ConfigManager()

# 保存配置
config_manager.save_config("my_config", {
    "provider": "ollama",
    "model": "llama2",
    "temperature": 0.8
})

# 加载配置
config = config_manager.load_config("my_config")
```

## 错误处理

### 1. 常见异常类型

```python
from exceptions import (
    LLMAPIError,
    ModelNotFoundError,
    ConnectionError,
    AuthenticationError
)

try:
    response = await client.send_message("Hello")
except ModelNotFoundError as e:
    print(f"Model not found: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except LLMAPIError as e:
    print(f"General API error: {e}")
```

### 2. 连接测试

```python
# 测试连接
try:
    is_connected = await client.test_connection()
    if is_connected:
        print("Connection successful")
    else:
        print("Connection failed")
except Exception as e:
    print(f"Connection test error: {e}")
```

## 国际化支持

### 1. 语言设置

```python
from i18n import set_language, Language, t

# 设置语言
set_language(Language.CHINESE)

# 使用翻译
message = t("connection_successful")
print(message)  # 输出: "连接成功！"
```

### 2. 支持的语言

- 英文 (English)
- 中文 (Chinese)

## 最佳实践

### 1. 资源管理

```python
# 使用上下文管理器
async with LLMClient(config) as client:
    response = await client.send_message("Hello")
    # 客户端会自动清理资源
```

### 2. 批量处理

```python
# 批量发送消息
messages = ["Hello", "How are you?", "Goodbye"]
responses = []

for message in messages:
    response = await client.send_message(message)
    responses.append(response)
```

### 3. 配置优化

```python
# 针对不同任务优化配置
configs = {
    "creative": {"temperature": 0.9, "max_tokens": 2000},
    "analytical": {"temperature": 0.3, "max_tokens": 1000},
    "conversational": {"temperature": 0.7, "max_tokens": 1500}
}

# 根据任务类型选择配置
task_type = "creative"
client.update_config(configs[task_type])
```

## 性能监控

### 1. 响应时间监控

```python
import time

start_time = time.time()
response = await client.send_message("Hello")
end_time = time.time()

print(f"Response time: {end_time - start_time:.2f} seconds")
```

### 2. Token使用统计

```python
# 获取使用统计
stats = client.get_usage_stats()
print(f"Total tokens used: {stats.get('total_tokens', 0)}")
print(f"Prompt tokens: {stats.get('prompt_tokens', 0)}")
print(f"Completion tokens: {stats.get('completion_tokens', 0)}")
```

## 扩展开发

### 1. 自定义智能体

```python
# 创建自定义智能体配置
custom_agent = {
    "name": "数据分析师",
    "role": "data_analyst",
    "system_prompt": "你是一位专业的数据分析师...",
    "temperature": 0.4,
    "max_tokens": 1500,
    "description": "专业数据分析和可视化专家"
}

# 保存自定义智能体
prompt_manager.save_agent("data_analyst", custom_agent)
```

### 2. 自定义提供商

```python
# 扩展新的LLM提供商
class CustomProvider:
    def __init__(self, config):
        self.config = config
    
    async def send_message(self, message, **kwargs):
        # 实现自定义提供商的消息发送逻辑
        pass
    
    async def test_connection(self):
        # 实现连接测试逻辑
        pass
```

## 故障排除

### 1. 常见问题

- **连接失败**: 检查网络连接和服务器状态
- **认证错误**: 验证API密钥是否正确
- **模型不可用**: 确认模型名称和提供商支持
- **响应超时**: 调整超时设置或检查网络延迟

### 2. 调试模式

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 客户端会输出详细的调试信息
client = LLMClient(config, debug=True)
```

## 版本兼容性

- Python 3.8+
- 支持异步操作
- 兼容主流LLM提供商API

## 安全注意事项

1. **API密钥管理**: 使用环境变量存储敏感信息
2. **输入验证**: 对用户输入进行适当的验证和清理
3. **错误处理**: 避免在错误信息中泄露敏感信息
4. **访问控制**: 实施适当的访问控制和权限管理

---

本指南为AI系统提供了完整的LLM-API使用方法。如需更多技术细节，请参考源代码和相关文档。