"""简化的models模块，提供ModelProvider枚举和相关函数"""

import os
import json
from enum import Enum
from pydantic import BaseModel
from typing import Tuple, List, Optional
from pathlib import Path

class ModelProvider(str, Enum):
    """支持的LLM提供商枚举"""
    ANTHROPIC = "Anthropic"
    DEEPSEEK = "DeepSeek"
    GEMINI = "Gemini"
    GROQ = "Groq"
    OPENAI = "OpenAI"
    OLLAMA = "Ollama"
    LMSTUDIO = "LMStudio"

class LLMModel(BaseModel):
    """LLM模型配置类"""
    display_name: str
    model_name: str
    provider: ModelProvider
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    supports_json_mode: Optional[bool] = None
    supports_streaming: Optional[bool] = True
    context_window: Optional[int] = None

    def to_choice_tuple(self) -> Tuple[str, str, str]:
        """转换为选择元组格式"""
        return (self.display_name, self.model_name, self.provider.value)

    def is_custom(self) -> bool:
        """检查是否为自定义模型"""
        return self.model_name == "-"

def get_model_info(model_name: str) -> Optional[LLMModel]:
    """获取模型信息（简化版）"""
    return None

def list_all_models() -> List[LLMModel]:
    """列出所有模型（简化版）"""
    return []