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
from logger_config import setup_main_logger
from notification_system import (
    emit_trade_signal, emit_position_update, emit_market_analysis,
    StrategyType, TradeDirection
)

# --- 新的事件驱动通知系统已替换原有的日志解析方式 ---
def manage_virtual_trade(symbol, final_decision, analysis_data, decision_reason=""):
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
            # 对于反转信号，生成完整的交易信号通知（包含详细的仓位信息）
            available_balance = float(available_balance_str)
            risk_per_trade = trade_config["RISK_PER_TRADE_PERCENT"] / 100
            
            if final_decision == "EXECUTE_LONG":
                stop_loss_price = current_price - stop_loss_distance
                direction = TradeDirection.LONG
            else: # EXECUTE_SHORT
                stop_loss_price = current_price + stop_loss_distance
                direction = TradeDirection.SHORT

            risk_amount_usd = available_balance * risk_per_trade
            position_size_coin = risk_amount_usd / stop_loss_distance
            position_size_usd = position_size_coin * current_price

            # 计算目标价位（2:1和3:1风险回报比）
            risk_distance = abs(current_price - stop_loss_price)
            target_price_2r = current_price + (2 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (2 * risk_distance)
            target_price_3r = current_price + (3 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (3 * risk_distance)
            
            # 获取ATR配置信息
            atr_config = config.ATR_CONFIG.get(symbol, config.ATR_CONFIG["DEFAULT"])
            atr_timeframe = atr_config["timeframe"]
            atr_length = atr_config["length"]
            
            # 使用新的通知系统发送反转信号
            signal_reason = f"检测到反转信号 - 当前持仓: {position_side.upper()}, 新信号: {direction.value}"
            
            emit_trade_signal(
                symbol=symbol,
                strategy_type=StrategyType.POSITION_REVERSAL,
                direction=direction,
                entry_price=current_price,
                stop_loss_price=stop_loss_price,
                position_size_coin=position_size_coin,
                position_size_usd=position_size_usd,
                risk_amount_usd=risk_amount_usd,
                target_price_2r=target_price_2r,
                target_price_3r=target_price_3r,
                atr_value=atr,
                atr_multiplier=atr_multiplier,
                atr_timeframe=atr_timeframe,
                atr_length=atr_length,
                decision_reason=signal_reason,
                account_balance=available_balance,
                risk_percent=risk_per_trade
            )
            
            logger.warning(f"发现反转信号: {symbol} 当前{position_side.upper()}仓位，新信号{direction.value}")
            return # 发现反转信号，生成通知后停止后续操作

        # 如果不是反转信号，则执行原有的追踪止损逻辑
        entry_price = float(existing_position['entryPrice'])
        logger.info(f"发现已持有 [{symbol}] 的 {position_side.upper()} 仓位，将检查追踪止损条件。")
        
        # 计算盈亏情况
        unrealized_pnl = float(existing_position.get('unrealizedPnl', 0))
        pnl_percent = (unrealized_pnl / (entry_price * abs(float(existing_position['size'])))) * 100
        
        if position_side == 'long':
            # 长仓追踪止损逻辑
            if current_price > entry_price + stop_loss_distance:
                new_stop_loss = current_price - stop_loss_distance
                if new_stop_loss > entry_price:
                    # 计算不同止盈阶段
                    profit_ratio = (current_price - entry_price) / entry_price
                    if profit_ratio >= 0.15:  # 盈利15%以上，建议部分止盈
                        emit_position_update(
                            symbol=symbol,
                            position_side=position_side,
                            entry_price=entry_price,
                            current_price=current_price,
                            unrealized_pnl=unrealized_pnl,
                            pnl_percent=pnl_percent,
                            profit_ratio=profit_ratio,
                            new_stop_loss=new_stop_loss,
                            update_type="high_profit",
                            suggestion="考虑止盈50%仓位锁定利润"
                        )
                    elif profit_ratio >= 0.08:  # 盈利8%以上，正常追踪
                        emit_position_update(
                            symbol=symbol,
                            position_side=position_side,
                            entry_price=entry_price,
                            current_price=current_price,
                            unrealized_pnl=unrealized_pnl,
                            pnl_percent=pnl_percent,
                            profit_ratio=profit_ratio,
                            new_stop_loss=new_stop_loss,
                            update_type="trailing_stop",
                            suggestion="利润保护模式，更新止损"
                        )
                    else:  # 小幅盈利，保守追踪
                        logger.info(f"[{symbol}] LONG仓位小幅盈利({profit_ratio:.1%})，建议继续持有，止损更新至{new_stop_loss:,.4f}")
        
        elif position_side == 'short':
            # 空仓追踪止损逻辑
            if current_price < entry_price - stop_loss_distance:
                new_stop_loss = current_price + stop_loss_distance
                if new_stop_loss < entry_price:
                    profit_ratio = (entry_price - current_price) / entry_price
                    if profit_ratio >= 0.15:  # 盈利15%以上
                        emit_position_update(
                            symbol=symbol,
                            position_side=position_side,
                            entry_price=entry_price,
                            current_price=current_price,
                            unrealized_pnl=unrealized_pnl,
                            pnl_percent=pnl_percent,
                            profit_ratio=profit_ratio,
                            new_stop_loss=new_stop_loss,
                            update_type="high_profit",
                            suggestion="考虑止盈50%仓位锁定利润"
                        )
                    elif profit_ratio >= 0.08:  # 盈利8%以上
                        emit_position_update(
                            symbol=symbol,
                            position_side=position_side,
                            entry_price=entry_price,
                            current_price=current_price,
                            unrealized_pnl=unrealized_pnl,
                            pnl_percent=pnl_percent,
                            profit_ratio=profit_ratio,
                            new_stop_loss=new_stop_loss,
                            update_type="trailing_stop",
                            suggestion="利润保护模式，更新止损"
                        )
                    else:
                        logger.info(f"[{symbol}] SHORT仓位小幅盈利({profit_ratio:.1%})，建议继续持有，止损更新至{new_stop_loss:,.4f}")

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
            direction = TradeDirection.LONG
        else: # EXECUTE_SHORT
            stop_loss_price = current_price + stop_loss_distance
            direction = TradeDirection.SHORT

        risk_amount_usd = available_balance * risk_per_trade
        position_size_coin = risk_amount_usd / stop_loss_distance
        position_size_usd = position_size_coin * current_price

        # 计算目标价位（2:1和3:1风险回报比）
        risk_distance = abs(current_price - stop_loss_price)
        target_price_2r = current_price + (2 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (2 * risk_distance)
        target_price_3r = current_price + (3 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (3 * risk_distance)
        
        # 获取ATR配置信息
        atr_config = config.ATR_CONFIG.get(symbol, config.ATR_CONFIG["DEFAULT"])
        atr_timeframe = atr_config["timeframe"]
        atr_length = atr_config["length"]
        
        # 使用传入的决策原因，或者使用默认值
        if not decision_reason:
            decision_reason = "趋势跟踪策略 - 三重时间框架共振确认"
        
        emit_trade_signal(
            symbol=symbol,
            strategy_type=StrategyType.TREND_FOLLOWING,
            direction=direction,
            entry_price=current_price,
            stop_loss_price=stop_loss_price,
            position_size_coin=position_size_coin,
            position_size_usd=position_size_usd,
            risk_amount_usd=risk_amount_usd,
            target_price_2r=target_price_2r,
            target_price_3r=target_price_3r,
            atr_value=atr,
            atr_multiplier=atr_multiplier,
            atr_timeframe=atr_timeframe,
            atr_length=atr_length,
            decision_reason=decision_reason,
            account_balance=available_balance,
            risk_percent=risk_per_trade
        )
        
        logger.warning(f"新开仓信号: {symbol} {direction.value}")  # 简化日志

def manage_reversal_virtual_trade(symbol, final_decision, analysis_data, decision_reason=""):
    """
    管理激进反转策略的虚拟交易：使用更小的风险敞口和更紧的止损。
    """
    logger = logging.getLogger("ReversalTrader")
    
    # --- 提取所需数据 ---
    current_price = analysis_data.get('close_price')
    atr = analysis_data.get('atr_info', {}).get('atr')
    account_status = analysis_data.get('account_status', {})
    open_positions = account_status.get('open_positions', [])
    available_balance_str = account_status.get('usdt_balance', {}).get('availableBalance')

    if not all([current_price, atr, available_balance_str]):
        logger.error(f"无法管理 {symbol} 的激进策略交易：缺少价格、ATR或余额信息。")
        return

    # --- 检查是否存在当前交易对的持仓 ---
    existing_position = next((p for p in open_positions if p['symbol'].split(':')[0] == symbol), None)
    
    if existing_position:
        logger.warning(f"[{symbol}] 激进策略信号被忽略：已存在持仓，避免冲突。")
        return

    # --- 使用激进策略的风险参数 ---
    rev_config = config.REVERSAL_STRATEGY_CONFIG
    available_balance = float(available_balance_str)
    risk_per_trade = rev_config["risk_per_trade_percent"] / 100
    atr_multiplier = rev_config["atr_multiplier_for_sl"]
    stop_loss_distance = atr * atr_multiplier
    
    if final_decision == "EXECUTE_LONG":
        stop_loss_price = current_price - stop_loss_distance
        direction = TradeDirection.LONG
    else: # EXECUTE_SHORT
        stop_loss_price = current_price + stop_loss_distance
        direction = TradeDirection.SHORT

    risk_amount_usd = available_balance * risk_per_trade
    position_size_coin = risk_amount_usd / stop_loss_distance
    position_size_usd = position_size_coin * current_price

    # 计算目标价位（激进策略目标更保守：1.5R和2R）
    risk_distance = abs(current_price - stop_loss_price)
    target_price_15r = current_price + (1.5 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (1.5 * risk_distance)
    target_price_2r = current_price + (2 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (2 * risk_distance)
    
    # 获取ATR配置信息
    atr_config = config.ATR_CONFIG.get(symbol, config.ATR_CONFIG["DEFAULT"])
    atr_timeframe = atr_config["timeframe"]
    atr_length = atr_config["length"]
    
    # 使用传入的决策原因，或者使用默认值
    if not decision_reason:
        decision_reason = "激进反转策略 - RSI极值 + 布林带突破"
    
    emit_trade_signal(
        symbol=symbol,
        strategy_type=StrategyType.REVERSAL,
        direction=direction,
        entry_price=current_price,
        stop_loss_price=stop_loss_price,
        position_size_coin=position_size_coin,
        position_size_usd=position_size_usd,
        risk_amount_usd=risk_amount_usd,
        target_price_2r=target_price_15r,  # 激进策略用1.5R作为主要目标
        target_price_3r=target_price_2r,   # 2R作为次要目标
        atr_value=atr,
        atr_multiplier=atr_multiplier,
        atr_timeframe=atr_timeframe,
        atr_length=atr_length,
        decision_reason=decision_reason,
        account_balance=available_balance,
        risk_percent=risk_per_trade
    )
    
    logger.warning(f"激进反转信号: {symbol} {direction.value}")  # 简化日志

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
    logging.info(f"开始分析 {len(config.SYMBOLS_TO_ANALYZE)} 个交易对: {', '.join(config.SYMBOLS_TO_ANALYZE)}")
    
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

        # 创建不包含账户信息的分析结果副本用于日志输出
        daily_analysis_log = {k: v for k, v in daily_analysis.items() if k not in ['account_status']}
        daily_analysis_str = json.dumps(daily_analysis_log, indent=4, default=str, ensure_ascii=False)
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

        # 创建不包含账户信息的分析结果副本用于日志输出
        h4_analysis_log = {k: v for k, v in h4_analysis.items() if k not in ['account_status']}
        h4_analysis_str = json.dumps(h4_analysis_log, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 4小时线分析结果: {h4_analysis_str}")
        is_mid_term_bullish = h4_analysis.get('total_score', 0) > 0

        # 3. 执行层面：1小时图 (1h)
        logging.info(f"--- 3. [{symbol}] 分析执行层面 (1小时图) ---")
        h1_signal_gen = SignalGenerator(symbol=symbol, timeframe='1h', exchange=exchange)
        h1_analysis = h1_signal_gen.generate_signal(account_status, atr_info)
        if not (h1_analysis and 'error' not in h1_analysis):
            logging.error(f"无法完成 [{symbol}] 的执行层面分析，已跳过。")
            continue

        # 创建不包含账户信息的分析结果副本用于日志输出
        h1_analysis_log = {k: v for k, v in h1_analysis.items() if k not in ['account_status']}
        h1_analysis_str = json.dumps(h1_analysis_log, indent=4, default=str, ensure_ascii=False)
        logging.info(f"[{symbol}] 1小时线分析结果: {h1_analysis_str}")
        h1_signal = h1_analysis.get('signal', 'NEUTRAL')

        # 4. 最终决策：三重时间周期过滤 + 激进策略
        logging.info(f"--- 4. [{symbol}] 最终决策 (三重过滤 + 激进策略) ---")
        final_decision = "HOLD"
        reversal_signal = h1_analysis.get('reversal_signal', 'NONE')
        
        decision_reason = ""  # 初始化决策原因
        
        # 主策略：三重时间周期过滤
        if is_long_term_bullish and is_mid_term_bullish and h1_signal in ['STRONG_BUY', 'WEAK_BUY']:
            final_decision = "EXECUTE_LONG"
            decision_reason = f"[{symbol}] 1d, 4h趋势看多，且1h出现买入信号"
            logging.warning(f"决策: {final_decision} - 原因: {decision_reason}")
        elif not is_long_term_bullish and not is_mid_term_bullish and h1_signal in ['STRONG_SELL', 'WEAK_SELL']:
            final_decision = "EXECUTE_SHORT"
            decision_reason = f"[{symbol}] 1d, 4h趋势看空，且1h出现卖出信号"
            logging.warning(f"决策: {final_decision} - 原因: {decision_reason}")
        
        # 激进策略：反转交易（独立于主策略）
        elif reversal_signal in ['EXECUTE_REVERSAL_LONG', 'EXECUTE_REVERSAL_SHORT']:
            if reversal_signal == 'EXECUTE_REVERSAL_LONG':
                final_decision = "EXECUTE_LONG"
                decision_reason = f"[{symbol}] 激进反转策略 - RSI严重超卖且触及布林下轨"
                logging.warning(f"决策: {final_decision} - 原因: {decision_reason}")
            else:
                final_decision = "EXECUTE_SHORT"
                decision_reason = f"[{symbol}] 激进反转策略 - RSI严重超买且触及布林上轨"
                logging.warning(f"决策: {final_decision} - 原因: {decision_reason}")
        
        else:
            reason = f"1d({long_term_direction}) | 4h({'看多' if is_mid_term_bullish else '看空'}) | 1h({h1_signal}) | 反转({reversal_signal})"
            logging.info(f"决策: {final_decision} - 原因: [{symbol}] 无符合条件的交易信号 ({reason})。建议观望。")
            
            # 详细调试信息
            daily_score = daily_analysis.get('total_score', 0)
            h4_score = h4_analysis.get('total_score', 0)
            logging.info(f"[{symbol}] 详细评分: 日线={daily_score}, 4h线={h4_score}, 1h信号={h1_signal}")
            logging.info(f"[{symbol}] 做多条件检查: 1d看多({is_long_term_bullish}) && 4h看多({is_mid_term_bullish}) && 1h买入({h1_signal in ['STRONG_BUY', 'WEAK_BUY']})")
            logging.info(f"[{symbol}] 做空条件检查: 1d看空({not is_long_term_bullish}) && 4h看空({not is_mid_term_bullish}) && 1h卖出({h1_signal in ['STRONG_SELL', 'WEAK_SELL']})")
            
        # 5. 管理虚拟交易（开仓或追踪止损）
        # 创建包含正确ATR信息的分析数据（使用原始atr_info，不是h1时间框架的ATR）
        trade_analysis_data = h1_analysis.copy()
        trade_analysis_data['atr_info'] = atr_info  # 使用正确的ATR配置（可能是1d或4h）
        
        # 为激进策略使用不同的风险参数
        if reversal_signal in ['EXECUTE_REVERSAL_LONG', 'EXECUTE_REVERSAL_SHORT']:
            manage_reversal_virtual_trade(symbol, final_decision, trade_analysis_data, decision_reason)
        else:
            manage_virtual_trade(symbol, final_decision, trade_analysis_data, decision_reason)

        logging.info(f"==完成分析: {symbol} \n")

def run_analysis_and_notify():
    """
    简化的包装器函数：执行分析并发送市场摘要。
    交易信号和持仓更新现在通过独立的通知系统发送。
    """
    signals_count = 0
    alerts_count = 0
    errors_count = 0
    
    try:
        # 执行核心分析函数
        logging.info("开始执行多交易对分析...")
        run_multi_symbol_analysis()
        logging.info("多交易对分析完成")
        
    except Exception as e:
        logging.error("执行分析时发生严重错误:", exc_info=True)
        errors_count = 1
    
    # 发送简化的市场分析摘要
    analyzed_symbols_count = len(config.SYMBOLS_TO_ANALYZE)
    
    # 只在没有重要信号时发送摘要（重要信号已通过独立通知系统发送）
    emit_market_analysis(
        analyzed_symbols_count=analyzed_symbols_count,
        signals_count=signals_count,
        alerts_count=alerts_count,
        errors_count=errors_count
    )

# --- 主程序入口 (修改定时任务的目标) ---
def main():
    """主函数 - 设置定时任务并启动独立监控进程"""
    # --- 使用新的日志配置系统 ---
    logger = setup_main_logger()
    
    # 确保根日志器也使用相同配置
    root_logger = logging.getLogger()
    root_logger.handlers = logger.handlers
    root_logger.setLevel(logger.level)

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
