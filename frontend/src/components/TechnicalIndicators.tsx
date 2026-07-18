import { useState } from "react";
import { Check, X, Minus, Info } from "lucide-react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Line,
  LineChart,
  Bar,
  BarChart,
  ComposedChart,
  YAxis,
  ReferenceLine,
} from "recharts";

const tabs = ["MACD", "RSI", "Moving Average", "Volume"];

const generateMACDData = () =>
  Array.from({ length: 36 }, (_, i) => ({
    macd: Math.sin(i * 0.28) * 40 + Math.random() * 8,
    signal: Math.sin(i * 0.28 + 0.45) * 32 + Math.random() * 6,
    histogram: Math.sin(i * 0.22) * 28,
  }));

const generateRSIData = () =>
  Array.from({ length: 36 }, (_, i) => ({
    value: 50 + Math.sin(i * 0.2) * 25 + Math.random() * 8,
  }));

const generateMAData = () => {
  let base = 100;
  return Array.from({ length: 36 }, () => {
    base += (Math.random() - 0.5) * 4;
    return { price: base, ma7: base - 1.5, ma25: base - 4 };
  });
};

const generateVolumeData = () =>
  Array.from({ length: 36 }, () => ({
    value: Math.random() * 100 + 20,
  }));

interface IndicatorHistoryItem {
  macd: number;
  signal: number;
  histogram: number;
  rsi: number;
  price: number;
  ma7: number;
  ma25: number;
  volume: number;
  open: number;
  close: number;
}

export interface ConfirmationCheck {
  id?: string;
  label: string;
  status: string;
}

interface TechnicalIndicatorsProps {
  history?: IndicatorHistoryItem[] | null;
  confirmationChecks?: ConfirmationCheck[] | null;
  confirmationScore?: number;
  isLoading?: boolean;
  tabExplanations?: any;
  groupedIndicators?: Array<{
    group: string;
    status: string;
    score: number;
    explanation?: string;
    strongest_support?: string;
    strongest_conflict?: string;
  }>;
}

const DEFAULT_CHECKS: ConfirmationCheck[] = [
  { id: "momentum", label: "Momentum Agreement", status: "Not Available" },
  { id: "rsi_healthy", label: "RSI Healthy", status: "Not Available" },
  { id: "rsi_rising", label: "RSI Rising", status: "Not Available" },
  { id: "macd", label: "MACD", status: "Not Available" },
  { id: "volume", label: "Volume", status: "Not Available" },
  { id: "price_volume", label: "Price-Volume Momentum", status: "Not Available" },
];

const displayLabel = (label: string) =>
  label === "Momentum" ? "Momentum Agreement" : label;

