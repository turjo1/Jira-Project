import { useEffect, useState } from 'react';
import { Dashboard, TeamSelector } from './components';
import { Login, TableView, KanbanView } from './pages';
import { useAuth } from './hooks/useAuth';
import { initializeAuth } from './contexts/AuthContext';
import { apiClient } from './api/client';
import './App.css';

type ViewType = 'dashboard' | 'table' | 'kanban';

function App() {
  const { isAuthenticated, login, setLoading, selectedTeamId, setSelectedTeamId } = useAuth();
  const [isInitializing, setIsInitializing] = useState(true);
  const [callbackError, setCallbackError] = useState<string | undefined>();
  const [autoSelectTeamId, setAutoSelectTeamId] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<ViewType>('dashboard');

  useEffect(() => {
    const boot = async () => {
      // DEV MODE: Auto-login for development/testing
      // TODO: Remove this and implement proper Google OAuth when ready
      const testToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIn0.test';
      login(testToken, 'test-user-123');

      setIsInitializing(false);
    };

    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isInitializing) {
    return (
      <div className="app">
        <div className="app-loading">
          <p>Loading…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login callbackError={callbackError} />;
  }

  // Auto-select the first team if none is selected yet
  useEffect(() => {
    if (selectedTeamId || autoSelectTeamId) return;

    const autoSelect = async () => {
      try {
        const response = await apiClient.getTeams() as Array<{ id: string; name: string }>;
        if (Array.isArray(response) && response.length > 0) {
          const firstTeamId = response[0].id;
          setAutoSelectTeamId(firstTeamId);
          setSelectedTeamId(firstTeamId);
        }
      } catch (err) {
        console.error('Failed to auto-select first team:', err);
      }
    };

    autoSelect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId]);

  const activeTeamId = selectedTeamId || autoSelectTeamId;

  return (
    <div className="app">
      <div className="app-header">
        <TeamSelector
          selectedTeamId={activeTeamId}
          onSelectTeam={setSelectedTeamId}
        />
      </div>
      {activeTeamId ? (
        <div className="app-main">
          <div className="view-switcher">
            <button
              className={`view-btn ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentView('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`view-btn ${currentView === 'table' ? 'active' : ''}`}
              onClick={() => setCurrentView('table')}
            >
              Table
            </button>
            <button
              className={`view-btn ${currentView === 'kanban' ? 'active' : ''}`}
              onClick={() => setCurrentView('kanban')}
            >
              Kanban
            </button>
          </div>
          <div className="view-container">
            {currentView === 'dashboard' && <Dashboard teamId={activeTeamId} />}
            {currentView === 'table' && <TableView teamId={activeTeamId} />}
            {currentView === 'kanban' && <KanbanView teamId={activeTeamId} />}
          </div>
        </div>
      ) : (
        <div className="app-loading">
          <p>Loading teams…</p>
        </div>
      )}
    </div>
  );
}

export default App;
