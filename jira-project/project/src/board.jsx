/* Figma-like canvas board: floating dev frames with pan/zoom */
const { useState: useStateBoard, useRef: useRefBoard, useEffect: useEffectBoard, useMemo: useMemoBoard, useCallback: useCallbackBoard } = React;

function Board({ data, onOpenUser, onOpenTicket }) {
  const { tickets, team, statuses, statusAvg, bottleneck } = data;
  const devs = team.filter(u => u.role === 'dev');

  // canvas pan/zoom state
  const [pan, setPan] = useStateBoard({ x: 40, y: 100 });
  const [zoom, setZoom] = useStateBoard(0.85);
  const [dragging, setDragging] = useStateBoard(false);
  const dragRef = useRefBoard({ x: 0, y: 0, panX: 0, panY: 0 });
  const shellRef = useRefBoard(null);
  const [hovered, setHovered] = useStateBoard(null);
  const [menuFor, setMenuFor] = useStateBoard(null); // dev id whose menu is open
  const [frameMeta, setFrameMeta] = useStateBoard(() => {
    const m = {};
    for (const u of devs) m[u.id] = { collapsed: false, category: u.role };
    return m;
  });
  const [connections, setConnections] = useStateBoard([]);
  const [connectMode, setConnectMode] = useStateBoard(false);
  const [connectFrom, setConnectFrom] = useStateBoard(null);

  // layout dev frames in a 2-col grid
  const FRAME_W = 540;
  const FRAME_H_EXPANDED = 460;
  const FRAME_H_COLLAPSED = 90;
  const COL_GAP = 80;
  const ROW_GAP = 110;
  const frames = useMemoBoard(() => {
    // compute y based on cumulative heights per column
    const colY = [0, 0];
    return devs.map((u, i) => {
      const col = i % 2;
      const collapsed = frameMeta[u.id]?.collapsed;
      const h = collapsed ? FRAME_H_COLLAPSED : FRAME_H_EXPANDED;
      const y = colY[col];
      colY[col] = y + h + ROW_GAP;
      return {
        user: u,
        x: col * (FRAME_W + COL_GAP),
        y,
        h,
        collapsed,
      };
    });
  }, [devs, frameMeta]);

  function setCategory(uid, category) {
    setFrameMeta(prev => ({ ...prev, [uid]: { ...prev[uid], category } }));
  }
  function toggleCollapsed(uid) {
    setFrameMeta(prev => ({ ...prev, [uid]: { ...prev[uid], collapsed: !prev[uid].collapsed } }));
  }
  function startConnectFrom(uid) {
    if (!connectMode) return;
    if (!connectFrom) {
      setConnectFrom(uid);
    } else if (connectFrom === uid) {
      setConnectFrom(null);
    } else {
      // create connection
      setConnections(prev => {
        const exists = prev.find(c => c.from === connectFrom && c.to === uid);
        if (exists) return prev;
        return [...prev, { from: connectFrom, to: uid }];
      });
      setConnectFrom(null);
      // remain in connect mode for chaining; user can press + again to exit
    }
  }
  function removeConnection(idx) {
    setConnections(prev => prev.filter((_, i) => i !== idx));
  }

  // mouse drag pan
  function onMouseDown(e) {
    // only pan if click is on shell or canvas bg (not on a frame or its kids)
    const target = e.target;
    if (target.closest('.frame') || target.closest('.canvas-toolbar')) return;
    setDragging(true);
    dragRef.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    e.preventDefault();
  }
  useEffectBoard(() => {
    if (!dragging) return;
    function onMove(e) {
      const { x, y, panX, panY } = dragRef.current;
      setPan({ x: panX + (e.clientX - x), y: panY + (e.clientY - y) });
    }
    function onUp() { setDragging(false); }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [dragging]);

  // wheel zoom
  function onWheel(e) {
    if (!shellRef.current) return;
    e.preventDefault();
    const rect = shellRef.current.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;
    // current world coord under cursor
    const wx = (px - pan.x) / zoom;
    const wy = (py - pan.y) / zoom;
    const delta = -e.deltaY * 0.0015;
    const newZoom = Math.max(0.4, Math.min(1.8, zoom + delta));
    // keep world coord stable under cursor
    setPan({ x: px - wx * newZoom, y: py - wy * newZoom });
    setZoom(newZoom);
  }

  function setZoomAt(newZoom) {
    if (!shellRef.current) return;
    const rect = shellRef.current.getBoundingClientRect();
    const px = rect.width / 2, py = rect.height / 2;
    const wx = (px - pan.x) / zoom;
    const wy = (py - pan.y) / zoom;
    setPan({ x: px - wx * newZoom, y: py - wy * newZoom });
    setZoom(newZoom);
  }
  function recenter() {
    setPan({ x: 40, y: 100 });
    setZoom(0.85);
  }

  return (
    <div>
      <div
        ref={shellRef}
        className={cls('canvas-shell', dragging && 'dragging', connectMode && 'connect-mode')}
        onMouseDown={onMouseDown}
        onWheel={onWheel}
      >
        <div
          className="canvas-inner"
          style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
        >
          {/* Connection layer (under frames) */}
          <ConnectionLayer
            frames={frames}
            frameW={FRAME_W}
            connections={connections}
            onRemove={removeConnection}
            connectingFrom={connectFrom}
          />

          {frames.map(({ user, x, y, h, collapsed }) => (
            <DevFrame
              key={user.id}
              user={user}
              data={data}
              x={x}
              y={y}
              w={FRAME_W}
              h={h}
              collapsed={collapsed}
              category={frameMeta[user.id]?.category}
              menuOpen={menuFor === user.id}
              connectMode={connectMode}
              isConnectFrom={connectFrom === user.id}
              onTitleClick={() => {
                if (connectMode) {
                  startConnectFrom(user.id);
                } else {
                  setMenuFor(menuFor === user.id ? null : user.id);
                }
              }}
              onCloseMenu={() => setMenuFor(null)}
              onToggleCollapsed={() => toggleCollapsed(user.id)}
              onSetCategory={(c) => setCategory(user.id, c)}
              onViewMetrics={() => { setMenuFor(null); onOpenUser(user); }}
              onOpenTicket={onOpenTicket}
              onHoverTicket={(ticket, ev) => {
                if (ticket && ev) {
                  const r = ev.currentTarget.getBoundingClientRect();
                  setHovered({ ticket, x: r.right + 10, y: r.top });
                } else {
                  setHovered(null);
                }
              }}
            />
          ))}
        </div>

        <div className="canvas-bottleneck-banner">
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS[bottleneck] }}></span>
          Workflow bottleneck: <b>{STATUS_LABELS[bottleneck]}</b> · avg <b>{statusAvg[bottleneck]}d</b> dwell across team
        </div>

        <div className="canvas-legend">
          <span className="leg"><span className="swatch" style={{ background: 'rgba(245,158,11,0.4)' }}></span> Warm</span>
          <span className="leg"><span className="swatch" style={{ background: 'rgba(239,68,68,0.5)' }}></span> Stuck</span>
          <span style={{ width: 1, height: 14, background: 'var(--border)' }}></span>
          {statuses.map(s => (
            <span key={s} className="leg">
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: STATUS_COLORS[s] }}></span>
              {STATUS_LABELS[s]}
            </span>
          ))}
        </div>

        <div className="canvas-toolbar" onMouseDown={e => e.stopPropagation()}>
          <button className="btn btn-icon" onClick={() => setZoomAt(Math.max(0.4, zoom - 0.1))} title="Zoom out" aria-label="Zoom out">−</button>
          <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
          <button className="btn btn-icon" onClick={() => setZoomAt(Math.min(1.8, zoom + 0.1))} title="Zoom in" aria-label="Zoom in">+</button>
          <span className="div"></span>
          <button className="btn" onClick={recenter} title="Recenter">Reset</button>
          <span className="div"></span>
          <button
            className={cls('btn', connectMode && 'btn-primary')}
            onClick={() => { setConnectMode(!connectMode); setConnectFrom(null); setMenuFor(null); }}
            title="Connect workflow handoffs"
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" style={{ marginRight: 2 }}>
              <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            {connectMode ? (connectFrom ? 'Pick target…' : 'Pick source…') : 'Connect workflow'}
          </button>
          {connections.length > 0 && !connectMode && (
            <span className="zoom-readout" style={{ minWidth: 'auto', padding: '0 6px' }}>{connections.length} link{connections.length>1?'s':''}</span>
          )}
        </div>
      </div>

      <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text-3)', textAlign: 'center' }}>
        {connectMode
          ? (connectFrom
            ? <span>Click a target frame to draw the handoff arrow · click <b>Connect workflow</b> again to exit</span>
            : <span>Click any developer frame to set the <b>source</b> of the workflow arrow</span>)
          : <span>Drag empty canvas to pan · scroll to zoom · click a name to open frame options · use <b>+ Connect</b> to draw workflow handoffs</span>
        }
      </div>

      {hovered && <TicketPreview ticket={hovered.ticket} x={hovered.x} y={hovered.y} team={team} />}
    </div>
  );
}

