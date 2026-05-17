/**
 * Main Dashboard Component
 */

import React, { useState, useEffect } from 'react';
import { MetricTile } from './MetricTile';
import { StatusDistribution } from './StatusDistribution';
import { RecentActivity } from './RecentActivity';
import { TeamInFlightLoad } from './TeamInFlightLoad';
import { apiClient } from '../api/client';
import './Dashboard.css';

interface MetricTile {
  title: string;
  value: string;
  unit: string;
  comparison?: string;
  trend?: 'up' | 'down';
}

interface DashboardData {
  team_id: string;
  metrics: MetricTile[];
  status_distribution: Record<string, any>;
  recent_activity: any[];
  last_synced: string;
}

export const Dashboard: React.FC<{ teamId: string }> = ({ teamId }) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSynced, setLastSynced] = useState<Date | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await apiClient.getDashboardMetrics(teamId) as DashboardData;
        setData(response);
        setLastSynced(new Date(response.last_synced));
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [teamId]);

  const handleRefresh = async () => {
    try {
      const response = await apiClient.getDashboardMetrics(teamId) as DashboardData;
      setData(response);
      setLastSynced(new Date(response.last_synced));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh');
    }
  };

  if (error) {
    return (
      <div className="dashboard-error">
        <p>{error}</p>
        <button onClick={handleRefresh}>Retry</button>
      </div>
    );
  }

  if (loading || !data) {
    return <div className="dashboard-loading">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="header-title">
          <h1>Team performance</h1>
          <p>Real-time view of velocity, bottlenecks, and quality</p>
        </div>
        <div className="header-actions">
          <div className="sync-status">
            {lastSynced && (
              <span>
                Synced {formatTimeAgo(lastSynced)} ago
              </span>
            )}
          </div>
          <button className="refresh-btn" onClick={handleRefresh}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        {data.metrics.map((metric, idx) => (
          <MetricTile key={idx} {...metric} />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="content-grid">
        <div className="content-left">
          <StatusDistribution distribution={data.status_distribution} />
          <TeamInFlightLoad teamId={teamId} />
        </div>
        <div className="content-right">
          <RecentActivity activity={data.recent_activity} />
        </div>
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
