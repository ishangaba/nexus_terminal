"use client";

import { useEffect, useState } from "react";

function getMarketStatus(): { open: boolean; label: string } {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
  }).formatToParts(new Date());

  const weekday = parts.find((p) => p.type === "weekday")?.value ?? "";
  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? 0);
  const minutesSinceMidnight = hour * 60 + minute;

  const isWeekday = !["Sat", "Sun"].includes(weekday);
  const isRegularHours = minutesSinceMidnight >= 9 * 60 + 30 && minutesSinceMidnight < 16 * 60;

  const open = isWeekday && isRegularHours;
  return { open, label: open ? "Market Open" : "Market Closed" };
}

export default function MarketStatus() {
  const [status, setStatus] = useState<{ open: boolean; label: string } | null>(null);

  useEffect(() => {
    setStatus(getMarketStatus());
    const interval = setInterval(() => setStatus(getMarketStatus()), 60_000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
      <span className={`h-1.5 w-1.5 rounded-full ${status.open ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.7)]" : "bg-zinc-400"}`} />
      {status.label}
    </span>
  );
}
