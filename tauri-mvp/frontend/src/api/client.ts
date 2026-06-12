/**
 * API Client for Writer Backend (FastAPI + SQLite).
 * Typed fetch wrappers matching the backend's /entries contract.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export interface Entry {
  id: string;
  title: string;
  body: string;
  entry_type: string;
  created_at: string | null;
  updated_at: string | null;
  tags: string[];
  project_id: string | null;
  chapter_id: string | null;
  sequence_order: number | null;
  archived_at: string | null;
  curation_status: string;
}

export interface EntryCreate {
  title?: string;
  body?: string;
  entry_type?: string;
  tags?: string[];
}

export interface EntryUpdate {
  title: string;
  body: string;
  tags?: string[];
}

export interface ApiError {
  detail: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      throw new Error(error.detail);
    }
    if (response.status === 204) {
      return null as T;
    }
    return response.json();
  }

  async healthCheck(): Promise<{ message: string; version: string }> {
    const response = await fetch(`${this.baseUrl}/`);
    return this.handleResponse(response);
  }

  async listEntries(limit = 100, includeArchived = false): Promise<Entry[]> {
    const params = new URLSearchParams({
      limit: String(limit),
      include_archived: String(includeArchived),
    });
    const response = await fetch(`${this.baseUrl}/entries?${params}`);
    return this.handleResponse(response);
  }

  async getEntry(id: string): Promise<Entry> {
    const response = await fetch(`${this.baseUrl}/entries/${id}`);
    return this.handleResponse(response);
  }

  async createEntry(entry: EntryCreate): Promise<Entry> {
    const response = await fetch(`${this.baseUrl}/entries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    });
    return this.handleResponse(response);
  }

  async updateEntry(id: string, entry: EntryUpdate): Promise<Entry> {
    const response = await fetch(`${this.baseUrl}/entries/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    });
    return this.handleResponse(response);
  }

  async deleteEntry(id: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/entries/${id}`, {
      method: 'DELETE',
    });
    return this.handleResponse(response);
  }
}

export const apiClient = new ApiClient();
export { ApiClient };
