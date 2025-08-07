# notification_system.py - 新的事件驱动通知系统

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import time
import logging
from dingtalk_notifier import send_dingtalk_markdown

class EventType(Enum):
    """事件类型枚举"""
    TRADE_SIGNAL = "trade_signal"           # 交易信号
    POSITION_UPDATE = "position_update"     # 仓位更新/追踪止损
    MARKET_ANALYSIS = "market_analysis"     # 市场分析摘要
    SYSTEM_ERROR = "system_error"           # 系统错误
    HIGH_PROFIT_ALERT = "high_profit_alert" # 高盈利提醒

class StrategyType(Enum):
    """策略类型"""
    TREND_FOLLOWING = "trend_following"     # 趋势跟踪
    REVERSAL = "reversal"                  # 激进反转
    POSITION_REVERSAL = "position_reversal" # 持仓反转

class TradeDirection(Enum):
    """交易方向"""
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class BaseEvent:
    """事件基类"""
    event_type: EventType
    timestamp: float = None
    symbol: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class TradeSignalEvent(BaseEvent):
    """交易信号事件"""
    event_type: EventType = EventType.TRADE_SIGNAL
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    direction: TradeDirection = TradeDirection.LONG
    entry_price: float = 0.0
    stop_loss_price: float = 0.0
    position_size_coin: float = 0.0
    position_size_usd: float = 0.0
    risk_amount_usd: float = 0.0
    target_price_2r: float = 0.0
    target_price_3r: float = 0.0
    atr_value: float = 0.0
    atr_multiplier: float = 0.0
    atr_timeframe: str = ""
    atr_length: int = 0
    decision_reason: str = ""
    account_balance: float = 0.0
    risk_percent: float = 0.0

@dataclass
class PositionUpdateEvent(BaseEvent):
    """仓位更新事件"""
    event_type: EventType = EventType.POSITION_UPDATE
    position_side: str = ""
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    pnl_percent: float = 0.0
    profit_ratio: float = 0.0
    new_stop_loss: float = 0.0
    update_type: str = ""  # "trailing_stop", "high_profit", "partial_profit"
    suggestion: str = ""

@dataclass
class MarketAnalysisEvent(BaseEvent):
    """市场分析摘要事件"""
    event_type: EventType = EventType.MARKET_ANALYSIS
    analyzed_symbols_count: int = 0
    signals_count: int = 0
    alerts_count: int = 0
    errors_count: int = 0
    analysis_summary: Dict[str, Any] = None

@dataclass  
class SystemErrorEvent(BaseEvent):
    """系统错误事件"""
    event_type: EventType = EventType.SYSTEM_ERROR
    error_message: str = ""
    error_type: str = ""
    stack_trace: str = ""

class NotificationChannel(ABC):
    """通知渠道抽象基类"""
    
    @abstractmethod
    def send(self, event: BaseEvent, formatted_message: str, title: str = "") -> bool:
        """发送通知"""
        pass

class DingTalkChannel(NotificationChannel):
    """钉钉通知渠道"""
    
    def send(self, event: BaseEvent, formatted_message: str, title: str = "") -> bool:
        """发送钉钉通知"""
        try:
            return send_dingtalk_markdown(title, formatted_message)
        except Exception as e:
            logging.error(f"钉钉通知发送失败: {e}")
            return False

class MessageFormatter:
    """消息格式化器"""
    
    @staticmethod
    def format_trade_signal(event: TradeSignalEvent) -> tuple[str, str]:
        """格式化交易信号消息"""
        current_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(event.timestamp))
        
        # 根据策略类型设置不同的显示
        if event.strategy_type == StrategyType.REVERSAL:
            strategy_name = "激进反转策略"
            strategy_emoji = "🔥"
            operation_reminder = "🔥 **激进策略**: 快进快出，严格止损，保守止盈"
        elif event.strategy_type == StrategyType.POSITION_REVERSAL:
            strategy_name = "仓位反转信号"
            strategy_emoji = "🔄"
            operation_reminder = "🔄 **重要提醒**: 检测到反转信号！建议先平仓当前持仓，再考虑开新仓"
        else:
            strategy_name = "趋势跟踪策略"
            strategy_emoji = "🚨"
            operation_reminder = "⚠️ **操作提醒**: 严格执行止损，建议分批止盈"
            
        title = f"{strategy_emoji} {event.symbol} {event.direction.value}"
        
        # 计算预期盈亏
        potential_profit_2r = event.risk_amount_usd * 2
        potential_profit_3r = event.risk_amount_usd * 3
        
        markdown_text = f"""### **{strategy_emoji} 交易信号: {event.symbol}** `{current_time}`

**策略类型**: {strategy_name}
**交易方向**: {event.direction.value}
**入场价格**: {event.entry_price:,.4f} USDT
**决策原因**: {event.decision_reason}

**仓位信息**:
- 持仓量: {event.position_size_coin:,.4f} {event.symbol.split('/')[0]}
- 持仓价值: {event.position_size_usd:,.2f} USDT
- 止损价: {event.stop_loss_price:,.4f} USDT
- 最大亏损: -{event.risk_amount_usd:,.2f} USDT

**技术指标**:
- ATR周期: {event.atr_timeframe}
- ATR时长: {event.atr_length}期
- 原始ATR: {event.atr_value:,.4f}
- 止损倍数: {event.atr_multiplier}x ATR
- 风险敞口: {event.risk_percent:.1%}

**目标价位**:
- 目标1 (2R): {event.target_price_2r:,.4f} USDT → +{potential_profit_2r:,.2f} USDT
- 目标2 (3R): {event.target_price_3r:,.4f} USDT → +{potential_profit_3r:,.2f} USDT

{operation_reminder}
"""
        return title, markdown_text
    
    @staticmethod
    def format_position_update(event: PositionUpdateEvent) -> tuple[str, str]:
        """格式化仓位更新消息"""
        current_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(event.timestamp))
        
        if event.update_type == "high_profit":
            title = f"💰 {event.symbol} 高盈利提醒"
            emoji = "💰"
            alert_type = "HIGH PROFIT ALERT & TRAILING SL"
        else:
            title = f"📊 {event.symbol} 追踪止损"
            emoji = "📊"
            alert_type = "TRAILING STOP LOSS UPDATE"
            
        markdown_text = f"""### **{emoji} {alert_type}** `{current_time}`

**交易对**: {event.symbol} ({event.position_side.upper()})
**入场价格**: {event.entry_price:,.4f}
**当前价格**: {event.current_price:,.4f} (+{event.profit_ratio:.1%})
**未实现盈亏**: {event.unrealized_pnl:,.2f} USDT ({event.pnl_percent:+.1f}%)
**建议止损价**: {event.new_stop_loss:,.4f}

**操作建议**: {event.suggestion}
"""
        return title, markdown_text
        
    @staticmethod
    def format_market_analysis(event: MarketAnalysisEvent) -> tuple[str, str]:
        """格式化市场分析摘要消息"""
        current_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(event.timestamp))
        
        title = f"📈 市场分析摘要"
        
        summary_items = []
        if event.analyzed_symbols_count > 0:
            summary_items.append(f"✅ 已分析 {event.analyzed_symbols_count} 个交易对")
        if event.signals_count > 0:
            summary_items.append(f"🎯 发现 {event.signals_count} 个交易信号")
        if event.alerts_count > 0:
            summary_items.append(f"⚠️ {event.alerts_count} 个持仓需关注")
        if event.errors_count > 0:
            summary_items.append(f"❌ {event.errors_count} 个错误")
            
        markdown_text = f"""### **📈 市场分析摘要** `{current_time}`

{chr(10).join(summary_items) if summary_items else "✅ 系统运行正常，暂无重要信号"}
"""
        return title, markdown_text

