import { NavLink } from "react-router-dom";
import { HomeIcon, LibraryIcon, UploadIcon, WaveIcon } from "./Icons";
import { useLibrary } from "../library";

const links = [
  { to: "/", label: "Home", Icon: HomeIcon },
  { to: "/library", label: "Library", Icon: LibraryIcon },
  { to: "/upload", label: "Upload", Icon: UploadIcon },
];

function ActiveBadge() {
  const { uploads } = useLibrary();
  const n = uploads.filter((u) => u.phase === "uploading" || u.phase === "queued" || u.phase === "processing").length;
  if (!n) return null;
  return (
    <span className="ml-auto min-w-5 h-5 px-1.5 rounded-full bg-accent text-black text-xs font-bold grid place-items-center"
      aria-label={`${n} processing`}>
      {n}
    </span>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-60 lg:w-64 shrink-0 flex-col gap-2 p-2">
      <div className="rounded-lg bg-card px-5 py-5 flex flex-col gap-1">
        <div className="flex items-center gap-2 mb-4 px-1">
          <WaveIcon className="w-7 h-7 text-accent" />
          <span className="text-xl font-extrabold tracking-tight">Acapella</span>
        </div>
        {links.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-4 rounded-md px-2 py-2.5 font-bold transition-colors ${
                isActive ? "text-white bg-white/5" : "text-muted hover:text-white"}`}>
            <Icon className="w-6 h-6" />
            {label}
            {to === "/upload" && <ActiveBadge />}
          </NavLink>
        ))}
      </div>
      <div className="rounded-lg bg-card p-5 flex-1 text-sm text-muted">
        <p className="font-bold text-white mb-1">Isolation strength</p>
        <p>Higher strength runs more models and silences the gaps between phrases. You lose a bit of vocal
          quality, but less of the band gets through.</p>
      </div>
    </aside>
  );
}

export function BottomNav() {
  return (
    <nav className="md:hidden flex justify-around bg-gradient-to-t from-black via-black/95 to-black/80 pb-[env(safe-area-inset-bottom)]">
      {links.map(({ to, label, Icon }) => (
        <NavLink key={to} to={to} end={to === "/"}
          className={({ isActive }) =>
            `flex flex-1 flex-col items-center gap-1 py-2 text-[11px] font-medium ${isActive ? "text-white" : "text-muted"}`}>
          <Icon className="w-6 h-6" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
