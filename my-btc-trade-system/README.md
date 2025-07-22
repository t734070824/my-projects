# BTC交易风险提示系统

一个基于币安API的比特币交易风险分析系统，能够实时获取BTCUSDT的K线数据并进行风险分析。

## 项目结构

```
my-btc-trade-system/
├── main.py              # 主程序文件
├── config.py            # 配置文件
├── requirements.txt      # 项目依赖
└── README.md           # 项目说明文档
```

## 功能特性

### 🔍 数据获取
- 从币安官方API获取BTCUSDT K线数据
- 支持自定义交易对、时间间隔和数据量
- 自动重试机制和错误处理
- 数据缓存和日志记录

### 📊 技术分析
- 移动平均线计算 (MA5, MA10, MA20, MA50)
- 价格变化率分析
- 成交量变化分析
- 波动率计算

### ⚠️ 风险提示
- 价格异常变化检测
- 成交量突增预警
- 高波动率提醒
- 分级风险提示 (HIGH/MEDIUM)

## 安装和运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 测试网络连接（推荐）
```bash
python test_connection.py
```

### 3. 运行程序
```bash
python main.py
```

## 配置说明

### API配置 (config.py)
```python
BINANCE_API_CONFIG = {
    'base_url': 'https://data-api.binance.vision/api/v3/klines',
    'default_symbol': 'BTCUSDT',    # 默认交易对
    'default_interval': '1h',       # 默认时间间隔
    'default_limit': 100,           # 默认获取数量
    'timeout': 30                   # 请求超时时间
}
```

### 风险分析配置
```python
RISK_ANALYSIS_CONFIG = {
    'price_change_threshold': 0.05,  # 价格变化阈值 (5%)
    'volume_spike_threshold': 2.0,   # 成交量突增阈值 (200%)
    'volatility_threshold': 0.03,    # 波动率阈值
    'ma_periods': [5, 10, 20, 50],  # 移动平均线周期
    'rsi_period': 14,               # RSI周期
    'rsi_overbought': 70,          # RSI超买线
    'rsi_oversold': 30             # RSI超卖线
}
```

## 输出示例

```
==================================================
BTC交易风险提示系统 - 分析结果
==================================================

最新价格: $106421.08
价格变化: -0.15%
成交量: 284.29

最新 10 条数据:
           open_time     open     high      low    close   volume
2024-01-01 12:00:00 106605.79 106706.05 106365.24 106421.08  284.29
2024-01-01 13:00:00 106421.07 106885.38 106301.04 106807.42 1241.44
...

✅ 当前无明显风险
```

## 风险提示类型

### 🔴 HIGH级别风险
- 价格变化超过10%
- 成交量突增超过200%

### 🟡 MEDIUM级别风险
- 价格变化超过5%
- 波动率超过阈值

## 日志文件

系统运行时会生成 `trading_system.log` 日志文件，记录：
- 数据获取状态
- 错误信息
- 系统运行日志

## 依赖包

- `requests`: HTTP请求库
- `pandas`: 数据处理库
- `numpy`: 数值计算库

## 网络连接问题

如果遇到网络连接问题，可以尝试以下解决方案：

### 1. 运行连接测试
```bash
python test_connection.py
```

### 2. 修改配置文件
在 `config.py` 中调整以下设置：
```python
DATA_FETCH_CONFIG = {
    'enable_ssl_verify': False,  # 禁用SSL验证
    'enable_proxy': False,       # 禁用代理
    # ...
}
```

### 3. 常见问题解决
- **SSL错误**: 设置 `enable_ssl_verify: False`
- **代理错误**: 设置 `enable_proxy: False`
- **超时错误**: 增加 `timeout` 值
- **网络限制**: 尝试使用VPN或更换网络

## 注意事项

1. 本系统仅用于风险提示，不构成投资建议
2. 请根据实际情况调整风险阈值参数
3. 建议在实盘交易前充分测试
4. 币安API可能有访问频率限制
5. 如遇到网络问题，请先运行连接测试脚本

## 扩展功能

可以进一步添加的功能：
- 更多技术指标 (RSI, MACD, Bollinger Bands)
- 图形化界面
- 实时监控和报警
- 历史数据分析
- 多币种支持 