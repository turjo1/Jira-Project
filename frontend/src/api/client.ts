/**
 * API client for backend communication
 *
 * Automatically attaches JWT Bearer token to every authenticated request.
 * On 401 Unauthorized it clears the token and redirects to /login.
 */

import { useAuthStore } from '../contexts/AuthContext';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface ApiError {
  detail: string;
}

export interface AuthUrlResponse {
  auth_url: string;
  state: string;
}

export interface AuthResponse {
  access_token: string;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /** Read current JWT from the Zustand store (does not trigger re-render). */
  private getAuthToken(): string | null {
    return useAuthStore.getState().token;
  }

  /** Core fetch wrapper — adds Content-Type, Authorization, and 401 handling. */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getAuthToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });

    // 401 → clear auth state and redirect to login
    if (response.status === 401) {
      useAuthStore.setState({ token: null, userId: null });
      window.location.href = '/login';
      throw new Error('Unauthorized – redirecting to login');
    }

    if (!response.ok) {
      let errorDetail = `API Error: ${response.status}`;
      try {
        const body: ApiError = await response.json();
        errorDetail = body.detail ?? errorDetail;
      } catch {
        // ignore parse failure
      }
      throw new Error(errorDetail);
    }

    return response.json() as Promise<T>;
  }

  // -------------------------------------------------------------------------
  // Auth endpoints (unauthenticated — no Bearer token needed)
  // -------------------------------------------------------------------------

  /** POST /auth/jira — initiate Jira OAuth2 flow, returns redirect URL. */
  async startOAuth(): Promise<AuthUrlResponse> {
    return this.request<AuthUrlResponse>('/auth/jira', { method: 'POST' });
  }

  /** POST /auth/callback — exchange OAuth2 code for JWT. */
  async completeOAuth(code: string, state: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/callback', {
      method: 'POST',
      body: JSON.stringify({ code, state }),
    });
  }

  /** POST /auth/logout — revoke server-side session. */
  async logout(): Promise<void> {
    await this.request('/auth/logout', { method: 'POST' });
  }

  // -------------------------------------------------------------------------
  // Teams
  // -------------------------------------------------------------------------

  async getTeams(): Promise<Array<{ id: string; name: string }>> {
    return this.request('/teams');
  }

  async getTeam(teamId: string) {
    return this.request(`/teams/${teamId}`);
  }

  // -------------------------------------------------------------------------
  // Dashboard metrics  (new URL shape matching BACKEND-API.md)
  // -------------------------------------------------------------------------

  async getDashboardMetrics(teamId: string) {
    return this.request(`/teams/${teamId}/metrics`);
  }

  async getTeamTickets(teamId: string, options: {
    status?: string;
    limit?: number;
    skip?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  } = {}) {
    const params = new URLSearchParams();
    if (options.limit !== undefined) params.append('limit', String(options.limit));
    if (options.skip !== undefined) params.append('skip', String(options.skip));
    if (options.status) params.append('status', options.status);
    if (options.sort_by) params.append('sort_by', options.sort_by);
    if (options.sort_order) params.append('sort_order', options.sort_order);

    return this.request(`/teams/${teamId}/tickets?${params.toString()}`);
  }

  // -------------------------------------------------------------------------
  // Developers
  // -------------------------------------------------------------------------

  async getDeveloper(devId: string) {
    return this.request(`/developers/${devId}`);
  }
}

export const apiClient = new ApiClient();
