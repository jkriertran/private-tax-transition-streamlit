# Long/Short Sleeve Candidate Research

This note is educational research for designing a taxable long/short sleeve around the current concentrated stock portfolio. It is not tax, legal, investment, or trading advice. Any actual short sale, ETF hedge, pair trade, tax-loss harvest, or concentrated-stock transition should be reviewed by qualified tax counsel, a CPA, and an investment professional.

## Decision Question

Which sectors, ETFs, and possible stock baskets should be considered for a long/short sleeve that reduces semiconductor and memory/storage concentration risk while preserving a transparent tax-aware implementation path?

The answer should not be a single ticker. The better structure is a regime-aware candidate framework:

1. Classify the market regime.
2. Identify what the portfolio already owns and what risks dominate.
3. Build a candidate universe by role: replacement long, sector hedge, market hedge, factor diversifier, defensive sleeve, and peer basket.
4. Score each candidate by regime, correlation, beta, liquidity, borrow risk, tax complexity, tracking error, and overlap with restricted names.

## Current Portfolio Context

The local model data is dated through May 15, 2026. It shows a broad semiconductor/memory/storage concentration, not just a single-stock problem.

| Holding | Role | Modeled Account Weight | Embedded Gain / Value | Comment |
| --- | ---: | ---: | ---: | --- |
| SNDK | Primary memory/storage exposure | 42.5% | 99.2% | Main tax-transition position. |
| WDC | Primary memory/storage exposure | 40.0% | 98.5% | Main tax-transition position. |
| STX | Storage peer exposure | 5.3% | 100.0% | Should likely be on the restricted/review list. |
| MU | Memory peer exposure | 4.3% | 97.3% | Should likely be on the restricted/review list. |
| INTC | Semiconductor factor exposure | 1.5% | 83.2% | Smaller but same broad factor cluster. |
| SMCI | AI hardware factor exposure | 0.0% | -5.1% | Small position, still relevant to restrictions. |

The modeled cluster is roughly 93.6% of account value. That means the sleeve should be designed first as a risk and transition-control system, not as an alpha-only long/short trade.

## Existing Hedge Evidence From The App

The app already has proxy evidence for the concentrated basket through May 15, 2026:

| Target | Candidate | Historical Correlation | Beta To Candidate | Interpretation |
| --- | ---: | ---: | ---: | --- |
| SNDK/WDC basket | STX | 0.78 | 0.84 | Strong peer hedge, but single-stock and tax/borrow complexity are high. |
| SNDK/WDC basket | MU | 0.76 | 0.76 | Strong peer hedge, but single-stock and tax/borrow complexity are high. |
| SNDK/WDC basket | SOXX | 0.67 | 1.10 | Best ETF-style sector hedge in the current model data. |
| SNDK/WDC basket | QQQ | 0.57 | 1.70 | Broader growth/tech hedge, less precise but simpler than peer shorts. |
| SNDK/WDC basket | SPY | 0.54 | 1.96 | Broad market hedge; lowest precision among available proxies. |

Interpretation: peer stocks track the risk more closely, but ETFs are cleaner starting points for a taxable DIY/SMA framework. The first-cut sleeve should be ETF-first, with single-name shorts considered only as a diversified basket and only after tax/legal and borrow review.

## Regime Framework

Start with simple rules. Use Markov chains or hidden Markov models only as a second layer if they improve out-of-sample behavior and remain stable.

### Primary Rule-Based Regime Classifier

Use these features:

| Feature | Example Measurement | Why It Matters |
| --- | --- | --- |
| Market trend | SPY 63-day return and 100/200-day moving average state | Determines whether a short book should be defensive or aggressively hedged. |
| Volatility | VIX, 21-day realized volatility, 63-day realized volatility | Cboe describes VIX as 30-day expected S&P 500 volatility implied by SPX options. |
| Tech/semi leadership | QQQ/SPY and SOXX/SPY relative strength | Determines whether the concentrated risk factor is leading or breaking down. |
| Correlation regime | Rolling 63-day correlation of portfolio basket vs SOXX, QQQ, SPY | Identifies whether a hedge is still tracking the actual concentration. |
| Rate/liquidity proxy | TLT or IEF trend, HYG/IEF spread proxy where data is available | Helps separate rate-shock regimes from ordinary equity selloffs. |
| Breadth | Equal-weight market vs cap-weight market, sector participation | Distinguishes tech-only leadership from broad participation. |

### Suggested Regime Labels

