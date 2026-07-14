export interface Project {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
}
