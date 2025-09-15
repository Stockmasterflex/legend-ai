import pandas as pd


def precision_at_k(candidates_df: pd.DataFrame, outcomes_df: pd.DataFrame, k: int = 10) -> float:
    if candidates_df is None or len(candidates_df) == 0:
        return 0.0
    # Ensure expected columns
    for col in ("date", "symbol", "confidence"):
        if col not in candidates_df.columns:
            return 0.0
    considered = []
    for d, grp in candidates_df.groupby("date"):
        top = grp.sort_values("confidence", ascending=False).head(k)
        considered.append(top[["date", "symbol"]])
    considered_df = pd.concat(considered, ignore_index=True) if considered else pd.DataFrame(columns=["date","symbol"])

    if outcomes_df is None or len(outcomes_df) == 0 or len(considered_df) == 0:
        return 0.0

    # Join on detection date and symbol
    join = considered_df.merge(
        outcomes_df,
        left_on=["date", "symbol"],
        right_on=["date_detected", "symbol"],
        how="left",
    )
    # Success among joined rows with any outcome
    success = (join.get("success", pd.Series(dtype=int)) == 1).sum()
    denom = len(considered_df)
    return float(success / denom) if denom else 0.0


def hit_rate(df_outcomes: pd.DataFrame) -> float:
    if df_outcomes is None or len(df_outcomes) == 0:
        return 0.0
    if "triggered" in df_outcomes.columns:
        df = df_outcomes[df_outcomes["triggered"] == 1]
    else:
        df = df_outcomes
    if len(df) == 0:
        return 0.0
    return float((df["success"] == 1).mean())


def median_runup(df_outcomes: pd.DataFrame) -> float:
    if df_outcomes is None or len(df_outcomes) == 0:
        return 0.0
    if "max_runup_30d" in df_outcomes.columns:
        ser = df_outcomes["max_runup_30d"].astype(float)
        if len(ser) == 0:
            return 0.0
        return float(ser.median())
    # Fallback: compute from available price columns if any (not expected in outcomes)
    return 0.0

