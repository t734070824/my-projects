"""
技术分析模块
提供各种技术指标的计算和信号生成功能
"""

from typing import Dict, Any, Optional, Tuple
import pandas as pd
import pandas_ta as ta
import logging

from utils.constants import (
    TradingSignal, DEFAULT_RSI_PERIOD, DEFAULT_SMA_PERIOD, 
    RSI_OVERSOLD_THRESHOLD, RSI_OVERBOUGHT_THRESHOLD,
    RSI_EXTREME_OVERSOLD, RSI_EXTREME_OVERBOUGHT
)
from utils.helpers import safe_float_conversion


class TechnicalAnalyzer:
    """
    技术分析器
    
    提供完整的技术指标计算和交易信号生成功能
    """
    
    def __init__(self, symbol: str, timeframe: str):
        """
        初始化技术分析器
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.logger = logging.getLogger(f"TechnicalAnalyzer.{symbol}.{timeframe}")
    
    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行完整的技术分析
        
        Args:
            df: OHLCV数据DataFrame
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if df is None or len(df) < 50:
            return {
                'success': False,
                'error': '数据不足，无法进行技术分析'
            }
        
        try:
            # 计算各种技术指标
            indicators = self._calculate_indicators(df)
            
            # 生成各指标信号
            signals = self._generate_signals(indicators)
            
            # 计算综合评分
            total_score = self._calculate_total_score(signals)
            
            # 确定最终信号
            final_signal = self._determine_final_signal(total_score, signals)
            
            # 检查反转信号
            reversal_signal = self._check_reversal_signal(indicators)
            
            result = {
                'success': True,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'signal': final_signal,
                'reversal_signal': reversal_signal,
                'total_score': total_score,
                'close_price': safe_float_conversion(df['close'].iloc[-1]),
                'indicators': indicators,
                'signals': signals
            }
            
            self.logger.debug(f"技术分析完成: {final_signal}, 评分: {total_score}")
            return result
            
        except Exception as e:
            self.logger.error(f"技术分析失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'技术分析失败: {str(e)}'
            }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算技术指标
        
        Args:
            df: OHLCV数据DataFrame
            
        Returns:
            Dict[str, Any]: 技术指标结果
        """
        indicators = {}
        
        try:
            # RSI指标
            df.ta.rsi(length=DEFAULT_RSI_PERIOD, append=True)
            rsi_col = f'RSI_{DEFAULT_RSI_PERIOD}'
            if rsi_col in df.columns:
                indicators['rsi'] = safe_float_conversion(df[rsi_col].iloc[-1])
            
            # 移动平均线
            df.ta.sma(length=20, append=True)
            df.ta.sma(length=50, append=True)
            
            if 'SMA_20' in df.columns:
                indicators['sma_20'] = safe_float_conversion(df['SMA_20'].iloc[-1])
            if 'SMA_50' in df.columns:
                indicators['sma_50'] = safe_float_conversion(df['SMA_50'].iloc[-1])
            
            # MACD指标
            df.ta.macd(append=True)
            if 'MACD_12_26_9' in df.columns:
                indicators['macd'] = safe_float_conversion(df['MACD_12_26_9'].iloc[-1])
            if 'MACDs_12_26_9' in df.columns:
                indicators['macd_signal'] = safe_float_conversion(df['MACDs_12_26_9'].iloc[-1])
            if 'MACDh_12_26_9' in df.columns:
                indicators['macd_histogram'] = safe_float_conversion(df['MACDh_12_26_9'].iloc[-1])
            
            # 布林带
            df.ta.bbands(length=20, append=True)
            if 'BBL_20_2.0' in df.columns:
                indicators['bb_lower'] = safe_float_conversion(df['BBL_20_2.0'].iloc[-1])
            if 'BBM_20_2.0' in df.columns:
                indicators['bb_middle'] = safe_float_conversion(df['BBM_20_2.0'].iloc[-1])
            if 'BBU_20_2.0' in df.columns:
                indicators['bb_upper'] = safe_float_conversion(df['BBU_20_2.0'].iloc[-1])
            
            # ATR指标
            df.ta.atr(length=14, append=True)
            if 'ATRr_14' in df.columns:
                indicators['atr'] = safe_float_conversion(df['ATRr_14'].iloc[-1])
            
            # 当前价格
            indicators['current_price'] = safe_float_conversion(df['close'].iloc[-1])
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"计算技术指标失败: {e}", exc_info=True)
            return {}
    
    def _generate_signals(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """
        根据技术指标生成交易信号
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            Dict[str, str]: 各指标信号
        """
        signals = {}
        
        try:
            # RSI信号
            rsi = indicators.get('rsi', 50)
            if rsi <= RSI_OVERSOLD_THRESHOLD:
                signals['rsi'] = TradingSignal.WEAK_BUY.value
            elif rsi >= RSI_OVERBOUGHT_THRESHOLD:
                signals['rsi'] = TradingSignal.WEAK_SELL.value
            else:
                signals['rsi'] = TradingSignal.NEUTRAL.value
            
            # 移动平均线信号
            current_price = indicators.get('current_price', 0)
            sma_20 = indicators.get('sma_20', 0)
            sma_50 = indicators.get('sma_50', 0)
            
            if current_price > sma_20 > sma_50:
                signals['sma'] = TradingSignal.STRONG_BUY.value
            elif current_price > sma_20:
                signals['sma'] = TradingSignal.WEAK_BUY.value
            elif current_price < sma_20 < sma_50:
                signals['sma'] = TradingSignal.STRONG_SELL.value
            elif current_price < sma_20:
                signals['sma'] = TradingSignal.WEAK_SELL.value
            else:
                signals['sma'] = TradingSignal.NEUTRAL.value
            
            # MACD信号
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_histogram = indicators.get('macd_histogram', 0)
            
            if macd > macd_signal and macd_histogram > 0:
                signals['macd'] = TradingSignal.STRONG_BUY.value
            elif macd > macd_signal:
                signals['macd'] = TradingSignal.WEAK_BUY.value
            elif macd < macd_signal and macd_histogram < 0:
                signals['macd'] = TradingSignal.STRONG_SELL.value
            elif macd < macd_signal:
                signals['macd'] = TradingSignal.WEAK_SELL.value
            else:
                signals['macd'] = TradingSignal.NEUTRAL.value
            
            # 布林带信号
            bb_lower = indicators.get('bb_lower', 0)
            bb_upper = indicators.get('bb_upper', 0)
            bb_middle = indicators.get('bb_middle', 0)
            
            if current_price <= bb_lower:
                signals['bollinger'] = TradingSignal.STRONG_BUY.value
            elif current_price >= bb_upper:
                signals['bollinger'] = TradingSignal.STRONG_SELL.value
            elif current_price > bb_middle:
                signals['bollinger'] = TradingSignal.WEAK_BUY.value
            elif current_price < bb_middle:
                signals['bollinger'] = TradingSignal.WEAK_SELL.value
            else:
                signals['bollinger'] = TradingSignal.NEUTRAL.value
            
            return signals
            
        except Exception as e:
            self.logger.error(f"生成交易信号失败: {e}", exc_info=True)
            return {}
    
    def _calculate_total_score(self, signals: Dict[str, str]) -> int:
        """
        计算综合评分
        
        Args:
            signals: 各指标信号字典
            
        Returns:
            int: 综合评分（-100到+100）
        """
        signal_weights = {
            'rsi': 20,
            'sma': 30,
            'macd': 25,
            'bollinger': 25
        }
        
        signal_scores = {
            TradingSignal.STRONG_BUY.value: 100,
            TradingSignal.WEAK_BUY.value: 50,
            TradingSignal.NEUTRAL.value: 0,
            TradingSignal.WEAK_SELL.value: -50,
            TradingSignal.STRONG_SELL.value: -100
        }
        
        total_score = 0
        total_weight = 0
        
        for indicator, signal in signals.items():
            if indicator in signal_weights:
                weight = signal_weights[indicator]
                score = signal_scores.get(signal, 0)
                total_score += (score * weight) / 100
                total_weight += weight
        
        if total_weight > 0:
            return int(total_score * 100 / total_weight)
        
        return 0
    
    def _determine_final_signal(self, total_score: int, signals: Dict[str, str]) -> str:
        """
        确定最终交易信号
        
        Args:
            total_score: 综合评分
            signals: 各指标信号字典
            
        Returns:
            str: 最终交易信号
        """
        if total_score >= 60:
            return TradingSignal.STRONG_BUY.value
        elif total_score >= 20:
            return TradingSignal.WEAK_BUY.value
        elif total_score <= -60:
            return TradingSignal.STRONG_SELL.value
        elif total_score <= -20:
            return TradingSignal.WEAK_SELL.value
        else:
            return TradingSignal.NEUTRAL.value
    
    def _check_reversal_signal(self, indicators: Dict[str, Any]) -> str:
        """
        检查反转信号（极端RSI + 布林带边界）
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            str: 反转信号类型
        """
        rsi = indicators.get('rsi', 50)
        current_price = indicators.get('current_price', 0)
        bb_lower = indicators.get('bb_lower', 0)
        bb_upper = indicators.get('bb_upper', 0)
        
        # 极端超卖 + 触及布林下轨
        if rsi <= RSI_EXTREME_OVERSOLD and current_price <= bb_lower:
            return "EXECUTE_REVERSAL_LONG"
        
        # 极端超买 + 触及布林上轨
        if rsi >= RSI_EXTREME_OVERBOUGHT and current_price >= bb_upper:
            return "EXECUTE_REVERSAL_SHORT"
        
        return "NONE"
    
    def calculate_atr(self, df: pd.DataFrame, length: int = 14) -> Optional[float]:
        """
        单独计算ATR指标
        
        Args:
            df: OHLCV数据DataFrame
            length: ATR周期长度
            
        Returns:
            Optional[float]: ATR值
        """
        try:
            if len(df) < length:
                return None
            
            df_copy = df.copy()
            df_copy.ta.atr(length=length, append=True)
            
            atr_col = f'ATRr_{length}'
            if atr_col in df_copy.columns:
                return safe_float_conversion(df_copy[atr_col].iloc[-1])
            
            return None
            
        except Exception as e:
            self.logger.error(f"计算ATR失败: {e}", exc_info=True)
            return None