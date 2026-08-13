"use client";

import { motion, type Variants } from "motion/react";
import AnimatedBackground from "@/components/AnimatedBackground";
import TickerTape from "@/components/TickerTape";
import Logo from "@/components/Logo";

interface HeroProps {
  onQuickStart: (symbol: string) => void;
}

const QUICK_START_TICKERS = ["AAPL", "NVDA", "TSLA", "MSFT"];

const STEPS = [
  {
    icon: "🔍",
    title: "Search any ticker",
    body: "Live price, 30-day range chart, and fundamentals — pulled in real time.",
  },
  {
    icon: "✦",
    title: "Read the AI brief",
    body: "A grounded analyst summary, written only from the data on screen — never invented.",
  },
  {
    icon: "💬",
    title: "Ask anything",
    body: "Follow-up questions answered from the same verified price, news, and filings.",
  },
  {
    icon: "★",
    title: "Build your watchlist",
    body: "Pin the tickers you care about and track them at a glance.",
  },
];

// Orchestration pattern: children declare `variants` only (no initial/animate of their own) and
// inherit the "hidden"/"visible" state from whichever ancestor sets `animate="visible"` — this
// is what makes the outer container and the inner step-card grid stagger independently while
// still firing in one coherent sequence on mount.
const container: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.05 } },
};

const grid: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.35 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function Hero({ onQuickStart }: HeroProps) {
  return (
    <div className="relative flex flex-col items-center gap-8 overflow-hidden rounded-lg py-6 text-center sm:py-10">
      <AnimatedBackground />

      <motion.div
        initial="hidden"
        animate="visible"
        variants={container}
        className="flex flex-col items-center gap-10"
      >
        <div className="flex flex-col items-center gap-4">
          <motion.div variants={item}>
            <Logo size={56} />
          </motion.div>
          <motion.div variants={item}>
            <h2 className="text-3xl font-semibold text-zinc-900 dark:text-zinc-50 sm:text-4xl">
              Market intelligence,{" "}
              <span className="shimmer-text bg-gradient-to-r from-cyan-500 via-violet-500 to-cyan-500 bg-clip-text text-transparent dark:from-cyan-400 dark:via-violet-400 dark:to-cyan-400">
                grounded in real data
              </span>
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm text-zinc-500 dark:text-zinc-400 sm:text-base">
              Price, sentiment-scored news, SEC filings, and an AI analyst brief — synthesized in
              seconds for any ticker. Built for research, not speculation: every answer is grounded
              in the data on screen, never hallucinated.
            </p>
          </motion.div>

          <motion.div variants={item} className="flex flex-wrap items-center justify-center gap-2 pt-2">
            <span className="text-xs text-zinc-400 dark:text-zinc-600">Try it now:</span>
            {QUICK_START_TICKERS.map((symbol) => (
              <button
                key={symbol}
                onClick={() => onQuickStart(symbol)}
                className="rounded-full border border-zinc-300 px-3 py-1 text-xs font-medium text-zinc-700 transition-colors hover:border-cyan-400 hover:text-cyan-600 dark:border-zinc-700 dark:text-zinc-300 dark:hover:border-cyan-500 dark:hover:text-cyan-400"
              >
                {symbol}
              </button>
            ))}
          </motion.div>
        </div>

        <motion.div variants={item} className="w-full max-w-2xl">
          <TickerTape />
        </motion.div>

        <motion.div
          variants={grid}
          className="grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              variants={item}
              className="relative rounded-lg border border-zinc-200 bg-white p-4 text-left dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur"
            >
              <span className="absolute right-3 top-3 font-mono text-xs text-zinc-300 dark:text-zinc-700">
                {i + 1}
              </span>
              <span className="text-xl">{step.icon}</span>
              <h3 className="mt-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{step.title}</h3>
              <p className="mt-1 text-xs leading-relaxed text-zinc-500 dark:text-zinc-500">{step.body}</p>
            </motion.div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
