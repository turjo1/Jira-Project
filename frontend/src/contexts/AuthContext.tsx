/**
 * Auth Context - JWT token management using Zustand
 *
 * Manages authentication state, token persistence, and auth status checks.
 * Persists token to localStorage so it survives page refresh.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const STORAGE_KEY = 'jira_token';
const USER_ID_KEY = 'jira_user_id';

export interface AuthState {
  token: string | null;
  userId: string | null;
  selectedTeamId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setToken: (token: string, userId: string) => void;
  getToken: () => string | null;
  clearToken: () => void;
  isAuthenticated: () => boolean;
  setError: (error: string | null) => void;
  setLoading: (isLoading: boolean) => void;
  setSelectedTeamId: (teamId: string) => void;
}

/**
 * useAuthStore - Zustand store for auth state
 *
 * Persists token and userId to localStorage automatically via persist middleware.
 * Key: 'auth-store'
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      userId: null,
      selectedTeamId: null,
      isLoading: false,
      error: null,

      setToken: (token: string, userId: string) => {
        set({ token, userId, error: null });
      },

      getToken: () => {
        return get().token;
      },

      clearToken: () => {
        set({ token: null, userId: null, selectedTeamId: null, error: null });
      },

      isAuthenticated: () => {
        const { token } = get();
        return token !== null && token !== '';
      },

      setError: (error: string | null) => {
        set({ error });
      },

      setLoading: (isLoading: boolean) => {
        set({ isLoading });
      },

      setSelectedTeamId: (teamId: string) => {
        set({ selectedTeamId: teamId });
      },
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        token: state.token,
        userId: state.userId,
        selectedTeamId: state.selectedTeamId,
      }),
    }
  )
);

/**
 * Check if a JWT token is expired
 * JWT format: header.payload.signature
 * Payload contains exp (expiration time in seconds since epoch)
 */
export function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return true;
    }

    // Decode payload (add padding if needed)
    const payload = JSON.parse(
      atob(parts[1] + '=='.slice(0, (4 - (parts[1].length % 4)) % 4))
    );

    if (!payload.exp) {
      return false; // No expiration, assume valid
    }

    // Check if token expires in less than 1 minute
    const expiresAt = payload.exp * 1000; // Convert to milliseconds
    const now = Date.now();
    return now >= expiresAt - 60000; // 60 second buffer
  } catch (error) {
    console.error('Failed to decode token:', error);
    return true;
  }
}

/**
 * Initialize auth from localStorage on app load
 * Call this in App.tsx useEffect
 */
export function initializeAuth(): void {
  const token = localStorage.getItem(STORAGE_KEY);
  const userId = localStorage.getItem(USER_ID_KEY);

  if (token && userId) {
    if (!isTokenExpired(token)) {
      useAuthStore.setState({ token, userId });
    } else {
      // Token expired, clear it
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(USER_ID_KEY);
      useAuthStore.setState({ token: null, userId: null });
    }
  }
}
