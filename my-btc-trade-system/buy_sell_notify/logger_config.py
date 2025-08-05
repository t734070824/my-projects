import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path
import config

def setup_logger(name: str = "main", log_filename: str = None):
    """
    设置日志器，支持文件和控制台输出
    
    Args:
        name: 日志器名称
        log_filename: 日志文件名，如果为None则使用main_log_file
    """
    # 创建日志目录
    log_dir = Path(config.LOG_CONFIG["log_dir"])
    log_dir.mkdir(exist_ok=True)
    
    # 确定日志文件名
    if log_filename is None:
        log_filename = config.LOG_CONFIG["main_log_file"]
    log_file_path = log_dir / log_filename
    
    # 创建日志器
    logger = logging.getLogger(name)
    
    # 清除现有处理器，避免重复
    if logger.handlers:
        logger.handlers.clear()
    
    # 设置日志级别
    log_level = getattr(logging, config.LOG_CONFIG["log_level"].upper())
    logger.setLevel(log_level)
    
    # 创建格式器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    formatter.converter = time.localtime
    
    # 添加文件处理器（带轮转）
    max_bytes = config.LOG_CONFIG["max_log_size_mb"] * 1024 * 1024
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=config.LOG_CONFIG["backup_count"],
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    
    # 添加控制台处理器（如果启用）
    if config.LOG_CONFIG["console_output"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    return logger

def setup_main_logger():
    """设置主程序日志器"""
    return setup_logger("main", config.LOG_CONFIG["main_log_file"])

def setup_position_monitor_logger():
    """设置仓位监控日志器"""
    return setup_logger("position_monitor", config.LOG_CONFIG["position_log_file"])

def get_logger(name: str = "main"):
    """获取已配置的日志器"""
    return logging.getLogger(name)