import React from 'react';

export function Footer() {
  return (
    <footer className="mt-auto border-t border-white/5 bg-[#0b0e13]/80 py-8 px-4 text-center">
      <div className="max-w-4xl mx-auto flex flex-col items-center justify-center gap-4">
        {/* TMDB Branding & Attribution */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 bg-[#131720] border border-white/5 px-5 py-3 rounded-2xl shadow-sm">
          {/* Official TMDB SVG Logo */}
          <a
            href="https://www.themoviedb.org/"
            target="_blank"
            rel="noopener noreferrer"
            title="The Movie Database (TMDB)"
            className="shrink-0 hover:opacity-80 transition-opacity"
          >
            <svg
              className="h-4 w-auto"
              viewBox="0 0 185 16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="The Movie Database Logo"
            >
              <defs>
                <linearGradient id="tmdbGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#90cea1" />
                  <stop offset="50%" stopColor="#01b4e4" />
                  <stop offset="100%" stopColor="#0d253f" />
                </linearGradient>
              </defs>
              <text
                x="0"
                y="13"
                fontFamily="system-ui, -apple-system, sans-serif"
                fontWeight="900"
                fontSize="15"
                letterSpacing="2"
                fill="url(#tmdbGradient)"
              >
                THE MOVIE DB
              </text>
            </svg>
          </a>

          <span className="hidden sm:inline text-slate-600">•</span>

          <p className="text-xs text-slate-400 max-w-md leading-relaxed text-center sm:text-left">
            This product uses the TMDB API but is not endorsed or certified by TMDB.
          </p>
        </div>

        {/* Creator Attribution & General App Disclaimer */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-2 text-xs text-slate-400">
          <p className="text-[11px] text-slate-500">
            Letterboxd Watchlist Matcher • Nicht offiziell mit Letterboxd verbunden
          </p>
          <span className="hidden sm:inline text-slate-700">•</span>
          <p className="flex items-center gap-1 text-xs">
            <span className="text-slate-500">By</span>
            <a
              href="https://github.com/Hawxkz"
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-slate-300 hover:text-[#00e054] transition-colors"
            >
              Hawxkz
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
