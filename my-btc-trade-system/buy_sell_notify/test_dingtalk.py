#!/usr/bin/env python3
"""
钉钉通知测试脚本
用于测试消息大小限制和格式化
"""

from dingtalk_notifier import send_dingtalk_markdown

def test_message_size():
    """测试不同大小的消息"""
    
    # 测试1: 正常大小的消息
    print("测试1: 发送正常大小的消息")
    normal_msg = """### **🚨 测试信号: BTC/USDT**

**策略类型**: 趋势跟踪策略
**交易方向**: LONG
**入场价格**: 95,123.45 USDT

**仓位信息**:
- 持仓量: 0.0526 BTC
- 止损价: 93,456.78 USDT
- 最大亏损: -250.00 USDT

**目标价位**:
- 目标1: 98,789.12 USDT → +500.00 USDT
- 目标2: 101,234.56 USDT → +750.00 USDT

⚠️ **操作提醒**: 严格执行止损，建议分批止盈
"""
    send_dingtalk_markdown("测试信号", normal_msg)
    
    # 测试2: 过大的消息
    print("\n测试2: 发送过大的消息")
    large_msg = "### **🚨 超大消息测试**\n\n" + "这是一个很长的消息内容。" * 2000
    send_dingtalk_markdown("超大消息测试", large_msg)
    
    print("\n测试完成！请查看钉钉群消息和系统日志。")

if __name__ == "__main__":
    test_message_size()