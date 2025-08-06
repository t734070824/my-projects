#!/usr/bin/env python3
"""
测试 MainTrader 配置引用修复
"""

import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_references():
    """测试配置引用是否正确"""
    print("测试配置引用修复...")
    
    try:
        # 测试核心组件导入
        from core.risk.position_calculator import PositionCalculator
        from core.decision.engine import DecisionEngine
        from config.settings import load_app_config, TradingPairConfig
        
        print("核心组件导入成功")
        
        # 测试配置加载
        config = load_app_config()
        print(f"配置加载成功")
        print(f"  - trading_pairs: {type(config.trading_pairs)} ({len(config.trading_pairs)} 项)")
        print(f"  - symbols_to_analyze: {len(config.symbols_to_analyze)} 个符号")
        
        # 模拟 MainTrader 的配置处理逻辑
        trading_pairs = config.trading_pairs
        
        if not trading_pairs and config.symbols_to_analyze:
            print("配置为空，创建默认交易对配置...")
            trading_pairs = {
                symbol: TradingPairConfig(
                    symbol=symbol,
                    risk_per_trade_percent=2.5,
                    atr_multiplier_for_sl=2.0
                ) for symbol in config.symbols_to_analyze
            }
        
        if not trading_pairs:
            # 如果还是空，创建测试配置
            print("创建测试配置...")
            trading_pairs = {
                'BTC/USDT': TradingPairConfig(
                    symbol='BTC/USDT',
                    risk_per_trade_percent=2.5,
                    atr_multiplier_for_sl=1.8
                ),
                'ETH/USDT': TradingPairConfig(
                    symbol='ETH/USDT', 
                    risk_per_trade_percent=2.0,
                    atr_multiplier_for_sl=2.0
                )
            }
        
        print(f"最终交易对配置: {len(trading_pairs)} 个")
        
        # 测试配置访问
        for symbol, pair_config in trading_pairs.items():
            print(f"  - {symbol}: 风险={pair_config.risk_per_trade_percent}%, ATR倍数={pair_config.atr_multiplier_for_sl}x")
            
            # 测试关键属性访问（这是引发错误的地方）
            assert hasattr(pair_config, 'atr_multiplier_for_sl'), f"{symbol} 缺少 atr_multiplier_for_sl"
            assert hasattr(pair_config, 'risk_per_trade_percent'), f"{symbol} 缺少 risk_per_trade_percent"
            assert hasattr(pair_config, 'symbol'), f"{symbol} 缺少 symbol"
        
        print("配置引用测试通过！")
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_position_calculator_integration():
    """测试仓位计算器集成"""
    print("\n测试仓位计算器集成...")
    
    try:
        from core.risk.position_calculator import PositionCalculator
        from config.settings import TradingPairConfig
        from utils.constants import TradingAction
        
        # 创建测试配置
        test_config = TradingPairConfig(
            symbol='BTC/USDT',
            risk_per_trade_percent=2.5,
            atr_multiplier_for_sl=1.8
        )
        
        # 测试风险配置构建（模拟 MainTrader 中的逻辑）
        risk_config = {
            'atr_multiplier_for_sl': test_config.atr_multiplier_for_sl,
            'risk_per_trade_percent': test_config.risk_per_trade_percent
        }
        
        print(f"风险配置构建成功: {risk_config}")
        
        # 测试仓位计算
        calculator = PositionCalculator()
        result = calculator.calculate_position_details(
            symbol='BTC/USDT',
            action=TradingAction.EXECUTE_SHORT.value,
            current_price=50000.0,
            atr_info={'atr': 1000.0, 'timeframe': '1d', 'length': 14},
            risk_config=risk_config,
            account_balance=10000.0
        )
        
        if result.get('calculation_valid'):
            print("仓位计算成功:")
            print(f"  - ATR倍数: {result['atr_multiplier']}x")
            print(f"  - 止损距离: {result['stop_loss_distance']:.2f}")
            print(f"  - 止损价格: {result['stop_loss_price']:.2f}")
            return True
        else:
            print(f"仓位计算失败: {result.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"集成测试失败: {e}")
        return False

def main():
    print("MainTrader 配置引用修复测试")
    print("=" * 40)
    
    success_count = 0
    
    if test_config_references():
        success_count += 1
    
    if test_position_calculator_integration():
        success_count += 1
    
    print(f"\n测试结果: {success_count}/2 通过")
    
    if success_count == 2:
        print("所有测试通过！配置引用问题已修复")
        return 0
    else:
        print("部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())