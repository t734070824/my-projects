"""
趋势跟踪策略实现
基于多重时间周期过滤的趋势跟踪策略
"""

from typing import Dict, Any, Optional
from core.strategy.base import TradingStrategy, StrategyResult
from utils.constants import TradingAction, StrategyType, TradingSignal
from utils.helpers import safe_float_conversion, is_opposite_position


class TrendFollowingStrategy(TradingStrategy):
    """
    趋势跟踪策略
    
    使用三重时间周期过滤：
    1. 日线图确定长期趋势方向
    2. 4小时图确定中期趋势方向  
    3. 1小时图寻找具体入场时机
    """
    
    def __init__(self):
        super().__init__("TrendFollowing", StrategyType.TREND_FOLLOWING)
        
        # 策略参数
        self.required_timeframes = ['1d', '4h', '1h']
        self.min_score_threshold = 20  # 最小评分阈值
        self.strong_signal_threshold = 60  # 强信号阈值
    
    def should_enter_long(self, 
                         market_data: Dict[str, Any],
                         portfolio_state: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该做多
        
        条件：1日线看多 AND 4小时看多 AND 1小时出现买入信号
        """
        try:
            # 获取各时间周期的分析结果
            daily_analysis = market_data.get('daily_analysis', {})
            h4_analysis = market_data.get('h4_analysis', {})
            h1_analysis = market_data.get('h1_analysis', {})
            
            # 检查数据完整性
            if not all([daily_analysis, h4_analysis, h1_analysis]):
                return StrategyResult(
                    TradingAction.HOLD,
                    0.0,
                    "缺少必要的时间周期数据"
                )
            
            # 1. 检查长期趋势（1日线）
            daily_score = daily_analysis.get('total_score', 0)
            is_long_term_bullish = daily_score > 0
            
            # 2. 检查中期趋势（4小时）
            h4_score = h4_analysis.get('total_score', 0)
            is_mid_term_bullish = h4_score > 0
            
            # 3. 检查短期信号（1小时）
            h1_signal = h1_analysis.get('signal', TradingSignal.NEUTRAL.value)
            is_h1_buy_signal = h1_signal in [TradingSignal.STRONG_BUY.value, TradingSignal.WEAK_BUY.value]
            
            # 4. 综合判断
            if is_long_term_bullish and is_mid_term_bullish and is_h1_buy_signal:
                # 计算置信度
                confidence = self._calculate_long_confidence(daily_score, h4_score, h1_signal)
                
                reason = self._build_long_reason(
                    market_data.get('symbol', ''),
                    daily_score, h4_score, h1_signal
                )
                
                return StrategyResult(
                    TradingAction.EXECUTE_LONG,
                    confidence,
                    reason,
                    {
                        'daily_score': daily_score,
                        'h4_score': h4_score, 
                        'h1_signal': h1_signal,
                        'strategy_type': 'trend_following'
                    }
                )
            
            # 不满足条件
            reason = f"趋势条件不满足: 1d({daily_score}) 4h({h4_score}) 1h({h1_signal})"
            return StrategyResult(TradingAction.HOLD, 0.0, reason)
            
        except Exception as e:
            self.logger.error(f"评估做多信号失败: {e}", exc_info=True)
            return StrategyResult(TradingAction.HOLD, 0.0, f"策略评估错误: {str(e)}")
    
    def should_enter_short(self, 
                          market_data: Dict[str, Any],
                          portfolio_state: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该做空
        
        条件：1日线看空 AND 4小时看空 AND 1小时出现卖出信号
        """
        try:
            # 获取各时间周期的分析结果
            daily_analysis = market_data.get('daily_analysis', {})
            h4_analysis = market_data.get('h4_analysis', {})
            h1_analysis = market_data.get('h1_analysis', {})
            
            # 检查数据完整性
            if not all([daily_analysis, h4_analysis, h1_analysis]):
                return StrategyResult(
                    TradingAction.HOLD,
                    0.0,
                    "缺少必要的时间周期数据"
                )
            
            # 1. 检查长期趋势（1日线）
            daily_score = daily_analysis.get('total_score', 0)
            is_long_term_bearish = daily_score <= 0
            
            # 2. 检查中期趋势（4小时）
            h4_score = h4_analysis.get('total_score', 0)
            is_mid_term_bearish = h4_score <= 0
            
            # 3. 检查短期信号（1小时）
            h1_signal = h1_analysis.get('signal', TradingSignal.NEUTRAL.value)
            is_h1_sell_signal = h1_signal in [TradingSignal.STRONG_SELL.value, TradingSignal.WEAK_SELL.value]
            
            # 4. 综合判断
            if is_long_term_bearish and is_mid_term_bearish and is_h1_sell_signal:
                # 计算置信度
                confidence = self._calculate_short_confidence(daily_score, h4_score, h1_signal)
                
                reason = self._build_short_reason(
                    market_data.get('symbol', ''),
                    daily_score, h4_score, h1_signal
                )
                
                return StrategyResult(
                    TradingAction.EXECUTE_SHORT,
                    confidence,
                    reason,
                    {
                        'daily_score': daily_score,
                        'h4_score': h4_score,
                        'h1_signal': h1_signal,
                        'strategy_type': 'trend_following'
                    }
                )
            
            # 不满足条件
            reason = f"趋势条件不满足: 1d({daily_score}) 4h({h4_score}) 1h({h1_signal})"
            return StrategyResult(TradingAction.HOLD, 0.0, reason)
            
        except Exception as e:
            self.logger.error(f"评估做空信号失败: {e}", exc_info=True)
            return StrategyResult(TradingAction.HOLD, 0.0, f"策略评估错误: {str(e)}")
    
    def should_exit_position(self, 
                           position: Dict[str, Any],
                           market_data: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该平仓
        
        检查是否收到反向信号或风险管理要求平仓
        """
        try:
            position_side = position.get('side', '')
            h1_analysis = market_data.get('h1_analysis', {})
            
            if not h1_analysis:
                return StrategyResult(TradingAction.HOLD, 0.0, "缺少市场数据")
            
            h1_signal = h1_analysis.get('signal', TradingSignal.NEUTRAL.value)
            
            # 检查是否收到相反信号
            should_reverse = False
            if position_side == 'long' and h1_signal in [TradingSignal.STRONG_SELL.value, TradingSignal.WEAK_SELL.value]:
                should_reverse = True
            elif position_side == 'short' and h1_signal in [TradingSignal.STRONG_BUY.value, TradingSignal.WEAK_BUY.value]:
                should_reverse = True
            
            if should_reverse:
                return StrategyResult(
                    TradingAction.EXECUTE_SHORT if position_side == 'long' else TradingAction.EXECUTE_LONG,
                    0.8,
                    f"检测到反转信号：当前持仓{position_side.upper()}，新信号{h1_signal}",
                    {
                        'position_side': position_side,
                        'new_signal': h1_signal,
                        'action_type': 'reversal'
                    }
                )
            
            # 保持持仓
            return StrategyResult(TradingAction.HOLD, 0.0, "趋势延续，保持持仓")
            
        except Exception as e:
            self.logger.error(f"评估平仓信号失败: {e}", exc_info=True)
            return StrategyResult(TradingAction.HOLD, 0.0, f"平仓评估错误: {str(e)}")
    
    def _calculate_long_confidence(self, daily_score: int, h4_score: int, h1_signal: str) -> float:
        """计算做多信号的置信度"""
        base_confidence = 0.6
        
        # 根据评分调整置信度
        score_bonus = (daily_score + h4_score) / 200.0  # 归一化到0-1
        
        # 根据1小时信号强度调整
        signal_bonus = 0.2 if h1_signal == TradingSignal.STRONG_BUY.value else 0.1
        
        confidence = min(base_confidence + score_bonus + signal_bonus, 1.0)
        return round(confidence, 3)
    
    def _calculate_short_confidence(self, daily_score: int, h4_score: int, h1_signal: str) -> float:
        """计算做空信号的置信度"""
        base_confidence = 0.6
        
        # 根据评分调整置信度（负分越低置信度越高）
        score_bonus = abs(daily_score + h4_score) / 200.0
        
        # 根据1小时信号强度调整
        signal_bonus = 0.2 if h1_signal == TradingSignal.STRONG_SELL.value else 0.1
        
        confidence = min(base_confidence + score_bonus + signal_bonus, 1.0)
        return round(confidence, 3)
    
    def _build_long_reason(self, symbol: str, daily_score: int, h4_score: int, h1_signal: str) -> str:
        """构建做多决策的原因描述"""
        return f"[{symbol}] 1d, 4h趋势看多，且1h出现买入信号。"
    
    def _build_short_reason(self, symbol: str, daily_score: int, h4_score: int, h1_signal: str) -> str:
        """构建做空决策的原因描述"""
        return f"[{symbol}] 1d, 4h趋势看空，且1h出现卖出信号。"
    
    def get_risk_parameters(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        获取趋势跟踪策略的风险参数
        """
        # 基础风险参数
        base_params = super().get_risk_parameters(symbol, market_data)
        
        # 趋势跟踪策略特定参数
        trend_params = {
            'stop_loss_atr_multiplier': 2.0,  # 2倍ATR止损
            'take_profit_multiplier_1': 2.0,  # 2R止盈
            'take_profit_multiplier_2': 3.0,  # 3R止盈
            'trailing_stop_atr_multiplier': 2.0,  # 追踪止损
        }
        
        base_params.update(trend_params)
        return base_params