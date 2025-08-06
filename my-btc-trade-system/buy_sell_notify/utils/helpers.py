"""
通用辅助函数
提供系统中常用的工具函数
"""

import json
import logging
import uuid
import hashlib
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from utils.constants import TradingSignal, TradingAction, PositionSide


def safe_float_conversion(value: Union[str, float, int, None], default: float = 0.0) -> float:
    """
    安全地转换值为浮点数
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
        
    Returns:
        float: 转换后的浮点数
    """
    if value is None:
        return default
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal_conversion(value: Union[str, float, int, None], 
                          decimal_places: int = 4, 
                          default: float = 0.0) -> Decimal:
    """
    安全地转换值为Decimal并保留指定小数位
    
    Args:
        value: 要转换的值
        decimal_places: 小数位数
        default: 转换失败时的默认值
        
    Returns:
        Decimal: 转换后的Decimal
    """
    try:
        decimal_value = Decimal(str(value)) if value is not None else Decimal(str(default))
        return decimal_value.quantize(
            Decimal('0.' + '0' * decimal_places), 
            rounding=ROUND_HALF_UP
        )
    except:
        return Decimal(str(default))


def format_percentage(value: float, decimal_places: int = 2) -> str:
    """
    格式化百分比显示
    
    Args:
        value: 数值 (0.05 表示 5%)
        decimal_places: 小数位数
        
    Returns:
        str: 格式化后的百分比字符串
    """
    return f"{value * 100:.{decimal_places}f}%"


def format_currency(value: float, currency: str = "USDT", decimal_places: int = 2) -> str:
    """
    格式化货币显示
    
    Args:
        value: 数值
        currency: 货币单位
        decimal_places: 小数位数
        
    Returns:
        str: 格式化后的货币字符串
    """
    return f"{value:,.{decimal_places}f} {currency}"


def sanitize_log_data(data: Dict[str, Any], 
                     sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    清理日志数据，移除敏感信息
    
    Args:
        data: 要清理的数据字典
        sensitive_keys: 敏感字段列表
        
    Returns:
        Dict[str, Any]: 清理后的数据
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'account_status', 'open_positions', 'balance', 
            'walletBalance', 'availableBalance', 'unrealizedProfit'
        ]
    
    return {k: v for k, v in data.items() if k not in sensitive_keys}


def create_log_safe_json(data: Dict[str, Any], 
                        indent: int = 2, 
                        max_length: Optional[int] = None) -> str:
    """
    创建适合日志输出的JSON字符串
    
    Args:
        data: 要序列化的数据
        indent: 缩进空格数
        max_length: 最大长度限制
        
    Returns:
        str: JSON字符串
    """
    try:
        # 清理敏感数据
        safe_data = sanitize_log_data(data)
        
        # 序列化为JSON
        json_str = json.dumps(safe_data, indent=indent, default=str, ensure_ascii=False)
        
        # 如果有长度限制，进行截断
        if max_length and len(json_str) > max_length:
            json_str = json_str[:max_length - 3] + "..."
            
        return json_str
    except Exception as e:
        return f"JSON序列化失败: {str(e)}"


def signal_to_action(signal: str) -> TradingAction:
    """
    将技术分析信号转换为交易动作
    
    Args:
        signal: 技术分析信号
        
    Returns:
        TradingAction: 对应的交易动作
    """
    signal_mapping = {
        TradingSignal.STRONG_BUY.value: TradingAction.EXECUTE_LONG,
        TradingSignal.WEAK_BUY.value: TradingAction.EXECUTE_LONG,
        TradingSignal.STRONG_SELL.value: TradingAction.EXECUTE_SHORT,
        TradingSignal.WEAK_SELL.value: TradingAction.EXECUTE_SHORT,
    }
    
    return signal_mapping.get(signal, TradingAction.HOLD)


def is_opposite_position(current_side: str, new_action: str) -> bool:
    """
    检查新动作是否与当前仓位方向相反
    
    Args:
        current_side: 当前仓位方向
        new_action: 新的交易动作
        
    Returns:
        bool: 是否为相反方向
    """
    return (
        (current_side == PositionSide.LONG.value and new_action == TradingAction.EXECUTE_SHORT.value) or
        (current_side == PositionSide.SHORT.value and new_action == TradingAction.EXECUTE_LONG.value)
    )


def calculate_position_side(amount: float) -> PositionSide:
    """
    根据持仓量计算仓位方向
    
    Args:
        amount: 持仓量（正数为多仓，负数为空仓）
        
    Returns:
        PositionSide: 仓位方向
    """
    return PositionSide.LONG if amount > 0 else PositionSide.SHORT


def get_timestamp_string(timestamp: Optional[float] = None) -> str:
    """
    获取格式化的时间戳字符串
    
    Args:
        timestamp: 时间戳（默认为当前时间）
        
    Returns:
        str: 格式化的时间字符串
    """
    if timestamp is None:
        timestamp = datetime.now().timestamp()
    
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def extract_symbol_from_log(log_text: str) -> Optional[str]:
    """
    从日志文本中提取交易对符号
    
    Args:
        log_text: 日志文本
        
    Returns:
        Optional[str]: 提取到的交易对符号
    """
    try:
        if "交易对:" in log_text:
            for line in log_text.split('\n'):
                if "交易对:" in line:
                    return line.split("交易对:")[1].strip()
        return None
    except Exception:
        return None


def extract_decision_reason(log_text: str) -> Optional[str]:
    """
    从日志文本中提取决策原因
    
    Args:
        log_text: 日志文本
        
    Returns:
        Optional[str]: 提取到的决策原因
    """
    try:
        if " - 原因: " in log_text:
            return log_text.split(" - 原因: ")[1]
        return None
    except Exception:
        return None


def generate_trade_id(symbol: str = "", action: str = "", timestamp: Optional[datetime] = None) -> str:
    """
    生成唯一的交易ID
    
    Args:
        symbol: 交易对符号
        action: 交易动作
        timestamp: 时间戳（可选）
        
    Returns:
        str: 生成的交易ID
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # 方式1: 使用UUID（最简单）
    if not symbol and not action:
        return str(uuid.uuid4())
    
    # 方式2: 基于参数生成可读ID
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    # 清理符号和动作
    clean_symbol = symbol.replace("/", "").replace("-", "") if symbol else "UNKNOWN"
    clean_action = action.replace("EXECUTE_", "") if action else "TRADE"
    
    # 生成短hash确保唯一性
    content = f"{clean_symbol}_{clean_action}_{time_str}_{timestamp.microsecond}"
    short_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    
    return f"{clean_symbol}_{clean_action}_{time_str}_{short_hash}"


def calculate_position_value(size: float, price: float, precision: int = 2) -> float:
    """
    计算持仓价值
    
    Args:
        size: 持仓数量
        price: 价格
        precision: 精度（小数点位数）
        
    Returns:
        float: 持仓价值
    """
    try:
        value = size * price
        return round(value, precision)
    except (TypeError, ValueError):
        return 0.0