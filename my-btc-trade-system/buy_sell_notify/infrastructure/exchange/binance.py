"""
Binance交易所接口实现
基于ccxt库实现的Binance期货交易接口
"""

from typing import Dict, Any, List, Optional
import ccxt
import pandas as pd

from infrastructure.exchange.base import ExchangeInterface
from utils.constants import ErrorMessage
from utils.helpers import safe_float_conversion


class BinanceExchange(ExchangeInterface):
    """
    Binance交易所接口实现
    
    提供与Binance期货API的完整集成，包括账户信息、持仓管理和市场数据获取
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Binance交易所接口
        
        Args:
            config: 配置字典，包含api_key, secret_key, proxy等
        """
        super().__init__(config)
        self._exchange: Optional[ccxt.binance] = None
    
    def connect(self) -> bool:
        """
        连接到Binance交易所
        
        Returns:
            bool: 连接是否成功
        """
        try:
            exchange_config = {
                'apiKey': self.config['api_key'],
                'secret': self.config['secret_key'],
                'options': {'defaultType': 'future'},  # 使用期货接口
                'enableRateLimit': True,
                'sandbox': self.config.get('sandbox', False)
            }
            
            # 配置代理
            if self.config.get('proxy'):
                proxy_url = self.config['proxy']
                exchange_config['proxies'] = {
                    'http': proxy_url, 
                    'https': proxy_url
                }
                self.logger.info(f"使用代理: {proxy_url}")
            
            self._exchange = ccxt.binance(exchange_config)
            
            # 测试连接
            self._exchange.load_markets()
            self.logger.info("成功连接到Binance期货接口")
            return True
            
        except ccxt.AuthenticationError as e:
            self.logger.error(f"Binance API认证失败: {e}")
            return False
        except ccxt.NetworkError as e:
            self.logger.error(f"网络连接失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"连接Binance时发生未知错误: {e}", exc_info=True)
            return False
    
    def get_account_balance(self) -> Dict[str, Any]:
        """
        获取账户余额信息
        
        Returns:
            Dict[str, Any]: 账户余额信息
        """
        if not self.is_connected():
            return self.handle_error(Exception("未连接到交易所"), "获取账户余额")
        
        try:
            balance_data = self._exchange.fetch_balance()
            usdt_balance = next(
                (item for item in balance_data['info']['assets'] if item['asset'] == 'USDT'), 
                {}
            )
            
            return {
                'success': True,
                'balance': {
                    'wallet_balance': safe_float_conversion(usdt_balance.get('walletBalance')),
                    'available_balance': safe_float_conversion(usdt_balance.get('availableBalance')),
                    'unrealized_profit': safe_float_conversion(usdt_balance.get('unrealizedProfit')),
                }
            }
            
        except ccxt.AuthenticationError as e:
            return self.handle_error(e, ErrorMessage.API_AUTH_FAILED)
        except ccxt.NetworkError as e:
            return self.handle_error(e, ErrorMessage.NETWORK_ERROR)
        except Exception as e:
            return self.handle_error(e, "获取账户余额")
    
    def get_open_positions(self) -> Dict[str, Any]:
        """
        获取当前持仓信息
        
        Returns:
            Dict[str, Any]: 持仓信息
        """
        if not self.is_connected():
            return self.handle_error(Exception("未连接到交易所"), "获取持仓信息")
        
        try:
            positions_data = self._exchange.fetch_positions()
            open_positions = [p for p in positions_data if safe_float_conversion(p['info']['positionAmt']) != 0]
            
            # 格式化持仓信息
            formatted_positions = []
            for position in open_positions:
                position_amt = safe_float_conversion(position['info']['positionAmt'])
                
                formatted_positions.append({
                    'symbol': position['symbol'],
                    'side': 'long' if position_amt > 0 else 'short',
                    'size': abs(position_amt),
                    'entry_price': safe_float_conversion(position['entryPrice']),
                    'mark_price': safe_float_conversion(position['markPrice']),
                    'unrealized_pnl': safe_float_conversion(position['unrealizedPnl']),
                    'leverage': int(safe_float_conversion(position['leverage'], 1)),
                    'percentage': safe_float_conversion(position['percentage']),
                })
            
            self.logger.debug(f"发现 {len(formatted_positions)} 个未平仓头寸")
            
            return {
                'success': True,
                'positions': formatted_positions
            }
            
        except ccxt.AuthenticationError as e:
            return self.handle_error(e, ErrorMessage.API_AUTH_FAILED)
        except ccxt.NetworkError as e:
            return self.handle_error(e, ErrorMessage.NETWORK_ERROR)
        except Exception as e:
            return self.handle_error(e, "获取持仓信息")
    
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
            Dict[str, Any]: K线数据
        """
        if not self.is_connected():
            return self.handle_error(Exception("未连接到交易所"), "获取市场数据")
        
        try:
            # 获取K线数据
            ohlcv_data = self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv_data or len(ohlcv_data) < 10:
                return {
                    'success': False,
                    'error': ErrorMessage.INSUFFICIENT_DATA,
                    'data': []
                }
            
            # 转换为DataFrame格式
            df = pd.DataFrame(
                ohlcv_data, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # 确保数值类型正确
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return {
                'success': True,
                'data': df,
                'symbol': symbol,
                'timeframe': timeframe,
                'count': len(df)
            }
            
        except ccxt.BaseError as e:
            return self.handle_error(e, f"获取 {symbol} 的市场数据")
        except Exception as e:
            return self.handle_error(e, f"获取 {symbol} 的市场数据")
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易对信息
        
        Args:
            symbol: 交易对符号
            
        Returns:
            Dict[str, Any]: 交易对信息
        """
        if not self.is_connected():
            return self.handle_error(Exception("未连接到交易所"), "获取交易对信息")
        
        try:
            markets = self._exchange.load_markets()
            
            if symbol not in markets:
                return {
                    'success': False,
                    'error': f"交易对 {symbol} 不存在"
                }
            
            market = markets[symbol]
            
            return {
                'success': True,
                'info': {
                    'symbol': symbol,
                    'base': market['base'],
                    'quote': market['quote'],
                    'active': market.get('active', False),
                    'type': market.get('type', 'spot'),
                    'precision': {
                        'amount': market['precision']['amount'],
                        'price': market['precision']['price']
                    },
                    'limits': market.get('limits', {})
                }
            }
            
        except Exception as e:
            return self.handle_error(e, f"获取交易对 {symbol} 信息")
    
    def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        获取当前价格
        
        Args:
            symbol: 交易对符号
            
        Returns:
            Dict[str, Any]: 当前价格信息
        """
        if not self.is_connected():
            return self.handle_error(Exception("未连接到交易所"), "获取当前价格")
        
        try:
            ticker = self._exchange.fetch_ticker(symbol)
            
            return {
                'success': True,
                'price': safe_float_conversion(ticker['last']),
                'bid': safe_float_conversion(ticker['bid']),
                'ask': safe_float_conversion(ticker['ask']),
                'volume': safe_float_conversion(ticker['baseVolume']),
                'timestamp': ticker.get('timestamp')
            }
            
        except Exception as e:
            return self.handle_error(e, f"获取 {symbol} 当前价格")
    
    def format_symbol(self, symbol: str) -> str:
        """
        格式化交易对符号为Binance格式
        
        Args:
            symbol: 标准格式的交易对符号 (如 BTC/USDT)
            
        Returns:
            str: Binance格式的交易对符号
        """
        # Binance使用标准的 BASE/QUOTE 格式
        return symbol
    
    def get_account_status(self) -> Dict[str, Any]:
        """
        获取完整的账户状态（余额 + 持仓）
        
        Returns:
            Dict[str, Any]: 完整账户状态
        """
        self.logger.debug("开始获取账户状态...")
        
        # 获取余额信息
        balance_result = self.get_account_balance()
        if not balance_result['success']:
            return balance_result
        
        # 获取持仓信息
        positions_result = self.get_open_positions()
        if not positions_result['success']:
            return positions_result
        
        return {
            'success': True,
            'usdt_balance': {
                'walletBalance': str(balance_result['balance']['wallet_balance']),
                'availableBalance': str(balance_result['balance']['available_balance']),
                'unrealizedProfit': str(balance_result['balance']['unrealized_profit'])
            },
            'open_positions': positions_result['positions']
        }