const TechnicalIndicators = ({
  history,
  confirmationChecks,
  confirmationScore,
  isLoading = false,
  tabExplanations,
  groupedIndicators = [],
}: TechnicalIndicatorsProps) => {
  const [activeTab, setActiveTab] = useState("MACD");
  const hasHistory = !!(history && history.length > 0);

  const macdData = hasHistory
    ? history!.map((item) => ({
        macd: item.macd,
        signal: item.signal,
        histogram: item.histogram,
      }))
    : generateMACDData();

  const rsiData = hasHistory
    ? history!.map((item) => ({ value: item.rsi }))
    : generateRSIData();

  const maData = hasHistory
    ? history!.map((item) => ({
        price: item.price,
        ma7: item.ma7,
        ma25: item.ma25,
      }))
    : generateMAData();

  const volumeData = hasHistory
    ? history!.map((item) => ({ value: item.volume }))
    : generateVolumeData();

  const checks =
    confirmationChecks && confirmationChecks.length > 0
      ? confirmationChecks
      : DEFAULT_CHECKS;

  const passedCount =
    typeof confirmationScore === "number"
      ? confirmationScore
      : checks.filter((c) => c.status === "Passed").length;

  const renderChart = () => {
    if (activeTab === "MACD") {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={macdData}>
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <ReferenceLine y={0} stroke="#334155" strokeDasharray="3 3" />
            <Bar
              dataKey="histogram"
              fill="#22c55e"
              opacity={0.55}
              shape={(props: any) => {
                const { x, y, width, height, payload } = props;
                const positive = (payload?.histogram ?? 0) >= 0;
                return (
                  <rect
                    x={x}
                    y={positive ? y : y + height}
                    width={width}
                    height={Math.abs(height)}
                    fill={positive ? "#22c55e" : "#ef4444"}
                    opacity={0.55}
                  />
                );
              }}
            />
            <Line type="monotone" dataKey="macd" stroke="#3b82f6" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="signal" stroke="#ef4444" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      );
    }
    if (activeTab === "RSI") {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rsiData}>
            <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
            <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fill="#3b82f633" />
          </AreaChart>
        </ResponsiveContainer>
      );
    }
    if (activeTab === "Moving Average") {
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={maData}>
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
            <Line type="monotone" dataKey="price" stroke="#475569" strokeWidth={1} dot={false} />
            <Line type="monotone" dataKey="ma7" stroke="#3b82f6" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="ma25" stroke="#ef4444" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      );
    }
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={volumeData}>
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
          <Bar dataKey="value" fill="#3b82f6" opacity={0.65} />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <div className="dash-panel h-full">
      <h3 className="text-[16px] font-semibold text-white mb-1">Market evidence</h3>
      <p className="text-[12px] text-slate-400 mb-4 leading-relaxed">
        Charts plus plain-English summaries. Use them to understand the suggestion — not as a trade order.
      </p>

      <div className="flex gap-2 mb-4 flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3.5 py-1.5 rounded-full text-[12px] font-semibold transition-colors ${
              activeTab === tab
                ? "bg-blue-500 text-white"
                : "bg-[#1e293b] text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="h-44 rounded-xl bg-[#0f172a]/60 border border-white/[0.04] p-2 mb-3 relative">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-slate-500">
            Loading charts…
          </div>
        ) : (
          renderChart()
        )}
      </div>

      {/* Per-tab plain-English snapshot */}
      <div className="mb-4 rounded-xl border border-white/[0.06] bg-[#0f172a]/40 px-3 py-2.5">
        {(() => {
          const te = tabExplanations || {};
          if (activeTab === "RSI") {
            const r = te.rsi;
            return (
              <p className="text-[12px] text-slate-300 leading-relaxed">
                <span className="text-white font-semibold">RSI: </span>
                {r
                  ? r.explanation
                  : "Run Predict to load a plain-English RSI reading."}
              </p>
            );
          }
          if (activeTab === "MACD") {
            const m = te.macd;
            return (
              <p className="text-[12px] text-slate-300 leading-relaxed">
                <span className="text-white font-semibold">MACD: </span>
                {m
                  ? m.explanation
                  : "Run Predict to load a plain-English MACD reading."}
              </p>
            );
          }
          if (activeTab === "Moving Average") {
            const m = te.moving_average;
            return (
              <p className="text-[12px] text-slate-300 leading-relaxed">
                <span className="text-white font-semibold">Moving averages: </span>
                {m
                  ? m.explanation
                  : "Run Predict to see whether price is above or below its recent path."}
              </p>
            );
          }
          const v = te.volume;
          return (
            <p className="text-[12px] text-slate-300 leading-relaxed">
              <span className="text-white font-semibold">Volume: </span>
              {v
                ? v.explanation
                : "Run Predict to see whether traders are participating."}
            </p>
          );
        })()}
      </div>

      {/* Grouped indicator summaries */}
      {groupedIndicators && groupedIndicators.length > 0 && (
        <div className="mb-4">
          <p className="text-[12px] font-semibold text-white mb-2">Five evidence groups</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {groupedIndicators.map((g: any) => (
              <div
                key={g.group}
                className="rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[12px] font-semibold text-white">{g.group}</span>
                  <span className="text-[11px] text-slate-400">
                    {g.status} · {g.score}/100
                  </span>
                </div>
                {g.what_it_means && (
                  <p className="text-[11px] text-slate-500 mb-1">{g.what_it_means}</p>
                )}
                <p className="text-[11px] text-slate-400 leading-snug">
                  {g.plain_summary || g.explanation || g.strongest_support || ""}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-white/[0.06] pt-4">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-[13px] font-semibold text-white">
            Technical checks:{" "}
            <span className="text-blue-400">{passedCount}/6</span>
          </p>
          <span title="These checks must support a BUY/SELL suggestion. If too few pass, you see HOLD.">
            <Info className="w-3.5 h-3.5 text-slate-500" />
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mb-3">
          Green = agrees with acting · Red = does not agree · Grey = not available
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {checks.map((check) => {
            const passed = check.status === "Passed";
            const failed = check.status === "Failed";
            return (
              <div
                key={check.id || check.label}
                className={`flex items-center gap-2 rounded-xl border px-2.5 py-2 ${
                  passed
                    ? "border-emerald-500/25 bg-emerald-500/10"
                    : failed
                      ? "border-red-500/25 bg-red-500/10"
                      : "border-white/10 bg-white/[0.03]"
                }`}
              >
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                    passed
                      ? "bg-emerald-500/20 text-emerald-400"
                      : failed
                        ? "bg-red-500/20 text-red-400"
                        : "bg-slate-700 text-slate-400"
                  }`}
                >
                  {passed ? <Check className="w-3 h-3" /> : failed ? <X className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                </span>
                <div className="min-w-0">
                  <p className="text-[11px] font-medium text-slate-100 truncate leading-tight">
                    {displayLabel(check.label)}
                  </p>
                  <p
                    className={`text-[10px] ${
                      passed ? "text-emerald-400" : failed ? "text-red-400" : "text-slate-500"
                    }`}
                  >
                    {passed ? "Agrees" : failed ? "Disagrees" : check.status}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TechnicalIndicators;
