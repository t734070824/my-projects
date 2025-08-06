"""
信号生成器
整合技术分析和市场数据，生成最终的交易信号
"""

from typing import Dict, Any, Optional
import logging

from core.signals.analyzer import TechnicalAnalyzer
from infrastructure.exchange.base import ExchangeInterface
from config.settings import TradingPairConfig
from utils.constants import ErrorMessage, SuccessMessage
from utils.helpers import create_log_safe_json


class SignalGenerator:
    """
    信号生成器
    
    负责整合技术分析结果和市场数据，生成最终的交易信号
    """
    
    def __init__(self, symbol: str, timeframe: str, exchange: ExchangeInterface):
        """
        初始化信号生成器
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            exchange: 交易所接口
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = exchange
        self.analyzer = TechnicalAnalyzer(symbol, timeframe)
        self.logger = logging.getLogger(f"SignalGenerator.{symbol}.{timeframe}")
    
    def generate_signal(self, 
                       account_status: Optional[Dict] = None,
                       atr_info: Optional[Dict] = None,
                       config: Optional[TradingPairConfig] = None) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            account_status: 账户状态信息
            atr_info: ATR信息
            config: 交易对配置
            
        Returns:
            Dict[str, Any]: 信号生成结果
        """
        self.logger.info(f"开始为 {self.symbol}({self.timeframe}) 生成信号...")
        
        try:
            # 1. 获取市场数据
            market_data_result = self.exchange.get_market_data(
                self.symbol, self.timeframe, limit=200
            )
            
            if not market_data_result['success']:
                return {
                    'success': False,
                    'error': market_data_result['error'],
                    'symbol': self.symbol,
                    'timeframe': self.timeframe
                }
            
            df = market_data_result['data']
            
            # 2. 执行技术分析
            analysis_result = self.analyzer.analyze(df)
            
            if not analysis_result['success']:
                return {
                    'success': False,
                    'error': analysis_result['error'],
                    'symbol': self.symbol,
                    'timeframe': self.timeframe
                }
            
            # 3. 整合结果
            final_result = {
                'success': True,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'signal': analysis_result['signal'],
                'reversal_signal': analysis_result['reversal_signal'],
                'total_score': analysis_result['total_score'],
                'close_price': analysis_result['close_price'],
                'timestamp': market_data_result.get('timestamp'),
                
                # 分解的信号详情
                'rsi_signal': analysis_result['signals'].get('rsi'),
                'sma_signal': analysis_result['signals'].get('sma'),  
                'macd_signal': analysis_result['signals'].get('macd'),
                'bollinger_signal': analysis_result['signals'].get('bollinger'),
                
                # 技术指标原始值
                'rsi_value': analysis_result['indicators'].get('rsi'),
                'current_price': analysis_result['indicators'].get('current_price'),
            }
            
            # 4. 添加ATR信息（如果提供）
            if atr_info:
                final_result['atr_info'] = atr_info
            
            # 5. 添加账户状态（如果提供）
            if account_status:
                final_result['account_status'] = account_status
            
            self.logger.info(f"信号生成成功: {analysis_result['signal']}, 评分: {analysis_result['total_score']}")
            
            # 记录技术分析摘要（不包含敏感信息）
            analysis_summary = create_log_safe_json({
                'signal': final_result['signal'],
                'score': final_result['total_score'],
                'rsi': final_result.get('rsi_value'),
                'price': final_result.get('current_price')
            })
            
            self.logger.debug(f"技术分析摘要: {analysis_summary}")
            
            return final_result
            
        except Exception as e:
            error_msg = f"生成 {self.symbol}({self.timeframe}) 信号时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                'success': False,
                'error': error_msg,
                'symbol': self.symbol,
                'timeframe': self.timeframe
            }
    
    def get_atr_info(self, config: TradingPairConfig) -> Dict[str, Any]:
        """
        获取ATR信息
        
        Args:
            config: 交易对配置
            
        Returns:
            Dict[str, Any]: ATR信息
        """
        self.logger.debug(f"获取 {self.symbol} 的ATR信息 (周期: {config.timeframe}, 长度: {config.atr_length})")
        
        try:
            # 获取ATR计算所需的数据
            market_data_result = self.exchange.get_market_data(
                self.symbol, config.timeframe, limit=200
            )
            
            if not market_data_result['success']:
                return {
                    'success': False,
                    'error': market_data_result['error']
                }
            
            df = market_data_result['data']
            
            # 计算ATR
            atr_value = self.analyzer.calculate_atr(df, config.atr_length)
            
            if atr_value is None:
                return {
                    'success': False,
                    'error': 'ATR计算失败'
                }
            
            self.logger.debug(f"{self.symbol} ATR值: {atr_value}")
            
            return {
                'success': True,
                'atr': round(atr_value, 6),
                'timeframe': config.timeframe,
                'length': config.atr_length,
                'symbol': self.symbol
            }
            
        except Exception as e:
            error_msg = f"获取 {self.symbol} ATR信息失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return {
                'success': False,
                'error': error_msg
            }