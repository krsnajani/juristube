# JurisTube (LexTerminal)

A lightweight, self-hosted, zero-dependency scholarly video discovery portal and catalog built for legal academics, constitutional theorists, and humanities researchers.

JurisTube aggregates, curates, and filters academic talks, endowed lectures, faculty symposia, and scholarly discussions—cutting through algorithmic recommendation slop and clickbait.

---

## Highlights

- **Zero External Server Dependencies**: Runs on Python 3 standard library (`sqlite3`, `http.server`, `urllib`, `xml.etree`).
- **No YouTube Data API Keys Needed**: Metadata ingestion operates via `yt-dlp` flat-playlist extraction and academic blog RSS scraping.
- **Aggressive Anti-Slop & Quality Scoring**: Automatically discards clickbait, promotional teasers, reaction clips, and shorts while boosting endowed lectures (Hamlyn, Tanner), book talks, and symposia.
- **Multi-Vector Discovery**:
  - **Vector 1 (Archive Ingestion)**: Ingestion mapping from HackerTube/humanities archives.
  - **Vector 2 (Curated Scholar Sweeps)**: Seeded queries across legal philosophers, constitutional scholars, and social theorists.
  - **Vector 3 (Institutional Channels)**: Tier-ranked monitoring of major faculty and institute YouTube channels.
  - **Vector 4 (Academic Blog RSS)**: Extraction of YouTube links embedded in leading legal theory and constitutional law blogs.
- **Retro Academic Terminal Aesthetic**: Fast, monochrome, information-dense catalog with Vim navigation keys (`j`, `k`, `m`, `/`).
- **Instant Local Playback**: Single-keystroke `mpv` command copying (`m`) or `mpv://` protocol handler launching, alongside privacy-preserving `youtube-nocookie.com` modal embeds.

---

## Directory Structure

```text
juristube/
├── config/
│   ├── scholars.json       # Seed list of scholars categorized by discipline
│   ├── channels.json       # Curated institutional channels & authority tiers (1-3)
│   └── feeds.json          # Academic blog RSS feeds to monitor
├── data/
│   ├── .gitkeep
│   └── juristube.db        # SQLite database (auto-initialized; git-ignored)
├── static/
│   ├── style.css           # Retro monospace terminal styling
│   └── app.js              # Vanilla JS frontend, modal player, & Vim bindings
├── templates/
│   └── index.html          # Single-page terminal catalogue interface
├── db.py                   # SQLite schema initialization and connection helpers
├── filter_engine.py        # Heuristics: duration gates, slop regex, and academic scoring
├── import_hackertube.py    # Vector 1: Ingest and map HackerTube archive datasets
├── ingest_scholars.py      # Vector 2: Targeted scholar query ingestion via yt-dlp
├── ingest_channels.py      # Vector 3: Institutional channel scraper
├── ingest_blogs.py         # Vector 4: Academic blog RSS mining
├── server.py               # Standalone HTTP & JSON API server (port 8085)
└── README.md
```

---

## Architecture & Discovery Pipeline

```
              ┌──────────────────────────────────────────────────┐
              │               Discovery Vectors                  │
              └──────────────────────────────────────────────────┘
                 │                 │                │
      (Scholars JSON)    (Channels JSON)     (Blog RSS Feeds)
                 │                 │                │
                 ▼                 ▼                ▼
        ingest_scholars.py  ingest_channels.py  ingest_blogs.py
                 │                 │                │
                 └─────────────────┼────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       filter_engine.py       │
                    │  - Reject duration < 20 min  │
                    │  - Reject regex slop words   │
                    │  - Boost endowed lectures    │
                    │  - Assign authority tier     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │      data/juristube.db       │
                    │       (SQLite Storage)       │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │          server.py           │
                    │   Zero-dep HTTP/API (8085)   │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   LexTerminal Web Frontend   │
                    │   (Vim Keys / MPV / Embed)   │
                    └──────────────────────────────┘
```

---

## Requirements

- **Python**: Python 3.8+ (standard library only)
- **yt-dlp** (for running ingestion scripts):
  ```bash
  # macOS (Homebrew)
  brew install yt-dlp

  # Linux / pip
  pip install yt-dlp
  ```
- **mpv** (optional, recommended for terminal-native video playback):
  ```bash
  brew install mpv
  ```

---

## Quickstart

### 1. Initialize Database Schema
```bash
python3 db.py
```
This sets up `data/juristube.db` with indexed tables for `videos`, `scholars`, `channels`, and `ingest_log`.

### 2. Run the Web Server
```bash
python3 server.py
```
Open **[http://localhost:8085](http://localhost:8085)** in your browser.

---

## Ingestion Workflows

Populate or refresh the catalogue using any of the ingestion vectors:

### Vector 2: Scholar Searches
Queries YouTube for high-value academic lectures, keynotes, and book talks by scholars listed in `config/scholars.json`:
```bash
# Scan all configured scholars
python3 ingest_scholars.py

# Scan only the first 10 scholars (useful for testing or incremental updates)
python3 ingest_scholars.py 10
```

### Vector 3: Institutional Channels
Pulls recent uploads from institutional channels defined in `config/channels.json` (Oxford, Cambridge, Harvard, Yale, Max Planck, etc.):
```bash
python3 ingest_channels.py
```

### Vector 4: Academic Blog RSS Mining
Parses academic law blogs in `config/feeds.json` (Verfassungsblog, Balkinization, Opinio Juris, EJIL:Talk!, ICLP, etc.) and extracts embedded video talks:
```bash
python3 ingest_blogs.py
```

### Vector 1: HackerTube Archive Import
If you have an archive export from HackerTube (`videos.jsonl` in `/tmp/hackertube-data/`):
```bash
python3 import_hackertube.py
```

---

## Keyboard Shortcuts

The web catalog provides keyboard navigation:

| Key | Action |
| :--- | :--- |
| `j` / `↓` | Select next video in catalogue |
| `k` / `↑` | Select previous video in catalogue |
| `m` | Copy `mpv "<video-url>"` launch command to system clipboard |
| `Enter` | Open video modal details and `youtube-nocookie.com` embed player |
| `/` | Focus search bar |
| `Esc` | Close playback modal or unfocus search bar |

---

## Configuration

- **`config/scholars.json`**: Mapping of academic disciplines (e.g. `constitutional-law`, `jurisprudence`, `political-philosophy`, `international-law`, `social-theory`, `economics-political-economy`) to lists of scholar names.
- **`config/channels.json`**: List of institutional YouTube channels with assigned authority tiers (Tier 1: primary law faculties, Tier 2: think tanks and research institutes, Tier 3: secondary academic channels).
- **`config/feeds.json`**: Curated list of RSS/Atom feeds from academic blogs.

---

## License

MIT License. Designed for personal and academic research use.
