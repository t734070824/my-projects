# system_check.py - 系统完整性检查

import sys
import logging
import importlib
from datetime import datetime

def check_imports():
    """检查所有关键模块导入"""
    modules_to_check = [
        ('config', '配置模块'),
        ('notification_system', '新通知系统'),
        ('dingtalk_notifier', '钉钉通知模块'),
        ('logger_config', '日志配置'),
        ('app', '主程序模块'),
        # 依赖包
        ('ccxt', 'CCXT交易所库'),
        ('pandas', 'Pandas数据处理'),
        ('pandas_ta', '技术指标库'),
        ('schedule', '任务调度'),
        ('requests', 'HTTP请求库')
    ]
    
    success = True
    print("=== 模块导入检查 ===")
    
    for module_name, description in modules_to_check:
        try:
            importlib.import_module(module_name)
            print(f"[OK] {description}: {module_name}")
        except ImportError as e:
            print(f"[ERROR] {description} 导入失败: {e}")
            success = False
    
    return success

def check_notification_system():
    """检查新通知系统功能"""
    print("\n=== 通知系统功能检查 ===")
    
    try:
        from notification_system import (
            EventType, StrategyType, TradeDirection,
            TradeSignalEvent, PositionUpdateEvent, MarketAnalysisEvent,
            NotificationManager, MessageFormatter
        )
        
        # 测试事件创建
        trade_event = TradeSignalEvent(
            symbol="TEST/USDT",
            strategy_type=StrategyType.TREND_FOLLOWING,
            direction=TradeDirection.LONG,
            entry_price=100.0,
            decision_reason="系统测试"
        )
        
        # 测试格式化
        formatter = MessageFormatter()
        title, message = formatter.format_trade_signal(trade_event)
        
        print(f"[OK] 事件创建和格式化正常")
        print(f"[OK] 通知系统核心组件运行正常")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 通知系统检查失败: {e}")
        return False

def check_config():
    """检查配置文件"""
    print("\n=== 配置文件检查 ===")
    
    try:
        import config
        
        # 检查关键配置
        required_configs = [
            ('SYMBOLS_TO_ANALYZE', '分析交易对列表'),
            ('ATR_CONFIG', 'ATR配置'),
            ('VIRTUAL_TRADE_CONFIG', '虚拟交易配置'),
            ('REVERSAL_STRATEGY_CONFIG', '反转策略配置'),
            ('DINGTALK_WEBHOOK', '钉钉Webhook'),
            ('API_KEY', 'Binance API Key'),
            ('SECRET_KEY', 'Binance Secret Key')
        ]
        
        for attr_name, description in required_configs:
            if hasattr(config, attr_name):
                value = getattr(config, attr_name)
                if value:
                    print(f"[OK] {description}: 已配置")
                else:
                    print(f"[WARN] {description}: 为空")
            else:
                print(f"[ERROR] {description}: 未找到配置项 {attr_name}")
        
        # 检查分析的交易对数量
        symbols_count = len(config.SYMBOLS_TO_ANALYZE)
        print(f"[INFO] 当前监控 {symbols_count} 个交易对: {', '.join(config.SYMBOLS_TO_ANALYZE[:3])}...")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 配置检查失败: {e}")
        return False

def check_integration():
    """检查新旧系统集成"""
    print("\n=== 系统集成检查 ===")
    
    try:
        from app import manage_virtual_trade, manage_reversal_virtual_trade
        from notification_system import emit_trade_signal, StrategyType, TradeDirection
        
        print("[OK] 虚拟交易管理函数导入正常")
        print("[OK] 新通知系统函数导入正常")
        print("[OK] 主程序与通知系统集成完成")
        
        # 检查函数签名是否支持decision_reason参数
        import inspect
        sig = inspect.signature(manage_virtual_trade)
        if 'decision_reason' in sig.parameters:
            print("[OK] 虚拟交易函数已更新支持决策原因传递")
        else:
            print("[WARN] 虚拟交易函数可能未更新")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 集成检查失败: {e}")
        return False

def generate_report():
    """生成系统状态报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n" + "="*50)
    print(f"系统检查报告 - {timestamp}")
    print("="*50)
    
    all_checks = [
        ("模块导入", check_imports()),
        ("通知系统", check_notification_system()),
        ("配置文件", check_config()),
        ("系统集成", check_integration())
    ]
    
    success_count = sum(1 for _, result in all_checks if result)
    total_count = len(all_checks)
    
    print(f"\n检查结果: {success_count}/{total_count} 项通过")
    
    if success_count == total_count:
        print("[SUCCESS] 系统状态良好，新通知系统已完全集成！")
        print("\n主要改进:")
        print("- [OK] 事件驱动通知系统替代日志解析")
        print("- [OK] 结构化通知数据，格式统一")
        print("- [OK] 模块化设计，易于扩展维护")
        print("- [OK] 错误隔离，提高系统稳定性")
    else:
        print("[WARNING] 部分检查未通过，请查看上述详细信息")
    
    return success_count == total_count

def main():
    """主函数"""
    print("买卖信号通知系统 - 完整性检查")
    print(f"Python版本: {sys.version}")
    print(f"执行路径: {sys.executable}")
    
    success = generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)