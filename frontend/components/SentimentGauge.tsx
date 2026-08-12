import { NewsItem } from "@/lib/api";

interface SentimentGaugeProps {
  news: NewsItem[];
}

function labelFor(score: number): { label: string; color: string } {
  if (score > 0.35) return { label: "Bullish", color: "text-emerald-600 dark:text-emerald-400" };
  if (score > 0.1) return { label: "Slightly Bullish", color: "text-emerald-600 dark:text-emerald-400" };
  if (score < -0.35) return { label: "Bearish", color: "text-rose-600 dark:text-rose-400" };
  if (score < -0.1) return { label: "Slightly Bearish", color: "text-rose-600 dark:text-rose-400" };
  return { label: "Neutral", color: "text-zinc-500 dark:text-zinc-400" };
}

export default function SentimentGauge({ news }: SentimentGaugeProps) {
  const scored = news.filter((n): n is NewsItem & { sentiment_score: number } => n.sentiment_score !== null);

  if (scored.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60">
        <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">News Sentiment</h3>
        <p className="text-sm text-zinc-500 dark:text-zinc-500">Not enough data yet.</p>
      </div>
    );
  }

  const avg = scored.reduce((sum, n) => sum + n.sentiment_score, 0) / scored.length;
  const { label, color } = labelFor(avg);
  // Map [-1, 1] to [0%, 100%]
  const positionPct = ((avg + 1) / 2) * 100;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <h3 className="mb-3 text-sm font-medium text-zinc-500 dark:text-zinc-400">News Sentiment</h3>
      <div className="flex items-baseline justify-between">
        <span className={`text-lg font-semibold ${color}`}>{label}</span>
        <span className="font-mono text-sm text-zinc-500 dark:text-zinc-500">
          {avg >= 0 ? "+" : ""}
          {avg.toFixed(2)} avg · {scored.length} article{scored.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="relative mt-3 h-2 w-full rounded-full bg-gradient-to-r from-rose-400 via-zinc-300 to-emerald-400 dark:from-rose-600 dark:via-zinc-700 dark:to-emerald-600">
        <div
          className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-zinc-900 shadow dark:border-zinc-950 dark:bg-white"
          style={{ left: `${positionPct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-zinc-400 dark:text-zinc-600">
        <span>Bearish</span>
        <span>Neutral</span>
        <span>Bullish</span>
      </div>
    </div>
  );
}
