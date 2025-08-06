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

# --- 新增：全局变量和自定义日志处理器 ---
# 用于在内存中临时存储日志的列表
ANALYSIS_LOGS = []

class ListLogHandler(logging.Handler):
    """一个非常简单的日志处理器，将每条日志记录添加到全局列表中。"""
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list

    def emit(self, record):
        # 使用格式器完整格式化日志消息，保留多行内容
        if self.formatter:
            formatted_message = self.formatter.format(record)
        else:
            formatted_message = record.getMessage()
        self.log_list.append(formatted_message)

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
    existing_position = None
    
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
            else: # EXECUTE_SHORT
                stop_loss_price = current_price + stop_loss_distance

            risk_amount_usd = available_balance * risk_per_trade
            position_size_coin = risk_amount_usd / stop_loss_distance
            position_size_usd = position_size_coin * current_price

            # 计算目标价位（2:1和3:1风险回报比）
            risk_distance = abs(current_price - stop_loss_price)
            target_price_2r = current_price + (2 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (2 * risk_distance)
            target_price_3r = current_price + (3 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (3 * risk_distance)
            
            # 计算预期盈亏
            potential_loss = risk_amount_usd
            potential_profit_2r = risk_amount_usd * 2
            potential_profit_3r = risk_amount_usd * 3
            
            logger.warning(f"""
    ------------------------------------------------------------
    |                 🔄 NEW TRADE SIGNAL 🔄                   |
    |                   (反转信号)                              |
    ------------------------------------------------------------
    | 交易对:           {symbol}
    | 当前持仓:         {position_side.upper()}
    | 新信号方向:       {final_decision.replace('EXECUTE_', '')}
    | 入场价格:         {current_price:,.4f} USDT
    | 
    | === 仓位计算 ===
    | 账户余额:         {available_balance:,.2f} USDT  
    | 风险敞口:         {risk_per_trade:.1%} = {risk_amount_usd:,.2f} USDT
    | 持仓量:           {position_size_coin:,.4f} {symbol.split('/')[0]}
    | 持仓价值:         {position_size_usd:,.2f} USDT
    |
    | === 风险管理 ===
    | 止损价格:         {stop_loss_price:,.4f} USDT
    | ATR距离:          {stop_loss_distance:,.4f} ({atr_multiplier}x ATR)
    | 最大亏损:         -{potential_loss:,.2f} USDT
    |
    | === 盈利目标 ===
    | 目标1 (2R):       {target_price_2r:,.4f} USDT → +{potential_profit_2r:,.2f} USDT
    | 目标2 (3R):       {target_price_3r:,.4f} USDT → +{potential_profit_3r:,.2f} USDT
    | 
    | ⚠️  重要提醒: 建议先平仓当前{position_side.upper()}仓位，再考虑开{final_decision.replace('EXECUTE_', '')}仓
    ------------------------------------------------------------
    """)
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
                        logger.warning(f"""
    ------------------------------------------------------------
    |             HIGH PROFIT ALERT & TRAILING SL             |
    ------------------------------------------------------------
    | Symbol:           {symbol} (LONG) - 建议部分止盈
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f} (+{profit_ratio:.1%})
    | Unrealized P&L:   {unrealized_pnl:,.2f} USDT ({pnl_percent:+.1f}%)
    | 
    | SUGGESTION:       考虑止盈50%仓位锁定利润
    | New Stop Loss:    {new_stop_loss:,.4f} (for remaining 50%)
    ------------------------------------------------------------
    """)
                    elif profit_ratio >= 0.08:  # 盈利8%以上，正常追踪
                        logger.warning(f"""
    ------------------------------------------------------------
    |               TRAILING STOP LOSS UPDATE                  |
    ------------------------------------------------------------
    | Symbol:           {symbol} (LONG) - 利润保护模式
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f} (+{profit_ratio:.1%})
    | Unrealized P&L:   {unrealized_pnl:,.2f} USDT ({pnl_percent:+.1f}%)
    | New Stop Loss:    {new_stop_loss:,.4f} (Profit Locked)
    ------------------------------------------------------------
    """)
                    else:  # 小幅盈利，保守追踪
                        logger.info(f"[{symbol}] LONG仓位小幅盈利({profit_ratio:.1%})，建议继续持有，止损更新至{new_stop_loss:,.4f}")
        
        elif position_side == 'short':
            # 空仓追踪止损逻辑
            if current_price < entry_price - stop_loss_distance:
                new_stop_loss = current_price + stop_loss_distance
                if new_stop_loss < entry_price:
                    profit_ratio = (entry_price - current_price) / entry_price
                    if profit_ratio >= 0.15:  # 盈利15%以上
                        logger.warning(f"""
    ------------------------------------------------------------
    |             HIGH PROFIT ALERT & TRAILING SL             |
    ------------------------------------------------------------
    | Symbol:           {symbol} (SHORT) - 建议部分止盈
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f} (-{profit_ratio:.1%})
    | Unrealized P&L:   {unrealized_pnl:,.2f} USDT ({pnl_percent:+.1f}%)
    | 
    | SUGGESTION:       考虑止盈50%仓位锁定利润
    | New Stop Loss:    {new_stop_loss:,.4f} (for remaining 50%)
    ------------------------------------------------------------
    """)
                    elif profit_ratio >= 0.08:  # 盈利8%以上
                        logger.warning(f"""
    ------------------------------------------------------------
    |               TRAILING STOP LOSS UPDATE                  |
    ------------------------------------------------------------
    | Symbol:           {symbol} (SHORT) - 利润保护模式
    | Entry Price:      {entry_price:,.4f}
    | Current Price:    {current_price:,.4f} (-{profit_ratio:.1%})
    | Unrealized P&L:   {unrealized_pnl:,.2f} USDT ({pnl_percent:+.1f}%)
    | New Stop Loss:    {new_stop_loss:,.4f} (Profit Locked)
    ------------------------------------------------------------
    """)
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
        else: # EXECUTE_SHORT
            stop_loss_price = current_price + stop_loss_distance

        risk_amount_usd = available_balance * risk_per_trade
        position_size_coin = risk_amount_usd / stop_loss_distance
        position_size_usd = position_size_coin * current_price

        # 计算目标价位（2:1和3:1风险回报比）
        risk_distance = abs(current_price - stop_loss_price)
        target_price_2r = current_price + (2 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (2 * risk_distance)
        target_price_3r = current_price + (3 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (3 * risk_distance)
        
        # 计算预期盈亏
        potential_loss = risk_amount_usd  # 最大风险就是设定的风险金额
        potential_profit_2r = risk_amount_usd * 2  # 2倍风险回报
        potential_profit_3r = risk_amount_usd * 3  # 3倍风险回报
        
        logger.warning(f"""
    ------------------------------------------------------------
    |                 🚨 NEW TRADE SIGNAL 🚨                   |
    ------------------------------------------------------------
    | 交易对:           {symbol}
    | 方向:             {final_decision.replace('EXECUTE_', '')}
    | 入场价格:         {current_price:,.4f} USDT
    | 
    | === 仓位计算 ===
    | 账户余额:         {available_balance:,.2f} USDT  
    | 风险敞口:         {risk_per_trade:.1%} = {risk_amount_usd:,.2f} USDT
    | 持仓量:           {position_size_coin:,.4f} {symbol.split('/')[0]}
    | 持仓价值:         {position_size_usd:,.2f} USDT
    |
    | === 风险管理 ===
    | 止损价格:         {stop_loss_price:,.4f} USDT
    | ATR距离:          {stop_loss_distance:,.4f} ({atr_multiplier}x ATR)
    | 最大亏损:         -{potential_loss:,.2f} USDT
    |
    | === 盈利目标 ===
    | 目标1 (2R):       {target_price_2r:,.4f} USDT → +{potential_profit_2r:,.2f} USDT
    | 目标2 (3R):       {target_price_3r:,.4f} USDT → +{potential_profit_3r:,.2f} USDT
    | 
    | 🎯 建议: 目标1处止盈50%，目标2处全部平仓
    ------------------------------------------------------------
    """)

def manage_reversal_virtual_trade(symbol, final_decision, analysis_data):
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
    else: # EXECUTE_SHORT
        stop_loss_price = current_price + stop_loss_distance

    risk_amount_usd = available_balance * risk_per_trade
    position_size_coin = risk_amount_usd / stop_loss_distance
    position_size_usd = position_size_coin * current_price

    # 计算目标价位（激进策略目标更保守：1.5R和2R）
    risk_distance = abs(current_price - stop_loss_price)
    target_price_15r = current_price + (1.5 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (1.5 * risk_distance)
    target_price_2r = current_price + (2 * risk_distance) if final_decision == "EXECUTE_LONG" else current_price - (2 * risk_distance)
    
    # 计算预期盈亏
    potential_loss = risk_amount_usd
    potential_profit_15r = risk_amount_usd * 1.5
    potential_profit_2r = risk_amount_usd * 2

    logger.warning(f"""
    ------------------------------------------------------------
    |                🔥 REVERSAL TRADE SIGNAL 🔥               |
    ------------------------------------------------------------
    | 交易对:           {symbol}
    | 策略:             激进反转策略
    | 方向:             {final_decision.replace('EXECUTE_', '')}
    | 入场价格:         {current_price:,.4f} USDT
    | 
    | === 仓位计算 (激进策略) ===
    | 账户余额:         {available_balance:,.2f} USDT  
    | 风险敞口:         {risk_per_trade:.1%} = {risk_amount_usd:,.2f} USDT (较保守)
    | 持仓量:           {position_size_coin:,.4f} {symbol.split('/')[0]}
    | 持仓价值:         {position_size_usd:,.2f} USDT
    |
    | === 风险管理 ===
    | 止损价格:         {stop_loss_price:,.4f} USDT
    | ATR距离:          {stop_loss_distance:,.4f} ({atr_multiplier}x ATR, 更紧)
    | 最大亏损:         -{potential_loss:,.2f} USDT
    |
    | === 盈利目标 (保守) ===
    | 目标1 (1.5R):     {target_price_15r:,.4f} USDT → +{potential_profit_15r:,.2f} USDT
    | 目标2 (2R):       {target_price_2r:,.4f} USDT → +{potential_profit_2r:,.2f} USDT
    | 
    | ⚡ 反转策略特点: 快进快出，严格止损，保守止盈
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
        
        # 主策略：三重时间周期过滤
        if is_long_term_bullish and is_mid_term_bullish and h1_signal in ['STRONG_BUY', 'WEAK_BUY']:
            final_decision = "EXECUTE_LONG"
            logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 1d, 4h趋势看多，且1h出现买入信号。")
        elif not is_long_term_bullish and not is_mid_term_bullish and h1_signal in ['STRONG_SELL', 'WEAK_SELL']:
            final_decision = "EXECUTE_SHORT"
            logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 1d, 4h趋势看空，且1h出现卖出信号。")
        
        # 激进策略：反转交易（独立于主策略）
        elif reversal_signal in ['EXECUTE_REVERSAL_LONG', 'EXECUTE_REVERSAL_SHORT']:
            if reversal_signal == 'EXECUTE_REVERSAL_LONG':
                final_decision = "EXECUTE_LONG"
                logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 激进反转策略 - RSI严重超卖且触及布林下轨。")
            else:
                final_decision = "EXECUTE_SHORT"  
                logging.warning(f"决策: {final_decision} - 原因: [{symbol}] 激进反转策略 - RSI严重超买且触及布林上轨。")
        
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
            manage_reversal_virtual_trade(symbol, final_decision, trade_analysis_data)
        else:
            manage_virtual_trade(symbol, final_decision, trade_analysis_data)

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

        # 2. 智能过滤和格式化日志
        execute_signals = []
        trend_analysis = []
        alerts = []
        errors = []
        
        # 同时收集完整的交易信号详情和对应的决策原因
        trade_details = []
        signal_decisions = {}  # 存储交易对 -> 决策原因的映射
        
        # 先收集所有决策原因，建立交易对映射
        for log_entry in ANALYSIS_LOGS:
            if "决策: EXECUTE_" in log_entry and " - 原因: " in log_entry:
                try:
                    # 提取交易对信息
                    if "[" in log_entry and "]" in log_entry:
                        symbol_part = log_entry.split("[")[1].split("]")[0]
                        decision_reason = log_entry.split(" - 原因: ")[1] if " - 原因: " in log_entry else ""
                        signal_decisions[symbol_part] = decision_reason
                except:
                    continue
        
        # 收集交易详情
        i = 0
        while i < len(ANALYSIS_LOGS):
            log_entry = ANALYSIS_LOGS[i]
            
            # 检测交易信号开始（包括主策略和激进策略）
            if any(signal_start in log_entry for signal_start in ["NEW TRADE SIGNAL", "REVERSAL TRADE SIGNAL"]):
                # 找到信号开始，收集整个信号块
                signal_block = [log_entry]
                j = i + 1
                # 继续收集直到遇到结束标记
                while j < len(ANALYSIS_LOGS):
                    next_entry = ANALYSIS_LOGS[j]
                    signal_block.append(next_entry)
                    # 如果遇到结束的分隔线，就停止收集
                    if "----" in next_entry and len(signal_block) > 5:
                        break
                    j += 1
                
                if len(signal_block) > 1:
                    trade_details.append("\n".join(signal_block))
                i = j + 1
            else:
                i += 1
        
        # 然后正常收集其他信息
        for log_entry in ANALYSIS_LOGS:
            if "决策: EXECUTE_" in log_entry:
                execute_signals.append(log_entry)
            elif "长期趋势判断:" in log_entry:
                trend_analysis.append(log_entry)
            elif any(alert in log_entry for alert in ["TRAILING STOP LOSS UPDATE", "HIGH PROFIT ALERT"]):
                alerts.append(log_entry)
            elif any(error in log_entry for error in ["无法管理", "无法获取", "无法完成", "严重错误"]):
                errors.append(log_entry)

        # 3. 生成结构化的通知内容
        current_time = time.strftime("%Y-%m-%d %H:%M", time.localtime())
        
        # 调试信息
        logging.info(f"交易详情捕获结果: 找到 {len(trade_details)} 个详细信号, {len(execute_signals)} 个简单信号")
        logging.info(f"总共处理了 {len(ANALYSIS_LOGS)} 条日志记录")
        
        # 详细调试信息 - 显示所有包含关键词的日志
        signal_related_logs = []
        for log_entry in ANALYSIS_LOGS:
            if any(keyword in log_entry for keyword in ["NEW TRADE SIGNAL", "REVERSAL TRADE SIGNAL", "决策: EXECUTE_"]):
                signal_related_logs.append(log_entry)
        
        if signal_related_logs:
            logging.info(f"发现 {len(signal_related_logs)} 条信号相关日志:")
            for i, log in enumerate(signal_related_logs):
                # 清理特殊字符用于控制台显示
                clean_log = log.replace('🚨', '[ALERT]').replace('🔥', '[FIRE]')
                logging.info(f"  信号日志 {i+1}: {clean_log[:150]}{'...' if len(clean_log) > 150 else ''}")
        
        if execute_signals:
            logging.info("发现的简单信号:")
            for i, signal in enumerate(execute_signals):
                logging.info(f"  {i+1}: {signal}")
        
        if trade_details:
            logging.info("发现的详细信号:")
            for i, detail in enumerate(trade_details):
                clean_detail = detail.replace('🚨', '[ALERT]').replace('🔥', '[FIRE]')
                logging.info(f"  详细信号 {i+1}: {clean_detail[:200]}...")  # 显示前200个字符
        else:
            logging.warning("没有捕获到详细的交易信号!")
            
        # 额外调试：显示用于匹配的关键模式
        logging.info("搜索的信号模式: ['NEW TRADE SIGNAL', 'REVERSAL TRADE SIGNAL']")
        
        if execute_signals:
            # 有交易信号时发送详细通知（包含持仓量、价格、止损等完整信息）
            title = f"🚨 交易信号 - {len(execute_signals)}个"
            
            if trade_details:
                # 发送精简的交易详情，避免超过钉钉20000字节限制
                for i, detail in enumerate(trade_details):
                    # 从详细信息中提取关键信息
                    lines = detail.split('\n')
                    symbol = ""
                    direction = ""
                    entry_price = ""
                    position_size = ""
                    position_value = ""  # 持仓价值（USDT数量）
                    stop_loss = ""
                    target1 = ""
                    target2 = ""
                    max_loss = ""
                    atr_distance = ""  # ATR距离信息
                    
                    for line in lines:
                        if "交易对:" in line:
                            symbol = line.split("交易对:")[1].strip() if "交易对:" in line else ""
                        elif "方向:" in line:
                            direction = line.split("方向:")[1].strip() if "方向:" in line else ""
                        elif "入场价格:" in line:
                            entry_price = line.split("入场价格:")[1].strip() if "入场价格:" in line else ""
                        elif "持仓量:" in line:
                            position_size = line.split("持仓量:")[1].strip() if "持仓量:" in line else ""
                        elif "持仓价值:" in line:
                            position_value = line.split("持仓价值:")[1].strip() if "持仓价值:" in line else ""
                        elif "止损价格:" in line:
                            stop_loss = line.split("止损价格:")[1].strip() if "止损价格:" in line else ""
                        elif "ATR距离:" in line:
                            atr_distance = line.split("ATR距离:")[1].strip() if "ATR距离:" in line else ""
                        elif "目标1" in line and "R):" in line:
                            target1 = line.split("R):")[1].strip() if "R):" in line else ""
                        elif "目标2" in line and "R):" in line:
                            target2 = line.split("R):")[1].strip() if "R):" in line else ""
                        elif "最大亏损:" in line:
                            max_loss = line.split("最大亏损:")[1].strip() if "最大亏损:" in line else ""
                    
                    # 判断策略类型（支持三种类型）
                    is_aggressive_reversal = "REVERSAL TRADE SIGNAL" in detail  # 激进反转策略
                    is_position_reversal = "(反转信号)" in detail  # 已有持仓的反转信号
                    
                    if is_aggressive_reversal:
                        strategy_type = "激进反转策略"
                        strategy_emoji = "🔥"
                    elif is_position_reversal:
                        strategy_type = "仓位反转信号"
                        strategy_emoji = "🔄"
                    else:
                        strategy_type = "趋势跟踪策略"
                        strategy_emoji = "🚨"
                    
                    # 从交易对配置中获取ATR参数
                    atr_config = config.ATR_CONFIG.get(symbol, config.ATR_CONFIG["DEFAULT"])
                    atr_timeframe = atr_config["timeframe"]
                    atr_length = atr_config["length"]
                    
                    # 从ATR距离信息中提取ATR数值和倍数（格式: "8874.0952 (1.8x ATR)"）
                    stop_loss_distance_val = ""
                    atr_multiplier = ""
                    original_atr = ""
                    if atr_distance:
                        if "(" in atr_distance and "x ATR)" in atr_distance:
                            parts = atr_distance.split("(")
                            stop_loss_distance_val = parts[0].strip()
                            atr_multiplier = parts[1].replace("x ATR)", "").replace("x ATR, 更紧)", "").strip()
                            # 计算原始ATR值
                            try:
                                if atr_multiplier and stop_loss_distance_val:
                                    original_atr = f"{float(stop_loss_distance_val) / float(atr_multiplier):,.4f}"
                            except:
                                original_atr = "N/A"
                    
                    # 获取对应的决策原因
                    decision_reason = signal_decisions.get(symbol, "系统技术指标综合判断")
                    
                    signal_title = f"{strategy_emoji} {symbol} {direction}"
                    
                    # 根据策略类型设置不同的操作提醒
                    if is_position_reversal:
                        operation_reminder = "🔄 **重要提醒**: 检测到反转信号！建议先平仓当前持仓，再考虑开新仓"
                    elif is_aggressive_reversal:
                        operation_reminder = "🔥 **激进策略**: 快进快出，严格止损，保守止盈"
                    else:
                        operation_reminder = "⚠️ **操作提醒**: 严格执行止损，建议分批止盈"
                    
                    markdown_text = f"""### **{strategy_emoji} 交易信号: {symbol}** `{current_time}`

**策略类型**: {strategy_type}
**交易方向**: {direction}
**入场价格**: {entry_price}
**决策原因**: {decision_reason}

**仓位信息**:
- 持仓量: {position_size}
- 持仓价值: {position_value}
- 止损价: {stop_loss}
- 最大亏损: {max_loss}

**技术指标**:
- ATR周期: {atr_timeframe}
- ATR时长: {atr_length}期
- 原始ATR: {original_atr}
- 止损倍数: {atr_multiplier}x ATR
- 止损距离: {stop_loss_distance_val}

**目标价位**:
- 目标1: {target1}
- 目标2: {target2}

{operation_reminder}
"""
                    # 检查消息长度，确保不超过限制
                    if len(markdown_text.encode('utf-8')) > 18000:  # 留2000字节缓冲
                        # 如果还是太长，使用超精简版本
                        markdown_text = f"""### **{strategy_emoji} {symbol} {direction}** `{current_time}`

**策略**: {strategy_type}
**原因**: {decision_reason}
**价格**: {entry_price}
**持仓**: {position_size}
**价值**: {position_value}
**止损**: {stop_loss}
**ATR**: {atr_timeframe}/{atr_length}期 = {atr_value}

⚠️ 详细信息请查看系统日志
"""
                    
                    send_dingtalk_markdown(signal_title, markdown_text)
            else:
                # 当没有捕获到详细信号时，尝试手动构建详细信息
                logging.warning("未捕获到详细交易信号，将手动构建详细通知")
                
                # 为每个信号手动构建详细信息
                for signal in execute_signals:
                    if " - 原因: " in signal:
                        parts = signal.split(" - 原因: ")
                        decision = parts[0].replace("决策: ", "")
                        reason = parts[1] if len(parts) > 1 else "未知原因"
                        
                        # 从原因中提取交易对
                        symbol = ""
                        if "[" in reason and "]" in reason:
                            symbol = reason.split("[")[1].split("]")[0]
                        
                        signal_title = f"🚨 {symbol} {decision}"
                        markdown_text = f"""### **🚨 交易信号: {symbol}** `{current_time}`

**交易方向**: {decision}
**信号原因**: {reason}

⚠️ **注意**: 详细的仓位信息请查看系统日志，包括：
- 建议持仓量和风险敞口
- 止损价格和ATR距离  
- 目标价位和预期盈利

**风险提醒**: 
- 严格执行止损策略
- 建议分批止盈
- 密切关注市场变化
"""
                        send_dingtalk_markdown(signal_title, markdown_text)
        
        if alerts:
            # 有持仓调整建议时发送提醒
            title = f"📊 持仓管理提醒 - {len(alerts)}个"
            markdown_text = f"""### **📊 持仓管理提醒** `{current_time}`

发现 {len(alerts)} 个持仓需要关注:
```
{chr(10).join(alerts[:3])}  
```
"""
            send_dingtalk_markdown(title, markdown_text)
        
        # 发送简化的定时报告
        summary_items = []
        analyzed_symbols = len([log for log in ANALYSIS_LOGS if "开始分析:" in log])
        
        if analyzed_symbols > 0:
            summary_items.append(f"✅ 已分析 {analyzed_symbols} 个交易对")
        if execute_signals:
            summary_items.append(f"🎯 发现 {len(execute_signals)} 个交易信号")
        if alerts:
            summary_items.append(f"⚠️ {len(alerts)} 个持仓需关注")
        if errors:
            summary_items.append(f"❌ {len(errors)} 个错误")
        
        if not execute_signals and not alerts:  # 只有在无重要事件时才发送定时摘要
            title = f"📈 市场分析摘要"
            markdown_text = f"""### **📈 市场分析摘要** `{current_time}`

{chr(10).join(summary_items) if summary_items else "✅ 系统运行正常，暂无重要信号"}
"""
            send_dingtalk_markdown(title, markdown_text)

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
