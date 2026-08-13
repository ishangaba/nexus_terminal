// Decorative only — illustrative figures, not live data. Real prices load once a symbol is
// searched; this just sets the "terminal" tone before that happens.
const SAMPLE_QUOTES: { symbol: string; change: number }[] = [
  { symbol: "AAPL", change: 0.93 },
  { symbol: "NVDA", change: 2.14 },
  { symbol: "TSLA", change: -1.42 },
  { symbol: "MSFT", change: 0.58 },
  { symbol: "AMZN", change: 1.07 },
  { symbol: "META", change: -0.35 },
  { symbol: "GOOGL", change: 0.71 },
  { symbol: "AMD", change: -2.03 },
  { symbol: "JPM", change: 0.44 },
  { symbol: "NFLX", change: 1.85 },
];

function TickerItem({ symbol, change }: { symbol: string; change: number }) {
  const up = change >= 0;
  return (
    <span className="mx-4 inline-flex items-center gap-1.5 font-mono text-xs">
      <span className="text-zinc-500 dark:text-zinc-500">{symbol}</span>
      <span className={up ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}>
        {up ? "▲" : "▼"} {Math.abs(change).toFixed(2)}%
      </span>
    </span>
  );
}

export default function TickerTape() {
  // Rendered twice back-to-back; the CSS animation scrolls exactly -50% (one copy's width),
  // so the seam is invisible and the loop reads as continuous.
  return (
    <div
      aria-hidden
      className="w-full overflow-hidden border-y border-zinc-200/60 bg-zinc-50/50 py-2 dark:border-zinc-800/60 dark:bg-zinc-950/30"
    >
      <div className="ticker-track flex w-max">
        {[0, 1].map((copy) => (
          <div key={copy} className="flex shrink-0">
            {SAMPLE_QUOTES.map((q, i) => (
              <TickerItem key={`${copy}-${i}`} symbol={q.symbol} change={q.change} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
