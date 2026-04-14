/* ============================================================
   Business Insights Dashboard — app.js
   ============================================================ */

const DATA = {
  iot:  'data/iot.json',
  agri: 'data/agriculture.json',
  ent:  'data/entrepreneurship.json',
};

/* ── Helpers ─────────────────────────────────────────────── */

function $(id) { return document.getElementById(id); }

function fmtDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  if (isNaN(d)) return isoStr;
  const now = new Date();
  const diff = now - d;
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);

  if (mins  < 60)  return `${mins}m ago`;
  if (hours < 24)  return `${hours}h ago`;
  if (days  <  7)  return `${days}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function isNew(isoStr) {
  if (!isoStr) return false;
  return (new Date() - new Date(isoStr)) < 6 * 3600 * 1000; // < 6 hours
}

function strip(html) {
  const tmp = document.createElement('div');
  tmp.innerHTML = html;
  return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim();
}

function excerpt(text, max = 160) {
  const clean = strip(text || '');
  return clean.length > max ? clean.slice(0, max) + '…' : clean;
}

function safeUrl(url) {
  try { return new URL(url).href; }
  catch { return '#'; }
}

/* ── Clock ────────────────────────────────────────────────── */

function startClock() {
  const el = $('liveClock');
  function tick() {
    el.textContent = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  }
  tick();
  setInterval(tick, 1000);
}

/* ── Render ───────────────────────────────────────────────── */

function renderCard(article) {
  const url  = safeUrl(article.link);
  const date = fmtDate(article.pub_date);
  const tag  = isNew(article.pub_date) ? '<span class="new-tag">New</span>' : '';
  const src  = article.source || '';

  return `
    <div class="news-card" onclick="window.open('${url}','_blank',
      'noopener,noreferrer')">
      ${tag}
      <div class="news-card-meta">
        ${src ? `<span class="news-source">${src}</span>` : ''}
        ${date ? `<span class="news-date">${date}</span>` : ''}
      </div>
      <p class="news-title">${article.title}</p>
      ${article.description
        ? `<p class="news-excerpt">${excerpt(article.description)}</p>`
        : ''}
      <div class="news-footer">
        <a href="${url}" target="_blank" rel="noopener noreferrer"
           class="read-more"
           onclick="event.stopPropagation()">
          Read article →
        </a>
      </div>
    </div>`;
}

function renderEmpty(msg) {
  return `
    <div class="state-msg">
      <span class="icon">📭</span>
      <p class="title">No articles yet</p>
      <p>${msg}</p>
    </div>`;
}

function renderError(msg) {
  return `
    <div class="state-msg error-msg">
      <span class="icon">⚠️</span>
      <p class="title">Could not load data</p>
      <p>${msg}</p>
    </div>`;
}

/* ── Fetch & Load ─────────────────────────────────────────── */

async function fetchJSON(url) {
  const res = await fetch(url + '?t=' + Date.now(), { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function loadSection(feedId, url, countId) {
  const feed = $(feedId);
  try {
    const data = await fetchJSON(url);
    const articles = Array.isArray(data.articles) ? data.articles : [];

    $(countId).textContent = articles.length;

    if (!articles.length) {
      feed.innerHTML = renderEmpty('The data file is empty — the next scheduled fetch will populate it.');
      return 0;
    }

    feed.innerHTML = articles.map(renderCard).join('');
    return articles.length;
  } catch (err) {
    console.warn(`[Dashboard] Failed to load ${url}:`, err.message);
    $(countId).textContent = '—';
    feed.innerHTML = renderError(`${err.message}. Will retry on next refresh.`);
    return 0;
  }
}

/* ── Main Load ────────────────────────────────────────────── */

async function loadAll() {
  const btn = $('refreshBtn');
  const tag  = $('updateText');

  btn.disabled = true;
  btn.textContent = 'Refreshing…';
  tag.textContent  = 'Fetching…';

  // Show skeletons
  ['iotFeed', 'agriFeed', 'entFeed'].forEach(id => {
    $(id).innerHTML = `
      <div class="skeleton-wrap">
        <div class="skeleton"></div><div class="skeleton short"></div>
        <div class="skeleton"></div><div class="skeleton short"></div>
        <div class="skeleton"></div><div class="skeleton short"></div>
      </div>`;
  });

  const [n1, n2, n3] = await Promise.all([
    loadSection('iotFeed',  DATA.iot,  'iotCount'),
    loadSection('agriFeed', DATA.agri, 'agriCount'),
    loadSection('entFeed',  DATA.ent,  'entCount'),
  ]);

  const total = n1 + n2 + n3;
  $('totalCount').textContent = total || '—';

  const now = new Date();
  tag.textContent = `Updated ${now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;

  btn.disabled = false;
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
    Refresh`;
}

/* ── Auto-refresh every 30 min ─────────────────────────────── */
setInterval(loadAll, 30 * 60 * 1000);

/* ── Boot ─────────────────────────────────────────────────── */
startClock();
loadAll();
