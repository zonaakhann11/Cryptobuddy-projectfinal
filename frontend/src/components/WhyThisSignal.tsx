import {
  Sparkles,
  Gauge,
  ListChecks,
  Newspaper,
  Activity,
  ShieldCheck,
} from "lucide-react";

interface WhyThisSignalProps {
  explanation?: string | null;
  hasPrediction?: boolean;
  isLoading?: boolean;
  error?: string | null;
  rawPrediction?: string;
  finalDecision?: string;
  probs?: { sell: number; buy: number; hold: number };
  confirmationScore?: number;
  newsLabel?: string;
  fearGreedLabel?: string;
  riskLevel?: string;
  riskEventCount?: number;
  confidence?: number;
  badge?: string;
  passedConfirmations?: string[];
  failedConfirmations?: string[];
  groupedIndicators?: Array<{
    group: string;
    status: string;
    score: number;
    strongest_support?: string;
    strongest_conflict?: string;
    what_it_means?: string;
  }>;
}

const WhyThisSignal = ({
  explanation,
  hasPrediction = false,
  isLoading = false,
  error = null,
  rawPrediction,
  finalDecision,
  probs,
  confirmationScore,
  newsLabel,
  fearGreedLabel,
  riskLevel,
  riskEventCount = 0,
  confidence,
  passedConfirmations = [],
  failedConfirmations = [],
  groupedIndicators = [],
}: WhyThisSignalProps) => {
  const buy = probs ? Math.round(probs.buy * 100) : null;
  const sell = probs ? Math.round(probs.sell * 100) : null;
  const hold = probs ? Math.round(probs.hold * 100) : null;

  const supports = passedConfirmations.length
    ? passedConfirmations.join("; ")
    : groupedIndicators
        .filter((g) => g.status === "Bullish")
        .map((g) => g.group)
        .join(", ") || "few supporting checks";
  const conflicts = failedConfirmations.length
    ? failedConfirmations.join("; ")
    : groupedIndicators
        .filter((g) => g.status === "Bearish" || g.status === "High Risk")
        .map((g) => g.group)
        .join(", ") || "no strong conflict listed";

  let body = "";
  if (isLoading) {
    body = "Gathering model outlook, technical checks, news mood, and risk…";
  } else if (error) {
    body = `Could not build the decision guide: ${error}`;
  } else if (!hasPrediction) {
    body =
      "Press PREDICT to see a next-hour outlook and a plain-English decision guide. " +
      "Crypto Buddy suggests — you decide.";
  } else {
    body =
      explanation?.trim() ||
      `Suggested action ${finalDecision} (model said ${rawPrediction}). ` +
        `Lean: BUY ${buy}% / SELL ${sell}% / HOLD ${hold}%. ` +
        `Supporting: ${supports}. Watching: ${conflicts}.`;
  }

  const factors: { icon: typeof Gauge; text: string }[] = [];
  if (hasPrediction) {
    factors.push({
      icon: Gauge,
      text: `Outlook ${rawPrediction} → suggestion ${finalDecision} (${confidence ?? "—"}% confidence).`,
    });
    factors.push({
      icon: ListChecks,
      text: `Checks ${confirmationScore ?? 0}/6 · Supporting: ${supports}.`,
    });
    factors.push({
      icon: Newspaper,
      text: `News mood: ${newsLabel || "n/a"}.`,
    });
    factors.push({
      icon: Activity,
      text: `Market fear/greed: ${fearGreedLabel || "n/a"}.`,
    });
    factors.push({
      icon: ShieldCheck,
      text:
        riskEventCount > 0
          ? `Risk flags: ${riskEventCount} (${riskLevel || "n/a"}).`
          : `No high-risk flags · risk ${riskLevel || "n/a"}.`,
    });
  }

  return (
    <div className="dash-panel">
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="flex gap-4 flex-1 min-w-0">
          <div className="w-11 h-11 rounded-full bg-violet-500/20 border border-violet-400/30 flex items-center justify-center shrink-0">
            <Sparkles className="w-5 h-5 text-violet-300" />
          </div>
          <div className="min-w-0">
            <h3 className="text-[16px] font-semibold text-white mb-1">Decision support</h3>
            <p className="text-[11px] text-slate-500 mb-2">
              Read the evidence, then choose for yourself — not financial advice.
            </p>
            <p className={`text-[13px] leading-relaxed ${error ? "text-red-400" : "text-slate-300"}`}>
              {body}
            </p>
            {hasPrediction && (
              <ul className="mt-3 space-y-1.5 text-[12px] text-slate-400">
                <li>
                  • What does the model think?{" "}
                  <span className="text-slate-200">{rawPrediction}</span>
                </li>
                <li>
                  • What is the filtered suggestion?{" "}
                  <span className="text-slate-200">{finalDecision}</span>
                </li>
                <li>
                  • What supports it? <span className="text-slate-200">{supports}</span>
                </li>
                <li>
                  • What disagrees? <span className="text-slate-200">{conflicts}</span>
                </li>
                <li>
                  • News / fear-greed?{" "}
                  <span className="text-slate-200">
                    {newsLabel || "—"} · {fearGreedLabel || "—"}
                  </span>
                </li>
                <li>
                  • Extra risk?{" "}
                  <span className="text-slate-200">
                    {riskEventCount > 0 ? `Yes (${riskEventCount})` : "No"}
                  </span>
                </li>
                <li>
                  • Model lean?{" "}
                  <span className="text-slate-200">
                    BUY {buy}% · SELL {sell}% · HOLD {hold}%
                  </span>
                </li>
              </ul>
            )}
          </div>
        </div>

        {hasPrediction && factors.length > 0 && (
          <div className="lg:w-72 shrink-0 lg:border-l lg:border-white/[0.06] lg:pl-6 border-t border-white/[0.06] pt-4 lg:pt-0 lg:border-t-0">
            <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-3">
              At a glance
            </p>
            <ul className="space-y-2.5">
              {factors.map((f, i) => {
                const Icon = f.icon;
                return (
                  <li key={i} className="flex items-start gap-2 text-[12px] text-slate-300">
                    <Icon className="w-3.5 h-3.5 mt-0.5 text-slate-500 shrink-0" />
                    <span>{f.text}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default WhyThisSignal;
