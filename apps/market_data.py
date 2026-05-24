from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ALPACA_DATA_BASE_URL = "https://data.alpaca.markets"
ALPACA_SUPPORTED_FEEDS = ("iex", "delayed_sip", "sip", "boats", "overnight", "otc")


@dataclass(frozen=True)
class MarketPrice:
    ticker: str
    price: float
    timestamp: str
    source: str
    feed: str


@dataclass(frozen=True)
class MarketDataResult:
    prices: dict[str, MarketPrice]
    status: str
    message: str
    source: str = "Manual prices"
    feed: str = ""
    missing_tickers: tuple[str, ...] = ()
    fallback_to_manual: bool = True


def clean_tickers(tickers: Any) -> tuple[str, ...]:
    if tickers is None:
        return ()
    raw_tickers = [tickers] if isinstance(tickers, str) else list(tickers)
    cleaned_values = set()
    for ticker in raw_tickers:
        if ticker is None:
            continue
        value = str(ticker).strip()
        if not value or value.lower() == "nan":
            continue
        cleaned_values.add(value.upper())
    cleaned = sorted(cleaned_values)
    return tuple(cleaned)


def credentials_available(api_key_id: str | None, api_secret_key: str | None) -> bool:
    return bool(str(api_key_id or "").strip() and str(api_secret_key or "").strip())


