import pandas as pd
import numpy as np


def breakout_trigger(df: pd.DataFrame, pivot: float, vol_mult=1.5):
    vol50 = df["Volume"].rolling(50).mean()
    cond = (df["Close"] >= pivot) & (df["Volume"] >= vol_mult * vol50)
    if cond.any():
        idx = int(np.argmax(cond.values))
        return True, df["Date"].iloc[idx]
    return False, None


def evaluate_outcome(df: pd.DataFrame, start_idx: int, pivot: float, stop: float,
                     rr_target=1.5, max_days=25):
    end_idx = min(start_idx + max_days, len(df)-1)
    window = df.iloc[start_idx:end_idx+1]
    R = max(pivot - stop, 1e-6)
    up = pivot + rr_target * R
    hit_up = (window["High"] >= up).any()
    hit_dn = (window["Low"] <= stop).any()

    if hit_up and not hit_dn:
        exit_date = window.loc[window["High"] >= up, "Date"].iloc[0]
        return True, exit_date
    if hit_dn and not hit_up:
        exit_date = window.loc[window["Low"] <= stop, "Date"].iloc[0]
        return False, exit_date
    return False, window["Date"].iloc[-1]

