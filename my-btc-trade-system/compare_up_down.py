from config import SYMBOLS, INTERVAL, TIMEZONE, BINANCE_KLINES_ENDPOINT
from data_provider import make_api_request
from analysis import calculate_change_and_amplitude

def calculate_trend_correlation(result: dict) -> dict:
    """
    计算其他交易对与BTCUSDT的每日趋势（涨跌）相关性百分比。
    """
    correlation_results = {}
    if "BTCUSDT" not in result:
        print("错误：分析结果中未找到 BTCUSDT 的数据，无法进行相关性计算。")
        return {}

    # BTC的K线数据，从第二条开始才有涨跌幅数据
    btc_klines = result["BTCUSDT"][1:]
    if not btc_klines:
        print("错误：BTCUSDT 的数据不足，无法计算相关性。")
        return {}

    # 遍历所有其他交易对
    for symbol, klines in result.items():
        if symbol == "BTCUSDT":
            continue

        other_klines = klines[1:] # 同样从第二条开始
        
        # 确保数据长度匹配，以较短的为准
        comparison_days = min(len(btc_klines), len(other_klines))
        if comparison_days == 0:
            correlation_results[symbol] = 0
            continue

        same_trend_days = 0
        for i in range(comparison_days):
            # change_percent 在倒数第二位 (索引 -2)
            btc_change = btc_klines[i][-2]
            other_change = other_klines[i][-2]

            # 判断涨跌方向是否相同
            # 同为正数（同涨）或同为负数（同跌）
            if (btc_change > 0 and other_change > 0) or (btc_change < 0 and other_change < 0):
                same_trend_days += 1

        
        # 计算百分比
        correlation_percentage = (same_trend_days / comparison_days) * 100
        correlation_results[symbol] = correlation_percentage
        
    return correlation_results

def main() -> None:
    """
    主函数，获取数据、计算涨跌幅并进行趋势相关性分析。
    """
    result = {}
    for symbol in SYMBOLS:
        # 获取日K数据
        params = {'symbol': symbol, 'interval': '1d', 'timeZone': TIMEZONE, 'limit': 100} # 获取最近100天的数据
        klines = make_api_request(BINANCE_KLINES_ENDPOINT, params)
        
        if klines:
            # 计算每日的涨跌幅和振幅
            # 注意：calculate_change_and_amplitude 会直接修改 klines 列表
            result[symbol] = calculate_change_and_amplitude(klines)

    # 计算并打印与BTC的趋势相关性
    if result:
        correlation = calculate_trend_correlation(result)
        print("\n--- 与 BTCUSDT 每日趋势相关性分析 ---")
        if correlation:
            for symbol, percentage in correlation.items():
                print(f"{symbol}: {percentage:.2f}% 的天数与 BTC 走势相同")
        else:
            print("未能计算任何交易对的相关性。")
    else:
        print("未能获取任何K线数据。")

    return

if __name__ == "__main__":
    main()