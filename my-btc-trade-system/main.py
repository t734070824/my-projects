import requests
import json
import time
import hmac
import hashlib
import schedule
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import base64
import io
from typing import Dict, List, Optional, Any, Tuple
from config import *
from api_keys import API_KEY, SECRET_KEY

# 尝试导入钉钉配置，如果不存在则使用默认配置
try:
    from dingtalk_config import DINGTALK_WEBHOOK_URL, ENABLE_DINGTALK_NOTIFICATION
except ImportError:
    # 如果没有dingtalk_config.py文件，使用config.py中的默认配置
    pass

# 全局变量：存储最近发送的通知记录
_notification_history = {}

# 盈亏记录相关函数
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

def generate_pnl_chart_data() -> List[Tuple[str, float]]:
    """生成盈亏图表数据"""
    history = load_pnl_history()
    
    if not history:
        return []
    
    # 取最近100个数据点，避免图表过于密集
    recent_history = history[-100:] if len(history) > 100 else history
    
    # 格式化时间显示（只显示小时:分钟）
    chart_data = []
    for record in recent_history:
        time_str = record['datetime'][11:16]  # 提取 HH:MM
        chart_data.append((time_str, record['pnl']))
    
    return chart_data

def generate_pnl_chart_image() -> Optional[str]:
    """生成盈亏走势图片并返回base64编码"""
    try:
        history = load_pnl_history()
        
        if not history:
            return None
        
        # 取最近100个数据点
        recent_history = history[-100:] if len(history) > 100 else history
        
        # 准备数据
        times = []
        pnl_values = []
        
        for record in recent_history:
            times.append(datetime.strptime(record['datetime'], '%Y-%m-%d %H:%M:%S'))
            pnl_values.append(record['pnl'])
        
        # 设置中文字体（如果需要）
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 绘制折线图
        ax.plot(times, pnl_values, color='#1f77b4', linewidth=2, marker='o', markersize=3)
        
        # 设置标题和标签
        ax.set_title('盈亏走势图', fontsize=16, fontweight='bold')
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('盈亏 (USDT)', fontsize=12)
        
        # 格式化x轴时间显示
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.xticks(rotation=45)
        
        # 添加网格
        ax.grid(True, alpha=0.3)
        
        # 设置背景色
        ax.set_facecolor('#f8f9fa')
        
        # 添加零线
        ax.axhline(y=0, color='red', linestyle='--', alpha=0.7, linewidth=1)
        
        # 调整布局
        plt.tight_layout()
        
        # 保存为字节流
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        
        # 转换为base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        # 清理资源
        plt.close(fig)
        img_buffer.close()
        
        return img_base64
        
    except Exception as e:
        print(f"生成盈亏图片失败: {e}")
        return None

def format_pnl_chart(chart_data: List[Tuple[str, float]]) -> str:
    """格式化盈亏图表为文本"""
    if not chart_data:
        return "暂无数据"
    
    # 计算图表参数
    pnl_values = [data[1] for data in chart_data]
    min_pnl = min(pnl_values)
    max_pnl = max(pnl_values)
    range_pnl = max_pnl - min_pnl if max_pnl != min_pnl else 1
    
    # 图表高度和宽度
    height = 8
    width = min(40, len(chart_data))
    
    # 创建二维图表数组
    chart_grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    # 绘制连线
    for j in range(width):
        if j < len(chart_data):
            pnl = chart_data[j][1]
            # 计算当前点在图表中的Y位置
            point_y = int((max_pnl - pnl) / range_pnl * (height - 1))
            point_y = max(0, min(height - 1, point_y))
            
            if j == 0:
                # 第一个点
                chart_grid[point_y][j] = '◆'
            elif j == len(chart_data) - 1:
                # 最后一个点
                chart_grid[point_y][j] = '★'
            else:
                # 中间的点用连线符号
                chart_grid[point_y][j] = '─'
            
            # 绘制到下一个点的连线
            if j < len(chart_data) - 1 and j + 1 < width:
                next_pnl = chart_data[j + 1][1]
                next_point_y = int((max_pnl - next_pnl) / range_pnl * (height - 1))
                next_point_y = max(0, min(height - 1, next_point_y))
                
                # 绘制垂直连线
                start_y = min(point_y, next_point_y)
                end_y = max(point_y, next_point_y)
                
                for y in range(start_y, end_y + 1):
                    if chart_grid[y][j] == ' ':
                        chart_grid[y][j] = '│'
    
    # 生成图表
    chart_lines = []
    chart_lines.append("📊 盈亏走势图:")
    chart_lines.append("=" * (width + 10))
    
    # 输出图表
    for i in range(height):
        y = max_pnl - (i * range_pnl / height)
        line = f"{y:8.2f} |"
        
        for j in range(width):
            line += chart_grid[i][j]
        
        chart_lines.append(line)
    
    # 添加底部边框
    chart_lines.append("        |" + "─" * width)
    chart_lines.append("=" * (width + 10))
    
    return "\n".join(chart_lines)

