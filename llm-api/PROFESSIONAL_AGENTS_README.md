# 专业智能体系统文档

## 📋 概述

本文档介绍了LLM-API项目中新增的专业智能体提示词系统，包含多个专业领域的AI助手角色，支持本地和云端模型部署。

## 🎭 专业角色目录

### 💼 商业与金融
- **金融分析师** (`financial_analyst`) - 投资分析、风险评估、市场研究
- **商业顾问** (`consultant`) - 战略规划、业务优化、管理咨询

### ⚖️ 法律与合规
- **法律顾问** (`lawyer`) - 法律咨询、合同审查、合规指导

### 🏥 健康与医疗
- **医生** (`doctor`) - 健康咨询、疾病预防、医疗建议
- **心理医生** (`psychologist`) - 心理健康、情绪管理、心理治疗
- **营养师** (`nutritionist`) - 营养咨询、膳食搭配、健康饮食

### 💪 运动与健身
- **健身教练** (`fitness_trainer`) - 运动指导、训练计划、健康生活

### 🎨 创意与设计
- **室内设计师** (`interior_designer`) - 空间设计、装修建议、家居搭配
- **摄影师** (`photographer`) - 摄影技巧、器材建议、后期处理

### 🔧 技能与手工
- **木匠** (`carpenter`) - 木工技艺、家具制作、工具使用

### 📚 教育与学习
- **教师** (`teacher`) - 教学指导、学习方法、知识传授
- **研究员** (`researcher`) - 学术研究、数据分析、文献调研

### 💻 技术与开发
- **程序员** (`coder`) - 编程指导、代码优化、技术解决方案
- **数据分析师** (`analyst`) - 数据分析、统计建模、业务洞察

### ✍️ 语言与写作
- **写作助手** (`writer`) - 文案创作、内容优化、写作指导
- **翻译专家** (`translator`) - 多语言翻译、本地化、语言学习

### 👨‍🍳 生活服务
- **专业厨师** (`chef`) - 烹饪指导、食谱推荐、营养搭配

## 🚀 快速开始

### 基本使用

```python
from client import LLMClient
from config_manager import get_config
from models import ModelProvider

# 初始化客户端
client = LLMClient(get_config())

# 创建专业智能体
success = client.create_agent_from_template(
    agent_id="my_doctor",
    template_id="doctor",
    name="我的AI医生",
    temperature=0.3,  # 医疗建议使用较低温度
    max_tokens=1500,
    model="llama-3.2-3b-instruct",
    provider=ModelProvider.LMSTUDIO
)

if success:
    # 进行咨询
    response = client.chat(
        messages=[
            {"role": "user", "content": "最近经常头痛，可能是什么原因？"}
        ],
        agent_id="my_doctor"
    )
    print(f"AI医生建议: {response}")
```

### 批量创建智能体

```python
# 创建多个专业智能体
professionals = [
    {"id": "fitness_trainer", "temp": 0.7},
    {"id": "nutritionist", "temp": 0.4},
    {"id": "psychologist", "temp": 0.5}
]

for prof in professionals:
    client.create_agent_from_template(
        agent_id=f"my_{prof['id']}",
        template_id=prof['id'],
        name=f"我的{prof['id']}",
        temperature=prof['temp'],
        max_tokens=1500
    )
```

## ⚙️ 参数调优建议

### Temperature 设置

| 角色类型 | 推荐Temperature | 说明 |
|---------|----------------|------|
| 医疗相关 (doctor, psychologist) | 0.2-0.4 | 确保医疗建议的准确性和可靠性 |
| 法律相关 (lawyer) | 0.2-0.3 | 确保法律建议的严谨性 |
| 技术相关 (coder, analyst) | 0.3-0.5 | 平衡准确性和创新性 |
| 创意相关 (designer, photographer) | 0.6-0.8 | 增加创造性和多样性 |
| 教育相关 (teacher, researcher) | 0.4-0.6 | 平衡准确性和启发性 |
| 生活服务 (chef, fitness_trainer) | 0.5-0.7 | 提供实用且有趣的建议 |

### Max Tokens 设置

- **简单咨询**: 500-800 tokens
- **详细指导**: 1000-1500 tokens  
- **复杂分析**: 1500-2000 tokens
- **教学内容**: 2000+ tokens

## 🔗 模型支持

### 本地模型

#### LM Studio
```python
from models import ModelProvider

client.create_agent_from_template(
    agent_id="local_agent",
    template_id="doctor",
    name="本地医生",
    model="llama-3.2-3b-instruct",
    provider=ModelProvider.LMSTUDIO
)
```

#### Ollama
```python
client.create_agent_from_template(
    agent_id="ollama_agent",
    template_id="fitness_trainer",
    name="Ollama健身教练",
    model="gemma2:2b",
    provider=ModelProvider.OLLAMA
)
```

