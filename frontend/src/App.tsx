import { Route, Routes } from "react-router-dom";
import { BottomNav, Sidebar } from "./components/Nav";
import { PlayerBar } from "./components/PlayerBar";
import Home from "./pages/Home";
import LibraryPage from "./pages/Library";
import UploadPage from "./pages/Upload";

export default function App() {
  return (
    <div className="h-dvh flex flex-col bg-black">
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-w-0 md:my-2 md:mr-2 md:rounded-lg bg-surface bg-gradient-to-b from-[#1f3a2a] via-surface via-[260px] to-surface overflow-y-auto scrollbar-thin">
          <div className="px-4 py-5 sm:px-6 md:px-8 md:py-6">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/library" element={<LibraryPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="*" element={<Home />} />
            </Routes>
          </div>
        </main>
      </div>
      <PlayerBar />
      <BottomNav />
    </div>
  );
}
