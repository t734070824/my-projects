import requests
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Dict, Optional, Any

from config import DINGTALK_WEBHOOK_URL, ENABLE_DINGTALK_NOTIFICATION, NOTIFICATION_INTERVAL
from api_keys import DINGTALK_SECRET

_last_notification_time = 0

def should_send_notification() -> bool:
    """检查是否应该发送通知（基于时间间隔）"""
    global _last_notification_time
    current_time = time.time()
    
    if (current_time - _last_notification_time) >= NOTIFICATION_INTERVAL:
        _last_notification_time = current_time
        return True
    
    print(f"通知冷却中，距离下次可发送还有 {int(NOTIFICATION_INTERVAL - (current_time - _last_notification_time))} 秒")
    return False

def get_signed_dingtalk_url() -> Optional[str]:
    """获取带签名的钉钉Webhook URL"""
    if not DINGTALK_SECRET:
        return DINGTALK_WEBHOOK_URL

    try:
        timestamp = str(round(time.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = f'{timestamp}\n{DINGTALK_SECRET}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        return f"{DINGTALK_WEBHOOK_URL}&timestamp={timestamp}&sign={sign}"
    except Exception as e:
        print(f"生成钉钉签名失败: {e}")
        return None

def send_dingtalk_notification(message: str, image_url: Optional[str] = None) -> bool:
    """发送钉钉机器人通知，支持文本或Markdown（带图片）"""
    if not ENABLE_DINGTALK_NOTIFICATION or not DINGTALK_WEBHOOK_URL:
        return False

    webhook_url = get_signed_dingtalk_url()
    if not webhook_url:
        return False

    try:
        headers = {'Content-Type': 'application/json'}
        
        if image_url:
            markdown_text = f"{message}\n\n![盈亏图表]({image_url})"
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "账户盈亏监控",
                    "text": markdown_text
                }
            }
        else:
            data = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
        
        response = requests.post(webhook_url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        return response.status_code == 200
        
    except Exception as e:
        print(f"钉钉通知发送失败: {e}")
        return False


def format_pnl_notification(account_info: Dict, pnl_stats: Dict[str, Any]) -> str:
    """格式化盈亏信息为钉钉通知消息"""
    messages = []
    messages.append("💰 账户盈亏监控 💰")
    messages.append(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    messages.append("")

    # 账户信息
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    pnl_ratio = (total_pnl / total_wallet) * 100 if total_wallet > 0 else 0
    
    messages.append("📊 **账户概览**")
    messages.append(f"   - **总余额**: {total_wallet:.2f} U")
    messages.append(f"   - **未实现盈亏**: {total_pnl:.2f} U")
    messages.append(f"   - **盈亏占比**: {pnl_ratio:.2f}%")
    messages.append("")

    # 盈亏统计信息
    if pnl_stats['total_records'] > 0:
        messages.append("📈 **盈亏统计 (过去 " + str(pnl_stats.get('record_hours', 'N/A')) + " 小时)**")
        messages.append(f"   - **当前盈亏**: {pnl_stats['current_pnl']:.2f} U")
        messages.append(f"   - **最高盈亏**: {pnl_stats['max_pnl']:.2f} U ({pnl_stats['max_pnl_time']})")
        messages.append(f"   - **最低盈亏**: {pnl_stats['min_pnl']:.2f} U ({pnl_stats['min_pnl_time']})")
        messages.append(f"   - **平均盈亏**: {pnl_stats['average_pnl']:.2f} U")
    
    # 使用两个空格+换行符来确保在钉钉Markdown中正确换行
    return "  \n".join(messages)