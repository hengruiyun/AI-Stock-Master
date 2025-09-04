#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM API命令行接口
用于从命令行调用LLM进行分析
"""

import sys
import argparse
import json
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from simple_client import LLMClient
except ImportError:
    try:
        from client import LLMClient
    except ImportError as e:
        print(f"导入模块失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LLM API命令行接口")
    parser.add_argument("--prompt", type=str, help="提示词文本")
    parser.add_argument("--prompt-file", type=str, help="提示词文件路径")
    parser.add_argument("--model", type=str, help="模型名称")
    parser.add_argument("--provider", type=str, help="提供商名称")
    parser.add_argument("--temperature", type=float, help="温度参数")
    
    args = parser.parse_args()
    
    # 获取提示词
    prompt = ""
    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        try:
            with open(args.prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
        except Exception as e:
            print(f"读取提示词文件失败: {e}", file=sys.stderr)
            return 1
    else:
        print("错误: 必须指定 --prompt 或 --prompt-file", file=sys.stderr)
        return 1
    
    try:
        # 创建LLM客户端
        client = LLMClient()
        
        # 调用LLM
        response = client.chat(
            message=prompt,
            model=args.model,
            provider=args.provider,
            temperature=args.temperature
        )
        
        # 输出结果
        print(response)
        return 0
        
    except Exception as e:
        print(f"LLM调用失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
