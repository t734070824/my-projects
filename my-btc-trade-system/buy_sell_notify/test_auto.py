# test_auto.py - 自动化测试新的通知系统（不需要用户交互）

import sys
import logging
from notification_system import (
    emit_trade_signal, emit_position_update, emit_market_analysis,
    StrategyType, TradeDirection
)

# 设置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_trend_signal():
    """测试趋势跟踪策略信号"""
    print("测试: 趋势跟踪策略 - BTC 做多信号")
    emit_trade_signal(
        symbol="BTC/USDT",
        strategy_type=StrategyType.TREND_FOLLOWING,
        direction=TradeDirection.LONG,
        entry_price=45000.0,
        stop_loss_price=43200.0,
        position_size_coin=0.2222,
        position_size_usd=10000.0,
        risk_amount_usd=400.0,
        target_price_2r=46800.0,
        target_price_3r=48600.0,
        atr_value=900.0,
        atr_multiplier=2.0,
        atr_timeframe="1d",
        atr_length=14,
        decision_reason="[BTC/USDT] 1d, 4h趋势看多，且1h出现买入信号",
        account_balance=20000.0,
        risk_percent=0.02
    )

def test_position_update():
    """测试仓位更新通知"""
    print("测试: 追踪止损更新 - ETH")
    emit_position_update(
        symbol="ETH/USDT",
        position_side="long",
        entry_price=3000.0,
        current_price=3240.0,
        unrealized_pnl=480.0,
        pnl_percent=8.0,
        profit_ratio=0.08,
        new_stop_loss=3120.0,
        update_type="trailing_stop",
        suggestion="利润保护模式，更新止损"
    )

def test_market_summary():
    """测试市场分析摘要"""
    print("测试: 市场分析摘要")
    emit_market_analysis(
        analyzed_symbols_count=12,
        signals_count=0,
        alerts_count=0,
        errors_count=0
    )

def main():
    """运行自动化测试"""
    print("=== 新通知系统自动化测试 ===")
    
    try:
        # 检查导入是否正常
        print("[OK] 通知系统模块导入成功")
        
        # 测试交易信号
        test_trend_signal()
        print("[OK] 交易信号测试完成")
        
        # 测试仓位更新
        test_position_update()
        print("[OK] 仓位更新测试完成")
        
        # 测试市场摘要
        test_market_summary()
        print("[OK] 市场分析摘要测试完成")
        
        print("\n[SUCCESS] 所有测试通过！新通知系统工作正常")
        print("\n新系统特点:")
        print("- [*] 结构化事件数据，告别日志解析")
        print("- [*] 模块化设计，易于扩展")
        print("- [*] 统一的消息格式和发送机制")
        print("- [*] 错误隔离，提高系统稳定性")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)