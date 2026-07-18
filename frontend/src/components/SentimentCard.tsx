import { Activity, Newspaper, Shield, Link2 } from "lucide-react";
import { useState } from "react";

interface Headline {
  title?: string;
  source?: string;
  age_hours?: number | null;
  vader_compound?: number;
}

interface FgPoint {
  value?: number;
  label?: string;
  timestamp?: string | null;
}

interface SentimentCardProps {
  fearGreedIndex: number;
  newsSentiment: number;
  riskScore?: number;
  isHighRisk?: boolean;
  riskEvents?: string[];
  newsLabel?: string;
  fearGreedValue?: number;
  fearGreedLabel?: string;
  riskLevel?: string;
  topHeadlines?: Headline[];
  fearGreedHistory?: {
    now?: FgPoint | null;
    yesterday?: FgPoint | null;
    last_week?: FgPoint | null;
    last_month?: FgPoint | null;
  } | null;
  fearGreedTrend?: string;
  fearGreedTrendPlain?: string;
  newsTakeaway?: { summary?: string; tone?: string } | null;
  isLoading?: boolean;
  isEmpty?: boolean;
}

const headlineTone = (v?: number) => {
  if (v == null) return { label: "Neutral", cls: "bg-slate-700/80 text-slate-300" };
  if (v <= -0.2) return { label: "Bearish", cls: "bg-red-500/20 text-red-400" };
  if (v >= 0.2) return { label: "Bullish", cls: "bg-emerald-500/20 text-emerald-400" };
  return { label: "Neutral", cls: "bg-slate-700/80 text-slate-300" };
};

const ageLabel = (h?: number | null) => {
  if (h == null) return "";
  if (h < 1) return `${Math.max(1, Math.round(h * 60))}m ago`;
  if (h < 24) return `${Math.round(h)}h ago`;
  return `${Math.round(h / 24)}d ago`;
};

const FgGauge = ({ value }: { value: number }) => {
  const v = Math.min(100, Math.max(0, value));
  // Map 0–100 onto a semi-circle rotation: -90deg (left) to +90deg (right)
  const angle = -90 + (v / 100) * 180;
  return (
    <div className="relative w-full max-w-[180px] mx-auto h-[96px]">
      <svg viewBox="0 0 200 110" className="w-full h-full">
        <defs>
          <linearGradient id="fgArc" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="35%" stopColor="#f97316" />
            <stop offset="55%" stopColor="#eab308" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
        </defs>
        <path
          d="M20 100 A80 80 0 0 1 180 100"
          fill="none"
          stroke="url(#fgArc)"
          strokeWidth="14"
          strokeLinecap="round"
          opacity="0.9"
        />
        <g transform={`rotate(${angle} 100 100)`}>
          <line x1="100" y1="100" x2="100" y2="32" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
          <circle cx="100" cy="100" r="7" fill="#f8fafc" />
        </g>
      </svg>
      <div className="absolute left-1/2 bottom-1 -translate-x-1/2 text-center">
        <p className="text-[20px] font-bold text-orange-300 leading-none">{Math.round(v)}</p>
      </div>
    </div>
  );
};

const histRow = (title: string, point?: FgPoint | null) => (
  <div className="flex items-center justify-between gap-2 py-1.5 border-b border-white/[0.05] last:border-0">
    <div>
      <p className="text-[11px] text-slate-400">{title}</p>
      <p className="text-[12px] font-medium text-orange-200/90">
        {point?.label || "—"}
      </p>
    </div>
    <span className="w-8 h-8 rounded-full bg-orange-500/20 border border-orange-400/30 flex items-center justify-center text-[12px] font-semibold text-orange-200">
      {point?.value ?? "—"}
    </span>
  </div>
);

