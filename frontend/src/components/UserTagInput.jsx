import React, { useState } from 'react';
import { UserPlus, X, User, AlertCircle, Link as LinkIcon } from 'lucide-react';
import { RecentSearches } from './RecentSearches';
import { extractLetterboxdUsername } from '../utils/letterboxd';

export function UserTagInput({
  usernames,
  onAddUser,
  onRemoveUser,
  onClearAll,
  disabled,
  recentSearches = [],
  onSelectRecent,
  onClearRecent,
}) {
  const [inputValue, setInputValue] = useState('');
  const [inputError, setInputError] = useState('');

  const isUrlInput =
    inputValue.toLowerCase().includes('letterboxd.com') ||
    inputValue.startsWith('http://') ||
    inputValue.startsWith('https://');

  const handleAdd = () => {
    const trimmed = extractLetterboxdUsername(inputValue);
    if (!trimmed) {
      setInputError('Bitte gib einen gültigen Letterboxd-Nutzernamen oder Profil-Link ein.');
      return;
    }

    if (usernames.some((u) => u.toLowerCase() === trimmed.toLowerCase())) {
      setInputError(`'@${trimmed}' ist bereits in der Liste.`);
      return;
    }

    onAddUser(trimmed);
    setInputValue('');
    setInputError('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <div className="bg-[#161b22]/90 border border-white/10 rounded-2xl p-5 shadow-xl backdrop-blur-md">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <User className="w-4 h-4 text-[#00e054]" />
            Letterboxd Profile vergleichen
          </h2>
          <p className="text-xs text-slate-400">
            Füge mindestens 2 Profile hinzu (Usernamen oder Profil-Links wie letterboxd.com/username).
          </p>
        </div>
        {usernames.length > 0 && (
          <button
            type="button"
            onClick={onClearAll}
            disabled={disabled}
            className="text-xs text-slate-400 hover:text-red-400 self-start sm:self-auto transition-colors disabled:opacity-50"
          >
            Alle entfernen
          </button>
        )}
      </div>

      {/* Input row */}
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500 font-mono text-sm">
            {isUrlInput ? (
              <LinkIcon className="w-3.5 h-3.5 text-cyan-400" />
            ) : (
              '@'
            )}
          </span>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              if (inputError) setInputError('');
            }}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Username oder Profil-Link (z.B. letterboxd.com/user)..."
            className="w-full pl-8 pr-4 py-2.5 bg-[#0d1117] border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#00e054] focus:ring-1 focus:ring-[#00e054] transition-all disabled:opacity-50"
          />
        </div>
        <button
          type="button"
          onClick={handleAdd}
          disabled={disabled || !inputValue.trim()}
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm rounded-xl border border-white/10 hover:border-white/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm cursor-pointer"
        >
          <UserPlus className="w-4 h-4 text-[#00e054]" />
          Hinzufügen
        </button>
      </div>

      {inputError && (
        <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          {inputError}
        </div>
      )}

      {/* User tag list */}
      <div className="mt-4 flex flex-wrap gap-2 items-center">
        {usernames.map((name) => (
          <div
            key={name}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#1c222b] border border-[#00e054]/30 rounded-xl text-xs font-mono text-slate-200 shadow-sm animate-in fade-in"
          >
            <span className="w-2 h-2 rounded-full bg-[#00e054]" />
            <span className="font-semibold text-white">@{name}</span>
            <button
              type="button"
              onClick={() => onRemoveUser(name)}
              disabled={disabled}
              className="text-slate-400 hover:text-red-400 p-0.5 rounded-md hover:bg-white/5 transition-colors disabled:opacity-50"
              title={`@${name} entfernen`}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}

        {usernames.length === 0 && (
          <span className="text-xs text-slate-500 italic">
            Noch keine Profile hinzugefügt.
          </span>
        )}
      </div>

      {/* Recent searches history */}
      {recentSearches.length > 0 && (
        <RecentSearches
          searches={recentSearches}
          onSelect={onSelectRecent}
          onClear={onClearRecent}
          disabled={disabled}
        />
      )}
    </div>
  );
}
