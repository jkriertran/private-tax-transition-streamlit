from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "analysis_output" / "tax_transition_model"
MODEL_DIR = Path(os.getenv("TAX_TRANSITION_MODEL_DIR", str(DEFAULT_MODEL_DIR))).expanduser()

SALE_METHOD_LABELS = {
    "tax_aware_each_symbol": "Tax-aware, same % from each cluster name",
    "tax_aware_combined": "Tax-aware across combined cluster pool",
    "pro_rata_all_lots": "Pro-rata all lots",
}

TAX_SCENARIO_ORDER = [
    "Federal top LTCG + NIIT",
    "Federal top LTCG only",
    "Federal + NIIT + 9.3% state placeholder",
    "Federal + NIIT + 13.3% state placeholder",
]


def safe_secret(section: str, key: str, default: Any = None) -> Any:
    try:
        block = st.secrets.get(section, {})
        if hasattr(block, "get"):
            return block.get(key, default)
    except Exception:
        return default
    return default


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_email_list(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        parts = value.replace("\n", ",").split(",")
    else:
        parts = list(value)
    return {str(part).strip().lower() for part in parts if str(part).strip()}


def get_access_mode() -> str:
    return str(
        os.getenv(
            "TAX_APP_ACCESS_MODE",
            safe_secret("access", "mode", "locked"),
        )
    ).strip().lower()


def enforce_access() -> dict[str, str]:
    mode = get_access_mode()
    if mode == "local_dev":
        return {"email": "local-dev", "method": "local_dev"}

    if mode == "streamlit_private":
        return {"email": "streamlit-private-viewer", "method": "streamlit_private"}

    if mode == "oidc_allowlist":
        if not hasattr(st, "login") or not hasattr(st, "user"):
            st.error("This Streamlit version does not support st.login/st.user OIDC authentication.")
            st.stop()

        user = st.user
        is_logged_in = bool(getattr(user, "is_logged_in", False))
        if not is_logged_in:
            st.title("Private Tax Transition Dashboard")
            st.caption("Sign in with the email address that was explicitly approved for this report.")
            connection = str(safe_secret("access", "oidc_connection", "") or "").strip()
            if connection:
                st.button("Sign in", on_click=st.login, args=(connection,))
            else:
                st.button("Sign in", on_click=st.login)
            st.stop()

        email = ""
        try:
            email = str(user.get("email", "") or "").strip().lower()
        except Exception:
            email = str(getattr(user, "email", "") or "").strip().lower()

        allowed = parse_email_list(
            os.getenv("TAX_APP_ALLOWED_EMAILS", safe_secret("access", "allowed_emails", []))
        )
        if not allowed:
            st.error("OIDC is enabled but no allowed email list is configured.")
            st.stop()
        if email not in allowed:
            st.error("This email is not authorized to view this report.")
            st.button("Sign out", on_click=st.logout)
            st.stop()

        return {"email": email, "method": "oidc_allowlist"}

    st.title("Private Tax Transition Dashboard")
    st.error("Access is locked because no approved access mode is configured.")
    st.markdown(
        "Set `TAX_APP_ACCESS_MODE=local_dev` for local testing, or configure "
        "`[access] mode = \"streamlit_private\"` after making the Streamlit Cloud app private."
    )
    st.stop()


def format_dollars(value: Any, digits: int = 0) -> str:
    if pd.isna(value):
        return ""
    return f"${float(value):,.{digits}f}"


def format_pct(value: Any, digits: int = 1) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value) * 100:.{digits}f}%"


def format_display_pct(value: Any, digits: int = 1) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}%"


def format_number(value: Any, digits: int = 0) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):,.{digits}f}"


