# Letterboxd Watchlist Matcher

Find common movie favorites across multiple Letterboxd watchlists.

---

## English

A full-stack application designed to compare two or more Letterboxd watchlists and find common films for movie nights.

### Features

- **Backend (FastAPI)**:
  - Scrapes Letterboxd watchlists across all paginated pages (extracting slug, title, and high-resolution poster URLs).
  - Built-in caching via `diskcache` (TTL: 60 minutes) to eliminate redundant requests.
  - Endpoint `POST /api/match`: Accepts a list of usernames (min. 2), computes watchlist intersections, and sorts them descending (movies on all profiles appear at the top).
  - CORS enabled for the frontend (`http://localhost:5173`).
- **Frontend (React + Vite + Tailwind CSS)**:
  - Modern cinema-dark user interface with Letterboxd-inspired accent colors.
  - Tag-based input system to dynamically add and remove Letterboxd usernames.
  - Loading animation and status updates during active scraping.
  - Distinct result categories:
    - **Perfect Matches**: Movies present on all submitted watchlists.
    - **Partial Overlaps**: Movies present on multiple watchlists, tagged with the profiles that have them.
    - Live title search and filter tabs (All, Perfect Matches, Partial Overlaps).
    - **Shareable URL links**: Automatically synchronizes usernames to the URL (`?users=user1,user2`) and provides one-click share buttons. Opening a share link automatically runs the comparison.
    - **Recent searches history**: Remembers recently compared user combinations in `localStorage` for fast one-click re-matching.

### Quickstart

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment (if not already present)
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`. Interactive documentation is available at `http://127.0.0.1:8000/docs`.

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

#### Running Tests

From the `backend` directory:

```bash
python -m pytest tests
```

---

## Deutsch

Eine Full-Stack-Anwendung zum Vergleichen von zwei oder mehr Letterboxd-Watchlists, um gemeinsame Film-Favoriten zu finden.

### Features

- **Backend (FastAPI)**:
  - Scrapt Letterboxd-Watchlists über alle paginierten Seiten (Slug, Titel und hochauflösende Filmposter).
  - Integriertes Caching mit `diskcache` (TTL: 60 Minuten) zur Vermeidung redundanter Anfragen.
  - Endpunkt `POST /api/match`: Empfängt mindestens zwei Usernamen, ermittelt die Schnittmengen und sortiert absteigend (Filme auf allen Listen stehen ganz oben).
  - **SSRF-Schutz**: Strikte Validierung von Nutzernamen (Regex, Pfadtraversierungs-Sperre, reservierte Letterboxd-Pfade) und DNS/IP-Prüfung zur Blockierung interner Netzwerk- und Cloud-Metadaten-Ziele (127.0.0.1, 169.254.169.254, RFC-1918).
  - **Gehärtetes CORS**: Strikt konfigurierbare Origins (Standard: localhost:5173, anpassbar via `CORS_ALLOWED_ORIGINS`), beschränkt auf erforderliche Methoden (`GET`, `POST`, `OPTIONS`) und Header.
  - **Rate Limiting**: Leichtgewichtiges, speicheroptimiertes Sliding-Window-Rate-Limiting (Standard: 15 Anfragen/Min für `/api/match`, 60/Min für Basispfade) mit `429 Too Many Requests` und `Retry-After`-Headern.
- **Frontend (React + Vite + Tailwind CSS)**:
  - Modernes Cinema-Dark-Design mit Letterboxd-Farbtönen.
  - Tag-basiertes Eingabefeld zum dynamischen Hinzufügen von Profilen (unterstützt Nutzernamen, `@handle` sowie vollständige Letterboxd-Profil- oder Watchlist-URLs wie `https://letterboxd.com/username/`).
  - Ladeanimation und Statusmeldungen während des Scraping-Vorgangs.
  - Strukturierte Trefferanzeige:
    - **Volltreffer**: Filme, die auf den Watchlists aller Profile vorkommen.
    - **Teilüberschneidungen**: Filme, die bei mehreren Profilen vorkommen, inklusive Profil-Tags.
  - Schnelle Live-Suche und Filtertabs (Alle, Nur Volltreffer, Nur Teil-Matches).
  - **Teilbare URL-Links**: Spiegelt Profile automatisch in der URL (`?users=user1,user2`) und bietet 1-Klick-Share-Buttons. Beim Öffnen eines Share-Links wird der Vergleich direkt automatisch gestartet.
  - **Verlauf & Zuletzt gesucht**: Speichert die letzten Profil-Kombinationen im `localStorage` für blitzschnellen erneuten Abgleich.

### Schnellstart

#### 1. Backend einrichten

```bash
cd backend

# Virtuelle Umgebung erstellen (falls nicht vorhanden)
python -m venv venv

# Virtuelle Umgebung aktivieren
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Server starten
uvicorn app.main:app --reload --port 8000
```

Die API läuft unter `http://127.0.0.1:8000`. Die interaktive Dokumentation ist unter `http://127.0.0.1:8000/docs` erreichbar.

#### 2. Frontend einrichten

```bash
cd frontend

# Abhängigkeiten installieren
npm install

# Entwicklungsserver starten
npm run dev
```

Das Frontend läuft unter `http://localhost:5173`.

#### Tests ausführen

Im `backend`-Verzeichnis:

```bash
python -m pytest tests
```