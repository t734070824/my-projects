import time
import logging
import ccxt
import math

import config
from signal_generator import get_account_status, get_atr_info
from dingtalk_notifier import send_dingtalk_markdown
from logger_config import setup_position_monitor_logger

def find_associated_stop_loss_order(open_orders, position):
    """
    在未成交订单列表中，查找与指定持仓关联的止损单。
    关联逻辑：交易对相同，方向相反，数量几乎相等。
    """
    position_symbol = position['symbol']
    position_side = position['side']
    position_size = abs(float(position['size']))
    
    sl_side = 'sell' if position_side == 'long' else 'buy'

    for order in open_orders:
        if (
            order['symbol'] == position_symbol and
            order['side'] == sl_side and
            order['type'] in ['stop', 'stop_market']
        ):
            return order
    return None

def monitor_existing_positions(exchange: ccxt.Exchange):
    """
    高频运行的监控函数，获取真实止损位并提供智能追踪止损建议。
    """
    logger = logging.getLogger("PositionMonitor")
    logger.info("--- 智能仓位监控程序已启动 (可获取真实止损位) ---")

    while True:
        try:
            account_status = get_account_status(exchange)
            if 'error' in account_status:
                logger.error(f"无法获取账户状态: {account_status['error']}"); time.sleep(60); continue

            open_positions = account_status.get('open_positions', [])
            if not open_positions:
                logger.info("当前无持仓，降低监控频率..."); time.sleep(config.MONITOR_INTERVAL_NO_POSITION); continue

            # logger.info(f"监控 {len(open_positions)} 个真实仓位...")
            has_high_profit_position = False  # 用于判断是否需要高频监控

            for position in open_positions:
                symbol = position['symbol']
                side = position['side']
                entry_price = float(position['entryPrice'])

                open_orders_for_symbol = exchange.fetch_open_orders(symbol)
                stop_loss_order = find_associated_stop_loss_order(open_orders_for_symbol, position)

                if not stop_loss_order:
                    logger.error(f"!!! 持仓无保护 !!! [{symbol}] {side.upper()} 仓位没有找到关联的止损订单。")
                    continue
                
                current_stop_price = float(stop_loss_order['stopPrice'])
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                atr_info = get_atr_info(symbol, exchange)
                if 'error' in atr_info or not atr_info.get('atr'):
                    logger.warning(f"无法为 [{symbol}] 获取ATR，跳过追踪止损检查。")
                    continue

                # --- 获取特定于交易对的虚拟交易配置 ---
                trade_config = config.VIRTUAL_TRADE_CONFIG.get(symbol, config.VIRTUAL_TRADE_CONFIG["DEFAULT"])
                stop_loss_distance = atr_info['atr'] * trade_config["ATR_MULTIPLIER_FOR_SL"]
                
                new_suggested_sl = None
                if side == 'long' and current_price > entry_price + stop_loss_distance:
                    potential_new_sl = current_price - stop_loss_distance
                    if potential_new_sl > current_stop_price:
                        new_suggested_sl = potential_new_sl
                
                elif side == 'short' and current_price < entry_price - stop_loss_distance:
                    potential_new_sl = current_price + stop_loss_distance
                    if potential_new_sl < current_stop_price:
                        new_suggested_sl = potential_new_sl

                if new_suggested_sl:
                    # 计算盈利情况判断是否为高盈利仓位
                    profit_ratio = 0
                    if side == 'long':
                        profit_ratio = (current_price - entry_price) / entry_price
                    else:
                        profit_ratio = (entry_price - current_price) / entry_price
                    
                    if profit_ratio >= 0.10:  # 盈利10%以上视为高盈利
                        has_high_profit_position = True
                    
                    log_message = f"""
    ------------------------------------------------------------
    |             >>> TRAILING STOP-LOSS UPDATE <<<              |
    ------------------------------------------------------------
    | Symbol:           {symbol} ({side.upper()}) P&L: {profit_ratio:+.1%}
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f}
    |----------------------------------------------------------
    | Current Stop-Loss:{current_stop_price:,.4f} (Order ID: {stop_loss_order['id']})
    | SUGGESTED New SL: {new_suggested_sl:,.4f} (to lock profit)
    | ACTION:           Cancel old order and create a new one.
    ------------------------------------------------------------
    """
                    logger.warning(log_message)

                    # --- 发送钉钉通知 ---
                    title = f"止损更新建议: {symbol}"
                    profit_indicator = "🔥高盈利" if profit_ratio >= 0.10 else "📈盈利中"
                    markdown_text = f"""### **止损更新建议: {symbol}** {profit_indicator}

- **持仓方向**: {side.upper()}
- **开仓价格**: {entry_price:,.4f}
- **当前价格**: {current_price:,.4f} ({profit_ratio:+.1%})
- **当前止损**: {current_stop_price:,.4f}  
- **<font color='#FF0000'>建议新止损</font>**: **{new_suggested_sl:,.4f}**
- **操作建议**: 取消旧订单({stop_loss_order['id']})，创建新止损单。
"""
                    send_dingtalk_markdown(title, markdown_text)
                else:
                    # 检查现有持仓是否为高盈利（即使不需要调整止损）
                    profit_ratio = 0
                    if side == 'long':
                        profit_ratio = (current_price - entry_price) / entry_price
                    else:
                        profit_ratio = (entry_price - current_price) / entry_price
                    if profit_ratio >= 0.10:
                        has_high_profit_position = True

        except ccxt.NetworkError as e:
            logger.error(f"监控时发生网络错误: {e}")
        except Exception as e:
            logger.error(f"监控循环发生未知错误: {e}", exc_info=True)
        
        # 智能睡眠间隔：根据持仓情况动态调整
        if has_high_profit_position:
            sleep_time = config.MONITOR_INTERVAL_HIGH_PROFIT
            logger.debug(f"检测到高盈利仓位，提高监控频率至{sleep_time}秒")
        else:
            sleep_time = config.MONITOR_INTERVAL_SECONDS
        
        time.sleep(sleep_time)


if __name__ == "__main__":
    # --- 使用新的日志配置系统 ---
    logger = setup_position_monitor_logger()
    
    # 确保根日志器也使用相同配置
    root_logger = logging.getLogger()
    root_logger.handlers = logger.handlers
    root_logger.setLevel(logger.level)

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

    if not hasattr(config, 'MONITOR_INTERVAL_SECONDS'):
        logger.error("请在 config.py 文件中添加 'MONITOR_INTERVAL_SECONDS' 配置项 (例如: 15)")
    else:
        try:
            monitor_existing_positions(exchange)
        except KeyboardInterrupt:
            logger.info("\n\n监控程序被手动停止。")