class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self.channels: List[NotificationChannel] = []
        self.formatter = MessageFormatter()
        self.logger = logging.getLogger("NotificationManager")
        
        # 默认添加钉钉通道
        self.add_channel(DingTalkChannel())
    
    def add_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.channels.append(channel)
    
    def emit_event(self, event: BaseEvent):
        """发送事件通知"""
        try:
            if event.event_type == EventType.TRADE_SIGNAL:
                title, message = self.formatter.format_trade_signal(event)
            elif event.event_type == EventType.POSITION_UPDATE:
                title, message = self.formatter.format_position_update(event)
            elif event.event_type == EventType.MARKET_ANALYSIS:
                title, message = self.formatter.format_market_analysis(event)
            else:
                self.logger.warning(f"未支持的事件类型: {event.event_type}")
                return
                
            # 发送到所有通道
            for channel in self.channels:
                success = channel.send(event, message, title)
                if success:
                    self.logger.info(f"通知发送成功: {event.event_type.value} - {event.symbol}")
                else:
                    self.logger.error(f"通知发送失败: {event.event_type.value} - {event.symbol}")
                    
        except Exception as e:
            self.logger.error(f"事件处理失败: {e}", exc_info=True)

# 全局通知管理器实例
notification_manager = NotificationManager()

# 便捷函数
def emit_trade_signal(symbol: str, strategy_type: StrategyType, direction: TradeDirection,
                     entry_price: float, stop_loss_price: float, position_size_coin: float,
                     position_size_usd: float, risk_amount_usd: float, target_price_2r: float,
                     target_price_3r: float, atr_value: float, atr_multiplier: float,
                     atr_timeframe: str, atr_length: int, decision_reason: str,
                     account_balance: float, risk_percent: float):
    """发送交易信号通知"""
    event = TradeSignalEvent(
        symbol=symbol,
        strategy_type=strategy_type,
        direction=direction,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        position_size_coin=position_size_coin,
        position_size_usd=position_size_usd,
        risk_amount_usd=risk_amount_usd,
        target_price_2r=target_price_2r,
        target_price_3r=target_price_3r,
        atr_value=atr_value,
        atr_multiplier=atr_multiplier,
        atr_timeframe=atr_timeframe,
        atr_length=atr_length,
        decision_reason=decision_reason,
        account_balance=account_balance,
        risk_percent=risk_percent
    )
    notification_manager.emit_event(event)

def emit_position_update(symbol: str, position_side: str, entry_price: float,
                        current_price: float, unrealized_pnl: float, pnl_percent: float,
                        profit_ratio: float, new_stop_loss: float, update_type: str,
                        suggestion: str):
    """发送仓位更新通知"""
    event = PositionUpdateEvent(
        symbol=symbol,
        position_side=position_side,
        entry_price=entry_price,
        current_price=current_price,
        unrealized_pnl=unrealized_pnl,
        pnl_percent=pnl_percent,
        profit_ratio=profit_ratio,
        new_stop_loss=new_stop_loss,
        update_type=update_type,
        suggestion=suggestion
    )
    notification_manager.emit_event(event)

def emit_market_analysis(analyzed_symbols_count: int, signals_count: int = 0,
                        alerts_count: int = 0, errors_count: int = 0,
                        analysis_summary: Dict[str, Any] = None):
    """发送市场分析摘要通知"""
    event = MarketAnalysisEvent(
        analyzed_symbols_count=analyzed_symbols_count,
        signals_count=signals_count,
        alerts_count=alerts_count,
        errors_count=errors_count,
        analysis_summary=analysis_summary
    )
    notification_manager.emit_event(event)