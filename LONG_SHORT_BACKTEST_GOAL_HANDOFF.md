# Long/Short ETF Sleeve Backtest Handoff

Use this document as the handoff prompt for a future `/goal`. It is designed for quantitative research on the concentrated portfolio already modeled in this repo, using the ETF universe from `LONG_SHORT_SLEEVE_RESEARCH.md`.

This work is educational research and decision support only. It is not tax, legal, investment, or trading advice. Any actual long/short, short-sale, ETF hedge, tax-loss harvesting, or concentrated-stock transition strategy must be reviewed by qualified tax counsel, a CPA, and an investment professional.

## Copy-Ready `/goal`

```text
/goal Conduct quantitative research and build a reproducible backtest for a tax-aware ETF long/short sleeve around the concentrated portfolio in this repo.

Objective:
Determine which ETF-based long/short sleeve designs best reduce the current portfolio's semiconductor/memory/storage concentration risk while preserving diversified equity exposure, controlling drawdowns, managing tax/implementation complexity, and adapting to market regimes.

Use the portfolio context and candidate universe from:
- analysis_output/tax_transition_model/cluster_exposure_summary.csv
- analysis_output/tax_transition_model/cluster_risk_weights.csv
- analysis_output/tax_transition_model/risk_proxy_correlation.csv
- LONG_SHORT_SLEEVE_RESEARCH.md

Core question:
Given the current concentrated portfolio, what ETF long/short sleeve design would have historically provided the best risk-adjusted transition support across market regimes?

Important constraints:
1. This is research only, not a trade recommendation.
2. Prefer ETF-first designs before single-stock shorts.
3. Do not hard-code one strategy as always best.
4. Compare simple rule-based regime detection against optional clustering/Markov/HMM methods if the needed libraries and data are available.
5. Use walk-forward or time-ordered validation. Do not optimize on the full history and report it as if it were out-of-sample.
6. Include realistic assumptions for borrow/carry, trading cost, rebalance frequency, slippage, and tax/implementation complexity.
7. Preserve raw data and intermediate outputs on disk under analysis_output/long_short_research/. Do not dump large API responses into chat.
8. If .env.alpaca exists, safely load it locally without printing secret values. If Alpaca is unavailable, fall back to existing local model data and clearly mark the limitation.

Research tasks:
1. Inspect the existing portfolio/model files and summarize the current concentration, embedded gain, and dominant risk exposures.
2. Build an ETF candidate universe from LONG_SHORT_SLEEVE_RESEARCH.md.
3. Load historical daily adjusted prices/returns for the portfolio tickers and ETF universe, preferably from Alpaca.
4. Construct portfolio return proxies for:
   - current concentrated portfolio basket,
   - SNDK/WDC primary basket,
   - semiconductor/memory/storage cluster basket.
5. Implement regime classification:
   - rule-based baseline using trend, realized volatility, relative strength, and rolling correlation,
   - optional clustering or HMM/Markov model as a comparison layer only.
6. Backtest multiple sleeve designs:
   - long-only broad replacement sleeve,
   - conservative ETF hedge sleeve,
   - balanced 130/30 to 150/50 ETF sleeve,
   - hedge-focused semiconductor/technology ETF overlay,
   - defensive high-volatility regime sleeve,
   - regime-switching ETF sleeve.
7. Rank strategies by:
   - volatility reduction,
   - max drawdown reduction,
   - tracking error to target exposure,
   - realized return drag or enhancement,
   - Sharpe/Sortino,
   - beta reduction,
   - correlation stability across regimes,
   - liquidity and borrow/carry risk,
   - tax/legal complexity flags,
   - turnover and implementation complexity.
8. Produce tables, charts, and a written recommendation explaining which sleeve design is most robust, when it works, when it fails, and what should be paper-traded next.
9. Add lightweight tests for core calculations where practical.
10. Run verification:
   - python3 -m compileall .
   - python3 -m unittest discover -s tests

Deliverables:
1. analysis_output/long_short_research/returns_panel.csv
2. analysis_output/long_short_research/regime_classification.csv
3. analysis_output/long_short_research/sleeve_backtest_results.csv
4. analysis_output/long_short_research/sleeve_regime_results.csv
5. analysis_output/long_short_research/candidate_etf_scores.csv
6. analysis_output/long_short_research/charts/
7. LONG_SHORT_BACKTEST_REPORT.md
8. Any reusable Python modules/tests needed for the backtest.
```

