#!/usr/bin/env python3
"""
主程序入口点
统一的程序启动入口，支持多种运行模式
"""

import sys
import argparse
import logging
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from application import MainTrader, PositionMonitor
from infrastructure.logging import setup_enhanced_logging
from infrastructure.notification import DingTalkNotifier
from utils.helpers import create_log_safe_json


def setup_notification_callback() -> callable:
    """设置通知回调函数"""
    try:
        # 从配置中加载钉钉通知设置
        from config.settings import load_app_config
        config = load_app_config()
        
        if hasattr(config, 'dingtalk_webhook') and config.dingtalk_webhook:
            notifier = DingTalkNotifier(
                webhook_url=config.dingtalk_webhook,
                secret=getattr(config, 'dingtalk_secret', None)
            )
            
            def notification_callback(signal_data):
                """处理交易信号通知"""
                try:
                    # 从日志数据中提取信号信息
                    extracted = signal_data.get('extracted_data', {})
                    
                    if extracted:
                        notifier.send_trading_signal(extracted)
                    else:
                        # 如果无法解析结构化数据，记录原始消息
                        logging.getLogger("NotificationCallback").warning(
                            f"无法解析信号数据，跳过通知: {signal_data.get('raw_message', '')[:100]}..."
                        )
                        
                except Exception as e:
                    logging.getLogger("NotificationCallback").error(
                        f"发送通知失败: {e}", exc_info=True
                    )
            
            return notification_callback
        else:
            logging.getLogger("Setup").warning("未配置钉钉通知，将跳过通知功能")
            return None
            
    except Exception as e:
        logging.getLogger("Setup").error(f"设置通知回调失败: {e}", exc_info=True)
        return None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='加密货币交易系统',
        epilog='示例: python main.py (默认both模式) | python main.py trader --log-level DEBUG',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
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
    parser.add_argument(
        '--log-dir',
        default='logs',
        help='日志目录 (默认: logs)'
    )
    parser.add_argument(
        '--structured-logs',
        action='store_true',
        help='启用结构化日志输出'
    )
    parser.add_argument(
        '--no-notifications',
        action='store_true',
        help='禁用通知功能'
    )
    
    args = parser.parse_args()
    
    try:
        # 设置通知回调
        notification_callback = None
        if not args.no_notifications:
            notification_callback = setup_notification_callback()
        
        # 设置日志系统
        log_config = setup_enhanced_logging(
            log_level=args.log_level,
            log_dir=args.log_dir,
            enable_structured_logging=args.structured_logs,
            signal_callback=notification_callback
        )
        
        logger = logging.getLogger("Main")
        logger.info(f"🚀 启动交易系统 - 模式: {args.mode}")
        logger.info(f"📋 配置信息: {create_log_safe_json(log_config)}")
        
        # 根据模式启动相应的应用
        if args.mode == 'trader':
            run_trader_only(args, logger)
        elif args.mode == 'monitor':
            run_monitor_only(args, logger)
        elif args.mode == 'both':
            run_both_applications(args, logger)
        
    except KeyboardInterrupt:
        logger.info("收到停止信号，程序退出")
        return 0
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        return 1
    
    return 0


def run_trader_only(args, logger):
    """只运行交易程序"""
    logger.info("启动主交易程序...")
    trader = MainTrader(args.config)
    trader.run()


def run_monitor_only(args, logger):
    """只运行持仓监控"""
    logger.info("启动持仓监控程序...")
    monitor = PositionMonitor(args.config)
    monitor.run()


def run_both_applications(args, logger):
    """同时运行两个应用程序"""
    import threading
    import time
    
    logger.info("启动双应用模式...")
    
    # 创建应用实例
    trader = MainTrader(args.config)
    monitor = PositionMonitor(args.config)
    
    # 创建线程
    trader_thread = threading.Thread(
        target=trader.run,
        name="MainTrader",
        daemon=False
    )
    
    monitor_thread = threading.Thread(
        target=monitor.run,
        name="PositionMonitor", 
        daemon=False
    )
    
    # 启动线程
    logger.info("启动主交易线程...")
    trader_thread.start()
    
    time.sleep(2)  # 稍微延迟启动监控线程
    
    logger.info("启动持仓监控线程...")
    monitor_thread.start()
    
    try:
        # 等待线程完成
        trader_thread.join()
        monitor_thread.join()
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭所有线程...")
        
        # 停止应用
        trader.stop()
        monitor.stop()
        
        # 等待线程完成
        trader_thread.join(timeout=10)
        monitor_thread.join(timeout=10)
        
        logger.info("所有线程已关闭")


def check_dependencies():
    """检查依赖项"""
    required_modules = [
        'pandas', 'pandas_ta', 'ccxt', 'requests', 'numpy'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺少必要的依赖项: {', '.join(missing_modules)}")
        print("请运行: pip install pandas pandas-ta ccxt requests numpy")
        return False
    
    return True


def show_system_info():
    """显示系统信息"""
    import sys
    import platform
    
    print("📊 系统信息:")
    print(f"  Python版本: {sys.version}")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  架构: {platform.machine()}")
    print(f"  项目路径: {project_root}")


if __name__ == "__main__":
    # 显示系统信息
    show_system_info()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 运行主程序
    exit_code = main()
    sys.exit(exit_code)