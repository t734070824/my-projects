
import schedule
import time
import logging
import json
import ccxt

import config
from signal_generator import SignalGenerator, get_account_status, get_atr_info

def manage_virtual_trade(symbol, final_decision, analysis_data):
    """
    管理虚拟交易：根据信号开仓，或根据市场情况调整现有仓位的止损。
    """
    logger = logging.getLogger("VirtualTrader")
    
    # --- 提取所需数据 ---
    current_price = analysis_data.get('close_price')
    atr = analysis_data.get('atr_info', {}).get('atr')
    account_status = analysis_data.get('account_status', {})
    open_positions = account_status.get('open_positions', [])
    available_balance_str = account_status.get('usdt_balance', {}).get('availableBalance')

    if not all([current_price, atr, available_balance_str]):
        logger.error(f"无法管理 {symbol} 的虚拟交易：缺少价格、ATR或余额信息。")
        return

    # --- 检查是否存在当前交易对的持仓 (关键修复：统一合约名称格式) ---
    normalized_symbol = symbol.replace('/', '')
    existing_position = next((p for p in open_positions if p['symbol'] == normalized_symbol), None)
    
    trade_config = config.VIRTUAL_TRADE_CONFIG
    atr_multiplier = trade_config["ATR_MULTIPLIER_FOR_SL"]
    stop_loss_distance = atr * atr_multiplier

    if existing_position:
        # --- 逻辑2：已有持仓，检查是否需要追踪止损 ---
        entry_price = float(existing_position['entryPrice'])
        
        if existing_position['side'] == 'long':
            # 对于多头，只有当价格上涨超过一个止损距离时，才开始追踪
            if current_price > entry_price + stop_loss_distance:
                new_stop_loss = current_price - stop_loss_distance
                # 确保新的止损点高于入场价，以锁定利润
                if new_stop_loss > entry_price:
                    logger.warning(f"""
    ------------------------------------------------------------
    |               TRAILING STOP LOSS UPDATE                  |
    ------------------------------------------------------------
    | Symbol:           {symbol} (LONG)
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f}
    | New Stop Loss:    {new_stop_loss:,.4f} (Profit Locked)
    ------------------------------------------------------------
    """)
        elif existing_position['side'] == 'short':
            # 对于空头，只有当价格下跌超过一个止损距离时，才开始追踪
            if current_price < entry_price - stop_loss_distance:
                new_stop_loss = current_price + stop_loss_distance
                # 确保新的止损点低于入场价，以锁定利润
                if new_stop_loss < entry_price:
                    logger.warning(f"""
    ------------------------------------------------------------
    |               TRAILING STOP LOSS UPDATE                  |
    ------------------------------------------------------------
    | Symbol:           {symbol} (SHORT)
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f}
    | New Stop Loss:    {new_stop_loss:,.4f} (Profit Locked)
    ------------------------------------------------------------
    """)

    else:
        # --- 逻辑1：没有持仓，检查是否有新的开仓信号 ---
        if final_decision not in ["EXECUTE_LONG", "EXECUTE_SHORT"]:
            return # 没有开仓信号，且没有持仓，不做任何事

        available_balance = float(available_balance_str)
        risk_per_trade = trade_config["RISK_PER_TRADE_PERCENT"] / 100
        
        if final_decision == "EXECUTE_LONG":
            stop_loss_price = current_price - stop_loss_distance
        else: # EXECUTE_SHORT
            stop_loss_price = current_price + stop_loss_distance

        risk_amount_usd = available_balance * risk_per_trade
        position_size_coin = risk_amount_usd / stop_loss_distance
        position_size_usd = position_size_coin * current_price

        logger.warning(f"""
    ------------------------------------------------------------
    |                 NEW VIRTUAL TRADE ALERT                  |
    ------------------------------------------------------------
    | Symbol:           {symbol}
    | Decision:         {final_decision}
    |
    | Entry Price:      {current_price:,.4f}
    | Initial Stop Loss:{stop_loss_price:,.4f} (Distance: {stop_loss_distance:,.4f})
    |
    | Account Balance:  {available_balance:,.2f} USDT
    | Risk Amount:      {risk_amount_usd:,.2f} USDT ({risk_per_trade:.2%})
    | Position Size:    {position_size_coin:,.4f} {symbol.split('/')[0]} ({position_size_usd:,.2f} USDT)
    ------------------------------------------------------------
    """)

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
        
        # 为当前交易对获取ATR信息
        logging.info(f"--- 0. [{symbol}] 获取ATR信息 ---")
        atr_info = get_atr_info(symbol, exchange)
        if 'error' in atr_info:
            logging.warning(f"无法获取 [{symbol}] 的ATR信息: {atr_info['error']}，将继续分析。")
        else:
            atr_val = atr_info.get('atr')
            tf = atr_info.get('timeframe')
            length = atr_info.get('length')
            logging.info(f"[{symbol}] 的ATR(周期:{tf}, 长度:{length})值为: {atr_val}")

        # 1. 战略层面：日线图 (1d)
        logging.info(f"--- 1. [{symbol}] 分析战略层面 (日线图) ---")
        daily_signal_gen = SignalGenerator(symbol=symbol, timeframe='1d', exchange=exchange)
        daily_analysis = daily_signal_gen.generate_signal(account_status, atr_info)
        if not (daily_analysis and 'error' not in daily_analysis):
            logging.error(f"无法完成 [{symbol}] 的战略层面分析，已跳过。")
            continue

        daily_analysis_str = json.dumps(daily_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 日线分析结果: {daily_analysis_str}")
        is_long_term_bullish = daily_analysis.get('total_score', 0) > 0
        long_term_direction = "看多" if is_long_term_bullish else "看空/震荡"
        logging.info(f"[{symbol}] 长期趋势判断: {long_term_direction}")

        # 2. 战术层面：4小时图 (4h)
        logging.info(f"--- 2. [{symbol}] 分析战术层面 (4小时图) ---")
        h4_signal_gen = SignalGenerator(symbol=symbol, timeframe='4h', exchange=exchange)
        h4_analysis = h4_signal_gen.generate_signal(account_status, atr_info)
        if not (h4_analysis and 'error' not in h4_analysis):
            logging.error(f"无法完成 [{symbol}] 的战术层面分析，已跳过。")
            continue

        h4_analysis_str = json.dumps(h4_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 4小时线分析结果: {h4_analysis_str}")
        is_mid_term_bullish = h4_analysis.get('total_score', 0) > 0

        # 3. 执行层面：1小时图 (1h)
        logging.info(f"--- 3. [{symbol}] 分析执行层面 (1小时图) ---")
        h1_signal_gen = SignalGenerator(symbol=symbol, timeframe='1h', exchange=exchange)
        h1_analysis = h1_signal_gen.generate_signal(account_status, atr_info)
        if not (h1_analysis and 'error' not in h1_analysis):
            logging.error(f"无法完成 [{symbol}] 的执行层面分析，已跳过。")
            continue


        h1_analysis_str = json.dumps(h1_analysis, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 1小时线分析结果: {h1_analysis_str}")
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
            
        # 5. 管理虚拟交易（开仓或追踪止损）
        manage_virtual_trade(symbol, final_decision, h1_analysis)

        logging.info(f"================== 完成分析: {symbol} ==================\n")




# --- 主程序入口 ---
def main():
    """主函数 - 设置定时任务"""
    # --- 配置日志以使用本地时间 ---
    log_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    log_formatter.converter = time.localtime # 关键：使用本地时间
    root_logger = logging.getLogger()
    # 清除可能存在的旧处理器
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    # 添加新的控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    logging.info("=== 新版交易信号分析系统启动 (使用本地时间) ===")
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
