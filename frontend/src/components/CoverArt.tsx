/** Deterministic gradient cover art generated from the track id + title. */
function hash(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function coverStyle(seed: string) {
  const h = hash(seed);
  const hue1 = h % 360;
  const hue2 = (hue1 + 40 + ((h >> 9) % 120)) % 360;
  const angle = (h >> 4) % 360;
  const x = 20 + ((h >> 12) % 60);
  const y = 20 + ((h >> 18) % 60);
  return {
    background: `radial-gradient(circle at ${x}% ${y}%, hsl(${hue2} 85% 65% / .9), transparent 55%),
      linear-gradient(${angle}deg, hsl(${hue1} 70% 45%), hsl(${hue2} 60% 22%))`,
  };
}

export function CoverArt({ seed, title, className = "" }: { seed: string; title: string; className?: string }) {
  const bars = Array.from({ length: 5 }, (_, i) => 30 + ((hash(seed + i) % 70)));
  return (
    <div className={`@container relative overflow-hidden ${className}`} style={coverStyle(seed)} aria-hidden>
      <div className="absolute inset-x-[14%] bottom-[14%] flex items-end gap-[6%] h-[34%] opacity-80">
        {bars.map((b, i) => (
          <span key={i} className="flex-1 rounded-full bg-white/85 mix-blend-overlay" style={{ height: `${b}%` }} />
        ))}
      </div>
      <span className="absolute left-[10%] top-[8%] text-[clamp(1rem,22cqw,3.5rem)] font-black text-white/90 leading-none drop-shadow">
        {title.trim().charAt(0).toUpperCase() || "♪"}
      </span>
    </div>
  );
}
