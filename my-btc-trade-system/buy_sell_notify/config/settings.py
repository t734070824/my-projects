"""
配置设置模块
集中管理所有配置项，提供类型安全和默认值
"""

import os
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

from utils.constants import Timeframe, DEFAULT_ATR_MULTIPLIER


@dataclass
class ExchangeConfig:
    """交易所配置"""
    api_key: str
    secret_key: str
    sandbox: bool = False
    testnet: bool = False
    proxy: Optional[str] = None


@dataclass
class TradingPairConfig:
    """交易对配置"""
    symbol: str
    risk_per_trade_percent: float
    atr_multiplier_for_sl: float
    timeframe: str = Timeframe.H4.value
    atr_length: int = 20


@dataclass
class StrategyConfig:
    """策略配置"""
    enabled: bool = True
    timeframe: str = Timeframe.H1.value
    risk_per_trade_percent: float = 0.8
    atr_multiplier_for_sl: float = 1.5
    rsi_oversold: int = 28
    rsi_overbought: int = 72


@dataclass
class LoggingConfig:
    """日志配置"""
    log_dir: str = "./logs"
    main_log_file: str = "trading_system.log"
    position_log_file: str = "position_monitor.log"
    max_log_size_mb: int = 50
    backup_count: int = 5
    log_level: str = "INFO"
    console_output: bool = True


@dataclass
class BackupConfig:
    """备份配置"""
    remove_original_after_backup: bool = True
    backup_retention_days: int = 30
    auto_cleanup_old_backups: bool = True


@dataclass
class NotificationConfig:
    """通知配置"""
    dingtalk_webhook: str
    dingtalk_secret: Optional[str] = None
    message_size_limit: int = 20000
    safe_size_limit: int = 18000


@dataclass
class MonitoringConfig:
    """监控配置"""
    base_interval_seconds: int = 10
    no_position_interval_seconds: int = 60
    high_profit_interval_seconds: int = 5
    run_at_minute: str = ":01"


