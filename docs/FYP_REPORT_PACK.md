# CryptoBuddy — Final Year Project Report Pack

**Use this document** for SRS, SDS, methodology, results, and limitations.  
Companion files: `REPORT_CHATGPT_BRIEF.md` (writing prompt), `STANDEE_DEMO.html` (poster).  
Repo is cleaned to production code + these docs + optional `experiments/train_final_v2.py`.

**Product positioning:** predictive system + decision-support system (not an auto-trader).

---

## 1. Project overview

| Item | Detail |
|------|--------|
| Name | CryptoBuddy |
| Goal | Next-hour **BUY / SELL / HOLD** outlook for BTCUSDT, ETHUSDT, SOLUSDT, plus human-readable evidence |
| Users | Students / retail learners reviewing crypto hourly context |
| Non-goals | Guaranteed profit, auto-execution, “financial advice” |

**Two layers**

1. **Predictive** — ML model outputs class probabilities → raw outlook.  
2. **Decision support** — technical checks, five evidence groups, news / Fear & Greed / risk → filtered **suggested action** + plain-English “why”.

The human still decides whether to buy, sell, or stay out.

---

## 2. SRS (Software Requirements Specification) — condensed

### 2.1 Functional requirements

| ID | Requirement |
|----|-------------|
| FR-1 | User selects BTC / ETH / SOL and requests a prediction |
| FR-2 | System returns BUY, SELL, or HOLD for a **1-hour** horizon |
| FR-3 | System shows class probabilities (BUY / SELL / HOLD %) |
| FR-4 | System shows raw model outlook vs filtered suggested action |
| FR-5 | System shows ≥6 technical confirmation checks (pass / fail) |
| FR-6 | System shows grouped evidence: Momentum, Trend, Volatility, Volume, Market Context |
| FR-7 | System shows RSI / MACD / MA / Volume charts with plain-English notes |
| FR-8 | System shows Fear & Greed, news sentiment, risk level / events |
| FR-9 | System explains the suggestion in plain language |
| FR-10 | High-risk context may **block BUY** suggestions (never invent BUY/SELL from HOLD) |

### 2.2 Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Live data from public APIs (Binance OHLCV, news RSS, Alternative.me F&G) |
| NFR-2 | No look-ahead leakage in feature engineering (backward-looking only) |
| NFR-3 | Chronological train/val/test evaluation for model claims |
| NFR-4 | Honest metrics (balanced accuracy); no inflated profit claims |
| NFR-5 | Educational disclaimer on UI |

### 2.3 Out of scope

- Portfolio / order execution  
- Sub-minute trading  
- Claiming AWS improves accuracy (AWS is optional hosting only)

---

## 3. SDS (Software Design Specification) — condensed

### 3.1 Architecture

```
[React dashboard :5173]
        |  POST /api/predict
[Flask API :5000]
        |— realtime_predict.py
        |— features/indicators.py + grouped_indicators.py + decision_copy.py
        |— models/saved/*.pkl (production)
        |— sentiment/ (news, F&G, risk, overlay)
        |— Binance / RSS / Alternative.me
```

### 3.2 Key modules

| Module | Role |
|--------|------|
| `backend/app.py` + `routes/prediction.py` | HTTP API |
| `backend/models/realtime_predict.py` | Live pipeline: data → features → model → filters → JSON |
| `backend/features/indicators.py` | ~90+ technical / context columns for ML |
| `backend/features/grouped_indicators.py` | Human evidence groups (explainability) |
| `backend/features/decision_copy.py` | Plain-English reason strings |
| `backend/sentiment/*` | News VADER, Fear & Greed, risk, overlay rules |
| `frontend/src/pages/Index.tsx` | Dashboard orchestration |
| `PredictionBox` / `TechnicalIndicators` / `SentimentCard` / `WhyThisSignal` | Decision-support UI |

### 3.3 Decision flow

1. Fetch / update hourly OHLCV  
2. Compute indicators  
3. ML model → raw BUY/SELL/HOLD + probabilities  
4. Run 6 technical checks  
5. Apply probability + confirmation policy (Strategy B style)  
6. Apply sentiment / risk overlay (can block BUY; does not invent directions)  
7. Build grouped summaries + human explanation  
8. Return JSON to dashboard  

### 3.4 Data sources

- Binance public klines  
- Historical CSVs under `backend/data/historical/`  
- News RSS (CoinTelegraph, CoinDesk, Decrypt, …) + VADER  
- Alternative.me Fear & Greed  

---