| Regime | Conditions | Sleeve Implication |
| --- | --- | --- |
| Risk-on, tech/semi leadership | Trend up, volatility normal/low, QQQ and SOXX outperform | Avoid over-shorting the strongest factor; use smaller sector hedge and broaden long book. |
| Risk-on broadening | Trend up, volatility normal, non-tech sectors participate | Use more value/cyclical/quality longs and keep semis/QQQ shorts as concentration reducers. |
| Defensive or high-volatility risk-off | Trend down or unstable, volatility high, correlations rising | Reduce gross exposure, favor defensive/min-vol longs, and use broad/sector ETF hedges. |
| Inflation/rate shock | Rates rising, duration assets weak, tech multiple pressure | Do not rely on TLT as a diversifier; consider value, financials, energy, and lower-duration equity. |
| Transition/range | Mixed trend, unstable correlations, no clear leadership | Keep gross lower, paper trade, and focus on tax-lot harvesting and restricted-list controls. |

### Markov Or HMM Layer

A Markov or hidden Markov model can classify latent states from SPY returns, realized volatility, VIX, SOXX/SPY, QQQ/SPY, TLT returns, and rolling correlation. It should be treated as a validation layer, not the default answer.

Use it only if:

- It is trained and tested on time-ordered splits.
- Regime labels are stable across reasonable parameter choices.
- It improves volatility reduction, drawdown reduction, and hedge tracking after costs.
- It does not merely label high volatility after the damage has already occurred.

The rule-based classifier should remain the governance layer because it is easier to explain to a user, CPA, counsel, and investment committee.

## ETF Candidate Universe

### Best First-Cut ETF Candidates

| Role | Candidate ETFs | Why They Belong In The Screen | Main Caution |
| --- | --- | --- | --- |
| Broad equity replacement long | VTI, ITOT, SPY, VOO, IVV | Keeps diversified equity exposure while reducing single-name concentration. | Broad indexes still contain technology and semiconductor exposure. |
| Quality replacement long | QUAL, SPHQ | Quality factor can preserve equity exposure with a more balanced fundamental screen. | Look-through overlap with mega-cap tech and semiconductor equipment names must be checked. |
| Low-volatility/defensive long | USMV, SPLV | Useful in high-volatility or defensive regimes. | Can lag in strong risk-on rallies and may load on utilities/staples/health care. |
| Value/cyclical long | VTV, XLF, XLI, XLE | Useful if market leadership broadens away from long-duration growth and semis. | Sector cyclicality can hurt in recessions or commodity shocks. |
| Defensive sector long | XLP, XLV, XLU | Diversifies away from semiconductor cyclicality and AI hardware beta. | These are not precise hedges; they are replacement/diversification sleeves. |
| Small-cap/risk broadening long | IWM, IWN, IJS | Useful if risk-on broadens beyond mega-cap tech. | Higher beta and credit sensitivity can be painful in risk-off regimes. |
| Semiconductor ETF short hedge | SOXX, SMH, SOXQ | Most direct ETF hedge for the semiconductor factor in the local model. | Higher tax/legal review burden because it is closer to the concentrated risk factor. |
| Tech/growth ETF short hedge | QQQ, XLK | Less narrow than semiconductor ETFs while still reducing tech/growth beta. | Still concentrated in mega-cap growth; may not track memory/storage idiosyncratic risk. |
| Broad market ETF short hedge | SPY, IVV, VOO, IWM | Useful for beta control and high-volatility regimes. | Lowest precision for the memory/storage concentration. |
| Non-equity diversifier research | IEF, TLT, GLD | Helpful regime diagnostics and possible diversifiers outside the equity sleeve. | Tax treatment, income taxation, and mandate fit differ from an equity long/short SMA. |

### Stock Candidates If ETFs Are Not Enough

Use stock shorts only as baskets, not as a one-name pair trade, unless the mandate explicitly allows pair-trade risk.

Candidate research basket:

- Storage/memory peers: STX, MU.
- Broad semiconductors: AMD, NVDA, AVGO, INTC, TXN, MCHP, ON, MRVL.
- Semiconductor equipment: LRCX, AMAT, KLAC, ASML.
- AI hardware/server supply chain: SMCI and related hardware names, if liquid and borrowable.

Why not start here: the existing model shows STX and MU track the SNDK/WDC basket better than ETFs, but that also makes them more tax-sensitive and operationally risky. A single-name peer short can create concentrated short-squeeze, borrow, recall, and tax-rule issues. A basket is better than a pair trade.

## Preliminary Candidate Ranking

### For The Short/Hedge Book

1. SOXX or SMH: best ETF candidates for semiconductor factor hedging.
2. QQQ or XLK: broader growth/technology hedge when direct semiconductor hedging is too tax-sensitive.
3. SPY or IVV: broad beta hedge when the goal is drawdown reduction rather than sector precision.
4. IWM: useful when small-cap beta is a relevant risk, but not a primary hedge for this specific memory/storage concentration.
5. Peer-stock basket: only after ETF hedges are tested and after tax/legal/borrow review.

### For The Long/Replacement Book

