# 🎬 Letterboxd Watchlist Matcher

Finde gemeinsame Film-Favoriten aus den Letterboxd-Watchlists mehrerer Profile!

## ✨ Features

- **Backend (FastAPI)**:
  - Scrapt automatisch alle Seiten der Letterboxd-Watchlist (Slug, Titel, hochauflösende Film-Poster).
  - Schneller Abgleich mit diskcache (TTL: 60 Minuten) für minimale Ladezeiten.
  - Endpunkt `POST /api/match`: Ermittelt Schnittmengen, sortiert absteigend (Volltreffer ganz oben).
  - CORS für Frontend aktiviert (`http://localhost:5173`).
- **Frontend (React + Vite + Tailwind CSS)**:
  - Elegantes Dark Cinema Theme mit Letterboxd-Farbakzenten.
  - Dynamisches Hinzufügen und Entfernen von Usernamen per Tag-System & Schnelltest-Vorschläge.
  - Live-Ladefeedback während des Scrapings.
  - Geteilte Ansicht: **Volltreffer** (bei allen) & **Teilüberschneidungen** (inkl. User-Badges).
  - Integrierte Schnellsuche und Filtertabs (Alle / Nur Volltreffer / Nur Teil-Matches).

---

## 🚀 Schnellstart

### 1. Backend starten

```bash
cd backend

# Virtuelle Umgebung aktivieren (falls noch nicht aktiv)
# Windows:
.\venv\Scripts\activate

# Abhängigkeiten installieren (einmalig)
pip install -r requirements.txt

# Server starten
uvicorn app.main:app --reload --port 8000
```
Das Backend ist unter `http://localhost:8000` erreichbar (Swagger-Doku unter `http://localhost:8000/docs`).

### 2. Frontend starten

```bash
cd frontend

# Abhängigkeiten installieren (einmalig)
npm install

# Dev-Server starten
npm run dev
```
Das Frontend ist unter `http://localhost:5173` erreichbar.

---

## 🧪 Tests ausführen

Im Backend-Verzeichnis:
```bash
cd backend
pytest tests
```