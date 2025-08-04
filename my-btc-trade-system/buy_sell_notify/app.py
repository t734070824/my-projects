import schedule
import time
import logging
import json
import ccxt
import subprocess
import sys

import config
from signal_generator import SignalGenerator, get_account_status, get_atr_info
from dingtalk_notifier import send_dingtalk_markdown

# --- 新增：全局变量和自定义日志处理器 ---
# 用于在内存中临时存储日志的列表
ANALYSIS_LOGS = []

class ListLogHandler(logging.Handler):
    """一个非常简单的日志处理器，将每条日志记录添加到全局列表中。"""
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list

    def emit(self, record):
        # 只将原始消息追加到列表中，不包含时间、名称、级别等格式化信息
        self.log_list.append(record.getMessage())

# --- 原有代码区域 (保持完全不变) ---
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

    # --- 检查是否存在当前交易对的持仓 (关键修复：处理':USDT' 后缀) ---
    existing_position = next((p for p in open_positions if p['symbol'].split(':')[0] == symbol), None)
    
    # --- 获取特定于交易对的虚拟交易配置 ---
    trade_config = config.VIRTUAL_TRADE_CONFIG.get(symbol, config.VIRTUAL_TRADE_CONFIG["DEFAULT"])
    logger.info(f"为 [{symbol}] 使用交易配置: {trade_config}")
    
    atr_multiplier = trade_config["ATR_MULTIPLIER_FOR_SL"]
    stop_loss_distance = atr * atr_multiplier

    if existing_position:
        # --- 逻辑2：已有持仓，检查信号冲突或追踪止损 ---
        position_side = existing_position['side']
        
        # 关键修正：检查新信号是否与持仓方向相反
        is_reversal_signal = (
            (position_side == 'long' and final_decision == "EXECUTE_SHORT") or
            (position_side == 'short' and final_decision == "EXECUTE_LONG")
        )

        if is_reversal_signal:
            logger.warning(f"""
    ------------------------------------------------------------
    |                  REVERSAL SIGNAL ALERT                   |
    ------------------------------------------------------------
    | Symbol:           {symbol}
    | Current Position: {position_side.upper()}
    | New Signal:       {final_decision}
    |
    | ACTION:           Consider closing the current position and
    |                   evaluating the new signal for entry.
    ------------------------------------------------------------
    """)
            return # 发现反转信号，停止后续操作

        # 如果不是反转信号，则执行原有的追踪止损逻辑
        entry_price = float(existing_position['entryPrice'])
        logger.info(f"发现已持有 [{symbol}] 的 {position_side.upper()} 仓位，将检查追踪止损条件。")
        
        if position_side == 'long':
            if current_price > entry_price + stop_loss_distance:
                new_stop_loss = current_price - stop_loss_distance
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
        elif position_side == 'short':
            if current_price < entry_price - stop_loss_distance:
                new_stop_loss = current_price + stop_loss_distance
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

        # 关键逻辑：在准备开新仓前，再次确认没有持仓（以防万一）
        if existing_position:
            logger.warning(f"信号冲突：收到 {final_decision} 信号，但已持有 [{symbol}] 仓位。本次不执行任何操作。")
            return

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
        logging.info(f"=== 开始分析: {symbol} ")
        
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

        logging.info(f"==完成分析: {symbol} \n")

# --- 新增：包装器函数，用于捕获日志并发送通知 ---
def run_analysis_and_notify():
    """
    一个包装器，它执行核心分析函数，捕获其所有日志输出，
    然后将捕获的日志通过钉钉发送出去。
    """
    global ANALYSIS_LOGS
    ANALYSIS_LOGS = [] # 每次运行时清空列表
    
    root_logger = logging.getLogger()
    # 获取当前控制台处理器的格式器，以便我们的新处理器使用相同的格式
    formatter = root_logger.handlers[0].formatter
    
    # 创建并挂载我们的自定义列表处理器
    list_handler = ListLogHandler(ANALYSIS_LOGS)
    list_handler.setFormatter(formatter)
    root_logger.addHandler(list_handler)

    try:
        # 执行原始的、未经修改的分析函数
        run_multi_symbol_analysis()
    except Exception:
        # 如果发生任何未捕获的异常，也将其记录下来
        logging.error("执行分析时发生严重错误:", exc_info=True)
    finally:
        # --- 无论成功或失败，最后都执行 ---
        # 1. 从系统中卸载我们的自定义处理器，避免重复记录
        root_logger.removeHandler(list_handler)

        # 2. 过滤日志，只保留关键信息
        key_info_phrases = [
            "开始分析:",
            "的ATR(周期:",
            "长期趋势判断:",
            "决策: ",
            "REVERSAL SIGNAL ALERT",
            "TRAILING STOP LOSS UPDATE",
            "NEW VIRTUAL TRADE ALERT",
            "信号冲突：",
            "无法管理", # 虚拟交易管理中的错误
            "无法获取账户状态", # 分析中止错误
            "无法完成", # 分析跳过错误
            "执行分析时发生严重错误", # 包装器中的错误
            "完成分析:"
        ]
        
        filtered_logs = []
        for log_entry in ANALYSIS_LOGS:
            if any(phrase in log_entry for phrase in key_info_phrases):
                filtered_logs.append(log_entry)
        
        # 3. 将收集到的日志列表合并成一个字符串
        captured_logs = "\n".join(filtered_logs)


        # 3. 发送钉钉通知
        if captured_logs:
            title = "每小时市场分析报告"
            max_len = 18000 # 钉钉消息长度限制
            if len(captured_logs) > max_len:
                captured_logs = captured_logs[:max_len] + "\n\n... (消息过长，已被截断)"
            
            markdown_text = f"### **每小时市场分析报告**\n\n```\n{captured_logs}\n```"
            send_dingtalk_markdown(title, markdown_text)

# --- 主程序入口 (修改定时任务的目标) ---
def main():
    """主函数 - 设置定时任务并启动独立监控进程"""
    # --- 配置日志以使用本地时间 ---
    log_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    log_formatter.converter = time.localtime
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    logging.info("=== 交易信号分析系统启动 (主程序) ===")

    # --- 启动独立的监控脚本作为子进程 ---
    monitor_process = None
    try:
        logging.info("正在启动独立的仓位监控进程...")
        monitor_process = subprocess.Popen([sys.executable, "position_monitor.py"])
        logging.info(f"仓位监控进程已启动，PID: {monitor_process.pid}")

        # --- 设置并运行主分析任务的定时调度 ---
        logging.info(f"主分析任务将每小时的{config.RUN_AT_MINUTE}分执行一次分析...")
        
        # --- 关键修改：将定时任务的目标指向新的包装器函数 ---
        run_analysis_and_notify() # 立即执行一次
        schedule.every().hour.at(config.RUN_AT_MINUTE).do(run_analysis_and_notify)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("\n\n主程序被手动停止运行")
    except Exception as e:
        logging.error(f"主程序发生严重错误: {e}", exc_info=True)
    finally:
        if monitor_process:
            logging.info("正在终止仓位监控进程...")
            monitor_process.terminate()
            monitor_process.wait()
            logging.info("仓位监控进程已终止。")

if __name__ == "__main__":
    main()
