/* Developer drill-down + Ticket detail modals */
const { useEffect: useEffectModal, useRef: useRefModal, useMemo: useMemoModal } = React;

function ModalShell({ onClose, children, width }) {
  useEffectModal(() => {
    function onKey(e) {if (e.key === 'Escape') onClose();}
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={width ? { width } : null} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        {children}
      </div>
    </div>);

}

function DeveloperDrilldown({ user, data, onClose, onOpenTicket }) {
  const stats = data.userStats[user.id];
  const userTickets = data.tickets.
  filter((t) => t.assignee === user.id).
  sort((a, b) => (b.cycleTimeDays || 0) - (a.cycleTimeDays || 0)).
  slice(0, 30);

  const cycleSamples = userTickets.filter((t) => t.cycleTimeDays != null).map((t) => t.cycleTimeDays);

  // Distribution histogram: 0-3, 3-6, 6-10, 10-15, 15-25, 25+
  const buckets = [
  { min: 0, max: 3, label: '0-3d', cls: 'ok' },
  { min: 3, max: 6, label: '3-6d', cls: 'ok' },
  { min: 6, max: 10, label: '6-10d', cls: '' },
  { min: 10, max: 15, label: '10-15d', cls: 'warn' },
  { min: 15, max: 25, label: '15-25d', cls: 'warn' },
  { min: 25, max: Infinity, label: '25d+', cls: 'bad' }];

  const histogram = buckets.map((b) => cycleSamples.filter((v) => v >= b.min && v < b.max).length);
  const maxBucket = Math.max(...histogram, 1);
  const teamAvg = data.totals.avgCycle;

  return (
    <ModalShell onClose={onClose}>
      <div className="modal__head">
        <Avatar user={user} size="xl" ring />
        <div style={{ flex: 1 }}>
          <div className="name">{user.name}</div>
          <div className="sub">
            <RolePill role={user.role} /> · {data.project.name} · {stats.total} tickets assigned this sprint
          </div>
        </div>
        <button className="btn btn-icon modal__close" onClick={onClose} aria-label="Close">
          <Icon.Close />
        </button>
      </div>

      <div className="modal__body">
        <div className="metrics-row">
          <div className="m">
            <div className="label">Avg cycle</div>
            <div className="val">{stats.avgCycle}<span style={{ fontSize: 13, color: 'var(--text-2)', fontWeight: 500 }}>d</span></div>
            <div className="delta" style={{ color: stats.avgCycle < teamAvg ? 'var(--success)' : 'var(--warning)' }}>
              {stats.avgCycle < teamAvg ? `↓ ${(teamAvg - stats.avgCycle).toFixed(1)}d vs team` : `↑ ${(stats.avgCycle - teamAvg).toFixed(1)}d vs team`}
            </div>
          </div>
          <div className="m">
            <div className="label">Done</div>
            <div className="val">{stats.done}</div>
            <div className="delta">last 30 days</div>
          </div>
          <div className="m">
            <div className="label">In flight</div>
            <div className="val">{stats.inFlight}</div>
            <div className="delta">{stats.inFlight >= 4 ? 'Heavy load' : 'Healthy load'}</div>
          </div>
          <div className="m">
            <div className="label">Bounces</div>
            <div className="val" style={{ color: stats.bounces > 2 ? 'var(--critical)' : 'var(--text-1)' }}>{stats.bounces}</div>
            <div className="delta">{stats.bounceRate}% bounce rate</div>
          </div>
        </div>

        <div style={{ marginBottom: 6, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div className="t-h4" style={{ whiteSpace: 'nowrap' }}>Cycle time distribution</div>
          <div className="t-meta" style={{ whiteSpace: 'nowrap' }}>n={cycleSamples.length} · team avg {teamAvg}d</div>
        </div>
        <div className="chart">
          {/* Team-avg overlay line */}
          <div className="chart-overlay-avg" style={{ bottom: `${teamAvg / 30 * 100}%` }}>
            <span>team avg {teamAvg}d</span>
          </div>
          {histogram.map((v, i) =>
          <div
            key={i}
            className={cls('bar', buckets[i].cls)}
            style={{ height: `${v / maxBucket * 100}%`, animationDelay: `${i * 60}ms` }}
            title={`${v} ticket${v !== 1 ? 's' : ''} in ${buckets[i].label}`}>
            
              <span className="vlabel">{v}</span>
            </div>
          )}
        </div>
        <div className="chart-x">
          {buckets.map((b) => <div key={b.label}>{b.label}</div>)}
        </div>

        <div style={{ marginTop: 24, marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div className="t-h4" style={{ whiteSpace: 'nowrap' }}>Recent tickets</div>
          <div className="t-meta" style={{ whiteSpace: 'nowrap' }}>Last {userTickets.length} · sorted by cycle time</div>
        </div>
        <div className="mini-tickets">
          {userTickets.map((t) =>
          <div key={t.key} className="row" onClick={() => onOpenTicket(t)} style={{ cursor: 'pointer' }}>
              <span className="k">{t.key}</span>
              <span className="t">{t.title}</span>
              <StatusBadge status={t.status} />
              <span className="c">
                {t.cycleTimeDays != null ? `${t.cycleTimeDays}d` : `${t.daysInStatus.toFixed(1)}d`}
                {t.bounces > 0 && <span style={{ color: 'var(--critical)', marginLeft: 6, fontWeight: 600 }}>↺{t.bounces}</span>}
              </span>
            </div>
          )}
        </div>
      </div>
    </ModalShell>);

}

function TicketModal({ ticket, data, onClose, onOpenUser }) {
  const u = data.team.find((x) => x.id === ticket.assignee);
  const reporter = data.team.find((x) => x.id === ticket.reporter);

  return (
    <ModalShell onClose={onClose} width={560}>
      <div className="modal__head">
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--primary)', fontSize: 13 }}>{ticket.key}</span>
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
          <div className="name" style={{ fontSize: 16 }}>{ticket.title}</div>
        </div>
        <button className="btn btn-icon" onClick={onClose}><Icon.Close /></button>
      </div>
      <div className="modal__body">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
          <div>
            <div className="t-label" style={{ marginBottom: 6 }}>Assignee</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }} onClick={() => onOpenUser(u)}>
              <Avatar user={u} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{u?.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-2)' }}>{ROLE_LABELS[u?.role]}</div>
              </div>
            </div>
          </div>
          <div>
            <div className="t-label" style={{ marginBottom: 6 }}>Reporter</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar user={reporter} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{reporter?.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-2)' }}>{ROLE_LABELS[reporter?.role]}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="metrics-row" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="m">
            <div className="label">In status</div>
            <div className="val">{ticket.daysInStatus.toFixed(1)}<span style={{ fontSize: 13, color: 'var(--text-2)', fontWeight: 500 }}>d</span></div>
          </div>
          <div className="m">
            <div className="label">Cycle time</div>
            <div className="val">{ticket.cycleTimeDays != null ? `${ticket.cycleTimeDays}d` : <span className="mute2">live</span>}</div>
          </div>
          <div className="m">
            <div className="label">Bounces</div>
            <div className="val" style={{ color: ticket.bounces ? 'var(--critical)' : 'var(--text-1)' }}>{ticket.bounces}</div>
          </div>
        </div>

        <div className="t-h4" style={{ marginBottom: 10 }}>Transition history</div>
        <TransitionTimeline history={ticket.history} team={data.team} />
      </div>
    </ModalShell>);

}

function TransitionTimeline({ history, team }) {
  function uname(id) {const u = team.find((x) => x.id === id);return u ? u.name : '—';}
  function userObj(id) {return team.find((x) => x.id === id);}
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {history.map((h, i) => {
        const prev = history[i - 1];
        const dwell = prev ? ((h.at - prev.at) / 86400000).toFixed(1) : null;
        return (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: '80px 24px 1fr', columnGap: 12, padding: '8px 0', position: 'relative' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)' }}>
              {fmtDate(h.at)}<br />{fmtTime(h.at)}
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', position: 'relative' }}>
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: STATUS_COLORS[h.status],
                boxShadow: '0 0 0 3px var(--bg)',
                marginTop: 6, position: 'relative', zIndex: 2
              }}></div>
              {i < history.length - 1 &&
              <div style={{
                position: 'absolute', top: 16, bottom: -12,
                width: 2, background: 'var(--border)'
              }}></div>
              }
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                <StatusBadge status={h.status} />
                {dwell && <span className="t-meta">+{dwell}d in prior status</span>}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>
                {i === 0 ? 'Created' : 'Transitioned'} by <b style={{ color: 'var(--text-1)' }}>{uname(h.by)}</b>
              </div>
            </div>
          </div>);

      })}
    </div>);

}

