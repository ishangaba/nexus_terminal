"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState<boolean | null>(null);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    window.dispatchEvent(new Event("theme-change"));
    localStorage.setItem("nexus-theme", next ? "dark" : "light");
  }

  // Avoid rendering with a guessed state before we've read the real one from the DOM.
  if (isDark === null) {
    return <div className="h-7 w-14 rounded-full bg-zinc-200 dark:bg-zinc-800" />;
  }

  return (
    <button
      onClick={toggle}
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={`relative inline-flex h-7 w-14 items-center rounded-full border transition-colors ${
        isDark ? "border-violet-800 bg-violet-950" : "border-zinc-300 bg-zinc-100"
      }`}
    >
      <span
        className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs shadow transition-transform ${
          isDark ? "translate-x-8 bg-zinc-900 text-cyan-300" : "translate-x-1 bg-white text-amber-500"
        }`}
      >
        {isDark ? "☾" : "☀"}
      </span>
    </button>
  );
}
