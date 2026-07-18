# CryptoBuddy — Master brief for ChatGPT / Claude (FYP report)

**How to use:** Paste EVERYTHING below into ChatGPT in one message (or upload this file).  
Then ask: *“Write Chapter 1 only…”* chapter by chapter. Do **not** ask for the whole thesis in one go.

---

## SYSTEM PROMPT (rules for the AI writer)

You are writing a Final Year Project report for DHA Suffa University, Department of Computer Science.

Project: **CryptoBuddy (P14F25)**  
Team: Mirza Omer Baig, Zona Khan, Dev Yogesh, Hattaf Ali  
Supervisor: Adnan Alam  

**Tone:** Formal academic, clear, university FYP standard.  
**Positioning:** Predictive system + decision-support system (educational). NOT an auto-trader. NOT financial advice.

**HARD RULES — never invent:**
- Do NOT claim 34× risk-reward, guaranteed profit, or SOTA accuracy.
- Do NOT invent metrics not listed in FACTS below.
- If something is unknown, write “as implemented in the prototype” or leave a `[TODO: screenshot]` placeholder.
- Call it **ML / AI-powered** because of Gradient Boosting + VADER NLP — not because of ChatGPT inside the product.

**Write chapter-by-chapter** when asked. Expand SRS/SDS properly. Use headings the student can paste into Word.

---

## FACTS (source of truth — use only these)

### Product
- Name: CryptoBuddy  
- Goal: Next-hour BUY / SELL / HOLD for BTCUSDT, ETHUSDT, SOLUSDT + human-readable evidence  
- Horizon: 1 hour  
- User decides whether to act  

### Two layers
1. Predictive — ML outlook + class probabilities  
2. Decision support — confirmations, evidence groups, Fear & Greed, news, risk, explanations  

### Stack
- Backend: Python, Flask, scikit-learn, pandas, numpy, TA-style indicators  
- Frontend: React (Vite)  
- Data: Binance OHLCV API, Alternative.me Fear & Greed API, news RSS (CoinTelegraph, CoinDesk, Decrypt, Bitcoin Magazine), VADER sentiment  
- Models live in: `backend/models/saved/` (production Gradient Boosting)  

### Key modules
- `realtime_predict.py` — live pipeline  
- `indicators.py` — ~90+ features  
- `grouped_indicators.py` — 5 evidence groups  
- `decision_support.py` — what would change, history, price zones, news takeaway  
- `sentiment/*` — F&G, news, risk, overlay  

### Decision flow
1. Live OHLCV → 2. Features → 3. ML predict → 4. 6 confirmation checks → 5. Prob/confirm thresholds (weak → HOLD) → 6. Sentiment/risk (may block BUY; never invent BUY/SELL from HOLD) → 7. Explanations → 8. Dashboard  

### Confirmations (6)
Short-term momentum · RSI healthy · RSI rising · MACD · Volume active · Price-volume together  

### Evidence groups (5)
Momentum · Trend · Volatility · Volume · Market Context  

### Evaluation (honest — use exactly)
Chronological split; primary metric balanced accuracy.

Production-style reported figures:
- BTC: Acc ~44.28%, Bal ~42.37%, Macro-F1 ~0.411  
- ETH: Acc ~40.11%, Bal ~41.57%, Macro-F1 ~0.399  
- SOL: Acc ~30.12%, Bal ~37.21%, Macro-F1 ~0.277  

Quick retrain candidates (similar, not forced live):
- BTC bal ~43.1%, ETH ~41.2%, SOL ~39.5%  

Models compared in experiments: Gradient Boosting, Extra Trees, Random Forest, LightGBM (when available).  
Random 3-class chance ≈ 33%. Lift vs random (relative): BTC ~+26%, ETH ~+23%, SOL ~+16%.  

Binary (HOLD excluded, approximate): ~51–54% directional accuracy.  
Selective confirmed BUY/SELL: about ~52% directional in reported selective test; most hours stay HOLD.

### Standee / marketing lines allowed
- Filters most weak hours to HOLD  
- 90+ features, 6 checks, 5 groups, 1H live, 3 coins  
- Decision support: what would change, signal history, price zones, F&G history  

