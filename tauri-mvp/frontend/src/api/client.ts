/**
 * API Client for the Living to Tell backend (FastAPI + SQLite).
 * Typed fetch wrappers matching the backend's /entries contract.
 */

import { apiFetch, handleResponse } from './base'

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

class ApiClient {
  constructor(_baseUrl?: string) {}

  async healthCheck(): Promise<{ message: string; version: string }> {
    const response = await apiFetch('/health');
    return handleResponse(response);
  }

  async listEntries(limit = 100, includeArchived = false): Promise<Entry[]> {
    const params = new URLSearchParams({
      limit: String(limit),
      include_archived: String(includeArchived),
    });
    const response = await apiFetch(`/api/articles?${params}`);
    return handleResponse(response);
  }

  async getEntry(id: string): Promise<Entry> {
    const response = await apiFetch(`/api/articles/${id}`);
    return handleResponse(response);
  }

  async createEntry(entry: EntryCreate): Promise<Entry> {
    const response = await apiFetch('/api/articles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    });
    return handleResponse(response);
  }

  async updateEntry(id: string, entry: EntryUpdate): Promise<Entry> {
    const response = await apiFetch(`/api/articles/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entry),
    });
    return handleResponse(response);
  }

  async deleteEntry(id: string): Promise<void> {
    const response = await apiFetch(`/api/articles/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  }
}

export const apiClient = new ApiClient();
export { ApiClient };
