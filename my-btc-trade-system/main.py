

import schedule
import time
from typing import Dict, List, Optional

from config import PNL_RECORD_INTERVAL, PNL_RECORD_MAX_HOURS, ENABLE_DINGTALK_NOTIFICATION
from data_provider import get_multiple_symbols_data, get_account_info, get_positions
from analysis import (
    calculate_trend_indicators, check_risk_control, check_operation_frequency, 
    check_pnl_ratio_reduce_signals, generate_reduce_position_signals, 
    generate_add_position_signals, analyze_no_signal_reasons
)
from pnl import record_pnl, get_pnl_statistics, record_pnl as record_pnl_only
from alerter import format_signals_for_notification, should_send_notification, send_dingtalk_notification

def print_account_info(account_info: Optional[Dict]) -> None:
    """打印账户信息"""
    if not account_info:
        return
        
    print("\n=== 账户基本信息 ===")
    fields = [
        ('总余额', 'totalWalletBalance'),
        ('可用余额', 'availableBalance'),
        ('未实现盈亏', 'totalUnrealizedProfit'),
        ('保证金余额', 'totalMarginBalance')
    ]
    
    for label, key in fields:
        value = float(account_info.get(key, 0))
        print(f"{label}: {value:.4f} USDT")
    
    # 计算并显示未实现盈亏占比
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    
    if total_wallet > 0:
        pnl_ratio = (total_pnl / total_wallet) * 100
        print(f"盈亏占比: {pnl_ratio:.2f}% ({total_pnl:.4f}/{total_wallet:.4f}*100)")
    
    # 计算并显示保证金使用率
    from analysis import calculate_margin_ratio, get_margin_level
    margin_ratio = calculate_margin_ratio(account_info)
    margin_level = get_margin_level(margin_ratio)
    
    level_names = {
        'aggressive': '积极操作区',
        'normal': '正常操作区', 
        'cautious': '谨慎操作区',
        'risk_control': '风险控制区',
        'emergency': '紧急区'
    }
    
    # 计算已使用保证金
    used_margin = float(account_info.get('totalInitialMargin', 0))
    available_balance = float(account_info.get('availableBalance', 0))
    
    print(f"已使用保证金: {used_margin:.4f} USDT (来源: totalInitialMargin)")
    print(f"计算验证: 总余额{total_wallet:.4f} - 可用余额{available_balance:.4f} = {total_wallet - available_balance:.4f} USDT")
    print(f"保证金使用率: {margin_ratio:.2f}% ({used_margin:.4f}/{total_wallet:.4f}*100)")
    print(f"操作级别: {level_names.get(margin_level, '未知')} ({margin_level})")

def print_positions(positions: Optional[List]) -> None:
    """打印持仓信息"""
    if not positions:
        return
        
    print("\n=== 合约持仓信息 ===")
    active_positions = [pos for pos in positions if float(pos.get('positionAmt', 0)) != 0]
    
    if not active_positions:
        print("当前无持仓")
        return
        
    for pos in active_positions:
        symbol = pos.get('symbol', '')
        position_side = pos.get('positionSide', '')
        size = float(pos.get('positionAmt', 0))
        side = "多头" if size > 0 else "空头"
        entry_price = float(pos.get('entryPrice', 0))
        position_value = abs(size * entry_price)
        notional = float(pos.get('notional', 0))
        
        print(f"\n{symbol} ({position_side}):")
        print(f"  方向: {side}")
        print(f"  持仓价值: {notional:.2f} USDT")
        
        # 只显示指定字段
        display_fields = [
            ('entryPrice', '开仓价'),
            ('unRealizedProfit', '未实现盈亏'),
            ('liquidationPrice', '强平价'),
            ('positionInitialMargin', '仓位初始保证金'),
            ('maintMargin', '维持保证金'),
            ('updateTime', '更新时间')
        ]
        
        margin_asset = pos.get('marginAsset', 'USDT')
        
        for key, chinese_name in display_fields:
            value = pos.get(key, 0)
            
            if key == 'updateTime':
                formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(value)/1000))
                print(f"  {chinese_name}: {formatted_time}")
            elif key == 'liquidationPrice':
                liquidation_price = float(value)
                if liquidation_price > 0:
                    print(f"  {chinese_name}: {liquidation_price:.6f}")
                else:
                    print(f"  {chinese_name}: 无")
            elif key in ['unRealizedProfit', 'positionInitialMargin', 'maintMargin']:
                num_value = float(value)
                print(f"  {chinese_name}: {num_value:.4f} {margin_asset}")
            else:
                num_value = float(value)
                print(f"  {chinese_name}: {num_value:.6f}")

