import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CryptoLogo = () => (
  <svg viewBox="0 0 100 100" className="w-7 h-7" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="logo-grad-1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#3b82f6" />
        <stop offset="100%" stopColor="#60a5fa" />
      </linearGradient>
    </defs>
    <path
      d="M50 10 L85 30 L85 70 L50 90 L15 70 L15 30 Z"
      stroke="url(#logo-grad-1)"
      strokeWidth="4"
      fill="none"
      strokeLinejoin="round"
    />
    <path
      d="M45 35 Q 30 35, 30 50 Q 30 65, 45 65"
      stroke="#93c5fd"
      strokeWidth="6"
      strokeLinecap="round"
      fill="none"
    />
    <path
      d="M55 35 L 65 35 Q 75 35, 75 42.5 Q 75 50, 65 50 L 55 50 Z M55 50 L 68 50 Q 78 50, 78 57.5 Q 78 65, 68 65 L 55 65 Z"
      stroke="#93c5fd"
      strokeWidth="6"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    />
  </svg>
);

interface HeaderProps {
  modelVersion?: string;
  lastUpdated?: Date | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  selectedCoin: string;
  onCoinChange: (coin: string) => void;
  onPredict: () => void;
  isPredicting?: boolean;
}

const Header = ({
  modelVersion = "v1",
  lastUpdated = null,
  onRefresh,
  isRefreshing = false,
  selectedCoin,
  onCoinChange,
  onPredict,
  isPredicting = false,
}: HeaderProps) => {
  const timeLabel = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    : "—";

  return (
    <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-[#1a2332]">
          <CryptoLogo />
        </div>
        <div>
          <h1 className="text-[22px] font-bold leading-tight tracking-tight text-white sm:text-[26px]">
            Crypto Buddy
          </h1>
          <p className="mt-0.5 text-[12px] font-medium text-emerald-400">
            {modelVersion === "v2"
              ? "Updated model — live"
              : "Production model — live"}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[13px] font-medium text-slate-400">Select Coin:</span>
        <Select value={selectedCoin} onValueChange={onCoinChange}>
          <SelectTrigger className="h-10 w-[180px] rounded-xl border-white/10 bg-[#141c2b] text-sm font-medium text-white">
            <SelectValue placeholder="Select coin" />
          </SelectTrigger>
          <SelectContent className="z-50 border-white/10 bg-[#141c2b] text-white">
            <SelectItem value="BTC">Bitcoin (BTC)</SelectItem>
            <SelectItem value="ETH">Ethereum (ETH)</SelectItem>
            <SelectItem value="SOL">Solana (SOL)</SelectItem>
          </SelectContent>
        </Select>
        <Button
          onClick={onPredict}
          disabled={isPredicting}
          className="h-10 rounded-xl bg-blue-500 px-6 text-sm font-bold text-white hover:bg-blue-500/90"
        >
          {isPredicting ? <Loader2 className="h-4 w-4 animate-spin" /> : "PREDICT"}
        </Button>
      </div>

      <div className="flex items-center gap-2 text-[13px] text-slate-400 lg:justify-end">
        <span>
          Last Updated: <span className="text-slate-200">{timeLabel}</span>
        </span>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-white/15 hover:bg-white/5 disabled:opacity-50"
            aria-label="Refresh"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;
