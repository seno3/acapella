import { useEffect, useRef, useState } from "react";
import { apiUrl, formatTime, type Track } from "../api";
import { useLibrary } from "../library";
import { usePlayer } from "../player";
import { CoverArt } from "./CoverArt";
import { MoreIcon, PauseIcon, PlayIcon } from "./Icons";

export function TrackCard({ track }: { track: Track }) {
  const player = usePlayer();
  const { remove } = useLibrary();
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const isCurrent = player.track?.id === track.id;
  const isPlaying = isCurrent && player.playing;

  useEffect(() => {
    if (!menu) return;
    const close = (e: MouseEvent) => !menuRef.current?.contains(e.target as Node) && setMenu(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menu]);

  const onPlay = () => (isCurrent ? player.toggle() : player.play(track));

  return (
    <div className="group relative rounded-lg bg-card p-2.5 sm:p-3 hover:bg-card-hover transition-colors">
      <button onClick={onPlay} className="block w-full text-left" aria-label={`${isPlaying ? "Pause" : "Play"} ${track.title}`}>
        <div className="relative mb-3">
          <CoverArt seed={track.id} title={track.title} className="aspect-square w-full rounded-md shadow-lg shadow-black/40" />
          <span className={`absolute right-2 bottom-2 grid place-items-center w-11 h-11 rounded-full bg-accent text-black
            shadow-xl shadow-black/50 transition-all duration-200
            ${isPlaying ? "opacity-100 translate-y-0" : "opacity-100 sm:opacity-0 sm:translate-y-2 group-hover:opacity-100 group-hover:translate-y-0"}`}>
            {isPlaying ? <PauseIcon className="w-5 h-5" /> : <PlayIcon className="w-5 h-5 translate-x-[1px]" />}
          </span>
        </div>
        <p className={`truncate font-bold text-sm sm:text-base ${isCurrent ? "text-accent" : ""}`}>{track.title}</p>
        <p className="truncate text-xs sm:text-sm text-muted capitalize mt-0.5">
          {formatTime(track.duration)} · {track.settings.strength}
        </p>
      </button>

      <div ref={menuRef} className="absolute right-2 top-2">
        <button onClick={() => setMenu((m) => !m)} aria-label="Track options" aria-expanded={menu}
          className="grid place-items-center w-8 h-8 rounded-full bg-black/60 text-white opacity-100 sm:opacity-0 group-hover:opacity-100 focus:opacity-100">
          <MoreIcon className="w-4 h-4" />
        </button>
        {menu && (
          <div role="menu" className="absolute right-0 mt-1 w-48 rounded-md bg-elevated p-1 shadow-2xl shadow-black z-20 text-sm">
            <a role="menuitem" className="block rounded px-3 py-2 hover:bg-white/10" href={apiUrl(`${track.audio.vocals_mp3}?download=true`)}>Download vocals</a>
            <button role="menuitem" className="block w-full text-left rounded px-3 py-2 hover:bg-white/10"
              onClick={() => { setMenu(false); player.play(track, "original"); }}>Play original</button>
            <button role="menuitem" className="block w-full text-left rounded px-3 py-2 text-red-400 hover:bg-white/10"
              onClick={() => { setMenu(false); if (confirm(`Delete "${track.title}"?`)) remove(track.id); }}>Delete</button>
          </div>
        )}
      </div>
    </div>
  );
}

export function TrackGrid({ tracks }: { tracks: Track[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3 sm:gap-4">
      {tracks.map((t) => <TrackCard key={t.id} track={t} />)}
    </div>
  );
}
