
import time
import logging
import ccxt

import config
from signal_generator import get_account_status, get_atr_info

def monitor_existing_positions(exchange: ccxt.Exchange):
    """
    高频运行的监控函数，专门负责检查和管理现有真实仓位。
    它独立于主分析程序运行，只关注追踪止损。
    """
    logger = logging.getLogger("PositionMonitor")
    logger.info("--- 独立仓位监控程序已启动 ---")

    while True:
        try:
            # 1. 获取当前真实的未平仓头寸
            account_status = get_account_status(exchange)
            if 'error' in account_status:
                logger.error(f"无法获取账户状态，暂停监控: {account_status['error']}")
                time.sleep(60) # 出错时等待较长时间
                continue

            open_positions = account_status.get('open_positions', [])
            if not open_positions:
                logger.info("当前无持仓，等待下一轮检查...")
                time.sleep(config.MONITOR_INTERVAL_SECONDS) 
                continue

            logger.info(f"监控 {len(open_positions)} 个真实仓位...")

            # 2. 遍历所有真实持仓
            for position in open_positions:
                symbol = position['symbol']
                side = position['side']
                entry_price = float(position['entryPrice'])

                # a. 获取最新价格
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']

                # b. 获取最新的ATR信息
                atr_info = get_atr_info(symbol, exchange)
                if 'error' in atr_info or not atr_info.get('atr'):
                    logger.warning(f"无法为 [{symbol}] 获取ATR，跳过本次追踪止损检查。")
                    continue

                # c. 计算追踪止损建议
                trade_config = config.VIRTUAL_TRADE_CONFIG
                stop_loss_distance = atr_info['atr'] * trade_config["ATR_MULTIPLIER_FOR_SL"]
                
                # 我们不知道当前的止损位，所以只在满足条件时发出“建议”
                if side == 'long' and current_price > entry_price + stop_loss_distance:
                    new_suggested_sl = current_price - stop_loss_distance
                    if new_suggested_sl > entry_price: # 确保止损位在开仓价之上
                        logger.warning(f"""
    ------------------------------------------------------------
    |              TRAILING STOP-LOSS SUGGESTION               |
    ------------------------------------------------------------
    | Symbol:           {symbol} (LONG)
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f}
    | SUGGESTED New SL: {new_suggested_sl:,.4f} (to lock profit)
    ------------------------------------------------------------
    """)
                elif side == 'short' and current_price < entry_price - stop_loss_distance:
                    new_suggested_sl = current_price + stop_loss_distance
                    if new_suggested_sl < entry_price: # 确保止损位在开仓价之下
                        logger.warning(f"""
    ------------------------------------------------------------
    |              TRAILING STOP-LOSS SUGGESTION               |
    ------------------------------------------------------------
    | Symbol:           {symbol} (SHORT)
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f}
    | SUGGESTED New SL: {new_suggested_sl:,.4f} (to lock profit)
    ------------------------------------------------------------
    """)
        except ccxt.NetworkError as e:
            logger.error(f"监控时发生网络错误: {e}")
        except Exception as e:
            logger.error(f"监控循环发生未知错误: {e}", exc_info=True)
        
        # 等待指定间隔后再次检查
        time.sleep(config.MONITOR_INTERVAL_SECONDS)


if __name__ == "__main__":
    # --- 1. 配置日志 ---
    log_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    log_formatter.converter = time.localtime
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    # --- 2. 初始化交易所实例 ---
    logger = logging.getLogger("MainMonitor")
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

    # --- 3. 添加监控频率配置 (需要在 config.py 中定义) ---
    if not hasattr(config, 'MONITOR_INTERVAL_SECONDS'):
        logger.error("请在 config.py 文件中添加 'MONITOR_INTERVAL_SECONDS' 配置项 (例如: 15)")
    else:
        # --- 4. 启动监控 ---
        try:
            monitor_existing_positions(exchange)
        except KeyboardInterrupt:
            logger.info("\n\n监控程序被手动停止。")