const SentimentCard = ({
  fearGreedIndex,
  newsSentiment,
  riskScore = 0,
  isHighRisk = false,
  riskEvents = [],
  newsLabel,
  fearGreedValue,
  fearGreedLabel,
  riskLevel,
  topHeadlines = [],
  fearGreedHistory,
  fearGreedTrendPlain,
  newsTakeaway,
  isLoading = false,
  isEmpty = false,
}: SentimentCardProps) => {
  const [open, setOpen] = useState(true);

  const riskLbl =
    riskLevel ||
    (isHighRisk || riskScore >= 0.6 ? "High" : riskScore >= 0.3 ? "Medium" : "Low");
  const riskColor =
    isHighRisk || riskScore >= 0.6
      ? "text-red-400"
      : riskScore >= 0.3
        ? "text-amber-400"
        : "text-emerald-400";

  const fg = Math.min(100, Math.max(0, Number(fearGreedValue ?? 50)));
  const hist = fearGreedHistory || {};

  if (isLoading) {
    return (
      <div className="dash-panel h-full animate-pulse">
        <div className="h-5 w-40 bg-white/5 rounded mb-5" />
        <div className="space-y-4">
          <div className="h-14 bg-white/5 rounded" />
          <div className="h-14 bg-white/5 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="dash-panel h-full flex flex-col">
      <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-1">
        Market mood &amp; risk
      </p>
      <h3 className="text-[16px] font-semibold text-white mb-1">Sentiment context</h3>
      <p className="text-[12px] text-slate-400 mb-4 leading-relaxed">
        Extra context only — it can block a risky BUY, but it does not invent BUY/SELL from HOLD.
      </p>

      {/* F&G gauge + history */}
      {!isEmpty && (
        <div className="mb-4 rounded-xl border border-white/[0.06] bg-[#0f172a]/40 p-3">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="sm:w-[45%] text-center">
              <p className="text-[11px] text-slate-400 mb-1">Fear &amp; Greed Index</p>
              <p className="text-[13px] font-semibold text-orange-300 mb-1">
                Now: {fearGreedLabel || "—"}
              </p>
              <FgGauge value={fg} />
              <p className="text-[10px] text-slate-500 mt-1">alternative.me · live</p>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-semibold text-white mb-1">Historical values</p>
              {histRow("Now", hist.now || { value: fearGreedValue, label: fearGreedLabel })}
              {histRow("Yesterday", hist.yesterday)}
              {histRow("Last week", hist.last_week)}
              {histRow("Last month", hist.last_month)}
              {fearGreedTrendPlain && (
                <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                  {fearGreedTrendPlain}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 flex-1">
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-xl bg-orange-500/15 flex items-center justify-center shrink-0">
              <Activity className="w-5 h-5 text-orange-400" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] text-slate-400 mb-0.5">Normalized F&amp;G</p>
              <p className="text-[14px] font-semibold text-orange-300">
                {isEmpty
                  ? "—"
                  : `${fearGreedIndex >= 0 ? "+" : ""}${Number(fearGreedIndex).toFixed(2)}`}
              </p>
              <p className="text-[11px] text-slate-500">Mapped from 0–100 into −1…+1</p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/15 flex items-center justify-center shrink-0">
              <Newspaper className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-[11px] text-slate-400 mb-0.5">News Sentiment</p>
              <p
                className={`text-[15px] font-semibold ${
                  newsSentiment < 0
                    ? "text-red-400"
                    : newsSentiment > 0
                      ? "text-emerald-400"
                      : "text-slate-200"
                }`}
              >
                {isEmpty ? "—" : newsLabel || "Neutral"}
              </p>
              <p className="text-[12px] text-slate-400 mt-0.5">
                Score:{" "}
                {isEmpty
                  ? "—"
                  : `${newsSentiment > 0 ? "+" : ""}${Number(newsSentiment).toFixed(2)}`}
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center shrink-0">
              <Shield className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-[11px] text-slate-400 mb-0.5">Risk Level</p>
              <p className={`text-[15px] font-semibold ${riskColor}`}>
                {isEmpty ? "—" : riskLbl}
              </p>
              <p className="text-[12px] text-slate-400 mt-0.5">
                Score: {isEmpty ? "—" : Number(riskScore).toFixed(2)} · Events:{" "}
                {isEmpty ? "—" : riskEvents.length}
              </p>
            </div>
          </div>

          {!isEmpty && newsTakeaway?.summary && (
            <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
              <p className="text-[11px] font-semibold text-slate-200 mb-1">News takeaway</p>
              <p className="text-[12px] text-slate-300 leading-relaxed">{newsTakeaway.summary}</p>
            </div>
          )}
        </div>

        <div className="md:border-l md:border-white/[0.06] md:pl-5 flex flex-col gap-3">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex w-full items-center justify-between text-[13px] font-semibold text-white"
          >
            <span>Recent headlines</span>
            <span className="text-slate-400 text-xs">{open ? "▾" : "▸"}</span>
          </button>

          {open && (
            <div className="space-y-3">
              {isEmpty ? (
                <p className="text-[12px] text-slate-400">Headlines appear after Predict.</p>
              ) : topHeadlines.length === 0 ? (
                <p className="text-[12px] text-slate-400">No recent headlines for this coin.</p>
              ) : (
                topHeadlines.slice(0, 3).map((h, i) => {
                  const tone = headlineTone(h.vader_compound);
                  return (
                    <div key={i}>
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-[11px] font-medium text-slate-300">
                          {h.source || "Source"}
                        </span>
                        {h.age_hours != null && (
                          <span className="text-[11px] text-slate-500">
                            · {ageLabel(h.age_hours)}
                          </span>
                        )}
                        <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${tone.cls}`}>
                          {tone.label}
                        </span>
                      </div>
                      <p className="text-[12px] text-slate-200 leading-snug">{h.title}</p>
                    </div>
                  );
                })
              )}
            </div>
          )}

          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 mt-auto">
            <div className="flex items-start gap-2">
              <Link2 className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
              <div className="text-[11px] text-slate-400 leading-relaxed space-y-1">
                <p className="text-slate-300 font-medium">Sources</p>
                <p>
                  Fear &amp; Greed:{" "}
                  <span className="text-slate-200">api.alternative.me/fng</span> (live)
                </p>
                <p>
                  News: CoinTelegraph · CoinDesk · Decrypt · Bitcoin Magazine RSS + VADER
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SentimentCard;
