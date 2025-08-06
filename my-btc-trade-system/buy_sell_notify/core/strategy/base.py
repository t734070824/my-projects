"""
交易策略基类
定义所有交易策略的标准接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from enum import Enum

from utils.constants import TradingAction, TradingSignal, StrategyType
from utils.helpers import safe_float_conversion


class StrategyResult:
    """策略执行结果"""
    
    def __init__(self, 
                 action: TradingAction,
                 confidence: float,
                 reason: str,
                 metadata: Optional[Dict[str, Any]] = None):
        self.action = action
        self.confidence = confidence  # 0.0 - 1.0
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'action': self.action.value,
            'confidence': self.confidence,
            'reason': self.reason,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }


class TradingStrategy(ABC):
    """
    交易策略抽象基类
    
    所有具体的交易策略都应该继承此类并实现必要的方法
    """
    
    def __init__(self, name: str, strategy_type: StrategyType):
        """
        初始化交易策略
        
        Args:
            name: 策略名称
            strategy_type: 策略类型
        """
        self.name = name
        self.strategy_type = strategy_type
        self.logger = logging.getLogger(f"Strategy.{name}")
        self.enabled = True
        self._results_history: List[StrategyResult] = []
    
    @abstractmethod
    def should_enter_long(self, 
                         market_data: Dict[str, Any],
                         portfolio_state: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该做多
        
        Args:
            market_data: 市场数据
            portfolio_state: 投资组合状态
            
        Returns:
            StrategyResult: 策略决策结果
        """
        pass
    
    @abstractmethod
    def should_enter_short(self, 
                          market_data: Dict[str, Any],
                          portfolio_state: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该做空
        
        Args:
            market_data: 市场数据
            portfolio_state: 投资组合状态
            
        Returns:
            StrategyResult: 策略决策结果
        """
        pass
    
    @abstractmethod
    def should_exit_position(self, 
                           position: Dict[str, Any],
                           market_data: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该平仓
        
        Args:
            position: 当前持仓信息
            market_data: 市场数据
            
        Returns:
            StrategyResult: 策略决策结果
        """
        pass
    
    def analyze_market_conditions(self, 
                                 market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析市场状况
        
        Args:
            market_data: 市场数据
            
        Returns:
            Dict[str, Any]: 市场分析结果
        """
        return {
            'trend': 'neutral',
            'volatility': 'normal',
            'strength': 0.5
        }
    
    def evaluate_decision(self, 
                         market_data: Dict[str, Any],
                         portfolio_state: Dict[str, Any],
                         existing_position: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        评估交易决策
        
        Args:
            market_data: 市场数据
            portfolio_state: 投资组合状态  
            existing_position: 现有持仓
            
        Returns:
            StrategyResult: 最终决策结果
        """
        if not self.enabled:
            return StrategyResult(
                TradingAction.HOLD,
                0.0,
                f"策略 {self.name} 已禁用"
            )
        
        try:
            # 如果有现有持仓，优先考虑平仓
            if existing_position:
                exit_result = self.should_exit_position(existing_position, market_data)
                if exit_result.action != TradingAction.HOLD:
                    return exit_result
            
            # 评估做多机会
            long_result = self.should_enter_long(market_data, portfolio_state)
            
            # 评估做空机会
            short_result = self.should_enter_short(market_data, portfolio_state)
            
            # 选择置信度最高的决策
            if long_result.confidence > short_result.confidence:
                if long_result.confidence > 0.5:  # 置信度阈值
                    return long_result
            else:
                if short_result.confidence > 0.5:
                    return short_result
            
            # 如果都不满足条件，持仓
            return StrategyResult(
                TradingAction.HOLD,
                0.0,
                "市场条件不满足入场要求"
            )
            
        except Exception as e:
            self.logger.error(f"策略 {self.name} 决策评估失败: {e}", exc_info=True)
            return StrategyResult(
                TradingAction.HOLD,
                0.0,
                f"策略评估出错: {str(e)}"
            )
    
    def get_risk_parameters(self, 
                           symbol: str,
                           market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        获取风险管理参数
        
        Args:
            symbol: 交易对符号
            market_data: 市场数据
            
        Returns:
            Dict[str, float]: 风险参数
        """
        return {
            'stop_loss_percent': 0.02,  # 2%
            'take_profit_percent': 0.04,  # 4%
            'max_position_size_percent': 0.1  # 10%
        }
    
    def enable(self):
        """启用策略"""
        self.enabled = True
        self.logger.info(f"策略 {self.name} 已启用")
    
    def disable(self):
        """禁用策略"""
        self.enabled = False
        self.logger.info(f"策略 {self.name} 已禁用")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取策略性能指标
        
        Returns:
            Dict[str, Any]: 性能指标
        """
        if not self._results_history:
            return {
                'total_decisions': 0,
                'success_rate': 0.0,
                'avg_confidence': 0.0
            }
        
        total_decisions = len(self._results_history)
        avg_confidence = sum(r.confidence for r in self._results_history) / total_decisions
        
        return {
            'total_decisions': total_decisions,
            'avg_confidence': avg_confidence,
            'strategy_type': self.strategy_type.value,
            'enabled': self.enabled
        }
    
    def _record_result(self, result: StrategyResult):
        """记录策略结果"""
        self._results_history.append(result)
        
        # 保持历史记录在合理范围内
        if len(self._results_history) > 1000:
            self._results_history = self._results_history[-500:]
    
    def _extract_signal_strength(self, signal: str) -> float:
        """
        从信号中提取强度值
        
        Args:
            signal: 交易信号
            
        Returns:
            float: 信号强度 (0.0 - 1.0)
        """
        signal_strength = {
            TradingSignal.STRONG_BUY.value: 1.0,
            TradingSignal.WEAK_BUY.value: 0.6,
            TradingSignal.NEUTRAL.value: 0.0,
            TradingSignal.WEAK_SELL.value: 0.6,
            TradingSignal.STRONG_SELL.value: 1.0
        }
        
        return signal_strength.get(signal, 0.0)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.name}({self.strategy_type.value})"
    
    def __repr__(self) -> str:
        """对象表示"""
        return f"TradingStrategy(name='{self.name}', type='{self.strategy_type.value}', enabled={self.enabled})"