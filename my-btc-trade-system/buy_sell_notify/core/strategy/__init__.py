"""
交易策略模块
提供各种交易策略的实现
"""

from .base import TradingStrategy, StrategyResult
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy

__all__ = [
    'TradingStrategy', 'StrategyResult',
    'TrendFollowingStrategy', 'MeanReversionStrategy'
]