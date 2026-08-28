// ---------------------------------------------------------------
// formatting helpers
// ---------------------------------------------------------------

function money(n) {
  if (n === null || n === undefined) return '—';
  const v = Number(n);
  const sign = v < 0 ? '–' : '';
  return sign + '$' + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
}

function pct(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toFixed(1) + '%';
}

function int(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('en-US');
}

function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------
// shared styling — same token system across every page
// ---------------------------------------------------------------

const STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Serif:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

  :root {
    --bg: #f2f4f3; --bg-raised: #ffffff; --ink: #12181f; --ink-soft: #4b5560; --ink-faint: #7c8790;
    --line: #d8dedc; --line-strong: #b7c0be; --accent: #a8661f; --accent-ink: #ffffff;
    --long: #1f7a5c; --long-bg: #e3f1ea; --short: #ac3636; --short-bg: #f6e6e5; --mono-bg: #e9ede9;
    --shadow: 0 1px 2px rgba(18,24,31,0.06), 0 8px 24px -12px rgba(18,24,31,0.12);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #0d1116; --bg-raised: #151b21; --ink: #e8ecef; --ink-soft: #9aa7b0; --ink-faint: #6d7981;
      --line: #262f38; --line-strong: #38434d; --accent: #dd9a49; --accent-ink: #14100a;
      --long: #56b78a; --long-bg: #12261f; --short: #e07872; --short-bg: #2a1616; --mono-bg: #1a2129;
      --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 28px -14px rgba(0,0,0,0.6);
    }
  }
  :root[data-theme="dark"] {
    --bg: #0d1116; --bg-raised: #151b21; --ink: #e8ecef; --ink-soft: #9aa7b0; --ink-faint: #6d7981;
    --line: #262f38; --line-strong: #38434d; --accent: #dd9a49; --accent-ink: #14100a;
    --long: #56b78a; --long-bg: #12261f; --short: #e07872; --short-bg: #2a1616; --mono-bg: #1a2129;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 28px -14px rgba(0,0,0,0.6);
  }

  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--ink);
    font-family: 'IBM Plex Serif', Georgia, 'Times New Roman', serif;
    line-height: 1.6; -webkit-font-smoothing: antialiased;
  }
  ::selection { background: var(--accent); color: var(--accent-ink); }
  a { color: inherit; }
  p { margin: 0 0 1rem; }

  .page { max-width: 980px; margin: 0 auto; padding: 3.5rem 1.5rem 5rem; }

  header.hero { margin-bottom: 2.5rem; }

  .eyebrow {
    font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 0.78rem;
    letter-spacing: 0.14em; text-transform: uppercase; color: var(--accent);
    display: flex; align-items: center; gap: 0.6em; margin-bottom: 0.9rem;
  }
  .eyebrow::before { content: ""; display: inline-block; width: 1.6em; height: 2px; background: var(--accent); }
  .eyebrow a { text-decoration: none; }

  h1.title {
    font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700;
    font-size: clamp(2.1rem, 5vw, 3rem); letter-spacing: -0.01em; margin: 0 0 0.55rem; text-wrap: balance;
  }
  .subtitle {
    font-family: 'IBM Plex Serif', serif; font-style: italic; color: var(--ink-soft);
    font-size: 1.1rem; margin: 0; max-width: 46em; text-wrap: balance;
  }

  .summary-strip {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1px;
    background: var(--line); border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
    margin: 2.25rem 0 0; box-shadow: var(--shadow);
  }
  .summary-strip .stat { background: var(--bg-raised); padding: 1.1rem 1.2rem; }
  .summary-strip .value {
    font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 1.45rem;
    font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
  }
  .summary-strip .value.pos { color: var(--long); }
  .summary-strip .value.neg { color: var(--short); }
  .summary-strip .label {
    font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 0.7rem; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--ink-faint); margin-top: 0.3rem;
  }

  section.roster, section.rule { margin-top: 3.25rem; padding-top: 2rem; border-top: 1px solid var(--line); }

  .roster-head { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
  .roster-count { font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; color: var(--ink-faint); }

  h2 {
    font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700; font-size: 1.4rem;
    margin: 0; letter-spacing: -0.005em; text-wrap: balance;
  }

  .rule-head { display: flex; align-items: baseline; gap: 0.85rem; margin-bottom: 1rem; }
  .rule-num {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; color: var(--ink-faint);
    border: 1px solid var(--line-strong); border-radius: 5px; padding: 0.1rem 0.45rem; flex: none;
  }
  section.rule > p, section.rule > div > p { max-width: 68ch; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.1rem; }

  .card {
    display: flex; flex-direction: column; border: 1px solid var(--line); border-radius: 12px;
    background: var(--bg-raised); padding: 1.4rem 1.4rem 1.2rem; box-shadow: var(--shadow);
    text-decoration: none; color: var(--ink); transition: transform 0.15s ease, border-color 0.15s ease;
  }
  .card:hover, .card:focus-visible { border-color: var(--accent); transform: translateY(-2px); }
  .card:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .card .kind {
    font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 0.7rem;
    letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); margin-bottom: 0.6rem;
  }
  .card h3 { font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700; font-size: 1.25rem; margin: 0 0 0.4rem; }
  .card .desc { font-family: 'IBM Plex Serif', serif; font-size: 0.92rem; color: var(--ink-soft); margin: 0 0 1.1rem; flex: 1; }
  .card .mini-stats { display: flex; gap: 1.1rem; padding-top: 0.9rem; border-top: 1px solid var(--line); font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }
  .card .mini-stats .mv { font-weight: 600; font-size: 1rem; display: block; }
  .card .mini-stats .mv.pos { color: var(--long); }
  .card .mini-stats .mv.neg { color: var(--short); }
  .card .mini-stats .ml { font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 0.64rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--ink-faint); margin-top: 0.15rem; }
  .card .go { margin-top: 1rem; font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 0.8rem; color: var(--accent); display: flex; align-items: center; gap: 0.35em; }
  .card .go svg { width: 0.9em; height: 0.9em; transition: transform 0.15s ease; }
  .card:hover .go svg { transform: translateX(3px); }
  .card.empty { align-items: center; justify-content: center; text-align: center; color: var(--ink-faint); box-shadow: none; background: transparent; border-style: dashed; border-color: var(--line-strong); min-height: 170px; }
  .card.empty .kind { color: var(--ink-faint); }
  .card.empty p { margin: 0; font-family: 'IBM Plex Serif', serif; font-size: 0.88rem; }

  .split { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1.1rem 0 1.4rem; }
  @media (max-width: 620px) { .split { grid-template-columns: 1fr; } }
  .side { border-radius: 10px; padding: 1.1rem 1.2rem; border: 1px solid var(--line); }
  .side.long { background: var(--long-bg); }
  .side.short { background: var(--short-bg); }
  .side .tag { font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700; font-size: 0.76rem; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.5rem; display: block; }
  .side.long .tag { color: var(--long); }
  .side.short .tag { color: var(--short); }
  .side p { margin: 0; font-size: 0.96rem; }

  .formula {
    font-family: 'IBM Plex Mono', monospace; background: var(--mono-bg); border: 1px solid var(--line);
    border-radius: 10px; padding: 1rem 1.25rem; font-size: 0.92rem; overflow-x: auto; line-height: 1.75;
    white-space: pre-wrap;
  }

  footer { margin-top: 3.5rem; padding-top: 1.5rem; border-top: 1px solid var(--line); font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 0.8rem; color: var(--ink-faint); letter-spacing: 0.02em; }

  @media (prefers-reduced-motion: reduce) { .card { transition: none; } }

  /* ---- research notes: extends the same tokens, no P&L assumed ---- */
  .card.note .kind { color: var(--ink-faint); }
  .card.note .mini-stats .mv { color: var(--ink); }

  .note-table-wrap { overflow-x: auto; margin: 1.1rem 0 1.4rem; }
  table.note-table { border-collapse: collapse; width: 100%; font-size: 0.88rem; min-width: 380px; }
  table.note-table th, table.note-table td { text-align: left; padding: 0.5rem 0.85rem; border-bottom: 1px solid var(--line); font-family: 'IBM Plex Sans Condensed', sans-serif; }
  table.note-table th { font-size: 0.68rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink-faint); font-weight: 600; }
  table.note-table td.num, table.note-table th.num { font-family: 'IBM Plex Mono', monospace; text-align: right; font-variant-numeric: tabular-nums; }
  table.note-table tr:last-child td { border-bottom: none; }

  .callout { background: var(--mono-bg); border-left: 3px solid var(--accent); border-radius: 0 10px 10px 0; padding: 1rem 1.25rem; margin: 1.1rem 0 1.4rem; font-size: 0.95rem; }
  .callout b { color: var(--accent); }

  .chart-box { border: 1px solid var(--line); border-radius: 10px; background: var(--bg-raised); padding: 1.25rem 1.25rem 1rem; margin: 1.1rem 0 1.4rem; }
  .chart-box .ct { font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 0.8rem; color: var(--ink-soft); margin: 0 0 0.2rem; }
  .chart-box .cs { font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 0.72rem; color: var(--ink-faint); margin: 0 0 0.9rem; }
  .chart-box svg { width: 100%; height: auto; display: block; overflow: visible; }
  .chart-box .axl { font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; fill: var(--ink-faint); }
  .chart-box .gl { stroke: var(--line); stroke-width: 1; }

  .bar-row { margin: 0.9rem 0; }
  .bar-row .rh { display: flex; justify-content: space-between; font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 0.82rem; margin-bottom: 0.35rem; }
  .bar-row .rh .n { color: var(--ink-faint); font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; }
  .bar-track { display: flex; height: 24px; border-radius: 6px; overflow: hidden; border: 1px solid var(--line); }
  .bar-seg { display: flex; align-items: center; justify-content: center; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #fff; }
  .seg-short { background: var(--short); }
  .seg-long { background: var(--long); }
  .seg-amb { background: var(--ink-faint); }
  .chart-legend { display: flex; gap: 1.1rem; flex-wrap: wrap; margin-top: 0.85rem; font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 0.75rem; color: var(--ink-soft); }
  .chart-legend span { display: inline-flex; align-items: center; gap: 0.4em; }
  .chart-legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

  ul.caveats { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.85rem; }
  ul.caveats li { padding-left: 1.3rem; position: relative; font-size: 0.94rem; color: var(--ink-soft); }
  ul.caveats li::before { content: "\\2014"; position: absolute; left: 0; top: 0; color: var(--ink-faint); }
  ul.caveats b { color: var(--ink); }
`;

function layout(title, description, body) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<link rel="icon" href="data:,">
<style>${STYLE}</style>
</head>
<body>
${body}
</body>
</html>`;
}

