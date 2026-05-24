from __future__ import annotations

import math
from typing import Any

import pandas as pd


DEFAULT_TAX_RATES = {
    "federal_long_term_rate": 0.20,
    "federal_short_term_rate": 0.37,
    "niit_rate": 0.038,
    "state_tax_rate": 0.093,
}

DEFAULT_STRATEGY_PRIORITIES = {
    "tax_cost": 5.0,
    "concentration_risk_reduction": 5.0,
    "diversification_benefit": 4.0,
    "implementation_complexity": 3.0,
    "liquidity_borrow_risk": 3.0,
    "time_horizon": 3.0,
    "tax_rule_uncertainty": 4.0,
}

DEFAULT_HEDGE_ASSUMPTIONS = {
    "annual_borrow_cost_rate": 0.015,
    "liquidity_requirement": 70.0,
    "tax_complexity_tolerance": 3.0,
}

DEFAULT_SMA_STUDY_PRIORITIES = {
    "tax_loss_capacity": 5.0,
    "concentration_transition_fit": 5.0,
    "risk_control": 4.0,
    "tax_rule_clarity": 4.0,
    "implementation_simplicity": 3.0,
    "liquidity_borrow_safety": 3.0,
    "cost_efficiency": 2.0,
    "manager_operational_quality": 3.0,
    "diversification_benefit": 3.0,
}

SAMPLE_PRICE_BY_TICKER = {
    "SNDK": 72.0,
    "WDC": 82.0,
    "STX": 96.0,
    "MU": 124.0,
    "NVDA": 125.0,
    "AAPL": 190.0,
}

MARKET_INDEX_PROXIES = {"SPY", "QQQ", "IWM", "VTI"}
SECTOR_PROXIES = {"SOXX", "SMH", "XLK", "XSD", "IGV"}
ETF_PROXIES = MARKET_INDEX_PROXIES | SECTOR_PROXIES
MULTI_PROXY_HEDGE_LABEL = "Multi-proxy hedge"

STRATEGY_LABELS = {
    "sell_immediately": "Sell immediately to target",
    "sell_gradually": "Sell gradually over tax years",
    "harvest_losses": "Harvest losses to offset gains",
    "long_short_overlay": "Long/short overlay strategy",
    "pair_or_basket_hedge": "Pair trade or basket hedge concept",
    "hold_monitor": "Hold and monitor",
    "charitable_daf": "Charitable / donor-advised fund strategy",
    "exchange_direct_indexing": "Exchange fund / direct indexing transition",
}

SMA_DESIGN_LIBRARY = [
    {
        "design_id": "conservative",
        "design": "Conservative tax-aware equity SMA",
        "description": "Direct-indexing style long book with a modest, tightly governed hedge sleeve.",
        "net_exposure": "85%-100%",
        "gross_exposure": "100%-120%",
        "long_book": "Broad diversified long basket, high overlap with target equity benchmark, issuer restrictions applied.",
        "short_book": "Limited index, sector, or factor hedges; single-name shorts are exceptional.",
        "expected_loss_harvest_potential": "Low to moderate",
        "estimated_fee_carry": "Lower SMA fee; limited borrow/carry budget.",
        "expected_tracking_error": "Low to moderate",
        "base_scores": {
            "tax_loss_capacity": 45.0,
            "concentration_transition_fit": 55.0,
            "risk_control": 55.0,
            "tax_rule_clarity": 78.0,
            "implementation_simplicity": 82.0,
            "liquidity_borrow_safety": 82.0,
            "cost_efficiency": 72.0,
            "manager_operational_quality": 65.0,
            "diversification_benefit": 68.0,
        },
        "implementation_complexity": 25.0,
        "liquidity_borrow_risk": 22.0,
        "tax_rule_risk": 34.0,
        "best_when": "Tax-rule clarity, low tracking error, and operational simplicity matter more than maximum harvest capacity.",
        "avoid_when": "The concentration must be reduced quickly or the investor needs substantial annual loss capacity.",
        "review_flags": "Confirm wash-sale controls, benchmark restrictions, and whether any hedge could be treated as an offsetting position.",
    },
    {
        "design_id": "balanced",
        "design": "Balanced diversified 130/30-150/50 SMA",
        "description": "Diversified tax-aware long/short equity mandate designed to balance harvest capacity, risk control, and implementability.",
        "net_exposure": "80%-100%",
        "gross_exposure": "130%-150%",
        "long_book": "Diversified replacement equity basket with tax-lot aware realization and restricted-list exclusions.",
        "short_book": "Diversified single-name, sector, and factor shorts sized by liquidity, borrow, and restricted-list rules.",
        "expected_loss_harvest_potential": "Moderate to high",
        "estimated_fee_carry": "Moderate SMA fee plus borrow/carry and trading costs.",
        "expected_tracking_error": "Moderate",
        "base_scores": {
            "tax_loss_capacity": 78.0,
            "concentration_transition_fit": 78.0,
            "risk_control": 76.0,
            "tax_rule_clarity": 58.0,
            "implementation_simplicity": 58.0,
            "liquidity_borrow_safety": 62.0,
            "cost_efficiency": 58.0,
            "manager_operational_quality": 78.0,
            "diversification_benefit": 80.0,
        },
        "implementation_complexity": 55.0,
        "liquidity_borrow_risk": 48.0,
        "tax_rule_risk": 52.0,
        "best_when": "The investor wants meaningful transition help without relying on one substitute security or an aggressive market-neutral book.",
        "avoid_when": "The investor cannot tolerate leverage, shorting, active turnover, or a manager-dependent tax process.",
        "review_flags": "Require lot-level reporting, restricted-list controls, real-time wash-sale monitoring, straddle review, and borrow-cost disclosure.",
    },
    {
        "design_id": "hedge_focused",
        "design": "Hedge-focused transition overlay",
        "description": "Overlay built mainly to dampen concentrated-position exposure while the legacy stock is sold or donated over time.",
        "net_exposure": "70%-95%",
        "gross_exposure": "110%-140%",
        "long_book": "Legacy concentrated position plus cash/replacement equity sleeve as sales occur.",
        "short_book": "Sector ETF, broad index, peer basket, or factor hedge selected from historical evidence.",
        "expected_loss_harvest_potential": "Moderate",
        "estimated_fee_carry": "Moderate fee; borrow/carry depends heavily on hedge instrument.",
        "expected_tracking_error": "Moderate to high",
        "base_scores": {
            "tax_loss_capacity": 58.0,
            "concentration_transition_fit": 88.0,
            "risk_control": 84.0,
            "tax_rule_clarity": 42.0,
            "implementation_simplicity": 42.0,
            "liquidity_borrow_safety": 52.0,
            "cost_efficiency": 62.0,
            "manager_operational_quality": 64.0,
            "diversification_benefit": 50.0,
        },
        "implementation_complexity": 68.0,
        "liquidity_borrow_risk": 58.0,
        "tax_rule_risk": 72.0,
        "best_when": "Near-term concentration risk is the main problem and tax/legal counsel approves the hedge design.",
        "avoid_when": "The hedge is substantially identical, borrow is uncertain, or the investor expects broad diversification from the overlay alone.",
        "review_flags": "Highest need for constructive-sale, straddle, short-against-the-box, wash-sale, holding-period, and restricted-list review.",
    },
    {
        "design_id": "aggressive",
        "design": "Aggressive market/factor-neutral long/short SMA",
        "description": "High-gross active long/short mandate where alpha, factor neutrality, and harvest capacity are primary goals.",
        "net_exposure": "0%-60%",
        "gross_exposure": "150%-250%",
        "long_book": "Active security-selection longs with tax-aware realization but less benchmark-like exposure.",
        "short_book": "Large diversified single-name and factor short book with active borrow and margin management.",
        "expected_loss_harvest_potential": "High but uncertain",
        "estimated_fee_carry": "Highest fee, borrow, margin, trading, and manager-risk budget.",
        "expected_tracking_error": "High",
        "base_scores": {
            "tax_loss_capacity": 84.0,
            "concentration_transition_fit": 58.0,
            "risk_control": 78.0,
            "tax_rule_clarity": 28.0,
            "implementation_simplicity": 28.0,
            "liquidity_borrow_safety": 35.0,
            "cost_efficiency": 35.0,
            "manager_operational_quality": 56.0,
            "diversification_benefit": 62.0,
        },
        "implementation_complexity": 88.0,
        "liquidity_borrow_risk": 78.0,
        "tax_rule_risk": 86.0,
        "best_when": "The investor deliberately wants an active long/short manager and accepts high tracking error, leverage, and operational complexity.",
        "avoid_when": "The objective is a clean transition from one concentrated stock into a benchmark-like taxable equity portfolio.",
        "review_flags": "Requires enhanced manager diligence, margin/borrow review, tax-lot controls, short-sale reporting, and explicit risk limits.",
    },
]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _clean_column(value: Any) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace("%", "pct")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if _is_missing(value):
        return default
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        if not cleaned:
            return default
        value = cleaned
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_decimal(value: Any, default: float = 0.0) -> float:
    if isinstance(value, str) and "%" in value:
        return _coerce_float(value, default) / 100.0
    number = _coerce_float(value, default)
    if abs(number) > 1.0:
        return number / 100.0
    return number


def _coerce_leverage_decimal(value: Any, default: float = 0.0) -> float:
    """Coerce exposure inputs where 1.20 means 120% and 120 means 120%."""
    if isinstance(value, str) and "%" in value:
        return _coerce_float(value, default) / 100.0
    number = _coerce_float(value, default)
    if abs(number) > 10.0:
        return number / 100.0
    return number


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _weighted_average(values: pd.Series, weights: pd.Series) -> float:
    clean = pd.DataFrame({"value": values, "weight": weights}).dropna()
    clean = clean[clean["weight"] > 0]
    if clean.empty:
        return 0.0
    return float((clean["value"] * clean["weight"]).sum() / clean["weight"].sum())


def standardize_holding_period(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"st", "short", "short term", "short-term"}:
        return "Short Term"
    if text in {"lt", "long", "long term", "long-term"}:
        return "Long Term"
    return "Unknown"


PORTFOLIO_COLUMN_ALIASES = {
    "symbol": "ticker",
    "ticker": "ticker",
    "security": "ticker",
    "quantity": "shares",
    "qty": "shares",
    "shares": "shares",
    "price": "current_price",
    "last_price": "current_price",
    "current_price": "current_price",
    "market_price": "current_price",
    "market_value": "market_value",
    "current_value": "market_value",
    "value": "market_value",
    "mv": "market_value",
    "basis": "cost_basis",
    "tax_basis": "cost_basis",
    "cost_basis": "cost_basis",
    "total_cost_basis": "cost_basis",
    "basis_per_share": "cost_basis_per_share",
    "cost_basis_per_share": "cost_basis_per_share",
    "unrealized_gain": "unrealized_gain",
    "unrealized_gain_loss": "unrealized_gain",
    "gain_loss_dollars": "unrealized_gain",
    "holding_period": "holding_period",
    "term": "holding_period",
    "current_weight": "current_weight",
    "current_portfolio_weight": "current_weight",
    "portfolio_weight": "current_weight",
    "account_market_value_weight": "current_weight",
    "target_weight": "target_weight",
    "target_portfolio_weight": "target_weight",
    "estimated_federal_tax_rate": "federal_long_term_rate",
    "federal_tax_rate": "federal_long_term_rate",
    "federal_long_term_rate": "federal_long_term_rate",
    "federal_ltcg_rate": "federal_long_term_rate",
    "federal_lt_rate": "federal_long_term_rate",
    "federal_st_rate": "federal_short_term_rate",
    "federal_short_term_rate": "federal_short_term_rate",
    "ordinary_income_rate": "federal_short_term_rate",
    "niit_rate": "niit_rate",
    "state_tax_rate": "state_tax_rate",
    "estimated_state_tax_rate": "state_tax_rate",
}


