import requests
import time
from typing import Dict, List, Optional

from config import DINGTALK_WEBHOOK_URL, ENABLE_DINGTALK_NOTIFICATION
from pnl import get_pnl_statistics

_notification_history = {}

def generate_signal_hash(
    reduce_signals: Dict[str, List], 
    add_signals: Dict[str, List],
    risk_warnings: Optional[Dict[str, List[str]]] = None
) -> str:
    """生成信号的唯一标识哈希值"""
    signal_data = []
    
    # 减仓信号
    if reduce_signals:
        for symbol, signal_list in reduce_signals.items():
            for signal in signal_list:
                signal_key = f"{symbol}_{signal['type']}_{signal.get('percentage', 0)}"
                signal_data.append(signal_key)
    
    # 加仓信号
    if add_signals:
        for symbol, signal_list in add_signals.items():
            for signal in signal_list:
                signal_key = f"{symbol}_{signal['type']}_{signal.get('amount', 0)}_{signal.get('position_side', '')}"
                signal_data.append(signal_key)

    # 风险警告
    if risk_warnings:
        for symbol, warning_list in risk_warnings.items():
            for warning in warning_list:
                signal_data.append(f"{symbol}_risk_{warning}")
    
    # 生成哈希
    signal_str = "_".join(sorted(signal_data))
    return str(hash(signal_str))

def should_send_notification(
    reduce_signals: Dict[str, List], 
    add_signals: Dict[str, List],
    risk_warnings: Optional[Dict[str, List[str]]] = None
) -> bool:
    """检查是否应该发送通知（10分钟内不重复发送相同内容）"""
    global _notification_history
    
    if not reduce_signals and not add_signals and not risk_warnings:
        return False
    
    # 生成当前信号的哈希值
    current_hash = generate_signal_hash(reduce_signals, add_signals, risk_warnings)
    current_time = time.time()
    
    # 清理10分钟前的记录
    cutoff_time = current_time - 600  # 10分钟 = 600秒
    _notification_history = {k: v for k, v in _notification_history.items() if v > cutoff_time}
    
    # 检查是否已发送过相同内容
    if current_hash in _notification_history:
        last_sent_time = _notification_history[current_hash]
        time_diff = (current_time - last_sent_time) / 60  # 转换为分钟
        print(f"相同信号在{time_diff:.1f}分钟前已发送，跳过钉钉通知")
        return False
    
    # 记录本次发送
    _notification_history[current_hash] = current_time
    return True

def send_dingtalk_notification(message: str) -> bool:
    """发送钉钉机器人通知"""
    if not ENABLE_DINGTALK_NOTIFICATION or not DINGTALK_WEBHOOK_URL:
        return False
    
    try:
        headers = {'Content-Type': 'application/json'}
        
        # 只发送文本消息
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        
        response = requests.post(DINGTALK_WEBHOOK_URL, headers=headers, json=data, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"钉钉通知发送失败: {e}")
        return False

def format_signals_for_notification(
    reduce_signals: Dict[str, List], 
    add_signals: Dict[str, List], 
    no_signal_analysis: Optional[Dict[str, List[str]]] = None,
    risk_warnings: Optional[Dict[str, List[str]]] = None
) -> str:
    """格式化信号为钉钉通知消息"""
    messages = []
    messages.append("🚨 币安交易提醒 🚨")
    messages.append(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    messages.append("")

    # 风控红线警告
    if risk_warnings:
        messages.append("=== ⚠️ 风控红线警告 ⚠️ ===")
        for symbol, warning_list in risk_warnings.items():
            if symbol == 'SYSTEM':
                messages.append(f"🚨 系统级风险:")
            else:
                messages.append(f"⚠️ {symbol}:")
            for warning in warning_list:
                messages.append(f"  • {warning}")
        messages.append("建议立即检查并调整仓位！")
        messages.append("")
    
    # 盈亏统计信息
    pnl_stats = get_pnl_statistics()
    if pnl_stats['total_records'] > 0:
        messages.append("💰 盈亏统计:")
        messages.append(f"   当前盈亏: {pnl_stats['current_pnl']:.2f}U")
        messages.append(f"   最高盈亏: {pnl_stats['max_pnl']:.2f}U ({pnl_stats['max_pnl_time']})")
        messages.append(f"   最低盈亏: {pnl_stats['min_pnl']:.2f}U ({pnl_stats['min_pnl_time']})")
        messages.append(f"   记录数量: {pnl_stats['total_records']}条")
        messages.append(f"   平均盈亏: {pnl_stats['average_pnl']:.2f}U")
        messages.append("")
    
    # 减仓信号
    if reduce_signals:
        messages.append("📉 减仓提示:")
        for symbol, signal_list in reduce_signals.items():
            for signal in signal_list:
                if symbol == 'SYSTEM':
                    messages.append(f"🔔 系统级: {signal['condition']}")
                    messages.append(f"   建议减仓: {signal['percentage']}")
                else:
                    messages.append(f"🔸 {symbol}: {signal['condition']}")
                    messages.append(f"   建议减仓: {signal['percentage']}")
        messages.append("")
    
    # 加仓信号
    if add_signals:
        messages.append("📈 加仓提示:")
        for symbol, signal_list in add_signals.items():
            for signal in signal_list:
                side_names = {'LONG': '多头', 'SHORT': '空头', 'BOTH': '双向'}
                side_name = side_names.get(signal.get('position_side', ''), '未知')
                messages.append(f"🔸 {symbol} ({side_name}): {signal['condition']}")
                messages.append(f"   建议加仓: {signal['amount']}U")
        messages.append("")
    
    if not reduce_signals and not add_signals and not risk_warnings:
        messages.append("✅ 当前无操作信号")
        messages.append("持续监控中...")
    
    # 添加无操作原因分析
    if no_signal_analysis:
        messages.append("\n❌ 无操作信号原因分析:")
        for symbol, reasons in no_signal_analysis.items():
            messages.append(f"\n{symbol}:")
            for reason in reasons:
                messages.append(f"  • {reason}")

    return "\n".join(messages)