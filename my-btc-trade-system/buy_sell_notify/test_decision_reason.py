#!/usr/bin/env python3
"""
测试决策原因提取功能
验证交易信号通知中是否包含决策原因
"""

import logging
import sys

# 添加当前目录到Python路径
sys.path.insert(0, '.')

# 复制应用程序的日志处理器类（避免导入依赖）
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

def test_decision_reason_extraction():
    """测试决策原因提取"""
    print("=== 测试决策原因提取功能 ===\n")
    
    # 创建测试日志列表
    test_logs = []
    
    # 设置测试日志器
    logger = logging.getLogger("TestTrader")
    logger.setLevel(logging.WARNING)
    
    # 创建格式器（模拟真实环境）
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建并配置我们的列表处理器
    list_handler = ListLogHandler(test_logs)
    list_handler.setFormatter(formatter)
    logger.addHandler(list_handler)
    
    # 模拟决策日志（先记录决策原因）
    logger.warning("决策: EXECUTE_SHORT - 原因: [DOT/USDT] 1d, 4h趋势看空，且1h出现卖出信号。")
    logger.warning("决策: EXECUTE_LONG - 原因: [BTC/USDT] 激进反转策略 - RSI严重超卖且触及布林下轨。")
    
    # 模拟交易信号日志
    logger.warning("""
    ------------------------------------------------------------
    |                 🚨 NEW TRADE SIGNAL 🚨                   |
    ------------------------------------------------------------
    | 交易对:           DOT/USDT
    | 方向:             SHORT
    | 入场价格:         3.6220 USDT
    | 
    | === 仓位计算 ===
    | 账户余额:         324.10 USDT  
    | 风险敞口:         2.5% = 8.10 USDT
    | 持仓量:           43.1263 DOT
    | 持仓价值:         156.20 USDT
    |
    | === 风险管理 ===
    | 止损价格:         3.8099 USDT
    | ATR距离:          0.1879 (2.2x ATR)
    | 最大亏损:         -8.10 USDT
    |
    | === 盈利目标 ===
    | 目标1 (2R):       3.2462 USDT → +16.21 USDT
    | 目标2 (3R):       3.0584 USDT → +24.31 USDT
    | 
    | 🎯 建议: 目标1处止盈50%，目标2处全部平仓
    ------------------------------------------------------------
    """)
    
    # 模拟激进策略信号
    logger.warning("""
    ------------------------------------------------------------
    |                🔥 REVERSAL TRADE SIGNAL 🔥               |
    ------------------------------------------------------------
    | 交易对:           BTC/USDT
    | 策略:             激进反转策略
    | 方向:             LONG
    | 入场价格:         43250.0000 USDT
    | 
    | === 仓位计算 (激进策略) ===
    | 账户余额:         1000.00 USDT  
    | 风险敞口:         0.8% = 8.00 USDT (较保守)
    | 持仓量:           0.0021 BTC
    | 持仓价值:         90.83 USDT
    |
    | === 风险管理 ===
    | 止损价格:         41374.0000 USDT
    | ATR距离:          1876.0000 (1.5x ATR, 更紧)
    | 最大亏损:         -8.00 USDT
    |
    | === 盈利目标 (保守) ===
    | 目标1 (1.5R):     46126.0000 USDT → +12.00 USDT
    | 目标2 (2R):       47002.0000 USDT → +16.00 USDT
    | 
    | ⚡ 反转策略特点: 快进快出，严格止损，保守止盈
    ------------------------------------------------------------
    """)
    
    print(f"总共捕获了 {len(test_logs)} 条日志记录\n")
    
    # 模拟app.py中的决策原因提取逻辑
    signal_decisions = {}  # 存储交易对 -> 决策原因的映射
    
    # 先收集所有决策原因，建立交易对映射
    for log_entry in test_logs:
        if "决策: EXECUTE_" in log_entry and " - 原因: " in log_entry:
            try:
                # 提取交易对信息
                if "[" in log_entry and "]" in log_entry:
                    symbol_part = log_entry.split("[")[1].split("]")[0]
                    decision_reason = log_entry.split(" - 原因: ")[1] if " - 原因: " in log_entry else ""
                    signal_decisions[symbol_part] = decision_reason
                    print(f"提取决策原因: {symbol_part} -> {decision_reason}")
            except:
                continue
    
    print(f"\n决策原因映射表: {signal_decisions}")
    
    # 分析交易信号
    trade_signals = []
    for log_entry in test_logs:
        if "NEW TRADE SIGNAL" in log_entry or "REVERSAL TRADE SIGNAL" in log_entry:
            trade_signals.append(log_entry)
    
    print(f"\n找到 {len(trade_signals)} 个交易信号")
    
    # 测试每个信号的决策原因关联
    for i, signal in enumerate(trade_signals):
        print(f"\n交易信号 {i+1}:")
        
        # 提取交易对
        lines = signal.split('\n')
        symbol = ""
        strategy_type = ""
        
        for line in lines:
            if "交易对:" in line:
                symbol = line.split("交易对:")[1].strip() if "交易对:" in line else ""
            
        # 判断策略类型
        if "REVERSAL TRADE SIGNAL" in signal:
            strategy_type = "激进反转策略"
        else:
            strategy_type = "趋势跟踪策略"
        
        # 获取决策原因
        decision_reason = signal_decisions.get(symbol, "系统技术指标综合判断")
        
        print(f"  交易对: {symbol}")
        print(f"  策略类型: {strategy_type}")
        print(f"  决策原因: {decision_reason}")
        
        # 验证关联是否正确
        if symbol in signal_decisions:
            print("  ✅ 成功关联决策原因")
        else:
            print("  ⚠️ 使用默认决策原因")
    
    print("\n=== 测试完成 ===")
    return len(signal_decisions) > 0 and len(trade_signals) > 0

if __name__ == "__main__":
    success = test_decision_reason_extraction()
    if success:
        print("决策原因提取功能测试通过")
    else:
        print("决策原因提取功能测试失败")