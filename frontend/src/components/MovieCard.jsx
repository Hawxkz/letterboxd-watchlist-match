import React, { useState } from 'react';
import { ExternalLink, Film, CheckCircle2, Users, Star, Clock } from 'lucide-react';

export function MovieCard({ movie, totalUsers, isPerfectMatch }) {
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const letterboxdUrl = `https://letterboxd.com/film/${movie.slug}/`;

  return (
    <div className="group relative flex flex-col bg-[#161b22] border border-white/10 rounded-xl overflow-hidden shadow-lg transition-all duration-300 hover:-translate-y-1.5 hover:shadow-2xl hover:border-[#00e054]/50">
      {/* Poster Container */}
      <div className="relative aspect-[2/3] w-full bg-[#0d1117] overflow-hidden flex items-center justify-center">
        {movie.poster_url && !imageError ? (
          <>
            {!imageLoaded && (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 animate-pulse">
                <Film className="w-8 h-8 text-slate-600 animate-spin" />
              </div>
            )}
            <img
              src={movie.poster_url}
              alt={movie.title}
              loading="lazy"
              onLoad={() => setImageLoaded(true)}
              onError={() => setImageError(true)}
              className={`w-full h-full object-cover transition-transform duration-500 group-hover:scale-105 ${
                imageLoaded ? 'opacity-100' : 'opacity-0'
              }`}
            />
          </>
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center p-4 text-center bg-gradient-to-br from-slate-900 to-[#141b24]">
            <Film className="w-12 h-12 text-slate-600 mb-2 group-hover:text-[#00e054] transition-colors" />
            <span className="text-xs text-slate-400 font-medium line-clamp-3">
              {movie.title}
            </span>
          </div>
        )}

        {/* Hover overlay with Letterboxd button */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end justify-center p-3">
          <a
            href={letterboxdUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00e054] text-black font-semibold text-xs rounded-lg shadow-md hover:bg-[#00f85e] transition-colors"
          >
            Auf Letterboxd ansehen
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Match Count Badge top-right */}
        <div className="absolute top-2 right-2">
          {isPerfectMatch ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-[#00e054] text-black shadow-md">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Volltreffer
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 shadow-md backdrop-blur-sm">
              <Users className="w-3 h-3" />
              {movie.match_count}/{totalUsers}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-3.5 flex flex-col flex-1 justify-between gap-2.5">
        <div className="space-y-1.5">
          <a
            href={letterboxdUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-bold text-sm text-slate-100 hover:text-[#00e054] line-clamp-2 transition-colors block"
            title={movie.title}
          >
            {movie.title}
          </a>

          {/* TMDB Meta: Rating & Runtime */}
          {(movie.rating != null || movie.runtime != null) && (
            <div className="flex items-center gap-2.5 text-xs text-slate-400">
              {movie.rating != null && (
                <span className="flex items-center gap-1 font-semibold text-amber-400">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  {movie.rating}
                </span>
              )}
              {movie.runtime != null && (
                <span className="flex items-center gap-1 text-slate-400">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  {movie.runtime} Min.
                </span>
              )}
            </div>
          )}

          {/* Genres */}
          {movie.genres && movie.genres.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-0.5">
              {movie.genres.map((genre) => (
                <span
                  key={genre}
                  className="px-1.5 py-0.5 bg-slate-800/80 text-emerald-400/90 border border-emerald-500/20 rounded text-[10px] font-medium"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* User Badges */}
        <div className="pt-1 border-t border-white/5">
          <div className="text-[11px] text-slate-400 mb-1.5 font-medium flex items-center justify-between">
            <span>Auf Watchlist von:</span>
            <span className="text-slate-500">{movie.matched_users.length} Nutzer</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {movie.matched_users.map((user) => (
              <span
                key={user}
                className="inline-block px-1.5 py-0.5 bg-slate-800/90 text-slate-300 border border-slate-700/60 rounded text-[10px] font-mono hover:border-slate-500 transition-colors"
              >
                @{user}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
