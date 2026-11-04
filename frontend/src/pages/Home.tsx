import { Link } from "react-router-dom";
import { formatTime } from "../api";
import { CoverArt } from "../components/CoverArt";
import { PlayIcon } from "../components/Icons";
import { TrackGrid } from "../components/TrackCard";
import { useLibrary } from "../library";
import { usePlayer } from "../player";
import { EmptyLibrary, GridSkeleton } from "./Library";
import { UploadList } from "./Upload";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function Home() {
  const { tracks, loading, uploads } = useLibrary();
  const player = usePlayer();
  const recent = tracks.slice(0, 6);
  const active = uploads.filter((u) => u.phase !== "done");

  return (
    <div className="flex flex-col gap-8">
      <section>
        <h1 className="text-2xl sm:text-3xl font-extrabold mb-4">{greeting()}</h1>
        {recent.length > 0 && (
          <div className="grid grid-cols-1 min-[420px]:grid-cols-2 xl:grid-cols-3 gap-2 sm:gap-3">
            {recent.map((t) => (
              <button key={t.id} onClick={() => player.play(t)}
                className="group flex items-center gap-3 rounded-md bg-white/[0.07] hover:bg-white/[0.14] transition-colors overflow-hidden text-left pr-3">
                <CoverArt seed={t.id} title={t.title} className="w-14 h-14 sm:w-16 sm:h-16 shrink-0" />
                <span className="flex-1 min-w-0">
                  <span className="block truncate font-bold text-sm">{t.title}</span>
                  <span className="block text-xs text-muted">{formatTime(t.duration)}</span>
                </span>
                <span className="hidden sm:grid place-items-center w-9 h-9 rounded-full bg-accent text-black opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <PlayIcon className="w-4 h-4 translate-x-[1px]" />
                </span>
              </button>
            ))}
          </div>
        )}
      </section>

      {active.length > 0 && (
        <section>
          <div className="flex items-baseline justify-between mb-3">
            <h2 className="text-xl font-bold">Processing</h2>
            <Link to="/upload" className="text-sm font-bold text-muted hover:text-white">Show all</Link>
          </div>
          <UploadList items={active.slice(0, 3)} />
        </section>
      )}

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-xl font-bold">Recently extracted</h2>
          {tracks.length > 0 && <Link to="/library" className="text-sm font-bold text-muted hover:text-white">Show all</Link>}
        </div>
        {loading ? <GridSkeleton /> : tracks.length ? <TrackGrid tracks={tracks.slice(0, 10)} /> : <EmptyLibrary />}
      </section>
    </div>
  );
}
