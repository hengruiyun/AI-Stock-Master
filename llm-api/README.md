# LLM API - Unified Large Language Model Interface

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/llm-api.svg)](https://badge.fury.io/py/llm-api)

A unified API interface for multiple Large Language Model providers, including OpenAI, Anthropic, Google, Groq, DeepSeek, Ollama, and LM Studio.

## Features

- 🔄 **Unified Interface**: One API to call all major LLM providers
- 🎯 **Structured Output**: Support for Pydantic model structured responses
- 🔧 **Auto Retry**: Built-in retry mechanism and error handling
- 🏠 **Local Models**: Complete Ollama and LM Studio support with model management
- ⚡ **Caching**: Model instance caching for improved performance
- 🛡️ **Type Safety**: Full type hints support
- 🌐 **Multi-language**: Support for both Chinese and English
- 💬 **Web Interface**: Streamlit-based chat web interface supporting all providers

## Supported Providers

| Provider | Example Models | Environment Variable |
|----------|----------------|---------------------|
| OpenAI | gpt-4o, gpt-4.1 | `OPENAI_API_KEY` |
| Anthropic | claude-3-5-haiku-latest | `ANTHROPIC_API_KEY` |
| Google | gemini-2.5-flash-preview | `GOOGLE_API_KEY` |
| Groq | llama-4-scout-17b | `GROQ_API_KEY` |
| DeepSeek | deepseek-reasoner | `DEEPSEEK_API_KEY` |
| Ollama | llama3.1:latest | No API key required |
| LM Studio | llama3.1:latest | No API key required |

## Installation

### From PyPI (Recommended)

```bash
pip install llm-api
```

### From Source

```bash
git clone https://github.com/ai-hedge-fund/llm-api.git
cd llm-api
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/ai-hedge-fund/llm-api.git
cd llm-api
pip install -e ".[dev]"
```

## Quick Start

### Basic Chat

```python
from llm_api import LLMClient

# Create client
client = LLMClient()

# Simple chat
response = client.chat("Hello, world!")
print(response)

# Specify model and provider
response = client.chat(
    "Explain machine learning",
    model="gpt-4o",
    provider="OpenAI"
)
print(response)
```

### Structured Output

```python
from pydantic import BaseModel
from llm_api import LLMClient

class AnalysisResult(BaseModel):
    sentiment: str
    confidence: float
    summary: str

client = LLMClient()

result = client.chat_with_structured_output(
    "Analyze the sentiment: 'Today is a beautiful day, I feel great!'",
    pydantic_model=AnalysisResult,
    model="gpt-4o"
)

print(f"Sentiment: {result.sentiment}")
print(f"Confidence: {result.confidence}")
print(f"Summary: {result.summary}")
```

## Chat Web UI

LLM-API provides a modern Streamlit-based chat web interface supporting all integrated LLM providers.

### Launch Web Interface

```bash
# Run in project directory
streamlit run chat-webui.py
```

Visit `http://localhost:8501` to use the chat interface.

### Web Interface Features

- 🎨 **Modern UI**: Beautiful chat interface with dark/light theme support
- 🔄 **Real-time Switching**: Switch between different models and providers without restart
- 📊 **Status Monitoring**: Real-time display of local server (Ollama/LM Studio) status
- 🔧 **Smart Caching**: Optimized model configuration loading, avoiding duplicate requests
- 💾 **Chat History**: Maintain conversation context with history clearing support
- 🛠️ **Debug Info**: Detailed error messages and connection status display
- 🔍 **Model Management**: View available model lists, supporting both local and cloud models

### Usage Steps

1. **Select Provider**: Choose LLM provider from sidebar
2. **Select Model**: Choose specific model based on provider
3. **Connection Test**: Click "Connect Model" for connection testing
4. **Start Chatting**: Enter messages in chat box to start conversation

### Local Server Support

- **Ollama**: Auto-detect service status, display available model list
- **LM Studio**: Monitor server status, get loaded models
- **Status Indicators**: Real-time display of server running status and connection info
- **One-click Refresh**: Support manual refresh of server status and model list

### Environment Configuration Guide

Web interface provides detailed environment configuration guidance:
- API key setup instructions
- Local server startup methods
- Common problem solutions
- Debug information display

### Using Ollama Local Models

```python
from llm_api import LLMClient

client = LLMClient()

# Use local Ollama model
response = client.chat(
    "Write a poem about spring",
    model="llama3.1:latest",
    provider="Ollama"
)
print(response)
```

### Using LM Studio Local Models

```python
from llm_api import LLMClient

client = LLMClient()

# Use LM Studio model
response = client.chat(
    "Explain quantum computing principles",
    model="llama-3.2-1b-instruct",  # Replace with your loaded model name
    provider="LMStudio"
)
print(response)
```

### Legacy Code Compatibility

```python
# Compatible with existing call_llm function
from llm_api.utils import call_llm
from pydantic import BaseModel

class MyResponse(BaseModel):
    answer: str
    confidence: float

result = call_llm(
    prompt="What is artificial intelligence?",
    pydantic_model=MyResponse,
    model_name="gpt-4o",
    provider="OpenAI"
)
```

## Configuration

### Environment Variables

Create a `.env` file and set the appropriate API keys:

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1  # Optional

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key

# Google
GOOGLE_API_KEY=your_google_api_key

# Groq
GROQ_API_KEY=your_groq_api_key

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key

# Ollama (Local)
OLLAMA_HOST=localhost  # Optional
OLLAMA_BASE_URL=http://localhost:11434  # Optional

# LM Studio (Local)
LMSTUDIO_HOST=localhost  # Optional
LMSTUDIO_PORT=1234  # Optional
LMSTUDIO_BASE_URL=http://localhost:1234  # Optional
```

### Model Configuration

Model configurations are stored in the `config/` directory:

- `api_models.json`: API model configurations
- `ollama_models.json`: Ollama model configurations
- `lmstudio_models.json`: LM Studio model configurations

You can modify these configuration files to add new models or adjust existing model settings.

## API Reference

### LLMClient Class

#### Initialization

```python
client = LLMClient(
    default_model="gpt-4o",  # Default model
    default_provider="OpenAI"  # Default provider
)
```

#### Methods

- `chat()`: Basic chat interface
- `chat_with_structured_output()`: Structured output interface
- `get_model()`: Get model instance
- `list_available_models()`: List available models
- `get_model_info()`: Get model information
- `clear_cache()`: Clear model cache

### Utility Functions

```python
from llm_api.utils import chat, call_llm, get_model, list_models

# Simple chat
response = chat("Hello")

# Structured output (legacy interface compatibility)
result = call_llm(prompt, MyModel)

# Get model instance
model = get_model("gpt-4o", "OpenAI")

# List all models
models = list_models()
```

## Ollama Support

LLM-API provides complete Ollama support, including:

- Automatic Ollama installation detection
- Automatic Ollama service startup
- Automatic model downloading
- Model management (download, delete)
- Docker environment support

### Ollama Model Management

```python
from llm_api.ollama_utils import (
    ensure_ollama_and_model,
    get_locally_available_models,
    download_model
)

# Ensure model is available (auto-download if not exists)
ensure_ollama_and_model("llama3.1:latest")

# Get locally available models
models = get_locally_available_models()

# Manually download model
download_model("gemma3:4b")
```

## LM Studio Support

LLM-API provides complete LM Studio support, including:

- Automatic LM Studio server status detection
- Get loaded model list
- Model information queries
- OpenAI API format compatibility

### LM Studio Setup

1. **Download and install LM Studio**: Download from [lmstudio.ai](https://lmstudio.ai)
2. **Load model**: Download and load a model in LM Studio
3. **Start local server**: Switch to "Local Server" tab, click "Start Server"
4. **Configure port**: Default runs on `http://localhost:1234`

### LM Studio Model Management

```python
from llm_api.lmstudio_utils import (
    ensure_lmstudio_server,
    list_lmstudio_models,
    get_lmstudio_info
)

# Check LM Studio server status
if ensure_lmstudio_server():
    print("LM Studio server is running")

# Get available model list
models = list_lmstudio_models()
print(f"Available models: {models}")

# Get server information
info = get_lmstudio_info()
print(f"Server info: {info}")
```

## Error Handling

LLM-API provides comprehensive error handling:

```python
from llm_api.exceptions import (
    LLMAPIError,
    ModelNotFoundError,
    APIKeyError,
    ModelProviderError,
    OllamaError,
    LMStudioError
)

try:
    response = client.chat("Hello")
except APIKeyError as e:
    print(f"API key error: {e}")
except LMStudioError as e:
    print(f"LM Studio error: {e}")
except OllamaError as e:
    print(f"Ollama error: {e}")
except ModelNotFoundError as e:
    print(f"Model not found: {e}")
except LLMAPIError as e:
    print(f"LLM API error: {e}")
```

## Best Practices

1. **Environment Variable Management**: Use `.env` files to manage API keys
2. **Model Selection**: Choose appropriate models based on task requirements
3. **Error Handling**: Always include proper error handling
4. **Cache Utilization**: Reuse the same client instance to leverage caching
5. **Structured Output**: Use Pydantic models to ensure consistent output format

## Development Tools

### Configuration Validation

Use the configuration validation script to check environment setup:

```bash
python validate_config.py
```

This script checks:
- Dependency package installation status
- Configuration file format
- Environment variable settings
- Ollama installation status
- Basic functionality tests

### Performance Testing

Run performance benchmarks:

```bash
python benchmark.py
```

Tests include:
- Sequential request testing
- Concurrent request testing
- Structured output testing
- Response time statistics

### Unit Testing

Run the complete unit test suite:

```bash
python test_llm_api.py
```

Or use pytest:

```bash
pip install pytest
pytest test_llm_api.py -v
```

### Package Installation

Install as a Python package:

```bash
pip install -e .
```

After installation, you can use command-line tools:

```bash
llm-api-test  # Run test suite
```

## Project Structure

```
llm-api/
├── __init__.py              # Main entry file
├── client.py                # Core LLMClient class
├── models.py                # Model definitions and configurations
├── exceptions.py            # Custom exception classes
├── utils.py                 # Compatibility utility functions
├── ollama_utils.py          # Ollama management tools
├── lmstudio_utils.py        # LM Studio management tools
├── config_manager.py        # Configuration management
├── langchain_lmstudio.py    # LangChain LM Studio adapter
├── setup.py                 # Package installation configuration
├── requirements.txt         # Dependency list
├── README.md               # Project documentation (Chinese)
├── README_EN.md            # Project documentation (English)
├── example.py              # Usage examples
├── example_lmstudio.py     # LM Studio examples
├── test_llm_api.py         # Unit tests
├── test_lmstudio.py        # LM Studio tests
├── validate_config.py      # Configuration validation script
├── benchmark.py            # Performance testing script
└── config/
    ├── __init__.py
    ├── api_models.json     # API model configurations
    ├── ollama_models.json  # Ollama model configurations
    └── lmstudio_models.json # LM Studio model configurations
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/llm-api.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
5. Install development dependencies: `pip install -e ".[dev]"`
6. Run tests: `pytest`

### Code Style

We use the following tools for code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking
- **Pytest**: Testing

Run all checks:

```bash
black .
flake8 .
mypy .
pytest
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions:

1. Check the [documentation](README.md)
2. Search [existing issues](https://github.com/ai-hedge-fund/llm-api/issues)
3. Create a [new issue](https://github.com/ai-hedge-fund/llm-api/issues/new)

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for the excellent LLM framework
- [Pydantic](https://github.com/pydantic/pydantic) for data validation
- [Ollama](https://ollama.ai/) for local model support
- [LM Studio](https://lmstudio.ai/) for local model management
- All the LLM providers for their amazing APIs