def calculate_change_and_amplitude(klines: List[List]) -> List[List]:
    """计算每条数据的涨跌和振幅，并将结果添加到klines中"""
    if len(klines) < 2:
        return klines
    
    for i in range(1, len(klines)):
        current, previous = klines[i], klines[i-1]
        
        # 解析价格数据
        current_close, previous_close = float(current[4]), float(previous[4])
        current_high, current_low = float(current[2]), float(current[3])
        
        # 计算指标
        change = current_close - previous_close
        change_percent = (change / previous_close) * 100
        amplitude = ((current_high - current_low) / previous_close) * 100
        
        # 添加计算结果
        current.extend([change, change_percent, amplitude])
    
    return klines

def make_api_request(endpoint: str, params: Optional[Dict] = None, auth_required: bool = False) -> Optional[Dict]:
    """统一的API请求函数"""
    url = f"{BINANCE_BASE_URL}{endpoint}"
    headers = {}
    proxies = {'http': 'http://127.0.0.1:10809', 'https': 'http://127.0.0.1:10809'} if USE_PROXY else None
    
    try:
        if auth_required:
            if not all([API_KEY, SECRET_KEY]):
                print("请先配置API_KEY和SECRET_KEY")
                return None
            
            timestamp = int(time.time() * 1000)
            query_params = params or {}
            query_params['timestamp'] = timestamp
            
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            
            url = f"{url}?{query_string}&signature={signature}"
            headers['X-MBX-APIKEY'] = API_KEY
        else:
            if params:
                query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                url = f"{url}?{query_string}"
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API请求失败: {e}")
        return None

def get_binance_klines(symbol: str) -> Optional[List]:
    """从币安获取指定symbol的K线数据"""
    params = {'symbol': symbol, 'interval': INTERVAL, 'timeZone': TIMEZONE}
    return make_api_request(BINANCE_KLINES_ENDPOINT, params)

def get_multiple_symbols_data() -> Dict[str, List]:
    """获取多个symbol的K线数据"""
    result = {}
    for symbol in SYMBOLS:
        klines = get_binance_klines(symbol)
        if klines:
            result[symbol] = calculate_change_and_amplitude(klines)
    return result

def get_account_info() -> Optional[Dict]:
    """获取账户基本信息"""
    return make_api_request(BINANCE_ACCOUNT_ENDPOINT, auth_required=True)

def get_positions() -> Optional[List]:
    """获取合约持仓信息"""
    return make_api_request(BINANCE_POSITION_ENDPOINT, auth_required=True)

def get_user_trades(symbol: str, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: int = 500) -> Optional[List]:
    """获取用户交易历史"""
    params = {'symbol': symbol, 'limit': limit}
    
    if start_time:
        params['startTime'] = start_time
    if end_time:
        params['endTime'] = end_time
        
    return make_api_request(BINANCE_USER_TRADES_ENDPOINT, params, auth_required=True)

def calculate_margin_ratio(account_info: Optional[Dict]) -> float:
    """计算保证金使用率"""
    if not account_info:
        return 0
    
    used_margin = float(account_info.get('totalInitialMargin', 0))
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    
    if total_wallet == 0:
        return 0
    
    return (used_margin / total_wallet) * 100

def get_margin_level(margin_ratio: float) -> str:
    """根据保证金使用率获取操作级别"""
    for level, (min_ratio, max_ratio) in MARGIN_LEVELS.items():
        if min_ratio <= margin_ratio < max_ratio:
            return level
    return 'emergency'

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

