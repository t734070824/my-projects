# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List, Optional
from functools import reduce

import talib.abstract as ta
import numpy as np  
import pandas as pd
from pandas import DataFrame

class TripleTimeframeTrendStrategyOptimized(IStrategy):
    """
    三重时间框架趋势跟踪策略 - 优化版本
    
    优化重点:
    1. 提高交易频率: 放宽部分过滤条件，增加弱信号交易
    2. 动态仓位: 根据信号强度调整仓位大小  
    3. 智能止盈: 分批止盈+动态追踪
    4. 币种权重: 基于历史表现动态调整
    5. 市场状态识别: 趋势/震荡市场自适应
    """

    # 策略参数
    INTERFACE_VERSION = 3
    
    # 优化的ROI设置 - 分批止盈
    minimal_roi = {
        "0": 0.25,   # 25% 全部平仓
        "30": 0.18,  # 30分钟后18%
        "60": 0.12,  # 1小时后12% 
        "120": 0.08, # 2小时后8%
        "240": 0.05, # 4小时后5%
        "480": 0.03  # 8小时后3%
    }

    # 动态止损
    stoploss = -0.04  # 4% 基础止损

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
    trailing_stop_positive = 0.015  # 1.5%后启用追踪止损 (更积极)
    trailing_stop_positive_offset = 0.04   # 追踪止损偏移4%
    trailing_only_offset_is_reached = True

    # 优化的策略参数
    # SMA 参数 - 稍微调整提高敏感度
    sma_short_period = 18  # 20→18 更敏感
    sma_long_period = 45   # 50→45 更敏感
    
    # MACD 参数 - 优化响应速度
    macd_fast = 11    # 12→11
    macd_slow = 24    # 26→24
    macd_signal = 8   # 9→8
    
    # RSI 参数 - 调整阈值增加交易机会
    rsi_period = 14
    rsi_overbought = 72  # 70→72 (减少过早退出)
    rsi_oversold = 28    # 30→28 (减少过早退出)
    
    # 布林带参数
    bb_period = 20
    bb_std = 2.0
    
    # 一目均衡表参数
    ichimoku_conversion = 9
    ichimoku_base = 26
    ichimoku_lagging = 52
    
    # ATR参数
    atr_period = 14

    # 新增: 币种权重 (基于历史表现和市值)
    pair_weights = {
        'XRP/USDT': 1.3,     # 表现最好 52.33%
        'SOL/USDT': 1.2,     # 高波动高收益
        'ETH/USDT': 1.1,     # 主流稳定
        'BTC/USDT': 1.0,     # 基准
        'ADA/USDT': 1.0,     # 大市值稳定币
        'AVAX/USDT': 1.1,    # 新兴公链
        'DOT/USDT': 0.9,     # 中等表现
        'DOGE/USDT': 1.1,    # 高波动meme币
        'SUI/USDT': 1.2,     # 新兴高潜力
        'LINK/USDT': 1.0,    # DeFi蓝筹
        'NEAR/USDT': 1.0,    # 公链项目
        'UNI/USDT': 1.0,     # DEX龙头
        'WIF/USDT': 0.8,     # 高风险meme币
        'BNB/USDT': 0.8,     # 表现相对较弱
    }
    
    # 新增: 信号强度阈值 (允许更多交易)
    strong_signal_threshold = 3    # 强信号阈值 (原来是2)
    weak_signal_threshold = 1      # 弱信号阈值 (新增)
    
    # 新增: 市场状态参数
    market_volatility_period = 50   # 计算市场波动率的周期
    trending_threshold = 0.02       # 趋势市场阈值

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
        计算所有技术指标 - 优化版本
        """
        # 获取额外时间框架的数据
        inf_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1d')
        inf_4h = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='4h')
        
        # === 1小时指标计算 (执行层面) ===
        
        # 优化的SMA
        dataframe['sma_short'] = ta.SMA(dataframe, timeperiod=self.sma_short_period)
        dataframe['sma_long'] = ta.SMA(dataframe, timeperiod=self.sma_long_period)
        
        # 优化的MACD
        macd = ta.MACD(dataframe, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal'] 
        dataframe['macdhist'] = macd['macdhist']
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        
        # 布林带
        bollinger = ta.BBANDS(dataframe, timeperiod=self.bb_period, nbdevup=float(self.bb_std), nbdevdn=float(self.bb_std))
        dataframe['bb_lower'] = bollinger['lowerband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])
        
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
        
        # 新增: 市场状态指标
        dataframe['market_volatility'] = dataframe['close'].rolling(self.market_volatility_period).std() / dataframe['close'].rolling(self.market_volatility_period).mean()
        dataframe['is_trending'] = dataframe['market_volatility'] > self.trending_threshold
        
        # 新增: 成交量指标
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # 新增: 动量指标
        dataframe['momentum'] = ta.MOM(dataframe, timeperiod=10)
        dataframe['roc'] = ta.ROC(dataframe, timeperiod=10)
        
        # === 计算1小时优化评分 ===
        dataframe['h1_score'] = self.calculate_optimized_score(dataframe)
        
        # === 处理日线数据 (战略层面) ===
        if len(inf_1d) > 0:
            # 计算日线指标
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
            
            # 计算日线评分
            inf_1d['daily_score'] = self.calculate_optimized_score(inf_1d)
            
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
            inf_4h['macdhist'] = macd_4h['macdhist']
            
            bollinger_4h = ta.BBANDS(inf_4h, timeperiod=self.bb_period, nbdevup=float(self.bb_std), nbdevdn=float(self.bb_std))
            inf_4h['bb_lower'] = bollinger_4h['lowerband']
            inf_4h['bb_middle'] = bollinger_4h['middleband']
            inf_4h['bb_upper'] = bollinger_4h['upperband']
            
            # 计算4小时评分
            inf_4h['h4_score'] = self.calculate_optimized_score(inf_4h)
            
            # 合并到主数据框
            dataframe = pd.merge(dataframe, inf_4h[['date', 'h4_score']], on='date', how='left') 
            dataframe['h4_score'] = dataframe['h4_score'].fillna(method='ffill')
            
        # 填充缺失值
        dataframe['daily_score'] = dataframe['daily_score'].fillna(0)
        dataframe['h4_score'] = dataframe['h4_score'].fillna(0)
        
        # 新增: 综合信号强度
        dataframe['signal_strength'] = self.calculate_signal_strength(dataframe)
        
        return dataframe

    def calculate_optimized_score(self, df: DataFrame) -> pd.Series:
        """
        优化的综合评分计算 - 加权更合理，更敏感
        """
        score = pd.Series(0.0, index=df.index)
        
        # SMA 趋势评分 (+3/-3) - 加权提高
        sma_trend = np.where(
            (df['close'] > df['sma_short']) & (df['sma_short'] > df['sma_long']), 3,
            np.where(
                (df['close'] < df['sma_short']) & (df['sma_short'] < df['sma_long']), -3,
                np.where(df['close'] > df['sma_short'], 1, -1)  # 至少要突破短期均线
            )
        )
        score += sma_trend
        
        # MACD 评分 (+2/-2) - 加权提高
        if 'macdhist' in df.columns:
            macd_score = np.where(
                (df['macd'] > df['macdsignal']) & (df['macdhist'] > 0), 2,
                np.where(
                    (df['macd'] < df['macdsignal']) & (df['macdhist'] < 0), -2,
                    np.where(df['macd'] > df['macdsignal'], 1, -1)
                )
            )
        else:
            # 如果没有macdhist列，只用macd和signal线比较
            macd_score = np.where(df['macd'] > df['macdsignal'], 1, -1)
        score += macd_score
        
        # RSI 评分 - 优化阈值
        rsi_score = np.where(
            df['rsi'] > 60, 1,
            np.where(df['rsi'] < 40, -1, 0)
        )
        score += rsi_score
        
        # 布林带评分 - 新增位置判断
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            bb_score = np.where(
                df['close'] > df['bb_upper'], 1,
                np.where(df['close'] < df['bb_lower'], -1, 0)
            )
            score += bb_score
        
        # 新增: 动量评分
        if 'momentum' in df.columns:
            momentum_score = np.where(df['momentum'] > 0, 1, -1)
            score += momentum_score * 0.5  # 权重0.5
        
        return score

    def calculate_signal_strength(self, dataframe: DataFrame) -> pd.Series:
        """
        计算综合信号强度 (0-10分)
        """
        strength = pd.Series(0.0, index=dataframe.index)
        
        # 基础分数来自三个时间框架
        daily_weight = abs(dataframe['daily_score']) * 0.4
        h4_weight = abs(dataframe['h4_score']) * 0.3  
        h1_weight = abs(dataframe['h1_score']) * 0.2
        
        # 成交量确认
        volume_confirm = np.where(dataframe['volume_ratio'] > 1.2, 0.5, 0)
        
        # 趋势市场加分
        trend_bonus = np.where(dataframe['is_trending'], 0.5, 0)
        
        strength = daily_weight + h4_weight + h1_weight + volume_confirm + trend_bonus
        
        # 标准化到0-10
        strength = np.clip(strength, 0, 10)
        
        return strength

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

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        优化的买入信号：分级信号系统
        """
        pair = metadata['pair']
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        conditions_strong = []  # 强信号条件
        conditions_weak = []    # 弱信号条件
        
        # === 强信号条件 (原逻辑) ===
        conditions_strong.append(dataframe['daily_score'] > 0)
        conditions_strong.append(dataframe['h4_score'] > 0)
        conditions_strong.append(dataframe['h1_score'] >= self.strong_signal_threshold)
        
        # === 新增弱信号条件 (增加交易频率) ===
        # 弱信号1: 日线+4h看多，1h中性偏多
        weak_cond_1 = (
            (dataframe['daily_score'] > 1) & 
            (dataframe['h4_score'] > 1) & 
            (dataframe['h1_score'] >= self.weak_signal_threshold)
        )
        
        # 弱信号2: 强趋势市场中的较弱信号
        weak_cond_2 = (
            (dataframe['is_trending']) &
            (dataframe['signal_strength'] >= 5) &
            (dataframe['daily_score'] > 0) &
            (dataframe['h1_score'] >= 0)
        )
        
        conditions_weak.append(weak_cond_1)
        conditions_weak.append(weak_cond_2)
        
        # === 通用过滤条件 ===
        common_filters = []
        common_filters.append(dataframe['volume'] > 0)
        common_filters.append(dataframe['rsi'] < self.rsi_overbought)
        common_filters.append(dataframe['volume_ratio'] > 0.8)  # 成交量不能太低
        
        # 币种权重过滤 (表现好的币种要求更宽松)
        if pair_weight > 1.0:
            common_filters.append(dataframe['rsi'] < 75)  # 放宽RSI要求
        else:
            common_filters.append(dataframe['rsi'] < 70)  # 收紧RSI要求
        
        # === 组合信号 ===
        # 强信号
        if conditions_strong and common_filters:
            strong_signal = reduce(lambda x, y: x & y, conditions_strong + common_filters)
            dataframe.loc[strong_signal, 'buy'] = 1
            dataframe.loc[strong_signal, 'buy_tag'] = 'strong_trend'
        
        # 弱信号 (仅在没有强信号时)
        if conditions_weak and common_filters:
            weak_signal = reduce(lambda x, y: x | y, conditions_weak)
            weak_signal = weak_signal & reduce(lambda x, y: x & y, common_filters)
            
            # 避免与强信号重复
            if 'buy' in dataframe.columns:
                weak_signal = weak_signal & (dataframe['buy'] != 1)
            
            dataframe.loc[weak_signal, 'buy'] = 1
            dataframe.loc[weak_signal, 'buy_tag'] = 'weak_trend'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict) -> DataFrame:
        """
        优化的卖出信号：更智能的退出
        """
        conditions_strong = []  # 强烈卖出
        conditions_weak = []    # 温和卖出
        
        # === 强烈卖出条件 ===
        conditions_strong.append(dataframe['daily_score'] < -1)
        conditions_strong.append(dataframe['h4_score'] < -1)
        conditions_strong.append(dataframe['h1_score'] <= -self.strong_signal_threshold)
        
        # === 温和卖出条件 (保护利润) ===
        # 条件1: 信号强度大幅下降
        weak_cond_1 = (
            (dataframe['signal_strength'] < 3) &
            (dataframe['h1_score'] < 0) &
            (dataframe['rsi'] > 60)
        )
        
        # 条件2: 技术指标背离
        weak_cond_2 = (
            (dataframe['rsi'] > self.rsi_overbought) &
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['macdhist'] < 0)
        )
        
        conditions_weak.append(weak_cond_1)
        conditions_weak.append(weak_cond_2)
        
        # === 通用过滤条件 ===
        common_filters = []
        common_filters.append(dataframe['volume'] > 0)
        common_filters.append(dataframe['rsi'] > self.rsi_oversold)
        
        # === 组合信号 ===
        # 强烈卖出
        if conditions_strong and common_filters:
            strong_exit = reduce(lambda x, y: x & y, conditions_strong + common_filters)
            dataframe.loc[strong_exit, 'sell'] = 1
            dataframe.loc[strong_exit, 'exit_tag'] = 'strong_bearish'
        
        # 温和卖出
        if conditions_weak and common_filters:
            weak_exit = reduce(lambda x, y: x | y, conditions_weak)
            weak_exit = weak_exit & reduce(lambda x, y: x & y, common_filters)
            
            if 'sell' in dataframe.columns:
                weak_exit = weak_exit & (dataframe['sell'] != 1)
            
            dataframe.loc[weak_exit, 'sell'] = 1
            dataframe.loc[weak_exit, 'exit_tag'] = 'weak_bearish'

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        动态止损 - 基于ATR和信号强度
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return self.stoploss
            
        last_candle = dataframe.iloc[-1]
        
        if 'atr' in last_candle and 'signal_strength' in last_candle:
            atr_value = last_candle['atr']
            signal_strength = last_candle['signal_strength']
            
            # 根据信号强度调整ATR倍数
            if signal_strength >= 7:
                atr_multiplier = 1.8  # 强信号用较紧止损
            elif signal_strength >= 5:
                atr_multiplier = 2.0  # 中等信号标准止损  
            else:
                atr_multiplier = 2.5  # 弱信号用较宽止损
            
            atr_stoploss = atr_multiplier * atr_value / current_rate
            
            # 根据币种权重调整
            pair_weight = self.pair_weights.get(pair, 1.0)
            if pair_weight > 1.1:  # 表现好的币种
                max_loss = 0.06    # 最大6%止损
            else:
                max_loss = 0.05    # 最大5%止损
            
            return max(-max_loss, min(-0.02, -atr_stoploss))
        
        return self.stoploss

    def custom_exit(self, pair: str, trade: 'Trade', current_time, current_rate: float,
                   current_profit: float, **kwargs) -> 'Optional[Union[str, bool]]':
        """
        智能出场逻辑 - 分批止盈
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return None
            
        last_candle = dataframe.iloc[-1]
        signal_strength = last_candle.get('signal_strength', 5)
        
        # 动态止盈阈值
        if signal_strength >= 7:
            first_target = 0.08   # 8%
            second_target = 0.15  # 15%
        else:
            first_target = 0.06   # 6%
            second_target = 0.12  # 12%
        
        # 第一次止盈 (25%仓位)
        if current_profit > first_target and not hasattr(trade, 'first_exit_done'):
            trade.first_exit_done = True
            return 'first_target_reached'
        
        # 第二次止盈 (50%仓位) 
        if current_profit > second_target and not hasattr(trade, 'second_exit_done'):
            trade.second_exit_done = True
            return 'second_target_reached'
        
        # 信号恶化时提前出场
        if signal_strength < 3 and current_profit > 0.02:
            return 'signal_weakening'
        
        # RSI过度超买时出场
        if last_candle.get('rsi', 50) > 78 and current_profit > 0.03:
            return 'rsi_overbought_exit'
        
        return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time, entry_tag: 'Optional[str]', 
                           side: str, **kwargs) -> bool:
        """
        交易确认 - 最后的安全检查
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return False
            
        last_candle = dataframe.iloc[-1]
        
        # 确保信号仍然有效
        if side == 'long':
            return (last_candle.get('signal_strength', 0) >= 3 and 
                   last_candle.get('daily_score', 0) >= 0)
        else:
            return (last_candle.get('signal_strength', 0) >= 3 and 
                   last_candle.get('daily_score', 0) <= 0)

    def position_sizing(self, pair: str, current_time, current_rate: float, 
                       proposed_stake: float, min_stake: float, max_stake: float, 
                       side: str, **kwargs) -> float:
        """
        动态仓位管理 - 基于信号强度和币种权重
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return proposed_stake
            
        last_candle = dataframe.iloc[-1]
        signal_strength = last_candle.get('signal_strength', 5)
        pair_weight = self.pair_weights.get(pair, 1.0)
        
        # 基础仓位调整
        if signal_strength >= 8:
            size_multiplier = 1.5      # 超强信号增加仓位50%
        elif signal_strength >= 6:
            size_multiplier = 1.2      # 强信号增加仓位20%
        elif signal_strength >= 4:
            size_multiplier = 1.0      # 中等信号标准仓位
        else:
            size_multiplier = 0.7      # 弱信号减少仓位30%
        
        # 币种权重调整
        final_multiplier = size_multiplier * pair_weight
        
        # 计算最终仓位
        final_stake = proposed_stake * final_multiplier
        
        # 确保在允许范围内
        return max(min_stake, min(final_stake, max_stake))

    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, side: str,
                 **kwargs) -> float:
        """
        动态杠杆 - 基于信号强度
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 1:
            return min(proposed_leverage, 3.0)  # 默认最大3倍
            
        last_candle = dataframe.iloc[-1]
        signal_strength = last_candle.get('signal_strength', 5)
        
        # 根据信号强度调整杠杆
        if signal_strength >= 8:
            target_leverage = 5.0      # 超强信号最高杠杆
        elif signal_strength >= 6:
            target_leverage = 4.0      # 强信号高杠杆
        elif signal_strength >= 4:
            target_leverage = 3.0      # 中等信号中等杠杆
        else:
            target_leverage = 2.0      # 弱信号低杠杆
        
        return min(target_leverage, max_leverage)