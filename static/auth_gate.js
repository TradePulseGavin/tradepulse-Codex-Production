(function () {
  if (!document.body.dataset.protected) return;
  var PLAN_IDS = ['free', 'pro', 'elite', 'all_access'];
  function demoPlan() {
    var saved = localStorage.getItem('tradepulse_demo_plan') || 'all_access';
    return PLAN_IDS.indexOf(saved) === -1 ? 'all_access' : saved;
  }
  function applyPlan(plan) {
    var normalized = ['free', 'pro', 'elite', 'all_access'].indexOf(plan) === -1 ? 'free' : plan;
    document.body.classList.remove('plan-free', 'plan-pro', 'plan-elite', 'plan-all_access');
    document.body.classList.add('plan-' + normalized);
    document.body.dataset.plan = normalized;
    document.querySelectorAll('.pro-lock, .elite-lock, .all-access-lock').forEach(function (el) { el.classList.remove('locked'); });
    document.querySelectorAll('.pro-lock').forEach(function (el) { if (normalized === 'free') el.classList.add('locked'); });
    document.querySelectorAll('.elite-lock').forEach(function (el) { if (['elite', 'all_access'].indexOf(normalized) === -1) el.classList.add('locked'); });
    document.querySelectorAll('.all-access-lock').forEach(function (el) { if (normalized !== 'all_access') el.classList.add('locked'); });
  }
  function lockPage(message) {
    var main = document.querySelector('main');
    if (!main) return;
    var banner = document.createElement('section');
    banner.className = 'notice plan-lock-banner';
    banner.innerHTML = '<b>Plan upgrade needed.</b> ' + message + ' <a class="button small secondary" href="/pricing">View plans</a>';
    main.insertBefore(banner, main.firstChild);
    main.querySelectorAll('button, input, textarea, select').forEach(function (el) {
      if (!el.closest('.plan-lock-banner')) el.disabled = true;
    });
    main.querySelectorAll('form').forEach(function (form) { form.addEventListener('submit', function (event) { event.preventDefault(); }); });
  }
  function enforceRequiredFeature(info) {
    var feature = document.body.dataset.requiredFeature;
    if (!feature || !info || !info.features) return;
    if (!info.features[feature]) {
      lockPage('This page is included in a higher TradePulse plan.');
    }
  }
  function waitForSupabase() {
    return new Promise(function (resolve) {
      var script = document.querySelector('script[data-tradepulse-supabase]');
      if (!window.supabase && !script) {
        script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
        script.async = true;
        script.dataset.tradepulseSupabase = 'true';
        script.onerror = function () { resolve(false); };
        document.head.appendChild(script);
      }
      var attempts = 0;
      function check() {
        if (window.supabase) { resolve(true); return; }
        attempts += 1;
        if (attempts >= 80) { resolve(false); return; }
        window.setTimeout(check, 50);
      }
      check();
    });
  }
  async function access(session, user) {
    var url = '/api/access?email=' + encodeURIComponent(user.email || '') + '&user_id=' + encodeURIComponent(user.id || '');
    var headers = session && session.access_token ? { Authorization: 'Bearer ' + session.access_token } : {};
    var res = await fetch(url, { headers: headers });
    return await res.json();
  }
  if (!window.TRADEPULSE_SUPABASE_URL || !window.TRADEPULSE_SUPABASE_KEY) {
    window.TRADEPULSE_AUTH_READY = fetch('/api/access?plan=' + encodeURIComponent(demoPlan())).then(function (res) { return res.json(); }).then(function (info) {
      applyPlan(info.plan || demoPlan());
      enforceRequiredFeature(info);
      return { user: { id: 'demo-local', email: 'demo@tradepulse.local' }, access: info };
    }).catch(function () {
      applyPlan('all_access');
      enforceRequiredFeature({ features: { dashboard: true, watchlist: true, journal: true, scanner: true, alerts: true, paper_trade: true, session_prep: true, live_charts: true, advanced_scanner: true, advanced_layouts: true, school_full: true, copilot_memory: true, screenshot_analyzer: true, strategy_builder: true, full_ai_data: true } });
      return null;
    });
    return;
  }
  window.TRADEPULSE_AUTH_READY = waitForSupabase().then(async function (ready) {
    if (!ready) {
      applyPlan('free');
      window.location.href = '/login';
      return null;
    }
    var client = window.supabase.createClient(window.TRADEPULSE_SUPABASE_URL, window.TRADEPULSE_SUPABASE_KEY);
    var result = await client.auth.getSession();
    var session = result && result.data ? result.data.session : null;
    var user = session ? session.user : null;
    if (!user) { localStorage.setItem('tradepulse_return_to', window.location.pathname); window.location.href = '/login'; return; }
    window.TRADEPULSE_USER_ID = user.id;
    window.TRADEPULSE_USER_EMAIL = user.email;
    var info = await access(session, user);
    applyPlan(info.plan || 'free');
    enforceRequiredFeature(info);
    return { user: { id: user.id, email: user.email }, access: info };
  }).catch(function () { window.location.href = '/login'; });
})();
