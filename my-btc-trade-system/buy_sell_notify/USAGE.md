# 交易系统使用说明

## 🚀 快速启动

### 最简单的运行方式
```bash
python main.py
```
这将使用默认的 `both` 模式，**同时启动主交易程序和持仓监控**。

## 📋 运行模式

### 1. 默认模式（推荐）
```bash
python main.py
# 或者显式指定
python main.py both
```
**同时运行**：
- 主交易程序：分析市场，生成交易信号
- 持仓监控：监控现有持仓，风险管理

### 2. 单独运行主交易程序
```bash
python main.py trader
```
只运行信号分析和交易决策，不进行持仓监控。

### 3. 单独运行持仓监控
```bash
python main.py monitor
```
只监控现有持仓状态，不生成新的交易信号。

## ⚙️ 常用参数

### 日志级别
```bash
python main.py --log-level DEBUG    # 详细调试信息
python main.py --log-level INFO     # 标准信息（默认）
python main.py --log-level WARNING  # 只显示警告和错误
```

### 自定义配置文件
```bash
python main.py --config my_config.py
```

### 自定义日志目录
```bash
python main.py --log-dir /path/to/logs
```

### 结构化日志输出
```bash
python main.py --structured-logs
```

### 禁用通知功能
```bash
python main.py --no-notifications
```

## 📊 组合使用示例

```bash
# 生产环境运行（推荐）
python main.py --log-level INFO

# 开发调试运行
python main.py --log-level DEBUG --structured-logs

# 测试运行（无通知）
python main.py trader --log-level DEBUG --no-notifications

# 自定义配置运行
python main.py --config prod_config.py --log-dir /var/log/trader
```

## 🔧 系统架构

当运行 `python main.py`（默认both模式）时，系统会：

1. **加载配置** - 从 `config.py` 读取交易对、策略参数等
2. **初始化组件** - 交易所接口、决策引擎、仓位计算器等
3. **启动双线程**：
   - **主交易线程** - 每5分钟分析市场，生成交易信号
   - **监控线程** - 每2分钟检查持仓状态，风险管理
4. **发送通知** - 钉钉消息通知交易信号和风险警报

## 📝 日志文件

运行后会生成以下日志文件：
- `logs/trader.log` - 主程序日志
- `logs/position_monitor.log` - 持仓监控日志

## ⚡ 快速故障排除

### 1. 导入错误
```bash
pip install ccxt pandas pandas-ta requests numpy
```

### 2. 配置错误
检查 `config.py` 文件中的：
- API 密钥和密码
- 钉钉 Webhook 地址
- 监控的交易对列表

### 3. 网络连接问题
检查：
- 代理设置（如果使用）
- API 访问权限
- 钉钉通知权限

## 🎯 推荐使用方式

**生产环境**：
```bash
python main.py --log-level INFO > output.log 2>&1 &
```

**开发测试**：
```bash
python main.py --log-level DEBUG --no-notifications
```

---

💡 **提示**：首次运行建议使用 `--log-level DEBUG` 查看详细运行情况，确认配置正确后再切换到 `INFO` 级别。