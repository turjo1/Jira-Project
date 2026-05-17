/**
 * Status Distribution Component - shows workflow distribution
 */

import React from 'react';
import './StatusDistribution.css';

interface StatusItem {
  status: string;
  count: number;
  avg_dwell_days: number;
}

interface StatusDistributionProps {
  distribution: Record<string, StatusItem>;
}

export const StatusDistribution: React.FC<StatusDistributionProps> = ({
  distribution,
}) => {
  const statuses = Object.entries(distribution);
  const totalTickets = statuses.reduce((sum, [_, item]) => sum + item.count, 0);

  // Color mapping for statuses
  const statusColors: Record<string, string> = {
    'To Do': '#f3f4f6',
    'In Progress': '#fbbf24',
    'In QA': '#60a5fa',
    'Done': '#10b981',
  };

  return (
    <div className="status-distribution">
      <div className="status-header">
        <h3>Workflow distribution</h3>
        <span className="status-subtitle">All {totalTickets} tickets in this sprint</span>
      </div>

      {/* Status Chart (simplified pie chart) */}
      <div className="status-chart">
        <div className="status-bars">
          {statuses.map(([status, item]) => {
            const percentage = (item.count / totalTickets) * 100;
            return (
              <div key={status} className="status-bar" title={status}>
                <div
                  className="bar-fill"
                  style={{
                    width: `${percentage}%`,
                    backgroundColor: statusColors[status] || '#d1d5db',
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Status Details */}
      <div className="status-details">
        {statuses.map(([status, item]) => (
          <div key={status} className="status-detail-item">
            <div className="detail-status">
              <div
                className="status-dot"
                style={{
                  backgroundColor: statusColors[status] || '#d1d5db',
                }}
              />
              <span className="status-name">{status}</span>
            </div>
            <div className="detail-count">
              <span className="count">{item.count}</span>
              <span className="dwell-time">
                · avg {item.avg_dwell_days.toFixed(1)}d dwell
              </span>
            </div>
          </div>
        ))}
      </div>

      <button className="open-board-btn">
        Open board →
      </button>
    </div>
  );
};
