from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    from apps.market_data import (
        ALPACA_DATA_BASE_URL,
        ALPACA_HISTORICAL_FEEDS,
        ALPACA_SUPPORTED_FEEDS,
        HistoricalBarsResult,
        MarketDataResult,
        apply_market_prices_to_portfolio,
        clean_tickers,
        default_history_window,
        fetch_alpaca_historical_bars,
        fetch_alpaca_latest_bars,
        market_data_qa_frame,
        market_prices_to_frame,
    )
    from apps.tax_transition_engine import (
        DEFAULT_HEDGE_ASSUMPTIONS,
        DEFAULT_SMA_STUDY_PRIORITIES,
        DEFAULT_STRATEGY_PRIORITIES,
        build_sma_due_diligence_checklist,
        build_transition_plan_summary,
        build_sample_portfolio_from_cluster_summary,
        evaluate_sma_designs,
        long_short_research_markdown,
        normalize_return_frame,
        normalize_portfolio_frame,
        run_transition_analysis,
    )
except ModuleNotFoundError:
    from market_data import (
        ALPACA_DATA_BASE_URL,
        ALPACA_HISTORICAL_FEEDS,
        ALPACA_SUPPORTED_FEEDS,
        HistoricalBarsResult,
        MarketDataResult,
        apply_market_prices_to_portfolio,
        clean_tickers,
        default_history_window,
        fetch_alpaca_historical_bars,
        fetch_alpaca_latest_bars,
        market_data_qa_frame,
        market_prices_to_frame,
    )
    from tax_transition_engine import (
        DEFAULT_HEDGE_ASSUMPTIONS,
        DEFAULT_SMA_STUDY_PRIORITIES,
        DEFAULT_STRATEGY_PRIORITIES,
        build_sma_due_diligence_checklist,
        build_transition_plan_summary,
        build_sample_portfolio_from_cluster_summary,
        evaluate_sma_designs,
        long_short_research_markdown,
        normalize_return_frame,
        normalize_portfolio_frame,
        run_transition_analysis,
    )


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


def safe_root_secret(key: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def secret_or_env(section: str, key: str, env_name: str, default: Any = None) -> Any:
    value = os.getenv(env_name)
    if value not in {None, ""}:
        return value
    section_value = safe_secret(section, key, None)
    if section_value not in {None, ""}:
        return section_value
    root_value = safe_root_secret(env_name, None)
    if root_value not in {None, ""}:
        return root_value
    return default


def alpaca_credentials() -> tuple[str, str]:
    api_key_id = str(
        secret_or_env("alpaca", "api_key_id", "APCA_API_KEY_ID", "")
        or safe_secret("alpaca", "key_id", "")
        or safe_secret("alpaca", "api_key", "")
    ).strip()
    api_secret_key = str(
        secret_or_env("alpaca", "api_secret_key", "APCA_API_SECRET_KEY", "")
        or safe_secret("alpaca", "secret_key", "")
        or safe_secret("alpaca", "api_secret", "")
    ).strip()
    return api_key_id, api_secret_key


def alpaca_config() -> dict[str, str]:
    return {
        "feed": str(
            secret_or_env("alpaca", "data_feed", "ALPACA_DATA_FEED", "")
            or safe_secret("alpaca", "feed", "")
            or "iex"
        ).strip().lower(),
        "base_url": str(
            os.getenv(
                "APCA_API_DATA_URL",
                secret_or_env("alpaca", "data_base_url", "ALPACA_DATA_BASE_URL", ALPACA_DATA_BASE_URL),
            )
            or ALPACA_DATA_BASE_URL
        ).strip(),
    }


def alpaca_credential_fingerprint(api_key_id: str) -> str:
    if not api_key_id:
        return "missing"
    return f"{len(api_key_id)}:{api_key_id[-4:]}"


@st.cache_data(ttl=60, show_spinner=False)
def cached_alpaca_latest_bars(
    tickers: tuple[str, ...],
    feed: str,
    base_url: str,
    credential_fingerprint: str,
    _api_key_id: str,
    _api_secret_key: str,
) -> MarketDataResult:
    del credential_fingerprint
    return fetch_alpaca_latest_bars(
        tickers,
        _api_key_id,
        _api_secret_key,
        feed=feed,
        base_url=base_url,
    )


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def cached_alpaca_historical_bars(
    tickers: tuple[str, ...],
    start: str,
    end: str,
    feed: str,
    adjustment: str,
    base_url: str,
    credential_fingerprint: str,
    _api_key_id: str,
    _api_secret_key: str,
) -> HistoricalBarsResult:
    del credential_fingerprint
    return fetch_alpaca_historical_bars(
        tickers,
        _api_key_id,
        _api_secret_key,
        start=start,
        end=end,
        feed=feed,
        adjustment=adjustment,
        base_url=base_url,
    )


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
    if value == "" or pd.isna(value):
        return ""
    return f"${float(value):,.{digits}f}"


def format_pct(value: Any, digits: int = 1) -> str:
    if value == "" or pd.isna(value):
        return ""
    return f"{float(value) * 100:.{digits}f}%"


def format_display_pct(value: Any, digits: int = 1) -> str:
    if value == "" or pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}%"


