#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试盈亏记录功能
"""

import time
import json
from main import record_pnl, get_pnl_statistics, print_pnl_statistics, format_pnl_chart, generate_pnl_chart_data

def test_pnl_record():
    """测试盈亏记录功能"""
    print("=== 测试盈亏记录功能 ===")
    
    # 模拟账户信息
    test_account_info = {
        'totalUnrealizedProfit': '123.45',
        'totalWalletBalance': '1000.00'
    }
    
    print("1. 记录测试盈亏数据...")
    for i in range(10):
        # 模拟不同的盈亏值
        pnl = 100 + i * 10 + (i % 3 - 1) * 5  # 波动盈亏
        test_account_info['totalUnrealizedProfit'] = str(pnl)
        
        record_pnl(test_account_info)
        print(f"   记录 {i+1}: {pnl:.2f}U")
        time.sleep(0.1)  # 短暂延迟
    
    print("\n2. 获取盈亏统计...")
    stats = get_pnl_statistics()
    print(f"   当前盈亏: {stats['current_pnl']:.2f}U")
    print(f"   最高盈亏: {stats['max_pnl']:.2f}U ({stats['max_pnl_time']})")
    print(f"   最低盈亏: {stats['min_pnl']:.2f}U ({stats['min_pnl_time']})")
    print(f"   记录数量: {stats['total_records']}条")
    
    print("\n3. 显示盈亏统计...")
    print_pnl_statistics()
    
    print("\n4. 生成图表数据...")
    chart_data = generate_pnl_chart_data()
    print(f"   图表数据点: {len(chart_data)}个")
    
    print("\n5. 格式化图表...")
    chart_text = format_pnl_chart(chart_data)
    print(chart_text)
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_pnl_record() 