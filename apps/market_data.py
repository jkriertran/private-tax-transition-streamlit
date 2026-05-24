from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ALPACA_DATA_BASE_URL = "https://data.alpaca.markets"
ALPACA_SUPPORTED_FEEDS = ("iex", "delayed_sip", "sip", "boats", "overnight", "otc")
ALPACA_HISTORICAL_FEEDS = ("iex", "sip", "boats", "otc")


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


@dataclass(frozen=True)
class HistoricalBarsResult:
    returns: pd.DataFrame
    bars: pd.DataFrame
    status: str
    message: str
    source: str = "Manual returns"
    feed: str = ""
    missing_tickers: tuple[str, ...] = ()
    fallback_to_manual: bool = True
    page_count: int = 0


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


def _clean_feed(feed: str | None, allowed_feeds: tuple[str, ...], default: str = "iex") -> str:
    clean_feed = str(feed or default).strip().lower()
    return clean_feed if clean_feed in allowed_feeds else default


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


def _alpaca_request(
    endpoint: str,
    query_params: dict[str, Any],
    api_key_id: str | None,
    api_secret_key: str | None,
) -> Request:
    query = urlencode({key: value for key, value in query_params.items() if value not in {None, ""}})
    return Request(
        f"{endpoint}?{query}",
        headers={
            "APCA-API-KEY-ID": str(api_key_id or "").strip(),
            "APCA-API-SECRET-KEY": str(api_secret_key or "").strip(),
            "Accept": "application/json",
        },
        method="GET",
    )


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

    clean_feed = _clean_feed(feed, ALPACA_SUPPORTED_FEEDS)

    endpoint = f"{str(base_url).rstrip('/')}/v2/stocks/bars/latest"
    request = _alpaca_request(
        endpoint,
        {"symbols": ",".join(symbols), "feed": clean_feed},
        api_key_id,
        api_secret_key,
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


def _date_value(value: date | datetime | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return parsed.date().isoformat()


def default_history_window(years: int = 3) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=max(int(years), 1) * 365)
    return start, end


def _bars_to_frames(
    bars_by_symbol: dict[str, Any],
    symbols: tuple[str, ...],
    *,
    source: str,
    feed: str,
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[str, ...]]:
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        bars = bars_by_symbol.get(symbol) or bars_by_symbol.get(symbol.upper()) or []
        if not isinstance(bars, list):
            continue
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            close = bar.get("c", 0.0)
            try:
                close_price = float(close)
            except (TypeError, ValueError):
                close_price = 0.0
            if close_price <= 0:
                continue
            rows.append(
                {
                    "date": pd.to_datetime(bar.get("t"), errors="coerce"),
                    "ticker": symbol,
                    "price": close_price,
                    "volume": float(bar.get("v", 0.0) or 0.0),
                    "source": source,
                    "feed": feed,
                }
            )

    if not rows:
        empty_bars = pd.DataFrame(columns=["date", "ticker", "price", "volume", "source", "feed"])
        empty_returns = pd.DataFrame(columns=["date", "ticker", "return"])
        return empty_bars, empty_returns, symbols

    bars = pd.DataFrame(rows).dropna(subset=["date"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    bars["return"] = bars.groupby("ticker")["price"].pct_change()
    returns = bars.loc[:, ["date", "ticker", "return"]].dropna().reset_index(drop=True)
    missing = tuple(symbol for symbol in symbols if symbol not in set(bars["ticker"]))
    return bars, returns, missing


def fetch_alpaca_historical_bars(
    tickers: Any,
    api_key_id: str | None,
    api_secret_key: str | None,
    *,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    timeframe: str = "1Day",
    feed: str = "iex",
    adjustment: str = "all",
    base_url: str = ALPACA_DATA_BASE_URL,
    limit: int = 10000,
    max_pages: int = 25,
    timeout: float = 20.0,
    urlopen_func: Callable[..., Any] | None = None,
) -> HistoricalBarsResult:
    """Fetch historical daily bars from Alpaca and convert closes into returns."""
    symbols = clean_tickers(tickers)
    if not symbols:
        return HistoricalBarsResult(
            returns=pd.DataFrame(columns=["date", "ticker", "return"]),
            bars=pd.DataFrame(columns=["date", "ticker", "price", "volume", "source", "feed"]),
            status="manual_fallback",
            message="No tickers were available for Alpaca history lookup; using uploaded or bundled returns.",
        )
    if not credentials_available(api_key_id, api_secret_key):
        return HistoricalBarsResult(
            returns=pd.DataFrame(columns=["date", "ticker", "return"]),
            bars=pd.DataFrame(columns=["date", "ticker", "price", "volume", "source", "feed"]),
            status="manual_fallback",
            message="Alpaca credentials are not configured; using uploaded or bundled returns.",
            missing_tickers=symbols,
        )

    if start is None or end is None:
        default_start, default_end = default_history_window()
        start = start or default_start
        end = end or default_end

    clean_feed = _clean_feed(feed, ALPACA_HISTORICAL_FEEDS)
    clean_timeframe = str(timeframe or "1Day").strip() or "1Day"
    clean_adjustment = str(adjustment or "all").strip().lower() or "all"
    endpoint = f"{str(base_url).rstrip('/')}/v2/stocks/bars"
    opener = urlopen_func or urlopen
    page_token = ""
    page_count = 0
    collected: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}

    try:
        while page_count < max(max_pages, 1):
            request = _alpaca_request(
                endpoint,
                {
                    "symbols": ",".join(symbols),
                    "timeframe": clean_timeframe,
                    "start": _date_value(start),
                    "end": _date_value(end),
                    "limit": max(1, min(int(limit), 10000)),
                    "adjustment": clean_adjustment,
                    "feed": clean_feed,
                    "sort": "asc",
                    "page_token": page_token,
                },
                api_key_id,
                api_secret_key,
            )
            with opener(request, timeout=timeout) as response:
                data = _read_response_json(response)
            page_count += 1
            bars = data.get("bars", {})
            if isinstance(bars, dict):
                for symbol in symbols:
                    symbol_bars = bars.get(symbol) or bars.get(symbol.upper()) or []
                    if isinstance(symbol_bars, list):
                        collected.setdefault(symbol, []).extend(symbol_bars)
            page_token = str(data.get("next_page_token") or "")
            if not page_token:
                break
    except Exception as error:
        if isinstance(error, (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError)):
            message = _safe_error_message(error).replace("manual prices", "uploaded or bundled returns")
            return HistoricalBarsResult(
                returns=pd.DataFrame(columns=["date", "ticker", "return"]),
                bars=pd.DataFrame(columns=["date", "ticker", "price", "volume", "source", "feed"]),
                status="manual_fallback",
                message=message,
                source="Alpaca historical bars",
                feed=clean_feed,
                missing_tickers=symbols,
                page_count=page_count,
            )
        raise

    bars_frame, returns, missing = _bars_to_frames(
        collected,
        symbols,
        source="Alpaca historical bars",
        feed=clean_feed,
    )
    if bars_frame.empty or returns.empty:
        return HistoricalBarsResult(
            returns=returns,
            bars=bars_frame,
            status="manual_fallback",
            message="Alpaca returned no usable historical bars; using uploaded or bundled returns.",
            source="Alpaca historical bars",
            feed=clean_feed,
            missing_tickers=missing or symbols,
            page_count=page_count,
        )

    start_label = bars_frame["date"].min().date()
    end_label = bars_frame["date"].max().date()
    message = (
        f"Loaded {len(returns):,} Alpaca daily-return rows for "
        f"{bars_frame['ticker'].nunique():,} of {len(symbols):,} tickers from {start_label} to {end_label}."
    )
    if missing:
        message += f" Uploaded or bundled returns remain needed for: {', '.join(missing)}."

    return HistoricalBarsResult(
        returns=returns,
        bars=bars_frame,
        status="loaded",
        message=message,
        source="Alpaca historical bars",
        feed=clean_feed,
        missing_tickers=missing,
        fallback_to_manual=bool(missing),
        page_count=page_count,
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


def market_data_qa_frame(
    *,
    latest_result: MarketDataResult | None = None,
    historical_result: HistoricalBarsResult | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if latest_result is not None:
        for price in latest_result.prices.values():
            rows.append(
                {
                    "Dataset": "Latest price",
                    "Ticker": price.ticker,
                    "Rows": 1,
                    "Start": price.timestamp,
                    "End": price.timestamp,
                    "Feed": price.feed,
                    "Source": price.source,
                    "Status": latest_result.status,
                }
            )
        for ticker in latest_result.missing_tickers:
            rows.append(
                {
                    "Dataset": "Latest price",
                    "Ticker": ticker,
                    "Rows": 0,
                    "Start": "",
                    "End": "",
                    "Feed": latest_result.feed,
                    "Source": latest_result.source,
                    "Status": "Manual fallback",
                }
            )

    if historical_result is not None:
        bars = historical_result.bars
        if bars is not None and not bars.empty:
            for ticker, group in bars.groupby("ticker"):
                rows.append(
                    {
                        "Dataset": "Historical bars",
                        "Ticker": ticker,
                        "Rows": len(group),
                        "Start": group["date"].min(),
                        "End": group["date"].max(),
                        "Feed": historical_result.feed,
                        "Source": historical_result.source,
                        "Status": historical_result.status,
                    }
                )
        for ticker in historical_result.missing_tickers:
            rows.append(
                {
                    "Dataset": "Historical bars",
                    "Ticker": ticker,
                    "Rows": 0,
                    "Start": "",
                    "End": "",
                    "Feed": historical_result.feed,
                    "Source": historical_result.source,
                    "Status": "Manual fallback",
                }
            )

    return pd.DataFrame(rows)
