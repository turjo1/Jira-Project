/**
 * Team Selector Component
 *
 * Dropdown to select which team's dashboard to view.
 * Fetches available teams from the API and persists selection to Zustand store.
 */

import { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import './TeamSelector.css';

interface Team {
  id: string;
  name: string;
}

export interface TeamSelectorProps {
  selectedTeamId: string | null;
  onSelectTeam: (teamId: string) => void;
}

export const TeamSelector: React.FC<TeamSelectorProps> = ({
  selectedTeamId,
  onSelectTeam,
}) => {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setLoading(true);
        const response = await apiClient.getTeams() as Team[];
        setTeams(Array.isArray(response) ? response : []);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load teams';
        setError(message);
        setTeams([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTeams();
  }, []);

  if (loading) {
    return (
      <div className="team-selector">
        <label htmlFor="team-select">Team:</label>
        <select id="team-select" disabled>
          <option>Loading teams...</option>
        </select>
      </div>
    );
  }

  if (error) {
    return (
      <div className="team-selector error">
        <label htmlFor="team-select">Team:</label>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (teams.length === 0) {
    return (
      <div className="team-selector">
        <label htmlFor="team-select">Team:</label>
        <select id="team-select" disabled>
          <option>No teams available</option>
        </select>
      </div>
    );
  }

  return (
    <div className="team-selector">
      <label htmlFor="team-select">Team:</label>
      <select
        id="team-select"
        value={selectedTeamId || ''}
        onChange={(e) => onSelectTeam(e.target.value)}
      >
        <option value="">Select a team...</option>
        {teams.map((team) => (
          <option key={team.id} value={team.id}>
            {team.name}
          </option>
        ))}
      </select>
    </div>
  );
};
