#!/bin/bash

# AI Stock Master - Mac Launch Script
# 确保脚本在出错时停止
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_step() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}AI Stock Master${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

print_info() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# 检查并安装 uv
install_uv() {
    echo -e "${BLUE}[1/6]${NC} 检查 uv 安装状态..."
    
    if command -v uv &> /dev/null; then
        print_info "uv 已安装: $(uv --version)"
    else
        print_warning "uv 未安装，正在安装..."
        
        # 安装 uv
        if command -v curl &> /dev/null; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
        elif command -v wget &> /dev/null; then
            wget -qO- https://astral.sh/uv/install.sh | sh
        else
            print_error "需要 curl 或 wget 来安装 uv"
            exit 1
        fi
        
        # 添加 uv 到 PATH (对于当前会话)
        export PATH="$HOME/.cargo/bin:$PATH"

        
        # 验证安装
        if command -v uv &> /dev/null; then
            print_info "uv 安装成功: $(uv --version)"
        else
            print_error "uv 安装失败"
            echo "请手动安装 uv: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
    fi
}

# 检查 Python 版本
check_python() {
    echo -e "${BLUE}[2/6]${NC} 检查 Python 版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        print_info "发现 Python 版本: $PYTHON_VERSION"
        
        # 检查版本是否 >= 3.10
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
            print_info "Python $PYTHON_VERSION 满足要求 (3.10+)"
            USE_SYSTEM_PYTHON=true
        else
            print_warning "Python 版本过低，将使用 uv 管理的 Python 3.10"
            USE_SYSTEM_PYTHON=false
        fi
    else
        print_warning "系统未安装 Python，将使用 uv 管理的 Python 3.10"
        USE_SYSTEM_PYTHON=false
    fi
}


# 设置虚拟环境
setup_venv() {
    echo -e "${BLUE}[3/6]${NC} 设置虚拟环境..."
    
    if [ -d ".venv" ]; then
        print_info "虚拟环境已存在"
    else
        export  UV_PYTHON_INSTALL_MIRROR=https://gh-proxy.com/https://github.com/indygreg/python-build-standalone/releases/download
        export  UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple
        print_info "创建 Python 3.10 虚拟环境..."
        if [ "$USE_SYSTEM_PYTHON" = true ]; then
            uv venv --python=python3
        else
            uv venv --python=3.10
        fi
        print_info "虚拟环境创建成功"
    fi
}

# 安装依赖
install_dependencies() {
    echo -e "${BLUE}[4/6]${NC} 安装依赖..."
    export  UV_PYTHON_INSTALL_MIRROR=https://gh-proxy.com/https://github.com/indygreg/python-build-standalone/releases/download
    export  UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple

    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt 文件未找到"
        exit 1
    fi
    
    print_info "从 requirements.txt 安装包..."
    uv pip install -r requirements.txt
    print_info "依赖安装成功"
}


# 启动 GUI 应用
launch_gui() {
    echo -e "${BLUE}[6/6]${NC} 启动 GUI 应用..."
    
    if [ ! -f "gui-pyqt5.py" ]; then
        print_error "gui-pyqt5.py 文件未找到"
        exit 1
    fi
    
    print_info "正在启动 AI Stock Master..."
    echo
    
    # 使用 uv run 启动应用
    uv run gui-pyqt5.py
    
    if [ $? -eq 0 ]; then
        print_info "应用成功完成"
    else
        print_error "应用启动失败"
        exit 1
    fi
}

# 主函数
main() {
    print_step
    
    # 检查当前目录是否为项目根目录
    if [ ! -f "gui-pyqt5.py" ] && [ ! -f "requirements.txt" ]; then
        print_error "请在 AI-Stock-Master 项目根目录下运行此脚本"
        exit 1
    fi
    
    install_uv
    check_python
    setup_venv
    install_dependencies
    launch_gui
    
    echo
    print_info "所有步骤完成！"
}

# 错误处理
trap 'echo -e "\n${RED}脚本执行中断${NC}"; exit 1' INT TERM

# 运行主函数
main "$@"

