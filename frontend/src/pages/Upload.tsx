import { useRef, useState, type DragEvent } from "react";
import type { Strength } from "../api";
import { CoverArt } from "../components/CoverArt";
import { PlayIcon, UploadIcon } from "../components/Icons";
import { useLibrary, type UploadItem } from "../library";
import { usePlayer } from "../player";

const ACCEPT = [".mp3", ".wav", ".flac", ".m4a"];

const STRENGTHS: { id: Strength; label: string; detail: string; passes: string }[] = [
  { id: "low", label: "Low", detail: "One Mel-Roformer pass. Fastest, most natural vocal.", passes: "1 pass" },
  { id: "medium", label: "Medium", detail: "Two models; keeps only what both agree is vocal.", passes: "2 passes" },
  { id: "high", label: "High", detail: "Medium + a second pass on the vocals + gating that fully silences the gaps.", passes: "3 passes + gate" },
];

const isAudio = (f: File) => ACCEPT.some((ext) => f.name.toLowerCase().endsWith(ext));

export default function UploadPage() {
  const { upload, uploads } = useLibrary();
  const [strength, setStrength] = useState<Strength>("high");
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState<string[]>([]);
  const input = useRef<HTMLInputElement>(null);

  const handleFiles = (list: FileList | null) => {
    const files = Array.from(list ?? []);
    const ok = files.filter(isAudio);
    setRejected(files.filter((f) => !isAudio(f)).map((f) => f.name));
    if (ok.length) upload(ok, strength);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="flex flex-col gap-8 max-w-3xl">
      <section>
        <h1 className="text-2xl sm:text-3xl font-extrabold mb-1">Upload</h1>
        <p className="text-muted">MP3, WAV, FLAC or M4A. Processing runs in the background, so you can keep listening.</p>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-muted mb-3">Isolation strength</h2>
        <div role="radiogroup" aria-label="Isolation strength" className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
          {STRENGTHS.map((s) => (
            <button key={s.id} role="radio" aria-checked={strength === s.id} onClick={() => setStrength(s.id)}
              className={`text-left rounded-lg p-4 border-2 transition-colors
                ${strength === s.id ? "border-accent bg-accent/10" : "border-transparent bg-card hover:bg-card-hover"}`}>
              <span className="flex items-center justify-between">
                <span className="font-bold">{s.label}</span>
                <span className={`text-xs font-semibold ${strength === s.id ? "text-accent" : "text-muted"}`}>{s.passes}</span>
              </span>
              <span className="block text-sm text-muted mt-1">{s.detail}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => input.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
          role="button" tabIndex={0} aria-label="Choose audio files to upload"
          className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 sm:py-16 text-center cursor-pointer transition-colors
            ${dragging ? "border-accent bg-accent/10" : "border-white/20 bg-card hover:border-white/40"}`}>
          <span className={`grid place-items-center w-16 h-16 rounded-full ${dragging ? "bg-accent text-black" : "bg-elevated"}`}>
            <UploadIcon className="w-8 h-8" />
          </span>
          <p className="text-lg font-bold"><span className="hidden sm:inline">Drop songs here or </span><span className="text-accent sm:text-white">browse files</span></p>
          <p className="text-sm text-muted">Strength: <span className="capitalize text-white">{strength}</span></p>
          <input ref={input} type="file" accept={ACCEPT.join(",") + ",audio/*"} multiple hidden
            onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }} />
        </div>
        {rejected.length > 0 && (
          <p className="mt-3 text-sm text-red-300">Skipped unsupported file{rejected.length > 1 ? "s" : ""}: {rejected.join(", ")}</p>
        )}
      </section>

      {uploads.length > 0 && (
        <section>
          <h2 className="text-xl font-bold mb-3">Queue</h2>
          <UploadList items={uploads} />
        </section>
      )}
    </div>
  );
}

const PHASE_LABEL: Record<UploadItem["phase"], string> = {
  uploading: "Uploading", queued: "Queued", processing: "Processing", done: "Ready", failed: "Failed",
};

export function UploadList({ items }: { items: UploadItem[] }) {
  const { tracks, dismiss } = useLibrary();
  const player = usePlayer();

  return (
    <ul className="flex flex-col gap-2">
      {items.map((u) => {
        const track = u.trackId ? tracks.find((t) => t.id === u.trackId) : undefined;
        // Upload is the first 10% of the bar; server-side processing fills the rest.
        const pct = u.phase === "uploading" ? u.progress * 10 : u.phase === "done" ? 100 : 10 + u.progress * 90;
        return (
          <li key={u.key} className="flex items-center gap-3 rounded-lg bg-card p-3">
            <CoverArt seed={u.trackId ?? u.key} title={u.name} className="w-12 h-12 rounded shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate font-semibold text-sm">{u.name}</p>
                <span className={`text-xs font-bold shrink-0 ${u.phase === "failed" ? "text-red-400" : u.phase === "done" ? "text-accent" : "text-muted"}`}>
                  {PHASE_LABEL[u.phase]}
                </span>
              </div>
              <p className="truncate text-xs text-muted mb-2">
                <span className="capitalize">{u.strength}</span> · {u.phase === "failed" ? u.error : u.message}
              </p>
              {u.phase !== "failed" && (
                <div className="h-1 rounded-full bg-white/10 overflow-hidden" role="progressbar"
                  aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={`${u.name} progress`}>
                  <div className={`h-full rounded-full bg-accent transition-[width] duration-500 ${u.phase === "queued" ? "animate-pulse" : ""}`}
                    style={{ width: `${pct}%` }} />
                </div>
              )}
            </div>
            {track ? (
              <button onClick={() => player.play(track)} aria-label={`Play ${track.title}`}
                className="grid place-items-center w-10 h-10 rounded-full bg-accent text-black hover:scale-105 transition shrink-0">
                <PlayIcon className="w-5 h-5 translate-x-[1px]" />
              </button>
            ) : (u.phase === "failed" || u.phase === "done") && (
              <button onClick={() => dismiss(u.key)} className="text-xs font-bold text-muted hover:text-white px-2 shrink-0">Dismiss</button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
