#!/usr/bin/env python3
"""
测试钉钉通知功能
模拟交易信号并测试通知发送
"""

import sys
import logging
from dingtalk_notifier import send_dingtalk_markdown

# 添加当前目录到Python路径
sys.path.insert(0, '.')

def test_simple_notification():
    """测试简单通知"""
    print("测试简单通知...")
    
    title = "🚨 测试信号"
    content = """### **🚨 交易信号: DOT/USDT** `2025-08-05 17:17`

**策略类型**: 趋势跟踪策略
**交易方向**: SHORT
**入场价格**: 3.6220 USDT

**仓位信息**:
- 持仓量: 43.1263 DOT
- 止损价: 3.8099 USDT
- 最大亏损: -8.10 USDT

**目标价位**:
- 目标1: 3.2462 USDT → +16.21 USDT
- 目标2: 3.0584 USDT → +24.31 USDT

⚠️ **操作提醒**: 严格执行止损，建议分批止盈
"""
    
    send_dingtalk_markdown(title, content)
    print("简单通知发送完成")

def test_signal_processing():
    """测试信号处理逻辑"""
    print("测试信号处理逻辑...")
    
    # 模拟从日志中捕获的交易信号详情
    mock_detail = """
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
    """
    
    # 测试信息提取
    lines = mock_detail.split('\n')
    symbol = ""
    direction = ""
    entry_price = ""
    position_size = ""
    stop_loss = ""
    target1 = ""
    target2 = ""
    max_loss = ""
    
    for line in lines:
        if "交易对:" in line:
            symbol = line.split("交易对:")[1].strip()
        elif "方向:" in line:
            direction = line.split("方向:")[1].strip()
        elif "入场价格:" in line:
            entry_price = line.split("入场价格:")[1].strip()
        elif "持仓量:" in line:
            position_size = line.split("持仓量:")[1].strip()
        elif "止损价格:" in line:
            stop_loss = line.split("止损价格:")[1].strip()
        elif "目标1" in line and "R):" in line:
            target1 = line.split("R):")[1].strip()
        elif "目标2" in line and "R):" in line:
            target2 = line.split("R):")[1].strip()
        elif "最大亏损:" in line:
            max_loss = line.split("最大亏损:")[1].strip()
    
    print(f"提取的信息:")
    print(f"  交易对: {symbol}")
    print(f"  方向: {direction}")
    print(f"  入场价格: {entry_price}")
    print(f"  持仓量: {position_size}")
    print(f"  止损价: {stop_loss}")
    print(f"  目标1: {target1}")
    print(f"  目标2: {target2}")
    print(f"  最大亏损: {max_loss}")
    
    # 判断策略类型
    is_reversal = "REVERSAL TRADE SIGNAL" in mock_detail
    strategy_type = "激进反转策略" if is_reversal else "趋势跟踪策略"
    strategy_emoji = "🔥" if is_reversal else "🚨"
    
    print(f"  策略类型: {strategy_type}")
    print(f"  是否反转策略: {is_reversal}")
    
    # 生成通知内容
    signal_title = f"{strategy_emoji} {symbol} {direction}"
    markdown_text = f"""### **{strategy_emoji} 交易信号: {symbol}** `2025-08-05 17:17`

**策略类型**: {strategy_type}
**交易方向**: {direction}
**入场价格**: {entry_price}
**决策原因**: [DOT/USDT] 1d, 4h趋势看空，且1h出现卖出信号。

**仓位信息**:
- 持仓量: {position_size}
- 持仓价值: 156.20 USDT
- 止损价: {stop_loss}
- 最大亏损: {max_loss}

**技术指标**:
- ATR周期: 4h
- ATR时长: 20期
- ATR数值: 0.1879
- 止损倍数: 2.2x ATR

**目标价位**:
- 目标1: {target1}
- 目标2: {target2}

⚠️ **操作提醒**: 严格执行止损，建议分批止盈
"""
    
    # 移除emoji字符以避免Windows控制台编码问题
    clean_title = signal_title.replace('🚨', '[ALERT]').replace('🔥', '[FIRE]')
    print(f"\n生成的通知标题（已清理emoji）: {clean_title}")
    print(f"通知内容长度: {len(markdown_text)} 字符")
    
    # 发送通知
    send_dingtalk_markdown(signal_title, markdown_text)
    print("处理后的通知发送完成")

def main():
    """主测试函数"""
    print("=== 钉钉通知功能测试 ===")
    
    try:
        # 测试1: 简单通知
        test_simple_notification()
        print()
        
        # 测试2: 信号处理逻辑
        test_signal_processing()
        print()
        
        print("=== 测试完成 ===")
        print("请检查钉钉群是否收到了测试消息")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()