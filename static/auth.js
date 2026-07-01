const msg = document.getElementById('auth-message');
const form = document.getElementById('auth-form');
function show(message) { msg.textContent = message; msg.classList.remove('hidden'); }
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
  show('Supabase is not configured yet. Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Render, then redeploy. Demo pages still work locally.');
} else {
  waitForSupabase().then((ready) => {
    if (!ready) {
      show('Supabase could not load. Check your connection or use the local demo pages for now.');
      return;
    }
    const client = window.supabase.createClient(window.TRADEPULSE_SUPABASE_URL, window.TRADEPULSE_SUPABASE_KEY);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;
      show('Working...');
      const redirectTo = window.location.origin + '/auth/confirmed';
      const result = window.TRADEPULSE_AUTH_MODE === 'signup'
        ? await client.auth.signUp({ email, password, options: { emailRedirectTo: redirectTo } })
        : await client.auth.signInWithPassword({ email, password });
      if (result.error) { show(result.error.message); return; }
      const fallback = window.TRADEPULSE_AUTH_MODE === 'signup' ? '/auth/confirmed' : '/dashboard';
      const target = localStorage.getItem('tradepulse_return_to') || fallback;
      localStorage.removeItem('tradepulse_return_to');
      show(window.TRADEPULSE_AUTH_MODE === 'signup' ? 'Account created. Check your email if Supabase asks for confirmation.' : 'Logged in. Redirecting...');
      setTimeout(() => { window.location.href = target; }, 700);
    });
  });
}
