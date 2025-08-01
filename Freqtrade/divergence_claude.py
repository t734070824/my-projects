# user_data/strategies/helpers/DivergenceHelper.py

import pandas as pd
import numpy as np
from typing import Tuple, Literal, Callable
from freqtrade.strategy import IStrategy, timeframe_to_minutes, merge_informative_pair

# --- ADD THIS SNIPPET TO SILENCE NUMBA ---
import logging
# Find the numba logger and set its level to WARNING to silence DEBUG messages
logging.getLogger('numba').setLevel(logging.WARNING)
# -----------------------------------------

# ==============================================================================
# |            EXACT DROP-IN REPLACEMENT - SAME INTERFACE                       |
# ==============================================================================

class DivergenceEngine:
    """
    EXACT same interface as your original, but with simple bias-free logic inside.
    """
    def __init__(self, strategy=None):
        self.confirmation_period: int = 1
        
        # Internal simple parameters
        self._simple_lookback = 20
        self._min_spacing = 10
        self._rolling_period = 5

    def get_bullish_signals(self, primary_series: pd.Series, secondary_series: pd.Series,
                           mode: Literal['regular', 'hidden'] = 'regular') -> pd.Series:
        """Same interface, simple logic inside"""
        if len(primary_series) < 50:
            return pd.Series(False, index=primary_series.index)
        
        return self._detect_simple_bullish(primary_series, secondary_series, mode)

    def get_bearish_signals(self, primary_series: pd.Series, secondary_series: pd.Series,
                           mode: Literal['regular', 'hidden'] = 'regular') -> pd.Series:
        """Same interface, simple logic inside"""
        if len(primary_series) < 50:
            return pd.Series(False, index=primary_series.index)
        
        return self._detect_simple_bearish(primary_series, secondary_series, mode)
    
    def _detect_simple_bullish(self, price_series: pd.Series, indicator_series: pd.Series, mode: str) -> pd.Series:
        """Simple bullish divergence without complex pivots"""
        signals = pd.Series(False, index=price_series.index)
        
        # Use rolling minimums instead of pivot detection
        price_lows = price_series.rolling(window=self._rolling_period, center=False).min()
        indicator_lows = indicator_series.rolling(window=self._rolling_period, center=False).min()
        
        for i in range(self._simple_lookback + self._rolling_period, len(price_series)):
            current_price_low = price_lows.iloc[i]
            current_indicator_low = indicator_lows.iloc[i]
            
            if pd.isna(current_price_low) or pd.isna(current_indicator_low):
                continue
                
            # Look back for comparison
            for j in range(i - self._simple_lookback, i - self._min_spacing):
                if j < 0:
                    continue
                    
                past_price_low = price_lows.iloc[j]
                past_indicator_low = indicator_lows.iloc[j]
                
                if pd.isna(past_price_low) or pd.isna(past_indicator_low):
                    continue
                
                # Regular bullish: price lower low, indicator higher low
                if mode == 'regular':
                    if current_price_low < past_price_low and current_indicator_low > past_indicator_low:
                        signals.iloc[i] = True
                        break
                # Hidden bullish: price higher low, indicator lower low  
                else:
                    if current_price_low > past_price_low and current_indicator_low < past_indicator_low:
                        signals.iloc[i] = True
                        break
                        
        return signals
    
    def _detect_simple_bearish(self, price_series: pd.Series, indicator_series: pd.Series, mode: str) -> pd.Series:
        """Simple bearish divergence without complex pivots"""
        signals = pd.Series(False, index=price_series.index)
        
        # Use rolling maximums instead of pivot detection
        price_highs = price_series.rolling(window=self._rolling_period, center=False).max()
        indicator_highs = indicator_series.rolling(window=self._rolling_period, center=False).max()
        
        for i in range(self._simple_lookback + self._rolling_period, len(price_series)):
            current_price_high = price_highs.iloc[i]
            current_indicator_high = indicator_highs.iloc[i]
            
            if pd.isna(current_price_high) or pd.isna(current_indicator_high):
                continue
                
            # Look back for comparison
            for j in range(i - self._simple_lookback, i - self._min_spacing):
                if j < 0:
                    continue
                    
                past_price_high = price_highs.iloc[j]
                past_indicator_high = indicator_highs.iloc[j]
                
                if pd.isna(past_price_high) or pd.isna(past_indicator_high):
                    continue
                
                # Regular bearish: price higher high, indicator lower high
                if mode == 'regular':
                    if current_price_high > past_price_high and current_indicator_high < past_indicator_high:
                        signals.iloc[i] = True
                        break
                # Hidden bearish: price lower high, indicator higher high
                else:
                    if current_price_high < past_price_high and current_indicator_high > past_indicator_high:
                        signals.iloc[i] = True
                        break
                        
        return signals

