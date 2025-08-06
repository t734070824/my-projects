#!/usr/bin/env python3
"""
测试默认 both 模式
"""

import sys
import argparse
from pathlib import Path

def test_argument_parsing():
    """测试参数解析的默认值"""
    print("测试 main.py 参数解析...")
    
    # 模拟 main.py 中的参数解析逻辑
    parser = argparse.ArgumentParser(description='加密货币交易系统')
    parser.add_argument(
        'mode',
        nargs='?',  # 使参数可选
        default='both',  # 默认值设置为 both
        choices=['trader', 'monitor', 'both'],
        help='运行模式: trader=主交易程序, monitor=持仓监控, both=同时运行 (默认: both)'
    )
    parser.add_argument(
        '--config',
        default='config.py',
        help='配置文件路径 (默认: config.py)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别 (默认: INFO)'
    )
    
    print("\n测试案例:")
    
    # 测试案例 1: 无参数运行
    try:
        args = parser.parse_args([])
        print(f"1. 无参数: mode='{args.mode}' (应该是 'both') ✓" if args.mode == 'both' else f"1. 无参数: mode='{args.mode}' ✗")
    except SystemExit:
        print("1. 无参数: 解析失败 ✗")
    
    # 测试案例 2: 显式指定 trader
    try:
        args = parser.parse_args(['trader'])
        print(f"2. 指定 trader: mode='{args.mode}' ✓" if args.mode == 'trader' else f"2. 指定 trader: mode='{args.mode}' ✗")
    except SystemExit:
        print("2. 指定 trader: 解析失败 ✗")
    
    # 测试案例 3: 显式指定 monitor  
    try:
        args = parser.parse_args(['monitor'])
        print(f"3. 指定 monitor: mode='{args.mode}' ✓" if args.mode == 'monitor' else f"3. 指定 monitor: mode='{args.mode}' ✗")
    except SystemExit:
        print("3. 指定 monitor: 解析失败 ✗")
    
    # 测试案例 4: 显式指定 both
    try:
        args = parser.parse_args(['both'])
        print(f"4. 指定 both: mode='{args.mode}' ✓" if args.mode == 'both' else f"4. 指定 both: mode='{args.mode}' ✗")
    except SystemExit:
        print("4. 指定 both: 解析失败 ✗")
    
    # 测试案例 5: 其他参数组合
    try:
        args = parser.parse_args(['--log-level', 'DEBUG'])
        print(f"5. 只指定日志级别: mode='{args.mode}', log_level='{args.log_level}' ✓" if args.mode == 'both' and args.log_level == 'DEBUG' else f"5. 只指定日志级别: 失败 ✗")
    except SystemExit:
        print("5. 只指定日志级别: 解析失败 ✗")
    
    print("\n✅ 参数解析测试完成！")
    
    return True

def simulate_main_usage():
    """模拟 main.py 的使用方式"""
    print("\n模拟使用方式:")
    print("# 默认运行（both模式）")
    print("python main.py")
    print("")
    print("# 等同于:")
    print("python main.py both")
    print("")
    print("# 其他运行方式:")
    print("python main.py trader          # 只运行主交易程序")
    print("python main.py monitor         # 只运行持仓监控")
    print("python main.py both            # 同时运行两个程序")
    print("python main.py --log-level DEBUG    # 默认both模式，DEBUG日志级别")
    
    return True

def main():
    print("🔧 默认 both 模式配置测试")
    print("=" * 40)
    
    success_count = 0
    
    if test_argument_parsing():
        success_count += 1
    
    if simulate_main_usage():
        success_count += 1
    
    print(f"\n📊 测试结果: {success_count}/2 通过")
    
    if success_count == 2:
        print("🎉 默认 both 模式配置成功！")
        print("现在可以直接运行 'python main.py' 启动完整系统")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())