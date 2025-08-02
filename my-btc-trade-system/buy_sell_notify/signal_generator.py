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
    新增了资金费率、ADX、一目均衡表等指标，以提供更全面的市场分析。
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
            'VOL_SMA_20',
            'ADX_14',       # ADX
            'ISA_9', 'ISB_26' # 一目均衡表的云层边界
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
                    {"kind": "sma", "length": 20}, {"kind": "sma", "length": 50}, {"kind": "sma", "length": 200},
                    {"kind": "macd"}, {"kind": "rsi"}, {"kind": "bbands", "length": 20},
                    {"kind": "adx"}, {"kind": "ichimoku"},
                    {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOL"}
                ]
            ))
        except Exception as e:
            self.logger.error(f"技术指标计算过程中发生未知异常: {e}", exc_info=True)
        
        self.logger.debug("技术指标计算完成。")
        return df

    def _apply_scoring_logic(self, df: pd.DataFrame, funding_rate_data: Optional[Dict] = None) -> Dict[str, Any]:
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

        scores = {'trend': 0, 'momentum': 0, 'sentiment': 0}
        reasons = []

        # --- 1. 趋势判断 (Trend Analysis) ---
        # MA交叉 (权重: +/- 2)
        if latest['SMA_50'] > latest['SMA_200']:
            scores['trend'] += 2; reasons.append("[趋势: 看多] 黄金交叉 (MA50 > MA200)")
        elif latest['SMA_50'] < latest['SMA_200']:
            scores['trend'] -= 2; reasons.append("[趋势: 看空] 死亡交叉 (MA50 < MA200)")
        
        # 价格与云层关系 (权重: +/- 1)
        if latest['close'] > latest['ISA_9'] and latest['close'] > latest['ISB_26']:
            scores['trend'] += 1; reasons.append("[趋势: 看多] 价格位于一目均衡表云层之上")
        elif latest['close'] < latest['ISA_9'] and latest['close'] < latest['ISB_26']:
            scores['trend'] -= 1; reasons.append("[趋势: 看空] 价格位于一目均衡表云层之下")

        # ADX 趋势强度 (不直接加分，仅作为判断依据)
        if latest['ADX_14'] > 25:
            reasons.append(f"[趋势: 确认] ADX ({latest['ADX_14']:.2f}) > 25，趋势强劲")
        elif latest['ADX_14'] < 20:
            reasons.append(f"[趋势: 警告] ADX ({latest['ADX_14']:.2f}) < 20，无明确趋势")

        # --- 2. 动量与强度 (Momentum & Strength) ---
        rsi = latest['RSI_14']
        if rsi > 65:
            scores['momentum'] += 1; reasons.append(f"[动量: 看多] RSI ({rsi:.2f}) 强势超买")
        elif rsi < 35:
            scores['momentum'] -= 1; reasons.append(f"[动量: 看空] RSI ({rsi:.2f}) 弱势超卖")
        else:
            reasons.append(f"[动量: 中性] RSI ({rsi:.2f}) 观望")

        # --- 3. 市场情绪 (Market Sentiment) ---
        if funding_rate_data and 'fundingRate' in funding_rate_data:
            rate = float(funding_rate_data['fundingRate'])
            if rate > 0.0005: # 资金费率过高，市场贪婪
                scores['sentiment'] -= 1; reasons.append(f"[情绪: 看空] 资金费率过高 ({rate:.4f})，市场贪婪")
            elif rate < -0.0005: # 资金费率过低，市场恐慌
                scores['sentiment'] += 1; reasons.append(f"[情绪: 看多] 资金费率过低 ({rate:.4f})，市场恐慌")
            else:
                reasons.append(f"[情绪: 中性] 资金费率 ({rate:.4f}) 正常")

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
            self.logger.warning("数据为空，中止信号生成。")
            return {"error": "无法获取或处理K线数据"}

        funding_rate_data = None
        try:
            funding_rate_data = self.exchange.fetch_funding_rate(self.symbol)
        except Exception as e:
            self.logger.warning(f"获取资金费率失败: {e}")

        df_with_indicators = self._calculate_indicators(df)
        final_signal = self._apply_scoring_logic(df_with_indicators, funding_rate_data)
        
        if final_signal:
            self.logger.info(f"信号生成完毕。最终信号: {final_signal.get('signal')}, 总分: {final_signal.get('total_score')}")
        else:
            self.logger.warning("信号生成失败，已中止。")

        return final_signal