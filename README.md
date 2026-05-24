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
