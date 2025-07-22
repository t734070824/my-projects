import requests
import json
import time
import hmac
import hashlib
from urllib.parse import urlencode
from config import BINANCE_API_URL, SYMBOLS, INTERVAL, TIMEZONE, USE_PROXY
from api_keys import API_KEY, SECRET_KEY

def calculate_change_and_amplitude(klines):
    """计算每条数据的涨跌和振幅，并将结果添加到klines中"""
    if len(klines) < 2:
        return klines
    
    for i in range(1, len(klines)):
        current = klines[i]
        previous = klines[i-1]
        
        # 解析数据
        current_close = float(current[4])  # 当前收盘价
        previous_close = float(previous[4])  # 前一条收盘价
        current_high = float(current[2])   # 当前最高价
        current_low = float(current[3])    # 当前最低价
        
        # 计算涨跌
        change = current_close - previous_close
        change_percent = (change / previous_close) * 100
        
        # 计算振幅
        amplitude = ((current_high - current_low) / previous_close) * 100
        
        # 将计算结果添加到klines中
        current.extend([change, change_percent, amplitude])
    
    return klines

def get_binance_klines(symbol):
    """从币安获取指定symbol的K线数据"""
    url = f"{BINANCE_API_URL}?symbol={symbol}&interval={INTERVAL}&timeZone={TIMEZONE}"
    
    proxies = None if USE_PROXY else {'http': None, 'https': None}
    response = requests.get(url, proxies=proxies)
    response.raise_for_status()
    data = response.json()
    return data

def get_multiple_symbols_data():
    """获取多个symbol的K线数据"""
    all_data = {}
    for symbol in SYMBOLS:
        klines = get_binance_klines(symbol)
        klines_with_indicators = calculate_change_and_amplitude(klines)
        all_data[symbol] = klines_with_indicators
    return all_data

def create_signature(query_string):
    """创建币安API签名"""
    return hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_account_info():
    """获取账户基本信息"""
    if not API_KEY or not SECRET_KEY:
        print("请先配置API_KEY和SECRET_KEY")
        return None
    
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v2/account"
    
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = create_signature(query_string)
    
    url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    proxies = None if USE_PROXY else {'http': None, 'https': None}
    response = requests.get(url, headers=headers, proxies=proxies)
    response.raise_for_status()
    
    return response.json()

def get_positions():
    """获取合约持仓信息"""
    if not API_KEY or not SECRET_KEY:
        print("请先配置API_KEY和SECRET_KEY")
        return None
    
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v3/positionRisk"
    
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = create_signature(query_string)
    
    url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    proxies = None if USE_PROXY else {'http': None, 'https': None}
    response = requests.get(url, headers=headers, proxies=proxies)
    response.raise_for_status()
    
    return response.json()

def print_account_info(account_info):
    """打印账户信息"""
    if not account_info:
        return
        
    print("\n=== 账户基本信息 ===")
    print(f"总余额: {float(account_info['totalWalletBalance']):.4f} USDT")
    print(f"可用余额: {float(account_info['availableBalance']):.4f} USDT")
    print(f"未实现盈亏: {float(account_info['totalUnrealizedProfit']):.4f} USDT")
    print(f"保证金余额: {float(account_info['totalMarginBalance']):.4f} USDT")

