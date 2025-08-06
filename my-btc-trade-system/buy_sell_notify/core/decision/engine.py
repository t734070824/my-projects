"""
决策引擎
整合多个策略的决策结果，生成最终的交易决策
"""

from typing import Dict, Any, List, Optional, Tuple
import logging

from core.strategy.base import TradingStrategy, StrategyResult
from core.strategy.trend_following import TrendFollowingStrategy
from core.strategy.mean_reversion import MeanReversionStrategy
from utils.constants import TradingAction
from utils.helpers import is_opposite_position, safe_float_conversion


class DecisionEngine:
    """
    决策引擎
    
    负责：
    1. 管理多个交易策略
    2. 整合策略决策结果
    3. 处理策略冲突
    4. 生成最终交易决策
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化决策引擎
        
        Args:
            config: 策略配置
        """
        self.logger = logging.getLogger("DecisionEngine")
        self.config = config
        
        # 初始化策略
        self.strategies: List[TradingStrategy] = []
        self._initialize_strategies()
        
        # 决策权重
        self.strategy_weights = {
            'TrendFollowing': 0.7,  # 趋势跟踪权重更高
            'MeanReversion': 0.3    # 反转策略权重较低
        }
        
        # 决策阈值
        self.min_confidence_threshold = 0.6
        self.conflict_resolution_threshold = 0.2
    
    def _initialize_strategies(self):
        """初始化所有策略"""
        try:
            # 初始化趋势跟踪策略
            trend_strategy = TrendFollowingStrategy()
            self.strategies.append(trend_strategy)
            self.logger.info("趋势跟踪策略已加载")
            
            # 初始化反转策略
            reversal_config = self.config.get('reversal_strategy', {})
            if reversal_config.get('enabled', True):
                mean_reversion_strategy = MeanReversionStrategy(reversal_config)
                self.strategies.append(mean_reversion_strategy)
                self.logger.info("反转策略已加载")
            
            self.logger.info(f"决策引擎初始化完成，加载了 {len(self.strategies)} 个策略")
            
        except Exception as e:
            self.logger.error(f"初始化策略失败: {e}", exc_info=True)
            raise
    
    def make_decision(self, 
                     symbol: str,
                     market_data: Dict[str, Any],
                     portfolio_state: Dict[str, Any],
                     existing_position: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        制定交易决策
        
        Args:
            symbol: 交易对符号
            market_data: 市场数据
            portfolio_state: 投资组合状态
            existing_position: 现有持仓
            
        Returns:
            Dict[str, Any]: 决策结果
        """
        self.logger.debug(f"开始为 {symbol} 制定交易决策")
        
        try:
            # 1. 收集所有策略的决策
            strategy_results = self._collect_strategy_decisions(
                market_data, portfolio_state, existing_position
            )
            
            if not strategy_results:
                return self._create_decision_result(
                    symbol, TradingAction.HOLD, 0.0, "没有可用的策略决策"
                )
            
            # 2. 检查是否有现有持仓需要特殊处理
            if existing_position:
                reversal_decision = self._check_position_reversal(
                    existing_position, strategy_results, symbol
                )
                if reversal_decision:
                    return reversal_decision
            
            # 3. 解决策略冲突并选择最佳决策
            final_decision = self._resolve_conflicts_and_decide(strategy_results, symbol)
            
            return final_decision
            
        except Exception as e:
            self.logger.error(f"制定 {symbol} 决策时发生错误: {e}", exc_info=True)
            return self._create_decision_result(
                symbol, TradingAction.HOLD, 0.0, f"决策过程出错: {str(e)}"
            )
    
    def _collect_strategy_decisions(self, 
                                  market_data: Dict[str, Any],
                                  portfolio_state: Dict[str, Any],
                                  existing_position: Optional[Dict[str, Any]]) -> List[Tuple[TradingStrategy, StrategyResult]]:
        """收集所有策略的决策结果"""
        results = []
        
        for strategy in self.strategies:
            if not strategy.enabled:
                continue
            
            try:
                # 对于反转策略，需要检查是否已有持仓
                if strategy.name == 'MeanReversion' and existing_position:
                    self.logger.debug(f"跳过反转策略：已存在 {existing_position.get('symbol', '')} 持仓")
                    continue
                
                # 获取策略决策
                decision = strategy.evaluate_decision(
                    market_data, portfolio_state, existing_position
                )
                
                if decision.action != TradingAction.HOLD:
                    results.append((strategy, decision))
                    self.logger.debug(f"策略 {strategy.name} 建议: {decision.action.value} (置信度: {decision.confidence})")
                
            except Exception as e:
                self.logger.error(f"策略 {strategy.name} 决策失败: {e}")
                continue
        
        return results
    
    def _check_position_reversal(self, 
                               existing_position: Dict[str, Any],
                               strategy_results: List[Tuple[TradingStrategy, StrategyResult]],
                               symbol: str) -> Optional[Dict[str, Any]]:
        """
        检查是否需要反转现有持仓
        """
        position_side = existing_position.get('side', '')
        
        for strategy, result in strategy_results:
            # 检查是否为相反方向的信号
            is_reversal = is_opposite_position(position_side, result.action.value)
            
            if is_reversal and result.confidence >= self.min_confidence_threshold:
                self.logger.warning(f"检测到反转信号: 当前持仓{position_side} vs 新信号{result.action.value}")
                
                return self._create_reversal_decision(
                    symbol, position_side, result.action, result.confidence, result.reason
                )
        
        return None
    
    def _resolve_conflicts_and_decide(self, 
                                    strategy_results: List[Tuple[TradingStrategy, StrategyResult]],
                                    symbol: str) -> Dict[str, Any]:
        """解决策略冲突并做出最终决策"""
        
        if not strategy_results:
            return self._create_decision_result(
                symbol, TradingAction.HOLD, 0.0, "没有策略建议交易"
            )
        
        # 如果只有一个策略建议，直接使用
        if len(strategy_results) == 1:
            strategy, result = strategy_results[0]
            return self._create_decision_result(
                symbol, result.action, result.confidence, result.reason, strategy.name
            )
        
        # 多策略决策：按权重计算最终决策
        weighted_decisions = self._calculate_weighted_decisions(strategy_results)
        
        # 选择权重最高的决策
        best_action = max(weighted_decisions.keys(), key=lambda x: weighted_decisions[x]['total_weight'])
        best_decision = weighted_decisions[best_action]
        
        # 检查是否满足最小置信度要求
        if best_decision['avg_confidence'] >= self.min_confidence_threshold:
            reason = self._build_combined_reason(best_decision['strategies'])
            
            return self._create_decision_result(
                symbol, 
                TradingAction(best_action),
                best_decision['avg_confidence'], 
                reason,
                strategy_names=[s.name for s in best_decision['strategies']]
            )
        
        # 置信度不足，保持观望
        return self._create_decision_result(
            symbol, TradingAction.HOLD, 0.0, "策略信号置信度不足"
        )
    
    def _calculate_weighted_decisions(self, 
                                    strategy_results: List[Tuple[TradingStrategy, StrategyResult]]) -> Dict[str, Dict]:
        """计算加权决策结果"""
        weighted_decisions = {}
        
        for strategy, result in strategy_results:
            action = result.action.value
            weight = self.strategy_weights.get(strategy.name, 0.5)
            weighted_confidence = result.confidence * weight
            
            if action not in weighted_decisions:
                weighted_decisions[action] = {
                    'total_weight': 0,
                    'total_confidence': 0,
                    'strategies': [],
                    'avg_confidence': 0
                }
            
            weighted_decisions[action]['total_weight'] += weight
            weighted_decisions[action]['total_confidence'] += weighted_confidence
            weighted_decisions[action]['strategies'].append(strategy)
            
            # 计算平均置信度
            strategy_count = len(weighted_decisions[action]['strategies'])
            weighted_decisions[action]['avg_confidence'] = (
                weighted_decisions[action]['total_confidence'] / weighted_decisions[action]['total_weight']
            )
        
        return weighted_decisions
    
    def _build_combined_reason(self, strategies: List[TradingStrategy]) -> str:
        """构建组合策略的决策原因"""
        strategy_names = [s.name for s in strategies]
        
        if len(strategy_names) == 1:
            return f"基于{strategy_names[0]}策略的综合分析"
        else:
            return f"基于多策略({'、'.join(strategy_names)})的综合分析"
    
    def _create_decision_result(self, 
                              symbol: str,
                              action: TradingAction,
                              confidence: float,
                              reason: str,
                              strategy_name: Optional[str] = None,
                              strategy_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """创建标准化的决策结果"""
        return {
            'symbol': symbol,
            'action': action.value,
            'confidence': round(confidence, 3),
            'reason': reason,
            'strategy': strategy_name or strategy_names,
            'timestamp': None,  # 由调用方设置
            'metadata': {
                'engine': 'DecisionEngine',
                'strategy_count': len(self.strategies),
                'enabled_strategies': [s.name for s in self.strategies if s.enabled]
            }
        }
    
    def _create_reversal_decision(self, 
                                symbol: str,
                                current_side: str,
                                new_action: TradingAction,
                                confidence: float,
                                reason: str) -> Dict[str, Any]:
        """创建反转决策结果"""
        return {
            'symbol': symbol,
            'action': new_action.value,
            'confidence': confidence,
            'reason': reason,
            'reversal': True,
            'current_position_side': current_side,
            'timestamp': None,
            'metadata': {
                'engine': 'DecisionEngine',
                'decision_type': 'reversal',
                'action_required': f"先平仓{current_side}，再开{new_action.value.replace('EXECUTE_', '')}"
            }
        }
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """获取所有策略的状态"""
        status = {
            'total_strategies': len(self.strategies),
            'enabled_strategies': sum(1 for s in self.strategies if s.enabled),
            'strategies': []
        }
        
        for strategy in self.strategies:
            strategy_status = {
                'name': strategy.name,
                'type': strategy.strategy_type.value,
                'enabled': strategy.enabled,
                'weight': self.strategy_weights.get(strategy.name, 0.5),
                'performance': strategy.get_performance_metrics()
            }
            status['strategies'].append(strategy_status)
        
        return status
    
    def enable_strategy(self, strategy_name: str) -> bool:
        """启用指定策略"""
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                strategy.enable()
                self.logger.info(f"策略 {strategy_name} 已启用")
                return True
        
        self.logger.warning(f"策略 {strategy_name} 不存在")
        return False
    
    def disable_strategy(self, strategy_name: str) -> bool:
        """禁用指定策略"""
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                strategy.disable()
                self.logger.info(f"策略 {strategy_name} 已禁用")
                return True
        
        self.logger.warning(f"策略 {strategy_name} 不存在")
        return False