def percent_display(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    view = df.copy()
    for column in columns:
        if column in view.columns:
            view[column] = view[column] * 100
    return view


def require_file(name: str) -> Path:
    path = MODEL_DIR / name
    if not path.exists():
        st.error(f"Missing required model output: `{path}`")
        st.stop()
    return path


def optional_file(name: str) -> Path | None:
    path = MODEL_DIR / name
    return path if path.exists() else None


@st.cache_data(show_spinner=False)
def _read_csv(path: str, mtime_ns: int) -> pd.DataFrame:
    del mtime_ns
    return pd.read_csv(path)


def canonicalize_model_columns(name: str, df: pd.DataFrame) -> pd.DataFrame:
    if name not in {"overlay_economics.csv", "overlay_loss_capacity.csv"}:
        return df
    legacy_to_cluster = {
        "overlay_gross_pct_of_sndk_wdc_mv": "overlay_gross_pct_of_cluster_mv",
    }
    usable_renames = {
        old: new
        for old, new in legacy_to_cluster.items()
        if old in df.columns and new not in df.columns
    }
    if usable_renames:
        return df.rename(columns=usable_renames)
    return df


def load_csv(name: str) -> pd.DataFrame:
    path = require_file(name)
    frame = _read_csv(str(path), path.stat().st_mtime_ns)
    return canonicalize_model_columns(name, frame)


def load_optional_csv(name: str) -> pd.DataFrame | None:
    path = optional_file(name)
    if path is None:
        return None
    frame = _read_csv(str(path), path.stat().st_mtime_ns)
    return canonicalize_model_columns(name, frame)


@st.cache_data(show_spinner=False)
def _read_text(path: str, mtime_ns: int) -> str:
    del mtime_ns
    return Path(path).read_text()


def load_text(name: str) -> str:
    path = require_file(name)
    return _read_text(str(path), path.stat().st_mtime_ns)


def render_svg(path: Path) -> None:
    if path.exists():
        st.markdown(path.read_text(), unsafe_allow_html=True)


def render_static_table(
    df: pd.DataFrame,
    columns: list[str],
    labels: dict[str, str],
    formatters: dict[str, Any] | None = None,
) -> None:
    formatters = formatters or {}
    view = df.loc[:, columns].copy()
    for column, formatter in formatters.items():
        if column in view.columns:
            view[column] = view[column].map(formatter)
    view = view.rename(columns=labels)
    html = view.to_html(index=False, escape=True, border=0)
    st.markdown(f'<div class="table-wrap">{html}</div>', unsafe_allow_html=True)


def init_page() -> None:
    st.set_page_config(
        page_title="Private Tax Transition Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        div[data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 16px;
            background: #ffffff;
        }
        div[data-testid="stMetricLabel"] p { color: #4b5563; }
        div[data-testid="stMetricValue"] { color: #111827; }
        .small-note {
            color: #6b7280;
            font-size: 0.88rem;
            line-height: 1.35;
        }
        .security-note {
            border-left: 4px solid #2563eb;
            background: #f8fafc;
            padding: 12px 14px;
            border-radius: 4px;
            color: #374151;
        }
        .table-wrap {
            overflow-x: auto;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin: 0.5rem 0 1rem 0;
        }
        .table-wrap table {
            border-collapse: collapse;
            width: 100%;
            font-size: 0.9rem;
        }
        .table-wrap thead tr {
            background: #f8fafc;
        }
        .table-wrap th {
            color: #374151;
            font-weight: 700;
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #e5e7eb;
            white-space: nowrap;
        }
        .table-wrap td {
            padding: 9px 12px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: top;
            white-space: nowrap;
        }
        .table-wrap tbody tr:last-child td {
            border-bottom: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar(access: dict[str, str]) -> str:
    st.sidebar.title("Report Access")
    st.sidebar.caption("Read-only dashboard")
    st.sidebar.write(f"Access mode: `{access['method']}`")
    if access["method"] == "oidc_allowlist":
        st.sidebar.write(f"Signed in: `{access['email']}`")
        if st.sidebar.button("Sign out"):
            st.logout()

    advisor_enabled = truthy(
        os.getenv("TAX_APP_ENABLE_ADVISOR_VIEW", safe_secret("app", "enable_advisor_view", False))
    )
    if advisor_enabled:
        audience = st.sidebar.selectbox("View", ["Client View", "Advisor View"], index=0)
    else:
        audience = "Client View"
        st.sidebar.info("Advisor View is disabled for this deployment.")

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        **Safety posture**

        - No raw Schwab exports are loaded.
        - No uploads, trade actions, or writebacks.
        - No download buttons.
        - Lot-level table is hidden unless Advisor View is enabled.
        """
    )
    return audience


def data_status(rec: pd.DataFrame, cluster_summary: pd.DataFrame, lots: pd.DataFrame | None = None) -> None:
    status_counts = rec["reconciliation_status"].value_counts().to_dict()
    all_pass = status_counts.get("PASS", 0) == len(rec)
    status_text = "PASS" if all_pass else "REVIEW"
    if lots is not None:
        target_lots = int(len(lots))
        long_term = int((lots["holding_period"] == "Long Term").sum())
        zero_basis = int(lots["is_zero_or_near_zero_basis"].sum())
    else:
        target_lots = int(cluster_summary["lots"].sum())
        long_term = int(cluster_summary["long_term_lots"].sum()) if "long_term_lots" in cluster_summary else 0
        zero_basis = int(cluster_summary["zero_basis_lots"].sum()) if "zero_basis_lots" in cluster_summary else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Schwab reconciliation", status_text)
    c2.metric("Cluster lots", f"{target_lots:,}")
    c3.metric("Long-term lots", f"{long_term:,}")
    c4.metric("Zero or near-zero basis", f"{zero_basis:,}")


def render_concentration_answer(cluster_summary: pd.DataFrame, risk_weights: pd.DataFrame) -> None:
    primary_symbols = {"SNDK", "WDC"}
    cluster_account_weight = float(cluster_summary["account_market_value_weight"].sum())
    primary_account_weight = float(
        cluster_summary.loc[cluster_summary["symbol"].isin(primary_symbols), "account_market_value_weight"].sum()
    )
    other_cluster_weight = max(0.0, cluster_account_weight - primary_account_weight)
    primary_risk_weight = float(
        risk_weights.loc[risk_weights["symbol"].isin(primary_symbols), "cluster_vol_weighted_risk_weight"].sum()
    )

    st.subheader("Concentration Answer")
    st.markdown(
        """
        <div class="security-note">
        This looks like a broader semiconductor/memory/storage factor concentration. SNDK and WDC are still
        the tax-transition center of gravity, but the restriction list and overlay design should include the
        other cluster names.
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cluster account weight", format_pct(cluster_account_weight))
    c2.metric("SNDK/WDC account weight", format_pct(primary_account_weight))
    c3.metric("Other cluster account weight", format_pct(other_cluster_weight))
    c4.metric("SNDK/WDC vol-weighted cluster risk", format_pct(primary_risk_weight))


def render_overview(
    rec: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    bucket_summary: pd.DataFrame,
    risk_weights: pd.DataFrame,
    lots: pd.DataFrame | None = None,
) -> None:
    render_concentration_answer(cluster_summary, risk_weights)
    data_status(rec, cluster_summary, lots)
    st.subheader("Semiconductor Cluster Exposure")
    st.caption("Derived from normalized Schwab lot-detail exports. SNDK/WDC remain the primary tax-transition focus; the broader cluster drives the risk and overlay design.")
    summary = percent_display(
        cluster_summary,
        ["basis_ratio", "embedded_gain_pct_of_mv", "account_market_value_weight", "cluster_market_value_weight"],
    )
    render_static_table(
        summary,
        [
            "symbol",
            "risk_bucket",
            "lots",
            "market_value",
            "unrealized_gain",
            "account_market_value_weight",
            "cluster_market_value_weight",
            "basis_ratio",
            "embedded_gain_pct_of_mv",
            "tax_transition_scope",
        ],
        {
            "symbol": "Symbol",
            "risk_bucket": "Risk Bucket",
            "lots": "Lots",
            "market_value": "Market Value",
            "unrealized_gain": "Unrealized Gain",
            "account_market_value_weight": "Modeled Account Weight",
            "cluster_market_value_weight": "Cluster Weight",
            "basis_ratio": "Basis / Value",
            "embedded_gain_pct_of_mv": "Gain / Value",
            "tax_transition_scope": "Scope",
        },
        {
            "lots": lambda x: format_number(x, 0),
            "market_value": format_dollars,
            "unrealized_gain": format_dollars,
            "account_market_value_weight": format_display_pct,
            "cluster_market_value_weight": format_display_pct,
            "basis_ratio": format_display_pct,
            "embedded_gain_pct_of_mv": format_display_pct,
        },
    )
    render_svg(MODEL_DIR / "charts" / "semiconductor_cluster_basis_exposure.svg")

    st.subheader("Risk Bucket View")
    bucket_display = percent_display(
        bucket_summary,
        ["account_market_value_weight", "cluster_market_value_weight", "embedded_gain_pct_of_mv"],
    )
    render_static_table(
        bucket_display,
        [
            "risk_bucket",
            "symbols",
            "lots",
            "long_term_lots",
            "market_value",
            "unrealized_gain",
            "account_market_value_weight",
            "cluster_market_value_weight",
            "embedded_gain_pct_of_mv",
        ],
        {
            "risk_bucket": "Risk Bucket",
            "symbols": "Symbols",
            "lots": "Lots",
            "long_term_lots": "Long-Term Lots",
            "market_value": "Market Value",
            "unrealized_gain": "Unrealized Gain",
            "account_market_value_weight": "Modeled Account Weight",
            "cluster_market_value_weight": "Cluster Weight",
            "embedded_gain_pct_of_mv": "Gain / Value",
        },
        {
            "symbols": lambda x: format_number(x, 0),
            "lots": lambda x: format_number(x, 0),
            "long_term_lots": lambda x: format_number(x, 0),
            "market_value": format_dollars,
            "unrealized_gain": format_dollars,
            "account_market_value_weight": format_display_pct,
            "cluster_market_value_weight": format_display_pct,
            "embedded_gain_pct_of_mv": format_display_pct,
        },
    )

    st.subheader("Cluster Risk Weights")
    risk_display = percent_display(
        risk_weights,
        [
            "account_market_value_weight",
            "cluster_market_value_weight",
            "annualized_vol",
            "cluster_vol_weighted_risk_weight",
        ],
    )
    render_static_table(
        risk_display,
        [
            "symbol",
            "risk_bucket",
            "market_value",
            "account_market_value_weight",
            "cluster_market_value_weight",
            "annualized_vol",
            "cluster_vol_weighted_risk_weight",
            "return_data_source",
        ],
        {
            "symbol": "Symbol",
            "risk_bucket": "Risk Bucket",
            "market_value": "Market Value",
            "account_market_value_weight": "Modeled Account Weight",
            "cluster_market_value_weight": "Cluster Weight",
            "annualized_vol": "Annualized Vol",
            "cluster_vol_weighted_risk_weight": "Vol-Weighted Risk",
            "return_data_source": "Return Data",
        },
        {
            "market_value": format_dollars,
            "account_market_value_weight": format_display_pct,
            "cluster_market_value_weight": format_display_pct,
            "annualized_vol": format_display_pct,
            "cluster_vol_weighted_risk_weight": format_display_pct,
        },
    )


def render_transition(transition: pd.DataFrame) -> None:
    st.subheader("Cluster Transition Tax Scenarios")
    tax_scenarios = [s for s in TAX_SCENARIO_ORDER if s in set(transition["tax_rate_scenario"])]
    tax_scenario = st.selectbox("Tax-rate scenario", tax_scenarios, index=0)
    sale_methods = [m for m in SALE_METHOD_LABELS if m in set(transition["sale_method"])]
    sale_method = st.selectbox(
        "Sale method",
        sale_methods,
        format_func=lambda x: SALE_METHOD_LABELS.get(x, x),
        index=sale_methods.index("tax_aware_each_symbol") if "tax_aware_each_symbol" in sale_methods else 0,
    )
    view = transition[
        (transition["tax_rate_scenario"] == tax_scenario) & (transition["sale_method"] == sale_method)
    ].copy()
    view = view.sort_values("sale_pct")
    view_display = percent_display(view, ["sale_pct", "effective_gain_pct_of_sale", "realized_gain_pct_of_full_embedded_gain", "gross_overlay_needed_at_10pct_loss_yield_pct_of_concentrated_mv"])
    c1, c2 = st.columns([2, 1])
    with c1:
        render_static_table(
            view_display,
            [
                "sale_pct",
                "sale_value",
                "realized_gain",
                "effective_gain_pct_of_sale",
                "estimated_tax",
                "after_tax_sale_proceeds",
                "gross_overlay_needed_at_10pct_loss_yield",
            ],
            {
                "sale_pct": "Sale %",
                "sale_value": "Sale Value",
                "realized_gain": "Realized Gain",
                "effective_gain_pct_of_sale": "Gain / Sale",
                "estimated_tax": "Estimated Tax",
                "after_tax_sale_proceeds": "After-Tax Proceeds",
                "gross_overlay_needed_at_10pct_loss_yield": "Gross Overlay Needed at 10% Loss Yield",
            },
            {
                "sale_pct": format_display_pct,
                "sale_value": format_dollars,
                "realized_gain": format_dollars,
                "effective_gain_pct_of_sale": format_display_pct,
                "estimated_tax": format_dollars,
                "after_tax_sale_proceeds": format_dollars,
                "gross_overlay_needed_at_10pct_loss_yield": format_dollars,
            },
        )
    with c2:
        selected = view[view["sale_pct"].isin([0.10, 0.25, 0.50, 1.00])]
        for _, row in selected.iterrows():
            st.metric(
                f"{float(row['sale_pct']):.0%} sale",
                format_dollars(row["estimated_tax"]),
                help="Estimated tax for the selected tax-rate and sale-method scenario.",
            )
    render_svg(MODEL_DIR / "charts" / "transition_tax_by_sale_pct.svg")


def render_overlay(overlay_capacity: pd.DataFrame, overlay_economics: pd.DataFrame, candidates: pd.DataFrame) -> None:
    st.subheader("Long/Short Overlay")
    st.markdown(
        """
        <div class="security-note">
        The overlay is modeled as a tax-loss harvesting and diversification sleeve. It does not erase taxes;
        it creates potential capital losses that may offset gains if the losses are valid and usable.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    candidates_display = percent_display(candidates, ["base_annual_harvest_yield_of_gross"])
    render_static_table(
        candidates_display,
        [
            "rank",
            "strategy_name",
            "core_role",
            "illustrative_net_exposure",
            "illustrative_gross_exposure",
            "base_annual_harvest_yield_of_gross",
            "fit_with_sndk_wdc",
        ],
        {
            "rank": "Rank",
            "strategy_name": "Strategy",
            "core_role": "Role",
            "illustrative_net_exposure": "Net Exposure",
            "illustrative_gross_exposure": "Gross Exposure",
            "base_annual_harvest_yield_of_gross": "Base Harvest Yield",
            "fit_with_sndk_wdc": "Fit With Cluster",
        },
        {
            "rank": lambda x: format_number(x, 0),
            "base_annual_harvest_yield_of_gross": format_display_pct,
        },
    )

    st.subheader("Overlay Economics")
    gross_options = sorted(overlay_economics["overlay_gross_pct_of_cluster_mv"].unique())
    cost_options = sorted(overlay_economics["annual_cost_pct_of_gross"].unique())
    c1, c2 = st.columns(2)
    gross_choice = c1.selectbox("Overlay gross as % of cluster value", gross_options, format_func=format_pct, index=1)
    cost_choice = c2.selectbox("Annual overlay cost as % of gross", cost_options, format_func=format_pct, index=1)
    econ = overlay_economics[
        (overlay_economics["overlay_gross_pct_of_cluster_mv"] == gross_choice)
        & (overlay_economics["annual_cost_pct_of_gross"] == cost_choice)
    ].sort_values("annual_harvested_loss_yield_of_gross")
    econ_display = percent_display(
        econ,
        [
            "annual_harvested_loss_yield_of_gross",
            "annual_cost_pct_of_gross",
            "breakeven_harvest_yield_at_23_8pct_tax_rate",
            "overlay_gross_pct_of_cluster_mv",
        ],
    )
    render_static_table(
        econ_display,
        [
            "annual_harvested_loss_yield_of_gross",
            "overlay_gross_dollars",
            "illustrative_harvested_loss",
            "tax_value_at_23_8pct_if_losses_used",
            "estimated_annual_overlay_cost",
            "illustrative_net_tax_value_before_alpha",
            "breakeven_harvest_yield_at_23_8pct_tax_rate",
        ],
        {
            "annual_harvested_loss_yield_of_gross": "Harvest Loss Yield",
            "overlay_gross_dollars": "Overlay Gross",
            "illustrative_harvested_loss": "Harvested Loss",
            "tax_value_at_23_8pct_if_losses_used": "Tax Value at 23.8%",
            "estimated_annual_overlay_cost": "Estimated Cost",
            "illustrative_net_tax_value_before_alpha": "Net Tax Value Before Alpha",
            "breakeven_harvest_yield_at_23_8pct_tax_rate": "Breakeven Harvest Yield",
        },
        {
            "annual_harvested_loss_yield_of_gross": format_display_pct,
            "overlay_gross_dollars": format_dollars,
            "illustrative_harvested_loss": format_dollars,
            "tax_value_at_23_8pct_if_losses_used": format_dollars,
            "estimated_annual_overlay_cost": format_dollars,
            "illustrative_net_tax_value_before_alpha": format_dollars,
            "breakeven_harvest_yield_at_23_8pct_tax_rate": format_display_pct,
        },
    )
    render_svg(MODEL_DIR / "charts" / "overlay_loss_capacity.svg")

    with st.expander("Loss-capacity grid"):
        capacity_display = percent_display(
            overlay_capacity,
            [
                "overlay_gross_pct_of_cluster_mv",
                "annual_harvested_loss_yield_of_gross",
                "coverage_of_10%_tax_aware_each_symbol_sale_gain",
                "coverage_of_25%_tax_aware_each_symbol_sale_gain",
                "coverage_of_50%_tax_aware_each_symbol_sale_gain",
                "coverage_of_100%_tax_aware_each_symbol_sale_gain",
            ],
        )
        capacity_columns = list(capacity_display.columns)
        capacity_labels = {column: column.replace("_", " ").replace("pct", "%").title() for column in capacity_columns}
        capacity_formatters = {
            "overlay_gross_pct_of_cluster_mv": format_display_pct,
            "annual_harvested_loss_yield_of_gross": format_display_pct,
            "illustrative_harvested_loss": format_dollars,
            "coverage_of_10%_tax_aware_each_symbol_sale_gain": format_display_pct,
            "coverage_of_25%_tax_aware_each_symbol_sale_gain": format_display_pct,
            "coverage_of_50%_tax_aware_each_symbol_sale_gain": format_display_pct,
            "coverage_of_100%_tax_aware_each_symbol_sale_gain": format_display_pct,
        }
        render_static_table(
            capacity_display,
            capacity_columns,
            capacity_labels,
            capacity_formatters,
        )


def render_risk(risk: pd.DataFrame) -> None:
    st.subheader("Risk Proxy Evidence")
    st.caption("Correlation and beta are risk guides only. They are not recommendations to short the proxy.")
    targets = list(risk["target"].drop_duplicates())
    selected_targets = st.multiselect("Targets", targets, default=targets)
    view = percent_display(
        risk[risk["target"].isin(selected_targets)].copy(),
        ["annualized_target_vol", "annualized_proxy_vol"],
    )
    render_static_table(
        view,
        [
            "target",
            "proxy",
            "start_date",
            "end_date",
            "n_days",
            "correlation",
            "beta_to_proxy",
            "r_squared",
            "annualized_target_vol",
            "annualized_proxy_vol",
        ],
        {
            "target": "Target",
            "proxy": "Proxy",
            "start_date": "Start",
            "end_date": "End",
            "n_days": "Days",
            "correlation": "Correlation",
            "beta_to_proxy": "Beta",
            "r_squared": "R-Squared",
            "annualized_target_vol": "Target Vol",
            "annualized_proxy_vol": "Proxy Vol",
        },
        {
            "n_days": lambda x: format_number(x, 0),
            "correlation": lambda x: format_number(x, 2),
            "beta_to_proxy": lambda x: format_number(x, 2),
            "r_squared": lambda x: format_number(x, 2),
            "annualized_target_vol": format_display_pct,
            "annualized_proxy_vol": format_display_pct,
        },
    )


def render_qa(rec: pd.DataFrame) -> None:
    st.subheader("Data QA")
    st.caption("Reconciliation of normalized lot data against Schwab lot-detail files and Schwab total rows.")
    render_static_table(
        rec,
        [
            "symbol",
            "source_lot_rows",
            "normalized_lot_rows",
            "source_total_rows",
            "reconciliation_status",
            "normalized_vs_schwab_total_market_value_diff",
            "normalized_vs_schwab_total_cost_basis_diff",
            "normalized_vs_schwab_total_gain_loss_dollars_diff",
        ],
        {
            "symbol": "Symbol",
            "source_lot_rows": "Source Rows",
            "normalized_lot_rows": "Normalized Rows",
            "source_total_rows": "Total Rows",
            "reconciliation_status": "Status",
            "normalized_vs_schwab_total_market_value_diff": "MV Diff",
            "normalized_vs_schwab_total_cost_basis_diff": "Basis Diff",
            "normalized_vs_schwab_total_gain_loss_dollars_diff": "Gain/Loss Diff",
        },
        {
            "source_lot_rows": lambda x: format_number(x, 0),
            "normalized_lot_rows": lambda x: format_number(x, 0),
            "source_total_rows": lambda x: format_number(x, 0),
            "normalized_vs_schwab_total_market_value_diff": lambda x: format_dollars(x, 2),
            "normalized_vs_schwab_total_cost_basis_diff": lambda x: format_dollars(x, 2),
            "normalized_vs_schwab_total_gain_loss_dollars_diff": lambda x: format_dollars(x, 2),
        },
    )


def render_advisor_lots(lots: pd.DataFrame | None, sale_schedule: pd.DataFrame | None) -> None:
    st.subheader("Advisor Detail")
    if lots is None or sale_schedule is None:
        st.error("Advisor detail files were not included in this deployment package.")
        st.stop()
    st.caption("Lot-level and sale-schedule views are intended for advisor review only.")
    lot_cols = [
        "symbol",
        "open_date",
        "quantity",
        "market_value",
        "cost_basis",
        "gain_loss_dollars",
        "basis_ratio",
        "embedded_gain_pct_of_mv",
        "holding_period",
        "tax_friendly_sale_rank",
    ]
    lots_display = percent_display(
        lots[lot_cols].sort_values(["tax_friendly_sale_rank", "symbol"]),
        ["basis_ratio", "embedded_gain_pct_of_mv"],
    )
    render_static_table(
        lots_display,
        lot_cols,
        {
            "symbol": "Symbol",
            "open_date": "Open Date",
            "quantity": "Quantity",
            "market_value": "Market Value",
            "cost_basis": "Cost Basis",
            "gain_loss_dollars": "Unrealized Gain",
            "basis_ratio": "Basis / Value",
            "embedded_gain_pct_of_mv": "Gain / Value",
            "holding_period": "Holding Period",
            "tax_friendly_sale_rank": "Sale Rank",
        },
        {
            "quantity": lambda x: format_number(x, 5),
            "market_value": format_dollars,
            "cost_basis": format_dollars,
            "gain_loss_dollars": format_dollars,
            "basis_ratio": format_display_pct,
            "embedded_gain_pct_of_mv": format_display_pct,
            "tax_friendly_sale_rank": lambda x: format_number(x, 0),
        },
    )
    with st.expander("Lot-level sale schedule"):
        sale_schedule_display = percent_display(
            sale_schedule,
            ["sale_pct", "sale_fraction_of_lot", "lot_embedded_gain_pct_of_mv"],
        )
        sale_columns = list(sale_schedule_display.columns)
        sale_labels = {column: column.replace("_", " ").title() for column in sale_columns}
        sale_formatters = {
            "sale_pct": format_display_pct,
            "lot_market_value": format_dollars,
            "lot_cost_basis": format_dollars,
            "lot_unrealized_gain": format_dollars,
            "lot_embedded_gain_pct_of_mv": format_display_pct,
            "sale_fraction_of_lot": format_display_pct,
            "sale_value": format_dollars,
            "basis_sold": format_dollars,
            "realized_gain": format_dollars,
        }
        render_static_table(
            sale_schedule_display,
            sale_columns,
            sale_labels,
            sale_formatters,
        )


def render_notes() -> None:
    st.subheader("Important Limits")
    st.markdown(
        """
        This dashboard is for discussion and planning. It is not tax, legal, or investment advice.

        The model does not determine whether any position is substantially identical, whether a short or option
        creates straddle or constructive-sale consequences, whether harvested losses are short-term or long-term
        for final netting, or whether securities can actually be borrowed at the modeled cost.

        Before implementation, the client should review the transition plan with a CPA or tax counsel and the
        investment manager responsible for the long/short SMA.
        """
    )


def main() -> None:
    init_page()
    access = enforce_access()
    audience = sidebar(access)

    rec = load_csv("schwab_lot_total_reconciliation.csv")
    cluster_summary = load_csv("cluster_exposure_summary.csv")
    bucket_summary = load_csv("cluster_risk_bucket_summary.csv")
    risk_weights = load_csv("cluster_risk_weights.csv")
    transition = load_csv("transition_tax_scenarios.csv")
    overlay_capacity = load_csv("overlay_loss_capacity.csv")
    overlay_economics = load_csv("overlay_economics.csv")
    candidates = load_csv("candidate_long_short_strategies.csv")
    risk = load_csv("risk_proxy_correlation.csv")
    lots = load_optional_csv("semiconductor_cluster_tax_lot_exposure.csv")
    sale_schedule = load_optional_csv("sale_lot_schedule.csv")

    st.title("Private Tax Transition Dashboard")
    st.caption("Semiconductor/memory/storage concentrated-position transition model")

    tabs = ["Overview", "Transition", "Long/Short Overlay", "Risk Proxies", "Data QA", "Notes"]
    if audience == "Advisor View":
        tabs.insert(5, "Advisor Detail")

    tab_objects = st.tabs(tabs)
    for label, tab in zip(tabs, tab_objects):
        with tab:
            if label == "Overview":
                render_overview(rec, cluster_summary, bucket_summary, risk_weights, lots)
            elif label == "Transition":
                render_transition(transition)
            elif label == "Long/Short Overlay":
                render_overlay(overlay_capacity, overlay_economics, candidates)
            elif label == "Risk Proxies":
                render_risk(risk)
            elif label == "Data QA":
                render_qa(rec)
            elif label == "Advisor Detail":
                render_advisor_lots(lots, sale_schedule)
            elif label == "Notes":
                render_notes()


if __name__ == "__main__":
    main()
