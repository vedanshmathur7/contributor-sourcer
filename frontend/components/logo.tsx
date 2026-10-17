export function Logo({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="hsl(252 95% 72%)" />
          <stop offset="1" stopColor="hsl(222 90% 60%)" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="url(#lg)" />
      <circle cx="11" cy="11" r="3" fill="white" />
      <circle cx="11" cy="21" r="3" fill="white" fillOpacity=".55" />
      <circle cx="21" cy="16" r="3" fill="white" />
      <path d="M11 14v4M13.6 12.4l4.8 2.4" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
