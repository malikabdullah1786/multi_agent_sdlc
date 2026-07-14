import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="h-16 border-b border-slate-900 bg-slate-950/50 backdrop-blur px-8 flex items-center justify-between">
      <h1 className="text-lg font-semibold text-white">System Status: Active</h1>
      <div className="flex items-center gap-4">
        <span className="flex h-2 w-2 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span className="text-sm text-slate-400">All Agents Running</span>
      </div>
    </header>
  );
};
