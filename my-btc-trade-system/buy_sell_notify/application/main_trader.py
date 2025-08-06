"""
主交易应用程序
使用模块化架构的交易系统主程序
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio

from config.settings import AppConfig, TradingPairConfig, load_app_config
from infrastructure.exchange.binance import BinanceExchange
from core.signals.generator import SignalGenerator
from core.decision.engine import DecisionEngine
from utils.constants import TradingAction, Timeframe
from utils.helpers import (
    sanitize_log_data, create_log_safe_json, 
    safe_float_conversion, generate_trade_id
)


class MainTrader:
    """
    主交易应用程序
    
    负责：
    1. 协调各个模块的工作
    2. 执行完整的交易流程
    3. 处理多交易对的并发分析
    4. 管理应用程序生命周期
    """
    
    def __init__(self, config_path: str = "config.py"):
        """
        初始化主交易程序
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger("MainTrader")
        
        # 加载配置
        self.config = load_app_config(config_path)
        self.logger.info(f"配置加载完成，监控 {len(self.config.trading_pairs)} 个交易对")
        
        # 初始化交易所接口
        self.exchange = BinanceExchange()
        if not self.exchange.connect():
            raise ConnectionError("无法连接到币安交易所")
        self.logger.info("交易所连接成功")
        
        # 初始化决策引擎
        self.decision_engine = DecisionEngine(self.config.strategy_config)
        self.logger.info("决策引擎初始化完成")
        
        # 运行状态
        self.running = False
        self.last_analysis_time = {}
        
        # 性能统计
        self.stats = {
            'total_analysis_runs': 0,
            'successful_analyses': 0,
            'signals_generated': 0,
            'trading_decisions_made': 0,
            'start_time': None
        }
    
    def run(self):
        """启动主交易循环"""
        self.logger.info("🚀 主交易程序启动")
        self.running = True
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        try:
            while self.running:
                cycle_start_time = time.time()
                
                # 执行一轮完整的分析
                self._run_analysis_cycle()
                
                # 计算运行时间和休眠时间
                cycle_duration = time.time() - cycle_start_time
                sleep_time = max(0, self.config.analysis_interval - cycle_duration)
                
                self.logger.debug(f"分析周期耗时: {cycle_duration:.2f}s，休眠: {sleep_time:.2f}s")
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在优雅关闭...")
        except Exception as e:
            self.logger.error(f"主程序运行异常: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _run_analysis_cycle(self):
        """执行一轮完整的分析循环"""
        self.stats['total_analysis_runs'] += 1
        
        try:
            # 1. 获取账户状态
            account_status = self.exchange.get_account_status()
            if not account_status['success']:
                self.logger.error(f"获取账户状态失败: {account_status.get('error', '未知错误')}")
                return
            
            # 2. 并发分析所有交易对
            analysis_results = self._analyze_all_pairs(account_status)
            
            # 3. 处理分析结果
            self._process_analysis_results(analysis_results, account_status)
            
            self.stats['successful_analyses'] += 1
            
        except Exception as e:
            self.logger.error(f"分析周期执行失败: {e}", exc_info=True)
    
    def _analyze_all_pairs(self, account_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """并发分析所有交易对"""
        results = []
        
        for pair_config in self.config.trading_pairs:
            try:
                result = self._analyze_single_pair(pair_config, account_status)
                if result:
                    results.append(result)
                    
            except Exception as e:
                self.logger.error(f"分析 {pair_config.symbol} 失败: {e}")
                continue
        
        return results
    
    def _analyze_single_pair(self, 
                           pair_config: TradingPairConfig,
                           account_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分析单个交易对"""
        symbol = pair_config.symbol
        
        # 检查是否需要分析（时间间隔控制）
        if not self._should_analyze_pair(symbol):
            return None
        
        self.logger.debug(f"开始分析 {symbol}...")
        
        try:
            # 1. 收集多时间周期数据
            market_data = self._collect_multi_timeframe_data(pair_config)
            if not market_data:
                return None
            
            # 2. 获取ATR信息
            atr_info = self._get_atr_info(pair_config)
            
            # 3. 检查现有持仓
            existing_position = self._get_existing_position(symbol, account_status)
            
            # 4. 制定交易决策
            portfolio_state = self._build_portfolio_state(account_status)
            
            decision = self.decision_engine.make_decision(
                symbol, market_data, portfolio_state, existing_position
            )
            
            # 5. 构建完整的分析结果
            analysis_result = {
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc),
                'market_data': market_data,
                'atr_info': atr_info,
                'decision': decision,
                'existing_position': existing_position,
                'config': pair_config
            }
            
            self.logger.debug(f"{symbol} 分析完成: {decision['action']} (置信度: {decision['confidence']})")
            
            # 更新最后分析时间
            self.last_analysis_time[symbol] = time.time()
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"分析 {symbol} 时发生错误: {e}", exc_info=True)
            return None
    
    def _collect_multi_timeframe_data(self, pair_config: TradingPairConfig) -> Optional[Dict[str, Any]]:
        """收集多时间周期的市场数据"""
        symbol = pair_config.symbol
        timeframes = ['1d', '4h', '1h']  # 三重时间周期过滤
        
        market_data = {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc)
        }
        
        for tf in timeframes:
            try:
                # 创建信号生成器
                signal_generator = SignalGenerator(symbol, tf, self.exchange)
                
                # 生成信号
                signal_result = signal_generator.generate_signal()
                
                if signal_result['success']:
                    market_data[f'{tf}_analysis'] = {
                        'signal': signal_result['signal'],
                        'total_score': signal_result['total_score'],
                        'close_price': signal_result['close_price'],
                        'rsi_value': signal_result.get('rsi_value'),
                        'indicators': {
                            'current_price': signal_result.get('current_price'),
                            'rsi': signal_result.get('rsi_value'),
                            # 这里可以添加更多技术指标
                        }
                    }
                    
                    self.logger.debug(f"{symbol} {tf} 信号: {signal_result['signal']} (评分: {signal_result['total_score']})")
                else:
                    self.logger.warning(f"{symbol} {tf} 信号生成失败: {signal_result.get('error')}")
                    
            except Exception as e:
                self.logger.error(f"获取 {symbol} {tf} 数据失败: {e}")
        
        # 检查是否有足够的数据
        required_data = [f'{tf}_analysis' for tf in timeframes]
        if not all(key in market_data for key in required_data):
            self.logger.warning(f"{symbol} 缺少必要的时间周期数据")
            return None
        
        return market_data
    
    def _get_atr_info(self, pair_config: TradingPairConfig) -> Optional[Dict[str, Any]]:
        """获取ATR信息"""
        try:
            signal_generator = SignalGenerator(
                pair_config.symbol, pair_config.timeframe, self.exchange
            )
            
            atr_result = signal_generator.get_atr_info(pair_config)
            
            if atr_result['success']:
                return {
                    'atr': atr_result['atr'],
                    'timeframe': atr_result['timeframe'],
                    'length': atr_result['length'],
                    'symbol': atr_result['symbol']
                }
            else:
                self.logger.warning(f"获取 {pair_config.symbol} ATR失败: {atr_result.get('error')}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取 {pair_config.symbol} ATR信息异常: {e}")
            return None
    
    def _get_existing_position(self, symbol: str, account_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取现有持仓信息"""
        try:
            open_positions = account_status.get('open_positions', [])
            
            for position in open_positions:
                if position.get('symbol') == symbol:
                    return {
                        'symbol': symbol,
                        'side': position.get('side'),
                        'size': safe_float_conversion(position.get('size', 0)),
                        'entry_price': safe_float_conversion(position.get('entry_price', 0)),
                        'unrealized_pnl': safe_float_conversion(position.get('unrealized_pnl', 0)),
                        'mark_price': safe_float_conversion(position.get('mark_price', 0))
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 持仓信息失败: {e}")
            return None
    
    def _build_portfolio_state(self, account_status: Dict[str, Any]) -> Dict[str, Any]:
        """构建投资组合状态"""
        try:
            usdt_balance = account_status.get('usdt_balance', {})
            
            return {
                'total_balance': safe_float_conversion(usdt_balance.get('wallet_balance', 0)),
                'available_balance': safe_float_conversion(usdt_balance.get('available_balance', 0)),
                'total_unrealized_pnl': safe_float_conversion(usdt_balance.get('total_unrealized_pnl', 0)),
                'total_positions': len(account_status.get('open_positions', [])),
                'account_health': 'healthy'  # 可以根据具体指标计算
            }
            
        except Exception as e:
            self.logger.error(f"构建投资组合状态失败: {e}")
            return {
                'total_balance': 0,
                'available_balance': 0, 
                'total_unrealized_pnl': 0,
                'total_positions': 0,
                'account_health': 'unknown'
            }
    
    def _process_analysis_results(self, results: List[Dict[str, Any]], account_status: Dict[str, Any]):
        """处理所有分析结果"""
        if not results:
            self.logger.debug("本轮分析无有效结果")
            return
        
        trading_decisions = []
        
        for result in results:
            decision = result['decision']
            symbol = result['symbol']
            
            # 只处理非HOLD的决策
            if decision['action'] != TradingAction.HOLD.value:
                trading_decisions.append(result)
                self.stats['trading_decisions_made'] += 1
                
                # 记录交易信号
                self._log_trading_signal(result)
        
        # 如果有交易决策，发送通知
        if trading_decisions:
            self._send_trading_notifications(trading_decisions, account_status)
            self.stats['signals_generated'] += len(trading_decisions)
        
        # 记录运行状态
        self._log_system_status()
    
    def _log_trading_signal(self, result: Dict[str, Any]):
        """记录交易信号详情"""
        try:
            decision = result['decision']
            symbol = result['symbol']
            atr_info = result.get('atr_info', {})
            
            # 构建信号详情
            signal_details = {
                'symbol': symbol,
                'action': decision['action'],
                'confidence': decision['confidence'],
                'reason': decision['reason'],
                'strategy': decision.get('strategy', 'unknown'),
                'timestamp': result['timestamp'].isoformat(),
            }
            
            # 添加ATR信息
            if atr_info:
                signal_details.update({
                    'atr': atr_info.get('atr'),
                    'atr_timeframe': atr_info.get('timeframe'),
                    'atr_length': atr_info.get('length')
                })
            
            # 添加持仓信息（如果存在）
            existing_position = result.get('existing_position')
            if existing_position:
                signal_details['current_position'] = {
                    'side': existing_position.get('side'),
                    'size': existing_position.get('size'),
                    'entry_price': existing_position.get('entry_price'),
                    'unrealized_pnl': existing_position.get('unrealized_pnl')
                }
            
            self.logger.info(f"🎯 NEW TRADE SIGNAL: {create_log_safe_json(signal_details)}")
            
        except Exception as e:
            self.logger.error(f"记录交易信号失败: {e}")
    
    def _send_trading_notifications(self, decisions: List[Dict[str, Any]], account_status: Dict[str, Any]):
        """发送交易通知"""
        # 这里应该调用通知模块
        # 目前先记录日志
        for decision_result in decisions:
            symbol = decision_result['symbol']
            decision = decision_result['decision']
            
            notification_data = {
                'symbol': symbol,
                'action': decision['action'],
                'confidence': decision['confidence'],
                'reason': decision['reason'],
                'timestamp': decision_result['timestamp'].isoformat()
            }
            
            # 过滤敏感信息后记录
            safe_notification = sanitize_log_data(
                notification_data, 
                ['account_status', 'open_positions', 'balance']
            )
            
            self.logger.info(f"📨 发送交易通知: {create_log_safe_json(safe_notification)}")
    
    def _should_analyze_pair(self, symbol: str) -> bool:
        """判断是否应该分析该交易对"""
        if symbol not in self.last_analysis_time:
            return True
        
        # 检查时间间隔
        elapsed = time.time() - self.last_analysis_time[symbol]
        return elapsed >= self.config.min_analysis_interval
    
    def _log_system_status(self):
        """记录系统运行状态"""
        if self.stats['total_analysis_runs'] % 10 == 0:  # 每10轮记录一次
            uptime = datetime.now(timezone.utc) - self.stats['start_time']
            
            status = {
                'uptime': str(uptime).split('.')[0],  # 去掉微秒
                'total_analyses': self.stats['total_analysis_runs'],
                'successful_analyses': self.stats['successful_analyses'],
                'signals_generated': self.stats['signals_generated'],
                'decisions_made': self.stats['trading_decisions_made'],
                'success_rate': f"{(self.stats['successful_analyses']/self.stats['total_analysis_runs']*100):.1f}%" if self.stats['total_analysis_runs'] > 0 else "0%"
            }
            
            self.logger.info(f"📊 系统状态: {create_log_safe_json(status)}")
    
    def stop(self):
        """停止交易程序"""
        self.running = False
        
        # 记录最终统计
        final_stats = {
            'total_runtime': str(datetime.now(timezone.utc) - self.stats['start_time']).split('.')[0],
            'total_analyses': self.stats['total_analysis_runs'],
            'signals_generated': self.stats['signals_generated'],
            'decisions_made': self.stats['trading_decisions_made']
        }
        
        self.logger.info(f"🛑 交易程序已停止. 最终统计: {create_log_safe_json(final_stats)}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取程序运行状态"""
        return {
            'running': self.running,
            'stats': self.stats.copy(),
            'strategy_status': self.decision_engine.get_strategy_status() if self.decision_engine else None,
            'monitored_pairs': [pair.symbol for pair in self.config.trading_pairs]
        }


def main():
    """主函数入口"""
    # 设置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/trader.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # 创建并启动主交易程序
        trader = MainTrader()
        trader.run()
        
    except Exception as e:
        logger = logging.getLogger("Main")
        logger.error(f"程序启动失败: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())