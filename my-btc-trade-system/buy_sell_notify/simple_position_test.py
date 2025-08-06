#!/usr/bin/env python3
"""
简单测试仓位计算修复
"""

import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("仓位计算修复验证测试")
    print("=" * 40)
    
    try:
        from core.risk.position_calculator import PositionCalculator
        from utils.constants import TradingAction
        
        calculator = PositionCalculator()
        print("成功导入仓位计算器")
        
        # 测试你提到的BTC/USDT SHORT案例
        print("\n测试BTC/USDT SHORT案例...")
        result = calculator.calculate_position_details(
            symbol='BTC/USDT',
            action=TradingAction.EXECUTE_SHORT.value,
            current_price=114114.8000,
            atr_info={
                'atr': 4930.0529,
                'timeframe': '1d',
                'length': 14
            },
            risk_config={
                'atr_multiplier_for_sl': 1.8,  # 关键参数！
                'risk_per_trade_percent': 2.5
            },
            account_balance=10000.0
        )
        
        if result.get('calculation_valid'):
            print("计算结果:")
            print(f"  入场价格: {result['current_price']:,.4f} USDT")
            print(f"  ATR数值: {result['atr_value']:,.4f}")  
            print(f"  ATR倍数: {result['atr_multiplier']}x")
            print(f"  止损距离: {result['stop_loss_distance']:,.4f} USDT")
            print(f"  止损价格: {result['stop_loss_price']:,.4f} USDT")
            
            # 手工验证
            expected_distance = 4930.0529 * 1.8  # 8874.09522
            expected_stop_loss = 114114.8 + expected_distance  # 122988.89522
            
            print(f"\n验证:")
            print(f"  期望止损距离: {expected_distance:.4f} USDT")
            print(f"  期望止损价格: {expected_stop_loss:.4f} USDT")
            
            distance_diff = abs(result['stop_loss_distance'] - expected_distance)
            price_diff = abs(result['stop_loss_price'] - expected_stop_loss)
            
            print(f"  距离误差: {distance_diff:.6f}")
            print(f"  价格误差: {price_diff:.6f}")
            
            if distance_diff < 0.01 and price_diff < 0.01:
                print("\n[SUCCESS] BUG已修复！计算正确")
                print("- 止损距离 = 1.8 × ATR ✓")
                print("- 止损价格计算正确 ✓")
                return 0
            else:
                print("\n[FAILED] 计算仍有问题")
                return 1
        else:
            print(f"[ERROR] 计算失败: {result.get('error', '未知错误')}")
            return 1
            
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())