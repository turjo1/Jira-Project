/* =============================================================
   AI Search Box — global "Ask Workpulse" in the top nav
   Uses window.claude.complete with a digest of team + ticket state
   ============================================================= */
const { useState: useStateAI, useEffect: useEffectAI, useMemo: useMemoAI, useRef: useRefAI } = React;

const AI_SUGGESTIONS = [
  "Who's overloaded right now?",
  "Which tickets are stuck in QA the longest?",
  "Where's the worst bottleneck this sprint?",
  "Any tickets bouncing between statuses?",
  "Summarize the team's current health",
];

function buildContextDigest(data) {
  const { team, tickets, statusAvg, bottleneck, totals, project, userStats } = data;

  const counts = { todo: 0, in_progress: 0, qa: 0, done: 0 };
  for (const t of tickets) counts[t.status]++;

  const devs = team.filter((u) => u.role === 'dev');
  const devLines = devs
    .map((u) => {
      const s = userStats[u.id];
      return `- ${u.name}: ${s.inFlight} open, ${s.avgCycle}d avg cycle, ${s.bounces} bounce${s.bounces === 1 ? '' : 's'}`;
    })
    .join('\n');

  const bouncyTickets = tickets
    .filter((t) => (t.bounces || 0) > 0)
    .sort((a, b) => b.bounces - a.bounces)
    .slice(0, 8);
  const bouncyLines = bouncyTickets
    .map((t) => {
      const a = team.find((u) => u.id === t.assignee);
      return `  · ${t.key} "${t.title}" — ${t.bounces} bounce${t.bounces === 1 ? '' : 's'}, currently ${t.status}, assigned ${a ? a.name : 'unassigned'}`;
    })
    .join('\n');

  const stuck = tickets
    .filter((t) => t.status !== 'done' && t.daysInStatus > 5)
    .sort((a, b) => b.daysInStatus - a.daysInStatus)
    .slice(0, 10);
  const stuckLines = stuck
    .map((t) => {
      const a = team.find((u) => u.id === t.assignee);
      return `  · ${t.key} "${t.title}" — ${t.daysInStatus.toFixed(1)}d in ${t.status} (${a ? a.name : 'unassigned'}, ${t.priority})`;
    })
    .join('\n');

  const critical = tickets
    .filter((t) => t.priority === 'critical' && t.status !== 'done')
    .slice(0, 6);
  const criticalLines = critical
    .map((t) => {
      const a = team.find((u) => u.id === t.assignee);
      return `  · ${t.key} "${t.title}" — ${t.status}, ${a ? a.name : 'unassigned'}, ${t.daysInStatus.toFixed(1)}d in status`;
    })
    .join('\n');

  return `PROJECT: ${project.name} — ${project.sprint}
TOTALS: ${tickets.length} tickets · ${counts.todo} todo · ${counts.in_progress} in progress · ${counts.qa} in QA · ${counts.done} done
TEAM HEALTH: avg cycle ${totals.avgCycle}d · bounce rate ${totals.bounceRate}% · ${totals.open} open
BOTTLENECK STATUS: ${bottleneck} (team-wide avg dwell ${statusAvg[bottleneck]}d)

PER-DEVELOPER LOAD:
${devLines}

TICKETS WITH BOUNCES (top 8):
${bouncyLines || '  (none)'}

LONGEST-DWELLING OPEN TICKETS:
${stuckLines || '  (none)'}

OPEN CRITICAL-PRIORITY:
${criticalLines || '  (none)'}`;
}

/* highlight ticket keys (WALL-123) so users can click → open ticket modal */
function renderAnswerWithLinks(text, tickets, onOpenTicket) {
  if (!text) return null;
  const re = /\b([A-Z]{2,6}-\d+)\b/g;
  const out = [];
  let lastIdx = 0;
  let m;
  let n = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > lastIdx) out.push(text.slice(lastIdx, m.index));
    const key = m[1];
    const t = tickets.find((x) => x.key === key);
    if (t) {
      out.push(
        <button
          key={`k-${n++}`}
          className="ai-search__ticket-link"
          onClick={(e) => {
            e.stopPropagation();
            onOpenTicket(t);
          }}
        >
          {key}
        </button>
      );
    } else {
      out.push(key);
    }
    lastIdx = m.index + key.length;
  }
  if (lastIdx < text.length) out.push(text.slice(lastIdx));
  return out;
}

