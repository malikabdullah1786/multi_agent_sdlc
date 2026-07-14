export interface WorkflowNode {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  agentType: string;
}

export interface WorkflowEdge {
  from: string;
  to: string;
}

export interface Workflow {
  id: string;
  projectId: string;
  status: 'pending' | 'running' | 'awaiting_approval' | 'completed' | 'failed';
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  createdAt: string;
}
