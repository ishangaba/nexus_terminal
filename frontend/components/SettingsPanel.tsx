"use client";

import { useEffect, useState } from "react";
import { clearSetting, fetchSettings, saveSettings, SettingsKey, SettingsStatus } from "@/lib/api";

interface SettingsPanelProps {
  onClose: () => void;
}

const FIELD_ORDER: SettingsKey[] = ["alpha_vantage_api_key", "finnhub_api_key", "marketaux_api_key", "anthropic_api_key"];

const KEY_INFO: Record<SettingsKey, { pricing: string; free: boolean; url: string; blurb: string }> = {
  alpha_vantage_api_key: {
    pricing: "Free · 25 requests/day",
    free: true,
    url: "https://www.alphavantage.co/support/#api-key",
    blurb: "Powers fundamentals and the 30-day price chart.",
  },
  finnhub_api_key: {
    pricing: "Free · 60 requests/min",
    free: true,
    url: "https://finnhub.io/register",
    blurb: "Powers live quotes and the bulk of news headlines.",
  },
  marketaux_api_key: {
    pricing: "Free · 100 requests/day, 3 articles/request",
    free: true,
    url: "https://www.marketaux.com/pricing",
    blurb: "Adds broader news-source diversity (5,000+ outlets, e.g. Nasdaq, TechCrunch) alongside Finnhub. Optional — news still works without it.",
  },
  anthropic_api_key: {
    pricing: "Paid · pay-as-you-go",
    free: false,
    url: "https://console.anthropic.com",
    blurb: "Powers the AI brief, Ask box, and sentiment scoring — typically a few dollars/month at personal-use volume.",
  },
};

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [status, setStatus] = useState<SettingsStatus | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<SettingsKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedKey, setSavedKey] = useState<SettingsKey | null>(null);

  useEffect(() => {
    fetchSettings()
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(key: SettingsKey) {
    const value = drafts[key]?.trim();
    if (!value) return;
    setSavingKey(key);
    setError(null);
    setSavedKey(null);
    try {
      const next = await saveSettings({ [key]: value });
      setStatus(next);
      setDrafts((d) => ({ ...d, [key]: "" }));
      setRevealed((r) => ({ ...r, [key]: false }));
      setSavedKey(key);
      setTimeout(() => setSavedKey((k) => (k === key ? null : k)), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save key");
    } finally {
      setSavingKey(null);
    }
  }

  async function handleClear(key: SettingsKey) {
    setSavingKey(key);
    setError(null);
    try {
      const next = await clearSetting(key);
      setStatus(next);
      setDrafts((d) => ({ ...d, [key]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear key");
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-20 backdrop-blur-sm" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-md overflow-y-auto rounded-lg border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">API Keys</h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
          >
            ✕
          </button>
        </div>

        {loading && <p className="text-sm text-zinc-500 dark:text-zinc-400">Loading…</p>}

        {!loading && status && (
          <div className="flex flex-col gap-5">
            {FIELD_ORDER.map((key) => {
              const field = status[key];
              const info = KEY_INFO[key];
              const draft = drafts[key] ?? "";
              const isRevealed = revealed[key] ?? false;
              const isSaving = savingKey === key;
              return (
                <div key={key}>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">{field.label}</label>
                    <span
                      className={`text-xs ${field.configured ? "text-emerald-600 dark:text-emerald-400" : "text-zinc-400 dark:text-zinc-600"}`}
                    >
                      {field.configured ? `Set · ${field.masked}` : "Not set"}
                    </span>
                  </div>
                  <div className="mb-1.5 flex items-center justify-between gap-2 text-xs">
                    <span className={info.free ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}>
                      {info.pricing}
                    </span>
                    <a
                      href={info.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-violet-600 hover:underline dark:text-violet-400"
                    >
                      Get a key ↗
                    </a>
                  </div>
                  <p className="mb-1.5 text-xs text-zinc-400 dark:text-zinc-600">{info.blurb}</p>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={isRevealed ? "text" : "password"}
                        value={draft}
                        onChange={(e) => setDrafts((d) => ({ ...d, [key]: e.target.value }))}
                        placeholder={field.configured ? "Enter a new key to replace it" : "Paste your API key"}
                        autoComplete="off"
                        className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 pr-9 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600"
                      />
                      {draft && (
                        <button
                          type="button"
                          onClick={() => setRevealed((r) => ({ ...r, [key]: !isRevealed }))}
                          aria-label={isRevealed ? "Hide key" : "Show key"}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                        >
                          {isRevealed ? "hide" : "show"}
                        </button>
                      )}
                    </div>
                    <button
                      onClick={() => handleSave(key)}
                      disabled={!draft.trim() || isSaving}
                      className="rounded-md bg-gradient-to-r from-violet-600 to-violet-500 px-3 py-2 text-sm font-medium text-white shadow-sm hover:from-violet-500 hover:to-violet-400 disabled:opacity-50"
                    >
                      {isSaving ? "…" : savedKey === key ? "Saved" : "Save"}
                    </button>
                    {field.configured && (
                      <button
                        onClick={() => handleClear(key)}
                        disabled={isSaving}
                        className="rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-500 hover:border-rose-300 hover:text-rose-600 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-rose-800 dark:hover:text-rose-400"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {error && <p className="mt-4 text-sm text-rose-600 dark:text-rose-400">{error}</p>}

        <div className="mt-5 space-y-2 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-950/60 dark:text-zinc-400">
          <p>
            Keys are stored locally and never displayed again after saving — only a masked preview is shown.
          </p>
          <p>
            Alpha Vantage and Finnhub have free tiers with no card required. Anthropic is pay-as-you-go and will
            bill the account the key belongs to — you're responsible for usage on your own keys. Never share an
            API key or paste one into an untrusted site.
          </p>
        </div>
      </div>
    </div>
  );
}
