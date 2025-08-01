# user_data/strategies/helpers/DivergenceHelper.py

import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from numba import njit
from typing import Tuple, Literal, Callable
from freqtrade.strategy import IStrategy, timeframe_to_minutes, merge_informative_pair

# --- ADD THIS SNIPPET TO SILENCE NUMBA ---
import logging
# Find the numba logger and set its level to WARNING to silence DEBUG messages
logging.getLogger('numba').setLevel(logging.WARNING)
# -----------------------------------------

# ==============================================================================
# |          SOPHISTICATED BUT BIAS-FREE DIVERGENCE DETECTION                   |
# ==============================================================================

@njit
def _find_divergence_signals_sequential(primary_series: np.array, secondary_series: np.array, 
                                       pivot_indices: np.array, lookback: int, mode: str) -> np.array:
    """
    Core divergence logic using only historical pivot data.
    """
    signals = np.zeros(len(primary_series))
    if len(pivot_indices) < 2: 
        return signals

    for i in range(1, len(pivot_indices)):
        current_idx = pivot_indices[i]
        for j in range(i - 1, -1, -1):
            last_idx = pivot_indices[j]
            if current_idx - last_idx > lookback: 
                break
                
            current_primary = primary_series[current_idx]
            last_primary = primary_series[last_idx]
            current_secondary = secondary_series[current_idx]
            last_secondary = secondary_series[last_idx]
            
            if np.isnan(current_secondary) or np.isnan(last_secondary): 
                continue

            # Regular Divergence
            if mode == 'bullish' and (current_primary < last_primary) and (current_secondary > last_secondary):
                signals[current_idx] = 1
                break
            if mode == 'bearish' and (current_primary > last_primary) and (current_secondary < last_secondary):
                signals[current_idx] = -1
                break
                
            # Hidden Divergence
            if mode == 'hidden_bullish' and (current_primary > last_primary) and (current_secondary < last_secondary):
                signals[current_idx] = 1
                break
            if mode == 'hidden_bearish' and (current_primary < last_primary) and (current_secondary > last_secondary):
                signals[current_idx] = -1
                break
                
    return signals

