#!/usr/bin/env python3
"""LLM API使用示例"""

import os
from pydantic import BaseModel
from typing import List

# 导入LLM API
from llm_api import LLMClient
from utils import chat, call_llm
from llm_api.exceptions import LLMAPIError, APIKeyError


class SentimentAnalysis(BaseModel):
    """情感分析结果模型"""
    sentiment: str  # positive, negative, neutral
    confidence: float  # 0.0 to 1.0
    summary: str
    keywords: List[str]


class StockAnalysis(BaseModel):
    """股票分析结果模型"""
    symbol: str
    recommendation: str  # buy, sell, hold
    target_price: float
    risk_level: str  # low, medium, high
    reasoning: str


def basic_chat_example():
    """基本聊天示例"""
    print("=== 基本聊天示例 ===")
    
    client = LLMClient()
    
    try:
        # 简单聊天
        response = client.chat("你好，请介绍一下你自己")
        print(f"AI回复: {response}")
        
        # 带系统消息的聊天
        response = client.chat(
            "分析一下苹果公司的投资价值",
            system_message="你是一位专业的金融分析师",
            model="gpt-4o",
            provider="OpenAI"
        )
        print(f"\n金融分析: {response}")
        
    except APIKeyError as e:
        print(f"API密钥错误: {e}")
    except LLMAPIError as e:
        print(f"LLM API错误: {e}")


def structured_output_example():
    """结构化输出示例"""
    print("\n=== 结构化输出示例 ===")
    
    client = LLMClient()
    
    try:
        # 情感分析
        text = "今天股市大涨，我的投资组合收益率达到了15%，心情非常好！"
        
        result = client.chat_with_structured_output(
            f"请分析以下文本的情感：'{text}'",
            pydantic_model=SentimentAnalysis,
            model="gpt-4o",
            provider="OpenAI"
        )
        
        print(f"情感: {result.sentiment}")
        print(f"置信度: {result.confidence}")
        print(f"摘要: {result.summary}")
        print(f"关键词: {', '.join(result.keywords)}")
        
        # 股票分析
        stock_result = client.chat_with_structured_output(
            "分析特斯拉(TSLA)股票的投资价值，当前价格约为250美元",
            pydantic_model=StockAnalysis,
            system_message="你是一位资深的股票分析师，请提供专业的投资建议",
            model="gpt-4o"
        )
        
        print(f"\n股票代码: {stock_result.symbol}")
        print(f"投资建议: {stock_result.recommendation}")
        print(f"目标价格: ${stock_result.target_price}")
        print(f"风险等级: {stock_result.risk_level}")
        print(f"分析理由: {stock_result.reasoning}")
        
    except Exception as e:
        print(f"结构化输出错误: {e}")


def ollama_example():
    """Ollama本地模型示例"""
    print("\n=== Ollama本地模型示例 ===")
    
    client = LLMClient()
    
    try:
        # 使用Ollama模型
        response = client.chat(
            "写一首关于人工智能的短诗",
            model="llama3.1:latest",
            provider="Ollama"
        )
        print(f"AI诗歌: {response}")
        
        # Ollama结构化输出
        analysis = client.chat_with_structured_output(
            "分析'人工智能将改变世界'这句话的情感",
            pydantic_model=SentimentAnalysis,
            model="llama3.1:latest",
            provider="Ollama"
        )
        
        print(f"\nOllama情感分析:")
        print(f"情感: {analysis.sentiment}")
        print(f"置信度: {analysis.confidence}")
        
    except Exception as e:
        print(f"Ollama示例错误: {e}")
        print("提示: 请确保Ollama已安装并且模型已下载")


def compatibility_example():
    """兼容性示例（与原有代码兼容）"""
    print("\n=== 兼容性示例 ===")
    
    try:
        # 使用兼容的chat函数
        response = chat(
            "什么是量化交易？",
            model="gpt-4o",
            provider="OpenAI"
        )
        print(f"量化交易解释: {response}")
        
        # 使用兼容的call_llm函数
        result = call_llm(
            prompt="分析比特币的投资风险",
            pydantic_model=SentimentAnalysis,
            model_name="gpt-4o",
            provider="OpenAI"
        )
        
        print(f"\n比特币风险分析:")
        print(f"情感: {result.sentiment}")
        print(f"摘要: {result.summary}")
        
    except Exception as e:
        print(f"兼容性示例错误: {e}")


def model_info_example():
    """模型信息示例"""
    print("\n=== 模型信息示例 ===")
    
    client = LLMClient()
    
    # 列出所有可用模型
    models = client.list_available_models()
    print(f"可用模型数量: {len(models)}")
    
    # 显示前5个模型
    print("\n前5个模型:")
    for model in models[:5]:
        print(f"- {model.display_name} ({model.provider})")
    
    # 获取特定模型信息
    model_info = client.get_model_info("gpt-4o", "OpenAI")
    if model_info:
        print(f"\nGPT-4o信息:")
        print(f"显示名称: {model_info.display_name}")
        print(f"支持JSON模式: {model_info.has_json_mode()}")
        print(f"支持流式输出: {model_info.supports_streaming}")


def main():
    """主函数"""
    print("LLM API 使用示例")
    print("=" * 50)
    
    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY"):
        print("警告: 未设置OPENAI_API_KEY环境变量")
        print("请在.env文件中设置API密钥")
        return
    
    try:
        # 运行各种示例
        basic_chat_example()
        structured_output_example()
        compatibility_example()
        model_info_example()
        
        # 如果Ollama可用，运行Ollama示例
        from llm_api.ollama_utils import is_ollama_installed
        if is_ollama_installed():
            ollama_example()
        else:
            print("\n提示: 安装Ollama以体验本地模型功能")
            
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n运行示例时出错: {e}")


if __name__ == "__main__":
    main()