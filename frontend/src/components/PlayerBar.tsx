import { formatTime } from "../api";
import { usePlayer, type Source } from "../player";
import { CoverArt } from "./CoverArt";
import { MicIcon, PauseIcon, PlayIcon, VolumeIcon, WaveIcon } from "./Icons";

function Slider({ value, max, onChange, label, className = "" }: {
  value: number; max: number; onChange: (v: number) => void; label: string; className?: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <input type="range" className={`slider w-full ${className}`} aria-label={label}
      min={0} max={max || 1} step="any" value={Math.min(value, max || 1)}
      style={{ ["--pct" as string]: `${pct}%` }}
      onChange={(e) => onChange(parseFloat(e.target.value))} />
  );
}

export function SourceToggle({ compact = false }: { compact?: boolean }) {
  const { source, setSource, track } = usePlayer();
  const options: { id: Source; label: string; Icon: typeof MicIcon }[] = [
    { id: "original", label: "Original", Icon: WaveIcon },
    { id: "vocals", label: "Vocals", Icon: MicIcon },
  ];
  return (
    <div role="radiogroup" aria-label="Audio source"
      className="inline-flex rounded-full bg-elevated p-0.5 text-xs font-bold shrink-0">
      {options.map(({ id, label, Icon }) => (
        <button key={id} role="radio" aria-checked={source === id} disabled={!track}
          onClick={() => setSource(id)}
          className={`flex items-center gap-1 rounded-full transition-colors disabled:opacity-50
            ${compact ? "px-2 py-1.5" : "px-3 py-1.5"}
            ${source === id ? "bg-accent text-black" : "text-muted hover:text-white"}`}>
          <Icon className="w-4 h-4" />
          <span className={compact ? "sr-only" : ""}>{label}</span>
        </button>
      ))}
    </div>
  );
}

export function PlayerBar() {
  const p = usePlayer();
  const { track, playing, time, duration, volume, muted } = p;
  const level = muted ? 0 : volume;

  const PlayButton = ({ className = "" }) => (
    <button onClick={p.toggle} disabled={!track} aria-label={playing ? "Pause" : "Play"}
      className={`grid place-items-center rounded-full bg-white text-black hover:scale-105 active:scale-95
        transition-transform disabled:opacity-40 disabled:hover:scale-100 ${className}`}>
      {playing ? <PauseIcon className="w-1/2 h-1/2" /> : <PlayIcon className="w-1/2 h-1/2 translate-x-[1px]" />}
    </button>
  );

  return (
    <footer className="bg-black md:px-4 md:py-3">
      {/* Mobile: compact card with thin progress line */}
      <div className="md:hidden mx-2 mb-1 rounded-md bg-elevated overflow-hidden">
        <div className="flex items-center gap-3 p-2">
          {track ? <CoverArt seed={track.id} title={track.title} className="w-10 h-10 rounded shrink-0" />
            : <div className="w-10 h-10 rounded bg-card shrink-0" />}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">{track?.title ?? "Nothing playing"}</p>
            <p className="text-xs text-muted">{track ? `${formatTime(time)} / ${formatTime(duration)}` : "Pick a track"}</p>
          </div>
          <SourceToggle compact />
          <PlayButton className="w-10 h-10 shrink-0" />
        </div>
        <div className="px-2 pb-2">
          <Slider label="Seek" value={time} max={duration} onChange={p.seek} />
        </div>
      </div>

      {/* Desktop: three-column bar */}
      <div className="hidden md:grid grid-cols-[1fr_minmax(0,2fr)_1fr] items-center gap-4">
        <div className="flex items-center gap-3 min-w-0">
          {track ? (
            <>
              <CoverArt seed={track.id} title={track.title} className="w-14 h-14 rounded shrink-0" />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{track.title}</p>
                <p className="truncate text-xs text-muted capitalize">
                  {p.source === "vocals" ? `Vocals · ${track.settings.strength} strength` : "Original mix"}
                </p>
              </div>
            </>
          ) : <p className="text-sm text-muted">Nothing playing</p>}
        </div>

        <div className="flex flex-col items-center gap-1.5">
          <PlayButton className="w-9 h-9" />
          <div className="flex w-full max-w-xl items-center gap-2 text-xs text-muted tabular-nums">
            <span className="w-10 text-right">{formatTime(time)}</span>
            <Slider label="Seek" value={time} max={duration} onChange={p.seek} />
            <span className="w-10">{formatTime(duration)}</span>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <SourceToggle />
          <button onClick={p.toggleMute} aria-label={muted ? "Unmute" : "Mute"} className="text-muted hover:text-white">
            <VolumeIcon level={level === 0 ? 0 : level} className="w-5 h-5" />
          </button>
          <Slider label="Volume" value={level} max={1} onChange={p.setVolume} className="max-w-28" />
        </div>
      </div>
    </footer>
  );
}