// ---------------------------------------------------------------
// hub page (the portfolio)
// ---------------------------------------------------------------

function cardHtml(s) {
  return `<a class="card" href="/strategy/${encodeURIComponent(s.slug)}">
    <div class="kind">${esc(s.category || 'Strategy')}</div>
    <h3>${esc(s.name)}</h3>
    <p class="desc">${esc(s.description || '')}</p>
    <div class="mini-stats">
      <div><span class="mv pos">${money(s.net_pnl)}</span><span class="ml">Net</span></div>
      <div><span class="mv">${pct(s.win_rate)}</span><span class="ml">Win rate</span></div>
      <div><span class="mv">${int(s.trades)}</span><span class="ml">Trades</span></div>
    </div>
    <div class="go">View full rule set
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12L12 4M12 4H6M12 4V10"/></svg>
    </div>
  </a>`;
}

function noteCardHtml(n) {
  const stats = n.stats || [];
  const mini = stats.slice(0, 3).map(st => `
      <div><span class="mv${st.pos ? ' pos' : ''}${st.neg ? ' neg' : ''}">${esc(st.value)}</span><span class="ml">${esc(st.label)}</span></div>`).join('');
  return `<a class="card note" href="/notes/${encodeURIComponent(n.slug)}">
    <div class="kind">${esc(n.eyebrow || 'Research note')}</div>
    <h3>${esc(n.title)}</h3>
    <p class="desc">${esc(n.subtitle || '')}</p>
    <div class="mini-stats">${mini}</div>
    <div class="go">Read the study
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12L12 4M12 4H6M12 4V10"/></svg>
    </div>
  </a>`;
}

