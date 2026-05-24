# Tax-Efficient Transition Strategy Framework

This Streamlit app is an educational decision-support model for concentrated stock transition analysis. It is not tax, legal, or investment advice. Any actual transition plan should be reviewed by a qualified CPA or tax counsel and an investment professional.

## Strategy Framework

The app compares eight strategy families:

- Sell immediately to the target weight.
- Sell gradually across multiple tax years.
- Harvest losses to offset realized gains.
- Use a long/short overlay.
- Use a peer basket hedge or pair-trade concept.
- Hold and monitor.
- Donate appreciated shares to a charity or donor-advised fund when charitable intent exists.
- Evaluate exchange fund or direct-indexing transition alternatives when the position size and embedded gain make those paths plausible.

The recommendation engine is assumption-driven. It scores each strategy using user-selected priorities for tax cost, concentration-risk reduction, diversification benefit, implementation complexity, liquidity/borrow risk, time horizon, and tax-rule uncertainty. No strategy is hard-coded as always best.

## Tax Concepts Considered

The app models realized gain using proportional basis: sale value minus the same fraction of total cost basis. This is intentionally simpler than lot-level optimization. The bundled advisor-only lot view remains separate when those files are available.

The tax estimate applies a combined modeled rate:

- Long-term positions use federal long-term capital gain rate, NIIT rate, and state tax rate inputs.
- Short-term positions use federal short-term/ordinary rate, NIIT rate, and state tax rate inputs.
- Unknown holding periods are treated as long-term assumed pending lot review and flagged in the normalized portfolio.

Loss harvesting is modeled as an offset budget allocated pro rata to gains from sales down to target. The model does not decide whether a loss is valid, same-character, currently usable, or deferred.

Relevant tax concepts flagged for professional review include constructive-sale rules, wash-sale rules, straddle rules, short-against-the-box concerns, holding-period effects, capital gain/loss netting, charitable contribution limits/substantiation, and exchange-fund eligibility.

## Long/Short Transition Logic

The app does not treat long/short as a single generic answer. For each ticker with available proxy evidence, it compares:

- Market index hedge: short broad ETFs such as SPY, QQQ, or IWM where available.
- Sector hedge: short sector or industry ETFs such as SOXX where available.
- Peer basket hedge: short a diversified basket of similar companies.
- Pair trade: short one highly correlated peer.
- Multi-proxy hedge: combine available market and sector proxies when true factor-return data is not supplied.
- Regime-aware overlay: use transparent rule-based regime logic as a governance layer rather than assuming a Markov or HMM model is superior.

For each candidate, the engine estimates beta hedge ratio, hedge notional, historical correlation, beta, annualized tracking error, volatility reduction, drawdown impact, liquidity score, borrow score, tax simplicity, implementation simplicity, data limitations, and tax/legal risk flags. Drawdown impact is calculated from daily returns when complete daily data is supplied; otherwise it is labeled as a heuristic proxy based on modeled volatility reduction.

The app accepts optional daily return or price data in long or wide CSV format. When daily returns are supplied, the regime module classifies market regimes using a 63-day trend rule and 21-day realized-volatility threshold, then evaluates each hedge by volatility reduction, drawdown change, and correlation within each regime. When daily returns are absent, the app clearly falls back to the bundled summary proxy evidence.

The app intentionally labels the former factor placeholder as a multi-proxy hedge unless true factor-return data is supplied. A production factor hedge should regress the concentrated position against explicit market, sector, size, value, growth, momentum, quality, and volatility factor returns, then build a hedge from those measured exposures.

If daily return histories and suitable libraries are later added, the framework can be extended to compare rolling beta/correlation regimes and optional Markov or Hidden Markov Models. Those more advanced methods should be used only if they improve out-of-sample hedge behavior after taxes, borrow, costs, and implementation constraints. The regime-aware overlay is displayed as a policy framework; its headline beta, correlation, tracking-error, and drawdown metrics come from the highest-ranked base hedge unless a separately validated dynamic trading rule is added.

## Scenario and Assumption Controls

The Strategy Lab exposes user-adjustable priority weights, gradual-sale horizon, decision horizon, available loss offsets, charitable-intent flag, annual borrow/carry cost, liquidity requirement, and tax-complexity tolerance.

Sensitivity tables show:

- Tax-rate shocks against the sale-to-target plan, carrying through the entered harvested-loss budget.
- Price drawdowns and their effect on sale value, realized gain, and estimated tax while keeping sale fractions fixed.
- Hedge correlation breakdowns and the resulting tracking-error/volatility-reduction impact.
- Loss-harvest shortfall scenarios showing how much gain remains unoffset.

## One-Page Transition Plan Builder

The app includes a fillable Transition Plan tab that turns model output into an implementation-ready draft. The builder pre-fills current weight, target weight, estimated sale value, realized gain, estimated tax, tax budget, selected strategy, top hedge evidence, and position-level actions from the analysis engine.

The user can fill in decision owner, decision status, chosen strategy, maximum tax budget, completion window, hedge permission, objective, execution rules, professional-review checklist, and implementation milestones. The preview is deliberately kept inside the app and is meant for review discussions, not as a trade authorization.

## Important Limitations

- This is not personalized advice.
- The app does not select tax lots unless a separate lot-level workflow is added.
- Sensitivity tables are scenario diagnostics and do not recompute a full tax plan, target allocation, or lot selection after every shock.
- The app does not verify borrow availability, rebate/carry, margin requirements, liquidity, or short-sale constraints.
- The app does not determine whether two securities are substantially identical.
- The app does not determine whether a hedge creates a constructive sale, straddle, wash sale, or holding-period issue.
- Historical correlation and beta can fail, especially during issuer-specific events.
- Exchange funds, collars, prepaid variable forwards, and charitable transfers require separate legal/tax analysis.

## Professional-Review Warnings

Do not implement any short, option, collar, exchange-fund, charitable-transfer, or concentrated-position transition plan solely from this app. Review the facts, lot history, holding periods, securities involved, account type, margin/borrow terms, tax year, loss carryovers, state tax rules, and investment-policy constraints with qualified professionals.

References consulted for general tax concepts:

- IRS Publication 550, Investment Income and Expenses: https://www.irs.gov/publications/p550
- IRS Publication 544, Sales and Other Dispositions of Assets: https://www.irs.gov/publications/p544
- IRS Topic 409, Capital Gains and Losses: https://www.irs.gov/taxtopics/tc409
