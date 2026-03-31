from typing import Dict, Any

# Very simple, placeholder weights – we can refine later
WEIGHTS = {
    "Income": {
        "dividendYield": 0.35,
        "payoutRatio": 0.20,     # our computed payout
        "roe": 0.20,
        "priceToBook": 0.10,
        "priceToSales": 0.05,
        "epsTTM": 0.10,          # proxy for earnings scale
    },
    "Balanced": {
        "dividendYield": 0.20,
        "payoutRatio": 0.10,
        "roe": 0.25,
        "priceToBook": 0.15,
        "priceToSales": 0.10,
        "epsTTM": 0.20,
    },
    "Growth": {
        "dividendYield": 0.00,   # dividends don't matter
        "payoutRatio": 0.05,     # small penalty for extreme payout
        "roe": 0.35,
        "priceToBook": 0.25,
        "priceToSales": 0.15,
        "epsTTM": 0.20,
    },
}



def normalize(metric_name: str, value: float | None) -> float:
    """Very rough normalizer: map raw values to 0–1; we’ll refine later."""
    if value is None:
        return 0.0

    # Example shapes – extremely rough, just to get going
    if metric_name == "dividendYield":
        # 0% -> 0, 2% -> 0.3, 4% -> 0.7, 6%+ -> 1 (cap)
        if value <= 0:
            return 0.0
        if value >= 0.06:
            return 1.0
        return min(1.0, value / 0.06)

    if metric_name == "payoutRatio":
        # Best between 0.3–0.6, penalize extremes
        if value <= 0.0 or value >= 1.5:
            return 0.0
        if 0.3 <= value <= 0.6:
            return 1.0
        # Linearly decrease outside the sweet spot
        if value < 0.3:
            return value / 0.3
        return max(0.0, (1.5 - value) / 0.9)

    if metric_name == "roe":
        # 0 -> 0, 10% -> ~0.5, 20%+ -> 1
        if value <= 0:
            return 0.0
        if value >= 0.20:
            return 1.0
        return value / 0.20

    if metric_name == "debtToEquity":
        # Lower is better: 0 -> 1, 1 -> 0.7, 2 -> 0.4, >=3 -> 0
        if value <= 0:
            return 1.0
        if value >= 3:
            return 0.0
        return max(0.0, 1.0 - value / 3.0)

    if metric_name == "forwardPE":
        # Ballpark: 10–20 sweetish zone; cheap gets some credit, too
        if value <= 0:
            return 0.0
        if value <= 10:
            return 1.0
        if value <= 20:
            return 0.8
        if value <= 30:
            return 0.5
        if value <= 40:
            return 0.2
        return 0.0

    if metric_name == "priceVs200dmaPct":
        # Slightly above MA is good; far below or far above less good
        # value is e.g. 0.10 for 10% above
        if value is None:
            return 0.0
        if -0.2 <= value <= 0.2:
            return 1.0
        if value < -0.5 or value > 0.5:
            return 0.0
        return max(0.0, 1.0 - (abs(value) - 0.2) / 0.3)

    if metric_name == "maxDrawdown5yPct":
        # value negative: -0.3 (−30%) is better than -0.7
        if value >= 0:
            return 0.0
        if value <= -0.7:
            return 0.0
        if value >= -0.2:
            return 1.0
        # linearly map -0.2..-0.7 to 1..0
        return max(0.0, (value + 0.7) / 0.5)
    
    if metric_name == "priceToBook":
        # 1–3 is okay, lower is cheaper, very high is bad
        if value <= 0:
            return 0.0
        if value <= 1:
            return 1.0
        if value <= 3:
            return 0.8
        if value <= 5:
            return 0.5
        if value <= 8:
            return 0.2
        return 0.0

    if metric_name == "priceToSales":
        # 1–4 okay, >8 expensive
        if value <= 0:
            return 0.0
        if value <= 1:
            return 1.0
        if value <= 3:
            return 0.8
        if value <= 5:
            return 0.5
        if value <= 8:
            return 0.2
        return 0.0

    if metric_name == "epsTTM":
        # higher EPS gets some credit, but we just compress to 0–1
        if value is None or value <= 0:
            return 0.0
        if value >= 10:
            return 1.0
        return min(1.0, value / 10.0)

    if metric_name == "payoutRatio":
        # 30–70% best, >120% bad, near 0 also low score (no income)
        if value is None:
            return 0.0
        if value > 1.2:
            return 0.0
        if 0.3 <= value <= 0.7:
            return 1.0
        if value < 0.3:
            return value / 0.3
        # value between 0.7 and 1.2
        return max(0.0, (1.2 - value) / 0.5)


    # Fallback
    return 0.5


def compute_score(priority: str, metrics: Dict[str, Any]) -> float:
    weights = WEIGHTS.get(priority, {})
    if not weights:
        return 0.0
    score = 0.0
    for name, w in weights.items():
        raw_val = metrics.get(name)
        norm_val = normalize(name, raw_val)
        score += w * norm_val
    return score
