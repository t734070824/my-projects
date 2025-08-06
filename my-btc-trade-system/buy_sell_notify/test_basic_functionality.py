#!/usr/bin/env python3
"""
基本功能测试脚本
测试重构后的模块是否能正确加载和运行基本功能
"""

import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """测试基本模块导入"""
    print("[检查] 测试基本模块导入...")
    
    try:
        # 测试工具模块
        from utils.constants import TradingSignal, TradingAction, StrategyType
        from utils.helpers import safe_float_conversion, create_log_safe_json
        print("[成功] Utils 模块导入成功")
        
        # 测试配置模块
        from config.settings import TradingPairConfig, AppConfig, load_app_config
        print("[成功] Config 模块导入成功")
        
        # 测试不依赖外部库的核心模块
        from core.strategy.base import TradingStrategy, StrategyResult
        print("[成功] Strategy 基类模块导入成功")
        
        return True
        
    except Exception as e:
        print(f"[失败] 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n🔍 测试配置加载...")
    
    try:
        from config.settings import load_app_config
        
        config = load_app_config()
        
        # 检查基本配置属性
        assert hasattr(config, 'analysis_interval'), "缺少 analysis_interval 属性"
        assert hasattr(config, 'strategy_config'), "缺少 strategy_config 属性"
        assert hasattr(config, 'dingtalk_webhook'), "缺少 dingtalk_webhook 属性"
        
        print(f"✅ 配置加载成功")
        print(f"   - 分析间隔: {config.analysis_interval}秒")
        print(f"   - 策略配置: {len(config.strategy_config)}个策略")
        print(f"   - 监控交易对: {len(config.symbols_to_analyze)}个")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_constants_and_helpers():
    """测试常量和辅助函数"""
    print("\n🔍 测试常量和辅助函数...")
    
    try:
        from utils.constants import TradingSignal, TradingAction
        from utils.helpers import safe_float_conversion, create_log_safe_json
        
        # 测试枚举
        assert TradingSignal.STRONG_BUY.value == "STRONG_BUY"
        assert TradingAction.EXECUTE_LONG.value == "EXECUTE_LONG"
        
        # 测试安全转换
        assert safe_float_conversion("123.45") == 123.45
        assert safe_float_conversion("invalid") == 0.0
        assert safe_float_conversion(None) == 0.0
        
        # 测试JSON创建
        test_data = {"symbol": "BTC/USDT", "price": 45000.0}
        json_result = create_log_safe_json(test_data)
        assert "BTC/USDT" in json_result
        
        print("✅ 常量和辅助函数测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 常量和辅助函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_base_class():
    """测试策略基类"""
    print("\n🔍 测试策略基类...")
    
    try:
        from core.strategy.base import TradingStrategy, StrategyResult
        from utils.constants import TradingAction, StrategyType
        
        # 创建策略结果实例
        result = StrategyResult(
            TradingAction.EXECUTE_LONG,
            0.85,
            "测试原因",
            {"test": "metadata"}
        )
        
        assert result.action == TradingAction.EXECUTE_LONG
        assert result.confidence == 0.85
        assert result.reason == "测试原因"
        
        # 测试转换为字典
        result_dict = result.to_dict()
        assert result_dict['action'] == "EXECUTE_LONG"
        assert result_dict['confidence'] == 0.85
        
        print("✅ 策略基类测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 策略基类测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notification_basic():
    """测试通知模块基本功能（不实际发送）"""
    print("\n🔍 测试通知模块基本功能...")
    
    try:
        from infrastructure.notification.dingtalk import DingTalkNotifier
        
        # 创建通知器实例（使用测试URL）
        notifier = DingTalkNotifier(
            webhook_url="https://test.example.com/webhook",
            secret="test_secret"
        )
        
        # 测试消息构建功能
        signal_data = {
            'symbol': 'BTC/USDT',
            'action': 'EXECUTE_LONG',
            'confidence': 0.85,
            'reason': '趋势向好',
            'timestamp': '2024-01-01 12:00:00'
        }
        
        message = notifier._build_trading_signal_message(signal_data)
        
        assert "BTC/USDT" in message
        assert "EXECUTE_LONG" in message
        assert "85.0%" in message
        
        print("✅ 通知模块基本功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 通知模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logging_setup():
    """测试日志系统设置"""
    print("\n🔍 测试日志系统设置...")
    
    try:
        from infrastructure.logging import setup_enhanced_logging
        
        # 测试日志设置（不启用信号回调）
        log_config = setup_enhanced_logging(
            log_level="INFO",
            log_dir="test_logs",
            enable_structured_logging=False,
            signal_callback=None
        )
        
        assert log_config['log_level'] == "INFO"
        assert log_config['log_dir'] == "test_logs"
        assert not log_config['structured_logging']
        
        print("✅ 日志系统设置测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 日志系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有基本功能测试"""
    print("🚀 开始基本功能测试\n")
    
    tests = [
        test_basic_imports,
        test_config_loading,
        test_constants_and_helpers,
        test_strategy_base_class,
        test_notification_basic,
        test_logging_setup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有基本功能测试通过！")
        print("📝 注意: 完整功能需要安装 ccxt、pandas、pandas-ta 等依赖")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())