"""
交易系统常量定义
包含系统中使用的所有常量和枚举值
"""

from enum import Enum
from typing import Final

# ===== 交易相关常量 =====
class TradingSignal(Enum):
    """交易信号枚举"""
    STRONG_BUY = "STRONG_BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    STRONG_SELL = "STRONG_SELL"

class TradingAction(Enum):
    """交易动作枚举"""
    EXECUTE_LONG = "EXECUTE_LONG"
    EXECUTE_SHORT = "EXECUTE_SHORT"
    HOLD = "HOLD"

class StrategyType(Enum):
    """策略类型枚举"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"

class PositionSide(Enum):
    """仓位方向枚举"""
    LONG = "long"
    SHORT = "short"

# ===== 时间周期常量 =====
class Timeframe(Enum):
    """时间周期枚举"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    H8 = "8h"
    D1 = "1d"
    W1 = "1w"

# ===== 技术指标常量 =====
DEFAULT_RSI_PERIOD: Final[int] = 14
DEFAULT_SMA_PERIOD: Final[int] = 20
DEFAULT_ATR_PERIOD: Final[int] = 14

# RSI阈值
RSI_OVERSOLD_THRESHOLD: Final[float] = 30.0
RSI_OVERBOUGHT_THRESHOLD: Final[float] = 70.0
RSI_EXTREME_OVERSOLD: Final[float] = 20.0
RSI_EXTREME_OVERBOUGHT: Final[float] = 80.0

# ===== 风险管理常量 =====
MAX_RISK_PER_TRADE: Final[float] = 0.05  # 5%
MIN_RISK_PER_TRADE: Final[float] = 0.001  # 0.1%
DEFAULT_ATR_MULTIPLIER: Final[float] = 2.0

# ===== 通知系统常量 =====
DINGTALK_MESSAGE_SIZE_LIMIT: Final[int] = 20000  # bytes
DINGTALK_SAFE_SIZE_LIMIT: Final[int] = 18000  # bytes (留缓冲)

# ===== 日志相关常量 =====
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
MAX_LOG_SIZE_MB: Final[int] = 50
BACKUP_COUNT: Final[int] = 5

# ===== 监控相关常量 =====
DEFAULT_MONITOR_INTERVAL: Final[int] = 10  # seconds
NO_POSITION_MONITOR_INTERVAL: Final[int] = 60  # seconds
HIGH_PROFIT_MONITOR_INTERVAL: Final[int] = 5  # seconds

# ===== 错误消息常量 =====
class ErrorMessage:
    """错误消息常量类"""
    API_AUTH_FAILED = "API密钥认证失败"
    NETWORK_ERROR = "网络连接失败"
    INSUFFICIENT_DATA = "数据不足"
    INVALID_SYMBOL = "无效的交易对"
    CALCULATION_ERROR = "计算过程中发生错误"
    
# ===== 成功消息常量 =====
class SuccessMessage:
    """成功消息常量类"""
    SIGNAL_GENERATED = "交易信号生成成功"
    NOTIFICATION_SENT = "通知发送成功"
    POSITION_UPDATED = "仓位更新成功"