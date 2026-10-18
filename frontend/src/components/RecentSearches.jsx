import React from 'react';
import { History, X, Users, ArrowRight } from 'lucide-react';

export function RecentSearches({ searches, onSelect, onClear, disabled }) {
  if (!searches || searches.length === 0) return null;

  return (
    <div className="mt-4 pt-3.5 border-t border-white/5 animate-in fade-in duration-300">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
          <History className="w-3.5 h-3.5 text-[#00e054]" />
          <span>Zuletzt verglichen:</span>
        </div>
        <button
          type="button"
          onClick={onClear}
          disabled={disabled}
          className="text-[11px] text-slate-500 hover:text-red-400 transition-colors disabled:opacity-50"
          title="Verlauf leeren"
        >
          Verlauf leeren
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {searches.map((item, index) => {
          const userList = Array.isArray(item) ? item : item.users || [];
          if (!userList.length) return null;

          return (
            <button
              key={index}
              type="button"
              onClick={() => onSelect(userList)}
              disabled={disabled}
              className="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0d1117] hover:bg-[#1f2937] border border-white/10 hover:border-[#00e054]/40 text-xs text-slate-300 hover:text-white transition-all disabled:opacity-50 text-left cursor-pointer"
              title={`Klicken um @${userList.join(', @')} zu laden`}
            >
              <Users className="w-3 h-3 text-slate-500 group-hover:text-[#00e054] transition-colors shrink-0" />
              <span className="font-mono text-[11px] truncate max-w-[200px] sm:max-w-none">
                {userList.map((u) => `@${u}`).join(' + ')}
              </span>
              <ArrowRight className="w-3 h-3 opacity-0 -ml-1 group-hover:opacity-100 group-hover:ml-0 text-[#00e054] transition-all shrink-0" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
