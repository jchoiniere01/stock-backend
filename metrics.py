from typing import Dict, Any, Tuple, List
import pandas as pd


def parse_finnhub_metrics(financials: Dict[str, Any]) -> Dict[str, Any]:
    metric = financials.get("metric", {}) or {}

    def to_float(key):
        val = metric.get(key)
        try:
            return float(val) if val not in (None, "", "None") else None
        except (ValueError, TypeError):
            return None

    # ROE is already in percent (e.g., 159.94 means 159.94%)
    raw_roe = to_float("roeTTM")
    roe = raw_roe / 100.0 if raw_roe is not None else None

    # Dividend yield indicated is also in percent (0.41 = 0.41%)
    raw_div_yield = to_float("dividendYieldIndicatedAnnual")
    dividend_yield = raw_div_yield / 100.0 if raw_div_yield is not None else None

    # Use dividendPerShareTTM if you want it later
    dividend_per_share = to_float("dividendPerShareTTM")
    eps_ttm = to_float("epsTTM")

    forward_pe = to_float("peForward")

    #Simple Payout ration: dividends per share / EPS
    payout_ratio = None
    if dividend_per_share is not None and eps_ttm not in (None, 0):
        payout_ratio = dividend_per_share / eps_ttm

    return {
        "roe": roe,
        "assetTurnover": to_float("assetTurnoverTTM"),
        "priceToBook": to_float("pbAnnual"),
        "priceToSales": to_float("psTTM"),
        "revenueTTM": to_float("revenueTTM"),
        "epsTTM": eps_ttm,
        "dividendYield": dividend_yield,
        "dividendPerShareTTM": dividend_per_share,
        "payoutRatio": payout_ratio,   # 0–1 scale
    }






def parse_finnhub_candles(candles: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Finnhub /stock/candle returns:
    {'c': [...], 'h': [...], 'l': [...], 'o': [...], 't': [...], 'v': [...], 's': 'ok'}
    """
    if not candles or candles.get("s") != "ok":
        return pd.DataFrame(), {}
    closes = candles.get("c", [])
    times = candles.get("t", [])
    records: List[Dict[str, Any]] = []
    for ts, close in zip(times, closes):
        records.append(
            {
                "date": pd.to_datetime(ts, unit="s"),
                "close": float(close),
            }
        )
    df = pd.DataFrame(records).sort_values("date")
    return df, {}



def price_vs_50dma(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    df = df.copy()
    df["ma50"] = df["close"].rolling(window=50, min_periods=20).mean()
    last = df.iloc[-1]
    if pd.isna(last["ma50"]):
        return None
    return (last["close"] - last["ma50"]) / last["ma50"]


def max_drawdown_recent(df: pd.DataFrame, lookback_days: int = 100) -> float | None:
    """Max drawdown over the last ~100 daily bars."""
    if df.empty:
        return None
    df = df.copy().tail(lookback_days)
    cum_max = df["close"].cummax()
    drawdowns = (df["close"] - cum_max) / cum_max
    return drawdowns.min()
