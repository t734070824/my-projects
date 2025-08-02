
import ccxt
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, List

class SignalGenerator:
    """
    一个多维度、基于评分的交易信号生成器。

    它综合了趋势、动量、波动性和成交量等多个维度来评估市场状态，
    并为自动化交易系统提供清晰、结构化的信号。
    """

    def __init__(self, symbol: str, timeframe: str = '4h'):
        """
        初始化信号生成器。

        Args:
            symbol (str): 交易对，例如 'BTC/USDT'。
            timeframe (str): K线的时间周期，例如 '1h', '4h', '1d'。
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = ccxt.binance({
            'options': {
                'defaultType': 'future'  # 确保我们获取的是U本位合约数据
            }
        })
        # 获取足够的数据以计算最长的指标 (MA200)
        self.history_limit = 400

    def _fetch_data(self) -> pd.DataFrame:
        """
        从币安获取OHLCV数据。

        Returns:
            pd.DataFrame: 包含OHLCV数据的Pandas DataFrame，如果获取失败则返回空DataFrame。
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.history_limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"数据获取失败: {e}")
            return pd.DataFrame()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有必要的技术指标。

        Args:
            df (pd.DataFrame): 包含OHLCV数据的DataFrame。

        Returns:
            pd.DataFrame: 附加了技术指标列的DataFrame。
        """
        # 使用 pandas-ta 扩展来计算指标，代码更简洁
        # ta.strategy() 可以一次性计算多个指标
        df.ta.strategy(ta.Strategy(
            name="Comprehensive_Strategy",
            ta=[
                # 趋势指标
                {"kind": "sma", "length": 20},
                {"kind": "sma", "length": 50},
                {"kind": "sma", "length": 200},
                {"kind": "macd"},
                # 动量指标
                {"kind": "rsi"},
                # 波动性指标
                {"kind": "bbands"},
                # 成交量指标
                {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOL"}
            ]
        ))
        return df

    def _apply_scoring_logic(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        应用多维度评分逻辑，生成最终信号。

        Args:
            df (pd.DataFrame): 包含了指标的DataFrame。

        Returns:
            Dict[str, Any]: 包含分数、信号和分析原因的字典。
        """
        # 我们只关心最新的、已完成的K线数据
        latest = df.iloc[-2]

        scores = {
            'trend': 0,
            'momentum': 0,
            'volatility': 0,
            'volume': 0
        }
        reasons = []

        # --- 1. 趋势判断 (Trend Analysis) ---
        # 长期趋势 (MA200 vs MA50)
        if latest['SMA_50'] > latest['SMA_200']:
            scores['trend'] += 2
            reasons.append("[趋势: 看多] 黄金交叉形态 (MA50 > MA200)")
        elif latest['SMA_50'] < latest['SMA_200']:
            scores['trend'] -= 2
            reasons.append("[趋势: 看空] 死亡交叉形态 (MA50 < MA200)")

        # 中短期趋势 (价格 vs MA20)
        if latest['close'] > latest['SMA_20']:
            scores['trend'] += 1
            reasons.append("[趋势: 看多] 价格位于MA20之上")
        else:
            scores['trend'] -= 1
            reasons.append("[趋势: 看空] 价格位于MA20之下")
        
        # MACD
        if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] and latest['MACD_12_26_9'] > 0:
            scores['trend'] += 1
            reasons.append("[趋势: 看多] MACD在零轴上方金叉")
        elif latest['MACD_12_26_9'] < latest['MACDs_12_26_9'] and latest['MACD_12_26_9'] < 0:
            scores['trend'] -= 1
            reasons.append("[趋势: 看空] MACD在零轴下方死叉")

        # --- 2. 动量与强度 (Momentum & Strength) ---
        rsi = latest['RSI_14']
        if rsi > 60:
            scores['momentum'] += 1
            reasons.append(f"[动量: 看多] RSI ({rsi:.2f}) 处于强势区")
        elif rsi < 40:
            scores['momentum'] -= 1
            reasons.append(f"[动量: 看空] RSI ({rsi:.2f}) 处于弱势区")
        else:
            reasons.append(f"[动量: 中性] RSI ({rsi:.2f}) 处于观望区")

        # --- 3. 波动性 (Volatility) ---
        # 价格沿布林带上轨运行
        if latest['close'] > latest['BBU_20_2.0']:
            scores['volatility'] += 1
            reasons.append("[波动性: 看多] 价格突破布林带上轨，趋势强劲")
        # 价格沿布林带下轨运行
        elif latest['close'] < latest['BBL_20_2.0']:
            scores['volatility'] -= 1
            reasons.append("[波动性: 看空] 价格跌破布林带下轨，趋势强劲")

        # --- 4. 成交量确认 (Volume Confirmation) ---
        # 比较当前成交量和20周期成交量均线
        if latest['volume'] > latest['VOL_SMA_20']:
            # 价涨量增
            if latest['close'] > latest['open']:
                scores['volume'] += 1
                reasons.append("[成交量: 看多] 放量上涨，趋势健康")
            # 价跌量增
            else:
                scores['volume'] -= 1
                reasons.append("[成交量: 看空] 放量下跌，恐慌加剧")
        else:
            # 缩量
            reasons.append("[成交量: 中性] 缩量整理，等待方向")

        # --- 综合评分 ---
        total_score = sum(scores.values())
        
        signal = "NEUTRAL"
        if total_score >= 3:
            signal = "STRONG_BUY"
        elif total_score > 0:
            signal = "WEAK_BUY"
        elif total_score <= -3:
            signal = "STRONG_SELL"
        elif total_score < 0:
            signal = "WEAK_SELL"

        return {
            "timestamp": latest['timestamp'],
            "total_score": total_score,
            "signal": signal,
            "scores_breakdown": scores,
            "reasons": reasons
        }

    def generate_signal(self) -> Dict[str, Any]:
        """
        执行完整流程：获取数据 -> 计算指标 -> 生成信号。

        Returns:
            Dict[str, Any]: 包含最终信号和分析详情的字典。
        """
        df = self._fetch_data()
        if df.empty:
            return {"error": "无法获取K线数据"}

        df_with_indicators = self._calculate_indicators(df)
        
        final_signal = self._apply_scoring_logic(df_with_indicators)
        
        return final_signal