def calculate_trend_indicators(klines_data: Dict[str, List]) -> Dict[str, Dict]:
    """计算趋势识别指标"""
    trend_results = {}
    
    # 获取BTC的7日涨跌幅作为基准
    btc_change_7d = 0
    if "BTCUSDT" in klines_data:
        btc_klines = klines_data["BTCUSDT"]
        if len(btc_klines) >= 168:
            btc_start_price, btc_end_price = float(btc_klines[-168][4]), float(btc_klines[-1][4])
            btc_change_7d = ((btc_end_price - btc_start_price) / btc_start_price) * 100
    
    for symbol, klines in klines_data.items():
        if len(klines) < 20:  # 需要至少20条数据来计算指标
            continue
            
        # 获取最近的数据
        recent_7_days = klines[-168:]  # 7天 * 24小时
        recent_5_days = klines[-120:]  # 5天 * 24小时
        recent_4_days = klines[-96:]   # 4天 * 24小时
        recent_20_days = klines[-480:] # 20天 * 24小时
        
        # 计算7日涨跌幅（7*24=168小时前的价格对比）
        if len(klines) >= 168:
            start_price = float(klines[-168][4])  # 168小时前（7天前）的收盘价
            end_price = float(klines[-1][4])      # 最新收盘价
            change_7d = ((end_price - start_price) / start_price) * 100
        else:
            change_7d = 0
            
        # 计算相对BTC强势/弱势
        if symbol == "BTCUSDT":
            relative_to_btc = 0  # BTC自己相对于自己为0
        else:
            relative_to_btc = change_7d - btc_change_7d
            
        # 计算连续收阳/收阴天数（按24小时为一天计算）
        consecutive_green = 0  # 连续收阳天数
        consecutive_red = 0    # 连续收阴天数
        
        # 检查连续收阳（最多检查5天）
        for day in range(min(5, len(klines) // 24)):
            day_start = len(klines) - 1 - (day * 24)
            day_end = len(klines) - 1 - ((day + 1) * 24)
            
            if day_end < 0:
                break
                
            day_open = float(klines[day_end][1])
            day_close = float(klines[day_start][4])
            
            if day_close > day_open:  # 当天收阳
                consecutive_green += 1
            else:
                break
                
        # 检查连续收阴（最多检查4天）
        for day in range(min(4, len(klines) // 24)):
            day_start = len(klines) - 1 - (day * 24)
            day_end = len(klines) - 1 - ((day + 1) * 24)
            
            if day_end < 0:
                break
                
            day_open = float(klines[day_end][1])
            day_close = float(klines[day_start][4])
            
            if day_close < day_open:  # 当天收阴
                consecutive_red += 1
            else:
                break
                
        # 计算20日均线（480小时均线）
        if len(recent_20_days) >= 480:
            ma20 = sum(float(kline[4]) for kline in recent_20_days) / 480
            current_price = float(klines[-1][4])
            distance_from_ma20 = ((current_price - ma20) / ma20) * 100
        else:
            ma20 = 0
            distance_from_ma20 = 0
            
        # 趋势判断
        trend = "未知"
        
        # 趋势判断 - 使用配置中的阈值
        if (change_7d > STRONG_UP_CHANGE and 
            consecutive_green >= STRONG_UP_CONSECUTIVE and
            (symbol == "BTCUSDT" or relative_to_btc > RELATIVE_BTC_STRONG)):
            trend = "强势上升"
        elif (change_7d < STRONG_DOWN_CHANGE and 
              consecutive_red >= STRONG_DOWN_CONSECUTIVE):
            trend = "弱势下降"
        elif (-SIDEWAYS_RANGE <= change_7d <= SIDEWAYS_RANGE and 
              abs(distance_from_ma20) <= MA20_DISTANCE):
            trend = "横盘震荡"
        elif (SIDEWAYS_RANGE < change_7d <= STRONG_UP_CHANGE):
            trend = "温和上升"
        elif (STRONG_DOWN_CHANGE <= change_7d < -SIDEWAYS_RANGE):
            trend = "温和下降"
        elif (change_7d > SIDEWAYS_RANGE and distance_from_ma20 < -MA20_DISTANCE):
            trend = "高位调整"
        elif (change_7d < -SIDEWAYS_RANGE and distance_from_ma20 > MA20_DISTANCE):
            trend = "低位反弹"
        else:
            trend = "盘整待变"
            
        trend_results[symbol] = {
            'trend': trend,
            'change_7d': change_7d,
            'relative_to_btc': relative_to_btc,
            'consecutive_green': consecutive_green,
            'consecutive_red': consecutive_red,
            'ma20': ma20,
            'distance_from_ma20': distance_from_ma20,
            'current_price': float(klines[-1][4])
        }
    
    return trend_results

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

def calculate_5day_high(klines: List[List]) -> float:
    """计算5日最高价"""
    if len(klines) < 120:  # 5天 * 24小时
        return 0
    
    recent_5days = klines[-120:]
    return max(float(kline[2]) for kline in recent_5days)

def calculate_7day_high(klines: List[List]) -> float:
    """计算7日最高价"""
    if len(klines) < 168:  # 7天 * 24小时
        return 0
    
    recent_7days = klines[-168:]
    return max(float(kline[2]) for kline in recent_7days)

def check_risk_control(positions: Optional[List], account_info: Optional[Dict]) -> Dict[str, List]:
    """检查硬性风控红线"""
    if not positions or not account_info:
        return {}
    
    warnings = {}
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    margin_ratio = calculate_margin_ratio(account_info)
    
    for pos in positions:
        if float(pos.get('positionAmt', 0)) == 0:
            continue
            
        symbol = pos.get('symbol', '')
        position_value = abs(float(pos.get('positionAmt', 0)) * float(pos.get('entryPrice', 0)))
        pnl = float(pos.get('unRealizedProfit', 0))
        
        position_warnings = []
        
        # 检查仓位上限
        if symbol in MAX_POSITION_LIMITS:
            max_limit = MAX_POSITION_LIMITS[symbol]
            if position_value > max_limit:
                position_warnings.append(f"仓位超限: {position_value:.2f}U > {max_limit}U")
        

        
        # 检查单币种亏损
        if total_wallet > 0:
            loss_ratio = abs(pnl / total_wallet) * 100 if pnl < 0 else 0
            if loss_ratio > FORCE_CLOSE_SINGLE_LOSS:
                position_warnings.append(f"单币种亏损超限: {loss_ratio:.1f}% > {FORCE_CLOSE_SINGLE_LOSS}%")
        
        if position_warnings:
            warnings[symbol] = position_warnings
    
    # 检查保证金使用率
    if margin_ratio > FORCE_CLOSE_MARGIN_RATIO:
        warnings['SYSTEM'] = [f"保证金使用率超限: {margin_ratio:.1f}% > {FORCE_CLOSE_MARGIN_RATIO}%"]
    
    # 检查账户总亏损
    total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    if total_wallet > 0 and total_pnl < 0:
        total_loss_ratio = abs(total_pnl / total_wallet) * 100
        if total_loss_ratio > FORCE_CLOSE_TOTAL_LOSS:
            if 'SYSTEM' not in warnings:
                warnings['SYSTEM'] = []
            warnings['SYSTEM'].append(f"账户总亏损超限: {total_loss_ratio:.1f}% > {FORCE_CLOSE_TOTAL_LOSS}%")
    
    return warnings

def check_operation_frequency(positions: Optional[List]) -> Dict[str, Dict[str, int]]:
    """检查当日操作频率"""
    daily_operations = {}
    
    if not positions:
        return daily_operations
    
    # 获取今日开始时间（UTC时间）
    today_start = int(time.time() // 86400 * 86400 * 1000)  # 今日0点的时间戳（毫秒）
    today_end = today_start + 86400000  # 今日24点的时间戳（毫秒）
    
    # 为每个持仓币种检查今日交易记录
    for pos in positions:
        if float(pos.get('positionAmt', 0)) == 0:
            continue
            
        symbol = pos.get('symbol', '')
        
        # 获取该币种今日的交易历史
        trades = get_user_trades(symbol, today_start, today_end, 1000)
        
        if not trades:
            daily_operations[symbol] = {'LONG': 0, 'SHORT': 0, 'BOTH': 0}
            continue
        
        # 统计各方向的操作次数
        side_counts = {'LONG': 0, 'SHORT': 0, 'BOTH': 0}
        
        for trade in trades:
            position_side = trade.get('positionSide', 'BOTH')
            if position_side in side_counts:
                side_counts[position_side] += 1
        
        daily_operations[symbol] = side_counts
    
    return daily_operations

def apply_margin_control(signals: Dict[str, List], margin_level: str, signal_type: str) -> Dict[str, List]:
    """根据保证金级别调整信号"""
    if not signals:
        return signals
    
    controlled_signals = {}
    
    for symbol, signal_list in signals.items():
        new_signals = []
        
        for signal in signal_list:
            if signal_type == 'add':
                if margin_level == 'cautious':
                    # 谨慎操作区：加仓幅度减半
                    signal['amount'] = signal['amount'] // 2
                    signal['condition'] += " [加仓减半]"
                elif margin_level in ['risk_control', 'emergency']:
                    # 风险控制区和紧急区：不允许加仓
                    continue
            elif signal_type == 'reduce':
                if margin_level == 'risk_control':
                    # 风险控制区：仅允许小幅减仓
                    if signal['percentage'] > 30:
                        signal['percentage'] = 30
                        signal['condition'] += " [减仓限制30%]"
                elif margin_level == 'emergency':
                    # 紧急区：强制减仓
                    signal['percentage'] = min(signal['percentage'] * 2, 80)
                    signal['condition'] += " [紧急强制减仓]"
            
            new_signals.append(signal)
        
        if new_signals:
            controlled_signals[symbol] = new_signals
    
    return controlled_signals

def analyze_no_signal_reasons(positions: Optional[List], klines_data: Dict[str, List], trend_results: Dict[str, Dict], account_info: Optional[Dict], reduce_signals: Dict[str, List], add_signals: Dict[str, List]) -> None:
    """分析没有信号的原因"""
    if not positions or not klines_data:
        return
    
    print("\n=== 无操作原因分析 ===")
    
    for pos in positions:
        if float(pos.get('positionAmt', 0)) == 0:
            continue
            
        symbol = pos.get('symbol', '')
        if symbol not in klines_data or symbol not in trend_results:
            continue
            
        # 如果该币种已有信号，跳过分析
        if symbol in reduce_signals or symbol in add_signals:
            continue
            
        print(f"\n{symbol}:")
        
        entry_price = float(pos.get('entryPrice', 0))
        current_price = float(klines_data[symbol][-1][4])
        position_side = pos.get('positionSide', 'BOTH')
        trend = trend_results[symbol]['trend']
        
        reasons = []
        
        # 分析减仓条件
        if current_price > entry_price:
            profit_pct = ((current_price - entry_price) / entry_price) * 100
            
            # 获取减仓策略
            if symbol == "BTCUSDT":
                if trend == "强势上升":
                    reduce_strategy = BTC_STRONG_UP_REDUCE_POSITION
                elif trend == "弱势下降":
                    reduce_strategy = BTC_WEAK_DOWN_REDUCE_POSITION
                else:
                    reduce_strategy = BTC_REDUCE_POSITION
            elif symbol == "ETHUSDT":
                if trend == "强势上升":
                    reduce_strategy = ETH_STRONG_UP_REDUCE_POSITION
                elif trend == "弱势下降":
                    reduce_strategy = ETH_WEAK_DOWN_REDUCE_POSITION
                else:
                    reduce_strategy = ETH_REDUCE_POSITION
            else:
                reduce_strategy = []
            
            if reduce_strategy:
                min_reduce_threshold = min(threshold for threshold, _ in reduce_strategy)
                if profit_pct < min_reduce_threshold:
                    reasons.append(f"盈利{profit_pct:.2f}%未达减仓阈值{min_reduce_threshold}%")
        
        # 分析加仓条件
        else:
            loss_pct = ((current_price - entry_price) / entry_price) * 100
            
            # 检查操作频率
            daily_ops = check_operation_frequency(positions)
            if symbol in daily_ops:
                side_ops = daily_ops[symbol].get(position_side, 0)
                if side_ops >= MAX_DAILY_OPERATIONS_PER_SIDE:
                    side_names = {'LONG': '多头', 'SHORT': '空头', 'BOTH': '双向'}
                    side_name = side_names.get(position_side, position_side)
                    reasons.append(f"{side_name}方向今日已操作{side_ops}次，达到频率上限")
            
            # 检查仓位上限
            current_position_value = abs(float(pos.get('positionAmt', 0)) * entry_price)
            if symbol in MAX_POSITION_LIMITS:
                max_limit = MAX_POSITION_LIMITS[symbol]
                if current_position_value >= max_limit * 0.9:
                    reasons.append(f"仓位{current_position_value:.0f}U接近上限{max_limit}U")
            
            # 检查加仓策略阈值
            if symbol == "BTCUSDT":
                if trend == "弱势下降":
                    add_strategy = BTC_WEAK_DOWN_ADD_POSITION
                else:
                    add_strategy = BTC_ADD_POSITION_BELOW_COST
            elif symbol == "ETHUSDT":
                if trend == "弱势下降":
                    add_strategy = ETH_WEAK_DOWN_ADD_POSITION
                else:
                    add_strategy = OTHER_ADD_POSITION_BELOW_COST
            else:
                add_strategy = OTHER_ADD_POSITION_BELOW_COST
            
            if add_strategy:
                min_add_threshold = max(threshold for threshold, _ in add_strategy)  # 最大负值，即最小跌幅
                if loss_pct > min_add_threshold:
                    reasons.append(f"亏损{loss_pct:.2f}%未达加仓阈值{min_add_threshold}%")
        
        # 分析回调加仓条件
        if current_price > entry_price:
            high_5day = calculate_5day_high(klines_data[symbol])
            high_7day = calculate_7day_high(klines_data[symbol])
            
            # 根据趋势选择高点
            use_7day_high = trend == "强势上升"
            high_price = high_7day if use_7day_high else high_5day
            high_days = "7日" if use_7day_high else "5日"
            
            if high_price > 0:
                high_diff_pct = ((current_price - high_price) / high_price) * 100
                
                # 获取回调加仓策略
                if symbol == "BTCUSDT" and trend == "强势上升":
                    above_cost_strategy = BTC_STRONG_UP_ADD_POSITION
                elif symbol == "ETHUSDT" and trend == "强势上升":
                    above_cost_strategy = ETH_STRONG_UP_ADD_POSITION
                elif symbol == "BTCUSDT":
                    above_cost_strategy = BTC_ADD_POSITION_ABOVE_COST
                else:
                    above_cost_strategy = OTHER_ADD_POSITION_ABOVE_COST
                
                if above_cost_strategy:
                    min_callback_threshold = max(threshold for threshold, _ in above_cost_strategy)  # 最大负值
                    if high_diff_pct > min_callback_threshold:
                        reasons.append(f"从{high_days}高点回调{abs(high_diff_pct):.2f}%未达阈值{abs(min_callback_threshold)}%")
        
        # 显示原因
        if not reasons:
            reasons.append("当前价位不满足任何操作条件")
        
        for reason in reasons:
            print(f"  • {reason}")
        
        print(f"  当前状态: 成本{entry_price:.4f} 现价{current_price:.4f} 趋势{trend}")

def generate_signal_hash(reduce_signals: Dict[str, List], add_signals: Dict[str, List]) -> str:
    """生成信号的唯一标识哈希值"""
    signal_data = []
    
    # 减仓信号
    for symbol, signal_list in reduce_signals.items():
        for signal in signal_list:
            signal_key = f"{symbol}_{signal['type']}_{signal.get('percentage', 0)}"
            signal_data.append(signal_key)
    
    # 加仓信号
    for symbol, signal_list in add_signals.items():
        for signal in signal_list:
            signal_key = f"{symbol}_{signal['type']}_{signal.get('amount', 0)}_{signal.get('position_side', '')}"
            signal_data.append(signal_key)
    
    # 生成哈希
    signal_str = "_".join(sorted(signal_data))
    return str(hash(signal_str))

def should_send_notification(reduce_signals: Dict[str, List], add_signals: Dict[str, List]) -> bool:
    """检查是否应该发送通知（10分钟内不重复发送相同内容）"""
    global _notification_history
    
    if not reduce_signals and not add_signals:
        return False
    
    # 生成当前信号的哈希值
    current_hash = generate_signal_hash(reduce_signals, add_signals)
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

def send_dingtalk_notification(message: str, image_base64: Optional[str] = None) -> bool:
    """发送钉钉机器人通知"""
    if not ENABLE_DINGTALK_NOTIFICATION or not DINGTALK_WEBHOOK_URL:
        return False
    
    try:
        headers = {'Content-Type': 'application/json'}
        
        # 如果有图片且配置为分别发送
        if image_base64 and DINGTALK_SEND_IMAGE_SEPARATELY:
            # 发送文本消息
            text_data = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            response1 = requests.post(DINGTALK_WEBHOOK_URL, headers=headers, json=text_data, timeout=10)
            text_success = response1.status_code == 200
            
            try:
                # 解码图片数据
                img_data = base64.b64decode(image_base64)
                
                # 保存图片到本地
                local_img_path = CHART_IMAGE_FILE
                with open(local_img_path, 'wb') as f:
                    f.write(img_data)
                print(f"📊 盈亏走势图已保存到: {local_img_path}")
                
                # 发送图片消息
                image_data = {
                    "msgtype": "image",
                    "image": {
                        "base64": image_base64,
                        "md5": hashlib.md5(img_data).hexdigest()
                    }
                }
                
                response2 = requests.post(DINGTALK_WEBHOOK_URL, headers=headers, json=image_data, timeout=10)
                image_success = response2.status_code == 200
                
                if image_success:
                    print("✅ 钉钉图片发送成功")
                else:
                    print(f"❌ 钉钉图片发送失败: {response2.status_code}, {response2.text}")
                
                return text_success and image_success
                
            except Exception as e:
                print(f"发送图片失败: {e}")
                return text_success
        
        else:
            # 只发送文本消息（或图片发送失败时的后备方案）
            if image_base64:
                try:
                    # 仍然保存图片到本地
                    img_data = base64.b64decode(image_base64)
                    local_img_path = CHART_IMAGE_FILE
                    with open(local_img_path, 'wb') as f:
                        f.write(img_data)
                    print(f"📊 盈亏走势图已保存到: {local_img_path}")
                    
                    # 在消息中添加图片说明
                    message += f"\n\n📊 盈亏走势图已生成，请查看本地文件: {local_img_path}"
                    
                except Exception as e:
                    print(f"保存图片失败: {e}")
                    message += "\n\n❌ 图片生成失败"
            
            # 发送文本消息
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

def format_signals_for_notification(reduce_signals: Dict[str, List], add_signals: Dict[str, List]) -> Tuple[str, Optional[str]]:
    """格式化信号为钉钉通知消息，返回消息文本和图片base64"""
    messages = []
    messages.append("🚨 币安交易提醒 🚨")
    messages.append(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
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
                    messages.append(f"   建议减仓: {signal['percentage']}%")
                else:
                    messages.append(f"🔸 {symbol}: {signal['condition']}")
                    messages.append(f"   建议减仓: {signal['percentage']}%")
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
    
    if not reduce_signals and not add_signals:
        messages.append("✅ 当前无操作信号")
        messages.append("持续监控中...")
    
    # 生成盈亏走势图
    image_base64 = None
    if ENABLE_CHART_IMAGE:
        image_base64 = generate_pnl_chart_image()
        # 不在这里添加图片提示，会在发送时添加
    else:
        # 使用文本图表
        chart_data = generate_pnl_chart_data()
        if chart_data:
            chart_text = format_pnl_chart(chart_data)
            messages.append("")
            messages.append(chart_text)
    
    return "\n".join(messages), image_base64

def check_pnl_ratio_reduce_signals(account_info: Optional[Dict]) -> Dict[str, List]:
    """检查基于未实现盈亏占比的减仓信号"""
    if not account_info:
        return {}
    
    total_wallet = float(account_info.get('totalWalletBalance', 0))
    total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    
    if total_wallet == 0 or total_pnl <= 0:
        return {}
    
    pnl_ratio = (total_pnl / total_wallet) * 100
    
    signals = {}
    
    for threshold, percentage in PNL_RATIO_REDUCE_STRATEGY:
        if pnl_ratio >= threshold:
            signals['SYSTEM'] = [{
                'type': '盈亏比例减仓',
                'condition': f'未实现盈亏{total_pnl:.2f}U占总余额{total_wallet:.2f}U的{pnl_ratio:.2f}% >= {threshold}%',
                'percentage': percentage,
                'pnl_ratio': pnl_ratio,
                'total_pnl': total_pnl,
                'total_wallet': total_wallet,
                'triggered': True
            }]
            break
    
    return signals

def generate_reduce_position_signals(positions: Optional[List], klines_data: Dict[str, List], trend_results: Dict[str, Dict], account_info: Optional[Dict]) -> Dict[str, List]:
    """生成减仓信号"""
    if not positions or not klines_data:
        return {}
    
    signals = {}
    
    for pos in positions:
        if float(pos.get('positionAmt', 0)) == 0:
            continue
            
        symbol = pos.get('symbol', '')
        if symbol not in klines_data or symbol not in trend_results:
            continue
            
        entry_price = float(pos.get('entryPrice', 0))
        current_price = float(klines_data[symbol][-1][4])
        
        if entry_price == 0 or current_price <= entry_price:
            continue
            
        cost_profit_pct = ((current_price - entry_price) / entry_price) * 100
        trend = trend_results[symbol]['trend']
        
        # 根据趋势选择策略配置
        if symbol == "BTCUSDT":
            if trend == "强势上升":
                reduce_strategy = BTC_STRONG_UP_REDUCE_POSITION
            elif trend == "弱势下降":
                reduce_strategy = BTC_WEAK_DOWN_REDUCE_POSITION
            else:
                reduce_strategy = BTC_REDUCE_POSITION
        elif symbol == "ETHUSDT":
            if trend == "强势上升":
                reduce_strategy = ETH_STRONG_UP_REDUCE_POSITION
            elif trend == "弱势下降":
                reduce_strategy = ETH_WEAK_DOWN_REDUCE_POSITION
            else:
                reduce_strategy = ETH_REDUCE_POSITION
        else:
            continue
        
        position_signals = []
        
        for threshold, percentage in reduce_strategy:
            if cost_profit_pct >= threshold:
                position_signals.append({
                    'type': '减仓',
                    'condition': f'从成本价{entry_price:.4f}涨到{current_price:.4f}，盈利{cost_profit_pct:.2f}%',
                    'percentage': percentage,
                    'current_profit': cost_profit_pct,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'trend': trend,
                    'triggered': True
                })
                break
        
        if position_signals:
            signals[symbol] = position_signals
    
    # 应用保证金控制
    margin_ratio = calculate_margin_ratio(account_info)
    margin_level = get_margin_level(margin_ratio)
    signals = apply_margin_control(signals, margin_level, 'reduce')
    
    return signals

def generate_add_position_signals(positions: Optional[List], klines_data: Dict[str, List], trend_results: Dict[str, Dict], account_info: Optional[Dict], reduce_signals: Dict[str, List]) -> Dict[str, List]:
    """生成加仓信号"""
    if not positions or not klines_data:
        return {}
    
    signals = {}
    
    for pos in positions:
        if float(pos.get('positionAmt', 0)) == 0:
            continue
            
        symbol = pos.get('symbol', '')
        if symbol not in klines_data or symbol not in trend_results:
            continue
            
        # 如果该symbol已有减仓信号，则不生成加仓信号
        if symbol in reduce_signals:
            continue
            
        # 检查操作频率限制
        position_side = pos.get('positionSide', 'BOTH')
        daily_ops = check_operation_frequency(positions)
        
        if symbol in daily_ops:
            side_ops = daily_ops[symbol].get(position_side, 0)
            if side_ops >= MAX_DAILY_OPERATIONS_PER_SIDE:
                continue  # 该方向今日操作次数已达上限，不打印信息
            
        # 检查仓位上限
        entry_price = float(pos.get('entryPrice', 0))
        current_position_value = abs(float(pos.get('positionAmt', 0)) * entry_price)
        
        if symbol in MAX_POSITION_LIMITS:
            max_limit = MAX_POSITION_LIMITS[symbol]
            if current_position_value >= max_limit * 0.9:  # 90%时就停止加仓
                continue
        current_price = float(klines_data[symbol][-1][4])
        high_5day = calculate_5day_high(klines_data[symbol])
        high_7day = calculate_7day_high(klines_data[symbol])
        trend = trend_results[symbol]['trend']
        
        if entry_price == 0:
            continue
            
        # 根据趋势选择策略配置
        if symbol == "BTCUSDT":
            if trend == "强势上升":
                below_cost_strategy = BTC_ADD_POSITION_BELOW_COST
                above_cost_strategy = BTC_STRONG_UP_ADD_POSITION
                use_7day_high = True
            elif trend == "弱势下降":
                below_cost_strategy = BTC_WEAK_DOWN_ADD_POSITION
                above_cost_strategy = BTC_ADD_POSITION_ABOVE_COST
                use_7day_high = False
            else:
                below_cost_strategy = BTC_ADD_POSITION_BELOW_COST
                above_cost_strategy = BTC_ADD_POSITION_ABOVE_COST
                use_7day_high = False
        elif symbol == "ETHUSDT":
            if trend == "强势上升":
                below_cost_strategy = OTHER_ADD_POSITION_BELOW_COST
                above_cost_strategy = ETH_STRONG_UP_ADD_POSITION
                use_7day_high = True
            elif trend == "弱势下降":
                below_cost_strategy = ETH_WEAK_DOWN_ADD_POSITION
                above_cost_strategy = OTHER_ADD_POSITION_ABOVE_COST
                use_7day_high = False
            else:
                below_cost_strategy = OTHER_ADD_POSITION_BELOW_COST
                above_cost_strategy = OTHER_ADD_POSITION_ABOVE_COST
                use_7day_high = False
        else:
            below_cost_strategy = OTHER_ADD_POSITION_BELOW_COST
            above_cost_strategy = OTHER_ADD_POSITION_ABOVE_COST
            use_7day_high = False
        
        position_signals = []
        
        if current_price <= entry_price:
            # 价格低于持仓成本
            cost_diff_pct = ((current_price - entry_price) / entry_price) * 100
            
            for threshold, amount in below_cost_strategy:
                if cost_diff_pct <= threshold:
                    position_signals.append({
                        'type': '成本加仓',
                        'condition': f'从成本价{entry_price:.4f}跌到{current_price:.4f}，相对成本{cost_diff_pct:.2f}%',
                        'amount': amount,
                        'current_diff': cost_diff_pct,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'position_side': position_side,
                        'trend': trend,
                        'triggered': True
                    })
                    break
        else:
            # 价格高于持仓成本
            high_price = high_7day if use_7day_high else high_5day
            high_days = "7日" if use_7day_high else "5日"
            
            if high_price > 0:
                high_diff_pct = ((current_price - high_price) / high_price) * 100
                
                for threshold, amount in above_cost_strategy:
                    if high_diff_pct <= threshold:
                        position_signals.append({
                            'type': '回调加仓',
                            'condition': f'从{high_days}高点{high_price:.4f}回调到{current_price:.4f}，回调{abs(high_diff_pct):.2f}%',
                            'amount': amount,
                            'current_diff': high_diff_pct,
                            'high_price': high_price,
                            'current_price': current_price,
                            'position_side': position_side,
                            'trend': trend,
                            'triggered': True
                        })
                        break
        
        if position_signals:
            signals[symbol] = position_signals
    
    # 应用保证金控制
    margin_ratio = calculate_margin_ratio(account_info)
    margin_level = get_margin_level(margin_ratio)
    signals = apply_margin_control(signals, margin_level, 'add')
    
    return signals

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
            print(f"  建议减仓: {signal['percentage']}%")

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
    
    # 显示盈亏走势图
    chart_data = generate_pnl_chart_data()
    if chart_data:
        print("\n" + format_pnl_chart(chart_data))

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

def record_pnl_only() -> None:
    """仅记录盈亏数据（用于定时任务）"""
    try:
        account_info = get_account_info()
        if account_info:
            record_pnl(account_info)
            total_pnl = float(account_info.get('totalUnrealizedProfit', 0))
            print(f"📊 记录盈亏: {total_pnl:.2f}U - {time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"❌ 记录盈亏失败: {e}")

def run_analysis() -> None:
    """执行一次完整的分析"""
    print(f"\n{'='*50}")
    print(f"开始分析 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    try:
        # 获取K线数据
        all_data = get_multiple_symbols_data()
        if not all_data:
            print("无法获取K线数据")
            return
        
        # 显示K线数据概览
        for symbol, klines in all_data.items():
            if klines:
                print(f"\n{symbol} - 获取到 {len(klines)} 条K线数据")
                print("最后5条数据的涨跌和振幅:")
                for kline in klines[-5:]:
                    if len(kline) >= 15:  # 确保有扩展数据
                        print(f"时间: {kline[0]}, 涨跌: {kline[-3]:.4f} ({kline[-2]:.2f}%), 振幅: {kline[-1]:.2f}%")
        
        # 趋势识别分析
        trend_results = calculate_trend_indicators(all_data)
        print_trend_analysis(trend_results)
        
        # 获取账户信息和持仓
        account_info = get_account_info()
        print_account_info(account_info)
        
        # 记录盈亏数据
        record_pnl(account_info)
        
        positions = get_positions()
        print_positions(positions)
        
        # 检查硬性风控红线
        risk_warnings = check_risk_control(positions, account_info)
        print_risk_warnings(risk_warnings)
        
        # 显示今日操作频率
        print_operation_frequency(positions)
        
        # 检查未实现盈亏占比减仓信号
        pnl_ratio_signals = check_pnl_ratio_reduce_signals(account_info)
        
        # 生成减仓信号
        reduce_signals = generate_reduce_position_signals(positions, all_data, trend_results, account_info)
        
        # 合并盈亏比例减仓信号
        if pnl_ratio_signals:
            reduce_signals.update(pnl_ratio_signals)
        
        print_reduce_position_signals(reduce_signals)
        
        # 生成加仓信号（排除已有减仓信号的产品）
        add_signals = generate_add_position_signals(positions, all_data, trend_results, account_info, reduce_signals)
        print_add_position_signals(add_signals)
        
        # 分析没有操作信号的原因
        analyze_no_signal_reasons(positions, all_data, trend_results, account_info, reduce_signals, add_signals)
        
        # 显示盈亏统计
        print_pnl_statistics()
        
        # 生成并打印钉钉通知内容
        if reduce_signals or add_signals:
            notification_message, image_base64 = format_signals_for_notification(reduce_signals, add_signals)
            print("\n" + "="*60)
            print("📱 钉钉通知内容:")
            print("="*60)
            print(notification_message)
            if image_base64:
                print("📊 盈亏走势图已生成")
            print("="*60)
            
            # 检查是否应该发送
            if should_send_notification(reduce_signals, add_signals):
                success = send_dingtalk_notification(notification_message, image_base64)
                if success:
                    print("✅ 钉钉通知发送成功")
                elif ENABLE_DINGTALK_NOTIFICATION:
                    print("❌ 钉钉通知发送失败")
            else:
                print("⏭️ 相同信号已在10分钟内发送，跳过钉钉通知")
                
    except Exception as e:
        print(f"❌ 分析执行失败: {e}")
        # 发送错误通知
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