(function () {
  function showBillingMessage(message) {
    var banner = document.getElementById('billing-message');
    if (!banner) {
      banner = document.createElement('section');
      banner.id = 'billing-message';
      banner.className = 'notice';
      var main = document.querySelector('main');
      if (main) main.insertBefore(banner, main.firstChild);
      else document.body.insertBefore(banner, document.body.firstChild);
    }
    banner.textContent = message;
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

  async function currentUser() {
    if (!window.TRADEPULSE_SUPABASE_URL || !window.TRADEPULSE_SUPABASE_KEY) return null;
    var ready = await waitForSupabase();
    if (!ready) return null;
    var client = window.supabase.createClient(window.TRADEPULSE_SUPABASE_URL, window.TRADEPULSE_SUPABASE_KEY);
    var result = await client.auth.getSession();
    var session = result && result.data ? result.data.session : null;
    return session ? session.user : null;
  }

  function withUserId(action, userId) {
    var url = new URL(action, window.location.origin);
    url.searchParams.set('user_id', userId);
    return url.pathname + url.search + url.hash;
  }

  document.querySelectorAll('form[data-billing-checkout], form[data-billing-portal]').forEach(function (form) {
    form.addEventListener('submit', async function (event) {
      if (form.dataset.billingSubmitting === 'true') return;
      event.preventDefault();
      showBillingMessage('Checking your logged-in account before opening Stripe...');
      var user = await currentUser();
      if (!user || !user.id) {
        localStorage.setItem('tradepulse_return_to', window.location.pathname);
        window.location.href = '/login';
        return;
      }
      form.action = withUserId(form.getAttribute('action') || '/billing/checkout?plan=pro', user.id);
      form.dataset.billingSubmitting = 'true';
      form.submit();
    });
  });
})();
