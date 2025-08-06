"""
钉钉通知实现
处理钉钉 Webhook 消息发送和签名验证
"""

import hmac
import hashlib
import base64
import urllib.parse
import time
import json
import logging
import requests
from typing import Dict, Any, Optional, List


class DingTalkNotifier:
    """
    钉钉通知器
    
    负责：
    1. 发送交易信号通知
    2. 发送风险警报
    3. 处理消息签名和验证
    4. 管理消息发送频率限制
    """
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        """
        初始化钉钉通知器
        
        Args:
            webhook_url: 钉钉机器人 Webhook URL
            secret: 签名密钥（可选）
        """
        self.webhook_url = webhook_url
        self.secret = secret
        self.logger = logging.getLogger("DingTalkNotifier")
        
        # 消息发送统计
        self.stats = {
            'total_sent': 0,
            'successful_sent': 0,
            'failed_sent': 0,
            'last_sent_time': None
        }
        
        # 消息长度限制
        self.max_message_length = 19900  # 留一些余量给签名等
        
        self.logger.info("钉钉通知器初始化完成")
    
    def send_trading_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        发送交易信号通知
        
        Args:
            signal_data: 交易信号数据
            
        Returns:
            bool: 发送是否成功
        """
        try:
            message = self._build_trading_signal_message(signal_data)
            return self._send_message(message, "交易信号")
            
        except Exception as e:
            self.logger.error(f"发送交易信号通知失败: {e}", exc_info=True)
            return False
    
    def send_risk_alert(self, risk_data: Dict[str, Any]) -> bool:
        """
        发送风险警报通知
        
        Args:
            risk_data: 风险数据
            
        Returns:
            bool: 发送是否成功
        """
        try:
            message = self._build_risk_alert_message(risk_data)
            return self._send_message(message, "风险警报")
            
        except Exception as e:
            self.logger.error(f"发送风险警报失败: {e}", exc_info=True)
            return False
    
    def send_position_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        发送持仓摘要通知
        
        Args:
            summary_data: 持仓摘要数据
            
        Returns:
            bool: 发送是否成功
        """
        try:
            message = self._build_position_summary_message(summary_data)
            return self._send_message(message, "持仓摘要")
            
        except Exception as e:
            self.logger.error(f"发送持仓摘要失败: {e}", exc_info=True)
            return False
    
    def send_system_status(self, status_data: Dict[str, Any]) -> bool:
        """
        发送系统状态通知
        
        Args:
            status_data: 系统状态数据
            
        Returns:
            bool: 发送是否成功
        """
        try:
            message = self._build_system_status_message(status_data)
            return self._send_message(message, "系统状态")
            
        except Exception as e:
            self.logger.error(f"发送系统状态失败: {e}", exc_info=True)
            return False
    
    def _build_trading_signal_message(self, signal_data: Dict[str, Any]) -> str:
        """构建交易信号消息"""
        symbol = signal_data.get('symbol', '')
        action = signal_data.get('action', '')
        confidence = signal_data.get('confidence', 0)
        reason = signal_data.get('reason', '')
        
        # 获取ATR和持仓信息
        atr_info = signal_data.get('atr_info', {})
        position_info = signal_data.get('position_info', {})
        
        # 构建消息
        message_parts = [
            "🎯 **新交易信号**",
            f"",
            f"**交易对**: {symbol}",
            f"**操作**: {self._format_action(action)}",
            f"**置信度**: {confidence:.1%}",
            f"**决策原因**: {reason}",
        ]
        
        # 添加ATR信息
        if atr_info:
            atr_value = atr_info.get('atr', 0)
            atr_timeframe = atr_info.get('timeframe', '')
            atr_length = atr_info.get('length', 0)
            
            # 获取ATR倍数
            atr_multiplier = signal_data.get('atr_multiplier', 
                            position_info.get('atr_multiplier', 2.0) if position_info else 2.0)
            
            message_parts.extend([
                f"",
                f"**技术指标**:",
                f"- ATR周期: {atr_timeframe}",
                f"- ATR时长: {atr_length}期",
                f"- ATR数值: {atr_value:,.4f}",
                f"- 止损倍数: {atr_multiplier}x ATR",
            ])
        
        # 添加持仓信息
        if position_info:
            position_size = position_info.get('position_size_coin', position_info.get('size', 0))
            entry_price = position_info.get('current_price', position_info.get('entry_price', 0))
            stop_loss = position_info.get('stop_loss_price', position_info.get('stop_loss', 0))
            usdt_amount = position_info.get('position_value_usd', position_info.get('usdt_amount', 0))
            max_loss = position_info.get('actual_risk_usd', 0)
            
            message_parts.extend([
                f"",
                f"**仓位信息**:",
                f"- 持仓量: {position_size:.6f} {symbol.replace('/USDT', '')}",
                f"- 入场价格: {entry_price:,.4f} USDT",
                f"- 持仓价值: {usdt_amount:.2f} USDT",
                f"- 止损价: {stop_loss:,.4f} USDT",
                f"- 最大亏损: -{max_loss:.2f} USDT",
            ])
            
            # 添加目标价位
            targets = position_info.get('target_prices', {})
            if targets:
                message_parts.extend([f"", f"**目标价位**:"])
                for i, (key, target) in enumerate(targets.items(), 1):
                    price = target.get('price', 0)
                    profit = target.get('profit_amount', 0)
                    message_parts.append(f"- 目标{i}: {price:,.4f} USDT → +{profit:.2f} USDT")
            
        
        # 添加时间戳
        message_parts.extend([
            f"",
            f"📅 {signal_data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S'))}"
        ])
        
        return "\n".join(message_parts)
    
    def _build_risk_alert_message(self, risk_data: Dict[str, Any]) -> str:
        """构建风险警报消息"""
        symbol = risk_data.get('symbol', '')
        risk_level = risk_data.get('risk_level', '')
        alerts = risk_data.get('alerts', [])
        pnl_percent = risk_data.get('pnl_percent', 0)
        
        # 选择合适的emoji
        emoji = "⚠️" if risk_level == "medium" else "🚨" if risk_level == "high" else "💡"
        
        message_parts = [
            f"{emoji} **风险警报**",
            f"",
            f"**交易对**: {symbol}",
            f"**风险等级**: {self._format_risk_level(risk_level)}",
            f"**当前盈亏**: {pnl_percent:.2%}",
            f"",
            f"**警报详情**:"
        ]
        
        # 添加具体警报
        for alert in alerts:
            message_parts.append(f"- {alert}")
        
        message_parts.extend([
            f"",
            f"📅 {risk_data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S'))}"
        ])
        
        return "\n".join(message_parts)
    
    def _build_position_summary_message(self, summary_data: Dict[str, Any]) -> str:
        """构建持仓摘要消息"""
        total_positions = summary_data.get('total_positions', 0)
        total_pnl = summary_data.get('total_unrealized_pnl', 0)
        positions = summary_data.get('positions', [])
        
        message_parts = [
            "📋 **持仓摘要**",
            f"",
            f"**总持仓数**: {total_positions}",
            f"**总浮动盈亏**: {total_pnl:.2f} USDT",
            f""
        ]
        
        if positions:
            message_parts.append("**详细持仓**:")
            for pos in positions[:10]:  # 限制显示前10个
                symbol = pos.get('symbol', '')
                side = pos.get('side', '')
                pnl = pos.get('unrealized_pnl', 0)
                message_parts.append(f"- {symbol} {side.upper()}: {pnl:+.2f} USDT")
            
            if len(positions) > 10:
                message_parts.append(f"- ...还有 {len(positions) - 10} 个持仓")
        
        message_parts.extend([
            f"",
            f"📅 {summary_data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S'))}"
        ])
        
        return "\n".join(message_parts)
    
    def _build_system_status_message(self, status_data: Dict[str, Any]) -> str:
        """构建系统状态消息"""
        uptime = status_data.get('uptime', '')
        total_analyses = status_data.get('total_analyses', 0)
        signals_generated = status_data.get('signals_generated', 0)
        success_rate = status_data.get('success_rate', '0%')
        
        message_parts = [
            "📊 **系统状态报告**",
            f"",
            f"**运行时间**: {uptime}",
            f"**分析次数**: {total_analyses}",
            f"**生成信号**: {signals_generated}",
            f"**成功率**: {success_rate}",
            f"",
            f"📅 {status_data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S'))}"
        ]
        
        return "\n".join(message_parts)
    
    def _send_message(self, message: str, message_type: str = "通知") -> bool:
        """
        发送消息到钉钉
        
        Args:
            message: 消息内容
            message_type: 消息类型（用于日志）
            
        Returns:
            bool: 发送是否成功
        """
        try:
            self.stats['total_sent'] += 1
            
            # 检查消息长度
            if len(message) > self.max_message_length:
                message = self._truncate_message(message)
            
            # 构建请求数据
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": message_type,
                    "text": message
                }
            }
            
            # 添加签名（如果有密钥）
            url = self.webhook_url
            if self.secret:
                url = self._add_signature(url)
            
            # 发送请求
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=10
            )
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    self.stats['successful_sent'] += 1
                    self.stats['last_sent_time'] = time.time()
                    self.logger.info(f"{message_type}发送成功")
                    return True
                else:
                    error_msg = result.get('errmsg', '未知错误')
                    self.logger.error(f"{message_type}发送失败: {error_msg}")
                    self.stats['failed_sent'] += 1
                    return False
            else:
                self.logger.error(f"{message_type}发送失败: HTTP {response.status_code}")
                self.stats['failed_sent'] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"{message_type}发送异常: {e}", exc_info=True)
            self.stats['failed_sent'] += 1
            return False
    
    def _add_signature(self, url: str) -> str:
        """添加签名到URL"""
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        
        hmac_code = hmac.new(
            secret_enc,
            string_to_sign_enc,
            digestmod=hashlib.sha256
        ).digest()
        
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        
        return f"{url}&timestamp={timestamp}&sign={sign}"
    
    def _truncate_message(self, message: str) -> str:
        """截断过长的消息"""
        if len(message) <= self.max_message_length:
            return message
        
        # 截断消息并添加提示
        truncated = message[:self.max_message_length - 100]
        truncated += "\n\n... (消息过长，已截断)"
        
        self.logger.warning(f"消息长度超限({len(message)})，已截断到{len(truncated)}")
        
        return truncated
    
    def _format_action(self, action: str) -> str:
        """格式化交易操作"""
        action_map = {
            'EXECUTE_LONG': '📈 做多',
            'EXECUTE_SHORT': '📉 做空',
            'HOLD': '⏸️ 观望'
        }
        return action_map.get(action, action)
    
    def _format_risk_level(self, level: str) -> str:
        """格式化风险等级"""
        level_map = {
            'low': '🟢 低风险',
            'medium': '🟡 中风险', 
            'high': '🔴 高风险'
        }
        return level_map.get(level, level)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取发送统计"""
        return self.stats.copy()