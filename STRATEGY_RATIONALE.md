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

## Long/Short SMA Study Logic

The SMA Study tab compares four implementation designs side by side:

- Conservative tax-aware equity SMA: broad long-only or mostly long direct-indexing style portfolio with a tightly governed hedge sleeve.
- Balanced diversified 130/30-150/50 SMA: diversified tax-aware long/short portfolio intended to balance loss-harvesting capacity, concentration transition, and implementability.
- Hedge-focused transition overlay: a targeted overlay around the concentrated position while the legacy position is sold, donated, or otherwise reduced over time.
- Aggressive market/factor-neutral long/short SMA: high-gross active long/short mandate where alpha, factor neutrality, and harvest capacity are primary objectives.

The SMA comparison uses separate criteria from the sale/hold strategy engine: tax-loss capacity, concentration-transition fit, risk control, tax-rule clarity, implementation simplicity, liquidity/borrow safety, cost efficiency, manager operational quality, and diversification benefit. The model adjusts the fit scores using the analyzed portfolio's embedded gain, excess concentration, sale-to-target gain, and available long/short hedge evidence.

The output is meant to frame manager due diligence, not to select a manager automatically. A balanced diversified SMA may rank highest when the account has large embedded gain and significant excess concentration because it provides a broader implementation path than a single hedge and more tax-loss potential than a conservative direct-indexing sleeve. A conservative design can rank highest when the user's priorities heavily favor tax-rule clarity, simplicity, liquidity, and cost. A hedge-focused overlay can fit near-term concentration control but carries higher constructive-sale, straddle, wash-sale, short-against-the-box, and restricted-list review needs. An aggressive design requires the strongest manager diligence because its high gross exposure can create substantial tracking, borrow, margin, tax, and operational risk.

## DIY SMA Builder Logic

The DIY SMA Builder tab is a pre-trade worksheet for turning an SMA concept into written operating limits. It does not select securities or authorize trades. It asks for sleeve capital, target net exposure, maximum gross exposure, maximum short exposure, single-name limits, sector caps, minimum loss-harvest threshold, annual realized-gain budget, and restricted tickers.

The exposure math uses standard long/short definitions:

- Net exposure equals long notional minus short notional.
- Gross exposure equals long notional plus short notional.
- Short budget is capped by both the user-entered short limit and the remaining gross exposure capacity implied by the target net exposure.
- Long budget is the target net exposure plus the permitted short budget.

The tab then converts those limits into dollar budgets, guardrails, automatic stop/review flags, an editable tax-lot tracker, and a paper-trading checklist. The tax-lot tracker is intentionally a worksheet, not a broker book of record. Before any live implementation, actual tax lots, wash-sale windows, constructive-sale or straddle exposure, short-borrow terms, margin rules, and restricted-list issues should be reviewed with qualified professionals.

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
