export interface AgentMetric {
  runsCount: number;
  successRate: number;
  avgLatencyMs: number;
  tokensUsed: number;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'busy' | 'offline';
  metrics: AgentMetric;
}