### Forbidden claims
34× losses avoided, guaranteed returns, “61/100 buys correct” unless measured, AWS improves accuracy.

---

## UNIVERSITY CHAPTER OUTLINE (ask AI to write one chapter at a time)

1. **Title page** — CryptoBuddy, P14F25, team, supervisor, DSU, year  
2. **Abstract** (150–250 words)  
3. **Acknowledgements**  
4. **Table of contents**  
5. **Chapter 1 — Introduction**  
   - Background (crypto volatility, noisy alerts)  
   - Problem statement  
   - Aim & objectives  
   - Scope & limitations  
   - Report structure  
6. **Chapter 2 — Literature review**  
   - Technical indicators, ML for finance, sentiment, decision-support systems  
   - Gap: alerts lack explanation + confirmation filters  
7. **Chapter 3 — Requirements (SRS)**  
   - Expand FR-1…FR-10 and NFR-1…NFR-5 into full SRS style  
   - Actors, use cases (Predict, View evidence, View sentiment)  
   - Non-functional: performance, honesty, no leakage  
8. **Chapter 4 — System design (SDS)**  
   - Architecture diagram description  
   - Module design  
   - Data design  
   - Decision-support design  
   - Sequence: user → API → predict → UI  
9. **Chapter 5 — Methodology & implementation**  
   - Data collection  
   - Feature engineering  
   - Labeling (±~0.15% BTC/ETH, ±~0.20% SOL)  
   - Model training & comparison  
   - Confirmation + sentiment overlay  
   - Frontend dashboard  
10. **Chapter 6 — Results & evaluation**  
    - Metrics table (use FACTS only)  
    - Model comparison narrative  
    - Decision-support qualitative evaluation  
    - Screenshots placeholders  
11. **Chapter 7 — Discussion**  
    - Why accuracy is modest  
    - Why DSS framing matters  
    - Threats to validity  
12. **Chapter 8 — Conclusion & future work**  
13. **References** (IEEE or APA — ask student which DSU wants)  
14. **Appendices** — API sample JSON, feature list categories, glossary  

---

## FIRST MESSAGE TO PASTE INTO CHATGPT

```
[Paste the SYSTEM PROMPT + FACTS + OUTLINE from this file]

Now write ONLY Chapter 1 — Introduction for our FYP report.
Use formal university style.
Include: background, problem statement, aim, 4–6 objectives, scope, limitations, report organization.
Do not invent metrics. Keep predictive + decision-support positioning.
Word count ~1200–1800 words.
```

Then continue:

```
Now write Chapter 3 — Software Requirements Specification in full SRS style from the FACTS (FR/NFR tables expanded into sections: Introduction, Overall description, Specific requirements, Use cases).
```

```
Now write Chapter 4 — Software Design Specification: architecture, modules, data flow, decision flow, UI components, diagrams described in Mermaid or clear ASCII for me to redraw.
```

```
Now write Chapter 6 — Results using ONLY the metrics in FACTS. Discuss lift vs random. Emphasize decision-support value. Add [TODO: insert Figure X dashboard screenshot] placeholders.
```

---

## YOUR JOB (human) after ChatGPT drafts

1. Paste into Word with DSU template (margins, fonts, numbering).  
2. Replace every `[TODO: screenshot]` with real dashboard images.  
3. Fix any invented numbers.  
4. Add real references (papers you actually cite).  
5. Align Abstract + Conclusion with the same story.  
6. Run plagiarism check; rewrite AI-sounding paragraphs in your voice.

---

## Local source files in this repo

- `docs/FYP_REPORT_PACK.md` — condensed SRS/SDS/results  
- `docs/STANDEE_CHANGE_NOTES.md` — poster notes  
- `experiments/results/final_model_comparison.csv` — quick-train numbers  
- `README.md` — how to run demo  

Primary story for the whole report:  
**CryptoBuddy predicts next-hour direction with ML, then supports human decisions with confirmations, sentiment/risk, and explanations — not an auto-trading profit machine.**
