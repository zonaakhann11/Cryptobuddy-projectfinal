import { Bitcoin, CircleDollarSign, Coins } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface PriceCardProps {
  coin: "BTC" | "ETH" | "SOL";
  price: number;
  change: number;
  chartData: { value: number }[];
  high24h?: number;
  low24h?: number;
}

const coinConfig = {
  BTC: { name: "Bitcoin", symbol: "BTC", icon: Bitcoin, color: "#f7931a" },
  ETH: { name: "Ethereum", symbol: "ETH", icon: CircleDollarSign, color: "#627eea" },
  SOL: { name: "Solana", symbol: "SOL", icon: Coins, color: "#14f195" },
};

const fmt = (n?: number) => {
  if (n == null || Number.isNaN(n) || n === 0) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: n < 10 ? 2 : 2,
    maximumFractionDigits: n < 10 ? 4 : 2,
  });
};

const PriceCard = ({ coin, price, change, chartData, high24h, low24h }: PriceCardProps) => {
  const config = coinConfig[coin];
  const isPositive = change >= 0;
  const Icon = config.icon;

  return (
    <div className="dash-panel !p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: `${config.color}22` }}
          >
            <Icon className="w-4.5 h-4.5" style={{ color: config.color }} />
          </div>
          <span className="text-[13px] font-semibold text-white">
            {config.name} ({config.symbol})
          </span>
        </div>
        <span
          className={`text-[12px] font-semibold ${
            isPositive ? "text-emerald-400" : "text-red-400"
          }`}
        >
          {isPositive ? "" : ""}
          {change.toFixed(3)}%
        </span>
      </div>

      <div className="text-[26px] font-bold text-white tracking-tight mb-1">
        ${fmt(price)}
      </div>

      <div className="h-[72px] mb-3 -mx-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id={`spark-${coin}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              fill={`url(#spark-${coin})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex justify-between text-[11px] text-slate-400 pt-2 border-t border-white/[0.06]">
        <span>
          24H Low <span className="text-slate-200">${fmt(low24h)}</span>
        </span>
        <span>
          24H High <span className="text-slate-200">${fmt(high24h)}</span>
        </span>
      </div>
    </div>
  );
};

export default PriceCard;
