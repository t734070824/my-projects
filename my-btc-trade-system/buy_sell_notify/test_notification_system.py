# test_notification_system.py - 测试新的通知系统

import sys
import logging
from notification_system import (
    emit_trade_signal, emit_position_update, emit_market_analysis,
    StrategyType, TradeDirection
)

# 设置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_trade_signals():
    """测试交易信号通知"""
    print("=== 测试交易信号通知 ===")
    
    # 测试趋势跟踪策略信号
    print("1. 趋势跟踪策略 - BTC 做多信号")
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
    
    # 测试激进反转策略信号
    print("\n2. 激进反转策略 - ETH 做空信号")
    emit_trade_signal(
        symbol="ETH/USDT",
        strategy_type=StrategyType.REVERSAL,
        direction=TradeDirection.SHORT,
        entry_price=3200.0,
        stop_loss_price=3280.0,
        position_size_coin=2.5,
        position_size_usd=8000.0,
        risk_amount_usd=160.0,
        target_price_2r=3120.0,  # 1.5R目标
        target_price_3r=3040.0,  # 2R目标
        atr_value=40.0,
        atr_multiplier=1.5,
        atr_timeframe="1h",
        atr_length=10,
        decision_reason="[ETH/USDT] 激进反转策略 - RSI严重超买且触及布林上轨",
        account_balance=20000.0,
        risk_percent=0.008
    )
    
    # 测试持仓反转信号
    print("\n3. 持仓反转信号 - SOL 平多开空")
    emit_trade_signal(
        symbol="SOL/USDT",
        strategy_type=StrategyType.POSITION_REVERSAL,
        direction=TradeDirection.SHORT,
        entry_price=120.0,
        stop_loss_price=126.0,
        position_size_coin=16.67,
        position_size_usd=2000.0,
        risk_amount_usd=100.0,
        target_price_2r=108.0,
        target_price_3r=102.0,
        atr_value=3.0,
        atr_multiplier=2.0,
        atr_timeframe="4h",
        atr_length=14,
        decision_reason="检测到反转信号 - 当前持仓: LONG, 新信号: SHORT",
        account_balance=20000.0,
        risk_percent=0.005
    )

def test_position_updates():
    """测试仓位更新通知"""
    print("\n=== 测试仓位更新通知 ===")
    
    # 测试高盈利提醒
    print("1. 高盈利提醒 - BTC")
    emit_position_update(
        symbol="BTC/USDT",
        position_side="long",
        entry_price=43000.0,
        current_price=49500.0,
        unrealized_pnl=1300.0,
        pnl_percent=15.1,
        profit_ratio=0.151,
        new_stop_loss=47700.0,
        update_type="high_profit",
        suggestion="考虑止盈50%仓位锁定利润"
    )
    
    # 测试追踪止损更新
    print("\n2. 追踪止损更新 - ETH")
    emit_position_update(
        symbol="ETH/USDT",
        position_side="short",
        entry_price=3500.0,
        current_price=3220.0,
        unrealized_pnl=560.0,
        pnl_percent=8.0,
        profit_ratio=0.08,
        new_stop_loss=3340.0,
        update_type="trailing_stop",
        suggestion="利润保护模式，更新止损"
    )

def test_market_analysis():
    """测试市场分析摘要通知"""
    print("\n=== 测试市场分析摘要通知 ===")
    
    # 测试正常摘要
    print("1. 正常市场分析摘要")
    emit_market_analysis(
        analyzed_symbols_count=12,
        signals_count=0,
        alerts_count=0,
        errors_count=0,
        analysis_summary={
            "trend_bullish": 6,
            "trend_bearish": 3,
            "trend_neutral": 3
        }
    )
    
    # 测试有信号和警告的摘要
    print("\n2. 有信号和警告的摘要")
    emit_market_analysis(
        analyzed_symbols_count=12,
        signals_count=2,
        alerts_count=1,
        errors_count=0,
        analysis_summary={
            "trend_bullish": 7,
            "trend_bearish": 2,
            "trend_neutral": 3
        }
    )

def main():
    """运行所有测试"""
    print("开始测试新的通知系统...")
    print("注意：这些测试会向钉钉发送真实通知！")
    
    response = input("确认继续测试？(y/N): ").strip().lower()
    if response != 'y':
        print("测试已取消")
        return
    
    try:
        test_trade_signals()
        
        # 等待一下再发送下一批
        input("\n按回车键继续测试仓位更新通知...")
        test_position_updates()
        
        # 等待一下再发送下一批
        input("\n按回车键继续测试市场分析摘要...")
        test_market_analysis()
        
        print("\n✅ 所有测试完成!")
        print("\n新通知系统的优势:")
        print("1. ✨ 结构化数据：通知内容基于结构化事件，不再依赖日志解析")
        print("2. 🔧 易于扩展：新增通知类型只需定义新事件类")
        print("3. 📱 多渠道支持：可轻松添加邮件、微信、Webhook等通知渠道")
        print("4. 🎨 模板化：消息格式统一，支持不同渠道的格式适配")
        print("5. 🐛 错误隔离：通知系统独立，不影响主业务逻辑")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()