## Research Framing

The portfolio is not a generic equity account. The existing model shows a semiconductor/memory/storage concentration centered on SNDK and WDC, with additional related exposure in STX, MU, INTC, and SMCI. The backtest should therefore measure whether an ETF sleeve reduces this specific concentration risk, not merely whether an ETF strategy had attractive standalone returns.

The right unit of analysis is the daily return of the combined taxable transition sleeve and the concentrated portfolio proxy. The decision horizon should include multiple regimes, with the most recent regime analyzed separately from the full history.

## Candidate ETF Universe

Use `LONG_SHORT_SLEEVE_RESEARCH.md` as the source of truth. Initial universe:

| Role | ETFs |
| --- | --- |
| Broad equity replacement | VTI, ITOT, SPY, VOO, IVV |
| Quality replacement | QUAL, SPHQ |
| Low-volatility / defensive | USMV, SPLV |
| Value / cyclical | VTV, XLF, XLI, XLE |
| Defensive sectors | XLP, XLV, XLU |
| Small-cap / broadening | IWM, IWN, IJS, AVUV |
| Semiconductor hedge | SOXX, SMH, SOXQ |
| Tech / growth hedge | QQQ, XLK |
| Broad market hedge | SPY, IVV, VOO, IWM |
| Regime diagnostics / possible diversifiers | IEF, TLT, GLD |

Treat SPY/IVV/VOO as economically similar for exposure purposes. Avoid double-counting them as separate independent bets in optimized portfolios unless the test explicitly studies instrument substitution.

## Portfolio Proxies To Build

Build at least three target series:

| Proxy | Construction |
| --- | --- |
| Current cluster basket | Weight tickers by current market value from `cluster_exposure_summary.csv`. |
| Primary SNDK/WDC basket | Weight only SNDK and WDC by current market value. |
| Semiconductor peer basket | Weight SNDK, WDC, STX, MU, INTC, and SMCI by current market value when return data is available. |

If a ticker lacks history due to corporate action, ticker change, or data unavailability, document the issue and use the best available proxy only after labeling it clearly.

## Regime Detection Requirements

Start with interpretable rules:

| Feature | Suggested Calculation |
| --- | --- |
| Trend | SPY 63-day return, SPY above/below 100-day and 200-day moving averages. |
| Realized volatility | SPY 21-day and 63-day annualized realized volatility. |
| Semiconductor leadership | SOXX/SPY trailing 63-day relative return. |
| Growth leadership | QQQ/SPY trailing 63-day relative return. |
| Defensive leadership | USMV/SPY or XLP/SPY trailing 63-day relative return. |
| Hedge stability | Rolling 63-day correlation and beta of portfolio proxy vs SOXX, QQQ, SPY. |
| Rate sensitivity | TLT/SPY or IEF/SPY relative return and TLT drawdown. |

Minimum rule-based labels:

1. Risk-on tech/semi leadership.
2. Risk-on broadening.
3. Defensive/high-volatility risk-off.
4. Inflation/rate shock.
5. Range/transition.

Optional advanced layer:

- K-means/Gaussian mixture clustering on standardized regime features.
- HMM/Markov switching model if dependencies are available.
- Compare against rules by out-of-sample stability, predictive usefulness, and interpretability.

Do not assume the advanced model is better. It must earn its place by improving out-of-sample hedge behavior.

## Sleeve Designs To Backtest

Use long and short weights that can be explained and implemented. Avoid unconstrained optimizers that create unstable or tiny weights.

| Design | Example Net / Gross | Long Book | Short Book |
| --- | --- | --- | --- |
| Long-only replacement | 100 / 100 | VTI/ITOT plus quality or low-vol tilt | None |
| Conservative ETF hedge | 80-100 / 100-120 | Broad/quality/defensive ETFs | SPY, QQQ, or SOXX light hedge |
| Balanced ETF 130/30-150/50 | 80-100 / 130-150 | Broad, quality, value, defensive ETFs | SOXX/SMH, QQQ/XLK, SPY |
| Hedge-focused overlay | 50-90 / 100-140 | Conservative broad replacement | SOXX/SMH plus QQQ/XLK |
| Defensive regime sleeve | 50-80 / 80-130 | USMV, SPLV, XLP, XLV, XLU | SPY/QQQ/SOXX depending on regime |
| Regime-switching sleeve | Varies by rule | Long book changes by regime | Hedge ratio changes by regime |

