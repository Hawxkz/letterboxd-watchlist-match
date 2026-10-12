import React, { useState } from 'react';
import { Header } from './components/Header';
import { UserTagInput } from './components/UserTagInput';
import { MovieCard } from './components/MovieCard';
import { StatsBanner } from './components/StatsBanner';
import {
  Film,
  CheckCircle2,
  Users,
  Loader2,
  AlertTriangle,
  PlayCircle,
  HelpCircle,
  Sparkles,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [usernames, setUsernames] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const [error, setError] = useState(null);
  const [matchData, setMatchData] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all'); // 'all', 'perfect', 'partial'

  const handleAddUser = (username) => {
    setUsernames((prev) => [...prev, username]);
    setError(null);
  };

  const handleRemoveUser = (username) => {
    setUsernames((prev) => prev.filter((u) => u !== username));
    setError(null);
  };

  const handleClearAll = () => {
    setUsernames([]);
    setMatchData(null);
    setError(null);
  };

  const handleCompare = async () => {
    if (usernames.length < 2) {
      setError('Bitte gib mindestens 2 verschiedene Letterboxd-Usernamen an.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setLoadingStatus('Letterboxd-Watchlists werden geladen...');

    // Dynamic loading status messages for user feedback
    const statusInterval = setInterval(() => {
      setLoadingStatus((prev) => {
        if (prev.includes('Watchlists')) return 'Analysiere Seiten & extrahiere Filmdaten...';
        if (prev.includes('Analysiere')) return 'Lade Filmposter & berechne Schnittmengen...';
        if (prev.includes('Lade Filmposter')) return 'Fast fertig, erstelle Trefferlisten...';
        return 'Watchlists werden geladen...';
      });
    }, 2500);

    try {
      const response = await fetch(`${API_BASE_URL}/api/match`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ usernames }),
      });

      clearInterval(statusInterval);

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(
          errData.detail || `Server antwortete mit Fehlercode ${response.status}.`
        );
      }

      const data = await response.json();
      setMatchData(data);
    } catch (err) {
      clearInterval(statusInterval);
      setError(
        err.message || 'Verbindung zum Backend fehlgeschlagen. Läuft der FastAPI-Server?'
      );
    } finally {
      setIsLoading(false);
      setLoadingStatus('');
    }
  };

  // Filter movies based on search query
  const filterByQuery = (movieList) => {
    if (!searchQuery.trim()) return movieList;
    const q = searchQuery.toLowerCase().trim();
    return movieList.filter(
      (m) =>
        m.title.toLowerCase().includes(q) ||
        m.slug.toLowerCase().includes(q) ||
        m.matched_users.some((u) => u.toLowerCase().includes(q))
    );
  };

  const perfectMatches = matchData ? filterByQuery(matchData.perfect_matches) : [];
  const partialMatches = matchData ? filterByQuery(matchData.partial_matches) : [];

  return (
    <div className="min-h-screen bg-[#0d1117] text-slate-100 flex flex-col font-sans selection:bg-[#00e054] selection:text-black">
      {/* Top Banner & Header */}
      <Header />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 pb-20">
        {/* Controls Container */}
        <div className="mb-10 max-w-3xl mx-auto flex flex-col gap-4">
          <UserTagInput
            usernames={usernames}
            onAddUser={handleAddUser}
            onRemoveUser={handleRemoveUser}
            onClearAll={handleClearAll}
            disabled={isLoading}
          />

          {/* Action button */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <button
              type="button"
              id="compare-btn"
              onClick={handleCompare}
              disabled={isLoading || usernames.length < 2}
              className={`w-full sm:w-auto px-8 py-3.5 rounded-xl font-bold text-base flex items-center justify-center gap-2.5 shadow-xl transition-all duration-300 ${
                isLoading || usernames.length < 2
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/5'
                  : 'bg-gradient-to-r from-[#00e054] to-[#00b343] text-black hover:from-[#05ff62] hover:to-[#00cc4c] hover:shadow-2xl hover:shadow-[#00e054]/25 hover:scale-[1.02] active:scale-[0.98]'
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin text-black" />
                  <span>Vergleiche Watchlists...</span>
                </>
              ) : (
                <>
                  <PlayCircle className="w-5 h-5" />
                  <span>Watchlists vergleichen</span>
                </>
              )}
            </button>
          </div>

          {/* Loading status indicator */}
          {isLoading && (
            <div className="bg-[#161b22] border border-[#00e054]/30 rounded-xl p-4 text-center animate-pulse flex flex-col items-center justify-center gap-2 shadow-lg">
              <div className="flex items-center gap-2 text-sm font-semibold text-[#00e054]">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{loadingStatus}</span>
              </div>
              <p className="text-xs text-slate-400">
                Letterboxd wird live abgefragt und gecacht (TTL: 60 min).
              </p>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="bg-red-950/60 border border-red-500/50 rounded-xl p-4 text-sm text-red-200 flex items-start gap-3 shadow-lg animate-in fade-in">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-red-300">Aktion fehlgeschlagen</p>
                <p className="text-xs text-red-200/90 mt-0.5">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Results Area */}
        {matchData && (
          <div className="animate-in fade-in duration-500">
            {/* Stats and Search bar */}
            <StatsBanner
              matchData={matchData}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              filterType={filterType}
              onFilterChange={setFilterType}
            />

            {/* Check if search resulted in zero matches */}
            {perfectMatches.length === 0 && partialMatches.length === 0 ? (
              <div className="bg-[#161b22] border border-white/10 rounded-2xl p-12 text-center max-w-xl mx-auto">
                <Film className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h3 className="text-lg font-bold text-white mb-1">
                  Keine Treffer gefunden
                </h3>
                <p className="text-sm text-slate-400">
                  {searchQuery
                    ? `Keine Filme passend zu "${searchQuery}" gefunden.`
                    : 'Es gibt leider keine gemeinsamen Filme zwischen diesen Watchlists.'}
                </p>
              </div>
            ) : (
              <div className="space-y-12">
                {/* 1. SEKTION: VOLLTREFFER */}
                {(filterType === 'all' || filterType === 'perfect') && (
                  <section id="section-volltreffer">
                    <div className="flex items-center justify-between pb-3 mb-6 border-b border-white/10">
                      <div className="flex items-center gap-2.5">
                        <span className="p-1.5 rounded-lg bg-[#00e054]/10 text-[#00e054] border border-[#00e054]/20">
                          <CheckCircle2 className="w-5 h-5" />
                        </span>
                        <div>
                          <h2 className="text-xl md:text-2xl font-extrabold text-white">
                            Volltreffer
                          </h2>
                          <p className="text-xs text-slate-400">
                            Filme, die auf den Watchlists <strong>aller</strong> Profile stehen
                          </p>
                        </div>
                      </div>
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-[#00e054]/20 text-[#00e054] border border-[#00e054]/30">
                        {perfectMatches.length} {perfectMatches.length === 1 ? 'Film' : 'Filme'}
                      </span>
                    </div>

                    {perfectMatches.length > 0 ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                        {perfectMatches.map((movie) => (
                          <MovieCard
                            key={movie.slug}
                            movie={movie}
                            totalUsers={matchData.total_users}
                            isPerfectMatch={true}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center bg-[#161b22]/50 border border-white/5 rounded-xl">
                        <p className="text-sm text-slate-400">
                          Keine Filme gefunden, die bei <em>allen</em> Nutzern auf der Watchlist stehen.
                        </p>
                      </div>
                    )}
                  </section>
                )}

                {/* 2. SEKTION: TEILÜBERSCHNEIDUNGEN */}
                {(filterType === 'all' || filterType === 'partial') && (
                  <section id="section-teilueberschneidungen">
                    <div className="flex items-center justify-between pb-3 mb-6 border-b border-white/10">
                      <div className="flex items-center gap-2.5">
                        <span className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                          <Users className="w-5 h-5" />
                        </span>
                        <div>
                          <h2 className="text-xl md:text-2xl font-extrabold text-white">
                            Teilüberschneidungen
                          </h2>
                          <p className="text-xs text-slate-400">
                            Filme, die bei mehreren (aber nicht allen) Profilen vorkommen
                          </p>
                        </div>
                      </div>
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                        {partialMatches.length} {partialMatches.length === 1 ? 'Film' : 'Filme'}
                      </span>
                    </div>

                    {partialMatches.length > 0 ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                        {partialMatches.map((movie) => (
                          <MovieCard
                            key={movie.slug}
                            movie={movie}
                            totalUsers={matchData.total_users}
                            isPerfectMatch={false}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center bg-[#161b22]/50 border border-white/5 rounded-xl">
                        <p className="text-sm text-slate-400">
                          Keine Teilüberschneidungen vorhanden.
                        </p>
                      </div>
                    )}
                  </section>
                )}
              </div>
            )}
          </div>
        )}

        {/* Initial Empty State Hero (When no match has been performed yet) */}
        {!matchData && !isLoading && !error && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
            <div className="bg-[#161b22]/60 border border-white/5 rounded-2xl p-5 text-center flex flex-col items-center">
              <div className="w-10 h-10 rounded-xl bg-[#00e054]/10 border border-[#00e054]/20 flex items-center justify-center text-[#00e054] mb-3">
                <Users className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-sm text-white mb-1">
                Profile eingeben
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Trage zwei oder mehr Letterboxd-Usernamen deiner Freunde ein.
              </p>
            </div>

            <div className="bg-[#161b22]/60 border border-white/5 rounded-2xl p-5 text-center flex flex-col items-center">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-3">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-sm text-white mb-1">
                Live & Gecacht
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Das Backend scrapt alle Seiten der Watchlist und puffert Anfragen 60 Minuten.
              </p>
            </div>

            <div className="bg-[#161b22]/60 border border-white/5 rounded-2xl p-5 text-center flex flex-col items-center">
              <div className="w-10 h-10 rounded-xl bg-[#ff8000]/10 border border-[#ff8000]/20 flex items-center justify-center text-[#ff8000] mb-3">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-sm text-white mb-1">
                Perfekte Matches
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Finde auf Anhieb Volltreffer und Teilüberschneidungen mit Original-Postern.
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-6 text-center text-xs text-slate-500">
        <p>Letterboxd Watchlist Matcher • Nicht offiziell mit Letterboxd verbunden</p>
      </footer>
    </div>
  );
}

export default App;
