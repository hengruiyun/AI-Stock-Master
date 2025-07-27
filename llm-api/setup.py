#!/usr/bin/env python3
"""LLM API 安装配置文件"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# 读取requirements文件
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="llm-api",
    version="1.0.0",
    author="AI Hedge Fund Team",
    author_email="team@aihedgefund.com",
    description="A unified API interface for multiple Large Language Model providers including OpenAI, Anthropic, Google, Groq, DeepSeek, Ollama, and LM Studio",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai-hedge-fund/llm-api",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Communications :: Chat",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=1.0.0",
        ],
        "all": [
            "python-dotenv>=1.0.0",
            "lmstudio>=0.1.0",
        ],
    },
    include_package_data=True,
    package_data={
        "llm_api": [
            "config/*.json",
            "*.md",
        ],
    },
    entry_points={
        "console_scripts": [
            "llm-api-test=llm_api.test_llm_api:run_tests",
        ],
    },
    keywords="llm, ai, api, openai, anthropic, ollama, lmstudio, groq, deepseek, gemini, langchain, chatbot, nlp, machine-learning",
    project_urls={
        "Bug Reports": "https://github.com/ai-hedge-fund/llm-api/issues",
        "Source": "https://github.com/ai-hedge-fund/llm-api",
        "Documentation": "https://github.com/ai-hedge-fund/llm-api/blob/main/README.md",
    },
)