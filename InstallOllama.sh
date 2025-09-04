#!/bin/bash

# Install Ollama - Mac Script
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
    echo -e "${BLUE}Install Ollama${NC}"
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

# 设置环境变量（镜像加速）
setup_environment() {
    export UV_PYTHON_INSTALL_MIRROR="https://gh-proxy.com/https://github.com/indygreg/python-build-standalone/releases/download"
    export UV_DEFAULT_INDEX="https://mirrors.aliyun.com/pypi/simple"
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
    export  UV_PYTHON_INSTALL_MIRROR=https://gh-proxy.com/https://github.com/indygreg/python-build-standalone/releases/download
    export  UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple

    if [ -d ".venv" ]; then
        print_info "虚拟环境已存在"
    else
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

    if [ -f "requireOlla.txt" ]; then
        REQUIREMENTS_FILE="requireOlla.txt"
    elif [ -f "requirements.txt" ]; then
        REQUIREMENTS_FILE="requirements.txt"
        print_warning "requireOlla.txt 未找到，使用 requirements.txt"
    else
        print_error "依赖文件未找到 (requireOlla.txt 或 requirements.txt)"
        exit 1
    fi
    
    print_info "从 $REQUIREMENTS_FILE 安装包..."
    uv pip install -r "$REQUIREMENTS_FILE"
    print_info "依赖安装成功"
}

# 安装 Ollama
install_ollama() {
    echo -e "${BLUE}[6/6]${NC} 安装和配置 Ollama..."
    
    # 检查 Ollama 是否已安装
    if command -v ollama &> /dev/null; then
        print_info "Ollama 已安装: $(ollama --version 2>/dev/null || echo 'version unknown')"
        print_info "Ollama 位置: $(which ollama)"
    else
        print_warning "Ollama 未安装，正在安装..."
        
        # 检测操作系统
        OS_TYPE=$(uname)
        if [[ "$OS_TYPE" == "Darwin" ]]; then
            # macOS 系统
            print_info "检测到 macOS 系统"
            
            # 根据架构显示信息
            if [[ $(uname -m) == "arm64" ]]; then
                print_info "系统架构: Apple Silicon (ARM64)"
            else
                print_info "系统架构: Intel (x86_64)"
            fi
            
            print_info "macOS 系统要求: macOS 12 Monterey 或更高版本"
            
            # 尝试自动下载并安装 DMG
            print_info "正在下载 Ollama for Mac..."
            OLLAMA_DMG_URL="https://ollama.com/download/Ollama.dmg"
            TEMP_DMG="/tmp/Ollama.dmg"
            
            if command -v curl &> /dev/null; then
                # 下载 DMG 文件
                print_info "下载中... 请稍候"
                if curl -L -o "$TEMP_DMG" "$OLLAMA_DMG_URL"; then
                    print_info "下载完成，正在安装..."
                    
                    # 挂载 DMG
                    MOUNT_POINT=$(hdiutil attach "$TEMP_DMG" | grep "Volumes" | awk '{print $3}')
                    
                    if [ -n "$MOUNT_POINT" ]; then
                        # 复制应用到 Applications 文件夹
                        if [ -d "$MOUNT_POINT/Ollama.app" ]; then
                            print_info "正在安装 Ollama.app 到 Applications..."
                            cp -R "$MOUNT_POINT/Ollama.app" /Applications/
                            
                            # 卸载 DMG
                            hdiutil detach "$MOUNT_POINT" &>/dev/null
                            
                            # 清理临时文件
                            rm -f "$TEMP_DMG"
                            
                            # 启动 Ollama 应用以完成安装
                            print_info "启动 Ollama 应用完成安装..."
                            open -a Ollama
                            sleep 5
                            
                            # 验证 CLI 是否可用
                            if command -v ollama &> /dev/null; then
                                print_info "Ollama 安装成功"
                            else
                                print_warning "Ollama GUI 已安装，但 CLI 可能需要手动配置"
                                print_info "请启动 Ollama.app 以完成 CLI 设置"
                            fi
                        else
                            print_error "DMG 中未找到 Ollama.app"
                        fi
                    else
                        print_error "无法挂载 DMG 文件"
                    fi
                else
                    print_error "下载 Ollama DMG 失败"
                fi
            else
                print_error "需要 curl 来下载 Ollama"
            fi
            
            # 如果自动安装失败，提供手动安装指引
            if ! command -v ollama &> /dev/null; then
                print_warning "自动安装失败，请手动安装 Ollama"
                echo
                echo -e "${YELLOW}手动安装步骤：${NC}"
                echo "1. 打开浏览器访问: https://ollama.com/download/mac"
                echo "2. 下载 Ollama.dmg 文件"
                echo "3. 双击 DMG 文件并将 Ollama.app 拖到 Applications 文件夹"
                echo "4. 启动 Ollama.app 完成安装"
                echo
                
                # 尝试打开浏览器
                if command -v open &> /dev/null; then
                    print_info "正在打开浏览器..."
                    open "https://ollama.com/download/mac"
                fi
                
                # 等待用户手动安装
                echo -e "${BLUE}请完成手动安装后按 Enter 键继续...${NC}"
                read -p ""
            fi
            
        elif [[ "$OS_TYPE" == "Linux" ]]; then
            # Linux 系统 - 使用官方安装脚本
            print_info "检测到 Linux 系统"
            if command -v curl &> /dev/null; then
                curl -fsSL https://ollama.com/install.sh | sh
            else
                print_error "需要 curl 来安装 Ollama"
                print_info "请手动安装 Ollama: https://ollama.com/download"
                exit 1
            fi
        else
            print_error "不支持的操作系统: $OS_TYPE"
            print_info "请手动安装 Ollama: https://ollama.com/download"
            exit 1
        fi
        
        # 验证安装
        if command -v ollama &> /dev/null; then
            print_info "Ollama 安装成功"
        else
            print_warning "Ollama CLI 可能需要重新启动终端或重新登录才能使用"
        fi
    fi
    
    # 启动 Ollama 服务 (如果需要)
    print_info "检查 Ollama 服务状态..."
    if pgrep -f "ollama" > /dev/null; then
        print_info "Ollama 服务已运行"
    else
        print_info "启动 Ollama 服务..."
        # 在 macOS 上，Ollama.app 通常会自动管理服务
        if [[ "$(uname)" == "Darwin" ]]; then
            # 尝试启动 Ollama 应用
            if [ -d "/Applications/Ollama.app" ]; then
                open -a Ollama &>/dev/null
                sleep 3
            fi
        else
            # Linux 系统
            ollama serve &
            sleep 3
        fi
        print_info "Ollama 服务已启动"
    fi
}

# 运行检查脚本
run_checks() {
    echo
    echo -e "${BLUE}运行环境检查...${NC}"
    ollama pull gemma3:1b

}

# 主函数
main() {
    print_step
    
    setup_environment
    install_uv
    check_python
    setup_venv
    install_dependencies
    install_ollama
    run_checks
    
    echo
    print_info "Ollama 安装和配置完成！"
    echo
    echo -e "${GREEN}下一步：${NC}"
    echo "1. 可以运行 'ollama pull gemma3:1b' 下载模型"
    echo "2. 运行 './AI-Stock-Master.sh' 启动主应用"
}

# 错误处理
trap 'echo -e "\n${RED}脚本执行中断${NC}"; exit 1' INT TERM

# 运行主函数
main "$@"

