import { Filing } from "@/lib/api";

interface FilingsProps {
  filings: Filing[];
}

const FORM_LABELS: Record<string, string> = {
  "10-K": "Annual report",
  "10-Q": "Quarterly report",
  "8-K": "Material event",
  "4": "Insider transaction",
};

export default function Filings({ filings }: FilingsProps) {
  if (!filings || filings.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900">
        No recent SEC filings found.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="mb-4 text-sm font-medium text-zinc-500">Recent SEC Filings</h3>
      <ul className="space-y-2">
        {filings.map((filing, i) => (
          <li key={i} className="flex items-center justify-between gap-3 text-sm">
            <a
              href={filing.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-900 hover:underline dark:text-zinc-100"
            >
              <span className="font-medium">{filing.form}</span>
              <span className="text-zinc-500"> — {FORM_LABELS[filing.form] ?? "Filing"}</span>
            </a>
            <span className="shrink-0 text-xs text-zinc-500">{filing.filed_date}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
