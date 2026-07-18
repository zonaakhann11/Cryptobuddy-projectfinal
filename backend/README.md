# CryptoBuddy — Quick Start & Submission Artifacts

This README lists the minimal setup, activation, and run commands you need to reproduce key outputs and collect artifacts for submission.

## Quick Checklist (for submission)
- Trained models: `models/saved/*_model.pkl`
- Feature lists: `models/saved/*_features.json`
- Reports & metrics: `models/reports/*.csv`, `models/reports/*.txt`
- Historical datasets: `data/historical/*.csv`
- Key scripts: `models/train_model.py`, `models/realtime_predict.py`, `models/prepare_dataset.py`

## Prerequisites
- Python 3.9+ recommended
- Git and a terminal (PowerShell on Windows)
- A virtual environment is strongly recommended

## Setup (Windows PowerShell)
```powershell
cd C:\projfinal
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Setup (macOS / Linux)
```bash
cd /path/to/projfinal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the main components

- Train models (creates artifacts under `models/saved/` and `models/reports/`):
```bash
python models/train_model.py
```

- Prepare / refresh historical data (safe to run before training):
```bash
python collectors/binance_historical.py
```
or
```bash
python collectors/binance_updater.py
```

- Run realtime predictor (prints decisions for BTC/ETH/SOL):
```bash
python models/realtime_predict.py
```

- Quick dataset summary script:
```bash
python scripts/summarize_historical.py
```

## Where outputs are stored
- Models and feature lists: `models/saved/` (collect both `.pkl` and `.json` files)  
- Performance reports and metrics: `models/reports/`  
- Historical CSVs and ML datasets: `data/historical/`  

## Sentiment data note
- The project uses the Crypto Fear & Greed Index (Alternative.me) via `sentiment/public_fear_greed_sentiment.py` (function `get_fear_greed_sentiment()`). Reddit scraping (`praw`) is not used and is unnecessary for submission.

## Packaging artifacts for submission
Collect the following into a zip for submission:
- `models/saved/` (all files)
- `models/reports/` (all files)
- `data/historical/` (relevant CSV files)
- `requirements.txt` and this `README.md`
- Optional: `scripts/` or `collectors/` if you want to demonstrate data collection

## Quick verification commands
After activation, run:
```bash
python -c "import sentiment.public_reddit_sentiment as s; print(s.get_reddit_sentiment())"
python models/realtime_predict.py
```

## Notes & Next Steps
- If you need a formatted Final Report (`FinalReport.md`) with chapters and appendices, tell me and I'll generate it using the repository metadata and code mapping.  
- If you want a one-page poster, a Gantt chart, or formatted references, I can produce those as well.

---
Generated automatically to support quick submission and verification.
