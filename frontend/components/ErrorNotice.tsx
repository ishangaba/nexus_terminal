interface ErrorNoticeProps {
  message: string;
}

export default function ErrorNotice({ message }: ErrorNoticeProps) {
  return (
    <div className="mt-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-400">
      ⚠ {message}
    </div>
  );
}
