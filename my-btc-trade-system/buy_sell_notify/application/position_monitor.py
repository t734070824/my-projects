"""
持仓监控应用程序
独立监控持仓状态和风险管理
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from config.settings import AppConfig, load_app_config
from infrastructure.exchange.binance import BinanceExchange
from core.decision.engine import DecisionEngine
from utils.constants import TradingAction
from utils.helpers import (
    safe_float_conversion, create_log_safe_json,
    sanitize_log_data
)


class PositionMonitor:
    """
    持仓监控器
    
    负责：
    1. 监控现有持仓状态
    2. 执行风险管理规则
    3. 检测平仓信号
    4. 发送持仓状态通知
    """
    
    def __init__(self, config_path: str = "config.py"):
        """
        初始化持仓监控器
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger("PositionMonitor")
        
        # 加载配置
        self.config = load_app_config(config_path)
        
        # 初始化交易所接口
        exchange_config = {
            'api_key': self.config.exchange.api_key,
            'secret_key': self.config.exchange.secret_key,
            'sandbox': self.config.exchange.sandbox,
            'proxy': self.config.exchange.proxy
        }
        self.exchange = BinanceExchange(exchange_config)
        if not self.exchange.connect():
            raise ConnectionError("无法连接到币安交易所")
        
        # 初始化决策引擎用于平仓判断
        self.decision_engine = DecisionEngine(self.config.strategy_config)
        
        # 运行状态
        self.running = False
        self.last_check_time = {}
        
        # 持仓状态缓存
        self.position_cache = {}
        
        # 统计信息
        self.stats = {
            'total_checks': 0,
            'positions_monitored': 0,
            'risk_alerts_sent': 0,
            'exit_signals_detected': 0,
            'start_time': None
        }
        
        self.logger.info("持仓监控器初始化完成")
    
    def run(self):
        """启动持仓监控循环"""
        self.logger.info("🔍 持仓监控器启动")
        self.running = True
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        try:
            while self.running:
                cycle_start_time = time.time()
                
                # 执行一轮监控
                self._run_monitor_cycle()
                
                # 计算睡眠时间
                cycle_duration = time.time() - cycle_start_time
                sleep_time = max(0, self.config.position_monitor_interval - cycle_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在关闭持仓监控...")
        except Exception as e:
            self.logger.error(f"持仓监控运行异常: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _run_monitor_cycle(self):
        """执行一轮监控周期"""
        self.stats['total_checks'] += 1
        
        try:
            # 1. 获取当前所有持仓
            account_status = self.exchange.get_account_status()
            
            if not account_status['success']:
                self.logger.error(f"获取账户状态失败: {account_status.get('error')}")
                return
            
            open_positions = account_status.get('open_positions', [])
            
            if not open_positions:
                self.logger.debug("当前无持仓")
                return
            
            self.stats['positions_monitored'] = len(open_positions)
            
            # 2. 监控每个持仓
            for position in open_positions:
                self._monitor_single_position(position, account_status)
            
            # 3. 清理已平仓的缓存
            self._cleanup_closed_positions(open_positions)
            
            # 4. 定期发送持仓摘要
            self._send_position_summary(open_positions)
            
        except Exception as e:
            self.logger.error(f"监控周期执行失败: {e}", exc_info=True)
    
    def _monitor_single_position(self, position: Dict[str, Any], account_status: Dict[str, Any]):
        """监控单个持仓"""
        symbol = position.get('symbol', '')
        
        if not symbol:
            return
        
        try:
            # 1. 解析持仓基本信息
            position_info = self._parse_position_info(position)
            
            # 2. 检查风险状况
            risk_status = self._check_position_risk(position_info)
            
            # 3. 获取最新市场数据（如果需要）
            market_data = self._get_market_data_for_position(symbol)
            
            # 4. 检查是否需要平仓
            exit_signal = self._check_exit_signals(position_info, market_data, account_status)
            
            # 5. 处理监控结果
            self._process_monitor_results(
                position_info, risk_status, exit_signal, market_data
            )
            
            # 6. 更新持仓缓存
            self._update_position_cache(position_info)
            
        except Exception as e:
            self.logger.error(f"监控持仓 {symbol} 失败: {e}")
    
    def _parse_position_info(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """解析持仓信息"""
        symbol = position.get('symbol', '')
        side = position.get('side', '')
        size = safe_float_conversion(position.get('size', 0))
        entry_price = safe_float_conversion(position.get('entry_price', 0))
        mark_price = safe_float_conversion(position.get('mark_price', 0))
        unrealized_pnl = safe_float_conversion(position.get('unrealized_pnl', 0))
        
        # 计算收益率
        pnl_percent = 0.0
        if entry_price > 0 and mark_price > 0:
            if side.lower() == 'long':
                pnl_percent = (mark_price - entry_price) / entry_price
            else:
                pnl_percent = (entry_price - mark_price) / entry_price
        
        return {
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': entry_price,
            'mark_price': mark_price,
            'unrealized_pnl': unrealized_pnl,
            'pnl_percent': pnl_percent,
            'notional_value': size * mark_price if mark_price > 0 else 0,
            'timestamp': datetime.now(timezone.utc)
        }
    
    def _check_position_risk(self, position_info: Dict[str, Any]) -> Dict[str, Any]:
        """检查持仓风险状况"""
        symbol = position_info['symbol']
        pnl_percent = position_info['pnl_percent']
        
        # 风险等级判断
        risk_level = 'low'
        risk_alerts = []
        
        # 1. 检查损失幅度
        if pnl_percent <= -0.05:  # -5%
            risk_level = 'high'
            risk_alerts.append('损失超过5%')
        elif pnl_percent <= -0.03:  # -3%
            risk_level = 'medium'
            risk_alerts.append('损失超过3%')
        
        # 2. 检查获利情况（是否应该考虑止盈）
        if pnl_percent >= 0.04:  # +4%
            risk_alerts.append('获利超过4%，可考虑分批止盈')
        elif pnl_percent >= 0.02:  # +2%
            risk_alerts.append('获利超过2%')
        
        # 3. 检查持仓时间（如果有缓存的话）
        if symbol in self.position_cache:
            cache_info = self.position_cache[symbol]
            holding_hours = (datetime.now(timezone.utc) - cache_info.get('first_seen', datetime.now(timezone.utc))).total_seconds() / 3600
            
            if holding_hours > 72:  # 持仓超过72小时
                risk_alerts.append(f'持仓时间过长({holding_hours:.1f}小时)')
        
        return {
            'risk_level': risk_level,
            'alerts': risk_alerts,
            'pnl_percent': pnl_percent,
            'requires_attention': len(risk_alerts) > 0 or risk_level != 'low'
        }
    
    def _get_market_data_for_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取持仓相关的市场数据"""
        try:
            # 仅获取1小时数据用于平仓判断
            from core.signals.generator import SignalGenerator
            
            signal_generator = SignalGenerator(symbol, '1h', self.exchange)
            signal_result = signal_generator.generate_signal()
            
            if signal_result['success']:
                return {
                    'signal': signal_result['signal'],
                    'total_score': signal_result['total_score'],
                    'close_price': signal_result['close_price'],
                    'rsi_value': signal_result.get('rsi_value'),
                    'timestamp': datetime.now(timezone.utc)
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 市场数据失败: {e}")
            return None
    
    def _check_exit_signals(self, 
                           position_info: Dict[str, Any],
                           market_data: Optional[Dict[str, Any]],
                           account_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检查平仓信号"""
        if not market_data:
            return None
        
        try:
            symbol = position_info['symbol']
            
            # 构建用于决策引擎的数据格式
            market_data_for_decision = {
                'symbol': symbol,
                'h1_analysis': {
                    'signal': market_data['signal'],
                    'total_score': market_data['total_score'],
                    'close_price': market_data['close_price'],
                    'rsi_value': market_data.get('rsi_value')
                }
            }
            
            portfolio_state = {
                'total_balance': safe_float_conversion(
                    account_status.get('usdt_balance', {}).get('wallet_balance', 0)
                ),
                'available_balance': safe_float_conversion(
                    account_status.get('usdt_balance', {}).get('available_balance', 0)
                )
            }
            
            # 使用决策引擎检查是否需要平仓
            decision = self.decision_engine.make_decision(
                symbol, market_data_for_decision, portfolio_state, position_info
            )
            
            # 如果决策不是HOLD，说明有平仓或反转信号
            if decision['action'] != TradingAction.HOLD.value:
                self.stats['exit_signals_detected'] += 1
                
                return {
                    'action': decision['action'],
                    'confidence': decision['confidence'],
                    'reason': decision['reason'],
                    'signal_type': 'strategy_based',
                    'market_signal': market_data['signal']
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"检查 {position_info['symbol']} 平仓信号失败: {e}")
            return None
    
    def _process_monitor_results(self,
                               position_info: Dict[str, Any],
                               risk_status: Dict[str, Any], 
                               exit_signal: Optional[Dict[str, Any]],
                               market_data: Optional[Dict[str, Any]]):
        """处理监控结果"""
        symbol = position_info['symbol']
        
        # 1. 记录风险警报
        if risk_status['requires_attention']:
            self._log_risk_alert(position_info, risk_status)
            self.stats['risk_alerts_sent'] += 1
        
        # 2. 记录平仓信号
        if exit_signal:
            self._log_exit_signal(position_info, exit_signal, market_data)
        
        # 3. 记录持仓状态更新
        self._log_position_update(position_info, risk_status, market_data)
    
    def _log_risk_alert(self, position_info: Dict[str, Any], risk_status: Dict[str, Any]):
        """记录风险警报"""
        alert_data = {
            'type': 'RISK_ALERT',
            'symbol': position_info['symbol'],
            'side': position_info['side'],
            'pnl_percent': f"{position_info['pnl_percent']:.2%}",
            'unrealized_pnl': position_info['unrealized_pnl'],
            'risk_level': risk_status['risk_level'],
            'alerts': risk_status['alerts'],
            'mark_price': position_info['mark_price']
        }
        
        self.logger.warning(f"⚠️ 风险警报: {create_log_safe_json(alert_data)}")
    
    def _log_exit_signal(self, 
                        position_info: Dict[str, Any],
                        exit_signal: Dict[str, Any],
                        market_data: Optional[Dict[str, Any]]):
        """记录平仓信号"""
        signal_data = {
            'type': 'EXIT_SIGNAL',
            'symbol': position_info['symbol'],
            'current_side': position_info['side'],
            'recommended_action': exit_signal['action'],
            'confidence': exit_signal['confidence'],
            'reason': exit_signal['reason'],
            'current_pnl': f"{position_info['pnl_percent']:.2%}",
            'market_signal': market_data.get('signal') if market_data else None
        }
        
        self.logger.info(f"🚪 平仓信号: {create_log_safe_json(signal_data)}")
    
    def _log_position_update(self, 
                           position_info: Dict[str, Any],
                           risk_status: Dict[str, Any],
                           market_data: Optional[Dict[str, Any]]):
        """记录持仓状态更新"""
        # 只在特定条件下记录详细更新
        symbol = position_info['symbol']
        
        # 检查是否需要记录（避免日志过多）
        should_log = (
            risk_status['requires_attention'] or
            abs(position_info['pnl_percent']) > 0.02 or  # PnL超过±2%
            self.stats['total_checks'] % 20 == 0  # 每20次检查记录一次
        )
        
        if should_log:
            update_data = {
                'symbol': symbol,
                'side': position_info['side'],
                'pnl': f"{position_info['pnl_percent']:.2%}",
                'mark_price': position_info['mark_price'],
                'size': position_info['size'],
                'market_signal': market_data.get('signal') if market_data else None
            }
            
            self.logger.debug(f"📊 持仓更新: {create_log_safe_json(update_data)}")
    
    def _update_position_cache(self, position_info: Dict[str, Any]):
        """更新持仓缓存"""
        symbol = position_info['symbol']
        
        if symbol not in self.position_cache:
            self.position_cache[symbol] = {
                'first_seen': position_info['timestamp'],
                'alerts_sent': 0
            }
        
        self.position_cache[symbol].update({
            'last_update': position_info['timestamp'],
            'last_pnl': position_info['pnl_percent'],
            'last_price': position_info['mark_price']
        })
    
    def _cleanup_closed_positions(self, open_positions: List[Dict[str, Any]]):
        """清理已平仓的缓存"""
        open_symbols = {pos.get('symbol') for pos in open_positions}
        cached_symbols = set(self.position_cache.keys())
        
        closed_symbols = cached_symbols - open_symbols
        
        for symbol in closed_symbols:
            cache_info = self.position_cache.pop(symbol)
            
            # 记录平仓信息
            self.logger.info(f"✅ 持仓已平仓: {symbol} (监控时长: {datetime.now(timezone.utc) - cache_info.get('first_seen', datetime.now(timezone.utc))})")
    
    def _send_position_summary(self, positions: List[Dict[str, Any]]):
        """定期发送持仓摘要"""
        # 每100次检查发送一次摘要
        if self.stats['total_checks'] % 100 == 0 and positions:
            
            total_pnl = sum(safe_float_conversion(pos.get('unrealized_pnl', 0)) for pos in positions)
            
            summary = {
                'type': 'POSITION_SUMMARY',
                'total_positions': len(positions),
                'total_unrealized_pnl': round(total_pnl, 2),
                'positions': []
            }
            
            for pos in positions:
                summary['positions'].append({
                    'symbol': pos.get('symbol'),
                    'side': pos.get('side'),
                    'unrealized_pnl': safe_float_conversion(pos.get('unrealized_pnl', 0))
                })
            
            self.logger.info(f"📋 持仓摘要: {create_log_safe_json(summary)}")
    
    def stop(self):
        """停止持仓监控"""
        self.running = False
        
        final_stats = {
            'total_checks': self.stats['total_checks'],
            'risk_alerts_sent': self.stats['risk_alerts_sent'],
            'exit_signals_detected': self.stats['exit_signals_detected'],
            'runtime': str(datetime.now(timezone.utc) - self.stats['start_time']).split('.')[0]
        }
        
        self.logger.info(f"🛑 持仓监控已停止. 统计: {create_log_safe_json(final_stats)}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控器状态"""
        return {
            'running': self.running,
            'stats': self.stats.copy(),
            'monitored_positions': list(self.position_cache.keys()),
            'cache_size': len(self.position_cache)
        }


def main():
    """主函数入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/position_monitor.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        monitor = PositionMonitor()
        monitor.run()
        
    except Exception as e:
        logger = logging.getLogger("Main")
        logger.error(f"持仓监控启动失败: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())