function AISearchBox({ data, onOpenTicket }) {
  const [query, setQuery] = useStateAI('');
  const [open, setOpen] = useStateAI(false);
  const [loading, setLoading] = useStateAI(false);
  const [answer, setAnswer] = useStateAI(null);
  const [error, setError] = useStateAI(null);
  const [recent, setRecent] = useStateAI([]); // last few asked queries
  const inputRef = useRefAI(null);
  const wrapRef = useRefAI(null);

  const digest = useMemoAI(() => buildContextDigest(data), [data]);

  /* Cmd/Ctrl + K to focus */
  useEffectAI(() => {
    function onKey(e) {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
      if (e.key === 'Escape') {
        if (document.activeElement === inputRef.current) inputRef.current.blur();
        setOpen(false);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  /* close on outside click */
  useEffectAI(() => {
    if (!open) return;
    function onDoc(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  async function ask(q) {
    const text = (q ?? query).trim();
    if (!text || loading) return;
    setLoading(true);
    setError(null);
    setAnswer({ q: text, text: '' });
    try {
      const prompt = `You are a senior engineering manager's analytics assistant inside Workpulse, a Jira analytics tool. Answer the user's question using ONLY the data digest below. Be concise (2-4 sentences). When referencing tickets, use their exact key (e.g. WALL-12) so they can be linked. Name specific developers when relevant. If the data doesn't contain the answer, say so plainly — don't speculate.

=== TEAM DATA DIGEST ===
${digest}
=== END DIGEST ===

User's question: ${text}`;
      const out = await window.claude.complete(prompt);
      setAnswer({ q: text, text: (out || '').trim() });
      setRecent((r) => [text, ...r.filter((x) => x !== text)].slice(0, 4));
    } catch (e) {
      setError(e?.message || "Couldn't reach the AI service.");
      setAnswer(null);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    ask();
  }

  const showSuggestions = open && !loading && !answer;
  const showAnswer = open && (loading || answer || error);

  return (
    <div className="ai-search" ref={wrapRef}>
      <form className="ai-search__form" onSubmit={onSubmit}>
        <span className="ai-search__icon"><Icon.Sparkles /></span>
        <input
          ref={inputRef}
          className="ai-search__input"
          type="text"
          value={query}
          placeholder="Ask Workpulse anything…"
          onFocus={() => setOpen(true)}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query && !loading && (
          <button
            type="button"
            className="ai-search__clear"
            aria-label="Clear"
            onClick={() => { setQuery(''); setAnswer(null); setError(null); inputRef.current?.focus(); }}
          >
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
          </button>
        )}
        {!query && !loading && <kbd className="ai-search__kbd">⌘K</kbd>}
        {loading && <span className="ai-search__spinner" aria-hidden="true"></span>}
      </form>

      {open && (
        <div className="ai-search__panel">
          {showSuggestions && (
            <div>
              {recent.length > 0 && (
                <>
                  <div className="ai-search__head">Recent</div>
                  <div className="ai-search__suggestions">
                    {recent.map((s) => (
                      <button
                        key={s}
                        className="ai-search__sugg"
                        onClick={() => { setQuery(s); ask(s); }}
                      >
                        <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4"/>
                          <path d="M8 5v3l2 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                        </svg>
                        <span style={{ flex: 1 }}>{s}</span>
                      </button>
                    ))}
                  </div>
                </>
              )}
              <div className="ai-search__head">Try asking</div>
              <div className="ai-search__suggestions">
                {AI_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="ai-search__sugg"
                    onClick={() => { setQuery(s); ask(s); }}
                  >
                    <Icon.Sparkles />
                    <span style={{ flex: 1 }}>{s}</span>
                    <span className="ai-search__sugg-arrow">↵</span>
                  </button>
                ))}
              </div>
              <div className="ai-search__footnote">
                Answers use live data from <b>{data.project.name}</b> · {data.tickets.length} tickets, {data.team.length} people
              </div>
            </div>
          )}

          {showAnswer && (
            <div className="ai-search__answer-wrap">
              {answer?.q && (
                <div className="ai-search__qrow">
                  <span className="ai-search__qmark">Q</span>
                  <span className="ai-search__qtext">{answer.q}</span>
                </div>
              )}
              {loading && (
                <div className="ai-search__loading">
                  <span className="ai-search__spinner"></span>
                  <span>Asking the team's data…</span>
                </div>
              )}
              {!loading && error && (
                <div className="ai-search__error">{error}</div>
              )}
              {!loading && !error && answer?.text && (
                <div className="ai-search__answer">
                  <span className="ai-search__amark"><Icon.Sparkles /></span>
                  <div>{renderAnswerWithLinks(answer.text, data.tickets, (t) => { setOpen(false); onOpenTicket(t); })}</div>
                </div>
              )}
              {!loading && answer && (
                <div className="ai-search__actions">
                  <button
                    className="ai-search__action"
                    onClick={() => { setAnswer(null); setQuery(''); inputRef.current?.focus(); }}
                  >
                    Ask another
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

window.AISearchBox = AISearchBox;
