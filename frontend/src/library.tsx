import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, uploadFile, type Job, type Strength, type Track } from "./api";

/** A job as the UI sees it: includes the browser-side upload phase before the server knows about it. */
export interface UploadItem {
  key: string;
  name: string;
  strength: Strength;
  phase: "uploading" | "queued" | "processing" | "done" | "failed";
  progress: number; // 0..1 for the current phase
  message: string;
  error?: string;
  jobId?: string;
  trackId?: string;
}

interface LibraryState {
  tracks: Track[];
  loading: boolean;
  error: string | null;
  uploads: UploadItem[];
  refresh: () => Promise<void>;
  upload: (files: File[], strength: Strength) => void;
  remove: (id: string) => Promise<void>;
  dismiss: (key: string) => void;
}

const LibraryContext = createContext<LibraryState | null>(null);

export const useLibrary = () => {
  const ctx = useContext(LibraryContext);
  if (!ctx) throw new Error("useLibrary must be used inside LibraryProvider");
  return ctx;
};

const POLL_MS = 1000;

function fromJob(job: Job): UploadItem {
  return {
    key: job.id,
    jobId: job.id,
    name: job.title,
    strength: job.strength,
    phase: job.status,
    progress: job.progress,
    message: job.message ?? "",
    error: job.error ?? undefined,
    trackId: job.track_id ?? undefined,
  };
}

export function LibraryProvider({ children }: { children: ReactNode }) {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const uploadsRef = useRef(uploads);
  uploadsRef.current = uploads;

  const patch = (key: string, p: Partial<UploadItem>) =>
    setUploads((list) => list.map((u) => (u.key === key ? { ...u, ...p } : u)));

  const refresh = useCallback(async () => {
    try {
      setTracks(await api.tracks());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load, plus pick up jobs that were already running (e.g. after a page reload).
  useEffect(() => {
    refresh();
    api.jobs(true).then((jobs) => setUploads((list) => [
      ...list,
      ...jobs.filter((j) => !list.some((u) => u.jobId === j.id)).map(fromJob),
    ])).catch(() => {});
  }, [refresh]);

  // Poll every active job until it finishes.
  useEffect(() => {
    const timer = setInterval(async () => {
      const active = uploadsRef.current.filter((u) => u.jobId && (u.phase === "queued" || u.phase === "processing"));
      if (!active.length) return;
      let finished = false;
      await Promise.all(active.map(async (u) => {
        try {
          const job = await api.job(u.jobId!);
          patch(u.key, { ...fromJob(job), key: u.key, name: u.name });
          if (job.status === "done") finished = true;
        } catch { /* transient; try again next tick */ }
      }));
      if (finished) refresh();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const upload = useCallback((files: File[], strength: Strength) => {
    for (const file of files) {
      const key = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setUploads((list) => [{
        key, name: file.name.replace(/\.[^.]+$/, ""), strength,
        phase: "uploading", progress: 0, message: "Uploading",
      }, ...list]);
      uploadFile(file, strength, (f) => patch(key, { progress: f }))
        .then((job) => patch(key, { ...fromJob(job), key }))
        .catch((e: Error) => patch(key, { phase: "failed", error: e.message, message: "Upload failed" }));
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    await api.deleteTrack(id);
    setTracks((t) => t.filter((x) => x.id !== id));
  }, []);

  const dismiss = (key: string) => setUploads((list) => list.filter((u) => u.key !== key));

  return (
    <LibraryContext.Provider value={{ tracks, loading, error, uploads, refresh, upload, remove, dismiss }}>
      {children}
    </LibraryContext.Provider>
  );
}
