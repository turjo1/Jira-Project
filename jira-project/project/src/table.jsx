/* Table view: sorting, filtering, column config, custom columns, per-column select + copy */
const { useState: useStateTbl, useMemo: useMemoTbl, useRef: useRefTbl, useEffect: useEffectTbl } = React;

const BUILTIN_COLUMNS = [
  { id: 'key',           label: 'Key',            width: 90,  sort: 'string' },
  { id: 'title',         label: 'Title',          flex: 1,    sort: 'string' },
  { id: 'assignee',      label: 'Assignee',       width: 180, sort: 'string' },
  { id: 'status',        label: 'Status',         width: 130, sort: 'status' },
  { id: 'daysInStatus',  label: 'Time in status', width: 180, sort: 'num' },
  { id: 'cycleTimeDays', label: 'Cycle time',     width: 130, sort: 'num' },
  { id: 'bounces',       label: 'Bounces',        width: 90,  sort: 'num' },
  { id: 'priority',      label: 'Priority',       width: 100, sort: 'string' },
  { id: 'storyPoints',   label: 'Pts',            width: 70,  sort: 'num' },
];

/* days → "1d 3hr" / "18hr" / "<1hr" */
function fmtDuration(days) {
  if (days == null || isNaN(days)) return null;
  const totalHr = days * 24;
  if (totalHr < 1) return '<1hr';
  if (totalHr < 24) return `${Math.round(totalHr)}hr`;
  const d = Math.floor(totalHr / 24);
  const h = Math.round(totalHr - d * 24);
  return h === 0 ? `${d}d` : `${d}d ${h}hr`;
}

/* plain-text cell value, used when copying to clipboard */
function cellText(t, col) {
  if (col.custom) return '';
  switch (col.id) {
    case 'key':           return t.key;
    case 'title':         return t.title;
    case 'assignee':      return t.assigneeUser?.name || '';
    case 'status':        return STATUS_LABELS[t.status] || t.status;
    case 'daysInStatus':  return fmtDuration(t.daysInStatus) || '';
    case 'cycleTimeDays': return fmtDuration(t.cycleTimeDays) || '';
    case 'bounces':       return String(t.bounces ?? 0);
    case 'priority':      return ({ critical: 'Critical', high: 'High', med: 'Medium', low: 'Low' }[t.priority]) || '';
    case 'storyPoints':   return String(t.storyPoints ?? '');
    default:              return '';
  }
}

