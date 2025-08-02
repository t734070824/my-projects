
import ccxt
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, List, Optional
import logging
import json

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

class SignalGenerator:
    """
    一个多维度、基于评分的交易信号生成器。
    """

    def __init__(self, symbol: str, timeframe: str = '4h', proxy: Optional[str] = None):
        """
        初始化信号生成器。
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.logger = logging.getLogger(f"SignalGenerator.{symbol}.{timeframe}")
        
        exchange_config = {
            'options': {
                'defaultType': 'future'
            }
        }

        if proxy:
            self.logger.info(f"使用代理: {proxy}")
            exchange_config['proxies'] = {
                'http': proxy,
                'https': proxy,
            }

        self.exchange = ccxt.binance(exchange_config)
        self.history_limit = 400
        self.required_columns = [
            'SMA_20', 'SMA_50', 'SMA_200',
            'MACD_12_26_9', 'MACDs_12_26_9',
            'RSI_14',
            'BBU_20_2.0', 'BBL_20_2.0',
            'VOL_SMA_20'
        ]

    def _fetch_data(self) -> pd.DataFrame:
        """
        从币安获取OHLCV数据并确保数据类型正确。
        """
        try:
            self.logger.debug(f"开始获取 {self.symbol} 在 {self.timeframe} 周期上的K线数据...")
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.history_limit)
            if not ohlcv:
                self.logger.warning("API未返回任何K线数据。")
                return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.dropna(subset=numeric_cols, inplace=True)

            self.logger.debug(f"成功获取并清洗了 {len(df)} 条K线数据。")
            return df
        except Exception as e:
            self.logger.error(f"数据获取或处理失败: {e}", exc_info=True)
            return pd.DataFrame()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有必要的技术指标。
        """
        self.logger.debug("开始计算技术指标...")
        try:
            df.ta.strategy(ta.Strategy(
                name="Comprehensive_Strategy",
                ta=[
                    {"kind": "sma", "length": 20}, 
                    {"kind": "sma", "length": 50}, 
                    {"kind": "sma", "length": 200},
                    {"kind": "macd"}, 
                    {"kind": "rsi"}, 
                    {"kind": "bbands", "length": 20},
                    {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOL"}
                ]
            ))
        except Exception as e:
            self.logger.error(f"技术指标计算过程中发生未知异常: {e}", exc_info=True)
        
        self.logger.debug("技术指标计算完成。")
        return df

    def _apply_scoring_logic(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        应用多维度评分逻辑，生成最终信号。
        """
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols:
            self.logger.warning(f"评分中止：缺少必要的指标列: {missing_cols}。")
            return {}

        if len(df) < 2:
            self.logger.warning("数据行数不足，无法安全地进行评分。")
            return {}

        latest = df.iloc[-2]
        self.logger.debug(f"基于时间戳 {latest['timestamp']} 的K线进行分析。")

        scores = {'trend': 0, 'momentum': 0, 'volatility': 0, 'volume': 0}
        reasons = []

        if latest['SMA_50'] > latest['SMA_200']:
            scores['trend'] += 2; reasons.append("[趋势: 看多] 黄金交叉 (MA50 > MA200)")
        elif latest['SMA_50'] < latest['SMA_200']:
            scores['trend'] -= 2; reasons.append("[趋势: 看空] 死亡交叉 (MA50 < MA200)")
        if latest['close'] > latest['SMA_20']:
            scores['trend'] += 1; reasons.append("[趋势: 看多] 价格位于MA20之上")
        else:
            scores['trend'] -= 1; reasons.append("[趋势: 看空] 价格位于MA20之下")
        if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] and latest['MACD_12_26_9'] > 0:
            scores['trend'] += 1; reasons.append("[趋势: 看多] MACD在零轴上方金叉")
        elif latest['MACD_12_26_9'] < latest['MACDs_12_26_9'] and latest['MACD_12_26_9'] < 0:
            scores['trend'] -= 1; reasons.append("[趋势: 看空] MACD在零轴下方死叉")
        rsi = latest['RSI_14']
        if rsi > 60: scores['momentum'] += 1; reasons.append(f"[动量: 看多] RSI ({rsi:.2f}) 强势")
        elif rsi < 40: scores['momentum'] -= 1; reasons.append(f"[动量: 看空] RSI ({rsi:.2f}) 弱势")
        else: reasons.append(f"[动量: 中性] RSI ({rsi:.2f}) 观望")
        if latest['close'] > latest['BBU_20_2.0']: scores['volatility'] += 1; reasons.append("[波动性: 看多] 价格突破布林带上轨")
        elif latest['close'] < latest['BBL_20_2.0']: scores['volatility'] -= 1; reasons.append("[波动性: 看空] 价格跌破布林带下轨")
        if latest['volume'] > latest['VOL_SMA_20']:
            if latest['close'] > latest['open']: scores['volume'] += 1; reasons.append("[成交量: 看多] 放量上涨")
            else: scores['volume'] -= 1; reasons.append("[成交量: 看空] 放量下跌")
        else: reasons.append("[成交量: 中性] 缩量整理")
        total_score = sum(scores.values())
        signal = "NEUTRAL"
        if total_score >= 3: signal = "STRONG_BUY"
        elif total_score > 0: signal = "WEAK_BUY"
        elif total_score <= -3: signal = "STRONG_SELL"
        elif total_score < 0: signal = "WEAK_SELL"

        self.logger.debug("评分逻辑应用完成。")
        return {
            "timestamp": latest['timestamp'], "total_score": total_score, "signal": signal,
            "scores_breakdown": scores, "reasons": reasons
        }

    def generate_signal(self) -> Dict[str, Any]:
        """
        执行完整流程：获取数据 -> 计算指标 -> 生成信号。
        """
        self.logger.info("开始生成信号...")
        df = self._fetch_data()
        if df.empty:
            self.logger.warning("数据为空，中止信号生成。 \n")
            return {"error": "无法获取或处理K线数据"}

        df_with_indicators = self._calculate_indicators(df)
        
        final_signal = self._apply_scoring_logic(df_with_indicators)
        
        if final_signal:
            self.logger.info(f"信号生成完毕。最终信号: {final_signal.get('signal')}, 总分: {final_signal.get('total_score')}")
        else:
            self.logger.warning("信号生成失败，已中止。")

        return final_signal

# --- 使用示例：多时间周期分析框架 ---
if __name__ == '__main__':
    PROXY = 'http://127.0.0.1:10809'  # <-- 在这里修改您的代理, 如果不需要代理，请设置为 None
    SYMBOL = 'BTC/USDT'

    logging.info("--- 1. 分析战略层面 (日线图) ---")
    daily_signal_gen = SignalGenerator(symbol=SYMBOL, timeframe='1d', proxy=PROXY)
    daily_analysis = daily_signal_gen.generate_signal()
    if daily_analysis and 'error' not in daily_analysis:
        # --- 关键修复：在json.dumps中添加 ensure_ascii=False ---
        daily_analysis_str = json.dumps(daily_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"日线分析结果: \n{daily_analysis_str}")
        
        is_long_term_bullish = daily_analysis.get('total_score', 0) > 0
        long_term_direction = "看多" if is_long_term_bullish else "看空/震荡"
        logging.info(f"长期趋势判断: {long_term_direction}")

        logging.info("--- 2. 分析战术层面 (4小时图) ---")
        h4_signal_gen = SignalGenerator(symbol=SYMBOL, timeframe='4h', proxy=PROXY)
        h4_analysis = h4_signal_gen.generate_signal()
        if h4_analysis and 'error' not in h4_analysis:
            # --- 关键修复：在json.dumps中添加 ensure_ascii=False ---
            h4_analysis_str = json.dumps(h4_analysis, indent=4, default=str, ensure_ascii=False)
            logging.info(f"4小时线分析结果: \n{h4_analysis_str}")
            trade_signal = h4_analysis.get('signal', 'NEUTRAL')

            logging.info("--- 3. 最终决策 ---")
            final_decision = "HOLD"
            if is_long_term_bullish and trade_signal in ['STRONG_BUY', 'WEAK_BUY']:
                final_decision = "EXECUTE_LONG"
                logging.warning(f"决策: {final_decision} - 原因: 长期趋势看多，且短期出现买入信号。")
            elif not is_long_term_bullish and trade_signal in ['STRONG_SELL', 'WEAK_SELL']:
                final_decision = "EXECUTE_SHORT"
                logging.warning(f"决策: {final_decision} - 原因: 长期趋势看空/震荡，且短期出现卖出信号。")
            else:
                logging.info(f"决策: {final_decision} - 原因: 长短期方向冲突或信号不明 ({long_term_direction} vs {trade_signal})。建议观望。")
    else:
        logging.error("无法完成分析，因为在战略层面(日线)数据获取失败或数据不足。")