## 4. Indicators — what they are (summed up)

Hundreds of raw columns are **not** shown one-by-one. Users see **four charts** and **five groups**.

### 4.1 Chart tabs (what people see)

| Tab | Plain meaning |
|-----|----------------|
| RSI | Has price been pushed too hard up or down lately? |
| MACD | Is short-term momentum stronger or weaker than a slower trend? |
| Moving Average | Is price above or below its recent smoothed path? |
| Volume | Are traders participating, or is the move thin? |

### 4.2 Five evidence groups (decision support)

| Group | Question it answers |
|-------|---------------------|
| Momentum | Is recent strength building or fading? |
| Trend | Is price riding above/below its averages? |
| Volatility | Is the market calm or unusually jumpy? |
| Volume | Is the move backed by participation? |
| Market Context | Session hours / Bitcoin backdrop for alts |

Each group has a **0–100 score**, status (Bullish / Bearish / Mixed / Neutral / High Risk), and plain “helping / watching” text.

### 4.3 Six technical checks (gate for BUY/SELL)

Short-term momentum agrees · RSI healthy · RSI rising · MACD supports upside · Volume active · Price & volume move together.

If too few pass → **suggested action stays HOLD**.

### 4.4 Features used by the ML model (categories)

Momentum (RSI multi-window, MACD, stochastic), trend (EMAs, crosses), volatility (ATR, Bollinger), volume (z-score, changes), returns / lags, optional BTC/ETH context for alts.  
Grouped scores are for **display**, not required as model inputs.

---

## 5. Model comparison & results (honest)

### 5.1 Method

- Task: ternary next-hour labels (±~0.15% BTC/ETH, ±~0.20% SOL)  
- Models compared over experiments: Gradient Boosting, Extra Trees, Random Forest, LightGBM (when available)  
- Split: chronological **60% / 20% / 20%**  
- Primary metric: **balanced accuracy**  

### 5.2 Production (live) baseline (report figures)

| Asset | Accuracy | Balanced acc. | Macro-F1 |
|-------|----------|---------------|----------|
| BTC | 44.28% | 42.37% | 0.411 |
| ETH | 40.11% | 41.57% | 0.399 |
| SOL | 30.12% | 37.21% | 0.277 |

### 5.3 Quick retrain candidate (`saved_v2/`, not live by default)

| Asset | Selected | Test bal. acc. | Accuracy |
|-------|----------|----------------|----------|
| BTC | GradientBoosting | 43.1% | 44.8% |
| ETH | GradientBoosting | 41.2% | 42.2% |
| SOL | GradientBoosting | 39.5% | 40.0% |

**Conclusion:** models are close; no large accuracy breakthrough. Live dashboard keeps **production** models. Product value is **transparent decision support**, not a claim of high predictive skill.

CSV: `experiments/results/final_model_comparison.csv`

---

## 6. What works / what does not

### Working (ship this)

- End-to-end live predict for BTC / ETH / SOL  
- Raw outlook vs suggested action  
- Probabilities, checks, groups, sentiment, risk, plain explanations  
- Leakage-aware feature design  
- Honest evaluation narrative  

### Not claimed / not working as “profit engine”

- Balanced accuracy stays ~38–44% (hard hourly crypto problem)  
- More training did **not** clearly beat production  
- Sentiment is **context**, not proven historical alpha  
- HOLD ≠ “loss avoided” / profitability multiplier  
- AWS hosting does **not** improve accuracy by itself  

---

## 7. How to run (demo)

```text
# Backend
cd backend
.\venv\Scripts\Activate.ps1
python app.py
# → http://127.0.0.1:5000

# Frontend
cd frontend
.\start-dashboard.ps1
# → http://127.0.0.1:5173
```

Select coin → PREDICT → read Model outlook, Suggested action, Market evidence, Sentiment, Decision support.

---

## 8. Report chapter mapping

| Typical FYP chapter | Use section |
|---------------------|-------------|
| Introduction / problem | §1 |
| SRS | §2 |
| SDS / architecture | §3 |
| Methodology / features | §4 |
| Experiments / results | §5 |
| Discussion / limitations | §6 |
| User guide / demo | §7 |

---

## 9. Integrity checklist (do not write)

- Fake “34× losses avoided”  
- Guaranteed returns / SOTA claims  
- That sentiment was proven to raise historical accuracy without a controlled archive study  
- That v2 must be enabled when metrics are similar  

---

*Last consolidated for final report focus: predictive + decision-support CryptoBuddy.*
