"""
统一的日志管理模块
支持：
1. 文件日志（--logs参数）
2. 控制台日志（--debug参数控制）
3. 日志级别控制
4. 自动日志轮转
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


class AppLogger:
    """应用程序日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if AppLogger._initialized:
            return
        AppLogger._initialized = True
        
        self.logger = logging.getLogger('AIStockMaster')
        self.logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别，由Handler控制实际输出
        
        # 防止重复添加Handler
        self.logger.handlers.clear()
        
        # 日志格式
        self.detailed_formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(name)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.simple_formatter = logging.Formatter(
            '%(asctime)s - [%(levelname)s] - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        self.file_handler = None
        self.console_handler = None
        self.debug_enabled = False
        self.logs_enabled = False
    
    def setup(self, enable_logs=False, enable_debug=False, log_dir=None):
        """
        配置日志系统
        
        Args:
            enable_logs: 是否启用文件日志
            enable_debug: 是否启用控制台调试输出
            log_dir: 日志文件目录（默认为exe所在目录）
        """
        self.logs_enabled = enable_logs
        self.debug_enabled = enable_debug
        
        # 配置文件日志
        if enable_logs:
            try:
                # 确定日志目录
                if log_dir is None:
                    if getattr(sys, 'frozen', False):
                        # 打包后的EXE环境
                        log_dir = Path(sys.executable).parent
                    else:
                        # 开发环境
                        log_dir = Path(__file__).parent.parent
                else:
                    log_dir = Path(log_dir)
                
                # 创建日志目录
                log_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成日志文件名（包含日期）
                timestamp = datetime.now().strftime('%Y%m%d')
                log_file = log_dir / f'AIStockMaster_{timestamp}.log'
                
                # 创建文件Handler（带轮转，最大10MB，保留5个备份）
                self.file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5,
                    encoding='utf-8'
                )
                self.file_handler.setLevel(logging.DEBUG)
                self.file_handler.setFormatter(self.detailed_formatter)
                self.logger.addHandler(self.file_handler)
                
                # 记录日志启动信息
                self.logger.info("="*60)
                self.logger.info(f"日志系统已启动 - 日志文件: {log_file}")
                self.logger.info(f"程序版本: AIStockMaster v1.0")
                self.logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info("="*60)
                
                print(f"[OK] 日志文件已启用: {log_file}")
                
            except Exception as e:
                print(f"[WARN] 文件日志创建失败: {e}")
                self.logs_enabled = False
        
        # 配置控制台日志
        if enable_debug:
            try:
                self.console_handler = logging.StreamHandler(sys.stdout)
                self.console_handler.setLevel(logging.DEBUG)
                self.console_handler.setFormatter(self.simple_formatter)
                self.logger.addHandler(self.console_handler)
                
                print("[OK] 调试模式已启用 - 控制台输出已开启")
                
            except Exception as e:
                print(f"[WARN] 控制台日志创建失败: {e}")
                self.debug_enabled = False
        else:
            # 如果未启用debug，只显示WARNING及以上级别
            if not enable_logs:
                # 如果既没有文件日志也没有debug，添加一个基础的控制台Handler
                self.console_handler = logging.StreamHandler(sys.stdout)
                self.console_handler.setLevel(logging.WARNING)
                self.console_handler.setFormatter(self.simple_formatter)
                self.logger.addHandler(self.console_handler)
    
    def get_logger(self):
        """获取logger实例"""
        return self.logger
    
    def cleanup(self):
        """清理日志资源"""
        try:
            if self.file_handler:
                self.logger.info("="*60)
                self.logger.info("程序正常退出")
                self.logger.info(f"退出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info("="*60)
                self.file_handler.close()
                self.logger.removeHandler(self.file_handler)
            
            if self.console_handler:
                self.console_handler.close()
                self.logger.removeHandler(self.console_handler)
        except:
            pass


# 全局单例
_app_logger = AppLogger()


def setup_logger(enable_logs=False, enable_debug=False, log_dir=None):
    """
    配置应用程序日志系统
    
    Args:
        enable_logs: 是否启用文件日志（--logs参数）
        enable_debug: 是否启用控制台调试输出（--debug参数）
        log_dir: 日志文件目录
    """
    _app_logger.setup(enable_logs, enable_debug, log_dir)


def get_logger(name=None):
    """
    获取logger实例
    
    Args:
        name: 模块名称（可选）
    
    Returns:
        logger实例
    """
    if name:
        return logging.getLogger(f'AIStockMaster.{name}')
    return _app_logger.get_logger()


def cleanup_logger():
    """清理日志资源"""
    _app_logger.cleanup()


# 便捷的日志函数
def debug(msg, *args, **kwargs):
    """调试级别日志"""
    _app_logger.get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """信息级别日志"""
    _app_logger.get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """警告级别日志"""
    _app_logger.get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """错误级别日志"""
    _app_logger.get_logger().error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """严重错误级别日志"""
    _app_logger.get_logger().critical(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    """异常日志（包含堆栈跟踪）"""
    _app_logger.get_logger().exception(msg, *args, **kwargs)


# 兼容性：保留print功能的日志函数
class LoggerPrint:
    """可以像print一样使用的日志类"""
    
    @staticmethod
    def log(level, *args, **kwargs):
        """模拟print但输出到日志"""
        msg = ' '.join(str(arg) for arg in args)
        logger = _app_logger.get_logger()
        
        if level == 'debug':
            logger.debug(msg)
        elif level == 'info':
            logger.info(msg)
        elif level == 'warning':
            logger.warning(msg)
        elif level == 'error':
            logger.error(msg)
        else:
            logger.info(msg)
    
    def __call__(self, *args, **kwargs):
        """允许直接调用：log_print("message")"""
        self.log('info', *args, **kwargs)


log_print = LoggerPrint()


# 测试函数
def test_logger():
    """测试日志功能"""
    print("\n" + "="*60)
    print("测试日志系统")
    print("="*60)
    
    # 测试1：仅文件日志
    print("\n[测试1] 启用文件日志，禁用debug")
    setup_logger(enable_logs=True, enable_debug=False)
    logger = get_logger()
    
    logger.debug("这是DEBUG消息 - 应该在文件中")
    logger.info("这是INFO消息 - 应该在文件中")
    logger.warning("这是WARNING消息 - 应该在文件和控制台中")
    logger.error("这是ERROR消息 - 应该在文件和控制台中")
    
    # 测试2：文件日志+debug
    print("\n[测试2] 启用文件日志和debug")
    cleanup_logger()
    setup_logger(enable_logs=True, enable_debug=True)
    logger = get_logger()
    
    logger.debug("这是DEBUG消息 - 应该在文件和控制台中")
    logger.info("这是INFO消息 - 应该在文件和控制台中")
    logger.warning("这是WARNING消息 - 应该在文件和控制台中")
    
    # 测试3：便捷函数
    print("\n[测试3] 测试便捷函数")
    debug("便捷debug函数")
    info("便捷info函数")
    warning("便捷warning函数")
    error("便捷error函数")
    
    # 测试4：异常日志
    print("\n[测试4] 测试异常日志")
    try:
        1 / 0
    except Exception as e:
        exception("捕获到异常")
    
    cleanup_logger()
    
    print("\n" + "="*60)
    print("日志测试完成！请检查生成的日志文件。")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_logger()

