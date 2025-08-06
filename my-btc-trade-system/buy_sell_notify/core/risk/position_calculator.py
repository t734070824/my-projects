"""
仓位和风险计算器
专门处理仓位大小、止损价格、风险金额等计算
"""

from typing import Dict, Any, Optional, Tuple
import logging

from utils.constants import TradingAction
from utils.helpers import safe_float_conversion


class PositionCalculator:
    """
    仓位计算器
    
    负责：
    1. 计算仓位大小
    2. 计算止损价格
    3. 计算风险金额
    4. 计算目标价位
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PositionCalculator")
    
    def calculate_position_details(self, 
                                 symbol: str,
                                 action: str,
                                 current_price: float,
                                 atr_info: Dict[str, Any],
                                 risk_config: Dict[str, Any],
                                 account_balance: float) -> Dict[str, Any]:
        """
        计算完整的仓位详情
        
        Args:
            symbol: 交易对符号
            action: 交易动作 (EXECUTE_LONG/EXECUTE_SHORT)
            current_price: 当前价格
            atr_info: ATR信息
            risk_config: 风险配置
            account_balance: 账户余额
            
        Returns:
            Dict[str, Any]: 包含仓位详情的字典
        """
        try:
            # 提取配置参数
            atr_value = atr_info.get('atr', 0)
            atr_multiplier = risk_config.get('atr_multiplier_for_sl', 2.0)
            risk_per_trade_percent = risk_config.get('risk_per_trade_percent', 2.5) / 100
            
            self.logger.debug(f"计算 {symbol} 仓位详情: 价格={current_price}, ATR={atr_value}, 倍数={atr_multiplier}")
            
            # 1. 计算止损距离和价格
            stop_loss_distance = atr_value * atr_multiplier
            stop_loss_price = self._calculate_stop_loss_price(
                action, current_price, stop_loss_distance
            )
            
            # 2. 计算风险金额和仓位大小
            risk_amount_usd = account_balance * risk_per_trade_percent
            position_size_coin = risk_amount_usd / stop_loss_distance if stop_loss_distance > 0 else 0
            
            # 3. 计算持仓价值
            position_value_usd = position_size_coin * current_price
            
            # 4. 计算目标价位
            targets = self._calculate_target_prices(
                action, current_price, stop_loss_distance, risk_amount_usd
            )
            
            # 5. 验证计算结果
            actual_risk = abs(current_price - stop_loss_price) * position_size_coin
            
            result = {
                'symbol': symbol,
                'action': action,
                'current_price': current_price,
                'position_size_coin': round(position_size_coin, 8),
                'position_value_usd': round(position_value_usd, 2),
                'stop_loss_price': round(stop_loss_price, 4),
                'stop_loss_distance': round(stop_loss_distance, 4),
                'atr_value': round(atr_value, 4),
                'atr_multiplier': atr_multiplier,
                'risk_amount_usd': round(risk_amount_usd, 2),
                'actual_risk_usd': round(actual_risk, 2),
                'target_prices': targets,
                'risk_reward_ratio': round(stop_loss_distance / atr_value, 2) if atr_value > 0 else 0,
                'calculation_valid': self._validate_calculation(
                    stop_loss_distance, atr_value, atr_multiplier, actual_risk, risk_amount_usd
                )
            }
            
            self.logger.info(f"{symbol} 仓位计算完成: 仓位={position_size_coin:.6f}, 止损={stop_loss_price:.4f}, 风险={actual_risk:.2f}USDT")
            
            return result
            
        except Exception as e:
            self.logger.error(f"计算 {symbol} 仓位详情失败: {e}", exc_info=True)
            return {
                'symbol': symbol,
                'action': action,
                'error': str(e),
                'calculation_valid': False
            }
    
    def _calculate_stop_loss_price(self, action: str, entry_price: float, stop_loss_distance: float) -> float:
        """
        计算止损价格
        
        Args:
            action: 交易动作
            entry_price: 入场价格
            stop_loss_distance: 止损距离
            
        Returns:
            float: 止损价格
        """
        if action == TradingAction.EXECUTE_LONG.value:
            # 做多：止损价格 = 入场价格 - 止损距离
            return entry_price - stop_loss_distance
        elif action == TradingAction.EXECUTE_SHORT.value:
            # 做空：止损价格 = 入场价格 + 止损距离
            return entry_price + stop_loss_distance
        else:
            return entry_price
    
    def _calculate_target_prices(self, 
                               action: str, 
                               entry_price: float, 
                               stop_loss_distance: float,
                               risk_amount: float) -> Dict[str, Any]:
        """
        计算目标价位
        
        Args:
            action: 交易动作
            entry_price: 入场价格
            stop_loss_distance: 止损距离
            risk_amount: 风险金额
            
        Returns:
            Dict[str, Any]: 目标价位信息
        """
        targets = {}
        
        try:
            # 设置风险回报比
            rr_ratios = [2.0, 3.0]  # 2R, 3R
            
            for i, rr_ratio in enumerate(rr_ratios, 1):
                profit_distance = stop_loss_distance * rr_ratio
                
                if action == TradingAction.EXECUTE_LONG.value:
                    target_price = entry_price + profit_distance
                else:  # SHORT
                    target_price = entry_price - profit_distance
                
                profit_amount = risk_amount * rr_ratio
                
                targets[f'target_{i}'] = {
                    'price': round(target_price, 4),
                    'profit_distance': round(profit_distance, 4),
                    'profit_amount': round(profit_amount, 2),
                    'risk_reward_ratio': rr_ratio
                }
            
        except Exception as e:
            self.logger.error(f"计算目标价位失败: {e}")
        
        return targets
    
    def _validate_calculation(self, 
                            stop_loss_distance: float,
                            atr_value: float, 
                            atr_multiplier: float,
                            actual_risk: float,
                            expected_risk: float) -> bool:
        """
        验证计算结果的准确性
        
        Args:
            stop_loss_distance: 计算出的止损距离
            atr_value: ATR值
            atr_multiplier: ATR倍数
            actual_risk: 实际风险金额
            expected_risk: 预期风险金额
            
        Returns:
            bool: 计算是否有效
        """
        try:
            # 1. 验证止损距离计算
            expected_distance = atr_value * atr_multiplier
            distance_error = abs(stop_loss_distance - expected_distance) / expected_distance if expected_distance > 0 else 1
            
            # 2. 验证风险金额计算
            risk_error = abs(actual_risk - expected_risk) / expected_risk if expected_risk > 0 else 1
            
            # 允许1%的计算误差
            distance_valid = distance_error < 0.01
            risk_valid = risk_error < 0.05  # 风险计算允许5%误差
            
            if not distance_valid:
                self.logger.warning(f"止损距离计算异常: 期望={expected_distance:.4f}, 实际={stop_loss_distance:.4f}, 误差={distance_error:.2%}")
            
            if not risk_valid:
                self.logger.warning(f"风险金额计算异常: 期望={expected_risk:.2f}, 实际={actual_risk:.2f}, 误差={risk_error:.2%}")
            
            return distance_valid and risk_valid
            
        except Exception as e:
            self.logger.error(f"验证计算结果失败: {e}")
            return False
    
    def calculate_trailing_stop(self,
                              position: Dict[str, Any],
                              current_price: float,
                              atr_info: Dict[str, Any],
                              atr_multiplier: float) -> Optional[Dict[str, Any]]:
        """
        计算追踪止损
        
        Args:
            position: 持仓信息
            current_price: 当前价格  
            atr_info: ATR信息
            atr_multiplier: ATR倍数
            
        Returns:
            Optional[Dict[str, Any]]: 追踪止损信息
        """
        try:
            side = position.get('side', '')
            entry_price = safe_float_conversion(position.get('entry_price', 0))
            atr_value = atr_info.get('atr', 0)
            
            if not all([side, entry_price, atr_value]):
                return None
            
            stop_loss_distance = atr_value * atr_multiplier
            
            # 计算新的追踪止损位
            if side.lower() == 'long':
                # 长仓：价格上涨时，止损向上调整
                if current_price > entry_price + stop_loss_distance:
                    new_stop_loss = current_price - stop_loss_distance
                    if new_stop_loss > entry_price:  # 确保止损在盈利区域
                        return {
                            'new_stop_loss': round(new_stop_loss, 4),
                            'reason': '价格上涨，调整追踪止损',
                            'profit_locked': True
                        }
            else:  # short
                # 空仓：价格下跌时，止损向下调整
                if current_price < entry_price - stop_loss_distance:
                    new_stop_loss = current_price + stop_loss_distance
                    if new_stop_loss < entry_price:  # 确保止损在盈利区域
                        return {
                            'new_stop_loss': round(new_stop_loss, 4),
                            'reason': '价格下跌，调整追踪止损',
                            'profit_locked': True
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"计算追踪止损失败: {e}")
            return None