def normalize_portfolio_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize a user-supplied portfolio into the fields used by the engine.

    Cost basis is treated as total position basis unless a separate
    cost_basis_per_share column is provided. The calculation is intentionally
    proportional at the position level and does not choose specific tax lots.
    """
    if raw is None or raw.empty:
        return pd.DataFrame()

    frame = raw.copy()
    rename_map: dict[str, str] = {}
    seen: set[str] = set()
    for column in frame.columns:
        canonical = PORTFOLIO_COLUMN_ALIASES.get(_clean_column(column))
        if canonical and canonical not in seen:
            rename_map[column] = canonical
            seen.add(canonical)
    frame = frame.rename(columns=rename_map)

    if "ticker" not in frame:
        frame["ticker"] = ""
    frame["ticker"] = frame["ticker"].map(lambda value: str(value).strip().upper())
    frame = frame[frame["ticker"] != ""].copy()

    for column in ["shares", "current_price", "market_value", "cost_basis", "cost_basis_per_share"]:
        if column in frame:
            frame[column] = frame[column].map(_coerce_float)

    if "shares" not in frame:
        frame["shares"] = 0.0
    if "current_price" not in frame:
        frame["current_price"] = 0.0
    if "market_value" not in frame:
        frame["market_value"] = frame["shares"] * frame["current_price"]
    else:
        missing_market_value = frame["market_value"] <= 0
        frame.loc[missing_market_value, "market_value"] = (
            frame.loc[missing_market_value, "shares"] * frame.loc[missing_market_value, "current_price"]
        )

    missing_price = (frame["current_price"] <= 0) & (frame["shares"] > 0)
    frame.loc[missing_price, "current_price"] = (
        frame.loc[missing_price, "market_value"] / frame.loc[missing_price, "shares"]
    )
    missing_shares = (frame["shares"] <= 0) & (frame["current_price"] > 0)
    frame.loc[missing_shares, "shares"] = (
        frame.loc[missing_shares, "market_value"] / frame.loc[missing_shares, "current_price"]
    )

    if "cost_basis" not in frame:
        if "cost_basis_per_share" in frame:
            frame["cost_basis"] = frame["cost_basis_per_share"] * frame["shares"]
        elif "unrealized_gain" in frame:
            frame["cost_basis"] = frame["market_value"] - frame["unrealized_gain"].map(_coerce_float)
        else:
            frame["cost_basis"] = frame["market_value"]
    frame["cost_basis"] = frame["cost_basis"].clip(lower=0.0)

    frame["unrealized_gain"] = frame["market_value"] - frame["cost_basis"]
    frame["unrealized_gain_pct"] = frame.apply(
        lambda row: row["unrealized_gain"] / row["market_value"] if row["market_value"] else 0.0,
        axis=1,
    )

    if "current_weight" in frame:
        frame["current_weight"] = frame["current_weight"].map(_coerce_decimal)
    else:
        total_market_value = float(frame["market_value"].sum())
        frame["current_weight"] = frame["market_value"] / total_market_value if total_market_value else 0.0

    if "target_weight" in frame:
        frame["target_weight"] = frame["target_weight"].map(_coerce_decimal)
    else:
        frame["target_weight"] = frame["current_weight"].map(lambda weight: min(float(weight), 0.10))

    if "holding_period" in frame:
        frame["holding_period"] = frame["holding_period"].map(standardize_holding_period)
    else:
        frame["holding_period"] = "Unknown"

    for column, default in DEFAULT_TAX_RATES.items():
        if column in frame:
            frame[column] = frame[column].map(lambda value: _coerce_decimal(value, default))
        else:
            frame[column] = default

    frame["gain_treatment"] = frame["holding_period"].map(
        {
            "Long Term": "Long-term capital gain treatment",
            "Short Term": "Short-term gain treatment",
            "Unknown": "Long-term assumed pending lot review",
        }
    )
    frame["gain_tax_rate"] = frame.apply(
        lambda row: (
            row["federal_short_term_rate"] + row["niit_rate"] + row["state_tax_rate"]
            if row["holding_period"] == "Short Term"
            else row["federal_long_term_rate"] + row["niit_rate"] + row["state_tax_rate"]
        ),
        axis=1,
    )
    frame["sale_fraction_to_target"] = frame.apply(position_sale_fraction_to_target, axis=1)
    frame["concentration_excess_weight"] = (frame["current_weight"] - frame["target_weight"]).clip(lower=0.0)

    ordered_columns = [
        "ticker",
        "shares",
        "current_price",
        "market_value",
        "cost_basis",
        "unrealized_gain",
        "unrealized_gain_pct",
        "holding_period",
        "gain_treatment",
        "current_weight",
        "target_weight",
        "sale_fraction_to_target",
        "federal_long_term_rate",
        "federal_short_term_rate",
        "niit_rate",
        "state_tax_rate",
        "gain_tax_rate",
        "concentration_excess_weight",
    ]
    return frame.loc[:, [column for column in ordered_columns if column in frame.columns]].reset_index(drop=True)


def build_sample_portfolio_from_cluster_summary(cluster_summary: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build editable sample inputs from bundled model output when available."""
    if cluster_summary is None or cluster_summary.empty:
        rows = [
            {
                "Ticker": "SNDK",
                "Shares": 51055.88,
                "Current Price": 72.0,
                "Cost Basis": 29501.54,
                "Holding Period": "Long Term",
                "Current Weight": 0.4246,
                "Target Weight": 0.0800,
            },
            {
                "Ticker": "WDC",
                "Shares": 42274.10,
                "Current Price": 82.0,
                "Cost Basis": 53680.87,
                "Holding Period": "Long Term",
                "Current Weight": 0.4004,
                "Target Weight": 0.0800,
            },
            {
                "Ticker": "MU",
                "Shares": 3028.23,
                "Current Price": 124.0,
                "Cost Basis": 9999.94,
                "Holding Period": "Long Term",
                "Current Weight": 0.0434,
                "Target Weight": 0.0250,
            },
        ]
    else:
        rows = []
        for _, row in cluster_summary.iterrows():
            ticker = str(row.get("symbol", "")).strip().upper()
            if not ticker:
                continue
            market_value = _coerce_float(row.get("market_value"))
            price = SAMPLE_PRICE_BY_TICKER.get(ticker, 100.0)
            current_weight = _coerce_decimal(row.get("account_market_value_weight"))
            target_weight = 0.08 if current_weight >= 0.20 else min(current_weight, 0.03)
            rows.append(
                {
                    "Ticker": ticker,
                    "Shares": market_value / price if price else 0.0,
                    "Current Price": price,
                    "Cost Basis": _coerce_float(row.get("cost_basis")),
                    "Holding Period": "Long Term" if _coerce_float(row.get("long_term_lots")) else "Unknown",
                    "Current Weight": current_weight,
                    "Target Weight": target_weight,
                    "Federal LTCG Rate": DEFAULT_TAX_RATES["federal_long_term_rate"],
                    "Federal ST Rate": DEFAULT_TAX_RATES["federal_short_term_rate"],
                    "NIIT Rate": DEFAULT_TAX_RATES["niit_rate"],
                    "State Tax Rate": DEFAULT_TAX_RATES["state_tax_rate"],
                }
            )
    return pd.DataFrame(rows)


def position_sale_fraction_to_target(position: pd.Series | dict[str, Any]) -> float:
    current_weight = _coerce_decimal(position.get("current_weight", 0.0))
    target_weight = _coerce_decimal(position.get("target_weight", 0.0))
    if current_weight <= 0 or target_weight >= current_weight:
        return 0.0
    return _clamp((current_weight - target_weight) / current_weight, 0.0, 1.0)


def estimate_sale_tax(
    position: pd.Series | dict[str, Any],
    sale_fraction: float,
    loss_offset: float = 0.0,
) -> dict[str, float]:
    """Estimate tax for a proportional sale of a position.

    The function does not select lots. It assumes the sold slice carries the
    same basis ratio as the full position. Negative tax values represent a
    potential capital-loss benefit only if the loss is valid and usable.
    """
    fraction = _clamp(float(sale_fraction), 0.0, 1.0)
    market_value = _coerce_float(position.get("market_value"))
    cost_basis = _coerce_float(position.get("cost_basis"))
    tax_rate = _coerce_decimal(position.get("gain_tax_rate", DEFAULT_TAX_RATES["federal_long_term_rate"]))

    sale_value = market_value * fraction
    basis_sold = cost_basis * fraction
    realized_gain = sale_value - basis_sold
    usable_offset = min(max(loss_offset, 0.0), max(realized_gain, 0.0))
    taxable_gain = max(realized_gain - usable_offset, 0.0)
    tax_on_gain = taxable_gain * tax_rate
    potential_loss_benefit = max(-realized_gain, 0.0) * tax_rate
    estimated_tax = tax_on_gain - potential_loss_benefit

    return {
        "sale_fraction": fraction,
        "sale_value": sale_value,
        "basis_sold": basis_sold,
        "realized_gain": realized_gain,
        "loss_offset_used": usable_offset,
        "taxable_gain": taxable_gain,
        "estimated_tax": estimated_tax,
        "after_tax_sale_proceeds": sale_value - max(estimated_tax, 0.0),
        "tax_rate": tax_rate,
    }


def allocate_loss_offsets(portfolio: pd.DataFrame, loss_offset_budget: float) -> dict[int, float]:
    """Allocate available losses pro rata to gains from sales down to target."""
    budget = max(float(loss_offset_budget), 0.0)
    if budget <= 0 or portfolio.empty:
        return {int(index): 0.0 for index in portfolio.index}

    gains: dict[int, float] = {}
    for index, row in portfolio.iterrows():
        sale = estimate_sale_tax(row, row.get("sale_fraction_to_target", 0.0))
        gains[int(index)] = max(sale["realized_gain"], 0.0)
    total_gain = sum(gains.values())
    usable_budget = min(total_gain, budget)
    if total_gain <= 0:
        return {int(index): 0.0 for index in portfolio.index}
    return {index: usable_budget * gain / total_gain for index, gain in gains.items()}


RETURN_COLUMN_ALIASES = {
    "date": "date",
    "ticker": "ticker",
    "symbol": "ticker",
    "security": "ticker",
    "return": "return",
    "daily_return": "return",
    "total_return": "return",
    "ret": "return",
    "price": "price",
    "close": "price",
    "adj_close": "price",
    "adjusted_close": "price",
}


