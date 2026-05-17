/* Print app: renders Dashboard, Board, and Table as three stacked print pages. */
function PrintApp() {
  const data = window.JIRA_DATA;
  const today = new Date('2026-05-16T14:32:00Z');
  const dateStr = today.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  function PageHead({ crumb, title, sub }) {
    return (
      <div className="print-page__head">
        <div className="print-page__title">
          <span className="brandmark">WP</span>
          <div>
            <h1>{title}</h1>
            <div className="sub">{sub}</div>
          </div>
        </div>
        <div className="print-page__meta">
          <span className="crumb">{crumb}</span>
          <span>{data.project.name} · {data.project.sprint}</span>
          <span>Exported {dateStr}</span>
        </div>
      </div>
    );
  }

  // Board view footer hint (the small line under the canvas) — wrap it so we can hide it
  const noOp = () => {};

  return (
    <div className="print-doc">
      <section className="print-page" data-screen-label="01 Dashboard">
        <PageHead
          crumb="01 · Dashboard"
          title="Team performance"
          sub="Real-time view of velocity, bottlenecks, and quality" />
        <Dashboard data={data} onOpenUser={noOp} onOpenView={noOp} />
      </section>

      <section className="print-page" data-screen-label="02 Board">
        <PageHead
          crumb="02 · Workflow board"
          title="Workflow board"
          sub="Per-developer view of in-flight work across Todo · Doing · QA · Done" />
        <div className="board-print-wrap">
          <Board data={data} onOpenUser={noOp} onOpenTicket={noOp} />
        </div>
      </section>

      <section className="print-page" data-screen-label="03 Table">
        <PageHead
          crumb="03 · All tickets"
          title="All tickets"
          sub={`${data.tickets.length} tickets — sorted by time in current status`} />
        <Table data={data} onOpenUser={noOp} onOpenTicket={noOp} />
      </section>
    </div>);

}

/* Mount when fonts and Babel are ready */
function mountPrint() {
  ReactDOM.createRoot(document.getElementById('root')).render(<PrintApp />);

  /* auto-print once fonts have loaded and React has committed */
  const fontsReady = (document.fonts && document.fonts.ready) || Promise.resolve();
  fontsReady.then(() => {
    /* wait two RAFs so React flushes layout, then a 500ms safety margin */
    requestAnimationFrame(() => requestAnimationFrame(() => {
      setTimeout(() => { window.print(); }, 500);
    }));
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountPrint);
} else {
  mountPrint();
}
