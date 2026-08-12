import ErrorNotice from "@/components/ErrorNotice";
import { TickerFundamentals, TickerPrice } from "@/lib/api";

interface PriceCardProps {
  symbol: string;
  price: TickerPrice;
  fundamentals: TickerFundamentals;
  fundamentalsError?: string;
}

function formatNumber(n: number | null, digits = 2): string {
  return n === null ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function formatMarketCap(n: number | null): string {
  if (n === null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n}`;
}

export default function PriceCard({ symbol, price, fundamentals, fundamentalsError }: PriceCardProps) {
  const isUp = price.change >= 0;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">{symbol}</h2>
        <span className="text-sm text-zinc-500 dark:text-zinc-500">{new Date(price.timestamp).toLocaleString()}</span>
      </div>
      <div className="mt-2 flex items-baseline gap-3 font-mono">
        <span className="text-3xl font-semibold text-zinc-900 dark:text-zinc-50">
          ${formatNumber(price.last)}
        </span>
        <span className={isUp ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}>
          {isUp ? "+" : ""}
          {formatNumber(price.change)} ({isUp ? "+" : ""}
          {formatNumber(price.change_pct)}%)
        </span>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <div className="text-zinc-500 dark:text-zinc-500">P/E</div>
          <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">{formatNumber(fundamentals.pe_ratio)}</div>
        </div>
        <div>
          <div className="text-zinc-500 dark:text-zinc-500">Market Cap</div>
          <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">{formatMarketCap(fundamentals.market_cap)}</div>
        </div>
        <div>
          <div className="text-zinc-500 dark:text-zinc-500">EPS</div>
          <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">{formatNumber(fundamentals.eps)}</div>
        </div>
        <div>
          <div className="text-zinc-500 dark:text-zinc-500">52wk Range</div>
          <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
            {formatNumber(fundamentals["52_week_low"])} – {formatNumber(fundamentals["52_week_high"])}
          </div>
        </div>
      </div>
      {fundamentalsError && <ErrorNotice message={fundamentalsError} />}
    </div>
  );
}
