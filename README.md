# CryptoBuddy

Next-hour **BUY / SELL / HOLD** for BTC, ETH, SOL — **ML prediction + decision support** (educational; not financial advice).

## Quick start

**Full clone / teammate instructions:** see **[SETUP_AND_RUN.md](SETUP_AND_RUN.md)** (point-by-point).

```powershell
# Terminal 1 — API
cd backend
.\venv\Scripts\Activate.ps1   # first time: python -m venv venv && pip install -r requirements.txt
python app.py

# Terminal 2 — Dashboard
cd frontend
npm install                   # first time only
.\start-dashboard.ps1
```

Open http://127.0.0.1:5173 → **PREDICT**.

## Docs

| File | Purpose |
|------|---------|
| [SETUP_AND_RUN.md](SETUP_AND_RUN.md) | How anyone runs backend, frontend, predict, sentiment |
| [docs/FYP_REPORT_PACK.md](docs/FYP_REPORT_PACK.md) | SRS / SDS / results for the report |
| [docs/REPORT_CHATGPT_BRIEF.md](docs/REPORT_CHATGPT_BRIEF.md) | Prompt pack for writing the report |

## Note

Production predictor: **Gradient Boosting (v1)**. `venv` and `node_modules` are **not** in Git — recreate them after clone (see SETUP_AND_RUN.md).
