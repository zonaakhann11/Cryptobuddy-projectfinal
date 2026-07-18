# CryptoBuddy

Next-hour **BUY / SELL / HOLD** for BTC, ETH, SOL — **ML prediction + decision support** (educational; not financial advice).

## Run

**Backend** (`:5000`):

```powershell
cd D:\CryptoBuddy-main\CryptoBuddy-main\backend
.\venv\Scripts\Activate.ps1
python app.py
```

**Frontend** (`:5173`):

```powershell
cd D:\CryptoBuddy-main\CryptoBuddy-main\frontend
.\start-dashboard.ps1
```

Open http://127.0.0.1:5173 → select coin → **PREDICT**.

## Layout

| Path | Purpose |
|------|---------|
| `backend/` | Flask API, features, models, sentiment |
| `backend/models/saved/` | Production models (live) |
| `backend/models/saved_v2/` | Optional retrain candidates |
| `backend/data/historical/*_hourly.csv` | OHLCV history |
| `frontend/` | React dashboard |
| `docs/FYP_REPORT_PACK.md` | SRS / SDS / results for the report |
| `docs/REPORT_CHATGPT_BRIEF.md` | Prompt pack for writing the report |
| `docs/STANDEE_DEMO.html` | Standee layout demo |
| `experiments/` | Optional retrain (`train_final_v2.py`) + comparison CSV |
| `scripts/` | PowerShell helpers for optional training |

## Report

Use **`docs/FYP_REPORT_PACK.md`** and **`docs/REPORT_CHATGPT_BRIEF.md`**.  
Results snapshot: `experiments/results/final_model_comparison.csv`.

## Note

Production predictor: **Gradient Boosting**. Other models were compared; scores were similar (~38–44% balanced accuracy), so GB stayed live and the product focus is **decision support**.