function hubPage(strategies, notes = []) {
  const totalNet = strategies.reduce((sum, s) => sum + (s.net_pnl !== null ? Number(s.net_pnl) : 0), 0);
  const bestWinRate = strategies.length ? Math.max(...strategies.map(s => s.win_rate !== null ? Number(s.win_rate) : 0)) : null;
  const totalTrades = strategies.reduce((sum, s) => sum + (s.trades || 0), 0);

  const cards = strategies.map(cardHtml).join('\n');
  const emptyCard = `<div class="card empty">
    <div class="kind">Next slot</div>
    <p>Add your next backtested strategy to the database and it appears here automatically.</p>
  </div>`;

  const noteCards = notes.map(noteCardHtml).join('\n');
  const notesSection = `<section class="roster">
    <div class="roster-head"><h2>Research</h2><span class="roster-count">${notes.length} listed</span></div>
    <div class="grid">
      ${noteCards || '<div class="card empty"><div class="kind">Next slot</div><p>Descriptive studies and market research live here — no P&amp;L required.</p></div>'}
    </div>
  </section>`;

  const body = `<div class="page">
  <header class="hero">
    <div class="eyebrow">Backtest portfolio</div>
    <h1 class="title">Strategy Desk</h1>
    <p class="subtitle">Every intraday strategy you've backtested, pulled live from the database — each card opens the full rule set and results.</p>

    <div class="summary-strip">
      <div class="stat"><div class="value">${strategies.length}</div><div class="label">Strategies</div></div>
      <div class="stat"><div class="value pos">${money(totalNet)}</div><div class="label">Combined net result</div></div>
      <div class="stat"><div class="value">${int(totalTrades)}</div><div class="label">Trades backtested</div></div>
      <div class="stat"><div class="value">${bestWinRate !== null ? pct(bestWinRate) : '—'}</div><div class="label">Top win rate</div></div>
    </div>
  </header>

  <section class="roster">
    <div class="roster-head"><h2>Strategies</h2><span class="roster-count">${strategies.length} listed</span></div>
    <div class="grid">
      ${cards}
      ${emptyCard}
    </div>
  </section>

  ${notesSection}

  <footer>Strategy Desk — personal backtest reference, served live from Postgres. Figures as supplied by each strategy's backtest; not a performance guarantee.</footer>
</div>`;

  return layout('Strategy Desk', 'Live portfolio of backtested strategies', body);
}