function Table({ data, onOpenUser, onOpenTicket }) {
  const { tickets, team, statuses } = data;
  const [search, setSearch] = useStateTbl('');
  const [statusFilter, setStatusFilter] = useStateTbl(new Set());
  const [assigneeFilter, setAssigneeFilter] = useStateTbl(new Set());
  const [sort, setSort] = useStateTbl({ id: 'daysInStatus', dir: 'desc' });
  const [customCols, setCustomCols] = useStateTbl([]); // [{id, label}]
  const [visibleCols, setVisibleCols] = useStateTbl(
    new Set(['key', 'title', 'assignee', 'status', 'daysInStatus', 'cycleTimeDays', 'bounces'])
  );
  const [selectedCols, setSelectedCols] = useStateTbl(new Set()); // colIds with select-all on
  const [colMenu, setColMenu] = useStateTbl(false);
  const [statusMenu, setStatusMenu] = useStateTbl(false);
  const [assigneeMenu, setAssigneeMenu] = useStateTbl(false);
  const [headerMenu, setHeaderMenu] = useStateTbl(null); // colId
  const [editingColId, setEditingColId] = useStateTbl(null);
  const [toast, setToast] = useStateTbl('');

  const statusMenuRef = useRefTbl(null);
  const assigneeMenuRef = useRefTbl(null);
  const colMenuRef = useRefTbl(null);
  const headerMenuRef = useRefTbl(null);

  /* full ordered column list = built-ins + customs (custom go after Pts) */
  const allColumns = useMemoTbl(() => [
    ...BUILTIN_COLUMNS,
    ...customCols.map((c) => ({ id: c.id, label: c.label, width: 150, sort: 'string', custom: true })),
  ], [customCols]);

  const visible = allColumns.filter((c) => visibleCols.has(c.id));

  /* dismiss popovers on outside click */
  useEffectTbl(() => {
    function onDoc(e) {
      if (statusMenuRef.current && !statusMenuRef.current.contains(e.target)) setStatusMenu(false);
      if (assigneeMenuRef.current && !assigneeMenuRef.current.contains(e.target)) setAssigneeMenu(false);
      if (colMenuRef.current && !colMenuRef.current.contains(e.target)) setColMenu(false);
      if (headerMenuRef.current && !headerMenuRef.current.contains(e.target)) setHeaderMenu(null);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  /* auto-hide toast */
  useEffectTbl(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(''), 1800);
    return () => clearTimeout(id);
  }, [toast]);

  const rows = useMemoTbl(() => {
    const userById = Object.fromEntries(team.map((u) => [u.id, u]));
    let arr = tickets.map((t) => ({
      ...t,
      assigneeUser: userById[t.assignee],
      storyPoints: t.story_points,
    }));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      arr = arr.filter((t) =>
        t.key.toLowerCase().includes(q) ||
        t.title.toLowerCase().includes(q) ||
        (t.assigneeUser && t.assigneeUser.name.toLowerCase().includes(q))
      );
    }
    if (statusFilter.size) arr = arr.filter((t) => statusFilter.has(t.status));
    if (assigneeFilter.size) arr = arr.filter((t) => assigneeFilter.has(t.assignee));

    const col = allColumns.find((c) => c.id === sort.id);
    const dir = sort.dir === 'asc' ? 1 : -1;
    if (col) {
      arr.sort((a, b) => {
        let av = a[sort.id], bv = b[sort.id];
        if (sort.id === 'assignee') { av = a.assigneeUser?.name; bv = b.assigneeUser?.name; }
        if (sort.id === 'status') {
          const order = ['todo', 'in_progress', 'qa', 'done'];
          return (order.indexOf(av) - order.indexOf(bv)) * dir;
        }
        if (col.sort === 'num') {
          av = av == null ? -Infinity : av;
          bv = bv == null ? -Infinity : bv;
        }
        if (av < bv) return -1 * dir;
        if (av > bv) return 1 * dir;
        return 0;
      });
    }
    return arr;
  }, [tickets, team, sort, search, statusFilter, assigneeFilter, allColumns]);

  function toggleSet(set, value) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value); else next.add(value);
    return next;
  }

  function clickHeader(col, e) {
    // click on the checkbox / rename input / menu button — handled by their own handlers
    if (editingColId === col.id) return;
    if (e?.target?.closest?.('.th-checkbox, .th-menu-btn, .th-menu, .th-rename')) return;
    if (sort.id === col.id) {
      setSort({ id: col.id, dir: sort.dir === 'asc' ? 'desc' : 'asc' });
    } else {
      setSort({ id: col.id, dir: col.sort === 'num' ? 'desc' : 'asc' });
    }
  }

  /* ---------- custom-column ops ---------- */
  function addCustomColumn() {
    const used = new Set([...BUILTIN_COLUMNS.map((c) => c.label), ...customCols.map((c) => c.label)]);
    let i = 1, label = 'New column';
    while (used.has(label)) { i += 1; label = `New column ${i}`; }
    const id = 'cc_' + Math.random().toString(36).slice(2, 8);
    setCustomCols([...customCols, { id, label }]);
    setVisibleCols(new Set([...visibleCols, id]));
    setColMenu(false);
    setTimeout(() => setEditingColId(id), 50);
  }
  function renameCustom(id, label) {
    const trimmed = (label || '').trim();
    setCustomCols(customCols.map((c) => (c.id === id ? { ...c, label: trimmed || c.label } : c)));
    setEditingColId(null);
  }
  function deleteCustom(id) {
    setCustomCols(customCols.filter((c) => c.id !== id));
    setVisibleCols(new Set([...visibleCols].filter((v) => v !== id)));
    setSelectedCols(new Set([...selectedCols].filter((v) => v !== id)));
    if (sort.id === id) setSort({ id: 'daysInStatus', dir: 'desc' });
    setHeaderMenu(null);
  }

  /* ---------- copy ops ---------- */
  async function copyText(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      setToast(label);
    } catch (e) {
      setToast('Copy failed');
    }
  }
  function buildTSV(colIds) {
    const cols = colIds
      .map((id) => allColumns.find((c) => c.id === id))
      .filter(Boolean);
    if (!cols.length) return '';
    const head = cols.map((c) => c.label).join('\t');
    const body = rows.map((t) => cols.map((c) => cellText(t, c)).join('\t')).join('\n');
    return head + '\n' + body;
  }
  function copySingleColumn(colId) {
    const col = allColumns.find((c) => c.id === colId);
    if (!col) return;
    const text = rows.map((t) => cellText(t, col)).join('\n');
    copyText(text, `Copied "${col.label}" — ${rows.length} rows`);
    setHeaderMenu(null);
  }
  function copySelectedColumns() {
    if (!selectedCols.size) return;
    // preserve visible order
    const orderedIds = visible.filter((c) => selectedCols.has(c.id)).map((c) => c.id);
    const text = buildTSV(orderedIds);
    copyText(text, `Copied ${orderedIds.length} column${orderedIds.length === 1 ? '' : 's'} — ${rows.length} rows`);
  }
  function toggleColSelected(colId) {
    setSelectedCols(toggleSet(selectedCols, colId));
  }
  function clearSelectedCols() { setSelectedCols(new Set()); }

  /* ---------- render ---------- */
  return (
    <div className="table-shell">
      {/* selection bar appears when ≥1 column is selected */}
      {selectedCols.size > 0 && (
        <div className="table-selbar">
          <span className="table-selbar__count">
            <Icon.Check />
            {selectedCols.size}&nbsp;column{selectedCols.size === 1 ? '' : 's'}&nbsp;selected
            <span className="mute2" style={{ marginLeft: 8 }}>· {rows.length} rows</span>
          </span>
          <div style={{ flex: 1 }}></div>
          <button className="btn btn-ghost" onClick={clearSelectedCols}>Clear</button>
          <button className="btn btn-primary" onClick={copySelectedColumns}>
            <Icon.Copy /> Copy selection
          </button>
        </div>
      )}

      <div className="table-bar" data-comment-anchor="ce60fd064a-div-94-7">
        <div className="search">
          <Icon.Search />
          <input
            type="text"
            placeholder="Search tickets, titles, people…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div ref={statusMenuRef} style={{ position: 'relative' }}>
          <button
            className={cls('filter-chip', statusFilter.size && 'active')}
            onClick={() => { setStatusMenu((v) => !v); setColMenu(false); setAssigneeMenu(false); }}
          >
            <Icon.Filter />
            <span>Status</span>
            {statusFilter.size > 0 && <span className="chip-count">{statusFilter.size}</span>}
            <Icon.Chevron />
          </button>
          {statusMenu && (
            <div className="popover" style={{ left: 0, right: 'auto' }}>
              <h5>Filter by status</h5>
              {statuses.map((s) => (
                <label key={s} className="row">
                  <input
                    type="checkbox"
                    checked={statusFilter.has(s)}
                    onChange={() => setStatusFilter(toggleSet(statusFilter, s))}
                  />
                  <StatusBadge status={s} />
                </label>
              ))}
              {statusFilter.size > 0 && (
                <button className="btn btn-ghost" style={{ width: '100%', marginTop: 4 }} onClick={() => setStatusFilter(new Set())}>
                  Clear
                </button>
              )}
            </div>
          )}
        </div>

        <div ref={assigneeMenuRef} style={{ position: 'relative' }}>
          <button
            className={cls('filter-chip', assigneeFilter.size && 'active')}
            onClick={() => { setAssigneeMenu((v) => !v); setColMenu(false); setStatusMenu(false); }}
          >
            <Icon.Filter />
            <span>Assignee</span>
            {assigneeFilter.size > 0 && <span className="chip-count">{assigneeFilter.size}</span>}
            <Icon.Chevron />
          </button>
          {assigneeMenu && (
            <div className="popover" style={{ left: 0, right: 'auto', width: 240 }}>
              <h5>Filter by assignee</h5>
              {team.map((u) => (
                <label key={u.id} className="row">
                  <input
                    type="checkbox"
                    checked={assigneeFilter.has(u.id)}
                    onChange={() => setAssigneeFilter(toggleSet(assigneeFilter, u.id))}
                  />
                  <Avatar user={u} size="sm" />
                  <span>{u.name}</span>
                  <span className="mute2" style={{ marginLeft: 'auto', fontSize: 10 }}>{ROLE_LABELS[u.role]}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="spacer"></div>

        <div style={{ fontSize: 12, color: 'var(--text-2)' }}>
          {rows.length} of {tickets.length}
        </div>

        <div ref={colMenuRef} style={{ position: 'relative' }}>
          <button
            className="btn btn-icon"
            onClick={() => { setColMenu((v) => !v); setStatusMenu(false); setAssigneeMenu(false); }}
            title="Configure columns"
            aria-label="Configure columns"
          >
            <Icon.Gear />
          </button>
          {colMenu && (
            <div className="popover" style={{ width: 240 }}>
              <h5>Show columns</h5>
              {allColumns.map((c) => (
                <label key={c.id} className="row">
                  <input
                    type="checkbox"
                    checked={visibleCols.has(c.id)}
                    onChange={() => setVisibleCols(toggleSet(visibleCols, c.id))}
                  />
                  <span style={{ flex: 1 }}>{c.label}</span>
                  {c.custom && <span className="custom-tag">custom</span>}
                </label>
              ))}
              <div className="popover-sep"></div>
              <button className="popover-action" onClick={addCustomColumn}>
                <Icon.Plus /> Add custom column
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="tbl-scroll">
        <table className="tbl">
          <thead>
            <tr>
              {visible.map((c) => {
                const isSorted = sort.id === c.id;
                const isSelected = selectedCols.has(c.id);
                const isEditing = editingColId === c.id;
                const isOpen = headerMenu === c.id;
                return (
                  <th
                    key={c.id}
                    onClick={(e) => clickHeader(c, e)}
                    className={cls(isSorted && 'sorted', isSorted && sort.dir, isSelected && 'col-selected', c.custom && 'is-custom')}
                    style={{ width: c.width ? c.width : 'auto' }}
                  >
                    <div className="th-inner">
                      <label
                        className="th-checkbox"
                        title="Select column"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleColSelected(c.id)}
                        />
                      </label>

                      {isEditing ? (
                        <input
                          autoFocus
                          className="th-rename"
                          defaultValue={c.label}
                          onClick={(e) => e.stopPropagation()}
                          onBlur={(e) => renameCustom(c.id, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') { e.preventDefault(); renameCustom(c.id, e.target.value); }
                            if (e.key === 'Escape') { e.preventDefault(); setEditingColId(null); }
                          }}
                        />
                      ) : (
                        <span className="th-label">{c.label}</span>
                      )}

                      <span className="sort">
                        <span className="a">▲</span>
                        <span className="d">▼</span>
                      </span>

                      <span style={{ flex: 1 }}></span>

                      <button
                        className="th-menu-btn"
                        title="Column actions"
                        aria-label="Column actions"
                        onClick={(e) => { e.stopPropagation(); setHeaderMenu(isOpen ? null : c.id); }}
                      >
                        <Icon.More />
                      </button>

                      {isOpen && (
                        <div className="th-menu popover" ref={headerMenuRef} onClick={(e) => e.stopPropagation()}>
                          <button className="popover-action" onClick={() => { toggleColSelected(c.id); setHeaderMenu(null); }}>
                            <Icon.Check /> {isSelected ? 'Deselect column' : 'Select column'}
                          </button>
                          <button className="popover-action" onClick={() => copySingleColumn(c.id)}>
                            <Icon.Copy /> Copy column
                          </button>
                          {c.custom && (
                            <React.Fragment>
                              <button className="popover-action" onClick={() => { setEditingColId(c.id); setHeaderMenu(null); }}>
                                <Icon.Pencil /> Rename
                              </button>
                              <div className="popover-sep"></div>
                              <button className="popover-action danger" onClick={() => deleteCustom(c.id)}>
                                <Icon.Trash /> Delete column
                              </button>
                            </React.Fragment>
                          )}
                        </div>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <TableRow
                key={t.key}
                t={t}
                visible={visible}
                selectedCols={selectedCols}
                onOpenTicket={onOpenTicket}
                onOpenUser={onOpenUser}
              />
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={visible.length} style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
                No tickets match these filters.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {toast && (
        <div className="table-toast">
          <Icon.Check /> {toast}
        </div>
      )}
    </div>
  );
}

function TableRow({ t, visible, selectedCols, onOpenTicket, onOpenUser }) {
  const u = t.assigneeUser;
  const dwellClass = t.daysInStatus < 2 ? 'ok' : t.daysInStatus < 5 ? 'warn' : 'bad';
  const dwellPct = Math.min(100, (t.daysInStatus / 14) * 100);
  const dwellLabel = fmtDuration(t.daysInStatus);
  const cycleLabel = fmtDuration(t.cycleTimeDays);
  return (
    <tr onClick={() => onOpenTicket(t)}>
      {visible.map((c) => {
        const sel = selectedCols && selectedCols.has(c.id) ? 'col-selected' : '';
        if (c.custom) return <td key={c.id} className={cls(sel, 'custom-cell')}><span className="mute2">—</span></td>;
        if (c.id === 'key') return <td key={c.id} className={cls('key', sel)}>{t.key}</td>;
        if (c.id === 'title') return <td key={c.id} className={sel}>
          <div className="title-cell">
            <span>{t.title}</span>
            {t.bounces > 0 && (
              <span className="bounces" title={`${t.bounces} bounces`}>
                <Icon.Bounce /> {t.bounces}
              </span>
            )}
          </div>
        </td>;
        if (c.id === 'assignee') return <td key={c.id} className={sel}>
          <div className="assignee-cell" onClick={(e) => { e.stopPropagation(); if (u) onOpenUser(u); }}>
            <Avatar user={u} size="sm" />
            <span>{u?.name}</span>
          </div>
        </td>;
        if (c.id === 'status') return <td key={c.id} className={sel}><StatusBadge status={t.status} /></td>;
        if (c.id === 'daysInStatus') return <td key={c.id} className={sel}>
          <div className="days-cell">
            <div className={cls('bar-mini', dwellClass)}><div style={{ width: `${dwellPct}%` }}></div></div>
            <span style={{ fontVariantNumeric: 'tabular-nums', fontSize: 12.5, whiteSpace: 'nowrap' }}>{dwellLabel}</span>
          </div>
        </td>;
        if (c.id === 'cycleTimeDays') return <td key={c.id} className={sel} style={{ fontVariantNumeric: 'tabular-nums' }}>
          {cycleLabel ? cycleLabel : <span className="mute2">—</span>}
        </td>;
        if (c.id === 'bounces') return <td key={c.id} className={sel} style={{ fontVariantNumeric: 'tabular-nums' }}>
          {t.bounces > 0 ? <span style={{ color: 'var(--critical)', fontWeight: 600 }}>{t.bounces}</span> : <span className="mute2">0</span>}
        </td>;
        if (c.id === 'priority') return <td key={c.id} className={sel}><PriorityBadge priority={t.priority} /></td>;
        if (c.id === 'storyPoints') return <td key={c.id} className={sel} style={{ fontVariantNumeric: 'tabular-nums' }}>{t.storyPoints}</td>;
        return <td key={c.id} className={sel}>—</td>;
      })}
    </tr>
  );
}

window.Table = Table;