window.DeveloperDrilldown = DeveloperDrilldown;
window.TicketModal = TicketModal;

/* ============================================================
   Settings modal — Jira API key + multiple AI model keys
   ============================================================ */
const AI_PROVIDERS = [
{ id: 'anthropic', label: 'Anthropic Claude', placeholder: 'sk-ant-…' },
{ id: 'openai', label: 'OpenAI GPT', placeholder: 'sk-…' },
{ id: 'google', label: 'Google Gemini', placeholder: 'AIza…' },
{ id: 'mistral', label: 'Mistral', placeholder: 'mst-…' },
{ id: 'cohere', label: 'Cohere', placeholder: 'co-…' },
{ id: 'azure', label: 'Azure OpenAI', placeholder: 'AZ-…' },
{ id: 'other', label: 'Other…', placeholder: 'API key' }];


function SecretField({ value, onChange, placeholder, isText }) {
  const [show, setShow] = React.useState(false);
  return (
    <div className="input-wrap">
      <span className="ico-pre"><Icon.Key /></span>
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={isText ? 'text-input' : ''}
        autoComplete="off"
        spellCheck="false" />
      
      <button
        type="button"
        className="reveal"
        onClick={() => setShow((s) => !s)}
        title={show ? 'Hide' : 'Show'}
        aria-label={show ? 'Hide key' : 'Show key'}>
        
        {show ? <Icon.EyeOff /> : <Icon.Eye />}
      </button>
    </div>);

}