// ---------------------------------------------------------------
// note detail page (descriptive research, no trade metrics required)
// ---------------------------------------------------------------

function notePage(n) {
  const stats = n.stats || [];
  const statHtml = stats.map(st => `<div class="stat"><div class="value${st.pos ? ' pos' : ''}${st.neg ? ' neg' : ''}">${esc(st.value)}</div><div class="label">${esc(st.label)}</div></div>`).join('');

  const sections = (n.sections || []).map(s => section(s.num, s.title, s.html)).join('\n');

  const body = `<div class="page">
  <header class="hero">
    <div class="eyebrow"><a href="/">&larr; Strategy Desk</a></div>
    <h1 class="title">${esc(n.title)}</h1>
    <p class="subtitle">${esc(n.subtitle || '')}</p>

    <div class="summary-strip">
      ${statHtml}
    </div>
  </header>

  ${sections}

  <footer>Strategy Desk — research note, served live from Postgres. Descriptive statistics, not a backtested strategy.</footer>
</div>`;

  return layout(n.title, n.subtitle || '', body);
}

// ---------------------------------------------------------------
// detail page (one strategy, rendered from its rules JSON)
// ---------------------------------------------------------------

function section(num, title, innerHtml) {
  return `<section class="rule">
    <div class="rule-head"><span class="rule-num">${esc(num)}</span><h2>${esc(title)}</h2></div>
    ${innerHtml}
  </section>`;
}

