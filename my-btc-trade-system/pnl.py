
import os
import json
import time
from typing import Dict, List, Optional, Any

from config import PNL_RECORD_FILE, PNL_RECORD_MAX_HOURS

def load_pnl_history() -> List[Dict]:
    """加载盈亏历史记录"""
    try:
        if os.path.exists(PNL_RECORD_FILE):
            with open(PNL_RECORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载盈亏历史记录失败: {e}")
    return []

def save_pnl_history(history: List[Dict]) -> None:
    """保存盈亏历史记录"""
    try:
        with open(PNL_RECORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存盈亏历史记录失败: {e}")

def record_pnl(account_info: Optional[Dict]) -> None:
    """记录当前未实现盈亏"""
    if not account_info:
        return
    
    total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    pnl_ratio = (total_pnl / total_wallet) * 100 if total_wallet > 0 else 0
    
    record = {
        'timestamp': int(time.time()),
        'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
        'pnl': total_pnl,
        'pnl_ratio': pnl_ratio,
        'total_wallet': total_wallet
    }
    
    # 加载历史记录
    history = load_pnl_history()
    
    # 添加新记录
    history.append(record)
    
    # 清理过期记录（保留指定小时数）
    current_time = int(time.time())
    max_age = PNL_RECORD_MAX_HOURS * 3600
    history = [h for h in history if current_time - h['timestamp'] <= max_age]
    
    # 保存记录
    save_pnl_history(history)

def get_pnl_statistics() -> Dict[str, Any]:
    """获取盈亏统计信息"""
    history = load_pnl_history()
    
    if not history:
        return {
            'max_pnl': 0,
            'min_pnl': 0,
            'max_pnl_time': '',
            'min_pnl_time': '',
            'current_pnl': 0,
            'total_records': 0,
            'average_pnl': 0
        }
    
    # 找出最高和最低盈亏
    max_record = max(history, key=lambda x: x['pnl'])
    min_record = min(history, key=lambda x: x['pnl'])
    
    # 获取最新记录
    latest_record = history[-1] if history else {'pnl': 0}
    
    # 计算平均盈亏
    average_pnl = sum(record['pnl'] for record in history) / len(history)
    
    return {
        'max_pnl': max_record['pnl'],
        'min_pnl': min_record['pnl'],
        'max_pnl_time': max_record['datetime'],
        'min_pnl_time': min_record['datetime'],
        'current_pnl': latest_record['pnl'],
        'total_records': len(history),
        'average_pnl': average_pnl
    }
