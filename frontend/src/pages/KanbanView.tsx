/**
 * Kanban View - 4-column board (Todo, InProgress, Review, Done)
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { DeveloperModal } from '../components/DeveloperModal';
import './KanbanView.css';

interface Ticket {
  id: string;
  key: string;
  summary: string;
  status: string;
  assignee?: {
    id: string;
    name: string;
  };
  cycle_time?: number;
}

interface TicketsResponse {
  tickets: Ticket[];
}

const STATUSES = ['Todo', 'InProgress', 'Review', 'Done'];

export const KanbanView: React.FC<{ teamId: string }> = ({ teamId }) => {
  const [tickets, setTickets] = useState<Record<string, Ticket[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDeveloper, setSelectedDeveloper] = useState<string | null>(null);

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getTeamTickets(teamId, {
          limit: 1000,
        }) as TicketsResponse;

        // Group tickets by status
        const grouped: Record<string, Ticket[]> = {};
        STATUSES.forEach((status) => {
          grouped[status] = [];
        });

        response.tickets.forEach((ticket) => {
          const status = ticket.status;
          if (status in grouped) {
            grouped[status].push(ticket);
          }
        });

        setTickets(grouped);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tickets');
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, [teamId]);

  if (error) {
    return (
      <div className="kanban-view error">
        <p>{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="kanban-view loading">
        <p>Loading board...</p>
      </div>
    );
  }

  return (
    <div className="kanban-view">
      <div className="kanban-columns">
        {STATUSES.map((status) => {
          const statusTickets = tickets[status] || [];
          const displayStatus = status
            .replace(/([A-Z])/g, ' $1')
            .trim()
            .split(' ')
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');

          return (
            <div key={status} className="kanban-column">
              <div className="column-header">
                <h3>{displayStatus}</h3>
                <span className="column-count">{statusTickets.length}</span>
              </div>
              <div className="cards-container">
                {statusTickets.length === 0 ? (
                  <div className="no-cards">No tickets</div>
                ) : (
                  statusTickets.map((ticket) => (
                    <div key={ticket.id} className="card">
                      <div className="card-header">
                        <span className="key">{ticket.key}</span>
                        {ticket.cycle_time !== null && ticket.cycle_time !== undefined && (
                          <span className="cycle-badge">
                            {ticket.cycle_time.toFixed(1)}d
                          </span>
                        )}
                      </div>
                      <p className="summary">{ticket.summary}</p>
                      {ticket.assignee && (
                        <button
                          className="assignee-avatar"
                          onClick={() => setSelectedDeveloper(ticket.assignee!.id)}
                          title={ticket.assignee.name}
                        >
                          {ticket.assignee.name
                            .split(' ')
                            .map((n) => n[0])
                            .join('')}
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {selectedDeveloper && (
        <DeveloperModal
          devId={selectedDeveloper}
          onClose={() => setSelectedDeveloper(null)}
        />
      )}
    </div>
  );
};
