# Acapella

Upload a song and get the vocals back. Acapella runs vocal separation models in a background queue, keeps a
library of processed tracks, and has a player that switches between the original mix and the extracted vocals
without losing your place.

```
acapella/
├── backend/    FastAPI + audio-separator + SQLite
└── frontend/   React + Vite + Tailwind
```

## Requirements

- **Python 3.10–3.12**
- **Node.js 18+**
- **ffmpeg** on your `PATH`. `audio-separator` won't start without it.
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install ffmpeg`
- About 2 GB of free disk for models. They download on first use into `backend/data/models/`.

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

**NVIDIA GPU:** install the GPU build instead, so onnxruntime and torch use CUDA:

```bash
pip install "audio-separator[gpu]"
# If torch.cuda.is_available() is False, install a CUDA torch build from https://pytorch.org/get-started/locally/
```

The backend picks a device automatically: CUDA first, then Apple Silicon (MPS), then CPU. If a GPU run fails
(for example, out of memory), the same model is retried on CPU. `GET /api/health` shows which device is in use
and whether ffmpeg was found.

### Frontend

```bash
cd frontend
npm install
```

## Run

Use two terminals:

```bash
# 1. API on http://127.0.0.1:8000
cd backend && source .venv/bin/activate
uvicorn app.main:create_app --factory --port 8000

# 2. UI on http://localhost:5173
cd frontend
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend. If port 5173 is taken, Vite
picks another one and prints it.

The first job takes longer than the rest because it downloads models: about 900 MB for Mel-Roformer, 640 MB
for BS-Roformer, and HT-Demucs only if a fallback is needed.

### Where files go

- `tracks/` (repo root): the finished vocals, one MP3 per song, named after its title, e.g.
  `Laufey - The Risk.mp3`. A second song with the same title becomes `Laufey - The Risk (2).mp3`.
  Don't rename or move these files while the app is running; the library looks them up by name.
- `backend/data/`: everything else. The SQLite database, `originals/` (the songs you uploaded), `models/`,
  and the scratch folders `uploads/` and `tmp/`.

### Production build

```bash
cd frontend && npm run build       # outputs frontend/dist/
```

Serve `frontend/dist` with any static server and route `/api` to the backend. Or set `VITE_API_URL` at build
time (e.g. `VITE_API_URL=https://api.example.com npm run build`) and add that origin to
`ACAPELLA_CORS_ORIGINS` on the backend.

## Isolation strength

All three levels favor removing instrumental bleed over keeping vocal quality.

| Level    | What runs                                                                                                    | Speed (relative) |
|----------|--------------------------------------------------------------------------------------------------------------|------------------|
| `low`    | One Mel-Roformer pass.                                                                                       | 1×               |
| `medium` | Mel-Roformer and BS-Roformer, combined by keeping the **lower** magnitude of the two vocal spectrograms in every time-frequency bin. A sound only stays if both models agree it's vocal. | ~2×              |
| `high`   | `medium`, then a second Mel-Roformer pass on the resulting vocal stem, then a noise gate that sets the gaps between phrases to exact digital silence. | ~3×              |

If a Roformer model fails to download or run, that step falls back to **HT-Demucs** (`htdemucs_ft`). The
models actually used are recorded in each track's `settings`.

Noise gate defaults (see `backend/app/pipeline.py`): threshold −40 dB below the loudest part of the stem,
120 ms hold after each phrase, 20 ms lookahead before it, and bursts shorter than 60 ms are dropped.

### Configuration

| Env var                     | Default                                         |
|-----------------------------|-------------------------------------------------|
| `ACAPELLA_DATA_DIR`         | `backend/data` (SQLite DB, originals, models) |
| `ACAPELLA_TRACKS_DIR`       | `tracks` at the repo root (finished vocal MP3s) |
| `ACAPELLA_PRIMARY_MODEL`    | `vocals_mel_band_roformer.ckpt`                 |
| `ACAPELLA_SECONDARY_MODEL`  | `model_bs_roformer_ep_317_sdr_12.9755.ckpt`     |
| `ACAPELLA_FALLBACK_MODEL`   | `htdemucs_ft.yaml`                              |
| `ACAPELLA_CORS_ORIGINS`     | `http://localhost:5173,http://127.0.0.1:5173`   |

You can use any vocal model that `audio-separator --list_models` shows. For even less bleed, try
`mel_band_roformer_kim_ft2_bleedless_unwa.ckpt` as the primary model.

## API

| Method & path                              | Purpose                                                          |
|--------------------------------------------|------------------------------------------------------------------|
| `POST /api/upload`                         | multipart: `file` (mp3/wav/flac/m4a), `strength` (low/medium/high), optional `title`. Returns a job (202). |
| `GET /api/jobs/{id}`                       | Poll a job: `status` (queued/processing/done/failed), `progress` 0–1, `message`, `track_id`. |
| `GET /api/jobs?active=true`                | Jobs that are still queued or running.                           |
| `GET /api/tracks`                          | Library: title, duration, settings, audio URLs.                  |
| `GET /api/tracks/{id}/audio/{kind}`        | `kind` = `original` or `vocals_mp3`. Supports range requests; add `?download=true` for an attachment. |
| `DELETE /api/tracks/{id}`                  | Delete a track and its files.                                    |
| `GET /api/health`                          | Device in use and whether ffmpeg was found.                      |

Jobs run one at a time in a background worker thread. Jobs that were still running when the server stopped are
marked as failed on the next start.

## Tests

```bash
cd backend && source .venv/bin/activate
pytest
```

The tests build a 3-second synthetic song: a two-phrase "vocal" tone, a bass tone, and a hi-hat tone. They use
a fake separator, so no models are downloaded. They check:

- the min-magnitude ensemble removes each model's leak by 20 dB or more while keeping the vocal
- the gate makes gaps exactly zero while leaving phrases untouched
- the right number of model passes runs at each strength
- WAV loading and MP3 encoding
- fallback to HT-Demucs and the GPU-to-CPU retry
- the full upload → poll → library → stream → delete flow through the API

## Getting audio to process

Use audio you have the rights to work with:

- your own recordings and mixes
- DRM-free purchases from stores like Bandcamp, Qobuz or 7digital
- Creative Commons music, e.g. [Free Music Archive](https://freemusicarchive.org) or
  [ccMixter](https://ccmixter.org) (ccMixter also hosts official a cappellas)
- stems and a cappellas that artists release for remix contests

The README doesn't cover tools that rip tracks from streaming services such as Spotify. Downloading that way
breaks those services' terms and, for most commercial music, copyright law.
