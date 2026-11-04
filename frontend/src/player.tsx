import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { apiUrl, type Track } from "./api";

export type Source = "vocals" | "original";

interface PlayerState {
  track: Track | null;
  source: Source;
  playing: boolean;
  time: number;
  duration: number;
  volume: number;
  muted: boolean;
  play: (track: Track, source?: Source) => void;
  toggle: () => void;
  seek: (t: number) => void;
  setVolume: (v: number) => void;
  toggleMute: () => void;
  setSource: (s: Source) => void;
}

const PlayerContext = createContext<PlayerState | null>(null);

export const usePlayer = () => {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error("usePlayer must be used inside PlayerProvider");
  return ctx;
};

const srcFor = (track: Track, source: Source) =>
  apiUrl(source === "vocals" ? track.audio.vocals_mp3 : track.audio.original);

function readVolume(): number {
  try {
    const v = parseFloat(localStorage.getItem("acapella:volume") ?? "");
    return Number.isFinite(v) ? v : 0.8;
  } catch {
    return 0.8;
  }
}

export function PlayerProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [track, setTrack] = useState<Track | null>(null);
  const [source, setSourceState] = useState<Source>("vocals");
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolumeState] = useState(readVolume);
  const [muted, setMuted] = useState(false);

  useEffect(() => {
    if (audio.current) audio.current.volume = muted ? 0 : volume;
    try { localStorage.setItem("acapella:volume", String(volume)); } catch { /* storage unavailable */ }
  }, [volume, muted]);

  const load = useCallback((t: Track, s: Source, startAt: number, autoplay: boolean) => {
    const el = audio.current;
    if (!el) return;
    el.src = srcFor(t, s);
    const start = () => {
      if (startAt > 0) el.currentTime = Math.min(startAt, el.duration || startAt);
      if (autoplay) el.play().catch(() => setPlaying(false));
    };
    el.addEventListener("loadedmetadata", start, { once: true });
    el.load();
  }, []);

  const play = useCallback((t: Track, s?: Source) => {
    const nextSource = s ?? source;
    if (track?.id === t.id && nextSource === source) {
      audio.current?.play();
      return;
    }
    setTrack(t);
    setSourceState(nextSource);
    setTime(0);
    setDuration(t.duration);
    load(t, nextSource, 0, true);
  }, [track, source, load]);

  const toggle = useCallback(() => {
    const el = audio.current;
    if (!el || !track) return;
    el.paused ? el.play() : el.pause();
  }, [track]);

  const seek = useCallback((t: number) => {
    if (audio.current) audio.current.currentTime = t;
    setTime(t);
  }, []);

  // Switching between original and vocals keeps position and play state, so you can A/B them.
  const setSource = useCallback((s: Source) => {
    if (s === source) return;
    setSourceState(s);
    if (track && audio.current) load(track, s, audio.current.currentTime, !audio.current.paused);
  }, [source, track, load]);

  // Space toggles playback unless the user is typing.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (e.code === "Space" && !["INPUT", "TEXTAREA", "BUTTON", "SELECT"].includes(tag)) {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  const value: PlayerState = {
    track, source, playing, time, duration, volume, muted,
    play, toggle, seek, setSource,
    setVolume: (v) => { setVolumeState(v); setMuted(false); },
    toggleMute: () => setMuted((m) => !m),
  };

  return (
    <PlayerContext.Provider value={value}>
      {children}
      <audio
        ref={audio}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onDurationChange={(e) => Number.isFinite(e.currentTarget.duration) && setDuration(e.currentTarget.duration)}
      />
    </PlayerContext.Provider>
  );
}
