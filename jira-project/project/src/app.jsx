/* Main app: shell, navigation, view routing, Tweaks integration */
const { useState: useStateApp, useEffect: useEffectApp, useMemo: useMemoApp } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "light"
} /*EDITMODE-END*/;

function App() {
  const [data, setData] = useStateApp(window.JIRA_DATA);
  const [loading, setLoading] = useStateApp(false);
  const [dataError, setDataError] = useStateApp(null);
  const [view, setView] = useStateApp('dashboard');
  const [drilldown, setDrilldown] = useStateApp(null); // user
  const [ticketDetail, setTicketDetail] = useStateApp(null); // ticket
  const [settingsOpen, setSettingsOpen] = useStateApp(false);
  const [aiModelMenu, setAiModelMenu] = useStateApp(false);
  const [aiKeys, setAiKeys] = useStateApp([
  { id: 'm-1', provider: 'anthropic', customName: '', key: 'sk-ant-api03-9w8…' },
  { id: 'm-2', provider: 'openai', customName: '', key: '' }]
  );
  const [activeModelId, setActiveModelId] = useStateApp('m-1');
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [secsAgo, setSecsAgo] = useStateApp(12);

  const aiModelBtnRef = React.useRef(null);
  useEffectApp(() => {
    function onDoc(e) {
      if (aiModelBtnRef.current && !aiModelBtnRef.current.contains(e.target)) setAiModelMenu(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  /* configured models = ones with a non-empty key */
  const configuredModels = aiKeys.filter((k) => k.key.trim());
  const activeModel = configuredModels.find((k) => k.id === activeModelId) || configuredModels[0] || null;
  const activeLabel = activeModel ?
  activeModel.provider === 'other' ?
  activeModel.customName || 'Custom model' :
  AI_PROVIDERS.find((p) => p.id === activeModel.provider)?.label.replace(/\s+.*$/, '') || activeModel.provider :
  'No model';

  useEffectApp(() => {
    document.documentElement.setAttribute('data-theme', tweaks.theme);
  }, [tweaks.theme]);

  // Fetch real data from backend
  async function fetchData() {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/jira/data');
      if (res.ok) {
        setData(await res.json());
        setDataError(null);
      } else if (res.status !== 404) {
        setDataError('Failed to load Jira data');
      }
      // 404 = not configured yet, stay on mock data silently
    } catch (e) {
      // Backend offline — stay on mock data silently
    }
    setLoading(false);
  }

  useEffectApp(() => { fetchData(); }, []);

  // Live-sync counter
  useEffectApp(() => {
    const id = setInterval(() => {
      setSecsAgo((s) => s >= 300 ? 0 : s + 1);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  function fmtSync(s) {
    if (s < 60) return `${s}s ago`;
    return `${Math.floor(s / 60)}m ${s % 60}s ago`;
  }

  const viewTitles = {
    dashboard: { title: 'Team performance', sub: "Real-time view of velocity, bottlenecks, and quality" },
    board: { title: 'Workflow board', sub: 'Figma-style canvas — every developer is a floating frame' },
    table: { title: 'All tickets', sub: 'Sortable, filterable view with configurable columns' }
  };

  return (
    <div className="app">
      <header className="nav">
        <div className="nav__brand">
          <span className="brandmark">WP</span>
          <span>Workpulse</span>
        </div>

        <div className="nav__project">
          <span style={{ width: 18, height: 18, borderRadius: 4, background: 'linear-gradient(135deg,#2563EB,#14B8A6)' }}></span>
          <span>{data.project.name}</span>
          <span className="t-meta" style={{ fontSize: 11 }}>· {data.project.sprint}</span>
          <span className="chev"><Icon.Chevron /></span>
        </div>

        <div className="nav__views" role="tablist">
          <button className={cls(view === 'dashboard' && 'active')} onClick={() => setView('dashboard')}>
            <Icon.Dashboard /> Dashboard
          </button>
          <button className={cls(view === 'board' && 'active')} onClick={() => setView('board')}>
            <Icon.Board /> Board
          </button>
          <button className={cls(view === 'table' && 'active')} onClick={() => setView('table')}>
            <Icon.Table /> Table
          </button>
        </div>

        <AISearchBox
          data={data}
          onOpenTicket={(t) => setTicketDetail(t)}
        />

        <div className="nav__sync" title="Live data from Jira; syncs every 5 minutes">
          <span className="sync-dot"></span>
          {loading
            ? <span>Syncing…</span>
            : <span>Synced <b style={{ color: 'var(--text-1)', fontWeight: 600 }}>{fmtSync(secsAgo)}</b></span>
          }
        </div>

        <button className="btn btn-icon" title="Refresh now" onClick={() => { setSecsAgo(0); fetchData(); }} aria-label="Refresh">
          <Icon.Refresh />
        </button>

        <div className="nav__avatar">MO</div>
      </header>

      <main className="page" data-comment-anchor="963c6fd611-main-105-7">
        <div className="page__header">
          <div className="page__title-block">
            <div className="page__crumb">
              <b>{data.project.name}</b> <span>›</span> <span>{viewTitles[view].title}</span>
            </div>
            <h1 className="t-h1">{viewTitles[view].title}</h1>
            <div className="t-meta" style={{ marginTop: 4 }}>{viewTitles[view].sub}</div>
          </div>
          <div className="page__actions">
            {view !== 'dashboard' &&
            <button className="btn" onClick={() => alert('Export queued — would be wired to /export endpoint.')}>
                Export
              </button>
            }

            <div ref={aiModelBtnRef} style={{ position: 'relative' }}>
              <button
                className={cls('btn ai-model-btn', !activeModel && 'is-empty')}
                onClick={() => setAiModelMenu((v) => !v)}
                title="Select AI model">
                
                <span className="ai-model-btn__ico"><Icon.Sparkles /></span>
                <span className="ai-model-btn__label">
                  <span className="ai-model-btn__caption">AI Model</span>
                  <span className="ai-model-btn__value">{activeLabel}</span>
                </span>
                <Icon.Chevron />
              </button>
              {aiModelMenu &&
              <div className="popover ai-model-popover">
                  <h5>Active AI model</h5>
                  {configuredModels.length === 0 &&
                <div className="ai-model-empty">
                      No models configured yet. Open Settings to add one.
                    </div>
                }
                  {configuredModels.map((m) => {
                  const meta = AI_PROVIDERS.find((p) => p.id === m.provider) || {};
                  const label = m.provider === 'other' ? m.customName || 'Custom model' : meta.label;
                  const checked = activeModel && m.id === activeModel.id;
                  return (
                    <label key={m.id} className="row ai-model-row">
                        <input
                        type="radio"
                        name="active-ai-model"
                        checked={!!checked}
                        onChange={() => {setActiveModelId(m.id);setAiModelMenu(false);}} />
                      
                        <span className="ai-model-row__dot" data-provider={m.provider}></span>
                        <span style={{ flex: 1 }}>{label}</span>
                      </label>);

                })}
                  <div className="popover-sep"></div>
                  <button className="popover-action" onClick={() => {setAiModelMenu(false);setSettingsOpen(true);}}>
                    <Icon.Gear /> Manage in Settings
                  </button>
                </div>
              }
            </div>

            <button className="btn btn-primary" onClick={() => setSettingsOpen(true)} data-comment-anchor="6e347f4e26-button-96-13">
              <Icon.Gear /> Settings
            </button>
          </div>
        </div>

        {view === 'dashboard' &&
        <Dashboard
          data={data}
          onOpenUser={(u) => setDrilldown(u)}
          onOpenView={setView} />

        }
        {view === 'board' &&
        <Board
          data={data}
          onOpenUser={(u) => setDrilldown(u)}
          onOpenTicket={(t) => setTicketDetail(t)} />

        }
        {view === 'table' &&
        <Table
          data={data}
          onOpenUser={(u) => setDrilldown(u)}
          onOpenTicket={(t) => setTicketDetail(t)} />

        }
      </main>

      {drilldown &&
      <DeveloperDrilldown
        user={drilldown}
        data={data}
        onClose={() => setDrilldown(null)}
        onOpenTicket={(t) => {setDrilldown(null);setTimeout(() => setTicketDetail(t), 60);}} />

      }
      {ticketDetail &&
      <TicketModal
        ticket={ticketDetail}
        data={data}
        onClose={() => setTicketDetail(null)}
        onOpenUser={(u) => {setTicketDetail(null);setTimeout(() => setDrilldown(u), 60);}} />

      }
      {settingsOpen &&
      <SettingsModal
        onClose={() => setSettingsOpen(false)}
        onSaveJira={async (creds) => {
          try {
            const res = await fetch('http://localhost:8000/api/jira/settings', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(creds)
            });
            if (res.ok) {
              fetchData();
            } else {
              alert('Failed to save Jira credentials');
            }
          } catch (e) {
            alert('Error saving credentials: ' + e.message);
          }
        }}
        aiKeys={aiKeys}
        setAiKeys={setAiKeys}
        activeModelId={activeModelId}
        setActiveModelId={setActiveModelId} />

      }

      <TweaksPanel title="Tweaks">
        <TweakSection label="Appearance" />
        <TweakRadio
          label="Theme"
          value={tweaks.theme}
          options={[
          { value: 'light', label: 'Light' },
          { value: 'dark', label: 'Dark' }]
          }
          onChange={(v) => setTweak('theme', v)} />
        
        <TweakSection label="Try" />
        <div style={{ fontSize: 11, color: 'rgba(41,38,27,.72)', lineHeight: 1.55 }}>
          • Click any developer on the board or dashboard to open their drill-down<br />
          • Hover a ticket on the board to see its transition history<br />
          • Sort or filter the table; toggle columns via the gear icon<br />
          • Watch the "Synced" counter in the header — it's live
        </div>
      </TweaksPanel>
    </div>);

}

ReactDOM.createRoot(document.getElementById('root')).render(<App data-comment-anchor="ed2ec67a45-div-83-11" />);