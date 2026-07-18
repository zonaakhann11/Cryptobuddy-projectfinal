# CryptoBuddy — Setup & Run Guide

For **you** and anyone who clones  
`https://github.com/zonaakhann11/Cryptobuddy-projectfinal`

Git stores **source code + models + hourly CSVs + docs**.  
It does **not** store `venv`, `node_modules`, or portable Node (too large).  
After clone, each person creates those once (steps below). Then the app works the same.

---

## 0. What you get after `git pull` / clone

| Included in Git | Not in Git (recreate locally) |
|-----------------|-------------------------------|
| Backend Python code | `backend/venv/` |
| Frontend React code | `frontend/node_modules/` |
| Production models `backend/models/saved/*.pkl` | Portable Node under `frontend/.tools/` |
| Hourly data `*_hourly.csv` | |
| Docs, scripts, experiments code | |

---

## 1. Clone (first time on a new PC)

```powershell
git clone https://github.com/zonaakhann11/Cryptobuddy-projectfinal.git
cd Cryptobuddy-projectfinal
```

(If the repo root is nested, use the folder that contains `backend` and `frontend`.)

---

## 2. Backend setup (one-time)

### 2.1 Requirements
- Python **3.10+** (3.11/3.12 fine)
- Internet (Binance, Fear & Greed, news RSS)

### 2.2 Create venv + install packages

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2.3 Start API (every time)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python app.py
```

You should see Flask on **http://127.0.0.1:5000**

Leave this terminal open.

---

## 3. Frontend setup (one-time)

### 3.1 Requirements
- **Node.js 18+** installed, **or** use the project script if you already have portable Node under `frontend/.tools/` (not in Git — optional local copy)

### 3.2 Install packages

```powershell
cd frontend
npm install
```

### 3.3 Start dashboard (every time)

**Option A — script (recommended if portable Node exists):**

```powershell
cd frontend
.\start-dashboard.ps1
```

**Option B — system Node:**

```powershell
cd frontend
npx vite --host=127.0.0.1 --port=5173
```

Open **http://127.0.0.1:5173**

Leave this terminal open (second terminal; backend stays running).

---

## 4. How to use the live system (point by point)

### 4.1 Dashboard predict (main demo)

1. Backend running on `:5000`
2. Frontend running on `:5173`
3. Select **BTC / ETH / SOL**
4. Click **PREDICT**
5. Read:
   - **Model outlook** (raw ML)
   - **Suggested action** (after confirmations + risk)
   - Sentiment / Fear & Greed / news
   - Technical evidence + 6 checks
   - Decision support cards (what would change, history, price zone)

Uses production models (**v1**) via `POST http://127.0.0.1:5000/api/predict`.

### 4.2 Terminal realtime predict (for screenshots / debug)

New terminal:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python models\realtime_predict.py --model-version v1
```

One coin:

```powershell
python models\realtime_predict.py --model-version v1 --symbol BTCUSDT
```

Also: `--symbol ETHUSDT` or `--symbol SOLUSDT`

This hits the same pipeline: data → features → model → confirmations → sentiment/risk → print summary.

### 4.3 Sentiment pieces (what runs inside predict)

You don’t start these separately. When you Predict / run `realtime_predict.py`, it automatically:

| Piece | Source | Code |
|-------|--------|------|
| Fear & Greed | Alternative.me API | `sentiment/public_fear_greed_sentiment.py` |
| News mood | RSS + VADER | `sentiment/news_sentiment.py` |
| Risk keywords | Same headlines | `sentiment/public_risk_sentiment.py` |
| Overlay rules | Block risky BUY, etc. | `sentiment/decision_overlay.py` |

Needs internet. If an API fails, safe fallbacks are used (e.g. neutral F&G).

### 4.4 Data updater (hourly candles)

Also automatic inside predict:

- `collectors/binance_updater.py` refreshes / appends latest Binance 1h candles  
- Base history: `backend/data/historical/*_hourly.csv` (in Git)

Optional: run collectors only if you are debugging data (normal demos don’t need this alone).

### 4.5 Optional — quick v2 retrain (not required for demo)

```powershell
cd <repo-root>
.\scripts\train_final_v2_quick.ps1
```

~30–90 min. Writes to `backend/models/saved_v2/`. **Does not** replace live v1 unless you enable v2 later.  
Live dashboard stays on **v1** by default.

---

## 5. Two terminals checklist (normal day)

| Terminal | Commands |
|----------|----------|
| **1 — Backend** | `cd backend` → `.\venv\Scripts\Activate.ps1` → `python app.py` |
| **2 — Frontend** | `cd frontend` → `.\start-dashboard.ps1` (or `npx vite --host=127.0.0.1 --port=5173`) |

Browser: http://127.0.0.1:5173  

---

## 6. After you push — what others do

```powershell
git clone https://github.com/zonaakhann11/Cryptobuddy-projectfinal.git
cd Cryptobuddy-projectfinal
```

Then **Section 2** (backend venv + `pip install`) and **Section 3** (`npm install` + start).  
Then **Section 5**.

They get models + hourly CSVs from Git, so Predict works after setup — no need to retrain.

---

## 7. Common problems

| Problem | Fix |
|---------|-----|
| `Cannot find path ...\backend` | You’re in the wrong folder; open the repo root that contains `backend` and `frontend` |
| Frontend can’t reach API | Start `python app.py` first; URL must be `127.0.0.1:5000` |
| `venv` activate fails | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `npm` / `node` not found | Install Node.js LTS from https://nodejs.org |
| PowerShell eats `--host` | Use `npx vite --host=127.0.0.1 --port=5173` (equals form) |
| Sentiment empty / F&G fallback | Check internet / firewall |

---

## 8. Important paths

```
backend/app.py                          → Flask server
backend/models/realtime_predict.py      → CLI + core predict
backend/routes/prediction.py            → /api/predict
backend/models/saved/                   → live v1 models
backend/features/indicators.py          → ML features
backend/features/decision_support.py    → DSS extras
backend/sentiment/                      → F&G, news, risk
frontend/src/pages/Index.tsx            → dashboard
docs/FYP_REPORT_PACK.md                 → report facts
docs/REPORT_CHATGPT_BRIEF.md            → report writing brief
```

---

## 9. Push this project (owner: zonaakhann11)

From the machine that already has the local commit:

```powershell
cd D:\CryptoBuddy-main\CryptoBuddy-main

git remote remove origin 2>$null
git remote add origin https://github.com/zonaakhann11/Cryptobuddy-projectfinal.git

git push -u origin main
```

If GitHub asks for a password, use a **Personal Access Token**, not your GitHub password.

After push, teammates only need this guide (Sections 1–5).