class InformativeDivergenceProvider:
    """
    EXACT same interface as your original.
    """
    def __init__(self, strategy: IStrategy, divergence_engine: DivergenceEngine):
        self.strategy = strategy
        self.divergence_engine = divergence_engine

    def add_signals(self, dataframe: pd.DataFrame, metadata: dict,
                   informative_timeframe: str,
                   bullish_primary_func: Callable[[pd.DataFrame], pd.Series],
                   bullish_secondary_func: Callable[[pd.DataFrame], pd.Series],
                   bullish_mode: str,
                   bearish_primary_func: Callable[[pd.DataFrame], pd.Series],
                   bearish_secondary_func: Callable[[pd.DataFrame], pd.Series],
                   bearish_mode: str) -> pd.DataFrame:
        """
        EXACT same interface, but with large safety buffer to prevent bias.
        """
        
        pair = metadata['pair']
        
        # Get informative data with LARGE safety buffer
        full_informative_df = self.strategy.dp.get_pair_dataframe(
            pair=pair, timeframe=informative_timeframe
        )
        
        if len(full_informative_df) < 100:
            # Return with empty signals if insufficient data
            final_bull_col = f'bull_div_{informative_timeframe}'
            final_bear_col = f'bear_div_{informative_timeframe}'
            dataframe[final_bull_col] = False
            dataframe[final_bear_col] = False
            return dataframe
        
        # CRITICAL: Use only old data with large buffer
        safety_buffer = 25  # Conservative buffer
        informative_df = full_informative_df.iloc[:-safety_buffer].copy()
        
        if len(informative_df) < 50:
            final_bull_col = f'bull_div_{informative_timeframe}'
            final_bear_col = f'bear_div_{informative_timeframe}'
            dataframe[final_bull_col] = False
            dataframe[final_bear_col] = False
            return dataframe
        
        # Generate your indicators on historical data only
        try:
            bullish_primary = bullish_primary_func(informative_df)
            bullish_secondary = bullish_secondary_func(informative_df)
            bearish_primary = bearish_primary_func(informative_df)
            bearish_secondary = bearish_secondary_func(informative_df)
        except Exception:
            final_bull_col = f'bull_div_{informative_timeframe}'
            final_bear_col = f'bear_div_{informative_timeframe}'
            dataframe[final_bull_col] = False
            dataframe[final_bear_col] = False
            return dataframe

        # Generate signals using simple logic
        bull_signals = self.divergence_engine.get_bullish_signals(
            bullish_primary, bullish_secondary, bullish_mode
        )
        bear_signals = self.divergence_engine.get_bearish_signals(
            bearish_primary, bearish_secondary, bearish_mode
        )

        # Add to informative dataframe
        informative_df['bull_div_signal'] = bull_signals
        informative_df['bear_div_signal'] = bear_signals
        
        # Merge with main dataframe
        dataframe = merge_informative_pair(
            dataframe, 
            informative_df[['date', 'bull_div_signal', 'bear_div_signal']],
            self.strategy.timeframe, 
            informative_timeframe, 
            ffill=True
        )

        # Final column names (same as your original)
        bull_col = f'bull_div_signal_{informative_timeframe}'
        bear_col = f'bear_div_signal_{informative_timeframe}'
        final_bull_col = f'bull_div_{informative_timeframe}'
        final_bear_col = f'bear_div_{informative_timeframe}'
        
        # Apply your confirmation period
        tf_ratio = timeframe_to_minutes(informative_timeframe) // timeframe_to_minutes(self.strategy.timeframe)
        confirmation_shift = self.divergence_engine.confirmation_period * tf_ratio
        
        if confirmation_shift > 0:
            dataframe[final_bull_col] = dataframe[bull_col].shift(confirmation_shift).fillna(False)
            dataframe[final_bear_col] = dataframe[bear_col].shift(confirmation_shift).fillna(False)
        else:
            dataframe[final_bull_col] = dataframe[bull_col].fillna(False)
            dataframe[final_bear_col] = dataframe[bear_col].fillna(False)
        
        # Clean up
        dataframe.drop([bull_col, bear_col], axis=1, inplace=True)
        
        return dataframe

# ==============================================================================
# |  Your original usage should work EXACTLY the same                           |
# ==============================================================================
