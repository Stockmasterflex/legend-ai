import pandas as pd
from scipy.signal import find_peaks
from typing import Optional, Dict, List

def add_technicals(df: pd.DataFrame, interval: str = '1d') -> pd.DataFrame:
    mult = 5 if interval == '1wk' else 1
    if df.empty or len(df) < 40 * mult:
        return pd.DataFrame()
    df.ta.strategy("common")
    df.dropna(inplace=True)
    return df

def calculate_rs_rating(stock_df: pd.DataFrame, spy_df: pd.DataFrame) -> Optional[int]:
    if spy_df is None or stock_df.empty or spy_df.empty or len(stock_df) < 63 or len(spy_df) < 63:
        return None
    try:
        stock_initial, spy_initial = stock_df['Close'].iloc[-63], spy_df['Close'].iloc[-63]
        if stock_initial == 0 or spy_initial == 0:
            return None
        stock_perf, spy_perf = stock_df['Close'].iloc[-1] / stock_initial, spy_df['Close'].iloc[-1] / spy_initial
        if spy_perf == 0:
            return None
        rs = stock_perf / spy_perf
        return min(max(int(rs * 50), 0), 99)
    except (IndexError, ZeroDivisionError):
        return None

def detect_vcp(df: pd.DataFrame) -> Optional[dict]:
    if len(df) < 60:
        return None
    highs = df['High']
    peak_indices, _ = find_peaks(highs, distance=5)
    if len(peak_indices) < 2:
        return None
    pivot_prices = highs.iloc[peak_indices].values
    with pd.option_context('mode.use_inf_as_na', True):
        prev_pivots = pivot_prices[:-1]
        prev_pivots[prev_pivots == 0] = 1e-10
        contractions_pct = 100 * (pivot_prices[1:] - prev_pivots) / prev_pivots
        contractions_pct = pd.Series(contractions_pct).dropna()
    vcp_contractions = -contractions_pct[contractions_pct < 0]
    if len(vcp_contractions) >= 2 and vcp_contractions.iloc[-1] < vcp_contractions.iloc[0]:
        return {"pattern": "VCP", "waves": [round(c, 2) for c in vcp_contractions.tail(3)]}
    return None

def find_all_patterns(df: pd.DataFrame) -> List[Dict]:
    if df.empty:
        return []
    detectors = [detect_vcp]
    return [result for detect in detectors if (result := detect(df))]

def analyze(ticker: str, daily_df: pd.DataFrame, weekly_df: pd.DataFrame, spy_df: Optional[pd.DataFrame]) -> dict:
    daily_df_tech = add_technicals(daily_df.copy(), '1d')
    weekly_df_tech = add_technicals(weekly_df.copy(), '1wk')
    if daily_df_tech.empty:
        return {"primary_pattern": "None", "details": "Not enough data to calculate technicals."}
        
    daily_patterns = find_all_patterns(daily_df_tech)
    weekly_patterns = find_all_patterns(weekly_df_tech) if not weekly_df_tech.empty else []
    
    final_result = {"ticker": ticker}
    primary_pattern = weekly_patterns[0] if weekly_patterns else (daily_patterns[0] if daily_patterns else None)
    
    if not primary_pattern:
        final_result["primary_pattern"] = "None"
        final_result["score"] = 0
    else:
        final_result["primary_pattern"] = primary_pattern.get("pattern")
        score = 50
        if weekly_patterns:
            score += 20
        rs_rating = calculate_rs_rating(daily_df_tech, spy_df)
        if rs_rating and rs_rating > 80:
            score += 20
        final_result["score"] = min(score, 99)
        final_result["rs_rating"] = rs_rating if rs_rating is not None else "N/A"
    
    return final_result