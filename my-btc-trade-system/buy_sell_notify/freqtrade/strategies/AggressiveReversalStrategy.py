# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce

import talib.abstract as ta
import numpy as np  
import pandas as pd
from pandas import DataFrame

class AggressiveReversalStrategy(IStrategy):
    """
    激进反转策略
    基于原系统的反转策略逻辑：
    在1小时图上寻找市场过度延伸的机会
    
    开仓条件:
    - 做多(抄底): RSI <= 28 AND 价格触及布林下轨
    - 做空(摸顶): RSI >= 72 AND 价格触及布林上轨
    
    这是一个高风险高回报的短线策略，使用更小的仓位和更紧的止损
    """

    # 策略参数
    INTERFACE_VERSION = 3
    
    # 最小 ROI 设置 - 反转策略目标更保守(1.5R和2R)
    minimal_roi = {
        "0": 0.20,   # 20% (对应2R目标)
        "30": 0.15,  # 30分钟后15% (对应1.5R目标)  
        "60": 0.08,  # 1小时后8%
        "120": 0.05, # 2小时后5%
        "180": 0.03  # 3小时后3%
    }

    # 止损设置 - 更紧的止损(对应原系统1.5倍ATR)
    stoploss = -0.03  # 3% 止损

    # 时间框架
    timeframe = '1h'
    
    # 启用位置堆叠
    position_stacking = False
    
    # 可以做多做空
    can_short = True

    # 启用使用卖出信号
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # 追踪止损设置 - 更积极的追踪
    trailing_stop = True
    trailing_stop_positive = 0.01  # 盈利1%后启用追踪止损
    trailing_stop_positive_offset = 0.03  # 追踪止损偏移3%
    trailing_only_offset_is_reached = True

    # 策略特定参数 - 对应原配置
    # RSI 参数
    rsi_period = 14
    rsi_oversold = 28    # 对应原配置
    rsi_overbought = 72  # 对应原配置
    
    # 布林带参数
    bb_period = 20
    bb_std = 2.0
    
    # ATR参数
    atr_period = 14
    
    # 成交量过滤
    volume_check = True

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        计算技术指标
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        
        # 布林带
        bollinger = ta.BBANDS(dataframe, timeperiod=self.bb_period, nbdevup=float(self.bb_std), nbdevdn=float(self.bb_std))
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_upper'] = bollinger['upperband']
        
        # ATR - 用于动态止损
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period)
        
        # 价格与布林带关系
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])
        
        # 成交量相关指标
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        
        # 价格波动率
        dataframe['price_change'] = dataframe['close'].pct_change()
        
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        买入信号：抄底反转
        """
        conditions = []
        
        # 核心反转条件：RSI严重超卖 AND 触及布林下轨
        conditions.append(dataframe['rsi'] <= self.rsi_oversold)
        conditions.append(
            (dataframe['close'] <= dataframe['bb_lower']) |  # 触及或跌破布林下轨
            (dataframe['low'] <= dataframe['bb_lower'])      # 或最低价触及布林下轨
        )
        
        # 额外过滤条件
        conditions.append(dataframe['volume'] > 0)  # 有交易量
        
        # 可选：成交量增加确认
        if self.volume_check:
            conditions.append(dataframe['volume'] > dataframe['volume_sma'] * 0.5)  # 成交量不能太低
        
        # 避免在极端下跌中抄底
        conditions.append(dataframe['price_change'] > -0.10)  # 单根K线跌幅不超过10%
        
        # 确保不是在长期下跌趋势的底部
        conditions.append(dataframe['bb_percent'] < 0.2)  # 价格必须在布林带下方区域
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        卖出信号：摸顶反转
        """
        conditions = []
        
        # 核心反转条件：RSI严重超买 AND 触及布林上轨
        conditions.append(dataframe['rsi'] >= self.rsi_overbought)
        conditions.append(
            (dataframe['close'] >= dataframe['bb_upper']) |  # 触及或突破布林上轨
            (dataframe['high'] >= dataframe['bb_upper'])     # 或最高价触及布林上轨
        )
        
        # 额外过滤条件
        conditions.append(dataframe['volume'] > 0)  # 有交易量
        
        # 可选：成交量增加确认
        if self.volume_check:
            conditions.append(dataframe['volume'] > dataframe['volume_sma'] * 0.5)  # 成交量不能太低
        
        # 避免在极端上涨中摸顶
        conditions.append(dataframe['price_change'] < 0.10)  # 单根K线涨幅不超过10%
        
        # 确保在布林带上方区域
        conditions.append(dataframe['bb_percent'] > 0.8)  # 价格必须在布林带上方区域
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        基于ATR的动态止损 (对应原系统的1.5倍ATR止损)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        
        if 'atr' in last_candle:
            atr_value = last_candle['atr']
            # 使用1.5倍ATR作为止损距离 (对应原反转策略配置)
            atr_stoploss = 1.5 * atr_value / current_rate
            
            # 限制止损范围在1.5%-8%之间 (反转策略更紧的止损)
            return max(-0.08, min(-0.015, -atr_stoploss))
        
        return self.stoploss

    def custom_sell(self, pair: str, trade: 'Trade', current_time, current_rate: float,
                   current_profit: float, **kwargs) -> 'Optional[Union[str, bool]]':
        """
        自定义卖出逻辑：快速止盈
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        
        # 快速止盈：如果盈利超过5%且RSI回调，则考虑出场
        if current_profit > 0.05:
            if trade.is_short:
                # 做空时，如果RSI回落到50以下，考虑平仓
                if last_candle['rsi'] < 50:
                    return 'rsi_normalization'
            else:
                # 做多时，如果RSI回升到50以上，考虑平仓  
                if last_candle['rsi'] > 50:
                    return 'rsi_normalization'
        
        # 如果反转信号消失且有盈利，提前出场
        if current_profit > 0.02:  # 盈利超过2%
            if trade.is_short:
                # 做空时，如果价格回到布林带中轨附近
                if last_candle['close'] < last_candle['bb_middle']:
                    return 'reversal_signal_weakening'
            else:
                # 做多时，如果价格回到布林带中轨附近
                if last_candle['close'] > last_candle['bb_middle']:
                    return 'reversal_signal_weakening'
        
        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time, entry_tag: 'Optional[str]', 
                           side: str, **kwargs) -> bool:
        """
        交易入场确认：额外的风险控制
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return False
            
        last_candle = dataframe.iloc[-1]
        
        # 确保RSI确实在极值区域
        if side == 'long':
            return last_candle['rsi'] <= self.rsi_oversold + 5  # 允许5点缓冲
        else:
            return last_candle['rsi'] >= self.rsi_overbought - 5  # 允许5点缓冲
            
    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        """
        杠杆设置：反转策略使用较低杠杆
        """
        # 反转策略风险较高，使用较低杠杆
        return min(proposed_leverage, 3.0)  # 最大3倍杠杆