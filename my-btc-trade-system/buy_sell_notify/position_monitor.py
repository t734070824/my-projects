
import time
import logging
import ccxt
import math

import config
from signal_generator import get_account_status, get_atr_info

def find_associated_stop_loss_order(open_orders, position):
    """
    在未成交订单列表中，查找与指定持仓关联的止损单。
    关联逻辑：交易对相同，方向相反，数量几乎相等。
    """
    position_symbol = position['symbol']
    position_side = position['side']
    position_size = abs(float(position['size']))
    
    # 确定止损单应该的方向 (与持仓相反)
    sl_side = 'sell' if position_side == 'long' else 'buy'

    for order in open_orders:
        # 筛选条件：交易对相同，方向匹配，是止损单类型
        if (
            order['symbol'] == position_symbol and
            order['side'] == sl_side and
            order['type'] in ['stop', 'stop_market'] and
            # 检查数量是否足够接近 (处理精度问题)
            math.isclose(float(order['amount']), position_size)
        ):
            return order # 找到匹配的止损单
    return None # 未找到

def monitor_existing_positions(exchange: ccxt.Exchange):
    """
    高频运行的监控函数，获取真实止损位并提供智能追踪止损建议。
    """
    logger = logging.getLogger("PositionMonitor")
    logger.info("--- 智能仓位监控程序已启动 (可获取真实止损位) ---")

    while True:
        try:
            # 1. 获取当前真实的未平仓头寸和所有未成交订单
            account_status = get_account_status(exchange)
            if 'error' in account_status:
                logger.error(f"无法获取账户状态: {account_status['error']}"); time.sleep(60); continue

            open_positions = account_status.get('open_positions', [])
            if not open_positions:
                logger.info("当前无持仓，等待下一轮检查..."); time.sleep(config.MONITOR_INTERVAL_SECONDS); continue

            all_open_orders = exchange.fetch_open_orders()
            logger.info(f"监控 {len(open_positions)} 个真实仓位，发现 {len(all_open_orders)} 个未结订单...")

            # 2. 遍历所有真实持仓
            for position in open_positions:
                symbol = position['symbol']
                side = position['side']
                entry_price = float(position['entryPrice'])

                # 核心改进：查找与该持仓关联的真实止损单
                stop_loss_order = find_associated_stop_loss_order(all_open_orders, position)

                if not stop_loss_order:
                    logger.error(f"!!! 持仓无保护 !!! [{symbol}] {side.upper()} 仓位没有找到关联的止损订单。")
                    continue
                
                current_stop_price = float(stop_loss_order['stopPrice'])

                # a. 获取最新价格
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']

                # b. 获取最新的ATR信息
                atr_info = get_atr_info(symbol, exchange)
                if 'error' in atr_info or not atr_info.get('atr'):
                    logger.warning(f"无法为 [{symbol}] 获取ATR，跳过追踪止损检查。" )
                    continue

                # c. 计算新的理想止损位
                trade_config = config.VIRTUAL_TRADE_CONFIG
                stop_loss_distance = atr_info['atr'] * trade_config["ATR_MULTIPLIER_FOR_SL"]
                
                new_suggested_sl = None
                if side == 'long' and current_price > entry_price + stop_loss_distance:
                    potential_new_sl = current_price - stop_loss_distance
                    # 关键决策：只有当新建议的止损位优于当前已设置的止损位时，才发出建议
                    if potential_new_sl > current_stop_price:
                        new_suggested_sl = potential_new_sl
                
                elif side == 'short' and current_price < entry_price - stop_loss_distance:
                    potential_new_sl = current_price + stop_loss_distance
                    # 关键决策：只有当新建议的止损位优于当前已设置的止损位时，才发出建议
                    if potential_new_sl < current_stop_price:
                        new_suggested_sl = potential_new_sl

                # d. 发出更新建议
                if new_suggested_sl:
                    logger.warning(f"""
    ------------------------------------------------------------
    |             >>> TRAILING STOP-LOSS UPDATE <<<              |
    ------------------------------------------------------------
    | Symbol:           {symbol} ({side.upper()})
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f}
    |----------------------------------------------------------
    | Current Stop-Loss:{current_stop_price:,.4f} (Order ID: {stop_loss_order['id']})
    | SUGGESTED New SL: {new_suggested_sl:,.4f} (to lock profit)
    | ACTION:           Cancel old order and create a new one.
    ------------------------------------------------------------
    ")
                else:
                    logger.info(f"[{symbol}] 持仓稳定，当前止损位 {current_stop_price:,.4f} 合理，无需调整。" )

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
