# -*- coding: utf-8 -*-
"""
提示词管理API端点
提供智能体和提示词模板的REST API接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

try:
    from prompt_manager import get_prompt_manager, AgentRole, PromptTemplate, AgentConfig
from client import LLMClient
from i18n import t
except ImportError:
    from prompt_manager import get_prompt_manager, AgentRole, PromptTemplate, AgentConfig
    from client import LLMClient
    from i18n import t


# Pydantic模型定义
class PromptTemplateRequest(BaseModel):
    """创建提示词模板请求"""
    name: str = Field(..., description="模板名称")
    role: str = Field(..., description="智能体角色")
    system_prompt: str = Field(..., description="系统提示词")
    description: str = Field(default="", description="模板描述")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="模板参数")
    examples: Optional[List[Dict[str, str]]] = Field(default=None, description="示例对话")
    tags: Optional[List[str]] = Field(default=None, description="标签")
    language: str = Field(default="zh-CN", description="语言")


class PromptTemplateResponse(BaseModel):
    """提示词模板响应"""
    name: str
    role: str
    system_prompt: str
    description: str
    parameters: Dict[str, Any]
    examples: List[Dict[str, str]]
    tags: List[str]
    language: str


class AgentConfigRequest(BaseModel):
    """创建智能体配置请求"""
    name: str = Field(..., description="智能体名称")
    template_id: Optional[str] = Field(default=None, description="基于的模板ID")
    role: Optional[str] = Field(default=None, description="智能体角色")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")
    model: Optional[str] = Field(default=None, description="模型名称")
    provider: Optional[str] = Field(default=None, description="提供商名称")
    description: str = Field(default="", description="智能体描述")
    custom_parameters: Optional[Dict[str, Any]] = Field(default=None, description="自定义参数")


class AgentConfigResponse(BaseModel):
    """智能体配置响应"""
    name: str
    role: str
    system_prompt: str
    temperature: float
    max_tokens: Optional[int]
    model: Optional[str]
    provider: Optional[str]
    description: str
    custom_parameters: Dict[str, Any]


class ChatWithAgentRequest(BaseModel):
    """使用智能体聊天请求"""
    message: Union[str, List[Dict[str, str]]] = Field(..., description="用户消息")
    agent_id: Optional[str] = Field(default=None, description="智能体ID")
    model: Optional[str] = Field(default=None, description="模型名称")
    provider: Optional[str] = Field(default=None, description="提供商名称")
    system_message: Optional[str] = Field(default=None, description="系统消息")
    temperature: Optional[float] = Field(default=None, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, description="最大token数")


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str = Field(..., description="AI回复")
    agent_used: Optional[str] = Field(default=None, description="使用的智能体ID")


class TemplateListResponse(BaseModel):
    """模板列表响应"""
    templates: List[str] = Field(..., description="模板ID列表")


class AgentListResponse(BaseModel):
    """智能体列表响应"""
    agents: List[str] = Field(..., description="智能体ID列表")


class RoleListResponse(BaseModel):
    """角色列表响应"""
    roles: List[str] = Field(..., description="可用角色列表")


# 创建路由器
router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates():
    """列出所有提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        templates = prompt_manager.list_templates()
        return TemplateListResponse(templates=templates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=PromptTemplateResponse)
async def get_template(template_id: str):
    """获取指定的提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        template = prompt_manager.load_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        return PromptTemplateResponse(
            name=template.name,
            role=template.role.value,
            system_prompt=template.system_prompt,
            description=template.description,
            parameters=template.parameters,
            examples=template.examples,
            tags=template.tags,
            language=template.language
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}", response_model=dict)
async def create_template(template_id: str, request: PromptTemplateRequest):
    """创建新的提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        
        template = prompt_manager.create_template(
            name=request.name,
            role=request.role,
            system_prompt=request.system_prompt,
            description=request.description,
            parameters=request.parameters,
            examples=request.examples,
            tags=request.tags,
            language=request.language
        )
        
        prompt_manager.save_template(template_id, template)
        
        return {"message": f"Template {template_id} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/templates/{template_id}", response_model=dict)
