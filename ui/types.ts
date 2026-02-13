export enum RunStatus {
  PLANNING = 'planning',
  EXECUTING = 'executing',
  REVIEWING = 'reviewing',
  AUDITING = 'auditing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  RUNNING = 'running', // Generic running state if specific sub-state isn't known
}

export interface Agent {
  name: string;
  description?: string;
}

export interface RunRequest {
  prompt: string;
  executor: string;
  workdir?: string | null;
  persona?: string;
  dry_run?: boolean;
}

export interface LoopRequest {
  task: string;
  executor: string;
  max_retries: number;
  workdir?: string | null;
  persona?: string;
  dry_run?: boolean;
  context_paths?: string[];
}

export interface RunResponse {
  run_id: string;
  status: string;
  result?: string | null;
  error?: string | null;
}

export interface RunEvent {
  type: string;
  message: string;
  ts: string;
  details?: any;
}

export interface RunDetails {
  run_id: string;
  meta: {
    status: string;
    task?: string;
    prompt?: string;
    executor: string;
    [key: string]: any;
  };
  events: RunEvent[];
  result?: string;
  error?: string;
}

export interface RunSummary {
  run_id: string;
  status: string;
  task?: string; // or prompt
  executor?: string;
  created_at?: string;
}

export enum AppMode {
  RUN = 'run',
  LOOP = 'loop',
}

export interface SettingsState {
  baseUrl: string;
  apiKey: string;
}
