import React from 'react';
import { Film, Clapperboard, Sparkles } from 'lucide-react';

export function Header() {
  return (
    <header className="relative py-8 md:py-12 text-center overflow-hidden">
      {/* Decorative background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-48 bg-[#00e054]/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 w-80 h-36 bg-[#40bcf4]/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative max-w-4xl mx-auto px-4">
        {/* Brand pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-white/10 text-xs font-medium text-slate-300 mb-4 backdrop-blur-sm shadow-sm">
          <Clapperboard className="w-3.5 h-3.5 text-slate-400" />
          <span>Watchlist Matcher (Inoffiziell)</span>
          <span className="text-slate-500">•</span>
          <span className="text-[#00e054] flex items-center gap-1 font-semibold">
            <Sparkles className="w-3 h-3" /> Live Sync
          </span>
        </div>

        <h1 className="text-3xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-white mb-3">
          Watchlist <span className="bg-gradient-to-r from-[#00e054] via-[#40bcf4] to-[#ff8000] bg-clip-text text-transparent">Matcher</span>
        </h1>

        <p className="text-sm md:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Welcher Film steht bei euch allen auf der Liste? Gib die Letterboxd-Usernamen deiner Filmrunde ein und finde sofort perfekte Filmabend-Treffer.
        </p>
      </div>
    </header>
  );
}
