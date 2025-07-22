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
    proxies = None if USE_PROXY else {'http': None, 'https': None}
    
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
        # 提取关键信息
        symbol = pos.get('symbol', '')
        position_side = pos.get('positionSide', '')
        size = float(pos.get('positionAmt', 0))
        entry_price = float(pos.get('entryPrice', 0))
        pnl = float(pos.get('unRealizedProfit', 0))
        liquidation_price = float(pos.get('liquidationPrice', 0))
        position_initial_margin = float(pos.get('positionInitialMargin', 0))
        margin_asset = pos.get('marginAsset', 'USDT')
        update_time = pos.get('updateTime', 0)
        
        side = "多头" if size > 0 else "空头"
        
        print(f"\n{symbol} ({position_side}):")
        print(f"  方向: {side}")
        print(f"  开仓价: {entry_price:.6f}")
        print(f"  未实现盈亏: {pnl:.4f} {margin_asset}")
        print(f"  强平价: {liquidation_price:.6f}" if liquidation_price > 0 else "  强平价: 无")
        print(f"  仓位初始保证金: {position_initial_margin:.4f} {margin_asset}")
        print(f"  更新时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(update_time/1000))}")

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

if __name__ == "__main__":
    main() 