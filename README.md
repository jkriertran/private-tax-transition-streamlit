# Private Tax Transition Streamlit Deploy Package

This folder is the client-shareable Streamlit package. It intentionally contains only the dashboard app and client-facing derived model outputs.

## What is included

- Streamlit app: `apps/private_tax_transition_app.py`
- Client-facing model summaries under `analysis_output/tax_transition_model/`
- Sanitized reconciliation file with row counts, pass/fail status, and rounding diffs only
- Chart SVGs used by the app
- `requirements.txt`
- Streamlit secrets example

## What is intentionally excluded

- Raw broker exports
- Normalized all-position upload files
- Lot-level tax basis tables
- Lot-level sale schedules
- Local screenshots and smoke-test artifacts
- Real secrets

## Deploy on Streamlit Community Cloud

1. Put the contents of this folder in a private GitHub repository.
2. In Streamlit Community Cloud, deploy the private repo.
3. Set the main file path to `apps/private_tax_transition_app.py`.
4. Add app secrets from `.streamlit/secrets.toml.example`.
5. In Streamlit Cloud sharing settings, choose `Only specific people can view this app`.
6. Add the viewer by email.

Keep `enable_advisor_view = false` for the client-facing share link unless you deliberately add lot-level files back into this package.

## Optional Alpaca market data

The Strategy Lab and Transition Plan can refresh current prices from Alpaca latest bars and can use Alpaca historical daily bars for hedge/regime return analysis. This is read-only market data; the app does not place orders, create broker files, or update cost basis.

Configure either Streamlit secrets or environment variables:

- Streamlit secrets: `[alpaca] api_key_id`, `api_secret_key`, `data_feed`, `data_base_url`
- Streamlit root secrets: `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `ALPACA_DATA_FEED`, `ALPACA_DATA_BASE_URL`
- Environment variables: `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `ALPACA_DATA_FEED`, `ALPACA_DATA_BASE_URL`

If Alpaca credentials are missing, the request fails, a symbol is unavailable, or the selected feed is not permitted by the subscription, the app continues with manual/uploaded prices and uploaded/bundled returns.
