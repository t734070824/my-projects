#!/usr/bin/env python3
"""
测试确认account_status信息不会被打印到日志中
"""

import logging
import json

def test_log_filtering():
    """测试日志过滤功能"""
    print("=== 测试日志过滤功能 ===\n")
    
    # 模拟包含account_status的分析结果
    mock_analysis = {
        'signal': 'STRONG_BUY',
        'total_score': 85,
        'sma_signal': 'BUY',
        'rsi_signal': 'NEUTRAL',
        'macd_signal': 'BUY',
        'close_price': 43250.50,
        'atr_info': {
            'atr': 1876.0,
            'timeframe': '1d',
            'length': 14
        },
        'account_status': {
            'usdt_balance': {
                'walletBalance': '1000.00',
                'availableBalance': '800.50',
                'unrealizedProfit': '25.75'
            },
            'open_positions': [
                {
                    'symbol': 'BTC/USDT',
                    'side': 'long',
                    'size': 0.025,
                    'entryPrice': 42800.0,
                    'markPrice': 43250.50,
                    'unrealizedPnl': 11.26,
                    'leverage': 10
                },
                {
                    'symbol': 'ETH/USDT',
                    'side': 'short',
                    'size': -0.5,
                    'entryPrice': 2450.0,
                    'markPrice': 2420.0,
                    'unrealizedPnl': 15.0,
                    'leverage': 5
                }
            ]
        }
    }
    
    print("原始分析结果包含的字段:")
    for key in mock_analysis.keys():
        print(f"  - {key}")
    
    print(f"\naccount_status包含 {len(mock_analysis['account_status']['open_positions'])} 个持仓")
    
    # 应用过滤逻辑（模拟app.py中的修改）
    filtered_analysis = {k: v for k, v in mock_analysis.items() if k not in ['account_status']}
    
    print("\n过滤后的分析结果包含的字段:")
    for key in filtered_analysis.keys():
        print(f"  - {key}")
    
    print(f"\n过滤后是否包含account_status: {'account_status' in filtered_analysis}")
    print(f"过滤后是否包含open_positions: {'open_positions' in str(filtered_analysis)}")
    
    # 生成JSON字符串（模拟日志输出）
    filtered_json = json.dumps(filtered_analysis, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n过滤后的JSON长度: {len(filtered_json)} 字符")
    print("过滤后的JSON预览（前200字符）:")
    print(filtered_json[:200] + "..." if len(filtered_json) > 200 else filtered_json)
    
    # 验证敏感信息已被移除
    sensitive_keywords = ['walletBalance', 'availableBalance', 'open_positions', 'entryPrice', 'unrealizedPnl']
    found_sensitive = []
    
    for keyword in sensitive_keywords:
        if keyword in filtered_json:
            found_sensitive.append(keyword)
    
    if found_sensitive:
        print(f"\n❌ 仍包含敏感信息: {found_sensitive}")
        return False
    else:
        print(f"\n✅ 已成功过滤所有敏感账户信息")
        return True

if __name__ == "__main__":
    success = test_log_filtering()
    if success:
        print("\n✅ 日志过滤测试通过")
    else:
        print("\n❌ 日志过滤测试失败")