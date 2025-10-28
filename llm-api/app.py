# -*- coding: utf-8 -*-
"""
LLM API FastAPI应用
提供LLM聊天和提示词管理的REST API服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client import LLMClient
    from llm_models import ModelProvider, LLMModel, get_model_info, list_all_models
    from exceptions import LLMAPIError, ModelNotFoundError, APIKeyError
    from config_manager import get_config
    from prompt_api import router as prompt_router
    from i18n import t
except ImportError as e:
    print(f"Module import failed: {e}")
    print("Please ensure you are running this script in the llm-api project directory")
    sys.exit(1)


# 创建FastAPI应用
app = FastAPI(
    title="LLM API with Prompt Management",
    description="统一的LLM API服务，支持多个提供商和智能体提示词管理",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含提示词管理路由
app.include_router(prompt_router)


# Pydantic模型定义
class ChatRequest(BaseModel):
    """聊天请求"""
    message: Union[str, List[Dict[str, str]]] = Field(..., description="用户消息")
    model: Optional[str] = Field(default=None, description="模型名称")
    provider: Optional[str] = Field(default=None, description="提供商名称")
    system_message: Optional[str] = Field(default=None, description="系统消息")
    temperature: Optional[float] = Field(default=None, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    agent_id: Optional[str] = Field(default=None, description="智能体ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str = Field(..., description="AI回复")
    model_used: Optional[str] = Field(default=None, description="使用的模型")
    provider_used: Optional[str] = Field(default=None, description="使用的提供商")
    agent_used: Optional[str] = Field(default=None, description="使用的智能体")


class ModelInfo(BaseModel):
    """模型信息"""
    name: str
    display_name: str
    provider: str
    supports_json_mode: Optional[bool] = None
    supports_streaming: Optional[bool] = None


class ModelsResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelInfo]


class ProvidersResponse(BaseModel):
    """提供商列表响应"""
    providers: List[str]


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    message: str


# 全局LLM客户端实例
client = LLMClient()


@app.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "message": "LLM API with Prompt Management",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        message="LLM API service is running"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        response = client.chat(
            message=request.message,
            model=request.model,
            provider=request.provider,
            system_message=request.system_message,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            agent_id=request.agent_id
        )
        
        return ChatResponse(
            response=response,
            model_used=request.model or client.default_model,
            provider_used=request.provider or client.default_provider,
            agent_used=request.agent_id
        )
    except LLMAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models", response_model=ModelsResponse)
async def list_models():
    """列出所有可用的模型"""
    try:
        models = list_all_models()
        model_list = []
        
        for model in models:
            model_info = ModelInfo(
                name=model.model_name,
                display_name=model.display_name,
                provider=model.provider.value,
                supports_json_mode=getattr(model, 'supports_json_mode', None),
                supports_streaming=getattr(model, 'supports_streaming', None)
            )
            model_list.append(model_info)
        
        return ModelsResponse(models=model_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{model_name}", response_model=ModelInfo)
async def get_model_details(model_name: str):
    """获取指定模型的详细信息"""
    try:
        model = get_model_info(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
        
        return ModelInfo(
            name=model.model_name,
            display_name=model.display_name,
            provider=model.provider.value,
            supports_json_mode=getattr(model, 'supports_json_mode', None),
            supports_streaming=getattr(model, 'supports_streaming', None)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """列出所有可用的提供商"""
    try:
        providers = [provider.value for provider in ModelProvider]
        return ProvidersResponse(providers=providers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/providers/{provider_name}/models", response_model=ModelsResponse)
async def list_provider_models(provider_name: str):
    """列出指定提供商的所有模型"""
    try:
        # 验证提供商名称
        try:
            provider = ModelProvider(provider_name)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
        
        all_models = list_all_models()
        provider_models = [model for model in all_models if model.provider == provider]
        
        model_list = []
        for model in provider_models:
            model_info = ModelInfo(
                name=model.model_name,
                display_name=model.display_name,
                provider=model.provider.value,
                supports_json_mode=getattr(model, 'supports_json_mode', None),
                supports_streaming=getattr(model, 'supports_streaming', None)
            )
            model_list.append(model_info)
        
        return ModelsResponse(models=model_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 异常处理器
@app.exception_handler(LLMAPIError)
async def llm_api_exception_handler(request, exc: LLMAPIError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(ModelNotFoundError)
async def model_not_found_exception_handler(request, exc: ModelNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)}
    )


@app.exception_handler(APIKeyError)
async def api_key_exception_handler(request, exc: APIKeyError):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)}
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"Starting LLM API server on {args.host}:{args.port}")
    print(f"API documentation available at: http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )