import React from 'react';
import Link from 'next/link';

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-900 min-h-screen text-slate-300 p-4">
      <div className="mb-8 font-bold text-xl text-white tracking-wider flex items-center gap-2">
        <span className="bg-indigo-600 w-8 h-8 rounded-lg flex items-center justify-center text-sm">AG</span>
        Antigravity SDLC
      </div>
      <nav className="space-y-1">
        <Link href="/dashboard" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 hover:text-white transition-colors">
          Dashboard
        </Link>
        <Link href="/projects" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 hover:text-white transition-colors">
          Projects
        </Link>
        <Link href="/workflows" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 hover:text-white transition-colors">
          Workflows
        </Link>
        <Link href="/agents" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 hover:text-white transition-colors">
          Agents
        </Link>
        <Link href="/approvals" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 hover:text-white transition-colors">
          Approvals
        </Link>
        <Link href="/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-900 hover:text-white transition-colors">
          Settings
        </Link>
      </nav>
    </aside>
  );
};
