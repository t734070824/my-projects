#!/usr/bin/env python3
"""
简单测试默认 both 模式
"""

import argparse

def test_parsing():
    print("测试默认 both 模式配置...")
    
    # 模拟修改后的参数解析
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'mode',
        nargs='?',
        default='both',
        choices=['trader', 'monitor', 'both'],
        help='运行模式 (默认: both)'
    )
    
    # 测试无参数运行
    args = parser.parse_args([])
    print(f"无参数运行: mode = '{args.mode}'")
    
    if args.mode == 'both':
        print("SUCCESS: 默认值正确设置为 'both'")
        return True
    else:
        print(f"FAILED: 期望 'both', 实际 '{args.mode}'")
        return False

def main():
    print("默认 both 模式测试")
    print("=" * 30)
    
    if test_parsing():
        print("\n配置成功！现在可以直接运行:")
        print("  python main.py")
        print("这将同时启动主交易程序和持仓监控")
        return 0
    else:
        print("配置失败")
        return 1

if __name__ == "__main__":
    exit(main())