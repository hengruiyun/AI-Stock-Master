"""LLM API - 统一的大语言模型API接口

这个模块提供了一个统一的接口来调用各种LLM厂商的模型，包括：
- OpenAI
- Anthropic (Claude)
- Google (Gemini)
- Groq
- DeepSeek
- Ollama (本地模型)

使用方式：
    from llm_api import LLMClient
    
    client = LLMClient()
    response = client.chat("Hello, world!", model="gpt-4o")
"""

from client import LLMClient
from llm_models import ModelProvider, LLMModel
from exceptions import LLMAPIError, ModelNotFoundError, APIKeyError
from utils import call_llm
from prompts.localized_prompts import LocalizedPrompts, PromptOptimizer
from models.analysis_models import StructuredAnalysisResult

__version__ = "1.0.0"
__all__ = ["LLMClient", "ModelProvider", "LLMModel", "LLMAPIError", "ModelNotFoundError", "APIKeyError", "StructuredAnalysisResult"]