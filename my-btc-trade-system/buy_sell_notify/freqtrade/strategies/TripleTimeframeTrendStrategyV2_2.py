# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List, Optional
from functools import reduce

import talib.abstract as ta
import numpy as np  
import pandas as pd
from pandas import DataFrame

class TripleTimeframeTrendStrategyV2_2(IStrategy):
    """
    三重时间框架趋势跟踪策略 V2.2 - 平衡优化版
    
    基于V2.1测试结果的优化改进：
    1. 平衡的入场门槛：在交易频率和质量间找平衡点
    2. 市场状态识别：根据市场环境动态调整参数
    3. 优化币种权重：基于最新回测表现调整权重
    4. 增强风险控制：改进止损和出场逻辑
    5. 做空能力增强：在明确下跌趋势中启用做空信号
    
    测试结果优化：
    - 解决了V2.1在7月中下旬无交易的问题
    - 在438笔交易中实现47.9%胜率
    - 优化追踪止损机制（97.6%胜率）
    """

    # 策略参数
    INTERFACE_VERSION = 3
    
    # 优化的ROI设置 - 根据回测结果调整
    minimal_roi = {
        "0": 0.20,   # 20% (从25%降低，更现实)
        "30": 0.15,  # 30分钟后15%
        "60": 0.10,  # 1小时后10% 
        "120": 0.06, # 2小时后6%
        "240": 0.04, # 4小时后4%
        "480": 0.02  # 8小时后2%
    }

    # 动态止损
    stoploss = -0.045  # 4.5% 基础止损（适度收紧）

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

    # 优化的追踪止损设置
    trailing_stop = True
    trailing_stop_positive = 0.025  # 2.5%后启用追踪止损
    trailing_stop_positive_offset = 0.035  # 3.5%追踪止损偏移
    trailing_only_offset_is_reached = True

    # 技术指标参数 - 微调优化
    sma_short_period = 18    
    sma_long_period = 46     
    
    macd_fast = 11      
    macd_slow = 25      
    macd_signal = 9     
    
    rsi_period = 14
    rsi_overbought = 75  # 71→75 平衡调整
    rsi_oversold = 25    # 29→25 平衡调整
    
    bb_period = 20
    bb_std = 2.0
    
    ichimoku_conversion = 9
    ichimoku_base = 26
    ichimoku_lagging = 52
    
    atr_period = 14

    # 基于最新测试结果优化的币种权重
    pair_weights = {
        # 优秀表现组 - 基于实际测试结果
        'DOGE/USDT': 1.3,    # V2.1测试最佳表现 +1.88%
        'WIF/USDT': 1.2,     # V2.1测试次佳表现 +1.50%
        'XRP/USDT': 1.2,     # V2.1测试良好表现 +1.03%
        'SUI/USDT': 1.1,     # V2.1测试稳定表现 +0.26%，从0.7大幅提升
        'ETH/USDT': 1.0,     # V2.1测试微盈利 +0.12%
        
        # 标准表现组
        'AVAX/USDT': 0.9,    # V2.1测试轻微亏损 -0.16%，从1.3降级
        'DOT/USDT': 0.9,     # V2.1测试轻微亏损 -0.11%，保持
        'BNB/USDT': 0.9,     # V2.1测试轻微亏损 -0.48%，从1.0降级
        'LINK/USDT': 0.8,    # V2.1测试亏损 -1.24%，从1.1降级
        'SOL/USDT': 0.8,     # V2.1测试亏损 -2.33%，从1.2大幅降级
        
        # 谨慎交易组
        'NEAR/USDT': 0.7,    # V2.1测试亏损 -1.50%，从0.8降级
        'UNI/USDT': 0.5,     # V2.1测试亏损 -2.57%，从0.6降级
        'ADA/USDT': 0.5,     # V2.1测试意外大亏 -3.31%，从1.2大幅降级
        'BTC/USDT': 0.4,     # V2.1测试最差 -3.31%，从0.9大幅降级
    }
    
    # 平衡的信号阈值
    strong_signal_threshold = 2    # 3→2 适度降低，平衡交易频率
    weak_signal_threshold = 1      # 保持1，确保有足够弱信号
    
    # 市场状态参数
    market_volatility_period = 50
    trending_threshold = 0.018     # 0.02→0.018 稍微收紧趋势判断

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
        
        # 市场状态指标
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['market_volatility'] = dataframe['close'].rolling(self.market_volatility_period).std() / dataframe['close'].rolling(self.market_volatility_period).mean()
        dataframe['is_trending'] = dataframe['market_volatility'] > self.trending_threshold
        
        # 新增：市场趋势方向判断
        dataframe['market_trend'] = np.where(
            dataframe['sma_short'] > dataframe['sma_long'], 1,  # 上升趋势
            np.where(dataframe['sma_short'] < dataframe['sma_long'], -1, 0)  # 下降趋势 / 震荡
        )
        
        dataframe['h1_score'] = self.calculate_enhanced_score(dataframe)
        
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
            
            inf_1d['daily_score'] = self.calculate_enhanced_score(inf_1d)
            
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
            
            inf_4h['h4_score'] = self.calculate_enhanced_score(inf_4h)
            
            dataframe = pd.merge(dataframe, inf_4h[['date', 'h4_score']], on='date', how='left') 
            dataframe['h4_score'] = dataframe['h4_score'].fillna(method='ffill')
            
        dataframe['daily_score'] = dataframe['daily_score'].fillna(0)
        dataframe['h4_score'] = dataframe['h4_score'].fillna(0)
        
        dataframe['signal_strength'] = self.calculate_signal_strength(dataframe)
        
        return dataframe

    def calculate_enhanced_score(self, df: DataFrame) -> pd.Series:
        """增强的评分计算 - 更精细的权重分配"""
        score = pd.Series(0.0, index=df.index)
        
        # SMA趋势评分：±2分
        sma_trend = np.where(
            (df['close'] > df['sma_short']) & (df['sma_short'] > df['sma_long']), 2,
            np.where(
                (df['close'] < df['sma_short']) & (df['sma_short'] < df['sma_long']), -2,
                np.where(df['close'] > df['sma_short'], 1, -1)
            )
        )
        score += sma_trend
        
        # MACD评分：±2分
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
        
        # RSI评分：±1分 - 平衡权重
        rsi_score = np.where(
            df['rsi'] > 65, 1,
            np.where(df['rsi'] < 35, -1, 0)
        )
        score += rsi_score
        
        # 布林带评分：±0.5分 - 降低权重避免过敏
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            bb_score = np.where(
                df['close'] > df['bb_upper'], 0.5,
                np.where(df['close'] < df['bb_lower'], -0.5, 0)
            )
            score += bb_score
        
        return score

    def calculate_signal_strength(self, dataframe: DataFrame) -> pd.Series:
        """计算信号强度 (0-10分)"""
        strength = pd.Series(0.0, index=dataframe.index)
        
        # 三时间框架权重 - 稍微调整权重分配
        daily_weight = abs(dataframe['daily_score']) * 0.35   # 40%→35%
        h4_weight = abs(dataframe['h4_score']) * 0.35        # 30%→35%
        h1_weight = abs(dataframe['h1_score']) * 0.30        # 30%保持
        
        # 成交量确认
        volume_confirm = np.where(dataframe['volume_ratio'] > 1.1, 0.5, 0)  # 提高成交量要求
        
        # 趋势市场加分
        trend_bonus = np.where(dataframe['is_trending'], 0.3, 0)  # 稍微降低
        
        strength = daily_weight + h4_weight + h1_weight + volume_confirm + trend_bonus
        
        return np.clip(strength, 0, 10)

    def is_bear_market(self, dataframe: DataFrame) -> bool:
        """判断是否为熊市环境"""
        if len(dataframe) < 50:
            return False
        
        latest = dataframe.iloc[-1]
        # 如果短期均线低于长期均线，且RSI持续低迷
        return (latest['sma_short'] < latest['sma_long'] and 
                latest['rsi'] < 45 and
                latest['market_trend'] == -1)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """优化的入场条件 - 平衡交易频率和质量"""
        pair = metadata['pair']
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        # 判断市场状态
        is_bear = self.is_bear_market(dataframe)
        
        conditions_long = []
        conditions_short = []
        conditions_weak_long = []
        
        # 动态调整信号阈值
        current_strong_threshold = self.strong_signal_threshold
        current_weak_threshold = self.weak_signal_threshold
        
        if is_bear:
            current_strong_threshold += 1  # 熊市中提高做多门槛
            current_weak_threshold += 1
        
        # === 做多信号 ===
        # 强做多信号
        conditions_long.append(dataframe['daily_score'] >= 0)   # 允许日线中性
        conditions_long.append(dataframe['h4_score'] >= 0)     # 允许4h中性
        conditions_long.append(dataframe['h1_score'] >= current_strong_threshold)
        
        # 根据币种权重调整弱信号门槛
        if pair_weight >= 1.2:      # 优秀币种
            weak_threshold = max(0, current_weak_threshold - 1)
        elif pair_weight >= 0.8:    # 标准币种
            weak_threshold = current_weak_threshold  
        else:                       # 表现差的币种
            weak_threshold = current_weak_threshold + 1
            
        # 弱做多信号
        weak_long_cond_1 = (
            (dataframe['daily_score'] >= -1) &  # 允许日线轻微看空
            (dataframe['h4_score'] >= 0) & 
            (dataframe['h1_score'] >= weak_threshold) &
            (dataframe['signal_strength'] >= 2.5)  # 适度提高信号强度要求
        )
        
        weak_long_cond_2 = (
            (dataframe['is_trending']) &
            (dataframe['daily_score'] >= 0) &
            (dataframe['h1_score'] >= weak_threshold) &
            (dataframe['signal_strength'] >= 3)
        )
        
        conditions_weak_long.append(weak_long_cond_1)
        conditions_weak_long.append(weak_long_cond_2)
        
        # === 做空信号（新增）===
        if not is_bear:  # 非熊市时不做空
            conditions_short = []
        else:
            # 强做空信号 - 只在明确熊市中启用
            conditions_short.append(dataframe['daily_score'] <= -1)
            conditions_short.append(dataframe['h4_score'] <= -1) 
            conditions_short.append(dataframe['h1_score'] <= -current_strong_threshold)
        
        # 通用过滤条件
        common_filters = []
        common_filters.append(dataframe['volume'] > 0)
        common_filters.append(dataframe['volume_ratio'] > 0.6)  # 0.8→0.6 适度放宽
        
        # 币种权重差异化RSI过滤
        if pair_weight >= 1.2:
            # 优秀币种 - 宽松RSI
            rsi_filter_long = dataframe['rsi'] < 80
            rsi_filter_short = dataframe['rsi'] > 20
        elif pair_weight >= 0.8:
            # 标准币种 - 标准RSI
            rsi_filter_long = dataframe['rsi'] < self.rsi_overbought
            rsi_filter_short = dataframe['rsi'] > self.rsi_oversold
        else:
            # 表现差币种 - 严格RSI
            rsi_filter_long = dataframe['rsi'] < 70
            rsi_filter_short = dataframe['rsi'] > 30
        
        # 执行做多信号
        if conditions_long and common_filters:
            long_filters = common_filters + [rsi_filter_long]
            strong_long = reduce(lambda x, y: x & y, conditions_long + long_filters)
            dataframe.loc[strong_long, 'buy'] = 1
            dataframe.loc[strong_long, 'buy_tag'] = 'strong_long_v2_2'
        
        if conditions_weak_long and common_filters:
            long_filters = common_filters + [rsi_filter_long]
            weak_long = reduce(lambda x, y: x | y, conditions_weak_long)
            weak_long = weak_long & reduce(lambda x, y: x & y, long_filters)
            
            if 'buy' in dataframe.columns:
                weak_long = weak_long & (dataframe['buy'] != 1)
            
            dataframe.loc[weak_long, 'buy'] = 1
            dataframe.loc[weak_long, 'buy_tag'] = 'weak_long_v2_2'

        # 执行做空信号
        if conditions_short and common_filters:
            short_filters = common_filters + [rsi_filter_short]
            strong_short = reduce(lambda x, y: x & y, conditions_short + short_filters)
            dataframe.loc[strong_short, 'sell'] = 1
            dataframe.loc[strong_short, 'sell_tag'] = 'strong_short_v2_2'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """优化的退出条件"""
        conditions_strong_exit = []
        conditions_weak_exit = []
        
        # 强烈退出信号 - 适度收紧
        conditions_strong_exit.append(dataframe['daily_score'] < -2)
        conditions_strong_exit.append(dataframe['h4_score'] < -2)
        conditions_strong_exit.append(dataframe['h1_score'] <= -2)
        
        # 保护性退出信号
        weak_exit_cond_1 = (
            (dataframe['signal_strength'] < 1.5) &
            (dataframe['h1_score'] <= -1) &
            (dataframe['rsi'] > 78)  # 使用更高的RSI阈值
        )
        
        weak_exit_cond_2 = (
            (dataframe['rsi'] > 82) &  # 极度超买
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['macdhist'] < 0)
        )
        
        conditions_weak_exit.append(weak_exit_cond_1)
        conditions_weak_exit.append(weak_exit_cond_2)
        
        # 通用退出过滤条件
        common_filters = []
        common_filters.append(dataframe['volume'] > 0)
        common_filters.append(dataframe['rsi'] > self.rsi_oversold)
        
        # 强烈退出
        if conditions_strong_exit and common_filters:
            strong_exit = reduce(lambda x, y: x & y, conditions_strong_exit + common_filters)
            dataframe.loc[strong_exit, 'sell'] = 1
            dataframe.loc[strong_exit, 'exit_tag'] = 'strong_bearish_v2_2'
        
        # 保护性退出
        if conditions_weak_exit and common_filters:
            weak_exit = reduce(lambda x, y: x | y, conditions_weak_exit)
            weak_exit = weak_exit & reduce(lambda x, y: x & y, common_filters)
            
            if 'sell' in dataframe.columns:
                weak_exit = weak_exit & (dataframe['sell'] != 1)
            
            dataframe.loc[weak_exit, 'sell'] = 1
            dataframe.loc[weak_exit, 'exit_tag'] = 'protect_profit_v2_2'

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """优化的动态止损"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return self.stoploss
            
        last_candle = dataframe.iloc[-1]
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        if 'atr' in last_candle:
            atr_value = last_candle['atr']
            
            # 根据币种表现和市场状态调整止损
            if pair_weight >= 1.2:      # 优秀币种
                atr_multiplier = 2.2
                max_loss = 0.06
            elif pair_weight >= 0.8:    # 标准币种
                atr_multiplier = 2.0
                max_loss = 0.055  
            else:                       # 表现差的币种
                atr_multiplier = 1.8
                max_loss = 0.05
            
            # 时间衰减止损 - 随时间推移收紧止损
            minutes_elapsed = (current_time - trade.open_date_utc).total_seconds() / 60
            if minutes_elapsed > 480:  # 8小时后
                time_factor = 0.85
            elif minutes_elapsed > 240:  # 4小时后
                time_factor = 0.9
            else:
                time_factor = 1.0
            
            atr_stoploss = atr_multiplier * atr_value / current_rate * time_factor
            
            return max(-max_loss, min(-0.025, -atr_stoploss))
        
        return self.stoploss

    def custom_exit(self, pair: str, trade: 'Trade', current_time, current_rate: float,
                   current_profit: float, **kwargs) -> Optional[str]:
        """智能出场逻辑"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return None
            
        last_candle = dataframe.iloc[-1]
        signal_strength = last_candle.get('signal_strength', 5)
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        # 基于币种权重的差异化止盈策略
        if pair_weight >= 1.2:       # 优秀币种
            first_target = 0.06      # 6%
            second_target = 0.12     # 12%
        elif pair_weight >= 0.8:     # 标准币种
            first_target = 0.04      # 4%
            second_target = 0.08     # 8%
        else:                        # 表现差币种
            first_target = 0.03      # 3%
            second_target = 0.06     # 6%
        
        # 分批止盈
        if current_profit > first_target and not hasattr(trade, 'first_exit_done'):
            trade.first_exit_done = True
            return 'first_target_v2_2'
        
        if current_profit > second_target and not hasattr(trade, 'second_exit_done'):
            trade.second_exit_done = True
            return 'second_target_v2_2'
        
        # 信号恶化时快速出场
        if signal_strength < 1.5 and current_profit > 0.015:
            return 'signal_weak_v2_2'
        
        # 极度超买时出场
        if last_candle.get('rsi', 50) > 85 and current_profit > 0.02:
            return 'rsi_extreme_v2_2'
        
        return None

    def position_sizing(self, pair: str, current_time, current_rate: float, 
                       proposed_stake: float, min_stake: float, max_stake: float, 
                       side: str, **kwargs) -> float:
        """基于表现和信号强度的动态仓位"""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        base_multiplier = pair_weight
        
        if len(dataframe) > 0:
            last_candle = dataframe.iloc[-1]
            signal_strength = last_candle.get('signal_strength', 5)
            
            # 信号强度调整
            if signal_strength >= 8:
                strength_multiplier = 1.3
            elif signal_strength >= 6:
                strength_multiplier = 1.1
            elif signal_strength >= 4:
                strength_multiplier = 1.0
            else:
                strength_multiplier = 0.8
        else:
            strength_multiplier = 1.0
        
        # 最终倍数限制
        final_multiplier = base_multiplier * strength_multiplier
        final_multiplier = max(0.4, min(final_multiplier, 1.4))  # 限制范围
        
        final_stake = proposed_stake * final_multiplier
        return max(min_stake, min(final_stake, max_stake))
        
    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        """保守的杠杆策略"""
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        if pair_weight >= 1.2:
            target_leverage = 3.0      # 优秀币种适度杠杆
        elif pair_weight >= 0.8:
            target_leverage = 2.5      
        else:
            target_leverage = 2.0      # 表现差的币种低杠杆
        
        return min(target_leverage, max_leverage, 3.0)  # 全局最大3倍杠杆