import ccxt
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, List, Optional
import logging
import json
import config

# 日志由主程序 app.py 统一配置
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     encoding='utf-8'
# )

def get_account_status(exchange: ccxt.Exchange) -> Dict[str, Any]:
    """获取币安期货账户的余额信息和当前未平仓的头寸。"""
    logger = logging.getLogger("AccountStatus")
    logger.debug("开始获取账户状态...")
    try:
        # 1. 获取账户余额
        balance_data = exchange.fetch_balance()
        usdt_balance = next((item for item in balance_data['info']['assets'] if item['asset'] == 'USDT'), {})
        
        # 2. 获取未平仓头寸
        positions_data = exchange.fetch_positions()
        open_positions = [p for p in positions_data if float(p['info']['positionAmt']) != 0]
        
        logger.debug(f"发现 {len(open_positions)} 个未平仓头寸。")

        # 3. 整理并返回数据
        return {
            "usdt_balance": {
                'walletBalance': usdt_balance.get('walletBalance'),
                'availableBalance': usdt_balance.get('availableBalance'),
                'unrealizedProfit': usdt_balance.get('unrealizedProfit')
            },
            "open_positions": [
                {
                    'symbol': p['symbol'],
                    'side': 'long' if float(p['info']['positionAmt']) > 0 else 'short',
                    'size': float(p['info']['positionAmt']),
                    'entryPrice': float(p['entryPrice']),
                    'markPrice': float(p['markPrice']),
                    'unrealizedPnl': float(p['unrealizedPnl']),
                    'leverage': int(p['leverage']),
                } for p in open_positions
            ]
        }
    except ccxt.AuthenticationError as e:
        logger.error(f"API密钥认证失败: {e}")
        return {"error": "AuthenticationError"}
    except ccxt.NetworkError as e:
        logger.error(f"网络连接失败: {e}")
        return {"error": "NetworkError"}
    except Exception as e:
        logger.error(f"获取账户信息时发生未知错误: {e}", exc_info=True)
        return {"error": str(e)}

def get_atr_info(symbol: str, exchange: ccxt.Exchange) -> Dict[str, Any]:
    """获取指定交易对的ATR（平均真实波幅）值，使用config中定义的参数。"""
    logger = logging.getLogger("ATR_Fetcher")
    
    # 1. 从配置读取参数
    atr_params = config.ATR_CONFIG.get(symbol, config.ATR_CONFIG["DEFAULT"])
    timeframe = atr_params["timeframe"]
    length = atr_params["length"]
    
    logger.debug(f"开始获取 {symbol} 的ATR信息 (周期: {timeframe}, 长度: {length})...")
    try:
        # 2. 获取K线数据 (获取更多数据以保证ATR计算的准确性)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
        if not ohlcv or len(ohlcv) < length:
            logger.warning(f"无法获取足够的 {symbol} 在 {timeframe} 的K线数据。")
            return {"error": "Not enough OHLCV data"}

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 3. 计算ATR
        df.ta.atr(length=length, append=True)
        
        # 4. 检查结果并返回
        atr_col_name = f'ATRr_{length}'
        if atr_col_name not in df.columns or df[atr_col_name].isnull().all():
            logger.error(f"无法计算 {symbol} 的ATR值。")
            return {"error": "ATR calculation failed"}
            
        latest_atr = df[atr_col_name].iloc[-2]
        
        logger.debug(f"成功获取 {symbol} 的ATR值为: {latest_atr}")
        return {
            "atr": round(latest_atr, 4),
            "timeframe": timeframe,
            "length": length
        }

    except Exception as e:
        logger.error(f"获取 {symbol} 的ATR信息时发生错误: {e}", exc_info=True)
        return {"error": str(e)}

