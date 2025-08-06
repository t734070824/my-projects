#!/usr/bin/env python3
"""
交易系统启动脚本
简化的启动方式，自动处理常见问题
"""

import sys
import os
import subprocess
from pathlib import Path

def check_dependencies():
    """检查必要的依赖项"""
    required_modules = {
        'ccxt': '交易所接口库',
        'pandas': '数据分析库', 
        'pandas_ta': '技术分析库',
        'requests': 'HTTP请求库',
        'numpy': '数值计算库'
    }
    
    missing = []
    for module, desc in required_modules.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(f"  pip install {module}  # {desc}")
    
    if missing:
        print("缺少必要依赖项，请先安装:")
        print("\n".join(missing))
        return False
    
    return True

def check_config():
    """检查配置文件"""
    config_file = Path("config.py")
    if not config_file.exists():
        print("警告: config.py 文件不存在")
        print("请确保配置文件存在并包含必要的设置")
        return False
    return True

def create_log_dir():
    """创建日志目录"""
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(exist_ok=True)
        print(f"已创建日志目录: {log_dir}")

def main():
    print("🚀 交易系统启动器")
    print("=" * 30)
    
    # 检查依赖
    print("检查依赖项...")
    if not check_dependencies():
        print("❌ 依赖检查失败，程序退出")
        return 1
    
    print("✅ 依赖项检查通过")
    
    # 检查配置
    print("检查配置文件...")
    if not check_config():
        print("⚠️ 配置检查失败，但继续运行...")
    else:
        print("✅ 配置文件存在")
    
    # 创建日志目录
    create_log_dir()
    
    # 启动主程序
    print("\n启动交易系统...")
    print("模式: both (主交易程序 + 持仓监控)")
    print("日志级别: INFO")
    print("按 Ctrl+C 停止程序\n")
    
    try:
        # 运行主程序
        result = subprocess.run([
            sys.executable, "main.py", "both", "--log-level", "INFO"
        ], cwd=Path(__file__).parent)
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n\n✋ 程序已停止")
        return 0
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())