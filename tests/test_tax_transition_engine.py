from __future__ import annotations

import unittest

import pandas as pd

from apps.tax_transition_engine import (
    MULTI_PROXY_HEDGE_LABEL,
    allocate_loss_offsets,
    build_sma_due_diligence_checklist,
    build_diy_paper_trading_checklist,
    build_diy_sma_exposure_budget,
    build_diy_sma_trade_budget_table,
    build_diy_sma_warning_flags,
    build_diy_tax_lot_tracker_template,
    build_transition_plan_summary,
    build_sensitivity_tables,
    analyze_long_short_candidates,
    evaluate_sma_designs,
    estimate_sale_tax,
    normalize_return_frame,
    normalize_portfolio_frame,
    run_transition_analysis,
    score_strategies_for_position,
)


class TaxTransitionEngineTests(unittest.TestCase):
    def test_normalize_portfolio_aliases_and_tax_treatment(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Symbol": "abc",
                    "Quantity": 100,
                    "Current Price": 50,
                    "Cost Basis": 3000,
                    "Holding Period": "Short Term",
                    "Current Weight": "25%",
                    "Target Weight": 0.10,
                    "Federal ST Rate": 0.40,
                    "State Tax Rate": 0.05,
                    "NIIT Rate": 0.038,
                }
            ]
        )

        normalized = normalize_portfolio_frame(raw)

        self.assertEqual(normalized.loc[0, "ticker"], "ABC")
        self.assertAlmostEqual(normalized.loc[0, "market_value"], 5000)
        self.assertAlmostEqual(normalized.loc[0, "unrealized_gain"], 2000)
        self.assertEqual(normalized.loc[0, "holding_period"], "Short Term")
        self.assertAlmostEqual(normalized.loc[0, "gain_tax_rate"], 0.488)
        self.assertAlmostEqual(normalized.loc[0, "sale_fraction_to_target"], 0.6)

    def test_percent_strings_below_one_are_percent_not_decimal(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Ticker": "ABC",
                    "Shares": 100,
                    "Current Price": 100,
                    "Cost Basis": 5000,
                    "Current Weight": "0.5%",
                    "Target Weight": "0.1%",
                    "Federal LTCG Rate": "20%",
                }
            ]
        )

        normalized = normalize_portfolio_frame(raw)

        self.assertAlmostEqual(normalized.loc[0, "current_weight"], 0.005)
        self.assertAlmostEqual(normalized.loc[0, "target_weight"], 0.001)
        self.assertAlmostEqual(normalized.loc[0, "federal_long_term_rate"], 0.20)

    def test_wide_return_percent_strings_are_decimal_returns(self) -> None:
        returns = normalize_return_frame(
            pd.DataFrame(
                {
                    "date": ["2024-01-01", "2024-01-02"],
                    "AAA": ["1%", "2%"],
                    "BBB": ["0.5%", "-1%"],
                }
            )
        )

        aaa = returns[returns["ticker"] == "AAA"].sort_values("date")["return"].tolist()
        bbb = returns[returns["ticker"] == "BBB"].sort_values("date")["return"].tolist()
        self.assertEqual(aaa, [0.01, 0.02])
        self.assertEqual(bbb, [0.005, -0.01])

    def test_estimate_sale_tax_applies_loss_offset(self) -> None:
        position = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "XYZ",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 2000,
                        "Holding Period": "Long Term",
                        "Current Weight": 0.30,
                        "Target Weight": 0.10,
                        "Federal LTCG Rate": 0.20,
                        "NIIT Rate": 0.038,
                        "State Tax Rate": 0.00,
                    }
                ]
            )
        ).iloc[0]

        sale = estimate_sale_tax(position, sale_fraction=0.5, loss_offset=1000)

        self.assertAlmostEqual(sale["sale_value"], 5000)
        self.assertAlmostEqual(sale["realized_gain"], 4000)
        self.assertAlmostEqual(sale["loss_offset_used"], 1000)
        self.assertAlmostEqual(sale["estimated_tax"], 714)

    def test_allocate_loss_offsets_caps_budget(self) -> None:
        portfolio = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "AAA",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 1000,
                        "Current Weight": 0.30,
                        "Target Weight": 0.10,
                    },
                    {
                        "Ticker": "BBB",
                        "Shares": 100,
                        "Current Price": 50,
                        "Cost Basis": 2500,
                        "Current Weight": 0.20,
                        "Target Weight": 0.10,
                    },
                ]
            )
        )

        allocations = allocate_loss_offsets(portfolio, 1000)

        self.assertAlmostEqual(sum(allocations.values()), 1000)
        self.assertGreater(allocations[0], allocations[1])

    def test_long_short_candidates_include_multiple_designs(self) -> None:
        position = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "SNDK",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 1000,
                        "Current Weight": 0.40,
                        "Target Weight": 0.10,
                    }
                ]
            )
        ).iloc[0]
        risk = pd.DataFrame(
            [
                {
                    "target": "SNDK",
                    "proxy": "QQQ",
                    "n_days": 1000,
                    "correlation": 0.55,
                    "beta_to_proxy": 1.5,
                    "r_squared": 0.30,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.25,
                },
                {
                    "target": "SNDK",
                    "proxy": "SOXX",
                    "n_days": 1000,
                    "correlation": 0.70,
                    "beta_to_proxy": 1.2,
                    "r_squared": 0.49,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.35,
                },
                {
                    "target": "SNDK",
                    "proxy": "MU",
                    "n_days": 1000,
                    "correlation": 0.65,
                    "beta_to_proxy": 0.9,
                    "r_squared": 0.42,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.55,
                },
                {
                    "target": "SNDK",
                    "proxy": "STX",
                    "n_days": 1000,
                    "correlation": 0.60,
                    "beta_to_proxy": 0.8,
                    "r_squared": 0.36,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.45,
                },
            ]
        )

        candidates = analyze_long_short_candidates(position, risk)

        self.assertIn("Market index hedge", set(candidates["hedge_type"]))
        self.assertIn("Sector hedge", set(candidates["hedge_type"]))
        self.assertIn("Peer basket hedge", set(candidates["hedge_type"]))
        self.assertIn("Pair trade", set(candidates["hedge_type"]))
        self.assertIn("Regime-aware overlay", set(candidates["hedge_type"]))
        self.assertIn(MULTI_PROXY_HEDGE_LABEL, set(candidates["hedge_type"]))

    def test_daily_returns_drive_regime_analysis_when_available(self) -> None:
        dates = pd.date_range("2024-01-01", periods=140, freq="B")
        sndk = [0.010, -0.006, 0.004, 0.012, -0.009] * 28
        soxx = [0.008, -0.004, 0.003, 0.010, -0.006] * 28
        qqq = [0.006, -0.003, 0.002, 0.007, -0.004] * 28
        spy = [0.004, -0.002, 0.002, 0.005, -0.003] * 28
        daily_returns = normalize_return_frame(
            pd.DataFrame({"date": dates, "SNDK": sndk, "SOXX": soxx, "QQQ": qqq, "SPY": spy})
        )
        position = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "SNDK",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 1000,
                        "Current Weight": 0.40,
                        "Target Weight": 0.10,
                    }
                ]
            )
        ).iloc[0]
        risk = pd.DataFrame(
            [
                {
                    "target": "SNDK",
                    "proxy": "SOXX",
                    "n_days": 140,
                    "correlation": 0.70,
                    "beta_to_proxy": 1.2,
                    "r_squared": 0.49,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.35,
                },
                {
                    "target": "SNDK",
                    "proxy": "QQQ",
                    "n_days": 140,
                    "correlation": 0.55,
                    "beta_to_proxy": 1.5,
                    "r_squared": 0.30,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.25,
                },
            ]
        )

        candidates = analyze_long_short_candidates(position, risk, daily_returns)

        self.assertIn("daily returns", set(candidates["return_data_source"]))
        self.assertTrue(candidates["scenario_behavior_by_regime"].str.contains("vol reduction").any())
        daily_rows = candidates[candidates["return_data_source"] == "daily returns"]
        self.assertTrue(daily_rows["drawdown_impact_method"].str.contains("Historical daily-return").any())

    def test_hedge_strategy_scores_require_matching_evidence(self) -> None:
        position = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "ABC",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 1000,
                        "Current Weight": 0.40,
                        "Target Weight": 0.10,
                    }
                ]
            )
        ).iloc[0]
        sector_only = pd.DataFrame(
            [
                {
                    "ticker": "ABC",
                    "hedge_type": "Sector hedge",
                    "volatility_reduction": 0.30,
                    "rank_score": 90.0,
                }
            ]
        )

        scores = score_strategies_for_position(
            position,
            sector_only,
            loss_offset=0.0,
            transition_years=3,
            user_horizon_years=5,
            philanthropic_intent=False,
        )

        overlay = scores[scores["strategy_id"] == "long_short_overlay"].iloc[0]
        pair = scores[scores["strategy_id"] == "pair_or_basket_hedge"].iloc[0]
        self.assertAlmostEqual(overlay["concentration_reduction"], 0.30)
        self.assertAlmostEqual(pair["concentration_reduction"], 0.05)

    def test_tax_rate_sensitivity_uses_loss_offsets(self) -> None:
        portfolio = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "XYZ",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 2000,
                        "Current Weight": 0.30,
                        "Target Weight": 0.15,
                        "Federal LTCG Rate": 0.20,
                        "NIIT Rate": 0.038,
                        "State Tax Rate": 0.00,
                    }
                ]
            )
        )

        sensitivity = build_sensitivity_tables(portfolio, pd.DataFrame(), loss_offset_budget=1000)
        base = sensitivity["tax_rate"].query("tax_rate_delta == 0").iloc[0]

        self.assertAlmostEqual(base["realized_gain"], 4000)
        self.assertAlmostEqual(base["estimated_tax"], 714)

    def test_run_transition_analysis_returns_summaries(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Ticker": "SNDK",
                    "Shares": 100,
                    "Current Price": 100,
                    "Cost Basis": 1000,
                    "Current Weight": 0.40,
                    "Target Weight": 0.10,
                }
            ]
        )
        risk = pd.DataFrame(
            [
                {
                    "target": "SNDK",
                    "proxy": "SOXX",
                    "n_days": 1000,
                    "correlation": 0.70,
                    "beta_to_proxy": 1.2,
                    "r_squared": 0.49,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.35,
                }
            ]
        )

        results = run_transition_analysis(raw, risk, loss_offset_budget=500)

        self.assertFalse(results["strategy_table"].empty)
        self.assertFalse(results["position_summary"].empty)
        self.assertFalse(results["portfolio_strategy_summary"].empty)
        self.assertFalse(results["long_short_table"].empty)
        self.assertIn("sensitivity_tables", results)
        self.assertFalse(results["sensitivity_tables"]["tax_rate"].empty)

    def test_transition_plan_summary_uses_selected_strategy_and_tax_budget(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Ticker": "SNDK",
                    "Shares": 100,
                    "Current Price": 100,
                    "Cost Basis": 1000,
                    "Current Weight": 0.40,
                    "Target Weight": 0.10,
                }
            ]
        )
        risk = pd.DataFrame(
            [
                {
                    "target": "SNDK",
                    "proxy": "SOXX",
                    "n_days": 1000,
                    "correlation": 0.70,
                    "beta_to_proxy": 1.2,
                    "r_squared": 0.49,
                    "annualized_target_vol": 0.60,
                    "annualized_proxy_vol": 0.35,
                }
            ]
        )

        results = run_transition_analysis(raw, risk)
        selected_strategy = results["portfolio_strategy_summary"].iloc[0]["strategy"]
        plan = build_transition_plan_summary(results, selected_strategy, max_tax_budget=5000)

        self.assertEqual(plan["selected_strategy"], selected_strategy)
        self.assertAlmostEqual(plan["max_tax_budget"], 5000)
        self.assertIn("Reduce concentrated exposure", plan["objective"])
        self.assertIn("SNDK", plan["primary_position_actions"])

    def test_sma_designs_compare_four_mandates_and_choose_balanced_by_default(self) -> None:
        portfolio = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "SNDK",
                        "Shares": 1000,
                        "Current Price": 100,
                        "Cost Basis": 10000,
                        "Current Weight": 0.60,
                        "Target Weight": 0.10,
                    },
                    {
                        "Ticker": "WDC",
                        "Shares": 1000,
                        "Current Price": 80,
                        "Cost Basis": 12000,
                        "Current Weight": 0.35,
                        "Target Weight": 0.08,
                    },
                ]
            )
        )
        long_short = pd.DataFrame(
            [
                {
                    "ticker": "SNDK",
                    "hedge_type": "Sector hedge",
                    "proposed_hedge": "SOXX",
                    "rank_score": 82.0,
                    "volatility_reduction": 0.28,
                    "maximum_drawdown_impact": 0.18,
                    "tracking_error": 0.30,
                    "return_data_source": "daily returns",
                }
            ]
        )

        comparison = evaluate_sma_designs(portfolio, long_short)

        self.assertEqual(len(comparison), 4)
        self.assertEqual(comparison.iloc[0]["design_id"], "balanced")
        self.assertIn("wash-sale", comparison["professional_review_flags"].str.cat(sep=" ").lower())
        self.assertIn("Sector hedge via SOXX", set(comparison["best_hedge_evidence"]))

    def test_sma_designs_respect_simplicity_priorities(self) -> None:
        portfolio = normalize_portfolio_frame(
            pd.DataFrame(
                [
                    {
                        "Ticker": "ABC",
                        "Shares": 100,
                        "Current Price": 100,
                        "Cost Basis": 7000,
                        "Current Weight": 0.20,
                        "Target Weight": 0.12,
                    }
                ]
            )
        )

        comparison = evaluate_sma_designs(
            portfolio,
            pd.DataFrame(),
            priorities={
                "tax_loss_capacity": 1.0,
                "concentration_transition_fit": 1.0,
                "risk_control": 1.0,
                "tax_rule_clarity": 5.0,
                "implementation_simplicity": 5.0,
                "liquidity_borrow_safety": 5.0,
                "cost_efficiency": 5.0,
                "manager_operational_quality": 2.0,
                "diversification_benefit": 1.0,
            },
        )

        self.assertEqual(comparison.iloc[0]["design_id"], "conservative")

    def test_sma_due_diligence_checklist_includes_tax_and_cost_controls(self) -> None:
        checklist = build_sma_due_diligence_checklist("Balanced diversified 130/30-150/50 SMA")

        text = " ".join(checklist["Question"].tolist() + checklist["Evidence Needed"].tolist()).lower()
        self.assertIn("wash", text)
        self.assertIn("form adv", text)
        self.assertGreaterEqual(len(checklist), 5)

    def test_diy_sma_exposure_budget_respects_gross_and_short_caps(self) -> None:
        budget = build_diy_sma_exposure_budget(
            sleeve_capital=1_000_000,
            target_net_exposure=0.90,
            max_gross_exposure=1.20,
            max_short_exposure=0.20,
        )

        self.assertAlmostEqual(budget["short_notional"], 150_000)
        self.assertAlmostEqual(budget["long_notional"], 1_050_000)
        self.assertAlmostEqual(budget["actual_net_exposure"], 0.90)
        self.assertAlmostEqual(budget["actual_gross_exposure"], 1.20)
        self.assertLessEqual(budget["actual_short_exposure"], 0.20)

        percent_style_budget = build_diy_sma_exposure_budget(
            sleeve_capital=1_000_000,
            target_net_exposure=90,
            max_gross_exposure=120,
            max_short_exposure=20,
        )
        self.assertAlmostEqual(percent_style_budget["actual_net_exposure"], 0.90)
        self.assertAlmostEqual(percent_style_budget["actual_gross_exposure"], 1.20)

    def test_diy_sma_tables_include_trade_budget_flags_and_lot_tracking(self) -> None:
        budget = build_diy_sma_exposure_budget(
            sleeve_capital=500_000,
            target_net_exposure=0.90,
            max_gross_exposure=1.10,
            max_short_exposure=0.30,
            annual_realized_gain_budget=0,
        )

        trade_budget = build_diy_sma_trade_budget_table(budget)
        flags = build_diy_sma_warning_flags(budget, restricted_tickers="")
        tracker = build_diy_tax_lot_tracker_template("SNDK,WDC")
        checklist = build_diy_paper_trading_checklist()

        self.assertIn("Replacement long book", set(trade_budget["Sleeve Component"]))
        self.assertTrue(flags["Flag"].str.contains("Restricted ticker list").any())
        self.assertEqual(tracker.loc[0, "Ticker"], "SNDK")
        self.assertIn("Wash-Sale Window Start", tracker.columns)
        self.assertTrue(checklist["Checklist Item"].str.contains("30-60 days").any())


if __name__ == "__main__":
    unittest.main()
