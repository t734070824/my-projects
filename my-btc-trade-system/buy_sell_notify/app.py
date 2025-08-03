
import schedule
import time
import logging
import json
import ccxt

import config
from signal_generator import SignalGenerator, get_account_status

# --- 核心分析函数 ---
def run_multi_symbol_analysis():
    """遍历多个交易对，执行三重时间周期信号分析 (1d, 4h, 1h)。"""
    # --- 1. 初始化交易所并获取一次性数据 ---
    logger = logging.getLogger("Analyzer")
    logger.info("初始化交易所实例...")
    exchange_config = {
        'apiKey': config.API_KEY,
        'secret': config.SECRET_KEY,
        'options': {'defaultType': 'future'},
    }
    if config.PROXY:
        logger.info(f"使用代理: {config.PROXY}")
        exchange_config['proxies'] = {'http': config.PROXY, 'https': config.PROXY}
    
    exchange = ccxt.binance(exchange_config)
    
    logger.info("获取当前账户状态...")
    account_status = get_account_status(exchange)
    if 'error' in account_status:
        logger.error(f"无法获取账户状态，分析中止: {account_status['error']}")
        return

    # --- 2. 循环分析每个交易对 ---
    for symbol in config.SYMBOLS_TO_ANALYZE:
        logging.info(f"================== 开始分析: {symbol} ==================")
        
        # 1. 战略层面：日线图 (1d)
        logging.info(f"--- 1. [{symbol}] 分析战略层面 (日线图) ---")
        daily_signal_gen = SignalGenerator(symbol=symbol, timeframe='1d', exchange=exchange)
        daily_analysis = daily_signal_gen.generate_signal(account_status)
        if not (daily_analysis and 'error' not in daily_analysis):
            logging.error(f"无法完成 [{symbol}] 的战略层面分析，已跳过。")
            continue

        daily_analysis_str = json.dumps(daily_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 日线分析结果: \n{daily_analysis_str}")
        is_long_term_bullish = daily_analysis.get('total_score', 0) > 0
        long_term_direction = "看多" if is_long_term_bullish else "看空/震荡"
        logging.info(f"[{symbol}] 长期趋势判断: {long_term_direction}")

        # 2. 战术层面：4小时图 (4h)
        logging.info(f"--- 2. [{symbol}] 分析战术层面 (4小时图) ---")
        h4_signal_gen = SignalGenerator(symbol=symbol, timeframe='4h', exchange=exchange)
        h4_analysis = h4_signal_gen.generate_signal(account_status)
        if not (h4_analysis and 'error' not in h4_analysis):
            logging.error(f"无法完成 [{symbol}] 的战术层面分析，已跳过。")
            continue

        h4_analysis_str = json.dumps(h4_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 4小时线分析结果: \n{h4_analysis_str}")
        is_mid_term_bullish = h4_analysis.get('total_score', 0) > 0

        # 3. 执行层面：1小时图 (1h)
        logging.info(f"--- 3. [{symbol}] 分析执行层面 (1小时图) ---")
        h1_signal_gen = SignalGenerator(symbol=symbol, timeframe='1h', exchange=exchange)
        h1_analysis = h1_signal_gen.generate_signal(account_status)
        if not (h1_analysis and 'error' not in h1_analysis):
            logging.error(f"无法完成 [{symbol}] 的执行层面分析，已跳过。")
            continue

        h1_analysis_str = json.dumps(h1_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 1小时线分析结果: \n{h1_analysis_str}")
        h1_signal = h1_analysis.get('signal', 'NEUTRAL')

        # 4. 最终决策：三重时间周期过滤
        logging.info(f"--- 4. [{symbol}] 最终决策 (三重过滤) ---")
        final_decision = "HOLD"
        if is_long_term_bullish and is_mid_term_bullish and h1_signal in ['STRONG_BUY', 'WEAK_BUY']:
            final_decision = "EXECUTE_LONG"
            logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 1d, 4h趋势看多，且1h出现买入信号。")
        elif not is_long_term_bullish and not is_mid_term_bullish and h1_signal in ['STRONG_SELL', 'WEAK_SELL']:
            final_decision = "EXECUTE_SHORT"
            logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 1d, 4h趋势看空，且1h出现卖出信号。")
        else:
            reason = f"1d({long_term_direction}) | 4h({'看多' if is_mid_term_bullish else '看空'}) | 1h({h1_signal})"
            logging.info(f"决策: {final_decision} - 原因: [{symbol}] 时间周期信号冲突 ({reason})。建议观望。")
            
        logging.info(f"================== 完成分析: {symbol} ==================\n")


# --- 主程序入口 ---
def main():
    """主函数 - 设置定时任务"""
    logging.info("=== 新版交易信号分析系统启动 ===")
    logging.info(f"系统将每小时的{config.RUN_AT_MINUTE}分执行一次分析...")
    
    run_multi_symbol_analysis()
    
    # --- 关键修改：设置为每小时的第01分钟执行 ---
    schedule.every().hour.at(config.RUN_AT_MINUTE).do(run_multi_symbol_analysis)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\n\n系统被手动停止运行")
            break
        except Exception as e:
            logging.error(f"定时任务执行出错: {e}", exc_info=True)
            time.sleep(60)

if __name__ == "__main__":
    main()
