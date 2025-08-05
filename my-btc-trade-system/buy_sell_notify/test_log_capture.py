#!/usr/bin/env python3
"""
测试日志捕获功能
验证ListLogHandler是否能够正确捕获多行交易信号
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

def test_log_capture():
    """测试日志捕获功能"""
    print("=== 测试日志捕获功能 ===\n")
    
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
    
    # 模拟发送一个交易信号日志（类似实际系统）
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
    
    # 发送一个决策日志
    logger.warning("决策: EXECUTE_SHORT - 原因: [DOT/USDT] 1d, 4h趋势看空，且1h出现卖出信号。")
    
    # 发送一个普通信息日志
    logger.info("这是一条普通的信息日志")
    
    print(f"总共捕获了 {len(test_logs)} 条日志记录\n")
    
    # 分析捕获的日志
    signal_blocks = []
    execute_decisions = []
    
    for i, log_entry in enumerate(test_logs):
        print(f"日志 {i+1}:")
        # 清理emoji字符以便在Windows控制台显示
        clean_log = log_entry.replace('🚨', '[ALERT]').replace('🎯', '[TARGET]')
        print(f"  长度: {len(log_entry)} 字符")
        print(f"  内容预览: {clean_log[:100]}...")
        
        # 检查是否包含交易信号
        if "NEW TRADE SIGNAL" in log_entry:
            signal_blocks.append(log_entry)
            print("  >>> 识别为：交易信号详情")
        elif "决策: EXECUTE_" in log_entry:
            execute_decisions.append(log_entry)
            print("  >>> 识别为：执行决策")
        else:
            print("  >>> 识别为：普通日志")
        print()
    
    print("=== 分析结果 ===")
    print(f"找到 {len(signal_blocks)} 个详细交易信号")
    print(f"找到 {len(execute_decisions)} 个执行决策")
    
    if signal_blocks:
        print("\n详细交易信号内容分析:")
        for i, signal in enumerate(signal_blocks):
            print(f"信号 {i+1}:")
            
            # 测试信息提取（模拟app.py中的逻辑）
            lines = signal.split('\n')
            extracted_info = {}
            
            for line in lines:
                if "交易对:" in line:
                    extracted_info['symbol'] = line.split("交易对:")[1].strip() if "交易对:" in line else ""
                elif "方向:" in line:
                    extracted_info['direction'] = line.split("方向:")[1].strip() if "方向:" in line else ""
                elif "入场价格:" in line:
                    extracted_info['entry_price'] = line.split("入场价格:")[1].strip() if "入场价格:" in line else ""
                elif "持仓量:" in line:
                    extracted_info['position_size'] = line.split("持仓量:")[1].strip() if "持仓量:" in line else ""
                elif "止损价格:" in line:
                    extracted_info['stop_loss'] = line.split("止损价格:")[1].strip() if "止损价格:" in line else ""
            
            print("  提取的关键信息:")
            for key, value in extracted_info.items():
                print(f"    {key}: {value}")
    
    if execute_decisions:
        print(f"\n执行决策:")
        for i, decision in enumerate(execute_decisions):
            print(f"  决策 {i+1}: {decision.strip()}")
    
    print("\n=== 测试完成 ===")
    return len(signal_blocks) > 0 and len(execute_decisions) > 0

if __name__ == "__main__":
    success = test_log_capture()
    if success:
        print("✅ 日志捕获功能测试通过")
    else:
        print("❌ 日志捕获功能测试失败")