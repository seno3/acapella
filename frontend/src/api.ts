export type Strength = "low" | "medium" | "high";

export interface Track {
  id: string;
  title: string;
  duration: number;
  created_at: number;
  settings: { strength: Strength; device: string; models: string[]; steps: string[] };
  audio: { original: string; vocals_mp3: string };
}

export interface Job {
  id: string;
  title: string;
  strength: Strength;
  status: "queued" | "processing" | "done" | "failed";
  progress: number;
  message: string | null;
  error: string | null;
  track_id: string | null;
  created_at: number;
}

const BASE = import.meta.env.VITE_API_URL ?? "";

export const apiUrl = (path: string) => `${BASE}${path}`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  tracks: () => request<Track[]>("/api/tracks"),
  track: (id: string) => request<Track>(`/api/tracks/${id}`),
  deleteTrack: (id: string) => request<void>(`/api/tracks/${id}`, { method: "DELETE" }),
  job: (id: string) => request<Job>(`/api/jobs/${id}`),
  jobs: (active = false) => request<Job[]>(`/api/jobs${active ? "?active=true" : ""}`),
};

/** Upload with XHR so we can report upload progress (fetch can't). */
export function uploadFile(
  file: File,
  strength: Strength,
  onProgress: (fraction: number) => void,
): Promise<Job> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    form.append("strength", strength);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/api/upload"));
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      let body: any = null;
      try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as Job);
      else reject(new Error(body?.detail ?? `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Network error — is the backend running?"));
    xhr.send(form);
  });
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
