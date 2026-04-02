from typing import List, Literal
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from finnhub_client import (
    get_company_profile,
    get_financials,
    get_quote,
    PROFILE_CACHE,
    FINANCIALS_CACHE,
    QUOTE_CACHE,
    FinnhubError,
)
from metrics import parse_finnhub_metrics
from scoring import compute_score

app = FastAPI(title="Stock Dashboard Backend")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    # "https://your-frontend-domain.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Tickers = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "AVGO", "TSLA", "ADBE", "ORCL",
    "CRM", "INTC", "AMD", "MU", "NFLX",
    "JPM", "BAC", "WFC", "GS", "MS",
    "V", "MA", "AXP", "BLK", "SCHW",
    "C", "USB", "PNC", "CB", "AIG",
    "JNJ", "PFE", "MRK", "ABBV", "LLY",
    "BMY", "AMGN", "MDT", "UNH", "HUM",
    "PG", "KO", "PEP", "KHC", "GIS",
    "CL", "KMB", "MO", "PM", "COST",
    "WMT", "TGT",
    "CAT", "UNP", "DE", "GE", "HON",
    "XOM", "CVX", "COP", "SLB", "EOG",
    "DUK", "NEE", "SO", "O", "VICI",
    "T", "VZ", "UPS", "HD", "LOW",
    "MCD", "SBUX", "DIS",
]

@app.get("/stocks")
def get_stocks(
    priority: Literal["Income", "Balanced", "Growth"] = Query("Income"),
    budget: float | None = Query(None, description="Amount available to invest"),
    tickers: List[str] = Query(
        default=[],
        description="Optional list of up to 25 tickers to include",
    ),
    category: str | None = Query(
        default=None,
        description="Optional category/sector filter, e.g. 'Technology' or 'Financials'",
    ),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rank: int | None = Query(default=None, ge=1),
    max_rank: int | None = Query(default=None, ge=1),
):
    if len(tickers) > 25:
        raise HTTPException(
            status_code=400,
            detail="You can select at most 25 tickers.",
        )

    print("tickers received:", tickers)

    symbols = list(dict.fromkeys(tickers or Tickers))

    records: list[dict] = []

    for symbol in symbols:
        try:
            profile = get_company_profile(symbol)
            financials = get_financials(symbol)
            quote = get_quote(symbol)
        except FinnhubError:
            continue

        base_metrics = parse_finnhub_metrics(financials)

        if category:
            sector = profile.get("finnhubIndustry") or ""
            if category.lower() not in sector.lower():
                continue

        current_price = quote.get("c")
        if isinstance(current_price, (int, float)):
            base_metrics["price"] = float(current_price)
        else:
            base_metrics["price"] = None

        price = base_metrics["price"]
        if price is not None:
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue

        if budget is not None and price:
            base_metrics["maxWholeSharesAtBudget"] = int(budget // price)
        else:
            base_metrics["maxWholeSharesAtBudget"] = None

        dividend_per_share = base_metrics.get("dividendPerShareTTM")
        shares = base_metrics.get("maxWholeSharesAtBudget")
        projected_annual_income = (
            dividend_per_share * shares
            if dividend_per_share is not None and shares is not None
            else None
        )
        base_metrics["projectedAnnualIncome"] = projected_annual_income

        if budget is not None and (price is None or price > budget):
            continue

        scores = {
            "income": compute_score("Income", base_metrics),
            "balanced": compute_score("Balanced", base_metrics),
            "growth": compute_score("Growth", base_metrics),
        }

        company_name = profile.get("name") or symbol

        record = {
            "ticker": symbol,
            "companyName": company_name,
            "metrics": base_metrics,
            "scores": scores,
            "selectedScore": scores[priority.lower()],
        }
        records.append(record)

    records.sort(key=lambda r: r["selectedScore"], reverse=True)

    if min_rank is not None or max_rank is not None:
        ranked: list[dict] = []
        for idx, rec in enumerate(records, start=1):
            rank = idx
            if min_rank is not None and rank < min_rank:
                continue
            if max_rank is not None and rank > max_rank:
                continue
            rec["rank"] = rank
            ranked.append(rec)
        records = ranked
    else:
        for idx, rec in enumerate(records, start=1):
            rec["rank"] = idx

    return {"priority": priority, "stocks": records}

@app.get("/debug/cache")
def debug_cache():
    return {
        "profiles_cached": len(PROFILE_CACHE),
        "financials_cached": len(FINANCIALS_CACHE),
        "quotes_cached": len(QUOTE_CACHE),
    }