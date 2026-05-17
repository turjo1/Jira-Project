/**
 * Metric Tile Component - displays a single KPI
 */

import React from 'react';
import './MetricTile.css';

export interface MetricTileProps {
  title: string;
  value: string;
  unit: string;
  comparison?: string;
  trend?: 'up' | 'down';
  onClick?: () => void;
}

export const MetricTile: React.FC<MetricTileProps> = ({
  title,
  value,
  unit,
  comparison,
  trend,
  onClick,
}) => {
  return (
    <button className="metric-tile" onClick={onClick}>
      <div className="metric-header">
        <span className="metric-title">{title}</span>
        <svg className="metric-icon" width="20" height="20" viewBox="0 0 20 20">
          <path d="M16 8l-8 8-4-4" stroke="currentColor" strokeWidth="2" fill="none" />
        </svg>
      </div>
      <div className="metric-value">
        <span className="value">{value}</span>
        {unit && <span className="unit">{unit}</span>}
      </div>
      {comparison && (
        <div className="metric-comparison">
          <span
            className={`comparison-text ${trend === 'down' ? 'positive' : 'negative'}`}
          >
            {trend === 'down' && '↓'} {comparison}
          </span>
        </div>
      )}
    </button>
  );
};
