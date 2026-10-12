import React from 'react';
import { Users, Film, CheckCircle2, Layers, Search } from 'lucide-react';

export function StatsBanner({
  matchData,
  searchQuery,
  onSearchChange,
  filterType,
  onFilterChange,
}) {
  if (!matchData) return null;

  const { total_users, usernames, user_stats, perfect_matches, partial_matches } = matchData;

  return (
    <div className="bg-[#161b22] border border-white/10 rounded-2xl p-5 mb-8 shadow-xl">
      {/* Top summary row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div className="bg-[#0d1117] p-3.5 rounded-xl border border-white/5 flex flex-col">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Users className="w-3.5 h-3.5 text-cyan-400" />
            Profile
          </span>
          <span className="text-xl font-bold text-white">{total_users}</span>
        </div>

        <div className="bg-[#0d1117] p-3.5 rounded-xl border border-white/5 flex flex-col">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#00e054]" />
            Volltreffer
          </span>
          <span className="text-xl font-bold text-[#00e054]">
            {perfect_matches.length}
          </span>
        </div>

        <div className="bg-[#0d1117] p-3.5 rounded-xl border border-white/5 flex flex-col">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Teil-Matches
          </span>
          <span className="text-xl font-bold text-cyan-400">
            {partial_matches.length}
          </span>
        </div>

        <div className="bg-[#0d1117] p-3.5 rounded-xl border border-white/5 flex flex-col">
          <span className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
            <Film className="w-3.5 h-3.5 text-[#ff8000]" />
            Gesamt-Matches
          </span>
          <span className="text-xl font-bold text-[#ff8000]">
            {perfect_matches.length + partial_matches.length}
          </span>
        </div>
      </div>

      {/* Profile Watchlist breakdown */}
      <div className="mb-5 pb-5 border-b border-white/5">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2.5 block">
          Watchlist-Größen:
        </span>
        <div className="flex flex-wrap gap-2">
          {usernames.map((user) => (
            <div
              key={user}
              className="px-3 py-1.5 rounded-lg bg-[#0d1117] border border-white/5 text-xs flex items-center gap-2"
            >
              <span className="font-mono text-slate-300 font-medium">@{user}</span>
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-bold">
                {user_stats[user] ?? 0} Filme
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Filter and Search row */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search input */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Ergebnisse durchsuchen (z.B. Dune, 2024)..."
            className="w-full pl-9 pr-3.5 py-2 bg-[#0d1117] border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#00e054] transition-all"
          />
        </div>

        {/* Tab/Filter toggle */}
        <div className="flex items-center gap-1 bg-[#0d1117] p-1 rounded-xl border border-white/5">
          <button
            type="button"
            onClick={() => onFilterChange('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filterType === 'all'
                ? 'bg-slate-800 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Alle ({perfect_matches.length + partial_matches.length})
          </button>
          <button
            type="button"
            onClick={() => onFilterChange('perfect')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filterType === 'perfect'
                ? 'bg-[#00e054]/20 text-[#00e054] border border-[#00e054]/30 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Nur Volltreffer ({perfect_matches.length})
          </button>
          <button
            type="button"
            onClick={() => onFilterChange('partial')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filterType === 'partial'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Nur Teil-Matches ({partial_matches.length})
          </button>
        </div>
      </div>
    </div>
  );
}