def print_trend_analysis(trend_results: Dict[str, Dict]) -> None:
    """打印趋势分析结果"""
    if not trend_results:
        print("无趋势分析数据")
        return
        
    print("\n=== 趋势识别分析 ===")
    
    for symbol, data in trend_results.items():
        print(f"\n{symbol}:")
        print(f"  趋势: {data.get('trend', '未知')}")
        print(f"  7日涨跌幅: {data.get('change_7d', 0):.2f}%")
        
        if symbol != "BTCUSDT":
            relative_to_btc = data.get('relative_to_btc', 0)
            relative_status = "强势" if relative_to_btc > 0 else "弱势"
            print(f"  相对BTC: {relative_status} {relative_to_btc:.2f}%")
            
        print(f"  连续收阳: {data.get('consecutive_green', 0)}天")
        print(f"  连续收阴: {data.get('consecutive_red', 0)}天")
        print(f"  当前价格: {data.get('current_price', 0):.4f}")
        print(f"  20日均线: {data.get('ma20', 0):.4f}")
        print(f"  偏离20日均线: {data.get('distance_from_ma20', 0):.2f}%")

def print_reduce_position_signals(signals: Dict[str, List]) -> None:
    """打印减仓信号"""
    if not signals:
        print("\n=== 减仓提示 ===")
        print("当前无减仓信号")
        return
    
    print("\n=== 减仓提示 ===")
    
    for symbol, signal_list in signals.items():
        print(f"\n{symbol}:")
        for signal in signal_list:
            print(f"  类型: {signal['type']}")
            print(f"  趋势: {signal.get('trend', '未知')}")
            print(f"  条件: {signal['condition']}")
            print(f"  建议减仓: {signal['percentage']}")

def print_add_position_signals(signals: Dict[str, List]) -> None:
    """打印加仓信号"""
    if not signals:
        print("\n=== 加仓提示 ===")
        print("当前无加仓信号")
        return
    
    print("\n=== 加仓提示 ===")
    
    # 方向中文映射
    side_names = {
        'LONG': '多头',
        'SHORT': '空头', 
        'BOTH': '双向'
    }
    
    for symbol, signal_list in signals.items():
        print(f"\n{symbol}:")
        for signal in signal_list:
            position_side = signal.get('position_side', '未知')
            side_name = side_names.get(position_side, position_side)
            
            print(f"  类型: {signal['type']}")
            print(f"  方向: {side_name}")
            print(f"  趋势: {signal.get('trend', '未知')}")
            print(f"  条件: {signal['condition']}")
            print(f"  建议加仓: {signal['amount']}U")

def print_risk_warnings(warnings: Dict[str, List]) -> None:
    """打印风控警告"""
    if not warnings:
        return
    
    print("\n=== ⚠️  风控红线警告 ===")
    
    for symbol, warning_list in warnings.items():
        if symbol == 'SYSTEM':
            print(f"\n🚨 系统级风险:")
        else:
            print(f"\n⚠️  {symbol}:")
        
        for warning in warning_list:
            print(f"  {warning}")
    
    print("\n建议立即检查并调整仓位！")

def print_operation_frequency(positions: Optional[List]) -> None:
    """打印操作频率统计"""
    daily_ops = check_operation_frequency(positions)
    
    if not daily_ops:
        return
    
    print("\n=== 今日操作频率 ===")
    
    # 方向中文映射
    side_names = {
        'LONG': '多头',
        'SHORT': '空头', 
        'BOTH': '双向'
    }
    
    for symbol, side_counts in daily_ops.items():
        total_ops = sum(side_counts.values())
        if total_ops > 0:
            print(f"\n{symbol}: 总操作{total_ops}次")
            for side, count in side_counts.items():
                if count > 0:
                    side_name = side_names.get(side, side)
                    print(f"  {side_name}: {count}次")