function DevFrame({ user, data, x, y, w, h, collapsed, category, menuOpen, connectMode, isConnectFrom, onTitleClick, onCloseMenu, onToggleCollapsed, onSetCategory, onViewMetrics, onOpenTicket, onHoverTicket }) {
  const stats = data.userStats[user.id];
  const userTickets = data.tickets.filter(t => t.assignee === user.id);
  const byStatus = {};
  for (const s of data.statuses) {
    byStatus[s] = userTickets.filter(t => t.status === s).sort((a,b) => b.daysInStatus - a.daysInStatus);
  }

  // hot: bottleneck signal
  const bottleneckTickets = byStatus[data.bottleneck] || [];
  const bottleneckAvg = bottleneckTickets.length
    ? bottleneckTickets.reduce((a,t)=>a+t.daysInStatus,0) / bottleneckTickets.length
    : 0;
  const isHot = bottleneckTickets.length >= 3 || bottleneckAvg > 12;

  // close menu on outside click
  const menuRef = useRefBoard(null);
  useEffectBoard(() => {
    if (!menuOpen) return;
    function onDoc(e) {
      if (menuRef.current && !menuRef.current.contains(e.target) && !e.target.closest('.frame__title')) {
        onCloseMenu();
      }
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [menuOpen]);

  const catLabels = { dev: 'Developer', qa: 'QA', po: 'Product Owner' };

  return (
    <div
      className={cls('frame', isHot && 'hot', isConnectFrom && 'connect-source', collapsed && 'collapsed')}
      style={{ left: x, top: y, width: w, minHeight: h }}
    >
      <div className={cls('frame__title', menuOpen && 'active', connectMode && 'connect-target')}
           onClick={(e) => { e.stopPropagation(); onTitleClick(); }}>
        <Avatar user={user} size="sm" />
        <span className="dev-name">{user.name}</span>
        <span className="dev-stats">·  {stats.inFlight} open · {stats.avgCycle}d avg cycle</span>
        {category && category !== 'dev' && (
          <span className={cls('role-pill', category)} style={{ marginLeft: 4 }}>{catLabels[category]}</span>
        )}
        {isHot && !collapsed && <span className="bn-pill">heavy in {STATUS_LABELS[data.bottleneck]}</span>}
        <span className={cls('frame__title-dots', menuOpen && 'show')} aria-hidden="true">
          <span></span><span></span><span></span>
        </span>

        {menuOpen && (
          <div className="frame__menu" ref={menuRef} onClick={e => e.stopPropagation()}>
            <button className="frame__menu-item" onClick={() => { onToggleCollapsed(); onCloseMenu(); }}>
              <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                {collapsed
                  ? <path d="M3 5l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  : <path d="M3 9l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>}
              </svg>
              {collapsed ? 'Expand frame' : 'Minimize frame'}
            </button>

            <div className="frame__menu-section">Set category</div>
            <div className="frame__menu-cats">
              {['dev','qa','po'].map(c => (
                <button
                  key={c}
                  className={cls('frame__menu-cat', category === c && 'on', c)}
                  onClick={() => onSetCategory(c)}
                >
                  <span className="sw"></span>
                  {catLabels[c]}
                </button>
              ))}
            </div>

            <div className="frame__menu-divider"></div>
            <button className="frame__menu-item" onClick={onViewMetrics}>
              <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                <path d="M2 11V7m3.5 4V4M9 11V8M12 11V5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              View performance metrics
            </button>
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="frame__columns">
          {data.statuses.map(s => {
            const items = byStatus[s];
            const avg = items.length ? items.reduce((a,t)=>a+t.daysInStatus,0)/items.length : 0;
            return (
              <div key={s} className={cls('frame__col', laneHeat(s === 'done' ? 0 : avg))}>
                <div className="frame__col-h">
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    <span className="dot" style={{ background: STATUS_COLORS[s] }}></span>
                    {s === 'in_progress' ? 'Doing' : s === 'todo' ? 'Todo' : s === 'qa' ? 'QA' : 'Done'}
                  </span>
                  <span className="count">{items.length}</span>
                </div>
                {items.length === 0 && <div className="frame__empty">—</div>}
                {items.slice(0, 6).map(t => (
                  <MiniCard
                    key={t.key}
                    ticket={t}
                    onClick={() => onOpenTicket(t)}
                    onMouseEnter={(ev) => onHoverTicket(t, ev)}
                    onMouseLeave={() => onHoverTicket(null)}
                  />
                ))}
                {items.length > 6 && (
                  <div style={{ fontSize: 10, color: 'var(--text-3)', textAlign: 'center', padding: '4px 0' }}>
                    +{items.length - 6} more
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {collapsed && (
        <div className="frame__collapsed-body">
          <div className="frame__collapsed-stats">
            <div><span className="num">{userTickets.length}</span><span className="lbl">tickets</span></div>
            <div><span className="num">{stats.inFlight}</span><span className="lbl">open</span></div>
            <div><span className="num">{stats.avgCycle}d</span><span className="lbl">cycle</span></div>
            <div><span className="num" style={{ color: stats.bounces > 0 ? 'var(--critical)' : 'inherit' }}>{stats.bounces}</span><span className="lbl">bounces</span></div>
          </div>
        </div>
      )}
    </div>
  );
}

function ConnectionLayer({ frames, frameW, connections, onRemove, connectingFrom }) {
  if (connections.length === 0) return null;
  // bounding box for SVG
  const byId = Object.fromEntries(frames.map(f => [f.user.id, f]));
  const pad = 60;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const c of connections) {
    const a = byId[c.from], b = byId[c.to];
    if (!a || !b) continue;
    minX = Math.min(minX, a.x, b.x);
    minY = Math.min(minY, a.y - 30, b.y - 30);
    maxX = Math.max(maxX, a.x + frameW, b.x + frameW);
    maxY = Math.max(maxY, a.y + a.h, b.y + b.h);
  }
  if (!isFinite(minX)) return null;
  minX -= pad; minY -= pad; maxX += pad; maxY += pad;

  return (
    <svg
      className="connections"
      width={maxX - minX}
      height={maxY - minY}
      style={{ position: 'absolute', left: minX, top: minY, pointerEvents: 'none', overflow: 'visible' }}
    >
      <defs>
        <marker id="cx-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--primary)" />
        </marker>
      </defs>
      {connections.map((c, i) => {
        const a = byId[c.from], b = byId[c.to];
        if (!a || !b) return null;
        // start: right edge of a, mid-height
        // end: left edge of b, mid-height
        const ax = a.x + frameW - minX;
        const ay = a.y + a.h / 2 - minY;
        const bx = b.x - minX;
        const by = b.y + b.h / 2 - minY;
        // if a is to the right of b, route along left side
        const aOnRight = a.x > b.x;
        const sx = aOnRight ? a.x - minX : ax;
        const ex = aOnRight ? b.x + frameW - minX : bx;
        const mx = (sx + ex) / 2;
        const path = `M${sx},${ay} C${mx},${ay} ${mx},${by} ${ex},${by}`;
        const midX = mx;
        const midY = (ay + by) / 2;
        return (
          <g key={i} style={{ pointerEvents: 'auto' }}>
            <path d={path} stroke="var(--primary)" strokeWidth="2" fill="none" markerEnd="url(#cx-arrow)" />
            <g transform={`translate(${midX}, ${midY})`} style={{ cursor: 'pointer' }} onClick={() => onRemove(i)}>
              <circle r="9" fill="var(--bg)" stroke="var(--primary)" strokeWidth="1.5" />
              <path d="M-3,-3 L3,3 M3,-3 L-3,3" stroke="var(--primary)" strokeWidth="1.5" strokeLinecap="round" />
            </g>
          </g>
        );
      })}
    </svg>
  );
}

function MiniCard({ ticket, onClick, onMouseEnter, onMouseLeave }) {
  const t = ticket;
  const dwellClass = t.daysInStatus < 2 ? '' : t.daysInStatus < 5 ? 'warn' : 'bad';
  const pdot = t.priority === 'critical' ? 'var(--critical)' : t.priority === 'high' ? 'var(--warning)' : null;
  return (
    <div
      className="mini-card"
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {pdot && <span className="mini-card__pdot" style={{ background: pdot }}></span>}
      <div className="mini-card__head">
        <span className="mini-card__key">{t.key}</span>
      </div>
      <div className="mini-card__title">{t.title}</div>
      <div className="mini-card__foot">
        <span className={dwellClass}>
          ⏱ {t.daysInStatus < 1 ? `${Math.round(t.daysInStatus * 24)}h` : `${t.daysInStatus.toFixed(1)}d`}
        </span>
        {t.bounces > 0 && (
          <span className="bounce" title={`${t.bounces} bounce${t.bounces > 1 ? 's' : ''}`}>
            <Icon.Bounce /> {t.bounces}
          </span>
        )}
      </div>
    </div>
  );
}

function TicketPreview({ ticket, x, y, team }) {
  const t = ticket;
  function uname(id) { const u = team.find(x=>x.id===id); return u ? u.name.split(' ')[0] : '—'; }
  const adjustedX = Math.min(x, window.innerWidth - 340);
  const adjustedY = Math.min(y, window.innerHeight - 280);
  return (
    <div className="hover-preview" style={{ left: adjustedX, top: adjustedY, position: 'fixed' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontSize: 11 }}>
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary)' }}>{t.key}</span>
        <span className="mute2">·</span>
        <StatusBadge status={t.status} />
      </div>
      <h4>{t.title}</h4>
      <div className="meta-row">
        <span>⏱ {t.daysInStatus.toFixed(1)}d in status</span>
        {t.cycleTimeDays != null && <span>· cycle {t.cycleTimeDays}d</span>}
        {t.bounces > 0 && <span style={{ color: 'var(--critical)' }}>· {t.bounces} bounce{t.bounces>1?'s':''}</span>}
        <span>· {t.story_points}pt</span>
      </div>
      <div className="meta-row">
        {t.labels.map(l => (
          <span key={l} style={{
            fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 5px',
            background: 'var(--bg-3)', borderRadius: 3, color: 'var(--text-2)'
          }}>{l}</span>
        ))}
      </div>
      <div className="timeline">
        <div className="t-label" style={{ fontSize: 9, marginBottom: 4 }}>Transition history</div>
        {t.history.map((h, i) => (
          <div key={i} className="tl-row">
            <span className="when">{fmtDate(h.at)}</span>
            <span className="what">
              {i === 0 ? 'Created in' : '→'} <StatusBadge status={h.status} />
            </span>
            <span className="mute2" style={{ fontSize: 10 }}>{uname(h.by)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

window.Board = Board;
