# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce

import talib.abstract as ta
import numpy as np  
import pandas as pd
from pandas import DataFrame

class TripleTimeframeTrendStrategy(IStrategy):
    """
    三重时间框架趋势跟踪策略
    基于原系统的策略逻辑：
    1. 战略层面(1d): 判断长期趋势方向
    2. 战术层面(4h): 判断中期趋势方向  
    3. 执行层面(1h): 寻找具体入场信号
    
    开仓条件:
    - 做多: 1d看多 AND 4h看多 AND 1h出现买入信号
    - 做空: 1d看空 AND 4h看空 AND 1h出现卖出信号
    """

    # 策略参数
    INTERFACE_VERSION = 3
    
    # 最小 ROI 设置 - 对应原系统的2R和3R目标
    minimal_roi = {
        "0": 0.30,   # 30% (对应3R目标)
        "60": 0.20,  # 1小时后20% (对应2R目标)  
        "120": 0.10, # 2小时后10%
        "180": 0.05  # 3小时后5%
    }

    # 止损设置 - 对应原系统的2倍ATR
    stoploss = -0.05  # 5% 止损

    # 时间框架
    timeframe = '1h'
    
    # 启用位置堆叠
    position_stacking = False
    
    # 只能做多
    can_short = True

    # 启用使用卖出信号
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    # 追踪止损设置
    trailing_stop = True
    trailing_stop_positive = 0.02  # 盈利2%后启用追踪止损
    trailing_stop_positive_offset = 0.05  # 追踪止损偏移5%
    trailing_only_offset_is_reached = True

    # 策略特定参数
    # SMA 参数
    sma_short_period = 20
    sma_long_period = 50
    
    # MACD 参数  
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    # RSI 参数
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    
    # 布林带参数
    bb_period = 20
    bb_std = 2
    
    # 一目均衡表参数
    ichimoku_conversion = 9
    ichimoku_base = 26
    ichimoku_lagging = 52
    
    # ATR参数
    atr_period = 14

    def informative_pairs(self):
        """
        定义需要获取的额外时间框架数据
        """
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        
        # 添加1d和4h的数据
        for pair in pairs:
            informative_pairs.extend([
                (pair, '1d'),
                (pair, '4h')
            ])
            
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        计算所有技术指标
        """
        # 获取额外时间框架的数据
        inf_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1d')
        inf_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='4h')
        
        # === 1小时指标计算 (执行层面) ===
        
        # SMA
        dataframe['sma_short'] = ta.SMA(dataframe, timeperiod=self.sma_short_period)
        dataframe['sma_long'] = ta.SMA(dataframe, timeperiod=self.sma_long_period)
        
        # MACD
        macd = ta.MACD(dataframe, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal'] 
        dataframe['macdhist'] = macd['macdhist']
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        
        # 布林带
        bollinger = ta.BBANDS(dataframe, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std)
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_upper'] = bollinger['upperband']
        
        # 一目均衡表
        ichimoku = self.ichimoku(dataframe, 
                               conversion_line_period=self.ichimoku_conversion,
                               base_line_period=self.ichimoku_base,
                               lagging_span_period=self.ichimoku_lagging)
        dataframe['tenkan'] = ichimoku['tenkan_sen']
        dataframe['kijun'] = ichimoku['kijun_sen']
        dataframe['senkou_a'] = ichimoku['senkou_span_a'] 
        dataframe['senkou_b'] = ichimoku['senkou_span_b']
        dataframe['chikou'] = ichimoku['chikou_span']
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period)
        
        # === 计算1小时综合评分 ===
        dataframe['h1_score'] = self.calculate_timeframe_score(dataframe)
        
        # === 处理日线数据 (战略层面) ===
        if len(inf_1d) > 0:
            # 计算日线指标
            inf_1d['sma_short'] = ta.SMA(inf_1d, timeperiod=self.sma_short_period)
            inf_1d['sma_long'] = ta.SMA(inf_1d, timeperiod=self.sma_long_period) 
            inf_1d['rsi'] = ta.RSI(inf_1d, timeperiod=self.rsi_period)
            
            macd_1d = ta.MACD(inf_1d, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
            inf_1d['macd'] = macd_1d['macd']
            inf_1d['macdsignal'] = macd_1d['macdsignal']
            
            bollinger_1d = ta.BBANDS(inf_1d, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std)
            inf_1d['bb_lower'] = bollinger_1d['lowerband']
            inf_1d['bb_middle'] = bollinger_1d['middleband'] 
            inf_1d['bb_upper'] = bollinger_1d['upperband']
            
            # 计算日线评分
            inf_1d['daily_score'] = self.calculate_timeframe_score(inf_1d)
            
            # 合并到主数据框
            dataframe = pd.merge(dataframe, inf_1d[['date', 'daily_score']], on='date', how='left')
            dataframe['daily_score'] = dataframe['daily_score'].fillna(method='ffill')
        
        # === 处理4小时数据 (战术层面) ===
        if len(inf_4h) > 0:
            # 计算4小时指标  
            inf_4h['sma_short'] = ta.SMA(inf_4h, timeperiod=self.sma_short_period)
            inf_4h['sma_long'] = ta.SMA(inf_4h, timeperiod=self.sma_long_period)
            inf_4h['rsi'] = ta.RSI(inf_4h, timeperiod=self.rsi_period)
            
            macd_4h = ta.MACD(inf_4h, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
            inf_4h['macd'] = macd_4h['macd'] 
            inf_4h['macdsignal'] = macd_4h['macdsignal']
            
            bollinger_4h = ta.BBANDS(inf_4h, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std)
            inf_4h['bb_lower'] = bollinger_4h['lowerband']
            inf_4h['bb_middle'] = bollinger_4h['middleband']
            inf_4h['bb_upper'] = bollinger_4h['upperband']
            
            # 计算4小时评分
            inf_4h['h4_score'] = self.calculate_timeframe_score(inf_4h)
            
            # 合并到主数据框
            dataframe = pd.merge(dataframe, inf_4h[['date', 'h4_score']], on='date', how='left') 
            dataframe['h4_score'] = dataframe['h4_score'].fillna(method='ffill')
            
        # 填充缺失值
        dataframe['daily_score'] = dataframe['daily_score'].fillna(0)
        dataframe['h4_score'] = dataframe['h4_score'].fillna(0)
        
        return dataframe

    def calculate_timeframe_score(self, df: DataFrame) -> pd.Series:
        """
        计算时间框架的综合评分 (复制原系统逻辑)
        """
        score = pd.Series(0, index=df.index)
        
        # SMA 趋势评分 (+2/-2)
        score += np.where((df['close'] > df['sma_short']) & (df['sma_short'] > df['sma_long']), 2, 
                         np.where((df['close'] < df['sma_short']) & (df['sma_short'] < df['sma_long']), -2, 0))
        
        # MACD 评分 (+1/-1) 
        score += np.where(df['macd'] > df['macdsignal'], 1, -1)
        
        # RSI 评分 (+1/0/-1)
        score += np.where(df['rsi'] > 50, 1, np.where(df['rsi'] < 50, -1, 0))
        
        # 布林带评分 (+1/-1/0)
        score += np.where(df['close'] > df['bb_upper'], 1,
                         np.where(df['close'] < df['bb_lower'], -1, 0))
        
        return score

    def ichimoku(self, dataframe: DataFrame, conversion_line_period: int = 9, 
                 base_line_period: int = 26, lagging_span_period: int = 52) -> Dict:
        """
        一目均衡表指标计算
        """
        high = dataframe['high']
        low = dataframe['low'] 
        close = dataframe['close']
        
        # 转换线 (Tenkan-sen)
        tenkan_sen = (high.rolling(window=conversion_line_period).max() + 
                     low.rolling(window=conversion_line_period).min()) / 2
        
        # 基准线 (Kijun-sen) 
        kijun_sen = (high.rolling(window=base_line_period).max() + 
                    low.rolling(window=base_line_period).min()) / 2
        
        # 先行带A (Senkou Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(base_line_period)
        
        # 先行带B (Senkou Span B)
        senkou_span_b = ((high.rolling(window=lagging_span_period).max() + 
                         low.rolling(window=lagging_span_period).min()) / 2).shift(base_line_period)
        
        # 滞后线 (Chikou Span)
        chikou_span = close.shift(-base_line_period)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen, 
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }

    def populate_buy_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        买入信号：三重时间框架过滤
        """
        conditions = []
        
        # 战略层面：日线看多 (评分 > 0)
        conditions.append(dataframe['daily_score'] > 0)
        
        # 战术层面：4小时看多 (评分 > 0) 
        conditions.append(dataframe['h4_score'] > 0)
        
        # 执行层面：1小时出现强买入信号 (评分 >= 2)
        conditions.append(dataframe['h1_score'] >= 2)
        
        # 额外过滤条件
        conditions.append(dataframe['volume'] > 0)  # 有交易量
        conditions.append(dataframe['rsi'] < 80)    # RSI不过度超买
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        卖出信号：三重时间框架过滤
        """
        conditions = []
        
        # 战略层面：日线看空 (评分 < 0)
        conditions.append(dataframe['daily_score'] < 0)
        
        # 战术层面：4小时看空 (评分 < 0)
        conditions.append(dataframe['h4_score'] < 0) 
        
        # 执行层面：1小时出现强卖出信号 (评分 <= -2)
        conditions.append(dataframe['h1_score'] <= -2)
        
        # 额外过滤条件
        conditions.append(dataframe['volume'] > 0)  # 有交易量
        conditions.append(dataframe['rsi'] > 20)    # RSI不过度超卖
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        基于ATR的动态止损 (对应原系统的2倍ATR止损)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        
        if 'atr' in last_candle:
            atr_value = last_candle['atr']
            # 使用2倍ATR作为止损距离 (对应原配置)
            atr_stoploss = 2.0 * atr_value / current_rate
            
            # 限制止损范围在2%-10%之间
            return max(-0.10, min(-0.02, -atr_stoploss))
        
        return self.stoploss