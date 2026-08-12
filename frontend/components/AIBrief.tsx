import { decodeHtmlEntities } from "@/lib/text";

interface AIBriefProps {
  brief: string | null;
  loading: boolean;
  error: string | null;
}

export default function AIBrief({ brief, loading, error }: AIBriefProps) {
  return (
    <div className="rounded-lg border border-violet-200 bg-violet-50 p-6 dark:border-violet-900/60 dark:bg-violet-950/20 dark:shadow-[0_0_24px_-8px_rgba(167,139,250,0.25)]">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-violet-700 dark:text-violet-400">
        <span aria-hidden>✦</span> AI Analyst Brief
        {loading && (
          <span className="flex items-center gap-1.5 text-xs font-normal text-violet-500 dark:text-violet-500">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-500" />
            Generating…
          </span>
        )}
      </h3>

      {loading && (
        <div className="space-y-2">
          <div className="h-3.5 w-full animate-pulse rounded bg-violet-200/60 dark:bg-violet-900/40" />
          <div className="h-3.5 w-11/12 animate-pulse rounded bg-violet-200/60 dark:bg-violet-900/40" />
          <div className="h-3.5 w-4/5 animate-pulse rounded bg-violet-200/60 dark:bg-violet-900/40" />
        </div>
      )}

      {!loading && error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}
      {!loading && !error && brief && (
        <p className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">{decodeHtmlEntities(brief)}</p>
      )}
    </div>
  );
}
