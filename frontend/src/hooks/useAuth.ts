/**
 * useAuth Hook - Simplified auth interface for components
 *
 * Provides easy access to auth state and methods.
 * Usage: const { token, isAuthenticated, login, logout } = useAuth();
 */

import { useAuthStore } from '../contexts/AuthContext';

export interface UseAuthReturn {
  token: string | null;
  userId: string | null;
  selectedTeamId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (token: string, userId: string) => void;
  logout: () => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
  setSelectedTeamId: (teamId: string) => void;
}

export function useAuth(): UseAuthReturn {
  const token = useAuthStore((state) => state.token);
  const userId = useAuthStore((state) => state.userId);
  const selectedTeamId = useAuthStore((state) => state.selectedTeamId);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);
  const setToken = useAuthStore((state) => state.setToken);
  const clearToken = useAuthStore((state) => state.clearToken);
  const isAuthenticatedFn = useAuthStore((state) => state.isAuthenticated);
  const setError = useAuthStore((state) => state.setError);
  const setLoading = useAuthStore((state) => state.setLoading);
  const setSelectedTeamIdFn = useAuthStore((state) => state.setSelectedTeamId);

  return {
    token,
    userId,
    selectedTeamId,
    isAuthenticated: isAuthenticatedFn(),
    isLoading,
    error,
    login: (token: string, userId: string) => setToken(token, userId),
    logout: () => clearToken(),
    setError,
    setLoading,
    setSelectedTeamId: setSelectedTeamIdFn,
  };
}