# --- 使用示例：多时间周期分析框架 ---
if __name__ == '__main__':
    import json

    # 交易对
    SYMBOL = 'BTC/USDT'

    # 1. 战略层面：使用日线图 (1d) 判断牛熊大环境
    print("--- 1. 分析战略层面 (日线图) ---")
    daily_signal_gen = SignalGenerator(symbol=SYMBOL, timeframe='1d')
    daily_analysis = daily_signal_gen.generate_signal()
    print(json.dumps(daily_analysis, indent=4, default=str))

    # 从日线分析中提取长期趋势判断
    # 我们定义总分大于0为长期看多，否则为长期看空或震荡
    is_long_term_bullish = daily_analysis.get('total_score', 0) > 0
    long_term_direction = "看多" if is_long_term_bullish else "看空/震荡"
    print(f"\n长期趋势判断: {long_term_direction}\n")

    # 2. 战术层面：使用4小时图 (4h) 寻找具体的交易机会
    print("--- 2. 分析战术层面 (4小时图) ---")
    h4_signal_gen = SignalGenerator(symbol=SYMBOL, timeframe='4h')
    h4_analysis = h4_signal_gen.generate_signal()
    print(json.dumps(h4_analysis, indent=4, default=str))

    # 从4小时分析中提取短期交易信号
    trade_signal = h4_analysis.get('signal', 'NEUTRAL')

    # 3. 决策逻辑：只有当长短期方向一致时，才产生最终交易决策
    print("\n--- 3. 最终决策 ---")
    final_decision = "HOLD"  # 默认决策为持有/观望

    if is_long_term_bullish and trade_signal in ['STRONG_BUY', 'WEAK_BUY']:
        final_decision = "EXECUTE_LONG"
        print(f"决策: {final_decision}")
        print("原因: 长期趋势看多，且短期出现买入信号。准备执行做多策略。\n")
    
    elif not is_long_term_bullish and trade_signal in ['STRONG_SELL', 'WEAK_SELL']:
        final_decision = "EXECUTE_SHORT"
        print(f"决策: {final_decision}")
        print("原因: 长期趋势看空/震荡，且短期出现卖出信号。准备执行做空策略。\n")
        
    else:
        print(f"决策: {final_decision}")
        print(f"原因: 长短期方向冲突或信号不明。长期方向: {long_term_direction}, 短期信号: {trade_signal}。建议观望。\n")

    # 在真实的自动化交易系统中，这里的 print 语句将被替换为
    # 调用风险管理、仓位计算和订单执行的模块。
    #
    # 例如:
    # if final_decision == "EXECUTE_LONG":
    #     risk_manager.calculate_position_size(...)
    #     order_executor.place_long_order(...)
    # elif final_decision == "EXECUTE_SHORT":
    #     ...


