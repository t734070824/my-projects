# FreqTrade 策略文件

基于原交易系统策略逻辑转换的 FreqTrade 策略文件包。

## 📁 文件结构

```
freqtrade/
├── strategies/
│   ├── TripleTimeframeTrendStrategy.py    # 三重时间框架趋势跟踪策略
│   └── AggressiveReversalStrategy.py      # 激进反转策略
├── config/
│   ├── config.json                        # 通用配置文件
│   ├── config_trend.json                  # 趋势策略专用配置
│   └── config_reversal.json               # 反转策略专用配置
└── README.md                              # 本说明文档
```

## 🎯 策略说明

### 1. 三重时间框架趋势跟踪策略 (TripleTimeframeTrendStrategy)

**策略理念**: 基于原系统的稳健趋势跟踪逻辑，通过三个时间框架的过滤确保高胜率。

**核心逻辑**:
- **战略层面 (1d)**: 判断长期趋势方向 (评分 > 0 看多，< 0 看空)
- **战术层面 (4h)**: 判断中期趋势方向
- **执行层面 (1h)**: 寻找具体入场信号

**开仓条件**:
- **做多**: 1d看多 AND 4h看多 AND 1h评分≥2
- **做空**: 1d看空 AND 4h看空 AND 1h评分≤-2

**技术指标**:
- SMA (20/50)
- MACD (12,26,9)  
- RSI (14)
- 布林带 (20,2)
- 一目均衡表
- ATR (14) - 动态止损

**风险参数**:
- 止损: 5% 或 2倍ATR
- 目标: 20%/30% (对应2R/3R)
- 追踪止损: 盈利2%后启用

### 2. 激进反转策略 (AggressiveReversalStrategy)

**策略理念**: 基于原系统的反转策略，在极值位置寻找反转机会。

**核心逻辑**:
- 在1小时图寻找市场过度延伸的反转机会
- 高风险高回报的短线策略

**开仓条件**:
- **做多 (抄底)**: RSI ≤ 28 AND 价格触及布林下轨
- **做空 (摸顶)**: RSI ≥ 72 AND 价格触及布林上轨

**技术指标**:
- RSI (14) - 超买/超卖判断
- 布林带 (20,2) - 价格极值位置
- ATR (14) - 动态止损
- 成交量 - 确认信号

**风险参数**:
- 止损: 3% 或 1.5倍ATR  
- 目标: 15%/20% (对应1.5R/2R)
- 追踪止损: 盈利1%后启用

## ⚙️ 配置文件说明

### config.json (通用配置)
- 最大开仓数: 8
- 交易模式: 期货 (futures)
- 保证金模式: 逐仓 (isolated)
- 模拟交易: 启用 (dry_run: true)

### config_trend.json (趋势策略)
- 最大开仓数: 5 (稳健型)
- 交易对: 主流大市值币种
- 处理间隔: 5秒 (较稳定)

### config_reversal.json (反转策略) 
- 最大开仓数: 3 (高风险控制)
- 交易对: 包含高波动币种
- 处理间隔: 3秒 (更快响应)
- 订单超时: 5分钟 (更短)

## 🚀 使用方法

### 1. 安装 FreqTrade

```bash
# 安装 FreqTrade
pip install freqtrade

# 或使用 Docker
docker pull freqtradeorg/freqtrade:stable
```

### 2. 配置 API 密钥

编辑配置文件中的 API 设置:

```json
"exchange": {
    "name": "binance",
    "key": "YOUR_API_KEY",
    "secret": "YOUR_SECRET_KEY"
}
```

### 3. 运行策略

**趋势跟踪策略**:
```bash
freqtrade trade --config ./config/config_trend.json --strategy TripleTimeframeTrendStrategy
```

**反转策略**:
```bash  
freqtrade trade --config ./config/config_reversal.json --strategy AggressiveReversalStrategy
```

### 4. 回测策略

```bash
# 趋势策略回测
freqtrade backtesting --config ./config/config_trend.json --strategy TripleTimeframeTrendStrategy --timerange 20240101-20241201

# 反转策略回测  
freqtrade backtesting --config ./config/config_reversal.json --strategy AggressiveReversalStrategy --timerange 20240101-20241201
```

### 5. 超参数优化

```bash
# 趋势策略优化
freqtrade hyperopt --config ./config/config_trend.json --strategy TripleTimeframeTrendStrategy --hyperopt-loss SharpeHyperOptLoss --epochs 100

# 反转策略优化
freqtrade hyperopt --config ./config/config_reversal.json --strategy AggressiveReversalStrategy --hyperopt-loss ProfitLossHyperOptLoss --epochs 100
```

## 📊 策略特点对比

| 特性 | 趋势跟踪策略 | 反转策略 |
|------|------------|---------|
| 风险等级 | 中等 | 高 |
| 持仓时间 | 数小时到数天 | 数分钟到数小时 |
| 胜率 | 较高 (40-60%) | 中等 (30-50%) |
| 盈亏比 | 高 (2-3R) | 中等 (1.5-2R) |
| 最大开仓 | 5个 | 3个 |
| 适用市场 | 趋势明确 | 震荡/反转 |

## ⚠️ 风险提示

1. **回测验证**: 上线前务必进行充分的历史回测
2. **模拟交易**: 先使用 `dry_run: true` 模式验证
3. **资金管理**: 根据账户规模调整仓位大小
4. **市场监控**: 密切关注市场变化，及时调整参数
5. **风险控制**: 设置合理的止损和仓位限制

## 🔧 参数调优建议

### 趋势策略调优:
- 增加 `sma_long_period` 适应更稳定趋势
- 调整 `rsi_overbought/oversold` 过滤假信号
- 优化 `trailing_stop_positive` 提高盈利锁定

### 反转策略调优:
- 微调 `rsi_oversold/overbought` 阈值
- 调整 `bb_std` 标准差适应市场波动
- 优化 `volume_check` 成交量过滤条件

## 📞 支持

如有问题请查阅:
- [FreqTrade 官方文档](https://www.freqtrade.io/)
- [策略开发指南](https://www.freqtrade.io/en/latest/strategy-customization/)
- [配置文件说明](https://www.freqtrade.io/en/latest/configuration/)