async def update_template(template_id: str, request: PromptTemplateRequest):
    """更新提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        
        # 检查模板是否存在
        existing_template = prompt_manager.load_template(template_id)
        if not existing_template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        template = prompt_manager.create_template(
            name=request.name,
            role=request.role,
            system_prompt=request.system_prompt,
            description=request.description,
            parameters=request.parameters,
            examples=request.examples,
            tags=request.tags,
            language=request.language
        )
        
        prompt_manager.save_template(template_id, template)
        
        return {"message": f"Template {template_id} updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}", response_model=dict)
async def delete_template(template_id: str):
    """删除提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        
        if prompt_manager.delete_template(template_id):
            return {"message": f"Template {template_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    """列出所有智能体"""
    try:
        prompt_manager = get_prompt_manager()
        agents = prompt_manager.list_agents()
        return AgentListResponse(agents=agents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentConfigResponse)
async def get_agent(agent_id: str):
    """获取指定的智能体配置"""
    try:
        prompt_manager = get_prompt_manager()
        agent = prompt_manager.load_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        return AgentConfigResponse(
            name=agent.name,
            role=agent.role.value,
            system_prompt=agent.system_prompt,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            model=agent.model,
            provider=agent.provider,
            description=agent.description,
            custom_parameters=agent.custom_parameters
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}", response_model=dict)
async def create_agent(agent_id: str, request: AgentConfigRequest):
    """创建新的智能体配置"""
    try:
        prompt_manager = get_prompt_manager()
        
        agent = prompt_manager.create_agent(
            name=request.name,
            template_id=request.template_id,
            role=request.role,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            model=request.model,
            provider=request.provider,
            description=request.description,
            custom_parameters=request.custom_parameters
        )
        
        prompt_manager.save_agent(agent_id, agent)
        
        return {"message": f"Agent {agent_id} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_id}", response_model=dict)
async def update_agent(agent_id: str, request: AgentConfigRequest):
    """更新智能体配置"""
    try:
        prompt_manager = get_prompt_manager()
        
        # 检查智能体是否存在
        existing_agent = prompt_manager.load_agent(agent_id)
        if not existing_agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        
        agent = prompt_manager.create_agent(
            name=request.name,
            template_id=request.template_id,
            role=request.role,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            model=request.model,
            provider=request.provider,
            description=request.description,
            custom_parameters=request.custom_parameters
        )
        
        prompt_manager.save_agent(agent_id, agent)
        
        return {"message": f"Agent {agent_id} updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}", response_model=dict)
async def delete_agent(agent_id: str):
    """删除智能体配置"""
    try:
        prompt_manager = get_prompt_manager()
        
        if prompt_manager.delete_agent(agent_id):
            return {"message": f"Agent {agent_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatWithAgentRequest):
    """使用智能体进行聊天"""
    try:
        client = LLMClient()
        
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
            agent_used=request.agent_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles", response_model=RoleListResponse)
async def list_roles():
    """列出所有可用的智能体角色"""
    try:
        roles = [role.value for role in AgentRole]
        return RoleListResponse(roles=roles)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/search", response_model=TemplateListResponse)
async def search_templates(
    query: str = Query(..., description="搜索关键词"),
    search_in: List[str] = Query(default=["name", "description", "tags"], description="搜索范围")
):
    """搜索提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        results = prompt_manager.search_templates(query, search_in)
        return TemplateListResponse(templates=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/role/{role}", response_model=TemplateListResponse)
async def get_templates_by_role(role: str):
    """根据角色获取模板"""
    try:
        prompt_manager = get_prompt_manager()
        templates = prompt_manager.get_role_templates(role)
        return TemplateListResponse(templates=templates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/format", response_model=dict)
async def format_template(
    template_id: str,
    variables: Optional[Dict[str, Any]] = None
):
    """格式化提示词模板"""
    try:
        prompt_manager = get_prompt_manager()
        formatted_prompt = prompt_manager.format_prompt(template_id, variables)
        
        if formatted_prompt is None:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        return {
            "template_id": template_id,
            "formatted_prompt": formatted_prompt,
            "variables": variables or {}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))