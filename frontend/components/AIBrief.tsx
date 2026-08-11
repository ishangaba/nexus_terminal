interface AIBriefProps {
  brief: string;
}

export default function AIBrief({ brief }: AIBriefProps) {
  if (!brief) return null;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-6 dark:border-blue-900 dark:bg-blue-950/40">
      <h3 className="mb-2 text-sm font-medium text-blue-700 dark:text-blue-400">AI Analyst Brief</h3>
      <p className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">{brief}</p>
    </div>
  );
}