def normalize_return_frame(raw: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize optional daily return or price data.

    Accepted formats:
    - Long returns: date, ticker, return.
    - Long prices: date, ticker, price.
    - Wide prices or returns: date plus one column per ticker.

    Wide values with negative observations or all values below 75% in absolute
    value are treated as returns; otherwise they are treated as prices and
    converted to returns.
    """
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "return"])

    frame = raw.copy()
    rename_map: dict[str, str] = {}
    seen: set[str] = set()
    for column in frame.columns:
        canonical = RETURN_COLUMN_ALIASES.get(_clean_column(column))
        if canonical and canonical not in seen:
            rename_map[column] = canonical
            seen.add(canonical)
    frame = frame.rename(columns=rename_map)

    if "date" not in frame:
        return pd.DataFrame(columns=["date", "ticker", "return"])

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).copy()
    if frame.empty:
        return pd.DataFrame(columns=["date", "ticker", "return"])

    if {"ticker", "return"}.issubset(frame.columns):
        output = frame.loc[:, ["date", "ticker", "return"]].copy()
        output["ticker"] = output["ticker"].astype(str).str.strip().str.upper()
        output["return"] = output["return"].map(_coerce_decimal)
        return output.dropna(subset=["date", "ticker", "return"]).query("ticker != ''").reset_index(drop=True)

    if {"ticker", "price"}.issubset(frame.columns):
        output = frame.loc[:, ["date", "ticker", "price"]].copy()
        output["ticker"] = output["ticker"].astype(str).str.strip().str.upper()
        output["price"] = output["price"].map(_coerce_float)
        output = output.sort_values(["ticker", "date"])
        output["return"] = output.groupby("ticker")["price"].pct_change()
        return output.loc[:, ["date", "ticker", "return"]].dropna().reset_index(drop=True)

    value_columns = [column for column in frame.columns if column != "date"]
    if not value_columns:
        return pd.DataFrame(columns=["date", "ticker", "return"])

    wide = frame.loc[:, ["date", *value_columns]].copy()
    has_percent_strings = bool(
        wide[value_columns]
        .astype(str)
        .apply(lambda column: column.str.contains("%", regex=False, na=False))
        .any()
        .any()
    )
    for column in value_columns:
        wide[column] = wide[column].map(_coerce_decimal if has_percent_strings else _coerce_float)
    max_abs = float(wide[value_columns].abs().max().max()) if value_columns else 0.0
    has_negative = bool((wide[value_columns] < 0).any().any())
    values_are_returns = has_percent_strings or has_negative or max_abs <= 0.75
    long = wide.melt(id_vars="date", var_name="ticker", value_name="value")
    long["ticker"] = long["ticker"].astype(str).str.strip().str.upper()
    if values_are_returns:
        long["return"] = long["value"]
        output = long.loc[:, ["date", "ticker", "return"]]
    else:
        long = long.sort_values(["ticker", "date"])
        long["return"] = long.groupby("ticker")["value"].pct_change()
        output = long.loc[:, ["date", "ticker", "return"]]
    return output.dropna(subset=["date", "ticker", "return"]).query("ticker != ''").reset_index(drop=True)


def _return_series(daily_returns: pd.DataFrame, ticker: str) -> pd.Series:
    if daily_returns is None or daily_returns.empty:
        return pd.Series(dtype=float)
    view = daily_returns[daily_returns["ticker"].astype(str).str.upper() == ticker.upper()].copy()
    if view.empty:
        return pd.Series(dtype=float)
    return view.sort_values("date").set_index("date")["return"].astype(float)


def _instrument_components(instrument: str) -> list[tuple[str, float]]:
    text = str(instrument or "").strip().upper()
    if not text or text.startswith("DYNAMIC"):
        return []
    components: list[tuple[str, float]] = []
    for part in text.split("/"):
        tokens = part.strip().split()
        if not tokens:
            continue
        ticker = tokens[0].strip().upper()
        weight = 1.0
        if len(tokens) > 1 and tokens[1].endswith("%"):
            weight = _coerce_decimal(tokens[1])
        components.append((ticker, weight))
    if not components:
        return []
    total_weight = sum(max(weight, 0.0) for _, weight in components)
    if total_weight <= 0:
        return [(ticker, 1.0 / len(components)) for ticker, _ in components]
    return [(ticker, max(weight, 0.0) / total_weight) for ticker, weight in components]


def _instrument_return_series(daily_returns: pd.DataFrame, instrument: str) -> pd.Series:
    components = _instrument_components(instrument)
    if not components:
        return pd.Series(dtype=float)
    series_parts = []
    total_weight = 0.0
    for ticker, weight in components:
        ticker_returns = _return_series(daily_returns, ticker)
        if ticker_returns.empty:
            return pd.Series(dtype=float)
        total_weight += weight
        series_parts.append((ticker_returns.rename(ticker), weight))
    if not series_parts or total_weight <= 0:
        return pd.Series(dtype=float)
    normalized_parts = [series * (weight / total_weight) for series, weight in series_parts]
    return pd.concat(normalized_parts, axis=1).dropna().sum(axis=1)


def max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    drawdowns = wealth / wealth.cummax() - 1.0
    return float(drawdowns.min())


def compute_hedge_drawdown_reduction(
    daily_returns: pd.DataFrame,
    target: str,
    instrument: str,
    hedge_ratio: float,
    min_observations: int = 60,
) -> float | None:
    """Return max-drawdown improvement from a static short hedge using daily returns.

    Positive values mean the hedge reduced the absolute peak-to-trough drawdown.
    Negative values mean the hedge made drawdown worse over the measured window.
    """
    target_returns = _return_series(daily_returns, target)
    proxy_returns = _instrument_return_series(daily_returns, instrument)
    if target_returns.empty or proxy_returns.empty:
        return None
    joined = pd.concat([target_returns.rename("target"), proxy_returns.rename("proxy")], axis=1).dropna()
    if len(joined) < min_observations:
        return None
    unhedged_drawdown = max_drawdown(joined["target"].astype(float))
    hedged_drawdown = max_drawdown(joined["target"].astype(float) - hedge_ratio * joined["proxy"].astype(float))
    return abs(unhedged_drawdown) - abs(hedged_drawdown)


def compute_return_hedge_stats(
    daily_returns: pd.DataFrame,
    target: str,
    instrument: str,
    min_observations: int = 60,
) -> dict[str, float] | None:
    target_returns = _return_series(daily_returns, target)
    proxy_returns = _instrument_return_series(daily_returns, instrument)
    if target_returns.empty or proxy_returns.empty:
        return None
    joined = pd.concat([target_returns.rename("target"), proxy_returns.rename("proxy")], axis=1).dropna()
    if len(joined) < min_observations:
        return None
    proxy_variance = float(joined["proxy"].var())
    beta = float(joined["target"].cov(joined["proxy"]) / proxy_variance) if proxy_variance > 0 else 0.0
    correlation = float(joined["target"].corr(joined["proxy"]))
    target_vol = float(joined["target"].std() * math.sqrt(252))
    proxy_vol = float(joined["proxy"].std() * math.sqrt(252))
    return {
        "correlation": 0.0 if pd.isna(correlation) else correlation,
        "beta_to_proxy": beta,
        "r_squared": 0.0 if pd.isna(correlation) else correlation**2,
        "annualized_target_vol": target_vol,
        "annualized_proxy_vol": proxy_vol,
        "n_days": float(len(joined)),
    }


def classify_daily_regimes(daily_returns: pd.DataFrame, market_proxy: str | None = None) -> pd.DataFrame:
    if daily_returns is None or daily_returns.empty:
        return pd.DataFrame(columns=["date", "regime"])
    available = set(daily_returns["ticker"].astype(str).str.upper())
    proxy = market_proxy if market_proxy and market_proxy.upper() in available else None
    if proxy is None:
        proxy = next((candidate for candidate in ["SPY", "QQQ", "IWM", "SOXX"] if candidate in available), None)
    if proxy is None:
        proxy = str(daily_returns["ticker"].iloc[0]).upper()

    returns = _return_series(daily_returns, proxy)
    if returns.empty:
        return pd.DataFrame(columns=["date", "regime"])
    trend = returns.rolling(63, min_periods=20).sum()
    volatility = returns.rolling(21, min_periods=10).std() * math.sqrt(252)
    vol_threshold = float(volatility.dropna().median()) if not volatility.dropna().empty else 0.0
    regimes = pd.DataFrame({"date": returns.index, "trend": trend, "volatility": volatility}).dropna()
    if regimes.empty:
        return pd.DataFrame(columns=["date", "regime"])
    regimes["regime"] = regimes.apply(
        lambda row: (
            "Uptrend / low volatility"
            if row["trend"] >= 0 and row["volatility"] <= vol_threshold
            else "Uptrend / high volatility"
            if row["trend"] >= 0
            else "Downtrend / low volatility"
            if row["volatility"] <= vol_threshold
            else "Downtrend / high volatility"
        ),
        axis=1,
    )
    return regimes.loc[:, ["date", "regime"]].reset_index(drop=True)


def evaluate_hedge_by_regime(
    daily_returns: pd.DataFrame,
    target: str,
    instrument: str,
    hedge_ratio: float,
) -> pd.DataFrame:
    target_returns = _return_series(daily_returns, target)
    proxy_returns = _instrument_return_series(daily_returns, instrument)
    regimes = classify_daily_regimes(daily_returns)
    if target_returns.empty or proxy_returns.empty or regimes.empty:
        return pd.DataFrame()
    joined = pd.concat([target_returns.rename("target"), proxy_returns.rename("proxy")], axis=1).dropna()
    joined = joined.merge(regimes, left_index=True, right_on="date", how="inner")
    if joined.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for regime, group in joined.groupby("regime"):
        if len(group) < 20:
            continue
        unhedged = group["target"].astype(float)
        hedged = group["target"].astype(float) - hedge_ratio * group["proxy"].astype(float)
        unhedged_vol = float(unhedged.std() * math.sqrt(252))
        hedged_vol = float(hedged.std() * math.sqrt(252))
        unhedged_drawdown = max_drawdown(unhedged)
        hedged_drawdown = max_drawdown(hedged)
        correlation = float(group["target"].corr(group["proxy"]))
        rows.append(
            {
                "regime": regime,
                "observations": int(len(group)),
                "correlation": 0.0 if pd.isna(correlation) else correlation,
                "unhedged_volatility": unhedged_vol,
                "hedged_volatility": hedged_vol,
                "volatility_reduction": (1 - hedged_vol / unhedged_vol) if unhedged_vol else 0.0,
                "unhedged_max_drawdown": unhedged_drawdown,
                "hedged_max_drawdown": hedged_drawdown,
                "drawdown_reduction": abs(unhedged_drawdown) - abs(hedged_drawdown),
            }
        )
    return pd.DataFrame(rows).sort_values("regime").reset_index(drop=True)


def _summarize_regime_table(regime_table: pd.DataFrame) -> str:
    if regime_table is None or regime_table.empty:
        return _regime_scenario_text("")
    parts = []
    for _, row in regime_table.iterrows():
        parts.append(
            f"{row['regime']}: vol reduction {row['volatility_reduction']:.1%}, "
            f"drawdown change {row['drawdown_reduction']:.1%}, corr {row['correlation']:.2f}"
        )
    return "; ".join(parts)


def _combine_risk_rows(rows: pd.DataFrame) -> dict[str, float]:
    if rows.empty:
        return {
            "correlation": 0.0,
            "beta_to_proxy": 0.0,
            "r_squared": 0.0,
            "annualized_target_vol": 0.0,
            "annualized_proxy_vol": 0.0,
            "n_days": 0.0,
        }
    weights = rows["correlation"].map(lambda value: max(_coerce_float(value), 0.01) ** 2)
    return {
        "correlation": _weighted_average(rows["correlation"], weights),
        "beta_to_proxy": _weighted_average(rows["beta_to_proxy"], weights),
        "r_squared": _weighted_average(rows["r_squared"], weights),
        "annualized_target_vol": _weighted_average(rows["annualized_target_vol"], weights),
        "annualized_proxy_vol": _weighted_average(rows["annualized_proxy_vol"], weights),
        "n_days": float(rows["n_days"].min()),
    }


def _hedge_tax_flags(hedge_type: str) -> str:
    common = "Review constructive-sale, straddle, wash-sale, short-against-the-box, and holding-period effects."
    if hedge_type == "Pair trade":
        return f"Highest tax/legal sensitivity. {common} Single-name substitute may be challenged if too close."
    if hedge_type == "Peer basket hedge":
        return f"High tax/legal sensitivity. {common} Basket design needs a restricted-list review."
    if hedge_type == "Sector hedge":
        return f"Moderate to high sensitivity. {common} ETF hedge can still create straddle questions."
    if hedge_type == "Market index hedge":
        return f"Moderate sensitivity. {common} Broad ETF is usually less issuer-specific but not risk-free."
    if hedge_type == MULTI_PROXY_HEDGE_LABEL:
        return f"High implementation sensitivity. {common} Proxy mix may overlap with restricted securities."
    return f"High governance sensitivity. {common} Dynamic changes need pre-clearance and documentation."


def _regime_scenario_text(hedge_type: str) -> str:
    return (
        "Low-vol uptrend: short hedge may drag performance; "
        "broad drawdown: market/sector hedges can reduce beta if correlations hold; "
        "sector stress: sector or peer basket may work better than SPY; "
        "issuer-specific event: none of the proxy hedges fully protects single-name risk."
    )


def _data_limitations(row_count: int, n_days: float, hedge_type: str, using_daily_returns: bool = False) -> str:
    limits = [
        (
            "Uses daily return history when supplied, but still does not verify live borrow, margin, or tax-lot details."
            if using_daily_returns
            else "Uses historical summary correlations, not a live borrow book or tax-lot optimizer."
        ),
        "Correlation can break during issuer-specific events.",
    ]
    if n_days < 504:
        limits.append("Available history is shorter than two trading years.")
    if hedge_type in {MULTI_PROXY_HEDGE_LABEL, "Regime-aware overlay"} and not using_daily_returns:
        limits.append("No bundled daily-return file was available, so proxy/regime results are heuristic.")
    if hedge_type in {"Peer basket hedge", MULTI_PROXY_HEDGE_LABEL} and not using_daily_returns:
        limits.append("Basket statistics approximate combined exposure from individual proxy summaries; they are not a full covariance model.")
    if row_count == 0:
        limits.append("No proxy evidence was available for this ticker.")
    return " ".join(limits)


def _hedge_type_scores(hedge_type: str) -> dict[str, float]:
    base = {
        "Market index hedge": {
            "liquidity_score": 95.0,
            "borrow_score": 90.0,
            "tax_simplicity_score": 48.0,
            "implementation_simplicity_score": 82.0,
        },
        "Sector hedge": {
            "liquidity_score": 88.0,
            "borrow_score": 82.0,
            "tax_simplicity_score": 38.0,
            "implementation_simplicity_score": 70.0,
        },
        "Peer basket hedge": {
            "liquidity_score": 70.0,
            "borrow_score": 58.0,
            "tax_simplicity_score": 28.0,
            "implementation_simplicity_score": 52.0,
        },
        "Pair trade": {
            "liquidity_score": 62.0,
            "borrow_score": 45.0,
            "tax_simplicity_score": 18.0,
            "implementation_simplicity_score": 42.0,
        },
        MULTI_PROXY_HEDGE_LABEL: {
            "liquidity_score": 84.0,
            "borrow_score": 78.0,
            "tax_simplicity_score": 32.0,
            "implementation_simplicity_score": 48.0,
        },
        "Regime-aware overlay": {
            "liquidity_score": 78.0,
            "borrow_score": 68.0,
            "tax_simplicity_score": 25.0,
            "implementation_simplicity_score": 36.0,
        },
    }
    return base.get(hedge_type, base["Market index hedge"])


def _make_hedge_candidate(
    position: pd.Series,
    hedge_type: str,
    instrument: str,
    rows: pd.DataFrame,
    regime_method: str,
    daily_returns: pd.DataFrame | None = None,
    hedge_assumptions: dict[str, float] | None = None,
) -> dict[str, Any]:
    summary_stats = _combine_risk_rows(rows)
    return_stats = compute_return_hedge_stats(
        daily_returns if daily_returns is not None else pd.DataFrame(),
        str(position.get("ticker", "")),
        instrument,
    )
    stats = return_stats or summary_stats
    correlation = stats["correlation"]
    hedge_ratio = max(stats["beta_to_proxy"], 0.0)
    target_vol = stats["annualized_target_vol"]
    proxy_vol = stats["annualized_proxy_vol"]
    regime_table = (
        evaluate_hedge_by_regime(
            daily_returns if daily_returns is not None else pd.DataFrame(),
            str(position.get("ticker", "")),
            instrument,
            hedge_ratio,
        )
        if return_stats
        else pd.DataFrame()
    )
    hedged_variance = max(
        target_vol**2 + (hedge_ratio * proxy_vol) ** 2 - 2 * hedge_ratio * correlation * target_vol * proxy_vol,
        0.0,
    )
    tracking_error = math.sqrt(hedged_variance) if target_vol else 0.0
    volatility_reduction = _clamp((1 - tracking_error / target_vol) * 100 if target_vol else 0.0, -100.0, 100.0)
    actual_drawdown_reduction = (
        compute_hedge_drawdown_reduction(
            daily_returns if daily_returns is not None else pd.DataFrame(),
            str(position.get("ticker", "")),
            instrument,
            hedge_ratio,
        )
        if return_stats
        else None
    )
    if actual_drawdown_reduction is None:
        drawdown_impact = _clamp(volatility_reduction * 0.80, -100.0, 100.0)
        drawdown_impact_method = (
            "Heuristic proxy: 80% of modeled volatility reduction. Upload complete daily returns to compute "
            "historical max-drawdown impact."
        )
    else:
        drawdown_impact = _clamp(actual_drawdown_reduction * 100.0, -100.0, 100.0)
        drawdown_impact_method = "Historical daily-return max-drawdown reduction."
    correlation_stability = _clamp(correlation * 80.0 + min(stats["n_days"] / 1260.0, 1.0) * 20.0)
    tracking_error_score = _clamp(100.0 - tracking_error * 100.0)
    type_scores = _hedge_type_scores(hedge_type).copy()
    assumptions = {**DEFAULT_HEDGE_ASSUMPTIONS, **(hedge_assumptions or {})}
    borrow_cost_rate = max(float(assumptions["annual_borrow_cost_rate"]), 0.0)
    tax_tolerance = _clamp(float(assumptions["tax_complexity_tolerance"]), 1.0, 5.0)
    liquidity_requirement = _clamp(float(assumptions["liquidity_requirement"]), 0.0, 100.0)
    type_scores["borrow_score"] = _clamp(type_scores["borrow_score"] - min(borrow_cost_rate * 800.0, 25.0))
    type_scores["tax_simplicity_score"] = _clamp(
        type_scores["tax_simplicity_score"] - (5.0 - tax_tolerance) * max(0.0, 60.0 - type_scores["tax_simplicity_score"]) / 8.0
    )
    type_scores["liquidity_score"] = _clamp(
        type_scores["liquidity_score"] - max(0.0, liquidity_requirement - type_scores["liquidity_score"]) * 0.75
    )

    rank_score = (
        volatility_reduction * 0.22
        + drawdown_impact * 0.16
        + correlation_stability * 0.16
        + tracking_error_score * 0.12
        + type_scores["liquidity_score"] * 0.10
        + type_scores["borrow_score"] * 0.10
        + type_scores["tax_simplicity_score"] * 0.08
        + type_scores["implementation_simplicity_score"] * 0.06
    )
    position_value = _coerce_float(position.get("market_value"))
    annual_borrow_cost = hedge_ratio * position_value * borrow_cost_rate

    return {
        "ticker": position.get("ticker", ""),
        "hedge_type": hedge_type,
        "proposed_hedge": instrument,
        "hedge_ratio": hedge_ratio,
        "hedge_notional": hedge_ratio * position_value,
        "historical_correlation": correlation,
        "historical_beta": stats["beta_to_proxy"],
        "target_volatility": target_vol,
        "proxy_volatility": proxy_vol,
        "tracking_error": tracking_error,
        "volatility_reduction": volatility_reduction / 100.0,
        "maximum_drawdown_impact": drawdown_impact / 100.0,
        "drawdown_impact_method": drawdown_impact_method,
        "scenario_behavior_by_regime": _summarize_regime_table(regime_table),
        "tax_legal_risk_flags": _hedge_tax_flags(hedge_type),
        "data_limitations": _data_limitations(len(rows), stats["n_days"], hedge_type, bool(return_stats)),
        "liquidity_score": type_scores["liquidity_score"],
        "borrow_score": type_scores["borrow_score"],
        "tax_simplicity_score": type_scores["tax_simplicity_score"],
        "implementation_simplicity_score": type_scores["implementation_simplicity_score"],
        "annual_borrow_cost_estimate": annual_borrow_cost,
        "correlation_stability_score": correlation_stability,
        "rank_score": _clamp(rank_score),
        "regime_detection_method": regime_method,
        "evidence_window": f"{int(stats['n_days']):,} trading days",
        "return_data_source": "daily returns" if return_stats else "summary proxy table",
        "regime_summary": regime_table.to_dict("records") if not regime_table.empty else [],
    }


def _best_rows(rows: pd.DataFrame, proxies: set[str], count: int = 1) -> pd.DataFrame:
    subset = rows[rows["proxy"].isin(proxies)].copy()
    if subset.empty:
        return subset
    subset["selection_score"] = subset["correlation"] * subset["r_squared"].clip(lower=0.01)
    return subset.sort_values("selection_score", ascending=False).head(count)


def _peer_rows(rows: pd.DataFrame, count: int = 3) -> pd.DataFrame:
    peers = rows[~rows["proxy"].isin(ETF_PROXIES)].copy()
    peers = peers[~peers["proxy"].astype(str).str.contains("BASKET", case=False, na=False)]
    if peers.empty:
        return peers
    peers["selection_score"] = peers["correlation"] * peers["r_squared"].clip(lower=0.01)
    return peers.sort_values("selection_score", ascending=False).head(count)


def _basket_label(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "No proxy available"
    weights = rows["correlation"].map(lambda value: max(_coerce_float(value), 0.01) ** 2)
    total = float(weights.sum())
    labels = []
    for (_, row), weight in zip(rows.iterrows(), weights):
        pct = weight / total if total else 1 / len(rows)
        labels.append(f"{row['proxy']} {pct:.0%}")
    return " / ".join(labels)


def analyze_long_short_candidates(
    position: pd.Series | dict[str, Any],
    risk_proxy: pd.DataFrame,
    daily_returns: pd.DataFrame | None = None,
    hedge_assumptions: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compare market, sector, peer, pair, multi-proxy, and regime-aware hedge designs."""
    position_series = pd.Series(position)
    ticker = str(position_series.get("ticker", "")).upper()
    if risk_proxy is None or risk_proxy.empty or "target" not in risk_proxy:
        return pd.DataFrame(
            [
                {
                    "ticker": ticker,
                    "hedge_type": "Data unavailable",
                    "proposed_hedge": "Add historical returns or proxy correlation data",
                    "rank_score": 0.0,
                    "data_limitations": "No proxy data was supplied.",
                    "why_selected_over_alternatives": "No hedge was selected because no proxy evidence was available.",
                }
            ]
        )

    rows = risk_proxy[risk_proxy["target"].astype(str).str.upper() == ticker].copy()
    for column in [
        "correlation",
        "beta_to_proxy",
        "r_squared",
        "annualized_target_vol",
        "annualized_proxy_vol",
        "n_days",
    ]:
        rows[column] = rows[column].map(_coerce_float) if column in rows else 0.0
    rows["proxy"] = rows["proxy"].astype(str).str.upper()

    returns = normalize_return_frame(daily_returns)
    has_returns = not returns.empty
    regime_method = (
        "Daily-return regime classification using 63-day trend and 21-day volatility thresholds."
        if has_returns
        else (
            "Rule-based volatility/correlation thresholds are described, but only summary proxy windows are available. "
            "A Markov/HMM model is not run unless daily returns and the required libraries are supplied."
        )
    )
    candidates: list[dict[str, Any]] = []

    market = _best_rows(rows, MARKET_INDEX_PROXIES, count=1)
    if not market.empty:
        candidates.append(
            _make_hedge_candidate(
                position_series,
                "Market index hedge",
                str(market.iloc[0]["proxy"]),
                market,
                regime_method,
                returns,
                hedge_assumptions,
            )
        )

    sector = _best_rows(rows, SECTOR_PROXIES, count=1)
    if not sector.empty:
        candidates.append(
            _make_hedge_candidate(
                position_series,
                "Sector hedge",
                str(sector.iloc[0]["proxy"]),
                sector,
                regime_method,
                returns,
                hedge_assumptions,
            )
        )

    peers = _peer_rows(rows, count=3)
    if len(peers) >= 2:
        candidates.append(
            _make_hedge_candidate(
                position_series,
                "Peer basket hedge",
                _basket_label(peers),
                peers,
                regime_method,
                returns,
                hedge_assumptions,
            )
        )
    if len(peers) >= 1:
        candidates.append(
            _make_hedge_candidate(
                position_series,
                "Pair trade",
                str(peers.iloc[0]["proxy"]),
                peers.head(1),
                regime_method,
                returns,
                hedge_assumptions,
            )
        )

    factor_rows = pd.concat([_best_rows(rows, MARKET_INDEX_PROXIES, count=2), _best_rows(rows, SECTOR_PROXIES, count=1)])
    if len(factor_rows.drop_duplicates("proxy")) >= 2:
        factor_rows = factor_rows.drop_duplicates("proxy")
        candidates.append(
            _make_hedge_candidate(
                position_series,
                MULTI_PROXY_HEDGE_LABEL,
                _basket_label(factor_rows),
                factor_rows,
                regime_method,
                returns,
                hedge_assumptions,
            )
        )

    if candidates:
        base = pd.DataFrame(candidates).sort_values("rank_score", ascending=False)
        top = base.iloc[0]
        regime_candidate = top.to_dict()
        regime_candidate["hedge_type"] = "Regime-aware overlay"
        if has_returns and "regime_summary" in base:
            regime_map: dict[str, str] = {}
            for _, candidate in base.iterrows():
                for regime_row in candidate.get("regime_summary", []) or []:
                    regime = str(regime_row.get("regime", ""))
                    score = _coerce_float(regime_row.get("volatility_reduction")) + _coerce_float(
                        regime_row.get("drawdown_reduction")
                    )
                    current = regime_map.get(regime)
                    if current is None or score > _coerce_float(current.split("|", 1)[0]):
                        regime_map[regime] = f"{score}|{candidate['hedge_type']} via {candidate['proposed_hedge']}"
            selected = [value.split("|", 1)[1] for _, value in sorted(regime_map.items())]
            regime_candidate["proposed_hedge"] = "Dynamic rules: " + "; ".join(selected[:4]) if selected else f"Dynamic rules using {top['hedge_type']} as base"
            regime_candidate["scenario_behavior_by_regime"] = _summarize_regime_table(
                pd.DataFrame(top.get("regime_summary", []))
            )
            regime_candidate["rank_score"] = _clamp(float(top["rank_score"]) - 3.0)
        else:
            regime_candidate["proposed_hedge"] = f"Dynamic rules using {top['hedge_type']} as base"
            regime_candidate["rank_score"] = _clamp(float(top["rank_score"]) - 8.0)
        regime_candidate["tax_legal_risk_flags"] = _hedge_tax_flags("Regime-aware overlay")
        regime_candidate["data_limitations"] = (
            _data_limitations(1, 0.0, "Regime-aware overlay", has_returns)
            + " Displayed correlation, beta, tracking-error, and drawdown metrics are inherited from the "
            "highest-ranked base hedge; the overlay is a policy framework that still needs out-of-sample "
            "rule validation before implementation."
        )
        regime_candidate["return_data_source"] = "daily returns" if has_returns else "summary proxy table"
        base = pd.concat([base, pd.DataFrame([regime_candidate])], ignore_index=True)
    else:
        base = pd.DataFrame(
            [
                {
                    "ticker": ticker,
                    "hedge_type": "Data unavailable",
                    "proposed_hedge": "Add historical returns or proxy correlation data",
                    "hedge_ratio": 0.0,
                    "hedge_notional": 0.0,
                    "historical_correlation": 0.0,
                    "historical_beta": 0.0,
                    "tracking_error": 0.0,
                    "volatility_reduction": 0.0,
                    "maximum_drawdown_impact": 0.0,
                    "drawdown_impact_method": "No drawdown estimate without proxy data.",
                    "scenario_behavior_by_regime": "No regime analysis without proxy data.",
                    "tax_legal_risk_flags": "Professional review required before any hedge.",
                    "data_limitations": "No proxy data was supplied for this ticker.",
                    "rank_score": 0.0,
                    "regime_detection_method": regime_method,
                    "evidence_window": "0 trading days",
                }
            ]
        )

    base = base.sort_values("rank_score", ascending=False).reset_index(drop=True)
    top_type = str(base.iloc[0]["hedge_type"])
    top_hedge = str(base.iloc[0]["proposed_hedge"])
    explanations = []
    for index, row in base.iterrows():
        if index == 0:
            explanations.append(
                f"Selected because it has the strongest blended hedge score for {ticker}: "
                f"{top_type} using {top_hedge}, balancing volatility reduction, correlation stability, liquidity, borrow risk, and tax complexity."
            )
        else:
            explanations.append(
                f"Ranked below {top_type} because its blended evidence/complexity score was lower for this ticker."
            )
    base["why_selected_over_alternatives"] = explanations
    return base


def _tax_cost_score(estimated_tax: float, market_value: float) -> float:
    if market_value <= 0:
        return 100.0
    tax_drag = max(estimated_tax, 0.0) / market_value
    return _clamp(100.0 - tax_drag * 250.0)


def _time_fit_score(strategy_id: str, user_horizon_years: int, transition_years: int) -> float:
    if strategy_id == "sell_immediately":
        return 92.0
    if strategy_id == "sell_gradually":
        return 88.0 if user_horizon_years >= transition_years else 52.0
    if strategy_id in {"long_short_overlay", "pair_or_basket_hedge"}:
        return 78.0 if user_horizon_years >= 2 else 58.0
    if strategy_id == "exchange_direct_indexing":
        return 72.0 if user_horizon_years >= 7 else 38.0
    if strategy_id == "hold_monitor":
        return 70.0 if user_horizon_years >= 5 else 45.0
    return 70.0


def _weighted_strategy_score(components: dict[str, float], priorities: dict[str, float]) -> float:
    total_weight = sum(max(float(value), 0.0) for value in priorities.values())
    if total_weight <= 0:
        return sum(components.values()) / len(components)
    return sum(components[key] * max(float(priorities.get(key, 0.0)), 0.0) for key in components) / total_weight


def _best_hedge_volatility_reduction(
    long_short_candidates: pd.DataFrame,
    hedge_types: set[str] | None = None,
) -> float | None:
    if long_short_candidates is None or long_short_candidates.empty or "hedge_type" not in long_short_candidates:
        return None
    candidates = long_short_candidates[long_short_candidates["hedge_type"].astype(str) != "Data unavailable"].copy()
    if hedge_types is not None:
        candidates = candidates[candidates["hedge_type"].astype(str).isin(hedge_types)]
    if candidates.empty:
        return None
    candidates = candidates.sort_values("rank_score", ascending=False)
    return _coerce_decimal(candidates.iloc[0].get("volatility_reduction"))


def _strategy_assumption_text(
    strategy_id: str,
    sale_fraction: float,
    transition_years: int,
    loss_offset: float,
    philanthropic_intent: bool,
) -> str:
    if strategy_id == "sell_immediately":
        return f"Sell {sale_fraction:.0%} of the position now to reach the target weight using proportional basis."
    if strategy_id == "sell_gradually":
        return f"Sell the target-reduction amount over {transition_years} tax years with static prices and tax rates."
    if strategy_id == "harvest_losses":
        return f"Apply ${loss_offset:,.0f} of available losses to the gain from the target-reduction sale."
    if strategy_id == "long_short_overlay":
        return "Use a hedge or tax-aware long/short sleeve while retaining the appreciated position."
    if strategy_id == "pair_or_basket_hedge":
        return "Use a peer, sector, or basket short to reduce specific exposure without an immediate sale."
    if strategy_id == "hold_monitor":
        return "Avoid near-term realization and revisit when concentration, tax rates, or liquidity needs change."
    if strategy_id == "charitable_daf":
        return "Contribute appreciated long-term shares only if charitable intent exists and the advisor confirms deductibility."
    if strategy_id == "exchange_direct_indexing":
        return "Evaluate institutional exchange-fund or direct-indexing transition paths; terms and eligibility are outside this model."
    return ""


def score_strategies_for_position(
    position: pd.Series,
    long_short_candidates: pd.DataFrame,
    *,
    loss_offset: float,
    transition_years: int,
    user_horizon_years: int,
    philanthropic_intent: bool,
    priorities: dict[str, float] | None = None,
) -> pd.DataFrame:
    priorities = priorities or DEFAULT_STRATEGY_PRIORITIES
    sale_fraction = _coerce_float(position.get("sale_fraction_to_target"))
    market_value = _coerce_float(position.get("market_value"))
    gain_pct = _coerce_float(position.get("unrealized_gain_pct"))
    current_weight = _coerce_decimal(position.get("current_weight"))
    target_weight = _coerce_decimal(position.get("target_weight"))
    excess_weight = max(current_weight - target_weight, 0.0)
    immediate_tax = estimate_sale_tax(position, sale_fraction)
    loss_harvest_tax = estimate_sale_tax(position, sale_fraction, loss_offset)
    hedge_vol_reduction = _best_hedge_volatility_reduction(long_short_candidates)
    pair_basket_vol_reduction = _best_hedge_volatility_reduction(
        long_short_candidates,
        {"Peer basket hedge", "Pair trade"},
    )
    overlay_risk_reduction = max(hedge_vol_reduction * 100.0, 20.0) if hedge_vol_reduction is not None else 5.0
    pair_basket_risk_reduction = (
        max(pair_basket_vol_reduction * 85.0, 18.0) if pair_basket_vol_reduction is not None else 5.0
    )

    strategy_inputs = {
        "sell_immediately": {
            "tax": immediate_tax,
            "risk_reduction": sale_fraction * 100.0,
            "diversification": sale_fraction * 92.0,
            "complexity": 18.0,
            "liquidity_borrow_risk": 8.0,
            "tax_uncertainty": 22.0,
        },
        "sell_gradually": {
            "tax": immediate_tax,
            "risk_reduction": sale_fraction * 72.0,
            "diversification": sale_fraction * 78.0,
            "complexity": 32.0,
            "liquidity_borrow_risk": 10.0,
            "tax_uncertainty": 28.0,
        },
        "harvest_losses": {
            "tax": loss_harvest_tax,
            "risk_reduction": sale_fraction * 88.0,
            "diversification": sale_fraction * 86.0,
            "complexity": 46.0 if loss_offset else 58.0,
            "liquidity_borrow_risk": 16.0,
            "tax_uncertainty": 48.0 if loss_offset else 65.0,
        },
        "long_short_overlay": {
            "tax": estimate_sale_tax(position, 0.0),
            "risk_reduction": overlay_risk_reduction,
            "diversification": 45.0,
            "complexity": 72.0,
            "liquidity_borrow_risk": 58.0,
            "tax_uncertainty": 78.0,
        },
        "pair_or_basket_hedge": {
            "tax": estimate_sale_tax(position, 0.0),
            "risk_reduction": pair_basket_risk_reduction,
            "diversification": 34.0 if pair_basket_vol_reduction is not None else 8.0,
            "complexity": 82.0,
            "liquidity_borrow_risk": 72.0,
            "tax_uncertainty": 86.0,
        },
        "hold_monitor": {
            "tax": estimate_sale_tax(position, 0.0),
            "risk_reduction": 100.0 if excess_weight <= 0.01 else 8.0,
            "diversification": 8.0,
            "complexity": 8.0,
            "liquidity_borrow_risk": 5.0,
            "tax_uncertainty": 12.0,
        },
        "charitable_daf": {
            "tax": estimate_sale_tax(position, 0.0),
            "risk_reduction": sale_fraction * (85.0 if philanthropic_intent else 28.0),
            "diversification": sale_fraction * (82.0 if philanthropic_intent else 20.0),
            "complexity": 44.0,
            "liquidity_borrow_risk": 12.0,
            "tax_uncertainty": 34.0 if philanthropic_intent and position.get("holding_period") == "Long Term" else 72.0,
        },
        "exchange_direct_indexing": {
            "tax": estimate_sale_tax(position, 0.0),
            "risk_reduction": 58.0 if market_value >= 500_000 and gain_pct >= 0.30 else 32.0,
            "diversification": 70.0 if market_value >= 500_000 and gain_pct >= 0.30 else 40.0,
            "complexity": 76.0,
            "liquidity_borrow_risk": 42.0,
            "tax_uncertainty": 54.0,
        },
    }

    rows: list[dict[str, Any]] = []
    for strategy_id, values in strategy_inputs.items():
        tax = values["tax"]
        components = {
            "tax_cost": _tax_cost_score(tax["estimated_tax"], market_value),
            "concentration_risk_reduction": _clamp(values["risk_reduction"]),
            "diversification_benefit": _clamp(values["diversification"]),
            "implementation_complexity": 100.0 - values["complexity"],
            "liquidity_borrow_risk": 100.0 - values["liquidity_borrow_risk"],
            "time_horizon": _time_fit_score(strategy_id, user_horizon_years, transition_years),
            "tax_rule_uncertainty": 100.0 - values["tax_uncertainty"],
        }
        rank_score = _weighted_strategy_score(components, priorities)
        if strategy_id == "charitable_daf" and not philanthropic_intent:
            rank_score *= 0.70
        if strategy_id == "hold_monitor" and excess_weight > 0.10:
            rank_score *= 0.75

        rows.append(
            {
                "ticker": position.get("ticker"),
                "strategy_id": strategy_id,
                "strategy": STRATEGY_LABELS[strategy_id],
                "rank_score": rank_score,
                "estimated_tax": tax["estimated_tax"],
                "sale_value": tax["sale_value"],
                "realized_gain": tax["realized_gain"],
                "loss_offset_used": tax["loss_offset_used"],
                "after_tax_sale_proceeds": tax["after_tax_sale_proceeds"],
                "concentration_reduction": values["risk_reduction"] / 100.0,
                "diversification_benefit_score": values["diversification"],
                "implementation_complexity": values["complexity"],
                "liquidity_borrow_risk": values["liquidity_borrow_risk"],
                "tax_rule_uncertainty": values["tax_uncertainty"],
                "time_horizon_fit": components["time_horizon"],
                "assumptions": _strategy_assumption_text(
                    strategy_id,
                    sale_fraction,
                    transition_years,
                    loss_offset,
                    philanthropic_intent,
                ),
                "pros": _strategy_pros(strategy_id),
                "cons": _strategy_cons(strategy_id),
                "key_risks": _strategy_risks(strategy_id),
                "not_applicable_when": _strategy_not_applicable_when(strategy_id),
            }
        )

    return pd.DataFrame(rows).sort_values("rank_score", ascending=False).reset_index(drop=True)


def _strategy_pros(strategy_id: str) -> str:
    return {
        "sell_immediately": "Fastest concentration reduction; simple execution; clean exposure change.",
        "sell_gradually": "Spreads realization across years; preserves flexibility if rates or prices change.",
        "harvest_losses": "Can reduce current tax cost if losses are valid, same-character, and usable.",
        "long_short_overlay": "May reduce beta and create tax-loss harvesting opportunities without an immediate sale.",
        "pair_or_basket_hedge": "Targets sector or peer exposure more directly than a broad market hedge.",
        "hold_monitor": "Avoids immediate tax realization and implementation complexity.",
        "charitable_daf": "May reduce concentration without selling if charitable goals already exist.",
        "exchange_direct_indexing": "Can diversify or transition while deferring some gain, subject to eligibility and terms.",
    }.get(strategy_id, "")


def _strategy_cons(strategy_id: str) -> str:
    return {
        "sell_immediately": "Highest immediate tax bill when embedded gains are large.",
        "sell_gradually": "Concentration risk remains during the transition period.",
        "harvest_losses": "Losses may be unavailable, deferred, or disallowed; tax benefit depends on character and timing.",
        "long_short_overlay": "Borrow, tracking, constructive-sale, straddle, and wash-sale issues require specialist review.",
        "pair_or_basket_hedge": "Higher basis risk and tax/legal sensitivity than a diversified broad hedge.",
        "hold_monitor": "Does not solve concentration risk unless the target weight is already acceptable.",
        "charitable_daf": "Only makes sense when charitable intent and deduction capacity are real.",
        "exchange_direct_indexing": "Eligibility, lockups, fees, and diversification limits can be restrictive.",
    }.get(strategy_id, "")


def _strategy_risks(strategy_id: str) -> str:
    hedge_risks = "constructive sale; straddle; wash sale; short-against-the-box; holding-period suspension; borrow recall"
    return {
        "sell_immediately": "Tax-rate estimate, lot selection, liquidity, and reinvestment timing.",
        "sell_gradually": "Price path, future tax-law changes, and delayed risk reduction.",
        "harvest_losses": "Wash-sale disallowance, short/long-term netting mismatch, and insufficient offset capacity.",
        "long_short_overlay": hedge_risks,
        "pair_or_basket_hedge": hedge_risks + "; correlation breakdown; crowded peer trade.",
        "hold_monitor": "Single-name drawdown and opportunity cost of delayed diversification.",
        "charitable_daf": "Deduction limits, appraisal/substantiation, charity timing, and loss of asset control.",
        "exchange_direct_indexing": "Illiquidity, manager terms, concentration gates, and tax opinion uncertainty.",
    }.get(strategy_id, "")


def _strategy_not_applicable_when(strategy_id: str) -> str:
    return {
        "sell_immediately": "Cash tax budget is constrained or the sale would force unacceptable gain recognition.",
        "sell_gradually": "Risk must be reduced immediately or future tax rates are expected to rise sharply.",
        "harvest_losses": "No valid losses exist or replacement trades would create wash-sale/straddle issues.",
        "long_short_overlay": "The investor cannot tolerate shorting, leverage, borrow risk, or complex tax review.",
        "pair_or_basket_hedge": "Peer correlations are unstable, borrow is unavailable, or substitutes are tax-sensitive.",
        "hold_monitor": "The position is materially above target and downside risk is unacceptable.",
        "charitable_daf": "There is no independent charitable goal or the position is short-term/low-gain.",
        "exchange_direct_indexing": "Minimums, lockups, fees, or security eligibility do not fit the investor.",
    }.get(strategy_id, "")


def run_transition_analysis(
    raw_portfolio: pd.DataFrame,
    risk_proxy: pd.DataFrame | None,
    *,
    daily_returns: pd.DataFrame | None = None,
    loss_offset_budget: float = 0.0,
    transition_years: int = 3,
    user_horizon_years: int = 5,
    philanthropic_intent: bool = False,
    priorities: dict[str, float] | None = None,
    hedge_assumptions: dict[str, float] | None = None,
) -> dict[str, pd.DataFrame]:
    portfolio = normalize_portfolio_frame(raw_portfolio)
    priorities = priorities or DEFAULT_STRATEGY_PRIORITIES
    returns = normalize_return_frame(daily_returns)
    loss_allocations = allocate_loss_offsets(portfolio, loss_offset_budget)

    strategy_frames: list[pd.DataFrame] = []
    long_short_frames: list[pd.DataFrame] = []
    for index, position in portfolio.iterrows():
        hedge_candidates = analyze_long_short_candidates(
            position,
            risk_proxy if risk_proxy is not None else pd.DataFrame(),
            returns,
            hedge_assumptions,
        )
        long_short_frames.append(hedge_candidates)
        strategy_frames.append(
            score_strategies_for_position(
                position,
                hedge_candidates,
                loss_offset=loss_allocations.get(int(index), 0.0),
                transition_years=max(int(transition_years), 1),
                user_horizon_years=max(int(user_horizon_years), 1),
                philanthropic_intent=philanthropic_intent,
                priorities=priorities,
            )
        )

    strategy_table = pd.concat(strategy_frames, ignore_index=True) if strategy_frames else pd.DataFrame()
    long_short_table = pd.concat(long_short_frames, ignore_index=True) if long_short_frames else pd.DataFrame()
    position_summary = (
        strategy_table.sort_values(["ticker", "rank_score"], ascending=[True, False])
        .groupby("ticker", as_index=False)
        .head(1)
        .reset_index(drop=True)
        if not strategy_table.empty
        else pd.DataFrame()
    )

    if not strategy_table.empty and not portfolio.empty:
        portfolio_weights = portfolio.set_index("ticker")["market_value"]
        grouped_rows = []
        for strategy, group in strategy_table.groupby("strategy"):
            weights = group["ticker"].map(portfolio_weights).fillna(0.0)
            grouped_rows.append(
                {
                    "strategy": strategy,
                    "weighted_rank_score": _weighted_average(group["rank_score"], weights),
                    "estimated_tax": group["estimated_tax"].sum(),
                    "sale_value": group["sale_value"].sum(),
                    "realized_gain": group["realized_gain"].sum(),
                    "loss_offset_used": group["loss_offset_used"].sum(),
                    "after_tax_sale_proceeds": group["after_tax_sale_proceeds"].sum(),
                    "average_concentration_reduction": _weighted_average(group["concentration_reduction"], weights),
                    "average_complexity": _weighted_average(group["implementation_complexity"], weights),
                    "average_tax_uncertainty": _weighted_average(group["tax_rule_uncertainty"], weights),
                }
            )
        portfolio_strategy_summary = pd.DataFrame(grouped_rows).sort_values(
            "weighted_rank_score", ascending=False
        ).reset_index(drop=True)
    else:
        portfolio_strategy_summary = pd.DataFrame()

    total_market_value = float(portfolio["market_value"].sum()) if not portfolio.empty else 0.0
    total_gain = float(portfolio["unrealized_gain"].sum()) if not portfolio.empty else 0.0
    current_weight = float(portfolio["current_weight"].sum()) if not portfolio.empty else 0.0
    target_weight = float(portfolio["target_weight"].sum()) if not portfolio.empty else 0.0
    top_portfolio_strategy = (
        str(portfolio_strategy_summary.iloc[0]["strategy"]) if not portfolio_strategy_summary.empty else "No recommendation"
    )
    portfolio_summary = pd.DataFrame(
        [
            {
                "total_market_value": total_market_value,
                "total_unrealized_gain": total_gain,
                "current_portfolio_weight": current_weight,
                "target_portfolio_weight": target_weight,
                "excess_weight": max(current_weight - target_weight, 0.0),
                "top_portfolio_strategy": top_portfolio_strategy,
                "positions_analyzed": int(len(portfolio)),
            }
        ]
    )

    return {
        "portfolio": portfolio,
        "strategy_table": strategy_table,
        "position_summary": position_summary,
        "portfolio_strategy_summary": portfolio_strategy_summary,
        "portfolio_summary": portfolio_summary,
        "long_short_table": long_short_table,
        "daily_returns": returns,
        "regime_table": classify_daily_regimes(returns),
        "sensitivity_tables": build_sensitivity_tables(portfolio, long_short_table, loss_offset_budget),
    }


def build_transition_plan_summary(
    analysis_results: dict[str, pd.DataFrame],
    selected_strategy: str | None = None,
    max_tax_budget: float | None = None,
) -> dict[str, Any]:
    """Create deterministic one-page plan defaults from analysis output."""
    portfolio = analysis_results.get("portfolio", pd.DataFrame())
    portfolio_summary = analysis_results.get("portfolio_summary", pd.DataFrame())
    strategy_summary = analysis_results.get("portfolio_strategy_summary", pd.DataFrame())
    position_summary = analysis_results.get("position_summary", pd.DataFrame())
    long_short_table = analysis_results.get("long_short_table", pd.DataFrame())

    summary_row = portfolio_summary.iloc[0].to_dict() if not portfolio_summary.empty else {}
    strategy_name = selected_strategy or summary_row.get("top_portfolio_strategy") or ""
    selected_strategy_row = pd.Series(dtype=object)
    if not strategy_summary.empty and strategy_name:
        matching = strategy_summary[strategy_summary["strategy"] == strategy_name]
        if not matching.empty:
            selected_strategy_row = matching.iloc[0]
    if selected_strategy_row.empty and not strategy_summary.empty:
        selected_strategy_row = strategy_summary.iloc[0]
        strategy_name = str(selected_strategy_row.get("strategy", strategy_name))

    available_hedges = (
        long_short_table[long_short_table["hedge_type"].astype(str) != "Data unavailable"].copy()
        if not long_short_table.empty and "hedge_type" in long_short_table
        else pd.DataFrame()
    )
    if not available_hedges.empty:
        top_hedge = available_hedges.sort_values("rank_score", ascending=False).iloc[0].to_dict()
        hedge_summary = f"{top_hedge.get('hedge_type')} via {top_hedge.get('proposed_hedge')}"
    else:
        hedge_summary = "No hedge candidate selected"

    tax_estimate = _coerce_float(selected_strategy_row.get("estimated_tax")) if not selected_strategy_row.empty else 0.0
    tax_budget = max_tax_budget if max_tax_budget is not None else tax_estimate * 1.15
    tax_budget_remaining = float(tax_budget) - tax_estimate
    sale_value = _coerce_float(selected_strategy_row.get("sale_value")) if not selected_strategy_row.empty else 0.0
    realized_gain = _coerce_float(selected_strategy_row.get("realized_gain")) if not selected_strategy_row.empty else 0.0
    loss_offset_used = (
        _coerce_float(selected_strategy_row.get("loss_offset_used")) if not selected_strategy_row.empty else 0.0
    )
    after_tax_sale_proceeds = (
        _coerce_float(selected_strategy_row.get("after_tax_sale_proceeds")) if not selected_strategy_row.empty else 0.0
    )

    primary_positions = []
    if not position_summary.empty:
        for _, row in position_summary.iterrows():
            primary_positions.append(
                f"{row.get('ticker')}: {row.get('strategy')} "
                f"(score {float(row.get('rank_score', 0.0)):.1f}, tax ${float(row.get('estimated_tax', 0.0)):,.0f})"
            )

    return {
        "objective": (
            f"Reduce concentrated exposure from {float(summary_row.get('current_portfolio_weight', 0.0)):.1%} "
            f"toward {float(summary_row.get('target_portfolio_weight', 0.0)):.1%} while managing realized gains and implementation risk."
        ),
        "selected_strategy": strategy_name,
        "current_weight": _coerce_float(summary_row.get("current_portfolio_weight")),
        "target_weight": _coerce_float(summary_row.get("target_portfolio_weight")),
        "excess_weight": _coerce_float(summary_row.get("excess_weight")),
        "total_market_value": _coerce_float(summary_row.get("total_market_value")),
        "total_unrealized_gain": _coerce_float(summary_row.get("total_unrealized_gain")),
        "estimated_sale_value": sale_value,
        "estimated_realized_gain": realized_gain,
        "loss_offset_used": loss_offset_used,
        "after_tax_sale_proceeds": after_tax_sale_proceeds,
        "estimated_tax": tax_estimate,
        "max_tax_budget": float(tax_budget),
        "tax_budget_remaining": tax_budget_remaining,
        "hedge_summary": hedge_summary,
        "primary_position_actions": "\n".join(primary_positions),
        "positions_analyzed": int(summary_row.get("positions_analyzed", len(portfolio))),
    }


def _sma_portfolio_context(portfolio: pd.DataFrame) -> dict[str, float]:
    if portfolio is None or portfolio.empty:
        return {
            "total_market_value": 0.0,
            "total_unrealized_gain": 0.0,
            "embedded_gain_pct": 0.0,
            "current_weight": 0.0,
            "target_weight": 0.0,
            "excess_weight": 0.0,
            "sale_to_target_gain": 0.0,
            "sale_to_target_gain_pct_of_value": 0.0,
        }
    total_market_value = float(portfolio["market_value"].sum())
    total_gain = float(portfolio["unrealized_gain"].sum())
    sale_to_target_gain = 0.0
    for _, row in portfolio.iterrows():
        sale_to_target_gain += max(estimate_sale_tax(row, row.get("sale_fraction_to_target", 0.0))["realized_gain"], 0.0)
    return {
        "total_market_value": total_market_value,
        "total_unrealized_gain": total_gain,
        "embedded_gain_pct": total_gain / total_market_value if total_market_value else 0.0,
        "current_weight": float(portfolio["current_weight"].sum()),
        "target_weight": float(portfolio["target_weight"].sum()),
        "excess_weight": max(float(portfolio["current_weight"].sum() - portfolio["target_weight"].sum()), 0.0),
        "sale_to_target_gain": sale_to_target_gain,
        "sale_to_target_gain_pct_of_value": sale_to_target_gain / total_market_value if total_market_value else 0.0,
    }


def _sma_hedge_context(long_short_table: pd.DataFrame | None) -> dict[str, Any]:
    if long_short_table is None or long_short_table.empty or "hedge_type" not in long_short_table:
        return {
            "best_hedge_type": "No hedge evidence",
            "best_hedge": "No proxy evidence available",
            "best_volatility_reduction": 0.0,
            "best_drawdown_impact": 0.0,
            "best_tracking_error": 0.0,
            "evidence_source": "No long/short evidence",
        }
    available = long_short_table[long_short_table["hedge_type"].astype(str) != "Data unavailable"].copy()
    if available.empty:
        return {
            "best_hedge_type": "No hedge evidence",
            "best_hedge": "No proxy evidence available",
            "best_volatility_reduction": 0.0,
            "best_drawdown_impact": 0.0,
            "best_tracking_error": 0.0,
            "evidence_source": "No long/short evidence",
        }
    top = available.sort_values("rank_score", ascending=False).iloc[0]
    return {
        "best_hedge_type": str(top.get("hedge_type", "")),
        "best_hedge": str(top.get("proposed_hedge", "")),
        "best_volatility_reduction": _coerce_decimal(top.get("volatility_reduction")),
        "best_drawdown_impact": _coerce_decimal(top.get("maximum_drawdown_impact")),
        "best_tracking_error": _coerce_decimal(top.get("tracking_error")),
        "evidence_source": str(top.get("return_data_source", "summary proxy table")),
    }


def _weighted_sma_score(scores: dict[str, float], priorities: dict[str, float]) -> float:
    total_weight = sum(max(float(value), 0.0) for value in priorities.values())
    if total_weight <= 0:
        return sum(scores.values()) / len(scores)
    return sum(scores[key] * max(float(priorities.get(key, 0.0)), 0.0) for key in scores) / total_weight


def evaluate_sma_designs(
    portfolio: pd.DataFrame,
    long_short_table: pd.DataFrame | None = None,
    *,
    priorities: dict[str, float] | None = None,
    hedge_assumptions: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compare long/short SMA designs for concentrated-stock transition work.

    Scores are educational and assumption-driven. The output is a due-diligence
    starting point, not a manager selection or trade recommendation.
    """
    priorities = {**DEFAULT_SMA_STUDY_PRIORITIES, **(priorities or {})}
    assumptions = {**DEFAULT_HEDGE_ASSUMPTIONS, **(hedge_assumptions or {})}
    context = _sma_portfolio_context(portfolio)
    hedge = _sma_hedge_context(long_short_table)
    embedded_gain_score = _clamp(context["embedded_gain_pct"] * 100.0)
    sale_gain_score = _clamp(context["sale_to_target_gain_pct_of_value"] * 140.0)
    excess_score = _clamp(context["excess_weight"] * 100.0)
    hedge_signal = _clamp((hedge["best_volatility_reduction"] + hedge["best_drawdown_impact"]) * 100.0)
    borrow_cost_penalty = min(max(float(assumptions["annual_borrow_cost_rate"]), 0.0) * 500.0, 20.0)
    tax_tolerance = _clamp(float(assumptions["tax_complexity_tolerance"]), 1.0, 5.0)
    tax_tolerance_penalty = (5.0 - tax_tolerance) * 5.0

    rows: list[dict[str, Any]] = []
    for design in SMA_DESIGN_LIBRARY:
        scores = dict(design["base_scores"])
        design_id = str(design["design_id"])

        if design_id == "conservative":
            scores["tax_loss_capacity"] += embedded_gain_score * 0.08 + sale_gain_score * 0.08
            scores["concentration_transition_fit"] += excess_score * 0.12
            scores["risk_control"] += hedge_signal * 0.10
        elif design_id == "balanced":
            scores["tax_loss_capacity"] += embedded_gain_score * 0.14 + sale_gain_score * 0.16
            scores["concentration_transition_fit"] += excess_score * 0.20
            scores["risk_control"] += hedge_signal * 0.28
            scores["liquidity_borrow_safety"] -= borrow_cost_penalty * 0.35
        elif design_id == "hedge_focused":
            scores["tax_loss_capacity"] += embedded_gain_score * 0.10 + sale_gain_score * 0.10
            scores["concentration_transition_fit"] += excess_score * 0.32
            scores["risk_control"] += hedge_signal * 0.48
            scores["tax_rule_clarity"] -= tax_tolerance_penalty * 0.65
            scores["liquidity_borrow_safety"] -= borrow_cost_penalty * 0.45
        elif design_id == "aggressive":
            scores["tax_loss_capacity"] += embedded_gain_score * 0.16 + sale_gain_score * 0.18
            scores["concentration_transition_fit"] += excess_score * 0.08
            scores["risk_control"] += hedge_signal * 0.15
            scores["tax_rule_clarity"] -= tax_tolerance_penalty
            scores["liquidity_borrow_safety"] -= borrow_cost_penalty * 0.65
            scores["cost_efficiency"] -= borrow_cost_penalty * 0.50

        scores = {key: _clamp(value) for key, value in scores.items()}
        selection_score = _weighted_sma_score(scores, priorities)
        rows.append(
            {
                "design_id": design_id,
                "design": design["design"],
                "description": design["description"],
                "selection_score": selection_score,
                "net_exposure": design["net_exposure"],
                "gross_exposure": design["gross_exposure"],
                "long_book": design["long_book"],
                "short_book": design["short_book"],
                "expected_loss_harvest_potential": design["expected_loss_harvest_potential"],
                "estimated_fee_carry": design["estimated_fee_carry"],
                "expected_tracking_error": design["expected_tracking_error"],
                "tax_loss_capacity_score": scores["tax_loss_capacity"],
                "concentration_transition_fit_score": scores["concentration_transition_fit"],
                "risk_control_score": scores["risk_control"],
                "tax_rule_clarity_score": scores["tax_rule_clarity"],
                "implementation_simplicity_score": scores["implementation_simplicity"],
                "liquidity_borrow_safety_score": scores["liquidity_borrow_safety"],
                "cost_efficiency_score": scores["cost_efficiency"],
                "manager_operational_quality_score": scores["manager_operational_quality"],
                "diversification_benefit_score": scores["diversification_benefit"],
                "implementation_complexity": design["implementation_complexity"],
                "liquidity_borrow_risk": design["liquidity_borrow_risk"],
                "tax_rule_risk": design["tax_rule_risk"],
                "best_when": design["best_when"],
                "avoid_when": design["avoid_when"],
                "professional_review_flags": design["review_flags"],
                "best_hedge_evidence": f"{hedge['best_hedge_type']} via {hedge['best_hedge']}",
                "hedge_evidence_source": hedge["evidence_source"],
                "portfolio_context": (
                    f"Analyzed value ${context['total_market_value']:,.0f}; embedded gain "
                    f"{context['embedded_gain_pct']:.1%}; excess weight {context['excess_weight']:.1%}; "
                    f"sale-to-target gain ${context['sale_to_target_gain']:,.0f}."
                ),
            }
        )

    output = pd.DataFrame(rows).sort_values("selection_score", ascending=False).reset_index(drop=True)
    output.insert(0, "rank", range(1, len(output) + 1))
    if not output.empty:
        top_design = str(output.iloc[0]["design"])
        explanations = []
        for index, row in output.iterrows():
            if index == 0:
                explanations.append(
                    f"Selected for study because it has the strongest blended fit across tax-loss capacity, "
                    f"concentration transition, risk control, implementation burden, liquidity/borrow safety, and tax-rule clarity."
                )
            else:
                explanations.append(
                    f"Ranks below {top_design} because the blended score gives less favorable tradeoffs for the current priorities."
                )
        output["why_selected_over_alternatives"] = explanations
    return output


def build_sma_due_diligence_checklist(selected_design: str | None = None) -> pd.DataFrame:
    design_note = f" for {selected_design}" if selected_design else ""
    rows = [
        {
            "Review Area": "Mandate fit",
            "Question": f"Does the SMA mandate{design_note} explicitly support concentrated-stock transition rather than generic alpha?",
            "Evidence Needed": "Investment policy statement, model portfolio ranges, benchmark, net/gross exposure limits.",
        },
        {
            "Review Area": "Tax controls",
            "Question": "Can the manager monitor wash sales, straddles, constructive-sale risk, and holding-period effects before trades?",
            "Evidence Needed": "Tax-lot workflow, restricted-list process, CPA report sample, year-end tax package sample.",
        },
        {
            "Review Area": "Hedge design",
            "Question": "Are shorts diversified, liquid, borrowable, and clearly not a short-against-the-box substitute?",
            "Evidence Needed": "Short-book policy, borrow-cost history, liquidity screens, restricted securities list.",
        },
        {
            "Review Area": "Risk model",
            "Question": "Does risk reporting show beta, sector/factor exposure, tracking error, drawdown, and stress behavior?",
            "Evidence Needed": "Sample monthly report, factor exposure report, historical drawdown and turnover analysis.",
        },
        {
            "Review Area": "Costs and conflicts",
            "Question": "What all-in cost applies after advisory fee, platform/wrap fee, borrow, margin, trading, and embedded expenses?",
            "Evidence Needed": "Form ADV/wrap brochure, fee schedule, trade-cost policy, soft-dollar/conflict disclosures.",
        },
        {
            "Review Area": "Implementation gates",
            "Question": "Who can approve launch, tax budget changes, restricted-list exceptions, and hedge exposure changes?",
            "Evidence Needed": "Written approval workflow, stop-loss/stop-review rules, named owner for tax/legal signoff.",
        },
    ]
    return pd.DataFrame(rows)


def build_diy_sma_exposure_budget(
    sleeve_capital: float,
    target_net_exposure: float,
    max_gross_exposure: float,
    max_short_exposure: float,
    *,
    max_single_long_weight: float = 0.04,
    max_single_short_weight: float = 0.02,
    sector_cap: float = 0.25,
    min_loss_harvest_threshold: float = 1000.0,
    annual_realized_gain_budget: float = 0.0,
) -> dict[str, float]:
    """Translate DIY SMA limits into dollar budgets.

    For a long/short book, net exposure equals long notional minus short
    notional. Gross exposure equals long notional plus short notional. The
    short budget is capped by both the user's max short limit and the gross
    exposure limit implied by the target net exposure.
    """
    capital = max(_coerce_float(sleeve_capital), 0.0)
    target_net = _clamp(_coerce_leverage_decimal(target_net_exposure), 0.0, 2.0)
    max_gross = max(_coerce_leverage_decimal(max_gross_exposure), target_net)
    max_short = _clamp(_coerce_decimal(max_short_exposure), 0.0, 1.5)

    short_cap_by_gross = max((max_gross - target_net) * capital / 2.0, 0.0)
    short_cap_by_policy = max_short * capital
    short_notional = min(short_cap_by_gross, short_cap_by_policy)
    long_notional = target_net * capital + short_notional
    gross_notional = long_notional + short_notional
    net_notional = long_notional - short_notional
    gross_capacity_remaining = max(max_gross * capital - gross_notional, 0.0)

    return {
        "sleeve_capital": capital,
        "target_net_exposure": target_net,
        "max_gross_exposure": max_gross,
        "max_short_exposure": max_short,
        "long_notional": long_notional,
        "short_notional": short_notional,
        "net_notional": net_notional,
        "gross_notional": gross_notional,
        "actual_net_exposure": net_notional / capital if capital else 0.0,
        "actual_gross_exposure": gross_notional / capital if capital else 0.0,
        "actual_short_exposure": short_notional / capital if capital else 0.0,
        "gross_capacity_remaining": gross_capacity_remaining,
        "max_single_long_dollars": capital * _clamp(_coerce_decimal(max_single_long_weight), 0.0, 1.0),
        "max_single_short_dollars": capital * _clamp(_coerce_decimal(max_single_short_weight), 0.0, 1.0),
        "sector_cap_dollars": capital * _clamp(_coerce_decimal(sector_cap), 0.0, 1.0),
        "min_loss_harvest_threshold": max(_coerce_float(min_loss_harvest_threshold), 0.0),
        "annual_realized_gain_budget": max(_coerce_float(annual_realized_gain_budget), 0.0),
    }


def build_diy_sma_trade_budget_table(budget: dict[str, float]) -> pd.DataFrame:
    capital = _coerce_float(budget.get("sleeve_capital"))
    rows = [
        {
            "Sleeve Component": "Replacement long book",
            "Budget": _coerce_float(budget.get("long_notional")),
            "Exposure": _coerce_float(budget.get("long_notional")) / capital if capital else 0.0,
            "Purpose": "Hold diversified equity exposure while avoiding restricted/overlap names.",
            "Starting Rule": "Use a broad ETF, direct-index basket, or manager model only after restricted-list review.",
        },
        {
            "Sleeve Component": "Short hedge book",
            "Budget": _coerce_float(budget.get("short_notional")),
            "Exposure": _coerce_float(budget.get("actual_short_exposure")),
            "Purpose": "Offset part of market, sector, or factor exposure; create a controlled short sleeve.",
            "Starting Rule": "Begin with broad/sector hedges in paper trading; avoid single-name shorts until tax/legal review.",
        },
        {
            "Sleeve Component": "Net equity exposure",
            "Budget": _coerce_float(budget.get("net_notional")),
            "Exposure": _coerce_float(budget.get("actual_net_exposure")),
            "Purpose": "Target invested equity exposure after shorts.",
            "Starting Rule": "Keep net exposure inside written mandate limits every day.",
        },
        {
            "Sleeve Component": "Gross exposure",
            "Budget": _coerce_float(budget.get("gross_notional")),
            "Exposure": _coerce_float(budget.get("actual_gross_exposure")),
            "Purpose": "Measure leverage and operational burden from longs plus shorts.",
            "Starting Rule": "Stop adding trades if gross exposure exceeds the approved cap.",
        },
        {
            "Sleeve Component": "Unused gross capacity",
            "Budget": _coerce_float(budget.get("gross_capacity_remaining")),
            "Exposure": _coerce_float(budget.get("gross_capacity_remaining")) / capital if capital else 0.0,
            "Purpose": "Reserve for drift, margin, and implementation slippage.",
            "Starting Rule": "Do not treat unused capacity as permission to add risk without review.",
        },
    ]
    return pd.DataFrame(rows)


def build_diy_sma_guardrail_table(budget: dict[str, float], restricted_tickers: Any = None) -> pd.DataFrame:
    restricted = ", ".join(clean for clean in [str(t).strip().upper() for t in str(restricted_tickers or "").replace("\n", ",").split(",")] if clean)
    rows = [
        {
            "Limit": "Max single long",
            "Value": _coerce_float(budget.get("max_single_long_dollars")),
            "Rule": "No one replacement long should dominate the sleeve.",
        },
        {
            "Limit": "Max single short",
            "Value": _coerce_float(budget.get("max_single_short_dollars")),
            "Rule": "Avoid concentrated single-name short risk in a DIY implementation.",
        },
        {
            "Limit": "Sector cap",
            "Value": _coerce_float(budget.get("sector_cap_dollars")),
            "Rule": "Avoid recreating the same sector concentration inside the replacement book.",
        },
        {
            "Limit": "Minimum loss harvest",
            "Value": _coerce_float(budget.get("min_loss_harvest_threshold")),
            "Rule": "Do not harvest tiny losses that are not worth tax, spread, and wash-sale complexity.",
        },
        {
            "Limit": "Annual realized gain budget",
            "Value": _coerce_float(budget.get("annual_realized_gain_budget")),
            "Rule": "Stop and review before realized gains exceed the approved tax budget.",
        },
        {
            "Limit": "Restricted tickers",
            "Value": 0.0,
            "Rule": restricted or "Add concentrated holdings, close substitutes, employer stock, and any compliance-restricted tickers.",
        },
    ]
    return pd.DataFrame(rows)


def build_diy_sma_warning_flags(budget: dict[str, float], restricted_tickers: Any = None) -> pd.DataFrame:
    flags: list[dict[str, str]] = []
    if _coerce_float(budget.get("sleeve_capital")) <= 0:
        flags.append({"Severity": "Stop", "Flag": "Sleeve capital must be greater than zero before planning trades."})
    if _coerce_float(budget.get("actual_gross_exposure")) > _coerce_float(budget.get("max_gross_exposure")) + 0.0001:
        flags.append({"Severity": "Stop", "Flag": "Gross exposure exceeds the written mandate."})
    if _coerce_float(budget.get("actual_short_exposure")) > 0.30:
        flags.append({"Severity": "Review", "Flag": "Short exposure is above 30%; DIY implementation risk is elevated."})
    if _coerce_float(budget.get("annual_realized_gain_budget")) <= 0:
        flags.append({"Severity": "Review", "Flag": "No annual realized-gain budget is set."})
    restricted = str(restricted_tickers or "").strip()
    if not restricted:
        flags.append({"Severity": "Review", "Flag": "Restricted ticker list is empty."})
    if not flags:
        flags.append({"Severity": "OK", "Flag": "No automatic mandate flags triggered. Professional review is still required."})
    return pd.DataFrame(flags)


def build_diy_tax_lot_tracker_template(restricted_tickers: Any = None) -> pd.DataFrame:
    restricted = [ticker.strip().upper() for ticker in str(restricted_tickers or "").replace("\n", ",").split(",") if ticker.strip()]
    first_restricted = restricted[0] if restricted else ""
    return pd.DataFrame(
        [
            {
                "Trade Date": "",
                "Ticker": first_restricted,
                "Side": "Legacy position",
                "Shares": 0.0,
                "Price": 0.0,
                "Notional": 0.0,
                "Open Date": "",
                "Cost Basis": 0.0,
                "Current Price": 0.0,
                "Unrealized Gain/Loss": 0.0,
                "Holding Period": "Unknown",
                "Replacement Candidate": "",
                "Wash-Sale Window Start": "",
                "Wash-Sale Window End": "",
                "Harvest Candidate": "No",
                "Review Notes": "Track legacy lots separately from replacement SMA lots.",
            },
            {
                "Trade Date": "",
                "Ticker": "",
                "Side": "Buy replacement long",
                "Shares": 0.0,
                "Price": 0.0,
                "Notional": 0.0,
                "Open Date": "",
                "Cost Basis": 0.0,
                "Current Price": 0.0,
                "Unrealized Gain/Loss": 0.0,
                "Holding Period": "Unknown",
                "Replacement Candidate": "",
                "Wash-Sale Window Start": "",
                "Wash-Sale Window End": "",
                "Harvest Candidate": "No",
                "Review Notes": "Do not buy restricted or substantially identical exposure without review.",
            },
            {
                "Trade Date": "",
                "Ticker": "",
                "Side": "Short hedge",
                "Shares": 0.0,
                "Price": 0.0,
                "Notional": 0.0,
                "Open Date": "",
                "Cost Basis": 0.0,
                "Current Price": 0.0,
                "Unrealized Gain/Loss": 0.0,
                "Holding Period": "Short",
                "Replacement Candidate": "",
                "Wash-Sale Window Start": "",
                "Wash-Sale Window End": "",
                "Harvest Candidate": "No",
                "Review Notes": "Confirm borrow, margin, constructive-sale, straddle, and short-sale rules.",
            },
        ]
    )


def build_diy_paper_trading_checklist() -> pd.DataFrame:
    rows = [
        {
            "Phase": "Before paper trading",
            "Checklist Item": "Write mandate limits for net, gross, short, sector, and single-name exposure.",
            "Owner": "Investor / advisor",
            "Status": "Needed",
        },
        {
            "Phase": "Before paper trading",
            "Checklist Item": "Create restricted list covering legacy holdings, close substitutes, employer stock, and compliance restrictions.",
            "Owner": "Investor / CPA / counsel",
            "Status": "Needed",
        },
        {
            "Phase": "Paper trading",
            "Checklist Item": "Simulate every buy, short, cover, sale, and loss harvest for at least 30-60 days.",
            "Owner": "Investor",
            "Status": "Needed",
        },
        {
            "Phase": "Paper trading",
            "Checklist Item": "Track daily net exposure, gross exposure, sector exposure, borrow cost, and tracking error.",
            "Owner": "Investor",
            "Status": "Needed",
        },
        {
            "Phase": "Tax review",
            "Checklist Item": "Review wash-sale windows, straddles, constructive-sale risk, holding-period effects, and loss usability.",
            "Owner": "CPA / tax counsel",
            "Status": "Needed",
        },
        {
            "Phase": "Launch gate",
            "Checklist Item": "Do not place live trades until tax/legal review, risk limits, and stop-review rules are documented.",
            "Owner": "Investor / advisor",
            "Status": "Needed",
        },
    ]
    return pd.DataFrame(rows)


def build_sensitivity_tables(
    portfolio: pd.DataFrame,
    long_short_table: pd.DataFrame,
    loss_offset_budget: float = 0.0,
) -> dict[str, pd.DataFrame]:
    if portfolio is None or portfolio.empty:
        return {
            "tax_rate": pd.DataFrame(),
            "price_drawdown": pd.DataFrame(),
            "hedge_correlation": pd.DataFrame(),
            "loss_shortfall": pd.DataFrame(),
        }

    tax_rows: list[dict[str, Any]] = []
    base_loss_allocations = allocate_loss_offsets(portfolio, loss_offset_budget)
    for delta in [-0.05, 0.0, 0.05, 0.10]:
        total_tax = 0.0
        total_gain = 0.0
        for index, row in portfolio.iterrows():
            adjusted = row.copy()
            adjusted["gain_tax_rate"] = _clamp(_coerce_float(row.get("gain_tax_rate")) + delta, 0.0, 1.0)
            sale = estimate_sale_tax(
                adjusted,
                row.get("sale_fraction_to_target", 0.0),
                base_loss_allocations.get(int(index), 0.0),
            )
            total_tax += sale["estimated_tax"]
            total_gain += sale["realized_gain"]
        tax_rows.append(
            {
                "tax_rate_delta": delta,
                "realized_gain": total_gain,
                "estimated_tax": total_tax,
            }
        )

    drawdown_rows: list[dict[str, Any]] = []
    for drawdown in [0.0, -0.10, -0.20, -0.30]:
        adjusted_rows = []
        for _, row in portfolio.iterrows():
            adjusted = row.copy()
            adjusted["market_value"] = _coerce_float(row.get("market_value")) * (1.0 + drawdown)
            adjusted["current_price"] = _coerce_float(row.get("current_price")) * (1.0 + drawdown)
            adjusted_rows.append(adjusted)
        adjusted_portfolio = pd.DataFrame(adjusted_rows)
        drawdown_loss_allocations = allocate_loss_offsets(adjusted_portfolio, loss_offset_budget)
        for index, row in adjusted_portfolio.iterrows():
            sale = estimate_sale_tax(
                row,
                row.get("sale_fraction_to_target", 0.0),
                drawdown_loss_allocations.get(int(index), 0.0),
            )
            drawdown_rows.append(
                {
                    "ticker": row.get("ticker"),
                    "price_shock": drawdown,
                    "sale_value": sale["sale_value"],
                    "realized_gain": sale["realized_gain"],
                    "estimated_tax": sale["estimated_tax"],
                }
            )

    hedge_rows: list[dict[str, Any]] = []
    if long_short_table is not None and not long_short_table.empty:
        hedge_source = (
            long_short_table[long_short_table["hedge_type"].astype(str) != "Data unavailable"].copy()
            if "hedge_type" in long_short_table
            else pd.DataFrame()
        )
        if not hedge_source.empty:
            top_hedges = (
                hedge_source.sort_values(["ticker", "rank_score"], ascending=[True, False])
                .groupby("ticker", as_index=False)
                .head(1)
            )
            for _, row in top_hedges.iterrows():
                target_vol = _coerce_float(row.get("target_volatility"))
                proxy_vol = _coerce_float(row.get("proxy_volatility"))
                beta = _coerce_float(row.get("historical_beta"))
                base_corr = _coerce_float(row.get("historical_correlation"))
                for multiplier in [1.0, 0.75, 0.50, 0.25]:
                    stressed_corr = base_corr * multiplier
                    variance = max(
                        target_vol**2 + (beta * proxy_vol) ** 2 - 2 * beta * stressed_corr * target_vol * proxy_vol,
                        0.0,
                    )
                    tracking_error = math.sqrt(variance) if target_vol else 0.0
                    hedge_rows.append(
                        {
                            "ticker": row.get("ticker"),
                            "hedge_type": row.get("hedge_type"),
                            "proposed_hedge": row.get("proposed_hedge"),
                            "correlation_multiplier": multiplier,
                            "stressed_correlation": stressed_corr,
                            "tracking_error": tracking_error,
                            "volatility_reduction": (1.0 - tracking_error / target_vol) if target_vol else 0.0,
                        }
                    )

    total_sale_gain = 0.0
    for _, row in portfolio.iterrows():
        total_sale_gain += max(estimate_sale_tax(row, row.get("sale_fraction_to_target", 0.0))["realized_gain"], 0.0)
    loss_budget_base = max(float(loss_offset_budget), total_sale_gain)
    loss_rows: list[dict[str, Any]] = []
    for coverage in [0.0, 0.25, 0.50, 1.0]:
        offset_budget = loss_budget_base * coverage
        allocations = allocate_loss_offsets(portfolio, offset_budget)
        estimated_tax = 0.0
        loss_used = 0.0
        for index, row in portfolio.iterrows():
            sale = estimate_sale_tax(row, row.get("sale_fraction_to_target", 0.0), allocations.get(int(index), 0.0))
            estimated_tax += sale["estimated_tax"]
            loss_used += sale["loss_offset_used"]
        loss_rows.append(
            {
                "loss_offset_coverage": coverage,
                "loss_offset_budget": offset_budget,
                "loss_offset_used": loss_used,
                "remaining_unoffset_gain": max(total_sale_gain - loss_used, 0.0),
                "estimated_tax": estimated_tax,
            }
        )

    return {
        "tax_rate": pd.DataFrame(tax_rows),
        "price_drawdown": pd.DataFrame(drawdown_rows),
        "hedge_correlation": pd.DataFrame(hedge_rows),
        "loss_shortfall": pd.DataFrame(loss_rows),
    }


def long_short_research_markdown(long_short_table: pd.DataFrame) -> str:
    available_hedges = (
        long_short_table[long_short_table["hedge_type"].astype(str) != "Data unavailable"].copy()
        if long_short_table is not None and not long_short_table.empty and "hedge_type" in long_short_table
        else pd.DataFrame()
    )
    if available_hedges.empty:
        evidence = "No hedge evidence was available."
    else:
        best = available_hedges.sort_values("rank_score", ascending=False).iloc[0]
        evidence = (
            f"The highest-scored hedge candidate is {best.get('hedge_type')} using "
            f"{best.get('proposed_hedge')} with correlation {best.get('historical_correlation', 0):.2f}, "
            f"beta {best.get('historical_beta', 0):.2f}, and estimated tracking error "
            f"{best.get('tracking_error', 0):.1%} over {best.get('evidence_window', 'the available window')}."
        )

    return "\n\n".join(
        [
            f"Candidate strategies considered: market index hedge, sector hedge, peer basket hedge, pair trade, {MULTI_PROXY_HEDGE_LABEL.lower()}, and regime-aware overlay.",
            "Regime method: when daily returns are supplied, the app classifies 63-day trend and 21-day volatility regimes and evaluates hedge behavior by regime. A Markov-chain or HMM workflow remains optional because it requires daily returns, enough observations, and out-of-sample validation.",
            f"Historical evidence: {evidence}",
            "Why simpler methods may be preferable: broad rules are easier to audit, less sensitive to short samples, and less likely to overfit a single market episode. More sophisticated models should earn their place by improving out-of-sample hedge behavior after costs and taxes.",
            "Do not use the recommendation when borrow is unavailable, tax counsel flags constructive-sale or straddle issues, the hedge creates unacceptable liquidity/leverage exposure, correlations are unstable, or the investor cannot tolerate basis risk and tracking error.",
        ]
    )
