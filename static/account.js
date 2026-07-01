const statusEl = document.getElementById('account-status');
const logoutBtn = document.getElementById('logout');
const demoPlanSelect = document.getElementById('demo-plan-select');
const accountDataResult = document.getElementById('account-data-result');
const downloadAccountDataBtn = document.getElementById('download-account-data');
const requestAccountDeleteBtn = document.getElementById('request-account-delete');
const PLAN_IDS = ['free', 'pro', 'elite', 'all_access'];
let currentAccount = { email: 'demo@tradepulse.local', user_id: 'demo-local', headers: {} };
function demoPlan() {
  const saved = localStorage.getItem('tradepulse_demo_plan') || 'all_access';
  return PLAN_IDS.includes(saved) ? saved : 'all_access';
}
function setDemoPlan(plan) {
  const normalized = PLAN_IDS.includes(plan) ? plan : 'all_access';
  localStorage.setItem('tradepulse_demo_plan', normalized);
  return normalized;
}
function safe(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])); }
function line(label, value) { return '<div class="metric-card"><span class="muted">' + label + '</span><br><strong>' + value + '</strong></div>'; }
function featureSummary(features) {
  const unlocked = [];
  if (features.watchlist) unlocked.push('Core tools');
  if (features.live_charts) unlocked.push('Elite workspace');
  if (features.strategy_builder && features.screenshot_analyzer) unlocked.push('Full AI tools');
  if (!unlocked.length) unlocked.push('Free preview');
  return unlocked.join(' | ');
}
function limitSummary(limits) {
  const pieces = [];
  if (limits.watchlist_symbols !== undefined) pieces.push('Watchlist ' + limits.watchlist_symbols);
  if (limits.scanner_runs_per_day !== undefined) pieces.push('Scanner/day ' + limits.scanner_runs_per_day);
  if (limits.alerts !== undefined) pieces.push('Alerts ' + limits.alerts);
  if (limits.copilot_prompts_per_day !== undefined) pieces.push('Copilot/day ' + limits.copilot_prompts_per_day);
  return pieces.length ? pieces.join(' | ') : 'Plan limits pending';
}
function renderStatus(email, access) {
  const planLabel = access.plan_label || (access.plan || 'free').replace('_', ' ').toUpperCase();
  return '<div class="account-metrics">' +
    line('Email', safe(email)) +
    line('Visible plan', safe(planLabel)) +
    line('Unlocked', safe(featureSummary(access.features || {}))) +
    line('Plan limits', safe(limitSummary(access.limits || {}))) +
    line('Owner bypass', access.is_owner ? 'All Access enabled' : 'No') +
    '</div>';
}
function usageMeter(item) {
  const percent = Math.max(0, Math.min(100, Number(item.percent || 0)));
  const limitText = item.limited ? String(item.used) + ' / ' + String(item.limit) : String(item.used) + ' / ' + String(item.limit);
  const upgrade = item.at_limit && item.upgrade_label ? '<div class="muted">Upgrade target: ' + safe(item.upgrade_label) + '</div>' : '';
  return '<div class="usage-meter"><div class="panel-title-row"><strong>' + safe(item.label) + '</strong><span class="pill ' + (item.at_limit ? 'locked' : '') + '">' + safe(item.status) + '</span></div><div class="muted">' + safe(limitText) + '</div><div class="usage-track"><span style="width:' + percent + '%"></span></div>' + upgrade + '</div>';
}
function renderUsage(usage) {
  const items = usage.items || [];
  const summary = usage.summary || 'Usage is being tracked for this plan.';
  const closest = usage.closest_limit ? 'Closest limit: ' + usage.closest_limit.label + ' at ' + usage.closest_limit.percent + '%.' : 'Unlimited or included features are ready.';
  return '<section class="account-usage"><h2>Usage and limits</h2><p class="muted">' + safe(summary) + ' ' + safe(closest) + '</p><p class="muted">Demo mode uses soft warnings instead of blocking actions. Production can use the same limit checks for strict enforcement.</p><div class="usage-grid">' + items.map(usageMeter).join('') + '</div></section>';
}
function billingNotice() {
  const status = new URLSearchParams(window.location.search).get('billing') || '';
  const messages = {
    portal_demo: 'Manage Billing is ready as a safe demo placeholder. It will open Stripe after live billing keys and a customer subscription exist.',
    portal_needs_account: 'Log in with a connected account before managing billing.',
    portal_needs_subscription: 'No Stripe subscription is attached to this account yet. Pick a paid plan first, then this button will manage it.',
    portal_error: 'Stripe billing portal could not open. Check the Stripe customer and portal settings, then try again.',
  };
  return messages[status] ? '<div class="callout">' + safe(messages[status]) + '</div>' : '';
}
function showAccountDataResult(markup) {
  if (!accountDataResult) return;
  accountDataResult.classList.remove('hidden');
  accountDataResult.innerHTML = markup;
}
function accountQuery() {
  const params = new URLSearchParams();
  if (currentAccount.email) params.set('email', currentAccount.email);
  if (currentAccount.user_id) params.set('user_id', currentAccount.user_id);
  const query = params.toString();
  return query ? '?' + query : '';
}
async function accountRequest(url, options) {
  const headers = Object.assign({}, currentAccount.headers || {}, options && options.headers ? options.headers : {});
  const response = await fetch(url, Object.assign({}, options || {}, { headers }));
  if (!response.ok) throw new Error('Request failed: ' + response.status);
  return await response.json();
}
function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function downloadAccountData() {
  try {
    const data = await accountRequest('/api/export/account-data' + accountQuery());
    const stamp = String(data.exported_at || new Date().toISOString()).slice(0, 10);
    downloadJson('tradepulse-account-data-' + stamp + '.json', data);
    const counts = data.counts || {};
    showAccountDataResult('<p>Account data export prepared.</p>' + line('Watchlists', safe(counts.watchlists || 0)) + line('Journal entries', safe(counts.journal_entries || 0)) + line('Paper plans', safe(counts.paper_trades || 0)) + line('Data requests', safe(counts.data_requests || 0)) + '<p class="muted">' + safe(data.note || 'No secrets are included.') + '</p>');
  } catch (error) {
    showAccountDataResult('<p>Data export could not be prepared right now.</p><p class="muted">Use Support if this happens on the hosted account page.</p>');
  }
}
async function requestAccountDeletion() {
  const confirmed = window.confirm('Create a reviewed account deletion request? Demo mode will record the request but will not delete data automatically.');
  if (!confirmed) return;
  try {
    const payload = {
      request_type: 'delete',
      email: currentAccount.email,
      user_id: currentAccount.user_id,
      notes: 'Requested from the TradePulse account page.'
    };
    const data = await accountRequest('/api/account/data-request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const request = data.request || {};
    showAccountDataResult('<p>' + safe(data.message || 'Request received.') + '</p>' + line('Request ID', safe(request.id || 'received')) + line('Status', safe(request.status || 'received')) + '<p class="muted">Support contact: ' + safe(data.support_email || 'Add APP_SUPPORT_EMAIL before public launch') + '</p>');
  } catch (error) {
    showAccountDataResult('<p>Request could not be saved right now.</p><p class="muted">Use Support and include your account email.</p>');
  }
}
async function showDemoStatus() {
  try {
    currentAccount = { email: 'demo@tradepulse.local', user_id: 'demo-local', headers: {} };
    const plan = demoPlan();
    if (demoPlanSelect) demoPlanSelect.value = plan;
    const access = await fetch('/api/access?plan=' + encodeURIComponent(plan)).then((res) => res.json());
    const usage = await fetch('/api/usage?plan=' + encodeURIComponent(plan)).then((res) => res.json());
    statusEl.innerHTML = billingNotice() + '<p class="muted">Demo mode is active. Real account billing connects after Supabase and Stripe keys are added.</p>' + renderStatus('demo@tradepulse.local', access) + renderUsage(usage);
  } catch (error) {
    statusEl.innerHTML = billingNotice() + 'Demo mode is active. Real account status will connect after Supabase keys are added.';
  }
}
function waitForSupabase() {
  return new Promise((resolve) => {
    let script = document.querySelector('script[data-tradepulse-supabase]');
    if (!window.supabase && !script) {
      script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      script.async = true;
      script.dataset.tradepulseSupabase = 'true';
      script.onerror = () => resolve(false);
      document.head.appendChild(script);
    }
    let attempts = 0;
    function check() {
      if (window.supabase) { resolve(true); return; }
      attempts += 1;
      if (attempts >= 80) { resolve(false); return; }
      window.setTimeout(check, 50);
    }
    check();
  });
}
if (!window.TRADEPULSE_SUPABASE_URL || !window.TRADEPULSE_SUPABASE_KEY) {
  if (demoPlanSelect) {
    demoPlanSelect.value = demoPlan();
    demoPlanSelect.addEventListener('change', () => {
      setDemoPlan(demoPlanSelect.value);
      showDemoStatus();
    });
  }
  showDemoStatus();
} else {
  if (demoPlanSelect) demoPlanSelect.closest('.demo-plan-panel').style.display = 'none';
  waitForSupabase().then((ready) => {
    if (!ready) {
      statusEl.innerHTML = 'Supabase could not load. Check your connection or use the local demo pages for now.';
      return;
    }
    const client = window.supabase.createClient(window.TRADEPULSE_SUPABASE_URL, window.TRADEPULSE_SUPABASE_KEY);
    client.auth.getSession().then(async ({ data, error }) => {
      const session = data ? data.session : null;
      const user = session ? session.user : null;
      if (error || !user) {
        statusEl.innerHTML = 'You are not logged in yet. <a href="/login">Log in</a> or <a href="/signup">create an account</a>.';
        return;
      }
      const headers = session.access_token ? { Authorization: 'Bearer ' + session.access_token } : {};
      currentAccount = { email: user.email || '', user_id: user.id || '', headers };
      const accessUrl = '/api/access?email=' + encodeURIComponent(user.email) + '&user_id=' + encodeURIComponent(user.id);
      const access = await fetch(accessUrl, { headers }).then((res) => res.json());
      const usageUrl = '/api/usage?email=' + encodeURIComponent(user.email) + '&user_id=' + encodeURIComponent(user.id);
      const usage = await fetch(usageUrl, { headers }).then((res) => res.json());
      document.querySelectorAll('form[action^="/billing/"]').forEach((form) => {
        const separator = form.action.includes('?') ? '&' : '?';
        if (!form.action.includes('user_id=')) form.action = form.action + separator + 'user_id=' + encodeURIComponent(user.id);
      });
      statusEl.innerHTML = billingNotice() + renderStatus(user.email, access) + renderUsage(usage);
    });
    logoutBtn.addEventListener('click', async () => { await client.auth.signOut(); window.location.href = '/'; });
  });
}
if (downloadAccountDataBtn) downloadAccountDataBtn.addEventListener('click', downloadAccountData);
if (requestAccountDeleteBtn) requestAccountDeleteBtn.addEventListener('click', requestAccountDeletion);
