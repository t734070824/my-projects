"""
均值回归（反转）策略实现
基于极端RSI和布林带边界的反转交易策略
"""

from typing import Dict, Any, Optional
from core.strategy.base import TradingStrategy, StrategyResult
from utils.constants import (
    TradingAction, StrategyType, TradingSignal,
    RSI_EXTREME_OVERSOLD, RSI_EXTREME_OVERBOUGHT
)
from utils.helpers import safe_float_conversion


class MeanReversionStrategy(TradingStrategy):
    """
    均值回归（反转）策略
    
    在市场出现极端超卖或超买时寻找反转机会：
    1. RSI达到极端水平（<20 或 >80）
    2. 价格触及布林带边界
    3. 快速进出，严格止损
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MeanReversion", StrategyType.MEAN_REVERSION)
        
        # 从配置加载参数，使用默认值作为备选
        config = config or {}
        
        self.rsi_oversold_threshold = config.get('rsi_oversold', 28)
        self.rsi_overbought_threshold = config.get('rsi_overbought', 72)
        self.risk_per_trade_percent = config.get('risk_per_trade_percent', 0.8)
        self.atr_multiplier_for_sl = config.get('atr_multiplier_for_sl', 1.5)
        
        # 策略特有参数
        self.min_rsi_extreme = 20  # 极端RSI阈值
        self.max_rsi_extreme = 80
        self.min_confidence_threshold = 0.7  # 最小置信度要求
    
    def should_enter_long(self, 
                         market_data: Dict[str, Any],
                         portfolio_state: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该做多（反转向上）
        
        条件：RSI极端超卖 AND 价格触及布林带下轨
        """
        try:
            h1_analysis = market_data.get('h1_analysis', {})
            
            if not h1_analysis:
                return StrategyResult(
                    TradingAction.HOLD,
                    0.0,
                    "缺少1小时分析数据"
                )
            
            # 获取RSI和布林带信息
            rsi_value = h1_analysis.get('rsi_value', 50)
            indicators = h1_analysis.get('indicators', {})
            
            current_price = indicators.get('current_price', 0)
            bb_lower = indicators.get('bb_lower', 0)
            bb_middle = indicators.get('bb_middle', 0)
            
            # 1. 检查RSI是否极端超卖
            is_rsi_extreme_oversold = rsi_value <= self.min_rsi_extreme
            
            # 2. 检查是否触及布林带下轨
            is_at_bb_lower = current_price <= bb_lower if bb_lower > 0 else False
            
            # 3. 额外确认：价格相对于中轨的位置
            price_below_middle = current_price < bb_middle if bb_middle > 0 else False
            
            # 4. 综合判断
            if is_rsi_extreme_oversold and is_at_bb_lower:
                confidence = self._calculate_reversal_confidence(
                    rsi_value, current_price, bb_lower, bb_middle, 'long'
                )
                
                if confidence >= self.min_confidence_threshold:
                    reason = self._build_reversal_long_reason(
                        market_data.get('symbol', ''),
                        rsi_value, current_price, bb_lower
                    )
                    
                    return StrategyResult(
                        TradingAction.EXECUTE_LONG,
                        confidence,
                        reason,
                        {
                            'rsi_value': rsi_value,
                            'current_price': current_price,
                            'bb_lower': bb_lower,
                            'strategy_type': 'mean_reversion',
                            'reversal_type': 'oversold_bounce'
                        }
                    )
            
            # 不满足反转条件
            reason = f"反转做多条件不满足: RSI={rsi_value:.1f}({is_rsi_extreme_oversold}) 价格触底={is_at_bb_lower}"
            return StrategyResult(TradingAction.HOLD, 0.0, reason)
            
        except Exception as e:
            self.logger.error(f"评估反转做多信号失败: {e}", exc_info=True)
            return StrategyResult(TradingAction.HOLD, 0.0, f"反转策略评估错误: {str(e)}")
    
    def should_enter_short(self, 
                          market_data: Dict[str, Any],
                          portfolio_state: Dict[str, Any]) -> StrategyResult:
        """
        判断是否应该做空（反转向下）
        
        条件：RSI极端超买 AND 价格触及布林带上轨
        """
        try:
            h1_analysis = market_data.get('h1_analysis', {})
            
            if not h1_analysis:
                return StrategyResult(
                    TradingAction.HOLD,
                    0.0,
                    "缺少1小时分析数据"
                )
            
            # 获取RSI和布林带信息
            rsi_value = h1_analysis.get('rsi_value', 50)
            indicators = h1_analysis.get('indicators', {})
            
            current_price = indicators.get('current_price', 0)
            bb_upper = indicators.get('bb_upper', 0)
            bb_middle = indicators.get('bb_middle', 0)
            
            # 1. 检查RSI是否极端超买
            is_rsi_extreme_overbought = rsi_value >= self.max_rsi_extreme
            
            # 2. 检查是否触及布林带上轨
            is_at_bb_upper = current_price >= bb_upper if bb_upper > 0 else False
            
            # 3. 额外确认：价格相对于中轨的位置
            price_above_middle = current_price > bb_middle if bb_middle > 0 else False
            
            # 4. 综合判断
            if is_rsi_extreme_overbought and is_at_bb_upper:
                confidence = self._calculate_reversal_confidence(
                    rsi_value, current_price, bb_upper, bb_middle, 'short'
                )
                
                if confidence >= self.min_confidence_threshold:
                    reason = self._build_reversal_short_reason(
                        market_data.get('symbol', ''),
                        rsi_value, current_price, bb_upper
                    )
                    
                    return StrategyResult(
                        TradingAction.EXECUTE_SHORT,
                        confidence,
                        reason,
                        {
                            'rsi_value': rsi_value,
                            'current_price': current_price,
                            'bb_upper': bb_upper,
                            'strategy_type': 'mean_reversion',
                            'reversal_type': 'overbought_correction'
                        }
                    )
            
            # 不满足反转条件
            reason = f"反转做空条件不满足: RSI={rsi_value:.1f}({is_rsi_extreme_overbought}) 价格触顶={is_at_bb_upper}"
            return StrategyResult(TradingAction.HOLD, 0.0, reason)
            
        except Exception as e:
            self.logger.error(f"评估反转做空信号失败: {e}", exc_info=True)
            return StrategyResult(TradingAction.HOLD, 0.0, f"反转策略评估错误: {str(e)}")
    
    def should_exit_position(self, 
                           position: Dict[str, Any],
                           market_data: Dict[str, Any]) -> StrategyResult:
        """
        判断反转策略是否应该平仓
        
        反转策略特点：快进快出，达到目标或RSI回到中性区域就平仓
        """
        try:
            position_side = position.get('side', '')
            entry_price = safe_float_conversion(position.get('entry_price', 0))
            unrealized_pnl = safe_float_conversion(position.get('unrealized_pnl', 0))
            
            h1_analysis = market_data.get('h1_analysis', {})
            if not h1_analysis:
                return StrategyResult(TradingAction.HOLD, 0.0, "缺少市场数据")
            
            current_price = h1_analysis.get('close_price', 0)
            rsi_value = h1_analysis.get('rsi_value', 50)
            
            # 1. 检查是否达到止盈目标
            profit_ratio = 0
            if entry_price > 0:
                if position_side == 'long':
                    profit_ratio = (current_price - entry_price) / entry_price
                else:
                    profit_ratio = (entry_price - current_price) / entry_price
            
            # 反转策略目标：1.5R或2R
            if profit_ratio >= 0.03:  # 3%目标利润
                return StrategyResult(
                    TradingAction.HOLD,  # 实际应该是平仓，但这里返回HOLD表示无需新开仓
                    0.9,
                    f"反转策略达到止盈目标: {profit_ratio:.2%}",
                    {'action_type': 'take_profit', 'profit_ratio': profit_ratio}
                )
            
            # 2. 检查RSI是否回到中性区域（反转信号失效）
            rsi_neutral = 40 <= rsi_value <= 60
            if rsi_neutral and profit_ratio > 0.01:  # RSI回中性且有小幅盈利
                return StrategyResult(
                    TradingAction.HOLD,
                    0.7,
                    f"RSI回到中性区域({rsi_value:.1f})，反转信号结束",
                    {'action_type': 'signal_exhausted', 'rsi_value': rsi_value}
                )
            
            # 3. 检查止损条件
            if profit_ratio <= -0.02:  # -2%止损
                return StrategyResult(
                    TradingAction.HOLD,
                    0.8,
                    f"触发止损: {profit_ratio:.2%}",
                    {'action_type': 'stop_loss', 'loss_ratio': profit_ratio}
                )
            
            # 继续持仓
            return StrategyResult(
                TradingAction.HOLD,
                0.0,
                f"反转交易继续: PnL={profit_ratio:.2%}, RSI={rsi_value:.1f}"
            )
            
        except Exception as e:
            self.logger.error(f"评估反转平仓信号失败: {e}", exc_info=True)
            return StrategyResult(TradingAction.HOLD, 0.0, f"反转平仓评估错误: {str(e)}")
    
    def _calculate_reversal_confidence(self, 
                                     rsi_value: float,
                                     current_price: float, 
                                     bb_boundary: float,
                                     bb_middle: float,
                                     direction: str) -> float:
        """计算反转信号的置信度"""
        base_confidence = 0.6
        
        # RSI极端程度加分
        if direction == 'long':
            rsi_extreme_score = max(0, (30 - rsi_value) / 30)  # RSI越低分数越高
        else:
            rsi_extreme_score = max(0, (rsi_value - 70) / 30)  # RSI越高分数越高
        
        # 布林带位置加分
        bb_score = 0
        if bb_boundary > 0 and bb_middle > 0:
            if direction == 'long':
                # 价格越接近下轨得分越高
                distance_ratio = abs(current_price - bb_boundary) / abs(bb_middle - bb_boundary)
                bb_score = max(0, 1 - distance_ratio)
            else:
                # 价格越接近上轨得分越高
                distance_ratio = abs(current_price - bb_boundary) / abs(bb_boundary - bb_middle)
                bb_score = max(0, 1 - distance_ratio)
        
        # 综合置信度
        confidence = base_confidence + (rsi_extreme_score * 0.2) + (bb_score * 0.15)
        return min(round(confidence, 3), 1.0)
    
    def _build_reversal_long_reason(self, symbol: str, rsi: float, price: float, bb_lower: float) -> str:
        """构建反转做多的原因描述"""
        return f"[{symbol}] 激进反转策略 - RSI严重超卖({rsi:.1f})且触及布林下轨。"
    
    def _build_reversal_short_reason(self, symbol: str, rsi: float, price: float, bb_upper: float) -> str:
        """构建反转做空的原因描述"""
        return f"[{symbol}] 激进反转策略 - RSI严重超买({rsi:.1f})且触及布林上轨。"
    
    def get_risk_parameters(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        获取反转策略的风险参数
        """
        # 基础风险参数
        base_params = super().get_risk_parameters(symbol, market_data)
        
        # 反转策略特定参数（更保守）
        reversal_params = {
            'stop_loss_atr_multiplier': self.atr_multiplier_for_sl,  # 更紧的止损
            'take_profit_multiplier_1': 1.5,  # 1.5R止盈
            'take_profit_multiplier_2': 2.0,  # 2R止盈
            'risk_per_trade_percent': self.risk_per_trade_percent / 100,  # 更小的仓位
            'max_holding_period_hours': 24,  # 最大持仓时间
        }
        
        base_params.update(reversal_params)
        return base_params
    
    def analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析市场是否适合反转策略
        """
        h1_analysis = market_data.get('h1_analysis', {})
        
        if not h1_analysis:
            return {'suitable': False, 'reason': '缺少市场数据'}
        
        rsi_value = h1_analysis.get('rsi_value', 50)
        indicators = h1_analysis.get('indicators', {})
        
        # 检查市场波动率
        atr = indicators.get('atr', 0)
        current_price = indicators.get('current_price', 0)
        volatility = (atr / current_price) if current_price > 0 else 0
        
        # 反转策略适合中等到高波动率的市场
        suitable = volatility > 0.02  # 2%以上的波动率
        
        return {
            'suitable': suitable,
            'volatility': volatility,
            'rsi': rsi_value,
            'reason': f"波动率{'适合' if suitable else '不适合'}反转策略"
        }