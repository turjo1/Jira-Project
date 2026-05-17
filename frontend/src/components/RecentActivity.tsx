/**
 * Recent Activity Component - shows activity feed
 */

import React from 'react';
import './RecentActivity.css';

interface ActivityItem {
  timestamp: string;
  actor_name: string;
  actor_initials: string;
  action: string;
  ticket_key: string;
  to_status: string;
}

interface RecentActivityProps {
  activity: ActivityItem[];
}

export const RecentActivity: React.FC<RecentActivityProps> = ({ activity }) => {
  return (
    <div className="recent-activity">
      <div className="activity-header">
        <h3>Recent activity</h3>
        <span className="live-indicator">● live</span>
      </div>

      <div className="activity-list">
        {activity.length === 0 ? (
          <div className="activity-empty">No recent activity</div>
        ) : (
          activity.map((item, idx) => (
            <div key={idx} className="activity-item">
              <span className="activity-time">
                {formatTimeAgo(new Date(item.timestamp))}
              </span>

              <div className="activity-avatar">
                <span className="avatar-initials">{item.actor_initials}</span>
              </div>

              <div className="activity-content">
                <span className="actor-name">{item.actor_name}</span>
                <span className="activity-text">
                  {item.action} <span className="ticket-key">{item.ticket_key}</span> to{' '}
                  <span className="status-badge">{item.to_status}</span>
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return `${seconds}s`;
  if (minutes < 60) return `${minutes}m`;
  if (hours < 24) return `${hours}h`;
  return `${days}d`;
}
