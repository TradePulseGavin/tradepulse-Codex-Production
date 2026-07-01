const resetMsg = document.getElementById('password-reset-message');
function showReset(message) { resetMsg.textContent = message; resetMsg.classList.remove('hidden'); }
function waitForSupabaseReset() {
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
  showReset('Password reset connects after SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are added. Demo pages still work locally.');
} else {
  waitForSupabaseReset().then(async (ready) => {
    if (!ready) {
      showReset('Supabase could not load. Check your connection and try again.');
      return;
    }
    const client = window.supabase.createClient(window.TRADEPULSE_SUPABASE_URL, window.TRADEPULSE_SUPABASE_KEY);
    const mode = window.TRADEPULSE_PASSWORD_RESET_MODE || 'request';
    if (mode === 'request') {
      const form = document.getElementById('password-reset-request-form');
      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = document.getElementById('reset-email').value;
        showReset('Sending reset link...');
        const result = await client.auth.resetPasswordForEmail(email, { redirectTo: window.location.origin + '/reset-password' });
        if (result.error) { showReset(result.error.message); return; }
        showReset('Reset link requested. Check your email and open the TradePulse reset link.');
      });
      return;
    }
    const code = new URL(window.location.href).searchParams.get('code');
    if (code && client.auth.exchangeCodeForSession) {
      await client.auth.exchangeCodeForSession(code);
    }
    const sessionResult = await client.auth.getSession();
    const session = sessionResult && sessionResult.data ? sessionResult.data.session : null;
    if (!session) {
      showReset('Open this page from your password reset email so Supabase can verify the reset session.');
    }
    const form = document.getElementById('password-update-form');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const password = document.getElementById('new-password').value;
      const confirm = document.getElementById('confirm-password').value;
      if (password !== confirm) { showReset('Passwords do not match.'); return; }
      showReset('Updating password...');
      const result = await client.auth.updateUser({ password });
      if (result.error) { showReset(result.error.message); return; }
      showReset('Password updated. Redirecting to login...');
      setTimeout(() => { window.location.href = '/login'; }, 900);
    });
  });
}