def _safe_error_message(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"Alpaca returned HTTP {error.code}; using manual prices."
    if isinstance(error, URLError):
        return "Could not reach Alpaca market data; using manual prices."
    return "Alpaca market data could not be loaded; using manual prices."


def _read_response_json(response: Any) -> dict[str, Any]:
    payload = response.read()
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    data = json.loads(payload or "{}")
    return data if isinstance(data, dict) else {}


def fetch_alpaca_latest_bars(
    tickers: Any,
    api_key_id: str | None,
    api_secret_key: str | None,
    *,
    feed: str = "iex",
    base_url: str = ALPACA_DATA_BASE_URL,
    timeout: float = 10.0,
    urlopen_func: Callable[..., Any] | None = None,
) -> MarketDataResult:
    """Fetch latest bar close prices from Alpaca's stock market-data API.

    This function intentionally returns a fallback result instead of raising
    for missing credentials, network errors, authorization errors, rate limits,
    malformed responses, or missing symbols. The Streamlit app can then keep
    using manual/uploaded prices without interrupting the analysis.
    """
    symbols = clean_tickers(tickers)
    if not symbols:
        return MarketDataResult(
            prices={},
            status="manual_fallback",
            message="No tickers were available for Alpaca lookup; using manual prices.",
        )
    if not credentials_available(api_key_id, api_secret_key):
        return MarketDataResult(
            prices={},
            status="manual_fallback",
            message="Alpaca credentials are not configured; using manual prices.",
            missing_tickers=symbols,
        )

    clean_feed = str(feed or "iex").strip().lower()
    if clean_feed not in ALPACA_SUPPORTED_FEEDS:
        clean_feed = "iex"

    endpoint = f"{str(base_url).rstrip('/')}/v2/stocks/bars/latest"
    query = urlencode({"symbols": ",".join(symbols), "feed": clean_feed})
    request = Request(
        f"{endpoint}?{query}",
        headers={
            "APCA-API-KEY-ID": str(api_key_id or "").strip(),
            "APCA-API-SECRET-KEY": str(api_secret_key or "").strip(),
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        opener = urlopen_func or urlopen
        with opener(request, timeout=timeout) as response:
            data = _read_response_json(response)
    except Exception as error:
        if isinstance(error, (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError)):
            return MarketDataResult(
                prices={},
                status="manual_fallback",
                message=_safe_error_message(error),
                source="Alpaca latest bars",
                feed=clean_feed,
                missing_tickers=symbols,
            )
        raise

    bars = data.get("bars", {})
    if not isinstance(bars, dict):
        bars = {}

    prices: dict[str, MarketPrice] = {}
    for symbol in symbols:
        bar = bars.get(symbol) or bars.get(symbol.upper()) or {}
        if not isinstance(bar, dict):
            continue
        try:
            close_price = float(bar.get("c", 0.0))
        except (TypeError, ValueError):
            close_price = 0.0
        if close_price <= 0:
            continue
        prices[symbol] = MarketPrice(
            ticker=symbol,
            price=close_price,
            timestamp=str(bar.get("t", "")),
            source="Alpaca latest bars",
            feed=clean_feed,
        )

    missing = tuple(symbol for symbol in symbols if symbol not in prices)
    if not prices:
        return MarketDataResult(
            prices={},
            status="manual_fallback",
            message="Alpaca returned no usable latest-bar prices; using manual prices.",
            source="Alpaca latest bars",
            feed=clean_feed,
            missing_tickers=missing,
        )

    message = f"Loaded Alpaca latest-bar prices for {len(prices):,} of {len(symbols):,} tickers."
    if missing:
        message += f" Manual prices remain for: {', '.join(missing)}."
    return MarketDataResult(
        prices=prices,
        status="loaded",
        message=message,
        source="Alpaca latest bars",
        feed=clean_feed,
        missing_tickers=missing,
        fallback_to_manual=bool(missing),
    )


def _canonical_column(column: Any) -> str:
    return (
        str(column)
        .strip()
        .lower()
        .replace("%", "pct")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


def _find_column(frame: pd.DataFrame, aliases: set[str]) -> str | None:
    for column in frame.columns:
        if _canonical_column(column) in aliases:
            return str(column)
    return None


def _numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0.0)


def apply_market_prices_to_portfolio(
    portfolio: pd.DataFrame,
    prices: dict[str, MarketPrice],
    *,
    recompute_current_weights: bool = False,
) -> pd.DataFrame:
    """Overlay fetched prices on an editable portfolio input.

    Cost basis and tax-rate columns are deliberately left unchanged. When a
    market-value column exists, it is updated as shares times latest price so
    downstream tax-dollar calculations use one coherent price snapshot.
    """
    if portfolio is None or portfolio.empty or not prices:
        return portfolio.copy() if portfolio is not None else pd.DataFrame()

    frame = portfolio.copy()
    ticker_column = _find_column(frame, {"ticker", "symbol", "security"})
    if ticker_column is None:
        return frame

    price_column = _find_column(frame, {"current_price", "price", "last_price", "market_price"})
    if price_column is None:
        price_column = "Current Price"
        frame[price_column] = 0.0

    shares_column = _find_column(frame, {"shares", "quantity", "qty"})
    market_value_column = _find_column(frame, {"market_value", "current_value", "value", "mv"})

    ticker_values = frame[ticker_column].astype(str).str.strip().str.upper()
    for row_index, ticker in ticker_values.items():
        market_price = prices.get(ticker)
        if market_price is None:
            continue
        frame.loc[row_index, price_column] = market_price.price

    if market_value_column is not None and shares_column is not None:
        shares = _numeric_series(frame[shares_column])
        prices_series = _numeric_series(frame[price_column])
        updated_rows = ticker_values.isin(prices)
        frame.loc[updated_rows, market_value_column] = shares[updated_rows] * prices_series[updated_rows]

    if recompute_current_weights:
        current_weight_column = _find_column(frame, {"current_weight", "current_portfolio_weight", "portfolio_weight"})
        if current_weight_column is None:
            current_weight_column = "Current Weight"
            frame[current_weight_column] = 0.0
        if market_value_column is None:
            market_value_column = "Market Value"
            if shares_column is not None:
                frame[market_value_column] = _numeric_series(frame[shares_column]) * _numeric_series(frame[price_column])
            else:
                frame[market_value_column] = 0.0
        market_values = _numeric_series(frame[market_value_column])
        total_market_value = float(market_values.sum())
        if total_market_value > 0:
            frame[current_weight_column] = market_values / total_market_value

    return frame


def market_prices_to_frame(prices: dict[str, MarketPrice]) -> pd.DataFrame:
    rows = [
        {
            "Ticker": price.ticker,
            "Price": price.price,
            "Timestamp": price.timestamp,
            "Feed": price.feed,
            "Source": price.source,
        }
        for price in prices.values()
    ]
    return pd.DataFrame(rows).sort_values("Ticker").reset_index(drop=True) if rows else pd.DataFrame()
