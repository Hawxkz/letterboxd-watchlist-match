# Letterboxd Watchlist Matcher

Find common movie favorites across multiple Letterboxd watchlists.

---

## English

A modern, full-stack application designed to compare two or more Letterboxd watchlists, find common films for movie nights, and enrich them with ratings, genres, and runtimes.

### Features

- **Backend (FastAPI)**:
  - **Modular Architecture (SRP)**: Clear separation into `app.core` (infrastructure) and `app.services` (business logic) with protocol interfaces (`WatchlistScraperProtocol`, `MovieEnricherProtocol`) and dependency injection.
  - **Letterboxd Web Scraping**: Scrapes Letterboxd watchlists across all paginated pages (extracting slug, title, and high-resolution posters).
  - **TMDB Enrichment**:
    - Enriches matched movies with official TMDB ratings (★ vote average), genre badges, and runtime.
    - Zero-config fallback catalog with realistic metadata when no API key is set.
    - Configurable via `tmdb.env` or `.env` (`TMDB_API_KEY`, `TMDB_LANGUAGE`).
  - **High-Performance Caching**: Centralized `diskcache` (TTL: 60 minutes for watchlists, 24 hours for TMDB and posters).
  - **Security & Hardening**:
    - **SSRF Protection**: Asynchronous DNS resolution via background threadpool, strict username schema validation, blocked reserved routes, and private IP rejection (RFC 1918, link-local, cloud metadata `169.254.169.254`).
    - **Hardened CORS**: Configurable allowed origins (`CORS_ALLOWED_ORIGINS`), restricted to required methods (`GET`, `POST`, `OPTIONS`).
    - **Sliding-Window Rate Limiting**: In-memory rate limiting with HTTP 429 and `Retry-After` headers.
- **Frontend (React + Vite + Tailwind CSS)**:
  - **Cinema-Dark UI**: Clean, responsive interface with Letterboxd-inspired styling.
  - **Flexible Input**: Supports usernames, `@handles`, and full Letterboxd profile/watchlist URLs (e.g. `https://letterboxd.com/username/watchlist/`).
  - **Match Categories & Live Filtering**:
    - **Perfect Matches**: Films present on 100% of the compared profiles.
    - **Partial Overlaps**: Films shared by multiple profiles, showing user avatars/tags.
    - Filter by title search, genre tags, and sort by match count, rating, runtime, or title.
  - **Shareable URLs**: Automatically reflects usernames in query parameters (`?users=alice,bob`) with 1-click share buttons. Opening a share link automatically runs the comparison.
  - **Recent Searches History**: Remembers recently compared profile groups in `localStorage` for instant re-matching.

### Environment Configuration

Create a `tmdb.env` or `.env` file in the `backend/` directory:

```env
# TMDB API (Optional - realistic fallback catalog is used if omitted)
TMDB_API_KEY=your_tmdb_api_key_here
TMDB_LANGUAGE=en-US

# CORS (Optional - defaults to http://localhost:5173,http://127.0.0.1:5173)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Rate Limiting & Proxy Trust (Optional)
RATE_LIMIT_MATCH_PER_MINUTE=15
RATE_LIMIT_GENERAL_PER_MINUTE=60
TRUST_PROXY_HEADERS=false
```

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

The API will be available at `http://127.0.0.1:8000`. Interactive Swagger documentation is at `http://127.0.0.1:8000/docs`.

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
python -m pytest tests -v
```

---

## Deutsch

Eine moderne Full-Stack-Anwendung zum Vergleichen von zwei oder mehr Letterboxd-Watchlists, um gemeinsame Film-Favoriten für Filmabende zu finden – angereichert mit Bewertungen, Genres und Laufzeiten.

### Features

- **Backend (FastAPI)**:
  - **Modulare Architektur (SRP)**: Klare Trennung in `app.core` (Infrastruktur) und `app.services` (Business-Logik) mit Interface-Protokollen (`WatchlistScraperProtocol`, `MovieEnricherProtocol`) und Dependency Injection.
  - **Letterboxd Web-Scraping**: Paginierungsfestes Auslesen vollständiger Watchlists (Slug, Titel und hochauflösende Filmposter).
  - **TMDB-Anreicherung (The Movie Database)**:
    - Ergänzt Treffer um offizielle TMDB-Bewertungen (★ Community Score), Genre-Tags und Laufzeiten.
    - Zero-Config-Fallback-Katalog mit realistischen Daten, falls kein API-Key hinterlegt ist.
    - Konfigurierbar über `tmdb.env` oder `.env` (`TMDB_API_KEY`, `TMDB_LANGUAGE`).
  - **Zentraler Diskcache**: Gecachte Watchlists (TTL: 60 Minuten) und TMDB-Metadaten (TTL: 24 Stunden) vermeiden redundante Anfragen.
  - **Sicherheit & Härtung**:
    - **SSRF-Schutz**: Asynchrone DNS-Prüfung via Threadpool, Validierung der Nutzernamen-Syntax, Blockierung reservierter Letterboxd-Pfade und privater IP-Adressen (RFC 1918, Link-Local, Cloud-Metadata `169.254.169.254`).
    - **Gehärtetes CORS**: Strikt konfigurierbare Origins (`CORS_ALLOWED_ORIGINS`), beschränkt auf erforderliche Methoden (`GET`, `POST`, `OPTIONS`).
    - **Sliding-Window Rate Limiting**: Schutz vor Denial-of-Service mit HTTP 429 und `Retry-After`-Headern.
- **Frontend (React + Vite + Tailwind CSS)**:
  - **Cinema-Dark UI**: Stilvolles, responsives Design mit Letterboxd-Farbtönen.
  - **Flexible Eingabe**: Unterstützt reine Nutzernamen, `@handle` und vollständige Letterboxd-URLs (z. B. `https://letterboxd.com/nutzer/watchlist/`).
  - **Treffer-Kategorien & Live-Filterung**:
    - **Volltreffer**: Filme, die auf den Listen ausnahmslos aller verglichenen Profile stehen.
    - **Teilüberschneidungen**: Filme auf mehreren Listen, mit Profil-Badges der jeweiligen Nutzer.
    - Filterbar nach Titeln, Genres und sortierbar nach Übereinstimmungen, Bewertung, Laufzeit oder Alphabet.
  - **Teilbare URL-Links**: Spiegelt Profile in der Adresszeile (`?users=alice,bob`) und bietet 1-Klick-Share-Buttons. Beim Öffnen startet der Abgleich direkt automatisch.
  - **Verlauf & Zuletzt gesucht**: Speichert letzte Profil-Kombinationen im `localStorage` für blitzschnellen erneuten Abgleich.

### Konfiguration (Umgebungsvariablen)

Erstelle bei Bedarf eine `tmdb.env` oder `.env` im `backend/`-Ordner:

```env
# TMDB API (Optional - ohne Key greift der Fallback-Katalog)
TMDB_API_KEY=dein_tmdb_api_key_hier
TMDB_LANGUAGE=de-DE

# CORS (Optional - Standard: http://localhost:5173,http://127.0.0.1:5173)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Rate Limiting & Proxy-Trust (Optional)
RATE_LIMIT_MATCH_PER_MINUTE=15
RATE_LIMIT_GENERAL_PER_MINUTE=60
TRUST_PROXY_HEADERS=false
```

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
python -m pytest tests -v
```