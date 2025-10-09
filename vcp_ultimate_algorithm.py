"""
VCP Ultimate Detection Algorithm
Volatility Contraction Pattern (VCP) Detection Algorithm
A comprehensive implementation for detecting VCP patterns in stock data
Based on Mark Minervini's and William O'Neil's trading methodologies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


@dataclass
class Contraction:
    """Represents a single contraction in the VCP pattern"""
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    high_price: float
    low_price: float
    percent_drop: float
    avg_volume: float
    duration_days: int


@dataclass
class VCPSignal:
    """Contains VCP detection results"""
    symbol: str
    detected: bool
    pivot_price: float = None
    contractions: List[Contraction] = None
    confidence_score: float = 0.0
    trend_strength: float = 0.0
    volume_dry_up: bool = False
    final_contraction_tightness: float = None
    breakout_detected: bool = False
    signal_date: pd.Timestamp = None
    notes: List[str] = None


class VCPDetector:
    """
    Advanced VCP Pattern Detection System
    
    This class implements a multi-layered approach to identify high-probability
    VCP setups following the Minervini/O'Neil methodology.
    """
    
    def __init__(self, 
                 min_price: float = 30.0,
                 min_volume: int = 1000000,
                 min_contractions: int = 2,
                 max_contractions: int = 6,
                 max_base_depth: float = 0.35,
                 final_contraction_max: float = 0.10,
                 breakout_volume_multiplier: float = 1.5,
                 check_trend_template: bool = True):
        """
        Initialize VCP Detector with configurable parameters
        
        Args:
            min_price: Minimum stock price to consider (default: 30.0)
            min_volume: Minimum average daily volume (default: 1,000,000)
            min_contractions: Minimum number of contractions required (default: 2)
            max_contractions: Maximum number of contractions allowed (default: 6)
            max_base_depth: Maximum depth of entire base (default: 0.35 = 35%)
            final_contraction_max: Maximum depth of final contraction (default: 0.10 = 10%)
            breakout_volume_multiplier: Volume multiplier for breakout confirmation (default: 1.5)
            check_trend_template: Whether to apply Minervini's 8-point trend template (default: True)
        """
        self.min_price = min_price
        self.min_volume = min_volume
        self.min_contractions = min_contractions
        self.max_contractions = max_contractions
        self.max_base_depth = max_base_depth
        self.final_contraction_max = final_contraction_max
        self.breakout_volume_multiplier = breakout_volume_multiplier
        self.check_trend_template = check_trend_template
    
    def detect_vcp(self, df: pd.DataFrame, symbol: str) -> VCPSignal:
        """
        Main VCP detection method
        
        Args:
            df: DataFrame with OHLCV data (Date, Open, High, Low, Close, Volume)
            symbol: Stock symbol
            
        Returns:
            VCPSignal object with detection results
        """
        try:
            # Initialize signal object
            signal = VCPSignal(symbol=symbol, detected=False, notes=[])
            
            # Data validation
            if not self._validate_data(df, signal):
                return signal
            
            # Apply Minervini Trend Template filter (can be bypassed)
            if self.check_trend_template:
                if not self._check_trend_template(df, signal):
                    return signal
            
            # Find swing points (highs and lows)
            swing_highs, swing_lows = self._find_swing_points(df)
            
            if len(swing_highs) < self.min_contractions or len(swing_lows) < self.min_contractions:
                signal.notes.append("Insufficient swing points for pattern analysis")
                return signal
            
            # Identify base and contractions
            base_start, contractions = self._identify_contractions(df, swing_highs, swing_lows)
            
            if len(contractions) < self.min_contractions:
                signal.notes.append(f"Only {len(contractions)} contractions found, need {self.min_contractions}")
                return signal
            
            # Validate VCP criteria
            is_valid_vcp = self._validate_vcp_pattern(df, contractions, signal)
            
            if is_valid_vcp:
                signal.detected = True
                signal.contractions = contractions
                signal.signal_date = df.index[-1]
                
                # Calculate additional metrics
                signal.pivot_price = self._calculate_pivot_price(df, contractions)
                signal.trend_strength = self._calculate_trend_strength(df)
                signal.volume_dry_up = self._check_volume_dry_up(df, contractions)
                signal.final_contraction_tightness = contractions[-1].percent_drop
                
                # Calculate confidence score
                signal.confidence_score = self._calculate_confidence_score(
                    signal, len(contractions), signal.volume_dry_up, True
                )
                
                # Check for breakout
                signal.breakout_detected = self._check_breakout(df, signal.pivot_price)
                
                signal.notes.append(f"VCP detected with {len(contractions)} contractions")
            
            return signal
            
        except Exception as e:
            signal.notes.append(f"Error in VCP detection: {str(e)}")
            return signal
    
    def _validate_data(self, df: pd.DataFrame, signal: VCPSignal) -> bool:
        """Validate input data quality and minimum requirements"""
        if df is None or len(df) < 60:
            signal.notes.append("Insufficient data points (need 60+ days)")
            return False
        
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_columns):
            signal.notes.append("Missing required OHLCV columns")
            return False
        
        current_price = df['Close'].iloc[-1]
        avg_volume = df['Volume'].iloc[-50:].mean()
        
        if current_price < self.min_price:
            signal.notes.append(f"Price {current_price:.2f} below minimum {self.min_price}")
            return False
        
        if avg_volume < self.min_volume:
            signal.notes.append(f"Volume {avg_volume:.0f} below minimum {self.min_volume}")
            return False
        
        return True
    
    def _check_trend_template(self, df: pd.DataFrame, signal: VCPSignal) -> bool:
        """
        Check Minervini's 8-point Trend Template
        
        1. Current price above 150-day and 200-day MA
        2. 150-day MA above 200-day MA
        3. 200-day MA trending up for at least 1 month
        4. 50-day MA above both 150-day and 200-day MA
        5. Current price above 50-day MA
        6. Current price at least 30% above 52-week low
        7. Current price within 25% of 52-week high
        8. RS rating above 70 (simplified check)
        """
        try:
            # Calculate moving averages
            df['MA_50'] = df['Close'].rolling(50).mean()
            df['MA_150'] = df['Close'].rolling(150).mean()
            df['MA_200'] = df['Close'].rolling(200).mean()
            
            # Get current values
            price = df['Close'].iloc[-1]
            ma50 = df['MA_50'].iloc[-1]
            ma150 = df['MA_150'].iloc[-1]
            ma200 = df['MA_200'].iloc[-1]
            ma200_20d_ago = df['MA_200'].iloc[-20] if len(df) >= 20 else ma200
            
            # 52-week high/low
            high_52w = df['High'].iloc[-252:].max() if len(df) >= 252 else df['High'].max()
            low_52w = df['Low'].iloc[-252:].min() if len(df) >= 252 else df['Low'].min()
            
            # Check all criteria
            criteria = []
            
            # 1 & 2: Price above 150 & 200 MA, 150 MA > 200 MA
            criteria.append(price > ma150 and price > ma200)
            criteria.append(ma150 > ma200)
            
            # 3: 200-day MA trending up (at least 1 month)
            criteria.append(ma200 > ma200_20d_ago)
            
            # 4: 50-day MA > both 150-day MA and 200-day MA
            criteria.append(ma50 > ma150 and ma50 > ma200)
            
            # 5: Current price > 50-day MA
            criteria.append(price > ma50)
            
            # 6: Current price at least 30% above 52-week low
            if low_52w > 0:
                criteria.append((price - low_52w) / low_52w >= 0.30)
            else:
                criteria.append(False)
            
            # 7: Current price within 25% of 52-week high
            if high_52w > 0:
                criteria.append((high_52w - price) / high_52w <= 0.25)
            else:
                criteria.append(False)
            
            # 8: Simplified RS check (price performance vs average)
            if len(df) >= 126:  # 6 months
                price_6m_ago = df['Close'].iloc[-126]
                price_performance = (price - price_6m_ago) / price_6m_ago
                criteria.append(price_performance > 0.1)  # 10% minimum performance
            else:
                criteria.append(True)
            
            passed_criteria = sum(criteria)
            signal.trend_strength = passed_criteria / len(criteria)
            
            if passed_criteria >= 6:  # Need at least 6/8 criteria
                return True
            else:
                signal.notes.append(f"Trend Template: {passed_criteria}/8 criteria passed")
                return False
                
        except Exception as e:
            signal.notes.append(f"Trend Template error: {str(e)}")
            return False
    
    def _find_swing_points(self, df: pd.DataFrame, window: int = 5) -> Tuple[List, List]:
        """Find swing highs and lows using rolling windows"""
        highs = df['High'].values
        lows = df['Low'].values
        dates = df.index
        
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(highs) - window):
            # Check for swing high
            if highs[i] == max(highs[i-window:i+window+1]):
                swing_highs.append({
                    'date': dates[i],
                    'price': highs[i],
                    'index': i
                })
            
            # Check for swing low
            if lows[i] == min(lows[i-window:i+window+1]):
                swing_lows.append({
                    'date': dates[i],
                    'price': lows[i],
                    'index': i
                })
        
        return swing_highs, swing_lows
    
    def _identify_contractions(self, df: pd.DataFrame, swing_highs: List, swing_lows: List) -> Tuple[int, List[Contraction]]:
        """Identify contractions from swing points"""
        contractions = []
        
        # Look for pattern in recent data (last 12 weeks = ~60 trading days)
        recent_period = min(60, len(df) // 2)
        base_start = len(df) - recent_period
        
        # Filter swing points to recent period
        recent_highs = [h for h in swing_highs if h['index'] >= base_start]
        recent_lows = [l for l in swing_lows if l['index'] >= base_start]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return base_start, contractions
        
        # Sort by date
        recent_highs.sort(key=lambda x: x['date'])
        recent_lows.sort(key=lambda x: x['date'])
        
        # Match highs and lows to form contractions
        for i in range(len(recent_highs) - 1):
            high_point = recent_highs[i]
            
            # Find corresponding low after this high
            corresponding_lows = [l for l in recent_lows if l['date'] > high_point['date']]
            
            if corresponding_lows:
                low_point = min(corresponding_lows, key=lambda x: x['price'])
                
                # Calculate contraction metrics
                percent_drop = (high_point['price'] - low_point['price']) / high_point['price']
                duration = (low_point['date'] - high_point['date']).days
                
                # Get volume data for this period
                start_idx = high_point['index']
                end_idx = low_point['index']
                avg_volume = df['Volume'].iloc[start_idx:end_idx+1].mean()
                
                contraction = Contraction(
                    start_date=high_point['date'],
                    end_date=low_point['date'],
                    high_price=high_point['price'],
                    low_price=low_point['price'],
                    percent_drop=percent_drop,
                    avg_volume=avg_volume,
                    duration_days=duration
                )
                
                contractions.append(contraction)
        
        # Sort contractions by date
        contractions.sort(key=lambda x: x.start_date)
        
        return base_start, contractions
    
    def _validate_vcp_pattern(self, df: pd.DataFrame, contractions: List[Contraction], signal: VCPSignal) -> bool:
        """Validate the contractions form a valid VCP pattern"""
        if len(contractions) < self.min_contractions:
            return False
        
        if len(contractions) > self.max_contractions:
            contractions = contractions[-self.max_contractions:]  # Keep most recent
        
        # Check 1: Contractions should generally decrease in magnitude
        decreasing_count = 0
        for i in range(1, len(contractions)):
            if contractions[i].percent_drop <= contractions[i-1].percent_drop:
                decreasing_count += 1
        
        if decreasing_count / (len(contractions) - 1) < 0.6:  # At least 60% should be decreasing
            signal.notes.append("Contractions not sufficiently decreasing")
            return False
        
        # Check 2: Final contraction should be tight
        final_contraction = contractions[-1]
        if final_contraction.percent_drop > self.final_contraction_max:
            signal.notes.append(f"Final contraction {final_contraction.percent_drop:.1%} too wide")
            return False
        
        # Check 3: Base shouldn't be too deep overall
        all_highs = [c.high_price for c in contractions]
        all_lows = [c.low_price for c in contractions]
        base_depth = (max(all_highs) - min(all_lows)) / max(all_highs)
        
        if base_depth > self.max_base_depth:
            signal.notes.append(f"Base too deep: {base_depth:.1%}")
            return False
        
        # Check 4: Volume should generally decrease through pattern
        volumes = [c.avg_volume for c in contractions]
        if len(volumes) >= 3:
            volume_trend = np.polyfit(range(len(volumes)), volumes, 1)[0]
            if volume_trend > 0:
                signal.notes.append("Volume not decreasing through pattern")
                # Don't fail on volume alone, but note it
        
        return True
    
    def _calculate_pivot_price(self, df: pd.DataFrame, contractions: List[Contraction]) -> float:
        """Calculate the pivot/breakout price level"""
        if not contractions:
            return df['Close'].iloc[-1] * 1.05
        
        # Use the highest high from the base as pivot
        recent_high = max([c.high_price for c in contractions])
        
        # Add small buffer for breakout confirmation
        return recent_high * 1.01  # 1% above the high
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate overall trend strength (0-1)"""
        try:
            if len(df) < 50:
                return 0.5
            
            # Price vs moving averages
            price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1]
            
            score = 0.0
            
            # Price above MAs
            if price > ma20:
                score += 0.3
            if price > ma50:
                score += 0.3
            
            # Recent price trend
            price_10d_ago = df['Close'].iloc[-10]
            if price > price_10d_ago:
                score += 0.2
            
            # Volume trend
            recent_volume = df['Volume'].iloc[-10:].mean()
            older_volume = df['Volume'].iloc[-30:-10].mean()
            if recent_volume > older_volume:
                score += 0.2
            
            return min(1.0, score)
            
        except Exception:
            return 0.5
    
    def _check_volume_dry_up(self, df: pd.DataFrame, contractions: List[Contraction]) -> bool:
        """Check if volume is drying up in recent contractions"""
        if len(contractions) < 2:
            return False
        
        try:
            # Compare volume in last 2 contractions
            recent_volume = contractions[-1].avg_volume
            previous_volume = contractions[-2].avg_volume
            
            # Check if recent volume is significantly lower
            volume_decrease = (previous_volume - recent_volume) / previous_volume
            
            return volume_decrease > 0.2  # 20% decrease
            
        except Exception:
            return False
    
    def _check_breakout(self, df: pd.DataFrame, pivot_price: float) -> bool:
        """Check if stock has broken out above pivot price with volume"""
        try:
            current_price = df['Close'].iloc[-1]
            current_volume = df['Volume'].iloc[-1]
            avg_volume = df['Volume'].iloc[-50:].mean()
            
            price_breakout = current_price > pivot_price
            volume_surge = current_volume > (avg_volume * self.breakout_volume_multiplier)
            
            return price_breakout and volume_surge
            
        except Exception as e:
            print(f"Error checking breakout: {e}")
            return False
    
    def _calculate_confidence_score(self, signal: VCPSignal, 
                                   num_contractions: int,
                                   volume_dry_up: bool,
                                   volatility_compressed: bool) -> float:
        """Calculate confidence score for the VCP signal"""
        score = 0.0
        
        # Base score from trend strength
        score += signal.trend_strength * 30
        
        # Ideal number of contractions (3-4)
        if 3 <= num_contractions <= 4:
            score += 20
        elif 2 <= num_contractions <= 5:
            score += 10
        
        # Volume characteristics
        if volume_dry_up:
            score += 20
        
        # Volatility compression
        if volatility_compressed:
            score += 15
        
        # Final contraction tightness
        if signal.final_contraction_tightness:
            if signal.final_contraction_tightness <= 0.05:
                score += 15
            elif signal.final_contraction_tightness <= 0.08:
                score += 10
            elif signal.final_contraction_tightness <= 0.10:
                score += 5
        
        # Normalize to 0-100
        return min(100, max(0, score))


