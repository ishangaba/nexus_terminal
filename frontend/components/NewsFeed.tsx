import { NewsItem } from "@/lib/api";

interface NewsFeedProps {
  news: NewsItem[];
}

function sentimentBadge(score: number | null) {
  if (score === null) return { label: "—", className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400" };
  if (score > 0.15) return { label: `+${score.toFixed(2)}`, className: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400" };
  if (score < -0.15) return { label: score.toFixed(2), className: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400" };
  return { label: score.toFixed(2), className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400" };
}

export default function NewsFeed({ news }: NewsFeedProps) {
  if (!news || news.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900">
        No recent news.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="mb-4 text-sm font-medium text-zinc-500">Recent News</h3>
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
                  className="text-sm font-medium text-zinc-900 hover:underline dark:text-zinc-100"
                >
                  {item.headline}
                </a>
                <div className="mt-0.5 text-xs text-zinc-500">
                  {item.source}
                  {item.published_at ? ` · ${new Date(item.published_at).toLocaleString()}` : ""}
                </div>
              </div>
              <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${badge.className}`}>
                {badge.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
