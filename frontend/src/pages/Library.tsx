import { Link } from "react-router-dom";
import { TrackGrid } from "../components/TrackCard";
import { useLibrary } from "../library";

export function EmptyLibrary() {
  return (
    <div className="rounded-lg bg-card p-8 text-center">
      <p className="text-lg font-bold">No tracks yet</p>
      <p className="text-muted mt-1 mb-5">Upload a song and Acapella will pull out the vocals.</p>
      <Link to="/upload" className="inline-block rounded-full bg-accent hover:bg-accent-hover text-black font-bold px-6 py-3 hover:scale-[1.03] transition">
        Upload a song
      </Link>
    </div>
  );
}

export default function LibraryPage() {
  const { tracks, loading, error } = useLibrary();
  return (
    <section>
      <h1 className="text-2xl sm:text-3xl font-extrabold mb-1">Your Library</h1>
      <p className="text-muted mb-6">{tracks.length} {tracks.length === 1 ? "track" : "tracks"}</p>
      {error && <p className="mb-4 rounded-md bg-red-500/10 text-red-300 px-4 py-3 text-sm">Couldn't load library: {error}</p>}
      {loading ? <GridSkeleton /> : tracks.length ? <TrackGrid tracks={tracks} /> : <EmptyLibrary />}
    </section>
  );
}

export function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="rounded-lg bg-card p-3 animate-pulse">
          <div className="aspect-square rounded-md bg-elevated mb-3" />
          <div className="h-4 w-3/4 rounded bg-elevated mb-2" />
          <div className="h-3 w-1/2 rounded bg-elevated" />
        </div>
      ))}
    </div>
  );
}