### 云端API
```python
client.create_agent_from_template(
    agent_id="cloud_agent",
    template_id="lawyer",
    name="云端律师",
    model="gpt-4",
    provider=ModelProvider.OPENAI
)
```

## 🧪 测试脚本

### 基础功能测试
```bash
# 测试所有专业模板
python test_professional_agents.py

# 测试LM Studio集成
python test_lmstudio_prompts.py

# 演示完整功能
python demo_enhanced_prompt_system.py
```

### 语法检查
```bash
# 检查Python文件语法
python check_syntax.py
```

## 📁 文件结构

```
prompts/
├── fitness_trainer.json     # 健身教练模板
├── doctor.json             # 医生模板
├── psychologist.json       # 心理医生模板
├── carpenter.json          # 木匠模板
├── nutritionist.json       # 营养师模板
├── interior_designer.json  # 室内设计师模板
├── photographer.json       # 摄影师模板
├── financial_analyst.json  # 金融分析师模板
├── lawyer.json            # 法律顾问模板
└── chef.json              # 专业厨师模板

test_scripts/
├── test_professional_agents.py      # 专业智能体测试
├── test_lmstudio_prompts.py        # LM Studio集成测试
├── demo_enhanced_prompt_system.py  # 完整功能演示
└── fix_template_format.py          # 模板格式修复工具
```

## 💡 最佳实践

### 1. 角色选择
- 根据具体需求选择最合适的专业角色
- 考虑问题的复杂度和专业性要求
- 可以组合多个角色获得全面建议

### 2. 提示词优化
- 提供清晰的上下文信息
- 使用具体的例子和场景
- 明确期望的输出格式
- 适当使用角色扮演技巧

### 3. 安全考虑
- 医疗建议仅供参考，严重问题请就医
- 法律建议不能替代专业律师咨询
- 投资建议需要结合个人风险承受能力
- 所有专业建议都应该谨慎对待

### 4. 性能优化
- 根据模型性能调整参数
- 使用缓存减少重复计算
- 合理设置超时时间
- 监控资源使用情况

## 🔧 自定义模板

### 创建新模板

1. 在 `prompts/` 目录创建JSON文件
2. 按照以下格式编写:

```json
{
  "name": "角色名称",
  "role": "role_id",
  "description": "角色描述",
  "system_prompt": "详细的系统提示词",
  "examples": [{
    "user": "用户问题示例",
    "assistant": "AI回复示例"
  }],
  "tags": ["标签1", "标签2"]
}
```

3. 在 `prompt_manager.py` 中添加新的 `AgentRole`
4. 测试新模板功能

### 模板验证
```python
from prompt_manager import PromptManager

pm = PromptManager()
template = pm.load_template("your_template_id")

if template:
    print(f"模板加载成功: {template.name}")
else:
    print("模板加载失败")
```

## 🚨 故障排除

### 常见问题

1. **模板加载失败**
   - 检查JSON格式是否正确
   - 确认文件路径和权限
   - 验证模板结构完整性

2. **LM Studio连接失败**
   - 确保LM Studio正在运行
   - 检查端口配置 (默认1234)
   - 验证模型是否已加载

3. **智能体创建失败**
   - 检查template_id是否存在
   - 验证参数格式正确性
   - 确认模型和提供商匹配

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查可用模板
from prompt_manager import PromptManager
pm = PromptManager()
print("可用模板:", pm.list_templates())

# 验证配置
from config_manager import get_config
config = get_config()
print("配置信息:", config)
```

## 📈 性能监控

### 响应时间监控
```python
import time

start_time = time.time()
response = client.chat(messages=[...], agent_id="test_agent")
end_time = time.time()

print(f"响应时间: {end_time - start_time:.2f}秒")
print(f"响应长度: {len(response)}字符")
```

### 资源使用监控
```python
import psutil
import os

# 内存使用
process = psutil.Process(os.getpid())
memory_usage = process.memory_info().rss / 1024 / 1024  # MB
print(f"内存使用: {memory_usage:.2f}MB")

# CPU使用
cpu_usage = process.cpu_percent()
print(f"CPU使用: {cpu_usage:.2f}%")
```

## 🤝 贡献指南

### 添加新的专业角色

1. Fork项目仓库
2. 创建新的模板文件
3. 更新 `AgentRole` 枚举
4. 编写测试用例
5. 更新文档
6. 提交Pull Request

### 代码规范

- 使用Python 3.8+
- 遵循PEP 8代码风格
- 添加类型注解
- 编写单元测试
- 更新文档

## 📞 技术支持

- **项目地址**: [GitHub Repository]
- **问题反馈**: [Issues]
- **功能请求**: [Feature Requests]
- **文档更新**: [Documentation]

## 📄 许可证

本项目采用 [MIT License] 开源许可证。

---

*最后更新: 2024年12月*