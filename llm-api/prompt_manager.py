# -*- coding: utf-8 -*-
"""
统一提示词管理模块
提供智能体提示词定制、角色模板管理和系统提示词配置功能
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from config_manager import get_config
    from i18n import t
except ImportError:
    from config_manager import get_config
    from i18n import t


class AgentRole(Enum):
    """预定义的智能体角色"""
    ASSISTANT = "assistant"  # 通用助手
    ANALYST = "analyst"      # 分析师
    TRANSLATOR = "translator" # 翻译员
    CODER = "coder"          # 程序员
    TEACHER = "teacher"      # 教师
    WRITER = "writer"        # 写作助手
    RESEARCHER = "researcher" # 研究员
    FINANCIAL_ANALYST = "financial_analyst"  # 金融分析师
    LAWYER = "lawyer"        # 法律顾问
    CHEF = "chef"            # 专业厨师
    FITNESS_TRAINER = "fitness_trainer"  # 健身教练
    DOCTOR = "doctor"        # 医生
    PSYCHOLOGIST = "psychologist"  # 心理医生
    CARPENTER = "carpenter"  # 木匠
    NUTRITIONIST = "nutritionist"  # 营养师
    INTERIOR_DESIGNER = "interior_designer"  # 室内设计师
    PHOTOGRAPHER = "photographer"  # 摄影师
    COMPUTER_EXPERT = "computer_expert"  # 电脑专家
    MUSICIAN = "musician"    # 音乐家
    PAINTER = "painter"      # 画家
    CONSULTANT = "consultant" # 顾问
    CUSTOM = "custom"        # 自定义角色


@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    role: AgentRole
    system_prompt: str
    description: str
    parameters: Dict[str, Any] = None
    examples: List[Dict[str, str]] = None
    tags: List[str] = None
    language: str = "zh-CN"
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.examples is None:
            self.examples = []
        if self.tags is None:
            self.tags = []


@dataclass
class AgentConfig:
    """智能体配置"""
    name: str
    role: AgentRole
    system_prompt: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    description: str = ""
    custom_parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_parameters is None:
            self.custom_parameters = {}


class PromptManager:
    """提示词管理器"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        初始化提示词管理器
        
        Args:
            templates_dir: 模板文件目录，默认为项目根目录下的prompts文件夹
        """
        self.config = get_config()
        
        if templates_dir is None:
            current_dir = Path(__file__).parent
            self.templates_dir = current_dir / "prompts"
        else:
            self.templates_dir = Path(templates_dir)
        
        # 确保模板目录存在
        self.templates_dir.mkdir(exist_ok=True)
        
        # 缓存
        self._templates_cache: Dict[str, PromptTemplate] = {}
        self._agents_cache: Dict[str, AgentConfig] = {}
        
        # 初始化默认模板
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认提示词模板"""
        default_templates = {
            "assistant": PromptTemplate(
                name="通用助手",
                role=AgentRole.ASSISTANT,
                system_prompt="你是一个有用、准确、诚实的AI助手。请根据用户的问题提供清晰、准确的回答。如果你不确定答案，请诚实地说明。",
                description="通用AI助手，适用于各种日常问答和任务",
                tags=["通用", "助手", "问答"]
            ),
            "analyst": PromptTemplate(
                name="数据分析师",
                role=AgentRole.ANALYST,
                system_prompt="你是一个专业的数据分析师。请用结构化的方式分析数据，提供清晰的洞察和建议。在分析时要考虑数据的准确性、相关性和实用性。",
                description="专业数据分析师，擅长数据解读和洞察发现",
                tags=["分析", "数据", "洞察"]
            ),
            "translator": PromptTemplate(
                name="翻译专家",
                role=AgentRole.TRANSLATOR,
                system_prompt="你是一个专业的翻译专家。请提供准确、自然、符合目标语言习惯的翻译。保持原文的语调和含义，必要时提供文化背景说明。",
                description="专业翻译专家，支持多语言精准翻译",
                tags=["翻译", "语言", "本地化"]
            ),
            "coder": PromptTemplate(
                name="编程助手",
                role=AgentRole.CODER,
                system_prompt="你是一个经验丰富的程序员。请提供清晰、高效、可维护的代码解决方案。包含必要的注释和最佳实践建议。如果需要，请解释代码的工作原理。",
                description="专业编程助手，提供代码解决方案和技术指导",
                tags=["编程", "代码", "开发"]
            ),
            "teacher": PromptTemplate(
                name="教学助手",
                role=AgentRole.TEACHER,
                system_prompt="你是一个耐心的教师。请用简单易懂的方式解释概念，提供循序渐进的学习指导。根据学习者的水平调整解释的深度和复杂度。",
                description="专业教学助手，提供个性化学习指导",
                tags=["教学", "学习", "指导"]
            ),
            "writer": PromptTemplate(
                name="写作助手",
                role=AgentRole.WRITER,
                system_prompt="你是一个专业的写作助手。请帮助用户创作高质量的文本内容，注意语言的流畅性、逻辑性和表达力。根据不同的写作目的调整文风和结构。",
                description="专业写作助手，协助创作各类文本内容",
                tags=["写作", "创作", "文本"]
            ),
            "researcher": PromptTemplate(
                name="研究助手",
                role=AgentRole.RESEARCHER,
                system_prompt="你是一个严谨的研究助手。请提供基于证据的分析和结论，引用可靠的信息源，保持客观中立的立场。在不确定时明确说明限制和假设。",
                description="专业研究助手，提供严谨的研究分析",
                tags=["研究", "分析", "学术"]
            ),
            "consultant": PromptTemplate(
                name="业务顾问",
                role=AgentRole.CONSULTANT,
                system_prompt="你是一个经验丰富的业务顾问。请提供实用的商业建议和解决方案，考虑成本效益、可行性和风险因素。用清晰的商业语言表达观点。",
                description="专业业务顾问，提供商业策略和解决方案",
                tags=["商业", "咨询", "策略"]
            )
        }
        
        # 保存默认模板到文件
        for template_id, template in default_templates.items():
            self.save_template(template_id, template)
    
    def create_template(
        self,
        name: str,
        role: Union[AgentRole, str],
        system_prompt: str,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        examples: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        language: str = "zh-CN"
    ) -> PromptTemplate:
        """创建新的提示词模板"""
        if isinstance(role, str):
            try:
                role = AgentRole(role)
            except ValueError:
                role = AgentRole.CUSTOM
        
        return PromptTemplate(
            name=name,
            role=role,
            system_prompt=system_prompt,
            description=description,
            parameters=parameters or {},
            examples=examples or [],
            tags=tags or [],
            language=language
        )
    
    def save_template(self, template_id: str, template: PromptTemplate) -> None:
        """保存提示词模板到文件"""
        template_file = self.templates_dir / f"{template_id}.json"
        
        # 转换为可序列化的字典
        template_dict = asdict(template)
        template_dict['role'] = template.role.value  # 将枚举转换为字符串
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_dict, f, ensure_ascii=False, indent=2)
        
        # 更新缓存
        self._templates_cache[template_id] = template
    
    def load_template(self, template_id: str) -> Optional[PromptTemplate]:
        """加载提示词模板"""
        # 检查缓存
        if template_id in self._templates_cache:
            return self._templates_cache[template_id]
        
        template_file = self.templates_dir / f"{template_id}.json"
        
        if not template_file.exists():
            return None
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换role字符串为枚举
            if 'role' in data:
                try:
                    data['role'] = AgentRole(data['role'])
                except ValueError:
                    data['role'] = AgentRole.CUSTOM
            
            template = PromptTemplate(**data)
            
            # 缓存模板
            self._templates_cache[template_id] = template
            
            return template
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Error loading template {template_id}: {e}")
            return None
    
    def list_templates(self) -> List[str]:
        """列出所有可用的模板ID"""
        template_files = list(self.templates_dir.glob("*.json"))
        return [f.stem for f in template_files]
    
    def delete_template(self, template_id: str) -> bool:
        """删除提示词模板"""
        template_file = self.templates_dir / f"{template_id}.json"
        
        if template_file.exists():
            template_file.unlink()
            # 从缓存中移除
            self._templates_cache.pop(template_id, None)
            return True
        
        return False
    
    def create_agent(
        self,
        name: str,
        template_id: Optional[str] = None,
        role: Optional[Union[AgentRole, str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        description: str = "",
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> AgentConfig:
        """创建智能体配置"""
        # 如果指定了模板，从模板加载配置
        if template_id:
            template = self.load_template(template_id)
            if template:
                role = template.role
                system_prompt = system_prompt or template.system_prompt
                description = description or template.description
        
        # 如果没有指定角色，使用默认角色
        if role is None:
            role = AgentRole.ASSISTANT
        elif isinstance(role, str):
            try:
                role = AgentRole(role)
            except ValueError:
                role = AgentRole.CUSTOM
        
        # 如果没有指定系统提示词，使用默认的
        if system_prompt is None:
            system_prompt = "你是一个有用的AI助手。"
        
        return AgentConfig(
            name=name,
            role=role,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            provider=provider,
            description=description,
            custom_parameters=custom_parameters or {}
        )
    
    def save_agent(self, agent_id: str, agent: AgentConfig) -> None:
        """保存智能体配置"""
        agents_dir = self.templates_dir / "agents"
        agents_dir.mkdir(exist_ok=True)
        
        agent_file = agents_dir / f"{agent_id}.json"
        
        # 转换为可序列化的字典
        agent_dict = asdict(agent)
        agent_dict['role'] = agent.role.value  # 将枚举转换为字符串
        
        with open(agent_file, 'w', encoding='utf-8') as f:
            json.dump(agent_dict, f, ensure_ascii=False, indent=2)
        
        # 更新缓存
        self._agents_cache[agent_id] = agent
    
    def load_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """加载智能体配置"""
        # 检查缓存
        if agent_id in self._agents_cache:
            return self._agents_cache[agent_id]
        
        agents_dir = self.templates_dir / "agents"
        agent_file = agents_dir / f"{agent_id}.json"
        
        if not agent_file.exists():
            return None
        
        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换role字符串为枚举
            if 'role' in data:
                try:
                    data['role'] = AgentRole(data['role'])
                except ValueError:
                    data['role'] = AgentRole.CUSTOM
            
            agent = AgentConfig(**data)
            
            # 缓存智能体
            self._agents_cache[agent_id] = agent
            
            return agent
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Error loading agent {agent_id}: {e}")
            return None
    
    def list_agents(self) -> List[str]:
        """列出所有可用的智能体ID"""
        agents_dir = self.templates_dir / "agents"
        if not agents_dir.exists():
            return []
        
        agent_files = list(agents_dir.glob("*.json"))
        return [f.stem for f in agent_files]
    
    def delete_agent(self, agent_id: str) -> bool:
        """删除智能体配置"""
        agents_dir = self.templates_dir / "agents"
        agent_file = agents_dir / f"{agent_id}.json"
        
        if agent_file.exists():
            agent_file.unlink()
            # 从缓存中移除
            self._agents_cache.pop(agent_id, None)
            return True
        
        return False
    
    def format_prompt(
        self,
        template_id: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """格式化提示词模板"""
        template = self.load_template(template_id)
        if not template:
            return None
        
        if variables:
            try:
                return template.system_prompt.format(**variables)
            except KeyError as e:
                print(f"Missing variable in template {template_id}: {e}")
                return template.system_prompt
        
        return template.system_prompt
    
    def get_role_templates(self, role: Union[AgentRole, str]) -> List[str]:
        """获取指定角色的所有模板"""
        if isinstance(role, str):
            try:
                role = AgentRole(role)
            except ValueError:
                return []
        
        templates = []
        for template_id in self.list_templates():
            template = self.load_template(template_id)
            if template and template.role == role:
                templates.append(template_id)
        
        return templates
    
    def search_templates(
        self,
        query: str,
        search_in: List[str] = None
    ) -> List[str]:
        """搜索模板"""
        if search_in is None:
            search_in = ["name", "description", "tags"]
        
        query = query.lower()
        results = []
        
        for template_id in self.list_templates():
            template = self.load_template(template_id)
            if not template:
                continue
            
            match = False
            
            if "name" in search_in and query in template.name.lower():
                match = True
            elif "description" in search_in and query in template.description.lower():
                match = True
            elif "tags" in search_in:
                for tag in template.tags:
                    if query in tag.lower():
                        match = True
                        break
            
            if match:
                results.append(template_id)
        
        return results
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._templates_cache.clear()
        self._agents_cache.clear()


# 全局提示词管理器实例
_global_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器实例"""
    global _global_prompt_manager
    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager()
    return _global_prompt_manager