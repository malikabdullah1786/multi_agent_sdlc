import React from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, Badge, Button } from '@/components/ui';

export default function DashboardPage() {
  return (
    <MainLayout>
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-extrabold text-white">Multi-Agent Workspace</h2>
            <p className="text-slate-400">Monitor active SDLC agent sessions and pipeline approvals.</p>
          </div>
          <Button variant="primary">New Project</Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <h3 className="text-slate-400 text-sm font-medium">Active Pipelines</h3>
            <p className="text-3xl font-bold mt-2 text-white">4</p>
          </Card>
          <Card>
            <h3 className="text-slate-400 text-sm font-medium">Pending Approvals</h3>
            <p className="text-3xl font-bold mt-2 text-amber-400">2</p>
          </Card>
          <Card>
            <h3 className="text-slate-400 text-sm font-medium">Agent Run Efficiency</h3>
            <p className="text-3xl font-bold mt-2 text-emerald-400">98.4%</p>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