def scan_for_vcp(tickers: List[str], data_fetcher, **detector_params) -> List[VCPSignal]:
    """
    Scan multiple stocks for VCP patterns
    
    Args:
        tickers: List of stock symbols to scan
        data_fetcher: Function to fetch stock data (should return DataFrame)
        **detector_params: Parameters to pass to VCPDetector
        
    Returns:
        List of VCPSignal objects for stocks with detected patterns
    """
    detector = VCPDetector(**detector_params)
    signals = []
    
    for ticker in tickers:
        try:
            # Fetch data (implement your own data fetcher)
            df = data_fetcher(ticker)
            
            if df is not None:
                signal = detector.detect_vcp(df, symbol=ticker)
                
                if signal.detected:
                    signals.append(signal)
                    print(f"✓ VCP detected for {ticker} - "
                          f"Confidence: {signal.confidence_score:.1f}%, "
                          f"Contractions: {len(signal.contractions)}, "
                          f"Pivot: ${signal.pivot_price:.2f}")
                else:
                    print(f"✗ No VCP for {ticker}")
            
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")
    
    # Sort by confidence score
    signals.sort(key=lambda x: x.confidence_score, reverse=True)
    
    return signals


# Example usage function
def example_usage():
    """
    Example of how to use the VCP detector
    """
    # Create sample data (replace with real data)
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    sample_data = pd.DataFrame({
        'Date': dates,
        'Open': np.random.uniform(90, 110, len(dates)),
        'High': np.random.uniform(95, 115, len(dates)),
        'Low': np.random.uniform(85, 105, len(dates)),
        'Close': np.random.uniform(90, 110, len(dates)),
        'Volume': np.random.uniform(1000000, 5000000, len(dates))
    })
    
    # Initialize detector with production-quality defaults
    detector = VCPDetector(
        min_price=30.0,
        min_volume=1000000,
        min_contractions=2,
        max_contractions=4,
        max_base_depth=0.35,
        final_contraction_max=0.10,
        check_trend_template=True
    )
    
    # Detect VCP
    signal = detector.detect_vcp(sample_data, symbol="EXAMPLE")
    
    # Print results
    print(f"Symbol: {signal.symbol}")
    print(f"VCP Detected: {signal.detected}")
    if signal.detected:
        print(f"Confidence Score: {signal.confidence_score:.1f}%")
        print(f"Pivot Price: ${signal.pivot_price:.2f}")
        print(f"Number of Contractions: {len(signal.contractions)}")
        print(f"Volume Dry-up: {signal.volume_dry_up}")
        print(f"Breakout Detected: {signal.breakout_detected}")
        print(f"Notes: {', '.join(signal.notes)}")
        
        # Print contraction details
        for i, contraction in enumerate(signal.contractions, 1):
            print(f"\nContraction {i}:")
            print(f"  Drop: {contraction.percent_drop:.1%}")
            print(f"  High: ${contraction.high_price:.2f}")
            print(f"  Low: ${contraction.low_price:.2f}")
            print(f"  Duration: {contraction.duration_days} days")


if __name__ == "__main__":
    example_usage()