def format_number(value: Any, digits: int = 0) -> str:
    if value == "" or pd.isna(value):
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
    view_source = df.copy()
    for column in columns:
        if column not in view_source:
            view_source[column] = ""
    view = view_source.loc[:, columns].copy()
    for column, formatter in formatters.items():
        if column in view.columns:
            view[column] = view[column].map(formatter)
    view = view.fillna("")
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
        .decision-brief {
            border-left: 4px solid #111827;
            background: #f9fafb;
            padding: 14px 16px;
            border-radius: 4px;
            color: #1f2937;
            line-height: 1.45;
            margin: 0.5rem 0 1rem 0;
        }
        .decision-brief strong {
            color: #111827;
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

        - No raw Schwab exports are required.
        - Optional simplified portfolio input stays in the Streamlit session.
        - Optional Alpaca market-data lookup is read-only and data-only.
        - No raw broker-export uploads, trade actions, or writebacks.
        - No app-generated trade tickets, broker files, or recommendation downloads.
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
    st.subheader("Long/Short Overlay Detail")
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


def render_strategy_disclaimer() -> None:
    st.markdown(
        """
        <div class="security-note">
        This section is educational decision support only. It is not tax, legal, or investment advice.
        Short sales, hedges, options, wash sales, straddles, constructive sales, exchange funds, charitable
        transfers, and concentrated positions should be reviewed with qualified tax and investment professionals.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_priority_controls(
    key_prefix: str,
    expanded: bool = True,
    title: str = "Assumptions and priority weights",
) -> tuple[dict[str, float], dict[str, Any], dict[str, float]]:
    with st.expander(title, expanded=expanded):
        c1, c2, c3, c4 = st.columns(4)
        transition_years = int(
            c1.number_input(
                "Gradual sale years",
                min_value=1,
                max_value=20,
                value=3,
                step=1,
                key=f"{key_prefix}_transition_years",
            )
        )
        user_horizon_years = int(
            c2.number_input(
                "Decision horizon years",
                min_value=1,
                max_value=30,
                value=5,
                step=1,
                key=f"{key_prefix}_user_horizon_years",
            )
        )
        loss_offset_budget = float(
            c3.number_input(
                "Available harvested losses",
                min_value=0.0,
                value=0.0,
                step=50000.0,
                format="%.0f",
                key=f"{key_prefix}_loss_offset_budget",
            )
        )
        philanthropic_intent = bool(c4.checkbox("Charitable intent", value=False, key=f"{key_prefix}_charitable_intent"))

        st.caption("Priority weights control the ranking engine. Higher values give that criterion more influence.")
        priority_columns = st.columns(4)
        priorities: dict[str, float] = {}
        for index, (key, default) in enumerate(DEFAULT_STRATEGY_PRIORITIES.items()):
            label = key.replace("_", " ").title()
            priorities[key] = float(
                priority_columns[index % 4].slider(
                    label,
                    min_value=0,
                    max_value=5,
                    value=int(default),
                    step=1,
                    key=f"{key_prefix}_priority_{key}",
                )
            )

        st.caption("Long/short assumption controls affect hedge ranking and implementation-risk scoring.")
        h1, h2, h3 = st.columns(3)
        hedge_assumptions = {
            "annual_borrow_cost_rate": float(
                h1.number_input(
                    "Annual borrow/carry cost",
                    min_value=0.0,
                    max_value=0.25,
                    value=float(DEFAULT_HEDGE_ASSUMPTIONS["annual_borrow_cost_rate"]),
                    step=0.0025,
                    format="%.4f",
                    key=f"{key_prefix}_borrow_cost",
                )
            ),
            "liquidity_requirement": float(
                h2.slider(
                    "Liquidity requirement",
                    min_value=0,
                    max_value=100,
                    value=int(DEFAULT_HEDGE_ASSUMPTIONS["liquidity_requirement"]),
                    step=5,
                    key=f"{key_prefix}_liquidity_requirement",
                )
            ),
            "tax_complexity_tolerance": float(
                h3.slider(
                    "Tax complexity tolerance",
                    min_value=1,
                    max_value=5,
                    value=int(DEFAULT_HEDGE_ASSUMPTIONS["tax_complexity_tolerance"]),
                    step=1,
                    key=f"{key_prefix}_tax_complexity_tolerance",
                )
            ),
        }

    assumptions = {
        "transition_years": transition_years,
        "user_horizon_years": user_horizon_years,
        "loss_offset_budget": loss_offset_budget,
        "philanthropic_intent": philanthropic_intent,
    }
    return priorities, assumptions, hedge_assumptions


def render_market_data_qa(qa: pd.DataFrame) -> None:
    if qa is None or qa.empty:
        return
    view = qa.copy()
    for column in ["Start", "End"]:
        if column in view:
            view[column] = view[column].map(
                lambda value: value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value or "")
            )
    render_static_table(
        view,
        ["Dataset", "Ticker", "Rows", "Start", "End", "Feed", "Source", "Status"],
        {
            "Dataset": "Dataset",
            "Ticker": "Ticker",
            "Rows": "Rows",
            "Start": "Start",
            "End": "End",
            "Feed": "Feed",
            "Source": "Source",
            "Status": "Status",
        },
        {"Rows": lambda x: format_number(x, 0)},
    )


def extract_portfolio_tickers(raw_portfolio: pd.DataFrame) -> tuple[str, ...]:
    if raw_portfolio is None or raw_portfolio.empty:
        return ()
    for column in raw_portfolio.columns:
        normalized = str(column).strip().lower().replace(" ", "_")
        if normalized in {"ticker", "symbol", "security"}:
            return clean_tickers(raw_portfolio[column])
    return ()


def return_universe_from_portfolio(raw_portfolio: pd.DataFrame, risk: pd.DataFrame | None = None) -> tuple[str, ...]:
    tickers = set(extract_portfolio_tickers(raw_portfolio))
    if risk is not None and not risk.empty and {"target", "proxy"}.issubset(risk.columns):
        portfolio_tickers = {ticker.upper() for ticker in tickers}
        risk_rows = risk[risk["target"].astype(str).str.upper().isin(portfolio_tickers)]
        tickers.update(clean_tickers(risk_rows["proxy"]))
    return clean_tickers(tickers)


def render_market_price_source(raw_portfolio: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    st.subheader("Market Price Source")
    source = st.radio(
        "Current price source",
        ["Manual / uploaded prices", "Alpaca latest bars"],
        horizontal=True,
        key=f"{key_prefix}_market_price_source",
        help="Alpaca only updates current prices and market values. Cost basis, holding period, tax rates, and target weights remain manual inputs.",
    )
    if source == "Manual / uploaded prices":
        st.caption("Using the prices entered in the table above. This is also the fallback whenever Alpaca is unavailable.")
        return raw_portfolio

    config = alpaca_config()
    feed_default = config["feed"] if config["feed"] in ALPACA_SUPPORTED_FEEDS else "iex"
    c1, c2 = st.columns([1, 2])
    feed = c1.selectbox(
        "Alpaca data feed",
        list(ALPACA_SUPPORTED_FEEDS),
        index=list(ALPACA_SUPPORTED_FEEDS).index(feed_default),
        key=f"{key_prefix}_alpaca_feed",
        help="Feed availability depends on the Alpaca market-data subscription.",
    )
    recompute_weights = c2.checkbox(
        "Recompute current weights from refreshed market values",
        value=False,
        key=f"{key_prefix}_alpaca_recompute_weights",
        help=(
            "Leave off when the entered current weights are account-level weights from another source. "
            "Turn on only when the rows represent the whole portfolio denominator you want to analyze."
        ),
    )

    tickers = extract_portfolio_tickers(raw_portfolio)
    if not tickers:
        st.info("Enter at least one ticker before requesting Alpaca prices. Manual prices remain in use.")
        return raw_portfolio

    api_key_id, api_secret_key = alpaca_credentials()
    st.caption(
        "Alpaca credentials: "
        + ("configured" if api_key_id and api_secret_key else "not found")
        + ". Accepted formats: `[alpaca] api_key_id` / `api_secret_key`, or root-level `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`."
    )
    if st.button("Refresh Alpaca prices", key=f"{key_prefix}_alpaca_refresh"):
        cached_alpaca_latest_bars.clear()

    result = cached_alpaca_latest_bars(
        tickers,
        feed,
        config["base_url"],
        alpaca_credential_fingerprint(api_key_id),
        api_key_id,
        api_secret_key,
    )

    if result.status == "loaded" and result.fallback_to_manual:
        st.warning(result.message)
    elif result.status == "loaded":
        st.success(result.message)
    else:
        st.warning(result.message)
        return raw_portfolio

    prices_frame = market_prices_to_frame(result.prices)
    if not prices_frame.empty:
        render_static_table(
            prices_frame,
            ["Ticker", "Price", "Timestamp", "Feed", "Source"],
            {
                "Ticker": "Ticker",
                "Price": "Latest Bar Close",
                "Timestamp": "Bar Time",
                "Feed": "Feed",
                "Source": "Source",
            },
            {"Price": lambda x: format_dollars(x, 2)},
        )
    qa = market_data_qa_frame(latest_result=result)
    if not qa.empty:
        with st.expander("Latest price QA", expanded=False):
            render_market_data_qa(qa)

    return apply_market_prices_to_portfolio(
        raw_portfolio,
        result.prices,
        recompute_current_weights=recompute_weights,
    )


def render_portfolio_input(cluster_summary: pd.DataFrame, key_prefix: str, show_help: bool = True) -> pd.DataFrame:
    st.subheader("Portfolio Input")
    sample = build_sample_portfolio_from_cluster_summary(cluster_summary)
    source = st.radio(
        "Input source",
        ["Sample from model outputs", "Upload simplified CSV", "Manual editor"],
        horizontal=True,
        key=f"{key_prefix}_portfolio_source",
    )

    if source == "Upload simplified CSV":
        uploaded = st.file_uploader(
            "Upload simplified portfolio CSV",
            type=["csv"],
            help="Expected fields include ticker, shares, current price, cost basis, holding period, current weight, target weight, and tax rates.",
            key=f"{key_prefix}_portfolio_upload",
        )
        if uploaded is not None:
            raw_portfolio = pd.read_csv(uploaded)
        else:
            st.info("Using sample data until a simplified CSV is uploaded.")
            raw_portfolio = sample
    elif source == "Manual editor":
        raw_portfolio = pd.DataFrame(
            [
                {
                    "Ticker": "",
                    "Shares": 0.0,
                    "Current Price": 0.0,
                    "Cost Basis": 0.0,
                    "Holding Period": "Long Term",
                    "Current Weight": 0.0,
                    "Target Weight": 0.0,
                    "Federal LTCG Rate": 0.20,
                    "Federal ST Rate": 0.37,
                    "NIIT Rate": 0.038,
                    "State Tax Rate": 0.093,
                }
            ]
        )
    else:
        raw_portfolio = sample

    edited = st.data_editor(
        raw_portfolio,
        hide_index=True,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Ticker": st.column_config.TextColumn(width="small"),
            "Holding Period": st.column_config.SelectboxColumn(
                options=["Long Term", "Short Term", "Unknown"],
                width="small",
            ),
            "Shares": st.column_config.NumberColumn(format="%.4f"),
            "Current Price": st.column_config.NumberColumn(format="$%.2f"),
            "Cost Basis": st.column_config.NumberColumn(format="$%.0f"),
            "Current Weight": st.column_config.NumberColumn(format="%.4f"),
            "Target Weight": st.column_config.NumberColumn(format="%.4f"),
            "Federal LTCG Rate": st.column_config.NumberColumn(format="%.3f"),
            "Federal ST Rate": st.column_config.NumberColumn(format="%.3f"),
            "NIIT Rate": st.column_config.NumberColumn(format="%.3f"),
            "State Tax Rate": st.column_config.NumberColumn(format="%.3f"),
        },
        key=f"{key_prefix}_portfolio_editor",
    )

    if show_help:
        with st.expander("Accepted simplified CSV fields"):
            st.markdown(
                """
                The parser accepts common aliases for ticker/symbol, shares/quantity, current price, market value,
                total cost basis, basis per share, holding period, current portfolio weight, target weight, federal
                long-term rate, federal short-term rate, NIIT rate, and state tax rate. Percent fields can be entered
                as decimals such as `0.20` or whole percents such as `20`.
                """
            )
    return render_market_price_source(edited, key_prefix)


def render_return_data_input(
    bundled_returns: pd.DataFrame | None = None,
    key_prefix: str = "returns",
    alpaca_tickers: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    st.subheader("Daily Return Data")
    source = st.radio(
        "Return data source",
        ["Upload / bundled returns", "Alpaca historical bars"],
        horizontal=True,
        key=f"{key_prefix}_return_data_source",
        help="Daily returns drive hedge beta, correlation, drawdown, and regime analysis when available.",
    )

    fallback_returns = normalize_return_frame(bundled_returns)
    if source == "Upload / bundled returns":
        uploaded = st.file_uploader(
            "Optional daily returns or prices CSV",
            type=["csv"],
            help="Accepted formats: long date/ticker/return, long date/ticker/price, or wide date plus one ticker column each.",
            key=f"{key_prefix}_daily_returns_upload",
        )
        if uploaded is not None:
            raw_returns = pd.read_csv(uploaded)
        elif bundled_returns is not None and not bundled_returns.empty:
            raw_returns = bundled_returns
        else:
            raw_returns = pd.DataFrame()

        returns = normalize_return_frame(raw_returns)
        if returns.empty:
            st.info("No daily return file is loaded. Hedge and regime results will use the existing summary proxy evidence.")
        else:
            start = returns["date"].min().date()
            end = returns["date"].max().date()
            tickers = returns["ticker"].nunique()
            st.caption(f"Loaded {len(returns):,} return rows for {tickers:,} tickers from {start} to {end}.")
        return returns

    config = alpaca_config()
    api_key_id, api_secret_key = alpaca_credentials()
    tickers = clean_tickers(alpaca_tickers or ())
    default_start, default_end = default_history_window(3)
    c1, c2, c3, c4 = st.columns(4)
    start_date = c1.date_input("History start", value=default_start, key=f"{key_prefix}_alpaca_history_start")
    end_date = c2.date_input("History end", value=default_end, key=f"{key_prefix}_alpaca_history_end")
    feed_default = config["feed"] if config["feed"] in ALPACA_HISTORICAL_FEEDS else "iex"
    feed = c3.selectbox(
        "History feed",
        list(ALPACA_HISTORICAL_FEEDS),
        index=list(ALPACA_HISTORICAL_FEEDS).index(feed_default),
        key=f"{key_prefix}_alpaca_history_feed",
        help="Historical bars currently use Alpaca's historical-bar feeds. Use IEX first if SIP is not enabled.",
    )
    adjustment = c4.selectbox(
        "Adjustment",
        ["all", "split", "raw", "dividend"],
        index=0,
        key=f"{key_prefix}_alpaca_history_adjustment",
        help="Adjusted bars reduce artificial return jumps from splits, dividends, and similar corporate actions.",
    )

    st.caption(
        "Alpaca credentials: "
        + ("configured" if api_key_id and api_secret_key else "not found")
        + f". Return universe includes {len(tickers):,} portfolio/proxy tickers."
    )
    if not tickers:
        st.info("No tickers are available for Alpaca history. Add portfolio tickers first.")
        return fallback_returns
    if start_date >= end_date:
        st.warning("History start must be before history end. Using uploaded or bundled returns for now.")
        return fallback_returns
    if st.button("Refresh Alpaca return history", key=f"{key_prefix}_alpaca_history_refresh"):
        cached_alpaca_historical_bars.clear()

    result = cached_alpaca_historical_bars(
        tickers,
        start_date.isoformat(),
        end_date.isoformat(),
        feed,
        adjustment,
        config["base_url"],
        alpaca_credential_fingerprint(api_key_id),
        api_key_id,
        api_secret_key,
    )

    if result.status == "loaded" and result.fallback_to_manual:
        st.warning(result.message)
    elif result.status == "loaded":
        st.success(result.message)
    else:
        st.warning(result.message)
        return fallback_returns

    qa = market_data_qa_frame(historical_result=result)
    if not qa.empty:
        with st.expander("Historical return QA", expanded=True):
            render_market_data_qa(qa)
            st.caption(
                "Rows are historical bars by ticker. Daily returns are computed from close-to-close percentage changes."
            )
    return result.returns


def render_sensitivity_tables(sensitivity_tables: dict[str, pd.DataFrame]) -> None:
    st.subheader("Scenario and Sensitivity Analysis")
    tax_rate = sensitivity_tables.get("tax_rate", pd.DataFrame())
    if not tax_rate.empty:
        st.caption("Tax-rate sensitivity uses the same sale-to-target fractions and available harvested-loss budget.")
        tax_display = percent_display(tax_rate, ["tax_rate_delta"])
        render_static_table(
            tax_display,
            ["tax_rate_delta", "realized_gain", "estimated_tax"],
            {
                "tax_rate_delta": "Tax-Rate Shock",
                "realized_gain": "Realized Gain",
                "estimated_tax": "Estimated Tax",
            },
            {
                "tax_rate_delta": format_display_pct,
                "realized_gain": format_dollars,
                "estimated_tax": format_dollars,
            },
        )

    with st.expander("Price drawdown sensitivity", expanded=False):
        drawdown = sensitivity_tables.get("price_drawdown", pd.DataFrame())
        if not drawdown.empty:
            st.caption("Price shocks keep the current sale fractions fixed; target weights are not recomputed after each shock.")
            drawdown_display = percent_display(drawdown, ["price_shock"])
            render_static_table(
                drawdown_display,
                ["ticker", "price_shock", "sale_value", "realized_gain", "estimated_tax"],
                {
                    "ticker": "Ticker",
                    "price_shock": "Price Shock",
                    "sale_value": "Sale Value",
                    "realized_gain": "Realized Gain",
                    "estimated_tax": "Estimated Tax",
                },
                {
                    "price_shock": format_display_pct,
                    "sale_value": format_dollars,
                    "realized_gain": format_dollars,
                    "estimated_tax": format_dollars,
                },
            )

    with st.expander("Hedge correlation-breakdown sensitivity", expanded=False):
        hedge = sensitivity_tables.get("hedge_correlation", pd.DataFrame())
        if not hedge.empty:
            hedge_display = percent_display(hedge, ["correlation_multiplier", "stressed_correlation", "tracking_error", "volatility_reduction"])
            render_static_table(
                hedge_display,
                [
                    "ticker",
                    "hedge_type",
                    "proposed_hedge",
                    "correlation_multiplier",
                    "stressed_correlation",
                    "tracking_error",
                    "volatility_reduction",
                ],
                {
                    "ticker": "Ticker",
                    "hedge_type": "Hedge Type",
                    "proposed_hedge": "Hedge",
                    "correlation_multiplier": "Correlation Multiplier",
                    "stressed_correlation": "Stressed Correlation",
                    "tracking_error": "Tracking Error",
                    "volatility_reduction": "Vol Reduction",
                },
                {
                    "correlation_multiplier": format_display_pct,
                    "stressed_correlation": format_display_pct,
                    "tracking_error": format_display_pct,
                    "volatility_reduction": format_display_pct,
                },
            )

    with st.expander("Loss-harvest shortfall sensitivity", expanded=False):
        loss = sensitivity_tables.get("loss_shortfall", pd.DataFrame())
        if not loss.empty:
            st.caption("Coverage rows are hypothetical offsets against the sale-to-target gain, not a claim that those losses exist.")
            loss_display = percent_display(loss, ["loss_offset_coverage"])
            render_static_table(
                loss_display,
                [
                    "loss_offset_coverage",
                    "loss_offset_budget",
                    "loss_offset_used",
                    "remaining_unoffset_gain",
                    "estimated_tax",
                ],
                {
                    "loss_offset_coverage": "Loss Offset Coverage",
                    "loss_offset_budget": "Loss Offset Budget",
                    "loss_offset_used": "Loss Offset Used",
                    "remaining_unoffset_gain": "Remaining Unoffset Gain",
                    "estimated_tax": "Estimated Tax",
                },
                {
                    "loss_offset_coverage": format_display_pct,
                    "loss_offset_budget": format_dollars,
                    "loss_offset_used": format_dollars,
                    "remaining_unoffset_gain": format_dollars,
                    "estimated_tax": format_dollars,
                },
            )


def render_decision_brief(results: dict[str, pd.DataFrame]) -> None:
    portfolio_summary = results["portfolio_summary"].iloc[0]
    strategy_summary = results["portfolio_strategy_summary"]
    top_strategy = str(portfolio_summary["top_portfolio_strategy"])
    selected = strategy_summary[strategy_summary["strategy"] == top_strategy]
    row = selected.iloc[0] if not selected.empty else pd.Series(dtype=object)
    estimated_tax = format_dollars(row.get("estimated_tax", 0.0))
    sale_value = format_dollars(row.get("sale_value", 0.0))
    realized_gain = format_dollars(row.get("realized_gain", 0.0))
    current_weight = format_pct(portfolio_summary["current_portfolio_weight"])
    target_weight = format_pct(portfolio_summary["target_portfolio_weight"])

    st.subheader("Decision Brief")
    st.markdown(
        f"""
        <div class="decision-brief">
        <strong>Question:</strong> how much concentration can be reduced without creating an unacceptable tax or implementation burden?<br>
        <strong>Current read:</strong> the analyzed positions are {current_weight} of the account versus a modeled target of {target_weight}.<br>
        <strong>Model answer:</strong> {top_strategy} is currently highest-ranked, with about {sale_value} of modeled sales,
        {realized_gain} of realized gain, and {estimated_tax} of estimated tax before professional review.<br>
        <strong>Decision gate:</strong> use the plan tab to choose the strategy, set a tax budget, assign review owners, and stop before trading if the checklist is not complete.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_normalized_portfolio_table(portfolio: pd.DataFrame) -> None:
    portfolio_display = percent_display(
        portfolio,
        [
            "unrealized_gain_pct",
            "current_weight",
            "target_weight",
            "sale_fraction_to_target",
            "gain_tax_rate",
        ],
    )
    render_static_table(
        portfolio_display,
        [
            "ticker",
            "shares",
            "current_price",
            "market_value",
            "cost_basis",
            "unrealized_gain",
            "unrealized_gain_pct",
            "holding_period",
            "current_weight",
            "target_weight",
            "sale_fraction_to_target",
            "gain_tax_rate",
        ],
        {
            "ticker": "Ticker",
            "shares": "Shares",
            "current_price": "Price",
            "market_value": "Market Value",
            "cost_basis": "Cost Basis",
            "unrealized_gain": "Unrealized Gain",
            "unrealized_gain_pct": "Gain / Value",
            "holding_period": "Holding Period",
            "current_weight": "Current Weight",
            "target_weight": "Target Weight",
            "sale_fraction_to_target": "Sale To Target",
            "gain_tax_rate": "Modeled Gain Tax Rate",
        },
        {
            "shares": lambda x: format_number(x, 2),
            "current_price": lambda x: format_dollars(x, 2),
            "market_value": format_dollars,
            "cost_basis": format_dollars,
            "unrealized_gain": format_dollars,
            "unrealized_gain_pct": format_display_pct,
            "current_weight": format_display_pct,
            "target_weight": format_display_pct,
            "sale_fraction_to_target": format_display_pct,
            "gain_tax_rate": format_display_pct,
        },
    )


def render_long_short_summary(long_short: pd.DataFrame) -> None:
    if long_short.empty:
        st.info("No long/short hedge evidence is available for the selected positions.")
        return
    if "hedge_type" not in long_short or "ticker" not in long_short:
        st.info("Long/short evidence is incomplete. Add proxy correlation data before using the hedge summary.")
        return

    available = long_short[long_short["hedge_type"].astype(str) != "Data unavailable"].copy()
    unavailable = sorted(set(long_short.loc[long_short["hedge_type"].astype(str) == "Data unavailable", "ticker"].astype(str)))
    if available.empty:
        st.info("No positions have enough proxy evidence for a hedge summary. Add daily returns or proxy correlations.")
        return

    top_hedges = (
        available.sort_values(["ticker", "rank_score"], ascending=[True, False])
        .groupby("ticker", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    st.caption("Top hedge per ticker. Treat this as research evidence, not automatic permission to short or hedge.")
    if unavailable:
        st.caption(f"No hedge evidence is available for: {', '.join(unavailable)}.")
    top_display = percent_display(
        top_hedges,
        ["tracking_error", "volatility_reduction", "maximum_drawdown_impact"],
    )
    render_static_table(
        top_display,
        [
            "ticker",
            "hedge_type",
            "proposed_hedge",
            "hedge_ratio",
            "historical_correlation",
            "historical_beta",
            "tracking_error",
            "volatility_reduction",
            "maximum_drawdown_impact",
            "return_data_source",
        ],
        {
            "ticker": "Ticker",
            "hedge_type": "Best Hedge Type",
            "proposed_hedge": "Instrument / Basket",
            "hedge_ratio": "Hedge Ratio",
            "historical_correlation": "Correlation",
            "historical_beta": "Beta",
            "tracking_error": "Tracking Error",
            "volatility_reduction": "Vol Reduction",
            "maximum_drawdown_impact": "Drawdown Impact (Est.)",
            "return_data_source": "Evidence Source",
        },
        {
            "hedge_ratio": lambda x: format_number(x, 2),
            "historical_correlation": lambda x: format_number(x, 2),
            "historical_beta": lambda x: format_number(x, 2),
            "tracking_error": format_display_pct,
            "volatility_reduction": format_display_pct,
            "maximum_drawdown_impact": format_display_pct,
        },
    )


def render_sma_study_controls(key_prefix: str) -> tuple[dict[str, float], dict[str, float]]:
    with st.expander("SMA study assumptions", expanded=False):
        st.caption("Higher priority means the SMA design score gives that criterion more influence.")
        priority_columns = st.columns(3)
        priorities: dict[str, float] = {}
        for index, (key, default) in enumerate(DEFAULT_SMA_STUDY_PRIORITIES.items()):
            priorities[key] = float(
                priority_columns[index % 3].slider(
                    key.replace("_", " ").title(),
                    min_value=0,
                    max_value=5,
                    value=int(default),
                    step=1,
                    key=f"{key_prefix}_sma_priority_{key}",
                )
            )

        st.caption("These assumptions affect borrow, liquidity, and tax-complexity tradeoffs in the SMA comparison.")
        h1, h2, h3 = st.columns(3)
        hedge_assumptions = {
            "annual_borrow_cost_rate": float(
                h1.number_input(
                    "Annual borrow/carry cost",
                    min_value=0.0,
                    max_value=0.25,
                    value=float(DEFAULT_HEDGE_ASSUMPTIONS["annual_borrow_cost_rate"]),
                    step=0.0025,
                    format="%.4f",
                    key=f"{key_prefix}_sma_borrow_cost",
                )
            ),
            "liquidity_requirement": float(
                h2.slider(
                    "Liquidity requirement",
                    min_value=0,
                    max_value=100,
                    value=int(DEFAULT_HEDGE_ASSUMPTIONS["liquidity_requirement"]),
                    step=5,
                    key=f"{key_prefix}_sma_liquidity_requirement",
                )
            ),
            "tax_complexity_tolerance": float(
                h3.slider(
                    "Tax complexity tolerance",
                    min_value=1,
                    max_value=5,
                    value=int(DEFAULT_HEDGE_ASSUMPTIONS["tax_complexity_tolerance"]),
                    step=1,
                    key=f"{key_prefix}_sma_tax_complexity_tolerance",
                )
            ),
        }
    return priorities, hedge_assumptions


def render_sma_study(
    cluster_summary: pd.DataFrame,
    risk: pd.DataFrame,
    bundled_returns: pd.DataFrame | None = None,
) -> None:
    render_strategy_disclaimer()
    st.subheader("Long/Short SMA Study")
    st.caption(
        "Compare conservative, balanced, hedge-focused, and aggressive long/short SMA designs as implementation candidates."
    )
    st.markdown(
        """
        <div class="decision-brief">
        <strong>Study question:</strong> which diversified long/short SMA mandate best supports a taxable transition
        from concentrated stock into broader equity exposure?<br>
        <strong>Use this screen for:</strong> comparing mandate designs, framing manager diligence, and identifying
        tax/legal review questions before any implementation decision.
        </div>
        """,
        unsafe_allow_html=True,
    )

    sma_priorities, hedge_assumptions = render_sma_study_controls("sma_study")
    with st.expander("Portfolio input used for SMA study", expanded=False):
        raw_portfolio = render_portfolio_input(cluster_summary, "sma_study", show_help=False)
    with st.expander("Optional return data used for hedge evidence", expanded=False):
        daily_returns = render_return_data_input(
            bundled_returns,
            "sma_study",
            return_universe_from_portfolio(raw_portfolio, risk),
        )

    normalized_preview = normalize_portfolio_frame(raw_portfolio)
    if normalized_preview.empty:
        st.warning("Enter at least one ticker with a market value or shares and price.")
        return

    results = run_transition_analysis(
        raw_portfolio,
        risk,
        daily_returns=daily_returns,
        hedge_assumptions=hedge_assumptions,
    )
    portfolio = results["portfolio"]
    comparison = evaluate_sma_designs(
        portfolio,
        results["long_short_table"],
        priorities=sma_priorities,
        hedge_assumptions=hedge_assumptions,
    )
    if comparison.empty:
        st.info("No SMA design comparison is available for the selected inputs.")
        return

    top = comparison.iloc[0]
    portfolio_summary = results["portfolio_summary"].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Study selection", str(top["design"]).replace(" SMA", ""))
    c2.metric("Selection score", format_number(top["selection_score"], 1))
    c3.metric("Excess weight", format_pct(portfolio_summary["excess_weight"]))
    c4.metric("Embedded gain", format_dollars(portfolio_summary["total_unrealized_gain"]))

    st.subheader("Side-by-Side Design Comparison")
    st.caption("Scores are 0-100 educational fit scores. Higher is better except explicit risk and complexity columns.")
    render_static_table(
        comparison,
        [
            "rank",
            "design",
            "selection_score",
            "net_exposure",
            "gross_exposure",
            "expected_loss_harvest_potential",
            "expected_tracking_error",
            "tax_loss_capacity_score",
            "concentration_transition_fit_score",
            "risk_control_score",
            "tax_rule_clarity_score",
            "implementation_complexity",
            "liquidity_borrow_risk",
            "tax_rule_risk",
        ],
        {
            "rank": "Rank",
            "design": "Design",
            "selection_score": "Score",
            "net_exposure": "Net Exposure",
            "gross_exposure": "Gross Exposure",
            "expected_loss_harvest_potential": "Loss-Harvest Potential",
            "expected_tracking_error": "Tracking Error",
            "tax_loss_capacity_score": "Tax-Loss Capacity",
            "concentration_transition_fit_score": "Transition Fit",
            "risk_control_score": "Risk Control",
            "tax_rule_clarity_score": "Tax-Rule Clarity",
            "implementation_complexity": "Complexity Risk",
            "liquidity_borrow_risk": "Liquidity/Borrow Risk",
            "tax_rule_risk": "Tax-Rule Risk",
        },
        {
            "rank": lambda x: format_number(x, 0),
            "selection_score": lambda x: format_number(x, 1),
            "tax_loss_capacity_score": lambda x: format_number(x, 1),
            "concentration_transition_fit_score": lambda x: format_number(x, 1),
            "risk_control_score": lambda x: format_number(x, 1),
            "tax_rule_clarity_score": lambda x: format_number(x, 1),
            "implementation_complexity": lambda x: format_number(x, 1),
            "liquidity_borrow_risk": lambda x: format_number(x, 1),
            "tax_rule_risk": lambda x: format_number(x, 1),
        },
    )

    with st.expander("Mandate architecture", expanded=True):
        render_static_table(
            comparison,
            [
                "design",
                "description",
                "long_book",
                "short_book",
                "estimated_fee_carry",
                "best_hedge_evidence",
                "hedge_evidence_source",
            ],
            {
                "design": "Design",
                "description": "Mandate",
                "long_book": "Long Book",
                "short_book": "Short Book",
                "estimated_fee_carry": "Cost / Carry",
                "best_hedge_evidence": "Hedge Evidence",
                "hedge_evidence_source": "Evidence Source",
            },
        )

    st.subheader("How To Choose")
    decision_rows = comparison.loc[
        :,
        [
            "design",
            "why_selected_over_alternatives",
            "best_when",
            "avoid_when",
            "professional_review_flags",
        ],
    ]
    render_static_table(
        decision_rows,
        list(decision_rows.columns),
        {
            "design": "Design",
            "why_selected_over_alternatives": "Model Rationale",
            "best_when": "Best When",
            "avoid_when": "Avoid When",
            "professional_review_flags": "Professional Review Flags",
        },
    )

    st.subheader("Manager Due Diligence Checklist")
    checklist = build_sma_due_diligence_checklist(str(top["design"]))
    render_static_table(
        checklist,
        ["Review Area", "Question", "Evidence Needed"],
        {
            "Review Area": "Review Area",
            "Question": "Question",
            "Evidence Needed": "Evidence Needed",
        },
    )


def default_completion_window(strategy: str, transition_years: int) -> str:
    strategy_lower = strategy.lower()
    if "gradually" in strategy_lower:
        return f"{transition_years} tax years"
    if "sell immediately" in strategy_lower:
        return "After approvals / current tax year"
    if "hold and monitor" in strategy_lower:
        return "Monitor quarterly"
    if "charitable" in strategy_lower:
        return "Before year-end if contribution is approved"
    if "long/short" in strategy_lower or "hedge" in strategy_lower:
        return "Research now; execute only after tax/legal approval"
    return f"{transition_years} tax years or as approved"


def render_strategy_lab(cluster_summary: pd.DataFrame, risk: pd.DataFrame, bundled_returns: pd.DataFrame | None = None) -> None:
    render_strategy_disclaimer()
    priorities, assumptions, hedge_assumptions = render_priority_controls(
        "strategy_lab",
        expanded=False,
        title="Strategy assumptions",
    )
    with st.expander("Portfolio input", expanded=False):
        raw_portfolio = render_portfolio_input(cluster_summary, "strategy_lab", show_help=False)
    with st.expander("Optional daily return data", expanded=False):
        daily_returns = render_return_data_input(
            bundled_returns,
            "strategy_lab",
            return_universe_from_portfolio(raw_portfolio, risk),
        )
    normalized_preview = normalize_portfolio_frame(raw_portfolio)

    if normalized_preview.empty:
        st.warning("Enter at least one ticker with a market value or shares and price.")
        return

    results = run_transition_analysis(
        raw_portfolio,
        risk,
        daily_returns=daily_returns,
        loss_offset_budget=assumptions["loss_offset_budget"],
        transition_years=assumptions["transition_years"],
        user_horizon_years=assumptions["user_horizon_years"],
        philanthropic_intent=assumptions["philanthropic_intent"],
        priorities=priorities,
        hedge_assumptions=hedge_assumptions,
    )

    portfolio = results["portfolio"]
    portfolio_summary = results["portfolio_summary"].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analyzed value", format_dollars(portfolio_summary["total_market_value"]))
    c2.metric("Embedded gain", format_dollars(portfolio_summary["total_unrealized_gain"]))
    c3.metric("Current weight", format_pct(portfolio_summary["current_portfolio_weight"]))
    c4.metric("Target weight", format_pct(portfolio_summary["target_portfolio_weight"]))

    render_decision_brief(results)

    st.subheader("Portfolio-Level Recommendation Summary")
    st.markdown(f"**Top portfolio-level strategy:** {portfolio_summary['top_portfolio_strategy']}")
    portfolio_strategy = results["portfolio_strategy_summary"]
    portfolio_strategy_display = percent_display(
        portfolio_strategy,
        ["average_concentration_reduction"],
    )
    render_static_table(
        portfolio_strategy_display,
        [
            "strategy",
            "weighted_rank_score",
            "estimated_tax",
            "sale_value",
            "realized_gain",
            "average_concentration_reduction",
            "average_complexity",
            "average_tax_uncertainty",
        ],
        {
            "strategy": "Strategy",
            "weighted_rank_score": "Weighted Score",
            "estimated_tax": "Estimated Tax",
            "sale_value": "Sale Value",
            "realized_gain": "Realized Gain",
            "average_concentration_reduction": "Avg. Target Gap Addressed",
            "average_complexity": "Avg. Complexity",
            "average_tax_uncertainty": "Avg. Tax-Rule Uncertainty",
        },
        {
            "weighted_rank_score": lambda x: format_number(x, 1),
            "estimated_tax": format_dollars,
            "sale_value": format_dollars,
            "realized_gain": format_dollars,
            "average_concentration_reduction": format_display_pct,
            "average_complexity": lambda x: format_number(x, 1),
            "average_tax_uncertainty": lambda x: format_number(x, 1),
        },
    )

    st.subheader("Position-Level Recommendation Summary")
    position_summary = results["position_summary"]
    position_display = percent_display(position_summary, ["concentration_reduction"])
    render_static_table(
        position_display,
        [
            "ticker",
            "strategy",
            "rank_score",
            "estimated_tax",
            "sale_value",
            "realized_gain",
            "loss_offset_used",
            "concentration_reduction",
            "assumptions",
        ],
        {
            "ticker": "Ticker",
            "strategy": "Recommended Strategy",
            "rank_score": "Score",
            "estimated_tax": "Estimated Tax",
            "sale_value": "Sale Value",
            "realized_gain": "Realized Gain",
            "loss_offset_used": "Loss Offset Used",
            "concentration_reduction": "Target Gap Addressed",
            "assumptions": "Assumptions",
        },
        {
            "rank_score": lambda x: format_number(x, 1),
            "estimated_tax": format_dollars,
            "sale_value": format_dollars,
            "realized_gain": format_dollars,
            "loss_offset_used": format_dollars,
            "concentration_reduction": format_display_pct,
        },
    )

    with st.expander("Normalized portfolio detail", expanded=False):
        st.caption("Parser output used by the scoring engine. Review this before relying on any strategy ranking.")
        render_normalized_portfolio_table(portfolio)

    with st.expander("Full strategy comparison table", expanded=False):
        strategy_table = results["strategy_table"].copy()
        strategy_display = percent_display(strategy_table, ["concentration_reduction"])
        render_static_table(
            strategy_display,
            [
                "ticker",
                "strategy",
                "rank_score",
                "estimated_tax",
                "sale_value",
                "realized_gain",
                "concentration_reduction",
                "implementation_complexity",
                "liquidity_borrow_risk",
                "tax_rule_uncertainty",
                "time_horizon_fit",
            ],
            {
                "ticker": "Ticker",
                "strategy": "Strategy",
                "rank_score": "Score",
                "estimated_tax": "Estimated Tax",
                "sale_value": "Sale Value",
                "realized_gain": "Realized Gain",
                "concentration_reduction": "Target Gap Addressed",
                "implementation_complexity": "Complexity",
                "liquidity_borrow_risk": "Liquidity/Borrow Risk",
                "tax_rule_uncertainty": "Tax-Rule Uncertainty",
                "time_horizon_fit": "Time Fit",
            },
            {
                "rank_score": lambda x: format_number(x, 1),
                "estimated_tax": format_dollars,
                "sale_value": format_dollars,
                "realized_gain": format_dollars,
                "concentration_reduction": format_display_pct,
                "implementation_complexity": lambda x: format_number(x, 1),
                "liquidity_borrow_risk": lambda x: format_number(x, 1),
                "tax_rule_uncertainty": lambda x: format_number(x, 1),
                "time_horizon_fit": lambda x: format_number(x, 1),
            },
        )

    render_sensitivity_tables(results["sensitivity_tables"])

    st.subheader("Long/Short Strategy Research")
    long_short = results["long_short_table"]
    st.markdown(long_short_research_markdown(long_short))
    render_long_short_summary(long_short)
    with st.expander("Full long/short evidence table", expanded=False):
        long_short_display = percent_display(
            long_short,
            ["volatility_reduction", "maximum_drawdown_impact", "tracking_error"],
        )
        render_static_table(
            long_short_display,
            [
                "ticker",
                "hedge_type",
                "proposed_hedge",
                "hedge_ratio",
                "historical_correlation",
                "historical_beta",
                "tracking_error",
                "volatility_reduction",
                "maximum_drawdown_impact",
                "drawdown_impact_method",
                "annual_borrow_cost_estimate",
                "liquidity_score",
                "borrow_score",
                "tax_simplicity_score",
                "return_data_source",
                "regime_detection_method",
                "scenario_behavior_by_regime",
                "tax_legal_risk_flags",
                "data_limitations",
                "why_selected_over_alternatives",
            ],
            {
                "ticker": "Ticker",
                "hedge_type": "Hedge Type",
                "proposed_hedge": "Instrument / Basket",
                "hedge_ratio": "Hedge Ratio",
                "historical_correlation": "Correlation",
                "historical_beta": "Beta",
                "tracking_error": "Tracking Error",
                "volatility_reduction": "Vol Reduction",
                "maximum_drawdown_impact": "Drawdown Impact (Est.)",
                "drawdown_impact_method": "Drawdown Method",
                "annual_borrow_cost_estimate": "Annual Borrow Cost",
                "liquidity_score": "Liquidity Score",
                "borrow_score": "Borrow Score",
                "tax_simplicity_score": "Tax Simplicity",
                "return_data_source": "Evidence Source",
                "regime_detection_method": "Regime Method",
                "scenario_behavior_by_regime": "Scenario Behavior by Regime",
                "tax_legal_risk_flags": "Tax / Legal Risk Flags",
                "data_limitations": "Data Limitations",
                "why_selected_over_alternatives": "Why Selected Over Alternatives",
            },
            {
                "hedge_ratio": lambda x: format_number(x, 2),
                "historical_correlation": lambda x: format_number(x, 2),
                "historical_beta": lambda x: format_number(x, 2),
                "tracking_error": format_display_pct,
                "volatility_reduction": format_display_pct,
                "maximum_drawdown_impact": format_display_pct,
                "annual_borrow_cost_estimate": format_dollars,
                "liquidity_score": lambda x: format_number(x, 1),
                "borrow_score": lambda x: format_number(x, 1),
                "tax_simplicity_score": lambda x: format_number(x, 1),
            },
        )

    st.subheader("Research and Rationale")
    for _, row in position_summary.iterrows():
        with st.expander(f"{row['ticker']}: {row['strategy']}", expanded=False):
            st.markdown(f"**Assumptions used:** {row['assumptions']}")
            st.markdown(f"**Pros:** {row['pros']}")
            st.markdown(f"**Cons:** {row['cons']}")
            st.markdown(f"**Key risks:** {row['key_risks']}")
            st.markdown(f"**Situations where it may not apply:** {row['not_applicable_when']}")


def render_status_badge(label: str, status: str) -> None:
    colors = {
        "Complete": "#166534",
        "Approved": "#166534",
        "In Review": "#92400e",
        "Needed": "#991b1b",
        "Not Started": "#991b1b",
        "Not Applicable": "#4b5563",
    }
    color = colors.get(status, "#374151")
    st.markdown(
        f"<span style='display:inline-block;margin:2px 8px 6px 0;color:{color};font-weight:700;'>{label}: {status}</span>",
        unsafe_allow_html=True,
    )


def render_transition_plan_builder(
    cluster_summary: pd.DataFrame,
    risk: pd.DataFrame,
    bundled_returns: pd.DataFrame | None = None,
) -> None:
    render_strategy_disclaimer()
    st.subheader("One-Page Transition Plan Builder")
    st.caption("Use this to turn the analysis into a review-ready draft: decision, tax budget, review gates, and execution rules.")

    st.markdown(
        """
        <div class="decision-brief">
        <strong>Planning flow:</strong> confirm the analysis inputs, choose the strategy, set the tax budget,
        complete the professional-review checklist, then approve execution rules. This screen is a draft plan,
        not a trade authorization.
        </div>
        """,
        unsafe_allow_html=True,
    )

    priorities, assumptions, hedge_assumptions = render_priority_controls(
        "transition_plan",
        expanded=False,
        title="Analysis assumptions used for this plan",
    )
    with st.expander("Portfolio input used for this plan", expanded=False):
        raw_portfolio = render_portfolio_input(cluster_summary, "transition_plan", show_help=False)
    with st.expander("Optional return data used for hedge research", expanded=False):
        daily_returns = render_return_data_input(
            bundled_returns,
            "transition_plan",
            return_universe_from_portfolio(raw_portfolio, risk),
        )
    if normalize_portfolio_frame(raw_portfolio).empty:
        st.warning("Enter at least one ticker with a market value or shares and price.")
        return

    results = run_transition_analysis(
        raw_portfolio,
        risk,
        daily_returns=daily_returns,
        loss_offset_budget=assumptions["loss_offset_budget"],
        transition_years=assumptions["transition_years"],
        user_horizon_years=assumptions["user_horizon_years"],
        philanthropic_intent=assumptions["philanthropic_intent"],
        priorities=priorities,
        hedge_assumptions=hedge_assumptions,
    )

    strategy_options = list(results["portfolio_strategy_summary"]["strategy"]) if not results["portfolio_strategy_summary"].empty else []
    default_strategy = results["portfolio_summary"].iloc[0]["top_portfolio_strategy"]
    strategy_index = strategy_options.index(default_strategy) if default_strategy in strategy_options else 0

    st.subheader("Decision Inputs")
    c1, c2, c3 = st.columns(3)
    plan_owner = c1.text_input("Plan owner", value="Investment team / advisor")
    decision_status = c2.selectbox(
        "Decision status",
        ["Draft", "Ready for professional review", "Approved for execution", "Paused"],
        index=0,
    )
    selected_strategy = c3.selectbox("Chosen strategy", strategy_options, index=strategy_index if strategy_options else 0)

    preliminary = build_transition_plan_summary(results, selected_strategy)
    c4, c5, c6 = st.columns(3)
    max_tax_budget = float(
        c4.number_input(
            "Maximum tax budget",
            min_value=0.0,
            value=float(preliminary["max_tax_budget"]),
            step=50000.0,
            format="%.0f",
        )
    )
    completion_window = c5.text_input(
        "Target completion window",
        value=default_completion_window(selected_strategy, assumptions["transition_years"]),
        key=f"transition_plan_completion_window_{selected_strategy}",
    )
    hedge_permission = c6.selectbox(
        "Hedge permission",
        ["No hedge without further approval", "Research hedge only", "Approved after tax/legal review", "No hedging permitted"],
        index=0,
    )

    plan = build_transition_plan_summary(results, selected_strategy, max_tax_budget)
    objective = st.text_area("Decision objective", value=plan["objective"], height=90)
    implementation_rules = st.text_area(
        "Execution rules",
        value=(
            "Do not trade until tax/legal review is complete.\n"
            "Use lot-level instructions for all sales.\n"
            "Stop and re-review if estimated tax exceeds budget, position price moves materially, or hedge correlation breaks down."
        ),
        height=120,
    )

    st.subheader("One-Page Plan Preview")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Current weight", format_pct(plan["current_weight"]))
    p2.metric("Target weight", format_pct(plan["target_weight"]))
    p3.metric("Estimated tax", format_dollars(plan["estimated_tax"]))
    p4.metric("Tax budget remaining", format_dollars(plan["tax_budget_remaining"]))

    st.markdown(
        f"""
        <div class="security-note">
        <strong>Status:</strong> {decision_status}<br>
        <strong>Owner:</strong> {plan_owner}<br>
        <strong>Objective:</strong> {objective}<br>
        <strong>Chosen strategy:</strong> {selected_strategy}<br>
        <strong>Completion window:</strong> {completion_window}<br>
        <strong>Hedge policy:</strong> {hedge_permission}<br>
        <strong>Hedge evidence:</strong> {plan["hedge_summary"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    plan_rows = pd.DataFrame(
        [
            {"Plan Field": "Total analyzed value", "Plan Value": format_dollars(plan["total_market_value"])},
            {"Plan Field": "Total unrealized gain", "Plan Value": format_dollars(plan["total_unrealized_gain"])},
            {"Plan Field": "Estimated sale value", "Plan Value": format_dollars(plan["estimated_sale_value"])},
            {"Plan Field": "Estimated realized gain", "Plan Value": format_dollars(plan["estimated_realized_gain"])},
            {"Plan Field": "Loss offset used", "Plan Value": format_dollars(plan["loss_offset_used"])},
            {"Plan Field": "After-tax sale proceeds", "Plan Value": format_dollars(plan["after_tax_sale_proceeds"])},
            {"Plan Field": "Maximum tax budget", "Plan Value": format_dollars(plan["max_tax_budget"])},
            {"Plan Field": "Positions analyzed", "Plan Value": format_number(plan["positions_analyzed"], 0)},
        ]
    )
    render_static_table(plan_rows, ["Plan Field", "Plan Value"], {"Plan Field": "Plan Field", "Plan Value": "Plan Value"})

    with st.expander("Position actions", expanded=True):
        st.text(plan["primary_position_actions"] or "No position actions available.")

    with st.expander("Execution rules", expanded=True):
        st.text(implementation_rules)

    st.subheader("Professional Review Checklist")
    st.caption("These gates keep the draft plan from being mistaken for permission to trade.")
    checklist_defaults = pd.DataFrame(
        [
            {"Review Item": "CPA confirms tax rates, gain character, and loss-offset availability", "Owner": "CPA", "Status": "Needed"},
            {"Review Item": "Tax counsel reviews constructive-sale, straddle, wash-sale, and short-against-the-box issues", "Owner": "Tax counsel", "Status": "Needed"},
            {"Review Item": "Investment advisor confirms target allocation and replacement portfolio", "Owner": "Advisor", "Status": "Needed"},
            {"Review Item": "Trading desk confirms liquidity, borrow, margin, and restricted-list constraints", "Owner": "Trading desk", "Status": "Needed"},
            {"Review Item": "Client approves tax budget, risk tradeoff, and implementation window", "Owner": "Client", "Status": "Needed"},
        ]
    )
    checklist = st.data_editor(
        checklist_defaults,
        hide_index=True,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Status": st.column_config.SelectboxColumn(
                options=["Needed", "In Review", "Complete", "Approved", "Not Applicable"],
                width="medium",
            )
        },
        key="transition_plan_checklist",
    )

    st.subheader("Implementation Milestones")
    milestones_default = pd.DataFrame(
        [
            {"Step": 1, "Milestone": "Finalize target weight and tax budget", "Timing": "Before trading", "Owner": "Client / advisor", "Status": "Not Started"},
            {"Step": 2, "Milestone": "Select tax lots and sale schedule", "Timing": "Before first trade", "Owner": "CPA / advisor", "Status": "Not Started"},
            {"Step": 3, "Milestone": "Complete professional review checklist", "Timing": "Before execution", "Owner": "All reviewers", "Status": "Not Started"},
            {"Step": 4, "Milestone": "Execute approved sale or hedge tranche", "Timing": "Per schedule", "Owner": "Advisor / trading desk", "Status": "Not Started"},
            {"Step": 5, "Milestone": "Monitor tax used, residual concentration, hedge tracking error, and year-end losses", "Timing": "Monthly / year-end", "Owner": "Advisor / CPA", "Status": "Not Started"},
        ]
    )
    milestones = st.data_editor(
        milestones_default,
        hide_index=True,
        num_rows="dynamic",
        width="stretch",
        column_config={
            "Step": st.column_config.NumberColumn(format="%d", width="small"),
            "Status": st.column_config.SelectboxColumn(
                options=["Not Started", "In Review", "Complete", "Approved", "Not Applicable"],
                width="medium",
            ),
        },
        key="transition_plan_milestones",
    )

    checklist_counts = checklist["Status"].value_counts().to_dict() if "Status" in checklist else {}
    milestone_counts = milestones["Status"].value_counts().to_dict() if "Status" in milestones else {}
    st.subheader("Readiness Snapshot")
    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Checklist complete", f"{checklist_counts.get('Complete', 0) + checklist_counts.get('Approved', 0):,}/{len(checklist):,}")
    rc2.metric("Milestones complete", f"{milestone_counts.get('Complete', 0) + milestone_counts.get('Approved', 0):,}/{len(milestones):,}")
    rc3.metric("Tax budget status", "Within budget" if plan["tax_budget_remaining"] >= 0 else "Over budget")

    for label, status in [
        ("CPA/tax review", checklist.loc[0, "Status"] if len(checklist) > 0 else "Needed"),
        ("Legal hedge review", checklist.loc[1, "Status"] if len(checklist) > 1 else "Needed"),
        ("Client approval", checklist.loc[4, "Status"] if len(checklist) > 4 else "Needed"),
    ]:
        render_status_badge(label, str(status))


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
    bundled_returns = load_optional_csv("daily_returns.csv")
    lots = load_optional_csv("semiconductor_cluster_tax_lot_exposure.csv")
    sale_schedule = load_optional_csv("sale_lot_schedule.csv")

    st.title("Private Tax Transition Dashboard")
    st.caption("Concentration diagnosis -> strategy comparison -> review-ready transition plan")

    tabs = [
        "Overview",
        "Strategy Lab",
        "SMA Study",
        "Transition Plan",
        "Tax Scenarios",
        "Long/Short Detail",
        "Risk Evidence",
        "Data QA",
        "Notes",
    ]
    if audience == "Advisor View":
        tabs.insert(6, "Advisor Detail")

    tab_objects = st.tabs(tabs)
    for label, tab in zip(tabs, tab_objects):
        with tab:
            if label == "Overview":
                render_overview(rec, cluster_summary, bucket_summary, risk_weights, lots)
            elif label == "Strategy Lab":
                render_strategy_lab(cluster_summary, risk, bundled_returns)
            elif label == "SMA Study":
                render_sma_study(cluster_summary, risk, bundled_returns)
            elif label == "Transition Plan":
                render_transition_plan_builder(cluster_summary, risk, bundled_returns)
            elif label == "Tax Scenarios":
                render_transition(transition)
            elif label == "Long/Short Detail":
                render_overlay(overlay_capacity, overlay_economics, candidates)
            elif label == "Risk Evidence":
                render_risk(risk)
            elif label == "Data QA":
                render_qa(rec)
            elif label == "Advisor Detail":
                render_advisor_lots(lots, sale_schedule)
            elif label == "Notes":
                render_notes()


if __name__ == "__main__":
    main()
