"""
交易所接口模块
提供统一的交易所访问接口
"""

from .base import ExchangeInterface
from .binance import BinanceExchange

__all__ = [
    'ExchangeInterface', 'BinanceExchange'
]