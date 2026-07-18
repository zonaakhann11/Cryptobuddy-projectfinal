import { useState, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import PredictionBox from "@/components/PredictionBox";
import PriceCard from "@/components/PriceCard";
import SentimentCard from "@/components/SentimentCard";
import TechnicalIndicators from "@/components/TechnicalIndicators";
import WhyThisSignal from "@/components/WhyThisSignal";
import DecisionSupportExtras from "@/components/DecisionSupportExtras";
import StatusBar from "@/components/StatusBar";

const generateChartData = (points: number = 24) => {
  let value = 45 + Math.random() * 20;
  return Array.from({ length: points }, () => {
    value += (Math.random() - 0.48) * 6;
    return { value: Math.max(8, Math.min(92, value)) };
  });
};

type CoinKey = "BTC" | "ETH" | "SOL";

type CoinPrice = {
  price: number;
  change: number;
  high24h?: number;
  low24h?: number;
  chartData: { value: number }[];
};

const shortDecisionReason = (data: any): string => {
  if (!data) return "";
  const badge = String(data.strategy_badge || "");
  const reasons: string[] = data.confirmation_reasons || [];
  const conf = Math.round((data.confidence || 0) * 100);
  const score = data.confirmation_score ?? 0;

  if (badge.includes("Insufficient") || reasons.includes("insufficient_confirmations")) {
    return "Model probabilities are close and technical confirmations are insufficient for a reliable BUY or SELL signal.";
  }
  if (badge.includes("Conflicting") || reasons.some((r) => String(r).includes("low_"))) {
    return "Signals conflict between the raw model output and confirmation/sentiment filters, so the system stays defensive.";
  }
  if (badge.includes("BUY Blocked") || reasons.includes("risk_override")) {
    return "A high-risk condition blocked an actionable BUY; final decision remains HOLD for safety.";
  }
  if (data.final_decision === "BUY") {
    return `BUY passed probability and confirmation thresholds (${score}/6) with calibrated confidence ${conf}%.`;
  }
  if (data.final_decision === "SELL") {
    return `SELL passed probability and confirmation thresholds (${score}/6) with calibrated confidence ${conf}%.`;
  }
  if (data.human_readable_explanation) {
    const first = String(data.human_readable_explanation).split(/(?<=\.)\s/)[0];
    return first.length > 160 ? `${first.slice(0, 157)}…` : first;
  }
  return `Final decision is ${data.final_decision} after confirmations and live sentiment/risk overlays.`;
};

const Index = () => {
  const [selectedCoin, setSelectedCoin] = useState<CoinKey>("ETH");
  const [predictionData, setPredictionData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [pricesLoading, setPricesLoading] = useState(false);

  const [priceData, setPriceData] = useState<Record<CoinKey, CoinPrice>>({
    BTC: { price: 0, change: 0, chartData: generateChartData() },
    ETH: { price: 0, change: 0, chartData: generateChartData() },
    SOL: { price: 0, change: 0, chartData: generateChartData() },
  });

  const fetchPrices = useCallback(async () => {
    setPricesLoading(true);
    try {
      const response = await fetch(
        'https://api.binance.com/api/v3/ticker/24hr?symbols=["BTCUSDT","ETHUSDT","SOLUSDT"]'
      );
      if (!response.ok) return;
      const data = await response.json();

      setPriceData((prev) => {
        const next = { ...prev };
        data.forEach((item: any) => {
          const coin = item.symbol.replace("USDT", "") as CoinKey;
          if (!next[coin]) return;
          const last = parseFloat(item.lastPrice);
          const change = parseFloat(item.priceChangePercent);
          const high24h = parseFloat(item.highPrice);
          const low24h = parseFloat(item.lowPrice);
          const prevChart = next[coin].chartData;
          const chartData = [
            ...prevChart.slice(-23),
            {
              value: Math.max(
                5,
                Math.min(
                  95,
                  (prevChart[prevChart.length - 1]?.value ?? 50) +
                    (change >= 0 ? 0.8 : -0.8) * (0.4 + Math.random() * 1.8)
                )
              ),
            },
          ];
          next[coin] = { price: last, change, high24h, low24h, chartData };
        });
        return next;
      });
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to fetch live prices:", err);
    } finally {
      setPricesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 10000);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  const handlePredict = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("http://127.0.0.1:5000/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: `${selectedCoin}USDT`,
          model_version: "v1",
        }),
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const errBody = await response.json();
          detail = errBody.error || errBody.message || detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }
      const data = await response.json();
      if (data.error) throw new Error(String(data.error));
      setPredictionData(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(
        err?.message === "Failed to fetch"
          ? "Cannot reach API at http://127.0.0.1:5000 — start the backend and retry."
          : err?.message || "Failed to fetch prediction"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const hasPrediction = Boolean(predictionData);
  const showPredictError = Boolean(error) && !isLoading;

  const currentPrediction: "BUY" | "SELL" | "HOLD" = hasPrediction
    ? ["BUY", "SELL", "HOLD"].includes(predictionData.final_decision)
      ? predictionData.final_decision
      : "HOLD"
    : "HOLD";
  const currentConfidence = hasPrediction
    ? Math.round(predictionData.confidence * 100)
    : 0;
  const rawPrediction = hasPrediction
    ? predictionData.raw_prediction || predictionData.model_decision
    : undefined;
  const modelVersion = hasPrediction ? predictionData.model_version : "v1";
  const probs = hasPrediction
    ? {
        sell: predictionData.prob_sell ?? 0,
        buy: predictionData.prob_buy ?? 0,
        hold: predictionData.prob_hold ?? 0,
      }
    : undefined;

  const fearGreedIndex = hasPrediction ? predictionData.fear_greed_index : 0;
  const newsSentiment = hasPrediction ? predictionData.news_sentiment : 0;
  const riskScore = hasPrediction ? predictionData.risk_score : 0.0;
  const isHighRisk = hasPrediction ? predictionData.is_high_risk : false;
  const riskEvents = hasPrediction ? predictionData.risk_events || [] : [];
  const strategyBadge = hasPrediction ? predictionData.strategy_badge : "";
  const confirmationScore = hasPrediction
    ? predictionData.confirmation_score
    : undefined;
  const confirmationChecks = hasPrediction
    ? predictionData.confirmation_checks
    : null;

  return (
    <div className="min-h-screen bg-[#0b121e] px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-[1400px]">
        <Header
          modelVersion={modelVersion || "v1"}
          lastUpdated={lastUpdated}
          onRefresh={fetchPrices}
          isRefreshing={pricesLoading}
          selectedCoin={selectedCoin}
          onCoinChange={(c) => setSelectedCoin(c as CoinKey)}
          onPredict={handlePredict}
          isPredicting={isLoading}
        />

        {error && (
          <div className="dash-panel mb-4 border border-red-500/30">
            <p className="text-sm font-semibold text-red-400">API error</p>
            <p className="mt-1 text-xs text-slate-400">{error}</p>
          </div>
        )}

        <div className="mb-5">
          <PredictionBox
            prediction={currentPrediction}
            confidence={currentConfidence}
            rawPrediction={rawPrediction}
            badge={strategyBadge}
            confidenceLabel={predictionData?.confidence_label}
            decisionReason={
              hasPrediction ? shortDecisionReason(predictionData) : undefined
            }
            probs={probs}
            isLoading={isLoading}
            error={showPredictError ? error : null}
            hasData={hasPrediction && !showPredictError}
          />
        </div>

        <div className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          {(["BTC", "ETH", "SOL"] as CoinKey[]).map((coin) => (
            <PriceCard
              key={coin}
              coin={coin}
              price={priceData[coin].price}
              change={priceData[coin].change}
              chartData={priceData[coin].chartData}
              high24h={priceData[coin].high24h}
              low24h={priceData[coin].low24h}
            />
          ))}
        </div>

        <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SentimentCard
            fearGreedIndex={fearGreedIndex}
            newsSentiment={newsSentiment}
            riskScore={riskScore}
            isHighRisk={isHighRisk}
            riskEvents={riskEvents}
            newsLabel={predictionData?.news_sentiment_label}
            fearGreedValue={predictionData?.fear_greed_value}
            fearGreedLabel={predictionData?.fear_greed_label}
            riskLevel={predictionData?.risk_level}
            topHeadlines={predictionData?.top_headlines || []}
            fearGreedHistory={predictionData?.fear_greed_history}
            fearGreedTrend={predictionData?.fear_greed_trend}
            fearGreedTrendPlain={predictionData?.fear_greed_trend_plain}
            newsTakeaway={predictionData?.news_takeaway}
            isLoading={isLoading}
            isEmpty={!hasPrediction && !isLoading}
          />
          <TechnicalIndicators
            history={hasPrediction ? predictionData.indicator_history : null}
            confirmationChecks={confirmationChecks}
            confirmationScore={confirmationScore}
            isLoading={isLoading}
            tabExplanations={hasPrediction ? predictionData.tab_explanations : null}
            groupedIndicators={hasPrediction ? predictionData.grouped_indicators || [] : []}
          />
        </div>

        <DecisionSupportExtras
          hasPrediction={hasPrediction && !showPredictError}
          isLoading={isLoading}
          whatWouldChange={predictionData?.what_would_change}
          changeSinceLast={predictionData?.change_since_last}
          signalHistory={predictionData?.signal_history || []}
          priceZone={predictionData?.price_zone_context}
        />

        <div className="mb-2">
          <WhyThisSignal
            explanation={predictionData?.human_readable_explanation}
            hasPrediction={hasPrediction && !showPredictError}
            isLoading={isLoading}
            error={showPredictError ? error : null}
            rawPrediction={rawPrediction}
            finalDecision={hasPrediction ? currentPrediction : undefined}
            probs={probs}
            confirmationScore={confirmationScore}
            newsLabel={predictionData?.news_sentiment_label}
            fearGreedLabel={predictionData?.fear_greed_label}
            riskLevel={predictionData?.risk_level}
            riskEventCount={riskEvents.length}
            confidence={currentConfidence}
            badge={strategyBadge}
            passedConfirmations={predictionData?.passed_confirmations || []}
            failedConfirmations={predictionData?.failed_confirmations || []}
            groupedIndicators={predictionData?.grouped_indicators || []}
          />
        </div>

        <StatusBar />
      </div>
    </div>
  );
};

export default Index;
