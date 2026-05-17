/**
 * Team In-Flight Load Component - shows team members and their in-flight work
 */

import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import './TeamInFlightLoad.css';

interface TeamMember {
  name: string;
  initials: string;
  in_flight_count: number;
}

interface TeamInFlightLoadProps {
  teamId: string;
}

interface JiraTicket {
  id: string;
  key: string;
  summary: string;
  assignee?: {
    name: string;
    avatarUrl?: string;
  } | null;
  status: string;
}

export const TeamInFlightLoad: React.FC<TeamInFlightLoadProps> = ({ teamId }) => {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!teamId) {
      setMembers([]);
      setLoading(false);
      return;
    }

    const fetchTeamMembers = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch in-progress tickets for the team
        const response = await apiClient.getTeamTickets(teamId, { status: 'InProgress' }) as { tickets: JiraTicket[] };
        const tickets = response.tickets || [];

        // Group tickets by assignee and calculate initials
        const memberMap = new Map<string, { count: number; initials: string }>();

        tickets.forEach((ticket) => {
          const assigneeName = ticket.assignee?.name || 'Unassigned';
          const existing = memberMap.get(assigneeName) || { count: 0, initials: '' };

          if (!existing.initials) {
            // Calculate initials from name (first letter of each word)
            const initials = assigneeName
              .split(' ')
              .map((word) => word[0])
              .join('')
              .toUpperCase()
              .slice(0, 2);
            existing.initials = initials;
          }

          existing.count += 1;
          memberMap.set(assigneeName, existing);
        });

        // Convert to array and sort by ticket count (descending)
        const memberList: TeamMember[] = Array.from(
          memberMap,
          ([name, { count, initials }]) => ({
            name,
            initials,
            in_flight_count: count,
          })
        ).sort((a, b) => b.in_flight_count - a.in_flight_count);

        setMembers(memberList);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load team members';
        setError(errorMessage);
        setMembers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTeamMembers();
  }, [teamId]);

  if (loading) {
    return (
      <div className="team-in-flight">
        <h3>Team in-flight load</h3>
        <div className="team-members">
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="team-in-flight">
        <h3>Team in-flight load</h3>
        <div className="team-members error">
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="team-in-flight">
      <h3>Team in-flight load</h3>
      <div className="team-members">
        {members.length === 0 ? (
          <p>No one working on tickets</p>
        ) : (
          members.map((member) => (
            <button key={member.name} className="team-member" title={member.name}>
              <div className="member-avatar">
                <span className="member-initials">{member.initials}</span>
              </div>
              <div className="member-info">
                <span className="member-name">{member.name}</span>
                <span className="member-load">{member.in_flight_count} in flight</span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
};
