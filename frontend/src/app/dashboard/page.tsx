'use client';

import React, { useEffect, useRef } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { createSimulation } from '@/lib/simulateWorkflow';

export default function DashboardPage() {
  const simulationRef = useRef<{ start: () => void; stop: () => void } | null>(null);

  useEffect(() => {
    // Start the workflow simulation on mount
    simulationRef.current = createSimulation();
    simulationRef.current.start();

    return () => {
      simulationRef.current?.stop();
    };
  }, []);

  return <MainLayout />;
}
