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