#!/usr/bin/env python3
"""
测试仓位计算修复
验证止损价格和ATR倍数计算的正确性
"""

import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_position_calculation():
    """测试仓位计算逻辑"""
    print("测试仓位计算修复...")
    
    try:
        from core.risk.position_calculator import PositionCalculator
        from utils.constants import TradingAction
        
        calculator = PositionCalculator()
        
        # 模拟BTC/USDT SHORT信号数据
        test_cases = [
            {
                'name': 'BTC/USDT SHORT (你提到的案例)',
                'symbol': 'BTC/USDT',
                'action': TradingAction.EXECUTE_SHORT.value,
                'current_price': 114114.8000,
                'atr_info': {
                    'atr': 4930.0529,
                    'timeframe': '1d', 
                    'length': 14
                },
                'risk_config': {
                    'atr_multiplier_for_sl': 1.8,  # 应该是1.8倍
                    'risk_per_trade_percent': 2.5
                },
                'account_balance': 10000.0,
                'expected_stop_loss': 114114.8 + (4930.0529 * 1.8)  # 122,988.9 USDT
            },
            {
                'name': 'ETH/USDT LONG',
                'symbol': 'ETH/USDT',
                'action': TradingAction.EXECUTE_LONG.value,
                'current_price': 3500.0,
                'atr_info': {
                    'atr': 100.0,
                    'timeframe': '4h',
                    'length': 20
                },
                'risk_config': {
                    'atr_multiplier_for_sl': 2.0,
                    'risk_per_trade_percent': 2.0
                },
                'account_balance': 5000.0,
                'expected_stop_loss': 3500.0 - (100.0 * 2.0)  # 3300.0 USDT
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[测试案例 {i}] {test_case['name']}")
            print("-" * 50)
            
            result = calculator.calculate_position_details(
                symbol=test_case['symbol'],
                action=test_case['action'], 
                current_price=test_case['current_price'],
                atr_info=test_case['atr_info'],
                risk_config=test_case['risk_config'],
                account_balance=test_case['account_balance']
            )
            
            if result.get('calculation_valid'):
                print(f"[成功] 计算完成")
                print(f"  入场价格: {result['current_price']:,.4f} USDT")
                print(f"  止损价格: {result['stop_loss_price']:,.4f} USDT")
                print(f"  ATR数值: {result['atr_value']:,.4f}")
                print(f"  ATR倍数: {result['atr_multiplier']}x")
                print(f"  止损距离: {result['stop_loss_distance']:,.4f} USDT")
                print(f"  预期止损: {test_case['expected_stop_loss']:,.4f} USDT")
                
                # 验证计算正确性
                expected_distance = test_case['atr_info']['atr'] * test_case['risk_config']['atr_multiplier_for_sl']
                actual_distance = result['stop_loss_distance']
                
                if abs(expected_distance - actual_distance) < 0.01:
                    print(f"  [验证] 止损距离计算正确 ✓")
                else:
                    print(f"  [错误] 止损距离计算错误: 期望={expected_distance:.4f}, 实际={actual_distance:.4f}")
                
                # 验证止损价格
                if test_case['action'] == TradingAction.EXECUTE_SHORT.value:
                    expected_sl = test_case['current_price'] + expected_distance
                else:
                    expected_sl = test_case['current_price'] - expected_distance
                
                if abs(expected_sl - result['stop_loss_price']) < 0.01:
                    print(f"  [验证] 止损价格计算正确 ✓")
                else:
                    print(f"  [错误] 止损价格计算错误: 期望={expected_sl:.4f}, 实际={result['stop_loss_price']:.4f}")
                
                print(f"  仓位大小: {result['position_size_coin']:.6f} {test_case['symbol'].replace('/USDT', '')}")
                print(f"  仓位价值: {result['position_value_usd']:,.2f} USDT")
                print(f"  风险金额: {result['actual_risk_usd']:,.2f} USDT")
                
                # 显示目标价位
                targets = result.get('target_prices', {})
                if targets:
                    print(f"  目标价位:")
                    for key, target in targets.items():
                        print(f"    {key}: {target['price']:,.4f} USDT (+{target['profit_amount']:.2f} USDT)")
                
            else:
                print(f"[失败] 计算失败: {result.get('error', '未知错误')}")
        
        print(f"\n📊 测试完成")
        return True
        
    except Exception as e:
        print(f"[错误] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_original_bug_case():
    """专门测试你提到的BTC/USDT案例"""
    print("\n🔍 专门测试原始bug案例...")
    
    try:
        from core.risk.position_calculator import PositionCalculator
        from utils.constants import TradingAction
        
        calculator = PositionCalculator()
        
        # 你提到的具体数据
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
                'atr_multiplier_for_sl': 1.8,  # 这是关键！
                'risk_per_trade_percent': 2.5
            },
            account_balance=10000.0
        )
        
        print("原始案例验证结果:")
        print(f"  入场价格: {result['current_price']:,.4f} USDT")
        print(f"  ATR数值: {result['atr_value']:,.4f}")  
        print(f"  ATR倍数: {result['atr_multiplier']}x")
        print(f"  止损距离: {result['stop_loss_distance']:,.4f} USDT")
        print(f"  止损价格: {result['stop_loss_price']:,.4f} USDT")
        
        # 手工验证
        manual_distance = 4930.0529 * 1.8  # 8874.09522
        manual_stop_loss = 114114.8 + manual_distance  # 122988.89522
        
        print(f"\n手工计算验证:")
        print(f"  期望止损距离: {manual_distance:.4f} USDT")
        print(f"  期望止损价格: {manual_stop_loss:.4f} USDT")
        
        # 检查是否修复
        distance_correct = abs(result['stop_loss_distance'] - manual_distance) < 0.01
        price_correct = abs(result['stop_loss_price'] - manual_stop_loss) < 0.01
        
        if distance_correct and price_correct:
            print(f"\n✅ BUG已修复！止损计算正确")
            print(f"   - 止损距离: {result['stop_loss_distance']:.4f} = {result['atr_multiplier']}x ATR ✓")
            print(f"   - 止损价格: {result['stop_loss_price']:.4f} ✓")
            return True
        else:
            print(f"\n❌ BUG仍然存在！")
            print(f"   距离错误: {not distance_correct}")
            print(f"   价格错误: {not price_correct}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    print("🧪 仓位计算修复验证测试")
    print("=" * 50)
    
    success_count = 0
    
    # 测试1: 基本功能测试
    if test_position_calculation():
        success_count += 1
    
    # 测试2: 原始bug案例测试
    if test_original_bug_case():
        success_count += 1
    
    print(f"\n🎯 测试结果: {success_count}/2 通过")
    
    if success_count == 2:
        print("🎉 所有测试通过！止损计算bug已修复")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())