class SignalGenerator:
    """
    一个多维度、基于评分的交易信号生成器。
    """

    def __init__(self, symbol: str, timeframe: str, exchange: ccxt.Exchange):
        self.symbol = symbol
        self.timeframe = timeframe
        self.logger = logging.getLogger(f"SignalGenerator.{symbol}.{timeframe}")
        self.exchange = exchange
        self.history_limit = config.HISTORY_LIMIT
        self.required_columns = [
            'SMA_20', 'SMA_50', 'SMA_200', 'VOL_SMA_20',
            'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9',
            'RSI_14', 'BBU_20_2.0', 'BBL_20_2.0',
            'ADX_14', 'ISA_9', 'ISB_26',
            'K_9_3', 'D_9_3', 'J_9_3'
        ]

    def _fetch_data(self) -> pd.DataFrame:
        try:
            self.logger.debug(f"获取 {self.symbol} 在 {self.timeframe} 的K线...")
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=self.history_limit)
            if not ohlcv: return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # 关键修改：将UTC时间戳转换为北京时间
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Shanghai')
            
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
            df.ta.strategy(ta.Strategy(
                name="Comprehensive_Strategy",
                ta=[
                    {"kind": "sma", "length": 20}, {"kind": "sma", "length": 50}, {"kind": "sma", "length": 200},
                    {"kind": "macd"}, {"kind": "rsi"}, {"kind": "bbands", "length": 20},
                    {"kind": "adx"}, {"kind": "ichimoku"}, {"kind": "kdj"},
                    {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOL"}
                ]
            ))
        except Exception as e:
            self.logger.error(f"技术指标计算过程中发生异常: {e}", exc_info=True)
        
        self.logger.debug("技术指标计算完成。")
        return df

    def _apply_scoring_logic(self, df: pd.DataFrame, funding_rate_data: Optional[Dict] = None) -> Dict[str, Any]:
        missing_cols = [col for col in self.required_columns if col not in df.columns]
        if missing_cols: self.logger.warning(f"评分中止：缺少指标列: {missing_cols}。"); return {}
        if len(df) < 2: self.logger.warning("数据行数不足，无法评分。"); return {}

        latest = df.iloc[-2]
        self.logger.debug(f"基于时间戳 {latest['timestamp']} 的K线进行分析。")

        # --- 1. 原有的趋势跟踪评分逻辑 ---
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
        is_kdj_oversold = latest['K_9_3'] < 20
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

        # --- 2. 新增：激进的反转策略逻辑 ---
        reversal_signal = "NONE"
        rev_config = config.REVERSAL_STRATEGY_CONFIG
        if rev_config["enabled"] and self.timeframe == rev_config["timeframe"]:
            self.logger.debug(f"正在执行激进反转策略 (RSI < {rev_config['rsi_oversold']} or > {rev_config['rsi_overbought']})")
            
            # 做多条件：RSI严重超卖 + 价格触及或跌破布林下轨
            if latest['RSI_14'] < rev_config["rsi_oversold"] and latest['close'] <= latest['BBL_20_2.0']:
                reversal_signal = "EXECUTE_REVERSAL_LONG"
                reasons.append(f"[反转策略: 做多] RSI ({latest['RSI_14']:.2f}) 严重超卖且价格触及布林下轨。")
            
            # 做空条件：RSI严重超买 + 价格触及或突破布林上轨
            elif latest['RSI_14'] > rev_config["rsi_overbought"] and latest['close'] >= latest['BBU_20_2.0']:
                reversal_signal = "EXECUTE_REVERSAL_SHORT"
                reasons.append(f"[反转策略: 做空] RSI ({latest['RSI_14']:.2f}) 严重超买且价格触及布林上轨。")

        # --- 3. 整合结果 ---
        return {
            "timestamp": latest['timestamp'], 
            "total_score": total_score, 
            "signal": signal,
            "reversal_signal": reversal_signal, # 新增字段
            "scores_breakdown": scores, 
            "reasons": reasons, 
            "close_price": latest['close']
        }

    def generate_signal(self, account_status: Optional[Dict] = None, atr_info: Optional[Dict] = None) -> Dict[str, Any]:
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
        
        if final_signal:
            self.logger.info(f"信号生成完毕。最终信号: {final_signal.get('signal')}, 总分: {final_signal.get('total_score')}")
            if account_status:
                final_signal['account_status'] = account_status
            if atr_info:
                final_signal['atr_info'] = atr_info
        else:
            self.logger.warning("信号生成失败，已中止。")
        return final_signal