function splitLongShort(longText, shortText) {
  return `<div class="split">
    <div class="side long"><span class="tag">Long</span><p>${esc(longText)}</p></div>
    <div class="side short"><span class="tag">Short</span><p>${esc(shortText)}</p></div>
  </div>`;
}

function detailPage(s) {
  const r = s.rules || {};
  const sections = [];
  let n = 1;
  const pad = (x) => String(x).padStart(2, '0');

  if (r.vwap && r.vwap.definition) {
    sections.push(section(pad(n++), 'VWAP', `<p>${esc(r.vwap.definition)}</p>`));
  }

  if (r.entry) {
    let inner = '';
    if (r.entry.note) inner += `<p>${esc(r.entry.note)}</p>`;
    if (r.entry.long || r.entry.short) inner += splitLongShort(r.entry.long || '', r.entry.short || '');
    const tail = [];
    if (r.entry.no_trade) tail.push(esc(r.entry.no_trade));
    if (r.entry.entry_price) tail.push('Entry price: ' + esc(r.entry.entry_price));
    if (tail.length) inner += `<p>${tail.join(' ')}</p>`;
    sections.push(section(pad(n++), 'Entry', inner));
  }

  if (r.initial_stop) {
    let inner = '';
    if (r.initial_stop.method) inner += `<p>${esc(r.initial_stop.method)}</p>`;
    if (r.initial_stop.long || r.initial_stop.short) inner += splitLongShort(r.initial_stop.long || '', r.initial_stop.short || '');
    const tail = [];
    if (r.initial_stop.lookback_window) tail.push(esc(r.initial_stop.lookback_window));
    if (r.initial_stop.fallback) tail.push(esc(r.initial_stop.fallback));
    if (tail.length) inner += `<p>${tail.join(' ')}</p>`;
    sections.push(section(pad(n++), 'Initial stop', inner));
  }

  if (r.position_sizing) {
    const ps = r.position_sizing;
    const lines = [ps.risk_dist, ps.contracts].filter(Boolean).map(esc).join('\n');
    sections.push(section(pad(n++), 'Position sizing', `<div class="formula">${lines}</div>`));
  }

  if (r.stop_management) {
    const sm = r.stop_management;
    let inner = '';
    ['freeze', 'on_trigger', 'after_trigger', 'if_never_stopped'].forEach((k) => {
      if (sm[k]) inner += `<p>${esc(sm[k])}</p>`;
    });
    sections.push(section(pad(n++), 'Stop management', inner));
  }

  if (r.notes) {
    sections.push(section(pad(n++), 'Why this shape produces these numbers', `<p>${esc(r.notes)}</p>`));
  }

  const breakeven = s.trades_reaching_breakeven !== null && s.trades_reaching_breakeven !== undefined
    ? `${int(s.trades_reaching_breakeven)}/${int(s.trades)}`
    : '—';

  const body = `<div class="page">
  <header class="hero">
    <div class="eyebrow"><a href="/">&larr; Strategy Desk</a></div>
    <h1 class="title">${esc(s.name)}</h1>
    <p class="subtitle">${esc(s.description || '')}</p>

    <div class="summary-strip">
      <div class="stat"><div class="value pos">${money(s.net_pnl)}</div><div class="label">Net result</div></div>
      <div class="stat"><div class="value">${pct(s.win_rate)}</div><div class="label">Win rate</div></div>
      <div class="stat"><div class="value">${int(s.trades)}</div><div class="label">Trades</div></div>
      <div class="stat"><div class="value">${breakeven}</div><div class="label">Reach breakeven</div></div>
      <div class="stat"><div class="value">${money(s.avg_win)}</div><div class="label">Avg win</div></div>
      <div class="stat"><div class="value">${money(s.avg_loss)}</div><div class="label">Avg loss</div></div>
    </div>
  </header>

  ${sections.join('\n')}

  <footer>Strategy Desk — served live from Postgres.</footer>
</div>`;

  return layout(s.name, s.description || '', body);
}

module.exports = { hubPage, detailPage, notePage, layout };
