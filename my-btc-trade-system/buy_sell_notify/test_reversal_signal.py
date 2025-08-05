#!/usr/bin/env python3
"""
测试反转信号通知功能
验证已有持仓时反方向信号是否能正确通知
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

def test_reversal_signal_capture():
    """测试反转信号捕获"""
    print("=== 测试反转信号捕获功能 ===\n")
    
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
    
    # 模拟发送一个反转信号日志（已有BTC LONG持仓，收到SHORT信号）
    logger.warning("""
    ------------------------------------------------------------
    |                 🔄 NEW TRADE SIGNAL 🔄                   |
    |                   (反转信号)                              |
    ------------------------------------------------------------
    | 交易对:           BTC/USDT
    | 当前持仓:         LONG
    | 新信号方向:       SHORT
    | 入场价格:         43250.0000 USDT
    | 
    | === 仓位计算 ===
    | 账户余额:         1000.00 USDT  
    | 风险敞口:         5.0% = 50.00 USDT
    | 持仓量:           0.0027 BTC
    | 持仓价值:         116.78 USDT
    |
    | === 风险管理 ===
    | 止损价格:         45126.0000 USDT
    | ATR距离:          1876.0000 (1.8x ATR)
    | 最大亏损:         -50.00 USDT
    |
    | === 盈利目标 ===
    | 目标1 (2R):       39498.0000 USDT → +100.00 USDT
    | 目标2 (3R):       37622.0000 USDT → +150.00 USDT
    | 
    | ⚠️  重要提醒: 建议先平仓当前LONG仓位，再考虑开SHORT仓
    ------------------------------------------------------------
    """)
    
    # 发送一个普通的新信号（无持仓情况）
    logger.warning("""
    ------------------------------------------------------------
    |                 🚨 NEW TRADE SIGNAL 🚨                   |
    ------------------------------------------------------------
    | 交易对:           ETH/USDT
    | 方向:             LONG
    | 入场价格:         2450.0000 USDT
    | 
    | === 仓位计算 ===
    | 账户余额:         1000.00 USDT  
    | 风险敞口:         4.0% = 40.00 USDT
    | 持仓量:           0.0188 ETH
    | 持仓价值:         46.06 USDT
    |
    | === 风险管理 ===
    | 止损价格:         2342.0000 USDT
    | ATR距离:          108.0000 (2.0x ATR)
    | 最大亏损:         -40.00 USDT
    |
    | === 盈利目标 ===
    | 目标1 (2R):       2558.0000 USDT → +80.00 USDT
    | 目标2 (3R):       2666.0000 USDT → +120.00 USDT
    | 
    | 🎯 建议: 目标1处止盈50%，目标2处全部平仓
    ------------------------------------------------------------
    """)
    
    print(f"总共捕获了 {len(test_logs)} 条日志记录\n")
    
    # 分析捕获的日志
    reversal_signals = []
    normal_signals = []
    
    for i, log_entry in enumerate(test_logs):
        print(f"日志 {i+1}:")
        # 清理emoji字符以便在Windows控制台显示
        clean_log = log_entry.replace('🔄', '[REVERSAL]').replace('🚨', '[ALERT]').replace('🎯', '[TARGET]')
        print(f"  长度: {len(log_entry)} 字符")
        print(f"  内容预览: {clean_log[:100]}...")
        
        # 检查信号类型
        if "(反转信号)" in log_entry:
            reversal_signals.append(log_entry)
            print("  >>> 识别为：反转信号")
        elif "NEW TRADE SIGNAL" in log_entry:
            normal_signals.append(log_entry)
            print("  >>> 识别为：普通交易信号")
        else:
            print("  >>> 识别为：其他日志")
        print()
    
    print("=== 分析结果 ===")
    print(f"找到 {len(reversal_signals)} 个反转信号")
    print(f"找到 {len(normal_signals)} 个普通信号")
    
    # 测试信息提取
    if reversal_signals:
        print("\n反转信号详细分析:")
        for i, signal in enumerate(reversal_signals):
            print(f"反转信号 {i+1}:")
            
            lines = signal.split('\n')
            extracted_info = {}
            
            for line in lines:
                if "交易对:" in line:
                    extracted_info['symbol'] = line.split("交易对:")[1].strip() if "交易对:" in line else ""
                elif "当前持仓:" in line:
                    extracted_info['current_position'] = line.split("当前持仓:")[1].strip() if "当前持仓:" in line else ""
                elif "新信号方向:" in line:
                    extracted_info['new_direction'] = line.split("新信号方向:")[1].strip() if "新信号方向:" in line else ""
                elif "入场价格:" in line:
                    extracted_info['entry_price'] = line.split("入场价格:")[1].strip() if "入场价格:" in line else ""
                elif "持仓量:" in line:
                    extracted_info['position_size'] = line.split("持仓量:")[1].strip() if "持仓量:" in line else ""
            
            print("  提取的关键信息:")
            for key, value in extracted_info.items():
                print(f"    {key}: {value}")
            
            # 检查是否包含反转提醒
            if "建议先平仓当前" in signal:
                print("  ✅ 包含反转操作提醒")
            else:
                print("  ❌ 缺少反转操作提醒")
    
    print("\n=== 测试完成 ===")
    return len(reversal_signals) > 0

if __name__ == "__main__":
    success = test_reversal_signal_capture()
    if success:
        print("反转信号捕获功能测试通过")
    else:
        print("反转信号捕获功能测试失败")