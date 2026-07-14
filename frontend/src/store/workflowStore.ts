import { create } from 'zustand';
import { Workflow } from '@/types/workflow';

interface WorkflowState {
  workflows: Workflow[];
  currentWorkflow: Workflow | null;
  setWorkflows: (workflows: Workflow[]) => void;
  setCurrentWorkflow: (workflow: Workflow | null) => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  workflows: [],
  currentWorkflow: null,
  setWorkflows: (workflows) => set({ workflows }),
  setCurrentWorkflow: (currentWorkflow) => set({ currentWorkflow }),
}));
