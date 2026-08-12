interface LogoProps {
  size?: number;
  className?: string;
}

export default function Logo({ size = 32, className = "" }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id="nexus-logo-gradient" x1="0" y1="32" x2="32" y2="0">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="url(#nexus-logo-gradient)" fillOpacity="0.12" />
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" stroke="url(#nexus-logo-gradient)" strokeOpacity="0.5" />
      <path
        d="M7 20L12 13L16.5 17L25 8"
        stroke="url(#nexus-logo-gradient)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M19.5 8H25V13.5" stroke="url(#nexus-logo-gradient)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="7" cy="20" r="1.6" fill="url(#nexus-logo-gradient)" />
      <circle cx="16.5" cy="17" r="1.6" fill="url(#nexus-logo-gradient)" />
    </svg>
  );
}
