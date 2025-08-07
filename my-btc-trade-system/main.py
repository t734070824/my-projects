import schedule
import time
import matplotlib.pyplot as plt
import os
from typing import Dict, Optional, List
import matplotlib
from datetime import datetime

# 设置matplotlib支持中文
matplotlib.rcParams['font.family'] = ['SimHei', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False # 解决负号显示问题

from config import PNL_RECORD_INTERVAL, ENABLE_DINGTALK_NOTIFICATION
from data_provider import get_account_info, get_positions
from pnl import record_pnl, get_pnl_statistics, load_pnl_history
from alerter import format_pnl_notification, should_send_notification, send_dingtalk_notification

def print_account_info(account_info: Optional[Dict]) -> None:
    """打印账户信息"""
    if not account_info:
        print("无法获取账户信息")
        return
        
    print("\n=== 账户基本信息 ===")
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    pnl_ratio = (total_pnl / total_wallet) * 100 if total_wallet > 0 else 0

    print(f"总余额: {total_wallet:.4f} USDT")
    print(f"未实现盈亏: {total_pnl:.4f} USDT")
    print(f"盈亏占比: {pnl_ratio:.2f}%")

def print_positions(positions: Optional[List]) -> None:
    """打印持仓信息"""
    if not positions:
        print("无法获取持仓信息")
        return
        
    print("\n=== 合约持仓信息 ===")
    active_positions = [pos for pos in positions if float(pos.get('positionAmt', 0)) != 0]
    
    if not active_positions:
        print("当前无持仓")
        return
        
    for pos in active_positions:
        symbol = pos.get('symbol', '')
        size = float(pos.get('positionAmt', 0))
        side = "多头" if size > 0 else "空头"
        notional = float(pos.get('notional', 0))
        pnl = float(pos.get('unRealizedProfit', 0))
        
        print(f"\n{symbol}: {side} {notional:.2f} U, PNL: {pnl:.2f} U")

def print_pnl_statistics() -> None:
    """打印盈亏统计信息"""
    pnl_stats = get_pnl_statistics()
    
    if pnl_stats['total_records'] == 0:
        print("\n=== 盈亏统计 ===")
        print("暂无盈亏记录数据")
        return
    
    print("\n=== 盈亏统计 (过去 " + str(pnl_stats.get('record_hours', 'N/A')) + " 小时) ===")
    print(f"当前盈亏: {pnl_stats['current_pnl']:.2f}U")
    print(f"最高盈亏: {pnl_stats['max_pnl']:.2f}U ({pnl_stats['max_pnl_time']})" )
    print(f"最低盈亏: {pnl_stats['min_pnl']:.2f}U ({pnl_stats['min_pnl_time']})" )
    print(f"记录数量: {pnl_stats['total_records']}条")

def generate_pnl_chart_locally() -> bool:
    """生成盈亏折线图并保存到本地"""
    try:
        history = load_pnl_history()
        if not history:
            print("无盈亏记录，无法生成图表")
            return False

        timestamps = [record['timestamp'] for record in history]
        pnls = [record['pnl'] for record in history]
        datetimes = [datetime.fromtimestamp(ts) for ts in timestamps]

        plt.figure(figsize=(12, 6))
        plt.plot(datetimes, pnls, linestyle='-', color='skyblue', marker='.')
        
        if datetimes and pnls:
            plt.plot(datetimes[0], pnls[0], marker='o', markersize=8, color='green', label=f'开始: {pnls[0]:.2f}')
            plt.plot(datetimes[-1], pnls[-1], marker='D', markersize=8, color='red', label=f'当前: {pnls[-1]:.2f}')
            plt.legend()

        plt.title('账户未实现盈亏 (PNL) 趋势')
        plt.xlabel('时间')
        plt.ylabel('PNL (USDT)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        img_path = "pnl_chart.png"
        plt.savefig(img_path)
        plt.close()
        print(f"✅ 盈亏图表已保存到本地: {img_path}")
        return True

    except Exception as e:
        print(f"❌ 生成盈亏图表失败: {e}")
        return False

def record_pnl_only() -> None:
    """仅记录盈亏信息"""
    print(f"--- {time.strftime('%H:%M:%S')} 正在记录PNL ---")
    try:
        account_info = get_account_info()
        if account_info:
            record_pnl(account_info)
            print("✅ PNL记录成功")
        else:
            print("❌ PNL记录失败: 无法获取账户信息")
    except Exception as e:
        print(f"❌ 记录盈亏时发生错误: {e}")

def monitor_and_notify() -> None:
    """执行一次完整的监控和通知流程"""
    print(f"\n{'='*50}")
    print(f"执行监控和通知 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    try:
        # 1. 数据获取
        account_info = get_account_info()
        positions = get_positions()

        # 2. 打印信息
        print_account_info(account_info)
        print_positions(positions)
        print_pnl_statistics()

        # 3. 生成图表
        chart_generated = generate_pnl_chart_locally()

        # 4. 钉钉通知
        if not account_info:
            print("无法获取账户信息，跳过通知")
            return

        if should_send_notification():
            pnl_stats = get_pnl_statistics()
            notification_message = format_pnl_notification(account_info, pnl_stats)
            
            print("\n" + "="*60)
            print("📱 准备发送钉钉通知...")
            print("="*60)
            
            image_url = None
            if chart_generated:
                # 定义图片URL，并附加一个时间戳参数来防止钉钉缓存
                timestamp = int(time.time())
                # 注意：这里需要一个公网可访问的地址来提供图片服务
                image_url = f"http://38.147.185.108:8088/pnl_chart.png?t={timestamp}"

            success = send_dingtalk_notification(notification_message, image_url=image_url)
            if success:
                print("✅ 钉钉通知发送成功")
            elif ENABLE_DINGTALK_NOTIFICATION:
                print("❌ 钉钉通知发送失败")
        else:
            print("⏭️ 跳过本次钉钉通知")

    except Exception as e:
        print(f"❌ 监控执行失败: {e}")
        error_message = f"🚨 PNL监控系统错误 🚨\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n错误信息: {str(e)}"
        send_dingtalk_notification(error_message)
    
    print(f"\n监控完成 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

def main() -> None:
    """主函数 - 设置定时任务"""
    print("=== 账户盈亏监控系统 ===")
    print(f"系统启动，每 {PNL_RECORD_INTERVAL} 秒记录一次PNL...")
    
    # 立即执行一次
    record_pnl_only()
    monitor_and_notify()
    
    # 设置定时任务
    schedule.every(PNL_RECORD_INTERVAL).seconds.do(record_pnl_only)
    schedule.every(1).minutes.do(monitor_and_notify)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n系统停止运行")
            break
        except Exception as e:
            print(f"定时任务主循环出错: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