function SettingsModal({ onClose, aiKeys, setAiKeys, activeModelId, setActiveModelId }) {
  /* in-memory only — wire to real persistence later */
  const [jiraDomain, setJiraDomain] = React.useState('acme.atlassian.net');
  const [jiraEmail, setJiraEmail] = React.useState('mo@acme.com');
  const [jiraKey, setJiraKey] = React.useState('ATATT3xFfGF0a3R…');

  const usedProviders = new Set(aiKeys.map((k) => k.provider));
  const firstUnused = AI_PROVIDERS.find((p) => !usedProviders.has(p.id)) || AI_PROVIDERS[0];

  function addAi() {
    const id = 'm-' + Math.random().toString(36).slice(2, 8);
    setAiKeys([...aiKeys, { id, provider: firstUnused.id, customName: '', key: '' }]);
  }
  function updateAi(id, patch) {
    setAiKeys(aiKeys.map((k) => k.id === id ? { ...k, ...patch } : k));
  }
  function removeAi(id) {
    const next = aiKeys.filter((k) => k.id !== id);
    setAiKeys(next);
    if (setActiveModelId && activeModelId === id) {
      const fallback = next.find((k) => k.key.trim());
      setActiveModelId(fallback ? fallback.id : null);
    }
  }

  const jiraConnected = jiraDomain && jiraEmail && jiraKey;
  const aiCount = aiKeys.filter((k) => k.key.trim()).length;

  return (
    <ModalShell onClose={onClose} width={620}>
      <div className="modal__head">
        <div style={{
          width: 40, height: 40, borderRadius: 8,
          background: 'linear-gradient(135deg, var(--primary), var(--role-po))',
          color: 'white', display: 'inline-flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Icon.Gear />
        </div>
        <div style={{ flex: 1 }}>
          <div className="name">Settings</div>
          <div className="sub">Connect Jira and your AI providers</div>
        </div>
        <button className="btn btn-icon modal__close" onClick={onClose} aria-label="Close">
          <Icon.Close />
        </button>
      </div>

      {/* ----------------- Jira ----------------- */}
      <div className="settings-section">
        <div className="settings-section__head">
          <span className="ico" style={{ background: 'var(--primary-50)', color: 'var(--primary)' }}>
            <Icon.Key />
          </span>
          <div style={{ flex: 1 }}>
            <h3>Jira API Key</h3>
            <p>Read tickets, statuses, and transitions from your Jira workspace.</p>
          </div>
          <span className={cls('settings-status', jiraConnected && 'connected')}>
            <span className="pulse"></span>
            {jiraConnected ? 'Connected' : 'Not connected'}
          </span>
        </div>

        <div className="settings-section__body">
          <div className="field-row">
            <label>Workspace domain<span className="req">*</span></label>
            <div className="input-wrap" data-comment-anchor="1952cf0bdd-div-347-13">
              <span className="ico-pre prefix-text">https://</span>
              <input
                type="text"
                className="text-input"
                value={jiraDomain}
                onChange={(e) => setJiraDomain(e.target.value)}
                placeholder="company.atlassian.net" />
            </div>
          </div>

          <div className="field-row">
            <label>Account email<span className="req">*</span></label>
            <div className="input-wrap">
              <span className="ico-pre"><Icon.At /></span>
              <input
                type="email"
                className="text-input"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
                placeholder="you@company.com" />
            </div>
          </div>

          <div className="field-row" style={{ marginBottom: 0 }}>
            <label>API token<span className="req">*</span></label>
            <SecretField
              value={jiraKey}
              onChange={setJiraKey}
              placeholder="ATATT3xFfGF0…" />
            <div className="input-help">
              Create one at{' '}
              <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noreferrer">
                id.atlassian.com / API tokens
              </a>
              . Stored encrypted at rest.
            </div>
          </div>
        </div>
      </div>

      {/* ----------------- AI Models ----------------- */}
      <div className="settings-section">
        <div className="settings-section__head">
          <span className="ico" style={{ background: 'var(--role-qa-50)', color: 'var(--role-qa)' }}>
            <Icon.Sparkles />
          </span>
          <div style={{ flex: 1 }}>
            <h3>AI Model API Keys</h3>
            <p>Power summaries, standup notes, and bottleneck explanations. Add as many providers as you like.</p>
          </div>
          <span className={cls('settings-status', aiCount > 0 && 'connected')}>
            <span className="pulse"></span>
            {aiCount} active
          </span>
        </div>

        <div className="settings-section__body">
          {aiKeys.length === 0 &&
          <div className="model-empty">
              No AI providers configured. Add one to enable AI-powered insights.
            </div>
          }

          <div className="model-list">
            {aiKeys.map((k) => {
              const meta = AI_PROVIDERS.find((p) => p.id === k.provider) || AI_PROVIDERS[0];
              const isOther = k.provider === 'other';
              return (
                <div className={cls('model-row', isOther && 'has-custom')} key={k.id}>
                  <div className="input-wrap">
                    <select value={k.provider} onChange={(e) => updateAi(k.id, { provider: e.target.value })}>
                      {AI_PROVIDERS.map((p) =>
                      <option key={p.id} value={p.id}>{p.label}</option>
                      )}
                    </select>
                  </div>
                  {isOther &&
                  <div className="input-wrap model-row__custom">
                      <input
                      type="text"
                      className="text-input"
                      value={k.customName}
                      onChange={(e) => updateAi(k.id, { customName: e.target.value })}
                      placeholder="Provider name (e.g. Perplexity)"
                      style={{ paddingLeft: 12 }} />
                    
                    </div>
                  }
                  <SecretField
                    value={k.key}
                    onChange={(v) => updateAi(k.id, { key: v })}
                    placeholder={meta.placeholder} />
                  
                  <button
                    className="row-del"
                    onClick={() => removeAi(k.id)}
                    aria-label="Remove provider"
                    title="Remove">
                    
                    <Icon.Trash />
                  </button>
                </div>);

            })}
          </div>

          <button className="add-model-btn" onClick={addAi}>
            <Icon.Plus /> Add another model
          </button>
        </div>
      </div>

      <div className="settings-foot">
        <span className="mute">Changes apply live. Keys are stored encrypted and never sent to third parties.</span>
      </div>
    </ModalShell>);

}

window.SettingsModal = SettingsModal;