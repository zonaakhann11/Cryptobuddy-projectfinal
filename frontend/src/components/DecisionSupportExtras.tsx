import { ArrowLeftRight, History, MapPin, Unlock } from "lucide-react";

interface DecisionSupportExtrasProps {
  hasPrediction?: boolean;
  isLoading?: boolean;
  whatWouldChange?: any;
  changeSinceLast?: any;
  signalHistory?: any[];
  priceZone?: any;
}

const timeLabel = (iso?: string) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
};

const DecisionSupportExtras = ({
  hasPrediction = false,
  isLoading = false,
  whatWouldChange,
  changeSinceLast,
  signalHistory = [],
  priceZone,
}: DecisionSupportExtrasProps) => {
  if (isLoading) {
    return (
      <div className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="dash-panel h-40 animate-pulse bg-white/[0.03]" />
        ))}
      </div>
    );
  }

  if (!hasPrediction) {
    return (
      <div className="dash-panel mb-5">
        <p className="text-[13px] text-slate-400">
          Run Predict to fill decision-support cards: what would change the signal, recent
          changes, signal history, and price zone context.
        </p>
      </div>
    );
  }

  const w = whatWouldChange || {};
  const c = changeSinceLast || {};
  const zone = priceZone || {};

  return (
    <div className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {/* What would change */}
      <div className="dash-panel">
        <div className="flex items-center gap-2 mb-2">
          <Unlock className="w-4 h-4 text-sky-400" />
          <h3 className="text-[13px] font-semibold text-white">What would change this?</h3>
        </div>
        <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">{w.headline}</p>
        {w.final_decision === "HOLD" ? (
          <div className="space-y-3">
            <div>
              <p className="text-[10px] uppercase tracking-wide text-emerald-400/80 mb-1">
                Toward BUY
              </p>
              <ul className="space-y-1">
                {(w.to_unlock_buy || []).slice(0, 3).map((t: string, i: number) => (
                  <li key={i} className="text-[11px] text-slate-300 leading-snug">
                    • {t}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-red-400/80 mb-1">
                Toward SELL
              </p>
              <ul className="space-y-1">
                {(w.to_unlock_sell || []).slice(0, 3).map((t: string, i: number) => (
                  <li key={i} className="text-[11px] text-slate-300 leading-snug">
                    • {t}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-amber-400/80 mb-1">
              Would invalidate
            </p>
            <ul className="space-y-1">
              {(w.would_invalidate || []).slice(0, 4).map((t: string, i: number) => (
                <li key={i} className="text-[11px] text-slate-300 leading-snug">
                  • {t}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Change since last */}
      <div className="dash-panel">
        <div className="flex items-center gap-2 mb-2">
          <ArrowLeftRight className="w-4 h-4 text-violet-400" />
          <h3 className="text-[13px] font-semibold text-white">Since last prediction</h3>
        </div>
        <p className="text-[11px] text-slate-300 leading-relaxed mb-3">
          {c.summary || "—"}
        </p>
        {c.available && (c.changes || []).length > 0 ? (
          <ul className="space-y-1.5 max-h-36 overflow-y-auto">
            {c.changes.slice(0, 6).map((ch: any, i: number) => (
              <li key={i} className="text-[11px] text-slate-400">
                <span className="text-slate-200">{ch.label}:</span> {String(ch.before)} →{" "}
                {String(ch.after)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[11px] text-slate-500">
            {c.available ? "No field-level diffs." : "Need a second Predict on this coin."}
          </p>
        )}
      </div>

      {/* Signal history */}
      <div className="dash-panel">
        <div className="flex items-center gap-2 mb-2">
          <History className="w-4 h-4 text-amber-400" />
          <h3 className="text-[13px] font-semibold text-white">Signal history</h3>
        </div>
        {signalHistory.length === 0 ? (
          <p className="text-[11px] text-slate-500">No saved signals yet for this coin.</p>
        ) : (
          <div className="space-y-2">
            {signalHistory.map((row, i) => (
              <div
                key={i}
                className="flex items-center justify-between gap-2 border-b border-white/[0.04] pb-1.5 last:border-0"
              >
                <div className="min-w-0">
                  <p className="text-[10px] text-slate-500 truncate">{timeLabel(row.timestamp)}</p>
                  <p className="text-[11px] text-slate-300">
                    {row.raw_outlook || "—"} →{" "}
                    <span className="text-white font-medium">{row.final_decision}</span>
                  </p>
                </div>
                <span className="text-[11px] tabular-nums text-slate-400 shrink-0">
                  {row.confidence != null ? `${Math.round(Number(row.confidence) * 100)}%` : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Price zone */}
      <div className="dash-panel">
        <div className="flex items-center gap-2 mb-2">
          <MapPin className="w-4 h-4 text-emerald-400" />
          <h3 className="text-[13px] font-semibold text-white">Price zone</h3>
        </div>
        <div className="grid grid-cols-2 gap-2 mb-2">
          <div className="rounded-lg bg-white/[0.03] px-2 py-1.5">
            <p className="text-[10px] text-slate-500">Support</p>
            <p className="text-[13px] font-semibold text-emerald-300">
              {zone.nearest_support != null ? `$${Number(zone.nearest_support).toLocaleString()}` : "—"}
            </p>
            <p className="text-[10px] text-slate-500">
              {zone.distance_to_support_pct != null
                ? `${zone.distance_to_support_pct}% below`
                : ""}
            </p>
          </div>
          <div className="rounded-lg bg-white/[0.03] px-2 py-1.5">
            <p className="text-[10px] text-slate-500">Resistance</p>
            <p className="text-[13px] font-semibold text-red-300">
              {zone.nearest_resistance != null
                ? `$${Number(zone.nearest_resistance).toLocaleString()}`
                : "—"}
            </p>
            <p className="text-[10px] text-slate-500">
              {zone.distance_to_resistance_pct != null
                ? `${zone.distance_to_resistance_pct}% above`
                : ""}
            </p>
          </div>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          {zone.ema_plain || zone.plain_summary || "—"}
        </p>
      </div>
    </div>
  );
};

export default DecisionSupportExtras;
