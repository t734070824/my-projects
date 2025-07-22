import requests
import json
import time
import hmac
import hashlib
from typing import Dict, List, Optional, Any
from config import *
from api_keys import API_KEY, SECRET_KEY

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
    total_wallet = float(account_info.get('totalWalletBalance', 0))
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
        
        print(f"\n{symbol} ({position_side}):")
        print(f"  方向: {side}")
        
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

def main() -> None:
    """主函数"""
    print("=== 币安交易风险提示系统 ===")
    
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
    
    positions = get_positions()
    print_positions(positions)
    
    # 检查硬性风控红线
    risk_warnings = check_risk_control(positions, account_info)
    print_risk_warnings(risk_warnings)
    
    # 显示今日操作频率
    print_operation_frequency(positions)
    
    # 生成减仓信号
    reduce_signals = generate_reduce_position_signals(positions, all_data, trend_results, account_info)
    print_reduce_position_signals(reduce_signals)
    
    # 生成加仓信号（排除已有减仓信号的产品）
    add_signals = generate_add_position_signals(positions, all_data, trend_results, account_info, reduce_signals)
    print_add_position_signals(add_signals)
    
    # 分析没有操作信号的原因
    analyze_no_signal_reasons(positions, all_data, trend_results, account_info, reduce_signals, add_signals)

if __name__ == "__main__":
    main() 