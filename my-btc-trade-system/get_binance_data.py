import requests
import json
from config import BINANCE_API_URL, SYMBOL, INTERVAL, TIMEZONE
from calculate_indicators import calculate_change_and_amplitude

def get_binance_klines():
    """从币安获取合约BTCUSDT的K线数据"""
    url = f"{BINANCE_API_URL}?symbol={SYMBOL}&interval={INTERVAL}&timeZone={TIMEZONE}"
    
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data

if __name__ == "__main__":
    klines = get_binance_klines()
    print(f"获取到 {len(klines)} 条K线数据")
    
    # 计算每条数据的涨跌和振幅，并添加到klines中
    klines_with_indicators = calculate_change_and_amplitude(klines)
    print(f"\n计算了 {len(klines_with_indicators)} 条数据的涨跌和振幅:")
    for kline in klines_with_indicators[-5:]:  # 显示最后5条
        print(f"时间: {kline[0]}, 涨跌: {kline[-3]:.4f} ({kline[-2]:.2f}%), 振幅: {kline[-1]:.2f}%") 