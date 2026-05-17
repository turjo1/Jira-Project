/**
 * Login Page - Jira OAuth2 login
 *
 * Provides "Login with Jira" button that initiates OAuth2 flow.
 * On click, calls POST /auth/jira and redirects to the returned auth_url.
 */

import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../api/client';
import './Login.css';

interface LoginProps {
  /** Pre-populated error message (e.g. from a failed OAuth callback) */
  callbackError?: string;
}

export function Login({ callbackError }: LoginProps) {
  const { setLoading, setError, error } = useAuth();
  const [busy, setBusy] = useState(false);

  const handleLoginClick = async () => {
    try {
      setBusy(true);
      setLoading(true);
      setError(null);

      const { auth_url } = await apiClient.startOAuth();

      if (!auth_url) {
        throw new Error('No authorization URL returned from backend');
      }

      window.location.href = auth_url;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed. Please try again.';
      setError(msg);
      setLoading(false);
      setBusy(false);
    }
  };

  const displayError = callbackError ?? error;

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>WorkPulse</h1>
          <p>Jira Team Performance Analytics</p>
        </div>

        <div className="login-content">
          <button
            className="login-button"
            onClick={handleLoginClick}
            disabled={busy}
          >
            {busy ? 'Redirecting to Google…' : 'Login with Google'}
          </button>

          {displayError && (
            <div className="login-error" role="alert">
              <p>{displayError}</p>
              <button
                className="login-retry-button"
                onClick={() => {
                  setError(null);
                  setBusy(false);
                }}
              >
                Try Again
              </button>
            </div>
          )}

          <div className="login-info">
            <h3>How it works</h3>
            <ol>
              <li>Click the button to authenticate with your Google account</li>
              <li>Google will ask you to confirm access permissions</li>
              <li>You will be redirected to the dashboard with full access</li>
            </ol>
          </div>
        </div>

        <div className="login-footer">
          <p>
            We use Google OAuth2 for secure sign-in. Your Google password is never
            stored or transmitted through this application.
          </p>
        </div>
      </div>
    </div>
  );
}