class TradingSystemConfig:
    """交易系统主配置类"""
    
    def __init__(self):
        self._load_from_legacy_config()
    
    def _load_from_legacy_config(self):
        """从旧的config.py加载配置"""
        try:
            # 导入旧配置 - 使用sys.path和importlib避免命名冲突
            import sys
            import os
            import importlib.util
            
            # 获取config.py文件的绝对路径
            config_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
            
            # 使用importlib动态导入config.py文件
            spec = importlib.util.spec_from_file_location("legacy_config", config_file_path)
            legacy_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy_config)
            
            # 交易所配置
            self.exchange = ExchangeConfig(
                api_key=getattr(legacy_config, 'API_KEY', ''),
                secret_key=getattr(legacy_config, 'SECRET_KEY', ''),
                proxy=getattr(legacy_config, 'PROXY', None)
            )
            
            # 交易对配置
            self.trading_pairs = self._create_trading_pairs_config(legacy_config)
            
            # 分析设置
            self.symbols_to_analyze: List[str] = getattr(
                legacy_config, 'SYMBOLS_TO_ANALYZE', []
            )
            
            # 策略配置
            self.reversal_strategy = StrategyConfig(
                enabled=getattr(legacy_config, 'REVERSAL_STRATEGY_CONFIG', {}).get('enabled', True),
                timeframe=getattr(legacy_config, 'REVERSAL_STRATEGY_CONFIG', {}).get('timeframe', '1h'),
                risk_per_trade_percent=getattr(legacy_config, 'REVERSAL_STRATEGY_CONFIG', {}).get('risk_per_trade_percent', 0.8),
                atr_multiplier_for_sl=getattr(legacy_config, 'REVERSAL_STRATEGY_CONFIG', {}).get('atr_multiplier_for_sl', 1.5),
                rsi_oversold=getattr(legacy_config, 'REVERSAL_STRATEGY_CONFIG', {}).get('rsi_oversold', 28),
                rsi_overbought=getattr(legacy_config, 'REVERSAL_STRATEGY_CONFIG', {}).get('rsi_overbought', 72)
            )
            
            # 日志配置
            log_config = getattr(legacy_config, 'LOG_CONFIG', {})
            self.logging = LoggingConfig(
                log_dir=log_config.get('log_dir', './logs'),
                main_log_file=log_config.get('main_log_file', 'trading_system.log'),
                position_log_file=log_config.get('position_log_file', 'position_monitor.log'),
                max_log_size_mb=log_config.get('max_log_size_mb', 50),
                backup_count=log_config.get('backup_count', 5),
                log_level=log_config.get('log_level', 'INFO'),
                console_output=log_config.get('console_output', True)
            )
            
            # 备份配置
            backup_config = getattr(legacy_config, 'BACKUP_CONFIG', {})
            self.backup = BackupConfig(
                remove_original_after_backup=backup_config.get('remove_original_after_backup', True),
                backup_retention_days=backup_config.get('backup_retention_days', 30),
                auto_cleanup_old_backups=backup_config.get('auto_cleanup_old_backups', True)
            )
            
            # 通知配置
            self.notification = NotificationConfig(
                dingtalk_webhook=getattr(legacy_config, 'DINGTALK_WEBHOOK', ''),
                dingtalk_secret=getattr(legacy_config, 'DINGTALK_SECRET', None)
            )
            
            # 监控配置
            self.monitoring = MonitoringConfig(
                base_interval_seconds=getattr(legacy_config, 'MONITOR_INTERVAL_SECONDS', 10),
                no_position_interval_seconds=getattr(legacy_config, 'MONITOR_INTERVAL_NO_POSITION', 60),
                high_profit_interval_seconds=getattr(legacy_config, 'MONITOR_INTERVAL_HIGH_PROFIT', 5),
                run_at_minute=getattr(legacy_config, 'RUN_AT_MINUTE', ':01')
            )
            
            # 应用程序级别配置
            self.analysis_interval = getattr(legacy_config, 'analysis_interval', 300)
            self.min_analysis_interval = getattr(legacy_config, 'min_analysis_interval', 60)
            self.position_monitor_interval = getattr(legacy_config, 'position_monitor_interval', 120)
            
            # 策略配置（兼容性）
            self.strategy_config = {
                'reversal_strategy': {
                    'enabled': self.reversal_strategy.enabled,
                    'rsi_oversold': self.reversal_strategy.rsi_oversold,
                    'rsi_overbought': self.reversal_strategy.rsi_overbought,
                    'risk_per_trade_percent': self.reversal_strategy.risk_per_trade_percent,
                    'atr_multiplier_for_sl': self.reversal_strategy.atr_multiplier_for_sl
                }
            }
            
            # 钉钉配置（兼容性）
            self.dingtalk_webhook = self.notification.dingtalk_webhook
            self.dingtalk_secret = self.notification.dingtalk_secret
            
        except ImportError:
            # 如果无法导入旧配置，使用默认值
            self._set_default_config()
    
    def _create_trading_pairs_config(self, legacy_config) -> Dict[str, TradingPairConfig]:
        """创建交易对配置"""
        trading_pairs = {}
        
        # 获取旧配置
        virtual_trade_config = getattr(legacy_config, 'VIRTUAL_TRADE_CONFIG', {})
        atr_config = getattr(legacy_config, 'ATR_CONFIG', {})
        
        # 默认配置
        default_virtual = virtual_trade_config.get('DEFAULT', {})
        default_atr = atr_config.get('DEFAULT', {})
        
        # 为每个交易对创建配置
        symbols = getattr(legacy_config, 'SYMBOLS_TO_ANALYZE', [])
        for symbol in symbols:
            virtual_cfg = virtual_trade_config.get(symbol, default_virtual)
            atr_cfg = atr_config.get(symbol, default_atr)
            
            trading_pairs[symbol] = TradingPairConfig(
                symbol=symbol,
                risk_per_trade_percent=virtual_cfg.get('RISK_PER_TRADE_PERCENT', 2.5),
                atr_multiplier_for_sl=virtual_cfg.get('ATR_MULTIPLIER_FOR_SL', DEFAULT_ATR_MULTIPLIER),
                timeframe=atr_cfg.get('timeframe', Timeframe.H4.value),
                atr_length=atr_cfg.get('length', 20)
            )
        
        return trading_pairs
    
    def _set_default_config(self):
        """设置默认配置"""
        self.exchange = ExchangeConfig(api_key='', secret_key='')
        self.trading_pairs = {}
        self.symbols_to_analyze = []
        self.reversal_strategy = StrategyConfig()
        self.logging = LoggingConfig()
        self.backup = BackupConfig()
        self.notification = NotificationConfig(dingtalk_webhook='')
        self.monitoring = MonitoringConfig()
        
        # 应用程序级别配置
        self.analysis_interval = 300
        self.min_analysis_interval = 60
        self.position_monitor_interval = 120
        
        # 策略配置
        self.strategy_config = {
            'reversal_strategy': {
                'enabled': True,
                'rsi_oversold': 28,
                'rsi_overbought': 72,
                'risk_per_trade_percent': 0.8,
                'atr_multiplier_for_sl': 1.5
            }
        }
        
        # 钉钉配置
        self.dingtalk_webhook = ''
        self.dingtalk_secret = None
    
    def get_trading_pair_config(self, symbol: str) -> TradingPairConfig:
        """
        获取指定交易对的配置
        
        Args:
            symbol: 交易对符号
            
        Returns:
            TradingPairConfig: 交易对配置
        """
        if symbol in self.trading_pairs:
            return self.trading_pairs[symbol]
        
        # 返回默认配置
        return TradingPairConfig(
            symbol=symbol,
            risk_per_trade_percent=2.5,
            atr_multiplier_for_sl=DEFAULT_ATR_MULTIPLIER
        )
    
    def validate_config(self) -> List[str]:
        """
        验证配置完整性
        
        Returns:
            List[str]: 配置错误列表
        """
        errors = []
        
        if not self.exchange.api_key:
            errors.append("缺少API密钥")
            
        if not self.exchange.secret_key:
            errors.append("缺少API密钥")
            
        if not self.notification.dingtalk_webhook:
            errors.append("缺少钉钉Webhook地址")
            
        if not self.symbols_to_analyze:
            errors.append("没有配置要分析的交易对")
        
        return errors


# 兼容性别名
AppConfig = TradingSystemConfig


def load_app_config(config_path: str = "config.py") -> TradingSystemConfig:
    """
    加载应用配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TradingSystemConfig: 配置实例
    """
    return TradingSystemConfig()


# 全局配置实例
config = TradingSystemConfig()