Hard constraints to test:

- Maximum single ETF weight.
- Maximum short notional.
- Maximum gross exposure.
- Maximum semiconductor ETF short weight.
- Maximum turnover per rebalance.
- Monthly rebalance baseline; compare quarterly and threshold-based rebalances.

## Backtest Methodology

Use point-in-time daily returns and lag signals by at least one trading day. Rebalance only at the defined rebalance frequency. Include:

- Trading cost assumptions for ETFs.
- Borrow/carry assumptions for short ETF exposure.
- Slippage assumptions.
- Cash collateral return if modeled; otherwise document as omitted.
- Dividends/total return if adjusted prices are available; otherwise document price-return limitation.
- No lookahead in regime labels, hedge ratios, correlations, or optimizer inputs.

Recommended validation:

1. In-sample exploratory period.
2. Walk-forward parameter selection.
3. Out-of-sample holdout.
4. Full-period diagnostic only after the out-of-sample results are shown separately.

## Metrics

Strategy-level:

- Annualized return.
- Annualized volatility.
- Sharpe ratio.
- Sortino ratio.
- Maximum drawdown.
- Calmar ratio.
- Hit rate by month.
- Turnover.
- Estimated transaction cost.
- Estimated borrow/carry cost.

Portfolio-transition metrics:

- Volatility reduction versus concentrated basket.
- Max drawdown reduction versus concentrated basket.
- Beta to SPY, QQQ, and SOXX.
- Correlation to SNDK/WDC basket.
- Tracking error to target replacement exposure.
- Regime-by-regime performance.
- Worst regime and failure mode.

Implementation metrics:

- Average gross exposure.
- Maximum gross exposure.
- Average short exposure.
- Maximum short exposure.
- Largest ETF weight.
- Number of rebalance events.
- Tax/legal complexity flag count.

## Ranking Logic

Create a transparent score, not a black-box answer:

```text
total_score =
  25% drawdown_reduction_score
  20% volatility_reduction_score
  15% regime_stability_score
  15% implementation_simplicity_score
  10% cost_score
  10% diversification_score
   5% tax_complexity_score
```

Run sensitivity where the user can emphasize:

- Tax simplicity.
- Drawdown control.
- Diversification.
- Lower gross exposure.
- ETF-only implementation.
- Regime adaptability.

## Expected Recommendation Format

The final report should answer:

1. Which sleeve design ranked best overall?
2. Which design worked best in each regime?
3. Which ETF long candidates were most useful?
4. Which ETF short candidates were most useful?
5. What was the best ETF-only hedge for the SNDK/WDC basket?
6. How much drawdown and volatility reduction did it produce?
7. What return drag or enhancement did it create?
8. How sensitive is the answer to costs, rebalance timing, and regime definitions?
9. What should be paper-traded first?
10. What should not be implemented without professional review?

## File/Code Suggestions

Reasonable implementation shape:

```text
apps/
  long_short_backtest.py
tests/
  test_long_short_backtest.py
analysis_output/
  long_short_research/
    returns_panel.csv
    regime_classification.csv
    sleeve_backtest_results.csv
    sleeve_regime_results.csv
    candidate_etf_scores.csv
    charts/
LONG_SHORT_BACKTEST_REPORT.md
```

Keep reusable math out of the Streamlit UI first. Once the research functions are tested, add a Streamlit tab or nested Evidence section that displays the candidate rankings and backtest summary.

## Data Notes

If `.env.alpaca` exists, load only the variable names needed by the local process and never print the secret values. Expected names may include:

- `APCA_API_KEY_ID`
- `APCA_API_SECRET_KEY`
- `ALPACA_DATA_FEED`
- `ALPACA_DATA_BASE_URL`

If those values are unavailable, continue with the existing local model evidence and clearly mark the backtest as incomplete.

## Done Criteria

- Backtest code is reproducible from local files and documented data pulls.
- Candidate ETF universe matches `LONG_SHORT_SLEEVE_RESEARCH.md`.
- Rule-based regime classifier is implemented and validated.
- Optional advanced regime model is either implemented or explicitly deferred with rationale.
- Multiple sleeve designs are compared side by side.
- Results include full-period, walk-forward/out-of-sample, and regime-by-regime tables.
- Report states the recommendation, evidence, failure cases, and professional-review warnings.
- `python3 -m compileall .` passes.
- `python3 -m unittest discover -s tests` passes if tests are present.
