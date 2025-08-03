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
    集成了用户高级策略：处理指标冲突、增加量能验证、引入KDJ/MACD/BOLL协同过滤。
    """

    def __init__(self, symbol: str, timeframe: str = '4h', proxy: Optional[str] = None):
        self.symbol = symbol
        self.timeframe = timeframe
        self.logger = logging.getLogger(f"SignalGenerator.{symbol}.{timeframe}")
        
        exchange_config = {'options': {'defaultType': 'future'}}
        if proxy:
            self.logger.info(f"使用代理: {proxy}")
            exchange_config['proxies'] = {'http': proxy, 'https': proxy}

        self.exchange = ccxt.binance(exchange_config)
        self.history_limit = 400
        self.required_columns = [
            'SMA_20', 'SMA_50', 'SMA_200', 'VOL_SMA_20',
            'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9',
            'RSI_14', 'BBU_20_2.0', 'BBL_20_2.0',
            'ADX_14', 'ISA_9', 'ISB_26',
            'K_9_3_3', 'D_9_3_3', 'J_9_3_3'
        ]

    def _fetch_data(self) -> pd.DataFrame:
        try:
            self.logger.debug(f"获取 {self.symbol} 在 {self.timeframe} 的K线...")
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.history_limit)
            if not ohlcv: return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols: df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=numeric_cols, inplace=True)
            self.logger.debug(f"成功获取并清洗 {len(df)} 条K线。")
            return df
        except Exception as e:
            self.logger.error(f"数据获取或处理失败: {e}", exc_info=True)
            return pd.DataFrame()

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        self.logger.debug("开始计算技术指标...")
        try:
            # 第一步：计算除KDJ外的所有指标
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
            self.logger.error(f"基础指标计算发生异常: {e}", exc_info=True)
        
        # --- 最终修复：独立计算KDJ并手动合并，以应对静默失败问题 ---
        try:
            self.logger.debug("正在独立计算并合并KDJ指标...")
            kdj = df.ta.kdj(append=False)
            df = pd.concat([df, kdj], axis=1)
            self.logger.debug("KDJ指标计算并合并成功。")
        except Exception as e:
            self.logger.error(f"KDJ指标计算或合并过程中发生错误: {e}", exc_info=True)

        self.logger.debug("技术指标计算完成。")
        return df

    def _apply_scoring_logic(self, df: pd.DataFrame, funding_rate_data: Optional[Dict] = None) -> Dict[str, Any]:
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols: self.logger.warning(f"评分中止：缺少指标列: {missing_cols}。"); return {}
        if len(df) < 2: self.logger.warning("数据行数不足，无法评分。"); return {}

        latest = df.iloc[-2]
        self.logger.debug(f"基于时间戳 {latest['timestamp']} 的K线进行分析。")

        scores = {'trend': 0, 'momentum': 0, 'sentiment': 0, 'volume': 0, 'volatility': 0}
        reasons = []

        is_golden_cross = latest['SMA_50'] > latest['SMA_200']
        is_death_cross = latest['SMA_50'] < latest['SMA_200']
        price_above_cloud = latest['close'] > latest['ISA_9'] and latest['close'] > latest['ISB_26']
        price_below_cloud = latest['close'] < latest['ISA_9'] and latest['close'] < latest['ISB_26']
        is_volume_strong = latest['volume'] > latest['VOL_SMA_20']
        cloud_thickness = abs(latest['ISA_9'] - latest['ISB_26']) / latest['close']

        if is_golden_cross:
            score = 2 if is_volume_strong else 1
            scores['trend'] += score; reasons.append(f"[趋势: 看多] 黄金交叉 (量能验证: {is_volume_strong}, 得分: {score})")
        elif is_death_cross:
            score = -2 if is_volume_strong else -1
            scores['trend'] += score; reasons.append(f"[趋势: 看空] 死亡交叉 (量能验证: {is_volume_strong}, 得分: {score})")

        if price_above_cloud:
            score = 2 if cloud_thickness > 0.03 else 1
            scores['trend'] += score; reasons.append(f"[趋势: 看多] 价格在云层之上 (云厚: {cloud_thickness:.2%}, 得分: {score})")
        elif price_below_cloud:
            score = -2 if cloud_thickness > 0.03 else -1
            scores['trend'] += score; reasons.append(f"[趋势: 看空] 价格在云层之下 (云厚: {cloud_thickness:.2%}, 得分: {score})")

        is_rsi_oversold = latest['RSI_14'] < 30
        is_kdj_oversold = latest['K_9_3_3'] < 20
        is_adx_strong = latest['ADX_14'] > 25

        if is_rsi_oversold and not is_adx_strong:
            scores['momentum'] += 1; reasons.append("[动量: 看多] RSI超卖且趋势不强，潜在反弹")
        if is_rsi_oversold and is_kdj_oversold:
            scores['momentum'] += 1; reasons.append("[动量: 看多] RSI与KDJ共振超卖，反弹需求强烈")
        if latest['MACDh_12_26_9'] > 0:
            scores['momentum'] += 1; reasons.append("[动量: 看多] MACD柱状图为正")
        elif latest['MACDh_12_26_9'] < 0:
            scores['momentum'] -= 1; reasons.append("[动量: 看空] MACD柱状图为负")

        if latest['close'] < latest['BBL_20_2.0'] and is_rsi_oversold:
            scores['volatility'] += 1; reasons.append("[波动: 看多] 价格触及布林下轨且RSI超卖")
        if price_below_cloud and not is_volume_strong:
            scores['volume'] += 1; reasons.append("[成交量: 看多] 缩量下跌，空头衰竭")
        elif price_above_cloud and not is_volume_strong:
            scores['volume'] -= 1; reasons.append("[成交量: 看空] 缩量上涨，动能不足")

        if funding_rate_data and 'fundingRate' in funding_rate_data:
            rate = float(funding_rate_data['fundingRate'])
            if rate > 0.0002: scores['sentiment'] -= 1; reasons.append(f"[情绪: 看空] 资金费率过高 ({rate:.6f})")
            elif rate < -0.0002: scores['sentiment'] += 1; reasons.append(f"[情绪: 看多] 资金费率过低 ({rate:.6f})")
            else: reasons.append(f"[情绪: 中性] 资金费率 ({rate:.6f}) 正常")

        total_score = sum(scores.values())
        signal = "NEUTRAL"
        if total_score >= 4: signal = "STRONG_BUY"
        elif total_score > 0: signal = "WEAK_BUY"
        elif total_score <= -4: signal = "STRONG_SELL"
        elif total_score < 0: signal = "WEAK_SELL"

        score_details = f"趋势={scores['trend']} | 动量={scores['momentum']} | 波动率={scores['volatility']} | 成交量={scores['volume']} | 情绪={scores['sentiment']}"
        self.logger.info(f"分数计算详情: {score_details} -> 总分: {total_score}")
        return {
            "timestamp": latest['timestamp'], "total_score": total_score, "signal": signal,
            "scores_breakdown": scores, "reasons": reasons
        }

    def generate_signal(self) -> Dict[str, Any]:
        self.logger.info("开始生成信号...")
        df = self._fetch_data()
        if df.empty: self.logger.warning("数据为空，中止。 "); return {"error": "无法获取K线数据"}

        funding_rate_data = None
        try:
            api_symbol = self.symbol.replace('/', '')
            funding_rate_data = self.exchange.fetch_funding_rate(api_symbol)
        except Exception as e:
            self.logger.warning(f"获取资金费率失败: {e}")

        df_with_indicators = self._calculate_indicators(df)
        final_signal = self._apply_scoring_logic(df_with_indicators, funding_rate_data)
        
        if final_signal: self.logger.info(f"信号生成完毕。最终信号: {final_signal.get('signal')}")
        else: self.logger.warning("信号生成失败，已中止。")
        return final_signal