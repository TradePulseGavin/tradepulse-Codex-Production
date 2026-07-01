(function () {
  var page = document.body.dataset.page || '';
  function byId(id) { return document.getElementById(id); }
  function html(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]; }); }
  function showAppError(error) {
    var banner = byId('app-error-banner');
    if (!banner) {
      banner = document.createElement('section');
      banner.id = 'app-error-banner';
      banner.className = 'notice app-error';
      var nav = document.querySelector('.topnav');
      if (nav && nav.parentNode) nav.parentNode.insertBefore(banner, nav.nextSibling);
      else document.body.insertBefore(banner, document.body.firstChild);
    }
    banner.innerHTML = '<b>Panel could not load.</b> TradePulse is still running in safe demo mode. Refresh this page or continue from another section.';
    if (window.console && console.warn) console.warn('TradePulse panel error', error);
  }
  window.addEventListener('unhandledrejection', function (event) { showAppError(event.reason); });
  var authClient = null;
  function supabaseClient() {
    if (authClient || !window.supabase || !window.TRADEPULSE_SUPABASE_URL || !window.TRADEPULSE_SUPABASE_KEY) return authClient;
    authClient = window.supabase.createClient(window.TRADEPULSE_SUPABASE_URL, window.TRADEPULSE_SUPABASE_KEY);
    return authClient;
  }
  function demoPlan() {
    var saved = localStorage.getItem('tradepulse_demo_plan') || 'all_access';
    return ['free', 'pro', 'elite', 'all_access'].indexOf(saved) === -1 ? 'all_access' : saved;
  }
  async function authContext() {
    if (window.TRADEPULSE_AUTH_READY) {
      try { await window.TRADEPULSE_AUTH_READY; } catch (e) {}
    }
    var client = supabaseClient();
    if (!client) return null;
    var result = await client.auth.getSession();
    var session = result && result.data ? result.data.session : null;
    if (!session) return null;
    return { token: session.access_token, user: session.user };
  }
  async function requestOptions(options, payload) {
    var ctx = await authContext();
    var headers = Object.assign({}, options && options.headers ? options.headers : {});
    if (ctx && ctx.token) headers.Authorization = 'Bearer ' + ctx.token;
    var bodyPayload = payload;
    if (ctx && ctx.user && bodyPayload && typeof bodyPayload === 'object' && !Array.isArray(bodyPayload) && !bodyPayload.user_id) {
      bodyPayload = Object.assign({}, bodyPayload, { user_id: ctx.user.id });
    }
    if (!ctx && bodyPayload && typeof bodyPayload === 'object' && !Array.isArray(bodyPayload) && !bodyPayload.plan) {
      bodyPayload = Object.assign({}, bodyPayload, { plan: demoPlan() });
    }
    return Object.assign({}, options || {}, {
      headers: headers,
      body: bodyPayload === undefined ? options && options.body : JSON.stringify(bodyPayload || {})
    });
  }
  async function getJson(url, options) { var res = await fetch(url, await requestOptions(options || {})); if (!res.ok) throw new Error('Request failed: ' + res.status); return await res.json(); }
  async function postJson(url, payload) { return await getJson(url, await requestOptions({ method: 'POST', headers: { 'Content-Type': 'application/json' } }, payload)); }
  function setStatus(text) { var el = byId('connection-status'); if (el) el.textContent = text; }
  var dashboardEventsBound = false;
  var alertEventsBound = false;
  var sessionPrepEventsBound = false;
  var reviewCenterEventsBound = false;
  var riskLabEventsBound = false;
  var onboardingEventsBound = false;
  var journalEventsBound = false;
  var paperTradeEventsBound = false;
  var screenshotEventsBound = false;
  var strategyEventsBound = false;
  var watchlistEventsBound = false;
  var newsEventsBound = false;
  var scannerEventsBound = false;
  var schoolPayload = null;
  var chartAnnotations = [];
  var lastMainChartPayload = null;
  function listItem(title, body, meta) { return '<div class="list-item"><strong>' + html(title) + '</strong><div class="muted">' + html(body || '') + '</div>' + (meta ? '<div class="pill">' + html(meta) + '</div>' : '') + '</div>'; }
  function kv(label, value) { return '<div class="metric-card"><span class="muted">' + html(label) + '</span><br><strong>' + html(value) + '</strong></div>'; }
  function loadChartAnnotations() {
    try {
      var saved = JSON.parse(localStorage.getItem('tradepulse_chart_annotations') || '[]');
      chartAnnotations = Array.isArray(saved) ? saved.slice(0, 8) : [];
    } catch (e) {
      chartAnnotations = [];
    }
  }
  function saveChartAnnotations() {
    try { localStorage.setItem('tradepulse_chart_annotations', JSON.stringify(chartAnnotations.slice(0, 8))); } catch (e) {}
  }
  function drawAnnotations(ctx, width, height, annotations) {
    if (!annotations || !annotations.length) return;
    ctx.save();
    ctx.font = '12px system-ui';
    annotations.forEach(function (mark, index) {
      var offset = index * 14;
      ctx.strokeStyle = mark.color || '#f4bf50';
      ctx.fillStyle = mark.color || '#f4bf50';
      ctx.lineWidth = 1.5;
      ctx.setLineDash(mark.type === 'vertical' ? [5, 5] : []);
      if (mark.type === 'horizontal') {
        var y = Math.max(52, Math.min(height - 42, mark.y || (height * 0.36 + offset)));
        ctx.beginPath(); ctx.moveTo(36, y); ctx.lineTo(width - 18, y); ctx.stroke();
        ctx.fillText(mark.label || 'Key level', 42, y - 7);
      } else if (mark.type === 'vertical') {
        var x = Math.max(52, Math.min(width - 52, mark.x || (width * 0.7 - offset)));
        ctx.beginPath(); ctx.moveTo(x, 36); ctx.lineTo(x, height - 34); ctx.stroke();
        ctx.fillText(mark.label || 'Review time', x + 6, 50);
      } else if (mark.type === 'trend') {
        ctx.setLineDash([]);
        ctx.beginPath(); ctx.moveTo(width * 0.22, height * 0.72); ctx.lineTo(width * 0.72, height * 0.34); ctx.stroke();
        ctx.fillText(mark.label || 'Trendline', width * 0.52, height * 0.38);
      } else if (mark.type === 'note') {
        ctx.setLineDash([]);
        var boxX = Math.max(44, width - 236);
        var boxY = 48 + offset;
        ctx.fillStyle = 'rgba(17, 24, 32, .92)';
        ctx.strokeStyle = mark.color || '#f4bf50';
        ctx.fillRect(boxX, boxY, 198, 44);
        ctx.strokeRect(boxX, boxY, 198, 44);
        ctx.fillStyle = mark.color || '#f4bf50';
        ctx.fillText(mark.label || 'Wait for confirmation', boxX + 10, boxY + 26);
      }
    });
    ctx.restore();
  }
  function drawCandles(canvas, payload, annotations) {
    if (!canvas || !payload || !payload.candles) return;
    var ctx = canvas.getContext('2d');
    var rect = canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(320, Math.floor(rect.width * dpr));
    canvas.height = Math.max(220, Math.floor(rect.height * dpr));
    ctx.scale(dpr, dpr);
    var width = canvas.width / dpr;
    var height = canvas.height / dpr;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#0a0d11';
    ctx.fillRect(0, 0, width, height);
    var pad = 34;
    var candles = payload.candles;
    var highs = candles.map(function (c) { return c.high; });
    var lows = candles.map(function (c) { return c.low; });
    var max = Math.max.apply(null, highs);
    var min = Math.min.apply(null, lows);
    var range = Math.max(1, max - min);
    function y(price) { return pad + (max - price) / range * (height - pad * 2); }
    ctx.strokeStyle = '#1c2530';
    ctx.lineWidth = 1;
    for (var g = 0; g < 5; g++) { var yy = pad + g * (height - pad * 2) / 4; ctx.beginPath(); ctx.moveTo(pad, yy); ctx.lineTo(width - 14, yy); ctx.stroke(); }
    var step = (width - pad - 20) / candles.length;
    var bodyW = Math.max(3, Math.min(10, step * .62));
    candles.forEach(function (c, i) {
      var x = pad + i * step + step / 2;
      var up = c.close >= c.open;
      ctx.strokeStyle = up ? '#7bd88f' : '#ff7474';
      ctx.fillStyle = up ? '#7bd88f' : '#ff7474';
      ctx.beginPath(); ctx.moveTo(x, y(c.high)); ctx.lineTo(x, y(c.low)); ctx.stroke();
      var top = y(Math.max(c.open, c.close));
      var bottom = y(Math.min(c.open, c.close));
      ctx.fillRect(x - bodyW / 2, top, bodyW, Math.max(2, bottom - top));
    });
    var closes = candles.map(function (c) { return c.close; });
    ctx.strokeStyle = '#44d7b6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    closes.forEach(function (close, i) { var x = pad + i * step + step / 2; var yy = y(close); if (i === 0) ctx.moveTo(x, yy); else ctx.lineTo(x, yy); });
    ctx.stroke();
    ctx.fillStyle = '#9ca8b6';
    ctx.font = '12px system-ui';
    ctx.fillText(payload.symbol + ' - ' + payload.mode + ' - ' + payload.timeframe, pad, 18);
    ctx.fillText(max.toFixed(2), width - 72, pad + 4);
    ctx.fillText(min.toFixed(2), width - 72, height - pad);
    drawAnnotations(ctx, width, height, annotations);
  }
  async function drawChartFor(canvasId, symbol, timeframe, live) { var data = await getJson('/api/chart-data?symbol=' + encodeURIComponent(symbol || 'SPY') + '&timeframe=' + encodeURIComponent(timeframe || '5m') + (live ? '&live=true' : '')); if (canvasId === 'main-chart') lastMainChartPayload = data; drawCandles(byId(canvasId), data, canvasId === 'main-chart' ? chartAnnotations : []); return data; }
  function renderWatchlist(el, items) { if (!el) return; el.innerHTML = (items || []).map(function (item) { return listItem(item.symbol + ' ' + item.price, item.trend_status, 'Score ' + item.tradepulse_score + '/10'); }).join(''); }
  function watchlistItems(list) { return list.items || list.watchlist_items || []; }
  function renderWatchlistManager(payload) {
    payload = payload || {};
    var lists = payload.watchlists || [];
    var target = byId('watchlist-target');
    if (target) {
      target.innerHTML = lists.length ? lists.map(function (list) {
        return '<option value="' + html(list.id || '') + '">' + html(list.name || 'Watchlist') + '</option>';
      }).join('') : '<option value="">Default watchlist</option>';
    }
    var el = byId('watchlists-list');
    if (!el) return;
    if (!lists.length) {
      el.innerHTML = listItem('No watchlists yet', 'Create one or save a symbol to start organizing research.');
      return;
    }
    el.innerHTML = lists.map(function (list) {
      var items = watchlistItems(list);
      var symbols = items.length ? items.map(function (item) {
        return '<span class="pill">' + html(item.symbol || '-') + '</span>';
      }).join(' ') : '<span class="muted">No symbols yet.</span>';
      var notes = items.slice(0, 3).map(function (item) {
        return (item.symbol || 'Symbol') + ': ' + (item.notes || item.asset_type || 'Research');
      }).join(' | ');
      return '<div class="list-item"><div class="panel-title-row"><strong>' + html(list.name || 'Watchlist') + '</strong><span class="pill">' + html(items.length) + ' symbols</span></div><div class="tool-row">' + symbols + '</div><div class="muted">' + html(notes || 'Add notes to track why each symbol matters.') + '</div></div>';
    }).join('');
  }
  async function loadWatchlistManager() {
    var data = await getJson('/api/watchlists');
    renderWatchlistManager(data);
    return data;
  }
  async function initWatchlists() {
    await loadWatchlistManager();
    if (watchlistEventsBound) return;
    watchlistEventsBound = true;
    var create = byId('create-watchlist');
    if (create) create.addEventListener('click', async function () {
      var saved = await postJson('/api/watchlists', { name: byId('new-watchlist-name').value || 'New Watchlist' });
      byId('watchlist-page-result').innerHTML = '<p>' + html(saved.message || 'Watchlist saved.') + '</p><p class="muted">Mode: ' + html(saved.mode || 'demo') + '</p>';
      await loadWatchlistManager();
    });
    var save = byId('save-watchlist-item');
    if (save) save.addEventListener('click', async function () {
      var payload = {
        watchlist_id: byId('watchlist-target').value,
        symbol: byId('watchlist-page-symbol').value,
        asset_type: byId('watchlist-page-asset').value,
        notes: byId('watchlist-page-notes').value
      };
      var saved = await postJson('/api/watchlist-items', payload);
      byId('watchlist-page-result').innerHTML = '<p>' + html(saved.message || 'Symbol saved.') + '</p>' + kv('Symbol', saved.item && saved.item.symbol ? saved.item.symbol : payload.symbol) + '<p class="muted">Watchlists are for research organization only.</p>';
      await loadWatchlistManager();
    });
  }
  function renderScanner(el, payload) { if (!el) return; el.innerHTML = (payload.items || []).map(function (item) { return '<div class="scan-item"><div class="panel-title-row"><strong>' + html(item.symbol) + '</strong><span class="pill">' + html(item.setup_score) + '/10</span></div><p>' + html(item.setup_note) + '</p><div class="muted">Trend: ' + html(item.trend_status) + ' | Volume: ' + html(item.volume_status) + ' | News: ' + html(item.news_risk) + '</div></div>'; }).join(''); }
  function renderScannerPage(payload) {
    payload = payload || {};
    var items = payload.items || [];
    var average = items.length ? (items.reduce(function (sum, item) { return sum + Number(item.setup_score || 0); }, 0) / items.length).toFixed(1) : '0.0';
    var highNews = items.filter(function (item) { return String(item.news_risk || '').toLowerCase() === 'high'; }).length;
    var summary = byId('scanner-summary');
    if (summary) summary.innerHTML = kv('Symbols scanned', items.length) + kv('Average setup', average + '/10') + kv('High news risk', highNews);
    renderScanner(byId('scanner-page-results'), payload);
  }
  async function runScannerPage() {
    var symbols = byId('scanner-symbols').value || 'SPY,QQQ,NVDA';
    var data = await postJson('/api/scanner/run', { symbols: symbols });
    renderScannerPage(data);
    return data;
  }
  async function initScannerPage() {
    var dashboard = await getJson('/api/demo/dashboard');
    var input = byId('scanner-symbols');
    if (input && dashboard.watchlist) input.value = dashboard.watchlist.map(function (item) { return item.symbol; }).join(',');
    await runScannerPage();
    if (scannerEventsBound) return;
    scannerEventsBound = true;
    var runButton = byId('run-scanner-page');
    if (runButton) runButton.addEventListener('click', runScannerPage);
  }
  function renderAlerts(el, payload) {
    if (!el) return;
    var evaluated = payload && payload.evaluated ? payload.evaluated : [];
    if (!evaluated.length) {
      el.innerHTML = listItem('No alerts yet', 'Create demo alerts to track review conditions.');
      return;
    }
    el.innerHTML = evaluated.slice(0, 8).map(function (alert) {
      var title = (alert.symbol || 'Alert') + ' - ' + (alert.triggered ? 'Review now' : 'Watching');
      var body = alert.message || ((alert.alert_type || 'condition') + ' ' + (alert.operator || '') + ' ' + (alert.target_value || ''));
      return listItem(title, body, alert.triggered ? 'Triggered' : 'Waiting');
    }).join('');
  }
  async function loadNewsResearch() {
    var impact = await getJson('/api/news-impact');
    var changed = await getJson('/api/what-changed');
    var providers = await getJson('/api/providers/status');
    var impactEl = byId('news-impact-list');
    if (impactEl) {
      impactEl.innerHTML = (impact.items || []).map(function (item) {
        return listItem((item.symbol || 'Market') + ' - ' + (item.impact || 'Review'), (item.type || 'News') + ' | ' + (item.trade_risk || item.chart_context || ''), item.volatility_risk || 'Risk');
      }).join('');
    }
    var changedEl = byId('what-changed-list');
    if (changedEl) {
      changedEl.innerHTML = (changed.items || []).map(function (item) { return listItem(item, 'Demo context to verify before planning.'); }).join('');
    }
    var providerEl = byId('news-provider-status');
    if (providerEl) {
      var news = providers.news || {};
      providerEl.innerHTML = kv('Yahoo RSS', news.yahoo_rss ? 'Available' : 'Off') + kv('Finnhub', news.finnhub ? 'Configured' : 'Missing') + kv('Alpha Vantage', news.alpha_vantage ? 'Configured' : 'Missing') + kv('NewsAPI', news.newsapi ? 'Configured' : 'Missing');
    }
  }
  function renderNewsHeadlines(payload) {
    var el = byId('news-headlines');
    if (!el) return;
    var items = payload.items || [];
    if (!items.length) {
      el.innerHTML = listItem('No provider headlines loaded', 'Use refresh when providers or internet access are available.');
      return;
    }
    el.innerHTML = items.slice(0, 20).map(function (item) {
      var sentiment = item.sentiment && item.sentiment.label ? item.sentiment.label : 'neutral';
      var meta = (item.provider || 'Provider') + ' | ' + (item.urgency || 'background') + ' | ' + sentiment;
      var title = item.url ? '<a href="' + html(item.url) + '" target="_blank" rel="noopener">' + html(item.headline || 'Headline') + '</a>' : html(item.headline || 'Headline');
      return '<div class="list-item"><strong>' + title + '</strong><div class="muted">' + html(item.summary || '') + '</div><div class="pill">' + html(meta) + '</div></div>';
    }).join('');
  }
  async function initNews() {
    await loadNewsResearch();
    renderNewsHeadlines({ items: [] });
    if (newsEventsBound) return;
    newsEventsBound = true;
    var refresh = byId('refresh-news');
    if (refresh) refresh.addEventListener('click', async function () {
      var symbols = byId('news-symbols').value || 'SPY,QQQ,NVDA';
      var data = await getJson('/api/news?save=false&symbols=' + encodeURIComponent(symbols));
      renderNewsHeadlines(data);
    });
  }
  function prepText(value) {
    if (Array.isArray(value)) return value.join('\n');
    return String(value || '');
  }
  function setField(id, value) {
    var el = byId(id);
    if (el) el.value = prepText(value);
  }
  function renderSessionPrepSummary(el, payload) {
    if (!el) return;
    var suggested = payload && payload.suggested_plan ? payload.suggested_plan : {};
    var latest = payload && payload.latest ? payload.latest : null;
    var cards = [
      listItem('Focus symbols', latest ? (latest.focus_symbols || suggested.focus_symbols) : (suggested.focus_symbols || 'SPY,QQQ,NVDA'), latest ? 'Latest saved session' : 'Suggested from watchlist'),
      listItem('Risk focus', latest ? (latest.risk_notes || suggested.risk_notes) : (suggested.risk_notes || 'Keep the plan research-only and paper-practice first.')),
      listItem('Before paper trade', 'Open Session Prep, write the plan, then use Paper Planner only if the setup is still clean.', latest ? 'Saved' : 'Ready')
    ];
    el.innerHTML = cards.join('');
  }
  function renderSessionPrep(payload) {
    payload = payload || {};
    var suggested = payload.suggested_plan || {};
    setField('prep-symbols', suggested.focus_symbols || 'SPY,QQQ,NVDA');
    setField('prep-market-notes', suggested.market_notes || '');
    setField('prep-risk-notes', suggested.risk_notes || '');
    setField('prep-rules', suggested.rules_for_today || []);
    setField('prep-avoid', suggested.avoid_conditions || []);
    var suggestedEl = byId('session-prep-suggested');
    if (suggestedEl) {
      var alerts = suggested.alerts_to_review && suggested.alerts_to_review.length ? prepText(suggested.alerts_to_review) : 'No triggered demo alerts right now.';
      suggestedEl.innerHTML = [
        listItem('Session goal', suggested.session_goal || 'Build disciplined paper-trading habits first.'),
        listItem('Focus symbols', suggested.focus_symbols || 'SPY,QQQ,NVDA', 'Watchlist'),
        listItem('Risk limits', suggested.risk_notes || 'Keep the plan conservative and written.'),
        listItem('Rules for today', prepText(suggested.rules_for_today || [])),
        listItem('Avoid conditions', prepText(suggested.avoid_conditions || [])),
        listItem('Alerts to review', alerts)
      ].join('');
    }
    var history = byId('session-prep-history');
    var items = payload.items || [];
    if (history) {
      if (!items.length) {
        history.innerHTML = listItem('No saved session prep yet', "Save today's plan to start building your prep history.");
      } else {
        history.innerHTML = items.slice(0, 10).map(function (item) {
          var body = (item.focus_symbols || 'No symbols') + ' | ' + (item.market_notes || item.risk_notes || 'No notes yet.');
          return listItem(item.session_label || 'Session prep', body, item.status || 'planned');
        }).join('');
      }
    }
  }
  function dashboardSymbols(data) {
    var fromWatchlist = (data && data.watchlist ? data.watchlist : []).map(function (item) { return item.symbol; }).filter(Boolean);
    var input = byId('symbols');
    if (input && input.value.trim()) {
      return input.value.split(',').map(function (symbol) { return symbol.trim().toUpperCase(); }).filter(Boolean);
    }
    return fromWatchlist.length ? fromWatchlist : ['SPY'];
  }
  function currentLayout() {
    var modeEl = byId('layout-mode');
    var hidden = [];
    document.querySelectorAll('.panel-toggle').forEach(function (input) {
      if (!input.checked && input.dataset.panel) hidden.push(input.dataset.panel);
    });
    return { mode: modeEl ? modeEl.value : 'command', hidden_panels: hidden };
  }
  function applyLayout(layout) {
    layout = layout || {};
    var modeEl = byId('layout-mode');
    var hidden = Array.isArray(layout.hidden_panels) ? layout.hidden_panels : [];
    if (modeEl && layout.mode) modeEl.value = layout.mode;
    document.querySelectorAll('.panel-toggle').forEach(function (input) {
      input.checked = hidden.indexOf(input.dataset.panel) === -1;
    });
    document.querySelectorAll('[data-panel-card]').forEach(function (card) {
      card.classList.toggle('is-hidden', hidden.indexOf(card.dataset.panelCard) !== -1);
    });
    var grid = byId('dashboard-grid');
    if (grid) grid.dataset.mode = modeEl ? modeEl.value : (layout.mode || 'command');
  }
  function bindDashboardEvents() {
    if (dashboardEventsBound) return;
    dashboardEventsBound = true;
    var refresh = byId('refresh-dashboard');
    if (refresh) refresh.addEventListener('click', initDashboard);
    var save = byId('save-layout');
    if (save) save.addEventListener('click', async function () {
      var saved = await postJson('/api/dashboard-layout', { layout: currentLayout() });
      setStatus(saved.message || 'Layout saved');
    });
    var mode = byId('layout-mode');
    if (mode) mode.addEventListener('change', function () { applyLayout(currentLayout()); });
    document.querySelectorAll('.panel-toggle').forEach(function (input) {
      input.addEventListener('change', function () { applyLayout(currentLayout()); });
    });
    var addSymbol = byId('add-watchlist-symbol');
    if (addSymbol) addSymbol.addEventListener('click', async function () {
      var input = byId('watchlist-symbol');
      var symbol = input ? input.value.trim().toUpperCase().replace('$', '') : '';
      if (!symbol) { setStatus('Add a symbol first'); return; }
      setStatus('Saving ' + symbol);
      await postJson('/api/watchlist-items', { symbol: symbol, asset_type: 'stock' });
      if (input) input.value = '';
      await initDashboard();
      setStatus(symbol + ' saved to watchlist');
    });
    var symbolInput = byId('watchlist-symbol');
    if (symbolInput) symbolInput.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        event.preventDefault();
        var button = byId('add-watchlist-symbol');
        if (button) button.click();
      }
    });
  }
  function renderDashboard(data) {
    renderWatchlist(byId('watchlist-panel'), data.watchlist || []);
    renderScanner(byId('scanner-panel'), data.scanner || {});
    var symbolsInput = byId('symbols');
    if (symbolsInput && data.watchlist) symbolsInput.value = data.watchlist.map(function (item) { return item.symbol; }).join(',');
    var first = (data.watchlist || [])[0] || {};
    var score = byId('score-panel');
    if (score) score.innerHTML = '<div class="score-number">' + html(first.tradepulse_score || '7.5') + '</div><p>Research score only. Trend and volume are decent, while news risk still needs review.</p>';
    var mood = data.market_mood || {};
    var moodEl = byId('market-mood-panel');
    if (moodEl) moodEl.innerHTML = kv('Mood', mood.mood) + kv('SPY trend', mood.spy_trend) + kv('Best environment', mood.best_environment);
    var news = byId('news-impact-panel');
    if (news) news.innerHTML = (data.news_impact || []).map(function (n) { return listItem(n.symbol + ' - ' + n.impact, n.type, n.volatility_risk); }).join('');
    var changed = byId('changed-panel');
    if (changed) changed.innerHTML = (data.what_changed || []).map(function (x) { return listItem(x, 'Review before making a decision.'); }).join('');
    var journal = byId('journal-summary-panel');
    if (journal) { var j = data.journal_summary || {}; journal.innerHTML = kv('Trades', j.total_trades) + kv('Wins / losses', String(j.wins) + ' / ' + String(j.losses)) + kv('Focus', j.focus); }
    var memory = byId('memory-panel');
    if (memory) {
      var cards = data.memory_summary && data.memory_summary.cards ? data.memory_summary.cards : [];
      var nextReviews = data.memory_summary && data.memory_summary.next_reviews ? data.memory_summary.next_reviews : [];
      memory.innerHTML = cards.slice(0, 4).map(function (card) { return listItem(card.label, card.detail, card.value); }).join('') + (nextReviews.length ? '<div class="response-box"><strong>Next reviews</strong><ul>' + nextReviews.map(function (item) { return '<li>' + html(item) + '</li>'; }).join('') + '</ul></div>' : '');
    }
    renderAlerts(byId('alerts-panel'), data.alert_summary || {});
    renderSessionPrepSummary(byId('session-prep-panel'), data.session_prep || {});
    var risk = byId('risk-panel');
    if (risk) { var r = data.risk_rules || {}; risk.innerHTML = kv('Max trades/day', r.max_trades_per_day) + kv('Stop required', r.require_stop_loss ? 'Yes' : 'No') + kv('Avoid news window', r.avoid_news_minutes + ' min'); }
    var school = byId('school-progress-panel');
    if (school) school.innerHTML = (data.school_modules || []).slice(0, 4).map(function (m) { return listItem(m.lesson, m.track, m.status); }).join('');
    applyLayout(data.dashboard_layout || currentLayout());
  }
  async function initLanding() { try { await drawChartFor('hero-chart', 'QQQ', '5m'); } catch (e) {} }
  async function initDashboard() {
    bindDashboardEvents();
    try {
      setStatus('Loading demo workspace');
      var data = await getJson('/api/demo/dashboard');
      renderDashboard(data);
      var symbols = dashboardSymbols(data);
      await drawChartFor('dashboard-chart', symbols[0] || 'SPY', '5m');
      try {
        await postJson('/api/activity', { last_dashboard_snapshot: { mode: currentLayout().mode, symbols: symbols } });
      } catch (activityError) {}
      setStatus('Demo data loaded');
    } catch (e) {
      setStatus('Demo load error');
    }
  }
  async function initCharts() {
    loadChartAnnotations();
    var payload = await getJson('/api/demo/dashboard'); renderWatchlist(byId('chart-watchlist'), payload.watchlist || []);
    async function load() { var symbol = byId('chart-symbol').value || 'SPY'; var tf = byId('timeframe').value || '5m'; var live = byId('live-data') && byId('live-data').checked; var data = await drawChartFor('main-chart', symbol, tf, live); var panel = byId('chart-ai-panel'); if (panel) panel.innerHTML = kv('Mode', data.mode) + kv('Source', data.data_source || 'demo') + kv('Trend', data.snapshot.trend_status) + kv('News risk', data.snapshot.news_risk) + kv('Research note', data.snapshot.setup_note) + (data.warning ? '<p class="muted">' + html(data.warning) + '</p>' : ''); }
    byId('load-chart').addEventListener('click', load); byId('save-chart-layout').addEventListener('click', function () { saveChartAnnotations(); showExplain('Chart workspace saved locally with ' + chartAnnotations.length + ' demo annotation(s). Supabase persistence is next.'); });
    var explain = byId('explain-vwap'); if (explain) explain.addEventListener('click', function () { explainTerm('VWAP'); });
    document.querySelectorAll('[data-tool]').forEach(function (btn) { btn.addEventListener('click', function () {
      var tool = btn.dataset.tool;
      if (tool === 'clear') {
        chartAnnotations = [];
        saveChartAnnotations();
        if (lastMainChartPayload) drawCandles(byId('main-chart'), lastMainChartPayload, chartAnnotations);
        showExplain('Chart annotations cleared for this demo workspace.');
        return;
      }
      var labels = {
        horizontal: 'Key level',
        vertical: 'Review time',
        trend: 'Trendline',
        note: 'Wait for confirmation'
      };
      chartAnnotations.push({ type: tool, label: labels[tool] || 'Chart mark' });
      chartAnnotations = chartAnnotations.slice(-8);
      saveChartAnnotations();
      if (lastMainChartPayload) drawCandles(byId('main-chart'), lastMainChartPayload, chartAnnotations);
      showExplain((labels[tool] || 'Chart mark') + ' added. Demo annotations are local planning marks only.');
    }); });
    load();
  }
  async function initCopilot() {
    document.querySelectorAll('[data-prompt]').forEach(function (btn) { btn.addEventListener('click', function () { byId('copilot-message').value = btn.dataset.prompt; }); });
    byId('ask-copilot').addEventListener('click', async function () { var out = byId('copilot-response'); out.textContent = 'Thinking...'; var data = await postJson('/api/copilot', { message: byId('copilot-message').value, symbol: byId('copilot-symbol').value, asset_type: byId('copilot-asset').value, timeframe: byId('copilot-timeframe').value }); out.innerHTML = '<p>' + html(data.response) + '</p><ul>' + data.risk_notes.map(function (n) { return '<li>' + html(n) + '</li>'; }).join('') + '</ul><p class="muted">Setup score: ' + html(data.setup_score) + '/10 | ' + html(data.ai_provider) + '</p>' + (data.warning ? '<p class="muted">' + html(data.warning) + '</p>' : ''); });
    byId('run-checklist').addEventListener('click', async function () { var data = await postJson('/api/trade-checklist', { entry: byId('check-entry').value, stop: byId('check-stop').value, target: byId('check-target').value, reason: byId('check-reason').value, invalidation: byId('check-invalid').value, news: byId('check-news').value }); byId('checklist-result').innerHTML = kv('Setup Quality', data.setup_quality + '/10') + kv('Risk Clarity', data.risk_clarity) + kv('News Risk', data.news_risk) + '<ul>' + data.rule_violations.map(function (v) { return '<li>' + html(v) + '</li>'; }).join('') + '</ul>'; });
  }
  async function loadAlerts() {
    var data = await getJson('/api/alerts');
    renderAlerts(byId('alert-list'), data);
    return data;
  }
  async function initAlerts() {
    await loadAlerts();
    if (alertEventsBound) return;
    alertEventsBound = true;
    byId('save-alert').addEventListener('click', async function () {
      var payload = {
        symbol: byId('alert-symbol').value,
        alert_type: byId('alert-type').value,
        operator: byId('alert-operator').value,
        target_value: byId('alert-target').value,
        notes: byId('alert-notes').value,
        enabled: true
      };
      var saved = await postJson('/api/alerts', payload);
      byId('alert-save-result').innerHTML = '<p>' + html(saved.message || 'Alert saved.') + '</p>' + listItem(saved.evaluated.symbol || payload.symbol, saved.evaluated.message || '', saved.evaluated.triggered ? 'Triggered' : 'Waiting');
      await loadAlerts();
    });
    byId('evaluate-alerts').addEventListener('click', async function () {
      var data = await postJson('/api/alerts/evaluate', {});
      renderAlerts(byId('alert-list'), data);
    });
  }
  async function loadSessionPrep() {
    var data = await getJson('/api/session-prep');
    renderSessionPrep(data);
    return data;
  }
  async function initSessionPrep() {
    await loadSessionPrep();
    if (sessionPrepEventsBound) return;
    sessionPrepEventsBound = true;
    byId('save-session-prep').addEventListener('click', async function () {
      var payload = {
        session_label: byId('prep-session-label').value,
        focus_symbols: byId('prep-symbols').value,
        market_notes: byId('prep-market-notes').value,
        risk_notes: byId('prep-risk-notes').value,
        rules_for_today: byId('prep-rules').value,
        avoid_conditions: byId('prep-avoid').value,
        status: 'planned'
      };
      var saved = await postJson('/api/session-prep', payload);
      byId('session-prep-result').innerHTML = '<p>' + html(saved.message || 'Session prep saved.') + '</p><p class="muted">Mode: ' + html(saved.mode || 'demo') + '</p>';
      await loadSessionPrep();
    });
  }
  function renderReviewCenter(payload) {
    payload = payload || {};
    var metrics = payload.metrics || {};
    var metricsEl = byId('review-center-metrics');
    if (metricsEl) {
      metricsEl.innerHTML = kv('Prep plans', metrics.saved_prep_plans || 0) + kv('Triggered alerts', metrics.triggered_alerts || 0) + kv('Risk scenarios', metrics.risk_scenarios || 0) + kv('Paper plans', metrics.paper_plans || 0) + kv('Reviewed paper', metrics.reviewed_paper_plans || 0) + kv('Journaled paper', metrics.journalized_paper_plans || 0) + kv('Journal entries', metrics.journal_entries || 0) + kv('Screenshots', metrics.screenshot_reviews || 0);
    }
    var queue = byId('review-center-queue');
    var tasks = payload.tasks || [];
    if (!queue) return;
    if (!tasks.length) {
      queue.innerHTML = listItem('Review queue is empty', 'Add prep, alerts, paper plans, screenshots, or journal entries to build the daily review loop.');
      return;
    }
    queue.innerHTML = tasks.map(function (task) {
      return '<div class="list-item"><div class="panel-title-row"><strong>' + html(task.title || 'Review task') + '</strong><a class="button small secondary" href="' + html(task.href || '/dashboard') + '">Open</a></div><div class="muted">' + html(task.body || '') + '</div><div class="pill">' + html(task.status || 'Review') + '</div></div>';
    }).join('');
  }
  async function loadReviewCenter() {
    var data = await getJson('/api/review-center');
    renderReviewCenter(data);
    return data;
  }
  async function initReviewCenter() {
    await loadReviewCenter();
    if (reviewCenterEventsBound) return;
    reviewCenterEventsBound = true;
    var refresh = byId('refresh-review-center');
    if (refresh) refresh.addEventListener('click', loadReviewCenter);
  }
  function renderProgress(data) {
    data = data || {};
    var score = byId('progress-score');
    if (score) score.textContent = String(data.readiness_score || 0) + '/100';
    var summary = byId('progress-summary');
    if (summary) {
      var latest = data.latest || {};
      summary.innerHTML = kv('Mode', data.mode || 'demo-local') + kv('Latest paper', latest.paper_trade ? (latest.paper_trade.symbol || 'Saved') : 'None') + kv('Latest journal', latest.journal_entry ? (latest.journal_entry.symbol || 'Saved') : 'None');
    }
    var milestones = byId('progress-milestones');
    if (milestones) {
      milestones.innerHTML = (data.milestones || []).map(function (item) {
        return '<article class="metric-card"><span class="muted">' + html(item.label) + '</span><br><strong>' + html(item.value) + '</strong><div class="pill">' + html(item.status || 'Ready') + '</div></article>';
      }).join('');
    }
    var actions = byId('progress-actions');
    if (actions) {
      actions.innerHTML = (data.next_actions || []).map(function (item) {
        return '<a class="list-item action-link" href="' + html(item.href || '#') + '"><strong>' + html(item.title) + '</strong><div class="muted">' + html(item.body || '') + '</div></a>';
      }).join('');
    }
    var focus = byId('progress-focus');
    if (focus) {
      var review = data.weekly_review || {};
      focus.innerHTML = kv('Trades journaled', review.total_trades || 0) + kv('Wins / losses', String(review.wins || 0) + ' / ' + String(review.losses || 0)) + kv('Repeated mistake', review.most_repeated_mistake || 'Keep collecting entries') + kv('Next focus', review.focus_next_week || 'Keep the review loop steady');
    }
  }
  async function initProgress() {
    renderProgress(await getJson('/api/progress'));
  }
  function renderRiskLab(payload) {
    payload = payload || {};
    var calc = payload.calculation || {};
    var summary = byId('risk-lab-summary');
    if (summary) {
      summary.innerHTML = [
        kv('Suggested max size', calc.suggested_max_size == null ? 0 : calc.suggested_max_size),
        kv('Planned risk', '$' + (calc.planned_risk || 0)),
        kv('Max risk', '$' + (calc.max_risk_dollars || 0)),
        kv('Reward / risk', calc.reward_to_risk || 0),
        listItem(calc.within_rules ? 'Inside current inputs' : 'Needs review', (calc.flags || []).join(' '), calc.within_rules ? 'OK' : 'Review')
      ].join('');
    }
    var list = byId('risk-scenario-list');
    var items = payload.items || [];
    if (list) {
      if (!items.length) {
        list.innerHTML = listItem('No saved scenarios yet', 'Calculate a paper risk scenario to save it here.');
      } else {
        list.innerHTML = items.slice(0, 10).map(function (item) {
          var title = (item.symbol || 'Scenario') + ' ' + (item.asset_type || '');
          var body = 'Risk $' + (item.planned_risk || 0) + ' / max $' + (item.max_risk_dollars || 0) + ' | R/R ' + (item.reward_to_risk || 0);
          return listItem(title, body, item.within_rules ? 'Inside rules' : 'Review');
        }).join('');
      }
    }
  }
  async function loadRiskLab() {
    var data = await getJson('/api/risk-lab');
    var rules = data.rules || {};
    if (byId('risk-max-dollars')) byId('risk-max-dollars').value = rules.max_risk_per_trade || 75;
    renderRiskLab(data);
    return data;
  }
  async function initRiskLab() {
    await loadRiskLab();
    if (riskLabEventsBound) return;
    riskLabEventsBound = true;
    byId('save-risk-scenario').addEventListener('click', async function () {
      var payload = {
        symbol: byId('risk-symbol').value,
        asset_type: byId('risk-asset').value,
        account_size: Number(byId('risk-account').value || 0),
        max_risk_dollars: Number(byId('risk-max-dollars').value || 0),
        entry: Number(byId('risk-entry').value || 0),
        stop: Number(byId('risk-stop').value || 0),
        target: Number(byId('risk-target').value || 0),
        planned_size: Number(byId('risk-size').value || 0),
        notes: byId('risk-notes').value
      };
      var saved = await postJson('/api/risk-lab', payload);
      renderRiskLab({ calculation: saved.calculation, items: [saved.item] });
      byId('risk-lab-result').innerHTML = '<p>' + html(saved.message || 'Risk scenario saved.') + '</p><p class="muted">Mode: ' + html(saved.mode || 'demo') + '</p>';
      await loadRiskLab();
    });
  }
  function renderPreferencesPreview(preferences) {
    var el = byId('preferences-preview');
    if (!el) return;
    preferences = preferences || {};
    el.innerHTML = [
      listItem('Copilot tone', 'Responses can lean ' + html(preferences.experience_level || 'beginner') + ' and focus on education-first review.'),
      listItem('Risk framing', 'Risk reminders use a ' + html(preferences.risk_style || 'conservative') + ' profile.'),
      listItem('Markets', String(preferences.markets || 'stocks, etfs'), 'Watchlist focus'),
      listItem('Default symbols', preferences.default_symbols || 'SPY,QQQ,NVDA,TSLA', 'Dashboard seed')
    ].join('');
  }
  function setPreferencesForm(preferences) {
    preferences = preferences || {};
    if (byId('pref-experience')) byId('pref-experience').value = preferences.experience_level || 'beginner';
    if (byId('pref-risk')) byId('pref-risk').value = preferences.risk_style || 'conservative';
    if (byId('pref-markets')) byId('pref-markets').value = Array.isArray(preferences.markets) ? preferences.markets.join(', ') : (preferences.markets || 'stocks, etfs');
    if (byId('pref-platforms')) byId('pref-platforms').value = Array.isArray(preferences.platforms) ? preferences.platforms.join(', ') : (preferences.platforms || 'TradingView');
    if (byId('pref-symbols')) byId('pref-symbols').value = preferences.default_symbols || 'SPY,QQQ,NVDA,TSLA';
    if (byId('pref-goal')) byId('pref-goal').value = preferences.learning_goal || '';
    renderPreferencesPreview(preferences);
  }
  function renderOnboardingChecklist(payload) {
    payload = payload || {};
    var score = byId('onboarding-score');
    if (score) score.textContent = (payload.completed || 0) + '/' + (payload.total || 0) + ' done';
    var el = byId('onboarding-checklist');
    if (!el) return;
    el.innerHTML = (payload.items || []).map(function (item) {
      var label = item.ready ? 'Done' : (item.status || 'Open');
      var lockClass = item.ready ? '' : ' locked';
      return '<a class="list-item action-link" href="' + html(item.href || '/dashboard') + '"><div class="panel-title-row"><strong>' + html(item.title || 'Step') + '</strong><span class="pill' + lockClass + '">' + html(label) + '</span></div><div class="muted">' + html(item.body || '') + '</div></a>';
    }).join('');
  }
  async function loadOnboardingChecklist() {
    var checklist = await getJson('/api/onboarding-checklist');
    renderOnboardingChecklist(checklist);
    return checklist;
  }
  async function initOnboarding() {
    var data = await getJson('/api/preferences');
    setPreferencesForm(data.preferences || {});
    await loadOnboardingChecklist();
    if (onboardingEventsBound) return;
    onboardingEventsBound = true;
    byId('save-preferences').addEventListener('click', async function () {
      var payload = {
        experience_level: byId('pref-experience').value,
        risk_style: byId('pref-risk').value,
        markets: byId('pref-markets').value.split(',').map(function (item) { return item.trim(); }).filter(Boolean),
        platforms: byId('pref-platforms').value.split(',').map(function (item) { return item.trim(); }).filter(Boolean),
        default_symbols: byId('pref-symbols').value,
        learning_goal: byId('pref-goal').value
      };
      var saved = await postJson('/api/preferences', payload);
      setPreferencesForm(saved.preferences || payload);
      byId('preferences-result').innerHTML = '<p>' + html(saved.message || 'Preferences saved.') + '</p><p class="muted">Mode: ' + html(saved.mode || 'demo') + '</p>';
      await loadOnboardingChecklist();
    });
  }
  function renderScreenshotReviews(items) {
    var el = byId('screen-review-list');
    if (!el) return;
    if (!items || !items.length) {
      el.innerHTML = listItem('No screenshot reviews yet', 'Upload a chart screenshot to save a demo review checklist.');
      return;
    }
    el.innerHTML = items.slice(0, 10).map(function (item) {
      var analysis = item.analysis || {};
      var tag = analysis.setup_quality ? 'Quality ' + analysis.setup_quality + '/10' : (item.symbol || item.platform || 'Demo');
      var body = analysis.trend_summary || item.notes || 'Review saved.';
      var tags = analysis.review_tags && analysis.review_tags.length ? ' | ' + analysis.review_tags.join(', ') : '';
      return listItem(item.filename || 'Screenshot', body + tags, tag);
    }).join('');
  }
  async function loadScreenshotReviews() {
    var data = await getJson('/api/screenshot-reviews');
    renderScreenshotReviews(data.items || []);
  }
  async function initScreenshotAnalyzer() {
    await loadScreenshotReviews();
    var fileInput = byId('screen-file');
    if (fileInput) fileInput.addEventListener('change', function () {
      var file = fileInput.files && fileInput.files[0];
      var preview = byId('screen-preview');
      if (!preview) return;
      if (!file) {
        preview.innerHTML = '';
        return;
      }
      var url = URL.createObjectURL(file);
      preview.innerHTML = '<img alt="Chart screenshot preview" src="' + url + '" />';
    });
    if (screenshotEventsBound) return;
    screenshotEventsBound = true;
    byId('analyze-screenshot').addEventListener('click', async function () {
      var file = byId('screen-file').files && byId('screen-file').files[0];
      var result = byId('screen-result');
      result.textContent = 'Reviewing...';
      var data = await postJson('/api/screenshot-analyzer', {
        filename: file ? file.name : 'No file selected',
        symbol: byId('screen-symbol').value,
        platform: byId('screen-platform').value,
        notes: byId('screen-notes').value
      });
      var tags = data.review_tags && data.review_tags.length ? data.review_tags.join(', ') : 'Needs review';
      var questions = (data.confirmation_questions || []).map(function (question) { return '<li>' + html(question) + '</li>'; }).join('');
      result.innerHTML = '<p>' + html(data.trend_summary) + '</p>' +
        kv('Review mode', data.ai_provider || 'Safe demo reviewer') +
        kv('Setup quality', (data.setup_quality || 'n/a') + '/10') +
        kv('Tags', tags) +
        kv('Support / resistance', data.support_resistance) +
        kv('Indicator notes', data.indicator_notes) +
        kv('Chasing risk', data.risk_of_chasing) +
        kv('Journal prompt', data.journal_prompt || 'Add notes before saving to your journal.') +
        '<ul>' + questions + '</ul><p class="muted">' + html(data.beginner_explanation) + '</p>';
      await loadScreenshotReviews();
    });
  }
  function renderPaperTrades(items) {
    var el = byId('paper-trade-list');
    if (!el) return;
    if (!items || !items.length) {
      el.innerHTML = listItem('No paper plans yet', 'Save a plan to practice risk review without placing orders.');
      return;
    }
    el.innerHTML = items.slice(0, 10).map(function (item) {
      var checklist = item.checklist || {};
      var title = (item.symbol || 'Paper trade') + ' ' + (item.direction || '');
      var journaled = item.journal_entry_id || item.journalized_at;
      var review = item.status === 'reviewed' ? ' | Result ' + (item.result || 'Reviewed') + ' | P/L ' + (item.pnl || '0') : '';
      if (journaled) review += ' | Journaled';
      var body = (item.strategy || item.reason || 'Practice setup') + ' | Entry ' + (item.entry || '-') + ' | Stop ' + (item.stop || '-') + ' | Target ' + (item.target || '-') + review;
      return listItem(title, body, journaled ? 'Journaled' : item.status === 'reviewed' ? 'Reviewed' : 'Quality ' + (checklist.setup_quality == null ? 'n/a' : checklist.setup_quality + '/10'));
    }).join('');
  }
  function renderPaperReviewOptions(items) {
    var select = byId('paper-review-id');
    if (!select) return;
    items = items || [];
    if (!items.length) {
      select.innerHTML = '<option value="">No saved plans yet</option>';
      return;
    }
    select.innerHTML = items.slice(0, 20).map(function (item) {
      var label = (item.symbol || 'Paper plan') + ' ' + (item.direction || '') + ' - ' + ((item.journal_entry_id || item.journalized_at) ? 'journaled' : (item.status || 'planned'));
      return '<option value="' + html(item.id || '') + '">' + html(label) + '</option>';
    }).join('');
  }
  async function loadPaperTrades() {
    var data = await getJson('/api/paper-trades');
    renderPaperTrades(data.items || []);
    renderPaperReviewOptions(data.items || []);
    return data;
  }
  async function initPaperTrade() {
    await loadPaperTrades();
    if (paperTradeEventsBound) return;
    paperTradeEventsBound = true;
    byId('save-paper-trade').addEventListener('click', async function () {
      var payload = {
        symbol: byId('paper-symbol').value,
        asset_type: byId('paper-asset').value,
        direction: byId('paper-direction').value,
        news: byId('paper-news').value,
        entry: byId('paper-entry').value,
        stop: byId('paper-stop').value,
        target: byId('paper-target').value,
        position_size: byId('paper-size').value,
        invalidation: byId('paper-invalid').value,
        strategy: byId('paper-strategy').value,
        reason: byId('paper-reason').value,
        following_rules: 'yes'
      };
      var saved = await postJson('/api/paper-trades', payload);
      var checklist = saved.checklist || {};
      byId('paper-check-result').innerHTML = '<p>' + html(saved.message || 'Paper plan saved.') + '</p>' + kv('Setup Quality', (checklist.setup_quality == null ? 'n/a' : checklist.setup_quality + '/10')) + kv('Risk Clarity', checklist.risk_clarity || 'Review') + kv('News Risk', checklist.news_risk || payload.news) + '<ul>' + (checklist.rule_violations || []).map(function (v) { return '<li>' + html(v) + '</li>'; }).join('') + '</ul>';
      await loadPaperTrades();
    });
    byId('save-paper-review').addEventListener('click', async function () {
      var payload = {
        trade_id: byId('paper-review-id').value,
        result: byId('paper-review-result').value,
        exit_price: byId('paper-review-exit').value,
        pnl: byId('paper-review-pnl').value,
        review_notes: byId('paper-review-notes').value,
        lesson_learned: byId('paper-review-lesson').value,
        mistake_tags: byId('paper-review-lesson').value,
        status: 'reviewed'
      };
      var saved = await postJson('/api/paper-trades/review', payload);
      var journal = saved.journal_prefill || {};
      byId('paper-review-result-box').innerHTML = '<p>' + html(saved.message || saved.summary || 'Practice review saved.') + '</p>' + kv('Result', journal.result || payload.result) + kv('P/L', journal.pnl || payload.pnl || '0') + '<p class="muted">Journal-ready notes were prepared from this review.</p>';
      await loadPaperTrades();
    });
    byId('journalize-paper-review').addEventListener('click', async function () {
      var payload = { trade_id: byId('paper-review-id').value };
      var saved = await postJson('/api/paper-trades/journalize', payload);
      var entry = saved.journal_entry || {};
      byId('paper-review-result-box').innerHTML = '<p>' + html(saved.message || 'Paper review sent to the journal.') + '</p>' + kv('Journal symbol', entry.symbol || 'Saved') + kv('Result', entry.result || '') + '<p class="muted">The journal stays educational and review-only; no broker order was placed.</p>';
      await loadPaperTrades();
    });
  }
  function renderJournalEntries(entries) {
    var el = byId('journal-entry-list');
    if (!el) return;
    if (!entries || !entries.length) {
      el.innerHTML = listItem('No entries yet', 'Save a demo entry to start building your review loop.');
      return;
    }
    el.innerHTML = entries.slice(0, 8).map(function (entry) {
      var title = (entry.symbol || 'Trade') + ' ' + (entry.direction || '');
      var body = (entry.setup_type || 'Setup') + ' | P/L: ' + (entry.pnl || '0') + ' | ' + (entry.lesson_learned || entry.mistakes || entry.entry_reason || 'No lesson added yet.');
      return listItem(title, body, entry.result || 'Review');
    }).join('');
  }
  async function loadJournalData() {
    var data = await getJson('/api/journal');
    var review = data.weekly_review || {};
    var reviewEl = byId('weekly-review');
    if (reviewEl) reviewEl.innerHTML = kv('Total trades', review.total_trades) + kv('Wins / losses', review.wins + ' / ' + review.losses) + kv('Repeated mistake', review.most_repeated_mistake) + kv('Next focus', review.focus_next_week);
    var replay = byId('replay-cards');
    if (replay) replay.innerHTML = (data.replay_cards || []).map(function (card) { return '<div class="list-item"><strong>' + html(card.prompt) + '</strong><div class="muted">Choices: ' + html(card.choices.join(' | ')) + '</div><p>Answer: ' + html(card.answer) + '</p><p class="muted">' + html(card.explanation) + '</p></div>'; }).join('');
    renderJournalEntries(data.entries || []);
  }
  async function initJournal() {
    await loadJournalData();
    if (journalEventsBound) return;
    journalEventsBound = true;
    byId('save-journal').addEventListener('click', async function () {
      var payload = {
        symbol: byId('journal-symbol').value,
        asset_type: byId('journal-asset').value,
        direction: byId('journal-direction').value,
        entry_price: byId('journal-entry').value,
        stop_loss: byId('journal-stop').value,
        target_price: byId('journal-target').value,
        exit_price: byId('journal-exit').value,
        position_size: byId('journal-size').value,
        pnl: byId('journal-pnl').value,
        result: byId('journal-result') ? byId('journal-result').value : '',
        setup_type: byId('journal-setup').value,
        entry_reason: byId('journal-reason').value,
        mistakes: byId('journal-reason').value,
        lesson_learned: byId('journal-reason').value,
        ai_summary: 'Entry reviewed by TradePulse demo journal.'
      };
      var saved = await postJson('/api/journal', payload);
      var shot = byId('screenshot-upload').files[0];
      var extra = shot ? '<p class="muted">Screenshot metadata captured: ' + html(shot.name) + '. Use Screenshot Analyzer for a structured demo chart review.</p>' : '';
      byId('journal-ai-result').innerHTML = '<p>' + html(saved.ai_summary) + '</p>' + extra;
      await loadJournalData();
    });
  }
  function renderSchoolQuiz(module) {
    var panel = byId('quiz-panel');
    if (!panel || !module) return;
    var questions = module.quiz || [];
    panel.innerHTML = '<strong>' + html(module.lesson) + '</strong><p class="muted">' + html(module.track) + ' | Current status: ' + html(module.status || 'Ready') + '</p>' + questions.map(function (question, qIndex) {
      return '<div class="list-item"><strong>' + html(question.question) + '</strong>' + question.choices.map(function (choice, cIndex) {
        return '<label class="quiz-choice"><input type="radio" name="quiz-q' + qIndex + '" value="' + cIndex + '" /> ' + html(choice) + '</label>';
      }).join('') + '</div>';
    }).join('') + '<button id="save-quiz-score" class="full" type="button">Check answers</button><div id="quiz-result" class="response-box hidden"></div>';
    byId('save-quiz-score').addEventListener('click', async function () {
      var correct = 0;
      var details = [];
      questions.forEach(function (question, qIndex) {
        var selected = document.querySelector('input[name="quiz-q' + qIndex + '"]:checked');
        var selectedIndex = selected ? Number(selected.value) : -1;
        if (selectedIndex === Number(question.answer_index)) correct += 1;
        details.push('<div class="list-item"><strong>' + html(selectedIndex === Number(question.answer_index) ? 'Correct' : 'Review') + '</strong><div class="muted">' + html(question.explanation) + '</div></div>');
      });
      var score = questions.length ? Math.round(correct / questions.length * 100) : 0;
      var saved = await postJson('/api/school/progress', { lesson_key: module.lesson_key, lesson: module.lesson, status: 'completed', quiz_score: score });
      var result = byId('quiz-result');
      result.classList.remove('hidden');
      result.innerHTML = '<p>Score saved: ' + html(score) + '%</p><p class="muted">Mode: ' + html(saved.mode || 'demo') + '</p>' + details.join('');
    });
  }
  async function initSchool() {
    schoolPayload = await getJson('/api/school');
    var el = byId('school-modules');
    if (el) {
      el.innerHTML = (schoolPayload.modules || []).map(function (m) {
        var score = m.quiz_score == null ? '' : ' | Score ' + m.quiz_score + '%';
        return '<article class="panel"><p class="eyebrow">' + html(m.track) + '</p><h2>' + html(m.lesson) + '</h2><p class="muted">' + html(m.status || 'Ready') + html(score) + '</p><button class="secondary full" data-lesson-key="' + html(m.lesson_key) + '" type="button">Open lesson</button></article>';
      }).join('');
    }
    document.querySelectorAll('[data-lesson-key]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var module = (schoolPayload.modules || []).find(function (m) { return m.lesson_key === btn.dataset.lessonKey; });
        renderSchoolQuiz(module);
      });
    });
  }
  function renderSavedStrategies(items) {
    var el = byId('saved-strategies');
    if (!el) return;
    if (!items || !items.length) {
      el.innerHTML = listItem('No saved strategies yet', 'Build one from a plain-English idea and it will be saved in demo mode.');
      return;
    }
    el.innerHTML = items.slice(0, 8).map(function (item) {
      var entryCount = Array.isArray(item.entry_rules) ? item.entry_rules.length : 0;
      var avoidCount = Array.isArray(item.avoid_rules) ? item.avoid_rules.length : 0;
      return listItem(item.name || 'Strategy', (item.description || 'No description yet.') + ' | Entry rules: ' + entryCount + ' | Avoid rules: ' + avoidCount, item.created_at ? 'Saved' : 'Demo');
    }).join('');
  }
  async function loadStrategies() {
    var data = await getJson('/api/strategies');
    renderSavedStrategies(data.items || []);
  }
  async function initStrategy() {
    await loadStrategies();
    if (strategyEventsBound) return;
    strategyEventsBound = true;
    byId('build-strategy').addEventListener('click', async function () {
      var data = await postJson('/api/strategy-builder', { prompt: byId('strategy-prompt').value });
      var s = data.strategy;
      function list(arr) { return '<ul>' + arr.map(function (x) { return '<li>' + html(x) + '</li>'; }).join('') + '</ul>'; }
      var savePayload = { name: s.name, description: s.description, entry_rules: s.entry_rules, exit_rules: [].concat(s.stop_rules || [], s.target_rules || []), avoid_rules: s.avoid_rules, risk_rules: s.risk_rules };
      var saved = await postJson('/api/strategies', savePayload);
      byId('strategy-result').innerHTML = '<h3>' + html(s.name) + '</h3><p>' + html(s.description) + '</p><h3>Entry rules</h3>' + list(s.entry_rules) + '<h3>Avoid rules</h3>' + list(s.avoid_rules) + '<h3>Risk rules</h3>' + kv('Best market', s.best_market_conditions) + kv('Worst market', s.worst_market_conditions) + '<p class="muted">' + html(s.scanner_logic_summary) + '</p><p class="muted">Save mode: ' + html(saved.mode || 'demo') + '</p>';
      await loadStrategies();
    });
  }
  function statusItem(label, isReady, readyText, missingText) {
    return '<div class="list-item"><div class="panel-title-row"><strong>' + html(label) + '</strong><span class="pill ' + (isReady ? '' : 'locked') + '">' + (isReady ? 'Ready' : 'Needed') + '</span></div><div class="muted">' + html(isReady ? readyText : missingText) + '</div></div>';
  }
  function launchItem(item) {
    return '<div class="list-item"><div class="panel-title-row"><strong>' + html(item.title) + '</strong><span class="pill ' + (item.ready ? '' : 'locked') + '">' + html(item.status || (item.ready ? 'Ready' : 'Needed')) + '</span></div><div class="muted">' + html(item.body || item.next_step || '') + '</div>' + (item.required_for_public_launch ? '' : '<div class="pill">Optional upgrade</div>') + '</div>';
  }
  async function initLaunchCenter() {
    var data = await getJson('/api/launch-checklist');
    var score = byId('launch-score');
    if (score) score.textContent = String(data.score || 0) + '%';
    var summary = byId('launch-summary');
    if (summary) summary.textContent = (data.summary || '') + ' Mode: ' + (data.mode || 'demo-ready') + '.';
    var metrics = byId('launch-metrics');
    if (metrics) {
      metrics.innerHTML = kv('Required ready', (data.required_ready || 0) + '/' + (data.required_total || 0)) + kv('Total checks ready', (data.ready_total || 0) + '/' + (data.item_total || 0)) + kv('Blockers', (data.blockers || []).length) + kv('Broker safety', 'Disabled');
    }
    var blockers = byId('launch-blockers');
    if (blockers) {
      blockers.innerHTML = (data.blockers || []).length ? data.blockers.map(launchItem).join('') : listItem('No required blockers', 'Production launch checks are ready. Keep legal and provider testing current.', 'Ready');
    }
    var plans = byId('launch-plan-summary');
    if (plans) {
      plans.innerHTML = (data.plans || []).map(function (plan) {
        var limits = plan.limits || {};
        return '<div class="list-item"><div class="panel-title-row"><strong>' + html(plan.label) + '</strong><span class="pill">' + html(plan.price) + '</span></div><div class="muted">' + html(plan.description || '') + '</div><div class="muted">Watchlist ' + html(limits.watchlist_symbols) + ' | Scanner/day ' + html(limits.scanner_runs_per_day) + ' | Alerts ' + html(limits.alerts) + '</div></div>';
      }).join('');
    }
    var grouped = {};
    (data.items || []).forEach(function (item) {
      var group = item.group || 'Other';
      if (!grouped[group]) grouped[group] = [];
      grouped[group].push(item);
    });
    var groups = byId('launch-groups');
    if (groups) {
      groups.innerHTML = Object.keys(grouped).map(function (group) {
        var ready = grouped[group].filter(function (item) { return item.ready; }).length;
        return '<section class="launch-group"><div class="panel-title-row"><h3>' + html(group) + '</h3><span class="pill">' + ready + '/' + grouped[group].length + ' ready</span></div><div class="stack-list">' + grouped[group].map(launchItem).join('') + '</div></section>';
      }).join('');
    }
    var notes = byId('launch-safe-notes');
    if (notes) {
      notes.innerHTML = (data.safe_notes || []).map(function (note) { return listItem(note, 'Launch safety requirement'); }).join('');
    }
  }
  async function initBusinessPlan() {
    var data = await getJson('/api/business-plan');
    var positioning = data.positioning || {};
    var offer = data.offer || {};
    var economics = data.unit_economics || {};
    var plans = offer.plans || [];
    var blockers = data.current_blockers || [];
    var category = byId('business-category');
    if (category) category.textContent = positioning.category || 'TradePulse business plan';
    var promise = byId('business-promise');
    if (promise) promise.textContent = positioning.promise || '';
    var summary = byId('business-summary');
    if (summary) {
      summary.innerHTML = kv('Launch mode', data.mode || 'demo-ready') + kv('Plans', plans.length) + kv('Full access', offer.full_access_plan || 'all_access') + kv('Blockers', blockers.length);
    }
    var audience = byId('business-audience');
    if (audience) {
      audience.innerHTML = (data.audience || []).map(function (item) { return listItem(item, 'Target customer'); }).join('');
    }
    var pricing = byId('business-pricing');
    if (pricing) {
      pricing.innerHTML = plans.map(function (plan) {
        var limits = plan.limits || {};
        return '<div class="list-item"><div class="panel-title-row"><strong>' + html(plan.label) + '</strong><span class="pill">' + html(plan.price) + '</span></div><div class="muted">' + html(plan.description || '') + '</div><div class="muted">Scanner/day ' + html(limits.scanner_runs_per_day) + ' | Alerts ' + html(limits.alerts) + ' | Screenshots ' + html(limits.screenshot_reviews) + '</div></div>';
      }).join('') + '<p class="muted">' + html(offer.upgrade_logic || '') + '</p>';
    }
    var milestones = byId('business-milestones');
    if (milestones) {
      milestones.innerHTML = (data.launch_milestones || []).map(function (item) {
        return listItem(item.stage || 'Milestone', item.goal || '', item.status || 'Planned');
      }).join('');
    }
    var economicsEl = byId('business-economics');
    if (economicsEl) {
      var breakEven = (economics.break_even_examples || []).map(function (item) {
        return kv(item.plan + ' needed', item.subscribers_needed + ' subs at ' + item.price);
      }).join('');
      var assumptions = (economics.assumptions || []).map(function (item) { return listItem(item, 'Assumption'); }).join('');
      economicsEl.innerHTML = kv('Monthly cost floor', '$' + html(economics.monthly_cost_floor || 0)) + breakEven + assumptions + '<p class="muted">' + html(economics.note || '') + '</p>';
    }
    var success = byId('business-success');
    if (success) {
      success.innerHTML = (data.customer_success || []).map(function (item) { return listItem(item, 'Customer trust'); }).join('');
    }
    var risks = byId('business-risks');
    if (risks) {
      risks.innerHTML = (data.risk_controls || []).map(function (item) { return listItem(item, 'Safety rule'); }).join('');
    }
    var next = byId('business-next-actions');
    if (next) {
      var actions = data.next_actions || [];
      next.innerHTML = actions.map(function (item) { return listItem('Next action', item, blockers.length ? 'Required' : 'Ready'); }).join('');
    }
  }
  async function initProductionSetup() {
    var data = await getJson('/api/production-readiness');
    var score = byId('production-score');
    if (score) score.textContent = String(data.score || 0) + '%';
    var summary = byId('production-summary');
    if (summary) {
      summary.textContent = data.mode === 'production-ready' ? 'Required connection pieces are configured.' : 'Some required connection pieces still need setup.';
    }
    var metrics = byId('production-metrics');
    if (metrics) {
      metrics.innerHTML = kv('Required ready', (data.required_ready || 0) + '/' + (data.required_total || 0)) + kv('All checks ready', (data.ready_total || 0) + '/' + (data.item_total || 0)) + kv('Private beta', data.private_beta_ready ? 'Ready' : 'Setup') + kv('Paid beta', data.paid_beta_ready ? 'Ready' : 'Setup');
    }
    var actions = byId('production-actions');
    if (actions) {
      actions.innerHTML = (data.next_actions || []).map(function (item) { return listItem('Next action', item, 'Required'); }).join('');
    }
    var urls = byId('production-urls');
    if (urls) {
      var u = data.urls || {};
      urls.innerHTML = listItem('Stripe webhook URL', u.stripe_webhook_url || '', 'Copy to Stripe') + listItem('Supabase redirect URL', u.supabase_redirect_url || '', 'Auth') + listItem('Password reset URL', u.password_reset_url || '', 'Auth') + listItem('App base URL', u.app_base_url || '', 'Public');
    }
    var groups = byId('production-groups');
    if (groups) {
      var grouped = data.groups || {};
      groups.innerHTML = Object.keys(grouped).map(function (group) {
        var items = grouped[group] || [];
        var ready = items.filter(function (item) { return item.ready; }).length;
        return '<section class="launch-group"><div class="panel-title-row"><h3>' + html(group) + '</h3><span class="pill">' + ready + '/' + items.length + ' ready</span></div><div class="stack-list">' + items.map(function (item) {
          return '<div class="list-item"><div class="panel-title-row"><strong>' + html(item.label || item.key) + '</strong><span class="pill ' + (item.ready ? '' : 'locked') + '">' + html(item.status || 'Needed') + '</span></div><div class="muted">' + html(item.body || '') + '</div><div class="pill">' + html(item.key || '') + '</div></div>';
        }).join('') + '</div></section>';
      }).join('');
    }
    var modes = byId('production-modes');
    if (modes) {
      var runtime = data.runtime_modes || {};
      modes.innerHTML = Object.keys(runtime).map(function (key) {
        return listItem(key.replace(/_/g, ' '), runtime[key], 'Mode');
      }).join('');
    }
    var notes = byId('production-safe-notes');
    if (notes) {
      notes.innerHTML = (data.safe_notes || []).map(function (note) { return listItem(note, 'Safety'); }).join('');
    }
  }
  async function initSettings() {
    var status = await getJson('/api/system/status');
    var config = status.configuration || {};
    var statusEl = byId('system-status');
    if (statusEl) {
      statusEl.innerHTML = [
        statusItem('Supabase public auth', config.supabase_public_auth, 'Login/signup keys are present.', 'Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY.'),
        statusItem('Supabase server persistence', config.supabase_server_persistence, 'Server-side subscription sync can write safely.', 'Add SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY.'),
        statusItem('Stripe checkout', config.stripe_checkout, 'Pro checkout can start.', 'Add STRIPE_SECRET_KEY and STRIPE_PRICE_ID_PRO.'),
        statusItem('Elite Stripe price', config.stripe_elite_price, 'Elite checkout can start.', 'Add STRIPE_PRICE_ID_ELITE.'),
        statusItem('All Access Stripe price', config.stripe_all_access_price, 'All Access checkout can start.', 'Add STRIPE_PRICE_ID_ALL_ACCESS.'),
        statusItem('Stripe webhook', config.stripe_webhook, 'Webhook signature verification is configured.', 'Add STRIPE_WEBHOOK_SECRET and configure /billing/webhook.'),
        statusItem('Stripe customer portal', config.stripe_customer_portal, 'Manage Billing can open Stripe portal sessions for saved subscribers.', 'Add STRIPE_SECRET_KEY and SUPABASE_SECRET_KEY, then enable the Stripe customer portal.'),
        statusItem('OpenAI', config.openai, 'Real AI key is present. Model: ' + (config.openai_model || 'configured'), 'Mock research responses stay active until OPENAI_API_KEY is added.'),
        statusItem('Support contact', config.support_contact, 'Support email is configured: ' + (config.support_email || 'set'), 'Add APP_SUPPORT_EMAIL for account, billing, and privacy questions.'),
        statusItem('Security headers', config.security_headers, config.security_header_names || 'Browser safety headers are active.', 'Keep browser safety headers enabled in production.'),
        statusItem('Real market data switch', config.real_market_data_enabled, 'ENABLE_REAL_MARKET_DATA is on; chart routes can request real research candles.', 'Demo candles stay active until ENABLE_REAL_MARKET_DATA=true.'),
        statusItem('YFinance research feed', config.yfinance_research_feed, 'Research quote/candle feed wrapper is installed.', 'Install yfinance or keep demo candles active.'),
        statusItem('News providers', config.market_data || config.news_data, 'At least one keyed news/data provider is configured, with Yahoo RSS available as fallback.', 'Add FINNHUB_API_KEY, ALPHA_VANTAGE_API_KEY, or NEWSAPI_KEY for richer news.'),
        statusItem('Broker safety', config.broker_orders_disabled, 'Broker order execution is disabled.', 'Disable broker orders before public testing.')
      ].join('');
    }
    var steps = byId('launch-steps');
    if (steps) {
      steps.innerHTML = (status.safe_defaults || []).map(function (step) { return listItem(step, 'Safe production posture'); }).join('');
    }
    var rules = await getJson('/api/risk-rules');
    var r = rules.rules || {};
    if (byId('risk-max-trades')) {
      byId('risk-max-trades').value = r.max_trades_per_day || 3;
      byId('risk-max-losses').value = r.max_losses_per_day || 2;
      byId('risk-news-minutes').value = r.avoid_news_minutes || 15;
      byId('risk-option-premium').value = r.max_option_premium || 250;
      byId('risk-max-risk').value = r.max_risk_per_trade || 75;
      byId('risk-stop-required').value = String(r.require_stop_loss !== false);
      byId('risk-checklist-required').checked = r.require_checklist !== false;
    }
    byId('save-risk-settings').addEventListener('click', async function () {
      var payload = {
        max_trades_per_day: Number(byId('risk-max-trades').value || 0),
        max_losses_per_day: Number(byId('risk-max-losses').value || 0),
        avoid_news_minutes: Number(byId('risk-news-minutes').value || 0),
        max_option_premium: Number(byId('risk-option-premium').value || 0),
        max_risk_per_trade: Number(byId('risk-max-risk').value || 0),
        require_stop_loss: byId('risk-stop-required').value === 'true',
        require_checklist: byId('risk-checklist-required').checked
      };
      var saved = await postJson('/api/risk-rules', payload);
      byId('risk-settings-result').innerHTML = '<p>' + html(saved.message || 'Risk rules saved.') + '</p><p class="muted">Mode: ' + html(saved.mode || 'demo') + '</p>';
    });
    var exportButton = byId('export-demo-state');
    if (exportButton) exportButton.addEventListener('click', async function () {
      var data = await getJson('/api/export/demo-state');
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var link = document.createElement('a');
      link.href = url;
      link.download = 'tradepulse-demo-backup-' + String(data.exported_at || new Date().toISOString()).slice(0, 10) + '.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      var counts = data.counts || {};
      byId('export-demo-result').innerHTML = '<p>Demo backup prepared.</p>' + kv('Journal entries', counts.journal_entries || 0) + kv('Paper plans', counts.paper_trades || 0) + kv('Session prep', counts.session_plans || 0) + '<p class="muted">' + html(data.note || 'No secrets are included.') + '</p>';
    });
  }
  function showExplain(text) { var old = document.querySelector('.explain-popover'); if (old) old.remove(); var box = document.createElement('div'); box.className = 'panel explain-popover'; box.innerHTML = '<h2>Explanation</h2><p>' + html(text) + '</p><button class="secondary full" type="button">Close</button>'; document.body.appendChild(box); box.querySelector('button').addEventListener('click', function () { box.remove(); }); }
  function explainTerm(term) { var notes = { VWAP: 'VWAP is the volume-weighted average price. Traders watch it as an intraday fair-price area. A common beginner mistake is chasing far from VWAP without a stop or confirmation.', RSI: 'RSI measures momentum. High RSI can show strength or extension; it is not a sell signal by itself.', ATR: 'ATR estimates typical movement size. Higher ATR means stops and position size need extra care.', IV: 'Implied volatility affects option premium. High IV can make contracts expensive and increase risk even when direction is right.' }; showExplain(notes[term] || (term + ' is a research input. Check what it means, why it matters, and how it changes risk before acting.')); }
  document.addEventListener('click', function (event) { var button = event.target.closest('[data-explain]'); if (button) explainTerm(button.dataset.explain); });
  if (page === 'landing') initLanding();
  if (page === 'onboarding') initOnboarding();
  if (page === 'dashboard') initDashboard();
  if (page === 'watchlists') initWatchlists();
  if (page === 'news') initNews();
  if (page === 'scanner') initScannerPage();
  if (page === 'live-charts') initCharts();
  if (page === 'copilot') initCopilot();
  if (page === 'alerts') initAlerts();
  if (page === 'session-prep') initSessionPrep();
  if (page === 'review-center') initReviewCenter();
  if (page === 'progress') initProgress();
  if (page === 'risk-lab') initRiskLab();
  if (page === 'screenshot-analyzer') initScreenshotAnalyzer();
  if (page === 'paper-trade') initPaperTrade();
  if (page === 'journal') initJournal();
  if (page === 'school') initSchool();
  if (page === 'strategy-builder') initStrategy();
  if (page === 'settings') initSettings();
  if (page === 'launch-center') initLaunchCenter();
  if (page === 'business-plan') initBusinessPlan();
  if (page === 'production-setup') initProductionSetup();
})();