def print_pnl_statistics() -> None:
    """打印盈亏统计信息"""
    pnl_stats = get_pnl_statistics()
    
    if pnl_stats['total_records'] == 0:
        print("\n=== 盈亏统计 ===")
        print("暂无盈亏记录数据")
        return
    
    print("\n=== 盈亏统计 ===")
    print(f"当前盈亏: {pnl_stats['current_pnl']:.2f}U")
    print(f"最高盈亏: {pnl_stats['max_pnl']:.2f}U ({pnl_stats['max_pnl_time']})")
    print(f"最低盈亏: {pnl_stats['min_pnl']:.2f}U ({pnl_stats['min_pnl_time']})")
    print(f"平均盈亏: {pnl_stats['average_pnl']:.2f}U")
    print(f"记录数量: {pnl_stats['total_records']}条")

def run_analysis() -> None:
    """执行一次完整的分析"""
    print(f"\n{'='*50}")
    print(f"开始分析 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    try:
        # 1. 数据获取
        all_data = get_multiple_symbols_data()
        if not all_data:
            print("无法获取K线数据")
            return
        
        account_info = get_account_info()
        positions = get_positions()

        # 2. 分析
        trend_results = calculate_trend_indicators(all_data)
        risk_warnings = check_risk_control(positions, account_info)
        pnl_ratio_signals = check_pnl_ratio_reduce_signals(account_info)
        reduce_signals = generate_reduce_position_signals(positions, all_data, trend_results, account_info)
        if pnl_ratio_signals:
            reduce_signals.update(pnl_ratio_signals)
        add_signals = generate_add_position_signals(positions, all_data, trend_results, account_info, reduce_signals)
        
        # 打印与告警
        print_trend_analysis(trend_results)
        print_account_info(account_info)
        record_pnl(account_info)
        print_positions(positions)
        print_risk_warnings(risk_warnings)
        print_operation_frequency(positions)
        print_reduce_position_signals(reduce_signals)
        print_add_position_signals(add_signals)
        no_signal_analysis = analyze_no_signal_reasons(positions, all_data, trend_results, account_info, reduce_signals, add_signals)
        print_pnl_statistics()

        # 4. 钉钉通知
        if reduce_signals or add_signals:
            notification_message = format_signals_for_notification(reduce_signals, add_signals, no_signal_analysis)
            print("\n" + "="*60)
            print("📱 钉钉通知内容:")
            print("="*60)
            print(notification_message)
            print("="*60)
            
            if should_send_notification(reduce_signals, add_signals):
                success = send_dingtalk_notification(notification_message)
                if success:
                    print("✅ 钉钉通知发送成功")
                elif ENABLE_DINGTALK_NOTIFICATION:
                    print("❌ 钉钉通知发送失败")
            else:
                print("⏭️ 相同信号已在10分钟内发送，跳过钉钉通知")
        else:
            notification_message = format_signals_for_notification(reduce_signals, add_signals, no_signal_analysis)
            print("\n" + "="*60)
            print("📱 钉钉通知内容:")
            print("="*60)
            print(notification_message)
            print("="*60)

    except Exception as e:
        print(f"❌ 分析执行失败: {e}")
        error_message = f"🚨 币安交易系统错误 🚨\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n错误信息: {str(e)}"
        send_dingtalk_notification(error_message)
    
    print(f"\n分析完成 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

def main() -> None:
    """主函数 - 设置定时任务"""
    print("=== 币安交易风险提示系统 ===")
    print("系统启动，每分钟执行一次分析...")
    print(f"盈亏记录间隔: {PNL_RECORD_INTERVAL}秒")
    print(f"最大记录时长: {PNL_RECORD_MAX_HOURS}小时")
    
    # 立即执行一次
    run_analysis()
    
    # 设置定时任务：每分钟执行一次完整分析
    schedule.every().minute.do(run_analysis)
    
    # 设置定时任务：按配置间隔记录盈亏
    if PNL_RECORD_INTERVAL != 60:  # 如果记录间隔不是1分钟，单独设置
        schedule.every(PNL_RECORD_INTERVAL).seconds.do(record_pnl_only)
    
    # 保持程序运行
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)  # 每秒检查一次
        except KeyboardInterrupt:
            print("\n\n系统停止运行")
            break
        except Exception as e:
            print(f"定时任务执行出错: {e}")
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == "__main__":
    main()
