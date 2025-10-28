"""LLM模型定义和配置"""

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
    SILICONFLOW = "SiliconFlow"
    VOLCENGINE = "Volcengine"
    BAILIAN = "Bailian"


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

    def has_json_mode(self) -> bool:
        """检查模型是否支持JSON模式"""
        if self.supports_json_mode is not None:
            return self.supports_json_mode
            
        # 默认逻辑
        if self.is_deepseek() or self.is_gemini():
            return False
            
        # 只有某些Ollama模型支持JSON模式
        if self.is_ollama():
            json_supported_models = [
                "llama3", "llama3.1", "llama3.2", "neural-chat", 
                "mistral", "mixtral", "qwen", "codeqwen"
            ]
            return any(model in self.model_name.lower() for model in json_supported_models)
            
        # OpenAI, Anthropic, Groq, LMStudio, SiliconFlow, Volcengine, Bailian 默认支持JSON模式
        if self.is_openai() or self.is_anthropic() or self.is_groq() or self.is_lmstudio() or self.is_siliconflow() or self.is_volcengine() or self.is_bailian():
            return True
            
        return False

    def is_deepseek(self) -> bool:
        """检查是否为DeepSeek模型"""
        return self.model_name.startswith("deepseek")

    def is_gemini(self) -> bool:
        """检查是否为Gemini模型"""
        return self.model_name.startswith("gemini")

    def is_ollama(self) -> bool:
        """检查是否为Ollama模型"""
        return self.provider == ModelProvider.OLLAMA

    def is_openai(self) -> bool:
        """检查是否为OpenAI模型"""
        return self.provider == ModelProvider.OPENAI

    def is_anthropic(self) -> bool:
        """检查是否为Anthropic模型"""
        return self.provider == ModelProvider.ANTHROPIC

    def is_groq(self) -> bool:
        """检查是否为Groq模型"""
        return self.provider == ModelProvider.GROQ

    def is_lmstudio(self) -> bool:
        """检查是否为LMStudio模型"""
        return self.provider == ModelProvider.LMSTUDIO

    def is_siliconflow(self) -> bool:
        """检查是否为SiliconFlow模型"""
        return self.provider == ModelProvider.SILICONFLOW

    def is_volcengine(self) -> bool:
        """检查是否为Volcengine模型"""
        return self.provider == ModelProvider.VOLCENGINE

    def is_bailian(self) -> bool:
        """检查是否为Bailian模型"""
        return self.provider == ModelProvider.BAILIAN


def load_models_from_json(json_path: str) -> List[LLMModel]:
    """从JSON文件加载模型配置"""
    if not os.path.exists(json_path):
        return []
        
    with open(json_path, 'r', encoding='utf-8') as f:
        models_data = json.load(f)
    
    models = []
    for model_data in models_data:
        # 转换字符串提供商为ModelProvider枚举
        provider_enum = ModelProvider(model_data["provider"])
        models.append(
            LLMModel(
                display_name=model_data["display_name"],
                model_name=model_data["model_name"],
                provider=provider_enum,
                max_tokens=model_data.get("max_tokens"),
                temperature=model_data.get("temperature"),
                supports_json_mode=model_data.get("supports_json_mode"),
                supports_streaming=model_data.get("supports_streaming", True),
                context_window=model_data.get("context_window")
            )
        )
    return models


# 获取JSON文件路径
current_dir = Path(__file__).parent
api_models_json_path = current_dir / "config" / "api_models.json"
ollama_models_json_path = current_dir / "config" / "ollama_models.json"
lmstudio_models_json_path = current_dir / "config" / "lmstudio_models.json"

# 加载可用模型
AVAILABLE_MODELS = load_models_from_json(str(api_models_json_path))
OLLAMA_MODELS = load_models_from_json(str(ollama_models_json_path))
LMSTUDIO_MODELS = load_models_from_json(str(lmstudio_models_json_path))

# 创建UI所需的LLM_ORDER格式
LLM_ORDER = [model.to_choice_tuple() for model in AVAILABLE_MODELS]
OLLAMA_LLM_ORDER = [model.to_choice_tuple() for model in OLLAMA_MODELS]
LMSTUDIO_LLM_ORDER = [model.to_choice_tuple() for model in LMSTUDIO_MODELS]

# 所有模型的合并列表
ALL_MODELS = AVAILABLE_MODELS + OLLAMA_MODELS + LMSTUDIO_MODELS


def get_model_info(model_name: str, provider: str) -> Optional[LLMModel]:
    """根据模型名称和提供商获取模型信息"""
    return next(
        (model for model in ALL_MODELS 
         if model.model_name == model_name and model.provider == provider), 
        None
    )


def get_models_by_provider(provider: ModelProvider) -> List[LLMModel]:
    """根据提供商获取模型列表"""
    return [model for model in ALL_MODELS if model.provider == provider]


def list_all_models() -> List[LLMModel]:
    """获取所有可用模型列表"""
    return ALL_MODELS.copy()