class DivergenceEngine:
    """
    Sophisticated divergence detection that processes data as if in real-time.
    Uses proper pivot detection but only on historical data.
    """
    def __init__(self, strategy=None):
        # Your original sophisticated parameters - now they matter again!
        self.bullish_pivot_prominence_pct: float = 0.05 #0.010
        self.bullish_pivot_distance: int = 4 #10
        self.bearish_pivot_prominence_pct: float = 0.05 #0.008
        self.bearish_pivot_distance: int = 4 #8
        self.lookback_period: int = 150
        self.confirmation_period: int = 1
        
        # Minimum data required for reliable pivot detection
        self.min_data_points: int = 100

    def get_bullish_signals(self, primary_series: pd.Series, secondary_series: pd.Series,
                           mode: Literal['regular', 'hidden'] = 'regular') -> pd.Series:
        """
        Process data sequentially to simulate real-time pivot detection.
        This is the key to maintaining sophistication without lookahead bias.
        """
        bullish_mode_str = 'hidden_bullish' if mode == 'hidden' else 'bullish'
        signals = pd.Series(False, index=primary_series.index)
        
        if len(primary_series) < self.min_data_points:
            return signals
        
        # Process data sequentially - this is the crucial difference
        # We simulate getting new candles one by one, like in live trading
        for current_idx in range(self.min_data_points, len(primary_series)):
            # Only use data available "up to now" - no future data!
            historical_primary = primary_series.iloc[:current_idx].dropna()
            historical_secondary = secondary_series.iloc[:current_idx]
            
            if len(historical_primary) < 50:
                continue
                
            # Find pivots in ONLY the historical data we have so far
            try:
                absolute_prominence = historical_primary.mean() * self.bullish_pivot_prominence_pct
                valley_indices_local, _ = find_peaks(
                    -historical_primary, 
                    prominence=absolute_prominence, 
                    distance=self.bullish_pivot_distance
                )
                
                if len(valley_indices_local) < 2:
                    continue
                    
                # Convert to global indices
                valley_indices_labels = historical_primary.index[valley_indices_local]
                valley_indices_np = primary_series.index.get_indexer(valley_indices_labels)
                
                # Check for divergence using only the pivots we've found so far
                current_signals = _find_divergence_signals_sequential(
                    primary_series.iloc[:current_idx].to_numpy(), 
                    secondary_series.iloc[:current_idx].to_numpy(),
                    valley_indices_np, 
                    self.lookback_period, 
                    bullish_mode_str
                )
                
                # Only update the signal for the current position if there's a new signal
                if current_signals[-1] == 1:  # Signal at the latest position
                    signals.iloc[current_idx-1] = True
                    
            except Exception:
                # If pivot detection fails, continue to next iteration
                continue
                
        return signals

    def get_bearish_signals(self, primary_series: pd.Series, secondary_series: pd.Series,
                           mode: Literal['regular', 'hidden'] = 'regular') -> pd.Series:
        """
        Process data sequentially for bearish signals.
        """
        bearish_mode_str = 'hidden_bearish' if mode == 'hidden' else 'bearish'
        signals = pd.Series(False, index=primary_series.index)
        
        if len(primary_series) < self.min_data_points:
            return signals
        
        # Process data sequentially
        for current_idx in range(self.min_data_points, len(primary_series)):
            # Only use historical data
            historical_primary = primary_series.iloc[:current_idx].dropna()
            historical_secondary = secondary_series.iloc[:current_idx]
            
            if len(historical_primary) < 50:
                continue
                
            # Find peaks in historical data only
            try:
                absolute_prominence = historical_primary.mean() * self.bearish_pivot_prominence_pct
                peak_indices_local, _ = find_peaks(
                    historical_primary, 
                    prominence=absolute_prominence, 
                    distance=self.bearish_pivot_distance
                )
                
                if len(peak_indices_local) < 2:
                    continue
                    
                # Convert to global indices
                peak_indices_labels = historical_primary.index[peak_indices_local]
                peak_indices_np = primary_series.index.get_indexer(peak_indices_labels)
                
                # Check for divergence
                current_signals = _find_divergence_signals_sequential(
                    primary_series.iloc[:current_idx].to_numpy(), 
                    secondary_series.iloc[:current_idx].to_numpy(),
                    peak_indices_np, 
                    self.lookback_period, 
                    bearish_mode_str
                )
                
                # Only update if there's a new signal
                if current_signals[-1] == -1:
                    signals.iloc[current_idx-1] = True
                    
            except Exception:
                continue
                
        return signals

class InformativeDivergenceProvider:
    """
    Provider that uses sophisticated, bias-free divergence detection.
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
        
        pair = metadata['pair']
        
        # Get informative data with conservative buffer
        full_informative_df = self.strategy.dp.get_pair_dataframe(
            pair=pair, timeframe=informative_timeframe
        )
        
        if len(full_informative_df) < self.divergence_engine.min_data_points:
            final_bull_col = f'bull_div_{informative_timeframe}'
            final_bear_col = f'bear_div_{informative_timeframe}'
            dataframe[final_bull_col] = False
            dataframe[final_bear_col] = False
            return dataframe
        
        # Use a reasonable buffer - not too aggressive to maintain signal quality
        safety_buffer = 10  # Reduced buffer since we're processing sequentially
        informative_df = full_informative_df.iloc[:-safety_buffer].copy()
        
        if len(informative_df) < 50:
            final_bull_col = f'bull_div_{informative_timeframe}'
            final_bear_col = f'bear_div_{informative_timeframe}'
            dataframe[final_bull_col] = False
            dataframe[final_bear_col] = False
            return dataframe
        
        # Generate indicators on historical data
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

        # Generate sophisticated signals using sequential processing
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

        # Apply confirmation period
        bull_col = f'bull_div_signal_{informative_timeframe}'
        bear_col = f'bear_div_signal_{informative_timeframe}'
        final_bull_col = f'bull_div_{informative_timeframe}'
        final_bear_col = f'bear_div_{informative_timeframe}'
        
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