1. VTI, ITOT, SPY, VOO, or IVV: broad equity replacement.
2. QUAL or SPHQ: quality tilt for a more resilient replacement book.
3. USMV or SPLV: defensive/min-vol tilt for high-volatility regimes.
4. XLP, XLV, XLU: defensive sector ballast.
5. XLF, XLI, XLE, VTV: cyclical/value diversifiers if leadership broadens or inflation/rates dominate.
6. IWM, IWN, IJS, or AVUV: optional small/value sleeve if the regime supports risk broadening and liquidity is acceptable.

## Regime-Conditional Sleeve Templates

These are research templates, not trade instructions.

| Regime | Long Book Tilt | Short Book Tilt | Gross/Net Guidance |
| --- | --- | --- | --- |
| Risk-on, tech/semi leadership | Broad equity plus quality; avoid excessive defensive drag | Light SOXX/SMH, more QQQ/XLK or SPY beta hedge | Keep hedge modest; do not fight strong trend too aggressively. |
| Risk-on broadening | Add VTV, XLF, XLI, IWM/IWN | SOXX/SMH plus QQQ/XLK | Better time to reduce concentration while keeping equity participation. |
| Defensive/high vol | USMV/SPLV, XLP, XLV, XLU; consider lower gross | SPY/QQQ plus smaller SOXX/SMH | Reduce gross and prioritize drawdown control. |
| Inflation/rate shock | XLE, XLF, VTV, shorter-duration equity | QQQ/XLK/SOXX if trend is broken | Avoid assuming bonds hedge equity; verify TLT/IEF behavior. |
| Range/transition | Balanced quality/core long book | ETF hedges only, no single-name shorts | Paper trade and prioritize tracking-error diagnostics. |

## Candidate Scoring Logic To Add To The App

Each candidate should receive regime-specific scores:

| Score | What To Measure |
| --- | --- |
| Diversification benefit | Negative or low overlap with SNDK/WDC/STX/MU and semiconductor factor. |
| Hedge effectiveness | Rolling correlation, beta, tracking error, volatility reduction, drawdown reduction. |
| Stability | Correlation and beta stability across regimes. |
| Liquidity | Volume, bid/ask spread, assets, borrow availability, short interest where available. |
| Tax complexity | Constructive-sale, straddle, wash-sale, holding-period, and short-against-the-box review flags. |
| Implementation complexity | Number of positions, rebalancing frequency, borrow management, margin burden. |
| Regime fit | Historical performance by rule-based regime and optional HMM regime. |
| User fit | Preference for ETF-only, max gross exposure, max short exposure, tax budget, and simplicity. |

## Implementation Recommendation

Start ETF-first:

1. Build a candidate universe from broad market, sector, factor, defensive, and semiconductor ETFs.
2. Add ETF holdings look-through so the app flags overlap with SNDK/WDC/STX/MU and close substitutes.
3. Use a rule-based regime classifier as the default.
4. Add an optional HMM/Markov layer only as a comparison model.
5. For each regime, rank long candidates and short candidates separately.
6. Assemble candidate sleeves from:
   - Long replacement book: broad equity, quality, low-vol, defensive/value/cyclical ETFs.
   - Short hedge book: SOXX/SMH, QQQ/XLK, SPY, and only later peer baskets.
7. Paper trade the recommended sleeve for 30 to 60 days before treating it as implementation-ready.

## Professional Review Flags

- Shorting an ETF or peer stock while holding appreciated concentrated stock may raise constructive-sale, straddle, wash-sale, short-sale, and holding-period questions.
- ETF hedges can still be tax-sensitive if the ETF is economically close to the concentrated position.
- Borrow availability and costs can change quickly.
- Peer baskets may be better hedges statistically but worse implementation choices operationally.
- The sleeve should never trade a restricted ticker without explicit approval.

## Sources

- Cboe VIX FAQ: https://www.cboe.com/tradable_products/vix/faqs
- State Street Select Sector SPDR ETF sector list: https://www.ssga.com/us/en/intermediary/capabilities/equities/sector-investing/select-sector-etfs
- iShares Semiconductor ETF SOXX: https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf
- VanEck Semiconductor ETF SMH: https://www.vaneck.com/us/en/investments/semiconductor-etf-smh/
- Invesco QQQ ETF: https://www.invesco.com/qqq-etf/en/about.html
- iShares Russell 2000 ETF IWM: https://www.ishares.com/us/products/239710/ishares-russell-2000-etf
- iShares MSCI USA Quality Factor ETF QUAL: https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf
- iShares MSCI USA Min Vol Factor ETF USMV: https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf
- Invesco S&P 500 Low Volatility ETF SPLV: https://www.invesco.com/us/en/financial-products/etfs/invesco-sp-500-low-volatility-etf.html
- Vanguard Value ETF VTV: https://advisors.vanguard.com/investments/products/vtv/vanguard-value-etf
- IRS Publication 550: https://www.irs.gov/publications/p550
- SEC Regulation SHO investor publication: https://www.sec.gov/investor/pubs/regsho.htm
