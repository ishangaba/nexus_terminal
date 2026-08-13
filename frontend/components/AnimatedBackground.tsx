// Purely decorative, absolutely-positioned behind hero content. clip-path/overflow-hidden on
// the parent keeps the blurred orbs from expanding page scroll bounds. Static in light mode
// (subtle enough there's little to animate); dark mode gets the full drifting-orb treatment to
// match the ambient radial-gradient background already set on <body> in globals.css.
export default function AnimatedBackground() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="orb-1 absolute -left-24 -top-24 h-72 w-72 rounded-full bg-cyan-400/20 blur-3xl dark:bg-cyan-500/25" />
      <div className="orb-2 absolute -right-16 top-10 h-64 w-64 rounded-full bg-violet-400/20 blur-3xl dark:bg-violet-500/25" />
      <div className="orb-3 absolute bottom-0 left-1/3 h-56 w-56 rounded-full bg-emerald-400/10 blur-3xl dark:bg-emerald-500/15" />
    </div>
  );
}
