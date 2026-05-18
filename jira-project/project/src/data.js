window.JIRA_DATA = null;

// Mock data removed — app fetches live from http://localhost:8000/api/jira/data
(function () { // kept so Workpulse.html script tag doesn't break
  const team = [
    { id: 'u1', name: 'Maya Okafor',    role: 'po',  initials: 'MO', hue: 168 },
    { id: 'u2', name: 'Diego Alvarez',  role: 'dev', initials: 'DA', hue: 217 },
    { id: 'u3', name: 'Priya Raman',    role: 'dev', initials: 'PR', hue: 217 },
    { id: 'u4', name: 'Soren Hale',     role: 'dev', initials: 'SH', hue: 217 },
    { id: 'u5', name: 'Lena Voss',      role: 'dev', initials: 'LV', hue: 217 },
    { id: 'u6', name: 'Kai Tanaka',     role: 'qa',  initials: 'KT', hue: 271 },
    { id: 'u7', name: 'Amara Bell',     role: 'qa',  initials: 'AB', hue: 271 },
  ];

  const STATUSES = ['todo', 'in_progress', 'qa', 'done'];

  const titles = [
    'Add Apple Pay to checkout sheet',
    'Fix race condition in transfer confirmation',
    'Onboarding: skip ID verification for sub-$50 accounts',
    'Update KYC error states for new copy',
    'Card freeze toggle missing haptic feedback',
    'Migrate transactions list to virtualized scroller',
    'Spinning loader stuck after biometric auth',
    'Bank linking: handle Plaid 2FA timeout',
    'Settings → Notifications: pull-to-refresh',
    'Send money flow: contact picker iPad layout',
    'Decimal input rounds incorrectly in EUR',
    'Push tokens not refreshed after re-install',
    'Empty state for activity feed week 1',
    'Add tooltip to recurring transfer toggle',
    'Audit accessibility labels for transaction rows',
    'Rate limit retry on /v2/transfers',
    'Show pending balance in nav header',
    'Wallet → Cards: reorder via drag handle',
    'Crash on cold-start when keychain locked',
    'In-app review prompt after 3rd successful send',
    'Localize currency formatting for fr-CA',
    'Replace deprecated FaceID API call',
    'Sticky CTA hidden behind keyboard on Android',
    'Background sync skips when on cellular',
    'Add merchant logos to recent transactions',
    'Investigate elevated 401s on /me endpoint',
    'Receipt PDF: include FX rate footnote',
    'Polish empty card art for premium tier',
    'Beta: split payments between two cards',
    'Recurring transfers: skip weekends toggle',
    'Reduce app size below 60MB',
    'Pin entry: shake animation on wrong code',
    'Disable copy on masked card numbers',
    'Sync contacts on first launch only',
    'Fix double-tap dismissing share sheet',
    'Add analytics for funnel drop at OTP',
    'Region picker missing flag for India',
    'Banner: scheduled maintenance Sat 2am',
    'Audit Sentry: top 5 crashes for v4.2',
    'Quick action: pay last sender',
  ];

  function mulberry32(a) {
    return function () {
      let t = (a += 0x6d2b79f5);
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const rand = mulberry32(42);

  function pick(arr) { return arr[Math.floor(rand() * arr.length)]; }

  // Status distribution: top of funnel -> done
  function pickStatus(i) {
    const r = rand();
    if (r < 0.18) return 'todo';
    if (r < 0.42) return 'in_progress';
    if (r < 0.58) return 'qa';
    return 'done';
  }

  const devs = team.filter(t => t.role === 'dev');
  const qas  = team.filter(t => t.role === 'qa');

  const today = new Date('2026-05-16T14:32:00Z');
  function daysAgo(d) {
    const t = new Date(today);
    t.setDate(t.getDate() - d);
    return t;
  }

  const tickets = titles.map((title, i) => {
    const key = `WALL-${1240 + i}`;
    const status = pickStatus(i);
    const assignee = pick(devs);
    const reporter = pick(team);

    // Build a plausible transition history
    const createdAt = daysAgo(Math.floor(rand() * 28) + 1);
    const history = [{ status: 'todo', at: createdAt, by: reporter.id }];
    let cursor = new Date(createdAt);

    const bumpDays = (min, max) => {
      cursor = new Date(cursor.getTime() + (min + rand() * (max - min)) * 86400000);
      return new Date(cursor);
    };

    let bounces = 0;

    if (status === 'in_progress' || status === 'qa' || status === 'done') {
      history.push({ status: 'in_progress', at: bumpDays(0.2, 2.5), by: assignee.id });
    }
    if (status === 'qa' || status === 'done') {
      history.push({ status: 'qa', at: bumpDays(0.5, 4), by: assignee.id });
    }
    if (status === 'done') {
      history.push({ status: 'done', at: bumpDays(0.5, 3), by: pick(qas).id });
      // Maybe bounce
      if (rand() < 0.22) {
        bounces = 1;
        history.push({ status: 'in_progress', at: bumpDays(0.2, 2), by: pick(qas).id });
        history.push({ status: 'qa', at: bumpDays(0.4, 2), by: assignee.id });
        history.push({ status: 'done', at: bumpDays(0.3, 1.5), by: pick(qas).id });
        if (rand() < 0.15) {
          bounces = 2;
          history.push({ status: 'qa', at: bumpDays(0.3, 1.2), by: pick(qas).id });
          history.push({ status: 'done', at: bumpDays(0.3, 1.2), by: pick(qas).id });
        }
      }
    }

    const last = history[history.length - 1];
    // Clamp every event to be <= today (don't let synthetic transitions stride into the future)
    for (const h of history) {
      if (h.at > today) h.at = new Date(today.getTime() - Math.floor(rand() * 30) * 60000);
    }
    // For non-done, override current status to match history end
    const currentStatus = last.status;
    const enteredStatusAt = last.at;
    const daysInStatus = +((today - enteredStatusAt) / 86400000).toFixed(1);

    const cycleTimeDays = currentStatus === 'done'
      ? +((last.at - createdAt) / 86400000).toFixed(1)
      : null;

    const priorities = ['low','med','med','med','high','high','critical'];
    const labels = pick([['ios'],['android'],['ios','android'],['backend'],['ios','perf'],['accessibility'],['design-debt']]);

    return {
      key, title, assignee: assignee.id, reporter: reporter.id,
      status: currentStatus,
      createdAt, enteredStatusAt, daysInStatus,
      cycleTimeDays, bounces, history,
      priority: pick(priorities),
      labels,
      story_points: pick([1,2,2,3,3,5,5,8]),
    };
  });

  // Derived: per-user stats
  const userStats = {};
  for (const u of team) {
    const mine = tickets.filter(t => t.assignee === u.id);
    const done = mine.filter(t => t.status === 'done');
    const cycle = done.map(t => t.cycleTimeDays).filter(Boolean);
    const avgCycle = cycle.length ? cycle.reduce((a,b)=>a+b,0)/cycle.length : 0;
    const bounces = mine.reduce((a,t)=>a+t.bounces,0);
    userStats[u.id] = {
      total: mine.length,
      done: done.length,
      inFlight: mine.filter(t=>['in_progress','qa'].includes(t.status)).length,
      avgCycle: +avgCycle.toFixed(1),
      bounces,
      bounceRate: done.length ? +(bounces / done.length * 100).toFixed(0) : 0,
      cycleSamples: cycle,
    };
  }

  // Bottleneck: avg time-in-status across all tickets
  const statusTimes = { todo: [], in_progress: [], qa: [], done: [] };
  for (const t of tickets) {
    for (let i = 0; i < t.history.length - 1; i++) {
      const cur = t.history[i], nxt = t.history[i+1];
      const days = (nxt.at - cur.at) / 86400000;
      if (statusTimes[cur.status]) statusTimes[cur.status].push(days);
    }
    // open ticket's current dwell
    if (t.status !== 'done') statusTimes[t.status].push(t.daysInStatus);
  }
  const statusAvg = {};
  for (const s of STATUSES) {
    const arr = statusTimes[s];
    statusAvg[s] = arr.length ? +(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1) : 0;
  }
  const bottleneck = Object.entries(statusAvg)
    .filter(([k])=>k!=='done')
    .sort((a,b)=>b[1]-a[1])[0][0];

  // Cycle trend last 8 weeks (synthetic)
  const cycleTrend = [22, 21, 23, 20, 19, 19, 18, 17.5];
  const bounceTrend = [18, 16, 17, 15, 14, 13, 12, 11];
  const openTrend = [54, 58, 56, 51, 47, 45, 43, 40];

  const totals = {
    open: tickets.filter(t => t.status !== 'done').length,
    done: tickets.filter(t => t.status === 'done').length,
    bounceRate: (() => {
      const done = tickets.filter(t=>t.status==='done');
      const bounced = done.filter(t=>t.bounces>0).length;
      return done.length ? +(bounced/done.length*100).toFixed(0) : 0;
    })(),
    avgCycle: (() => {
      const arr = tickets.filter(t=>t.cycleTimeDays!=null).map(t=>t.cycleTimeDays);
      return arr.length ? +(arr.reduce((a,b)=>a+b,0)/arr.length).toFixed(1) : 0;
    })(),
  };

  return {
    team, tickets, userStats, statusAvg, bottleneck,
    cycleTrend, bounceTrend, openTrend, totals,
    statuses: STATUSES,
    project: { key: 'WALL', name: 'Wallet Mobile', sprint: 'Sprint 47 · Pulse' },
  };
})();
