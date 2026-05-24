from __future__ import annotations

import unittest
from urllib.error import HTTPError

import pandas as pd

from apps.market_data import (
    MarketPrice,
    apply_market_prices_to_portfolio,
    clean_tickers,
    fetch_alpaca_latest_bars,
    fetch_alpaca_historical_bars,
    market_data_qa_frame,
)


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class MarketDataTests(unittest.TestCase):
    def test_clean_tickers_deduplicates_and_sorts(self) -> None:
        self.assertEqual(clean_tickers([" sndk ", "WDC", "sndk", "", None]), ("SNDK", "WDC"))

    def test_fetch_alpaca_latest_bars_parses_prices(self) -> None:
        calls = []

        def fake_urlopen(request, timeout):
            calls.append((request.full_url, timeout))
            return FakeResponse(
                b'{"bars":{"SNDK":{"c":72.5,"t":"2026-05-22T20:00:00Z"},"WDC":{"c":82.25,"t":"2026-05-22T20:00:00Z"}}}'
            )

        result = fetch_alpaca_latest_bars(
            ["WDC", "SNDK"],
            "key-id",
            "secret",
            feed="iex",
            timeout=3.0,
            urlopen_func=fake_urlopen,
        )

        self.assertEqual(result.status, "loaded")
        self.assertFalse(result.fallback_to_manual)
        self.assertAlmostEqual(result.prices["SNDK"].price, 72.5)
        self.assertIn("symbols=SNDK%2CWDC", calls[0][0])
        self.assertIn("feed=iex", calls[0][0])
        self.assertEqual(calls[0][1], 3.0)

    def test_fetch_alpaca_missing_credentials_returns_manual_fallback(self) -> None:
        result = fetch_alpaca_latest_bars(["SNDK"], "", "", urlopen_func=lambda *_args, **_kwargs: None)

        self.assertEqual(result.status, "manual_fallback")
        self.assertTrue(result.fallback_to_manual)
        self.assertEqual(result.prices, {})
        self.assertIn("credentials", result.message.lower())

    def test_fetch_alpaca_http_error_returns_manual_fallback(self) -> None:
        def fake_urlopen(_request, timeout):
            del timeout
            raise HTTPError("https://data.alpaca.markets", 403, "Forbidden", hdrs=None, fp=None)

        result = fetch_alpaca_latest_bars(["SNDK"], "key-id", "secret", urlopen_func=fake_urlopen)

        self.assertEqual(result.status, "manual_fallback")
        self.assertTrue(result.fallback_to_manual)
        self.assertEqual(result.missing_tickers, ("SNDK",))
        self.assertIn("HTTP 403", result.message)

    def test_apply_market_prices_updates_price_and_market_value_only(self) -> None:
        portfolio = pd.DataFrame(
            [
                {
                    "Ticker": "SNDK",
                    "Shares": 100,
                    "Current Price": 70.0,
                    "Market Value": 7000.0,
                    "Cost Basis": 3000.0,
                    "Current Weight": 0.40,
                }
            ]
        )
        prices = {"SNDK": MarketPrice("SNDK", 72.5, "2026-05-22T20:00:00Z", "Alpaca latest bars", "iex")}

        updated = apply_market_prices_to_portfolio(portfolio, prices)

        self.assertAlmostEqual(updated.loc[0, "Current Price"], 72.5)
        self.assertAlmostEqual(updated.loc[0, "Market Value"], 7250.0)
        self.assertAlmostEqual(updated.loc[0, "Cost Basis"], 3000.0)
        self.assertAlmostEqual(updated.loc[0, "Current Weight"], 0.40)

    def test_apply_market_prices_can_recompute_current_weights(self) -> None:
        portfolio = pd.DataFrame(
            [
                {"Ticker": "AAA", "Shares": 100, "Current Price": 10.0, "Market Value": 1000.0},
                {"Ticker": "BBB", "Shares": 100, "Current Price": 10.0, "Market Value": 1000.0},
            ]
        )
        prices = {
            "AAA": MarketPrice("AAA", 30.0, "", "Alpaca latest bars", "iex"),
            "BBB": MarketPrice("BBB", 10.0, "", "Alpaca latest bars", "iex"),
        }

        updated = apply_market_prices_to_portfolio(portfolio, prices, recompute_current_weights=True)

        self.assertAlmostEqual(updated.loc[0, "Current Weight"], 0.75)
        self.assertAlmostEqual(updated.loc[1, "Current Weight"], 0.25)

    def test_fetch_alpaca_historical_bars_parses_paginated_returns(self) -> None:
        calls = []

        def fake_urlopen(request, timeout):
            del timeout
            calls.append(request.full_url)
            if "page_token=next-token" in request.full_url:
                return FakeResponse(
                    b'{"bars":{"WDC":[{"c":84.0,"t":"2026-01-02T05:00:00Z"},{"c":82.0,"t":"2026-01-03T05:00:00Z"}]}}'
                )
            return FakeResponse(
                b'{"bars":{"SNDK":[{"c":70.0,"t":"2026-01-01T05:00:00Z"},{"c":77.0,"t":"2026-01-02T05:00:00Z"}],"WDC":[{"c":80.0,"t":"2026-01-01T05:00:00Z"}]},"next_page_token":"next-token"}'
            )

        result = fetch_alpaca_historical_bars(
            ["SNDK", "WDC"],
            "key-id",
            "secret",
            start="2026-01-01",
            end="2026-01-03",
            feed="iex",
            urlopen_func=fake_urlopen,
        )

        self.assertEqual(result.status, "loaded")
        self.assertEqual(result.page_count, 2)
        self.assertEqual(result.missing_tickers, ())
        self.assertIn("timeframe=1Day", calls[0])
        sndk_return = result.returns[result.returns["ticker"] == "SNDK"].iloc[0]["return"]
        wdc_returns = result.returns[result.returns["ticker"] == "WDC"]["return"].tolist()
        self.assertAlmostEqual(sndk_return, 0.10)
        self.assertAlmostEqual(wdc_returns[0], 0.05)
        self.assertAlmostEqual(wdc_returns[1], -2.0 / 84.0)

    def test_fetch_alpaca_historical_missing_credentials_returns_fallback(self) -> None:
        result = fetch_alpaca_historical_bars(["SNDK"], "", "", urlopen_func=lambda *_args, **_kwargs: None)

        self.assertEqual(result.status, "manual_fallback")
        self.assertTrue(result.returns.empty)
        self.assertEqual(result.missing_tickers, ("SNDK",))
        self.assertIn("credentials", result.message.lower())

    def test_market_data_qa_frame_summarizes_latest_and_history(self) -> None:
        latest = fetch_alpaca_latest_bars(
            ["SNDK", "MISSING"],
            "key-id",
            "secret",
            urlopen_func=lambda _request, timeout: FakeResponse(
                b'{"bars":{"SNDK":{"c":72.5,"t":"2026-01-03T20:00:00Z"}}}'
            ),
        )
        history = fetch_alpaca_historical_bars(
            ["SNDK"],
            "key-id",
            "secret",
            start="2026-01-01",
            end="2026-01-03",
            urlopen_func=lambda _request, timeout: FakeResponse(
                b'{"bars":{"SNDK":[{"c":70.0,"t":"2026-01-01T05:00:00Z"},{"c":77.0,"t":"2026-01-02T05:00:00Z"}]}}'
            ),
        )

        qa = market_data_qa_frame(latest_result=latest, historical_result=history)

        self.assertIn("Latest price", set(qa["Dataset"]))
        self.assertIn("Historical bars", set(qa["Dataset"]))
        self.assertIn("MISSING", set(qa["Ticker"]))
        sndk_history = qa[(qa["Dataset"] == "Historical bars") & (qa["Ticker"] == "SNDK")].iloc[0]
        self.assertEqual(sndk_history["Rows"], 2)


if __name__ == "__main__":
    unittest.main()
