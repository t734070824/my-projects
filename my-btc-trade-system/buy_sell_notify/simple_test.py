#!/usr/bin/env python3
"""
简单功能测试
"""

import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("开始基本功能测试...")
    
    tests_passed = 0
    total_tests = 6
    
    # 测试1: 工具模块
    try:
        from utils.constants import TradingSignal, TradingAction
        from utils.helpers import safe_float_conversion
        print("[1/6] 工具模块导入 - 成功")
        tests_passed += 1
    except Exception as e:
        print(f"[1/6] 工具模块导入 - 失败: {e}")
    
    # 测试2: 配置模块
    try:
        from config.settings import load_app_config
        config = load_app_config()
        print(f"[2/6] 配置模块加载 - 成功 (分析间隔: {config.analysis_interval}秒)")
        tests_passed += 1
    except Exception as e:
        print(f"[2/6] 配置模块加载 - 失败: {e}")
    
    # 测试3: 策略基类
    try:
        from core.strategy.base import TradingStrategy, StrategyResult
        from utils.constants import TradingAction
        result = StrategyResult(TradingAction.EXECUTE_LONG, 0.85, "测试")
        print(f"[3/6] 策略基类功能 - 成功 (结果: {result.action.value})")
        tests_passed += 1
    except Exception as e:
        print(f"[3/6] 策略基类功能 - 失败: {e}")
    
    # 测试4: 通知模块
    try:
        from infrastructure.notification.dingtalk import DingTalkNotifier
        notifier = DingTalkNotifier("https://test.com", "secret")
        print("[4/6] 通知模块创建 - 成功")
        tests_passed += 1
    except Exception as e:
        print(f"[4/6] 通知模块创建 - 失败: {e}")
    
    # 测试5: 日志模块
    try:
        from infrastructure.logging import setup_enhanced_logging
        print("[5/6] 日志模块导入 - 成功")
        tests_passed += 1
    except Exception as e:
        print(f"[5/6] 日志模块导入 - 失败: {e}")
    
    # 测试6: 辅助函数
    try:
        from utils.helpers import safe_float_conversion, create_log_safe_json
        
        # 测试数据转换
        assert safe_float_conversion("123.45") == 123.45
        assert safe_float_conversion("invalid") == 0.0
        
        # 测试JSON生成
        data = {"test": "data", "value": 123}
        json_str = create_log_safe_json(data)
        assert "test" in json_str
        
        print("[6/6] 辅助函数功能 - 成功")
        tests_passed += 1
    except Exception as e:
        print(f"[6/6] 辅助函数功能 - 失败: {e}")
    
    print(f"\n测试结果: {tests_passed}/{total_tests} 通过")
    
    if tests_passed == total_tests:
        print("所有基本功能测试通过！")
        print("注意: 完整功能需要安装外部依赖 (ccxt, pandas, pandas-ta)")
        return 0
    else:
        print("部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())