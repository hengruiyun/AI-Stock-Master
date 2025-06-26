# 提示词管理功能说明

本项目已集成统一的提示词自定义功能，支持智能体管理、模板系统和自定义提示词。

## 🚀 功能特性

### 1. 智能体管理
- **预定义角色**: 助手、分析师、翻译员、程序员、教师、作家、研究员、顾问
- **自定义配置**: 支持自定义系统提示词、温度、最大令牌数等参数
- **持久化存储**: 智能体配置自动保存到本地文件
- **动态切换**: 可在对话过程中随时切换智能体

### 2. 模板系统
- **内置模板**: 提供多种预定义的提示词模板
- **模板参数**: 支持模板参数化，可动态替换内容
- **快速创建**: 基于模板快速创建新的智能体
- **模板搜索**: 支持按标签和关键词搜索模板

### 3. API接口
- **RESTful API**: 完整的REST API支持
- **批量操作**: 支持批量创建、更新、删除操作
- **格式化功能**: 支持模板格式化和参数替换

## 📁 文件结构

```
llm-api/
├── prompt_manager.py      # 核心提示词管理模块
├── prompt_api.py          # REST API接口
├── client.py              # 集成智能体功能的LLM客户端
├── app.py                 # FastAPI应用入口
├── chat-webui.py          # Streamlit Web界面
├── demo_prompt_management.py  # 功能演示脚本
└── prompts/               # 提示词存储目录
    ├── templates/         # 模板文件
    └── agents/           # 智能体配置文件
```

## 🛠️ 使用方法

### 1. 命令行使用

```python
from client import LLMClient
from prompt_manager import get_prompt_manager

# 初始化客户端
client = LLMClient()
prompt_manager = get_prompt_manager()

# 查看可用模板
templates = prompt_manager.list_templates()
print(f"可用模板: {templates}")

# 从模板创建智能体
client.create_agent_from_template(
    agent_id="my_assistant",
    template_id="assistant",
    name="我的助手",
    custom_params={"temperature": 0.7}
)

# 设置当前智能体
client.set_agent("my_assistant")

# 与智能体对话
response = client.chat("你好，请介绍一下你自己")
print(response)
```

### 2. Web界面使用

启动Streamlit界面：
```bash
streamlit run chat-webui.py
```

在侧边栏中：
1. 选择或创建智能体
2. 查看智能体配置
3. 与智能体对话

### 3. API接口使用

启动FastAPI服务器：
```bash
python app.py
```

访问API文档：http://localhost:8000/docs

#### 主要API端点：

- `GET /api/prompts/templates` - 获取所有模板
- `POST /api/prompts/templates` - 创建新模板
- `GET /api/prompts/agents` - 获取所有智能体
- `POST /api/prompts/agents` - 创建新智能体
- `POST /api/prompts/chat/{agent_id}` - 与指定智能体对话

### 4. 演示脚本

运行演示脚本查看完整功能：
```bash
python demo_prompt_management.py
```

## 🤖 预定义智能体角色

| 角色 | 描述 | 适用场景 |
|------|------|----------|
| assistant | 通用助手 | 日常问答、任务协助 |
| analyst | 数据分析师 | 数据分析、报告生成 |
| translator | 翻译员 | 多语言翻译 |
| coder | 程序员 | 代码编写、调试 |
| teacher | 教师 | 教学、知识解释 |
| writer | 作家 | 内容创作、文案写作 |
| researcher | 研究员 | 学术研究、文献分析 |
| consultant | 顾问 | 专业咨询、建议提供 |

## 📝 自定义模板

### 创建新模板

```python
from prompt_manager import PromptTemplate, AgentRole

# 创建自定义模板
template = PromptTemplate(
    id="custom_helper",
    name="自定义助手",
    role=AgentRole.ASSISTANT,
    system_prompt="你是一个专业的{domain}助手，擅长{skills}。",
    description="可自定义领域和技能的助手模板",
    parameters=["domain", "skills"],
    examples=[
        {
            "domain": "医疗",
            "skills": "诊断建议和健康咨询",
            "result": "你是一个专业的医疗助手，擅长诊断建议和健康咨询。"
        }
    ],
    tags=["自定义", "通用"],
    language="zh"
)

# 保存模板
prompt_manager.save_template(template)
```

### 使用参数化模板

```python
# 格式化模板
formatted_prompt = prompt_manager.format_template(
    "custom_helper",
    domain="编程",
    skills="Python开发和代码优化"
)
print(formatted_prompt)
# 输出: "你是一个专业的编程助手，擅长Python开发和代码优化。"
```

## ⚙️ 配置说明

### 环境变量

在`.env`文件中配置API密钥：
```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Groq
GROQ_API_KEY=your_groq_api_key

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key

# 其他配置
DEFAULT_PROVIDER=openai
DEFAULT_CHAT_MODEL=gpt-4o-mini
REQUEST_TIMEOUT=30
MAX_RETRIES=3
```

### 智能体配置参数

```python
from prompt_manager import AgentConfig, AgentRole

agent_config = AgentConfig(
    id="my_agent",
    name="我的智能体",
    role=AgentRole.ASSISTANT,
    system_prompt="你是一个专业的助手...",
    temperature=0.7,        # 创造性 (0.0-2.0)
    max_tokens=2000,        # 最大输出长度
    model="gpt-4o-mini",    # 指定模型
    provider="openai",      # 指定提供商
    custom_params={         # 自定义参数
        "top_p": 0.9,
        "frequency_penalty": 0.0
    }
)
```

## 🔧 高级功能

### 1. 模板搜索

```python
# 按标签搜索
templates = prompt_manager.search_templates(tags=["编程"])

# 按关键词搜索
templates = prompt_manager.search_templates(query="翻译")

# 按角色搜索
templates = prompt_manager.get_templates_by_role(AgentRole.CODER)
```

### 2. 批量操作

```python
# 批量创建智能体
agents_data = [
    {"id": "agent1", "template_id": "assistant", "name": "助手1"},
    {"id": "agent2", "template_id": "coder", "name": "程序员1"}
]

for agent_data in agents_data:
    client.create_agent_from_template(**agent_data)
```

### 3. 动态参数

```python
# 在对话中动态设置参数
response = client.chat(
    "请帮我写一个Python函数",
    temperature=0.3,  # 临时降低创造性
    max_tokens=1000   # 限制输出长度
)
```

## 🚨 注意事项

1. **API密钥安全**: 请妥善保管API密钥，不要提交到版本控制系统
2. **文件权限**: 确保`prompts/`目录有读写权限
3. **模型兼容性**: 不同模型对参数的支持可能有差异
4. **资源使用**: 长对话可能消耗较多API配额
5. **并发限制**: 注意API提供商的并发请求限制

## 🐛 故障排除

### 常见问题

1. **智能体创建失败**
   - 检查模板ID是否存在
   - 确认智能体ID未重复
   - 验证参数格式是否正确

2. **API调用失败**
   - 检查API密钥配置
   - 确认网络连接正常
   - 查看错误日志信息

3. **模板加载错误**
   - 检查`prompts/templates/`目录权限
   - 验证JSON文件格式
   - 确认文件编码为UTF-8

### 日志调试

```python
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 查看详细错误信息
try:
    client.chat("测试消息")
except Exception as e:
    logging.error(f"对话失败: {e}")
```

## 📚 更多资源

- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Streamlit文档](https://docs.streamlit.io/)
- [LangChain文档](https://python.langchain.com/)
- [项目GitHub仓库](https://github.com/your-repo/llm-api)

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。