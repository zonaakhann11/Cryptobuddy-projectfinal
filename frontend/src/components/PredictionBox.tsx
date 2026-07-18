interface PredictionBoxProps {
  prediction: "BUY" | "SELL" | "HOLD";
  confidence: number;
  rawPrediction?: string;
  badge?: string;
  confidenceLabel?: string;
  decisionReason?: string;
  probs?: { sell: number; buy: number; hold: number };
  isLoading?: boolean;
  error?: string | null;
  hasData?: boolean;
}

const tone = (d?: string) => {
  if (d === "BUY") return "text-emerald-400";
  if (d === "SELL") return "text-red-400";
  return "text-amber-400";
};

const badgeText = (badge?: string) => {
  if (!badge) return "";
  return badge
    .replace(/^HOLD — /, "")
    .replace(/^BUY Blocked — /, "BUY blocked · ")
    .replace(/^High-Confidence /, "")
    .replace(/^Moderate /, "");
};

const PredictionBox = ({
  prediction,
  confidence,
  rawPrediction,
  badge,
  confidenceLabel,
  decisionReason,
  probs,
  isLoading = false,
  error = null,
  hasData = false,
}: PredictionBoxProps) => {
  const buyPct = probs ? Math.round(probs.buy * 100) : 0;
  const sellPct = probs ? Math.round(probs.sell * 100) : 0;
  const holdPct = probs ? Math.round(probs.hold * 100) : 0;

  const confLabel =
    confidenceLabel ||
    (confidence >= 55
      ? "Higher confidence"
      : confidence >= 40
        ? "Moderate confidence"
        : "Lower confidence");

  if (error) {
    return (
      <div className="dash-panel h-full border-red-500/30">
        <p className="text-sm font-semibold text-red-400">Could not load suggestion</p>
        <p className="text-xs text-slate-400 mt-2">{error}</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="dash-panel h-full animate-pulse space-y-4">
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-14 bg-white/5 rounded-lg" />
          ))}
        </div>
        <div className="space-y-2">
          <div className="h-2 bg-white/5 rounded" />
          <div className="h-2 bg-white/5 rounded" />
          <div className="h-2 bg-white/5 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="dash-panel h-full">
      <p className="text-[12px] text-slate-400 mb-4 leading-relaxed">
        Predictive outlook for the next hour, plus a filtered suggestion. You decide whether to act.
      </p>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-5 xl:gap-6">
        <div>
          <p className="text-[11px] text-slate-400 font-medium mb-1.5">Model outlook</p>
          <p className={`text-[32px] leading-none font-bold ${tone(hasData ? rawPrediction : undefined)}`}>
            {hasData ? rawPrediction || "—" : "—"}
          </p>
          <p className="text-[11px] text-slate-500 mt-2">What the ML model says first</p>
        </div>

        <div>
          <p className="text-[11px] text-slate-400 font-medium mb-1.5">Suggested action</p>
          <p className={`text-[32px] leading-none font-bold ${tone(hasData ? prediction : undefined)}`}>
            {hasData ? prediction : "—"}
          </p>
          {hasData && badge && (
            <span className="inline-flex mt-2.5 text-[11px] px-2.5 py-[3px] rounded-full border border-amber-400/60 text-amber-300 font-medium">
              {badgeText(badge) || badge}
            </span>
          )}
          <p className="text-[11px] text-slate-500 mt-2">After checks &amp; risk filters</p>
        </div>

        <div>
          <p className="text-[11px] text-slate-400 font-medium mb-1.5">Confidence</p>
          <p className="text-[32px] leading-none font-bold text-amber-400">
            {hasData ? `${confidence}%` : "—"}
          </p>
          {hasData && (
            <>
              <p className="text-[12px] text-slate-400 mt-2">{confLabel}</p>
              <div className="mt-2 h-1.5 rounded-full bg-[#1e293b] overflow-hidden max-w-[140px]">
                <div
                  className="h-full rounded-full bg-amber-400"
                  style={{ width: `${Math.min(100, Math.max(0, confidence))}%` }}
                />
              </div>
            </>
          )}
        </div>

        <div className="col-span-2 xl:col-span-1">
          <p className="text-[11px] text-slate-400 font-medium mb-1.5">Why this suggestion</p>
          <p className="text-[13px] text-slate-300 leading-relaxed">
            {hasData
              ? decisionReason ||
                "Technical checks and market context shaped this suggestion."
              : "Press PREDICT to load a live outlook and suggestion."}
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-2.5">
        <p className="text-[11px] text-slate-500 mb-1">How strongly the model leans each way</p>
        {(
          [
            { key: "BUY", pct: buyPct, bar: "bg-emerald-500", label: "text-emerald-400" },
            { key: "SELL", pct: sellPct, bar: "bg-red-500", label: "text-red-400" },
            { key: "HOLD", pct: holdPct, bar: "bg-amber-400", label: "text-amber-400" },
          ] as const
        ).map((row) => (
          <div key={row.key} className="flex items-center gap-3">
            <span className={`w-10 text-[12px] font-semibold ${row.label}`}>{row.key}</span>
            <div className="flex-1 h-2 rounded-full bg-[#1e293b] overflow-hidden">
              <div
                className={`h-full rounded-full ${row.bar} transition-all duration-500`}
                style={{ width: hasData ? `${row.pct}%` : "0%" }}
              />
            </div>
            <span className="w-10 text-right text-[12px] tabular-nums text-slate-400">
              {hasData ? `${row.pct}%` : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PredictionBox;