def print_positions(positions):
    """打印持仓信息"""
    if not positions:
        return
        
    print("\n=== 合约持仓信息 ===")
    active_positions = [pos for pos in positions if float(pos['positionAmt']) != 0]
    
    if not active_positions:
        print("当前无持仓")
        return
        
    for pos in active_positions:
        symbol = pos['symbol']
        position_side = pos['positionSide']
        size = float(pos['positionAmt'])
        entry_price = float(pos['entryPrice'])
        break_even_price = float(pos['breakEvenPrice'])
        mark_price = float(pos['markPrice'])
        pnl = float(pos['unRealizedProfit'])
        liquidation_price = float(pos['liquidationPrice'])
        isolated_margin = float(pos['isolatedMargin'])
        notional = float(pos['notional'])
        margin_asset = pos['marginAsset']
        isolated_wallet = float(pos['isolatedWallet'])
        initial_margin = float(pos['initialMargin'])
        maint_margin = float(pos['maintMargin'])
        position_initial_margin = float(pos['positionInitialMargin'])
        open_order_initial_margin = float(pos['openOrderInitialMargin'])
        adl = pos['adl']
        bid_notional = float(pos['bidNotional'])
        ask_notional = float(pos['askNotional'])
        update_time = pos['updateTime']
        
        side = "多头" if size > 0 else "空头"
        
        print(f"\n{symbol} ({position_side}):")
        print(f"  方向: {side}")
        print(f"  开仓价: {entry_price:.6f}")
        print(f"  未实现盈亏: {pnl:.4f} {margin_asset}")
        print(f"  强平价: {liquidation_price:.6f}" if liquidation_price > 0 else "  强平价: 无")
        print(f"  仓位初始保证金: {position_initial_margin:.4f} {margin_asset}")
        print(f"  更新时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(update_time/1000))}")

def calculate_trend_indicators(klines_data):
    """计算趋势识别指标"""
    trend_results = {}
    
    # 获取BTC的7日涨跌幅作为基准
    btc_change_7d = 0
    if "BTCUSDT" in klines_data:
        btc_klines = klines_data["BTCUSDT"]
        if len(btc_klines) >= 168:
            btc_start_price = float(btc_klines[-168][4])
            btc_end_price = float(btc_klines[-1][4])
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
        
        # 强势上升趋势（增加相对BTC强势条件）
        if (change_7d > 15 and 
            consecutive_green >= 5 and
            (symbol == "BTCUSDT" or relative_to_btc > 8)):
            trend = "强势上升"
            
        # 弱势下降趋势  
        elif (change_7d < -12 and 
              consecutive_red >= 4):
            trend = "弱势下降"
            
        # 横盘震荡
        elif (-8 <= change_7d <= 8 and 
              abs(distance_from_ma20) <= 5):
            trend = "横盘震荡"
            
        # 温和上升趋势
        elif (8 < change_7d <= 15):
            trend = "温和上升"
            
        # 温和下降趋势
        elif (-12 <= change_7d < -8):
            trend = "温和下降"
            
        # 高位调整
        elif (change_7d > 8 and 
              distance_from_ma20 < -5):
            trend = "高位调整"
            
        # 低位反弹
        elif (change_7d < -8 and 
              distance_from_ma20 > 5):
            trend = "低位反弹"
            
        # 其他情况
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

def print_trend_analysis(trend_results):
    """打印趋势分析结果"""
    print("\n=== 趋势识别分析 ===")
    
    for symbol, data in trend_results.items():
        print(f"\n{symbol}:")
        print(f"  趋势: {data['trend']}")
        print(f"  7日涨跌幅: {data['change_7d']:.2f}%")
        if symbol != "BTCUSDT":
            relative_status = "强势" if data['relative_to_btc'] > 0 else "弱势"
            print(f"  相对BTC: {relative_status} {data['relative_to_btc']:.2f}%")
        print(f"  连续收阳: {data['consecutive_green']}天")
        print(f"  连续收阴: {data['consecutive_red']}天")
        print(f"  当前价格: {data['current_price']:.4f}")
        print(f"  20日均线: {data['ma20']:.4f}")
        print(f"  偏离20日均线: {data['distance_from_ma20']:.2f}%")

if __name__ == "__main__":
    all_data = get_multiple_symbols_data()
    
    for symbol, klines in all_data.items():
        print(f"\n{symbol} - 获取到 {len(klines)} 条K线数据")
        print(f"最后5条数据的涨跌和振幅:")
        for kline in klines[-5:]:
            print(f"时间: {kline[0]}, 涨跌: {kline[-3]:.4f} ({kline[-2]:.2f}%), 振幅: {kline[-1]:.2f}%")
    
    # 趋势识别分析
    trend_results = calculate_trend_indicators(all_data)
    print_trend_analysis(trend_results)
    
    # 获取账户信息和持仓
    account_info = get_account_info()
    print_account_info(account_info)
    
    positions = get_positions()
    print_positions(positions) 