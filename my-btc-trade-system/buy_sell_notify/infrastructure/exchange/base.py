"""
交易所接口基类
定义所有交易所接口的标准协议
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

from utils.constants import Timeframe


class ExchangeInterface(ABC):
    """
    交易所接口抽象基类
    
    定义了与交易所交互的标准方法，所有具体的交易所实现都应该继承此类
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化交易所接口
        
        Args:
            config: 交易所配置参数
        """
        self.config = config
        self.logger = logging.getLogger(f"Exchange.{self.__class__.__name__}")
        self._exchange = None
    
    @abstractmethod
    def connect(self) -> bool:
        """
        连接到交易所
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def get_account_balance(self) -> Dict[str, Any]:
        """
        获取账户余额信息
        
        Returns:
            Dict[str, Any]: 包含余额信息的字典
                - success: bool, 是否成功
                - balance: Dict, 余额详情
                - error: str, 错误信息（如果失败）
        """
        pass
    
    @abstractmethod
    def get_open_positions(self) -> Dict[str, Any]:
        """
        获取当前持仓信息
        
        Returns:
            Dict[str, Any]: 包含持仓信息的字典
                - success: bool, 是否成功
                - positions: List[Dict], 持仓列表
                - error: str, 错误信息（如果失败）
        """
        pass
    
    @abstractmethod
    def get_market_data(self, 
                       symbol: str, 
                       timeframe: str, 
                       limit: int = 500) -> Dict[str, Any]:
        """
        获取市场K线数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            limit: 数据条数限制
            
        Returns:
            Dict[str, Any]: 包含K线数据的字典
                - success: bool, 是否成功
                - data: List, K线数据列表
                - error: str, 错误信息（如果失败）
        """
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易对信息
        
        Args:
            symbol: 交易对符号
            
        Returns:
            Dict[str, Any]: 包含交易对信息的字典
                - success: bool, 是否成功
                - info: Dict, 交易对详情
                - error: str, 错误信息（如果失败）
        """
        pass
    
    def is_connected(self) -> bool:
        """
        检查连接状态
        
        Returns:
            bool: 是否已连接
        """
        return self._exchange is not None
    
    def get_supported_timeframes(self) -> List[str]:
        """
        获取支持的时间周期列表
        
        Returns:
            List[str]: 支持的时间周期
        """
        return [tf.value for tf in Timeframe]
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        验证交易对是否有效
        
        Args:
            symbol: 交易对符号
            
        Returns:
            bool: 交易对是否有效
        """
        result = self.get_symbol_info(symbol)
        return result.get('success', False)
    
    def format_symbol(self, symbol: str) -> str:
        """
        格式化交易对符号以适配交易所格式
        
        Args:
            symbol: 标准格式的交易对符号 (如 BTC/USDT)
            
        Returns:
            str: 交易所格式的交易对符号
        """
        # 默认实现，子类可以重写
        return symbol
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        统一错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            Dict[str, Any]: 标准化的错误响应
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': error.__class__.__name__
        }