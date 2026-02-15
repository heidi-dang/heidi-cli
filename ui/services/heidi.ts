import { Agent, LoopRequest, RunDetails, RunRequest, RunResponse, RunSummary, SettingsState } from '../types';

const DEFAULT_BASE_URL = '/api';

export const getSettings = (): SettingsState => {
  return {
    baseUrl: localStorage.getItem('HEIDI_BASE_URL') || DEFAULT_BASE_URL,
    apiKey: localStorage.getItem('HEIDI_API_KEY') || '',
  };
};

export const saveSettings = (settings: SettingsState) => {
  localStorage.setItem('HEIDI_BASE_URL', settings.baseUrl);
  localStorage.setItem('HEIDI_API_KEY', settings.apiKey);
};

const getHeaders = (customApiKey?: string) => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  // NOTE: Backend currently has no auth. Sending this header might cause CORS issues if not allowed.
  // Uncomment when backend supports X-Heidi-Key.
  /*
  const { apiKey } = getSettings();
  const key = customApiKey !== undefined ? customApiKey : apiKey;
  if (key) {
    headers['X-Heidi-Key'] = key;
  }
  */
  
  return headers;
};

const getBaseUrl = (customUrl?: string) => {
  let url = customUrl || getSettings().baseUrl;
  // Remove trailing slash if present
  return url.replace(/\/$/, '');
};

export const api = {
  health: async (customBaseUrl?: string, customApiKey?: string): Promise<{ status: string }> => {
    const url = getBaseUrl(customBaseUrl);
    const headers = getHeaders(customApiKey);
    const res = await fetch(`${url}/health`, { headers });
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  getAgents: async (): Promise<Agent[]> => {
    try {
      const res = await fetch(`${getBaseUrl()}/agents`, { headers: getHeaders() });
      if (!res.ok) return [];
      return res.json();
    } catch (e) {
      console.warn("Could not fetch agents", e);
      return [];
    }
  },

  startRun: async (payload: RunRequest): Promise<RunResponse> => {
    // Spec: POST /run { "prompt": "text", "executor": "copilot", "workdir": null }
    const body = {
      prompt: payload.prompt,
      executor: payload.executor || 'copilot',
      workdir: payload.workdir || null,
      // Optional: Include dry_run only if true
      ...(payload.dry_run ? { dry_run: true } : {})
    };

    const res = await fetch(`${getBaseUrl()}/run`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Failed to start run: ${errText}`);
    }
    return res.json();
  },

  startLoop: async (payload: LoopRequest): Promise<RunResponse> => {
    // Spec: POST /loop { "task": "text", "executor": "copilot", "max_retries": 2, "workdir": null }
    const body = {
      task: payload.task,
      executor: payload.executor || 'copilot',
      max_retries: payload.max_retries ?? 2,
      workdir: payload.workdir || null,
      // Optional: Include dry_run only if true
      ...(payload.dry_run ? { dry_run: true } : {})
    };

    const res = await fetch(`${getBaseUrl()}/loop`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Failed to start loop: ${errText}`);
    }
    return res.json();
  },

  chat: async (message: string, executor: string = 'copilot'): Promise<{ response: string }> => {
    const res = await fetch(`${getBaseUrl()}/chat`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ message, executor }),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Chat failed: ${errText}`);
    }
    return res.json();
  },

  cancelRun: async (runId: string): Promise<void> => {
    // Best effort cancellation
    try {
      await fetch(`${getBaseUrl()}/runs/${runId}/cancel`, {
        method: 'POST',
        headers: getHeaders(),
      });
    } catch (e) {
      console.warn("Failed to cancel run via backend", e);
    }
  },

  getRuns: async (limit = 10): Promise<RunSummary[]> => {
    const res = await fetch(`${getBaseUrl()}/runs?limit=${limit}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch runs');
    return res.json();
  },

  getRun: async (runId: string): Promise<RunDetails> => {
    const res = await fetch(`${getBaseUrl()}/runs/${runId}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch run details');
    return res.json();
  },

  getStreamUrl: (runId: string): string => {
    return(`${getBaseUrl()}/runs/${runId}/stream`);
  }
};