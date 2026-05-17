/**
 * Developer Modal - Shows developer detail and performance stats
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import './DeveloperModal.css';

interface DeveloperMetrics {
  avg_cycle_time?: number;
  tickets_resolved: number;
  bounce_contribution: number;
  current_in_progress: number;
}

interface Developer {
  id: string;
  name: string;
  email: string;
  metrics: DeveloperMetrics;
}

export const DeveloperModal: React.FC<{
  devId: string;
  onClose: () => void;
}> = ({ devId, onClose }) => {
  const [developer, setDeveloper] = useState<Developer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDeveloper = async () => {
      try {
        setLoading(true);
        setError(null);
        const dev = await apiClient.getDeveloper(devId) as Developer;
        setDeveloper(dev);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load developer');
      } finally {
        setLoading(false);
      }
    };

    fetchDeveloper();
  }, [devId]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleBackdropClick}>
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} title="Close">
          ✕
        </button>

        {loading ? (
          <div className="modal-loading">Loading developer info...</div>
        ) : error ? (
          <div className="modal-error">{error}</div>
        ) : developer ? (
          <div className="developer-detail">
            <div className="developer-header">
              <div className="avatar-placeholder">
                {developer.name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')}
              </div>
              <div className="developer-info">
                <h2>{developer.name}</h2>
                <p className="email">{developer.email}</p>
              </div>
            </div>

            <div className="metrics-section">
              <h3>Performance Metrics</h3>
              <div className="metrics-grid">
                <div className="metric">
                  <label>Avg Cycle Time</label>
                  <span className="value">
                    {developer.metrics.avg_cycle_time !== undefined
                      ? `${developer.metrics.avg_cycle_time.toFixed(1)}d`
                      : '—'}
                  </span>
                </div>
                <div className="metric">
                  <label>Tickets Resolved</label>
                  <span className="value">{developer.metrics.tickets_resolved}</span>
                </div>
                <div className="metric">
                  <label>Bounce Contribution</label>
                  <span className="value">
                    {(developer.metrics.bounce_contribution * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="metric">
                  <label>In Progress</label>
                  <span className="value">{developer.metrics.current_in_progress}</span>
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn-primary">View all tickets</button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
