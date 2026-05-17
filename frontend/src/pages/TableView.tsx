/**
 * Table View - Sortable, filterable ticket table
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { DeveloperModal } from '../components/DeveloperModal';
import './TableView.css';

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
  updated_at: string;
}

interface TicketsResponse {
  tickets: Ticket[];
  total: number;
}

export const TableView: React.FC<{ teamId: string }> = ({ teamId }) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [sortBy, setSortBy] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedDeveloper, setSelectedDeveloper] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);

  const PAGE_SIZE = 10;

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getTeamTickets(teamId, {
          status: statusFilter || undefined,
          skip: (page - 1) * PAGE_SIZE,
          limit: PAGE_SIZE,
          sort_by: sortBy,
          sort_order: sortOrder,
        }) as TicketsResponse;

        setTickets(response.tickets || []);
        setTotalCount(response.total || 0);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load tickets');
        setTickets([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, [teamId, statusFilter, page, sortBy, sortOrder]);

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const hasNextPage = (page * PAGE_SIZE) < totalCount;
  const hasPrevPage = page > 1;

  if (error) {
    return (
      <div className="table-view error">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="table-view">
      <div className="table-controls">
        <div className="filter-group">
          <label htmlFor="status-filter">Filter by Status:</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All</option>
            <option value="Todo">Todo</option>
            <option value="InProgress">In Progress</option>
            <option value="Review">Review</option>
            <option value="Done">Done</option>
          </select>
        </div>
        <div className="info-text">
          {loading ? 'Loading...' : `${totalCount} tickets`}
        </div>
      </div>

      {loading && !tickets.length ? (
        <div className="table-loading">Loading tickets...</div>
      ) : tickets.length === 0 ? (
        <div className="table-empty">No tickets found</div>
      ) : (
        <>
          <div className="table-wrapper">
            <table className="tickets-table">
              <thead>
                <tr>
                  <th
                    className={sortBy === 'key' ? 'sorted' : ''}
                    onClick={() => handleSort('key')}
                    style={{ cursor: 'pointer' }}
                  >
                    Key {sortBy === 'key' && <span className="sort-icon">{sortOrder === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                  <th
                    className={sortBy === 'summary' ? 'sorted' : ''}
                    onClick={() => handleSort('summary')}
                    style={{ cursor: 'pointer' }}
                  >
                    Summary {sortBy === 'summary' && <span className="sort-icon">{sortOrder === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                  <th
                    className={sortBy === 'status' ? 'sorted' : ''}
                    onClick={() => handleSort('status')}
                    style={{ cursor: 'pointer' }}
                  >
                    Status {sortBy === 'status' && <span className="sort-icon">{sortOrder === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                  <th>Assignee</th>
                  <th
                    className={sortBy === 'cycle_time' ? 'sorted' : ''}
                    onClick={() => handleSort('cycle_time')}
                    style={{ cursor: 'pointer' }}
                  >
                    Cycle Time {sortBy === 'cycle_time' && <span className="sort-icon">{sortOrder === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                  <th
                    className={sortBy === 'updated_at' ? 'sorted' : ''}
                    onClick={() => handleSort('updated_at')}
                    style={{ cursor: 'pointer' }}
                  >
                    Last Updated {sortBy === 'updated_at' && <span className="sort-icon">{sortOrder === 'asc' ? '↑' : '↓'}</span>}
                  </th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td className="key-cell">{ticket.key}</td>
                    <td className="summary-cell">{ticket.summary}</td>
                    <td className="status-cell">
                      <span className={`status-badge status-${ticket.status.toLowerCase()}`}>
                        {ticket.status}
                      </span>
                    </td>
                    <td className="assignee-cell">
                      {ticket.assignee ? (
                        <button
                          className="assignee-link"
                          onClick={() => setSelectedDeveloper(ticket.assignee!.id)}
                          title={ticket.assignee.name}
                        >
                          {ticket.assignee.name}
                        </button>
                      ) : (
                        <span className="unassigned">Unassigned</span>
                      )}
                    </td>
                    <td className="cycle-time-cell">
                      {ticket.cycle_time !== null && ticket.cycle_time !== undefined
                        ? `${ticket.cycle_time.toFixed(1)}d`
                        : '—'}
                    </td>
                    <td className="updated-cell">
                      {new Date(ticket.updated_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button
              className="btn-prev"
              onClick={() => setPage(page - 1)}
              disabled={!hasPrevPage}
            >
              ← Prev
            </button>
            <span className="page-indicator">Page {page}</span>
            <button
              className="btn-next"
              onClick={() => setPage(page + 1)}
              disabled={!hasNextPage}
            >
              Next →
            </button>
          </div>
        </>
      )}

      {selectedDeveloper && (
        <DeveloperModal
          devId={selectedDeveloper}
          onClose={() => setSelectedDeveloper(null)}
        />
      )}
    </div>
  );
};
