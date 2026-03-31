from typing import List, Literal
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from finnhub_client import (
    get_company_profile,
    get_financials,
    get_quote,
    FinnhubError,
)
from metrics import (
    parse_finnhub_metrics,
)
from scoring import compute_score

app = FastAPI(title="Stock Dashboard Backend")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

Tickers = ["AAPL", "MSFT", "JNJ", "T", "KO",
           "PFE", "INTC", "VZ", "F", "BAC",           
           ]  # small universe for now


@app.get("/stocks")
def get_stocks(
    priority: Literal["Income", "Balanced", "Growth"] = Query("Income"),
    budget: float | None = Query(None, description="Amount available to invest"),
):
    records: List[dict] = []

    for symbol in Tickers:
        try:
            profile = get_company_profile(symbol)
            financials = get_financials(symbol)
            quote = get_quote(symbol)
        except FinnhubError:
            continue

        base_metrics = parse_finnhub_metrics(financials)

        # --- price and budget logic ---
        current_price = quote.get("c")  # Finnhub /quote current price
        if isinstance(current_price, (int, float)):
            base_metrics["price"] = float(current_price)
        else:
            base_metrics["price"] = None

        if budget is not None and base_metrics["price"]:
            base_metrics["maxWholeSharesAtBudget"] = int(
                budget // base_metrics["price"]
            )
        else:
            base_metrics["maxWholeSharesAtBudget"] = None

        # NEW: projected annual dividend income (per ticker)
        dividend_per_share = base_metrics.get("dividendPerShareTTM")
        shares = base_metrics.get("maxWholeSharesAtBudget")
        projected_annual_income = None
        if dividend_per_share is not None and shares is not None:
            projected_annual_income = dividend_per_share * shares
        base_metrics["projectedAnnualIncome"] = projected_annual_income
        # --- end projected income logic ---

        # Skip unaffordable stocks completely
        if budget is not None and (
            base_metrics["price"] is None or base_metrics["price"] > budget
        ):
            continue
        # --- end price and budget logic ---

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
    return {"priority": priority, "stocks": records}

