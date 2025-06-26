#!/usr/bin/env python3
"""LLM API 性能测试脚本"""

import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from pydantic import BaseModel
from colorama import Fore, Style, init

# 初始化colorama
init()

try:
    from llm_api import LLMClient
    from llm_api.models import list_all_models
except ImportError:
    try:
        from client import LLMClient
        from models import list_all_models
    except ImportError:
        print(f"{Fore.RED}请先安装LLM API包{Style.RESET_ALL}")
        print("运行: pip install -e .")
        sys.exit(1)


class SimpleResponse(BaseModel):
    """简单响应模型"""
    message: str
    sentiment: str
    confidence: float


class BenchmarkResult:
    """基准测试结果"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.response_times: List[float] = []
        self.success_count = 0
        self.error_count = 0
        self.errors: List[str] = []
    
    def add_result(self, response_time: float, success: bool, error: str = None):
        """添加测试结果"""
        if success:
            self.response_times.append(response_time)
            self.success_count += 1
        else:
            self.error_count += 1
            if error:
                self.errors.append(error)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.response_times:
            return {
                'test_name': self.test_name,
                'total_requests': self.success_count + self.error_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'median_response_time': 0.0,
                'p95_response_time': 0.0,
            }
        
        total_requests = self.success_count + self.error_count
        success_rate = (self.success_count / total_requests) * 100 if total_requests > 0 else 0
        
        sorted_times = sorted(self.response_times)
        p95_index = int(len(sorted_times) * 0.95)
        
        return {
            'test_name': self.test_name,
            'total_requests': total_requests,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': success_rate,
            'avg_response_time': statistics.mean(self.response_times),
            'min_response_time': min(self.response_times),
            'max_response_time': max(self.response_times),
            'median_response_time': statistics.median(self.response_times),
            'p95_response_time': sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1],
        }


def test_single_request(client: LLMClient, model_name: str, provider: str) -> tuple[float, bool, str]:
    """测试单个请求"""
    start_time = time.time()
    
    try:
        response = client.chat(
            message="请分析这句话的情感：'今天天气真好！'",
            model=model_name,
            provider=provider
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # 简单验证响应
        if response and len(response) > 0:
            return response_time, True, None
        else:
            return response_time, False, "空响应"
            
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        return response_time, False, str(e)


def test_structured_request(client: LLMClient, model_name: str, provider: str) -> tuple[float, bool, str]:
    """测试结构化请求"""
    start_time = time.time()
    
    try:
        response = client.chat_with_structured_output(
            message="请分析这句话的情感：'今天天气真好！'，返回情感分析结果",
            pydantic_model=SimpleResponse,
            model=model_name,
            provider=provider
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # 验证结构化响应
        if isinstance(response, SimpleResponse):
            return response_time, True, None
        else:
            return response_time, False, "响应格式错误"
            
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        return response_time, False, str(e)


def run_sequential_test(client: LLMClient, model_name: str, provider: str, num_requests: int = 10) -> BenchmarkResult:
    """运行顺序测试"""
    print(f"  运行顺序测试: {num_requests} 个请求...")
    
    result = BenchmarkResult(f"Sequential-{model_name}-{provider}")
    
    for i in range(num_requests):
        print(f"    请求 {i+1}/{num_requests}", end="\r")
        response_time, success, error = test_single_request(client, model_name, provider)
        result.add_result(response_time, success, error)
    
    print(f"    完成 {num_requests} 个请求")
    return result


def run_concurrent_test(client: LLMClient, model_name: str, provider: str, num_requests: int = 10, max_workers: int = 5) -> BenchmarkResult:
    """运行并发测试"""
    print(f"  运行并发测试: {num_requests} 个请求，{max_workers} 个并发...")
    
    result = BenchmarkResult(f"Concurrent-{model_name}-{provider}")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = []
        for i in range(num_requests):
            future = executor.submit(test_single_request, client, model_name, provider)
            futures.append(future)
        
        # 收集结果
        completed = 0
        for future in as_completed(futures):
            completed += 1
            print(f"    完成 {completed}/{num_requests}", end="\r")
            
            try:
                response_time, success, error = future.result()
                result.add_result(response_time, success, error)
            except Exception as e:
                result.add_result(0.0, False, str(e))
    
    print(f"    完成 {num_requests} 个并发请求")
    return result


def run_structured_output_test(client: LLMClient, model_name: str, provider: str, num_requests: int = 5) -> BenchmarkResult:
    """运行结构化输出测试"""
    print(f"  运行结构化输出测试: {num_requests} 个请求...")
    
    result = BenchmarkResult(f"Structured-{model_name}-{provider}")
    
    for i in range(num_requests):
        print(f"    请求 {i+1}/{num_requests}", end="\r")
        response_time, success, error = test_structured_request(client, model_name, provider)
        result.add_result(response_time, success, error)
    
    print(f"    完成 {num_requests} 个结构化请求")
    return result


def print_results(results: List[BenchmarkResult]):
    """打印测试结果"""
    print(f"\n{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}性能测试结果{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
    
    for result in results:
        stats = result.get_stats()
        
        print(f"\n{Fore.CYAN}测试: {stats['test_name']}{Style.RESET_ALL}")
        print(f"  总请求数: {stats['total_requests']}")
        print(f"  成功数: {stats['success_count']}")
        print(f"  失败数: {stats['error_count']}")
        print(f"  成功率: {stats['success_rate']:.1f}%")
        
        if stats['success_count'] > 0:
            print(f"  平均响应时间: {stats['avg_response_time']:.2f}s")
            print(f"  最小响应时间: {stats['min_response_time']:.2f}s")
            print(f"  最大响应时间: {stats['max_response_time']:.2f}s")
            print(f"  中位数响应时间: {stats['median_response_time']:.2f}s")
            print(f"  95%响应时间: {stats['p95_response_time']:.2f}s")
        
        if result.errors:
            print(f"  错误示例: {result.errors[0]}")


def benchmark_model(client: LLMClient, model_name: str, provider: str) -> List[BenchmarkResult]:
    """对单个模型进行基准测试"""
    print(f"\n{Fore.GREEN}测试模型: {model_name} ({provider}){Style.RESET_ALL}")
    
    results = []
    
    try:
        # 顺序测试
        seq_result = run_sequential_test(client, model_name, provider, 5)
        results.append(seq_result)
        
        # 并发测试
        conc_result = run_concurrent_test(client, model_name, provider, 10, 3)
        results.append(conc_result)
        
        # 结构化输出测试
        struct_result = run_structured_output_test(client, model_name, provider, 3)
        results.append(struct_result)
        
    except Exception as e:
        print(f"  {Fore.RED}测试失败: {e}{Style.RESET_ALL}")
    
    return results


def main():
    """主函数"""
    print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}LLM API 性能基准测试{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
    
    # 创建客户端
    client = LLMClient()
    
    # 获取可用模型
    available_models = list_all_models()
    
    if not available_models:
        print(f"{Fore.RED}未找到可用模型{Style.RESET_ALL}")
        return
    
    # 选择要测试的模型（限制数量以避免测试时间过长）
    test_models = []
    
    # 优先测试常用模型
    preferred_models = [
        ("gpt-4o", "OpenAI"),
        ("claude-3-5-haiku-latest", "Anthropic"),
        ("llama3.1:latest", "Ollama"),
    ]
    
    for model_name, provider in preferred_models:
        model_info = next(
            (m for m in available_models if m.model_name == model_name and m.provider == provider),
            None
        )
        if model_info:
            test_models.append(model_info)
    
    # 如果没有找到首选模型，使用前几个可用模型
    if not test_models:
        test_models = available_models[:3]
    
    print(f"将测试以下模型: {', '.join([f'{m.model_name} ({m.provider})' for m in test_models])}")
    
    all_results = []
    
    for model in test_models:
        model_results = benchmark_model(client, model.model_name, model.provider)
        all_results.extend(model_results)
    
    # 打印结果
    print_results(all_results)
    
    # 总结
    print(f"\n{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}测试总结{Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'='*80}{Style.RESET_ALL}")
    
    total_requests = sum(r.success_count + r.error_count for r in all_results)
    total_success = sum(r.success_count for r in all_results)
    overall_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
    
    print(f"总请求数: {total_requests}")
    print(f"总成功数: {total_success}")
    print(f"整体成功率: {overall_success_rate:.1f}%")
    
    if total_success > 0:
        all_response_times = []
        for result in all_results:
            all_response_times.extend(result.response_times)
        
        if all_response_times:
            avg_time = statistics.mean(all_response_times)
            print(f"平均响应时间: {avg_time:.2f}s")
    
    print(f"\n{Fore.GREEN}基准测试完成！{Style.RESET_ALL}")


if __name__ == "__main__":
    main()