/* Dashboard view */
const { useState: useStateDash, useMemo: useMemoDash } = React;

function Dashboard({ data, onOpenUser, onOpenView }) {
  const { totals, statusAvg, bottleneck, cycleTrend, bounceTrend, openTrend, tickets, team } = data;

  // tile health logic
  const cycleHealth = totals.avgCycle <= 12 ? 'healthy' : totals.avgCycle <= 18 ? 'watch' : 'critical';
  const bounceHealth = totals.bounceRate <= 10 ? 'healthy' : totals.bounceRate <= 20 ? 'watch' : 'critical';
  const openHealth = totals.open <= 30 ? 'healthy' : totals.open <= 50 ? 'watch' : 'critical';

  // Status distribution counts
  const counts = { todo: 0, in_progress: 0, qa: 0, done: 0 };
  for (const t of tickets) counts[t.status]++;
  const totalCount = tickets.length;

  // Activity feed (last 10 transitions)
  const events = useMemoDash(() => {
    const evs = [];
    for (const t of tickets) {
      for (let i = 1; i < t.history.length; i++) {
        evs.push({
          at: t.history[i].at,
          ticket: t,
          from: t.history[i-1].status,
          to: t.history[i].status,
          by: t.history[i].by,
        });
      }
    }
    evs.sort((a,b) => b.at - a.at);
    return evs.slice(0, 9);
  }, [tickets]);

  function userById(id) { return team.find(u => u.id === id); }
  function relTime(d) {
    const diff = (new Date('2026-05-16T14:32:00Z') - new Date(d)) / 60000;
    if (diff < 60) return `${Math.round(diff)}m`;
    if (diff < 60*24) return `${Math.round(diff/60)}h`;
    return `${Math.round(diff/60/24)}d`;
  }

  // Bottleneck callout
  const bottleneckAvg = statusAvg[bottleneck];

  return (
    <div className="dashboard">
      {/* Metric tiles */}
      <div className="dash-grid">
        <div className={cls('tile', openHealth)} onClick={() => onOpenView('table')} role="button" tabIndex={0}>
          <span className="tile__indicator"></span>
          <div className="tile__title">Open tickets</div>
          <div className="tile__value">
            <span className="num">{totals.open}</span>
            <span className="unit">of {totals.open + totals.done}</span>
          </div>
          <div className={cls('tile__trend', openTrend[7] < openTrend[0] ? 'good' : 'bad')}>
            <Icon.ArrowDown /> {openTrend[0] - openTrend[7]} this quarter
          </div>
          <Sparkline data={openTrend} color="var(--primary)" />
        </div>

        <div className={cls('tile', cycleHealth)} onClick={() => onOpenView('board')} role="button" tabIndex={0}>
          <span className="tile__indicator"></span>
          <div className="tile__title">Avg. cycle time</div>
          <div className="tile__value">
            <span className="num">{totals.avgCycle}</span>
            <span className="unit">days</span>
          </div>
          <div className="tile__trend good">
            <Icon.ArrowDown /> 4.3d vs prior 30 days
          </div>
          <Sparkline data={cycleTrend} color="var(--success)" />
        </div>

        <div className={cls('tile', bounceHealth)} onClick={() => onOpenView('board')} role="button" tabIndex={0}>
          <span className="tile__indicator"></span>
          <div className="tile__title">QA bounce rate</div>
          <div className="tile__value">
            <span className="num">{totals.bounceRate}</span>
            <span className="unit">%</span>
          </div>
          <div className="tile__trend good">
            <Icon.ArrowDown /> 4 pts vs prior 30 days
          </div>
          <Sparkline data={bounceTrend} color="var(--warning)" />
        </div>

        <div className={cls('tile', 'watch')} onClick={() => onOpenView('board')} role="button" tabIndex={0}>
          <span className="tile__indicator"></span>
          <div className="tile__title">Current bottleneck</div>
          <div className="tile__value">
            <span className="num" style={{ fontSize: 24 }}>{bottleneckAvg}<span className="unit" style={{ marginLeft: 4 }}>d</span></span>
          </div>
          <div className="tile__bottleneck">
            <span className={cls('badge', `status-${bottleneck}`)}>
              <span className="dot"></span>{STATUS_LABELS[bottleneck]}
            </span>
            <span className="t-meta" style={{ fontSize: 11 }}>{tickets.filter(t => t.status === bottleneck).length} tickets</span>
          </div>
        </div>
      </div>

      {/* Second row: status distribution + activity feed */}
      <div className="dash-row">
        <div className="card">
          <div className="card__header">
            <div>
              <div className="t-h3">Workflow distribution</div>
              <div className="t-meta">All {totalCount} tickets in this sprint</div>
            </div>
            <button className="btn btn-ghost" onClick={() => onOpenView('board')}>
              Open board →
            </button>
          </div>
          <div className="card__body">
            <div className="status-bar" role="img" aria-label="Status distribution">
              {data.statuses.map(s => {
                const w = (counts[s] / totalCount) * 100;
                return (
                  <div key={s} style={{ width: `${w}%`, background: STATUS_COLORS[s] }} title={`${STATUS_LABELS[s]}: ${counts[s]}`} />
                );
              })}
            </div>
            <div className="status-legend">
              {data.statuses.map(s => (
                <div key={s} className="item">
                  <span className="sw" style={{ background: STATUS_COLORS[s] }}></span>
                  <span>{STATUS_LABELS[s]}</span>
                  <b>{counts[s]}</b>
                  {s !== 'done' && <span className="mute2" style={{ fontSize: 11 }}>· avg {statusAvg[s]}d dwell</span>}
                </div>
              ))}
            </div>

            {/* per-developer mini ranking */}
            <div style={{ marginTop: 24 }}>
              <div className="t-label" style={{ marginBottom: 10 }}>Team in-flight load</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {team.filter(u => u.role === 'dev').map(u => {
                  const stats = data.userStats[u.id];
                  const pct = Math.min(100, stats.inFlight * 20);
                  return (
                    <div key={u.id} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 70px', alignItems: 'center', gap: 12, cursor: 'pointer' }}
                      onClick={() => onOpenUser(u)}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Avatar user={u} />
                        <span style={{ fontSize: 13, color: 'var(--text-1)' }}>{u.name}</span>
                      </div>
                      <div style={{ height: 6, background: 'var(--bg-3)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: stats.inFlight >= 4 ? 'var(--warning)' : 'var(--primary)', borderRadius: 3 }}></div>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-2)', textAlign: 'right' }}>
                        <b style={{ color: 'var(--text-1)' }}>{stats.inFlight}</b> in flight
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <div className="t-h3">Recent activity</div>
            <span className="t-meta">live</span>
          </div>
          <div className="card__body" style={{ paddingTop: 4 }}>
            <div className="feed">
              {events.map((e, i) => {
                const u = userById(e.by);
                return (
                  <div key={i} className="feed__item">
                    <span className="time">{relTime(e.at)}</span>
                    <Avatar user={u} size="sm" />
                    <span className="text">
                      <b>{u.name.split(' ')[0]}</b> moved <span className="key">{e.ticket.key}</span> to{' '}
                      <StatusBadge status={e.to} />
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.Dashboard = Dashboard;
