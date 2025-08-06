"""
日志处理器
提供增强的日志功能，包括结构化日志和特殊处理
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式器
    将日志输出为结构化格式，便于解析和分析
    """
    
    def __init__(self, include_extra_fields: bool = True):
        """
        初始化格式器
        
        Args:
            include_extra_fields: 是否包含额外字段
        """
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础日志信息
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if self.include_extra_fields and hasattr(record, '__dict__'):
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                    'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                    'thread', 'threadName', 'processName', 'process', 'message'
                ]:
                    extra_fields[key] = value
            
            if extra_fields:
                log_data['extra'] = extra_fields
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class TradingSignalHandler(logging.Handler):
    """
    交易信号专用日志处理器
    专门用于捕获和处理交易信号相关的日志
    """
    
    def __init__(self, signal_callback: Optional[callable] = None):
        """
        初始化处理器
        
        Args:
            signal_callback: 信号回调函数
        """
        super().__init__()
        self.signal_callback = signal_callback
        self.signal_patterns = [
            r'🎯 NEW TRADE SIGNAL',
            r'NEW TRADE SIGNAL',
            r'TRADE SIGNAL'
        ]
        self.processed_signals = set()  # 避免重复处理
    
    def emit(self, record: logging.LogRecord):
        """处理日志记录"""
        try:
            message = self.format(record)
            
            # 检查是否是交易信号
            if self._is_trading_signal(message):
                signal_data = self._extract_signal_data(message, record)
                
                # 避免重复处理
                signal_id = self._generate_signal_id(signal_data)
                if signal_id not in self.processed_signals:
                    self.processed_signals.add(signal_id)
                    
                    if self.signal_callback:
                        self.signal_callback(signal_data)
                    
                    # 清理过期的信号ID（保持集合大小合理）
                    if len(self.processed_signals) > 1000:
                        self.processed_signals.clear()
                        
        except Exception as e:
            # 处理器内部错误，记录但不影响主程序
            self.handleError(record)
    
    def _is_trading_signal(self, message: str) -> bool:
        """判断是否为交易信号"""
        for pattern in self.signal_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    def _extract_signal_data(self, message: str, record: logging.LogRecord) -> Dict[str, Any]:
        """从日志消息中提取信号数据"""
        signal_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'raw_message': message,
            'extracted_data': {}
        }
        
        # 尝试解析JSON格式的数据
        try:
            # 查找JSON部分
            json_match = re.search(r'\{.*\}', message, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_data = json.loads(json_str)
                signal_data['extracted_data'] = parsed_data
        except (json.JSONDecodeError, AttributeError):
            # 如果不是JSON格式，尝试使用正则表达式提取关键信息
            signal_data['extracted_data'] = self._extract_with_regex(message)
        
        return signal_data
    
    def _extract_with_regex(self, message: str) -> Dict[str, Any]:
        """使用正则表达式提取信号信息"""
        extracted = {}
        
        # 提取交易对
        symbol_match = re.search(r'symbol["\']?\s*:\s*["\']?([A-Z/]+)', message, re.IGNORECASE)
        if symbol_match:
            extracted['symbol'] = symbol_match.group(1)
        
        # 提取操作类型
        action_match = re.search(r'action["\']?\s*:\s*["\']?(EXECUTE_[A-Z]+|LONG|SHORT)', message, re.IGNORECASE)
        if action_match:
            extracted['action'] = action_match.group(1)
        
        # 提取置信度
        confidence_match = re.search(r'confidence["\']?\s*:\s*([0-9.]+)', message, re.IGNORECASE)
        if confidence_match:
            extracted['confidence'] = float(confidence_match.group(1))
        
        # 提取ATR值
        atr_match = re.search(r'atr["\']?\s*:\s*([0-9.]+)', message, re.IGNORECASE)
        if atr_match:
            extracted['atr'] = float(atr_match.group(1))
        
        return extracted
    
    def _generate_signal_id(self, signal_data: Dict[str, Any]) -> str:
        """生成信号唯一标识"""
        extracted = signal_data.get('extracted_data', {})
        symbol = extracted.get('symbol', 'UNKNOWN')
        action = extracted.get('action', 'UNKNOWN')
        timestamp = signal_data.get('timestamp', '')
        
        # 使用时间戳的分钟精度避免重复
        minute_timestamp = timestamp[:16] if len(timestamp) >= 16 else timestamp
        
        return f"{symbol}_{action}_{minute_timestamp}"


class LogRotationManager:
    """
    日志轮转管理器
    管理日志文件的备份和清理
    """
    
    def __init__(self, log_dir: str = "logs", backup_dir: str = "logs/backup"):
        """
        初始化日志轮转管理器
        
        Args:
            log_dir: 日志目录
            backup_dir: 备份目录
        """
        self.log_dir = log_dir
        self.backup_dir = backup_dir
        self.logger = logging.getLogger("LogRotationManager")
        
        import os
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def rotate_logs(self) -> bool:
        """
        执行日志轮转
        
        Returns:
            bool: 轮转是否成功
        """
        try:
            import os
            import shutil
            from datetime import datetime
            
            if not os.path.exists(self.log_dir):
                self.logger.warning(f"日志目录不存在: {self.log_dir}")
                return False
            
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            successful_rotations = 0
            
            # 遍历日志目录中的所有.log文件
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.log'):
                    log_path = os.path.join(self.log_dir, filename)
                    
                    # 检查文件是否存在且不为空
                    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
                        # 创建备份文件名
                        name_without_ext = filename[:-4]  # 移除.log扩展名
                        backup_filename = f"{name_without_ext}_{backup_timestamp}.log"
                        backup_path = os.path.join(self.backup_dir, backup_filename)
                        
                        # 复制文件到备份目录
                        shutil.copy2(log_path, backup_path)
                        
                        # 清空原始文件
                        open(log_path, 'w').close()
                        
                        successful_rotations += 1
                        self.logger.info(f"日志轮转成功: {filename} -> {backup_filename}")
            
            self.logger.info(f"日志轮转完成，处理了 {successful_rotations} 个文件")
            return True
            
        except Exception as e:
            self.logger.error(f"日志轮转失败: {e}", exc_info=True)
            return False
    
    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """
        清理旧的备份文件
        
        Args:
            keep_days: 保留天数
            
        Returns:
            int: 删除的文件数量
        """
        try:
            import os
            from datetime import datetime, timedelta
            
            if not os.path.exists(self.backup_dir):
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            for filename in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, filename)
                
                if os.path.isfile(file_path):
                    # 获取文件修改时间
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_date:
                        os.remove(file_path)
                        deleted_count += 1
                        self.logger.info(f"删除过期备份: {filename}")
            
            self.logger.info(f"清理完成，删除了 {deleted_count} 个过期备份")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"清理备份失败: {e}", exc_info=True)
            return 0


def setup_enhanced_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_structured_logging: bool = False,
    signal_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    设置增强的日志系统
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        enable_structured_logging: 是否启用结构化日志
        signal_callback: 信号处理回调
        
    Returns:
        Dict[str, Any]: 日志配置信息
    """
    import os
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 设置格式器
    if enable_structured_logging:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    
    # 文件处理器
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'trader.log'),
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 交易信号处理器（如果提供了回调）
    if signal_callback:
        signal_handler = TradingSignalHandler(signal_callback)
        signal_handler.setLevel(logging.INFO)
        root_logger.addHandler(signal_handler)
    
    # 创建日志轮转管理器
    rotation_manager = LogRotationManager(log_dir)
    
    config_info = {
        'log_level': log_level,
        'log_dir': log_dir,
        'structured_logging': enable_structured_logging,
        'signal_callback_enabled': signal_callback is not None,
        'rotation_manager': rotation_manager
    }
    
    logging.getLogger("LoggingSetup").info(f"增强日志系统已配置: {config_info}")
    
    return config_info