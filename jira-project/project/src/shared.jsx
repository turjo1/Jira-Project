/* shared components: Avatar, StatusBadge, Sparkline, etc. */

const { useState, useEffect, useRef, useMemo, useCallback } = React;

const STATUS_LABELS = {
  todo: 'To Do',
  in_progress: 'In Progress',
  qa: 'In QA',
  done: 'Done',
};
const STATUS_COLORS = {
  todo: '#9CA3AF',
  in_progress: 'var(--primary)',
  qa: 'var(--role-qa)',
  done: 'var(--success)',
};
const ROLE_LABELS = { dev: 'Developer', qa: 'QA', po: 'Product' };

function cls(...args) { return args.filter(Boolean).join(' '); }
function fmtDate(d) {
  if (!d) return '—';
  const dt = new Date(d);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
function fmtTime(d) {
  const dt = new Date(d);
  return dt.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

function Avatar({ user, size = '', ring = false }) {
  if (!user) return null;
  return (
    <span className={cls('avatar', size, user.role)} title={user.name}>
      {user.initials}
      {ring && <span className={cls('avatar__ring', user.role)}></span>}
    </span>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={cls('badge', `status-${status}`)}>
      <span className="dot"></span>
      {STATUS_LABELS[status]}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const label = { critical: 'Critical', high: 'High', med: 'Medium', low: 'Low' }[priority];
  return <span className={cls('badge', `priority-${priority}`)}>{label}</span>;
}

function RolePill({ role }) {
  return <span className={cls('role-pill', role)}>{ROLE_LABELS[role]}</span>;
}

/* Sparkline: tiny SVG line + area, no axes */
function Sparkline({ data, color = 'var(--primary)', height = 32, width = 78, fill = true }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = (max - min) || 1;
  const stepX = width / (data.length - 1);
  const points = data.map((v, i) => {
    const x = i * stepX;
    const y = height - ((v - min) / range) * (height - 6) - 3;
    return [x, y];
  });
  const path = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `${path} L${width},${height} L0,${height} Z`;
  const last = points[points.length - 1];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="tile__spark">
      {fill && (
        <path d={area} fill={color} opacity="0.10" />
      )}
      <path d={path} stroke={color} strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="2.5" fill={color} />
    </svg>
  );
}

/* helper: clamp + heatmap class for dwell */
function heatClass(days, kind = 'dwell') {
  if (kind === 'dwell') {
    if (days < 2) return '';
    if (days < 5) return 'warn';
    return 'bad';
  }
  return '';
}
function laneHeat(avgDays) {
  if (avgDays < 1.5) return '';
  if (avgDays < 3)   return 'heat-1';
  if (avgDays < 4.5) return 'heat-2';
  if (avgDays < 6)   return 'heat-3';
  return 'heat-4';
}

/* Icons (inline SVG, currentColor) */
const Icon = {
  Dashboard: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="1.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="8.5" y="1.5" width="6" height="3" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="8.5" y="5.5" width="6" height="9" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="1.5" y="8.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.4"/></svg>,
  Board: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="1.5" width="3.5" height="13" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="6.25" y="1.5" width="3.5" height="9" rx="1" stroke="currentColor" strokeWidth="1.4"/><rect x="11" y="1.5" width="3.5" height="6" rx="1" stroke="currentColor" strokeWidth="1.4"/></svg>,
  Table: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="2.5" width="13" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.4"/><path d="M1.5 6.5h13M1.5 10h13M6 6.5v7" stroke="currentColor" strokeWidth="1.4"/></svg>,
  Refresh: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4.5A6 6 0 0 1 13.8 5M14 2.5V5h-2.5M14 11.5A6 6 0 0 1 2.2 11M2 13.5V11h2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Gear: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.4" stroke="currentColor" strokeWidth="1.4"/><path d="M8 1.5v1.6M8 12.9v1.6M14.5 8h-1.6M3.1 8H1.5M12.6 3.4l-1.13 1.13M4.5 11.5l-1.1 1.1M12.6 12.6l-1.13-1.13M4.5 4.5L3.4 3.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>,
  Search: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4"/><path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>,
  Close: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>,
  Chevron: () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 3.5L5 6.5l3-3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Filter: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M1.5 3.5h13l-5 6v4l-3-1.5v-2.5l-5-6z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>,
  ArrowDown: () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M5 1v7m0 0l-3-3m3 3l3-3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  ArrowUp: () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M5 9V2m0 0L2 5m3-3l3 3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Bounce: () => <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 3h4a2 2 0 1 1 0 4H4M4 5L2 3l2-2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Plus: () => <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1.5v9M1.5 6h9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>,
  Copy: () => <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><rect x="4.5" y="4.5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.4"/><path d="M9.5 4.5V2.5a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1H4.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>,
  More: () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="3" cy="7" r="1.1" fill="currentColor"/><circle cx="7" cy="7" r="1.1" fill="currentColor"/><circle cx="11" cy="7" r="1.1" fill="currentColor"/></svg>,
  Trash: () => <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M2.5 3.5h9M5 3.5V2.5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1M3.5 3.5l.7 8a1 1 0 0 0 1 .9h3.6a1 1 0 0 0 1-.9l.7-8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Pencil: () => <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M2 12l1-3 6.5-6.5a1.4 1.4 0 0 1 2 2L5 11l-3 1z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg>,
  Check: () => <svg width="12" height="12" viewBox="0 0 14 14" fill="none"><path d="M2 7l3 3 7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>,
  Eye: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M1 8s2.5-4.5 7-4.5S15 8 15 8s-2.5 4.5-7 4.5S1 8 1 8z" stroke="currentColor" strokeWidth="1.4"/><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.4"/></svg>,
  EyeOff: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 2l12 12M6.5 6.5a2 2 0 0 0 2.8 2.8M9.8 9.7c-.55.2-1.15.3-1.8.3-4.5 0-7-4.5-7-4.5a13 13 0 0 1 3-3.4M5.5 4.2A7.5 7.5 0 0 1 8 3.5c4.5 0 7 4.5 7 4.5a13.6 13.6 0 0 1-2 2.6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>,
  Key: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="5.5" cy="10.5" r="3" stroke="currentColor" strokeWidth="1.4"/><path d="M7.6 8.4l6-6M11 5l1.5 1.5M13 3l1.5 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>,
  Sparkles: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 1.5l1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3zM12 8l.7 2.1 2.1.7-2.1.7L12 13.6l-.7-2.1-2.1-.7 2.1-.7L12 8z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></svg>,
  At: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3"/><path d="M10.5 8v1.4c0 1 .8 1.6 1.6 1.6 1.3 0 2.1-1.1 2.1-2.5A6 6 0 1 0 11.5 13" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>,
  Send: () => <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 8l12-6-3 13-3.5-5L2 8zm5.5 2L11 5.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" strokeLinecap="round"/></svg>,
};

Object.assign(window, {
  Avatar, StatusBadge, PriorityBadge, RolePill, Sparkline,
  STATUS_LABELS, STATUS_COLORS, ROLE_LABELS, Icon,
  cls, fmtDate, fmtTime, heatClass, laneHeat,
});
