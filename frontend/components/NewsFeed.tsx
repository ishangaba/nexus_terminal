import { NewsItem } from "@/lib/api";
import { decodeHtmlEntities } from "@/lib/text";

interface NewsFeedProps {
  news: NewsItem[];
}

function sentimentBadge(score: number | null) {
  if (score === null) return { label: "—", className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400" };
  if (score > 0.15) return { label: `+${score.toFixed(2)}`, className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" };
  if (score < -0.15) return { label: score.toFixed(2), className: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400" };
  return { label: score.toFixed(2), className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400" };
}

export default function NewsFeed({ news }: NewsFeedProps) {
  if (!news || news.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/60">
        No recent news.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <h3 className="mb-4 text-sm font-medium text-zinc-500 dark:text-zinc-400">Recent News</h3>
      <ul className="space-y-3">
        {news.map((item, i) => {
          const badge = sentimentBadge(item.sentiment_score);
          return (
            <li key={i} className="flex items-start justify-between gap-3">
              <div>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-zinc-900 hover:text-cyan-600 hover:underline dark:text-zinc-100 dark:hover:text-cyan-400"
                >
                  {decodeHtmlEntities(item.headline)}
                </a>
                <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-500">
                  {decodeHtmlEntities(item.source)}
                  {item.published_at ? ` · ${new Date(item.published_at).toLocaleString()}` : ""}
                </div>
              </div>
              <span className={`shrink-0 rounded px-2 py-0.5 font-mono text-xs font-medium ${badge.className}`}>
                {badge.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
