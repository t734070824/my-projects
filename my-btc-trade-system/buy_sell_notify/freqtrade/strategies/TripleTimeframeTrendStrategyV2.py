# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List, Optional
from functools import reduce

import talib.abstract as ta
import numpy as np  
import pandas as pd
from pandas import DataFrame

class TripleTimeframeTrendStrategyV2(IStrategy):
    """
    三重时间框架趋势跟踪策略 V2 - 平衡版本
    
    基于优化版本的反馈，进行风险控制优化：
    1. 降低回撤：调整止损和仓位管理
    2. 提高胜率：收紧入场条件  
    3. 保持交易频率：适度平衡
    4. 优化币种权重：基于实际表现调整
    """

    # 策略参数
    INTERFACE_VERSION = 3
    
    # 平衡的ROI设置 - 更保守的止盈
    minimal_roi = {
        "0": 0.20,   # 20% 降低目标
        "30": 0.15,  # 30分钟后15%
        "60": 0.10,  # 1小时后10% 
        "120": 0.06, # 2小时后6%
        "240": 0.04, # 4小时后4%
        "480": 0.02  # 8小时后2%
    }

    # 更严格的止损
    stoploss = -0.035  # 3.5% 止损 (原4%)

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

    # 更保守的追踪止损设置
    trailing_stop = True
    trailing_stop_positive = 0.02   # 2%后启用追踪止损 (更保守)
    trailing_stop_positive_offset = 0.035  # 追踪止损偏移3.5%
    trailing_only_offset_is_reached = True

    # 平衡的策略参数
    sma_short_period = 19    # 18→19 稍微保守
    sma_long_period = 47     # 45→47 稍微保守
    
    macd_fast = 12      # 11→12 恢复标准
    macd_slow = 25      # 24→25 
    macd_signal = 9     # 8→9 恢复标准
    
    rsi_period = 14
    rsi_overbought = 70  # 72→70 更严格
    rsi_oversold = 30    # 28→30 更严格
    
    bb_period = 20
    bb_std = 2.0
    
    ichimoku_conversion = 9
    ichimoku_base = 26
    ichimoku_lagging = 52
    
    atr_period = 14

    # 基于实际表现调整权重
    pair_weights = {
        'XRP/USDT': 1.4,     # 577.88% - 最佳表现，加大权重
        'AVAX/USDT': 1.3,    # 514.12% - 优秀表现
        'WIF/USDT': 1.0,     # 396.57% - 但波动大，标准权重
        'ADA/USDT': 1.2,     # 367.26% - 良好表现
        'LINK/USDT': 1.1,    # 324.00% - 稳定表现
        'ETH/USDT': 1.1,     # 319.24% - 主流稳定
        'SOL/USDT': 1.2,     # 303.08% - 好表现
        'BNB/USDT': 1.0,     # 289.12% - 中等表现
        'DOGE/USDT': 1.0,    # 281.69% - 中等表现
        'DOT/USDT': 0.9,     # 180.89% - 较弱表现
        'NEAR/USDT': 0.8,    # 118.14% - 弱表现
        'SUI/USDT': 0.6,     # -7.89% - 亏损，大幅降权
        'BTC/USDT': 0.8,     # -14.93% - 意外亏损，降权
        'UNI/USDT': 0.4,     # -78.05% - 最差表现，严重降权
    }
    
    # 更严格的信号阈值
    strong_signal_threshold = 4    # 3→4 更严格
    weak_signal_threshold = 2      # 1→2 更严格
    
    market_volatility_period = 50
    trending_threshold = 0.025     # 0.02→0.025 更严格

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        for pair in pairs:
            informative_pairs.extend([
                (pair, '1d'),
                (pair, '4h')
            ])
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        inf_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1d')
        inf_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='4h')
        
        # 1小时指标
        dataframe['sma_short'] = ta.SMA(dataframe, timeperiod=self.sma_short_period)
        dataframe['sma_long'] = ta.SMA(dataframe, timeperiod=self.sma_long_period)
        
        macd = ta.MACD(dataframe, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal'] 
        dataframe['macdhist'] = macd['macdhist']
        
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        
        bollinger = ta.BBANDS(dataframe, timeperiod=self.bb_period, nbdevup=float(self.bb_std), nbdevdn=float(self.bb_std))
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])
        
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period)
        
        # 新增风险控制指标
        dataframe['volatility_rank'] = dataframe['atr'].rolling(50).rank(pct=True)  # ATR排名
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # 市场状态
        dataframe['market_volatility'] = dataframe['close'].rolling(self.market_volatility_period).std() / dataframe['close'].rolling(self.market_volatility_period).mean()
        dataframe['is_trending'] = dataframe['market_volatility'] > self.trending_threshold
        
        dataframe['h1_score'] = self.calculate_balanced_score(dataframe)
        
        # 处理日线数据
        if len(inf_1d) > 0:
            inf_1d['sma_short'] = ta.SMA(inf_1d, timeperiod=self.sma_short_period)
            inf_1d['sma_long'] = ta.SMA(inf_1d, timeperiod=self.sma_long_period) 
            inf_1d['rsi'] = ta.RSI(inf_1d, timeperiod=self.rsi_period)
            
            macd_1d = ta.MACD(inf_1d, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
            inf_1d['macd'] = macd_1d['macd']
            inf_1d['macdsignal'] = macd_1d['macdsignal']
            inf_1d['macdhist'] = macd_1d['macdhist']
            
            bollinger_1d = ta.BBANDS(inf_1d, timeperiod=self.bb_period, nbdevup=float(self.bb_std), nbdevdn=float(self.bb_std))
            inf_1d['bb_lower'] = bollinger_1d['lowerband']
            inf_1d['bb_middle'] = bollinger_1d['middleband'] 
            inf_1d['bb_upper'] = bollinger_1d['upperband']
            
            inf_1d['daily_score'] = self.calculate_balanced_score(inf_1d)
            
            dataframe = pd.merge(dataframe, inf_1d[['date', 'daily_score']], on='date', how='left')
            dataframe['daily_score'] = dataframe['daily_score'].fillna(method='ffill')
        
        # 处理4小时数据
        if len(inf_4h) > 0:
            inf_4h['sma_short'] = ta.SMA(inf_4h, timeperiod=self.sma_short_period)
            inf_4h['sma_long'] = ta.SMA(inf_4h, timeperiod=self.sma_long_period)
            inf_4h['rsi'] = ta.RSI(inf_4h, timeperiod=self.rsi_period)
            
            macd_4h = ta.MACD(inf_4h, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
            inf_4h['macd'] = macd_4h['macd'] 
            inf_4h['macdsignal'] = macd_4h['macdsignal']
            inf_4h['macdhist'] = macd_4h['macdhist']
            
            bollinger_4h = ta.BBANDS(inf_4h, timeperiod=self.bb_period, nbdevup=float(self.bb_std), nbdevdn=float(self.bb_std))
            inf_4h['bb_lower'] = bollinger_4h['lowerband']
            inf_4h['bb_middle'] = bollinger_4h['middleband']
            inf_4h['bb_upper'] = bollinger_4h['upperband']
            
            inf_4h['h4_score'] = self.calculate_balanced_score(inf_4h)
            
            dataframe = pd.merge(dataframe, inf_4h[['date', 'h4_score']], on='date', how='left') 
            dataframe['h4_score'] = dataframe['h4_score'].fillna(method='ffill')
            
        dataframe['daily_score'] = dataframe['daily_score'].fillna(0)
        dataframe['h4_score'] = dataframe['h4_score'].fillna(0)
        
        dataframe['signal_strength'] = self.calculate_signal_strength(dataframe)
        
        return dataframe

    def calculate_balanced_score(self, df: DataFrame) -> pd.Series:
        """平衡版评分计算 - 更保守但准确"""
        score = pd.Series(0.0, index=df.index)
        
        # SMA趋势评分 - 标准权重
        sma_trend = np.where(
            (df['close'] > df['sma_short']) & (df['sma_short'] > df['sma_long']), 2,
            np.where(
                (df['close'] < df['sma_short']) & (df['sma_short'] < df['sma_long']), -2,
                np.where(df['close'] > df['sma_short'], 1, -1)
            )
        )
        score += sma_trend
        
        # MACD评分 - 更重视histogram
        if 'macdhist' in df.columns:
            macd_score = np.where(
                (df['macd'] > df['macdsignal']) & (df['macdhist'] > 0), 2,
                np.where(
                    (df['macd'] < df['macdsignal']) & (df['macdhist'] < 0), -2,
                    np.where(df['macd'] > df['macdsignal'], 1, -1)
                )
            )
        else:
            macd_score = np.where(df['macd'] > df['macdsignal'], 1, -1)
        score += macd_score
        
        # RSI评分 - 更保守
        rsi_score = np.where(
            df['rsi'] > 65, 1,
            np.where(df['rsi'] < 35, -1, 0)
        )
        score += rsi_score * 0.5  # 降低权重
        
        # 布林带评分
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            bb_score = np.where(
                df['close'] > df['bb_upper'], 0.5,  # 降低权重
                np.where(df['close'] < df['bb_lower'], -0.5, 0)
            )
            score += bb_score
        
        return score

    def calculate_signal_strength(self, dataframe: DataFrame) -> pd.Series:
        """计算信号强度 - 更保守的评分"""
        strength = pd.Series(0.0, index=dataframe.index)
        
        daily_weight = abs(dataframe['daily_score']) * 0.5   # 增加日线权重
        h4_weight = abs(dataframe['h4_score']) * 0.3  
        h1_weight = abs(dataframe['h1_score']) * 0.2
        
        # 成交量和波动率确认
        volume_confirm = np.where(dataframe['volume_ratio'] > 1.2, 0.3, 0)
        volatility_penalty = np.where(dataframe['volatility_rank'] > 0.8, -0.5, 0)  # 高波动惩罚
        
        strength = daily_weight + h4_weight + h1_weight + volume_confirm + volatility_penalty
        
        return np.clip(strength, 0, 10)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """更严格的入场条件"""
        pair = metadata['pair']
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        # 对表现差的币种直接跳过
        if pair_weight < 0.7:
            return dataframe
        
        conditions_strong = []
        conditions_weak = []
        
        # 强信号 - 更严格
        conditions_strong.append(dataframe['daily_score'] >= 1)    # 更严格
        conditions_strong.append(dataframe['h4_score'] >= 1)      # 更严格  
        conditions_strong.append(dataframe['h1_score'] >= self.strong_signal_threshold)
        conditions_strong.append(dataframe['signal_strength'] >= 6)  # 新增强度要求
        
        # 弱信号 - 只在高权重币种中使用
        if pair_weight >= 1.2:
            weak_cond_1 = (
                (dataframe['daily_score'] > 1) & 
                (dataframe['h4_score'] > 0) & 
                (dataframe['h1_score'] >= self.weak_signal_threshold) &
                (dataframe['signal_strength'] >= 4)
            )
            conditions_weak.append(weak_cond_1)
        
        # 通用过滤 - 更严格
        common_filters = []
        common_filters.append(dataframe['volume'] > 0)
        common_filters.append(dataframe['rsi'] < self.rsi_overbought)
        common_filters.append(dataframe['volume_ratio'] > 1.0)     # 更严格
        common_filters.append(dataframe['volatility_rank'] < 0.9)  # 避免极高波动
        
        # 强信号
        if conditions_strong and common_filters:
            strong_signal = reduce(lambda x, y: x & y, conditions_strong + common_filters)
            dataframe.loc[strong_signal, 'buy'] = 1
            dataframe.loc[strong_signal, 'buy_tag'] = 'strong_v2'
        
        # 弱信号 
        if conditions_weak and common_filters:
            weak_signal = reduce(lambda x, y: x | y, conditions_weak)
            weak_signal = weak_signal & reduce(lambda x, y: x & y, common_filters)
            
            if 'buy' in dataframe.columns:
                weak_signal = weak_signal & (dataframe['buy'] != 1)
            
            dataframe.loc[weak_signal, 'buy'] = 1
            dataframe.loc[weak_signal, 'buy_tag'] = 'weak_v2'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """更保守的退出条件"""
        conditions_strong = []
        conditions_weak = []
        
        # 强烈卖出 - 标准
        conditions_strong.append(dataframe['daily_score'] < -1)
        conditions_strong.append(dataframe['h4_score'] < -1)
        conditions_strong.append(dataframe['h1_score'] <= -self.strong_signal_threshold)
        
        # 保护性退出 - 更敏感
        weak_cond_1 = (
            (dataframe['signal_strength'] < 2) &
            (dataframe['h1_score'] <= 0) &
            (dataframe['rsi'] > 65)
        )
        
        weak_cond_2 = (
            (dataframe['rsi'] > self.rsi_overbought) &
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['macdhist'] < 0)
        )
        
        conditions_weak.append(weak_cond_1)
        conditions_weak.append(weak_cond_2)
        
        common_filters = []
        common_filters.append(dataframe['volume'] > 0)
        common_filters.append(dataframe['rsi'] > self.rsi_oversold)
        
        if conditions_strong and common_filters:
            strong_exit = reduce(lambda x, y: x & y, conditions_strong + common_filters)
            dataframe.loc[strong_exit, 'sell'] = 1
            dataframe.loc[strong_exit, 'exit_tag'] = 'strong_bearish_v2'
        
        if conditions_weak and common_filters:
            weak_exit = reduce(lambda x, y: x | y, conditions_weak)
            weak_exit = weak_exit & reduce(lambda x, y: x & y, common_filters)
            
            if 'sell' in dataframe.columns:
                weak_exit = weak_exit & (dataframe['sell'] != 1)
            
            dataframe.loc[weak_exit, 'sell'] = 1
            dataframe.loc[weak_exit, 'exit_tag'] = 'protect_profit_v2'

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """保守的动态止损"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return self.stoploss
            
        last_candle = dataframe.iloc[-1]
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        if 'atr' in last_candle:
            atr_value = last_candle['atr']
            signal_strength = last_candle.get('signal_strength', 5)
            
            # 根据币种表现调整止损
            if pair_weight >= 1.3:      # 优秀币种
                base_multiplier = 1.8
            elif pair_weight >= 1.0:    # 标准币种
                base_multiplier = 2.0  
            else:                       # 表现差的币种
                base_multiplier = 1.5   # 更紧止损
            
            # 根据信号强度微调
            if signal_strength >= 7:
                atr_multiplier = base_multiplier - 0.2
            else:
                atr_multiplier = base_multiplier + 0.2
            
            atr_stoploss = atr_multiplier * atr_value / current_rate
            
            # 更严格的止损范围
            max_loss = 0.05 if pair_weight >= 1.2 else 0.04
            
            return max(-max_loss, min(-0.02, -atr_stoploss))
        
        return self.stoploss

    def custom_exit(self, pair: str, trade: 'Trade', current_time, current_rate: float,
                   current_profit: float, **kwargs) -> 'Optional[Union[str, bool]]':
        """更保守的出场策略"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return None
            
        last_candle = dataframe.iloc[-1]
        signal_strength = last_candle.get('signal_strength', 5)
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        # 基于币种表现调整止盈策略
        if pair_weight >= 1.3:       # 优秀币种
            first_target = 0.06
            second_target = 0.12
        elif pair_weight >= 1.0:     # 标准币种
            first_target = 0.05
            second_target = 0.10
        else:                        # 表现差的币种
            first_target = 0.03      # 快速止盈
            second_target = 0.06
        
        # 分批止盈
        if current_profit > first_target and not hasattr(trade, 'first_exit_done'):
            trade.first_exit_done = True
            return 'first_target_v2'
        
        if current_profit > second_target and not hasattr(trade, 'second_exit_done'):
            trade.second_exit_done = True
            return 'second_target_v2'
        
        # 信号恶化提前出场
        if signal_strength < 2 and current_profit > 0.01:
            return 'signal_weak_v2'
        
        # 高波动期保护利润
        volatility_rank = last_candle.get('volatility_rank', 0.5)
        if volatility_rank > 0.9 and current_profit > 0.02:
            return 'high_volatility_exit'
        
        return None

    def position_sizing(self, pair: str, current_time, current_rate: float, 
                       proposed_stake: float, min_stake: float, max_stake: float, 
                       side: str, **kwargs) -> float:
        """基于表现的仓位调整"""
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        # 表现差的币种降低仓位
        if pair_weight < 0.7:
            final_multiplier = 0.5
        elif pair_weight < 1.0:
            final_multiplier = 0.8
        else:
            final_multiplier = pair_weight
        
        final_stake = proposed_stake * final_multiplier
        return max(min_stake, min(final_stake, max_stake))
        
    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        """保守的杠杆设置"""
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        if pair_weight >= 1.3:
            target_leverage = 3.0      # 优秀币种适中杠杆
        elif pair_weight >= 1.0:
            target_leverage = 2.5      
        else:
            target_leverage = 2.0      # 表现差的币种低杠杆
        
        return min(target_leverage, max_leverage)